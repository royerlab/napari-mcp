"""MCP Server runner for napari plugin."""

from __future__ import annotations

import ast
import asyncio
import contextlib
import logging
import threading
import traceback
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from io import StringIO
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import napari
    from mcp.types import ImageContent
else:
    ImageContent = Any

from qtpy.QtCore import QObject, QThread, Signal, Slot
from qtpy.QtWidgets import QApplication

from napari_mcp.output import truncate_output
from napari_mcp.server import _parse_bool, create_server
from napari_mcp.state import ServerState, StartupMode


class QtBridge(QObject):
    """Qt bridge for thread-safe operations."""

    operation_requested = Signal(object, object)  # (callable, future)

    def __init__(self):
        super().__init__()
        self.operation_requested.connect(self._execute_operation)

    @Slot(object, object)
    def _execute_operation(self, operation, future):
        """Execute operation in main thread."""
        try:
            result = operation()
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)

    def run_in_main_thread(self, operation, timeout=300.0):
        """Run an operation in the main thread and return the result.

        Parameters
        ----------
        operation : callable
            The function to execute on the Qt main thread.
        timeout : float
            Maximum seconds to wait for the operation to complete.
            Defaults to 300 (5 minutes).
        """
        if QThread.currentThread() == QApplication.instance().thread():
            return operation()

        future = Future()
        self.operation_requested.emit(operation, future)
        try:
            return future.result(timeout=timeout)
        except (TimeoutError, FutureTimeoutError):
            raise TimeoutError(
                f"napari bridge operation timed out after {timeout:.0f}s. "
                f"The operation may still be running on the napari main thread. "
                f"Consider breaking your code into smaller steps, or if the "
                f"computation is genuinely long-running, use execute_code with "
                f"a larger timeout parameter."
            ) from None


class NapariBridgeServer:
    """MCP Server that exposes the current napari viewer."""

    def __init__(self, viewer: napari.Viewer, port: int = 9999):
        """Initialize the bridge server.

        Parameters
        ----------
        viewer : napari.Viewer
            The napari viewer instance to expose
        port : int
            Port to run the HTTP server on
        """
        self.viewer = viewer
        self.port = port
        self.server_task = None
        self.loop = None
        self.thread = None

        # Qt bridge for thread-safe operations
        self.qt_bridge = QtBridge()
        app = QApplication.instance()
        if app and app.thread() != self.qt_bridge.thread():
            self.qt_bridge.moveToThread(app.thread())

        # Create state with STANDALONE mode (bridge IS the local viewer)
        self.state = ServerState(mode=StartupMode.STANDALONE, bridge_port=port)
        self.state.viewer = viewer
        self.state.gui_executor = self.qt_bridge.run_in_main_thread

        # Create server with all shared tools bound to this state
        self.server = create_server(self.state)

        # Override the 3 tools that differ in bridge mode
        self._register_bridge_overrides()

    def _register_bridge_overrides(self):
        """Register bridge-specific tool overrides."""

        @self.server.tool()
        async def session_information():
            """Get comprehensive information about the current napari session."""

            def get_info():
                viewer_info = {
                    "title": self.viewer.title,
                    "viewer_id": id(self.viewer),
                    "n_layers": len(self.viewer.layers),
                    "layer_names": [layer.name for layer in self.viewer.layers],
                    "selected_layers": [
                        layer.name for layer in self.viewer.layers.selection
                    ],
                    "ndisplay": self.viewer.dims.ndisplay,
                    "camera_center": list(self.viewer.camera.center),
                    "camera_zoom": float(self.viewer.camera.zoom),
                    "camera_angles": list(self.viewer.camera.angles)
                    if self.viewer.camera.angles
                    else [],
                    "grid_enabled": self.viewer.grid.enabled,
                }

                layer_details = []
                for layer in self.viewer.layers:
                    layer_detail: dict[str, Any] = {
                        "name": layer.name,
                        "type": layer.__class__.__name__,
                        "visible": _parse_bool(getattr(layer, "visible", True)),
                        "opacity": float(getattr(layer, "opacity", 1.0)),
                    }
                    if hasattr(layer, "data") and hasattr(layer.data, "shape"):
                        layer_detail["data_shape"] = list(layer.data.shape)
                    if hasattr(layer, "colormap"):
                        layer_detail["colormap"] = getattr(
                            layer.colormap, "name", str(layer.colormap)
                        )
                    layer_details.append(layer_detail)

                return {
                    "status": "ok",
                    "session_type": "napari_bridge_session",
                    "viewer": viewer_info,
                    "layers": layer_details,
                    "bridge_port": self.port,
                }

            return self.qt_bridge.run_in_main_thread(get_info)

        @self.server.tool()
        async def add_image(
            data: list | None = None,
            path: str | None = None,
            name: str | None = None,
            colormap: str | None = None,
            blending: str | None = None,
            channel_axis: int | str | None = None,
        ):
            """Add an image layer from data or file path."""
            if path:
                # Use file-based loading directly via Qt bridge
                import imageio.v3 as iio

                img_data = iio.imread(path)

                def _add_from_file():
                    layer = self.viewer.add_image(
                        img_data,
                        name=name,
                        colormap=colormap,
                        blending=blending,
                        channel_axis=int(channel_axis)
                        if channel_axis is not None
                        else None,
                    )
                    return {
                        "status": "ok",
                        "name": layer.name,
                        "shape": list(np.shape(img_data)),
                    }

                return self.qt_bridge.run_in_main_thread(_add_from_file)

            if data is None:
                return {
                    "status": "error",
                    "message": "Either data or path must be provided",
                }

            arr = np.asarray(data)

            def add_layer():
                kwargs: dict[str, Any] = {"name": name, "colormap": colormap}
                if blending is not None:
                    kwargs["blending"] = blending
                if channel_axis is not None:
                    kwargs["channel_axis"] = int(channel_axis)
                layer = self.viewer.add_image(arr, **kwargs)
                return {"status": "ok", "name": layer.name, "shape": list(arr.shape)}

            return self.qt_bridge.run_in_main_thread(add_layer)

        @self.server.tool()
        async def execute_code(code: str, line_limit: int | str = 30):
            """Execute Python code with access to the viewer.

            Parameters
            ----------
            code : str
                Python code string. The value of the last expression (if any)
                is returned as 'result_repr'.
            line_limit : int, default=30
                Maximum number of output lines to return. Use -1 for unlimited.
            """

            def _run_on_qt():
                """Run code on Qt main thread; returns raw (status, stdout, stderr, result_repr, error)."""
                self.state.exec_globals.setdefault("__builtins__", __builtins__)
                self.state.exec_globals["viewer"] = self.viewer
                self.state.exec_globals.setdefault("napari", None)
                self.state.exec_globals.setdefault("np", np)

                stdout_buf = StringIO()
                stderr_buf = StringIO()
                result_repr = None

                try:
                    with (
                        contextlib.redirect_stdout(stdout_buf),
                        contextlib.redirect_stderr(stderr_buf),
                    ):
                        parsed = ast.parse(code, mode="exec")
                        if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                            if len(parsed.body) > 1:
                                exec_ast = ast.Module(
                                    body=parsed.body[:-1], type_ignores=[]
                                )
                                exec(
                                    compile(exec_ast, "<bridge-exec>", "exec"),
                                    self.state.exec_globals,
                                )
                            last_expr = ast.Expression(body=parsed.body[-1].value)
                            value = eval(
                                compile(last_expr, "<bridge-eval>", "eval"),
                                self.state.exec_globals,
                            )
                            result_repr = repr(value)
                        else:
                            exec(
                                compile(parsed, "<bridge-exec>", "exec"),
                                self.state.exec_globals,
                            )

                    return (
                        "ok",
                        stdout_buf.getvalue(),
                        stderr_buf.getvalue(),
                        result_repr,
                        None,
                    )
                except Exception as e:
                    tb = traceback.format_exc()
                    return (
                        "error",
                        stdout_buf.getvalue(),
                        stderr_buf.getvalue() + tb,
                        None,
                        e,
                    )

            try:
                status, stdout_full, stderr_full, result_repr, error = (
                    self.qt_bridge.run_in_main_thread(_run_on_qt, timeout=600.0)
                )
            except TimeoutError:
                output_id = await self.state.store_output(
                    tool_name="execute_code",
                    stdout="",
                    stderr="execute_code timed out after 600s.",
                    code=code,
                    error=True,
                )
                return {
                    "status": "error",
                    "output_id": output_id,
                    "stdout": "",
                    "stderr": (
                        "execute_code timed out after 600s. "
                        "The code may still be running on the napari main thread. "
                        "To avoid this, break your computation into smaller steps "
                        "or move heavy processing to a background thread."
                    ),
                }

            # Store full output
            output_id = await self.state.store_output(
                tool_name="execute_code",
                stdout=stdout_full,
                stderr=stderr_full,
                result_repr=result_repr,
                code=code,
                **({"error": True} if status == "error" else {}),
            )

            # Build response with truncation (same shape as server's execute_code)
            response: dict[str, Any] = {
                "status": status,
                "output_id": output_id,
            }
            if result_repr is not None:
                response["result_repr"] = result_repr

            if line_limit == -1:
                response["warning"] = (
                    "Unlimited output requested. This may consume a large number "
                    "of tokens. Consider using read_output for large outputs."
                )
                response["stdout"] = stdout_full
                response["stderr"] = stderr_full
            else:
                stdout_truncated, stdout_was_truncated = truncate_output(
                    stdout_full, int(line_limit)
                )
                stderr_truncated, stderr_was_truncated = truncate_output(
                    stderr_full, int(line_limit)
                )
                response["stdout"] = stdout_truncated
                if status == "error" and error is not None:
                    error_summary = f"{type(error).__name__}: {error}"
                    if error_summary not in stderr_truncated:
                        if stderr_truncated and not stderr_truncated.endswith("\n"):
                            stderr_truncated += "\n"
                        stderr_truncated += error_summary + "\n"
                response["stderr"] = stderr_truncated
                if stdout_was_truncated or stderr_was_truncated:
                    response["truncated"] = True
                    response["message"] = (
                        f"Output truncated to {line_limit} lines. "
                        f"Use read_output('{output_id}') to retrieve full output."
                    )

            return response

    def _run_server_thread(self):
        """Run the server in a separate thread with its own event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.server.run(
                transport="http", host="127.0.0.1", port=self.port, path="/mcp"
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Server error while running MCP server thread"
            )

    def start(self):
        """Start the MCP server in a background thread."""
        if self.thread is not None and self.thread.is_alive():
            return False

        self.thread = threading.Thread(target=self._run_server_thread, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """Stop the MCP server."""
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except RuntimeError:
                pass

        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None

        self.loop = None
        return True

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.thread is not None and self.thread.is_alive()

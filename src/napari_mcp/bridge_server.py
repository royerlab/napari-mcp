"""Bridge MCP server for the napari plugin.

Creates a ``ServerState`` and calls ``create_server()`` to build the base
server, then overrides ``session_information``, ``add_layer``, and
``execute_code`` with thread-safe versions that dispatch to the Qt main thread
via ``QtBridge``.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import napari
    from mcp.types import ImageContent
else:
    ImageContent = Any

from qtpy.QtCore import QObject, QThread, Signal, Slot
from qtpy.QtWidgets import QApplication

from napari_mcp._helpers import (
    build_layer_detail,
    build_truncated_response,
    create_layer_on_viewer,
    resolve_layer_type,
    run_code,
)
from napari_mcp.server import create_server
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

        # Remove lifecycle tools that should not be available in bridge mode
        # (the viewer is managed by napari, not the agent)
        for name in ("close_viewer", "init_viewer"):
            self.server._tool_manager._tools.pop(name, None)

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

                layer_details = [
                    build_layer_detail(layer) for layer in self.viewer.layers
                ]

                return {
                    "status": "ok",
                    "session_type": "napari_bridge_session",
                    "viewer": viewer_info,
                    "layers": layer_details,
                    "bridge_port": self.port,
                }

            return self.qt_bridge.run_in_main_thread(get_info)

        @self.server.tool()
        async def add_layer(
            layer_type: str,
            path: str | None = None,
            data: list | None = None,
            data_var: str | None = None,
            name: str | None = None,
            colormap: str | None = None,
            blending: str | None = None,
            channel_axis: int | str | None = None,
            size: float | str | None = None,
            shape_type: str | None = None,
            edge_color: str | None = None,
            face_color: str | None = None,
            edge_width: float | str | None = None,
        ):
            """Add a layer via the bridge (Qt main thread)."""
            lt = resolve_layer_type(layer_type)
            if lt is None:
                return {
                    "status": "error",
                    "message": (
                        f"Unknown layer_type '{layer_type}'. "
                        f"Valid types: image, labels, points, shapes, vectors, tracks, surface"
                    ),
                }

            # Validate only one data source
            sources = sum([data_var is not None, data is not None, path is not None])
            if sources > 1:
                return {
                    "status": "error",
                    "message": "Provide only ONE of 'path', 'data', or 'data_var', not multiple.",
                }

            # Resolve data
            resolved = None
            if path and lt in ("image", "labels"):
                from pathlib import Path as _Path

                import imageio.v3 as iio

                p = _Path(path).expanduser().resolve(strict=False)
                if not p.exists():
                    return {
                        "status": "error",
                        "message": f"File not found: {p}",
                    }
                try:
                    resolved = iio.imread(str(p))
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to read file: {e}",
                    }
            elif data_var:
                if data_var not in self.state.exec_globals:
                    return {
                        "status": "error",
                        "message": f"Variable '{data_var}' not found in execution namespace",
                    }
                resolved = self.state.exec_globals[data_var]
            elif data is not None:
                resolved = data

            if resolved is None:
                return {
                    "status": "error",
                    "message": "Provide 'path', 'data', or 'data_var'.",
                }

            def _do_add():
                return create_layer_on_viewer(
                    self.viewer,
                    resolved,
                    lt,
                    name=name,
                    colormap=colormap,
                    blending=blending,
                    channel_axis=channel_axis,
                    size=size,
                    shape_type=shape_type,
                    edge_color=edge_color,
                    face_color=face_color,
                    edge_width=edge_width,
                )

            try:
                return self.qt_bridge.run_in_main_thread(_do_add)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to add {layer_type} layer: {e}",
                }

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
                """Run code on Qt main thread using shared helper."""
                self.state.exec_globals.setdefault("__builtins__", __builtins__)
                self.state.exec_globals["viewer"] = self.viewer
                self.state.exec_globals.setdefault("napari", None)
                self.state.exec_globals.setdefault("np", np)
                return run_code(
                    code, self.state.exec_globals, source_label="<bridge-exec>"
                )

            try:
                stdout_full, stderr_full, result_repr, error = (
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

            status = "error" if error else "ok"
            output_id = await self.state.store_output(
                tool_name="execute_code",
                stdout=stdout_full,
                stderr=stderr_full,
                result_repr=result_repr,
                code=code,
                **({"error": True} if error else {}),
            )

            return build_truncated_response(
                status=status,
                output_id=output_id,
                stdout_full=stdout_full,
                stderr_full=stderr_full,
                result_repr=result_repr,
                line_limit=line_limit,
                error=error,
            )

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

"""MCP Server runner for napari plugin."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
import threading
from concurrent.futures import Future
from functools import wraps
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Any

import numpy as np
from fastmcp import FastMCP

from napari_mcp.server import NapariMCPTools as _Tools

if TYPE_CHECKING:
    import napari
    from mcp.types import ImageContent
else:
    ImageContent = Any

from PIL import Image
from qtpy.QtCore import QObject, QThread, Signal, Slot
from qtpy.QtWidgets import QApplication

from napari_mcp.server import _parse_bool


class QtBridge(QObject):
    """Qt bridge for thread-safe operations."""

    # Signal to request operation in main thread
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

    def run_in_main_thread(self, operation):
        """Run an operation in the main thread and return the result."""
        # Check if we're already on the main thread using Qt's method
        if QThread.currentThread() == QApplication.instance().thread():
            # We're already on the main thread, execute directly
            return operation()

        # Use signal/slot mechanism for cross-thread execution
        future = Future()
        self.operation_requested.emit(operation, future)
        return future.result(timeout=5.0)


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
        self.server = FastMCP("Napari Bridge MCP Server")
        self.server_task = None
        self.loop = None
        self.thread = None
        self._exec_globals: dict[str, Any] = {}
        self.qt_bridge = QtBridge()
        # Move QtBridge to main thread for proper signal/slot communication
        app = QApplication.instance()
        if app and app.thread() != self.qt_bridge.thread():
            self.qt_bridge.moveToThread(app.thread())
        # Expose this viewer to shared implementation so server/bridge delegate consistently
        try:
            from napari_mcp import server as _srv_impl

            _srv_impl._viewer = viewer  # type: ignore[attr-defined]

            # Disable external proxying inside the bridge to avoid loops
            async def _no_proxy(*_args, **_kwargs):
                return None

            async def _no_detect():
                return (None, None)

            _srv_impl._proxy_to_external = _no_proxy  # type: ignore[attr-defined]
            _srv_impl._detect_external_viewer = _no_detect  # type: ignore[attr-defined]
            # Configure shared tools to run GUI ops on the main thread
            if hasattr(_srv_impl, "set_gui_executor"):
                _srv_impl.set_gui_executor(self.qt_bridge.run_in_main_thread)

            # Also disable external session info to prevent recursion
            async def _no_external_session_info(_port):
                raise RuntimeError("external session disabled in bridge")

            if hasattr(_srv_impl, "NapariMCPTools"):
                _srv_impl.NapariMCPTools._external_session_information = (  # type: ignore[attr-defined, method-assign]
                    _no_external_session_info
                )
        except Exception:
            pass
        self._setup_tools()

    def _run_in_main(self, func):
        """Decorator to run a function in the main thread."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.qt_bridge.run_in_main_thread(lambda: func(*args, **kwargs))

        return wrapper

    def _encode_png_base64(self, img: np.ndarray) -> dict[str, str]:
        """Encode image as base64 PNG."""
        pil = Image.fromarray(img)
        buf = BytesIO()
        pil.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode("ascii")
        return {"mime_type": "image/png", "base64_data": data}

    def _setup_tools(self):
        """Register all MCP tools with the server."""

        @self.server.tool
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
                    layer_detail = {
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

            # Run in main thread via Qt bridge and avoid any external proxy recursion
            return self.qt_bridge.run_in_main_thread(get_info)

        @self.server.tool
        async def list_layers():
            """Return a list of layers with key properties."""
            return await _Tools.list_layers()

        @self.server.tool
        async def add_image(
            data: list | None = None,
            path: str | None = None,
            name: str | None = None,
            colormap: str | None = None,
        ):
            """Add an image layer from data or file path."""
            if path:
                return await _Tools.add_image(path=path, name=name, colormap=colormap)

            if data is None:
                return {
                    "status": "error",
                    "message": "Either data or path must be provided",
                }

            # Fallback: add from in-memory data on GUI thread
            arr = np.asarray(data)

            def add_layer():
                layer = self.viewer.add_image(arr, name=name, colormap=colormap)
                return {"status": "ok", "name": layer.name, "shape": list(arr.shape)}

            return self.qt_bridge.run_in_main_thread(add_layer)

        @self.server.tool
        async def add_points(
            points: list[list[float]], name: str | None = None, size: float = 10.0
        ):
            """Add a points layer."""
            return await _Tools.add_points(points=points, name=name, size=size)

        @self.server.tool
        async def remove_layer(name: str):
            """Remove a layer by name."""
            return await _Tools.remove_layer(name)

        @self.server.tool
        async def rename_layer(old_name: str, new_name: str):
            """Rename a layer (delegates to set_layer_properties)."""
            return await _Tools.set_layer_properties(name=old_name, new_name=new_name)

        @self.server.tool
        async def set_layer_properties(
            name: str,
            visible: bool | None = None,
            opacity: float | None = None,
            colormap: str | None = None,
        ):
            """Set properties on a layer."""
            return await _Tools.set_layer_properties(
                name=name, visible=visible, opacity=opacity, colormap=colormap
            )

        @self.server.tool
        async def reset_view():
            """Reset the camera view to fit data."""
            return await _Tools.reset_view()

        @self.server.tool
        async def set_zoom(zoom: float):
            """Set camera zoom factor."""
            return await _Tools.set_camera(zoom=zoom)

        @self.server.tool
        async def set_ndisplay(ndisplay: int):
            """Set number of displayed dimensions (2 or 3)."""
            return await _Tools.set_ndisplay(ndisplay)

        @self.server.tool
        async def screenshot(canvas_only: bool | str = True) -> ImageContent:
            """Take a screenshot and return as base64 PNG."""
            return await _Tools.screenshot(canvas_only=canvas_only)

        @self.server.tool
        async def timelapse_screenshot(
            axis: int,
            slice_range: str,
            canvas_only: bool | str = True,
            interpolate_to_fit: bool = False,
        ) -> list[ImageContent]:
            """Capture a series of screenshots while sweeping a dims axis with optional downsampling to fit size cap."""
            return await _Tools.timelapse_screenshot(
                axis=axis,
                slice_range=slice_range,
                canvas_only=canvas_only,
                interpolate_to_fit=interpolate_to_fit,
            )

        @self.server.tool
        async def execute_code(code: str):
            """Execute Python code with access to the viewer."""

            def execute():
                self._exec_globals.setdefault("__builtins__", __builtins__)
                self._exec_globals["viewer"] = self.viewer
                self._exec_globals.setdefault("napari", None)
                self._exec_globals.setdefault("np", np)

                stdout_buf = StringIO()
                stderr_buf = StringIO()
                result_repr = None

                try:
                    with (
                        contextlib.redirect_stdout(stdout_buf),
                        contextlib.redirect_stderr(stderr_buf),
                    ):
                        import ast

                        parsed = ast.parse(code, mode="exec")
                        if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                            if len(parsed.body) > 1:
                                exec_ast = ast.Module(
                                    body=parsed.body[:-1], type_ignores=[]
                                )
                                exec(
                                    compile(exec_ast, "<bridge-exec>", "exec"),
                                    self._exec_globals,
                                )
                            last_expr = ast.Expression(body=parsed.body[-1].value)
                            value = eval(
                                compile(last_expr, "<bridge-eval>", "eval"),
                                self._exec_globals,
                            )
                            result_repr = repr(value)
                        else:
                            exec(
                                compile(parsed, "<bridge-exec>", "exec"),
                                self._exec_globals,
                            )

                    return {
                        "status": "ok",
                        **({"result_repr": result_repr} if result_repr else {}),
                        "stdout": stdout_buf.getvalue(),
                        "stderr": stderr_buf.getvalue(),
                    }
                except Exception:
                    import traceback

                    tb = traceback.format_exc()
                    return {
                        "status": "error",
                        "stdout": stdout_buf.getvalue(),
                        "stderr": stderr_buf.getvalue() + tb,
                    }

            return self.qt_bridge.run_in_main_thread(execute)

        @self.server.tool
        async def install_packages(
            packages: list[str],
            upgrade: bool | None = False,
            no_deps: bool | None = False,
            index_url: str | None = None,
            extra_index_url: str | None = None,
            pre: bool | None = False,
            line_limit: int | str = 30,
            timeout: int = 240,
        ):
            """Install Python packages using pip.

            Install packages into the currently running server environment.
            """
            # Delegate to shared implementation (no Qt main-thread requirement)
            return await _Tools.install_packages(
                packages=packages,
                upgrade=upgrade,
                no_deps=no_deps,
                index_url=index_url,
                extra_index_url=extra_index_url,
                pre=pre,
                line_limit=line_limit,
                timeout=timeout,
            )

    def _run_server_thread(self):
        """Run the server in a separate thread with its own event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            # Run the server synchronously (FastMCP handles the async internally)
            self.server.run(
                transport="http", host="127.0.0.1", port=self.port, path="/mcp"
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Server error while running MCP server thread"
            )

    def start(self):
        """Start the MCP server in a background thread."""
        # Thread-safe check and creation
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
                pass  # Loop already stopped/closed

        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None

        # Clean up loop reference
        self.loop = None
        return True

    # Method wrappers to expose tools as direct methods for easier testing
    async def session_information(self):
        """Get session information via the registered tool."""
        tool = await self.server.get_tool("session_information")
        return await tool.fn()

    async def list_layers(self):
        """List layers via the registered tool."""
        tool = await self.server.get_tool("list_layers")
        return await tool.fn()

    async def execute_code(self, code: str):
        """Execute code via the registered tool."""
        tool = await self.server.get_tool("execute_code")
        return await tool.fn(code)

    async def screenshot(self, canvas_only: bool = True) -> dict[str, str]:
        """Take screenshot via the registered tool."""
        tool = await self.server.get_tool("screenshot")
        return await tool.fn(canvas_only)

    async def timelapse_screenshot(
        self,
        axis: int,
        slice_range: str,
        canvas_only: bool = True,
        interpolate_to_fit: bool = False,
    ) -> list[dict[str, str]]:
        """Timelapse screenshot via the registered tool."""
        tool = await self.server.get_tool("timelapse_screenshot")
        return await tool.fn(axis, slice_range, canvas_only, interpolate_to_fit)

    async def add_image(self, **kwargs):
        """Add image via the registered tool."""
        tool = await self.server.get_tool("add_image")
        return await tool.fn(**kwargs)

    async def add_points(self, **kwargs):
        """Add points via the registered tool."""
        tool = await self.server.get_tool("add_points")
        return await tool.fn(**kwargs)

    async def remove_layer(self, name: str):
        """Remove layer via the registered tool."""
        tool = await self.server.get_tool("remove_layer")
        return await tool.fn(name)

    async def install_packages(self, **kwargs):
        """Install packages via the registered tool."""
        tool = await self.server.get_tool("install_packages")
        return await tool.fn(**kwargs)

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.thread is not None and self.thread.is_alive()

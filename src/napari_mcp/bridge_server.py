"""MCP Server runner for napari plugin."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import threading
import traceback
from concurrent.futures import Future
from functools import wraps
from io import BytesIO, StringIO
from typing import Any

import napari
import numpy as np
from fastmcp import FastMCP
from PIL import Image
from qtpy.QtCore import QObject, QThread, Signal, Slot
from qtpy.QtWidgets import QApplication


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
                        "visible": bool(getattr(layer, "visible", True)),
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

            # Run in main thread via Qt bridge
            return self.qt_bridge.run_in_main_thread(get_info)

        @self.server.tool
        async def list_layers():
            """Return a list of layers with key properties."""

            def get_layers():
                result = []
                for lyr in self.viewer.layers:
                    entry = {
                        "name": lyr.name,
                        "type": lyr.__class__.__name__,
                        "visible": bool(getattr(lyr, "visible", True)),
                        "opacity": float(getattr(lyr, "opacity", 1.0)),
                    }
                    if hasattr(lyr, "colormap"):
                        entry["colormap"] = getattr(
                            lyr.colormap, "name", str(lyr.colormap)
                        )
                    result.append(entry)
                return result

            return self.qt_bridge.run_in_main_thread(get_layers)

        @self.server.tool
        async def add_image(
            data: list | None = None,
            path: str | None = None,
            name: str | None = None,
            colormap: str | None = None,
        ):
            """Add an image layer from data or file path."""
            # Load data if path provided (can be done in any thread)
            if path:
                import imageio.v3 as iio

                img_data = iio.imread(path)
            elif data:
                img_data = np.asarray(data)
            else:
                return {
                    "status": "error",
                    "message": "Either data or path must be provided",
                }

            def add_layer():
                layer = self.viewer.add_image(img_data, name=name, colormap=colormap)
                return {
                    "status": "ok",
                    "name": layer.name,
                    "shape": list(img_data.shape),
                }

            return self.qt_bridge.run_in_main_thread(add_layer)

        @self.server.tool
        async def add_points(
            points: list[list[float]], name: str | None = None, size: float = 10.0
        ):
            """Add a points layer."""
            arr = np.asarray(points, dtype=float)

            def add_layer():
                layer = self.viewer.add_points(arr, name=name, size=size)
                return {
                    "status": "ok",
                    "name": layer.name,
                    "n_points": int(arr.shape[0]),
                }

            return self.qt_bridge.run_in_main_thread(add_layer)

        @self.server.tool
        async def remove_layer(name: str):
            """Remove a layer by name."""

            def remove():
                if name in self.viewer.layers:
                    self.viewer.layers.remove(name)
                    return {"status": "removed", "name": name}
                return {"status": "not_found", "name": name}

            return self.qt_bridge.run_in_main_thread(remove)

        @self.server.tool
        async def rename_layer(old_name: str, new_name: str):
            """Rename a layer."""

            def rename():
                if old_name not in self.viewer.layers:
                    return {"status": "not_found", "name": old_name}
                lyr = self.viewer.layers[old_name]
                lyr.name = new_name
                return {"status": "ok", "old": old_name, "new": new_name}

            return self.qt_bridge.run_in_main_thread(rename)

        @self.server.tool
        async def set_layer_properties(
            name: str,
            visible: bool | None = None,
            opacity: float | None = None,
            colormap: str | None = None,
        ):
            """Set properties on a layer."""

            def set_props():
                if name not in self.viewer.layers:
                    return {"status": "not_found", "name": name}
                lyr = self.viewer.layers[name]
                if visible is not None:
                    lyr.visible = bool(visible)
                if opacity is not None:
                    lyr.opacity = float(opacity)
                if colormap is not None and hasattr(lyr, "colormap"):
                    lyr.colormap = colormap
                return {"status": "ok", "name": lyr.name}

            return self.qt_bridge.run_in_main_thread(set_props)

        @self.server.tool
        async def reset_view():
            """Reset the camera view to fit data."""

            def reset():
                self.viewer.reset_view()
                return {"status": "ok"}

            return self.qt_bridge.run_in_main_thread(reset)

        @self.server.tool
        async def set_zoom(zoom: float):
            """Set camera zoom factor."""

            def set_z():
                self.viewer.camera.zoom = float(zoom)
                return {"status": "ok", "zoom": float(self.viewer.camera.zoom)}

            return self.qt_bridge.run_in_main_thread(set_z)

        @self.server.tool
        async def set_ndisplay(ndisplay: int):
            """Set number of displayed dimensions (2 or 3)."""

            def set_nd():
                self.viewer.dims.ndisplay = int(ndisplay)
                return {"status": "ok", "ndisplay": int(self.viewer.dims.ndisplay)}

            return self.qt_bridge.run_in_main_thread(set_nd)

        @self.server.tool
        async def screenshot(canvas_only: bool = True) -> dict[str, str]:
            """Take a screenshot and return as base64 PNG."""

            def take_screenshot():
                arr = self.viewer.screenshot(canvas_only=canvas_only)
                if not isinstance(arr, np.ndarray):
                    arr = np.asarray(arr)
                if arr.dtype != np.uint8:
                    arr = arr.astype(np.uint8, copy=False)
                return self._encode_png_base64(arr)

            return self.qt_bridge.run_in_main_thread(take_screenshot)

        @self.server.tool
        async def execute_code(code: str):
            """Execute Python code with access to the viewer."""

            def execute():
                self._exec_globals.setdefault("__builtins__", __builtins__)
                self._exec_globals["viewer"] = self.viewer
                self._exec_globals.setdefault("napari", napari)
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
                    tb = traceback.format_exc()
                    return {
                        "status": "error",
                        "stdout": stdout_buf.getvalue(),
                        "stderr": stderr_buf.getvalue() + tb,
                    }

            return self.qt_bridge.run_in_main_thread(execute)

    def _run_server_thread(self):
        """Run the server in a separate thread with its own event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            # Run the server synchronously (FastMCP handles the async internally)
            self.server.run(
                transport="http", host="127.0.0.1", port=self.port, path="/mcp"
            )
        except Exception as e:
            print(f"Server error: {e}")

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

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.thread is not None and self.thread.is_alive()

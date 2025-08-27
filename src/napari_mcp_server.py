"""
Napari MCP Server

Exposes a set of MCP tools to control a running napari Viewer: layer control,
viewer control (zoom, camera, dims), and a screenshot tool returning a PNG image
as base64.
"""

from __future__ import annotations

import asyncio
import base64
from io import BytesIO, StringIO
import contextlib
import traceback
import ast
import tempfile
import uuid
import io
from typing import Any, Dict, List, Optional
import sys
import shlex
import asyncio.subprocess

import numpy as np
from PIL import Image
from qtpy import QtWidgets

import napari
import fastmcp
from fastmcp import FastMCP 


server = FastMCP("Napari MCP Server", dependencies=["napari", "Pillow", "imageio", "numpy", "qtpy", "PyQt6"])


# Global GUI singletons (created lazily)
_qt_app: Optional[QtWidgets.QApplication] = None
_viewer: Optional[napari.Viewer] = None
_viewer_lock: asyncio.Lock = asyncio.Lock()
_exec_globals: Dict[str, Any] = {}
_qt_pump_task: Optional[asyncio.Task] = None
_window_close_connected: bool = False


def _ensure_qt_app() -> QtWidgets.QApplication:
    global _qt_app
    app = QtWidgets.QApplication.instance()
    if app is None:
        _qt_app = QtWidgets.QApplication([])
        app = _qt_app
    # Ensure the application stays alive even if the last window is closed
    try:
        app.setQuitOnLastWindowClosed(False)
    except Exception:
        # Best-effort; some headless backends may not support this
        pass
    return app  # type: ignore[return-value]


def _ensure_viewer() -> napari.Viewer:
    global _viewer
    _ensure_qt_app()
    if _viewer is None:
        _viewer = napari.Viewer()
        _connect_window_destroyed_signal(_viewer)
    return _viewer


def _connect_window_destroyed_signal(viewer: napari.Viewer) -> None:
    """Connect to the Qt window destroyed signal to clear our singleton.

    This prevents stale references after a user manually closes the window.
    """
    global _window_close_connected, _viewer
    if _window_close_connected:
        return
    try:
        qt_win = viewer.window._qt_window  # type: ignore[attr-defined]

        def _on_destroyed(*_args: Any) -> None:
            # Clear the global so future calls re-create a fresh viewer
            # Keep the Qt application alive
            global _viewer
            _viewer = None

        qt_win.destroyed.connect(_on_destroyed)  # type: ignore[attr-defined]
        _window_close_connected = True
    except Exception:
        # If anything goes wrong, continue without the connection
        pass


def _process_events(cycles: int = 2) -> None:
    app = _ensure_qt_app()
    for _ in range(max(1, cycles)):
        app.processEvents()


def _encode_png_base64(img: np.ndarray) -> Dict[str, str]:
    pil = Image.fromarray(img)
    buf = BytesIO()
    pil.save(buf, format="PNG")
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"mime_type": "image/png", "base64_data": data}


async def _qt_event_pump() -> None:
    """Periodically process Qt events so the GUI remains responsive.

    We avoid calling napari.run() to keep the server responsive while still
    allowing the user to interact with the GUI.
    """
    try:
        # Tight loop with small sleep keeps UI fluid without starving asyncio
        while True:
            _process_events(2)
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        # Graceful shutdown of the pump
        pass


async def init_viewer(title: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None) -> Dict[str, Any]:
    """
    Create or return the singleton napari viewer.

    - title: Optional window title
    - width/height: Optional initial canvas size in logical pixels
    """
    async with _viewer_lock:
        v = _ensure_viewer()
        if title:
            v.title = title
        if width or height:
            w = int(width) or v.window.qt_viewer.canvas.size().width()
            h = int(height) or v.window.qt_viewer.canvas.size().height()
            v.window.qt_viewer.canvas.native.resize(w, h)
        _process_events()
        return {"status": "ok", "title": v.title, "layers": [lyr.name for lyr in v.layers]}


async def start_gui(focus: bool = True) -> Dict[str, Any]:
    """Start a non-blocking GUI event pump so the user can use the napari UI.

    - focus: If True, bring the window to the front.

    Notes:
    - We intentionally do NOT call napari.run() to avoid blocking the server.
    - The Qt application is configured to not quit when the last window closes.
    """
    global _qt_pump_task
    async with _viewer_lock:
        app = _ensure_qt_app()
        try:
            app.setQuitOnLastWindowClosed(False)
        except Exception:
            pass
        v = _ensure_viewer()
        _connect_window_destroyed_signal(v)

        # Optionally show and focus the window
        try:
            qt_win = v.window._qt_window  # type: ignore[attr-defined]
            qt_win.show()
            if focus:
                qt_win.raise_()
                qt_win.activateWindow()
        except Exception:
            pass

        # Start the pump if not already running
        if _qt_pump_task is None or _qt_pump_task.done():
            loop = asyncio.get_running_loop()
            _qt_pump_task = loop.create_task(_qt_event_pump())
            status = "started"
        else:
            status = "already_running"
        _process_events(2)
        return {"status": status}


async def stop_gui() -> Dict[str, Any]:
    """Stop the non-blocking GUI event pump (leaves the app and viewer as-is)."""
    global _qt_pump_task
    async with _viewer_lock:
        if _qt_pump_task is not None and not _qt_pump_task.done():
            _qt_pump_task.cancel()
            try:
                await _qt_pump_task
            except asyncio.CancelledError:
                pass
        _qt_pump_task = None
        _process_events(1)
        return {"status": "stopped"}


async def is_gui_running() -> Dict[str, Any]:
    """Return whether the GUI pump is currently running."""
    async with _viewer_lock:
        running = _qt_pump_task is not None and not _qt_pump_task.done()
        return {"status": "ok", "running": bool(running)}


async def close_viewer() -> Dict[str, Any]:
    """Close the viewer window and clear all layers."""
    async with _viewer_lock:
        global _viewer
        if _viewer is not None:
            _viewer.close()
            _viewer = None
            _process_events()
            return {"status": "closed"}
        return {"status": "no_viewer"}


async def session_information() -> Dict[str, Any]:
    """Get comprehensive information about the current napari session."""
    import platform
    import os
    
    async with _viewer_lock:
        global _viewer, _qt_pump_task, _exec_globals
        
        # Check if viewer exists
        viewer_exists = _viewer is not None
        if not viewer_exists:
            return {
                "status": "ok",
                "session_type": "napari_mcp_standalone_session",
                "timestamp": str(np.datetime64('now')),
                "viewer": None,
                "message": "No viewer currently initialized. Call init_viewer() first."
            }
        
        v = _viewer
        
        # Viewer information
        viewer_info = {
            "title": v.title,
            "viewer_id": id(v),
            "n_layers": len(v.layers),
            "layer_names": [layer.name for layer in v.layers],
            "selected_layers": [layer.name for layer in v.layers.selection],
            "current_step": dict(enumerate(v.dims.current_step)) if hasattr(v.dims, 'current_step') else {},
            "ndisplay": v.dims.ndisplay,
            "camera_center": list(v.camera.center),
            "camera_zoom": float(v.camera.zoom),
            "camera_angles": list(v.camera.angles) if v.camera.angles else [],
            "grid_enabled": v.grid.enabled,
        }
        
        # System information
        system_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "napari_version": napari.__version__,
            "process_id": os.getpid(),
            "working_directory": os.getcwd(),
        }
        
        # Session status
        gui_running = _qt_pump_task is not None and not _qt_pump_task.done()
        session_info = {
            "server_type": "napari_mcp_standalone",
            "viewer_instance": f"<napari.Viewer at {hex(id(v))}>",
            "gui_pump_running": gui_running,
            "execution_namespace_vars": list(_exec_globals.keys()),
            "qt_app_available": _qt_app is not None,
        }
        
        # Layer details
        layer_details = []
        for layer in v.layers:
            layer_detail = {
                "name": layer.name,
                "type": layer.__class__.__name__,
                "visible": bool(getattr(layer, "visible", True)),
                "opacity": float(getattr(layer, "opacity", 1.0)),
                "blending": getattr(layer, "blending", None),
                "data_shape": list(layer.data.shape) if hasattr(layer, 'data') and hasattr(layer.data, 'shape') else None,
                "data_dtype": str(layer.data.dtype) if hasattr(layer, 'data') and hasattr(layer.data, 'dtype') else None,
                "layer_id": id(layer),
            }
            
            # Add layer-specific properties
            if hasattr(layer, "colormap"):
                layer_detail["colormap"] = getattr(layer.colormap, "name", str(layer.colormap))
            if hasattr(layer, "contrast_limits"):
                try:
                    cl = getattr(layer, "contrast_limits")
                    layer_detail["contrast_limits"] = [float(cl[0]), float(cl[1])]
                except Exception:
                    pass
            if hasattr(layer, "gamma"):
                layer_detail["gamma"] = float(getattr(layer, "gamma", 1.0))
            
            layer_details.append(layer_detail)
        
        return {
            "status": "ok",
            "session_type": "napari_mcp_standalone_session",
            "timestamp": str(np.datetime64('now')),
            "viewer": viewer_info,
            "system": system_info,
            "session": session_info,
            "layers": layer_details,
        }


async def list_layers() -> List[Dict[str, Any]]:
    """Return a list of layers with key properties."""
    async with _viewer_lock:
        v = _ensure_viewer()
        result: List[Dict[str, Any]] = []
        for lyr in v.layers:
            entry = {
                "name": lyr.name,
                "type": lyr.__class__.__name__,
                "visible": bool(getattr(lyr, "visible", True)),
                "opacity": float(getattr(lyr, "opacity", 1.0)),
                "blending": getattr(lyr, "blending", None),
            }
            if hasattr(lyr, "colormap") and getattr(lyr, "colormap", None) is not None:
                entry["colormap"] = getattr(lyr.colormap, "name", None) or str(lyr.colormap)
            if hasattr(lyr, "contrast_limits") and getattr(lyr, "contrast_limits", None) is not None:
                try:
                    cl = list(getattr(lyr, "contrast_limits"))
                    entry["contrast_limits"] = [float(cl[0]), float(cl[1])]
                except Exception:
                    pass
            result.append(entry)
        return result


async def add_image(path: str, name: Optional[str] = None, colormap: Optional[str] = None, blending: Optional[str] = None, channel_axis: Optional[int] = None) -> Dict[str, Any]:
    """
    Add an image layer from a file path.

    - path: Path to an image readable by imageio (e.g., PNG, TIFF, OME-TIFF)
    - name: Optional layer name
    - colormap: Optional napari colormap name (e.g., 'gray', 'magma')
    - blending: Optional blending mode (e.g., 'translucent')
    - channel_axis: If provided, interpret that axis as channels
    """
    import imageio.v3 as iio

    async with _viewer_lock:
        v = _ensure_viewer()
        data = iio.imread(path)
        layer = v.add_image(data, name=name, colormap=colormap, blending=blending, channel_axis=channel_axis)
        _process_events()
        return {"status": "ok", "name": layer.name, "shape": list(np.shape(data))}


async def add_labels(path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a labels layer from a file path (e.g., PNG/TIFF with integer labels).
    """
    import imageio.v3 as iio

    async with _viewer_lock:
        v = _ensure_viewer()
        data = iio.imread(path)
        layer = v.add_labels(data, name=name)
        _process_events()
        return {"status": "ok", "name": layer.name, "shape": list(np.shape(data))}


async def add_points(points: List[List[float]], name: Optional[str] = None, size: float = 10.0) -> Dict[str, Any]:
    """
    Add a points layer.

    - points: List of [y, x] or [z, y, x] coordinates
    - name: Optional layer name
    - size: Point size in pixels
    """
    async with _viewer_lock:
        v = _ensure_viewer()
        arr = np.asarray(points, dtype=float)
        layer = v.add_points(arr, name=name, size=size)
        _process_events()
        return {"status": "ok", "name": layer.name, "n_points": int(arr.shape[0])}


async def remove_layer(name: str) -> Dict[str, Any]:
    """Remove a layer by name."""
    async with _viewer_lock:
        v = _ensure_viewer()
        if name in v.layers:
            v.layers.remove(name)
            _process_events()
            return {"status": "removed", "name": name}
        return {"status": "not_found", "name": name}


async def rename_layer(old_name: str, new_name: str) -> Dict[str, Any]:
    """Rename a layer."""
    async with _viewer_lock:
        v = _ensure_viewer()
        if old_name not in v.layers:
            return {"status": "not_found", "name": old_name}
        lyr = v.layers[old_name]
        lyr.name = new_name
        _process_events()
        return {"status": "ok", "old": old_name, "new": new_name}


async def set_layer_properties(
    name: str,
    visible: Optional[bool] = None,
    opacity: Optional[float] = None,
    colormap: Optional[str] = None,
    blending: Optional[str] = None,
    contrast_limits: Optional[List[float]] = None,
    gamma: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Set common properties on a layer by name.
    """
    async with _viewer_lock:
        v = _ensure_viewer()
        if name not in v.layers:
            return {"status": "not_found", "name": name}
        lyr = v.layers[name]
        if visible is not None and hasattr(lyr, "visible"):
            lyr.visible = bool(visible)
        if opacity is not None and hasattr(lyr, "opacity"):
            lyr.opacity = float(opacity)
        if colormap is not None and hasattr(lyr, "colormap"):
            lyr.colormap = colormap
        if blending is not None and hasattr(lyr, "blending"):
            lyr.blending = blending
        if contrast_limits is not None and hasattr(lyr, "contrast_limits"):
            try:
                lyr.contrast_limits = [float(contrast_limits[0]), float(contrast_limits[1])]
            except Exception:
                pass
        if gamma is not None and hasattr(lyr, "gamma"):
            lyr.gamma = float(gamma)
        _process_events()
        return {"status": "ok", "name": lyr.name}


async def reorder_layer(name: str, index: Optional[int] = None, before: Optional[str] = None, after: Optional[str] = None) -> Dict[str, Any]:
    """
    Reorder a layer by name.

    Provide exactly one of:
    - index: absolute target index
    - before: move before this layer name
    - after: move after this layer name
    """
    async with _viewer_lock:
        v = _ensure_viewer()
        if name not in v.layers:
            return {"status": "not_found", "name": name}
        if sum(x is not None for x in (index, before, after)) != 1:
            return {"status": "error", "message": "Provide exactly one of index, before, or after"}
        cur = v.layers.index(name)
        target = cur
        if index is not None:
            target = max(0, min(int(index), len(v.layers) - 1))
        elif before is not None:
            if before not in v.layers:
                return {"status": "not_found", "name": before}
            target = v.layers.index(before)
        elif after is not None:
            if after not in v.layers:
                return {"status": "not_found", "name": after}
            target = v.layers.index(after) + 1
        if target != cur:
            v.layers.move(cur, target)
        _process_events()
        return {"status": "ok", "name": name, "index": v.layers.index(name)}


async def set_active_layer(name: str) -> Dict[str, Any]:
    """Set the selected/active layer by name."""
    async with _viewer_lock:
        v = _ensure_viewer()
        if name not in v.layers:
            return {"status": "not_found", "name": name}
        v.layers.selection = {v.layers[name]}
        _process_events()
        return {"status": "ok", "active": name}


async def reset_view() -> Dict[str, Any]:
    """Reset the camera view to fit data."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.reset_view()
        _process_events()
        return {"status": "ok"}


async def set_zoom(zoom: float) -> Dict[str, Any]:
    """Set camera zoom factor."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.camera.zoom = float(zoom)
        _process_events()
        return {"status": "ok", "zoom": float(v.camera.zoom)}


async def set_camera(center: Optional[List[float]] = None, zoom: Optional[float] = None, angle: Optional[float] = None) -> Dict[str, Any]:
    """Set camera properties: center, zoom, and/or angle."""
    async with _viewer_lock:
        v = _ensure_viewer()
        if center is not None:
            v.camera.center = list(map(float, center))
        if zoom is not None:
            v.camera.zoom = float(zoom)
        if angle is not None:
            v.camera.angles = (float(angle),)
        _process_events()
        return {
            "status": "ok",
            "center": list(map(float, v.camera.center)),
            "zoom": float(v.camera.zoom),
        }


async def set_ndisplay(ndisplay: int) -> Dict[str, Any]:
    """Set number of displayed dimensions (2 or 3)."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.dims.ndisplay = int(ndisplay)
        _process_events()
        return {"status": "ok", "ndisplay": int(v.dims.ndisplay)}


async def set_dims_current_step(axis: int, value: int) -> Dict[str, Any]:
    """Set the current step (slider position) for a specific axis."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.dims.set_current_step(int(axis), int(value))
        _process_events()
        return {"status": "ok", "axis": int(axis), "value": int(value)}


async def set_grid(enabled: bool = True) -> Dict[str, Any]:
    """Enable or disable grid view."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.grid.enabled = bool(enabled)
        _process_events()
        return {"status": "ok", "grid": bool(v.grid.enabled)}


async def screenshot(canvas_only: bool = True) -> Dict[str, str]:
    """
    Take a screenshot of the napari canvas and return a image as base64.

    Returns a base64-encoded PNG image.
    """
    async with _viewer_lock:
        v = _ensure_viewer()
        _process_events(3)
        arr = v.screenshot(canvas_only=canvas_only)
        if not isinstance(arr, np.ndarray):
            arr = np.asarray(arr)

        # Ensure uint8 image for PNG
        if arr.dtype != np.uint8:
            arr = arr.astype(np.uint8, copy=False)

        return _encode_png_base64(arr)


async def execute_code(code: str) -> Dict[str, Any]:
    """
    Execute arbitrary Python code in the server's interpreter, similar to napari's console.

    - code: Python code string. The value of the last expression (if any) is returned as 'result_repr'.
    Returns a dict with: 'status', optional 'result_repr', 'stdout', and 'stderr'.
    The execution namespace persists across calls and includes 'viewer', 'napari', and 'np'.
    """
    async with _viewer_lock:
        # Ensure Qt and viewer exist; expose common names in a persistent namespace
        v = _ensure_viewer()
        _exec_globals.setdefault("__builtins__", __builtins__)  # type: ignore[assignment]
        _exec_globals["viewer"] = v
        _exec_globals.setdefault("napari", napari)
        _exec_globals.setdefault("np", np)

        stdout_buf = StringIO()
        stderr_buf = StringIO()
        result_repr: Optional[str] = None
        try:
            # Capture stdout/stderr during execution
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                # Try to evaluate last expression if present
                parsed = ast.parse(code, mode="exec")
                if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                    # Execute all but last, then eval last expression to capture a result
                    if len(parsed.body) > 1:
                        exec_ast = ast.Module(body=parsed.body[:-1], type_ignores=[])
                        exec(compile(exec_ast, "<mcp-exec>", "exec"), _exec_globals, _exec_globals)
                    last_expr = ast.Expression(body=parsed.body[-1].value)
                    value = eval(compile(last_expr, "<mcp-eval>", "eval"), _exec_globals, _exec_globals)
                    result_repr = repr(value)
                else:
                    # Pure statements
                    exec(compile(parsed, "<mcp-exec>", "exec"), _exec_globals, _exec_globals)
            _process_events(2)
            return {
                "status": "ok",
                **({"result_repr": result_repr} if result_repr is not None else {}),
                "stdout": stdout_buf.getvalue(),
                "stderr": stderr_buf.getvalue(),
            }
        except Exception:
            _process_events(1)
            tb = traceback.format_exc()
            return {
                "status": "error",
                "stdout": stdout_buf.getvalue(),
                "stderr": stderr_buf.getvalue() + tb,
            }


async def install_packages(
    packages: List[str],
    upgrade: Optional[bool] = False,
    no_deps: Optional[bool] = False,
    index_url: Optional[str] = None,
    extra_index_url: Optional[str] = None,
    pre: Optional[bool] = False,
) -> Dict[str, Any]:
    """
    Install Python packages into the currently running server environment using pip.

    - packages: List of package specifiers (e.g., "scikit-image", "torch==2.3.1").
    - upgrade: If True, pass --upgrade.
    - no_deps: If True, pass --no-deps.
    - index_url: Optional custom index URL.
    - extra_index_url: Optional extra index URL.
    - pre: Allow pre-releases (--pre).

    Returns a dict including status, returncode, stdout, stderr, and the executed command.
    """
    if not packages or not isinstance(packages, list):
        return {"status": "error", "message": "Parameter 'packages' must be a non-empty list of package names"}

    cmd: List[str] = [sys.executable, "-m", "pip", "install", "--no-input", "--disable-pip-version-check"]
    if upgrade:
        cmd.append("--upgrade")
    if no_deps:
        cmd.append("--no-deps")
    if pre:
        cmd.append("--pre")
    if index_url:
        cmd.extend(["--index-url", index_url])
    if extra_index_url:
        cmd.extend(["--extra-index-url", extra_index_url])
    cmd.extend(packages)

    # Run pip as a subprocess without blocking the event loop
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    stdout = stdout_b.decode(errors="replace")
    stderr = stderr_b.decode(errors="replace")

    status = "ok" if proc.returncode == 0 else "error"
    return {
        "status": status,
        "returncode": int(proc.returncode),
        "command": " ".join(shlex.quote(part) for part in cmd),
        "stdout": stdout,
        "stderr": stderr,
    }


def main() -> None:
    server.run()

# Register tools with the FastMCP server without replacing the callables
server.tool()(init_viewer)
server.tool()(close_viewer)
server.tool()(session_information)
server.tool()(list_layers)
server.tool()(add_image)
server.tool()(add_labels)
server.tool()(add_points)
server.tool()(remove_layer)
server.tool()(rename_layer)
server.tool()(set_layer_properties)
server.tool()(reorder_layer)
server.tool()(set_active_layer)
server.tool()(reset_view)
server.tool()(set_zoom)
server.tool()(set_camera)
server.tool()(set_ndisplay)
server.tool()(set_dims_current_step)
server.tool()(set_grid)
server.tool()(screenshot)
server.tool()(execute_code)
server.tool()(install_packages)
server.tool()(start_gui)
server.tool()(stop_gui)
server.tool()(is_gui_running)

if __name__ == "__main__":
    main()



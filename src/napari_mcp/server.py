"""
Napari MCP Server.

Exposes a set of MCP tools to control a running napari Viewer: layer control,
viewer control (zoom, camera, dims), and a screenshot tool returning a PNG image
as base64.
"""

from __future__ import annotations

import ast
import asyncio
import asyncio.subprocess
import base64
import contextlib
import os
import shlex
import sys
import traceback
from io import BytesIO, StringIO
from typing import Any


# Optional imports: make module importable without heavy GUI deps.
# Do not cache napari at import time; tests may swap in a fake later.
def _napari_module() -> Any | None:
    """Return the current napari module if available.

    Looks up sys.modules first (to honor tests swapping in fakes), and falls
    back to importlib if not already loaded. Returns None if unavailable.
    """
    mod = sys.modules.get("napari")
    if mod is not None:
        return mod
    try:  # late import
        import importlib

        return importlib.import_module("napari")
    except Exception:
        return None


import numpy as np

try:  # FastMCP may not be installed in some environments
    from fastmcp import Client, FastMCP  # type: ignore
except Exception:  # pragma: no cover - provide light fallbacks

    class _DummyServer:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def tool(self):  # decorator factory
            def _decorator(fn):
                return fn

            return _decorator

        async def get_tools(self) -> dict[str, Any]:
            return {}

        def run(self, *_: Any, **__: Any) -> None:
            raise RuntimeError("FastMCP not available")

    class _DummyClient:  # used only under patching in tests
        pass

    FastMCP = _DummyServer  # type: ignore[assignment]
    Client = _DummyClient  # type: ignore[assignment]

from PIL import Image

try:  # qtpy may not be installed in headless environments
    from qtpy import QtWidgets  # type: ignore
except Exception:  # pragma: no cover
    QtWidgets = None  # type: ignore[assignment]

server = FastMCP(
    "Napari MCP Server",
    dependencies=["napari", "Pillow", "imageio", "numpy", "qtpy", "PyQt6"],
)


# Global GUI singletons (created lazily)
_qt_app: Any | None = None
_viewer: Any | None = None
_viewer_lock: asyncio.Lock = asyncio.Lock()
_exec_globals: dict[str, Any] = {}
_qt_pump_task: asyncio.Task | None = None
_window_close_connected: bool = False
# Note: _external_client is kept for test compatibility but not used
# - we create fresh clients for each call
_external_client: Any = None
_external_port: int = int(os.environ.get("NAPARI_MCP_BRIDGE_PORT", "9999"))


def _parse_bool(value: bool | str | None, default: bool = False) -> bool:
    """Parse a boolean value from various input types.

    Parameters
    ----------
    value : bool | str | None
        Value to parse. Strings like "true", "1", "yes", "on" are considered True.
    default : bool
        Default value if input is None.

    Returns
    -------
    bool
        Parsed boolean value.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)


async def _proxy_to_external(
    tool_name: str, params: dict[str, Any] | None = None, port: int | None = None
) -> dict[str, Any] | None:
    """Proxy a tool call to the external viewer if available.

    Parameters
    ----------
    tool_name : str
        Name of the tool to call
    params : dict, optional
        Parameters for the tool call
    port : int, optional
        Port to use for connection. If None, uses global _external_port

    Returns
    -------
    dict or None
        Tool result if external viewer available and call succeeds, None otherwise.
    """
    try:
        # Try to detect and use external viewer
        client, info = await _detect_external_viewer(port or _external_port)
        if not client or not info:
            return None
        
        # Use the detected client
        async with client:
            result = await client.call_tool(tool_name, params or {})
            # Parse the result from the external viewer
            if hasattr(result, "content"):
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    import json

                    response = (
                        content[0].text
                        if hasattr(content[0], "text")
                        else str(content[0])
                    )
                    try:
                        return (
                            json.loads(response)
                            if isinstance(response, str)
                            else response
                        )
                    except json.JSONDecodeError:
                        return {
                            "status": "error",
                            "message": f"Invalid JSON response: {response}",
                        }
            return {
                "status": "error",
                "message": "Invalid response format from external viewer",
            }
    except Exception:
        # Fall back to local execution
        return None


def _ensure_qt_app() -> Any:
    """Return a Qt application instance if available, else a no-op stub.

    This allows running in environments without Qt (e.g., some CI or tests
    that mock napari) while keeping real GUI behavior when Qt is present.
    """
    global _qt_app
    if QtWidgets is None:  # Fallback: provide a minimal stub

        class _StubApp:
            def processEvents(self, *_: Any) -> None:  # noqa: N802 (Qt-style)
                pass

            def setQuitOnLastWindowClosed(self, *_: Any) -> None:  # noqa: N802
                pass

        if _qt_app is None:
            _qt_app = _StubApp()
        return _qt_app

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
    return app


async def _detect_external_viewer(port: int | None = None) -> tuple[Client | None, dict[str, Any] | None]:
    """Detect if an external napari viewer is available via MCP bridge.

    Parameters
    ----------
    port : int, optional
        Port to check. If None, uses global _external_port.

    Returns
    -------
    tuple
        (client, session_info) if external viewer found, (None, None) otherwise
    """
    check_port = port or _external_port
    try:
        client = Client(f"http://localhost:{check_port}/mcp")
        async with client:
            # Try to get session info to verify it's a napari bridge
            result = await client.call_tool("session_information")
            if result and hasattr(result, "content"):
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    info = (
                        content[0].text
                        if hasattr(content[0], "text")
                        else str(content[0])
                    )
                    # Parse the JSON response
                    import json

                    info_dict = json.loads(info) if isinstance(info, str) else info
                    if info_dict.get("session_type") == "napari_bridge_session":
                        return client, info_dict
            return None, None
    except Exception:
        return None, None


def _detect_external_viewer_sync(port: int | None = None) -> bool:
    """Synchronous wrapper to check if external viewer is available.

    Parameters
    ----------
    port : int, optional
        Port to check. If None, uses global _external_port.

    In tests, ``_detect_external_viewer`` may be patched to return a plain
    tuple rather than a coroutine. Handle both cases gracefully.
    """
    try:
        import asyncio
        import inspect

        maybe_coro = _detect_external_viewer(port)
        if inspect.isawaitable(maybe_coro):
            loop = asyncio.new_event_loop()
            try:
                client, info = loop.run_until_complete(maybe_coro)  # type: ignore[assignment]
            finally:
                loop.close()
        else:
            # Already a concrete (client, info) tuple from a patch/mocked fn
            client, info = maybe_coro  # type: ignore[misc]
        return client is not None
    except Exception:
        return False


def _ensure_viewer() -> Any:
    global _viewer
    _ensure_qt_app()
    if _viewer is None:
        napari_mod = _napari_module()
        if napari_mod is None:
            raise RuntimeError("napari is not available")
        _viewer = napari_mod.Viewer()
        _connect_window_destroyed_signal(_viewer)
    return _viewer


def _connect_window_destroyed_signal(viewer) -> None:
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


def _encode_png_base64(img: np.ndarray) -> dict[str, str]:
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


async def detect_viewers() -> dict[str, Any]:
    """
    Detect available viewers (local and external).

    Returns
    -------
    dict
        Dictionary with information about available viewers
    """
    viewers: dict[str, Any] = {"local": None, "external": None}

    # Check for external viewer
    client, info = await _detect_external_viewer()
    if client and info is not None:
        viewers["external"] = {
            "available": True,
            "type": "napari_bridge",
            "port": info.get("bridge_port", _external_port),
            "viewer_info": info.get("viewer", {}),
        }
        await client.close()
    else:
        viewers["external"] = {"available": False}

    # Check for local viewer
    global _viewer
    if _viewer is not None:
        viewers["local"] = {
            "available": True,
            "type": "singleton",
            "title": _viewer.title,
            "n_layers": len(_viewer.layers),
        }
    else:
        viewers["local"] = {
            "available": True,  # Can be created
            "type": "not_initialized",
        }

    return {
        "status": "ok",
        "viewers": viewers,
        "auto_detect": True,
        "preference": "external_if_available",
    }




async def init_viewer(
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    port: int | None = None,
) -> dict[str, Any]:
    """
    Create or return the napari viewer (local or external).

    Auto-detects if an external napari-mcp server is running and uses it if available.
    Otherwise, creates a local viewer.

    Parameters
    ----------
    title : str, optional
        Optional window title (only for local viewer).
    width : int, optional
        Optional initial canvas width (only for local viewer).
    height : int, optional
        Optional initial canvas height (only for local viewer).
    port : int, optional
        Port to check for external server. If None, uses NAPARI_MCP_BRIDGE_PORT
        environment variable (default: 9999).

    Returns
    -------
    dict
        Dictionary containing status, viewer type, and layer info.
    """
    async with _viewer_lock:
        # First try to detect external viewer
        check_port = port or _external_port
        client, info = await _detect_external_viewer(check_port)
        
        if client and info:
            try:
                # External viewer is available
                await client.close()  # Close detection client
                return {
                    "status": "ok",
                    "viewer_type": "external",
                    "title": info.get("viewer", {}).get(
                        "title", "External Viewer"
                    ),
                    "layers": info.get("viewer", {}).get(
                        "layer_names", []
                    ),
                    "port": info.get("bridge_port", check_port),
                }
            except Exception:
                # If anything fails with external, fall back to local
                pass

        # Use local viewer
        v = _ensure_viewer()
        if title:
            v.title = title
        if width or height:
            w = (
                int(width)
                if width is not None
                else v.window.qt_viewer.canvas.size().width()
            )
            h = (
                int(height)
                if height is not None
                else v.window.qt_viewer.canvas.size().height()
            )
            v.window.qt_viewer.canvas.native.resize(w, h)
        # Always ensure GUI pump is running for local viewer (backwards-incompatible change)
        global _qt_pump_task
        app = _ensure_qt_app()
        with contextlib.suppress(Exception):
            app.setQuitOnLastWindowClosed(False)
        _connect_window_destroyed_signal(v)

        # Best-effort to show window without forcing focus (safer for tests/headless)
        try:
            qt_win = v.window._qt_window  # type: ignore[attr-defined]
            qt_win.show()
        except Exception:
            pass

        if _qt_pump_task is None or _qt_pump_task.done():
            loop = asyncio.get_running_loop()
            _qt_pump_task = loop.create_task(_qt_event_pump())

        _process_events()
        return {
            "status": "ok",
            "viewer_type": "local",
            "title": v.title,
            "layers": [lyr.name for lyr in v.layers],
        }


# Removed explicit GUI control APIs (start_gui/stop_gui/is_gui_running)
# GUI pump now starts automatically when initializing a local viewer.


async def close_viewer() -> dict[str, Any]:
    """
    Close the viewer window and clear all layers.

    Returns
    -------
    dict
        Dictionary with status: 'closed' if viewer existed, 'no_viewer' if none.
    """
    async with _viewer_lock:
        global _viewer, _qt_pump_task
        if _viewer is not None:
            _viewer.close()
            _viewer = None
            # Stop GUI pump when closing viewer
            if _qt_pump_task is not None and not _qt_pump_task.done():
                _qt_pump_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await _qt_pump_task
            _qt_pump_task = None
            _process_events()
            return {"status": "closed"}
        return {"status": "no_viewer"}


async def session_information() -> dict[str, Any]:
    """
    Get comprehensive information about the current napari session.

    Returns
    -------
    dict
        Comprehensive session information including viewer state, system info,
        and environment details.
    """
    import os
    import platform

    async with _viewer_lock:
        global _viewer, _qt_pump_task, _exec_globals

        # Check if viewer exists
        viewer_exists = _viewer is not None
        if not viewer_exists:
            return {
                "status": "ok",
                "session_type": "napari_mcp_standalone_session",
                "timestamp": str(np.datetime64("now")),
                "viewer": None,
                "message": "No viewer currently initialized. Call init_viewer() first.",
            }

        v = _viewer
        assert v is not None  # We already checked this above

        # Viewer information
        viewer_info = {
            "title": v.title,
            "viewer_id": id(v),
            "n_layers": len(v.layers),
            "layer_names": [layer.name for layer in v.layers],
            "selected_layers": [layer.name for layer in v.layers.selection],
            "current_step": dict(enumerate(v.dims.current_step))
            if hasattr(v.dims, "current_step")
            else {},
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
            "napari_version": getattr(_napari_module(), "__version__", "unknown"),
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
                "data_shape": list(layer.data.shape)
                if hasattr(layer, "data") and hasattr(layer.data, "shape")
                else None,
                "data_dtype": str(layer.data.dtype)
                if hasattr(layer, "data") and hasattr(layer.data, "dtype")
                else None,
                "layer_id": id(layer),
            }

            # Add layer-specific properties
            if hasattr(layer, "colormap"):
                layer_detail["colormap"] = getattr(
                    layer.colormap, "name", str(layer.colormap)
                )
            if hasattr(layer, "contrast_limits"):
                try:
                    cl = layer.contrast_limits
                    layer_detail["contrast_limits"] = [float(cl[0]), float(cl[1])]
                except Exception:
                    pass
            if hasattr(layer, "gamma"):
                layer_detail["gamma"] = float(getattr(layer, "gamma", 1.0))

            layer_details.append(layer_detail)

        return {
            "status": "ok",
            "session_type": "napari_mcp_standalone_session",
            "timestamp": str(np.datetime64("now")),
            "viewer": viewer_info,
            "system": system_info,
            "session": session_info,
            "layers": layer_details,
        }


async def list_layers() -> list[dict[str, Any]]:
    """Return a list of layers with key properties."""
    # Try to proxy to external viewer first
    proxy_result = await _proxy_to_external("list_layers")
    if proxy_result is not None:
        # Ensure the result is the expected list format
        if isinstance(proxy_result, list):
            return proxy_result
        elif isinstance(proxy_result, dict) and "content" in proxy_result:
            content = proxy_result["content"]
            if isinstance(content, list):
                return content
        return []

    # Local execution
    async with _viewer_lock:
        v = _ensure_viewer()
        result: list[dict[str, Any]] = []
        for lyr in v.layers:
            entry = {
                "name": lyr.name,
                "type": lyr.__class__.__name__,
                "visible": bool(getattr(lyr, "visible", True)),
                "opacity": float(getattr(lyr, "opacity", 1.0)),
                "blending": getattr(lyr, "blending", None),
            }
            if hasattr(lyr, "colormap") and getattr(lyr, "colormap", None) is not None:
                entry["colormap"] = getattr(lyr.colormap, "name", None) or str(
                    lyr.colormap
                )
            if (
                hasattr(lyr, "contrast_limits")
                and getattr(lyr, "contrast_limits", None) is not None
            ):
                try:
                    cl = list(lyr.contrast_limits)
                    entry["contrast_limits"] = [float(cl[0]), float(cl[1])]
                except Exception:
                    pass
            result.append(entry)
        return result


async def add_image(
    path: str,
    name: str | None = None,
    colormap: str | None = None,
    blending: str | None = None,
    channel_axis: int | None = None,
) -> dict[str, Any]:
    """
    Add an image layer from a file path.

    Parameters
    ----------
    path : str
        Path to an image readable by imageio (e.g., PNG, TIFF, OME-TIFF).
    name : str, optional
        Layer name. If None, uses filename.
    colormap : str, optional
        Napari colormap name (e.g., 'gray', 'magma').
    blending : str, optional
        Blending mode (e.g., 'translucent').
    channel_axis : int, optional
        If provided, interpret that axis as channels.

    Returns
    -------
    dict
        Dictionary containing status, layer name, and image shape.
    """
    # Try to proxy to external viewer first
    params: dict[str, Any] = {"path": path}
    if name:
        params["name"] = name
    if colormap:
        params["colormap"] = colormap
    if blending:
        params["blending"] = blending
    if channel_axis is not None:
        params["channel_axis"] = channel_axis

    result = await _proxy_to_external("add_image", params)
    if result is not None:
        return result

    # Local execution
    import imageio.v3 as iio

    async with _viewer_lock:
        v = _ensure_viewer()
        data = iio.imread(path)
        layer = v.add_image(
            data,
            name=name,
            colormap=colormap,
            blending=blending,
            channel_axis=channel_axis,
        )
        _process_events()
        return {"status": "ok", "name": layer.name, "shape": list(np.shape(data))}


async def add_labels(path: str, name: str | None = None) -> dict[str, Any]:
    """Add a labels layer from a file path (e.g., PNG/TIFF with integer labels)."""
    import imageio.v3 as iio

    async with _viewer_lock:
        v = _ensure_viewer()
        data = iio.imread(path)
        layer = v.add_labels(data, name=name)
        _process_events()
        return {"status": "ok", "name": layer.name, "shape": list(np.shape(data))}


async def add_points(
    points: list[list[float]], name: str | None = None, size: float = 10.0
) -> dict[str, Any]:
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


async def remove_layer(name: str) -> dict[str, Any]:
    """Remove a layer by name."""
    async with _viewer_lock:
        v = _ensure_viewer()
        if name in v.layers:
            v.layers.remove(name)
            _process_events()
            return {"status": "removed", "name": name}
        return {"status": "not_found", "name": name}


# Removed: rename_layer (use set_layer_properties with new_name instead)


async def set_layer_properties(
    name: str,
    visible: bool | None = None,
    opacity: float | None = None,
    colormap: str | None = None,
    blending: str | None = None,
    contrast_limits: list[float] | None = None,
    gamma: float | None = None,
    new_name: str | None = None,
) -> dict[str, Any]:
    """Set common properties on a layer by name."""
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
            with contextlib.suppress(Exception):
                lyr.contrast_limits = [
                    float(contrast_limits[0]),
                    float(contrast_limits[1]),
                ]
        if gamma is not None and hasattr(lyr, "gamma"):
            lyr.gamma = float(gamma)
        if new_name is not None:
            lyr.name = new_name
        _process_events()
        return {"status": "ok", "name": lyr.name}


async def reorder_layer(
    name: str,
    index: int | None = None,
    before: str | None = None,
    after: str | None = None,
) -> dict[str, Any]:
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
            return {
                "status": "error",
                "message": "Provide exactly one of index, before, or after",
            }
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


async def set_active_layer(name: str) -> dict[str, Any]:
    """Set the selected/active layer by name."""
    async with _viewer_lock:
        v = _ensure_viewer()
        if name not in v.layers:
            return {"status": "not_found", "name": name}
        v.layers.selection = {v.layers[name]}
        _process_events()
        return {"status": "ok", "active": name}


async def reset_view() -> dict[str, Any]:
    """Reset the camera view to fit data."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.reset_view()
        _process_events()
        return {"status": "ok"}


# Removed: set_zoom (use set_camera with zoom instead)


async def set_camera(
    center: list[float] | None = None,
    zoom: float | None = None,
    angle: float | None = None,
) -> dict[str, Any]:
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


async def set_ndisplay(ndisplay: int) -> dict[str, Any]:
    """Set number of displayed dimensions (2 or 3)."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.dims.ndisplay = int(ndisplay)
        _process_events()
        return {"status": "ok", "ndisplay": int(v.dims.ndisplay)}


async def set_dims_current_step(axis: int, value: int) -> dict[str, Any]:
    """Set the current step (slider position) for a specific axis."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.dims.set_current_step(int(axis), int(value))
        _process_events()
        return {"status": "ok", "axis": int(axis), "value": int(value)}


async def set_grid(enabled: bool = True) -> dict[str, Any]:
    """Enable or disable grid view."""
    async with _viewer_lock:
        v = _ensure_viewer()
        v.grid.enabled = bool(enabled)
        _process_events()
        return {"status": "ok", "grid": bool(v.grid.enabled)}


async def screenshot(canvas_only: bool = True) -> dict[str, str]:
    """
    Take a screenshot of the napari canvas and return as base64.

    Parameters
    ----------
    canvas_only : bool, default=True
        If True, only capture the canvas area.

    Returns
    -------
    dict
        Dictionary with 'mime_type' and 'base64_data' keys containing
        the base64-encoded PNG image.
    """
    # Try to proxy to external viewer first
    result = await _proxy_to_external("screenshot", {"canvas_only": canvas_only})
    if result is not None:
        return result

    # Local execution
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


async def execute_code(code: str) -> dict[str, Any]:
    """
    Execute arbitrary Python code in the server's interpreter.

    Similar to napari's console. The execution namespace persists across calls
    and includes 'viewer', 'napari', and 'np'.

    Parameters
    ----------
    code : str
        Python code string. The value of the last expression (if any)
        is returned as 'result_repr'.

    Returns
    -------
    dict
        Dictionary with 'status', optional 'result_repr', 'stdout', and 'stderr'.
    """
    # Try to proxy to external viewer first
    result = await _proxy_to_external("execute_code", {"code": code})
    if result is not None:
        return result

    # Local execution
    async with _viewer_lock:
        v = _ensure_viewer()
        _exec_globals.setdefault("__builtins__", __builtins__)  # type: ignore[assignment]
        _exec_globals["viewer"] = v
        napari_mod = _napari_module()
        if napari_mod is not None:
            _exec_globals.setdefault("napari", napari_mod)
        _exec_globals.setdefault("np", np)

        stdout_buf = StringIO()
        stderr_buf = StringIO()
        result_repr: str | None = None
        try:
            # Capture stdout/stderr during execution
            with (
                contextlib.redirect_stdout(stdout_buf),
                contextlib.redirect_stderr(stderr_buf),
            ):
                # Try to evaluate last expression if present
                parsed = ast.parse(code, mode="exec")
                if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                    # Execute all but last, then eval last expression to
                    # capture a result
                    if len(parsed.body) > 1:
                        exec_ast = ast.Module(body=parsed.body[:-1], type_ignores=[])
                        exec(
                            compile(exec_ast, "<mcp-exec>", "exec"),
                            _exec_globals,
                            _exec_globals,
                        )
                    last_expr = ast.Expression(body=parsed.body[-1].value)
                    value = eval(
                        compile(last_expr, "<mcp-eval>", "eval"),
                        _exec_globals,
                        _exec_globals,
                    )
                    result_repr = repr(value)
                else:
                    # Pure statements
                    exec(
                        compile(parsed, "<mcp-exec>", "exec"),
                        _exec_globals,
                        _exec_globals,
                    )
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
    packages: list[str],
    upgrade: bool | None = False,
    no_deps: bool | None = False,
    index_url: str | None = None,
    extra_index_url: str | None = None,
    pre: bool | None = False,
) -> dict[str, Any]:
    """
    Install Python packages using pip.

    Install packages into the currently running server environment.

    Parameters
    ----------
    packages : list of str
        List of package specifiers (e.g., "scikit-image", "torch==2.3.1").
    upgrade : bool, optional
        If True, pass --upgrade flag.
    no_deps : bool, optional
        If True, pass --no-deps flag.
    index_url : str, optional
        Custom index URL.
    extra_index_url : str, optional
        Extra index URL.
    pre : bool, optional
        Allow pre-releases (--pre flag).

    Returns
    -------
    dict
        Dictionary including status, returncode, stdout, stderr, and the executed
        command.
    """
    if not packages or not isinstance(packages, list):
        return {
            "status": "error",
            "message": "Parameter 'packages' must be a non-empty list of package names",
        }

    cmd: list[str] = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--no-input",
        "--disable-pip-version-check",
    ]
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
        "returncode": proc.returncode if proc.returncode is not None else -1,
        "command": " ".join(shlex.quote(part) for part in cmd),
        "stdout": stdout,
        "stderr": stderr,
    }


def main() -> None:
    """Run the MCP server."""
    server.run()


# Register tools with the FastMCP server without replacing the callables
server.tool()(detect_viewers)
server.tool()(init_viewer)
server.tool()(close_viewer)
server.tool()(session_information)
server.tool()(list_layers)
server.tool()(add_image)
server.tool()(add_labels)
server.tool()(add_points)
server.tool()(remove_layer)
server.tool()(set_layer_properties)
server.tool()(reorder_layer)
server.tool()(set_active_layer)
server.tool()(reset_view)
server.tool()(set_camera)
server.tool()(set_ndisplay)
server.tool()(set_dims_current_step)
server.tool()(set_grid)
server.tool()(screenshot)
server.tool()(execute_code)
server.tool()(install_packages)

if __name__ == "__main__":
    main()

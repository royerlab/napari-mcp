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
import contextlib
import datetime
import os
import shlex
import sys
import traceback
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Any

import fastmcp

if TYPE_CHECKING:
    from mcp.types import ImageContent


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
_use_external: bool = os.environ.get("NAPARI_MCP_USE_EXTERNAL", "false").lower() in (
    "true",
    "1",
    "yes",
    "on",
)
_external_port: int = int(os.environ.get("NAPARI_MCP_BRIDGE_PORT", "9999"))

# Output storage for tool results
_output_storage: dict[str, dict[str, Any]] = {}
_output_storage_lock: asyncio.Lock = asyncio.Lock()
_next_output_id: int = 1
# Maximum number of output items to retain; set NAPARI_MCP_MAX_OUTPUT_ITEMS<=0 for unlimited
try:
    _MAX_OUTPUT_ITEMS: int = int(os.environ.get("NAPARI_MCP_MAX_OUTPUT_ITEMS", "1000"))
except Exception:
    _MAX_OUTPUT_ITEMS = 1000


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


def _truncate_output(output: str, line_limit: int) -> tuple[str, bool]:
    """Truncate output to specified line limit.

    Parameters
    ----------
    output : str
        The output text to truncate.
    line_limit : int
        Maximum number of lines to return. If -1, return all lines.

    Returns
    -------
    tuple[str, bool]
        Tuple of (truncated_output, was_truncated).
    """
    # Normalize/validate line_limit
    try:
        line_limit = int(line_limit)
    except Exception:
        line_limit = 30
    if line_limit < -1:
        line_limit = -1
    if line_limit == -1:
        return output, False

    lines = output.splitlines(keepends=True)
    if len(lines) <= line_limit:
        return output, False

    truncated = "".join(lines[:line_limit])
    return truncated, True


async def _store_output(
    tool_name: str,
    stdout: str = "",
    stderr: str = "",
    result_repr: str | None = None,
    **metadata: Any,
) -> str:
    """Store tool output and return a unique ID.

    Parameters
    ----------
    tool_name : str
        Name of the tool that generated the output.
    stdout : str
        Standard output content.
    stderr : str
        Standard error content.
    result_repr : str, optional
        String representation of the result.
    **metadata : Any
        Additional metadata to store with the output.

    Returns
    -------
    str
        Unique output ID for later retrieval.
    """
    global _next_output_id

    async with _output_storage_lock:
        output_id = str(_next_output_id)
        _next_output_id += 1

        _output_storage[output_id] = {
            "tool_name": tool_name,
            # ISO8601 UTC timestamp for interoperability
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "stdout": stdout,
            "stderr": stderr,
            "result_repr": result_repr,
            **metadata,
        }
        # Evict oldest items if exceeding capacity
        if _MAX_OUTPUT_ITEMS > 0 and len(_output_storage) > _MAX_OUTPUT_ITEMS:
            overflow = len(_output_storage) - _MAX_OUTPUT_ITEMS
            # IDs are numeric strings; evict smallest IDs first
            for victim in sorted(_output_storage.keys(), key=lambda k: int(k))[
                :overflow
            ]:
                _output_storage.pop(victim, None)

        return output_id


async def _proxy_to_external(
    tool_name: str, params: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Proxy a tool call to the external viewer if available.

    Returns None if external viewer is not being used or call fails.
    """
    global _use_external
    if not _use_external:
        return None

    try:
        # Create fresh client for each call to avoid connection issues
        client = Client(f"http://localhost:{_external_port}/mcp")
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


async def _detect_external_viewer() -> tuple[Client | None, dict[str, Any] | None]:
    """Detect if an external napari viewer is available via MCP bridge.

    Returns
    -------
    tuple
        (client, session_info) if external viewer found, (None, None) otherwise
    """
    try:
        client = Client(f"http://localhost:{_external_port}/mcp")
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


def _detect_external_viewer_sync() -> bool:
    """Synchronous wrapper to check if external viewer is available.

    In tests, ``_detect_external_viewer`` may be patched to return a plain
    tuple rather than a coroutine. Handle both cases gracefully.
    """
    try:
        import asyncio
        import inspect

        maybe_coro = _detect_external_viewer()
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
        "using_external": _use_external,
        "preference": "external" if _use_external else "local",
    }


async def select_viewer(use_external: bool | str | None = None) -> dict[str, Any]:
    """
    Select which viewer to use (local or external).

    Parameters
    ----------
    use_external : bool | str, optional
        If True/"true"/"1"/"yes", prefer external viewer. If None, auto-detect.

    Returns
    -------
    dict
        Status and selected viewer information
    """
    global _use_external

    # Parse boolean value if provided
    if use_external is not None:
        use_external = _parse_bool(use_external)
    else:
        # Auto-detect: use external if available
        client, info = await _detect_external_viewer()
        use_external = client is not None
        if client:
            await client.close()

    _use_external = use_external

    if _use_external:
        client, info = await _detect_external_viewer()
        if client:
            await client.close()  # Close test connection
            return {"status": "ok", "selected": "external", "info": info}
        else:
            return {
                "status": "error",
                "message": "External viewer requested but not found",
                "fallback": "local",
            }
    else:
        return {"status": "ok", "selected": "local"}


async def init_viewer(
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    use_external: bool | str | None = None,
) -> dict[str, Any]:
    """
    Create or return the napari viewer (local or external).

    Parameters
    ----------
    title : str, optional
        Optional window title (only for local viewer).
    width : int, optional
        Optional initial canvas width (only for local viewer).
    height : int, optional
        Optional initial canvas height (only for local viewer).
    use_external : bool | str, optional
        If True/"true"/"1"/"yes", try to use external viewer.
        If None, use current setting.

    Returns
    -------
    dict
        Dictionary containing status, viewer type, and layer info.
    """
    global _use_external
    # No global client - create fresh connections as needed

    # Parse boolean value and handle viewer selection if specified
    if use_external is not None:
        use_external = _parse_bool(use_external)
        await select_viewer(use_external)

    async with _viewer_lock:
        # Check if we should use external viewer
        if _use_external:
            try:
                # Test connection to external viewer
                test_client = Client(f"http://localhost:{_external_port}/mcp")
                async with test_client:
                    result = await test_client.call_tool("session_information")
                    if hasattr(result, "content"):
                        content = result.content
                        if isinstance(content, list) and len(content) > 0:
                            import json

                            info = (
                                content[0].text
                                if hasattr(content[0], "text")
                                else str(content[0])
                            )
                            info_dict = (
                                json.loads(info) if isinstance(info, str) else info
                            )
                            if info_dict.get("session_type") == "napari_bridge_session":
                                # External viewer is available
                                return {
                                    "status": "ok",
                                    "viewer_type": "external",
                                    "title": info_dict.get("viewer", {}).get(
                                        "title", "External Viewer"
                                    ),
                                    "layers": info_dict.get("viewer", {}).get(
                                        "layer_names", []
                                    ),
                                    "port": info_dict.get(
                                        "bridge_port", _external_port
                                    ),
                                }
            except Exception as e:
                print(f"Failed to connect to external viewer: {e}")
                _use_external = False

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


async def screenshot(canvas_only: bool = True) -> ImageContent:
    """
    Take a screenshot of the napari canvas and return as base64.

    Parameters
    ----------
    canvas_only : bool, default=True
        If True, only capture the canvas area.

    Returns
    -------
    ImageContent
        The screenshot image as an mcp.types.ImageContent object.
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

        img = Image.fromarray(arr)
        buf = BytesIO()
        img.save(buf, format="PNG")
        enc = buf.getvalue()
        return fastmcp.utilities.types.Image(data=enc, format="png").to_image_content()


async def execute_code(code: str, line_limit: int = 30) -> dict[str, Any]:
    """
    Execute arbitrary Python code in the server's interpreter.

    Similar to napari's console. The execution namespace persists across calls
    and includes 'viewer', 'napari', and 'np'.

    Parameters
    ----------
    code : str
        Python code string. The value of the last expression (if any)
        is returned as 'result_repr'.
    line_limit : int, default=30
        Maximum number of output lines to return. Use -1 for unlimited output.
        Warning: Using -1 may consume a large number of tokens.

    Returns
    -------
    dict
        Dictionary with 'status', optional 'result_repr', 'stdout', 'stderr',
        and 'output_id' for retrieving full output if truncated.
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

            # Get full output
            stdout_full = stdout_buf.getvalue()
            stderr_full = stderr_buf.getvalue()

            # Store full output and get ID
            output_id = await _store_output(
                tool_name="execute_code",
                stdout=stdout_full,
                stderr=stderr_full,
                result_repr=result_repr,
                code=code,
            )

            # Prepare response with line limiting
            response = {
                "status": "ok",
                "output_id": output_id,
                **({"result_repr": result_repr} if result_repr is not None else {}),
            }

            # Add warning for unlimited output
            if line_limit == -1:
                response["warning"] = (
                    "Unlimited output requested. This may consume a large number "
                    "of tokens. Consider using read_output for large outputs."
                )
                response["stdout"] = stdout_full
                response["stderr"] = stderr_full
            else:
                # Truncate stdout and stderr
                stdout_truncated, stdout_was_truncated = _truncate_output(
                    stdout_full, line_limit
                )
                stderr_truncated, stderr_was_truncated = _truncate_output(
                    stderr_full, line_limit
                )

                response["stdout"] = stdout_truncated
                response["stderr"] = stderr_truncated

                if stdout_was_truncated or stderr_was_truncated:
                    response["truncated"] = True  # type: ignore
                    response["message"] = (
                        f"Output truncated to {line_limit} lines. "
                        f"Use read_output('{output_id}') to retrieve full output."
                    )

            return response
        except Exception as e:
            _process_events(1)
            tb = traceback.format_exc()

            # Get full output including traceback
            stdout_full = stdout_buf.getvalue()
            stderr_full = stderr_buf.getvalue() + tb

            # Store full output and get ID
            output_id = await _store_output(
                tool_name="execute_code",
                stdout=stdout_full,
                stderr=stderr_full,
                code=code,
                error=True,
            )

            # Prepare error response with line limiting
            response = {
                "status": "error",
                "output_id": output_id,
            }

            # Add warning for unlimited output
            if line_limit == -1:
                response["warning"] = (
                    "Unlimited output requested. This may consume a large number "
                    "of tokens. Consider using read_output for large outputs."
                )
                response["stdout"] = stdout_full
                response["stderr"] = stderr_full
            else:
                # Truncate stdout and stderr
                stdout_truncated, stdout_was_truncated = _truncate_output(
                    stdout_full, line_limit
                )
                stderr_truncated, stderr_was_truncated = _truncate_output(
                    stderr_full, line_limit
                )

                response["stdout"] = stdout_truncated
                # Ensure exception summary is present even when truncated
                error_summary = f"{type(e).__name__}: {e}"
                if error_summary not in stderr_truncated:
                    # Append a concise summary line so callers can see the error type
                    if stderr_truncated and not stderr_truncated.endswith("\n"):
                        stderr_truncated += "\n"
                    stderr_truncated += error_summary + "\n"
                response["stderr"] = stderr_truncated

                if stdout_was_truncated or stderr_was_truncated:
                    response["truncated"] = True  # type: ignore
                    response["message"] = (
                        f"Output truncated to {line_limit} lines. "
                        f"Use read_output('{output_id}') to retrieve full output."
                    )

            return response


async def install_packages(
    packages: list[str],
    upgrade: bool | None = False,
    no_deps: bool | None = False,
    index_url: str | None = None,
    extra_index_url: str | None = None,
    pre: bool | None = False,
    line_limit: int = 30,
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
    line_limit : int, default=30
        Maximum number of output lines to return. Use -1 for unlimited output.
        Warning: Using -1 may consume a large number of tokens.

    Returns
    -------
    dict
        Dictionary including status, returncode, stdout, stderr, command,
        and output_id for retrieving full output if truncated.
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
    command_str = " ".join(shlex.quote(part) for part in cmd)

    # Store full output and get ID
    output_id = await _store_output(
        tool_name="install_packages",
        stdout=stdout,
        stderr=stderr,
        packages=packages,
        command=command_str,
        returncode=proc.returncode,
    )

    # Prepare response with line limiting
    response = {
        "status": status,
        "returncode": proc.returncode if proc.returncode is not None else -1,
        "command": command_str,
        "output_id": output_id,
    }

    # Add warning for unlimited output
    if line_limit == -1:
        response["warning"] = (
            "Unlimited output requested. This may consume a large number "
            "of tokens. Consider using read_output for large outputs."
        )
        response["stdout"] = stdout
        response["stderr"] = stderr
    else:
        # Truncate stdout and stderr
        stdout_truncated, stdout_was_truncated = _truncate_output(stdout, line_limit)
        stderr_truncated, stderr_was_truncated = _truncate_output(stderr, line_limit)

        response["stdout"] = stdout_truncated
        response["stderr"] = stderr_truncated

        if stdout_was_truncated or stderr_was_truncated:
            response["truncated"] = True
            response["message"] = (
                f"Output truncated to {line_limit} lines. "
                f"Use read_output('{output_id}') to retrieve full output."
            )

    return response


async def read_output(output_id: str, start: int = 0, end: int = -1) -> dict[str, Any]:
    """
    Read stored tool output with optional line range.

    Parameters
    ----------
    output_id : str
        Unique ID of the stored output.
    start : int, default=0
        Starting line number (0-indexed).
    end : int, default=-1
        Ending line number (exclusive). If -1, read to end.

    Returns
    -------
    dict
        Dictionary containing the requested output lines and metadata.
    """
    async with _output_storage_lock:
        if output_id not in _output_storage:
            return {"status": "error", "message": f"Output ID '{output_id}' not found"}

        stored_output = _output_storage[output_id]

        # Combine stdout and stderr for line-based access
        full_output = ""
        if stored_output.get("stdout"):
            full_output = stored_output["stdout"]
        if stored_output.get("stderr"):
            stderr_text = stored_output["stderr"]
            if (
                full_output
                and not full_output.endswith("\n")
                and not stderr_text.startswith("\n")
            ):
                full_output += "\n"
            full_output += stderr_text

        # Normalize and clamp range inputs
        try:
            start = int(start)
        except Exception:
            start = 0
        try:
            end = int(end)
        except Exception:
            end = -1

        start = max(0, start)

        lines = full_output.splitlines(keepends=True)
        total_lines = len(lines)

        # Handle line range
        end = total_lines if end == -1 else min(total_lines, end)

        selected_lines = [] if start >= total_lines else lines[start:end]

        return {
            "status": "ok",
            "output_id": output_id,
            "tool_name": stored_output["tool_name"],
            "timestamp": stored_output["timestamp"],
            "lines": selected_lines,
            "line_range": {"start": start, "end": min(end, total_lines)},
            "total_lines": total_lines,
            "result_repr": stored_output.get("result_repr"),
        }


def main() -> None:
    """Run the MCP server."""
    server.run()


# Register tools with the FastMCP server without replacing the callables
server.tool()(detect_viewers)
server.tool()(select_viewer)
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
server.tool()(read_output)

if __name__ == "__main__":
    main()

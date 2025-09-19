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
import logging
import math
import os
import shlex
import sys
import traceback
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.types import ImageContent
else:
    ImageContent = Any


import fastmcp
import napari
import numpy as np
from fastmcp import Client, FastMCP
from qtpy import QtWidgets
from PIL import Image
 

server = FastMCP(
    "Napari MCP Server",
    # -- deprecated --
    # dependencies=["napari", "Pillow", "imageio", "numpy", "qtpy", "PyQt6"],
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

# Module logger
logger = logging.getLogger(__name__)

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
    """Proxy a tool call to an external viewer if available.

    Attempts to contact a running napari-mcp bridge server on the configured
    port. Returns None if no external server is reachable, so the caller can
    fall back to the local viewer implementation.
    """
    try:
        client = Client(f"http://localhost:{_external_port}/mcp")
        async with client:
            result = await client.call_tool(tool_name, params or {})
            #return result
            if hasattr(result, "content"):
                content = result.content
                if content[0].type == "text":
                    import json
                    response = (
                        content[0].text
                        if hasattr(content[0], "text")
                        else str(content[0])
                    )
                    try:
                        return json.loads(response)
                    except json.JSONDecodeError:
                        return {
                            "status": "error",
                            "message": f"Invalid JSON response: {response}",
                        }
                else:
                    return content
            return {
                "status": "error",
                "message": "Invalid response format from external viewer",
            }
    except Exception:
        raise
        #return None


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
        _viewer = napari.Viewer()
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

# Optional GUI executor for running viewer operations on the main thread
_GUI_EXECUTOR: Any | None = None

def set_gui_executor(executor: Any | None) -> None:
    """Configure an executor that runs a callable on the GUI/main thread.

    If None, operations execute directly in the current thread.
    """
    global _GUI_EXECUTOR
    _GUI_EXECUTOR = executor

def _gui_execute(operation):
    if _GUI_EXECUTOR is not None:
        return _GUI_EXECUTOR(operation)
    return operation()

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


class NapariMCPTools:
    """
    Implementation of Napari MCP tools (exactly matching server.py behavior).
    """

    @staticmethod
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
        }

    @staticmethod
    async def init_viewer(
        title: str | None = None,
        width: int | str | None = None,
        height: int | str | None = None,
        port: int | str | None = None,
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
        port : int, optional
            If provided, attempt to connect to an external napari-mcp bridge on
            this port (default is taken from NAPARI_MCP_BRIDGE_PORT or 9999).

        Returns
        -------
        dict
            Dictionary containing status, viewer type, and layer info.
        """
        # Allow overriding the external port per-call
        global _external_port
        if port is not None:
            try:
                _external_port = int(port)
            except Exception:
                logger.error("Invalid port: {port}")
                _external_port = _external_port

        async with _viewer_lock:
            # Try external viewer first; fall back to local
            try:
                return await NapariMCPTools._external_session_information(_external_port)
            except Exception:
                # No external viewer; continue to local viewer
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

    @staticmethod
    async def _external_session_information(_external_port: int) -> dict[str, Any]:
        """
        Get session information from the external viewer.
        """
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
                        return {
                            "status": "ok",
                            "viewer_type": "external",
                            "title": info_dict.get("viewer", {}).get(
                                "title", "External Viewer"
                            ),
                            "layers": info_dict.get("viewer", {}).get(
                                "layer_names", []
                            ),
                            "port": info_dict.get("bridge_port", _external_port),
                        }

    @staticmethod
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

    @staticmethod
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

            try:
                return await NapariMCPTools._external_session_information(_external_port)
            except Exception:
                # No external viewer; continue to local viewer
                pass

            # Use local viewer

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
                "napari_version": getattr(napari, "__version__", "unknown"),
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
                    "visible": _parse_bool(getattr(layer, "visible", True)),
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

    @staticmethod
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
            def _build():
                v = _ensure_viewer()
                result: list[dict[str, Any]] = []
                for lyr in v.layers:
                    entry = {
                        "name": lyr.name,
                        "type": lyr.__class__.__name__,
                        "visible": _parse_bool(getattr(lyr, "visible", True)),
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

            return _gui_execute(_build)

    @staticmethod
    async def add_image(
        path: str,
        name: str | None = None,
        colormap: str | None = None,
        blending: str | None = None,
        channel_axis: int | str |None = None,
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
            params["channel_axis"] = int(channel_axis)

        result = await _proxy_to_external("add_image", params)
        if result is not None:
            return result

        # Local execution
        import imageio.v3 as iio

        async with _viewer_lock:
            data = iio.imread(path)

            def _add():
                v = _ensure_viewer()
                layer = v.add_image(
                    data,
                    name=name,
                    colormap=colormap,
                    blending=blending,
                    channel_axis=int(channel_axis),
                )
                _process_events()
                return {"status": "ok", "name": layer.name, "shape": list(np.shape(data))}

            return _gui_execute(_add)

    @staticmethod
    async def add_labels(path: str, name: str | None = None) -> dict[str, Any]:
        """Add a labels layer from a file path (e.g., PNG/TIFF with integer labels)."""
        import imageio.v3 as iio

        async with _viewer_lock:
            try:
                from pathlib import Path

                def _add():
                    v = _ensure_viewer()
                    p = Path(path).expanduser().resolve(strict=False)
                    data = iio.imread(str(p))
                    layer = v.add_labels(data, name=name)
                    _process_events()
                    return {
                        "status": "ok",
                        "name": layer.name,
                        "shape": list(np.shape(data)),
                    }

                return _gui_execute(_add)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to add labels from '{path}': {e}",
                }

    @staticmethod
    async def add_points(
        points: list[list[float]], name: str | None = None, size: float | str = 10.0
    ) -> dict[str, Any]:
        """
        Add a points layer.

        - points: List of [y, x] or [z, y, x] coordinates
        - name: Optional layer name
        - size: Point size in pixels
        """
        async with _viewer_lock:
            def _add():
                v = _ensure_viewer()
                arr = np.asarray(points, dtype=float)
                layer = v.add_points(arr, name=name, size=float(size))
                _process_events()
                return {"status": "ok", "name": layer.name, "n_points": int(arr.shape[0])}

            return _gui_execute(_add)

    @staticmethod
    async def remove_layer(name: str) -> dict[str, Any]:
        """Remove a layer by name."""
        async with _viewer_lock:
            def _remove():
                v = _ensure_viewer()
                if name in v.layers:
                    v.layers.remove(name)
                    _process_events()
                    return {"status": "removed", "name": name}
                return {"status": "not_found", "name": name}

            return _gui_execute(_remove)

    # Removed: rename_layer (use set_layer_properties with new_name instead)

    @staticmethod
    async def set_layer_properties(
        name: str,
        visible: bool | None = None,
        opacity: float | None = None,
        colormap: str | None = None,
        blending: str | None = None,
        contrast_limits: list[float] | None = None,
        gamma: float | str | None = None,
        new_name: str | None = None,
    ) -> dict[str, Any]:
        """Set common properties on a layer by name."""
        async with _viewer_lock:
            def _set():
                v = _ensure_viewer()
                if name not in v.layers:
                    return {"status": "not_found", "name": name}
                lyr = v.layers[name]
                if visible is not None and hasattr(lyr, "visible"):
                    lyr.visible = _parse_bool(visible)
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

            return _gui_execute(_set)

    @staticmethod
    async def reorder_layer(
        name: str,
        index: int | str | None = None,
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
            def _reorder():
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

            return _gui_execute(_reorder)

    @staticmethod
    async def set_active_layer(name: str) -> dict[str, Any]:
        """Set the selected/active layer by name."""
        async with _viewer_lock:
            def _set_active():
                v = _ensure_viewer()
                if name not in v.layers:
                    return {"status": "not_found", "name": name}
                v.layers.selection = {v.layers[name]}
                _process_events()
                return {"status": "ok", "active": name}

            return _gui_execute(_set_active)

    @staticmethod
    async def reset_view() -> dict[str, Any]:
        """Reset the camera view to fit data."""
        async with _viewer_lock:
            def _reset():
                v = _ensure_viewer()
                v.reset_view()
                _process_events()
                return {"status": "ok"}

            return _gui_execute(_reset)

    # Removed: set_zoom (use set_camera with zoom instead)

    @staticmethod
    async def set_camera(
        center: list[float] | None = None,
        zoom: float | str | None = None,
        angle: float | str | None = None,
    ) -> dict[str, Any]:
        """Set camera properties: center, zoom, and/or angle."""
        async with _viewer_lock:
            def _set_cam():
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

            return _gui_execute(_set_cam)

    @staticmethod
    async def set_ndisplay(ndisplay: int | str) -> dict[str, Any]:
        """Set number of displayed dimensions (2 or 3)."""
        async with _viewer_lock:
            def _set():
                v = _ensure_viewer()
                v.dims.ndisplay = int(ndisplay)
                _process_events()
                return {"status": "ok", "ndisplay": int(v.dims.ndisplay)}

            return _gui_execute(_set)

    @staticmethod
    async def set_dims_current_step(axis: int | str, value: int | str) -> dict[str, Any]:
        """Set the current step (slider position) for a specific axis."""
        async with _viewer_lock:
            def _set():
                v = _ensure_viewer()
                v.dims.set_current_step(int(axis), int(value))
                _process_events()
                return {"status": "ok", "axis": int(axis), "value": int(value)}

            return _gui_execute(_set)

    @staticmethod
    async def set_grid(enabled: bool | str = True) -> dict[str, Any]:
        """Enable or disable grid view."""
        async with _viewer_lock:
            def _set():
                v = _ensure_viewer()
                v.grid.enabled = _parse_bool(enabled)
                _process_events()
                return {"status": "ok", "grid": _parse_bool(v.grid.enabled)}

            return _gui_execute(_set)

    @staticmethod
    async def screenshot(canvas_only: bool | str = True) -> ImageContent:
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
            def _shot():
                v = _ensure_viewer()
                _process_events(3)
                arr = v.screenshot(canvas_only=canvas_only)
                if not isinstance(arr, np.ndarray):
                    arr = np.asarray(arr)
                if arr.dtype != np.uint8:
                    arr = arr.astype(np.uint8, copy=False)
                img = Image.fromarray(arr)
                buf = BytesIO()
                img.save(buf, format="PNG")
                enc = buf.getvalue()
                return fastmcp.utilities.types.Image(data=enc, format="png").to_image_content()

            return _gui_execute(_shot)

    @staticmethod
    async def timelapse_screenshot(
        axis: int | str,
        slice_range: str,
        canvas_only: bool | str = True,
        interpolate_to_fit: bool = True,
    ) -> list[ImageContent]:
        """
        Capture a series of screenshots while sweeping a dims axis.

        Parameters
        ----------
        axis : int
            Dims axis index to sweep (e.g., temporal axis).
        slice_range : str
            Python-like slice string over step indices, e.g. "1:5", ":6", "::2".
            Defaults follow Python semantics with start=0, stop=nsteps, step=1.
        canvas_only : bool, default=True
            If True, only capture the canvas area.
        interpolate_to_fit : bool, default=False
            If True, interpolate the images to fit the total size cap of 1309246 bytes.

        Returns
        -------
        list[ImageContent]
            List of screenshots as mcp.types.ImageContent objects.
        """
        max_total_base64_bytes = 1309246 if interpolate_to_fit else None

        # Try to proxy to external viewer first
        result = await _proxy_to_external(
            "timelapse_screenshot",
            {
                "axis": axis,
                "slice_range": slice_range,
                "canvas_only": canvas_only,
                "interpolate_to_fit": interpolate_to_fit,
            },
        )
        if result is not None:
            return result  # type: ignore[return-value]

        def _parse_slice(spec: str, length: int) -> list[int]:
            # Normalize
            s = (spec or "").strip()
            # Single integer
            if s and ":" not in s:
                try:
                    idx = int(s)
                except Exception as err:
                    raise ValueError(f"Invalid slice range: {spec!r}") from err
                if idx < 0:
                    idx += length
                if not (0 <= idx < length):
                    raise ValueError(
                        f"Index out of bounds for axis with {length} steps: {idx}"
                    )
                return [idx]

            # Slice form start:stop:step
            parts = s.split(":")
            if len(parts) > 3:
                raise ValueError(f"Invalid slice range: {spec!r}")
            start_s, stop_s, step_s = (parts + [""] * 3)[:3]

            def _to_int_or_none(val: str) -> int | None:
                v = val.strip()
                if v == "":
                    return None
                return int(v)

            start = _to_int_or_none(start_s)
            stop = _to_int_or_none(stop_s)
            step = _to_int_or_none(step_s) or 1
            if step == 0:
                raise ValueError("slice step cannot be 0")

            # Handle negatives like Python
            if start is None:
                start = 0 if step > 0 else length - 1
            if stop is None:
                stop = length if step > 0 else -1
            if start < 0:
                start += length
            if stop < 0:
                stop += length

            # Clamp to valid iteration range similar to range() behavior
            rng = range(start, stop, step)
            indices = [i for i in rng if 0 <= i < length]
            return indices

        # Local execution
        async with _viewer_lock:
            v = _ensure_viewer()

            # Determine number of steps along axis
            try:
                nsteps_tuple = getattr(v.dims, "nsteps", None)
                if nsteps_tuple is None:
                    # Fallback: infer from current_step length and a conservative stop
                    # We cannot reliably infer total steps without dims.nsteps; require it
                    raise AttributeError
                total = int(nsteps_tuple[int(axis)])
            except Exception:
                # Best effort via bounds from layers; may be approximate
                try:
                    total = max(
                        int(getattr(lyr.data, "shape", [1])[(int(axis))])
                        if int(axis) < getattr(lyr.data, "ndim", 0)
                        else 1
                        for lyr in v.layers
                    )
                except Exception:
                    total = 0

            if total <= 0:
                raise RuntimeError("Unable to determine number of steps for the given axis")

            indices = _parse_slice(slice_range, total)
            if not indices:
                return []

            # Take a sample at the first index to estimate size
            v.dims.set_current_step(int(axis), int(indices[0]))
            _process_events(2)
            sample_arr = v.screenshot(canvas_only=canvas_only)
            if not isinstance(sample_arr, np.ndarray):
                sample_arr = np.asarray(sample_arr)
            if sample_arr.dtype != np.uint8:
                sample_arr = sample_arr.astype(np.uint8, copy=False)
            sample_img = Image.fromarray(sample_arr)
            sbuf = BytesIO()
            sample_img.save(sbuf, format="PNG")
            sample_png = sbuf.getvalue()
            sample_b64_len = ((len(sample_png) + 2) // 3) * 4

            # Ask user whether to downsample if estimated total exceeds cap
            downsample_factor = 1.0
            if (
                max_total_base64_bytes is not None
                and sample_b64_len * len(indices) > max_total_base64_bytes
            ):
                est_factor = math.sqrt(
                    max_total_base64_bytes / float(max(1, sample_b64_len * len(indices)))
                )
                downsample_factor = max(0.05, min(1.0, est_factor))

            images: list[ImageContent] = []
            total_b64_len = 0
            for idx in indices:
                # Move slider
                v.dims.set_current_step(int(axis), int(idx))
                _process_events(2)

                # Capture
                arr = v.screenshot(canvas_only=canvas_only)
                if not isinstance(arr, np.ndarray):
                    arr = np.asarray(arr)
                if arr.dtype != np.uint8:
                    arr = arr.astype(np.uint8, copy=False)

                img = Image.fromarray(arr)
                if downsample_factor < 1.0:
                    new_w = max(1, int(img.width * downsample_factor))
                    new_h = max(1, int(img.height * downsample_factor))
                    if new_w != img.width or new_h != img.height:
                        img = img.resize((new_w, new_h), resample=Image.BILINEAR)
                buf = BytesIO()
                img.save(buf, format="PNG")
                enc = buf.getvalue()
                b64_len = ((len(enc) + 2) // 3) * 4
                if (
                    max_total_base64_bytes is not None
                    and total_b64_len + b64_len > max_total_base64_bytes
                ):
                    break
                total_b64_len += b64_len
                images.append(
                    fastmcp.utilities.types.Image(data=enc, format="png").to_image_content()
                )

            return images

    @staticmethod
    async def execute_code(code: str, line_limit: int | str = 30) -> dict[str, Any]:
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
            napari_mod = napari
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

    @staticmethod
    async def install_packages(
        packages: list[str],
        upgrade: bool | None = False,
        no_deps: bool | None = False,
        index_url: str | None = None,
        extra_index_url: str | None = None,
        pre: bool | None = False,
        line_limit: int | str = 30,
        timeout: int = 240,
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
        timeout : int, default=240
            Timeout for pip install in seconds.

        Returns
        -------
        dict
            Dictionary including status, returncode, stdout, stderr, command,
            and output_id for retrieving full output if truncated.
        """
        # Try to proxy to external viewer first
        result = await _proxy_to_external("install_packages", {"packages": packages, "upgrade": upgrade, "no_deps": no_deps, "index_url": index_url, "extra_index_url": extra_index_url, "pre": pre, "line_limit": line_limit, "timeout": timeout})
        if result is not None:
            return result
        
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
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            stdout_b, stderr_b = b"", f"pip install timed out after {timeout}s".encode()
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

    @staticmethod
    async def read_output(output_id: str, start: int | str = 0, end: int | str = -1) -> dict[str, Any]:
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

async def detect_viewers() -> dict[str, Any]:
    """
    Detect available viewers (local and external).

    Returns
    -------
    dict
        Dictionary with information about available viewers
    """
    return await NapariMCPTools.detect_viewers()


# Removed explicit selection API; the server now auto-detects an external
# napari-mcp bridge if available and otherwise uses a local viewer.

async def _external_session_information(_external_port: int) -> dict[str, Any]:
    """
    Get session information from the external viewer.
    """
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
                    return {
                        "status": "ok",
                        "viewer_type": "external",
                        "title": info_dict.get("viewer", {}).get(
                            "title", "External Viewer"
                        ),
                        "layers": info_dict.get("viewer", {}).get(
                            "layer_names", []
                        ),
                        "port": info_dict.get("bridge_port", _external_port),
                    }

async def init_viewer(
    title: str | None = None,
    width: int | str | None = None,
    height: int | str | None = None,
    port: int | str | None = None,
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
    port : int, optional
        If provided, attempt to connect to an external napari-mcp bridge on
        this port (default is taken from NAPARI_MCP_BRIDGE_PORT or 9999).

    Returns
    -------
    dict
        Dictionary containing status, viewer type, and layer info.
    """
    return await NapariMCPTools.init_viewer(title=title, width=width, height=height, port=port)


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
    return await NapariMCPTools.close_viewer()


async def session_information() -> dict[str, Any]:
    """
    Get comprehensive information about the current napari session.

    Returns
    -------
    dict
        Comprehensive session information including viewer state, system info,
        and environment details.
    """
    return await NapariMCPTools.session_information()


async def list_layers() -> list[dict[str, Any]]:
    """Return a list of layers with key properties."""
    return await NapariMCPTools.list_layers()


async def add_image(
    path: str,
    name: str | None = None,
    colormap: str | None = None,
    blending: str | None = None,
    channel_axis: int | str |None = None,
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
    return await NapariMCPTools.add_image(path=path, name=name, colormap=colormap, blending=blending, channel_axis=channel_axis)


async def add_labels(path: str, name: str | None = None) -> dict[str, Any]:
    """Add a labels layer from a file path (e.g., PNG/TIFF with integer labels)."""
    return await NapariMCPTools.add_labels(path=path, name=name)


async def add_points(
    points: list[list[float]], name: str | None = None, size: float | str = 10.0
) -> dict[str, Any]:
    """
    Add a points layer.

    - points: List of [y, x] or [z, y, x] coordinates
    - name: Optional layer name
    - size: Point size in pixels
    """
    return await NapariMCPTools.add_points(points=points, name=name, size=size)


async def remove_layer(name: str) -> dict[str, Any]:
    """Remove a layer by name."""
    return await NapariMCPTools.remove_layer(name)


# Removed: rename_layer (use set_layer_properties with new_name instead)


async def set_layer_properties(
    name: str,
    visible: bool | None = None,
    opacity: float | None = None,
    colormap: str | None = None,
    blending: str | None = None,
    contrast_limits: list[float] | None = None,
    gamma: float | str | None = None,
    new_name: str | None = None,
) -> dict[str, Any]:
    """Set common properties on a layer by name."""
    return await NapariMCPTools.set_layer_properties(name=name, visible=visible, opacity=opacity, colormap=colormap, blending=blending, contrast_limits=contrast_limits, gamma=gamma, new_name=new_name)


async def reorder_layer(
    name: str,
    index: int | str | None = None,
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
    return await NapariMCPTools.reorder_layer(name=name, index=index, before=before, after=after)


async def set_active_layer(name: str) -> dict[str, Any]:
    """Set the selected/active layer by name."""
    return await NapariMCPTools.set_active_layer(name)


async def reset_view() -> dict[str, Any]:
    """Reset the camera view to fit data."""
    return await NapariMCPTools.reset_view()


# Removed: set_zoom (use set_camera with zoom instead)


async def set_camera(
    center: list[float] | None = None,
    zoom: float | str | None = None,
    angle: float | str | None = None,
) -> dict[str, Any]:
    """Set camera properties: center, zoom, and/or angle."""
    return await NapariMCPTools.set_camera(center=center, zoom=zoom, angle=angle)


async def set_ndisplay(ndisplay: int | str) -> dict[str, Any]:
    """Set number of displayed dimensions (2 or 3)."""
    return await NapariMCPTools.set_ndisplay(ndisplay)


async def set_dims_current_step(axis: int | str, value: int | str) -> dict[str, Any]:
    """Set the current step (slider position) for a specific axis."""
    return await NapariMCPTools.set_dims_current_step(axis, value)


async def set_grid(enabled: bool | str = True) -> dict[str, Any]:
    """Enable or disable grid view."""
    return await NapariMCPTools.set_grid(enabled)


async def screenshot(canvas_only: bool | str = True) -> ImageContent:
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
    return await NapariMCPTools.screenshot(canvas_only)


async def timelapse_screenshot(
    axis: int | str,
    slice_range: str,
    canvas_only: bool | str = True,
    interpolate_to_fit: bool = True,
) -> list[ImageContent]:
    """
    Capture a series of screenshots while sweeping a dims axis.

    Parameters
    ----------
    axis : int
        Dims axis index to sweep (e.g., temporal axis).
    slice_range : str
        Python-like slice string over step indices, e.g. "1:5", ":6", "::2".
        Defaults follow Python semantics with start=0, stop=nsteps, step=1.
    canvas_only : bool, default=True
        If True, only capture the canvas area.
    interpolate_to_fit : bool, default=False
        If True, interpolate the images to fit the total size cap of 1309246 bytes.

    Returns
    -------
    list[ImageContent]
        List of screenshots as mcp.types.ImageContent objects.
    """
    return await NapariMCPTools.timelapse_screenshot(axis=axis, slice_range=slice_range, canvas_only=canvas_only, interpolate_to_fit=interpolate_to_fit)


async def execute_code(code: str, line_limit: int | str = 30) -> dict[str, Any]:
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
    return await NapariMCPTools.execute_code(code=code, line_limit=line_limit)


async def install_packages(
    packages: list[str],
    upgrade: bool | None = False,
    no_deps: bool | None = False,
    index_url: str | None = None,
    extra_index_url: str | None = None,
    pre: bool | None = False,
    line_limit: int | str = 30,
    timeout: int = 240,
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
    timeout : int, default=240
        Timeout for pip install in seconds.

    Returns
    -------
    dict
        Dictionary including status, returncode, stdout, stderr, command,
        and output_id for retrieving full output if truncated.
    """
    return await NapariMCPTools.install_packages(packages=packages, upgrade=upgrade, no_deps=no_deps, index_url=index_url, extra_index_url=extra_index_url, pre=pre, line_limit=line_limit, timeout=timeout)


async def read_output(output_id: str, start: int | str = 0, end: int | str = -1) -> dict[str, Any]:
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
    return await NapariMCPTools.read_output(output_id=output_id, start=start, end=end)


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
server.tool()(timelapse_screenshot)
server.tool()(execute_code)
server.tool()(install_packages)
server.tool()(read_output)

if __name__ == "__main__":
    main()

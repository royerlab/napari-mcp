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
import numpy as np
import typer
from fastmcp import FastMCP

from napari_mcp.output import truncate_output
from napari_mcp.qt_helpers import (
    connect_window_destroyed_signal,
    ensure_qt_app,
    ensure_viewer,
    process_events,
    qt_event_pump,
)
from napari_mcp.state import ServerState, StartupMode

# Module logger
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure utility (no state)
# ---------------------------------------------------------------------------


def _parse_bool(value: bool | str | None, default: bool = False) -> bool:
    """Parse a boolean value from various input types."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)


# Keep old name available for external imports
_truncate_output = truncate_output


# ---------------------------------------------------------------------------
# Module-level state singleton (for backward compat + test access)
# ---------------------------------------------------------------------------

_state: ServerState | None = None


def get_state() -> ServerState:
    """Return the current module-level ServerState singleton."""
    if _state is None:
        raise RuntimeError("Server state not initialised. Call create_server() first.")
    return _state


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def create_server(state: ServerState | None = None) -> FastMCP:
    """Create a FastMCP server with all tools bound to *state*.

    Parameters
    ----------
    state : ServerState, optional
        The server state instance. If None, creates a default STANDALONE state.

    Returns
    -------
    FastMCP
        Fully configured MCP server with all napari tools registered.
    """
    global _state

    if state is None:
        state = ServerState()
    _state = state

    server = FastMCP("Napari MCP Server")

    # Dict to collect raw async functions before @server.tool() wraps them.
    # Used at the end to expose backward-compatible module-level names.
    _raw_tools: dict[str, Any] = {}

    def _register(fn: Any) -> Any:
        """Register fn in _raw_tools, then pass to @server.tool()."""
        _raw_tools[fn.__name__] = fn
        return server.tool()(fn)

    # ------------------------------------------------------------------
    # Tool definitions (closures over *state*)
    # ------------------------------------------------------------------

    @_register
    async def detect_viewers() -> dict[str, Any]:
        """Detect available viewers (local and external)."""
        viewers: dict[str, Any] = {"local": None, "external": None}

        client, info = await state.detect_external_viewer()
        if client and info is not None:
            viewers["external"] = {
                "available": True,
                "type": "napari_bridge",
                "port": info.get("bridge_port", state.bridge_port),
                "viewer_info": info.get("viewer", {}),
            }
        else:
            viewers["external"] = {"available": False}

        if state.viewer is not None:
            viewers["local"] = {
                "available": True,
                "type": "singleton",
                "title": state.viewer.title,
                "n_layers": len(state.viewer.layers),
            }
        else:
            viewers["local"] = {
                "available": True,
                "type": "not_initialized",
            }

        return {"status": "ok", "viewers": viewers}

    @_register
    async def init_viewer(
        title: str | None = None,
        width: int | str | None = None,
        height: int | str | None = None,
        port: int | str | None = None,
    ) -> dict[str, Any]:
        """Create or return the napari viewer (local or external).

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
        """
        if port is not None:
            try:
                state.bridge_port = int(port)
            except Exception:
                logger.error("Invalid port: %s", port)

        async with state.viewer_lock:
            if state.mode == StartupMode.AUTO_DETECT:
                try:
                    return await state.external_session_information()
                except Exception:
                    pass

            v = ensure_viewer(state)
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

            app = ensure_qt_app(state)
            with contextlib.suppress(Exception):
                app.setQuitOnLastWindowClosed(False)
            connect_window_destroyed_signal(state, v)

            try:
                qt_win = v.window._qt_window  # type: ignore[attr-defined]
                qt_win.show()
            except Exception:
                pass

            if state.qt_pump_task is None or state.qt_pump_task.done():
                loop = asyncio.get_running_loop()
                state.qt_pump_task = loop.create_task(qt_event_pump(state))

            process_events(state)
            return {
                "status": "ok",
                "viewer_type": "local",
                "title": v.title,
                "layers": [lyr.name for lyr in v.layers],
            }

    @_register
    async def close_viewer() -> dict[str, Any]:
        """Close the viewer window and clear all layers."""
        async with state.viewer_lock:
            if state.viewer is not None:
                state.viewer.close()
                state.viewer = None
                if state.qt_pump_task is not None and not state.qt_pump_task.done():
                    state.qt_pump_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await state.qt_pump_task
                state.qt_pump_task = None
                process_events(state)
                return {"status": "closed"}
            return {"status": "no_viewer"}

    @_register
    async def session_information() -> dict[str, Any]:
        """Get comprehensive information about the current napari session."""
        import platform

        import napari

        async with state.viewer_lock:
            if state.mode == StartupMode.AUTO_DETECT:
                try:
                    return await state.external_session_information()
                except Exception:
                    pass

            viewer_exists = state.viewer is not None
            if not viewer_exists:
                return {
                    "status": "ok",
                    "session_type": "napari_mcp_standalone_session",
                    "timestamp": str(np.datetime64("now")),
                    "viewer": None,
                    "message": "No viewer currently initialized. Call init_viewer() first.",
                }

            v = state.viewer
            assert v is not None

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

            system_info = {
                "python_version": sys.version,
                "platform": platform.platform(),
                "napari_version": getattr(napari, "__version__", "unknown"),
                "process_id": os.getpid(),
                "working_directory": os.getcwd(),
            }

            gui_running = (
                state.qt_pump_task is not None and not state.qt_pump_task.done()
            )
            session_info = {
                "server_type": "napari_mcp_standalone",
                "viewer_instance": f"<napari.Viewer at {hex(id(v))}>",
                "gui_pump_running": gui_running,
                "execution_namespace_vars": list(state.exec_globals.keys()),
                "qt_app_available": state.qt_app is not None,
            }

            layer_details = []
            for layer in v.layers:
                layer_detail: dict[str, Any] = {
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

    @_register
    async def list_layers() -> list[dict[str, Any]]:
        """Return a list of layers with key properties."""
        proxy_result = await state.proxy_to_external("list_layers")
        if proxy_result is not None:
            if isinstance(proxy_result, list):
                return proxy_result
            elif isinstance(proxy_result, dict) and "content" in proxy_result:
                content = proxy_result["content"]
                if isinstance(content, list):
                    return content
            return []

        async with state.viewer_lock:

            def _build():
                v = ensure_viewer(state)
                result: list[dict[str, Any]] = []
                for lyr in v.layers:
                    entry: dict[str, Any] = {
                        "name": lyr.name,
                        "type": lyr.__class__.__name__,
                        "visible": _parse_bool(getattr(lyr, "visible", True)),
                        "opacity": float(getattr(lyr, "opacity", 1.0)),
                        "blending": getattr(lyr, "blending", None),
                    }
                    if (
                        hasattr(lyr, "colormap")
                        and getattr(lyr, "colormap", None) is not None
                    ):
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

            return state.gui_execute(_build)

    @_register
    async def add_image(
        path: str,
        name: str | None = None,
        colormap: str | None = None,
        blending: str | None = None,
        channel_axis: int | str | None = None,
    ) -> dict[str, Any]:
        """Add an image layer from a file path.

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
        """
        params: dict[str, Any] = {"path": path}
        if name:
            params["name"] = name
        if colormap:
            params["colormap"] = colormap
        if blending:
            params["blending"] = blending
        if channel_axis is not None:
            params["channel_axis"] = int(channel_axis)

        result = await state.proxy_to_external("add_image", params)
        if result is not None:
            return result

        import imageio.v3 as iio

        async with state.viewer_lock:
            data = iio.imread(path)

            def _add():
                v = ensure_viewer(state)
                layer = v.add_image(
                    data,
                    name=name,
                    colormap=colormap,
                    blending=blending,
                    channel_axis=channel_axis,
                )
                process_events(state)
                return {
                    "status": "ok",
                    "name": layer.name,
                    "shape": list(np.shape(data)),
                }

            return state.gui_execute(_add)

    @_register
    async def add_labels(path: str, name: str | None = None) -> dict[str, Any]:
        """Add a labels layer from a file path (e.g., PNG/TIFF with integer labels)."""
        import imageio.v3 as iio

        async with state.viewer_lock:
            try:
                from pathlib import Path

                def _add():
                    v = ensure_viewer(state)
                    p = Path(path).expanduser().resolve(strict=False)
                    data = iio.imread(str(p))
                    layer = v.add_labels(data, name=name)
                    process_events(state)
                    return {
                        "status": "ok",
                        "name": layer.name,
                        "shape": list(np.shape(data)),
                    }

                return state.gui_execute(_add)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to add labels from '{path}': {e}",
                }

    @_register
    async def add_points(
        points: list[list[float]], name: str | None = None, size: float | str = 10.0
    ) -> dict[str, Any]:
        """Add a points layer.

        - points: List of [y, x] or [z, y, x] coordinates
        - name: Optional layer name
        - size: Point size in pixels
        """
        async with state.viewer_lock:

            def _add():
                v = ensure_viewer(state)
                arr = np.asarray(points, dtype=float)
                layer = v.add_points(arr, name=name, size=float(size))
                process_events(state)
                return {
                    "status": "ok",
                    "name": layer.name,
                    "n_points": int(arr.shape[0]),
                }

            return state.gui_execute(_add)

    @_register
    async def remove_layer(name: str) -> dict[str, Any]:
        """Remove a layer by name."""
        async with state.viewer_lock:

            def _remove():
                v = ensure_viewer(state)
                if name in v.layers:
                    v.layers.remove(name)
                    process_events(state)
                    return {"status": "removed", "name": name}
                return {"status": "not_found", "name": name}

            return state.gui_execute(_remove)

    @_register
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
        async with state.viewer_lock:

            def _set():
                v = ensure_viewer(state)
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
                process_events(state)
                return {"status": "ok", "name": lyr.name}

            return state.gui_execute(_set)

    @_register
    async def reorder_layer(
        name: str,
        index: int | str | None = None,
        before: str | None = None,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Reorder a layer by name.

        Provide exactly one of:
        - index: absolute target index
        - before: move before this layer name
        - after: move after this layer name
        """
        async with state.viewer_lock:

            def _reorder():
                v = ensure_viewer(state)
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
                process_events(state)
                return {"status": "ok", "name": name, "index": v.layers.index(name)}

            return state.gui_execute(_reorder)

    @_register
    async def set_active_layer(name: str) -> dict[str, Any]:
        """Set the selected/active layer by name."""
        async with state.viewer_lock:

            def _set_active():
                v = ensure_viewer(state)
                if name not in v.layers:
                    return {"status": "not_found", "name": name}
                v.layers.selection = {v.layers[name]}
                process_events(state)
                return {"status": "ok", "active": name}

            return state.gui_execute(_set_active)

    @_register
    async def reset_view() -> dict[str, Any]:
        """Reset the camera view to fit data."""
        async with state.viewer_lock:

            def _reset():
                v = ensure_viewer(state)
                v.reset_view()
                process_events(state)
                return {"status": "ok"}

            return state.gui_execute(_reset)

    @_register
    async def set_camera(
        center: list[float] | None = None,
        zoom: float | str | None = None,
        angles: list[float] | None = None,
    ) -> dict[str, Any]:
        """Set camera properties: center, zoom, and/or angles.

        Parameters
        ----------
        center : list[float], optional
            Camera center position.
        zoom : float, optional
            Camera zoom factor.
        angles : list[float], optional
            Camera angles as [azimuth, elevation, roll] in degrees.
        """
        async with state.viewer_lock:

            def _set_cam():
                v = ensure_viewer(state)
                if center is not None:
                    v.camera.center = list(map(float, center))
                if zoom is not None:
                    v.camera.zoom = float(zoom)
                if angles is not None:
                    v.camera.angles = tuple(float(a) for a in angles)
                process_events(state)
                return {
                    "status": "ok",
                    "center": list(map(float, v.camera.center)),
                    "zoom": float(v.camera.zoom),
                    "angles": list(map(float, v.camera.angles)),
                }

            return state.gui_execute(_set_cam)

    @_register
    async def set_ndisplay(ndisplay: int | str) -> dict[str, Any]:
        """Set number of displayed dimensions (2 or 3)."""
        async with state.viewer_lock:

            def _set():
                v = ensure_viewer(state)
                v.dims.ndisplay = int(ndisplay)
                process_events(state)
                return {"status": "ok", "ndisplay": int(v.dims.ndisplay)}

            return state.gui_execute(_set)

    @_register
    async def set_dims_current_step(
        axis: int | str, value: int | str
    ) -> dict[str, Any]:
        """Set the current step (slider position) for a specific axis."""
        async with state.viewer_lock:

            def _set():
                v = ensure_viewer(state)
                v.dims.set_current_step(int(axis), int(value))
                process_events(state)
                return {"status": "ok", "axis": int(axis), "value": int(value)}

            return state.gui_execute(_set)

    @_register
    async def set_grid(enabled: bool | str = True) -> dict[str, Any]:
        """Enable or disable grid view."""
        async with state.viewer_lock:

            def _set():
                v = ensure_viewer(state)
                v.grid.enabled = _parse_bool(enabled)
                process_events(state)
                return {"status": "ok", "grid": _parse_bool(v.grid.enabled)}

            return state.gui_execute(_set)

    @_register
    async def screenshot(canvas_only: bool | str = True) -> ImageContent:
        """Take a screenshot of the napari canvas and return as base64.

        Parameters
        ----------
        canvas_only : bool, default=True
            If True, only capture the canvas area.
        """
        from PIL import Image

        result = await state.proxy_to_external(
            "screenshot", {"canvas_only": canvas_only}
        )
        if result is not None:
            return result

        async with state.viewer_lock:

            def _shot():
                v = ensure_viewer(state)
                process_events(state, 3)
                arr = v.screenshot(canvas_only=canvas_only)
                if not isinstance(arr, np.ndarray):
                    arr = np.asarray(arr)
                if arr.dtype != np.uint8:
                    arr = arr.astype(np.uint8, copy=False)
                img = Image.fromarray(arr)
                buf = BytesIO()
                img.save(buf, format="PNG")
                enc = buf.getvalue()
                return fastmcp.utilities.types.Image(
                    data=enc, format="png"
                ).to_image_content()

            return state.gui_execute(_shot)

    @_register
    async def timelapse_screenshot(
        axis: int | str,
        slice_range: str,
        canvas_only: bool | str = True,
        interpolate_to_fit: bool = False,
    ) -> list[ImageContent]:
        """Capture a series of screenshots while sweeping a dims axis.

        Parameters
        ----------
        axis : int
            Dims axis index to sweep (e.g., temporal axis).
        slice_range : str
            Python-like slice string over step indices, e.g. "1:5", ":6", "::2".
        canvas_only : bool, default=True
            If True, only capture the canvas area.
        interpolate_to_fit : bool, default=False
            If True, interpolate the images to fit the total size cap of 1309246 bytes.
        """
        from PIL import Image

        max_total_base64_bytes = 1309246 if interpolate_to_fit else None

        result = await state.proxy_to_external(
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
            s = (spec or "").strip()
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
            step = _to_int_or_none(step_s)
            if step == 0:
                raise ValueError("slice step cannot be 0")
            if step is None:
                step = 1
            if start is None:
                start = 0 if step > 0 else length - 1
            if stop is None:
                stop = length if step > 0 else -1
            if start < 0:
                start += length
            if stop < 0:
                stop += length
            rng = range(start, stop, step)
            return [i for i in rng if 0 <= i < length]

        async with state.viewer_lock:

            def _run_series():
                v = ensure_viewer(state)
                try:
                    nsteps_tuple = getattr(v.dims, "nsteps", None)
                    if nsteps_tuple is None:
                        raise AttributeError
                    total = int(nsteps_tuple[int(axis)])
                except Exception:
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
                    raise RuntimeError(
                        "Unable to determine number of steps for the given axis"
                    )

                indices = _parse_slice(slice_range, total)
                if not indices:
                    return []

                v.dims.set_current_step(int(axis), int(indices[0]))
                process_events(state, 2)
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

                downsample_factor = 1.0
                if (
                    max_total_base64_bytes is not None
                    and sample_b64_len * len(indices) > max_total_base64_bytes
                ):
                    est_factor = math.sqrt(
                        max_total_base64_bytes
                        / float(max(1, sample_b64_len * len(indices)))
                    )
                    downsample_factor = max(0.05, min(1.0, est_factor))

                images: list[ImageContent] = []
                total_b64_len = 0
                for idx in indices:
                    v.dims.set_current_step(int(axis), int(idx))
                    process_events(state, 2)
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
                        fastmcp.utilities.types.Image(
                            data=enc, format="png"
                        ).to_image_content()
                    )
                return images

            return state.gui_execute(_run_series)

    @_register
    async def execute_code(code: str, line_limit: int | str = 30) -> dict[str, Any]:
        """Execute arbitrary Python code in the server's interpreter.

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
        """
        import napari

        result = await state.proxy_to_external("execute_code", {"code": code})
        if result is not None:
            return result

        async with state.viewer_lock:
            v = ensure_viewer(state)
            state.exec_globals.setdefault("__builtins__", __builtins__)  # type: ignore[assignment]
            state.exec_globals["viewer"] = v
            napari_mod = napari
            if napari_mod is not None:
                state.exec_globals.setdefault("napari", napari_mod)
            state.exec_globals.setdefault("np", np)

            stdout_buf = StringIO()
            stderr_buf = StringIO()
            result_repr: str | None = None
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
                                compile(exec_ast, "<mcp-exec>", "exec"),
                                state.exec_globals,
                                state.exec_globals,
                            )
                        last_expr = ast.Expression(body=parsed.body[-1].value)
                        value = eval(
                            compile(last_expr, "<mcp-eval>", "eval"),
                            state.exec_globals,
                            state.exec_globals,
                        )
                        result_repr = repr(value)
                    else:
                        exec(
                            compile(parsed, "<mcp-exec>", "exec"),
                            state.exec_globals,
                            state.exec_globals,
                        )
                process_events(state, 2)

                stdout_full = stdout_buf.getvalue()
                stderr_full = stderr_buf.getvalue()

                output_id = await state.store_output(
                    tool_name="execute_code",
                    stdout=stdout_full,
                    stderr=stderr_full,
                    result_repr=result_repr,
                    code=code,
                )

                response: dict[str, Any] = {
                    "status": "ok",
                    "output_id": output_id,
                    **({"result_repr": result_repr} if result_repr is not None else {}),
                }

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
                    response["stderr"] = stderr_truncated
                    if stdout_was_truncated or stderr_was_truncated:
                        response["truncated"] = True
                        response["message"] = (
                            f"Output truncated to {line_limit} lines. "
                            f"Use read_output('{output_id}') to retrieve full output."
                        )
                return response

            except Exception as e:
                process_events(state, 1)
                tb = traceback.format_exc()
                stdout_full = stdout_buf.getvalue()
                stderr_full = stderr_buf.getvalue() + tb

                output_id = await state.store_output(
                    tool_name="execute_code",
                    stdout=stdout_full,
                    stderr=stderr_full,
                    code=code,
                    error=True,
                )

                response = {
                    "status": "error",
                    "output_id": output_id,
                }

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
                    error_summary = f"{type(e).__name__}: {e}"
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

    @_register
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
        """Install Python packages using pip.

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
        timeout : int, default=240
            Timeout for pip install in seconds.
        """
        result = await state.proxy_to_external(
            "install_packages",
            {
                "packages": packages,
                "upgrade": upgrade,
                "no_deps": no_deps,
                "index_url": index_url,
                "extra_index_url": extra_index_url,
                "pre": pre,
                "line_limit": line_limit,
                "timeout": timeout,
            },
        )
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

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            stdout_b, stderr_b = (
                b"",
                f"pip install timed out after {timeout}s".encode(),
            )
        stdout = stdout_b.decode(errors="replace")
        stderr = stderr_b.decode(errors="replace")

        status = "ok" if proc.returncode == 0 else "error"
        command_str = " ".join(shlex.quote(part) for part in cmd)

        output_id = await state.store_output(
            tool_name="install_packages",
            stdout=stdout,
            stderr=stderr,
            packages=packages,
            command=command_str,
            returncode=proc.returncode,
        )

        response: dict[str, Any] = {
            "status": status,
            "returncode": proc.returncode if proc.returncode is not None else -1,
            "command": command_str,
            "output_id": output_id,
        }

        if line_limit == -1:
            response["warning"] = (
                "Unlimited output requested. This may consume a large number "
                "of tokens. Consider using read_output for large outputs."
            )
            response["stdout"] = stdout
            response["stderr"] = stderr
        else:
            stdout_truncated, stdout_was_truncated = truncate_output(
                stdout, int(line_limit)
            )
            stderr_truncated, stderr_was_truncated = truncate_output(
                stderr, int(line_limit)
            )
            response["stdout"] = stdout_truncated
            response["stderr"] = stderr_truncated
            if stdout_was_truncated or stderr_was_truncated:
                response["truncated"] = True
                response["message"] = (
                    f"Output truncated to {line_limit} lines. "
                    f"Use read_output('{output_id}') to retrieve full output."
                )
        return response

    @_register
    async def read_output(
        output_id: str, start: int | str = 0, end: int | str = -1
    ) -> dict[str, Any]:
        """Read stored tool output with optional line range.

        Parameters
        ----------
        output_id : str
            Unique ID of the stored output.
        start : int, default=0
            Starting line number (0-indexed).
        end : int, default=-1
            Ending line number (exclusive). If -1, read to end.
        """
        async with state.output_storage_lock:
            if output_id not in state.output_storage:
                return {
                    "status": "error",
                    "message": f"Output ID '{output_id}' not found",
                }

            stored_output = state.output_storage[output_id]

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

    # ---- backward-compatible module-level tool names (for tests) ----
    # The @server.tool() decorator wraps closures into FunctionTool objects.
    # We need to expose the raw async functions (stored in _raw_tools before
    # decoration) so that ``from napari_mcp.server import list_layers`` works.
    _mod = sys.modules[__name__]
    for _name, _fn in _raw_tools.items():
        setattr(_mod, _name, _fn)

    # Store server instance for test access via ``napari_mcp.server.server``
    _mod.server = server

    return server


def detect_external_viewer_sync() -> bool:
    """Synchronous check for external viewer availability."""
    if _state is None:
        return False
    try:
        try:
            asyncio.get_running_loop()
            return False
        except RuntimeError:
            pass
        loop = asyncio.new_event_loop()
        try:
            client, _ = loop.run_until_complete(_state.detect_external_viewer())
            return client is not None
        finally:
            loop.close()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="napari-mcp",
    help="Napari MCP Server - Control napari viewers via Model Context Protocol",
    add_completion=False,
)


@app.command()
def run(
    auto_detect: bool = typer.Option(
        False, "--auto-detect", help="Auto-detect external napari viewers at startup"
    ),
    port: int = typer.Option(9999, "--port", help="Bridge port for auto-detect mode"),
) -> None:
    """Run the MCP server."""
    mode = StartupMode.AUTO_DETECT if auto_detect else StartupMode.STANDALONE
    state = ServerState(mode=mode, bridge_port=port)
    srv = create_server(state)
    srv.run()


@app.command()
def install() -> None:
    """Install napari-mcp in various AI clients.

    NOTE: This command is deprecated. Use 'napari-mcp-install' instead.
    """
    from rich.console import Console

    console = Console()
    console.print(
        "\n[bold yellow]Deprecated Command[/bold yellow]\n",
        style="yellow",
    )
    console.print(
        "The 'napari-mcp install' command has been replaced by 'napari-mcp-install'.",
    )
    console.print("\n[bold green]To install napari-mcp:[/bold green]")
    console.print("  Run: [bold cyan]napari-mcp-install --help[/bold cyan]")
    console.print(
        "  Or: [bold cyan]napari-mcp-install install --target claude-desktop[/bold cyan] (for example)\n"
    )
    console.print("[yellow]Please use 'napari-mcp-install' instead.[/yellow]\n")
    raise typer.Exit(1)


def main() -> None:
    """Entry point that defaults to running the server."""
    if len(sys.argv) == 1:
        state = ServerState()
        srv = create_server(state)
        srv.run()
    else:
        app()


# ---------------------------------------------------------------------------
# Default initialisation: create state and register tools so that
# ``from napari_mcp.server import list_layers`` works at import time.
# Tests override this via conftest's ``reset_server_state`` fixture.
# ---------------------------------------------------------------------------

if _state is None:
    _state = ServerState()
    create_server(_state)


if __name__ == "__main__":
    main()

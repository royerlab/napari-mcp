"""
Napari MCP Server.

Provides ``create_server(state) -> FastMCP`` which builds an MCP server with
tools defined as closures over a ``ServerState`` instance.  Tool categories
include session management, layer operations, viewer/camera controls,
screenshots, code execution, and package installation.
"""

from __future__ import annotations

import asyncio
import asyncio.subprocess
import contextlib
import logging
import math
import os
import re
import shlex
import sys
from io import BytesIO
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.types import ImageContent
else:
    ImageContent = Any


import fastmcp
import numpy as np
import typer
from fastmcp import FastMCP

from napari_mcp._helpers import (
    build_layer_detail,
    build_truncated_response,
    create_layer_on_viewer,
    parse_bool,
    resolve_layer_type,
    run_code,
)
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


# Regex for validating pip package specifiers (rejects URL-based specifiers)
_PKG_NAME_RE = re.compile(
    r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?"
    r"(\[[\w,\s-]+\])?"
    r"([<>=!~]=?[\w.*,<>=!~\s]*)?$"
)


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
    # Helpers (closures over *state*)
    # ------------------------------------------------------------------

    def _resolve_data_var(var_name: str) -> Any:
        """Look up a variable in the execution namespace.

        Raises ``KeyError`` with a helpful message if the variable is missing.
        """
        if var_name not in state.exec_globals:
            avail = [
                k
                for k in state.exec_globals
                if not k.startswith("__") and k not in ("viewer", "napari", "np")
            ]
            raise KeyError(
                f"Variable '{var_name}' not found in execution namespace. "
                f"Available user variables: {avail}"
            )
        return state.exec_globals[var_name]

    # ------------------------------------------------------------------
    # Tool definitions (closures over *state*)
    # ------------------------------------------------------------------

    @_register
    async def init_viewer(
        title: str | None = None,
        width: int | str | None = None,
        height: int | str | None = None,
        port: int | str | None = None,
        detect_only: bool = False,
    ) -> dict[str, Any]:
        """Create or return the napari viewer, with viewer detection.

        When ``detect_only=True``, reports available viewers (local and
        external) without creating or modifying anything.

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
        detect_only : bool, default=False
            If True, only detect available viewers without initialising.
        """
        if port is not None:
            try:
                state.bridge_port = int(port)
            except Exception:
                logger.error("Invalid port: %s", port)

        # --- Detect-only mode (replaces former detect_viewers tool) ---
        if detect_only:
            viewers: dict[str, Any] = {"local": None, "external": None}
            found, info = await state.detect_external_viewer()
            if found and info is not None:
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
                viewers["local"] = {"available": True, "type": "not_initialized"}
            return {"status": "ok", "viewers": viewers}

        # --- Normal init ---
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
            if state.viewer is None:
                return {"status": "no_viewer"}

            def _close():
                if state.viewer is not None:
                    state.viewer.close()
                    state.viewer = None
                process_events(state)
                return {"status": "closed"}

            try:
                result = state.gui_execute(_close)
            except Exception as e:
                return {"status": "error", "message": f"Failed to close viewer: {e}"}

            if state.qt_pump_task is not None and not state.qt_pump_task.done():
                state.qt_pump_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await state.qt_pump_task
            state.qt_pump_task = None

            return result

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

            layer_details = [build_layer_detail(layer) for layer in v.layers]
            # Add standalone-specific fields
            for layer, detail in zip(v.layers, layer_details, strict=False):
                detail["layer_id"] = id(layer)

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
            if state.viewer is None:
                return []

            def _build():
                v = state.viewer
                return [build_layer_detail(lyr) for lyr in v.layers]

            try:
                return state.gui_execute(_build)
            except Exception:
                return []

    def _parse_numpy_slicing(spec: str) -> tuple:
        """Parse a numpy-style slicing string into a tuple of slices/ints.

        Only allows integers, colons, and commas — no arbitrary expressions.
        Examples: ``"0, :5, :5"`` → ``(0, slice(None, 5), slice(None, 5))``
        """
        components: list[int | slice] = []
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                pieces = part.split(":")
                if len(pieces) > 3:
                    raise ValueError(f"Invalid slice component: {part!r}")
                vals: list[int | None] = []
                for p in pieces:
                    p = p.strip()
                    vals.append(int(p) if p else None)
                while len(vals) < 3:
                    vals.append(None)
                components.append(slice(vals[0], vals[1], vals[2]))
            else:
                components.append(int(part))
        if not components:
            raise ValueError(f"Empty slicing specification: {spec!r}")
        return tuple(components)

    @_register
    async def get_layer(
        name: str,
        include_data: bool = False,
        slicing: str | None = None,
        max_elements: int | str = 1000,
    ) -> dict[str, Any]:
        """Get detailed info about a layer, optionally including data.

        Always returns metadata (shape, dtype, scale, translate, type-specific
        properties). When ``include_data=True`` or ``slicing`` is provided,
        also returns statistics and/or raw data values.

        Parameters
        ----------
        name : str
            Layer name (exact match).
        include_data : bool, default False
            If True, include data statistics (min/max/mean/std) and, for
            small layers, inline data values.
        slicing : str, optional
            Numpy-style index string, e.g. ``"0, :5, :5"``. Implies
            ``include_data=True``.
        max_elements : int, default 1000
            Maximum number of data elements to return inline. Larger data
            is stored and an ``output_id`` returned for ``read_output``.
        """
        max_el = int(max_elements)
        max_el = 1_000_000 if max_el < 0 else min(max_el, 1_000_000)
        want_data = include_data or slicing is not None

        async with state.viewer_lock:
            if state.viewer is None:
                return {
                    "status": "not_found",
                    "name": name,
                    "message": "No viewer is open.",
                }

            def _build():
                v = state.viewer
                if name not in v.layers:
                    return {"status": "not_found", "name": name}

                lyr = v.layers[name]
                ltype = lyr.__class__.__name__
                data = getattr(lyr, "data", None)

                # --- Always: metadata (former get_layer_info) ---
                info: dict[str, Any] = {
                    "status": "ok",
                    "name": lyr.name,
                    "type": ltype,
                    "visible": bool(getattr(lyr, "visible", True)),
                    "opacity": float(getattr(lyr, "opacity", 1.0)),
                    "blending": getattr(lyr, "blending", None),
                    "ndim": int(getattr(lyr, "ndim", 0)),
                }

                if data is not None:
                    try:
                        info["data_shape"] = list(np.shape(data))
                    except Exception:
                        pass
                    dtype = getattr(data, "dtype", None)
                    if dtype is not None:
                        info["data_dtype"] = str(dtype)

                scale = getattr(lyr, "scale", None)
                if scale is not None:
                    try:
                        info["scale"] = [float(s) for s in scale]
                    except Exception:
                        pass
                translate = getattr(lyr, "translate", None)
                if translate is not None:
                    try:
                        info["translate"] = [float(t) for t in translate]
                    except Exception:
                        pass

                # Type-specific metadata
                if ltype == "Image":
                    if hasattr(lyr, "colormap") and lyr.colormap is not None:
                        info["colormap"] = getattr(lyr.colormap, "name", None) or str(
                            lyr.colormap
                        )
                    if (
                        hasattr(lyr, "contrast_limits")
                        and lyr.contrast_limits is not None
                    ):
                        try:
                            cl = list(lyr.contrast_limits)
                            info["contrast_limits"] = [float(cl[0]), float(cl[1])]
                        except Exception:
                            pass
                    info["gamma"] = float(getattr(lyr, "gamma", 1.0))
                    if hasattr(lyr, "interpolation2d"):
                        info["interpolation2d"] = str(lyr.interpolation2d)

                elif ltype == "Labels":
                    if data is not None:
                        try:
                            info["n_labels"] = int(
                                len(np.unique(data)) - (1 if 0 in data else 0)
                            )
                        except Exception:
                            pass
                    if hasattr(lyr, "selected_label"):
                        info["selected_label"] = int(lyr.selected_label)

                elif ltype == "Points":
                    if data is not None:
                        try:
                            info["n_points"] = int(np.shape(data)[0])
                        except Exception:
                            pass
                    if hasattr(lyr, "size"):
                        try:
                            info["point_size"] = float(np.mean(lyr.size))
                        except Exception:
                            pass
                    if hasattr(lyr, "symbol"):
                        info["symbol"] = str(lyr.symbol)

                elif ltype == "Shapes":
                    if data is not None:
                        try:
                            info["nshapes"] = int(lyr.nshapes)
                        except Exception:
                            pass
                    if hasattr(lyr, "shape_type"):
                        info["shape_type"] = list(lyr.shape_type)
                    if hasattr(lyr, "edge_width"):
                        try:
                            info["edge_width"] = float(np.mean(lyr.edge_width))
                        except Exception:
                            pass

                elif ltype == "Vectors":
                    if data is not None:
                        try:
                            info["n_vectors"] = int(np.shape(data)[0])
                        except Exception:
                            pass
                    if hasattr(lyr, "edge_width"):
                        info["edge_width"] = float(lyr.edge_width)

                elif ltype == "Tracks":
                    if data is not None:
                        try:
                            info["n_tracks"] = int(len(np.unique(data[:, 0])))
                        except Exception:
                            pass

                elif ltype == "Surface":
                    if data is not None:
                        try:
                            vertices, faces = data[0], data[1]
                            info["n_vertices"] = int(np.shape(vertices)[0])
                            info["n_faces"] = int(np.shape(faces)[0])
                        except Exception:
                            pass

                if not want_data:
                    return info

                # --- Data retrieval (former get_layer_data) ---

                # Compute statistics for any numeric array data
                def _add_stats(arr_like):
                    try:
                        arr = np.asarray(arr_like)
                        # Sample to avoid allocating a huge float64 copy
                        flat = (
                            arr.flat[:1_000_000]
                            if arr.size > 1_000_000
                            else arr.ravel()
                        )
                        a = np.asarray(flat, dtype=float)
                        info["statistics"] = {
                            "min": float(np.nanmin(a)),
                            "max": float(np.nanmax(a)),
                            "mean": float(np.nanmean(a)),
                            "std": float(np.nanstd(a)),
                        }
                    except Exception:
                        pass

                if ltype == "Points" and data is not None:
                    coords = np.asarray(data)
                    _add_stats(coords)
                    if coords.size <= max_el:
                        info["coordinates"] = coords.tolist()
                    else:
                        info["_large_data"] = coords
                        info["_large_label"] = "coordinates"
                    return info

                if ltype == "Shapes":
                    shapes_data = lyr.data
                    total_elems = sum(np.asarray(s).size for s in shapes_data)
                    if total_elems <= max_el:
                        info["shapes"] = [np.asarray(s).tolist() for s in shapes_data]
                    else:
                        info["_large_data"] = shapes_data
                        info["_large_label"] = "shapes"
                    return info

                if ltype == "Surface" and data is not None:
                    try:
                        vertices, faces = np.asarray(data[0]), np.asarray(data[1])
                        info["data_shape"] = {
                            "vertices": list(vertices.shape),
                            "faces": list(faces.shape),
                        }
                        total = vertices.size + faces.size
                        if total <= max_el:
                            info["vertices"] = vertices.tolist()
                            info["faces"] = faces.tolist()
                        else:
                            info["_large_data"] = (vertices, faces)
                            info["_large_label"] = "surface"
                    except Exception:
                        pass
                    return info

                if ltype == "Vectors" and data is not None:
                    arr = np.asarray(data)
                    _add_stats(arr)
                    if arr.size <= max_el:
                        info["data"] = arr.tolist()
                    else:
                        info["_large_data"] = arr
                        info["_large_label"] = "vectors"
                    return info

                if ltype == "Tracks" and data is not None:
                    arr = np.asarray(data)
                    _add_stats(arr)
                    if arr.size <= max_el:
                        info["data"] = arr.tolist()
                    else:
                        info["_large_data"] = arr
                        info["_large_label"] = "tracks"
                    return info

                # Image / Labels / generic
                if data is None:
                    return info

                arr = np.asarray(data)
                if np.issubdtype(arr.dtype, np.number) or np.issubdtype(
                    arr.dtype, np.bool_
                ):
                    _add_stats(arr)

                if slicing is not None:
                    try:
                        idx = _parse_numpy_slicing(slicing)
                        extracted = np.asarray(arr[idx])
                        info["slice_shape"] = list(extracted.shape)
                        if extracted.size <= max_el:
                            info["data"] = extracted.tolist()
                        else:
                            info["_large_data"] = extracted
                            info["_large_label"] = f"slice[{slicing}]"
                    except Exception as e:
                        info["slice_error"] = str(e)

                return info

            try:
                raw = state.gui_execute(_build)
            except Exception as e:
                return {"status": "error", "message": f"Failed to get layer: {e}"}

        # Handle large data storage (outside gui_execute since store_output is async)
        if isinstance(raw, dict) and "_large_data" in raw:
            large = raw.pop("_large_data")
            label = raw.pop("_large_label", "data")
            if isinstance(large, list | tuple):
                lines = [
                    repr(item)
                    if not isinstance(item, np.ndarray)
                    else np.array2string(item, threshold=np.inf)
                    for item in large
                ]
                text = "\n---\n".join(lines)
            elif isinstance(large, np.ndarray):
                text = np.array2string(large, threshold=np.inf)
            else:
                text = repr(large)
            oid = await state.store_output(
                tool_name="get_layer",
                stdout=text,
                stderr="",
            )
            raw["output_id"] = oid
            raw["message"] = (
                f"{label} too large for inline response "
                f"(>{max_el} elements). Use read_output('{oid}') to retrieve."
            )

        return raw

    @_register
    async def add_layer(
        layer_type: str,
        path: str | None = None,
        data: list | None = None,
        data_var: str | None = None,
        name: str | None = None,
        # Image / Labels options
        colormap: str | None = None,
        blending: str | None = None,
        channel_axis: int | str | None = None,
        # Points options
        size: float | str | None = None,
        # Shapes options
        shape_type: str | None = None,
        edge_color: str | None = None,
        face_color: str | None = None,
        edge_width: float | str | None = None,
    ) -> dict[str, Any]:
        """Add a layer to the viewer.

        Parameters
        ----------
        layer_type : str
            One of: ``"image"``, ``"labels"``, ``"points"``, ``"shapes"``,
            ``"vectors"``, ``"tracks"``, ``"surface"``.
        path : str, optional
            File path (for image/labels).
        data : list, optional
            Inline data (coordinates, shape vertices, etc.).
        data_var : str, optional
            Name of a variable in the ``execute_code`` namespace.
        name : str, optional
            Layer name. Defaults to variable name or filename.
        colormap : str, optional
            Colormap name (image only).
        blending : str, optional
            Blending mode (image only).
        channel_axis : int, optional
            Channel axis (image only).
        size : float, optional
            Point size in pixels (points only, default 10).
        shape_type : str, optional
            Shape type: "rectangle", "ellipse", "line", "path", "polygon"
            (shapes only, default "rectangle").
        edge_color : str, optional
            Edge color (shapes/vectors only).
        face_color : str, optional
            Face color (shapes only).
        edge_width : float, optional
            Edge width in pixels (shapes/vectors only).
        """
        lt = resolve_layer_type(layer_type)
        if lt is None:
            return {
                "status": "error",
                "message": (
                    f"Unknown layer_type '{layer_type}'. "
                    f"Valid types: image, labels, points, shapes, vectors, tracks, surface"
                ),
            }

        # --- Resolve data ---
        sources = sum([data_var is not None, data is not None, path is not None])
        if sources > 1:
            return {
                "status": "error",
                "message": "Provide only ONE of 'path', 'data', or 'data_var', not multiple.",
            }

        resolved_data = None
        if data_var:
            try:
                resolved_data = _resolve_data_var(data_var)
            except KeyError as e:
                return {"status": "error", "message": str(e)}
            if name is None:
                name = data_var
        elif data is not None:
            resolved_data = data
        elif path:
            if lt in ("image", "labels"):
                # Proxy check for image path loading
                if lt == "image":
                    params: dict[str, Any] = {
                        "layer_type": "image",
                        "path": path,
                    }
                    if name:
                        params["name"] = name
                    if colormap:
                        params["colormap"] = colormap
                    if blending:
                        params["blending"] = blending
                    if channel_axis is not None:
                        params["channel_axis"] = int(channel_axis)
                    result = await state.proxy_to_external("add_layer", params)
                    if result is not None:
                        return result

                from pathlib import Path as _Path

                import imageio.v3 as iio

                p = _Path(path).expanduser().resolve(strict=False)
                if not p.exists():
                    return {
                        "status": "error",
                        "message": f"File not found: {p}",
                    }
                try:
                    resolved_data = iio.imread(str(p))
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to add {layer_type} layer: {e}",
                    }
            else:
                return {
                    "status": "error",
                    "message": f"'path' is only supported for image/labels, not {layer_type}",
                }
        elif lt == "surface":
            return {
                "status": "error",
                "message": "'data_var' is required for surface layers.",
            }
        else:
            return {
                "status": "error",
                "message": "Provide 'path', 'data', or 'data_var'.",
            }

        async with state.viewer_lock:

            def _add():
                v = ensure_viewer(state)
                result = create_layer_on_viewer(
                    v,
                    resolved_data,
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
                process_events(state)
                return result

            try:
                return state.gui_execute(_add)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to add {layer_type} layer: {e}",
                }

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

            try:
                return state.gui_execute(_remove)
            except Exception as e:
                return {"status": "error", "message": f"Failed to remove layer: {e}"}

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
        active: bool | None = None,
    ) -> dict[str, Any]:
        """Set properties on a layer by name.

        Parameters
        ----------
        name : str
            Layer name (exact match).
        visible, opacity, colormap, blending, contrast_limits, gamma
            Standard layer rendering properties.
        new_name : str, optional
            Rename the layer.
        active : bool, optional
            If True, make this the selected/active layer. Setting to False
            has no effect (use viewer selection directly).
        """
        async with state.viewer_lock:

            def _set():
                v = ensure_viewer(state)
                if name not in v.layers:
                    return {"status": "not_found", "name": name}
                lyr = v.layers[name]
                if visible is not None and hasattr(lyr, "visible"):
                    lyr.visible = parse_bool(visible)
                if opacity is not None and hasattr(lyr, "opacity"):
                    o = float(opacity)
                    if not (0.0 <= o <= 1.0):
                        return {
                            "status": "error",
                            "message": f"opacity must be between 0.0 and 1.0, got {o}",
                        }
                    lyr.opacity = o
                if colormap is not None and hasattr(lyr, "colormap"):
                    try:
                        lyr.colormap = colormap
                    except (KeyError, ValueError) as e:
                        return {
                            "status": "error",
                            "message": f"Invalid colormap '{colormap}': {e}",
                        }
                if blending is not None and hasattr(lyr, "blending"):
                    try:
                        lyr.blending = blending
                    except (ValueError, KeyError) as e:
                        return {
                            "status": "error",
                            "message": f"Invalid blending mode '{blending}': {e}",
                        }
                if contrast_limits is not None and hasattr(lyr, "contrast_limits"):
                    cl = list(contrast_limits)
                    if len(cl) != 2:
                        return {
                            "status": "error",
                            "message": f"contrast_limits must be [min, max], got {len(cl)} values",
                        }
                    try:
                        lyr.contrast_limits = [float(cl[0]), float(cl[1])]
                    except Exception as e:
                        return {
                            "status": "error",
                            "message": f"Invalid contrast_limits: {e}",
                        }
                if gamma is not None and hasattr(lyr, "gamma"):
                    g = float(gamma)
                    if g <= 0:
                        return {
                            "status": "error",
                            "message": f"gamma must be > 0, got {g}",
                        }
                    lyr.gamma = g
                if new_name is not None:
                    lyr.name = new_name
                if active is not None and parse_bool(active):
                    v.layers.selection = {lyr}
                process_events(state)
                return {"status": "ok", "name": lyr.name}

            try:
                return state.gui_execute(_set)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to set layer properties: {e}",
                }

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

            try:
                return state.gui_execute(_reorder)
            except Exception as e:
                return {"status": "error", "message": f"Failed to reorder layer: {e}"}

    @_register
    async def apply_to_layers(
        filter_type: str | None = None,
        filter_pattern: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply property changes to multiple layers matching a filter.

        Parameters
        ----------
        filter_type : str, optional
            Layer type name to match (e.g., "Image", "Labels", "Points").
        filter_pattern : str, optional
            Glob pattern matched against layer names (e.g., "seg_*").
        properties : dict, optional
            Properties to set on matched layers. Supported keys: ``visible``,
            ``opacity``, ``colormap``, ``blending``, ``contrast_limits``,
            ``gamma``, ``new_name`` (renames by appending a suffix is NOT
            supported — use ``set_layer_properties`` individually).
        """
        import fnmatch

        if properties is None or not properties:
            return {"status": "error", "message": "No properties specified."}

        _KNOWN_PROPS = {
            "visible",
            "opacity",
            "colormap",
            "blending",
            "contrast_limits",
            "gamma",
        }
        unknown_keys = set(properties.keys()) - _KNOWN_PROPS

        async with state.viewer_lock:

            def _apply():
                v = ensure_viewer(state)
                matched: list[str] = []

                for lyr in list(v.layers):
                    ltype = lyr.__class__.__name__
                    if filter_type and ltype != filter_type:
                        continue
                    if filter_pattern and not fnmatch.fnmatch(lyr.name, filter_pattern):
                        continue

                    matched.append(lyr.name)
                    for key, val in properties.items():
                        if key in unknown_keys:
                            continue
                        try:
                            if key == "visible":
                                lyr.visible = parse_bool(val)
                            elif key == "opacity":
                                o = float(val)
                                if 0.0 <= o <= 1.0:
                                    lyr.opacity = o
                            elif key == "colormap" and hasattr(lyr, "colormap"):
                                lyr.colormap = val
                            elif key == "blending":
                                lyr.blending = val
                            elif key == "contrast_limits" and hasattr(
                                lyr, "contrast_limits"
                            ):
                                cl = list(val)
                                if len(cl) == 2:
                                    lyr.contrast_limits = (float(cl[0]), float(cl[1]))
                            elif key == "gamma" and hasattr(lyr, "gamma"):
                                g = float(val)
                                if g > 0:
                                    lyr.gamma = g
                        except Exception:
                            pass  # skip invalid values per-layer

                process_events(state)
                result: dict[str, Any] = {
                    "status": "ok",
                    "matched": matched,
                    "count": len(matched),
                }
                if unknown_keys:
                    result["unknown_properties"] = sorted(unknown_keys)
                    result["message"] = (
                        f"Unknown properties ignored: {', '.join(sorted(unknown_keys))}"
                    )
                return result

            try:
                return state.gui_execute(_apply)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to apply properties: {e}",
                }

    @_register
    async def configure_viewer(
        reset_view: bool = False,
        center: list[float] | None = None,
        zoom: float | str | None = None,
        angles: list[float] | None = None,
        ndisplay: int | str | None = None,
        dims_axis: int | str | None = None,
        dims_value: int | str | None = None,
        grid: bool | str | None = None,
    ) -> dict[str, Any]:
        """Configure viewer display: camera, dimensions, and grid.

        All parameters are optional — set any combination in one call.

        Parameters
        ----------
        reset_view : bool, default False
            If True, reset the camera to fit all data.
        center : list[float], optional
            Camera center position.
        zoom : float, optional
            Camera zoom factor (must be > 0).
        angles : list[float], optional
            Camera angles as [azimuth, elevation, roll] in degrees.
        ndisplay : int, optional
            Number of displayed dimensions (2 or 3).
        dims_axis : int, optional
            Axis index for slider position (use with ``dims_value``).
        dims_value : int, optional
            Step value for the given axis.
        grid : bool, optional
            Enable or disable grid view.
        """
        async with state.viewer_lock:

            def _configure():
                v = ensure_viewer(state)
                result: dict[str, Any] = {"status": "ok"}

                # Validate upfront
                if zoom is not None:
                    z = float(zoom)
                    if z <= 0:
                        return {
                            "status": "error",
                            "message": f"zoom must be > 0, got {z}",
                        }
                if ndisplay is not None:
                    nd = int(ndisplay)
                    if nd not in (2, 3):
                        return {
                            "status": "error",
                            "message": f"ndisplay must be 2 or 3, got {nd}",
                        }
                if (dims_axis is None) != (dims_value is None):
                    return {
                        "status": "error",
                        "message": "Both 'dims_axis' and 'dims_value' must be provided together.",
                    }
                if dims_axis is not None:
                    ax = int(dims_axis)
                    if ax < 0 or ax >= v.dims.ndim:
                        return {
                            "status": "error",
                            "message": f"axis {ax} out of range for {v.dims.ndim}D data",
                        }

                # Apply
                if reset_view:
                    v.reset_view()

                if center is not None:
                    v.camera.center = list(map(float, center))
                if zoom is not None:
                    v.camera.zoom = float(zoom)
                if angles is not None:
                    v.camera.angles = tuple(float(a) for a in angles)

                result["center"] = list(map(float, v.camera.center))
                result["zoom"] = float(v.camera.zoom)
                result["angles"] = list(map(float, v.camera.angles))

                if ndisplay is not None:
                    v.dims.ndisplay = int(ndisplay)
                    result["ndisplay"] = int(v.dims.ndisplay)

                if dims_axis is not None and dims_value is not None:
                    ax = int(dims_axis)
                    val = int(dims_value)
                    nsteps = v.dims.nsteps[ax]
                    clamped = max(0, min(val, nsteps - 1))
                    v.dims.set_current_step(ax, clamped)
                    result["axis"] = ax
                    result["value"] = clamped
                    if clamped != val:
                        result["warning"] = (
                            f"value {val} clamped to {clamped} "
                            f"(axis {ax} has {nsteps} steps)"
                        )

                if grid is not None:
                    v.grid.enabled = parse_bool(grid)
                    result["grid"] = bool(v.grid.enabled)

                process_events(state)
                return result

            try:
                return state.gui_execute(_configure)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to configure viewer: {e}",
                }

    @_register
    async def save_layer_data(
        name: str,
        path: str,
        format: str | None = None,
    ) -> dict[str, Any]:
        """Save a layer's data to a file.

        Parameters
        ----------
        name : str
            Layer name.
        path : str
            Output file path. Format is inferred from extension unless
            *format* is specified. Supported: ``.tiff``, ``.png``,
            ``.npy``, ``.csv`` (points/tabular only).
        format : str, optional
            Explicit format override (e.g., ``"npy"``, ``"tiff"``).
        """
        from pathlib import Path as _Path

        async with state.viewer_lock:

            def _save():
                v = ensure_viewer(state)
                if name not in v.layers:
                    return {"status": "not_found", "name": name}

                lyr = v.layers[name]
                p = _Path(path).expanduser().resolve()
                p.parent.mkdir(parents=True, exist_ok=True)
                ext = format or p.suffix.lstrip(".").lower()
                ltype = lyr.__class__.__name__

                _SUPPORTED_EXTS = {
                    "npy",
                    "csv",
                    "tiff",
                    "tif",
                    "png",
                    "jpg",
                    "jpeg",
                }
                if ext and ext not in _SUPPORTED_EXTS:
                    return {
                        "status": "error",
                        "message": (
                            f"Unsupported format '{ext}'. "
                            f"Supported: {', '.join(sorted(_SUPPORTED_EXTS))}"
                        ),
                    }

                # Validate format/type compatibility
                if ext == "csv" and ltype not in ("Points", "Tracks", "Vectors"):
                    return {
                        "status": "error",
                        "message": f"CSV format only supported for Points/Tracks/Vectors, not {ltype}.",
                    }
                if ext in ("tiff", "tif", "png", "jpg", "jpeg") and ltype not in (
                    "Image",
                    "Labels",
                ):
                    return {
                        "status": "error",
                        "message": f"Image format '{ext}' only supported for Image/Labels, not {ltype}.",
                    }

                if ext == "npy":
                    data = getattr(lyr, "data", None)
                    if not str(p).endswith(".npy"):
                        p = p.with_suffix(".npy")
                    np.save(str(p), data, allow_pickle=False)
                elif ext == "csv" and ltype in ("Points", "Tracks", "Vectors"):
                    data = np.asarray(lyr.data)
                    flat = data.reshape(-1, data.shape[-1])
                    ncols = flat.shape[1]
                    if ltype == "Points":
                        header = ",".join(f"axis-{i}" for i in range(ncols))
                    elif ltype == "Tracks":
                        header = ",".join(
                            ["track_id"] + [f"axis-{i}" for i in range(ncols - 1)]
                        )
                    else:
                        header = ",".join(f"col-{i}" for i in range(ncols))
                    np.savetxt(str(p), flat, delimiter=",", header=header, comments="")
                elif ltype in ("Image", "Labels"):
                    import imageio.v3 as iio

                    data = np.asarray(lyr.data)
                    iio.imwrite(str(p), data)
                else:
                    # Fallback: numpy save
                    data = getattr(lyr, "data", None)
                    if not str(p).endswith(".npy"):
                        p = p.with_suffix(".npy")
                    np.save(str(p), data, allow_pickle=False)

                return {
                    "status": "ok",
                    "path": str(p),
                    "format": ext,
                    "size_bytes": int(p.stat().st_size),
                }

            try:
                return state.gui_execute(_save)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to save layer data: {e}",
                }

    @_register
    async def screenshot(
        canvas_only: bool | str = True,
        save_path: str | None = None,
        axis: int | str | None = None,
        slice_range: str | None = None,
        interpolate_to_fit: bool = False,
        save_dir: str | None = None,
    ) -> ImageContent | list[ImageContent] | dict[str, Any]:
        """Take a screenshot, or a timelapse series by sweeping a dims axis.

        For a single screenshot, call with no ``axis``/``slice_range``.
        For a timelapse, provide both ``axis`` and ``slice_range``.

        Parameters
        ----------
        canvas_only : bool, default True
            If True, only capture the canvas area.
        save_path : str, optional
            Save single screenshot to this file path (returns metadata).
        axis : int, optional
            Dims axis to sweep for timelapse (e.g., temporal axis).
        slice_range : str, optional
            Python-like slice string, e.g. ``"1:5"``, ``":6"``, ``"::2"``.
            Required when ``axis`` is provided.
        interpolate_to_fit : bool, default False
            If True, downsample timelapse frames to fit ~1.3 MB total.
        save_dir : str, optional
            Save timelapse frames as ``frame_NNNN.png`` in this directory.
        """
        from PIL import Image

        co = parse_bool(canvas_only, default=True)

        # --- Single screenshot mode ---
        if axis is None and slice_range is None:
            from pathlib import Path as _Path

            if save_path is None:
                result = await state.proxy_to_external(
                    "screenshot", {"canvas_only": co}
                )
                if result is not None:
                    return result

            async with state.viewer_lock:

                def _shot():
                    v = ensure_viewer(state)
                    process_events(state, 3)
                    arr = v.screenshot(canvas_only=co)
                    if not isinstance(arr, np.ndarray):
                        arr = np.asarray(arr)
                    if arr.dtype != np.uint8:
                        arr = arr.astype(np.uint8, copy=False)
                    img = Image.fromarray(arr)

                    if save_path is not None:
                        p = _Path(save_path).expanduser().resolve()
                        p.parent.mkdir(parents=True, exist_ok=True)
                        img.save(str(p))
                        return {
                            "status": "ok",
                            "path": str(p),
                            "size": [img.width, img.height],
                        }

                    # Auto-downscale inline screenshots to stay under
                    # ~200 KB base64 (≈150 KB PNG).  This prevents MCP
                    # context overflow while keeping useful resolution.
                    max_png_bytes = 150_000
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    enc = buf.getvalue()
                    if len(enc) > max_png_bytes:
                        scale = math.sqrt(max_png_bytes / len(enc))
                        new_w = max(1, int(img.width * scale))
                        new_h = max(1, int(img.height * scale))
                        img = img.resize((new_w, new_h), resample=Image.BILINEAR)
                        buf = BytesIO()
                        img.save(buf, format="PNG")
                        enc = buf.getvalue()
                    return fastmcp.utilities.types.Image(
                        data=enc, format="png"
                    ).to_image_content()

                try:
                    return state.gui_execute(_shot)
                except Exception as e:
                    return {"status": "error", "message": f"Screenshot failed: {e}"}

        # --- Timelapse mode ---
        if axis is None or slice_range is None:
            return {
                "status": "error",
                "message": "Both 'axis' and 'slice_range' are required for timelapse.",
            }

        max_total_base64_bytes = 1309246 if interpolate_to_fit else None

        result = await state.proxy_to_external(
            "screenshot",
            {
                "axis": axis,
                "slice_range": slice_range,
                "canvas_only": co,
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
                ax = int(axis)
                try:
                    nsteps_tuple = getattr(v.dims, "nsteps", None)
                    if nsteps_tuple is None:
                        raise AttributeError
                    total = int(nsteps_tuple[ax])
                except Exception:
                    try:
                        total = max(
                            int(getattr(lyr.data, "shape", [1])[ax])
                            if ax < getattr(lyr.data, "ndim", 0)
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

                v.dims.set_current_step(ax, int(indices[0]))
                process_events(state, 2)
                sample_arr = v.screenshot(canvas_only=co)
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

                # Save to directory mode
                if save_dir is not None:
                    from pathlib import Path as _Path

                    dirp = _Path(save_dir).expanduser().resolve()
                    dirp.mkdir(parents=True, exist_ok=True)
                    saved_paths: list[str] = []
                    for idx in indices:
                        v.dims.set_current_step(ax, int(idx))
                        process_events(state, 2)
                        arr = v.screenshot(canvas_only=co)
                        if not isinstance(arr, np.ndarray):
                            arr = np.asarray(arr)
                        if arr.dtype != np.uint8:
                            arr = arr.astype(np.uint8, copy=False)
                        img = Image.fromarray(arr)
                        fp = dirp / f"frame_{idx:04d}.png"
                        img.save(str(fp))
                        saved_paths.append(str(fp))
                    return {
                        "status": "ok",
                        "paths": saved_paths,
                        "n_frames": len(saved_paths),
                    }

                images: list[ImageContent] = []
                total_b64_len = 0
                for idx in indices:
                    v.dims.set_current_step(ax, int(idx))
                    process_events(state, 2)
                    arr = v.screenshot(canvas_only=co)
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

            try:
                return state.gui_execute(_run_series)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Timelapse screenshot failed: {e}",
                }

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

        Note
        ----
        In standalone mode, code execution runs synchronously on the main
        thread (required for Qt/napari operations) and has no timeout.
        In bridge mode, a 600-second timeout is enforced.
        """
        import napari

        try:
            line_limit = int(line_limit)
        except (ValueError, TypeError):
            line_limit = 30

        result = await state.proxy_to_external("execute_code", {"code": code})
        if result is not None:
            return result

        async with state.viewer_lock:
            v = ensure_viewer(state)
            state.exec_globals.setdefault("__builtins__", __builtins__)  # type: ignore[assignment]
            state.exec_globals["viewer"] = v
            state.exec_globals.setdefault("napari", napari)
            state.exec_globals.setdefault("np", np)

            stdout_full, stderr_full, result_repr, error = run_code(
                code, state.exec_globals, source_label="<mcp-exec>"
            )
            process_events(state, 2 if error is None else 1)

            status = "error" if error else "ok"
            output_id = await state.store_output(
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
        try:
            line_limit = int(line_limit)
        except (ValueError, TypeError):
            line_limit = 30

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

        for pkg in packages:
            if not _PKG_NAME_RE.match(pkg.strip()):
                return {
                    "status": "error",
                    "message": f"Invalid package specifier: {pkg!r}. "
                    "Use standard pip format (e.g., 'numpy>=1.20').",
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

        response = build_truncated_response(
            status=status,
            output_id=output_id,
            stdout_full=stdout,
            stderr_full=stderr,
            result_repr=None,
            line_limit=line_limit,
        )
        response["returncode"] = proc.returncode if proc.returncode is not None else -1
        response["command"] = command_str
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
            found, _ = loop.run_until_complete(_state.detect_external_viewer())
            return found
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
        "  Or: [bold cyan]napari-mcp-install install claude-desktop[/bold cyan] (for example)\n"
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


if __name__ == "__main__":
    main()

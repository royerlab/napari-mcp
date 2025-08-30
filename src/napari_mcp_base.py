"""Base MCP tools for napari viewer control.

This module contains the core tool implementations that can be shared
between the standalone server and the bridge plugin.
"""

from __future__ import annotations

import ast
import base64
import contextlib
import traceback
from collections.abc import Callable
from functools import wraps
from io import BytesIO, StringIO
from typing import Any

import napari
import numpy as np
from PIL import Image


def viewer_tool(func: Callable) -> Callable:
    """Decorator for viewer tools that need access to a viewer instance.

    The decorated function should have 'viewer' as its first parameter.
    """

    @wraps(func)
    async def wrapper(viewer: napari.Viewer, *args, **kwargs):
        return await func(viewer, *args, **kwargs)

    return wrapper


class NapariMCPTools:
    """Base class with MCP tool implementations for napari viewer control."""

    def __init__(self, viewer: napari.Viewer | None = None):
        """Initialize with an optional viewer instance.

        Parameters
        ----------
        viewer : napari.Viewer, optional
            The viewer instance. Can be set later with set_viewer().
        """
        self.viewer = viewer
        self._exec_globals: dict[str, Any] = {}

    def set_viewer(self, viewer: napari.Viewer) -> None:
        """Set or update the viewer instance."""
        self.viewer = viewer

    def _ensure_viewer(self) -> napari.Viewer:
        """Ensure a viewer is available."""
        if self.viewer is None:
            raise RuntimeError("No viewer instance available")
        return self.viewer

    @staticmethod
    def encode_png_base64(img: np.ndarray) -> dict[str, str]:
        """Encode image as base64 PNG."""
        pil = Image.fromarray(img)
        buf = BytesIO()
        pil.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode("ascii")
        return {"mime_type": "image/png", "base64_data": data}

    async def session_information(self) -> dict[str, Any]:
        """Get comprehensive information about the current napari session."""
        v = self._ensure_viewer()

        viewer_info = {
            "title": v.title,
            "viewer_id": id(v),
            "n_layers": len(v.layers),
            "layer_names": [layer.name for layer in v.layers],
            "selected_layers": [layer.name for layer in v.layers.selection],
            "ndisplay": v.dims.ndisplay,
            "camera_center": list(v.camera.center),
            "camera_zoom": float(v.camera.zoom),
            "camera_angles": list(v.camera.angles) if v.camera.angles else [],
            "grid_enabled": v.grid.enabled,
        }

        layer_details = []
        for layer in v.layers:
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
            "viewer": viewer_info,
            "layers": layer_details,
        }

    async def list_layers(self) -> list[dict[str, Any]]:
        """Return a list of layers with key properties."""
        v = self._ensure_viewer()
        result = []
        for lyr in v.layers:
            entry = {
                "name": lyr.name,
                "type": lyr.__class__.__name__,
                "visible": bool(getattr(lyr, "visible", True)),
                "opacity": float(getattr(lyr, "opacity", 1.0)),
            }
            if hasattr(lyr, "colormap"):
                entry["colormap"] = getattr(lyr.colormap, "name", str(lyr.colormap))
            result.append(entry)
        return result

    async def add_image(
        self,
        path: str | None = None,
        data: list | np.ndarray | None = None,
        name: str | None = None,
        colormap: str | None = None,
        blending: str | None = None,
        channel_axis: int | None = None,
    ) -> dict[str, Any]:
        """Add an image layer from a file path or data."""
        v = self._ensure_viewer()

        # Load data
        if path:
            import imageio.v3 as iio

            img_data = iio.imread(path)
        elif data is not None:
            img_data = np.asarray(data)
        else:
            return {
                "status": "error",
                "message": "Either path or data must be provided",
            }

        layer = v.add_image(
            img_data,
            name=name,
            colormap=colormap,
            blending=blending,
            channel_axis=channel_axis,
        )
        return {"status": "ok", "name": layer.name, "shape": list(img_data.shape)}

    async def add_labels(
        self,
        path: str | None = None,
        data: np.ndarray | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Add a labels layer from a file path or data."""
        v = self._ensure_viewer()

        if path:
            import imageio.v3 as iio

            label_data = iio.imread(path)
        elif data is not None:
            label_data = np.asarray(data)
        else:
            return {
                "status": "error",
                "message": "Either path or data must be provided",
            }

        layer = v.add_labels(label_data, name=name)
        return {"status": "ok", "name": layer.name, "shape": list(label_data.shape)}

    async def add_points(
        self, points: list[list[float]], name: str | None = None, size: float = 10.0
    ) -> dict[str, Any]:
        """Add a points layer."""
        v = self._ensure_viewer()
        arr = np.asarray(points, dtype=float)
        layer = v.add_points(arr, name=name, size=size)
        return {"status": "ok", "name": layer.name, "n_points": int(arr.shape[0])}

    async def remove_layer(self, name: str) -> dict[str, Any]:
        """Remove a layer by name."""
        v = self._ensure_viewer()
        if name in v.layers:
            v.layers.remove(name)
            return {"status": "removed", "name": name}
        return {"status": "not_found", "name": name}

    async def rename_layer(self, old_name: str, new_name: str) -> dict[str, Any]:
        """Rename a layer."""
        v = self._ensure_viewer()
        if old_name not in v.layers:
            return {"status": "not_found", "name": old_name}
        lyr = v.layers[old_name]
        lyr.name = new_name
        return {"status": "ok", "old": old_name, "new": new_name}

    async def set_layer_properties(
        self,
        name: str,
        visible: bool | None = None,
        opacity: float | None = None,
        colormap: str | None = None,
        blending: str | None = None,
        contrast_limits: list[float] | None = None,
        gamma: float | None = None,
    ) -> dict[str, Any]:
        """Set properties on a layer."""
        v = self._ensure_viewer()
        if name not in v.layers:
            return {"status": "not_found", "name": name}

        lyr = v.layers[name]
        if visible is not None:
            lyr.visible = bool(visible)
        if opacity is not None:
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

        return {"status": "ok", "name": lyr.name}

    async def reorder_layer(
        self,
        name: str,
        index: int | None = None,
        before: str | None = None,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Reorder a layer."""
        v = self._ensure_viewer()
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

        return {"status": "ok", "name": name, "index": v.layers.index(name)}

    async def set_active_layer(self, name: str) -> dict[str, Any]:
        """Set the selected/active layer."""
        v = self._ensure_viewer()
        if name not in v.layers:
            return {"status": "not_found", "name": name}
        v.layers.selection = {v.layers[name]}
        return {"status": "ok", "active": name}

    async def reset_view(self) -> dict[str, Any]:
        """Reset the camera view to fit data."""
        v = self._ensure_viewer()
        v.reset_view()
        return {"status": "ok"}

    async def set_zoom(self, zoom: float) -> dict[str, Any]:
        """Set camera zoom factor."""
        v = self._ensure_viewer()
        v.camera.zoom = float(zoom)
        return {"status": "ok", "zoom": float(v.camera.zoom)}

    async def set_camera(
        self,
        center: list[float] | None = None,
        zoom: float | None = None,
        angle: float | None = None,
    ) -> dict[str, Any]:
        """Set camera properties."""
        v = self._ensure_viewer()
        if center is not None:
            v.camera.center = list(map(float, center))
        if zoom is not None:
            v.camera.zoom = float(zoom)
        if angle is not None:
            v.camera.angles = (float(angle),)
        return {
            "status": "ok",
            "center": list(map(float, v.camera.center)),
            "zoom": float(v.camera.zoom),
        }

    async def set_ndisplay(self, ndisplay: int) -> dict[str, Any]:
        """Set number of displayed dimensions (2 or 3)."""
        v = self._ensure_viewer()
        v.dims.ndisplay = int(ndisplay)
        return {"status": "ok", "ndisplay": int(v.dims.ndisplay)}

    async def set_dims_current_step(self, axis: int, value: int) -> dict[str, Any]:
        """Set the current step for a specific axis."""
        v = self._ensure_viewer()
        v.dims.set_current_step(int(axis), int(value))
        return {"status": "ok", "axis": int(axis), "value": int(value)}

    async def set_grid(self, enabled: bool = True) -> dict[str, Any]:
        """Enable or disable grid view."""
        v = self._ensure_viewer()
        v.grid.enabled = bool(enabled)
        return {"status": "ok", "grid": bool(v.grid.enabled)}

    async def screenshot(self, canvas_only: bool = True) -> dict[str, str]:
        """Take a screenshot and return as base64 PNG."""
        v = self._ensure_viewer()
        arr = v.screenshot(canvas_only=canvas_only)
        if not isinstance(arr, np.ndarray):
            arr = np.asarray(arr)
        if arr.dtype != np.uint8:
            arr = arr.astype(np.uint8, copy=False)
        return self.encode_png_base64(arr)

    async def execute_code(self, code: str) -> dict[str, Any]:
        """Execute Python code with access to the viewer."""
        v = self._ensure_viewer()

        # Setup execution environment
        self._exec_globals.setdefault("__builtins__", __builtins__)
        self._exec_globals["viewer"] = v
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
                parsed = ast.parse(code, mode="exec")
                if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                    # Execute all but last, then eval last expression
                    if len(parsed.body) > 1:
                        exec_ast = ast.Module(body=parsed.body[:-1], type_ignores=[])
                        exec(
                            compile(exec_ast, "<mcp-exec>", "exec"),
                            self._exec_globals,
                            self._exec_globals,
                        )
                    last_expr = ast.Expression(body=parsed.body[-1].value)
                    value = eval(
                        compile(last_expr, "<mcp-eval>", "eval"),
                        self._exec_globals,
                        self._exec_globals,
                    )
                    result_repr = repr(value)
                else:
                    exec(
                        compile(parsed, "<mcp-exec>", "exec"),
                        self._exec_globals,
                        self._exec_globals,
                    )

            return {
                "status": "ok",
                **({"result_repr": result_repr} if result_repr is not None else {}),
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

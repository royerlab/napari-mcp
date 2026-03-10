"""Shared helpers used by both server.py and bridge_server.py.

These functions extract logic that was previously duplicated between the
standalone server and the bridge server.
"""

from __future__ import annotations

import ast
import contextlib
import traceback
from io import StringIO
from typing import Any

import numpy as np

from napari_mcp.output import truncate_output

# ---------------------------------------------------------------------------
# Bool parsing
# ---------------------------------------------------------------------------


def parse_bool(value: bool | str | None, default: bool = False) -> bool:
    """Parse a boolean value from various input types.

    Handles bool, str ("true"/"false"/"1"/"0"/etc.), and None.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)


# ---------------------------------------------------------------------------
# Layer type alias map
# ---------------------------------------------------------------------------

LAYER_TYPE_ALIASES: dict[str, str] = {
    "image": "image",
    "images": "image",
    "labels": "labels",
    "label": "labels",
    "points": "points",
    "point": "points",
    "shapes": "shapes",
    "shape": "shapes",
    "vectors": "vectors",
    "vector": "vectors",
    "tracks": "tracks",
    "track": "tracks",
    "surface": "surface",
    "surfaces": "surface",
}


def resolve_layer_type(layer_type: str) -> str | None:
    """Resolve a layer type string to its canonical form.

    Returns None if the type is not recognized.
    """
    return LAYER_TYPE_ALIASES.get(layer_type.strip().lower())


# ---------------------------------------------------------------------------
# Layer detail building (shared between session_information variants)
# ---------------------------------------------------------------------------


def build_layer_detail(layer: Any) -> dict[str, Any]:
    """Build a detail dict for a single napari layer.

    Used by session_information in both standalone and bridge modes.
    """
    detail: dict[str, Any] = {
        "name": layer.name,
        "type": layer.__class__.__name__,
        "visible": bool(getattr(layer, "visible", True)),
        "opacity": float(getattr(layer, "opacity", 1.0)),
    }
    if hasattr(layer, "data") and hasattr(layer.data, "shape"):
        detail["data_shape"] = list(layer.data.shape)
    if hasattr(layer, "data") and hasattr(layer.data, "dtype"):
        detail["data_dtype"] = str(layer.data.dtype)
    if hasattr(layer, "colormap"):
        detail["colormap"] = getattr(layer.colormap, "name", str(layer.colormap))
    if hasattr(layer, "blending"):
        detail["blending"] = getattr(layer, "blending", None)
    if hasattr(layer, "contrast_limits"):
        try:
            cl = layer.contrast_limits
            detail["contrast_limits"] = [float(cl[0]), float(cl[1])]
        except Exception:
            pass
    if hasattr(layer, "gamma"):
        detail["gamma"] = float(getattr(layer, "gamma", 1.0))
    return detail


# ---------------------------------------------------------------------------
# Layer creation on viewer (shared between server and bridge)
# ---------------------------------------------------------------------------


def create_layer_on_viewer(
    viewer: Any,
    resolved_data: Any,
    lt: str,
    *,
    name: str | None = None,
    colormap: str | None = None,
    blending: str | None = None,
    channel_axis: int | str | None = None,
    size: float | str | None = None,
    shape_type: str | None = None,
    edge_color: str | None = None,
    face_color: str | None = None,
    edge_width: float | str | None = None,
) -> dict[str, Any]:
    """Add a layer to a napari viewer and return a result dict.

    This is the shared core used by ``add_layer`` in both server.py
    (standalone) and bridge_server.py (Qt thread). The caller is responsible
    for calling ``process_events`` and holding locks.

    Parameters
    ----------
    viewer : napari.Viewer
        The napari viewer instance.
    resolved_data : Any
        The data to add (numpy array, list, tuple, etc.).
    lt : str
        Canonical layer type (one of: image, labels, points, shapes,
        vectors, tracks, surface).
    """
    if lt == "image":
        arr = np.asarray(resolved_data)
        if arr.size == 0:
            return {
                "status": "error",
                "message": "Cannot add image layer: data is empty.",
            }
        if np.issubdtype(arr.dtype, np.complexfloating):
            return {
                "status": "error",
                "message": (
                    f"Cannot add image layer: complex dtype ({arr.dtype}) "
                    "not supported. Convert to real first (e.g., np.abs(data))."
                ),
            }
        kwargs: dict[str, Any] = {"name": name}
        if colormap is not None:
            kwargs["colormap"] = colormap
        if blending is not None:
            kwargs["blending"] = blending
        if channel_axis is not None:
            kwargs["channel_axis"] = int(channel_axis)
        layer = viewer.add_image(arr, **kwargs)
        # napari returns a list of layers when channel_axis is used
        if isinstance(layer, list):
            names = [lyr.name for lyr in layer]
            return {
                "status": "ok",
                "name": names,
                "shape": list(np.shape(arr)),
                "n_channels": len(layer),
            }
        return {"status": "ok", "name": layer.name, "shape": list(np.shape(arr))}

    elif lt == "labels":
        arr = np.asarray(resolved_data)
        if arr.size == 0:
            return {
                "status": "error",
                "message": "Cannot add labels layer: data is empty.",
            }
        layer = viewer.add_labels(arr, name=name)
        return {"status": "ok", "name": layer.name, "shape": list(np.shape(arr))}

    elif lt == "points":
        arr = np.asarray(resolved_data, dtype=float)
        if arr.size == 0:
            return {
                "status": "error",
                "message": "Cannot add points layer: data is empty.",
            }
        layer = viewer.add_points(arr, name=name, size=float(size or 10.0))
        return {"status": "ok", "name": layer.name, "n_points": int(arr.shape[0])}

    elif lt == "shapes":
        kwargs = {"name": name, "shape_type": shape_type or "rectangle"}
        if edge_color is not None:
            kwargs["edge_color"] = edge_color
        if face_color is not None:
            kwargs["face_color"] = face_color
        if edge_width is not None:
            kwargs["edge_width"] = float(edge_width)
        layer = viewer.add_shapes(resolved_data, **kwargs)
        return {"status": "ok", "name": layer.name, "nshapes": int(layer.nshapes)}

    elif lt == "vectors":
        arr = np.asarray(resolved_data, dtype=float)
        kwargs = {"name": name}
        if edge_color is not None:
            kwargs["edge_color"] = edge_color
        if edge_width is not None:
            kwargs["edge_width"] = float(edge_width)
        layer = viewer.add_vectors(arr, **kwargs)
        return {"status": "ok", "name": layer.name, "n_vectors": int(arr.shape[0])}

    elif lt == "tracks":
        arr = np.asarray(resolved_data, dtype=float)
        layer = viewer.add_tracks(arr, name=name)
        return {
            "status": "ok",
            "name": layer.name,
            "n_tracks": int(len(np.unique(arr[:, 0]))),
        }

    elif lt == "surface":
        layer = viewer.add_surface(resolved_data, name=name)
        verts = np.asarray(resolved_data[0])
        faces = np.asarray(resolved_data[1])
        return {
            "status": "ok",
            "name": layer.name,
            "n_vertices": int(verts.shape[0]),
            "n_faces": int(faces.shape[0]),
        }

    else:
        return {
            "status": "error",
            "message": f"Unknown layer type '{lt}'.",
        }


# ---------------------------------------------------------------------------
# Code execution core
# ---------------------------------------------------------------------------


def run_code(
    code: str,
    exec_globals: dict[str, Any],
    *,
    source_label: str = "<mcp-exec>",
) -> tuple[str, str, str | None, Exception | None]:
    """Execute Python code with stdout/stderr capture.

    This is the shared core used by both ``execute_code`` in server.py
    (standalone) and bridge_server.py (Qt thread).

    Parameters
    ----------
    code : str
        Python code string. The last expression's value is captured.
    exec_globals : dict
        The execution namespace (both globals and locals).
    source_label : str
        Label for compile() filename, e.g. ``"<mcp-exec>"`` or ``"<bridge-exec>"``.

    Returns
    -------
    tuple of (stdout, stderr, result_repr, error)
        - stdout: captured stdout output
        - stderr: captured stderr output (includes traceback on error)
        - result_repr: repr() of the last expression, or None
        - error: the exception if one occurred, or None
    """
    stdout_buf = StringIO()
    stderr_buf = StringIO()
    result_repr: str | None = None
    error: Exception | None = None

    try:
        with (
            contextlib.redirect_stdout(stdout_buf),
            contextlib.redirect_stderr(stderr_buf),
        ):
            parsed = ast.parse(code, mode="exec")
            if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                if len(parsed.body) > 1:
                    exec_ast = ast.Module(body=parsed.body[:-1], type_ignores=[])
                    exec(
                        compile(exec_ast, source_label, "exec"),
                        exec_globals,
                        exec_globals,
                    )
                last_expr = ast.Expression(body=parsed.body[-1].value)
                value = eval(
                    compile(last_expr, source_label.replace("-exec", "-eval"), "eval"),
                    exec_globals,
                    exec_globals,
                )
                result_repr = repr(value)
            else:
                exec(
                    compile(parsed, source_label, "exec"),
                    exec_globals,
                    exec_globals,
                )
    except Exception as e:
        tb = traceback.format_exc()
        error = e
        # Append traceback to stderr
        stderr_buf.write(tb)

    return (
        stdout_buf.getvalue(),
        stderr_buf.getvalue(),
        result_repr,
        error,
    )


# ---------------------------------------------------------------------------
# Truncated response building
# ---------------------------------------------------------------------------


def build_truncated_response(
    *,
    status: str,
    output_id: str,
    stdout_full: str,
    stderr_full: str,
    result_repr: str | None,
    line_limit: int | str,
    error: Exception | None = None,
) -> dict[str, Any]:
    """Build a response dict with optional output truncation.

    This is the shared pattern used by ``execute_code`` in both server.py
    and bridge_server.py, and also by ``install_packages``.

    Parameters
    ----------
    status : str
        "ok" or "error".
    output_id : str
        The stored output ID.
    stdout_full, stderr_full : str
        Full stdout/stderr content.
    result_repr : str or None
        The repr of the last expression result.
    line_limit : int or str
        Maximum lines (-1 for unlimited).
    error : Exception or None
        The exception, if status == "error".

    Returns
    -------
    dict[str, Any]
        The response dict ready to return from a tool.
    """
    response: dict[str, Any] = {
        "status": status,
        "output_id": output_id,
    }
    if result_repr is not None:
        response["result_repr"] = result_repr

    if line_limit == -1 or str(line_limit) == "-1":
        response["warning"] = (
            "Unlimited output requested. This may consume a large number "
            "of tokens. Consider using read_output for large outputs."
        )
        response["stdout"] = stdout_full
        response["stderr"] = stderr_full
    else:
        limit = int(line_limit)
        stdout_truncated, stdout_was_truncated = truncate_output(stdout_full, limit)
        stderr_truncated, stderr_was_truncated = truncate_output(stderr_full, limit)
        response["stdout"] = stdout_truncated

        # For errors, inject a summary line if not already visible
        if status == "error" and error is not None:
            error_summary = f"{type(error).__name__}: {error}"
            if error_summary not in stderr_truncated:
                if stderr_truncated and not stderr_truncated.endswith("\n"):
                    stderr_truncated += "\n"
                stderr_truncated += error_summary + "\n"

        response["stderr"] = stderr_truncated
        if stdout_was_truncated or stderr_was_truncated:
            response["truncated"] = True
            response["message"] = (
                f"Output truncated to {limit} lines. "
                f"Use read_output('{output_id}') to retrieve full output."
            )

    return response

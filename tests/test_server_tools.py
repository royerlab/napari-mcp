"""Unit tests for all 16 MCP tools exposed by the server.

Organised by tool name. Each class covers happy paths, edge cases,
error handling, and input validation for one tool.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import imageio.v3 as iio
import numpy as np
import pytest

from napari_mcp import server as s
from napari_mcp.state import StartupMode

# Shortcut: every test that needs a viewer uses this pattern.
pytestmark = pytest.mark.asyncio


# ── helpers ────────────────────────────────────────────────────────────────


def _viewer(make_napari_viewer):
    """Create viewer and wire it into server state."""
    v = make_napari_viewer()
    s._state.viewer = v
    return v


# ── init_viewer ────────────────────────────────────────────────────────────


class TestInitViewer:
    async def test_basic(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.init_viewer(title="T", width=640, height=480)
        assert res["status"] == "ok"
        assert res["title"] == "T"
        assert isinstance(res["layers"], list)

    async def test_detect_only_with_viewer(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        res = await s.init_viewer(detect_only=True)
        assert res["status"] == "ok"
        assert res["viewers"]["local"]["available"] is True
        assert res["viewers"]["local"]["title"] == v.title
        assert res["viewers"]["external"]["available"] is False

    async def test_detect_only_no_viewer(self):
        s._state.viewer = None
        res = await s.init_viewer(detect_only=True)
        assert res["viewers"]["local"]["type"] == "not_initialized"

    async def test_invalid_port_does_not_crash(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.init_viewer(port="not_a_number")
        assert res["status"] == "ok"

    async def test_auto_detect_fallback(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        s._state.mode = StartupMode.AUTO_DETECT
        with patch.object(
            s._state,
            "external_session_information",
            new_callable=AsyncMock,
            side_effect=ConnectionError,
        ):
            res = await s.init_viewer()
        assert res["status"] == "ok"
        assert res["viewer_type"] == "local"


# ── close_viewer ───────────────────────────────────────────────────────────


class TestCloseViewer:
    async def test_close_then_close_again(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.close_viewer())["status"] == "closed"
        assert (await s.close_viewer())["status"] == "no_viewer"


# ── session_information ────────────────────────────────────────────────────


class TestSessionInformation:
    async def test_with_layers(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        v.add_points(np.array([[1, 1]]), name="pts")
        await s.set_layer_properties("pts", active=True)

        res = await s.session_information()
        assert res["status"] == "ok"
        assert res["viewer"]["n_layers"] == 2
        assert "pts" in res["viewer"]["selected_layers"]
        assert "system" in res
        assert len(res["layers"]) == 2

    async def test_no_viewer(self):
        s._state.viewer = None
        res = await s.session_information()
        assert res["status"] == "ok"
        assert res["viewer"] is None

    async def test_auto_detect_fallback(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        s._state.mode = StartupMode.AUTO_DETECT
        with patch.object(
            s._state,
            "external_session_information",
            new_callable=AsyncMock,
            side_effect=ConnectionError,
        ):
            res = await s.session_information()
        assert res["session_type"] == "napari_mcp_standalone_session"


# ── list_layers ────────────────────────────────────────────────────────────


class TestListLayers:
    async def test_returns_properties(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        await s.set_layer_properties("img", opacity=0.3, visible=False)

        layers = await s.list_layers()
        lyr = next(entry for entry in layers if entry["name"] == "img")
        assert lyr["opacity"] == pytest.approx(0.3)
        assert lyr["visible"] is False
        assert lyr["type"] == "Image"

    async def test_empty(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert await s.list_layers() == []

    async def test_proxy_list(self):
        s._state.mode = StartupMode.AUTO_DETECT
        mock = [{"name": "x"}]
        with patch.object(
            s._state, "proxy_to_external", new_callable=AsyncMock, return_value=mock
        ):
            assert await s.list_layers() == mock

    async def test_proxy_dict_with_content(self):
        s._state.mode = StartupMode.AUTO_DETECT
        inner = [{"name": "x"}]
        with patch.object(
            s._state,
            "proxy_to_external",
            new_callable=AsyncMock,
            return_value={"content": inner},
        ):
            assert await s.list_layers() == inner

    async def test_proxy_bad_format(self):
        s._state.mode = StartupMode.AUTO_DETECT
        with patch.object(
            s._state,
            "proxy_to_external",
            new_callable=AsyncMock,
            return_value={"content": "bad"},
        ):
            assert await s.list_layers() == []
        with patch.object(
            s._state,
            "proxy_to_external",
            new_callable=AsyncMock,
            return_value={"error": "x"},
        ):
            assert await s.list_layers() == []


# ── get_layer ──────────────────────────────────────────────────────────────


class TestGetLayer:
    # -- metadata (include_data=False) --

    async def test_image_metadata(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(
            np.zeros((10, 20), dtype=np.uint8),
            name="img",
            scale=[2.0, 3.0],
            translate=[10.0, 20.0],
        )
        res = await s.get_layer("img")
        assert res["status"] == "ok"
        assert res["type"] == "Image"
        assert res["data_shape"] == [10, 20]
        assert res["data_dtype"] == "uint8"
        assert res["ndim"] == 2
        assert res["scale"] == [2.0, 3.0]
        assert res["translate"] == [10.0, 20.0]
        assert "colormap" in res and "gamma" in res
        assert "statistics" not in res  # not requested

    async def test_labels_metadata(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_labels(np.array([[0, 1], [2, 0]], dtype=np.int32), name="seg")
        res = await s.get_layer("seg")
        assert res["type"] == "Labels"
        assert res["n_labels"] == 2

    async def test_points_metadata(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_points(np.array([[1.0, 2.0], [3.0, 4.0]]), name="pts")
        res = await s.get_layer("pts")
        assert res["n_points"] == 2
        assert "point_size" in res
        assert "coordinates" not in res  # not requested

    async def test_not_found(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.get_layer("nope"))["status"] == "not_found"

    # -- data (include_data=True / slicing) --

    async def test_image_statistics(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.array([[10, 20], [30, 40]], dtype=np.float32), name="img")
        res = await s.get_layer("img", include_data=True)
        st = res["statistics"]
        assert st["min"] == 10.0 and st["max"] == 40.0 and st["mean"] == 25.0

    async def test_image_slicing(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.arange(60).reshape(3, 4, 5).astype(np.float32), name="vol")
        res = await s.get_layer("vol", slicing="0, :2, :2")
        assert res["slice_shape"] == [2, 2]
        assert res["data"] == [[0, 1], [5, 6]]
        assert "statistics" in res  # slicing implies include_data

    async def test_invalid_slicing(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.get_layer("img", slicing="bad")
        assert "slice_error" in res

    async def test_points_data(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_points(np.array([[1.0, 2.0], [3.0, 4.0]]), name="pts")
        res = await s.get_layer("pts", include_data=True)
        assert res["coordinates"] == [[1.0, 2.0], [3.0, 4.0]]
        assert "statistics" in res

    async def test_large_data_stores_output(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((100, 100), dtype=np.uint8), name="big")
        res = await s.get_layer("big", slicing=":50, :50", max_elements=10)
        assert "output_id" in res
        assert "message" in res

    async def test_labels_statistics(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_labels(np.array([[0, 1], [2, 3]], dtype=np.int32), name="seg")
        res = await s.get_layer("seg", include_data=True)
        assert res["data_dtype"] == "int32"
        assert "statistics" in res

    async def test_max_elements_minus_one_means_unlimited(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_points(np.random.rand(50, 2), name="pts")
        res = await s.get_layer("pts", include_data=True, max_elements=-1)
        assert "coordinates" in res  # inline, not output_id
        assert len(res["coordinates"]) == 50


# ── add_layer ──────────────────────────────────────────────────────────────


class TestAddLayer:
    # -- per-type happy paths --

    async def test_image_from_path(self, make_napari_viewer, tmp_path):
        _viewer(make_napari_viewer)
        p = tmp_path / "img.tif"
        iio.imwrite(p, np.zeros((8, 8), dtype=np.uint8))
        res = await s.add_layer("image", path=str(p), name="img", colormap="magma")
        assert res["status"] == "ok"
        assert res["name"] == "img"
        assert res["shape"] == [8, 8]

    async def test_image_from_data_var(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        await s.execute_code("arr = np.zeros((4, 4), dtype=np.uint8)")
        res = await s.add_layer("image", data_var="arr")
        assert res["status"] == "ok"
        assert res["name"] == "arr"

    async def test_labels_from_path(self, make_napari_viewer, tmp_path):
        _viewer(make_napari_viewer)
        p = tmp_path / "lbl.tif"
        iio.imwrite(p, np.array([[0, 1], [2, 0]], dtype=np.uint8))
        res = await s.add_layer("labels", path=str(p), name="lbl")
        assert res["status"] == "ok" and res["shape"] == [2, 2]

    async def test_labels_from_data_var(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        await s.execute_code("lbl = np.array([[0,1],[2,0]], dtype=np.int32)")
        res = await s.add_layer("labels", data_var="lbl")
        assert res["status"] == "ok"

    async def test_points_inline(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.add_layer("points", data=[[1, 2], [3, 4]], name="pts", size=5)
        assert res["status"] == "ok" and res["n_points"] == 2

    async def test_shapes_inline(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        rect = [[0, 0], [0, 10], [10, 10], [10, 0]]
        res = await s.add_layer("shapes", data=[rect], name="r", edge_color="red")
        assert res["status"] == "ok" and res["nshapes"] == 1

    async def test_vectors_inline(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.add_layer("vectors", data=[[[0, 0], [1, 1]]], name="v")
        assert res["status"] == "ok" and res["n_vectors"] == 1

    async def test_tracks_inline(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        data = [[0, 0, 10, 10], [0, 1, 11, 11], [1, 0, 20, 20], [1, 1, 21, 21]]
        res = await s.add_layer("tracks", data=data, name="t")
        assert res["status"] == "ok" and res["n_tracks"] == 2

    async def test_surface_from_data_var(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        await s.execute_code(
            "verts = np.array([[0,0,0],[1,0,0],[0,1,0]])\n"
            "faces = np.array([[0,1,2]])\n"
            "surf = (verts, faces)"
        )
        res = await s.add_layer("surface", data_var="surf", name="s")
        assert res["status"] == "ok"
        assert res["n_vertices"] == 3 and res["n_faces"] == 1

    # -- type normalization --

    async def test_singular_plural_case(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.add_layer("point", data=[[1, 2]]))["status"] == "ok"
        assert (await s.add_layer("Points", data=[[3, 4]]))["status"] == "ok"
        assert (await s.add_layer("IMAGE", data_var=None))["status"] == "error"

    async def test_whitespace_in_type(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.add_layer(" image ", data_var=None))[
            "status"
        ] == "error"  # no data, but type accepted
        # With data it works
        await s.execute_code("ws_img = np.zeros((3,3), dtype=np.uint8)")
        assert (await s.add_layer("  points  ", data=[[1, 2]]))["status"] == "ok"

    # -- error paths --

    async def test_unknown_type(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.add_layer("bogus", data=[[1]])
        assert res["status"] == "error" and "Unknown" in res["message"]

    async def test_no_data_source(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.add_layer("image"))["status"] == "error"
        assert (await s.add_layer("points"))["status"] == "error"
        assert (await s.add_layer("surface"))["status"] == "error"

    async def test_data_var_not_found(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.add_layer("image", data_var="nope")
        assert res["status"] == "error" and "not found" in res["message"]

    async def test_bad_image_path(self, make_napari_viewer, tmp_path):
        _viewer(make_napari_viewer)
        bad = tmp_path / "bad.tif"
        bad.write_text("not an image")
        res = await s.add_layer("image", path=str(bad))
        assert res["status"] == "error"

    async def test_bad_labels_path(self, make_napari_viewer, tmp_path):
        _viewer(make_napari_viewer)
        bad = tmp_path / "bad.txt"
        bad.write_text("not an image")
        res = await s.add_layer("labels", path=str(bad))
        assert res["status"] == "error" and "Failed to add" in res["message"]

    async def test_path_unsupported_for_non_image_type(
        self, make_napari_viewer, tmp_path
    ):
        _viewer(make_napari_viewer)
        p = tmp_path / "x.tif"
        iio.imwrite(p, np.zeros((5, 5), dtype=np.uint8))
        res = await s.add_layer("points", path=str(p))
        assert res["status"] == "error" and "only supported" in res["message"]


# ── remove_layer ───────────────────────────────────────────────────────────


class TestRemoveLayer:
    async def test_remove_existing(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="x")
        assert (await s.remove_layer("x"))["status"] == "removed"
        assert len(v.layers) == 0

    async def test_remove_not_found(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.remove_layer("nope"))["status"] == "not_found"


# ── set_layer_properties ──────────────────────────────────────────────────


class TestSetLayerProperties:
    async def test_all_properties(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties(
            "img",
            visible=False,
            opacity=0.3,
            colormap="magma",
            blending="additive",
            contrast_limits=[10, 200],
            gamma=2.0,
        )
        assert res["status"] == "ok"
        assert v.layers["img"].visible is False
        assert v.layers["img"].opacity == pytest.approx(0.3)
        assert v.layers["img"].gamma == pytest.approx(2.0)

    async def test_rename(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="old")
        res = await s.set_layer_properties("old", new_name="new")
        assert res["name"] == "new"
        assert "new" in v.layers

    async def test_active(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="a")
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="b")
        await s.set_layer_properties("b", active=True)
        assert v.layers["b"] in v.layers.selection

    async def test_not_found(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.set_layer_properties("nope", visible=False))[
            "status"
        ] == "not_found"

    async def test_malformed_contrast_limits(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        # Too short — now returns error
        assert (await s.set_layer_properties("img", contrast_limits=[1]))[
            "status"
        ] == "error"
        # Non-numeric — returns error
        assert (await s.set_layer_properties("img", contrast_limits=["a", "b"]))[
            "status"
        ] == "error"

    async def test_opacity_out_of_range(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties("img", opacity=-0.5)
        assert res["status"] == "error" and "opacity" in res["message"]
        res = await s.set_layer_properties("img", opacity=5.0)
        assert res["status"] == "error" and "opacity" in res["message"]

    async def test_gamma_zero(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties("img", gamma=0)
        assert res["status"] == "error" and "gamma" in res["message"]

    async def test_invalid_colormap(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties("img", colormap="nonexistent_xyz")
        assert res["status"] == "error" and "colormap" in res["message"].lower()

    async def test_invalid_blending(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties("img", blending="invalid_blend")
        assert res["status"] == "error" and "blending" in res["message"].lower()


# ── reorder_layer ─────────────────────────────────────────────────────────


class TestReorderLayer:
    async def test_by_index(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        for n in ("a", "b", "c"):
            v.add_points(np.array([[0, 0]]), name=n)
        res = await s.reorder_layer("c", index=0)
        assert res["status"] == "ok" and res["index"] == 0

    async def test_before_after(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        for n in ("a", "b", "c"):
            v.add_points(np.array([[0, 0]]), name=n)
        assert (await s.reorder_layer("a", after="b"))["status"] == "ok"
        assert (await s.reorder_layer("a", before="c"))["status"] == "ok"

    async def test_not_found(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.reorder_layer("nope", index=0))["status"] == "not_found"

    async def test_no_target(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_points(np.array([[0, 0]]), name="a")
        res = await s.reorder_layer("a")
        assert res["status"] == "error" and "exactly one" in res["message"]

    async def test_multiple_targets(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_points(np.array([[0, 0]]), name="a")
        v.add_points(np.array([[0, 0]]), name="b")
        res = await s.reorder_layer("a", index=0, before="b")
        assert res["status"] == "error"

    async def test_before_not_found(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_points(np.array([[0, 0]]), name="a")
        assert (await s.reorder_layer("a", before="nope"))["status"] == "not_found"


# ── apply_to_layers ───────────────────────────────────────────────────────


class TestApplyToLayers:
    async def test_by_type(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img1")
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img2")
        v.add_points(np.array([[1, 1]]), name="pts")
        res = await s.apply_to_layers(
            filter_type="Image", properties={"visible": False}
        )
        assert res["count"] == 2
        assert v.layers["img1"].visible is False
        assert v.layers["pts"].visible is True

    async def test_by_pattern(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="seg_a")
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="raw")
        res = await s.apply_to_layers(
            filter_pattern="seg_*", properties={"opacity": 0.5}
        )
        assert res["count"] == 1
        assert v.layers["seg_a"].opacity == pytest.approx(0.5)
        assert v.layers["raw"].opacity == pytest.approx(1.0)

    async def test_no_match(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.apply_to_layers(
            filter_type="Labels", properties={"visible": False}
        )
        assert res["count"] == 0

    async def test_no_properties(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.apply_to_layers(filter_type="Image"))["status"] == "error"

    async def test_colormap_on_labels_no_crash(self, make_napari_viewer):
        """Setting colormap='viridis' on Labels should not crash with raw KeyError."""
        v = _viewer(make_napari_viewer)
        v.add_labels(np.array([[0, 1], [2, 0]], dtype=np.int32), name="seg")
        # This used to raise KeyError: 'colors'
        res = await s.apply_to_layers(
            filter_type="Labels", properties={"colormap": "viridis"}
        )
        # Should either succeed or report count (error is swallowed per-layer)
        assert res["status"] == "ok"

    async def test_invalid_opacity_no_crash(self, make_napari_viewer):
        """Out-of-range opacity on batch op should not crash."""
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.apply_to_layers(filter_type="Image", properties={"opacity": -5.0})
        assert res["status"] == "ok"  # -5 skipped silently, layer matched


# ── configure_viewer ──────────────────────────────────────────────────────


class TestConfigureViewer:
    async def test_camera(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.configure_viewer(
            center=[10, 10], zoom=2.0, angles=[45.0, 0.0, 0.0]
        )
        assert res["status"] == "ok"
        assert res["zoom"] == pytest.approx(2.0)
        assert isinstance(res["angles"], list)

    async def test_reset_view(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.configure_viewer(reset_view=True)
        assert res["status"] == "ok"

    async def test_ndisplay(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.configure_viewer(ndisplay=3)
        assert res["ndisplay"] == 3

    async def test_dims(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10, 10)))
        res = await s.configure_viewer(dims_axis=0, dims_value=5)
        assert res["value"] == 5

    async def test_dims_clamped(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10, 10)))
        res = await s.configure_viewer(dims_axis=0, dims_value=99999)
        assert res["value"] == 9 and "warning" in res

    async def test_dims_negative_clamps_to_zero(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10, 10)))
        res = await s.configure_viewer(dims_axis=0, dims_value=-5)
        assert res["value"] == 0 and "warning" in res

    async def test_grid(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.configure_viewer(grid=True))["grid"] is True
        assert (await s.configure_viewer(grid=False))["grid"] is False

    async def test_combined(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.configure_viewer(zoom=1.5, ndisplay=2, grid=True)
        assert res["zoom"] == pytest.approx(1.5)
        assert res["ndisplay"] == 2
        assert res["grid"] is True

    # -- validation --

    async def test_zoom_zero(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.configure_viewer(zoom=0)
        assert res["status"] == "error" and "zoom" in res["message"]

    async def test_zoom_negative(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.configure_viewer(zoom=-1))["status"] == "error"

    async def test_zoom_string_zero(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.configure_viewer(zoom="0"))["status"] == "error"

    async def test_zoom_validation_no_mutation(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        await s.configure_viewer(center=[0, 0], zoom=1.0)
        original = list(s._state.viewer.camera.center)
        await s.configure_viewer(center=[999, 999], zoom=0)
        assert list(s._state.viewer.camera.center) == original

    async def test_ndisplay_invalid(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        assert (await s.configure_viewer(ndisplay=5))["status"] == "error"
        assert (await s.configure_viewer(ndisplay=0))["status"] == "error"

    async def test_dims_axis_out_of_range(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10, 10)))
        assert (await s.configure_viewer(dims_axis=99, dims_value=0))[
            "status"
        ] == "error"

    async def test_dims_axis_negative(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10, 10)))
        assert (await s.configure_viewer(dims_axis=-1, dims_value=0))[
            "status"
        ] == "error"

    async def test_dims_axis_without_value(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10, 10)))
        res = await s.configure_viewer(dims_axis=0)
        assert res["status"] == "error" and "together" in res["message"]

    async def test_dims_value_without_axis(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10, 10)))
        res = await s.configure_viewer(dims_value=5)
        assert res["status"] == "error" and "together" in res["message"]


# ── save_layer_data ───────────────────────────────────────────────────────


class TestSaveLayerData:
    async def test_npy(self, make_napari_viewer, tmp_path):
        v = _viewer(make_napari_viewer)
        v.add_image(np.ones((5, 5), dtype=np.uint8) * 42, name="img")
        out = tmp_path / "img.npy"
        res = await s.save_layer_data("img", str(out))
        assert res["status"] == "ok" and res["format"] == "npy"
        assert np.load(str(out))[0, 0] == 42

    async def test_tiff(self, make_napari_viewer, tmp_path):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10), dtype=np.uint8), name="img")
        res = await s.save_layer_data("img", str(tmp_path / "img.tiff"))
        assert res["status"] == "ok" and Path(res["path"]).exists()

    async def test_csv_points(self, make_napari_viewer, tmp_path):
        v = _viewer(make_napari_viewer)
        v.add_points(np.array([[1.0, 2.0], [3.0, 4.0]]), name="pts")
        out = tmp_path / "pts.csv"
        res = await s.save_layer_data("pts", str(out))
        assert res["status"] == "ok"
        # Verify header row
        lines = out.read_text().strip().splitlines()
        assert lines[0] == "axis-0,axis-1"
        # Data still loads correctly (skiprows=1 for header)
        loaded = np.loadtxt(str(out), delimiter=",", skiprows=1)
        assert loaded.shape == (2, 2)

    async def test_format_override(self, make_napari_viewer, tmp_path):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        out = tmp_path / "img.dat"  # unusual extension
        res = await s.save_layer_data("img", str(out), format="npy")
        assert res["status"] == "ok"

    async def test_not_found(self, make_napari_viewer, tmp_path):
        _viewer(make_napari_viewer)
        assert (await s.save_layer_data("nope", str(tmp_path / "x.npy")))[
            "status"
        ] == "not_found"


# ── screenshot ─────────────────────────────────────────────────────────────


class TestScreenshot:
    async def test_returns_image_content(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10), dtype=np.uint8))
        res = await s.screenshot()
        assert hasattr(res, "mimeType")  # ImageContent
        assert str(res.mimeType).lower() in ("png", "image/png")

    async def test_save_to_file(self, make_napari_viewer, tmp_path):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((10, 10), dtype=np.uint8))
        out = tmp_path / "shot.png"
        res = await s.screenshot(save_path=str(out))
        assert res["status"] == "ok"
        assert Path(res["path"]).exists()
        assert res["size"][0] > 0

    async def test_timelapse_requires_both(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.screenshot(axis=0)
        assert res["status"] == "error" and "slice_range" in res["message"]
        res = await s.screenshot(slice_range=":")
        assert res["status"] == "error" and "axis" in res["message"]

    async def test_proxy(self):
        s._state.mode = StartupMode.AUTO_DETECT
        sentinel = {"type": "image", "data": "x"}
        with patch.object(
            s._state, "proxy_to_external", new_callable=AsyncMock, return_value=sentinel
        ):
            assert (await s.screenshot()) is sentinel

    async def test_inline_auto_downscale(self, make_napari_viewer):
        """Inline screenshots are auto-downscaled to stay under ~200KB base64."""
        import base64

        v = _viewer(make_napari_viewer)
        # Large image that would produce a big screenshot
        v.add_image(np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8))
        res = await s.screenshot()
        assert hasattr(res, "data")
        raw = base64.b64decode(res.data)
        # Should be under 200KB after auto-downscale
        assert len(raw) <= 200_000

    async def test_different_dtypes(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = (np.random.rand(20, 20, 3) * 255).astype(np.uint8)
            iio.imwrite(f.name, img)
            await s.add_layer("image", path=f.name, name="test_float")
        res = await s.screenshot()
        assert hasattr(res, "data")


# ── execute_code ──────────────────────────────────────────────────────────


class TestExecuteCode:
    async def test_expression(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.execute_code("1 + 2")
        assert res["status"] == "ok" and res["result_repr"] == "3"

    async def test_namespace_persistence(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        await s.execute_code("x = 42")
        res = await s.execute_code("x * 2")
        assert res["result_repr"] == "84"

    async def test_viewer_available(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.execute_code(
            "viewer.add_image(np.ones((5,5)), name='gen')\nlen(viewer.layers)"
        )
        assert res["status"] == "ok" and res["result_repr"] == "1"

    async def test_syntax_error(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.execute_code("invalid syntax !!!")
        assert res["status"] == "error" and res["stderr"]

    async def test_runtime_error(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.execute_code("raise ValueError('boom')")
        assert res["status"] == "error" and "boom" in res["stderr"]

    async def test_stdout_stderr(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.execute_code(
            "import sys; print('out'); print('err', file=sys.stderr)"
        )
        assert "out" in res["stdout"] and "err" in res["stderr"]

    async def test_truncation(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.execute_code("for i in range(100): print(i)", line_limit=5)
        assert res.get("truncated") is True
        assert "output_id" in res

    async def test_unlimited_output(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.execute_code("print('hello')", line_limit=-1)
        assert "warning" in res and "large number of tokens" in res["warning"]

    async def test_exception_handling_in_code(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.execute_code(
            "try:\n x=1/0\nexcept ZeroDivisionError:\n result='caught'\nresult"
        )
        assert res["status"] == "ok" and "caught" in res["result_repr"]


# ── Bug fix regression tests ──────────────────────────────────────────────


class TestBugFixRegressions:
    """Tests guarding specific bug fixes identified in test rounds."""

    # Bug 5: contrast_limits invalid shapes
    async def test_contrast_limits_empty_list(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties("img", contrast_limits=[])
        assert res["status"] == "error"
        assert "contrast_limits" in res["message"]

    async def test_contrast_limits_single_value(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties("img", contrast_limits=[100])
        assert res["status"] == "error"

    async def test_contrast_limits_three_values(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties("img", contrast_limits=[10, 50, 200])
        assert res["status"] == "error"

    async def test_contrast_limits_valid(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.set_layer_properties("img", contrast_limits=[0, 100])
        assert res["status"] == "ok"

    # Bug 8: data + data_var conflict
    async def test_data_and_data_var_conflict(self, make_napari_viewer):
        _viewer(make_napari_viewer)
        res = await s.add_layer("image", data=[[1, 2], [3, 4]], data_var="x")
        assert res["status"] == "error"
        assert (
            "only ONE" in res["message"].upper() or "only one" in res["message"].lower()
        )

    async def test_path_and_data_conflict(self, make_napari_viewer, tmp_path):
        _viewer(make_napari_viewer)
        res = await s.add_layer("image", path=str(tmp_path / "img.tif"), data=[[1, 2]])
        assert res["status"] == "error"

    # Bug 10: unknown extension
    async def test_save_unknown_extension(self, make_napari_viewer, tmp_path):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.save_layer_data("img", str(tmp_path / "out.xyz"))
        assert res["status"] == "error"
        assert "Unsupported" in res["message"]

    # Bug 11: format/type mismatch
    async def test_save_points_as_tiff(self, make_napari_viewer, tmp_path):
        v = _viewer(make_napari_viewer)
        v.add_points(np.array([[0.0, 0.0], [1.0, 1.0]]), name="pts")
        res = await s.save_layer_data("pts", str(tmp_path / "pts.tiff"))
        assert res["status"] == "error"
        assert "Image/Labels" in res["message"]

    async def test_save_image_as_csv(self, make_napari_viewer, tmp_path):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.save_layer_data("img", str(tmp_path / "img.csv"))
        assert res["status"] == "error"
        assert "Points/Tracks/Vectors" in res["message"]

    # Bug 12: unknown property keys
    async def test_apply_unknown_properties(self, make_napari_viewer):
        v = _viewer(make_napari_viewer)
        v.add_image(np.zeros((5, 5), dtype=np.uint8), name="img")
        res = await s.apply_to_layers(
            properties={"visible": True, "nonexistent_key": 42}
        )
        assert res["status"] == "ok"
        assert "unknown_properties" in res
        assert "nonexistent_key" in res["unknown_properties"]

    # Bug 14: nonexistent file path
    async def test_add_layer_nonexistent_path(self, make_napari_viewer, tmp_path):
        _viewer(make_napari_viewer)
        res = await s.add_layer("image", path=str(tmp_path / "does_not_exist.tif"))
        assert res["status"] == "error"
        assert "not found" in res["message"].lower()

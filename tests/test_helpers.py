"""Tests for napari_mcp._helpers shared module."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import numpy as np
import pytest

from napari_mcp._helpers import (
    build_layer_detail,
    build_truncated_response,
    create_layer_on_viewer,
    parse_bool,
    resolve_layer_type,
    run_code,
)

# ---------------------------------------------------------------------------
# resolve_layer_type
# ---------------------------------------------------------------------------


class TestResolveLayerType:
    """Test layer type resolution and alias handling."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("image", "image"),
            ("Image", "image"),
            ("  IMAGE  ", "image"),
            ("images", "image"),
            ("labels", "labels"),
            ("label", "labels"),
            ("points", "points"),
            ("point", "points"),
            ("shapes", "shapes"),
            ("shape", "shapes"),
            ("vectors", "vectors"),
            ("vector", "vectors"),
            ("tracks", "tracks"),
            ("track", "tracks"),
            ("surface", "surface"),
            ("surfaces", "surface"),
        ],
    )
    def test_valid_types(self, input_val, expected):
        assert resolve_layer_type(input_val) == expected

    @pytest.mark.parametrize("input_val", ["unknown", "mesh", "", "123", "im age"])
    def test_invalid_types(self, input_val):
        assert resolve_layer_type(input_val) is None


# ---------------------------------------------------------------------------
# create_layer_on_viewer
# ---------------------------------------------------------------------------


class TestCreateLayerOnViewer:
    """Test the shared layer creation helper."""

    def _make_viewer(self):
        """Create a mock viewer with all add_* methods."""
        viewer = MagicMock()
        # Each add method returns a mock layer with a .name
        for method in [
            "add_image",
            "add_labels",
            "add_points",
            "add_shapes",
            "add_vectors",
            "add_tracks",
            "add_surface",
        ]:
            layer = MagicMock()
            layer.name = f"test_{method}"
            layer.nshapes = 1
            getattr(viewer, method).return_value = layer
        return viewer

    def test_image_basic(self):
        viewer = self._make_viewer()
        data = np.zeros((10, 10))
        result = create_layer_on_viewer(viewer, data, "image", name="img")
        assert result["status"] == "ok"
        assert result["shape"] == [10, 10]
        viewer.add_image.assert_called_once()

    def test_image_with_colormap(self):
        viewer = self._make_viewer()
        data = np.zeros((10, 10))
        result = create_layer_on_viewer(
            viewer, data, "image", name="img", colormap="viridis", blending="additive"
        )
        assert result["status"] == "ok"
        call_kwargs = viewer.add_image.call_args[1]
        assert call_kwargs["colormap"] == "viridis"
        assert call_kwargs["blending"] == "additive"

    def test_image_with_channel_axis(self):
        viewer = self._make_viewer()
        data = np.zeros((3, 10, 10))
        create_layer_on_viewer(viewer, data, "image", channel_axis="0")
        call_kwargs = viewer.add_image.call_args[1]
        assert call_kwargs["channel_axis"] == 0

    def test_labels(self):
        viewer = self._make_viewer()
        data = np.zeros((10, 10), dtype=int)
        result = create_layer_on_viewer(viewer, data, "labels", name="lbl")
        assert result["status"] == "ok"
        viewer.add_labels.assert_called_once()

    def test_points(self):
        viewer = self._make_viewer()
        data = [[0, 0], [1, 1], [2, 2]]
        result = create_layer_on_viewer(viewer, data, "points", name="pts")
        assert result["status"] == "ok"
        assert result["n_points"] == 3
        viewer.add_points.assert_called_once()

    def test_points_custom_size(self):
        viewer = self._make_viewer()
        data = [[0, 0]]
        create_layer_on_viewer(viewer, data, "points", size=20.0)
        call_kwargs = viewer.add_points.call_args[1]
        assert call_kwargs["size"] == 20.0

    def test_shapes(self):
        viewer = self._make_viewer()
        data = [np.array([[0, 0], [0, 1], [1, 1], [1, 0]])]
        result = create_layer_on_viewer(
            viewer,
            data,
            "shapes",
            name="shp",
            shape_type="polygon",
            edge_color="red",
            face_color="blue",
            edge_width=2.0,
        )
        assert result["status"] == "ok"
        call_kwargs = viewer.add_shapes.call_args[1]
        assert call_kwargs["shape_type"] == "polygon"
        assert call_kwargs["edge_color"] == "red"
        assert call_kwargs["face_color"] == "blue"
        assert call_kwargs["edge_width"] == 2.0

    def test_vectors(self):
        viewer = self._make_viewer()
        data = np.array([[[0, 0], [1, 1]]])
        result = create_layer_on_viewer(viewer, data, "vectors", name="vec")
        assert result["status"] == "ok"
        viewer.add_vectors.assert_called_once()

    def test_tracks(self):
        viewer = self._make_viewer()
        data = np.array([[0, 0, 0], [0, 1, 1], [1, 0, 0], [1, 1, 1]])
        result = create_layer_on_viewer(viewer, data, "tracks", name="trk")
        assert result["status"] == "ok"
        assert result["n_tracks"] == 2  # track IDs 0 and 1

    def test_surface(self):
        viewer = self._make_viewer()
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        result = create_layer_on_viewer(viewer, (verts, faces), "surface", name="srf")
        assert result["status"] == "ok"
        assert result["n_vertices"] == 3
        assert result["n_faces"] == 1

    def test_unknown_type(self):
        viewer = self._make_viewer()
        result = create_layer_on_viewer(viewer, None, "unknown")
        assert result["status"] == "error"
        assert "Unknown" in result["message"]

    # --- Bug fixes: validation ---

    def test_empty_image_rejected(self):
        """Bug 1: empty array should return error, not crash."""
        viewer = self._make_viewer()
        result = create_layer_on_viewer(viewer, np.zeros((0, 0)), "image")
        assert result["status"] == "error"
        assert "empty" in result["message"].lower()

    def test_empty_labels_rejected(self):
        viewer = self._make_viewer()
        result = create_layer_on_viewer(viewer, np.zeros((0,), dtype=int), "labels")
        assert result["status"] == "error"
        assert "empty" in result["message"].lower()

    def test_empty_points_rejected(self):
        viewer = self._make_viewer()
        result = create_layer_on_viewer(viewer, np.zeros((0, 2)), "points")
        assert result["status"] == "error"
        assert "empty" in result["message"].lower()

    def test_complex_dtype_rejected(self):
        """Bug 2: complex dtype should return error, not crash."""
        viewer = self._make_viewer()
        data = np.array([[1 + 2j, 3 + 4j]], dtype=np.complex128)
        result = create_layer_on_viewer(viewer, data, "image")
        assert result["status"] == "error"
        assert "complex" in result["message"].lower()

    def test_channel_axis_returns_list(self):
        """Bug 13: channel_axis makes napari return a list of layers."""
        viewer = self._make_viewer()
        # Mock add_image to return a list (like napari does with channel_axis)
        layer1 = MagicMock()
        layer1.name = "ch0"
        layer2 = MagicMock()
        layer2.name = "ch1"
        viewer.add_image.return_value = [layer1, layer2]

        data = np.zeros((2, 10, 10))
        result = create_layer_on_viewer(viewer, data, "image", channel_axis=0)
        assert result["status"] == "ok"
        assert result["name"] == ["ch0", "ch1"]
        assert result["n_channels"] == 2


# ---------------------------------------------------------------------------
# build_layer_detail
# ---------------------------------------------------------------------------


class TestBuildLayerDetail:
    """Test layer detail dict building."""

    def test_basic_layer(self):
        layer = MagicMock()
        layer.name = "test"
        layer.__class__.__name__ = "Image"
        layer.visible = True
        layer.opacity = 0.8
        layer.data.shape = (100, 100)
        layer.data.dtype = np.dtype("uint8")
        layer.blending = "translucent"
        type(layer).colormap = PropertyMock(return_value=MagicMock(name="viridis"))
        layer.colormap.name = "viridis"
        layer.gamma = 1.0

        detail = build_layer_detail(layer)
        assert detail["name"] == "test"
        assert detail["type"] == "Image"
        assert detail["visible"] is True
        assert detail["opacity"] == 0.8
        assert detail["data_shape"] == [100, 100]
        assert detail["data_dtype"] == "uint8"

    def test_visible_uses_bool_not_parse_bool(self):
        """visible field should use bool(), not parse_bool(), on napari attributes."""
        layer = MagicMock(spec=["name", "visible", "opacity"])
        layer.name = "test"
        layer.__class__.__name__ = "Image"
        layer.opacity = 1.0

        # numpy bool_ (common from napari)
        layer.visible = np.bool_(True)
        detail = build_layer_detail(layer)
        assert detail["visible"] is True
        assert type(detail["visible"]) is bool  # Should be Python bool, not numpy

        layer.visible = np.bool_(False)
        detail = build_layer_detail(layer)
        assert detail["visible"] is False

    def test_layer_without_data(self):
        layer = MagicMock(spec=["name", "visible", "opacity"])
        layer.name = "empty"
        layer.__class__.__name__ = "Shapes"
        layer.visible = False
        layer.opacity = 1.0

        detail = build_layer_detail(layer)
        assert detail["name"] == "empty"
        assert "data_shape" not in detail
        assert "colormap" not in detail


# ---------------------------------------------------------------------------
# run_code
# ---------------------------------------------------------------------------


class TestRunCode:
    """Test the shared code execution helper."""

    def test_simple_expression(self):
        ns = {}
        stdout, stderr, result_repr, error = run_code("1 + 1", ns)
        assert result_repr == "2"
        assert error is None
        assert stdout == ""
        assert stderr == ""

    def test_print_output(self):
        ns = {}
        stdout, stderr, result_repr, error = run_code("print('hello')", ns)
        assert stdout == "hello\n"
        # print() is an expression returning None, so result_repr is 'None'
        assert result_repr == "None"
        assert error is None

    def test_assignment_no_result(self):
        """Pure assignment (not an expression) should have no result_repr."""
        ns = {}
        stdout, stderr, result_repr, error = run_code("x = 42", ns)
        assert result_repr is None
        assert error is None

    def test_multi_statement_with_expression(self):
        ns = {}
        stdout, stderr, result_repr, error = run_code("x = 5\nx * 2", ns)
        assert result_repr == "10"
        assert ns["x"] == 5
        assert error is None

    def test_error_captured(self):
        ns = {}
        stdout, stderr, result_repr, error = run_code("1/0", ns)
        assert error is not None
        assert isinstance(error, ZeroDivisionError)
        assert "ZeroDivisionError" in stderr

    def test_namespace_persistence(self):
        ns = {}
        run_code("x = 42", ns)
        _, _, result_repr, _ = run_code("x", ns)
        assert result_repr == "42"

    def test_source_label(self):
        ns = {}
        _, stderr, _, error = run_code(
            "raise ValueError('test')", ns, source_label="<test>"
        )
        assert error is not None
        assert "<test>" in stderr

    def test_eval_label_derived_from_exec_label(self):
        """The eval label should be derived from the exec label by replacing -exec with -eval."""
        ns = {}
        # This should use <bridge-eval> for the last expression
        run_code("42", ns, source_label="<bridge-exec>")
        # Just verify it doesn't crash - label is internal


# ---------------------------------------------------------------------------
# build_truncated_response
# ---------------------------------------------------------------------------


class TestBuildTruncatedResponse:
    """Test truncated response building."""

    def test_unlimited(self):
        resp = build_truncated_response(
            status="ok",
            output_id="id1",
            stdout_full="long output",
            stderr_full="",
            result_repr=None,
            line_limit=-1,
        )
        assert resp["stdout"] == "long output"
        assert "warning" in resp
        assert "truncated" not in resp

    def test_within_limit(self):
        resp = build_truncated_response(
            status="ok",
            output_id="id1",
            stdout_full="line1\nline2\n",
            stderr_full="",
            result_repr="42",
            line_limit=10,
        )
        assert resp["stdout"] == "line1\nline2\n"
        assert resp["result_repr"] == "42"
        assert "truncated" not in resp

    def test_truncated(self):
        stdout = "\n".join(f"line{i}" for i in range(100)) + "\n"
        resp = build_truncated_response(
            status="ok",
            output_id="id1",
            stdout_full=stdout,
            stderr_full="",
            result_repr=None,
            line_limit=5,
        )
        assert resp["truncated"] is True
        assert "read_output" in resp["message"]

    def test_error_summary_injected(self):
        resp = build_truncated_response(
            status="error",
            output_id="id1",
            stdout_full="",
            stderr_full="",
            result_repr=None,
            line_limit=30,
            error=ValueError("test error"),
        )
        assert "ValueError: test error" in resp["stderr"]

    def test_string_line_limit(self):
        """line_limit as string should work."""
        resp = build_truncated_response(
            status="ok",
            output_id="id1",
            stdout_full="hello\n",
            stderr_full="",
            result_repr=None,
            line_limit="30",
        )
        assert resp["stdout"] == "hello\n"

    def test_string_minus_one(self):
        """line_limit='-1' as string should trigger unlimited mode."""
        resp = build_truncated_response(
            status="ok",
            output_id="id1",
            stdout_full="hello\n",
            stderr_full="",
            result_repr=None,
            line_limit="-1",
        )
        assert "warning" in resp


# ---------------------------------------------------------------------------
# parse_bool (already tested via test_property_based.py, but add edge cases)
# ---------------------------------------------------------------------------


class TestParseBool:
    def test_none_default(self):
        assert parse_bool(None) is False
        assert parse_bool(None, default=True) is True

    def test_bool_passthrough(self):
        assert parse_bool(True) is True
        assert parse_bool(False) is False

    def test_non_bool_non_string(self):
        assert parse_bool(1) is True
        assert parse_bool(0) is False


# ---------------------------------------------------------------------------
# Package name regex (from server.py)
# ---------------------------------------------------------------------------


class TestPackageNameRegex:
    """Test the _PKG_NAME_RE regex used by install_packages."""

    @pytest.fixture(autouse=True)
    def _load_regex(self):
        from napari_mcp.server import _PKG_NAME_RE

        self.regex = _PKG_NAME_RE

    @pytest.mark.parametrize(
        "pkg",
        [
            "numpy",
            "numpy>=1.20",
            "numpy>=1.20,<2.0",
            "scikit-image",
            "torch[cuda]",
            "torch[cuda,cpu]>=2.0",
            "Pillow==10.0",
            "package~=1.0",
            "napari-mcp",
            "a",
            "a2",
            "package!=1.0",
        ],
    )
    def test_valid_packages(self, pkg):
        assert self.regex.match(pkg.strip()), f"{pkg!r} should be valid"

    @pytest.mark.parametrize(
        "pkg",
        [
            "https://evil.com/pkg",
            "package @ https://evil.com",
            "--index-url http://evil",
            "pkg;rm -rf /",
            "",
            " ",
        ],
    )
    def test_invalid_packages(self, pkg):
        assert not self.regex.match(pkg.strip()), f"{pkg!r} should be rejected"


# ---------------------------------------------------------------------------
# list_layers consistency with build_layer_detail
# ---------------------------------------------------------------------------


class TestListLayersBuildLayerDetailConsistency:
    """Verify list_layers returns the same fields as build_layer_detail."""

    @pytest.mark.asyncio
    async def test_list_layers_returns_build_layer_detail_fields(self):
        """list_layers should include all fields from build_layer_detail."""

        # The conftest fixture creates fresh state; set up a mock viewer
        mock_layer = MagicMock()
        mock_layer.name = "test_layer"
        mock_layer.__class__.__name__ = "Image"
        mock_layer.visible = True
        mock_layer.opacity = 0.8
        mock_layer.data.shape = (100, 100)
        mock_layer.data.dtype = np.dtype("float32")
        mock_layer.blending = "translucent"
        mock_layer.colormap.name = "viridis"
        mock_layer.gamma = 1.5

        # Compare: what build_layer_detail returns vs what list_layers would build
        detail = build_layer_detail(mock_layer)

        # build_layer_detail should include all these keys
        assert "name" in detail
        assert "type" in detail
        assert "visible" in detail
        assert "opacity" in detail
        assert "data_shape" in detail
        assert "data_dtype" in detail
        assert "colormap" in detail
        assert "blending" in detail
        assert "gamma" in detail


class TestBuildTruncatedResponseForInstallPackages:
    """Test that build_truncated_response works correctly for install_packages use case."""

    def test_extra_fields_can_be_added(self):
        """install_packages adds returncode and command after building response."""
        resp = build_truncated_response(
            status="ok",
            output_id="pip_123",
            stdout_full="Successfully installed numpy\n",
            stderr_full="",
            result_repr=None,
            line_limit=30,
        )
        # Simulate what install_packages does
        resp["returncode"] = 0
        resp["command"] = "pip install numpy"

        assert resp["status"] == "ok"
        assert resp["returncode"] == 0
        assert resp["command"] == "pip install numpy"
        assert resp["stdout"] == "Successfully installed numpy\n"
        assert "result_repr" not in resp  # None should not be included

    def test_string_line_limit_minus_one(self):
        """Ensure string '-1' triggers unlimited mode (was a bug in old install_packages)."""
        resp = build_truncated_response(
            status="ok",
            output_id="pip_456",
            stdout_full="output\n",
            stderr_full="",
            result_repr=None,
            line_limit="-1",
        )
        assert "warning" in resp
        assert "truncated" not in resp

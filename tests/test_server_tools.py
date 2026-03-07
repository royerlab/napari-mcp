"""Tests for individual MCP tool functions exposed by the server.

Canonical home for tool-by-tool unit tests covering edge cases, error paths,
and the AUTO_DETECT proxy fallback logic.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import imageio
import imageio.v3 as iio
import numpy as np
import pytest

from napari_mcp import server as napari_mcp_server
from napari_mcp.state import StartupMode

# ---------------------------------------------------------------------------
# Tool function tests (moved from test_coverage.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_viewer_with_size(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    res = await napari_mcp_server.init_viewer(title="Test", width=640, height=480)
    assert res["status"] == "ok"
    assert res["title"] == "Test"


@pytest.mark.asyncio
async def test_layer_error_cases(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    res = await napari_mcp_server.remove_layer("nonexistent")
    assert res["status"] == "not_found"

    res = await napari_mcp_server.set_layer_properties(
        "nonexistent", new_name="new_name"
    )
    assert res["status"] == "not_found"

    res = await napari_mcp_server.set_layer_properties("nonexistent", visible=False)
    assert res["status"] == "not_found"

    res = await napari_mcp_server.reorder_layer("nonexistent", index=0)
    assert res["status"] == "not_found"

    res = await napari_mcp_server.set_active_layer("nonexistent")
    assert res["status"] == "not_found"


@pytest.mark.asyncio
async def test_reorder_layer_edge_cases(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    await napari_mcp_server.add_points([[1, 1]], name="layer1")
    await napari_mcp_server.add_points([[2, 2]], name="layer2")
    await napari_mcp_server.add_points([[3, 3]], name="layer3")

    # No target specified
    res = await napari_mcp_server.reorder_layer("layer1")
    assert res["status"] == "error"
    assert "exactly one" in res["message"]

    # Multiple targets
    res = await napari_mcp_server.reorder_layer("layer1", index=0, before="layer2")
    assert res["status"] == "error"
    assert "exactly one" in res["message"]

    # Non-existent targets
    res = await napari_mcp_server.reorder_layer("layer1", before="nonexistent")
    assert res["status"] == "not_found"

    res = await napari_mcp_server.reorder_layer("layer1", after="nonexistent")
    assert res["status"] == "not_found"

    # Valid reordering
    res = await napari_mcp_server.reorder_layer("layer1", after="layer2")
    assert res["status"] == "ok"


@pytest.mark.asyncio
async def test_set_layer_properties_comprehensive(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer
    await napari_mcp_server.add_points([[1, 1]], name="test_layer")

    res = await napari_mcp_server.set_layer_properties(
        "test_layer",
        visible=False,
        opacity=0.5,
        colormap="viridis",
        blending="additive",
        contrast_limits=[0.1, 0.9],
        gamma=1.5,
    )
    assert res["status"] == "ok"


@pytest.mark.asyncio
async def test_execute_code_error_cases(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    # Syntax error
    res = await napari_mcp_server.execute_code("invalid python syntax !!!")
    assert res["status"] == "error"
    assert res["stderr"]

    # Runtime error
    res = await napari_mcp_server.execute_code("raise ValueError('test error')")
    assert res["status"] == "error"
    assert "test error" in res["stderr"]

    # stdout/stderr capture
    res = await napari_mcp_server.execute_code(
        "import sys; print('stdout'); print('stderr', file=sys.stderr)"
    )
    assert res["status"] == "ok"
    assert "stdout" in res["stdout"]
    assert "stderr" in res["stderr"]

    # Expression evaluation
    res = await napari_mcp_server.execute_code("x = 42\nx")
    assert res["status"] == "ok"
    assert res.get("result_repr") == "42"


@pytest.mark.asyncio
async def test_screenshot_with_different_dtypes(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        test_image = (np.random.rand(20, 20, 3) * 255).astype(np.uint8)
        imageio.imwrite(f.name, test_image)
        await napari_mcp_server.add_image(path=f.name, name="test_float")

    res = await napari_mcp_server.screenshot()
    assert res.mimeType.lower() in ("png", "image/png")
    assert res.data is not None


@pytest.mark.asyncio
async def test_camera_operations(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer
    await napari_mcp_server.set_ndisplay(2)

    res = await napari_mcp_server.set_camera(zoom=2.5)
    assert res["status"] == "ok"
    assert abs(res["zoom"] - 2.5) < 0.01

    res = await napari_mcp_server.set_camera(
        center=[100, 200], zoom=1.5, angles=[45.0, 0.0, 0.0]
    )
    assert res["status"] == "ok"
    assert res["zoom"] == 1.5
    assert "angles" in res

    res = await napari_mcp_server.set_camera(zoom=3.0)
    assert res["status"] == "ok"
    assert res["zoom"] == 3.0
    assert "angles" in res


@pytest.mark.asyncio
async def test_dims_operations(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    res = await napari_mcp_server.set_ndisplay(3)
    assert res["status"] == "ok"
    assert res["ndisplay"] == 3

    res = await napari_mcp_server.set_dims_current_step(0, 5)
    assert res["status"] == "ok"
    assert res["axis"] == 0
    assert res["value"] == 5


@pytest.mark.asyncio
async def test_grid_operations(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    res = await napari_mcp_server.set_grid(True)
    assert res["status"] == "ok"
    assert res["grid"] is True

    res = await napari_mcp_server.set_grid(False)
    assert res["status"] == "ok"
    assert res["grid"] is False


@pytest.mark.asyncio
async def test_list_layers_with_properties(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    await napari_mcp_server.add_points([[1, 1]], name="test_points")
    await napari_mcp_server.set_layer_properties(
        "test_points", opacity=0.8, visible=False
    )

    layers = await napari_mcp_server.list_layers()
    assert len(layers) >= 1

    points_layer = next(
        (layer for layer in layers if layer["name"] == "test_points"), None
    )
    assert points_layer is not None
    assert points_layer["opacity"] == 0.8
    assert points_layer["visible"] is False


@pytest.mark.asyncio
async def test_image_loading_error(make_napari_viewer, tmp_path: Path):
    bad_file = tmp_path / "bad_image.tif"
    bad_file.write_text("not an image")

    with pytest.raises((ValueError, OSError, RuntimeError)):
        await napari_mcp_server.add_image(str(bad_file))


@pytest.mark.asyncio
async def test_reorder_layer_by_index(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    await napari_mcp_server.add_points([[1, 1]], name="layer_a")
    await napari_mcp_server.add_points([[2, 2]], name="layer_b")
    await napari_mcp_server.add_points([[3, 3]], name="layer_c")

    res = await napari_mcp_server.reorder_layer("layer_c", index=0)
    assert res["status"] == "ok"
    assert res["name"] == "layer_c"
    assert res["index"] == 0


@pytest.mark.asyncio
async def test_add_labels_error_path(make_napari_viewer, tmp_path):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    bad_file = tmp_path / "bad_labels.txt"
    bad_file.write_text("not image data")

    res = await napari_mcp_server.add_labels(str(bad_file))
    assert res["status"] == "error"
    assert "Failed to add labels" in res["message"]


# ---------------------------------------------------------------------------
# Tests moved from test_napari_server_coverage.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complex_execute_code_scenarios(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    code = """
import numpy as np
data = np.ones((5, 5))
viewer.add_image(data, name='generated')
len(viewer.layers)
"""
    result = await napari_mcp_server.execute_code(code)
    assert result["status"] == "ok"
    assert result.get("result_repr") == "1"

    code = """
try:
    x = 1 / 0
except ZeroDivisionError:
    result = "Caught division by zero"
result
"""
    result = await napari_mcp_server.execute_code(code)
    assert result["status"] == "ok"
    assert "Caught division by zero" in result.get("result_repr", "")


@pytest.mark.asyncio
async def test_session_information_with_selected_layers(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        iio.imwrite(f.name, np.zeros((10, 10), dtype=np.uint8))
        await napari_mcp_server.add_image(f.name, name="image1")

    await napari_mcp_server.add_points([[5, 5]], name="points1")
    await napari_mcp_server.set_active_layer("points1")

    result = await napari_mcp_server.session_information()
    assert result["status"] == "ok"
    assert "points1" in result["viewer"]["selected_layers"]


@pytest.mark.asyncio
async def test_close_viewer_multiple_times(make_napari_viewer):
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    result = await napari_mcp_server.close_viewer()
    assert result["status"] == "closed"

    result = await napari_mcp_server.close_viewer()
    assert result["status"] == "no_viewer"


# ---------------------------------------------------------------------------
# NEW: AUTO_DETECT mode fallback tests
# ---------------------------------------------------------------------------


class TestAutoDetectMode:
    """Test AUTO_DETECT proxy fallback paths in server.py."""

    @pytest.mark.asyncio
    async def test_session_information_fallback_on_exception(self, make_napari_viewer):
        """session_information() falls back to local when external raises."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer
        napari_mcp_server._state.mode = StartupMode.AUTO_DETECT

        with patch.object(
            napari_mcp_server._state,
            "external_session_information",
            new_callable=AsyncMock,
            side_effect=ConnectionError("no bridge"),
        ):
            result = await napari_mcp_server.session_information()

        assert result["status"] == "ok"
        assert result["session_type"] == "napari_mcp_standalone_session"

    @pytest.mark.asyncio
    async def test_init_viewer_fallback_on_exception(self, make_napari_viewer):
        """init_viewer() falls back to local when external raises."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer
        napari_mcp_server._state.mode = StartupMode.AUTO_DETECT

        with patch.object(
            napari_mcp_server._state,
            "external_session_information",
            new_callable=AsyncMock,
            side_effect=ConnectionError("no bridge"),
        ):
            result = await napari_mcp_server.init_viewer()

        assert result["status"] == "ok"
        assert result["viewer_type"] == "local"

    @pytest.mark.asyncio
    async def test_list_layers_proxy_returns_list(self):
        """list_layers() returns proxy result directly when it's a list."""
        napari_mcp_server._state.mode = StartupMode.AUTO_DETECT

        mock_layers = [{"name": "img", "type": "Image"}]
        with patch.object(
            napari_mcp_server._state,
            "proxy_to_external",
            new_callable=AsyncMock,
            return_value=mock_layers,
        ):
            result = await napari_mcp_server.list_layers()

        assert result == mock_layers

    @pytest.mark.asyncio
    async def test_list_layers_proxy_returns_dict_with_content(self):
        """list_layers() extracts content from proxy dict response."""
        napari_mcp_server._state.mode = StartupMode.AUTO_DETECT

        inner = [{"name": "img", "type": "Image"}]
        with patch.object(
            napari_mcp_server._state,
            "proxy_to_external",
            new_callable=AsyncMock,
            return_value={"content": inner},
        ):
            result = await napari_mcp_server.list_layers()

        assert result == inner

    @pytest.mark.asyncio
    async def test_list_layers_proxy_returns_dict_with_non_list_content(self):
        """list_layers() returns [] when content key is not a list."""
        napari_mcp_server._state.mode = StartupMode.AUTO_DETECT

        with patch.object(
            napari_mcp_server._state,
            "proxy_to_external",
            new_callable=AsyncMock,
            return_value={"content": "not a list"},
        ):
            result = await napari_mcp_server.list_layers()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_layers_proxy_returns_unexpected_format(self):
        """list_layers() returns [] when proxy gives dict without content key."""
        napari_mcp_server._state.mode = StartupMode.AUTO_DETECT

        with patch.object(
            napari_mcp_server._state,
            "proxy_to_external",
            new_callable=AsyncMock,
            return_value={"error": "something went wrong"},
        ):
            result = await napari_mcp_server.list_layers()

        assert result == []

    @pytest.mark.asyncio
    async def test_screenshot_proxy_returns_result(self):
        """screenshot() returns proxy result directly."""
        napari_mcp_server._state.mode = StartupMode.AUTO_DETECT

        sentinel = {"type": "image", "data": "base64data"}
        with patch.object(
            napari_mcp_server._state,
            "proxy_to_external",
            new_callable=AsyncMock,
            return_value=sentinel,
        ):
            result = await napari_mcp_server.screenshot()

        assert result is sentinel


# ---------------------------------------------------------------------------
# NEW: Invalid input edge cases
# ---------------------------------------------------------------------------


class TestInvalidInputs:
    """Test defensive error handling for malformed inputs."""

    @pytest.mark.asyncio
    async def test_init_viewer_invalid_port(self, make_napari_viewer):
        """init_viewer with port='invalid' logs error and continues."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer

        # Should not crash — logs error and uses existing port
        res = await napari_mcp_server.init_viewer(port="not_a_number")
        assert res["status"] == "ok"

    @pytest.mark.asyncio
    async def test_set_layer_properties_malformed_contrast_limits(
        self, make_napari_viewer
    ):
        """contrast_limits=[1] (too short) is silently suppressed."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer

        img = np.zeros((10, 10), dtype=np.uint8)
        viewer.add_image(img, name="img")

        res = await napari_mcp_server.set_layer_properties("img", contrast_limits=[1])
        assert res["status"] == "ok"

    @pytest.mark.asyncio
    async def test_set_layer_properties_non_numeric_contrast_limits(
        self, make_napari_viewer
    ):
        """contrast_limits=['a', 'b'] is silently suppressed."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer

        img = np.zeros((10, 10), dtype=np.uint8)
        viewer.add_image(img, name="img")

        res = await napari_mcp_server.set_layer_properties(
            "img", contrast_limits=["a", "b"]
        )
        assert res["status"] == "ok"

    @pytest.mark.asyncio
    async def test_execute_code_unlimited_output_path(self, make_napari_viewer):
        """line_limit=-1 returns warning about unlimited output."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer

        res = await napari_mcp_server.execute_code("print('hello')", line_limit=-1)
        assert res["status"] == "ok"
        assert "warning" in res
        assert "large number of tokens" in res["warning"]

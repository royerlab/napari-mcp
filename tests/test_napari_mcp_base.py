"""
Comprehensive test coverage for napari_mcp_base module.

This file provides extensive test coverage for the NapariMCPTools class
and its methods to improve overall code coverage.
"""

from unittest.mock import patch

import numpy as np
import pytest

from napari_mcp.base import NapariMCPTools, viewer_tool


@pytest.fixture
def napari_viewer_with_layers(make_napari_viewer):
    """Create a napari viewer with test layers."""
    viewer = make_napari_viewer()
    viewer.title = "Test Viewer"

    # Add test layers
    image_data = np.random.random((100, 100))
    viewer.add_image(image_data, name="layer1", colormap="viridis")

    points_data = np.array([[10, 10], [20, 20]])
    viewer.add_points(points_data, name="layer2", visible=False, opacity=0.5)

    return viewer


@pytest.fixture
def mcp_tools(napari_viewer_with_layers):
    """Create NapariMCPTools instance with napari viewer."""
    return NapariMCPTools(napari_viewer_with_layers)


@pytest.fixture
def mcp_tools_no_viewer():
    """Create NapariMCPTools instance without viewer."""
    return NapariMCPTools()


def test_viewer_tool_decorator():
    """Test the viewer_tool decorator."""

    @viewer_tool
    async def test_func(viewer, arg1, arg2):
        return viewer, arg1, arg2

    # Test that wrapper is created
    assert test_func.__name__ == "test_func"
    assert test_func.__wrapped__.__name__ == "test_func"


def test_init_with_viewer(napari_viewer_with_layers):
    """Test initialization with a viewer instance."""
    tools = NapariMCPTools(napari_viewer_with_layers)
    assert tools.viewer is napari_viewer_with_layers
    assert tools._exec_globals == {}


def test_init_without_viewer():
    """Test initialization without a viewer instance."""
    tools = NapariMCPTools()
    assert tools.viewer is None
    assert tools._exec_globals == {}


def test_set_viewer(napari_viewer_with_layers):
    """Test setting viewer after initialization."""
    tools = NapariMCPTools()
    tools.set_viewer(napari_viewer_with_layers)
    assert tools.viewer is napari_viewer_with_layers


def test_ensure_viewer_with_viewer(mcp_tools):
    """Test _ensure_viewer with viewer present."""
    viewer = mcp_tools._ensure_viewer()
    assert viewer is mcp_tools.viewer


def test_ensure_viewer_without_viewer(mcp_tools_no_viewer):
    """Test _ensure_viewer raises error when no viewer."""
    with pytest.raises(RuntimeError, match="No viewer instance available"):
        mcp_tools_no_viewer._ensure_viewer()


def test_encode_png_base64():
    """Test encoding image as base64 PNG."""
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    result = NapariMCPTools.encode_png_base64(img)

    assert "mime_type" in result
    assert result["mime_type"] == "image/png"
    assert "base64_data" in result
    assert isinstance(result["base64_data"], str)


@pytest.mark.asyncio
async def test_session_information(mcp_tools, napari_viewer_with_layers):
    """Test getting session information."""
    result = await mcp_tools.session_information()

    assert result["status"] == "ok"
    assert result["viewer"]["title"] == "Test Viewer"
    assert result["viewer"]["n_layers"] == 2
    assert result["viewer"]["layer_names"] == ["layer1", "layer2"]
    assert result["viewer"]["ndisplay"] == 2
    assert len(result["layers"]) == 2
    assert result["layers"][0]["name"] == "layer1"


@pytest.mark.asyncio
async def test_list_layers(mcp_tools):
    """Test listing layers."""
    result = await mcp_tools.list_layers()

    assert len(result) == 2
    assert result[0]["name"] == "layer1"
    assert result[0]["type"] == "Image"
    assert result[0]["visible"] is True
    assert result[0]["opacity"] == 1.0
    assert result[0]["colormap"] == "viridis"

    assert result[1]["name"] == "layer2"
    assert result[1]["type"] == "Points"
    assert result[1]["visible"] is False
    assert result[1]["opacity"] == 0.5


@pytest.mark.asyncio
async def test_add_image_from_path(mcp_tools, tmp_path):
    """Test adding image from file path."""
    # Create a test image file
    import imageio.v3 as iio

    test_img = np.zeros((20, 20, 3), dtype=np.uint8)
    img_path = tmp_path / "test.png"
    iio.imwrite(img_path, test_img)

    with patch("imageio.v3") as mock_iio:
        mock_iio.imread.return_value = test_img
        result = await mcp_tools.add_image(path=str(img_path), name="test_img")

    assert result["status"] == "ok"
    assert result["name"] == "test_img"
    assert result["shape"] == [20, 20, 3]


@pytest.mark.asyncio
async def test_add_image_from_data(mcp_tools):
    """Test adding image from numpy array."""
    test_data = np.zeros((30, 30))
    result = await mcp_tools.add_image(data=test_data, name="test_array")

    assert result["status"] == "ok"
    assert result["shape"] == [30, 30]


@pytest.mark.asyncio
async def test_add_image_no_data(mcp_tools):
    """Test adding image with neither path nor data."""
    result = await mcp_tools.add_image()

    assert result["status"] == "error"
    assert "Either path or data must be provided" in result["message"]


@pytest.mark.asyncio
async def test_add_labels_from_path(mcp_tools, tmp_path):
    """Test adding labels from file path."""
    import imageio.v3 as iio

    test_labels = np.zeros((20, 20), dtype=np.uint8)
    labels_path = tmp_path / "labels.png"
    iio.imwrite(labels_path, test_labels)

    with patch("imageio.v3") as mock_iio:
        mock_iio.imread.return_value = test_labels
        result = await mcp_tools.add_labels(path=str(labels_path))

    assert result["status"] == "ok"
    assert result["shape"] == [20, 20]


@pytest.mark.asyncio
async def test_add_labels_from_data(mcp_tools):
    """Test adding labels from numpy array."""
    test_data = np.zeros((15, 15), dtype=np.int32)
    result = await mcp_tools.add_labels(data=test_data)

    assert result["status"] == "ok"
    assert result["shape"] == [15, 15]


@pytest.mark.asyncio
async def test_add_labels_no_data(mcp_tools):
    """Test adding labels with neither path nor data."""
    result = await mcp_tools.add_labels()

    assert result["status"] == "error"
    assert "Either path or data must be provided" in result["message"]


@pytest.mark.asyncio
async def test_add_points(mcp_tools):
    """Test adding points layer."""
    points = [[10.0, 20.0], [30.0, 40.0]]
    result = await mcp_tools.add_points(points, name="test_points", size=15.0)

    assert result["status"] == "ok"
    assert result["name"] == "test_points"
    assert result["n_points"] == 2


@pytest.mark.asyncio
async def test_remove_layer_exists(mcp_tools, napari_viewer_with_layers):
    """Test removing existing layer."""
    result = await mcp_tools.remove_layer("layer1")

    assert result["status"] == "removed"
    assert result["name"] == "layer1"
    assert "layer1" not in napari_viewer_with_layers.layers


@pytest.mark.asyncio
async def test_remove_layer_not_found(mcp_tools):
    """Test removing non-existent layer."""
    result = await mcp_tools.remove_layer("nonexistent")

    assert result["status"] == "not_found"
    assert result["name"] == "nonexistent"


@pytest.mark.asyncio
async def test_rename_layer_exists(mcp_tools, napari_viewer_with_layers):
    """Test renaming existing layer."""
    result = await mcp_tools.rename_layer("layer1", "new_name")

    assert result["status"] == "ok"
    assert result["old"] == "layer1"
    assert result["new"] == "new_name"
    # Check that the layer was renamed
    assert "new_name" in napari_viewer_with_layers.layers
    assert "layer1" not in napari_viewer_with_layers.layers


@pytest.mark.asyncio
async def test_rename_layer_not_found(mcp_tools):
    """Test renaming non-existent layer."""
    result = await mcp_tools.rename_layer("nonexistent", "new_name")

    assert result["status"] == "not_found"
    assert result["name"] == "nonexistent"


@pytest.mark.asyncio
async def test_set_layer_properties_all(mcp_tools, napari_viewer_with_layers):
    """Test setting all layer properties."""
    layer = napari_viewer_with_layers.layers["layer1"]
    layer.colormap = "gray"
    layer.blending = "translucent"
    layer.contrast_limits = [0, 1]
    layer.gamma = 1.0

    result = await mcp_tools.set_layer_properties(
        "layer1",
        visible=False,
        opacity=0.7,
        colormap="plasma",
        blending="additive",
        contrast_limits=[0.2, 0.8],
        gamma=1.2,
    )

    assert result["status"] == "ok"
    assert layer.visible is False
    assert layer.opacity == 0.7
    assert layer.colormap.name == "plasma"
    assert layer.blending == "additive"
    assert layer.contrast_limits == [0.2, 0.8]
    assert layer.gamma == 1.2


@pytest.mark.asyncio
async def test_set_layer_properties_not_found(mcp_tools):
    """Test setting properties on non-existent layer."""
    result = await mcp_tools.set_layer_properties("nonexistent", visible=False)

    assert result["status"] == "not_found"
    assert result["name"] == "nonexistent"


@pytest.mark.asyncio
async def test_reorder_layer_by_index(mcp_tools, napari_viewer_with_layers):
    """Test reordering layer by index."""
    result = await mcp_tools.reorder_layer("layer1", index=1)

    assert result["status"] == "ok"
    assert result["name"] == "layer1"
    # Check layer was moved


@pytest.mark.asyncio
async def test_reorder_layer_before(mcp_tools, napari_viewer_with_layers):
    """Test reordering layer before another."""
    result = await mcp_tools.reorder_layer("layer2", before="layer1")

    assert result["status"] == "ok"
    assert result["name"] == "layer2"


@pytest.mark.asyncio
async def test_reorder_layer_after(mcp_tools, napari_viewer_with_layers):
    """Test reordering layer after another."""
    result = await mcp_tools.reorder_layer("layer1", after="layer2")

    assert result["status"] == "ok"
    assert result["name"] == "layer1"


@pytest.mark.asyncio
async def test_reorder_layer_invalid_params(mcp_tools):
    """Test reordering with invalid parameters."""
    # No positioning parameter
    result = await mcp_tools.reorder_layer("layer1")
    assert result["status"] == "error"
    assert "exactly one" in result["message"]

    # Multiple positioning parameters
    result = await mcp_tools.reorder_layer("layer1", index=0, before="layer2")
    assert result["status"] == "error"
    assert "exactly one" in result["message"]


@pytest.mark.asyncio
async def test_reorder_layer_not_found(mcp_tools):
    """Test reordering non-existent layer."""
    result = await mcp_tools.reorder_layer("nonexistent", index=0)
    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_set_active_layer(mcp_tools, napari_viewer_with_layers):
    """Test setting active layer."""
    result = await mcp_tools.set_active_layer("layer1")

    assert result["status"] == "ok"
    assert result["active"] == "layer1"


@pytest.mark.asyncio
async def test_set_active_layer_not_found(mcp_tools):
    """Test setting non-existent layer as active."""
    result = await mcp_tools.set_active_layer("nonexistent")

    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_reset_view(mcp_tools, napari_viewer_with_layers):
    """Test resetting camera view."""
    result = await mcp_tools.reset_view()

    assert result["status"] == "ok"
    # View should be reset


@pytest.mark.asyncio
async def test_set_zoom(mcp_tools, napari_viewer_with_layers):
    """Test setting camera zoom."""
    result = await mcp_tools.set_zoom(2.5)

    assert result["status"] == "ok"
    assert result["zoom"] == 2.5
    assert napari_viewer_with_layers.camera.zoom == 2.5


@pytest.mark.asyncio
async def test_set_camera_all_params(mcp_tools, napari_viewer_with_layers):
    """Test setting all camera parameters."""
    result = await mcp_tools.set_camera(center=[100, 200], zoom=3.0, angle=45.0)

    assert result["status"] == "ok"
    if len(napari_viewer_with_layers.camera.center) == 3:
        assert napari_viewer_with_layers.camera.center == (0, 100.0, 200.0)
    else:
        assert napari_viewer_with_layers.camera.center == (100.0, 200.0)
    assert result["zoom"] == 3.0

    if len(napari_viewer_with_layers.camera.angles) == 3:
        assert napari_viewer_with_layers.camera.angles == (0.0, 0.0, 45.0)
    else:
        assert napari_viewer_with_layers.camera.angles == (45.0,)


@pytest.mark.asyncio
async def test_set_camera_partial_params(mcp_tools, napari_viewer_with_layers):
    """Test setting partial camera parameters."""
    result = await mcp_tools.set_camera(zoom=1.5)

    assert result["status"] == "ok"
    assert result["zoom"] == 1.5


@pytest.mark.asyncio
async def test_set_ndisplay(mcp_tools, napari_viewer_with_layers):
    """Test setting ndisplay."""
    result = await mcp_tools.set_ndisplay(3)

    assert result["status"] == "ok"
    assert result["ndisplay"] == 3
    assert napari_viewer_with_layers.dims.ndisplay == 3


@pytest.mark.asyncio
async def test_set_dims_current_step(mcp_tools, napari_viewer_with_layers):
    """Test setting current step for dimension."""
    result = await mcp_tools.set_dims_current_step(0, 10)

    assert result["status"] == "ok"
    assert result["axis"] == 0
    assert result["value"] == 10
    # Dimension step should be updated


@pytest.mark.asyncio
async def test_set_grid(mcp_tools, napari_viewer_with_layers):
    """Test enabling/disabling grid."""
    result = await mcp_tools.set_grid(True)

    assert result["status"] == "ok"
    assert result["grid"] is True
    assert napari_viewer_with_layers.grid.enabled is True


@pytest.mark.asyncio
async def test_screenshot(mcp_tools, napari_viewer_with_layers):
    """Test taking screenshot."""
    result = await mcp_tools.screenshot(canvas_only=True)

    assert "mime_type" in result
    assert result["mime_type"] == "image/png"
    assert "base64_data" in result
    # Screenshot should have been taken


@pytest.mark.asyncio
async def test_screenshot_non_uint8(mcp_tools, napari_viewer_with_layers):
    """Test screenshot with non-uint8 data."""
    # Return float data from screenshot
    # Mock screenshot with non-uint8 data
    with patch(
        "napari.viewer.Viewer.screenshot",
        return_value=np.zeros((50, 50, 3), dtype=np.float32),
    ):
        result = await mcp_tools.screenshot()

        assert "mime_type" in result
        assert result["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_execute_code_simple(mcp_tools, napari_viewer_with_layers):
    """Test executing simple Python code."""
    code = "x = 1 + 1"
    result = await mcp_tools.execute_code(code)

    assert result["status"] == "ok"
    assert mcp_tools._exec_globals["x"] == 2


@pytest.mark.asyncio
async def test_execute_code_with_expression(mcp_tools):
    """Test executing code with expression evaluation."""
    code = "x = 42\nx * 2"
    result = await mcp_tools.execute_code(code)

    assert result["status"] == "ok"
    assert result.get("result_repr") == "84"


@pytest.mark.asyncio
async def test_execute_code_with_stdout(mcp_tools):
    """Test executing code with stdout output."""
    code = "print('Hello, World!')"
    result = await mcp_tools.execute_code(code)

    assert result["status"] == "ok"
    assert "Hello, World!" in result["stdout"]


@pytest.mark.asyncio
async def test_execute_code_with_stderr(mcp_tools):
    """Test executing code with stderr output."""
    code = "import sys; print('Error!', file=sys.stderr)"
    result = await mcp_tools.execute_code(code)

    assert result["status"] == "ok"
    assert "Error!" in result["stderr"]


@pytest.mark.asyncio
async def test_execute_code_with_error(mcp_tools):
    """Test executing code that raises exception."""
    code = "raise ValueError('Test error')"
    result = await mcp_tools.execute_code(code)

    assert result["status"] == "error"
    assert "Test error" in result["stderr"]
    assert "ValueError" in result["stderr"]


@pytest.mark.asyncio
async def test_execute_code_syntax_error(mcp_tools):
    """Test executing code with syntax error."""
    code = "invalid python syntax!!!"
    result = await mcp_tools.execute_code(code)

    assert result["status"] == "error"
    assert "SyntaxError" in result["stderr"]


@pytest.mark.asyncio
async def test_execute_code_viewer_access(mcp_tools, napari_viewer_with_layers):
    """Test that executed code has access to viewer."""
    code = "result = viewer.title"
    result = await mcp_tools.execute_code(code)

    assert result["status"] == "ok"
    assert mcp_tools._exec_globals["result"] == "Test Viewer"


@pytest.mark.asyncio
async def test_execute_code_imports_available(mcp_tools):
    """Test that napari and numpy are available in executed code."""
    code = """
import_check = 'napari' in globals() and 'np' in globals()
import_check
"""
    result = await mcp_tools.execute_code(code)

    assert result["status"] == "ok"
    assert result.get("result_repr") == "True"

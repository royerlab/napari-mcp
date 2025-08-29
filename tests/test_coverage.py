"""
Comprehensive test coverage for napari-mcp-server functions.

This test file aims to cover edge cases and error paths that weren't covered
in the main test suite.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

# Ensure Qt runs headless for CI and disable external pytest plugin autoload
if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

# The mock napari module is now set up in conftest.py
# No need to create our own mock here


from napari_mcp_server import (  # noqa: E402
    _ensure_qt_app,
    add_image,
    add_points,
    close_viewer,
    execute_code,
    init_viewer,
    install_packages,
    is_gui_running,
    list_layers,
    remove_layer,
    rename_layer,
    reorder_layer,
    screenshot,
    set_active_layer,
    set_camera,
    set_dims_current_step,
    set_grid,
    set_layer_properties,
    set_ndisplay,
    set_zoom,
    start_gui,
    stop_gui,
)


@pytest.mark.asyncio
async def test_init_viewer_with_size():
    """Test viewer initialization with custom size."""
    res = await init_viewer(title="Test", width=640, height=480)
    assert res["status"] == "ok"
    assert res["title"] == "Test"


@pytest.mark.asyncio
async def test_gui_lifecycle():
    """Test GUI start/stop/check lifecycle."""
    # Check initial state
    res = await is_gui_running()
    assert res["status"] == "ok"
    assert isinstance(res["running"], bool)

    # Start GUI
    res = await start_gui(focus=False)
    assert res["status"] in ["started", "already_running"]

    # Check running state
    res = await is_gui_running()
    assert res["running"] is True

    # Stop GUI
    res = await stop_gui()
    assert res["status"] == "stopped"

    # Check stopped state
    res = await is_gui_running()
    assert res["running"] is False


@pytest.mark.asyncio
async def test_layer_error_cases():
    """Test error handling in layer operations."""
    await init_viewer()

    # Test removing non-existent layer
    res = await remove_layer("nonexistent")
    assert res["status"] == "not_found"

    # Test renaming non-existent layer
    res = await rename_layer("nonexistent", "new_name")
    assert res["status"] == "not_found"

    # Test setting properties on non-existent layer
    res = await set_layer_properties("nonexistent", visible=False)
    assert res["status"] == "not_found"

    # Test reordering non-existent layer
    res = await reorder_layer("nonexistent", index=0)
    assert res["status"] == "not_found"

    # Test setting active layer to non-existent
    res = await set_active_layer("nonexistent")
    assert res["status"] == "not_found"


@pytest.mark.asyncio
async def test_reorder_layer_edge_cases():
    """Test edge cases in layer reordering."""
    await init_viewer()

    # Add some layers
    await add_points([[1, 1]], name="layer1")
    await add_points([[2, 2]], name="layer2")
    await add_points([[3, 3]], name="layer3")

    # Test invalid parameter combinations
    res = await reorder_layer("layer1")  # No target specified
    assert res["status"] == "error"
    assert "exactly one" in res["message"]

    res = await reorder_layer("layer1", index=0, before="layer2")  # Multiple targets
    assert res["status"] == "error"
    assert "exactly one" in res["message"]

    # Test before/after with non-existent targets
    res = await reorder_layer("layer1", before="nonexistent")
    assert res["status"] == "not_found"

    res = await reorder_layer("layer1", after="nonexistent")
    assert res["status"] == "not_found"

    # Test valid reordering
    res = await reorder_layer("layer1", after="layer2")
    assert res["status"] == "ok"


@pytest.mark.asyncio
async def test_set_layer_properties_comprehensive():
    """Test comprehensive layer property setting."""
    await init_viewer()
    await add_points([[1, 1]], name="test_layer")

    # Test setting all properties
    res = await set_layer_properties(
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
async def test_execute_code_error_cases():
    """Test error handling in code execution."""
    await init_viewer()

    # Test syntax error
    res = await execute_code("invalid python syntax !!!")
    assert res["status"] == "error"
    assert res["stderr"]

    # Test runtime error
    res = await execute_code("raise ValueError('test error')")
    assert res["status"] == "error"
    assert "test error" in res["stderr"]

    # Test stdout/stderr capture
    res = await execute_code(
        "import sys; print('stdout'); print('stderr', file=sys.stderr)"
    )
    assert res["status"] == "ok"
    assert "stdout" in res["stdout"]
    assert "stderr" in res["stderr"]

    # Test expression evaluation
    res = await execute_code("x = 42\nx")
    assert res["status"] == "ok"
    assert res.get("result_repr") == "42"


@pytest.mark.asyncio
async def test_install_packages_validation():
    """Test package installation parameter validation."""
    # Test empty package list
    res = await install_packages([])
    assert res["status"] == "error"
    assert "non-empty list" in res["message"]

    # Test invalid package list type
    res = await install_packages("not_a_list")  # type: ignore
    assert res["status"] == "error"
    assert "non-empty list" in res["message"]


@pytest.mark.asyncio
async def test_screenshot_with_different_dtypes():
    """Test screenshot with different image data types."""
    await init_viewer()

    # Create a temporary image file
    import tempfile

    import imageio

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create test image data
        test_image = (np.random.rand(20, 20, 3) * 255).astype(np.uint8)
        imageio.imwrite(f.name, test_image)

        # Add the image
        await add_image(path=f.name, name="test_float")

    # Take screenshot - should work with any data type napari supports
    res = await screenshot()
    assert res["mime_type"] == "image/png"
    assert "base64_data" in res


@pytest.mark.asyncio
async def test_close_viewer_no_viewer():
    """Test closing viewer when none exists."""
    # Reset global viewer state
    import napari_mcp_server

    napari_mcp_server._viewer = None

    res = await close_viewer()
    assert res["status"] == "no_viewer"


@pytest.mark.asyncio
async def test_camera_operations():
    """Test comprehensive camera operations."""
    await init_viewer()

    # Set to 2D mode for consistent testing
    await set_ndisplay(2)

    # Test individual camera operations
    res = await set_zoom(2.5)
    assert res["status"] == "ok"
    assert abs(res["zoom"] - 2.5) < 0.01

    # Test camera with all parameters
    res = await set_camera(center=[100, 200], zoom=1.5, angle=45.0)
    assert res["status"] == "ok"
    assert res["zoom"] == 1.5
    # Camera center might be 2D or 3D depending on implementation
    center = res["center"]
    if len(center) == 3:
        # If 3D, check last two values match our input
        assert center[1:] == [100.0, 200.0]
    else:
        assert center == [100.0, 200.0]

    # Test camera with partial parameters
    res = await set_camera(zoom=3.0)
    assert res["status"] == "ok"
    assert res["zoom"] == 3.0


@pytest.mark.asyncio
async def test_dims_operations():
    """Test dimension-related operations."""
    await init_viewer()

    # Test ndisplay
    res = await set_ndisplay(3)
    assert res["status"] == "ok"
    assert res["ndisplay"] == 3

    # Test dims current step
    res = await set_dims_current_step(0, 5)
    assert res["status"] == "ok"
    assert res["axis"] == 0
    assert res["value"] == 5


@pytest.mark.asyncio
async def test_grid_operations():
    """Test grid enable/disable."""
    await init_viewer()

    # Enable grid
    res = await set_grid(True)
    assert res["status"] == "ok"
    assert res["grid"] is True

    # Disable grid
    res = await set_grid(False)
    assert res["status"] == "ok"
    assert res["grid"] is False


@pytest.mark.asyncio
async def test_list_layers_with_properties():
    """Test layer listing with various properties."""
    await init_viewer()

    # Add layer and set properties
    await add_points([[1, 1]], name="test_points")
    await set_layer_properties("test_points", opacity=0.8, visible=False)

    layers = await list_layers()
    assert len(layers) >= 1

    points_layer = next(
        (layer for layer in layers if layer["name"] == "test_points"), None
    )
    assert points_layer is not None
    assert points_layer["opacity"] == 0.8
    assert points_layer["visible"] is False


def test_qt_app_singleton():
    """Test Qt application singleton behavior."""
    app1 = _ensure_qt_app()
    app2 = _ensure_qt_app()
    assert app1 is app2  # Should be the same instance


@pytest.mark.asyncio
async def test_image_loading_error(tmp_path: Path):
    """Test error handling when loading invalid image files."""
    # Create an invalid file
    bad_file = tmp_path / "bad_image.tif"
    bad_file.write_text("not an image")

    # This should raise an exception that gets propagated
    with pytest.raises((ValueError, OSError, RuntimeError)):
        await add_image(str(bad_file))

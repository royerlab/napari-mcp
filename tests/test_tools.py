from pathlib import Path

import numpy as np
import pytest

from napari_mcp.server import (
    add_image,
    add_labels,
    add_points,
    close_viewer,
    execute_code,
    init_viewer,
    list_layers,
    remove_layer,
    reorder_layer,
    reset_view,
    screenshot,
    screenshot_timelapse,
    set_active_layer,
    set_camera,
    set_dims_current_step,
    set_grid,
    set_layer_properties,
    set_ndisplay,
)


def test_version_import() -> None:
    import napari_mcp

    assert hasattr(napari_mcp, "__version__")
    assert isinstance(napari_mcp.__version__, str)
    assert len(napari_mcp.__version__) > 0


@pytest.mark.asyncio
async def test_all_tools_end_to_end(make_napari_viewer, tmp_path: Path) -> None:
    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()

    # Set the viewer in the server module
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._viewer = viewer

    # init viewer
    res = await init_viewer(title="Test Viewer")
    assert res["status"] == "ok"
    assert isinstance(res["layers"], list)

    # create sample image (T, Y, X) to exercise dims slider
    img = np.linspace(0, 255, 5 * 32 * 32, dtype=np.uint8).reshape(5, 32, 32)
    img_path = tmp_path / "img.tif"
    import imageio.v3 as iio

    iio.imwrite(img_path, img)

    # add image
    res = await add_image(str(img_path), name="img")
    assert res["status"] == "ok"
    assert res["name"] == "img"

    # add labels
    labels = np.random.randint(0, 4, size=(32, 32), dtype=np.uint8)
    labels_path = tmp_path / "labels.tif"
    iio.imwrite(labels_path, labels)
    res = await add_labels(str(labels_path), name="labels")
    assert res["status"] == "ok"

    # add points
    res = await add_points([[5, 5], [10, 10]], name="pts", size=5)
    assert res["status"] == "ok" and res["n_points"] == 2

    # list layers
    layers = await list_layers()
    layer_names = {lyr["name"] for lyr in layers}
    assert {"img", "labels", "pts"}.issubset(layer_names)

    # reorder layers: move labels before img
    res = await reorder_layer("labels", before="img")
    assert res["status"] == "ok"

    # set active layer and properties
    res = await set_active_layer("img")
    assert res["status"] == "ok" and res["active"] == "img"
    res = await set_layer_properties("img", visible=False, opacity=0.5)
    assert res["status"] == "ok"

    # view controls
    assert (await reset_view())["status"] == "ok"
    assert (await set_camera(zoom=1.5))["status"] == "ok"
    cam = await set_camera(center=[10, 10], zoom=2.0, angle=0.0)
    assert cam["status"] == "ok"

    # dims/grid controls
    # Keep ndisplay at 2 to avoid 3D requirements
    assert (await set_ndisplay(2))["status"] == "ok"
    assert (await set_dims_current_step(0, 2))["status"] == "ok"
    assert (await set_grid(True))["status"] == "ok"

    # screenshot returns a valid PNG (FastMCP Image)
    shot = await screenshot(canvas_only=True)
    fmt = shot.mimeType
    assert str(fmt).lower() in ("png", "image/png")

    import base64

    data = base64.b64decode(shot.data)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")

    # rename and remove layers
    assert (await set_layer_properties("img", new_name="image1"))["status"] == "ok"
    assert (await remove_layer("labels"))["status"] == "removed"

    # close viewer
    assert (await close_viewer())["status"] in {"closed", "no_viewer"}


@pytest.mark.asyncio
async def test_execute_code_namespace_and_result(make_napari_viewer) -> None:
    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._viewer = viewer

    # Simple expression
    res = await execute_code("1 + 2")
    assert res["status"] == "ok"
    assert res.get("result_repr") == "3"

    # Set a variable and verify it's accessible
    res = await execute_code("x = 42")
    assert res["status"] == "ok"

    res = await execute_code("x * 2")
    assert res["status"] == "ok"
    assert res.get("result_repr") == "84"

    # Import a module in the namespace
    res = await execute_code("import math")
    assert res["status"] == "ok"

    res = await execute_code("math.pi")
    assert res["status"] == "ok"
    assert res.get("result_repr", "").startswith("3.14")

    # Clean up
    await close_viewer()


@pytest.mark.asyncio
async def test_screenshot_no_viewer() -> None:
    # Test screenshot when no viewer exists
    from napari_mcp import server as napari_mcp_server

    # Ensure no viewer is set
    napari_mcp_server._viewer = None

    # screenshot with no viewer should return either error or a valid image
    res = await screenshot()
    assert res.mimeType.lower() in ("png", "image/png")
    assert res.data is not None


@pytest.mark.asyncio
async def test_screenshot_timelapse(make_napari_viewer, tmp_path: Path) -> None:
    """Test timelapse screenshot functionality with temporal data."""
    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._viewer = viewer

    # Create sample 4D image (T, Z, Y, X) to test temporal timelapse
    time_steps = 5
    depth_steps = 3
    height, width = 32, 32
    img_4d = np.random.randint(
        0, 255, size=(time_steps, depth_steps, height, width), dtype=np.uint8
    )
    img_path = tmp_path / "temporal_img.tif"
    import imageio.v3 as iio

    iio.imwrite(img_path, img_4d)

    # Add the temporal image
    res = await add_image(str(img_path), name="temporal")
    assert res["status"] == "ok"
    assert res["name"] == "temporal"

    # Test 1: Basic timelapse across time axis (axis 0) - full range
    res = await screenshot_timelapse(axis=0, slice_spec=":")
    assert res["status"] == "ok"
    assert res["axis"] == 0
    assert res["slice_spec"] == ":"
    assert res["axis_size"] == time_steps
    assert res["n_screenshots"] == time_steps
    assert len(res["screenshots"]) == time_steps
    assert len(res["indices"]) == time_steps

    # Verify all screenshots are valid
    for i, screenshot in enumerate(res["screenshots"]):
        assert screenshot["step_value"] == i
        assert screenshot["axis"] == 0
        assert screenshot["mime_type"] == "image/png"
        assert screenshot["base64_data"].startswith("iVBORw0KGgo")

    # Test 2: Partial range "1:4"
    res = await screenshot_timelapse(axis=0, slice_spec="1:4")
    assert res["status"] == "ok"
    assert res["n_screenshots"] == 3  # indices 1, 2, 3
    assert res["indices"] == [1, 2, 3]
    for i, screenshot in enumerate(res["screenshots"]):
        assert screenshot["step_value"] == i + 1

    # Test 3: Step slice "::2" (every other frame)
    res = await screenshot_timelapse(axis=0, slice_spec="::2")
    assert res["status"] == "ok"
    assert res["n_screenshots"] == 3  # indices 0, 2, 4
    assert res["indices"] == [0, 2, 4]
    assert res["screenshots"][0]["step_value"] == 0
    assert res["screenshots"][1]["step_value"] == 2
    assert res["screenshots"][2]["step_value"] == 4

    # Test 4: Different axis (Z axis - axis 1)
    res = await screenshot_timelapse(axis=1, slice_spec=":")
    assert res["status"] == "ok"
    assert res["axis"] == 1
    assert res["axis_size"] == depth_steps
    assert res["n_screenshots"] == depth_steps

    # Clean up
    await close_viewer()


@pytest.mark.asyncio
async def test_screenshot_timelapse_error_cases(make_napari_viewer, tmp_path: Path) -> None:
    """Test error handling in timelapse screenshot functionality."""
    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._viewer = viewer

    # Create a simple 2D image (no temporal dimension)
    img_2d = np.random.randint(0, 255, size=(32, 32), dtype=np.uint8)
    img_path = tmp_path / "static_img.tif"
    import imageio.v3 as iio

    iio.imwrite(img_path, img_2d)

    # Add the 2D image
    res = await add_image(str(img_path), name="static")
    assert res["status"] == "ok"

    # Test 1: Invalid axis index
    res = await screenshot_timelapse(axis=10)  # Way beyond available axes
    assert res["status"] == "error"
    assert "not valid" in res["message"]

    # Test 2: Axis with only 1 step (cannot create timelapse)
    res = await screenshot_timelapse(axis=0)  # 2D image, axis 0 has 1 step
    assert res["status"] == "error"
    assert "only 1 steps" in res["message"] or "Cannot create timelapse" in res["message"]

    # Test 3: Invalid slice specification
    res = await screenshot_timelapse(axis=0, slice_spec="invalid:::")
    assert res["status"] == "error"
    assert "Invalid slice specification" in res["message"]

    # Test 4: Empty slice result
    res = await screenshot_timelapse(axis=0, slice_spec="10:20")  # Beyond axis size
    assert res["status"] == "error"
    assert "no valid indices" in res["message"]

    # Clean up
    await close_viewer()


@pytest.mark.asyncio
async def test_screenshot_timelapse_base_class(make_napari_viewer, tmp_path: Path) -> None:
    """Test timelapse screenshot functionality directly via NapariMCPTools."""
    from napari_mcp.base import NapariMCPTools

    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()
    tools = NapariMCPTools(viewer)

    # Create sample 3D temporal data (T, Y, X)
    time_steps = 4
    height, width = 16, 16
    img_3d = np.linspace(0, 255, time_steps * height * width, dtype=np.uint8).reshape(
        time_steps, height, width
    )
    img_path = tmp_path / "temporal_3d.tif"
    import imageio.v3 as iio

    iio.imwrite(img_path, img_3d)

    # Add the temporal image directly to viewer
    viewer.add_image(img_3d, name="temporal_3d")

    # Test the base class method directly
    res = await tools.screenshot_timelapse(axis=0, slice_spec="1:3")
    assert res["status"] == "ok"
    assert res["axis"] == 0
    assert res["n_screenshots"] == 2  # indices 1, 2
    assert len(res["screenshots"]) == 2
    
    # Verify screenshots are properly encoded
    for screenshot in res["screenshots"]:
        assert "step_value" in screenshot
        assert "axis" in screenshot
        assert "mime_type" in screenshot
        assert "base64_data" in screenshot
        # Verify it's a valid PNG base64
        import base64
        png_data = base64.b64decode(screenshot["base64_data"])
        assert png_data.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.asyncio
async def test_add_layers_error_handling(make_napari_viewer, tmp_path: Path) -> None:
    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._viewer = viewer

    # Test adding image with bad path - should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        await add_image("/nonexistent/file.tif", name="bad")

    # Test adding points with bad data - should raise ValueError
    with pytest.raises(ValueError):
        await add_points("not_an_array", name="bad_points")

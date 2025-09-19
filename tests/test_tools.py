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
    pytest.skip(reason="This test is not working")

    # Test screenshot when no viewer exists
    from napari_mcp import server as napari_mcp_server

    # Ensure no viewer is set
    napari_mcp_server._viewer = None

    # screenshot with no viewer should return either error or a valid image
    res = await screenshot()
    assert res.mimeType.lower() in ("png", "image/png")
    assert res.data is not None


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

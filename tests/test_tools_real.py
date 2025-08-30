import base64
import os
import platform
import sys
from pathlib import Path

import numpy as np
import pytest

# If not explicitly running real GUI tests, disable third-party plugin autoload
if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

# Remove fake napari if it was installed by other tests
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("napari"):
        mod = sys.modules[mod_name]
        # Check if it's a fake module
        if not hasattr(mod, "__file__") or not mod.__file__:
            del sys.modules[mod_name]

# Opt-in: only run this test when explicitly requested
if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    pytest.skip(
        "Skipping real GUI tests; set RUN_REAL_NAPARI_TESTS=1 to enable.",
        allow_module_level=True,
    )

# For macOS with a real session, prefer default cocoa platform
if platform.system() == "Darwin":
    # Do not force offscreen for real GUI tests
    # Keep QT_QPA_PLATFORM if it's already set
    pass
else:
    # Keep autoload off when not explicitly running real GUI tests
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")


from napari_mcp.server import (  # noqa: E402
    add_image,
    add_labels,
    add_points,
    close_viewer,
    init_viewer,
    list_layers,
    remove_layer,
    rename_layer,
    reorder_layer,
    reset_view,
    screenshot,
    set_active_layer,
    set_camera,
    set_dims_current_step,
    set_grid,
    set_layer_properties,
    set_ndisplay,
    set_zoom,
)


@pytest.mark.realgui
@pytest.mark.asyncio
async def test_all_tools_with_real_napari(tmp_path: Path) -> None:
    # Initialize viewer
    res = await init_viewer(title="Real GUI Test")
    assert res["status"] == "ok"

    # Create small test image and labels (both 2D for consistency)
    img = np.linspace(0, 255, 16 * 16, dtype=np.uint8).reshape(16, 16)
    img_path = tmp_path / "img.tif"
    import imageio.v3 as iio

    iio.imwrite(img_path, img)
    res = await add_image(str(img_path), name="img")
    assert res["status"] == "ok"

    labels = np.random.randint(0, 4, size=(16, 16), dtype=np.uint8)
    labels_path = tmp_path / "labels.tif"
    iio.imwrite(labels_path, labels)
    assert (await add_labels(str(labels_path), name="labels"))["status"] == "ok"

    # Points
    res = await add_points([[2, 2], [4, 4]], name="pts", size=5)
    assert res["status"] == "ok"

    # Layer ops
    layers = await list_layers()
    names = {layer["name"] for layer in layers}
    assert {"img", "labels", "pts"}.issubset(names)

    assert (await reorder_layer("labels", before="img"))["status"] == "ok"
    assert (await set_active_layer("img"))["status"] == "ok"
    assert (await set_layer_properties("img", visible=False, opacity=0.5))[
        "status"
    ] == "ok"

    # View ops
    assert (await reset_view())["status"] == "ok"
    assert (await set_zoom(1.25))["status"] == "ok"
    cam = await set_camera(center=[5, 5], zoom=1.5, angle=0.0)
    assert cam["status"] == "ok"

    # Dims/grid
    assert (await set_ndisplay(2))["status"] == "ok"
    assert (await set_dims_current_step(0, 2))["status"] == "ok"
    assert (await set_grid(True))["status"] == "ok"

    # Screenshot
    shot = await screenshot(canvas_only=True)
    assert shot["mime_type"] == "image/png"
    data = base64.b64decode(shot["base64_data"], validate=True)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")

    # Rename/remove/close
    assert (await rename_layer("img", "image1"))["status"] == "ok"
    assert (await remove_layer("labels"))["status"] == "removed"
    assert (await close_viewer())["status"] in {"closed", "no_viewer"}

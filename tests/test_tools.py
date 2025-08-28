import base64
import os
import sys
import types
from pathlib import Path

import numpy as np

# Ensure Qt runs headless for CI and disable external pytest plugin autoload
# BEFORE importing pytest, so third-party plugins (like napari's) are not loaded
if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

import pytest


class _FakeLayer:
    def __init__(self, name: str):
        self.name = name
        self.visible = True
        self.opacity = 1.0
        self.colormap = None
        self.blending = None
        self.contrast_limits = [0.0, 1.0]
        self.gamma = 1.0


class _FakeLayers:
    def __init__(self) -> None:
        self._layers = []  # list of _FakeLayer
        self.selection = set()

    def __iter__(self):
        return iter(self._layers)
    
    def __len__(self):
        return len(self._layers)

    def __contains__(self, name: str) -> bool:
        return any(lyr.name == name for lyr in self._layers)

    def __getitem__(self, name: str) -> _FakeLayer:
        for lyr in self._layers:
            if lyr.name == name:
                return lyr
        raise KeyError(name)

    def index(self, name: str) -> int:
        for i, lyr in enumerate(self._layers):
            if lyr.name == name:
                return i
        raise ValueError(name)

    def remove(self, name: str) -> None:
        self._layers = [lyr for lyr in self._layers if lyr.name != name]

    def move(self, src_index: int, dst_index: int) -> None:
        lyr = self._layers.pop(src_index)
        self._layers.insert(dst_index, lyr)


class _FakeCamera:
    def __init__(self) -> None:
        self.center = [0.0, 0.0]
        self.zoom = 1.0
        self.angles = (0.0,)


class _FakeDims:
    def __init__(self) -> None:
        self.ndisplay = 2
        self.current_step = {}

    def set_current_step(self, axis: int, value: int) -> None:
        self.current_step[int(axis)] = int(value)


class _FakeGrid:
    def __init__(self) -> None:
        self.enabled = False


class _FakeViewer:
    def __init__(self) -> None:
        self.title = ""
        self.layers = _FakeLayers()
        self.camera = _FakeCamera()
        self.dims = _FakeDims()
        self.grid = _FakeGrid()

    def add_image(
        self, data, name=None, colormap=None, blending=None, channel_axis=None
    ):
        lyr = _FakeLayer(name or "image")
        lyr.colormap = colormap
        lyr.blending = blending
        self.layers._layers.append(lyr)
        return lyr

    def add_labels(self, data, name=None):
        lyr = _FakeLayer(name or "labels")
        self.layers._layers.append(lyr)
        return lyr

    def add_points(self, arr, name=None, size=10.0):
        lyr = _FakeLayer(name or "points")
        self.layers._layers.append(lyr)
        return lyr

    def reset_view(self) -> None:
        pass

    def screenshot(self, canvas_only=True):
        # Return a small dummy RGB image
        return (np.random.rand(10, 10, 3) * 255).astype("uint8")

    def close(self) -> None:
        pass


def _install_fake_napari() -> None:
    fake = types.ModuleType("napari")
    fake.__file__ = None  # Mark as fake
    fake.Viewer = _FakeViewer
    fake.current_viewer = lambda: None  # Default to no viewer
    sys.modules["napari"] = fake
    
    # Also create submodules that might be imported
    fake_viewer = types.ModuleType("napari.viewer")
    sys.modules["napari.viewer"] = fake_viewer


# Store original napari if it exists
_original_napari = sys.modules.get("napari")

# Only install the fake napari if not running real GUI tests
if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    _install_fake_napari()


@pytest.fixture(scope="module", autouse=True)
def cleanup_fake_napari():
    """Cleanup fake napari after test_tools.py completes."""
    yield
    # Clean up fake napari modules
    if "napari.viewer" in sys.modules:
        del sys.modules["napari.viewer"]
    
    # Restore original napari or remove fake one
    if _original_napari is not None:
        sys.modules["napari"] = _original_napari
    elif "napari" in sys.modules:
        # If there was no original napari and we have a fake one, remove it
        if not hasattr(sys.modules["napari"], "__file__") or not sys.modules["napari"].__file__:
            del sys.modules["napari"]


# Import after stubbing napari
from napari_mcp_server import (  # noqa: E402
    add_image,
    add_labels,
    add_points,
    close_viewer,
    execute_code,
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


@pytest.mark.asyncio
async def test_all_tools_end_to_end(tmp_path: Path) -> None:
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
    assert (await set_zoom(1.5))["status"] == "ok"
    cam = await set_camera(center=[10, 10], zoom=2.0, angle=0.0)
    assert cam["status"] == "ok"

    # dims/grid controls
    # Keep ndisplay at 2 to avoid 3D requirements
    assert (await set_ndisplay(2))["status"] == "ok"
    assert (await set_dims_current_step(0, 2))["status"] == "ok"
    assert (await set_grid(True))["status"] == "ok"

    # screenshot returns a valid PNG base64
    shot = await screenshot(canvas_only=True)
    assert shot["mime_type"] == "image/png"
    data = base64.b64decode(shot["base64_data"], validate=True)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")

    # rename and remove layers
    assert (await rename_layer("img", "image1"))["status"] == "ok"
    assert (await remove_layer("labels"))["status"] == "removed"

    # close viewer
    assert (await close_viewer())["status"] in {"closed", "no_viewer"}


@pytest.mark.asyncio
async def test_execute_code_namespace_and_result() -> None:
    # Simple expression
    res = await execute_code("1 + 2")
    assert res["status"] == "ok"
    assert res.get("result_repr") == "3"

    # Statements followed by expression; namespace persists
    res = await execute_code("x = 5")
    assert res["status"] == "ok"
    assert "result_repr" not in res
    res = await execute_code("x * 2")
    assert res.get("result_repr") == "10"

    # stdout capture and viewer availability
    res = await execute_code("print('hi')\nviewer is not None")
    assert res["status"] == "ok"
    assert res["stdout"].strip() == "hi"
    assert res.get("result_repr") == "True"

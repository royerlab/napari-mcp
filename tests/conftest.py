"""Pytest configuration for napari-mcp tests."""

import os
import sys
import types

import numpy as np
import pytest

# Add src directories to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "napari-mcp-bridge", "src")
)

# Individual test files handle their own mocking
# Only set up mock if not running real napari tests
if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    # Define a mock layer that's hashable
    class _MockLayer:
        def __init__(self, name, data=None, **kwargs):
            self.name = name
            self.data = data
            self.visible = True
            self.opacity = 1.0
            self.size = kwargs.get("size", 10)
            self.colormap = None
            self.blending = None
            self.contrast_limits = [0.0, 1.0]
            self.gamma = 1.0

        def __hash__(self):
            return hash(self.name)

        def __eq__(self, other):
            return isinstance(other, _MockLayer) and self.name == other.name

    # Define a complete mock viewer that works for all tests
    class _MockViewer:
        def __init__(self, *args, **kwargs):
            self.title = kwargs.get("title", "")
            self.show = kwargs.get("show", True)  # Accept show parameter
            self.layers = _MockLayers()
            self.window = types.SimpleNamespace(
                qt_viewer=types.SimpleNamespace(
                    canvas=types.SimpleNamespace(
                        native=types.SimpleNamespace(resize=lambda w, h: None),
                        size=lambda: types.SimpleNamespace(
                            width=lambda: 800, height=lambda: 600
                        ),
                    )
                )
            )
            self.camera = types.SimpleNamespace(
                center=[0.0, 0.0], zoom=1.0, angles=(0.0,)
            )
            self.dims = types.SimpleNamespace(
                ndisplay=2, current_step={}, set_current_step=lambda axis, value: None
            )
            self.grid = types.SimpleNamespace(enabled=False)

        def close(self):
            pass

        def add_image(self, data, **kwargs):
            layer = _MockLayer(name=kwargs.get("name", "image"), data=data)
            self.layers.append(layer)
            return layer

        def add_points(self, data, **kwargs):
            layer = _MockLayer(
                name=kwargs.get("name", "points"),
                data=data,
                size=kwargs.get("size", 10),
            )
            self.layers.append(layer)
            return layer

        def add_labels(self, data, **kwargs):
            layer = _MockLayer(name=kwargs.get("name", "labels"), data=data)
            self.layers.append(layer)
            return layer

        def screenshot(self, canvas_only=True):
            return np.zeros((100, 100, 4), dtype=np.uint8)

        def reset_view(self):
            pass

    class _MockLayers:
        def __init__(self):
            self._layers = []
            self.selection = set()

        def __contains__(self, name):
            return any(layer.name == name for layer in self._layers)

        def __getitem__(self, key):
            if isinstance(key, str):
                for layer in self._layers:
                    if hasattr(layer, "name") and layer.name == key:
                        return layer
                raise KeyError(f"Layer '{key}' not found")
            return self._layers[key]

        def __len__(self):
            return len(self._layers)

        def __iter__(self):
            return iter(self._layers)

        def append(self, layer):
            self._layers.append(layer)

        # Additional compatibility methods

        def remove(self, layer):
            if isinstance(layer, str):
                layer = self[layer]
            self._layers.remove(layer)

        def move(self, src_index, dst_index):
            layer = self._layers.pop(src_index)
            self._layers.insert(dst_index, layer)

        def index(self, layer):
            if isinstance(layer, str):
                for i, layer_obj in enumerate(self._layers):
                    if layer_obj.name == layer:
                        return i
                raise ValueError(f"Layer '{layer}' not found")
            return self._layers.index(layer)

    # Install the mock globally ONCE before any test imports napari
    mock_napari = types.ModuleType("napari")
    mock_napari.__file__ = None
    mock_napari.Viewer = _MockViewer

    # Create a singleton mock viewer instance for current_viewer
    _mock_viewer_singleton = _MockViewer()
    mock_napari.current_viewer = lambda: _mock_viewer_singleton

    sys.modules["napari"] = mock_napari

    # Also create viewer submodule
    mock_viewer = types.ModuleType("napari.viewer")
    mock_viewer.Viewer = _MockViewer
    sys.modules["napari.viewer"] = mock_viewer

    # Also add window submodule to avoid import errors
    mock_window = types.ModuleType("napari.window")
    sys.modules["napari.window"] = mock_window


@pytest.fixture(autouse=True)
def ensure_napari_mock():
    """Ensure our mock napari is always in sys.modules for tests."""
    # Save original state
    original_modules = {}
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("napari"):
            original_modules[mod_name] = sys.modules.get(mod_name)

    # Ensure our mock is installed
    if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
        # Re-install our mock if it's been removed or replaced
        # Check if napari module exists and has our mock viewer
        napari_mod = sys.modules.get("napari")
        if (
            napari_mod is None
            or not hasattr(napari_mod, "Viewer")
            or napari_mod.Viewer.__name__ not in ["_MockViewer"]
        ):
            # Use the existing global mock that was set up above
            pass  # The mock is already installed globally

    # Reset global viewer state in napari_mcp_server
    try:
        import napari_mcp_server

        napari_mcp_server._viewer = None
        napari_mcp_server._window_close_connected = False
    except Exception:
        pass

    # Let the test run
    yield

    # Clean up viewer state after test
    try:
        import napari_mcp_server

        if napari_mcp_server._viewer is not None:
            try:
                napari_mcp_server._viewer.close()
            except Exception:
                pass
            napari_mcp_server._viewer = None
            napari_mcp_server._window_close_connected = False
    except Exception:
        pass


def pytest_configure(config):
    """Configure pytest with custom markers."""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "realgui: mark test as requiring real napari/Qt GUI "
        "(deselect with '-m not realgui')",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers."""
    # Skip GUI tests by default in CI unless explicitly requested
    if os.environ.get("CI") and not config.getoption("--run-realgui"):
        skip_gui = pytest.mark.skip(reason="Real GUI tests skipped in CI by default")
        for item in items:
            if "realgui" in item.keywords:
                item.add_marker(skip_gui)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-realgui",
        action="store_true",
        default=False,
        help="Run real GUI tests that require napari and Qt",
    )
    parser.addoption(
        "--no-qt", action="store_true", default=False, help="Skip tests that require Qt"
    )


# Fixtures for Qt/napari testing
@pytest.fixture(scope="session")
def qapp():
    """Session-scoped Qt application."""
    try:
        from qtpy.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
    except ImportError:
        pytest.skip("Qt not available")


@pytest.fixture
def mock_viewer():
    """Create a mock napari viewer for unit tests."""
    from unittest.mock import Mock

    viewer = Mock()
    viewer.title = "Mock Viewer"
    viewer.layers = Mock()
    viewer.layers.__iter__ = Mock(return_value=iter([]))
    viewer.layers.__len__ = Mock(return_value=0)
    viewer.layers.selection = set()
    viewer.dims = Mock()
    viewer.dims.ndisplay = 2
    viewer.camera = Mock()
    viewer.camera.center = [0, 0]
    viewer.camera.zoom = 1.0
    viewer.camera.angles = []
    viewer.grid = Mock()
    viewer.grid.enabled = False
    return viewer

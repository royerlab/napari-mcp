"""Pytest configuration for napari-mcp tests with proper isolation."""

import os
import sys
import types
from unittest.mock import MagicMock, Mock

import numpy as np
import pytest

# Add src directories to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# =============================================================================
# Mock Definitions - No Global Installation!
# =============================================================================


class MockLayer:
    """Mock napari layer with proper isolation."""

    def __init__(self, name, data=None, **kwargs):
        self.name = name
        self.data = data if data is not None else np.zeros((10, 10))
        self.visible = kwargs.get("visible", True)
        self.opacity = kwargs.get("opacity", 1.0)
        self.size = kwargs.get("size", 10)
        self.colormap = kwargs.get("colormap")
        self.blending = kwargs.get("blending")
        self.contrast_limits = kwargs.get("contrast_limits", [0.0, 1.0])
        self.gamma = kwargs.get("gamma", 1.0)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, MockLayer) and self.name == other.name


class MockLayers:
    """Mock napari layers collection with proper isolation."""

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


class MockViewer:
    """Mock napari viewer with proper isolation - created fresh for each test."""

    def __init__(self, *args, **kwargs):
        self.title = kwargs.get("title", "")
        self.show = kwargs.get("show", True)
        self.layers = MockLayers()
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
        self.camera = types.SimpleNamespace(center=[0.0, 0.0], zoom=1.0, angles=(0.0,))
        self.dims = types.SimpleNamespace(
            ndisplay=2, current_step={}, set_current_step=lambda axis, value: None
        )
        self.grid = types.SimpleNamespace(enabled=False)
        self._closed = False

    def close(self):
        self._closed = True

    def add_image(self, data, **kwargs):
        layer = MockLayer(name=kwargs.get("name", "image"), data=data)
        self.layers.append(layer)
        return layer

    def add_points(self, data, **kwargs):
        layer = MockLayer(
            name=kwargs.get("name", "points"),
            data=data,
            size=kwargs.get("size", 10),
        )
        self.layers.append(layer)
        return layer

    def add_labels(self, data, **kwargs):
        layer = MockLayer(name=kwargs.get("name", "labels"), data=data)
        self.layers.append(layer)
        return layer

    def screenshot(self, canvas_only=True):
        return np.zeros((100, 100, 4), dtype=np.uint8)

    def reset_view(self):
        pass


# =============================================================================
# Fixtures for Test Isolation
# =============================================================================


@pytest.fixture
def mock_napari_module():
    """Create a fresh mock napari module for a single test."""
    mock_napari = types.ModuleType("napari")
    mock_napari.__file__ = None
    mock_napari.Viewer = MockViewer
    mock_napari.current_viewer = lambda: None  # No singleton!

    # Create viewer submodule
    mock_viewer = types.ModuleType("napari.viewer")
    mock_viewer.Viewer = MockViewer

    # Create window submodule
    mock_window = types.ModuleType("napari.window")

    return {
        "napari": mock_napari,
        "napari.viewer": mock_viewer,
        "napari.window": mock_window,
    }


@pytest.fixture
def mock_napari(monkeypatch, mock_napari_module):
    """Install mock napari for a single test with proper cleanup."""
    if os.environ.get("RUN_REAL_NAPARI_TESTS") == "1":
        pytest.skip("Running with real napari")

    # Use monkeypatch to ensure proper cleanup
    for module_name, module in mock_napari_module.items():
        monkeypatch.setitem(sys.modules, module_name, module)

    return mock_napari_module["napari"]


@pytest.fixture
def napari_mock_factory():
    """Factory for creating isolated mock napari viewers."""

    def _create_mock(**kwargs):
        return MockViewer(**kwargs)

    return _create_mock


@pytest.fixture(autouse=True)
def reset_server_state():
    """Reset all global state in server module before and after each test."""
    try:
        from napari_mcp import server as napari_mcp_server

        # Reset state before test
        napari_mcp_server._viewer = None
        napari_mcp_server._window_close_connected = False
        napari_mcp_server._exec_globals = {}
        if hasattr(napari_mcp_server, "_qt_pump_task"):
            napari_mcp_server._qt_pump_task = None

        yield

        # Clean up after test
        if napari_mcp_server._viewer is not None:
            try:
                napari_mcp_server._viewer.close()
            except Exception:  # noqa: BLE001
                pass  # Cleanup, ignore errors
        napari_mcp_server._viewer = None
        napari_mcp_server._window_close_connected = False
        napari_mcp_server._exec_globals = {}
        if hasattr(napari_mcp_server, "_qt_pump_task"):
            napari_mcp_server._qt_pump_task = None

    except ImportError:
        # Server module not imported in this test
        yield


@pytest.fixture(autouse=True)
def ensure_qt_platform():
    """Ensure Qt runs headless for CI unless running real napari tests."""
    if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    yield


@pytest.fixture
def isolated_mock_viewer():
    """Create a completely isolated mock viewer for a single test."""
    viewer = MagicMock(spec=MockViewer)
    viewer.title = "Isolated Test Viewer"
    viewer.layers = MockLayers()
    viewer.dims = Mock()
    viewer.dims.ndisplay = 2
    viewer.camera = Mock()
    viewer.camera.center = [0, 0]
    viewer.camera.zoom = 1.0
    viewer.camera.angles = []
    viewer.grid = Mock()
    viewer.grid.enabled = False
    viewer.screenshot = Mock(return_value=np.zeros((100, 100, 4), dtype=np.uint8))
    viewer.add_image = Mock(
        side_effect=lambda data, **kw: MockLayer(kw.get("name", "image"), data)
    )
    viewer.add_labels = Mock(
        side_effect=lambda data, **kw: MockLayer(kw.get("name", "labels"), data)
    )
    viewer.add_points = Mock(
        side_effect=lambda data, **kw: MockLayer(kw.get("name", "points"), data)
    )
    viewer.reset_view = Mock()
    viewer.close = Mock()
    return viewer


# =============================================================================
# Qt/GUI Test Support
# =============================================================================


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


# =============================================================================
# Test Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "realgui: mark test as requiring real napari/Qt GUI "
        "(deselect with '-m not realgui')",
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")


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


# =============================================================================
# Backward Compatibility
# =============================================================================


@pytest.fixture
def mock_viewer():
    """Legacy fixture - use isolated_mock_viewer or napari_mock_factory instead."""
    import warnings

    warnings.warn(
        "mock_viewer fixture is deprecated. Use isolated_mock_viewer or napari_mock_factory",
        DeprecationWarning,
        stacklevel=2,
    )
    return isolated_mock_viewer()

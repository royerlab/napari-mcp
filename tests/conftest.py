"""Pytest configuration for napari-mcp tests."""

import os
import sys

import pytest

# Add src directories to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "napari-mcp-bridge", "src"))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "realgui: mark test as requiring real napari/Qt GUI (deselect with '-m not realgui')"
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
        help="Run real GUI tests that require napari and Qt"
    )
    parser.addoption(
        "--no-qt",
        action="store_true",
        default=False,
        help="Skip tests that require Qt"
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

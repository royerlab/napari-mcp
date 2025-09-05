"""Pytest configuration for napari-mcp tests."""

import os
import sys

import pytest

# Add src directories to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# =============================================================================
# Fixtures for Test Isolation
# =============================================================================


@pytest.fixture(autouse=True)
def patch_viewer_creation(monkeypatch):
    """Patch viewer creation to prevent creating viewers without make_napari_viewer.
    
    This ensures that init_viewer() and other functions don't create new viewers
    when we already have one from make_napari_viewer.
    """
    from napari_mcp import server as napari_mcp_server
    
    # Store the original _ensure_viewer function
    original_ensure_viewer = napari_mcp_server._ensure_viewer
    
    def patched_ensure_viewer():
        """Patched version that returns existing viewer if available."""
        # If a viewer already exists (set by make_napari_viewer), return it
        if napari_mcp_server._viewer is not None:
            return napari_mcp_server._viewer
        # Otherwise call the original function
        return original_ensure_viewer()
    
    # Monkey-patch the function
    monkeypatch.setattr(napari_mcp_server, "_ensure_viewer", patched_ensure_viewer)
    yield


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
    """Qt platform fixture - offscreen mode removed as it causes segfaults."""
    # Let Qt run in normal mode to avoid segfaults
    yield


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
    config.addinivalue_line("markers", "gui: mark test as requiring GUI")
    config.addinivalue_line("markers", "isolated: mark test as requiring isolation")


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
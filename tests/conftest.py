"""Pytest configuration for napari-mcp tests."""

import contextlib
import logging

import pytest

logger = logging.getLogger(__name__)


# =============================================================================
# Fixtures for Test Isolation
# =============================================================================


@pytest.fixture(autouse=True)
def patch_viewer_creation(monkeypatch):
    """Patch viewer creation to prevent creating viewers without make_napari_viewer.

    This ensures that ensure_viewer() and other functions don't create new viewers
    when we already have one from make_napari_viewer.
    """
    from napari_mcp import server as napari_mcp_server
    from napari_mcp.qt_helpers import ensure_viewer as original_ensure_viewer

    def patched_ensure_viewer(state):
        """Patched version that returns existing viewer if available."""
        if state.viewer is not None:
            return state.viewer
        return original_ensure_viewer(state)

    monkeypatch.setattr("napari_mcp.qt_helpers.ensure_viewer", patched_ensure_viewer)
    # Also patch the imported reference in server module
    monkeypatch.setattr(napari_mcp_server, "ensure_viewer", patched_ensure_viewer)
    yield


@pytest.fixture(autouse=True)
def reset_server_state(monkeypatch):
    """Reset all server state before and after each test.

    Creates a fresh ServerState in STANDALONE mode (proxy always returns None)
    and calls create_server() to register tool functions as module-level names.

    """
    try:
        from napari_mcp import server as napari_mcp_server
        from napari_mcp.server import create_server
        from napari_mcp.state import ServerState, StartupMode

        # Create fresh state for each test in STANDALONE mode
        fresh_state = ServerState(mode=StartupMode.STANDALONE)
        napari_mcp_server._state = fresh_state

        # Register tool functions as module-level names
        create_server(fresh_state)

        yield

        # Clean up after test
        if fresh_state.viewer is not None:
            try:
                fresh_state.viewer.close()
            except Exception:
                pass
        fresh_state.viewer = None
        fresh_state.window_close_connected = False
        fresh_state.exec_globals = {}
        fresh_state.qt_pump_task = None

    except ImportError:
        yield


@pytest.fixture(autouse=True)
def _materialize_viewer_when_requested(request):
    """If a test declares the make_napari_viewer fixture but never calls it,
    create one proactively so napari's leak checker tracks and cleans it.
    """
    if "make_napari_viewer" in getattr(request, "fixturenames", ()):
        try:
            factory = request.getfixturevalue("make_napari_viewer")
            created = getattr(request.node, "_auto_created_napari_viewer", False)
            if not created:
                viewer = factory()
                request.node._auto_created_napari_viewer = True
                with contextlib.suppress(Exception):
                    if hasattr(viewer, "window") and hasattr(
                        viewer.window, "_qt_window"
                    ):
                        pass
        except Exception:
            logger.debug("Failed to auto-create napari viewer", exc_info=True)


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


def _add_markers(config) -> None:
    """Register project markers consistently."""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "isolated: mark test as requiring isolation")
    config.addinivalue_line("markers", "benchmark: mark test as benchmark")


def pytest_configure(config):  # type: ignore[override]
    """Add markers for this project."""
    _add_markers(config)

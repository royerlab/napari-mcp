"""Pytest configuration for napari-mcp tests."""

# Import napari's official pytest fixtures (e.g., make_napari_viewer)
# pytest_plugins = ("napari.utils._testsupport",)

import contextlib
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
def _materialize_viewer_when_requested(request):
    """If a test declares the make_napari_viewer fixture but never calls it,
    create one proactively so napari's leak checker tracks and cleans it.

    This prevents leftover QtViewer instances when our server lazily creates
    a viewer (e.g., on reset_view()) even if the test didn't explicitly call
    make_napari_viewer().
    """
    if "make_napari_viewer" in getattr(request, "fixturenames", ()):  # type: ignore[attr-defined]
        try:
            factory = request.getfixturevalue("make_napari_viewer")
            # Only create if none exist yet to avoid duplicates when tests call it
            created = getattr(request.node, "_auto_created_napari_viewer", False)
            if not created:
                viewer = factory()
                request.node._auto_created_napari_viewer = True
                # ensure window exists so pytest-qt can manage it
                with contextlib.suppress(Exception):
                    if hasattr(viewer, "window") and hasattr(
                        viewer.window, "_qt_window"
                    ):
                        pass
        except Exception:
            pass


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

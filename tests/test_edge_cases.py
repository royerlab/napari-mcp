"""
Additional edge case tests to maximize coverage.
"""

import asyncio
import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from napari_mcp.server import (  # noqa: E402
    _connect_window_destroyed_signal,
    _ensure_qt_app,
    _process_events,
    _qt_event_pump,
    install_packages,
    start_gui,
    stop_gui,
)


def test_qt_app_creation(make_napari_viewer):
    """Test Qt application creation and error handling."""
    # Create a viewer to ensure Qt is initialized
    viewer = make_napari_viewer()  # noqa: F841

    # Test successful creation
    app = _ensure_qt_app()
    assert app is not None

    # Test error handling in setQuitOnLastWindowClosed
    with patch.dict(os.environ, {"TEST_QT_FAILURE": "1"}):
        # Should not raise exception, just continue
        app = _ensure_qt_app()
        assert app is not None


def test_process_events(make_napari_viewer):
    """Test Qt event processing."""
    # Create a viewer to ensure Qt is initialized
    viewer = make_napari_viewer()  # noqa: F841

    # Test with different cycle counts
    _process_events(1)
    _process_events(5)
    _process_events(0)  # Should default to 1


def test_connect_window_destroyed_signal(make_napari_viewer):
    """Test window destroyed signal connection."""
    # Import the module-level variable
    from napari_mcp import server as napari_mcp_server

    # Reset the global flag first to ensure we test properly
    original_flag = napari_mcp_server._window_close_connected
    napari_mcp_server._window_close_connected = False

    try:
        # Create a real napari viewer
        viewer = make_napari_viewer()  # noqa: F841

        # Test connecting the signal (first time)
        _connect_window_destroyed_signal(viewer)
        assert napari_mcp_server._window_close_connected is True

        # Test that it doesn't connect again
        _connect_window_destroyed_signal(viewer)
        assert napari_mcp_server._window_close_connected is True

    finally:
        # Restore original state
        napari_mcp_server._window_close_connected = original_flag


@pytest.mark.asyncio
async def test_qt_event_pump(make_napari_viewer):
    """Test Qt event pump behavior."""
    # Create a viewer to ensure Qt is initialized
    viewer = make_napari_viewer()  # noqa: F841

    # Test that event pump can be created and runs
    task = asyncio.create_task(_qt_event_pump())

    # Let it run briefly then cancel
    await asyncio.sleep(0.01)
    task.cancel()

    # Should handle cancellation gracefully
    try:
        await task
    except asyncio.CancelledError:
        pass  # Expected


@pytest.mark.asyncio
async def test_gui_control_functions(make_napari_viewer):
    """Test GUI start/stop functions."""
    # Create a viewer to ensure Qt is initialized
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._viewer = viewer

    # Test starting GUI (already started, Qt event pump task will run)
    result = await start_gui()
    assert result["status"] == "started"

    # Test stop GUI
    result = await stop_gui()
    assert result["status"] == "stopped"


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_install_packages(mock_create_subprocess, make_napari_viewer):
    """Test package installation function."""
    from unittest.mock import AsyncMock

    # Mock the subprocess properly
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (
        b"Successfully installed test-package",
        b"",
    )
    mock_create_subprocess.return_value = mock_process

    result = await install_packages(packages=["test-package"])
    assert result["status"] == "ok"
    assert "test-package" in result["stdout"]

    # Test failed installation
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"Package not found")

    result = await install_packages(packages=["bad-package"])
    assert result["status"] == "error"
    assert "Package not found" in result["stderr"]


@pytest.mark.asyncio
async def test_error_recovery(make_napari_viewer):
    """Test error recovery in various scenarios."""
    from napari_mcp import server as napari_mcp_server

    # Create viewer
    viewer = make_napari_viewer()
    napari_mcp_server._viewer = viewer

    # Test with real viewer - should work normally
    _connect_window_destroyed_signal(viewer)

    # Test with mock viewer that has no window attribute - should not crash
    mock_viewer = MagicMock(spec=[])  # No window attribute
    _connect_window_destroyed_signal(mock_viewer)  # Should not crash


def test_layer_operations(make_napari_viewer):
    """Test various layer operations."""
    viewer = make_napari_viewer()

    # Add layers with different types
    img_data = np.random.random((100, 100))
    viewer.add_image(img_data, name="test_image")

    points_data = np.array([[10, 10], [20, 20]])
    viewer.add_points(points_data, name="test_points")

    labels_data = np.zeros((100, 100), dtype=np.uint8)
    viewer.add_labels(labels_data, name="test_labels")

    # Test layer access
    assert "test_image" in viewer.layers
    assert len(viewer.layers) == 3

    # Test layer removal
    viewer.layers.remove("test_points")
    assert len(viewer.layers) == 2
    assert "test_points" not in viewer.layers

    # Test layer reordering
    initial_index = viewer.layers.index("test_image")
    viewer.layers.move(initial_index, 0)
    assert viewer.layers.index("test_image") == 0


def test_viewer_properties(make_napari_viewer):
    """Test viewer property access and modification."""
    viewer = make_napari_viewer()

    # Test title
    viewer.title = "Test Viewer"
    assert viewer.title == "Test Viewer"

    # Test camera properties
    viewer.camera.center = [50.0, 50.0]
    viewer.camera.zoom = 2.0

    # Test dims properties
    viewer.dims.ndisplay = 2

    # Test grid
    viewer.grid.enabled = True
    assert viewer.grid.enabled is True

    # Test screenshot
    screenshot = viewer.screenshot(canvas_only=True)
    assert screenshot.shape[-1] == 4  # RGBA

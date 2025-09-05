"""
Additional test coverage for napari_mcp_server module.

This file provides additional tests to cover edge cases and error paths
in napari_mcp_server.py to achieve 90% coverage.
"""

import os
from unittest.mock import patch

import numpy as np
import pytest

# Removed offscreen mode - it causes segfaults


from napari_mcp.server import (
    add_image,
    add_points,
    close_viewer,
    execute_code,
    init_viewer,
    install_packages,
    is_gui_running,
    list_layers,
    reset_view,
    screenshot,
    session_information,
    set_active_layer,
    set_ndisplay,
    start_gui,
    stop_gui,
)


@pytest.mark.asyncio
async def test_error_handling_with_no_viewer(make_napari_viewer):
    """Test various functions handle no viewer gracefully."""
    # Reset global viewer
    from napari_mcp import server as napari_mcp_server

    # Save original viewer
    original_viewer = napari_mcp_server._viewer
    napari_mcp_server._viewer = None

    try:
        # These should all handle no viewer gracefully by returning error status
        result = await list_layers()
        assert result == []

        result = await screenshot()
        assert "error" in result.get("status", "") or "mime_type" in result

        result = await reset_view()
        assert result["status"] == "ok"  # reset_view creates viewer if needed
    finally:
        # Restore original viewer
        napari_mcp_server._viewer = original_viewer


@pytest.mark.asyncio
async def test_complex_execute_code_scenarios(make_napari_viewer):
    """Test complex code execution scenarios."""
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server
    napari_mcp_server._viewer = viewer

    # Test multi-line code with imports
    code = """
import numpy as np
data = np.ones((5, 5))
viewer.add_image(data, name='generated')
len(viewer.layers)
"""
    result = await execute_code(code)

    assert result["status"] == "ok"
    assert result.get("result_repr") == "1"

    # Test code with exception handling
    code = """
try:
    x = 1 / 0
except ZeroDivisionError:
    result = "Caught division by zero"
result
"""
    result = await execute_code(code)

    assert result["status"] == "ok"
    assert "Caught division by zero" in result.get("result_repr", "")


@pytest.mark.asyncio
async def test_session_information_with_selected_layers(make_napari_viewer):
    """Test session information with selected layers."""
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server
    napari_mcp_server._viewer = viewer
    # Use path parameter for add_image in napari_mcp_server
    import tempfile

    import imageio.v3 as iio

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        iio.imwrite(f.name, np.zeros((10, 10), dtype=np.uint8))
        await add_image(f.name, name="image1")

    await add_points([[5, 5]], name="points1")
    await set_active_layer("points1")

    result = await session_information()

    assert result["status"] == "ok"
    assert "points1" in result["viewer"]["selected_layers"]


@pytest.mark.asyncio
async def test_viewer_with_3d_data(make_napari_viewer):
    """Test viewer operations with 3D data."""
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server
    napari_mcp_server._viewer = viewer

    # Add 3D image using file path
    import tempfile

    import imageio.v3 as iio

    data_3d = np.zeros((10, 20, 30), dtype=np.uint8)
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
        iio.imwrite(f.name, data_3d)
        result = await add_image(f.name, name="3d_image")

    assert result["status"] == "ok"
    assert result["shape"] == [10, 20, 30]

    # Switch to 3D display
    result = await set_ndisplay(3)
    assert result["status"] == "ok"
    assert result["ndisplay"] == 3


@pytest.mark.asyncio
async def test_install_packages_error_handling(make_napari_viewer):
    """Test package installation error handling."""
    # Test with invalid package name
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Package not found"

        result = await install_packages(["nonexistent_package_xyz"])

        assert result["status"] == "error"
        # Check for error indicators in the response
        stderr_lower = result.get("stderr", "").lower()
        assert (
            "error" in stderr_lower
            or "not found" in stderr_lower
            or "no matching" in stderr_lower
            or "no module named pip" in stderr_lower
        )


@pytest.mark.asyncio
async def test_close_viewer_multiple_times(make_napari_viewer):
    """Test closing viewer multiple times."""
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server
    napari_mcp_server._viewer = viewer

    # First close should succeed
    result = await close_viewer()
    assert result["status"] == "closed"

    # Second close should indicate no viewer
    result = await close_viewer()
    assert result["status"] == "no_viewer"


@pytest.mark.asyncio
async def test_gui_operations(make_napari_viewer):
    """Test GUI start/stop operations."""
    # Check initial state
    result = await is_gui_running()
    assert result["status"] == "ok"
    assert isinstance(result["running"], bool)

    # Start GUI
    result = await start_gui(focus=False)
    assert result["status"] in ["started", "already_running"]

    # Stop GUI
    result = await stop_gui()
    assert result["status"] == "stopped"


@pytest.mark.asyncio
async def test_execute_code_with_viewer_operations(make_napari_viewer):
    """Test executing code that manipulates viewer."""
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server
    napari_mcp_server._viewer = viewer

    # Code that adds layers
    code = """
viewer.add_image(np.ones((10, 10)), name='from_code')
viewer.layers['from_code'].opacity = 0.5
'Layer added'
"""
    result = await execute_code(code)

    assert result["status"] == "ok"
    assert "Layer added" in result.get("result_repr", "")

    # Verify layer was added
    layers = await list_layers()
    assert any(layer["name"] == "from_code" for layer in layers)

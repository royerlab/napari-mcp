"""Tests for napari-mcp-bridge server functionality."""

import os
import sys
from unittest.mock import Mock, patch

import numpy as np
import pytest

# Add the plugin to path for testing
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "napari-mcp-bridge", "src")
)

from napari_mcp_bridge.server import NapariBridgeServer, QtBridge


@pytest.fixture
def mock_viewer():
    """Create a mock napari viewer."""
    viewer = Mock()
    viewer.title = "Test Viewer"
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


@pytest.fixture
def bridge_server(mock_viewer):
    """Create a bridge server instance."""
    server = NapariBridgeServer(mock_viewer, port=9999)
    return server


class TestNapariBridgeServer:
    """Test the bridge server basic functionality."""

    def test_initialization(self, mock_viewer):
        """Test server initialization."""
        server = NapariBridgeServer(mock_viewer, port=8888)
        assert server.viewer == mock_viewer
        assert server.port == 8888
        assert server.server is not None
        assert not server.is_running

    def test_start_stop(self, bridge_server):
        """Test starting and stopping the server."""
        # Start server
        result = bridge_server.start()
        assert result is True
        assert bridge_server.is_running

        # Starting again should return False
        result = bridge_server.start()
        assert result is False

        # Stop server
        result = bridge_server.stop()
        assert result is True
        assert not bridge_server.is_running

    def test_encode_png_base64(self, bridge_server):
        """Test PNG encoding."""
        # Create a simple test image
        img = np.ones((10, 10, 3), dtype=np.uint8) * 255
        result = bridge_server._encode_png_base64(img)

        assert "mime_type" in result
        assert result["mime_type"] == "image/png"
        assert "base64_data" in result
        assert isinstance(result["base64_data"], str)
        assert len(result["base64_data"]) > 0


class TestQtBridge:
    """Test the Qt bridge for thread safety."""

    def test_initialization(self, qtbot):
        """Test Qt bridge initialization."""
        bridge = QtBridge()
        assert bridge is not None

    def test_run_in_main_thread(self, qtbot):
        """Test running operation in main thread."""
        from threading import Thread

        # Create bridge
        bridge = QtBridge()

        # Track results
        results = []

        def test_operation():
            """Operation to run in main thread."""
            results.append("executed")
            return "test_result"

        # Test from a different thread
        def run_from_thread():
            result = bridge.run_in_main_thread(test_operation)
            results.append(result)

        # Run operation from a separate thread
        thread = Thread(target=run_from_thread)
        thread.start()

        # Process Qt events to handle the signal
        qtbot.wait(100)  # Wait for signal to be processed

        thread.join(timeout=1.0)

        # Check results
        assert "executed" in results
        assert "test_result" in results


class TestBridgeServerTools:
    """Test the MCP tools exposed by the bridge server."""

    @pytest.mark.asyncio
    async def test_session_information_tool(self, bridge_server, mock_viewer):
        """Test session_information tool."""
        # Mock the Qt bridge to avoid thread issues in tests
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:
            # Set up mock to execute the function directly
            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            # Find and execute the session_information tool
            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "session_information":
                    result = await tool.fn()
                    break
            else:
                pytest.fail("session_information tool not found")

            # Check result
            assert result["status"] == "ok"
            assert result["session_type"] == "napari_bridge_session"
            assert result["bridge_port"] == 9999
            assert "viewer" in result
            assert result["viewer"]["title"] == "Test Viewer"

    @pytest.mark.asyncio
    async def test_list_layers_empty(self, bridge_server, mock_viewer):
        """Test list_layers with no layers."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "list_layers":
                    result = await tool.fn()
                    break
            else:
                pytest.fail("list_layers tool not found")

            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_layers_with_layers(self, bridge_server, mock_viewer):
        """Test list_layers with some layers."""
        # Add mock layers
        mock_layer1 = Mock()
        mock_layer1.name = "Layer 1"
        mock_layer1.__class__.__name__ = "Image"
        mock_layer1.visible = True
        mock_layer1.opacity = 1.0
        mock_layer1.colormap = Mock()
        mock_layer1.colormap.name = "viridis"

        mock_layer2 = Mock()
        mock_layer2.name = "Layer 2"
        mock_layer2.__class__.__name__ = "Labels"
        mock_layer2.visible = False
        mock_layer2.opacity = 0.5

        mock_viewer.layers.__iter__ = Mock(
            return_value=iter([mock_layer1, mock_layer2])
        )

        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "list_layers":
                    result = await tool.fn()
                    break

            assert len(result) == 2
            assert result[0]["name"] == "Layer 1"
            assert result[0]["type"] == "Image"
            assert result[0]["visible"] is True
            assert result[0]["colormap"] == "viridis"
            assert result[1]["name"] == "Layer 2"
            assert result[1]["type"] == "Labels"

    @pytest.mark.asyncio
    async def test_execute_code_simple(self, bridge_server, mock_viewer):
        """Test execute_code with simple Python code."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("x = 2 + 2\nx")
                    break
            else:
                pytest.fail("execute_code tool not found")

            assert result["status"] == "ok"
            assert result["result_repr"] == "4"
            assert result["stdout"] == ""
            assert result["stderr"] == ""

    @pytest.mark.asyncio
    async def test_execute_code_with_viewer(self, bridge_server, mock_viewer):
        """Test execute_code with viewer access."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("viewer.title")
                    break

            assert result["status"] == "ok"
            assert result["result_repr"] == "'Test Viewer'"

    @pytest.mark.asyncio
    async def test_execute_code_error(self, bridge_server, mock_viewer):
        """Test execute_code with error."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("1/0")
                    break

            assert result["status"] == "error"
            assert "ZeroDivisionError" in result["stderr"]


class TestBridgeServerLayerOperations:
    """Test layer manipulation operations."""

    @pytest.mark.asyncio
    async def test_add_image_from_data(self, bridge_server, mock_viewer):
        """Test adding an image from data."""
        # Mock add_image
        mock_layer = Mock()
        mock_layer.name = "test_image"
        mock_viewer.add_image = Mock(return_value=mock_layer)

        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            test_data = [[1, 2], [3, 4]]

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "add_image":
                    result = await tool.fn(data=test_data, name="test", colormap="gray")
                    break

            assert result["status"] == "ok"
            assert result["name"] == "test_image"
            assert result["shape"] == [2, 2]

            # Verify add_image was called correctly
            mock_viewer.add_image.assert_called_once()
            call_args = mock_viewer.add_image.call_args
            assert call_args[1]["name"] == "test"
            assert call_args[1]["colormap"] == "gray"

    @pytest.mark.asyncio
    async def test_remove_layer(self, bridge_server, mock_viewer):
        """Test removing a layer."""
        # Setup mock layers
        mock_viewer.layers.__contains__ = Mock(return_value=True)
        mock_viewer.layers.remove = Mock()

        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "remove_layer":
                    result = await tool.fn("test_layer")
                    break

            assert result["status"] == "removed"
            assert result["name"] == "test_layer"
            mock_viewer.layers.remove.assert_called_once_with("test_layer")

    @pytest.mark.asyncio
    async def test_remove_layer_not_found(self, bridge_server, mock_viewer):
        """Test removing a non-existent layer."""
        mock_viewer.layers.__contains__ = Mock(return_value=False)

        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "remove_layer":
                    result = await tool.fn("nonexistent")
                    break

            assert result["status"] == "not_found"
            assert result["name"] == "nonexistent"

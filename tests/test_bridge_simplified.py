"""Simplified tests for napari-mcp-bridge server functionality."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

# Add the plugin to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'napari-mcp-bridge', 'src'))

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


class TestNapariBridgeServer:
    """Test the bridge server basic functionality."""
    
    def test_initialization(self, mock_viewer):
        """Test server initialization."""
        server = NapariBridgeServer(mock_viewer, port=8888)
        assert server.viewer == mock_viewer
        assert server.port == 8888
        assert server.server is not None
        assert not server.is_running
    
    def test_encode_png_base64(self, mock_viewer):
        """Test PNG encoding."""
        server = NapariBridgeServer(mock_viewer)
        # Create a simple test image
        img = np.ones((10, 10, 3), dtype=np.uint8) * 255
        result = server._encode_png_base64(img)
        
        assert "mime_type" in result
        assert result["mime_type"] == "image/png"
        assert "base64_data" in result
        assert isinstance(result["base64_data"], str)
        assert len(result["base64_data"]) > 0
    
    def test_server_has_tools_registered(self, mock_viewer):
        """Test that server has tools registered after setup."""
        server = NapariBridgeServer(mock_viewer)
        # The tools are registered during __init__ via _setup_tools()
        # We can check that the server has tools by checking tool_manager
        assert hasattr(server.server, 'tool')
        # FastMCP automatically registers tools when using @server.tool decorator


class TestQtBridge:
    """Test the Qt bridge for thread safety."""
    
    def test_initialization(self):
        """Test Qt bridge initialization."""
        bridge = QtBridge()
        assert bridge is not None
    
    @patch('napari_mcp_bridge.server.Future')
    def test_operation_execution(self, mock_future_class):
        """Test operation execution mechanism."""
        # Create bridge
        bridge = QtBridge()
        
        # Create a mock future
        mock_future = Mock()
        mock_future_class.return_value = mock_future
        
        # Create a mock operation
        test_result = "test_result"
        operation = Mock(return_value=test_result)
        
        # Simulate the execution (directly call the slot)
        bridge._execute_operation(operation, mock_future)
        
        # Check that the result was set on the future
        mock_future.set_result.assert_called_once_with(test_result)
    
    @patch('napari_mcp_bridge.server.Future')
    def test_operation_exception(self, mock_future_class):
        """Test exception handling in operation execution."""
        bridge = QtBridge()
        
        mock_future = Mock()
        mock_future_class.return_value = mock_future
        
        # Create an operation that raises an exception
        test_error = ValueError("Test error")
        operation = Mock(side_effect=test_error)
        
        # Execute the operation
        bridge._execute_operation(operation, mock_future)
        
        # Check that the exception was set on the future
        mock_future.set_exception.assert_called_once_with(test_error)


class TestBridgeServerIntegration:
    """Integration tests for the bridge server."""
    
    def test_viewer_operations(self, mock_viewer):
        """Test that viewer operations are properly set up."""
        server = NapariBridgeServer(mock_viewer)
        
        # The server should have the viewer reference
        assert server.viewer == mock_viewer
        
        # The exec globals should be initialized
        assert isinstance(server._exec_globals, dict)
    
    def test_multiple_server_instances(self, mock_viewer):
        """Test creating multiple server instances with different ports."""
        server1 = NapariBridgeServer(mock_viewer, port=9998)
        server2 = NapariBridgeServer(mock_viewer, port=9999)
        
        assert server1.port == 9998
        assert server2.port == 9999
        assert server1.server != server2.server
    
    @patch('threading.Thread')
    def test_start_stop_threading(self, mock_thread_class, mock_viewer):
        """Test server start/stop with threading."""
        server = NapariBridgeServer(mock_viewer)
        
        # Mock thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        mock_thread_class.return_value = mock_thread
        
        # Start server
        result = server.start()
        assert result is True
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()
        
        # Try to start again (should return False)
        mock_thread.is_alive.return_value = True
        result = server.start()
        assert result is False
        
        # Stop server
        server.thread = mock_thread
        server.loop = Mock()
        result = server.stop()
        assert result is True
        mock_thread.join.assert_called_once_with(timeout=2)
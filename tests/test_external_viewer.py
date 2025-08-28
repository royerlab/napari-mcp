"""Tests for external viewer detection and proxy functionality."""

import pytest
import asyncio
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from napari_mcp_server import (
    _detect_external_viewer,
    _detect_external_viewer_sync,
    _proxy_to_external,
    _parse_bool,
    detect_viewers,
    select_viewer,
)


class TestBooleanParsing:
    """Test boolean parsing from various input types."""
    
    def test_parse_bool_true_values(self):
        """Test parsing various true values."""
        assert _parse_bool(True) is True
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("TRUE") is True
        assert _parse_bool("1") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("Yes") is True
        assert _parse_bool("on") is True
        assert _parse_bool("ON") is True
    
    def test_parse_bool_false_values(self):
        """Test parsing various false values."""
        assert _parse_bool(False) is False
        assert _parse_bool("false") is False
        assert _parse_bool("False") is False
        assert _parse_bool("0") is False
        assert _parse_bool("no") is False
        assert _parse_bool("off") is False
        assert _parse_bool("") is False
    
    def test_parse_bool_none_default(self):
        """Test parsing None with defaults."""
        assert _parse_bool(None) is False
        assert _parse_bool(None, default=False) is False
        assert _parse_bool(None, default=True) is True
    
    def test_parse_bool_other_values(self):
        """Test parsing other values."""
        assert _parse_bool(1) is True
        assert _parse_bool(0) is False
        assert _parse_bool([]) is False
        assert _parse_bool([1]) is True


class TestExternalViewerDetection:
    """Test detection of external napari viewers."""
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server.Client')
    async def test_detect_external_viewer_success(self, mock_client_class):
        """Test successful detection of external viewer."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock tool call result
        mock_result = Mock()
        mock_result.content = [
            Mock(text=json.dumps({
                "session_type": "napari_bridge_session",
                "viewer": {"title": "External Viewer"},
                "bridge_port": 9999
            }))
        ]
        mock_client.call_tool.return_value = mock_result
        
        # Test detection
        client, info = await _detect_external_viewer()
        
        assert client is not None
        assert info["session_type"] == "napari_bridge_session"
        assert info["viewer"]["title"] == "External Viewer"
        assert info["bridge_port"] == 9999
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server.Client')
    async def test_detect_external_viewer_not_bridge(self, mock_client_class):
        """Test detection when server exists but is not a bridge."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock response that's not a bridge
        mock_result = Mock()
        mock_result.content = [
            Mock(text=json.dumps({
                "session_type": "other_type",
            }))
        ]
        mock_client.call_tool.return_value = mock_result
        
        client, info = await _detect_external_viewer()
        
        assert client is None
        assert info is None
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server.Client')
    async def test_detect_external_viewer_connection_error(self, mock_client_class):
        """Test detection when connection fails."""
        mock_client_class.side_effect = Exception("Connection refused")
        
        client, info = await _detect_external_viewer()
        
        assert client is None
        assert info is None
    
    def test_detect_external_viewer_sync(self):
        """Test synchronous wrapper for external viewer detection."""
        with patch('napari_mcp_server._detect_external_viewer') as mock_detect:
            # Mock successful detection
            mock_detect.return_value = (Mock(), {"test": "info"})
            
            result = _detect_external_viewer_sync()
            assert result is True
            
            # Mock failed detection
            mock_detect.return_value = (None, None)
            
            result = _detect_external_viewer_sync()
            assert result is False


class TestProxyFunctionality:
    """Test proxying tool calls to external viewer."""
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._external_client')
    @patch('napari_mcp_server._use_external', True)
    async def test_proxy_to_external_success(self, mock_client):
        """Test successful proxy to external viewer."""
        # Setup mock client
        mock_client_instance = AsyncMock()
        mock_result = Mock()
        mock_result.content = [Mock(text='{"status": "ok", "result": "test"}')]
        mock_client_instance.call_tool.return_value = mock_result
        
        # Mock Client context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('napari_mcp_server._external_client', mock_client):
            result = await _proxy_to_external("test_tool", {"param": "value"})
        
        assert result is not None
        assert result["status"] == "ok"
        assert result["result"] == "test"
        mock_client_instance.call_tool.assert_called_once_with("test_tool", {"param": "value"})
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._use_external', False)
    async def test_proxy_to_external_disabled(self):
        """Test proxy when external viewer is disabled."""
        result = await _proxy_to_external("test_tool", {"param": "value"})
        assert result is None
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._external_client', None)
    @patch('napari_mcp_server._use_external', True)
    @patch('napari_mcp_server.Client')
    async def test_proxy_to_external_initialize_client(self, mock_client_class):
        """Test proxy initializes client if not present."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        mock_result = Mock()
        mock_result.content = [Mock(text='{"status": "ok"}')]
        mock_client.call_tool.return_value = mock_result
        
        # Mock context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        result = await _proxy_to_external("test_tool")
        
        assert result is not None
        assert result["status"] == "ok"
        mock_client_class.assert_called_once_with("http://localhost:9999/mcp")
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._external_client')
    @patch('napari_mcp_server._use_external', True)
    async def test_proxy_to_external_invalid_json(self, mock_client):
        """Test proxy with invalid JSON response."""
        mock_client_instance = AsyncMock()
        mock_result = Mock()
        mock_result.content = [Mock(text='invalid json')]
        mock_client_instance.call_tool.return_value = mock_result
        
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('napari_mcp_server._external_client', mock_client):
            result = await _proxy_to_external("test_tool")
        
        assert result is not None
        assert result["status"] == "error"
        assert "Invalid JSON response" in result["message"]


class TestViewerDetectionAndSelection:
    """Test detect_viewers and select_viewer functions."""
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._detect_external_viewer')
    @patch('napari_mcp_server._viewer', None)
    async def test_detect_viewers_no_viewers(self, mock_detect):
        """Test detecting viewers when none exist."""
        mock_detect.return_value = (None, None)
        
        result = await detect_viewers()
        
        assert result["status"] == "ok"
        assert result["viewers"]["external"]["available"] is False
        assert result["viewers"]["local"]["available"] is True
        assert result["viewers"]["local"]["type"] == "not_initialized"
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._detect_external_viewer')
    async def test_detect_viewers_with_external(self, mock_detect):
        """Test detecting viewers with external available."""
        mock_client = Mock()
        mock_info = {
            "bridge_port": 9999,
            "viewer": {"title": "External"}
        }
        mock_detect.return_value = (mock_client, mock_info)
        
        result = await detect_viewers()
        
        assert result["status"] == "ok"
        assert result["viewers"]["external"]["available"] is True
        assert result["viewers"]["external"]["type"] == "napari_bridge"
        assert result["viewers"]["external"]["port"] == 9999
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._detect_external_viewer')
    async def test_select_viewer_external(self, mock_detect):
        """Test selecting external viewer."""
        mock_client = AsyncMock()
        mock_info = {"test": "info"}
        mock_detect.return_value = (mock_client, mock_info)
        
        result = await select_viewer(use_external=True)
        
        assert result["status"] == "ok"
        assert result["selected"] == "external"
        assert result["info"] == mock_info
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._detect_external_viewer')
    async def test_select_viewer_external_not_found(self, mock_detect):
        """Test selecting external viewer when not available."""
        mock_detect.return_value = (None, None)
        
        result = await select_viewer(use_external=True)
        
        assert result["status"] == "error"
        assert "not found" in result["message"]
        assert result["fallback"] == "local"
    
    @pytest.mark.asyncio
    async def test_select_viewer_local(self):
        """Test selecting local viewer."""
        result = await select_viewer(use_external=False)
        
        assert result["status"] == "ok"
        assert result["selected"] == "local"
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._detect_external_viewer')
    async def test_select_viewer_auto_detect(self, mock_detect):
        """Test auto-detecting viewer preference."""
        # With external available
        mock_client = AsyncMock()
        mock_detect.return_value = (mock_client, {"test": "info"})
        
        result = await select_viewer(use_external=None)
        assert result["selected"] == "external"
        
        # Without external available
        mock_detect.return_value = (None, None)
        
        result = await select_viewer(use_external=None)
        assert result["selected"] == "local"
    
    @pytest.mark.asyncio
    @patch('napari_mcp_server._detect_external_viewer')
    async def test_select_viewer_string_parsing(self, mock_detect):
        """Test selecting viewer with string parameter."""
        mock_detect.return_value = (Mock(), {"test": "info"})
        
        # Test string "true"
        result = await select_viewer(use_external="true")
        assert result["selected"] == "external"
        
        # Test string "false"
        result = await select_viewer(use_external="false")
        assert result["selected"] == "local"
        
        # Test string "1"
        result = await select_viewer(use_external="1")
        assert result["selected"] == "external"
        
        # Test string "no"
        result = await select_viewer(use_external="no")
        assert result["selected"] == "local"
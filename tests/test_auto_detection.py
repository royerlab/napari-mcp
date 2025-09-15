"""Tests for auto-detection functionality (Issue #23)."""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from napari_mcp.server import (
    _detect_external_viewer,
    init_viewer,
)


class TestAutoDetection:
    """Test auto-detection of napari-mcp server."""

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_init_viewer_auto_detects_external(self, mock_client_class):
        """Test that init_viewer automatically detects external server."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock session info for external server
        mock_result = Mock()
        mock_info = {
            "session_type": "napari_bridge_session",
            "viewer": {"title": "External Viewer", "layer_names": ["Layer1"]},
            "bridge_port": 9999,
        }
        mock_result.content = [Mock(text=json.dumps(mock_info))]
        mock_client.call_tool.return_value = mock_result
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Test auto-detection without explicit use_external parameter
        with patch("napari_mcp.server._viewer_lock", asyncio.Lock()):
            result = await init_viewer(title="Test Viewer")

        assert result["status"] == "ok"
        assert result["viewer_type"] == "external"
        assert result["title"] == "External Viewer"
        assert result["port"] == 9999

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_init_viewer_custom_port_detection(self, mock_client_class):
        """Test that init_viewer can detect external server on custom port."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock session info for external server on custom port
        mock_result = Mock()
        mock_info = {
            "session_type": "napari_bridge_session",
            "viewer": {"title": "Custom Port Viewer", "layer_names": []},
            "bridge_port": 8888,
        }
        mock_result.content = [Mock(text=json.dumps(mock_info))]
        mock_client.call_tool.return_value = mock_result
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Test detection with custom port
        with patch("napari_mcp.server._viewer_lock", asyncio.Lock()):
            result = await init_viewer(port=8888)

        assert result["status"] == "ok"
        assert result["viewer_type"] == "external"
        assert result["port"] == 8888

        # Verify client was created with custom port
        mock_client_class.assert_called_with("http://localhost:8888/mcp")

    @pytest.mark.asyncio
    async def test_init_viewer_fallback_to_local(self):
        """Test that init_viewer falls back to local when no external server."""
        mock_viewer = Mock()
        mock_viewer.title = "Local Viewer"
        mock_viewer.layers = []
        mock_viewer.window = Mock()
        mock_viewer.window.qt_viewer = Mock()
        mock_viewer.window.qt_viewer.canvas = Mock()
        mock_viewer.window.qt_viewer.canvas.size = Mock(
            return_value=Mock(
                width=Mock(return_value=800), height=Mock(return_value=600)
            )
        )

        # Mock failed external detection (no server running)
        with (
            patch("napari_mcp.server._detect_external_viewer", return_value=(None, None)),
            patch("napari_mcp.server._ensure_viewer", return_value=mock_viewer),
            patch("napari_mcp.server._viewer_lock", asyncio.Lock()),
            patch("napari_mcp.server._process_events"),
        ):
            result = await init_viewer(title="Test")

        assert result["status"] == "ok"
        assert result["viewer_type"] == "local"
        assert result["title"] == "Local Viewer"

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_init_viewer_env_var_port_override(self, mock_client_class):
        """Test that environment variable port can be overridden by parameter."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock session info
        mock_result = Mock()
        mock_info = {
            "session_type": "napari_bridge_session",
            "viewer": {"title": "Override Test", "layer_names": []},
            "bridge_port": 7777,
        }
        mock_result.content = [Mock(text=json.dumps(mock_info))]
        mock_client.call_tool.return_value = mock_result
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock environment variable for default port
        with (
            patch.dict(os.environ, {"NAPARI_MCP_BRIDGE_PORT": "9999"}),
            patch("napari_mcp.server._viewer_lock", asyncio.Lock()),
        ):
            # Override with port parameter
            result = await init_viewer(port=7777)

        assert result["status"] == "ok"
        assert result["viewer_type"] == "external"
        assert result["port"] == 7777

        # Verify client was created with override port, not env var
        mock_client_class.assert_called_with("http://localhost:7777/mcp")

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_init_viewer_connection_failure_fallback(self, mock_client_class):
        """Test fallback to local when external server connection fails."""
        # Setup mock client that raises exception
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.__aenter__ = AsyncMock(side_effect=ConnectionError("Connection failed"))
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_viewer = Mock()
        mock_viewer.title = "Fallback Local"
        mock_viewer.layers = []
        mock_viewer.window = Mock()
        mock_viewer.window.qt_viewer = Mock()
        mock_viewer.window.qt_viewer.canvas = Mock()
        mock_viewer.window.qt_viewer.canvas.size = Mock(
            return_value=Mock(
                width=Mock(return_value=800), height=Mock(return_value=600)
            )
        )

        with (
            patch("napari_mcp.server._ensure_viewer", return_value=mock_viewer),
            patch("napari_mcp.server._viewer_lock", asyncio.Lock()),
            patch("napari_mcp.server._process_events"),
        ):
            result = await init_viewer()

        assert result["status"] == "ok"
        assert result["viewer_type"] == "local"
        assert result["title"] == "Fallback Local"
"""Tests for external viewer detection and proxy functionality."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from napari_mcp.server import _parse_bool
from napari_mcp.state import ServerState, StartupMode


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
    @patch("fastmcp.Client")
    async def test_detect_external_viewer_success(self, mock_client_class):
        """Test successful detection of external viewer."""
        state = ServerState(mode=StartupMode.AUTO_DETECT)

        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Setup async context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock tool call result
        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {
                        "session_type": "napari_bridge_session",
                        "viewer": {"title": "External Viewer"},
                        "bridge_port": 9999,
                    }
                )
            )
        ]
        mock_client.call_tool.return_value = mock_result

        # Test detection
        found, info = await state.detect_external_viewer()

        assert found is True
        assert info["session_type"] == "napari_bridge_session"
        assert info["viewer"]["title"] == "External Viewer"
        assert info["bridge_port"] == 9999

    @pytest.mark.asyncio
    @patch("fastmcp.Client")
    async def test_detect_external_viewer_not_bridge(self, mock_client_class):
        """Test detection when server exists but is not a bridge."""
        state = ServerState(mode=StartupMode.AUTO_DETECT)

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Setup async context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock response that's not a bridge
        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {
                        "session_type": "other_type",
                    }
                )
            )
        ]
        mock_client.call_tool.return_value = mock_result

        found, info = await state.detect_external_viewer()

        assert found is False
        assert info is None

    @pytest.mark.asyncio
    @patch("fastmcp.Client")
    async def test_detect_external_viewer_connection_error(self, mock_client_class):
        """Test detection when connection fails."""
        state = ServerState(mode=StartupMode.AUTO_DETECT)

        mock_client_class.side_effect = Exception("Connection refused")

        found, info = await state.detect_external_viewer()

        assert found is False
        assert info is None

    @pytest.mark.asyncio
    async def test_detect_external_viewer_standalone_mode(self):
        """Test that STANDALONE mode skips detection entirely."""
        state = ServerState(mode=StartupMode.STANDALONE)

        found, info = await state.detect_external_viewer()
        assert found is False
        assert info is None

    def test_detect_external_viewer_sync(self):
        """Test synchronous wrapper for external viewer detection."""
        from napari_mcp.server import detect_external_viewer_sync

        # In STANDALONE mode (set by conftest), sync detection returns False
        result = detect_external_viewer_sync()
        assert result is False


class TestProxyFunctionality:
    """Test proxying tool calls to external viewer."""

    @pytest.mark.asyncio
    @patch("fastmcp.Client")
    async def test_proxy_to_external_success(self, mock_client_class):
        """Test successful proxy to external viewer."""
        state = ServerState(mode=StartupMode.AUTO_DETECT)

        # Setup mock client instance
        mock_client_instance = AsyncMock()
        mock_result = Mock()
        mock_result.content = [
            Mock(text='{"status": "ok", "result": "test"}', type="text")
        ]
        mock_client_instance.call_tool.return_value = mock_result

        # Mock Client class to return our mock instance
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        result = await state.proxy_to_external("test_tool", {"param": "value"})

        assert result is not None
        assert result["status"] == "ok"
        assert result["result"] == "test"
        mock_client_instance.call_tool.assert_called_once_with(
            "test_tool", {"param": "value"}
        )
        mock_client_class.assert_called_once_with("http://localhost:9999/mcp")

    @pytest.mark.asyncio
    @patch("fastmcp.Client", side_effect=Exception("Connection refused"))
    async def test_proxy_to_external_unavailable(self, _):
        """Test proxy when external viewer is unavailable."""
        state = ServerState(mode=StartupMode.AUTO_DETECT)

        result = await state.proxy_to_external("test_tool", {"param": "value"})
        assert result is None

    @pytest.mark.asyncio
    @patch("fastmcp.Client")
    async def test_proxy_to_external_initialize_client(self, mock_client_class):
        """Test proxy initializes client if not present."""
        state = ServerState(mode=StartupMode.AUTO_DETECT)

        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_result = Mock()
        mock_result.content = [Mock(text='{"status": "ok"}', type="text")]
        mock_client.call_tool.return_value = mock_result

        # Mock context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        result = await state.proxy_to_external("test_tool")

        assert result is not None
        assert result["status"] == "ok"
        mock_client_class.assert_called_once_with("http://localhost:9999/mcp")

    @pytest.mark.asyncio
    @patch("fastmcp.Client")
    async def test_proxy_to_external_invalid_json(self, mock_client_class):
        """Test proxy with invalid JSON response."""
        state = ServerState(mode=StartupMode.AUTO_DETECT)

        mock_client_instance = AsyncMock()
        mock_result = Mock()
        mock_result.content = [Mock(text="invalid json", type="text")]
        mock_client_instance.call_tool.return_value = mock_result

        mock_client_class.return_value = mock_client_instance
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        result = await state.proxy_to_external("test_tool")

        assert result is not None
        assert result["status"] == "error"
        assert "Invalid JSON response" in result["message"]

    @pytest.mark.asyncio
    async def test_proxy_standalone_returns_none(self):
        """Test proxy returns None immediately in STANDALONE mode."""
        state = ServerState(mode=StartupMode.STANDALONE)
        result = await state.proxy_to_external("test_tool", {"param": "value"})
        assert result is None


class TestViewerDetectionAndSelection:
    """Test detect_viewers behavior."""

    @pytest.mark.asyncio
    async def test_detect_viewers_no_viewers(self):
        """Test detecting viewers when none exist (STANDALONE mode)."""
        from napari_mcp import server as napari_mcp_server

        # In STANDALONE mode, external is always unavailable
        result = await napari_mcp_server.init_viewer(detect_only=True)

        assert result["status"] == "ok"
        assert result["viewers"]["external"]["available"] is False
        assert result["viewers"]["local"]["available"] is True
        assert result["viewers"]["local"]["type"] == "not_initialized"

    @pytest.mark.asyncio
    @patch("fastmcp.Client")
    async def test_detect_viewers_with_external(self, mock_client_class):
        """Test detecting viewers with external available."""
        from napari_mcp import server as napari_mcp_server
        from napari_mcp.server import create_server

        # Create state in AUTO_DETECT mode
        state = ServerState(mode=StartupMode.AUTO_DETECT)
        napari_mcp_server._state = state
        create_server(state)

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {
                        "session_type": "napari_bridge_session",
                        "bridge_port": 9999,
                        "viewer": {"title": "External"},
                    }
                )
            )
        ]
        mock_client.call_tool.return_value = mock_result

        result = await napari_mcp_server.init_viewer(detect_only=True)

        assert result["status"] == "ok"
        assert result["viewers"]["external"]["available"] is True
        assert result["viewers"]["external"]["type"] == "napari_bridge"
        assert result["viewers"]["external"]["port"] == 9999

    # Selection API removed; auto-detection is covered by detect_viewers tests above

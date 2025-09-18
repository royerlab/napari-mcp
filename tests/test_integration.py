"""Integration tests for napari-mcp with external viewer."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from napari_mcp import server as napari_mcp_server


class TestEndToEndIntegration:
    """Test end-to-end integration between main server and bridge."""

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_execute_code_via_proxy(self, mock_client_class):
        """Test executing code through proxy to external viewer."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock successful code execution
        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {"status": "ok", "result_repr": "42", "stdout": "", "stderr": ""}
                )
            )
        ]
        mock_client.call_tool.return_value = mock_result
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock the Client class instead of global variable
        with patch("napari_mcp.server.Client", return_value=mock_client):
            result = await napari_mcp_server.execute_code("21 * 2")

        assert result["status"] == "ok"
        assert result["result_repr"] == "42"

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_list_layers_via_proxy(self, mock_client_class):
        """Test listing layers through proxy."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock layer list response - _proxy_to_external returns the parsed JSON directly
        mock_layers = [
            {"name": "Layer1", "type": "Image"},
            {"name": "Layer2", "type": "Labels"},
        ]
        mock_result = Mock()
        mock_result.content = [Mock(text=json.dumps(mock_layers))]
        mock_client.call_tool.return_value = mock_result
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        result = await napari_mcp_server.list_layers()

        assert len(result) == 2
        assert result[0]["name"] == "Layer1"
        assert result[1]["name"] == "Layer2"

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client", side_effect=Exception("Connection refused"))
    async def test_fallback_to_local_on_proxy_failure(self, _):
        """Test fallback to local viewer when proxy fails."""
        # Mock local viewer
        mock_viewer = Mock()
        mock_viewer.layers = []

        with (
            patch("napari_mcp.server._ensure_viewer", return_value=mock_viewer),
            patch("napari_mcp.server._viewer_lock", asyncio.Lock()),
        ):
            result = await napari_mcp_server.list_layers()

        # Should get empty list from local viewer
        assert result == []

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_init_viewer_with_external(self, mock_client_class):
        """Test initializing viewer with external preference."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock session info
        mock_result = Mock()
        mock_info = {
            "session_type": "napari_bridge_session",
            "viewer": {"title": "External Viewer", "layer_names": ["Layer1", "Layer2"]},
            "bridge_port": 9999,
        }
        mock_result.content = [Mock(text=json.dumps(mock_info))]
        mock_client.call_tool.return_value = mock_result
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Test init_viewer auto-detects external when available (port can be provided)
        with patch("napari_mcp.server._viewer_lock", asyncio.Lock()):
            result = await napari_mcp_server.init_viewer(port=9999)

        assert result["status"] == "ok"
        assert result["viewer_type"] == "external"
        assert result["title"] == "External Viewer"
        assert result["layers"] == ["Layer1", "Layer2"]
        assert result["port"] == 9999

    @pytest.mark.asyncio
    async def test_init_viewer_with_local(self):
        """Test initializing viewer with local preference."""
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

        with (
            patch("napari_mcp.server._detect_external_viewer", return_value=(None, None)),
            patch("napari_mcp.server._ensure_viewer", return_value=mock_viewer),
            patch("napari_mcp.server._viewer_lock", asyncio.Lock()),
            patch("napari_mcp.server._process_events"),
        ):
            result = await napari_mcp_server.init_viewer()

        assert result["status"] == "ok"
        assert result["viewer_type"] == "local"
        assert result["title"] == "Local Viewer"


class TestBridgeWidget:
    """Test the bridge widget integration."""

    def test_widget_initialization(self, make_napari_viewer, qtbot):
        """Test widget can be initialized with viewer."""
        viewer = make_napari_viewer()
        viewer.title = "Test Viewer"

        from napari_mcp.widget import MCPControlWidget

        widget = MCPControlWidget(napari_viewer=viewer)
        qtbot.addWidget(widget)  # Add widget to qtbot for proper cleanup
        assert widget.viewer == viewer
        assert widget.port == 9999
        assert widget.server is None

    def test_widget_initialization_without_viewer(self, make_napari_viewer, qtbot):
        """Test widget uses current_viewer when no viewer provided."""
        viewer = make_napari_viewer()
        viewer.title = "Current Viewer"

        # Patch napari.current_viewer to return our viewer
        import napari

        with patch.object(napari, "current_viewer", return_value=viewer):
            from napari_mcp.widget import MCPControlWidget

            widget = MCPControlWidget()
            qtbot.addWidget(widget)
            assert widget.viewer == viewer

    def test_widget_initialization_no_viewer_error(self, qtbot):
        """Test widget raises error when no viewer available."""
        # Patch napari.current_viewer to return None
        import napari

        with patch.object(napari, "current_viewer", return_value=None):
            from napari_mcp.widget import MCPControlWidget

            with pytest.raises(RuntimeError, match="No napari viewer found"):
                MCPControlWidget()

    @patch("napari_mcp.widget.NapariBridgeServer")
    def test_widget_start_server(self, mock_server_class, make_napari_viewer, qtbot):
        """Test starting server from widget."""
        viewer = make_napari_viewer()
        mock_server = Mock()
        mock_server.start.return_value = True
        mock_server.is_running = True
        mock_server_class.return_value = mock_server

        from napari_mcp.widget import MCPControlWidget

        widget = MCPControlWidget(napari_viewer=viewer)
        qtbot.addWidget(widget)
        widget._start_server()

        assert widget.server == mock_server
        mock_server.start.assert_called_once()
        assert widget.start_button.isEnabled() is False
        assert widget.stop_button.isEnabled() is True

    @patch("napari_mcp.widget.NapariBridgeServer")
    def test_widget_stop_server(self, mock_server_class, make_napari_viewer, qtbot):
        """Test stopping server from widget."""
        viewer = make_napari_viewer()
        mock_server = Mock()
        mock_server.stop.return_value = True
        mock_server.is_running = False

        from napari_mcp.widget import MCPControlWidget

        widget = MCPControlWidget(napari_viewer=viewer)
        qtbot.addWidget(widget)
        widget.server = mock_server
        widget._stop_server()

        mock_server.stop.assert_called_once()
        assert widget.start_button.isEnabled() is True
        assert widget.stop_button.isEnabled() is False


class TestProxyPatterns:
    """Test various proxy patterns and edge cases."""

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_add_image_with_path_via_proxy(self, mock_client_class):
        """Test adding image with file path through proxy."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {"status": "ok", "name": "test_image", "shape": [512, 512, 3]}
                )
            )
        ]
        mock_client.call_tool.return_value = mock_result
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("napari_mcp.server.Client", return_value=mock_client):
            result = await napari_mcp_server.add_image(
                path="/path/to/image.png", name="test", colormap="viridis"
            )

        assert result["status"] == "ok"
        assert result["name"] == "test_image"
        assert result["shape"] == [512, 512, 3]

        # Verify correct parameters were passed
        mock_client.call_tool.assert_called_once()
        call_args = mock_client.call_tool.call_args
        assert call_args[0][0] == "add_image"
        assert call_args[0][1]["path"] == "/path/to/image.png"
        assert call_args[0][1]["name"] == "test"
        assert call_args[0][1]["colormap"] == "viridis"

    @pytest.mark.asyncio
    @patch("napari_mcp.server.Client")
    async def test_screenshot_via_proxy(self, mock_client_class):
        """Test taking screenshot through proxy."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock base64 screenshot data
        mock_result = Mock()
        mock_screenshot = {
            "mime_type": "image/png",
            "base64_data": (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN"
                "kYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
            ),
        }
        mock_result.content = [Mock(text=json.dumps(mock_screenshot))]
        mock_client.call_tool.return_value = mock_result
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("napari_mcp.server.Client", return_value=mock_client):
            result = await napari_mcp_server.screenshot(canvas_only=True)

        assert result["mime_type"] == "image/png"
        assert len(result["base64_data"]) > 0
        mock_client.call_tool.assert_called_once_with(
            "screenshot", {"canvas_only": True}
        )

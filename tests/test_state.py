"""Tests for napari_mcp.state.ServerState and napari_mcp.viewer_protocol."""

from unittest.mock import patch

import pytest

from napari_mcp.state import ServerState, StartupMode


class TestServerState:
    """Test ServerState initialization and methods."""

    def test_default_standalone_mode(self):
        state = ServerState()
        assert state.mode == StartupMode.STANDALONE
        assert state.viewer is None
        assert state.exec_globals == {}
        assert state.output_storage == {}
        assert state.next_output_id == 1
        assert state.window_close_connected is False
        assert state.gui_executor is None

    def test_auto_detect_mode(self):
        state = ServerState(mode=StartupMode.AUTO_DETECT, bridge_port=1234)
        assert state.mode == StartupMode.AUTO_DETECT
        assert state.bridge_port == 1234

    def test_default_bridge_port_from_env(self):
        with patch.dict("os.environ", {"NAPARI_MCP_BRIDGE_PORT": "5555"}):
            state = ServerState()
            assert state.bridge_port == 5555

    def test_gui_execute_without_executor(self):
        state = ServerState()
        result = state.gui_execute(lambda: 42)
        assert result == 42

    def test_gui_execute_with_executor(self):
        state = ServerState()
        calls = []
        state.gui_executor = lambda op: calls.append("called") or op()
        state.gui_execute(lambda: 42)
        assert calls == ["called"]

    @pytest.mark.asyncio
    async def test_store_output(self):
        state = ServerState()
        oid = await state.store_output("test_tool", stdout="hello", stderr="")
        assert oid == "1"
        assert "1" in state.output_storage
        assert state.output_storage["1"]["stdout"] == "hello"
        assert state.output_storage["1"]["tool_name"] == "test_tool"
        assert state.next_output_id == 2

    @pytest.mark.asyncio
    async def test_store_output_eviction(self):
        state = ServerState()
        state.max_output_items = 2
        await state.store_output("t", stdout="a")
        await state.store_output("t", stdout="b")
        await state.store_output("t", stdout="c")
        assert len(state.output_storage) == 2
        assert "1" not in state.output_storage
        assert "2" in state.output_storage
        assert "3" in state.output_storage

    @pytest.mark.asyncio
    async def test_proxy_standalone_returns_none(self):
        state = ServerState(mode=StartupMode.STANDALONE)
        result = await state.proxy_to_external("some_tool")
        assert result is None

    @pytest.mark.asyncio
    async def test_detect_external_standalone_returns_false(self):
        state = ServerState(mode=StartupMode.STANDALONE)
        found, info = await state.detect_external_viewer()
        assert found is False
        assert info is None


class TestRequestShutdown:
    """Test ServerState.request_shutdown lifecycle."""

    def test_initial_shutdown_state(self):
        state = ServerState()
        assert state._shutdown_requested is False
        assert state._event_loop is None

    def test_shutdown_without_event_loop(self):
        """request_shutdown should not raise when no event loop is set."""
        state = ServerState()
        state.request_shutdown()
        assert state._shutdown_requested is True

    def test_shutdown_is_idempotent(self):
        """Calling request_shutdown twice should only act once."""
        state = ServerState()
        state.request_shutdown()
        assert state._shutdown_requested is True
        # Second call should be a no-op (no error)
        state.request_shutdown()
        assert state._shutdown_requested is True

    def test_shutdown_with_closed_loop(self):
        """request_shutdown should not raise when the loop is already closed."""
        import asyncio

        loop = asyncio.new_event_loop()
        loop.close()
        state = ServerState()
        state._event_loop = loop
        # Should not raise
        state.request_shutdown()
        assert state._shutdown_requested is True

    def test_shutdown_schedules_delayed_stop(self):
        """request_shutdown should schedule a delayed loop.stop via call_later."""
        import asyncio
        from unittest.mock import MagicMock

        loop = MagicMock(spec=asyncio.AbstractEventLoop)
        loop.is_closed.return_value = False

        state = ServerState()
        state._event_loop = loop

        state.request_shutdown()

        loop.call_soon_threadsafe.assert_called_once()
        # The argument should be a lambda that calls call_later
        scheduled_fn = loop.call_soon_threadsafe.call_args[0][0]
        scheduled_fn()
        loop.call_later.assert_called_once()
        delay_arg, stop_fn = loop.call_later.call_args[0]
        assert delay_arg == 1.0
        assert stop_fn is loop.stop


class TestServerModuleInit:
    """Test that server module initializes correctly at import time."""

    def test_tools_available_at_import(self):
        from napari_mcp import server as srv

        assert hasattr(srv, "list_layers")
        assert hasattr(srv, "execute_code")
        assert hasattr(srv, "screenshot")
        assert callable(srv.list_layers)

    def test_state_exists_at_import(self):
        from napari_mcp import server as srv

        assert srv._state is not None

    def test_server_instance_exists_at_import(self):
        from napari_mcp import server as srv

        assert hasattr(srv, "server")


class TestServerStateEnvFallbacks:
    """Test environment variable parsing edge cases."""

    def test_malformed_max_output_items_env(self, monkeypatch):
        monkeypatch.setenv("NAPARI_MCP_MAX_OUTPUT_ITEMS", "abc")
        state = ServerState()
        assert state.max_output_items == 1000  # fallback

    @pytest.mark.asyncio
    async def test_external_session_information_not_bridge(self, monkeypatch):
        """external_session_information returns error when response is not a bridge session."""
        from unittest.mock import AsyncMock, MagicMock

        state = ServerState(mode=StartupMode.AUTO_DETECT)

        mock_content_item = MagicMock()
        mock_content_item.type = "text"
        mock_content_item.text = '{"session_type": "something_else"}'

        mock_result = MagicMock()
        mock_result.content = [mock_content_item]

        mock_client_instance = AsyncMock()
        mock_client_instance.call_tool = AsyncMock(return_value=mock_result)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("fastmcp.Client", return_value=mock_client_instance):
            result = await state.external_session_information()

        assert result["status"] == "error"
        assert "Failed to get session information" in result["message"]


class TestViewerProtocol:
    """Test ViewerProtocol structural typing."""

    def test_protocol_is_importable(self):
        from napari_mcp.viewer_protocol import ViewerProtocol

        assert ViewerProtocol is not None

    def test_protocol_defines_expected_methods(self):
        from napari_mcp.viewer_protocol import ViewerProtocol

        for method_name in (
            "add_image",
            "add_labels",
            "add_points",
            "screenshot",
            "reset_view",
            "close",
        ):
            assert hasattr(ViewerProtocol, method_name), (
                f"Missing method: {method_name}"
            )

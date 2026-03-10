"""Tests for napari-mcp-bridge server functionality."""

from unittest.mock import Mock, patch

import numpy as np
import pytest
from qtpy.QtCore import QThread

from napari_mcp.bridge_server import NapariBridgeServer, QtBridge


@pytest.fixture
def bridge_server(make_napari_viewer):
    """Create a bridge server instance with proper cleanup."""
    viewer = make_napari_viewer()
    viewer.title = "Test Viewer"  # Set expected title
    server = NapariBridgeServer(viewer, port=9999)
    yield server
    # Ensure server is stopped after test
    try:
        server.stop()
    except Exception:
        pass  # Cleanup, ignore errors


class TestNapariBridgeServer:
    """Test the bridge server basic functionality."""

    def test_initialization(self, make_napari_viewer):
        """Test server initialization."""
        viewer = make_napari_viewer()
        server = NapariBridgeServer(viewer, port=8888)
        assert server.viewer == viewer
        assert server.port == 8888
        assert server.server is not None
        assert not server.is_running

    @patch("threading.Thread")
    def test_start_stop(self, mock_thread_class, bridge_server):
        """Test starting and stopping the server."""
        # Mock the thread to avoid actually starting servers
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        mock_thread_class.return_value = mock_thread

        # Start server
        result = bridge_server.start()
        assert result is True
        # Manually set running state since we mocked the thread
        bridge_server.thread = mock_thread
        mock_thread.is_alive.return_value = True
        assert bridge_server.is_running

        # Starting again should return False
        result = bridge_server.start()
        assert result is False

        # Stop server
        bridge_server.thread = None  # Simulate thread stopped
        result = bridge_server.stop()
        assert result is True
        assert not bridge_server.is_running

    def test_server_has_tools_registered(self, make_napari_viewer):
        """Test that server has tools registered after setup."""
        viewer = make_napari_viewer()
        server = NapariBridgeServer(viewer)
        assert hasattr(server.server, "tool")

    def test_lifecycle_tools_excluded(self, make_napari_viewer):
        """Bridge server must NOT expose viewer lifecycle tools.

        When running from napari, the viewer is managed by napari itself.
        Allowing an agent to close/init/detect viewers would be disruptive.
        """
        viewer = make_napari_viewer()
        server = NapariBridgeServer(viewer)
        tool_names = set(server.server._tool_manager._tools.keys())
        for excluded in ("close_viewer", "init_viewer"):
            assert excluded not in tool_names, (
                f"{excluded} should not be available in bridge mode"
            )
        # Sanity: other tools should still be present
        for expected in (
            "session_information",
            "execute_code",
            "list_layers",
            "screenshot",
        ):
            assert expected in tool_names, (
                f"{expected} should be available in bridge mode"
            )


class TestQtBridge:
    """Test the Qt bridge for thread safety."""

    def test_initialization(self, qtbot):
        """Test Qt bridge initialization."""
        bridge = QtBridge()
        assert bridge is not None

    def test_run_in_main_thread(self, qtbot):
        """Test running operation in main thread."""
        from threading import Thread

        bridge = QtBridge()
        results = []

        def test_operation():
            results.append("executed")
            return "test_result"

        def run_from_thread():
            result = bridge.run_in_main_thread(test_operation)
            results.append(result)

        thread = Thread(target=run_from_thread)
        thread.start()
        qtbot.wait(100)
        thread.join(timeout=1.0)

        assert "executed" in results
        assert "test_result" in results

    @patch("napari_mcp.bridge_server.Future")
    def test_operation_execution(self, mock_future_class):
        """Test operation execution mechanism."""
        bridge = QtBridge()
        mock_future = Mock()
        mock_future_class.return_value = mock_future

        test_result = "test_result"
        operation = Mock(return_value=test_result)

        bridge._execute_operation(operation, mock_future)
        mock_future.set_result.assert_called_once_with(test_result)

    @patch("napari_mcp.bridge_server.Future")
    def test_operation_exception(self, mock_future_class):
        """Test exception handling in operation execution."""
        bridge = QtBridge()
        mock_future = Mock()
        mock_future_class.return_value = mock_future

        test_error = ValueError("Test error")
        operation = Mock(side_effect=test_error)

        bridge._execute_operation(operation, mock_future)
        mock_future.set_exception.assert_called_once_with(test_error)


class TestBridgeServerIntegration:
    """Integration tests for the bridge server."""

    def test_viewer_operations(self, make_napari_viewer):
        """Test that viewer operations are properly set up."""
        viewer = make_napari_viewer()
        server = NapariBridgeServer(viewer)
        assert server.viewer == viewer
        assert isinstance(server.state.exec_globals, dict)

    def test_multiple_server_instances(self, make_napari_viewer):
        """Test creating multiple server instances with different ports."""
        viewer1 = make_napari_viewer()
        server1 = NapariBridgeServer(viewer1, port=9998)
        viewer2 = make_napari_viewer()
        server2 = NapariBridgeServer(viewer2, port=9999)

        assert server1.port == 9998
        assert server2.port == 9999
        assert server1.server != server2.server

    @patch("threading.Thread")
    def test_start_stop_threading(self, mock_thread_class, make_napari_viewer):
        """Test server start/stop with threading."""
        viewer = make_napari_viewer()
        server = NapariBridgeServer(viewer)

        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        mock_thread_class.return_value = mock_thread

        result = server.start()
        assert result is True
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

        mock_thread.is_alive.return_value = True
        result = server.start()
        assert result is False

        server.thread = mock_thread
        server.loop = Mock()
        result = server.stop()
        assert result is True
        mock_thread.join.assert_called_once_with(timeout=2)


class TestBridgeServerTools:
    """Test the MCP tools exposed by the bridge server."""

    @pytest.mark.asyncio
    async def test_session_information_tool(self, bridge_server):
        """Test session_information tool."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "session_information":
                    result = await tool.fn()
                    break
            else:
                pytest.fail("session_information tool not found")

            assert result["status"] == "ok"
            assert result["session_type"] == "napari_bridge_session"
            assert result["bridge_port"] == 9999
            assert "viewer" in result
            assert result["viewer"]["title"] == "Test Viewer"

    @pytest.mark.asyncio
    async def test_list_layers_empty(self, bridge_server):
        """Test list_layers with no layers."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
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
    async def test_list_layers_with_layers(self, bridge_server):
        """Test list_layers with some layers."""
        bridge_server.viewer.add_image(
            np.random.random((100, 100)), name="Layer 1", colormap="viridis"
        )
        bridge_server.viewer.add_labels(
            np.ones((100, 100), dtype=np.uint8),
            name="Layer 2",
            visible=False,
            opacity=0.5,
        )

        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
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
    async def test_execute_code_simple(self, bridge_server):
        """Test execute_code with simple Python code."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
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
    async def test_execute_code_with_viewer(self, bridge_server):
        """Test execute_code with viewer access."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
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
    async def test_execute_code_error(self, bridge_server):
        """Test execute_code with error."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("1/0")
                    break

            assert result["status"] == "error"
            assert "ZeroDivisionError" in result["stderr"]

    @pytest.mark.asyncio
    async def test_screenshot_tool(self, bridge_server):
        """Test screenshot tool returns PNG data."""
        # Add an image so there's something to screenshot
        bridge_server.viewer.add_image(np.random.random((50, 50)), name="test_img")

        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "screenshot":
                    result = await tool.fn(True)
                    break
            else:
                pytest.fail("screenshot tool not found")

            # Result is an ImageContent object from FastMCP
            assert hasattr(result, "mimeType") or isinstance(result, dict)
            if hasattr(result, "mimeType"):
                assert result.mimeType.lower() in ("png", "image/png")
                assert result.data is not None
                assert len(result.data) > 0
            else:
                assert result["mime_type"] == "image/png"
                assert len(result["base64_data"]) > 0


class TestBridgeTimeoutBehavior:
    """Test timeout handling in the bridge server."""

    @pytest.mark.asyncio
    async def test_execute_code_timeout_returns_error_dict(self, bridge_server):
        """Test that execute_code returns a structured error on timeout."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:
            mock_run.side_effect = TimeoutError("timed out")

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("import time; time.sleep(9999)")
                    break
            else:
                pytest.fail("execute_code tool not found")

            assert result["status"] == "error"
            assert "timed out" in result["stderr"]
            assert "600s" in result["stderr"]
            assert result["stdout"] == ""

    def test_run_in_main_thread_timeout_message(self, qtbot):
        """Test that QtBridge timeout produces an actionable error message."""
        bridge = QtBridge()
        mock_future = Mock()
        mock_future.result.side_effect = TimeoutError()

        with (
            patch("napari_mcp.bridge_server.Future", return_value=mock_future),
            patch.object(QThread, "currentThread") as mock_ct,
        ):
            # Ensure we take the cross-thread path
            mock_ct.return_value = Mock()

            with pytest.raises(
                TimeoutError, match="napari bridge operation timed out after 10s"
            ):
                bridge.run_in_main_thread(lambda: None, timeout=10.0)

    def test_run_in_main_thread_custom_timeout_forwarded(self, qtbot):
        """Test that custom timeout value is forwarded to Future.result()."""
        bridge = QtBridge()
        mock_future = Mock()
        mock_future.result.return_value = "ok"

        with (
            patch("napari_mcp.bridge_server.Future", return_value=mock_future),
            patch.object(QThread, "currentThread") as mock_ct,
        ):
            mock_ct.return_value = Mock()

            bridge.run_in_main_thread(lambda: None, timeout=42.0)
            mock_future.result.assert_called_once_with(timeout=42.0)

    def test_run_in_main_thread_default_timeout(self, qtbot):
        """Test that default timeout is 300s (5 minutes)."""
        bridge = QtBridge()
        mock_future = Mock()
        mock_future.result.return_value = "ok"

        with (
            patch("napari_mcp.bridge_server.Future", return_value=mock_future),
            patch.object(QThread, "currentThread") as mock_ct,
        ):
            mock_ct.return_value = Mock()

            bridge.run_in_main_thread(lambda: None)
            mock_future.result.assert_called_once_with(timeout=300.0)


class TestBridgeServerLayerOperations:
    """Test layer manipulation operations."""

    @pytest.mark.asyncio
    async def test_add_image_from_data(self, bridge_server):
        """Test adding an image from data."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            test_data = [[1, 2], [3, 4]]

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "add_layer":
                    result = await tool.fn(
                        layer_type="image", data=test_data, name="test", colormap="gray"
                    )
                    break

            assert result["status"] == "ok"
            assert result["name"] == "test"
            assert result["shape"] == [2, 2]

            assert "test" in bridge_server.viewer.layers
            assert bridge_server.viewer.layers["test"].data.shape == (2, 2)
            assert bridge_server.viewer.layers["test"].colormap.name == "gray"

    @pytest.mark.asyncio
    async def test_add_points_from_data(self, bridge_server):
        """Test adding points via bridge add_layer — verifies type normalization."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            tool = tools["add_layer"]
            result = await tool.fn(
                layer_type="points", data=[[1, 2], [3, 4]], name="pts"
            )

            assert result["status"] == "ok"
            assert result["n_points"] == 2
            assert "pts" in bridge_server.viewer.layers

    @pytest.mark.asyncio
    async def test_remove_layer(self, bridge_server):
        """Test removing a layer."""
        import numpy as np

        layer = bridge_server.viewer.add_points(np.array([[0, 0]]), name="test_layer")

        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "remove_layer":
                    result = await tool.fn(layer)
                    break

            assert result["status"] == "removed"
            assert "test_layer" not in [lyr.name for lyr in bridge_server.viewer.layers]

    @pytest.mark.asyncio
    async def test_remove_layer_not_found(self, bridge_server):
        """Test removing a non-existent layer."""
        bridge_server.viewer.layers.__contains__ = Mock(return_value=False)

        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "remove_layer":
                    result = await tool.fn("nonexistent")
                    break

            assert result["status"] == "not_found"
            assert result["name"] == "nonexistent"


class TestBridgeAddLayerValidation:
    """Test bridge add_layer validation matches standalone server."""

    @pytest.mark.asyncio
    async def test_path_rejected_for_non_image_types(self, bridge_server):
        """Bridge add_layer should reject path for non-image/labels types."""
        tools = await bridge_server.server.get_tools()
        tool = tools["add_layer"]

        result = await tool.fn(layer_type="points", path="/some/file.csv")
        assert result["status"] == "error"
        assert "only supported for image/labels" in result["message"]

    @pytest.mark.asyncio
    async def test_surface_requires_data_var(self, bridge_server):
        """Bridge add_layer should require data_var for surface layers."""
        tools = await bridge_server.server.get_tools()
        tool = tools["add_layer"]

        result = await tool.fn(layer_type="surface")
        assert result["status"] == "error"
        assert "data_var" in result["message"]
        assert "surface" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_multiple_data_sources_rejected(self, bridge_server):
        """Bridge add_layer should reject multiple data sources."""
        tools = await bridge_server.server.get_tools()
        tool = tools["add_layer"]

        result = await tool.fn(
            layer_type="image", data=[[1, 2]], data_var="x", path="/nonexistent/img.tif"
        )
        assert result["status"] == "error"
        assert "only ONE" in result["message"]

    @pytest.mark.asyncio
    async def test_unknown_layer_type_rejected(self, bridge_server):
        """Bridge add_layer should reject unknown layer types."""
        tools = await bridge_server.server.get_tools()
        tool = tools["add_layer"]

        result = await tool.fn(layer_type="mesh", data=[[1, 2]])
        assert result["status"] == "error"
        assert "Unknown" in result["message"]


class TestBridgeExecuteCodeParity:
    """Test that bridge execute_code matches server response shape."""

    @pytest.mark.asyncio
    async def test_execute_code_returns_output_id(self, bridge_server):
        """Test that bridge execute_code returns output_id for later retrieval."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("42")
                    break

            assert "output_id" in result
            assert result["output_id"] == "1"

            # Verify output is retrievable via read_output
            for name, tool in tools.items():
                if name == "read_output":
                    stored = await tool.fn(result["output_id"])
                    break
            assert stored["status"] == "ok"
            assert stored["tool_name"] == "execute_code"

    @pytest.mark.asyncio
    async def test_execute_code_line_limit_truncation(self, bridge_server):
        """Test that bridge execute_code truncates output with line_limit."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn(
                        "for i in range(50): print(f'line {i}')",
                        line_limit=5,
                    )
                    break

            assert result["status"] == "ok"
            assert result["truncated"] is True
            assert "output_id" in result
            # stdout should have only 5 lines
            assert result["stdout"].count("\n") <= 5

    @pytest.mark.asyncio
    async def test_execute_code_unlimited_output(self, bridge_server):
        """Test that bridge execute_code with line_limit=-1 returns all output."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("print('hello')", line_limit=-1)
                    break

            assert result["status"] == "ok"
            assert "warning" in result
            assert "large number of tokens" in result["warning"]


class TestBridgeExecNamespace:
    """Test that bridge execute_code injects correct namespace."""

    @pytest.mark.asyncio
    async def test_napari_module_available(self, bridge_server):
        """Regression: bridge used to inject napari=None instead of the real module."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("type(napari).__name__")
                    break
            else:
                pytest.fail("execute_code tool not found")

            assert result["status"] == "ok"
            assert result["result_repr"] == "'module'"

    @pytest.mark.asyncio
    async def test_np_available(self, bridge_server):
        """numpy should be available as 'np' in the exec namespace."""
        with patch.object(bridge_server.qt_bridge, "run_in_main_thread") as mock_run:

            def execute_directly(func, **kwargs):
                return func()

            mock_run.side_effect = execute_directly

            tools = await bridge_server.server.get_tools()
            for name, tool in tools.items():
                if name == "execute_code":
                    result = await tool.fn("int(np.array([1, 2, 3]).sum())")
                    break

            assert result["status"] == "ok"
            assert result["result_repr"] == "6"


class TestBridgeServerState:
    """Test that bridge server properly creates its own state."""

    def test_bridge_creates_standalone_state(self, make_napari_viewer):
        from napari_mcp.state import StartupMode

        viewer = make_napari_viewer()
        bridge = NapariBridgeServer(viewer, port=9876)
        assert bridge.state.mode == StartupMode.STANDALONE
        assert bridge.state.viewer is viewer
        assert bridge.state.gui_executor is not None
        assert bridge.port == 9876

    @pytest.mark.asyncio
    async def test_bridge_does_not_proxy(self, make_napari_viewer):
        viewer = make_napari_viewer()
        bridge = NapariBridgeServer(viewer)
        result = await bridge.state.proxy_to_external("any_tool")
        assert result is None

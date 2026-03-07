"""Integration tests for napari-mcp: multi-step workflows and concurrent calls."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from napari_mcp import server as napari_mcp_server


class TestEndToEndIntegration:
    """Test end-to-end integration between main server and bridge."""

    @pytest.mark.asyncio
    async def test_execute_code_via_proxy(self):
        """Test execute_code falls through to local when proxy is unavailable.

        In STANDALONE mode (set by conftest), proxy always returns None.
        """
        result = await napari_mcp_server.execute_code("21 * 2")

        assert result["status"] == "ok"
        assert result["result_repr"] == "42"

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
            patch(
                "napari_mcp.qt_helpers.ensure_viewer",
                return_value=mock_viewer,
            ),
            patch.object(napari_mcp_server, "ensure_viewer", return_value=mock_viewer),
            patch("napari_mcp.qt_helpers.process_events"),
        ):
            result = await napari_mcp_server.init_viewer()

        assert result["status"] == "ok"
        assert result["viewer_type"] == "local"
        assert result["title"] == "Local Viewer"


class TestMultiStepWorkflows:
    """Test realistic multi-step tool workflows."""

    @pytest.mark.asyncio
    async def test_execute_code_adds_layer_visible_via_tools(self, make_napari_viewer):
        """execute_code adds a layer, then list_layers and session_information see it."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer

        code = (
            "import numpy as np; viewer.add_image(np.zeros((10, 10)), name='from_code')"
        )
        res = await napari_mcp_server.execute_code(code)
        assert res["status"] == "ok"

        layers = await napari_mcp_server.list_layers()
        assert any(lyr["name"] == "from_code" for lyr in layers)

        sess = await napari_mcp_server.session_information()
        assert "from_code" in sess["viewer"]["layer_names"]

    @pytest.mark.asyncio
    async def test_output_storage_across_multiple_executions(self, make_napari_viewer):
        """Multiple execute_code calls store separate outputs, all retrievable."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer
        napari_mcp_server._state.output_storage.clear()
        napari_mcp_server._state.next_output_id = 1

        res1 = await napari_mcp_server.execute_code(
            "for i in range(100): print(f'batch1_{i}')", line_limit=5
        )
        assert res1["status"] == "ok"
        assert res1.get("truncated") is True
        oid1 = res1["output_id"]

        res2 = await napari_mcp_server.execute_code(
            "for i in range(50): print(f'batch2_{i}')", line_limit=5
        )
        assert res2["status"] == "ok"
        oid2 = res2["output_id"]

        assert oid1 != oid2

        full1 = await napari_mcp_server.read_output(oid1)
        assert full1["total_lines"] == 100

        full2 = await napari_mcp_server.read_output(oid2)
        assert full2["total_lines"] == 50


class TestConcurrentToolCalls:
    """Test concurrent tool access doesn't corrupt state."""

    @pytest.mark.asyncio
    async def test_concurrent_list_layers(self, make_napari_viewer):
        """Multiple simultaneous list_layers calls return consistent results."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer
        viewer.add_points([[1, 1]], name="pts")

        results = await asyncio.gather(
            napari_mcp_server.list_layers(),
            napari_mcp_server.list_layers(),
            napari_mcp_server.list_layers(),
        )
        for r in results:
            assert isinstance(r, list)
            assert any(lyr["name"] == "pts" for lyr in r)

    @pytest.mark.asyncio
    async def test_concurrent_execute_code(self, make_napari_viewer):
        """Concurrent execute_code calls all return valid results."""
        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer

        results = await asyncio.gather(
            napari_mcp_server.execute_code("1 + 1"),
            napari_mcp_server.execute_code("2 + 2"),
            napari_mcp_server.execute_code("3 + 3"),
        )
        expected = ["2", "4", "6"]
        for r, exp in zip(results, expected, strict=False):
            assert r["status"] == "ok"
            assert r["result_repr"] == exp

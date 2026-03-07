"""Performance and benchmark tests for napari-mcp."""

import time
from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import Mock

import numpy as np
import pytest

# Performance test configuration
PERFORMANCE_THRESHOLD = {
    "screenshot": 0.5,  # 500ms
}


@contextmanager
def measure_time(operation: str) -> Generator[dict, None, None]:
    """Context manager to measure operation time."""
    result = {"duration": 0, "operation": operation}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["duration"] = time.perf_counter() - start


class TestPerformanceBenchmarks:
    """Performance benchmark tests that exercise real code."""

    @pytest.mark.benchmark
    def test_memory_usage_layer_operations(self):
        """Test memory usage during layer operations."""
        import tracemalloc

        tracemalloc.start()

        # Baseline memory
        snapshot1 = tracemalloc.take_snapshot()

        # Allocate real numpy arrays (not just mocks)
        arrays = []
        for _ in range(10):
            data = np.zeros((1000, 1000, 3), dtype=np.uint8)  # ~3MB each
            arrays.append(data)

        snapshot2 = tracemalloc.take_snapshot()

        # Calculate memory difference
        stats = snapshot2.compare_to(snapshot1, "lineno")
        total_memory = sum(stat.size_diff for stat in stats) / 1024 / 1024  # MB

        # Clean up
        del arrays
        tracemalloc.stop()

        # Memory should be reasonable (less than 50MB for 10 layers)
        assert total_memory < 50, f"Excessive memory usage: {total_memory:.2f}MB"

    @pytest.mark.benchmark
    def test_screenshot_encoding_performance(self):
        """Test screenshot PNG encoding performance with real PIL."""
        sizes = [(100, 100), (800, 600), (1920, 1080)]

        for size in sizes:
            mock_data = np.zeros((*size, 4), dtype=np.uint8)

            with measure_time(f"screenshot_{size}") as timer:
                import base64
                from io import BytesIO

                from PIL import Image

                img = Image.fromarray(mock_data[:, :, :3])
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                _ = base64.b64encode(buffer.getvalue())

            assert timer["duration"] < PERFORMANCE_THRESHOLD["screenshot"]


class TestPerformanceRegression:
    """Performance regression tests."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_regression_async_operations(self):
        """Test for performance regression in async operations."""
        from napari_mcp import server as napari_mcp_server

        mock_viewer = Mock()
        mock_viewer.layers = []  # Make layers iterable
        napari_mcp_server._state.viewer = mock_viewer
        try:
            operations = [("list_layers", napari_mcp_server.list_layers)]

            for op_name, operation in operations:
                with measure_time(op_name) as timer:
                    for _ in range(10):
                        await operation()

                avg_time = timer["duration"] / 10

                # In STANDALONE mode proxy is a no-op, so should be fast
                assert avg_time < 0.1, (
                    f"Async operation {op_name} too slow: {avg_time:.4f}s"
                )
        finally:
            napari_mcp_server._state.viewer = None


class TestExecGlobalsPersistence:
    """Test that the execution namespace persists across calls."""

    @pytest.mark.asyncio
    async def test_exec_globals_persist_across_calls(self, make_napari_viewer):
        """Variables set in one execute_code call are available in the next."""
        from napari_mcp import server as napari_mcp_server

        viewer = make_napari_viewer()
        napari_mcp_server._state.viewer = viewer

        res = await napari_mcp_server.execute_code("my_var = 42")
        assert res["status"] == "ok"

        res = await napari_mcp_server.execute_code("my_var * 2")
        assert res["status"] == "ok"
        assert res["result_repr"] == "84"

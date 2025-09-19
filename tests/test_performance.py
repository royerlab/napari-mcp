"""Performance and benchmark tests for napari-mcp."""

import asyncio
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import Mock, patch

import numpy as np
import pytest

# Removed offscreen mode - it causes segfaults

# Performance test configuration
PERFORMANCE_THRESHOLD = {
    "layer_add": 0.1,  # 100ms
    "layer_remove": 0.05,  # 50ms
    "screenshot": 0.5,  # 500ms
    "code_execution": 0.2,  # 200ms
    "viewer_init": 1.0,  # 1s
    "bulk_operations": 2.0,  # 2s
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
    """Performance benchmark tests."""

    @pytest.mark.benchmark
    def test_layer_addition_performance(self):
        """Benchmark layer addition operations."""
        mock_viewer = Mock()
        mock_viewer.layers = []
        mock_viewer.add_image = Mock(
            side_effect=lambda data, **kwargs: mock_viewer.layers.append(
                Mock(data=data)
            )
        )

        # Generate test data
        data_sizes = [(100, 100), (500, 500), (1000, 1000)]
        results = []

        for size in data_sizes:
            data = np.random.random(size)

            with measure_time(f"add_layer_{size}") as timer:
                mock_viewer.add_image(data)

            results.append(timer)
            assert timer["duration"] < PERFORMANCE_THRESHOLD["layer_add"]

        # Performance regression check
        avg_time = sum(r["duration"] for r in results) / len(results)
        assert avg_time < PERFORMANCE_THRESHOLD["layer_add"], (
            f"Layer addition too slow: {avg_time:.3f}s"
        )

    @pytest.mark.benchmark
    def test_bulk_layer_operations(self):
        """Test performance of bulk layer operations."""
        mock_viewer = Mock()
        mock_viewer.layers = []

        with measure_time("bulk_add_100_layers") as timer:
            for i in range(100):
                layer = Mock(name=f"layer_{i}")
                mock_viewer.layers.append(layer)

        assert timer["duration"] < PERFORMANCE_THRESHOLD["bulk_operations"]

        # Test bulk removal
        with measure_time("bulk_remove_50_layers") as timer:
            for _ in range(50):
                if mock_viewer.layers:
                    mock_viewer.layers.pop()

        assert timer["duration"] < PERFORMANCE_THRESHOLD["bulk_operations"] / 2

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations."""
        mock_viewer = Mock()
        mock_viewer.layers = []

        async def add_layer(index: int):
            await asyncio.sleep(0.001)  # Simulate async work
            mock_viewer.layers.append(Mock(name=f"layer_{index}"))

        with measure_time("concurrent_add_50_layers") as timer:
            tasks = [add_layer(i) for i in range(50)]
            await asyncio.gather(*tasks)

        assert timer["duration"] < 1.0  # Should complete within 1 second
        assert len(mock_viewer.layers) == 50

    @pytest.mark.benchmark
    def test_memory_usage_layer_operations(self):
        """Test memory usage during layer operations."""
        import tracemalloc

        tracemalloc.start()
        mock_viewer = Mock()
        mock_viewer.layers = []

        # Baseline memory
        snapshot1 = tracemalloc.take_snapshot()

        # Add large layers
        for _ in range(10):
            data = np.zeros((1000, 1000, 3), dtype=np.uint8)  # ~3MB each
            mock_viewer.layers.append(Mock(data=data))

        snapshot2 = tracemalloc.take_snapshot()

        # Calculate memory difference
        stats = snapshot2.compare_to(snapshot1, "lineno")
        total_memory = sum(stat.size_diff for stat in stats) / 1024 / 1024  # MB

        # Clean up
        tracemalloc.stop()

        # Memory should be reasonable (less than 50MB for 10 layers)
        assert total_memory < 50, f"Excessive memory usage: {total_memory:.2f}MB"

    @pytest.mark.benchmark
    def test_screenshot_performance(self):
        """Test screenshot generation performance."""
        mock_viewer = Mock()

        # Mock screenshot with different sizes
        sizes = [(100, 100), (800, 600), (1920, 1080)]

        for size in sizes:
            mock_data = np.zeros((*size, 4), dtype=np.uint8)
            mock_viewer.screenshot = Mock(return_value=mock_data)

            with measure_time(f"screenshot_{size}") as timer:
                result = mock_viewer.screenshot(canvas_only=True)
                # Simulate encoding
                import base64
                from io import BytesIO

                from PIL import Image

                img = Image.fromarray(result[:, :, :3])
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                _ = base64.b64encode(buffer.getvalue())  # Simulate encoding

            assert timer["duration"] < PERFORMANCE_THRESHOLD["screenshot"]


class TestScalabilityTests:
    """Scalability tests for napari-mcp."""

    @pytest.mark.slow
    def test_layer_count_scalability(self):
        """Test system behavior with many layers."""
        mock_viewer = Mock()
        mock_viewer.layers = []

        layer_counts = [10, 50, 100, 500]
        timings = []

        for count in layer_counts:
            mock_viewer.layers.clear()

            with measure_time(f"add_{count}_layers") as timer:
                for i in range(count):
                    mock_viewer.layers.append(Mock(name=f"layer_{i}"))

            timings.append((count, timer["duration"]))

        # Check for linear or better scaling
        for i in range(1, len(timings)):
            prev_count, prev_time = timings[i - 1]
            curr_count, curr_time = timings[i]

            # Time should not scale worse than O(n log n)
            expected_max_time = (
                prev_time
                * (curr_count / prev_count)
                * np.log2(curr_count / prev_count + 1)
            )

            assert curr_time < expected_max_time * 1.5, (
                f"Poor scaling: {curr_count} layers took {curr_time:.3f}s"
            )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_viewer_operations(self):
        """Test concurrent operations on multiple viewers."""
        viewers = [Mock() for _ in range(5)]

        async def operate_on_viewer(viewer, viewer_id):
            viewer.layers = []
            for i in range(20):
                await asyncio.sleep(0.001)
                viewer.layers.append(Mock(name=f"viewer_{viewer_id}_layer_{i}"))

        with measure_time("concurrent_5_viewers") as timer:
            tasks = [operate_on_viewer(v, i) for i, v in enumerate(viewers)]
            await asyncio.gather(*tasks)

        assert timer["duration"] < 2.0  # Should complete within 2 seconds

        # Verify all viewers have correct number of layers
        for viewer in viewers:
            assert len(viewer.layers) == 20

    @pytest.mark.slow
    def test_data_size_scalability(self):
        """Test performance with different data sizes."""
        mock_viewer = Mock()
        mock_viewer.add_image = Mock()

        data_sizes = [
            (100, 100),
            (500, 500),
            (1000, 1000),
            (2000, 2000),
        ]

        timings = []

        for size in data_sizes:
            data = np.random.random(size)

            with measure_time(f"process_{size}") as timer:
                mock_viewer.add_image(data)
                # Simulate processing
                _ = data.mean()
                _ = data.std()

            timings.append((np.prod(size), timer["duration"]))

        # Check scaling is not worse than O(n)
        for i in range(1, len(timings)):
            prev_pixels, prev_time = timings[i - 1]
            curr_pixels, curr_time = timings[i]

            # Linear scaling with tolerance for CI variability
            expected_time = prev_time * (curr_pixels / prev_pixels)
            # Use 3x tolerance for CI environments (was 2x)
            tolerance = 3.0 if os.environ.get("CI") else 2.0
            assert curr_time < expected_time * tolerance, (
                f"Poor data scaling: {curr_pixels} pixels took {curr_time:.3f}s"
            )


class TestPerformanceRegression:
    """Performance regression tests."""

    @pytest.fixture
    def performance_baseline(self):
        """Load or create performance baseline."""
        return {
            "layer_add": 0.05,
            "layer_remove": 0.02,
            "screenshot_small": 0.1,
            "screenshot_large": 0.3,
            "bulk_operation": 0.5,
        }

    @pytest.mark.benchmark
    def test_regression_layer_operations(self, performance_baseline):
        """Test for performance regression in layer operations."""
        mock_viewer = Mock()
        mock_viewer.layers = []

        operations = {
            "layer_add": lambda: mock_viewer.layers.append(Mock()),
            "layer_remove": lambda: mock_viewer.layers.pop()
            if mock_viewer.layers
            else None,
        }

        for op_name, operation in operations.items():
            # Prepare state
            mock_viewer.layers = [Mock() for _ in range(10)]

            # Measure operation
            with measure_time(op_name) as timer:
                for _ in range(100):
                    operation()

            avg_time = timer["duration"] / 100
            baseline = performance_baseline.get(op_name, 0.1)

            # Allow more tolerance in CI environments
            tolerance = 1.5 if os.environ.get("CI") else 1.2
            assert avg_time < baseline * tolerance, (
                f"Performance regression in {op_name}: {avg_time:.4f}s vs baseline {baseline:.4f}s"
            )

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_regression_async_operations(self, performance_baseline):
        """Test for performance regression in async operations."""
        from napari_mcp import server as napari_mcp_server

        mock_viewer = Mock()
        mock_viewer.layers = []  # Make layers iterable
        with patch("napari_mcp.server._viewer", mock_viewer):
            operations = [("list_layers", napari_mcp_server.list_layers)]

            for op_name, operation in operations:
                with measure_time(op_name) as timer:
                    for _ in range(10):
                        await operation()

                avg_time = timer["duration"] / 10

                # These should be very fast
                assert avg_time < 0.02, (
                    f"Async operation {op_name} too slow: {avg_time:.4f}s"
                )


class TestCachingPerformance:
    """Test caching and memoization performance."""

    def test_viewer_singleton_performance(self):
        """Test that viewer singleton pattern improves performance."""
        from napari_mcp import server as napari_mcp_server

        with patch("napari.Viewer", Mock()) as mock_viewer_class:
            mock_viewer_class.return_value = Mock()

            # First access - should create viewer
            with measure_time("first_viewer_access") as timer1:
                napari_mcp_server._ensure_viewer()

            # Subsequent accesses - should be cached
            timings = []
            for i in range(100):
                with measure_time(f"cached_access_{i}") as timer:
                    napari_mcp_server._ensure_viewer()
                timings.append(timer["duration"])

            avg_cached_time = sum(timings) / len(timings)

            # Cached access should be at least 10x faster
            assert avg_cached_time < timer1["duration"] / 10, (
                "Viewer singleton not providing performance benefit"
            )

    def test_exec_globals_caching(self):
        """Test that exec globals are properly cached."""
        from napari_mcp.server import _exec_globals

        # First execution - builds namespace
        code1 = "x = 1"
        with measure_time("first_exec") as timer1:
            exec(code1, _exec_globals)

        # Subsequent execution - uses cached namespace
        code2 = "y = x + 1"
        with measure_time("cached_exec") as timer2:
            exec(code2, _exec_globals)

        # Cached execution should be fast (more tolerance in CI)
        tolerance = 4 if os.environ.get("CI") else 3
        assert timer2["duration"] < timer1["duration"] * tolerance
        assert _exec_globals.get("y") == 2


@pytest.mark.benchmark
class TestLoadTesting:
    """Load testing for napari-mcp."""

    @pytest.mark.asyncio
    async def test_high_frequency_operations(self):
        """Test system under high frequency operations."""
        mock_viewer = Mock()
        mock_viewer.layers = []

        operation_count = 1000

        async def rapid_operation(index):
            # Simulate rapid fire operations
            if index % 2 == 0:
                mock_viewer.layers.append(Mock(name=f"layer_{index}"))
            elif mock_viewer.layers:
                mock_viewer.layers.pop()

        with measure_time(f"{operation_count}_rapid_operations") as timer:
            tasks = [rapid_operation(i) for i in range(operation_count)]
            await asyncio.gather(*tasks)

        # Should handle 1000 operations in reasonable time
        assert timer["duration"] < 5.0

        # System should remain stable
        assert isinstance(mock_viewer.layers, list)

    def test_memory_stability_under_load(self):
        """Test memory stability under sustained load."""
        import gc
        import tracemalloc

        tracemalloc.start()
        initial_snapshot = tracemalloc.take_snapshot()

        mock_viewer = Mock()

        # Simulate sustained load
        for _ in range(10):
            layers = []

            # Add many layers
            for _ in range(100):
                layer = Mock(data=np.zeros((100, 100)))
                layers.append(layer)

            mock_viewer.layers = layers

            # Clear and force garbage collection
            mock_viewer.layers.clear()
            gc.collect()

        final_snapshot = tracemalloc.take_snapshot()
        stats = final_snapshot.compare_to(initial_snapshot, "lineno")

        # Calculate leak
        leak_mb = (
            sum(stat.size_diff for stat in stats if stat.size_diff > 0) / 1024 / 1024
        )

        tracemalloc.stop()

        # Should not leak more than 10MB after cycles
        assert leak_mb < 10, f"Memory leak detected: {leak_mb:.2f}MB"

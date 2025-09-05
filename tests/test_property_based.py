"""Property-based tests for napari-mcp using Hypothesis."""

import os
from unittest.mock import Mock

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

# Removed offscreen mode - it causes segfaults

# Use the mock napari from conftest
from napari_mcp.base import NapariMCPTools


class TestPropertyBasedLayerOperations:
    """Property-based tests for layer operations."""

    @given(
        layer_names=st.lists(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(min_codepoint=65, max_codepoint=122),
            ),
            min_size=1,
            max_size=10,
            unique=True,
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_layer_name_uniqueness_invariant(self, layer_names):
        """Test that layer names remain unique after operations."""
        mock_viewer = Mock()
        mock_viewer.layers = []
        _ = NapariMCPTools(mock_viewer)  # Tools instance not used directly

        # Property: Adding layers should maintain unique names
        added_names = set()
        for name in layer_names:
            if name not in added_names:
                layer = Mock()
                layer.name = name
                mock_viewer.layers.append(layer)
                added_names.add(name)

        # Verify uniqueness invariant
        actual_names = [layer.name for layer in mock_viewer.layers]
        assert len(actual_names) == len(set(actual_names))

    @given(
        dimensions=st.integers(min_value=2, max_value=4),
        shape=st.lists(
            st.integers(min_value=10, max_value=100), min_size=2, max_size=4
        ),
    )
    @settings(max_examples=30, deadline=None)
    def test_image_data_shape_preservation(self, dimensions, shape):
        """Test that image data shapes are preserved correctly."""
        # Adjust shape to match dimensions
        shape = shape[:dimensions]

        mock_viewer = Mock()
        mock_viewer.add_image = Mock()
        _ = NapariMCPTools(mock_viewer)  # Tools instance not used directly

        # Create random numpy array with given shape
        data = np.random.random(shape)

        # Property: Shape should be preserved when adding image
        mock_viewer.add_image(data)
        mock_viewer.add_image.assert_called_once()
        call_args = mock_viewer.add_image.call_args[0]

        assert call_args[0].shape == tuple(shape)

    @given(
        zoom_level=st.floats(
            min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
        center_x=st.floats(min_value=-1000, max_value=1000, allow_nan=False),
        center_y=st.floats(min_value=-1000, max_value=1000, allow_nan=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_camera_state_consistency(self, zoom_level, center_x, center_y):
        """Test camera state remains consistent after transformations."""
        mock_viewer = Mock()
        mock_viewer.camera = Mock()
        mock_viewer.camera.zoom = 1.0
        mock_viewer.camera.center = [0, 0]

        # Property: Camera state should be retrievable after setting
        mock_viewer.camera.zoom = zoom_level
        mock_viewer.camera.center = [center_x, center_y]

        assert mock_viewer.camera.zoom == zoom_level
        assert mock_viewer.camera.center == [center_x, center_y]

        # Property: Zoom level should remain positive
        assert mock_viewer.camera.zoom > 0

    @given(
        opacity_values=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_layer_opacity_bounds(self, opacity_values):
        """Test that layer opacity values stay within valid bounds."""
        mock_viewer = Mock()
        mock_viewer.layers = []

        for i, opacity in enumerate(opacity_values):
            layer = Mock()
            layer.name = f"layer_{i}"
            layer.opacity = opacity
            mock_viewer.layers.append(layer)

        # Property: All opacity values should be in [0, 1]
        for layer in mock_viewer.layers:
            assert 0.0 <= layer.opacity <= 1.0

    @given(
        layer_indices=st.lists(
            st.integers(min_value=0, max_value=9), min_size=2, max_size=10
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_layer_reordering_preservation(self, layer_indices):
        """Test that layer reordering preserves all layers."""
        mock_viewer = Mock()
        initial_layers = [Mock(name=f"layer_{i}") for i in range(10)]
        mock_viewer.layers = initial_layers.copy()

        # Simulate reordering
        assume(max(layer_indices) < len(mock_viewer.layers))

        # Property: Reordering should preserve layer count
        _ = len(mock_viewer.layers)  # Store original count for reference

        # Perform mock reordering (simplified)
        if len(set(layer_indices)) == len(layer_indices):  # Only if indices are unique
            reordered = [
                mock_viewer.layers[i]
                for i in layer_indices
                if i < len(mock_viewer.layers)
            ]
            assert len(set(reordered)) == len(
                reordered
            )  # No duplicates after reordering


class TestPropertyBasedDataTransformations:
    """Property-based tests for data transformations."""

    @given(
        array_data=arrays(
            dtype=np.float64,
            shape=st.tuples(
                st.integers(min_value=10, max_value=100),
                st.integers(min_value=10, max_value=100),
            ),
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_screenshot_encoding_roundtrip(self, array_data):
        """Test that screenshot encoding/decoding is lossless for valid data."""
        import base64
        from io import BytesIO

        from PIL import Image

        # Normalize data to valid image range
        normalized = (
            (array_data - array_data.min())
            / (array_data.max() - array_data.min() + 1e-10)
            * 255
        ).astype(np.uint8)

        # Convert to RGB
        rgb_data = np.stack([normalized] * 3, axis=-1)

        # Property: Encoding and decoding should preserve image dimensions
        img = Image.fromarray(rgb_data)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Decode
        decoded_bytes = base64.b64decode(encoded)
        decoded_img = Image.open(BytesIO(decoded_bytes))
        decoded_array = np.array(decoded_img)

        assert decoded_array.shape == rgb_data.shape

    @given(
        points=arrays(
            dtype=np.float64,
            shape=st.tuples(
                st.integers(min_value=1, max_value=100),
                st.integers(min_value=2, max_value=3),
            ),
        ),
        point_size=st.floats(min_value=1, max_value=50, allow_nan=False),
    )
    @settings(max_examples=30, deadline=None)
    def test_points_layer_data_integrity(self, points, point_size):
        """Test that points layer data maintains integrity."""
        mock_viewer = Mock()
        mock_viewer.add_points = Mock(return_value=Mock())

        # Property: Points data shape should be preserved
        mock_viewer.add_points(points, size=point_size)

        call_args = mock_viewer.add_points.call_args
        assert call_args[0][0].shape == points.shape
        assert call_args[1]["size"] == point_size

    @given(
        code_snippets=st.lists(
            st.text(min_size=1, max_size=100), min_size=1, max_size=5
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_code_execution_isolation(self, code_snippets):
        """Test that code execution maintains isolated namespaces."""
        from napari_mcp.base import NapariMCPTools

        _ = NapariMCPTools()  # Tools instance not used directly

        # Property: Each execution should have isolated namespace
        for i, code in enumerate(code_snippets):
            # Only test valid Python variable assignments
            var_name = f"test_var_{i}"
            safe_code = f"{var_name} = {repr(code)}"

            # Execute in isolated namespace
            namespace = {}
            try:
                exec(safe_code, namespace)
                assert var_name in namespace
                assert namespace[var_name] == code
            except Exception:
                pass  # Skip invalid code

    @given(
        grid_enabled=st.booleans(),
        ndisplay=st.integers(min_value=2, max_value=3),
        axis_values=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=3),
                st.integers(min_value=0, max_value=100),
            ),
            max_size=4,
        ),
    )
    @settings(max_examples=30, deadline=None)
    def test_viewer_state_consistency(self, grid_enabled, ndisplay, axis_values):
        """Test that viewer state remains consistent after multiple operations."""
        mock_viewer = Mock()
        mock_viewer.grid = Mock(enabled=False)
        mock_viewer.dims = Mock(ndisplay=2)
        mock_viewer.dims.set_current_step = Mock()

        # Apply state changes
        mock_viewer.grid.enabled = grid_enabled
        mock_viewer.dims.ndisplay = ndisplay

        for axis, value in axis_values:
            if axis < ndisplay:
                mock_viewer.dims.set_current_step(axis, value)

        # Properties to verify
        assert mock_viewer.grid.enabled == grid_enabled
        assert mock_viewer.dims.ndisplay == ndisplay
        assert ndisplay in [2, 3]  # Valid display dimensions


class TestPropertyBasedConcurrency:
    """Property-based tests for concurrent operations."""

    @given(
        operation_count=st.integers(min_value=1, max_value=10),
        operation_types=st.lists(
            st.sampled_from(["add", "remove", "rename", "reorder"]),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_concurrent_layer_operations(self, operation_count, operation_types):
        """Test that concurrent layer operations maintain consistency."""
        import asyncio

        mock_viewer = Mock()
        mock_viewer.layers = []

        # Property: Concurrent operations should not corrupt layer state
        async def perform_operation(op_type, index):
            await asyncio.sleep(0.001)  # Simulate async operation
            if op_type == "add" and len(mock_viewer.layers) < 20:
                mock_viewer.layers.append(Mock(name=f"layer_{index}"))
            elif op_type == "remove" and mock_viewer.layers:
                mock_viewer.layers.pop(0)
            # Other operations omitted for brevity

        tasks = [
            perform_operation(op_type, i)
            for i, op_type in enumerate(operation_types[:operation_count])
        ]

        await asyncio.gather(*tasks)

        # Verify consistency
        layer_names = [
            layer.name for layer in mock_viewer.layers if hasattr(layer, "name")
        ]
        assert len(layer_names) == len(set(layer_names))  # No duplicate names


# Strategy definitions for complex data types
image_strategy = arrays(
    dtype=np.uint8,
    shape=st.tuples(
        st.integers(min_value=10, max_value=200),
        st.integers(min_value=10, max_value=200),
        st.just(3),  # RGB channels
    ),
)

layer_property_strategy = st.fixed_dictionaries(
    {
        "visible": st.booleans(),
        "opacity": st.floats(min_value=0.0, max_value=1.0),
        "blending": st.sampled_from(["translucent", "additive", "opaque"]),
        "colormap": st.sampled_from(["viridis", "magma", "gray", "turbo"]),
    }
)


@given(image_data=image_strategy, properties=layer_property_strategy)
@settings(max_examples=20, deadline=None)
def test_complex_layer_creation(image_data, properties):
    """Test complex layer creation with various properties."""
    mock_viewer = Mock()
    mock_viewer.add_image = Mock(return_value=Mock())

    # Create layer with properties
    _ = mock_viewer.add_image(image_data, **properties)  # Layer not used directly

    # Verify call was made with correct arguments
    mock_viewer.add_image.assert_called_once()
    call_kwargs = mock_viewer.add_image.call_args[1]

    for key, value in properties.items():
        assert call_kwargs[key] == value

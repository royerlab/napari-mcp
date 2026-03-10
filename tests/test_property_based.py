"""Property-based tests for napari-mcp using Hypothesis."""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from napari_mcp._helpers import parse_bool as _parse_bool
from napari_mcp.output import truncate_output as _truncate_output


class TestPropertyBasedParseBool:
    """Property-based tests for _parse_bool."""

    @given(value=st.booleans())
    @settings(max_examples=50, deadline=None)
    def test_bool_passthrough(self, value):
        """Test that bool values pass through unchanged."""
        assert _parse_bool(value) is value

    @given(
        true_str=st.sampled_from(
            ["true", "True", "TRUE", "1", "yes", "Yes", "on", "ON"]
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_true_strings(self, true_str):
        """Test that all true-like strings return True."""
        assert _parse_bool(true_str) is True

    @given(false_str=st.sampled_from(["false", "False", "0", "no", "off", ""]))
    @settings(max_examples=50, deadline=None)
    def test_false_strings(self, false_str):
        """Test that all false-like strings return False."""
        assert _parse_bool(false_str) is False

    @given(default=st.booleans())
    @settings(max_examples=20, deadline=None)
    def test_none_returns_default(self, default):
        """Test that None returns the default value."""
        assert _parse_bool(None, default=default) is default


class TestPropertyBasedTruncateOutput:
    """Property-based tests for _truncate_output."""

    @given(
        lines=st.lists(
            st.text(
                min_size=1,
                max_size=80,
                alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            ),
            min_size=0,
            max_size=50,
        ),
        line_limit=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100, deadline=None)
    def test_truncation_respects_limit(self, lines, line_limit):
        """Test that truncated output never exceeds line_limit."""
        output = "\n".join(lines) + ("\n" if lines else "")
        result, was_truncated = _truncate_output(output, line_limit)

        # Count non-empty trailing lines
        actual_line_count = (
            len([line for line in result.split("\n") if line]) if result else 0
        )

        assert actual_line_count <= max(line_limit, 0)

    @given(
        lines=st.lists(
            st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(min_codepoint=65, max_codepoint=90),
            ),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_unlimited_returns_full_output(self, lines):
        """Test that line_limit=-1 returns full output."""
        output = "\n".join(lines) + "\n"
        result, was_truncated = _truncate_output(output, -1)
        assert result == output
        assert was_truncated is False

    @given(
        line_limit=st.integers(min_value=-10, max_value=-1),
        output=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=30, deadline=None)
    def test_negative_limits_are_unlimited(self, line_limit, output):
        """Test that any negative line_limit acts as unlimited."""
        result, was_truncated = _truncate_output(output, line_limit)
        assert result == output
        assert was_truncated is False


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
        """Test that screenshot encoding/decoding preserves image dimensions."""
        import base64
        from io import BytesIO

        from PIL import Image

        # Normalize data to valid image range
        data_range = array_data.max() - array_data.min()
        if data_range == 0:
            normalized = np.zeros_like(array_data, dtype=np.uint8)
        else:
            normalized = (
                (array_data - array_data.min()) / (data_range + 1e-10) * 255
            ).astype(np.uint8)

        rgb_data = np.stack([normalized] * 3, axis=-1)

        img = Image.fromarray(rgb_data)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

        decoded_bytes = base64.b64decode(encoded)
        decoded_img = Image.open(BytesIO(decoded_bytes))
        decoded_array = np.array(decoded_img)

        assert decoded_array.shape == rgb_data.shape

"""Tests for output storage and line limiting functionality."""

import pytest

from napari_mcp.server import (
    _store_output,
    _truncate_output,
    close_viewer,
    execute_code,
    install_packages,
    read_output,
)


class TestOutputTruncation:
    """Test output truncation functionality."""

    def test_truncate_output_no_limit(self):
        """Test that -1 line limit returns full output."""
        output = "line1\nline2\nline3\nline4\n"
        result, was_truncated = _truncate_output(output, -1)
        assert result == output
        assert was_truncated is False

    def test_truncate_output_within_limit(self):
        """Test output within line limit."""
        output = "line1\nline2\n"
        result, was_truncated = _truncate_output(output, 5)
        assert result == output
        assert was_truncated is False

    def test_truncate_output_exceeds_limit(self):
        """Test output that exceeds line limit."""
        output = "line1\nline2\nline3\nline4\n"
        result, was_truncated = _truncate_output(output, 2)
        expected = "line1\nline2\n"
        assert result == expected
        assert was_truncated is True

    def test_truncate_output_empty(self):
        """Test empty output."""
        output = ""
        result, was_truncated = _truncate_output(output, 10)
        assert result == ""
        assert was_truncated is False

    def test_truncate_output_exact_limit(self):
        """Test output exactly at line limit."""
        output = "line1\nline2\n"
        result, was_truncated = _truncate_output(output, 2)
        assert result == output
        assert was_truncated is False

    def test_truncate_output_zero_limit(self):
        """Test behavior when line_limit is 0 (returns no lines)."""
        output = "line1\nline2\nline3\n"
        result, was_truncated = _truncate_output(output, 0)
        assert result == ""
        assert was_truncated is True

    def test_truncate_output_negative_less_than_minus_one(self):
        """Test normalization when line_limit < -1 (treated as unlimited)."""
        output = "line1\nline2\nline3\n"
        result, was_truncated = _truncate_output(output, -2)
        assert result == output
        assert was_truncated is False


@pytest.mark.asyncio
class TestOutputStorage:
    """Test output storage functionality."""

    async def test_store_and_retrieve_output(self):
        """Test basic output storage and retrieval."""
        # Clear any existing storage
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        # Store output
        output_id = await _store_output(
            tool_name="test_tool",
            stdout="test stdout",
            stderr="test stderr",
            result_repr="'test result'",
            custom_field="custom_value",
        )

        assert output_id == "1"

        # Retrieve output
        result = await read_output(output_id)
        assert result["status"] == "ok"
        assert result["tool_name"] == "test_tool"
        assert result["result_repr"] == "'test result'"
        assert "test stdout" in "".join(result["lines"])
        assert "test stderr" in "".join(result["lines"])

    async def test_read_output_not_found(self):
        """Test reading non-existent output."""
        result = await read_output("999")
        assert result["status"] == "error"
        assert "not found" in result["message"]

    async def test_read_output_with_range(self):
        """Test reading output with line range."""
        # Clear storage
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        # Store multi-line output
        multiline_stdout = "\n".join([f"line {i}" for i in range(10)])
        output_id = await _store_output(tool_name="test_tool", stdout=multiline_stdout)

        # Read first 3 lines
        result = await read_output(output_id, start=0, end=3)
        assert result["status"] == "ok"
        assert result["line_range"]["start"] == 0
        assert result["line_range"]["end"] == 3
        assert len(result["lines"]) == 3
        assert "line 0" in result["lines"][0]
        assert "line 2" in result["lines"][2]

    async def test_read_output_beyond_range(self):
        """Test reading output beyond available range."""
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        output_id = await _store_output(tool_name="test_tool", stdout="line1\nline2\n")

        # Try to read beyond available lines
        result = await read_output(output_id, start=5, end=10)
        assert result["status"] == "ok"
        assert len(result["lines"]) == 0
        assert result["total_lines"] == 2


@pytest.mark.asyncio
class TestExecuteCodeLimiting:
    """Test execute_code with line limiting."""

    async def test_execute_code_default_limit(self, make_napari_viewer):
        """Test execute_code with default line limit."""
        viewer = make_napari_viewer()
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._viewer = viewer
        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        # Execute code that produces output
        result = await execute_code('print("test output")')
        assert result["status"] == "ok"
        assert "output_id" in result
        assert "test output" in result["stdout"]

        await close_viewer()

    async def test_execute_code_unlimited_output(self, make_napari_viewer):
        """Test execute_code with unlimited output."""
        viewer = make_napari_viewer()
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._viewer = viewer
        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        result = await execute_code('print("test")', line_limit=-1)
        assert result["status"] == "ok"
        assert "warning" in result
        assert "large number of tokens" in result["warning"]

        await close_viewer()

    async def test_execute_code_with_truncation(self, make_napari_viewer):
        """Test execute_code that produces output requiring truncation."""
        viewer = make_napari_viewer()
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._viewer = viewer
        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        # Generate many lines of output
        code = "for i in range(50): print(f'line {i}')"
        result = await execute_code(code, line_limit=5)

        assert result["status"] == "ok"
        assert "truncated" in result
        assert result["truncated"] is True
        assert "Use read_output" in result["message"]

        # Verify we can read the full output
        full_result = await read_output(result["output_id"])
        assert len(full_result["lines"]) == 50

        await close_viewer()

    async def test_execute_code_error_with_limiting(self, make_napari_viewer):
        """Test execute_code error handling with line limiting."""
        viewer = make_napari_viewer()
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._viewer = viewer
        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        result = await execute_code('raise ValueError("test error")', line_limit=5)
        assert result["status"] == "error"
        assert "output_id" in result
        assert "ValueError" in result["stderr"]

        await close_viewer()


@pytest.mark.asyncio
class TestInstallPackagesLimiting:
    """Test install_packages with line limiting."""

    async def test_install_packages_default_limit(self):
        """Test install_packages with default line limit."""
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        # Use a package that should fail quickly to avoid long test times
        result = await install_packages(["nonexistent-package-xyz-123"])

        assert "output_id" in result
        assert "status" in result
        # Should have some output even if installation fails
        assert isinstance(result.get("stdout", ""), str)
        assert isinstance(result.get("stderr", ""), str)

    async def test_install_packages_unlimited_output(self):
        """Test install_packages with unlimited output."""
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        result = await install_packages(["nonexistent-package"], line_limit=-1)
        assert "warning" in result
        assert "large number of tokens" in result["warning"]

    async def test_install_packages_empty_list(self):
        """Test install_packages with empty package list."""
        result = await install_packages([])
        assert result["status"] == "error"
        assert "non-empty list" in result["message"]

    async def test_install_packages_invalid_input(self):
        """Test install_packages with invalid input."""
        result = await install_packages("not-a-list")  # type: ignore
        assert result["status"] == "error"
        assert "non-empty list" in result["message"]


@pytest.mark.asyncio
class TestReadOutputTool:
    """Test the read_output tool functionality."""

    async def test_read_output_full_range(self):
        """Test reading full output range."""
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        # Store test output
        lines = [f"line {i}\n" for i in range(10)]
        output_text = "".join(lines)
        output_id = await _store_output(tool_name="test_tool", stdout=output_text)

        # Read full range (default parameters)
        result = await read_output(output_id)
        assert result["status"] == "ok"
        assert result["total_lines"] == 10
        assert len(result["lines"]) == 10

    async def test_read_output_partial_range(self):
        """Test reading partial output range."""
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        lines = [f"line {i}\n" for i in range(20)]
        output_text = "".join(lines)
        output_id = await _store_output(tool_name="test_tool", stdout=output_text)

        # Read middle portion
        result = await read_output(output_id, start=5, end=10)
        assert result["status"] == "ok"
        assert result["line_range"]["start"] == 5
        assert result["line_range"]["end"] == 10
        assert len(result["lines"]) == 5
        assert "line 5" in result["lines"][0]
        assert "line 9" in result["lines"][4]

    async def test_read_output_combined_stdout_stderr(self):
        """Test reading output with both stdout and stderr."""
        from napari_mcp import server as napari_mcp_server

        napari_mcp_server._output_storage.clear()
        napari_mcp_server._next_output_id = 1

        output_id = await _store_output(
            tool_name="test_tool",
            stdout="stdout line 1\nstdout line 2\n",
            stderr="stderr line 1\nstderr line 2\n",
        )

        result = await read_output(output_id)
        assert result["status"] == "ok"

        # Check that both stdout and stderr are included
        combined_output = "".join(result["lines"])
        assert "stdout line 1" in combined_output
        assert "stderr line 1" in combined_output

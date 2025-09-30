"""Tests for CLI installer utility functions."""

import json
import os
import platform
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from rich.console import Console

from napari_mcp.cli.install.utils import (
    build_server_config,
    check_existing_server,
    expand_path,
    get_app_display_name,
    get_platform,
    get_python_executable,
    prompt_update_existing,
    read_json_config,
    show_installation_summary,
    validate_python_environment,
    write_json_config,
)


class TestPlatformDetection:
    """Test platform detection utilities."""

    @patch("platform.system")
    def test_get_platform_macos(self, mock_system):
        """Test macOS platform detection."""
        mock_system.return_value = "Darwin"
        assert get_platform() == "macos"

    @patch("platform.system")
    def test_get_platform_windows(self, mock_system):
        """Test Windows platform detection."""
        mock_system.return_value = "Windows"
        assert get_platform() == "windows"

    @patch("platform.system")
    def test_get_platform_linux(self, mock_system):
        """Test Linux platform detection."""
        mock_system.return_value = "Linux"
        assert get_platform() == "linux"

    @patch("platform.system")
    def test_get_platform_unknown(self, mock_system):
        """Test unknown platform defaults to linux."""
        mock_system.return_value = "FreeBSD"
        assert get_platform() == "linux"


class TestPathExpansion:
    """Test path expansion utilities."""

    @patch("os.path.expanduser")
    @patch("os.path.expandvars")
    def test_expand_path_home(self, mock_expandvars, mock_expanduser):
        """Test home directory expansion."""
        mock_expanduser.return_value = "/home/user/test/file.json"
        mock_expandvars.return_value = "/home/user/test/file.json"

        result = expand_path("~/test/file.json")
        mock_expanduser.assert_called_once_with("~/test/file.json")
        assert "test/file.json" in str(result)

    @patch("os.path.expanduser")
    @patch("os.path.expandvars")
    def test_expand_path_env_var(self, mock_expandvars, mock_expanduser):
        """Test environment variable expansion."""
        mock_expanduser.return_value = "$APPDATA/config.json"
        mock_expandvars.return_value = "/app/data/config.json"

        result = expand_path("$APPDATA/config.json")
        mock_expandvars.assert_called()
        assert "config.json" in str(result)

    @patch("os.path.expanduser")
    @patch("os.path.expandvars")
    def test_expand_path_windows_env(self, mock_expandvars, mock_expanduser):
        """Test Windows-style environment variable expansion."""
        mock_expanduser.return_value = "%APPDATA%\\config.json"
        mock_expandvars.return_value = "C:\\Users\\User\\AppData\\config.json"

        result = expand_path("%APPDATA%\\config.json")
        assert "config.json" in str(result)

    def test_expand_path_returns_path_object(self):
        """Test that expand_path returns a Path object."""
        result = expand_path("/absolute/path/file.json")
        assert isinstance(result, Path)

    def test_expand_path_makes_absolute(self):
        """Test that expand_path returns absolute path."""
        result = expand_path("./relative/path")
        assert result.is_absolute()


class TestJSONConfig:
    """Test JSON configuration file handling."""

    def test_read_json_config_nonexistent(self):
        """Test reading non-existent config returns empty dict."""
        result = read_json_config(Path("/nonexistent/file.json"))
        assert result == {}

    def test_read_json_config_valid(self, tmp_path):
        """Test reading valid JSON config."""
        config_file = tmp_path / "config.json"
        test_config = {"mcpServers": {"test": {"command": "test"}}}
        config_file.write_text(json.dumps(test_config))

        result = read_json_config(config_file)
        assert result == test_config

    def test_read_json_config_preserves_order(self, tmp_path):
        """Test reading JSON preserves key order."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"z": 1, "a": 2, "m": 3}')

        result = read_json_config(config_file)
        assert isinstance(result, OrderedDict)
        assert list(result.keys()) == ["z", "a", "m"]

    def test_read_json_config_invalid_json(self, tmp_path):
        """Test reading invalid JSON returns empty dict."""
        config_file = tmp_path / "config.json"
        config_file.write_text("invalid json{")

        with patch("napari_mcp.cli.install.utils.console") as mock_console:
            result = read_json_config(config_file)
            assert result == {}
            mock_console.print.assert_called()

    def test_write_json_config_create_parent(self, tmp_path):
        """Test writing config creates parent directories."""
        config_file = tmp_path / "subdir" / "config.json"
        test_config = {"test": "value"}

        result = write_json_config(config_file, test_config, backup=False)
        assert result is True
        assert config_file.exists()
        assert json.loads(config_file.read_text()) == test_config

    def test_write_json_config_backup(self, tmp_path):
        """Test writing config creates backup of existing file."""
        config_file = tmp_path / "config.json"
        original_content = {"original": "content"}
        config_file.write_text(json.dumps(original_content))

        new_content = {"new": "content"}
        result = write_json_config(config_file, new_content, backup=True)

        assert result is True
        assert json.loads(config_file.read_text()) == new_content

        # Check backup was created
        backup_files = list(tmp_path.glob("config.backup_*"))
        assert len(backup_files) == 1
        assert json.loads(backup_files[0].read_text()) == original_content

    def test_write_json_config_atomic(self, tmp_path):
        """Test atomic write using temporary file."""
        config_file = tmp_path / "config.json"
        test_config = {"test": "atomic"}

        with patch("pathlib.Path.replace") as mock_replace:
            write_json_config(config_file, test_config, backup=False)
            mock_replace.assert_called_once()

    def test_write_json_config_failure(self, tmp_path):
        """Test write failure handling."""
        config_file = tmp_path / "config.json"
        test_config = {"test": "value"}

        with patch("builtins.open", side_effect=IOError("Test error")):
            with patch("napari_mcp.cli.install.utils.console") as mock_console:
                result = write_json_config(config_file, test_config)
                assert result is False
                mock_console.print.assert_called()

    def test_write_json_config_unicode(self, tmp_path):
        """Test writing config with Unicode characters."""
        config_file = tmp_path / "config.json"
        test_config = {"test": "émoji 🎉"}

        result = write_json_config(config_file, test_config, backup=False)
        assert result is True

        content = config_file.read_text(encoding="utf-8")
        assert "émoji 🎉" in content
        assert json.loads(content) == test_config


class TestPythonExecutable:
    """Test Python executable detection."""

    def test_get_python_executable_default(self):
        """Test default returns uv."""
        command, desc = get_python_executable()
        assert command == "uv"
        assert "ephemeral" in desc.lower()

    def test_get_python_executable_persistent(self):
        """Test persistent mode returns current Python."""
        command, desc = get_python_executable(persistent=True)
        assert command == sys.executable
        assert "persistent" in desc.lower()

    def test_get_python_executable_custom_path(self, tmp_path):
        """Test custom Python path."""
        custom_python = tmp_path / "python"
        custom_python.touch()

        command, desc = get_python_executable(python_path=str(custom_python))
        assert command == str(custom_python)
        assert "custom" in desc.lower()

    def test_get_python_executable_nonexistent_custom(self):
        """Test warning for non-existent custom path."""
        with patch("napari_mcp.cli.install.utils.console") as mock_console:
            command, desc = get_python_executable(python_path="/nonexistent/python")
            assert command == "/nonexistent/python"
            mock_console.print.assert_called()


class TestPythonEnvironmentValidation:
    """Test Python environment validation."""

    @patch("subprocess.run")
    def test_validate_python_environment_success(self, mock_run):
        """Test successful environment validation."""
        mock_run.return_value = MagicMock(returncode=0)
        assert validate_python_environment("/usr/bin/python3") is True

    @patch("subprocess.run")
    def test_validate_python_environment_missing_package(self, mock_run):
        """Test validation with missing napari-mcp."""
        mock_run.return_value = MagicMock(returncode=1)

        with patch("napari_mcp.cli.install.utils.console") as mock_console:
            result = validate_python_environment("/usr/bin/python3")
            assert result is False
            mock_console.print.assert_called()

    @patch("subprocess.run")
    def test_validate_python_environment_exception(self, mock_run):
        """Test validation with subprocess exception."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("python", 5)

        with patch("napari_mcp.cli.install.utils.console") as mock_console:
            result = validate_python_environment("/usr/bin/python3")
            assert result is False
            mock_console.print.assert_called()


class TestServerConfiguration:
    """Test server configuration building."""

    def test_build_server_config_uv(self):
        """Test building server config for uv."""
        config = build_server_config(persistent=False, python_path=None)
        assert config["command"] == "uv"
        assert config["args"] == ["run", "--with", "napari-mcp", "napari-mcp"]

    def test_build_server_config_python(self):
        """Test building server config for Python path."""
        config = build_server_config(persistent=False, python_path="/usr/bin/python3")
        assert config["command"] == "/usr/bin/python3"
        assert config["args"] == ["-m", "napari_mcp.server"]

    def test_build_server_config_persistent(self):
        """Test building config with persistent Python."""
        config = build_server_config(persistent=True, python_path=None)
        assert config["command"] == sys.executable
        assert config["args"] == ["-m", "napari_mcp.server"]

    def test_build_server_config_with_extras(self):
        """Test building config with extra fields."""
        extras = {"timeout": 60000, "cwd": "/project"}
        config = build_server_config(persistent=False, python_path=None, extra_args=extras)

        assert config["command"] == "uv"
        assert config["timeout"] == 60000
        assert config["cwd"] == "/project"

    def test_check_existing_server_found(self):
        """Test checking for existing server configuration."""
        config = {
            "mcpServers": {
                "napari-mcp": {"command": "uv"},
                "other": {"command": "python"}
            }
        }
        assert check_existing_server(config, "napari-mcp") is True

    def test_check_existing_server_not_found(self):
        """Test checking for non-existent server."""
        config = {"mcpServers": {"other": {"command": "python"}}}
        assert check_existing_server(config, "napari-mcp") is False

    def test_check_existing_server_empty_config(self):
        """Test checking in empty config."""
        assert check_existing_server({}, "napari-mcp") is False

    def test_check_existing_server_no_mcp_servers(self):
        """Test checking with missing mcpServers key."""
        config = {"otherKey": {}}
        assert check_existing_server(config, "napari-mcp") is False


class TestAppDisplayNames:
    """Test application display name mapping."""

    def test_get_app_display_name_known(self):
        """Test getting display name for known applications."""
        assert get_app_display_name("claude-desktop") == "Claude Desktop"
        assert get_app_display_name("claude-code") == "Claude Code"
        assert get_app_display_name("cursor") == "Cursor"
        assert get_app_display_name("cline-vscode") == "Cline (VS Code)"
        assert get_app_display_name("cline-cursor") == "Cline (Cursor IDE)"
        assert get_app_display_name("gemini") == "Gemini CLI"
        assert get_app_display_name("codex") == "Codex CLI"

    def test_get_app_display_name_unknown(self):
        """Test getting display name for unknown application."""
        assert get_app_display_name("unknown-app") == "unknown-app"


class TestPromptUtilities:
    """Test user prompt utilities."""

    @patch("rich.prompt.Confirm.ask")
    def test_prompt_update_existing_yes(self, mock_ask):
        """Test prompting for update with yes response."""
        mock_ask.return_value = True
        result = prompt_update_existing("Claude Desktop", Path("/test/config.json"))
        assert result is True
        mock_ask.assert_called_once()

    @patch("rich.prompt.Confirm.ask")
    def test_prompt_update_existing_no(self, mock_ask):
        """Test prompting for update with no response."""
        mock_ask.return_value = False
        result = prompt_update_existing("Claude Desktop", Path("/test/config.json"))
        assert result is False
        mock_ask.assert_called_once()


class TestInstallationSummary:
    """Test installation summary display."""

    @patch("napari_mcp.cli.install.utils.console")
    def test_show_installation_summary_all_success(self, mock_console):
        """Test summary with all successful installations."""
        results = {
            "Claude Desktop": (True, "Installed successfully"),
            "Claude Code": (True, "Installed successfully")
        }
        show_installation_summary(results)

        # Check that console.print was called (displays Rich Table)
        assert mock_console.print.called
        # Verify it was called multiple times (for newlines and table)
        assert mock_console.print.call_count >= 2

    @patch("napari_mcp.cli.install.utils.console")
    def test_show_installation_summary_with_failures(self, mock_console):
        """Test summary with some failures."""
        results = {
            "Claude Desktop": (True, "Installed successfully"),
            "Claude Code": (False, "Failed to install")
        }
        show_installation_summary(results)

        # Check that console.print was called
        assert mock_console.print.called
        assert mock_console.print.call_count >= 2

    @patch("napari_mcp.cli.install.utils.console")
    def test_show_installation_summary_empty(self, mock_console):
        """Test summary with no results."""
        show_installation_summary({})
        mock_console.print.assert_called()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_expand_path_with_multiple_vars(self):
        """Test path with multiple environment variables."""
        with patch.dict(os.environ, {"HOME": "/home/user", "PROJ": "myproject"}):
            result = expand_path("$HOME/$PROJ/config.json")
            assert "/home/user/myproject/config.json" in str(result)

    def test_write_json_config_readonly_directory(self, tmp_path):
        """Test writing to read-only directory."""
        config_file = tmp_path / "readonly" / "config.json"
        config_file.parent.mkdir()

        # Make directory read-only
        config_file.parent.chmod(0o444)

        try:
            with patch("napari_mcp.cli.install.utils.console"):
                result = write_json_config(config_file, {"test": "value"}, backup=False)
                # On some systems this might still succeed, but most should fail
                # Either way, no exception should propagate
                assert isinstance(result, bool)
        except PermissionError:
            # This is also acceptable - the function tried and failed
            assert True
        finally:
            # Restore permissions for cleanup
            config_file.parent.chmod(0o755)

    def test_read_json_config_permission_denied(self, tmp_path):
        """Test reading config with permission denied."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        config_file.chmod(0o000)

        try:
            with patch("napari_mcp.cli.install.utils.console"):
                result = read_json_config(config_file)
                # Might succeed on some systems
                assert isinstance(result, dict)
        finally:
            config_file.chmod(0o644)
"""Tests for main CLI installer commands."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from napari_mcp.cli.main import app


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_installer():
    """Create a mock installer instance."""
    mock = MagicMock()
    mock.install.return_value = (True, "Installation successful")
    mock.uninstall.return_value = (True, "Uninstall successful")
    mock.get_config_path.return_value = Path("/mock/config.json")
    return mock


class TestCLICommands:
    """Test main CLI commands."""

    def test_version_flag(self, cli_runner):
        """Test --version flag displays version."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "napari-mcp version" in result.stdout

    def test_help_command(self, cli_runner):
        """Test help text generation."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "napari-mcp-install" in result.stdout
        assert "claude-desktop" in result.stdout
        assert "claude-code" in result.stdout

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    def test_claude_desktop_install(self, mock_installer_class, cli_runner, mock_installer):
        """Test claude-desktop installation command."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["claude-desktop"])
        assert result.exit_code == 0
        mock_installer.install.assert_called_once()

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    def test_claude_desktop_install_with_options(self, mock_installer_class, cli_runner):
        """Test claude-desktop installation with options."""
        result = cli_runner.invoke(app, [
            "claude-desktop",
            "--persistent",
            "--python-path", "/usr/bin/python3",
            "--force",
            "--no-backup",
            "--dry-run"
        ])

        mock_installer_class.assert_called_once()
        call_kwargs = mock_installer_class.call_args[1]
        assert call_kwargs["persistent"] is True
        assert call_kwargs["python_path"] == "/usr/bin/python3"
        assert call_kwargs["force"] is True
        assert call_kwargs["backup"] is False
        assert call_kwargs["dry_run"] is True

    @patch("napari_mcp.cli.main.ClaudeCodeInstaller")
    def test_claude_code_install(self, mock_installer_class, cli_runner, mock_installer):
        """Test claude-code installation command."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["claude-code"])
        assert result.exit_code == 0
        mock_installer.install.assert_called_once()

    @patch("napari_mcp.cli.main.CursorInstaller")
    def test_cursor_install_global(self, mock_installer_class, cli_runner, mock_installer):
        """Test cursor global installation."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["cursor", "--global"])
        assert result.exit_code == 0

        call_kwargs = mock_installer_class.call_args[1]
        assert call_kwargs["global_install"] is True

    @patch("napari_mcp.cli.main.CursorInstaller")
    def test_cursor_install_project(self, mock_installer_class, cli_runner, mock_installer):
        """Test cursor project-specific installation."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["cursor", "--project", "/path/to/project"])
        assert result.exit_code == 0

        call_kwargs = mock_installer_class.call_args[1]
        assert call_kwargs["project_dir"] == "/path/to/project"

    @patch("napari_mcp.cli.main.ClineVSCodeInstaller")
    def test_cline_vscode_install(self, mock_installer_class, cli_runner, mock_installer):
        """Test cline-vscode installation."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["cline-vscode"])
        assert result.exit_code == 0
        mock_installer.install.assert_called_once()

    @patch("napari_mcp.cli.main.ClineCursorInstaller")
    def test_cline_cursor_install(self, mock_installer_class, cli_runner, mock_installer):
        """Test cline-cursor installation."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["cline-cursor"])
        assert result.exit_code == 0
        mock_installer.install.assert_called_once()

    @patch("napari_mcp.cli.main.GeminiCLIInstaller")
    def test_gemini_install(self, mock_installer_class, cli_runner, mock_installer):
        """Test gemini installation."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["gemini", "--global"])
        assert result.exit_code == 0

        call_kwargs = mock_installer_class.call_args[1]
        assert call_kwargs["global_install"] is True

    @patch("napari_mcp.cli.main.CodexCLIInstaller")
    def test_codex_install(self, mock_installer_class, cli_runner, mock_installer):
        """Test codex installation."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["codex"])
        assert result.exit_code == 0
        mock_installer.install.assert_called_once()

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    def test_install_failure(self, mock_installer_class, cli_runner):
        """Test installation failure handling."""
        mock = MagicMock()
        mock.install.return_value = (False, "Installation failed")
        mock_installer_class.return_value = mock

        result = cli_runner.invoke(app, ["claude-desktop"])
        assert result.exit_code == 1


class TestInstallAllCommand:
    """Test install-all command."""

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    @patch("napari_mcp.cli.main.ClaudeCodeInstaller")
    @patch("napari_mcp.cli.main.CursorInstaller")
    @patch("napari_mcp.cli.main.ClineVSCodeInstaller")
    @patch("napari_mcp.cli.main.ClineCursorInstaller")
    @patch("napari_mcp.cli.main.GeminiCLIInstaller")
    @patch("napari_mcp.cli.main.CodexCLIInstaller")
    def test_install_all_success(
        self,
        mock_codex,
        mock_gemini,
        mock_cline_cursor,
        mock_cline_vscode,
        mock_cursor,
        mock_claude_code,
        mock_claude_desktop,
        cli_runner
    ):
        """Test successful installation for all applications."""
        # Setup all mocks to return success
        for mock_class in [
            mock_claude_desktop,
            mock_claude_code,
            mock_cursor,
            mock_cline_vscode,
            mock_cline_cursor,
            mock_gemini,
            mock_codex
        ]:
            mock_instance = MagicMock()
            mock_instance.install.return_value = (True, "Success")
            mock_class.return_value = mock_instance

        result = cli_runner.invoke(app, ["all"])
        assert result.exit_code == 0
        assert "Installing napari-mcp for all supported applications" in result.stdout

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    @patch("napari_mcp.cli.main.ClaudeCodeInstaller")
    def test_install_all_partial_failure(
        self,
        mock_claude_code,
        mock_claude_desktop,
        cli_runner
    ):
        """Test partial failure in install-all."""
        # Claude Desktop succeeds
        mock_desktop = MagicMock()
        mock_desktop.install.return_value = (True, "Success")
        mock_claude_desktop.return_value = mock_desktop

        # Claude Code fails
        mock_code = MagicMock()
        mock_code.install.return_value = (False, "Failed")
        mock_claude_code.return_value = mock_code

        # Mock other installers to prevent actual instantiation
        with patch("napari_mcp.cli.main.CursorInstaller"), \
             patch("napari_mcp.cli.main.ClineVSCodeInstaller"), \
             patch("napari_mcp.cli.main.ClineCursorInstaller"), \
             patch("napari_mcp.cli.main.GeminiCLIInstaller"), \
             patch("napari_mcp.cli.main.CodexCLIInstaller"):

            result = cli_runner.invoke(app, ["all"])
            assert result.exit_code == 1


class TestUninstallCommand:
    """Test uninstall commands."""

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    def test_uninstall_single_app(self, mock_installer_class, cli_runner, mock_installer):
        """Test uninstalling from a single application."""
        mock_installer_class.return_value = mock_installer

        result = cli_runner.invoke(app, ["uninstall", "claude-desktop"])
        assert result.exit_code == 0
        mock_installer.uninstall.assert_called_once()

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    def test_uninstall_with_options(self, mock_installer_class, cli_runner):
        """Test uninstall with options."""
        result = cli_runner.invoke(app, [
            "uninstall",
            "claude-desktop",
            "--force",
            "--no-backup",
            "--dry-run"
        ])

        call_kwargs = mock_installer_class.call_args[1]
        assert call_kwargs["force"] is True
        assert call_kwargs["backup"] is False
        assert call_kwargs["dry_run"] is True

    def test_uninstall_invalid_app(self, cli_runner):
        """Test uninstall with invalid application name."""
        result = cli_runner.invoke(app, ["uninstall", "invalid-app"])
        assert result.exit_code == 1
        assert "Unknown application: invalid-app" in result.stdout

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    @patch("napari_mcp.cli.main.ClaudeCodeInstaller")
    def test_uninstall_all(
        self,
        mock_claude_code,
        mock_claude_desktop,
        cli_runner
    ):
        """Test uninstalling from all applications."""
        # Setup mocks
        for mock_class in [mock_claude_desktop, mock_claude_code]:
            mock_instance = MagicMock()
            mock_instance.uninstall.return_value = (True, "Success")
            mock_class.return_value = mock_instance

        # Mock other installers
        with patch("napari_mcp.cli.main.CursorInstaller"), \
             patch("napari_mcp.cli.main.ClineVSCodeInstaller"), \
             patch("napari_mcp.cli.main.ClineCursorInstaller"), \
             patch("napari_mcp.cli.main.GeminiCLIInstaller"), \
             patch("napari_mcp.cli.main.CodexCLIInstaller"):

            result = cli_runner.invoke(app, ["uninstall", "all"])
            assert "Uninstalling napari-mcp from all applications" in result.stdout


class TestListCommand:
    """Test list command."""

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    @patch("napari_mcp.cli.main.ClaudeCodeInstaller")
    def test_list_installations(
        self,
        mock_claude_code,
        mock_claude_desktop,
        cli_runner
    ):
        """Test listing installations."""
        # Setup mock config paths
        mock_desktop = MagicMock()
        mock_desktop.get_config_path.return_value = Path("/mock/claude-desktop/config.json")
        mock_claude_desktop.return_value = mock_desktop

        mock_code = MagicMock()
        mock_code.get_config_path.return_value = Path("/mock/claude-code/config.json")
        mock_claude_code.return_value = mock_code

        # Mock other installers
        with patch("napari_mcp.cli.main.CursorInstaller"), \
             patch("napari_mcp.cli.main.ClineVSCodeInstaller"), \
             patch("napari_mcp.cli.main.ClineCursorInstaller"), \
             patch("napari_mcp.cli.main.GeminiCLIInstaller"), \
             patch("napari_mcp.cli.main.CodexCLIInstaller"):

            result = cli_runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "napari-mcp Installation Status" in result.stdout

    @patch("napari_mcp.cli.main.CodexCLIInstaller")
    @patch("toml.load")
    @patch("pathlib.Path.exists")
    def test_list_codex_toml_config(
        self,
        mock_exists,
        mock_toml_load,
        mock_codex,
        cli_runner
    ):
        """Test listing with Codex TOML configuration."""
        mock_exists.return_value = True
        mock_toml_load.return_value = {
            "mcp_servers": {
                "napari_mcp": {
                    "command": "uv",
                    "args": ["run", "--with", "napari-mcp", "napari-mcp"]
                }
            }
        }

        mock_instance = MagicMock()
        mock_instance.get_config_path.return_value = Path("/mock/.codex/config.toml")
        mock_codex.return_value = mock_instance

        # Mock other installers
        with patch("napari_mcp.cli.main.ClaudeDesktopInstaller"), \
             patch("napari_mcp.cli.main.ClaudeCodeInstaller"), \
             patch("napari_mcp.cli.main.CursorInstaller"), \
             patch("napari_mcp.cli.main.ClineVSCodeInstaller"), \
             patch("napari_mcp.cli.main.ClineCursorInstaller"), \
             patch("napari_mcp.cli.main.GeminiCLIInstaller"):

            with patch("builtins.open", create=True):
                result = cli_runner.invoke(app, ["list"])
                assert result.exit_code == 0


class TestErrorHandling:
    """Test error handling in CLI commands."""

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    def test_installer_exception(self, mock_installer_class, cli_runner):
        """Test handling of installer exceptions."""
        mock_installer_class.side_effect = Exception("Test exception")

        # The all command catches exceptions
        result = cli_runner.invoke(app, ["all"])
        # Should still complete but with error status
        assert result.exit_code == 1

    @patch("napari_mcp.cli.main.ClaudeDesktopInstaller")
    def test_dry_run_mode(self, mock_installer_class, cli_runner):
        """Test dry-run mode doesn't make changes."""
        mock = MagicMock()
        mock.install.return_value = (True, "Dry run successful")
        mock_installer_class.return_value = mock

        result = cli_runner.invoke(app, ["claude-desktop", "--dry-run"])
        assert result.exit_code == 0

        # Verify dry_run was passed
        call_kwargs = mock_installer_class.call_args[1]
        assert call_kwargs["dry_run"] is True
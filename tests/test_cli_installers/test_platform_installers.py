"""Tests for platform-specific installers."""

from pathlib import Path
from unittest.mock import mock_open, patch

from napari_mcp.cli.install.claude_code import ClaudeCodeInstaller
from napari_mcp.cli.install.claude_desktop import ClaudeDesktopInstaller
from napari_mcp.cli.install.cline_cursor import ClineCursorInstaller
from napari_mcp.cli.install.cline_vscode import ClineVSCodeInstaller
from napari_mcp.cli.install.codex_cli import CodexCLIInstaller
from napari_mcp.cli.install.cursor import CursorInstaller
from napari_mcp.cli.install.gemini_cli import GeminiCLIInstaller


class TestClaudeDesktopInstaller:
    """Test Claude Desktop installer."""

    @patch("napari_mcp.cli.install.claude_desktop.get_platform")
    def test_config_path_macos(self, mock_platform):
        """Test config path on macOS."""
        mock_platform.return_value = "macos"
        installer = ClaudeDesktopInstaller()
        path = installer.get_config_path()
        assert "Library/Application Support/Claude" in str(path)
        assert path.name == "claude_desktop_config.json"

    @patch("napari_mcp.cli.install.claude_desktop.get_platform")
    def test_config_path_windows(self, mock_platform):
        """Test config path on Windows."""
        mock_platform.return_value = "windows"
        with patch.dict("os.environ", {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
            installer = ClaudeDesktopInstaller()
            path = installer.get_config_path()
            assert "Claude" in str(path)
            assert path.name == "claude_desktop_config.json"

    @patch("napari_mcp.cli.install.claude_desktop.get_platform")
    def test_config_path_linux(self, mock_platform):
        """Test config path on Linux."""
        mock_platform.return_value = "linux"
        installer = ClaudeDesktopInstaller()
        path = installer.get_config_path()
        assert ".config/Claude" in str(path)
        assert path.name == "claude_desktop_config.json"

    def test_no_extra_config(self):
        """Test Claude Desktop has no extra configuration."""
        installer = ClaudeDesktopInstaller()
        assert installer.get_extra_config() == {}


class TestClaudeCodeInstaller:
    """Test Claude Code installer."""

    def test_config_path_all_platforms(self):
        """Test config path is always ~/.claude.json."""
        installer = ClaudeCodeInstaller()
        path = installer.get_config_path()
        assert path.name == ".claude.json"
        assert ".claude.json" in str(path)

    def test_no_extra_config(self):
        """Test Claude Code has no extra configuration."""
        installer = ClaudeCodeInstaller()
        assert installer.get_extra_config() == {}


class TestCursorInstaller:
    """Test Cursor IDE installer."""

    def test_global_config_path(self):
        """Test global Cursor configuration path."""
        installer = CursorInstaller(global_install=True)
        path = installer.get_config_path()
        assert ".cursor/mcp.json" in str(path)

    def test_project_config_path(self):
        """Test project-specific configuration path."""
        with patch("napari_mcp.cli.install.cursor.Confirm.ask", return_value=True):
            installer = CursorInstaller(project_dir="/my/project")
            path = installer.get_config_path()
            assert "/my/project" in str(path)
            assert "mcp.json" in str(path)

    def test_default_project_config(self):
        """Test default project configuration (current directory)."""
        installer = CursorInstaller(global_install=True)
        path = installer.get_config_path()
        assert path.name == "mcp.json"
        assert ".cursor" in str(path)

    def test_no_extra_config(self):
        """Test Cursor has no extra configuration."""
        installer = CursorInstaller()
        assert installer.get_extra_config() == {}


class TestClineInstallers:
    """Test Cline installers for VS Code and Cursor IDE."""

    @patch("napari_mcp.cli.install.cline_vscode.get_platform")
    def test_cline_vscode_path_macos(self, mock_platform):
        """Test Cline VS Code path on macOS."""
        mock_platform.return_value = "macos"
        installer = ClineVSCodeInstaller()
        path = installer.get_config_path()
        assert "Application Support/Code/User/globalStorage" in str(path)
        assert "saoudrizwan.claude-dev" in str(path)
        assert path.name == "cline_mcp_settings.json"

    @patch("napari_mcp.cli.install.cline_vscode.get_platform")
    def test_cline_vscode_path_windows(self, mock_platform):
        """Test Cline VS Code path on Windows."""
        mock_platform.return_value = "windows"
        with patch.dict("os.environ", {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
            installer = ClineVSCodeInstaller()
            path = installer.get_config_path()
            assert "globalStorage" in str(path)

    @patch("napari_mcp.cli.install.cline_vscode.get_platform")
    def test_cline_vscode_path_linux(self, mock_platform):
        """Test Cline VS Code path on Linux."""
        mock_platform.return_value = "linux"
        installer = ClineVSCodeInstaller()
        path = installer.get_config_path()
        assert "globalStorage" in str(path)

    @patch("napari_mcp.cli.install.cline_cursor.get_platform")
    def test_cline_cursor_path_macos(self, mock_platform):
        """Test Cline Cursor path on macOS."""
        mock_platform.return_value = "macos"
        installer = ClineCursorInstaller()
        path = installer.get_config_path()
        assert "Application Support/Cursor/User/globalStorage" in str(path)
        assert "saoudrizwan.claude-dev" in str(path)

    def test_cline_extra_config(self):
        """Test Cline extra configuration."""
        installer = ClineVSCodeInstaller()
        config = installer.get_extra_config()
        assert "alwaysAllow" in config
        assert config["disabled"] is False

        installer2 = ClineCursorInstaller()
        config2 = installer2.get_extra_config()
        assert "alwaysAllow" in config2


class TestGeminiCLIInstaller:
    """Test Gemini CLI installer."""

    def test_global_config_path(self):
        """Test global Gemini configuration."""
        installer = GeminiCLIInstaller(global_install=True)
        path = installer.get_config_path()
        assert ".gemini/settings.json" in str(path)

    def test_project_config_path(self):
        """Test project-specific Gemini configuration."""
        with patch("napari_mcp.cli.install.gemini_cli.Confirm.ask", return_value=True):
            installer = GeminiCLIInstaller(project_dir="/my/project")
            path = installer.get_config_path()
            assert "/my/project" in str(path)
            assert "settings.json" in str(path)

    def test_default_project_config(self):
        """Test default project configuration."""
        installer = GeminiCLIInstaller(global_install=True)
        path = installer.get_config_path()
        assert path.name == "settings.json"
        assert ".gemini" in str(path)

    def test_extra_config(self):
        """Test Gemini extra configuration."""
        installer = GeminiCLIInstaller()
        config = installer.get_extra_config()
        assert config["cwd"] == "."
        assert config["timeout"] == 600000
        assert config["trust"] is False


class TestCodexCLIInstaller:
    """Test Codex CLI installer."""

    def test_config_path(self):
        """Test Codex configuration path."""
        installer = CodexCLIInstaller()
        path = installer.get_config_path()
        assert ".codex/config.toml" in str(path)
        assert path.suffix == ".toml"

    def test_no_extra_config(self):
        """Test Codex has no extra configuration."""
        installer = CodexCLIInstaller()
        assert installer.get_extra_config() == {}

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("toml.load")
    @patch("toml.dump")
    def test_install_toml_format(
        self, mock_dump, mock_load, mock_mkdir, mock_exists, mock_file
    ):
        """Test Codex installer uses TOML format."""
        mock_exists.return_value = False
        installer = CodexCLIInstaller()

        with patch.object(installer, "validate_environment") as mock_validate:
            mock_validate.return_value = True

            success, message = installer.install()

            assert success is True
            # Verify toml.dump was called
            mock_dump.assert_called_once()

            # Check the config structure passed to toml.dump
            call_args = mock_dump.call_args[0]
            config = call_args[0]
            assert "mcp_servers" in config
            assert "napari_mcp" in config["mcp_servers"]

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("toml.load")
    @patch("toml.dump")
    def test_uninstall_toml_format(self, mock_dump, mock_load, mock_exists, mock_file):
        """Test Codex uninstaller handles TOML format."""
        mock_exists.return_value = True
        existing_config = {
            "mcp_servers": {
                "napari_mcp": {"command": "uv"},
                "other": {"command": "python"},
            }
        }
        mock_load.return_value = existing_config

        installer = CodexCLIInstaller()

        success, message = installer.uninstall()

        assert success is True
        # Verify toml.dump was called
        mock_dump.assert_called_once()

        # Check that napari_mcp was removed
        call_args = mock_dump.call_args[0]
        config = call_args[0]
        assert "napari_mcp" not in config["mcp_servers"]
        assert "other" in config["mcp_servers"]


class TestInstallerEdgeCases:
    """Test edge cases for installers."""

    def test_cursor_installer_path_expansion(self):
        """Test Cursor installer expands paths correctly."""
        with patch("napari_mcp.cli.install.cursor.Confirm.ask", return_value=True):
            installer = CursorInstaller(project_dir="/home/test/myproject")
            path = installer.get_config_path()
            assert "/home/test/myproject" in str(path)

    def test_gemini_installer_path_expansion(self):
        """Test Gemini installer expands paths correctly."""
        with patch("napari_mcp.cli.install.gemini_cli.Confirm.ask", return_value=True):
            installer = GeminiCLIInstaller(project_dir="/home/test/myproject")
            path = installer.get_config_path()
            assert "/home/test/myproject" in str(path)

    @patch("napari_mcp.cli.install.utils.get_platform")
    def test_platform_specific_paths_all_platforms(self, mock_platform):
        """Test all installers handle all platforms."""
        platforms = ["macos", "windows", "linux"]
        installers = [
            ClaudeDesktopInstaller,
            ClaudeCodeInstaller,
            ClineVSCodeInstaller,
            ClineCursorInstaller,
        ]

        for platform_name in platforms:
            mock_platform.return_value = platform_name
            for installer_class in installers:
                installer = installer_class()
                path = installer.get_config_path()
                assert path is not None
                assert isinstance(path, Path)

    def test_all_installers_have_required_methods(self):
        """Test all installers implement required methods."""
        installers = [
            ClaudeDesktopInstaller(),
            ClaudeCodeInstaller(),
            CursorInstaller(global_install=True),  # Avoid prompts
            ClineVSCodeInstaller(),
            ClineCursorInstaller(),
            GeminiCLIInstaller(global_install=True),  # Avoid prompts
            CodexCLIInstaller(),
        ]

        for installer in installers:
            # Test required methods exist and return correct types
            path = installer.get_config_path()
            assert isinstance(path, Path)

            extra = installer.get_extra_config()
            assert isinstance(extra, dict)

            # Test app_key is set
            assert hasattr(installer, "app_key")
            assert installer.app_key is not None


class TestInstallerIntegration:
    """Test installer integration scenarios."""

    @patch("napari_mcp.cli.install.utils.read_json_config")
    @patch("napari_mcp.cli.install.utils.write_json_config")
    def test_claude_desktop_full_install(self, mock_write, mock_read):
        """Test full installation flow for Claude Desktop."""
        mock_read.return_value = {}
        mock_write.return_value = True

        installer = ClaudeDesktopInstaller(
            persistent=False, force=True, backup=True, dry_run=False
        )

        with patch.object(installer, "validate_environment") as mock_validate:
            mock_validate.return_value = True
            success, message = installer.install()

        assert success is True
        assert "successful" in message.lower()

    @patch("napari_mcp.cli.install.base.validate_python_environment")
    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.write_json_config")
    @patch("napari_mcp.cli.install.base.build_server_config")
    @patch("napari_mcp.cli.install.base.get_python_executable")
    def test_cursor_project_install(
        self, mock_get_exe, mock_build, mock_write, mock_read, mock_validate_env
    ):
        """Test project-specific installation for Cursor."""
        mock_read.return_value = {}
        mock_write.return_value = True
        mock_get_exe.return_value = ("/usr/bin/python3", "custom Python")
        mock_build.return_value = {
            "command": "/usr/bin/python3",
            "args": ["-m", "napari_mcp.server"],
        }
        mock_validate_env.return_value = True

        with patch("napari_mcp.cli.install.cursor.Confirm.ask", return_value=True):
            installer = CursorInstaller(
                project_dir="/my/project",
                persistent=True,
                python_path="/usr/bin/python3",
            )

            success, message = installer.install()

        assert success is True
        # Verify correct path was used - check if mock_write was called
        assert mock_write.called

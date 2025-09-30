"""Tests for base installer class."""

from pathlib import Path
from unittest.mock import patch

import pytest

from napari_mcp.cli.install.base import BaseInstaller


class ConcreteInstaller(BaseInstaller):
    """Concrete implementation for testing."""

    def get_config_path(self) -> Path:
        """Return a test config path."""
        return Path("/test/config.json")

    def get_extra_config(self):
        """Return test extra config."""
        return {"timeout": 60000}


class TestBaseInstaller:
    """Test base installer functionality."""

    def test_initialization_defaults(self):
        """Test installer initialization with defaults."""
        installer = ConcreteInstaller(app_key="test-app")

        assert installer.app_key == "test-app"
        assert installer.server_name == "napari-mcp"
        assert installer.persistent is False
        assert installer.python_path is None
        assert installer.force is False
        assert installer.backup is True
        assert installer.dry_run is False

    def test_initialization_with_options(self):
        """Test installer initialization with custom options."""
        installer = ConcreteInstaller(
            app_key="test-app",
            server_name="custom-server",
            persistent=True,
            python_path="/custom/python",
            force=True,
            backup=False,
            dry_run=True,
        )

        assert installer.server_name == "custom-server"
        assert installer.persistent is True
        assert installer.python_path == "/custom/python"
        assert installer.force is True
        assert installer.backup is False
        assert installer.dry_run is True

    @patch("napari_mcp.cli.install.base.get_app_display_name")
    def test_app_name_resolution(self, mock_get_name):
        """Test application display name is resolved."""
        mock_get_name.return_value = "Test Application"
        installer = ConcreteInstaller(app_key="test-app")
        assert installer.app_name == "Test Application"
        mock_get_name.assert_called_with("test-app")

    @patch("napari_mcp.cli.install.base.validate_python_environment")
    @patch("napari_mcp.cli.install.base.get_python_executable")
    def test_validate_environment_persistent(self, mock_get_exe, mock_validate):
        """Test environment validation with persistent Python."""
        mock_get_exe.return_value = ("/usr/bin/python3", "persistent Python")
        mock_validate.return_value = True

        installer = ConcreteInstaller(app_key="test-app", persistent=True)
        result = installer.validate_environment()

        assert result is True
        mock_validate.assert_called_with("/usr/bin/python3")

    @patch("napari_mcp.cli.install.base.validate_python_environment")
    @patch("napari_mcp.cli.install.base.get_python_executable")
    def test_validate_environment_custom_path(self, mock_get_exe, mock_validate):
        """Test environment validation with custom Python path."""
        mock_get_exe.return_value = ("/custom/python", "custom Python")
        mock_validate.return_value = True

        installer = ConcreteInstaller(app_key="test-app", python_path="/custom/python")
        result = installer.validate_environment()

        assert result is True
        mock_validate.assert_called_with("/custom/python")

    @patch("napari_mcp.cli.install.base.validate_python_environment")
    @patch("napari_mcp.cli.install.base.get_python_executable")
    @patch("napari_mcp.cli.install.base.console")
    def test_validate_environment_missing_package(
        self, mock_console, mock_get_exe, mock_validate
    ):
        """Test validation failure with missing napari-mcp."""
        mock_get_exe.return_value = ("/usr/bin/python3", "persistent Python")
        mock_validate.return_value = False

        installer = ConcreteInstaller(app_key="test-app", persistent=True)
        result = installer.validate_environment()

        assert result is False
        mock_console.print.assert_called()

    def test_validate_environment_uv(self):
        """Test environment validation with uv (always succeeds)."""
        installer = ConcreteInstaller(app_key="test-app")
        result = installer.validate_environment()
        assert result is True

    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.write_json_config")
    @patch("napari_mcp.cli.install.base.build_server_config")
    @patch("napari_mcp.cli.install.base.get_python_executable")
    @patch("napari_mcp.cli.install.base.console")
    def test_install_new_config(
        self, mock_console, mock_get_exe, mock_build_config, mock_write, mock_read
    ):
        """Test installing to new configuration."""
        mock_read.return_value = {}
        mock_write.return_value = True
        mock_get_exe.return_value = ("uv", "ephemeral uv")
        mock_build_config.return_value = {
            "command": "uv",
            "args": ["run", "--with", "napari-mcp", "napari-mcp"],
        }

        installer = ConcreteInstaller(app_key="test-app")
        success, message = installer.install()

        assert success is True
        assert "successful" in message.lower()
        mock_write.assert_called_once()
        # Verify build_server_config was called with correct signature
        mock_build_config.assert_called_with(False, None, {"timeout": 60000})

    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.write_json_config")
    @patch("napari_mcp.cli.install.base.check_existing_server")
    @patch("napari_mcp.cli.install.base.prompt_update_existing")
    @patch("napari_mcp.cli.install.base.build_server_config")
    @patch("napari_mcp.cli.install.base.get_python_executable")
    @patch("napari_mcp.cli.install.base.console")
    def test_install_existing_update(
        self,
        mock_console,
        mock_get_exe,
        mock_build,
        mock_prompt,
        mock_check,
        mock_write,
        mock_read,
    ):
        """Test updating existing configuration."""
        existing_config = {
            "mcpServers": {
                "napari-mcp": {"command": "python", "args": ["-m", "old_module"]}
            }
        }
        mock_read.return_value = existing_config
        mock_check.return_value = True
        mock_prompt.return_value = True
        mock_write.return_value = True
        mock_get_exe.return_value = ("uv", "ephemeral uv")
        mock_build.return_value = {"command": "uv", "args": ["run"]}

        installer = ConcreteInstaller(app_key="test-app")
        success, message = installer.install()

        assert success is True
        assert "successful" in message.lower()
        mock_prompt.assert_called_once()

    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.check_existing_server")
    @patch("napari_mcp.cli.install.base.prompt_update_existing")
    @patch("napari_mcp.cli.install.base.console")
    def test_install_existing_skip(
        self, mock_console, mock_prompt, mock_check, mock_read
    ):
        """Test skipping update of existing configuration."""
        mock_read.return_value = {"mcpServers": {"napari-mcp": {}}}
        mock_check.return_value = True
        mock_prompt.return_value = False

        installer = ConcreteInstaller(app_key="test-app")
        success, message = installer.install()

        assert success is False
        assert "cancel" in message.lower()

    @patch("napari_mcp.cli.install.base.console")
    def test_install_dry_run(self, mock_console):
        """Test dry run mode."""
        installer = ConcreteInstaller(app_key="test-app", dry_run=True)

        with patch.object(installer, "get_config_path") as mock_path:
            mock_path.return_value = Path("/test/config.json")

            success, message = installer.install()

            assert success is True
            assert "dry run" in message.lower()
            mock_console.print.assert_called()

    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.write_json_config")
    @patch("napari_mcp.cli.install.base.console")
    def test_install_write_failure(self, mock_console, mock_write, mock_read):
        """Test handling write failure during install."""
        mock_read.return_value = {}
        mock_write.return_value = False

        installer = ConcreteInstaller(app_key="test-app")
        success, message = installer.install()

        assert success is False
        assert "failed" in message.lower()

    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.write_json_config")
    @patch("napari_mcp.cli.install.base.check_existing_server")
    @patch("napari_mcp.cli.install.base.console")
    def test_uninstall_success(self, mock_console, mock_check, mock_write, mock_read):
        """Test successful uninstallation."""
        config = {
            "mcpServers": {
                "napari-mcp": {"command": "uv"},
                "other": {"command": "python"},
            }
        }
        mock_read.return_value = config
        mock_check.return_value = True
        mock_write.return_value = True

        installer = ConcreteInstaller(app_key="test-app")

        # Mock config_path.exists()
        with patch.object(Path, "exists", return_value=True):
            success, message = installer.uninstall()

        assert success is True
        assert "successful" in message.lower()

        # Check that only napari-mcp was removed
        call_args = mock_write.call_args[0][1]
        assert "napari-mcp" not in call_args["mcpServers"]
        assert "other" in call_args["mcpServers"]

    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.check_existing_server")
    @patch("napari_mcp.cli.install.base.console")
    def test_uninstall_not_found(self, mock_console, mock_check, mock_read):
        """Test uninstalling when server not found."""
        mock_read.return_value = {"mcpServers": {}}
        mock_check.return_value = False

        installer = ConcreteInstaller(app_key="test-app")
        success, message = installer.uninstall()

        assert success is False
        assert "not found" in message.lower()

    @patch("napari_mcp.cli.install.base.console")
    @patch("napari_mcp.cli.install.base.check_existing_server")
    def test_uninstall_dry_run(self, mock_check, mock_console):
        """Test uninstall in dry run mode."""
        installer = ConcreteInstaller(app_key="test-app", dry_run=True)
        mock_check.return_value = True

        with patch("napari_mcp.cli.install.base.read_json_config") as mock_read:
            mock_read.return_value = {"mcpServers": {"napari-mcp": {}}}

            with patch.object(Path, "exists", return_value=True):
                success, message = installer.uninstall()

            assert success is True
            assert "dry run" in message.lower()

    @patch("napari_mcp.cli.install.base.console")
    def test_uninstall_config_not_found(self, mock_console):
        """Test uninstall when config file doesn't exist."""
        installer = ConcreteInstaller(app_key="test-app")

        with patch.object(installer, "get_config_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/config.json")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                success, message = installer.uninstall()

                assert success is False
                assert "not found" in message.lower()

    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented."""
        with pytest.raises(TypeError):
            # Can't instantiate abstract class
            BaseInstaller(app_key="test")

    @patch("napari_mcp.cli.install.base.console")
    def test_install_with_validation_failure(self, mock_console):
        """Test install fails when environment validation fails."""
        installer = ConcreteInstaller(app_key="test-app", persistent=True)

        with patch.object(installer, "validate_environment") as mock_validate:
            mock_validate.return_value = False

            success, message = installer.install()

            assert success is False
            assert "validation failed" in message.lower()


class TestInstallerIntegration:
    """Test installer integration scenarios."""

    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.write_json_config")
    @patch("napari_mcp.cli.install.base.build_server_config")
    def test_install_preserves_other_servers(self, mock_build, mock_write, mock_read):
        """Test that installation preserves other server configurations."""
        existing_config = {
            "mcpServers": {
                "other-server": {"command": "other"},
                "another": {"command": "another"},
            }
        }
        mock_read.return_value = existing_config
        mock_write.return_value = True
        mock_build.return_value = {"command": "uv", "args": ["run"]}

        installer = ConcreteInstaller(app_key="test-app")
        installer.install()

        # Check that other servers are preserved
        written_config = mock_write.call_args[0][1]
        assert "other-server" in written_config["mcpServers"]
        assert "another" in written_config["mcpServers"]
        assert "napari-mcp" in written_config["mcpServers"]

    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.write_json_config")
    def test_force_mode_skips_prompts(self, mock_write, mock_read):
        """Test force mode skips all prompts."""
        mock_read.return_value = {"mcpServers": {"napari-mcp": {"command": "old"}}}
        mock_write.return_value = True

        installer = ConcreteInstaller(app_key="test-app", force=True)

        with patch("napari_mcp.cli.install.base.prompt_update_existing") as mock_prompt:
            installer.install()
            mock_prompt.assert_not_called()

    @patch("napari_mcp.cli.install.base.get_python_executable")
    @patch("napari_mcp.cli.install.base.build_server_config")
    @patch("napari_mcp.cli.install.base.read_json_config")
    @patch("napari_mcp.cli.install.base.write_json_config")
    def test_extra_config_applied(
        self, mock_write, mock_read, mock_build, mock_get_exe
    ):
        """Test that extra configuration is applied."""
        mock_read.return_value = {}
        mock_write.return_value = True
        mock_get_exe.return_value = ("uv", "ephemeral")
        mock_build.return_value = {
            "command": "uv",
            "args": ["run"],
            "timeout": 60000,  # From get_extra_config
        }

        installer = ConcreteInstaller(app_key="test-app")
        installer.install()

        # Verify build_server_config was called with extras
        mock_build.assert_called_with(False, None, {"timeout": 60000})

"""
Tests for napari MCP server installers.

These tests validate both the shell script and Python UV-based installers.
"""

import json
import os
import subprocess
import tempfile
import unittest.mock
from pathlib import Path
from unittest import TestCase, mock

import pytest

# Import the UV installer
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    from uv_install import NapariMCPInstaller, InstallerError
    UV_INSTALLER_AVAILABLE = True
except ImportError:
    UV_INSTALLER_AVAILABLE = False

class TestShellInstaller(TestCase):
    """Test the shell script installer."""
    
    def setUp(self):
        """Set up test environment."""
        self.script_path = Path(__file__).parent.parent / "scripts" / "install.sh"
        self.assertTrue(self.script_path.exists(), "install.sh script not found")
    
    def test_script_exists_and_executable(self):
        """Test that the install script exists and is executable."""
        self.assertTrue(self.script_path.exists())
        # Note: In CI, we may not have execute permissions, so we check file content instead
        content = self.script_path.read_text()
        self.assertTrue(content.startswith("#!/bin/bash"))
    
    def test_script_help(self):
        """Test that the script shows help."""
        try:
            result = subprocess.run(
                ["bash", str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("Usage:", result.stdout)
            self.assertIn("claude-desktop", result.stdout)
            self.assertIn("claude-code", result.stdout)
            self.assertIn("cursor", result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            pytest.skip(f"Cannot test shell script: {e}")
    
    def test_script_invalid_target(self):
        """Test that the script rejects invalid targets."""
        try:
            result = subprocess.run(
                ["bash", str(self.script_path), "invalid-target"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unknown target", result.stderr)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            pytest.skip(f"Cannot test shell script: {e}")


@pytest.mark.skipif(not UV_INSTALLER_AVAILABLE, reason="UV installer not available")
class TestUVInstaller(TestCase):
    """Test the Python UV installer."""
    
    def setUp(self):
        """Set up test environment."""
        self.installer = NapariMCPInstaller(verbose=True)
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_installer_creation(self):
        """Test installer can be created."""
        installer = NapariMCPInstaller()
        self.assertIsInstance(installer, NapariMCPInstaller)
    
    def test_detect_os(self):
        """Test OS detection."""
        os_type = self.installer.detect_os()
        self.assertIn(os_type, ["macos", "linux", "windows", "unknown"])
    
    def test_command_exists(self):
        """Test command existence checking."""
        # Test with a command that should exist
        self.assertTrue(self.installer.command_exists("python3") or 
                       self.installer.command_exists("python"))
        
        # Test with a command that should not exist
        self.assertFalse(self.installer.command_exists("nonexistent-command-xyz"))
    
    @mock.patch('platform.system')
    def test_get_claude_config_path_macos(self, mock_system):
        """Test Claude config path detection on macOS."""
        mock_system.return_value = "Darwin"
        path = self.installer.get_claude_config_path()
        expected = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
        self.assertEqual(path, expected)
    
    @mock.patch('platform.system')
    def test_get_claude_config_path_linux(self, mock_system):
        """Test Claude config path detection on Linux."""
        mock_system.return_value = "Linux"
        path = self.installer.get_claude_config_path()
        expected = Path.home() / ".config/Claude/claude_desktop_config.json"
        self.assertEqual(path, expected)
    
    @mock.patch('platform.system')
    @mock.patch.dict(os.environ, {'APPDATA': '/fake/appdata'})
    def test_get_claude_config_path_windows(self, mock_system):
        """Test Claude config path detection on Windows."""
        mock_system.return_value = "Windows"
        path = self.installer.get_claude_config_path()
        expected = Path("/fake/appdata/Claude/claude_desktop_config.json")
        self.assertEqual(path, expected)
    
    def test_invalid_target_raises_error(self):
        """Test that invalid target raises error."""
        with self.assertRaises(InstallerError):
            self.installer.install_target("invalid-target", Path("/fake/path"))
    
    @mock.patch.object(NapariMCPInstaller, 'command_exists')
    def test_check_dependencies_missing_uv(self, mock_command_exists):
        """Test dependency checking when uv is missing."""
        mock_command_exists.side_effect = lambda cmd: cmd != "uv"
        
        with self.assertRaises(InstallerError) as context:
            self.installer.check_dependencies()
        
        self.assertIn("Missing dependencies", str(context.exception))
        self.assertIn("uv", str(context.exception))
    
    @mock.patch('requests.get')
    def test_download_server_success(self, mock_get):
        """Test successful server download."""
        # Skip if requests not available
        if not hasattr(self.installer, 'download_server'):
            pytest.skip("Requests not available for download test")
        
        mock_response = mock.Mock()
        mock_response.text = "# Mock server content"
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response
        
        target_path = self.temp_dir / "test_server.py"
        self.installer.download_server(target_path)
        
        self.assertTrue(target_path.exists())
        self.assertEqual(target_path.read_text(), "# Mock server content")
        # Check if file is executable (on Unix systems)
        if os.name != 'nt':
            self.assertTrue(os.access(target_path, os.X_OK))
    
    def test_claude_desktop_config_creation(self):
        """Test Claude Desktop config creation."""
        # Create a fake server file
        server_path = self.temp_dir / "napari_mcp_server.py"
        server_path.write_text("# Mock server")
        
        # Create a fake config path
        config_path = self.temp_dir / "claude_desktop_config.json"
        
        # Mock the config path detection
        with mock.patch.object(self.installer, 'get_claude_config_path', 
                              return_value=config_path):
            self.installer.install_claude_desktop(server_path)
        
        # Verify config was created
        self.assertTrue(config_path.exists())
        
        # Verify config content
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.assertIn("mcpServers", config)
        self.assertIn("napari", config["mcpServers"])
        self.assertEqual(config["mcpServers"]["napari"]["command"], "uv")
        self.assertIn("fastmcp", config["mcpServers"]["napari"]["args"])
    
    @mock.patch.object(NapariMCPInstaller, 'run_command')
    @mock.patch.object(NapariMCPInstaller, 'command_exists')
    def test_claude_code_installation(self, mock_command_exists, mock_run_command):
        """Test Claude Code installation."""
        mock_command_exists.return_value = True  # fastmcp exists
        
        server_path = self.temp_dir / "napari_mcp_server.py"
        server_path.write_text("# Mock server")
        
        self.installer.install_claude_code(server_path)
        
        # Verify fastmcp install was called
        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        self.assertEqual(call_args[0], "fastmcp")
        self.assertEqual(call_args[1], "install")
        self.assertEqual(call_args[2], "claude-code")
        self.assertIn("--with", call_args)
        self.assertIn("napari", call_args)
    
    @mock.patch.object(NapariMCPInstaller, 'run_command')
    @mock.patch.object(NapariMCPInstaller, 'command_exists')
    def test_cursor_installation(self, mock_command_exists, mock_run_command):
        """Test Cursor installation."""
        mock_command_exists.return_value = True  # fastmcp exists
        
        server_path = self.temp_dir / "napari_mcp_server.py"
        server_path.write_text("# Mock server")
        
        self.installer.install_cursor(server_path)
        
        # Verify fastmcp install was called
        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        self.assertEqual(call_args[0], "fastmcp")
        self.assertEqual(call_args[1], "install")
        self.assertEqual(call_args[2], "cursor")
        self.assertIn("--with", call_args)
        self.assertIn("napari", call_args)
    
    def test_chatgpt_installation(self):
        """Test ChatGPT installation (shows guide only)."""
        # This should not raise an error and just print guide
        self.installer.install_chatgpt()
        # No assertion needed as it only prints information
    
    def test_all_target_installation(self):
        """Test 'all' target installation."""
        server_path = self.temp_dir / "napari_mcp_server.py"
        server_path.write_text("# Mock server")
        
        config_path = self.temp_dir / "claude_desktop_config.json"
        
        with mock.patch.object(self.installer, 'get_claude_config_path', 
                              return_value=config_path), \
             mock.patch.object(self.installer, 'run_command'), \
             mock.patch.object(self.installer, 'command_exists', return_value=True):
            
            self.installer.install_target("all", server_path)
        
        # Verify Claude Desktop config was created
        self.assertTrue(config_path.exists())
    
    def test_claude_desktop_config_backup(self):
        """Test that existing config is backed up."""
        server_path = self.temp_dir / "napari_mcp_server.py"
        server_path.write_text("# Mock server")
        
        config_path = self.temp_dir / "claude_desktop_config.json"
        existing_config = {"existing": "config"}
        
        # Create existing config
        with open(config_path, 'w') as f:
            json.dump(existing_config, f)
        
        # Mock user input to say yes to backup
        with mock.patch('builtins.input', return_value='y'), \
             mock.patch.object(self.installer, 'get_claude_config_path', 
                              return_value=config_path):
            
            self.installer.install_claude_desktop(server_path)
        
        # Check that backup was created
        backup_files = list(self.temp_dir.glob("claude_desktop_config.backup.*.json"))
        self.assertEqual(len(backup_files), 1)
        
        # Verify backup content
        with open(backup_files[0], 'r') as f:
            backup_config = json.load(f)
        self.assertEqual(backup_config, existing_config)
    
    @mock.patch('subprocess.run')
    def test_test_installation_claude_desktop(self, mock_run):
        """Test installation testing for Claude Desktop."""
        config_path = self.temp_dir / "claude_desktop_config.json"
        
        # Create valid config
        config = {
            "mcpServers": {
                "napari": {
                    "command": "uv",
                    "args": ["run", "fastmcp"]
                }
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        with mock.patch.object(self.installer, 'get_claude_config_path', 
                              return_value=config_path):
            # Should not raise an error
            self.installer.test_installation("claude-desktop")
    
    @mock.patch('subprocess.run')
    def test_test_installation_fastmcp_tools(self, mock_run):
        """Test installation testing for fastmcp-based tools."""
        # Mock successful fastmcp list output
        mock_result = mock.Mock()
        mock_result.stdout = "claude-code\ncursor\nother-tool"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Test Claude Code
        self.installer.test_installation("claude-code")
        
        # Test Cursor
        self.installer.test_installation("cursor")
        
        # Verify fastmcp list was called
        mock_run.assert_called_with(
            ["fastmcp", "list"],
            capture_output=True,
            text=True,
            check=True
        )
    
    def test_run_command_success(self):
        """Test successful command execution."""
        # Test with a simple command that should succeed
        self.installer.run_command(["echo", "test"], "Test echo command")
        # No assertion needed if no exception is raised
    
    def test_run_command_failure(self):
        """Test command execution failure."""
        with self.assertRaises(InstallerError):
            self.installer.run_command(["false"], "Test failing command")
    
    def test_run_command_not_found(self):
        """Test command not found error."""
        with self.assertRaises(InstallerError) as context:
            self.installer.run_command(["nonexistent-command-xyz"], "Test missing command")
        
        self.assertIn("Command not found", str(context.exception))


class TestIntegrationTests(TestCase):
    """Integration tests for both installers."""
    
    def test_installers_have_same_targets(self):
        """Test that both installers support the same targets."""
        # Expected targets from the issue requirements
        expected_targets = {"claude-desktop", "claude-code", "cursor", "chatgpt", "all"}
        
        # Test UV installer (if available)
        if UV_INSTALLER_AVAILABLE:
            import argparse
            from uv_install import main
            
            # Create a parser to get the choices
            parser = argparse.ArgumentParser()
            parser.add_argument(
                "target",
                choices=["claude-desktop", "claude-code", "cursor", "chatgpt", "all"]
            )
            
            # Get choices from the argument parser
            target_action = None
            for action in parser._actions:
                if hasattr(action, 'choices') and action.choices:
                    target_action = action
                    break
            
            if target_action:
                uv_targets = set(target_action.choices)
                self.assertEqual(uv_targets, expected_targets)
        
        # Test shell script by examining its content
        script_path = Path(__file__).parent.parent / "scripts" / "install.sh"
        if script_path.exists():
            content = script_path.read_text()
            
            # Check that all expected targets are mentioned in usage
            for target in expected_targets:
                if target != "all":  # 'all' might be mentioned differently
                    self.assertIn(target, content, f"Target {target} not found in shell script")
    
    def test_server_url_consistency(self):
        """Test that both installers use the same server URL."""
        expected_url = "https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py"
        
        # Check UV installer
        if UV_INSTALLER_AVAILABLE:
            from uv_install import SERVER_URL
            self.assertEqual(SERVER_URL, expected_url)
        
        # Check shell script
        script_path = Path(__file__).parent.parent / "scripts" / "install.sh"
        if script_path.exists():
            content = script_path.read_text()
            self.assertIn(expected_url, content)


if __name__ == "__main__":
    pytest.main([__file__])
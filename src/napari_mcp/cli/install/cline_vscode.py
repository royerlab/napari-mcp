"""Cline in VS Code installer for napari-mcp."""

from pathlib import Path
from typing import Any, Dict

from rich.console import Console

from .base import BaseInstaller
from .utils import expand_path, get_platform

console = Console()


class ClineVSCodeInstaller(BaseInstaller):
    """Installer for Cline extension in VS Code."""

    def __init__(self, **kwargs):
        """Initialize the Cline VS Code installer."""
        super().__init__(app_key="cline-vscode", **kwargs)

    def get_config_path(self) -> Path:
        """Get the Cline configuration file path.

        Returns
        -------
        Path
            Path to cline_mcp_settings.json for Cline.
        """
        platform = get_platform()

        # Cline stores config in VSCode's global storage directory
        if platform == "macos":
            # macOS path
            path = "~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
        elif platform == "windows":
            # Windows path
            path = "%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
        else:  # linux
            # Linux path
            path = "~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"

        return expand_path(path)

    def get_extra_config(self) -> Dict[str, Any]:
        """Get extra configuration for Cline.

        Returns
        -------
        Dict[str, Any]
            Additional configuration for Cline.
        """
        # Cline supports additional fields for tool permissions
        return {
            "alwaysAllow": [],  # Tools to always allow without prompting
            "disabled": False,  # Whether the server is disabled
        }

    def show_post_install_message(self) -> None:
        """Show post-installation instructions."""
        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"1. Open VS Code")
        console.print(f"2. Open the Cline extension")
        console.print(f"3. Click the MCP Servers icon to verify the installation")
        console.print(f"4. The napari-mcp server will be available")

        if self.persistent:
            console.print(f"\n[dim]Note: Using persistent Python environment[/dim]")
            console.print(f"[dim]Make sure napari-mcp is installed: pip install napari-mcp[/dim]")

        console.print(f"\n[dim]Tip: You can configure tool permissions in the Cline MCP settings[/dim]")
        console.print(f"[dim]Note: If using VS Code Insiders, the path will contain 'Code - Insiders' instead of 'Code'[/dim]")
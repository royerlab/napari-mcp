"""Cline in Cursor IDE installer for napari-mcp."""

from pathlib import Path
from typing import Any, Dict

from rich.console import Console

from .base import BaseInstaller
from .utils import expand_path, get_platform

console = Console()


class ClineCursorInstaller(BaseInstaller):
    """Installer for Cline extension in Cursor IDE."""

    def __init__(self, **kwargs):
        """Initialize the Cline Cursor installer."""
        super().__init__(app_key="cline-cursor", **kwargs)

    def get_config_path(self) -> Path:
        """Get the Cline configuration file path for Cursor IDE.

        Returns
        -------
        Path
            Path to cline_mcp_settings.json for Cline in Cursor.
        """
        platform = get_platform()

        # Cline stores config in Cursor's global storage directory
        if platform == "macos":
            # macOS path
            path = "~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
        elif platform == "windows":
            # Windows path
            path = "%APPDATA%/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
        else:  # linux
            # Linux path
            path = "~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"

        return expand_path(path)

    def get_extra_config(self) -> Dict[str, Any]:
        """Get extra configuration for Cline in Cursor.

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
        console.print(f"1. Open Cursor IDE")
        console.print(f"2. Open the Cline extension")
        console.print(f"3. Click the MCP Servers icon to verify the installation")
        console.print(f"4. The napari-mcp server will be available")

        if self.persistent:
            console.print(f"\n[dim]Note: Using persistent Python environment[/dim]")
            console.print(f"[dim]Make sure napari-mcp is installed: pip install napari-mcp[/dim]")

        console.print(f"\n[dim]Tip: You can configure tool permissions in the Cline MCP settings[/dim]")
        console.print(f"\n[yellow]Note: This configures Cline extension in Cursor IDE[/yellow]")
        console.print(f"[yellow]For Cursor's native MCP support, use: napari-mcp-install cursor[/yellow]")
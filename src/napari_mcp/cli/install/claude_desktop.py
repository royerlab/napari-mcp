"""Claude Desktop installer for napari-mcp."""

from pathlib import Path
from typing import Any, Dict

from .base import BaseInstaller
from .utils import expand_path, get_platform


class ClaudeDesktopInstaller(BaseInstaller):
    """Installer for Claude Desktop application."""

    def __init__(self, **kwargs):
        """Initialize Claude Desktop installer."""
        super().__init__(app_key="claude-desktop", **kwargs)

    def get_config_path(self) -> Path:
        """Get the Claude Desktop configuration file path.

        Returns
        -------
        Path
            Path to claude_desktop_config.json.
        """
        platform = get_platform()

        if platform == "macos":
            path = "~/Library/Application Support/Claude/claude_desktop_config.json"
        elif platform == "windows":
            path = "%APPDATA%/Claude/claude_desktop_config.json"
        else:  # linux
            path = "~/.config/Claude/claude_desktop_config.json"

        return expand_path(path)

    def get_extra_config(self) -> Dict[str, Any]:
        """Get extra configuration for Claude Desktop.

        Returns
        -------
        Dict[str, Any]
            Empty dict as Claude Desktop doesn't need extra fields.
        """
        return {}
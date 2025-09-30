"""Claude Code installer for napari-mcp."""

from pathlib import Path
from typing import Any, Dict

from .base import BaseInstaller
from .utils import expand_path


class ClaudeCodeInstaller(BaseInstaller):
    """Installer for Claude Code CLI."""

    def __init__(self, **kwargs):
        """Initialize Claude Code installer."""
        super().__init__(app_key="claude-code", **kwargs)

    def get_config_path(self) -> Path:
        """Get the Claude Code configuration file path.

        Returns
        -------
        Path
            Path to .claude.json in user home.
        """
        # Claude Code uses ~/.claude.json for MCP configuration
        return expand_path("~/.claude.json")

    def get_extra_config(self) -> Dict[str, Any]:
        """Get extra configuration for Claude Code.

        Returns
        -------
        Dict[str, Any]
            Empty dict as Claude Code doesn't need extra fields.
        """
        return {}
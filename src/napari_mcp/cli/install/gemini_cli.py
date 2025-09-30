"""Gemini CLI installer for napari-mcp."""

from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.prompt import Confirm

from .base import BaseInstaller
from .utils import expand_path

console = Console()


class GeminiCLIInstaller(BaseInstaller):
    """Installer for Gemini CLI."""

    def __init__(
        self,
        server_name: str = "napari-mcp",
        persistent: bool = False,
        python_path: Optional[str] = None,
        force: bool = False,
        backup: bool = True,
        dry_run: bool = False,
        global_install: bool = False,
        project_dir: Optional[str] = None,
    ):
        """Initialize the Gemini CLI installer.

        Parameters
        ----------
        server_name : str
            Name for the server in configuration.
        persistent : bool
            Use Python path instead of uv run.
        python_path : Optional[str]
            Custom Python executable path.
        force : bool
            Skip prompts and force update.
        backup : bool
            Create backup before updating.
        dry_run : bool
            Preview changes without applying.
        global_install : bool
            Install globally instead of project-specific.
        project_dir : Optional[str]
            Project directory for project-specific installation.
        """
        super().__init__(
            "gemini",
            server_name,
            persistent,
            python_path,
            force,
            backup,
            dry_run,
        )
        self.global_install = global_install
        self.project_dir = project_dir

    def get_config_path(self) -> Path:
        """Get the Gemini CLI configuration file path.

        Returns
        -------
        Path
            Path to settings.json for Gemini CLI.
        """
        if self.global_install:
            # Global configuration
            return expand_path("~/.gemini/settings.json")
        else:
            # Project-specific configuration
            if self.project_dir:
                base_path = expand_path(self.project_dir)
            else:
                # Use current working directory
                base_path = Path.cwd()

            config_path = base_path / ".gemini" / "settings.json"

            # Confirm project directory with user
            if not self.force and not self.dry_run:
                console.print(f"\n[cyan]Project directory: {base_path}[/cyan]")
                if not Confirm.ask("Install napari-mcp for this project?", default=True):
                    raise ValueError("User cancelled installation")

            return config_path

    def get_extra_config(self) -> Dict[str, Any]:
        """Get extra configuration for Gemini CLI.

        Returns
        -------
        Dict[str, Any]
            Gemini-specific configuration fields.
        """
        # Gemini CLI supports additional configuration fields
        return {
            "cwd": ".",  # Working directory for the server
            "timeout": 600000,  # Request timeout in milliseconds (10 minutes)
            "trust": False,  # Whether to bypass tool call confirmations
        }

    def show_post_install_message(self) -> None:
        """Show post-installation instructions."""
        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"1. Start Gemini CLI in your terminal")
        console.print(f"2. Run '/mcp refresh' command to reload servers")
        console.print(f"3. The napari-mcp server will be available")

        if self.persistent:
            console.print(f"\n[dim]Note: Using persistent Python environment[/dim]")
            console.print(f"[dim]Make sure napari-mcp is installed: pip install napari-mcp[/dim]")

        if not self.global_install:
            console.print(f"\n[dim]Note: Installation is project-specific[/dim]")
            console.print(f"[dim]The server will only be available in this project[/dim]")

        console.print(f"\n[dim]Tip: Set 'trust': true to bypass tool confirmations (use with caution)[/dim]")
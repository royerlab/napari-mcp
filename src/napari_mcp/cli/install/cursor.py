"""Cursor installer for napari-mcp."""

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Confirm

from .base import BaseInstaller
from .utils import expand_path

console = Console()


class CursorInstaller(BaseInstaller):
    """Installer for Cursor IDE."""

    def __init__(
        self,
        server_name: str = "napari-mcp",
        persistent: bool = False,
        python_path: str | None = None,
        force: bool = False,
        backup: bool = True,
        dry_run: bool = False,
        global_install: bool = False,
        project_dir: str | None = None,
    ):
        """Initialize the Cursor installer.

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
            "cursor",
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
        """Get the Cursor configuration file path.

        Returns
        -------
        Path
            Path to mcp.json for Cursor.
        """
        if self.global_install:
            # Global configuration
            return expand_path("~/.cursor/mcp.json")
        else:
            # Project-specific configuration
            if self.project_dir:
                base_path = expand_path(self.project_dir)
            else:
                # Use current working directory
                base_path = Path.cwd()

            config_path = base_path / ".cursor" / "mcp.json"

            # Confirm project directory with user
            if not self.force and not self.dry_run:
                console.print(f"\n[cyan]Project directory: {base_path}[/cyan]")
                if not Confirm.ask(
                    "Install napari-mcp for this project?", default=True
                ):
                    raise ValueError("User cancelled installation")

            return config_path

    def get_extra_config(self) -> dict[str, Any]:
        """Get extra configuration for Cursor.

        Returns
        -------
        dict[str, Any]
            Empty dict as Cursor doesn't need extra fields.
        """
        return {}

    def show_post_install_message(self) -> None:
        """Show post-installation instructions."""
        super().show_post_install_message()

        if not self.global_install:
            console.print("\n[dim]Note: Installation is project-specific[/dim]")
            console.print(
                "[dim]The server will only be available in this project[/dim]"
            )

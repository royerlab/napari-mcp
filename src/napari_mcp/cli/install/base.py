"""Base installer class for MCP server configuration."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console

from .utils import (
    build_server_config,
    check_existing_server,
    expand_path,
    get_app_display_name,
    get_python_executable,
    prompt_update_existing,
    read_json_config,
    validate_python_environment,
    write_json_config,
)

console = Console()


class BaseInstaller(ABC):
    """Base class for MCP server installers."""

    def __init__(
        self,
        app_key: str,
        server_name: str = "napari-mcp",
        persistent: bool = False,
        python_path: Optional[str] = None,
        force: bool = False,
        backup: bool = True,
        dry_run: bool = False,
    ):
        """Initialize the installer.

        Parameters
        ----------
        app_key : str
            Application identifier (e.g., 'claude-desktop').
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
        """
        self.app_key = app_key
        self.app_name = get_app_display_name(app_key)
        self.server_name = server_name
        self.persistent = persistent
        self.python_path = python_path
        self.force = force
        self.backup = backup
        self.dry_run = dry_run

    @abstractmethod
    def get_config_path(self) -> Path:
        """Get the configuration file path for this application.

        Returns
        -------
        Path
            Path to the configuration file.
        """
        pass

    @abstractmethod
    def get_extra_config(self) -> Dict[str, Any]:
        """Get any extra configuration fields specific to this application.

        Returns
        -------
        Dict[str, Any]
            Extra configuration fields (e.g., timeout for Gemini).
        """
        return {}

    def validate_environment(self) -> bool:
        """Validate the installation environment.

        Returns
        -------
        bool
            True if environment is valid, False otherwise.
        """
        if self.persistent or self.python_path:
            # Validate Python environment has napari-mcp
            command, desc = get_python_executable(self.persistent, self.python_path)
            if command != "uv":
                console.print(f"[cyan]Using {desc}[/cyan]")
                if not validate_python_environment(command):
                    if not self.force:
                        console.print("[red]Aborting installation.[/red]")
                        return False
                    console.print("[yellow]Continuing anyway (--force specified)[/yellow]")
        return True

    def install(self) -> Tuple[bool, str]:
        """Install the MCP server configuration.

        Returns
        -------
        Tuple[bool, str]
            Success status and message.
        """
        try:
            # Get configuration path
            config_path = self.get_config_path()
            console.print(f"\n[bold cyan]Installing napari-mcp for {self.app_name}[/bold cyan]")
            console.print(f"[dim]Config file: {config_path}[/dim]")

            # Validate environment
            if not self.validate_environment():
                return False, "Environment validation failed"

            # Read existing configuration
            config = read_json_config(config_path)

            # Initialize mcpServers if not present
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Check for existing installation
            if check_existing_server(config, self.server_name):
                if not self.force and not prompt_update_existing(self.app_name, config_path):
                    return False, "User cancelled update"

            # Build server configuration
            server_config = build_server_config(
                self.persistent,
                self.python_path,
                self.get_extra_config()
            )

            # Show what will be installed
            command, desc = get_python_executable(self.persistent, self.python_path)
            console.print(f"\n[cyan]Configuration to install:[/cyan]")
            console.print(f"  Command: {desc}")
            console.print(f"  Server name: {self.server_name}")

            if self.dry_run:
                console.print("\n[yellow]DRY RUN - No changes will be made[/yellow]")
                console.print(f"Would update: {config_path}")
                return True, "Dry run completed"

            # Update configuration
            config["mcpServers"][self.server_name] = server_config

            # Write configuration
            if write_json_config(config_path, config, backup=self.backup):
                console.print(f"\n[green]✓ Successfully installed napari-mcp for {self.app_name}[/green]")
                self.show_post_install_message()
                return True, "Installation successful"
            else:
                return False, "Failed to write configuration"

        except Exception as e:
            console.print(f"[red]Installation failed: {e}[/red]")
            return False, str(e)

    def uninstall(self) -> Tuple[bool, str]:
        """Uninstall the MCP server configuration.

        Returns
        -------
        Tuple[bool, str]
            Success status and message.
        """
        try:
            # Get configuration path
            config_path = self.get_config_path()

            if not config_path.exists():
                return False, f"Configuration file not found: {config_path}"

            # Read configuration
            config = read_json_config(config_path)

            # Check if server exists
            if not check_existing_server(config, self.server_name):
                return False, f"Server '{self.server_name}' not found in configuration"

            if self.dry_run:
                console.print(f"\n[yellow]DRY RUN - Would remove '{self.server_name}' from {config_path}[/yellow]")
                return True, "Dry run completed"

            # Remove server
            del config["mcpServers"][self.server_name]

            # Clean up empty mcpServers
            if not config["mcpServers"]:
                del config["mcpServers"]

            # Write configuration
            if write_json_config(config_path, config, backup=self.backup):
                console.print(f"\n[green]✓ Successfully uninstalled napari-mcp from {self.app_name}[/green]")
                return True, "Uninstallation successful"
            else:
                return False, "Failed to write configuration"

        except Exception as e:
            console.print(f"[red]Uninstallation failed: {e}[/red]")
            return False, str(e)

    def show_post_install_message(self) -> None:
        """Show post-installation instructions."""
        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"1. Restart {self.app_name}")
        console.print(f"2. The napari-mcp server will be available automatically")
        if self.persistent:
            console.print(f"\n[dim]Note: Using persistent Python environment[/dim]")
            console.print(f"[dim]Make sure napari-mcp is installed: pip install napari-mcp[/dim]")
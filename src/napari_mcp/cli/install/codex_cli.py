"""Codex CLI installer for napari-mcp."""

import sys
from pathlib import Path
from typing import Any

from rich.console import Console

from .base import BaseInstaller
from .utils import build_server_config, expand_path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

console = Console()


class CodexCLIInstaller(BaseInstaller):
    """Installer for Codex CLI (OpenAI's terminal-based coding agent)."""

    def __init__(self, **kwargs):
        """Initialize Codex CLI installer."""
        super().__init__(app_key="codex", **kwargs)

    def get_config_path(self) -> Path:
        """Get the Codex CLI configuration file path.

        Returns
        -------
        Path
            Path to config.toml for Codex CLI.
        """
        # Codex CLI uses ~/.codex/config.toml for configuration
        return expand_path("~/.codex/config.toml")

    def get_extra_config(self) -> dict[str, Any]:
        """Get extra configuration for Codex CLI.

        Returns
        -------
        dict[str, Any]
            Empty dict as extras are handled in TOML format.
        """
        return {}

    def install(self):
        """Install the MCP server configuration for Codex CLI.

        Override to handle TOML format instead of JSON.
        """
        import toml as toml_writer

        try:
            # Get configuration path
            config_path = self.get_config_path()
            console.print(
                "\n[bold cyan]Installing napari-mcp for Codex CLI[/bold cyan]"
            )
            console.print(f"[dim]Config file: {config_path}[/dim]")

            # Validate environment
            if not self.validate_environment():
                return False, "Environment validation failed"

            # Read existing configuration or create new
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
            else:
                config = {}

            # Initialize mcp_servers if not present
            if "mcp_servers" not in config:
                config["mcp_servers"] = {}

            # Check for existing installation
            server_name = "napari_mcp"  # Use underscore for TOML convention
            if server_name in config.get("mcp_servers", {}) and not self.force:
                from .utils import prompt_update_existing

                if not prompt_update_existing("Codex CLI", config_path):
                    return False, "User cancelled update"

            # Build server configuration for TOML format
            build_kwargs: dict[str, Any] = {}
            if self.napari_backend is not None:
                build_kwargs["napari_requirement"] = self.napari_backend

            server_config = build_server_config(
                self.persistent,
                self.python_path,
                self.get_extra_config(),
                **build_kwargs,
            )

            # Show what will be installed
            console.print("\n[cyan]Configuration to install:[/cyan]")
            console.print(f"  Server name: {server_name}")
            console.print(f"  Command: {server_config['command']}")

            if self.dry_run:
                console.print("\n[yellow]DRY RUN - No changes will be made[/yellow]")
                console.print(f"Would update: {config_path}")
                return True, "Dry run completed"

            # Update configuration
            config["mcp_servers"][server_name] = server_config

            # Create parent directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write TOML configuration
            with open(config_path, "w") as f:
                toml_writer.dump(config, f)

            console.print(
                "\n[green]\u2713 Successfully installed napari-mcp for Codex CLI[/green]"
            )
            self.show_post_install_message()
            return True, "Installation successful"

        except Exception as e:
            console.print(f"[red]Installation failed: {e}[/red]")
            return False, str(e)

    def uninstall(self):
        """Uninstall the MCP server configuration for Codex CLI.

        Override to handle TOML format instead of JSON.
        """
        import toml as toml_writer

        try:
            # Get configuration path
            config_path = self.get_config_path()

            if not config_path.exists():
                return False, f"Configuration file not found: {config_path}"

            # Read configuration
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Check if server exists
            server_name = "napari_mcp"
            if "mcp_servers" not in config or server_name not in config["mcp_servers"]:
                return False, f"Server '{server_name}' not found in configuration"

            if self.dry_run:
                console.print(
                    f"\n[yellow]DRY RUN - Would remove '{server_name}' from {config_path}[/yellow]"
                )
                return True, "Dry run completed"

            # Remove server
            del config["mcp_servers"][server_name]

            # Clean up empty mcp_servers
            if not config["mcp_servers"]:
                del config["mcp_servers"]

            # Write TOML configuration
            with open(config_path, "w") as f:
                toml_writer.dump(config, f)

            console.print(
                "\n[green]\u2713 Successfully uninstalled napari-mcp from Codex CLI[/green]"
            )
            return True, "Uninstallation successful"

        except Exception as e:
            console.print(f"[red]Uninstallation failed: {e}[/red]")
            return False, str(e)

    def show_post_install_message(self) -> None:
        """Show post-installation instructions."""
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Start Codex CLI in your terminal: codex")
        console.print("2. The napari-mcp server will be available automatically")
        console.print("3. Use napari tools for image visualization and analysis")

        if self.persistent:
            console.print("\n[dim]Note: Using persistent Python environment[/dim]")
            console.print(
                "[dim]Make sure napari-mcp is installed: pip install napari-mcp[/dim]"
            )

        console.print("\n[dim]Tip: Codex CLI uses TOML format for configuration[/dim]")

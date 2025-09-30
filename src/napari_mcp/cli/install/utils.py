"""Shared utilities for MCP server installers."""

import json
import os
import platform
import shutil
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

console = Console()


def get_platform() -> str:
    """Get the current platform.

    Returns
    -------
    str
        One of 'macos', 'windows', or 'linux'.
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    else:
        return "linux"


def expand_path(path: str) -> Path:
    """Expand user home directory and environment variables in path.

    Parameters
    ----------
    path : str
        Path string that may contain ~ or environment variables.

    Returns
    -------
    Path
        Resolved absolute path.
    """
    # Expand ~ to user home directory
    path = os.path.expanduser(path)
    # Expand environment variables like %APPDATA%
    path = os.path.expandvars(path)
    return Path(path).resolve()


def read_json_config(path: Path) -> Dict[str, Any]:
    """Read JSON configuration file, preserving order.

    Parameters
    ----------
    path : Path
        Path to JSON configuration file.

    Returns
    -------
    Dict[str, Any]
        Configuration dictionary, or empty dict if file doesn't exist.
    """
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f, object_pairs_hook=OrderedDict)
    except (json.JSONDecodeError, IOError) as e:
        console.print(f"[red]Error reading {path}: {e}[/red]")
        return {}


def write_json_config(path: Path, config: Dict[str, Any], backup: bool = True) -> bool:
    """Write JSON configuration file atomically.

    Parameters
    ----------
    path : Path
        Path to JSON configuration file.
    config : Dict[str, Any]
        Configuration dictionary to write.
    backup : bool
        Whether to create a backup of existing file.

    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    # Create parent directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Backup existing file if requested
    if backup and path.exists():
        backup_path = path.with_suffix(f".backup_{os.getpid()}")
        shutil.copy2(path, backup_path)
        console.print(f"[dim]Backup created: {backup_path}[/dim]")

    # Write to temporary file first (atomic write)
    temp_path = path.with_suffix(f".tmp_{os.getpid()}")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add trailing newline

        # Atomic rename
        temp_path.replace(path)
        return True
    except (IOError, OSError) as e:
        console.print(f"[red]Error writing {path}: {e}[/red]")
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        return False


def get_python_executable(persistent: bool = False, python_path: Optional[str] = None) -> Tuple[str, str]:
    """Get the appropriate Python executable and description.

    Parameters
    ----------
    persistent : bool
        If True, use current Python executable instead of uv.
    python_path : Optional[str]
        Custom Python executable path.

    Returns
    -------
    Tuple[str, str]
        Command to use and description for user.
    """
    if python_path:
        # User specified a custom Python path
        python_path_obj = expand_path(python_path)
        if not python_path_obj.exists():
            console.print(f"[red]Warning: Python path does not exist: {python_path}[/red]")
        return str(python_path_obj), f"custom Python ({python_path_obj})"

    if persistent:
        # Use current Python executable
        return sys.executable, f"persistent Python ({sys.executable})"

    # Default to uv for ephemeral environments
    return "uv", "uv (ephemeral environment)"


def build_server_config(
    persistent: bool = False,
    python_path: Optional[str] = None,
    extra_args: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build the server configuration for napari-mcp.

    Parameters
    ----------
    persistent : bool
        If True, use Python executable instead of uv.
    python_path : Optional[str]
        Custom Python executable path.
    extra_args : Optional[Dict[str, Any]]
        Additional configuration fields (e.g., for Gemini CLI).

    Returns
    -------
    Dict[str, Any]
        Server configuration dictionary.
    """
    command, _ = get_python_executable(persistent, python_path)

    if command == "uv":
        # Ephemeral environment with uv
        config = {
            "command": "uv",
            "args": ["run", "--with", "napari-mcp", "napari-mcp"]
        }
    else:
        # Persistent Python environment
        config = {
            "command": command,
            "args": ["-m", "napari_mcp.server"]
        }

    # Add any extra configuration fields
    if extra_args:
        config.update(extra_args)

    return config


def check_existing_server(config: Dict[str, Any], server_name: str = "napari-mcp") -> bool:
    """Check if napari-mcp server already exists in configuration.

    Parameters
    ----------
    config : Dict[str, Any]
        Configuration dictionary.
    server_name : str
        Name of the server to check for.

    Returns
    -------
    bool
        True if server exists, False otherwise.
    """
    if "mcpServers" not in config:
        return False

    return server_name in config.get("mcpServers", {})


def prompt_update_existing(app_name: str, config_path: Path) -> bool:
    """Prompt user about updating existing installation.

    Parameters
    ----------
    app_name : str
        Name of the application (e.g., "Claude Desktop").
    config_path : Path
        Path to the configuration file.

    Returns
    -------
    bool
        True if user wants to update, False to abort.
    """
    console.print(f"\n[yellow]napari-mcp is already configured for {app_name}[/yellow]")
    console.print(f"[dim]Config file: {config_path}[/dim]\n")

    return Confirm.ask(
        "Do you want to update the existing configuration?",
        default=False
    )


def show_installation_summary(installations: Dict[str, Tuple[bool, str]]) -> None:
    """Show a summary table of installation results.

    Parameters
    ----------
    installations : Dict[str, Tuple[bool, str]]
        Dictionary mapping app names to (success, message) tuples.
    """
    table = Table(title="Installation Summary", show_header=True)
    table.add_column("Application", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    for app_name, (success, message) in installations.items():
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        style = "green" if success else "red"
        table.add_row(app_name, status, f"[{style}]{message}[/{style}]")

    console.print("\n")
    console.print(table)


def validate_python_environment(python_path: str) -> bool:
    """Validate that a Python environment has napari-mcp installed.

    Parameters
    ----------
    python_path : str
        Path to Python executable.

    Returns
    -------
    bool
        True if napari-mcp is accessible, False otherwise.
    """
    import subprocess

    try:
        # Check if napari-mcp module can be imported
        result = subprocess.run(
            [python_path, "-c", "import napari_mcp"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            console.print(f"[yellow]Warning: napari-mcp not found in {python_path}[/yellow]")
            console.print("[dim]You may need to install it: pip install napari-mcp[/dim]")
            return False

        return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        console.print(f"[red]Error validating Python environment: {e}[/red]")
        return False


def detect_python_environment() -> Optional[str]:
    """Detect the current Python environment type.

    Returns
    -------
    Optional[str]
        Environment type ('conda', 'venv', 'system'), or None if detection fails.
    """
    # Check for Conda environment
    if os.environ.get("CONDA_DEFAULT_ENV"):
        return "conda"

    # Check for virtual environment
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        return "venv"

    # Otherwise it's likely system Python
    return "system"


def get_app_display_name(app_key: str) -> str:
    """Get the display name for an application.

    Parameters
    ----------
    app_key : str
        Application key (e.g., 'claude-desktop').

    Returns
    -------
    str
        Display name for the application.
    """
    display_names = {
        "claude-desktop": "Claude Desktop",
        "claude-code": "Claude Code",
        "cursor": "Cursor",
        "cline-vscode": "Cline (VS Code)",
        "cline-cursor": "Cline (Cursor IDE)",
        "gemini": "Gemini CLI",
        "codex": "Codex CLI",
        "codex-cli": "Codex CLI",
    }
    return display_names.get(app_key, app_key)
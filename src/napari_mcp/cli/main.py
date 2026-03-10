"""Main CLI entry point for napari-mcp installer."""

import sys as _sys
from enum import Enum
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .install import (  # noqa: F401 - accessed via _get_installer_class
    ClaudeCodeInstaller,
    ClaudeDesktopInstaller,
    ClineCursorInstaller,
    ClineVSCodeInstaller,
    CodexCLIInstaller,
    CursorInstaller,
    GeminiCLIInstaller,
)
from .install.utils import get_app_display_name, show_installation_summary

app = typer.Typer(
    name="napari-mcp-install",
    help="Install napari-mcp for various LLM applications",
    add_completion=False,
)
console = Console()


class InstallTarget(str, Enum):
    """Supported installation targets."""

    CLAUDE_DESKTOP = "claude-desktop"
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    CLINE_VSCODE = "cline-vscode"
    CLINE_CURSOR = "cline-cursor"
    GEMINI = "gemini"
    CODEX = "codex"
    ALL = "all"


# Maps target names to class attribute names in this module (looked up at
# call time so that unittest.mock.patch works correctly).
_INSTALLER_CLASS_NAMES = {
    InstallTarget.CLAUDE_DESKTOP: "ClaudeDesktopInstaller",
    InstallTarget.CLAUDE_CODE: "ClaudeCodeInstaller",
    InstallTarget.CURSOR: "CursorInstaller",
    InstallTarget.CLINE_VSCODE: "ClineVSCodeInstaller",
    InstallTarget.CLINE_CURSOR: "ClineCursorInstaller",
    InstallTarget.GEMINI: "GeminiCLIInstaller",
    InstallTarget.CODEX: "CodexCLIInstaller",
}


def _get_installer_class(target: InstallTarget):
    """Look up installer class by name (supports mock patching)."""
    return getattr(_sys.modules[__name__], _INSTALLER_CLASS_NAMES[target])


# Targets that support --global / --project options
PROJECT_TARGETS = {InstallTarget.CURSOR, InstallTarget.GEMINI}


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        from napari_mcp import __version__

        console.print(f"napari-mcp version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
):
    """napari-mcp installer - Easy setup for LLM applications."""


def _create_installer(
    target: InstallTarget,
    *,
    persistent: bool = False,
    python_path: str | None = None,
    force: bool = False,
    backup: bool = True,
    dry_run: bool = False,
    global_install: bool = False,
    project_dir: str | None = None,
):
    """Create an installer instance for the given target."""
    installer_class = _get_installer_class(target)
    kwargs = {
        "persistent": persistent,
        "python_path": python_path,
        "force": force,
        "backup": backup,
        "dry_run": dry_run,
    }
    if target in PROJECT_TARGETS:
        kwargs["global_install"] = global_install
        if project_dir is not None:
            kwargs["project_dir"] = project_dir
    elif global_install or project_dir:
        console.print(
            f"[yellow]Warning: --global/--project ignored for {target.value}[/yellow]"
        )
    return installer_class(**kwargs)


@app.command("install")
def install(
    target: Annotated[
        InstallTarget,
        typer.Argument(help="Target application to install for"),
    ],
    persistent: Annotated[
        bool,
        typer.Option("--persistent", help="Use Python path instead of uv run"),
    ] = False,
    python_path: Annotated[
        str | None,
        typer.Option("--python-path", help="Custom Python executable path"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip prompts and force update"),
    ] = False,
    backup: Annotated[
        bool,
        typer.Option("--backup/--no-backup", help="Create backup before updating"),
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying"),
    ] = False,
    global_install: Annotated[
        bool,
        typer.Option("--global", help="Install globally (cursor/gemini only)"),
    ] = False,
    project_dir: Annotated[
        str | None,
        typer.Option("--project", help="Project directory (cursor/gemini only)"),
    ] = None,
):
    """Install napari-mcp for a target application."""
    if target == InstallTarget.ALL:
        console.print(
            "[bold cyan]Installing napari-mcp for all supported applications...[/bold cyan]\n"
        )
        results = {}
        for app_target in _INSTALLER_CLASS_NAMES:
            try:
                display_name = get_app_display_name(app_target.value)
                console.print(f"[cyan]Installing for {display_name}...[/cyan]")
                inst = _create_installer(
                    app_target,
                    persistent=persistent,
                    python_path=python_path,
                    force=force,
                    backup=backup,
                    dry_run=dry_run,
                    global_install=app_target in PROJECT_TARGETS,
                )
                success, message = inst.install()
                results[display_name] = (success, message)
            except Exception as e:
                results[get_app_display_name(app_target.value)] = (False, str(e))

        show_installation_summary(results)
        if not all(success for success, _ in results.values()):
            raise typer.Exit(1)
        return

    inst = _create_installer(
        target,
        persistent=persistent,
        python_path=python_path,
        force=force,
        backup=backup,
        dry_run=dry_run,
        global_install=global_install,
        project_dir=project_dir,
    )
    success, message = inst.install()
    if not success:
        raise typer.Exit(1)


@app.command("uninstall")
def uninstall(
    target: Annotated[
        InstallTarget,
        typer.Argument(help="Target application to uninstall from"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip prompts"),
    ] = False,
    backup: Annotated[
        bool,
        typer.Option("--backup/--no-backup", help="Create backup before removing"),
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying"),
    ] = False,
):
    """Uninstall napari-mcp from an application."""
    if target == InstallTarget.ALL:
        console.print(
            "[bold cyan]Uninstalling napari-mcp from all applications...[/bold cyan]\n"
        )
        results = {}
        for app_target in _INSTALLER_CLASS_NAMES:
            try:
                display_name = get_app_display_name(app_target.value)
                console.print(f"[cyan]Uninstalling from {display_name}...[/cyan]")
                inst = _create_installer(
                    app_target,
                    force=force,
                    backup=backup,
                    dry_run=dry_run,
                    global_install=app_target in PROJECT_TARGETS,
                )
                success, message = inst.uninstall()
                results[display_name] = (success, message)
            except Exception as e:
                results[get_app_display_name(app_target.value)] = (False, str(e))

        show_installation_summary(results)
        if not all(success for success, _ in results.values()):
            raise typer.Exit(1)
        return

    inst = _create_installer(
        target,
        force=force,
        backup=backup,
        dry_run=dry_run,
        global_install=target in PROJECT_TARGETS,
    )
    success, message = inst.uninstall()
    if not success:
        console.print(f"[red]Failed: {message}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_installations():
    """List installed napari-mcp configurations."""
    console.print("[bold cyan]Checking napari-mcp installations...[/bold cyan]\n")

    table = Table(title="napari-mcp Installation Status", show_header=True)
    table.add_column("Application", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Config Path")
    table.add_column("Details")

    for app_target in _INSTALLER_CLASS_NAMES:
        app_key = app_target.value
        try:
            kwargs = {"force": True}
            if app_target in PROJECT_TARGETS:
                kwargs["global_install"] = True
            installer = _get_installer_class(app_target)(**kwargs)

            config_path = installer.get_config_path()
            display_name = get_app_display_name(app_key)

            if config_path.exists():
                if app_key == "codex":
                    try:
                        import sys

                        if sys.version_info >= (3, 11):
                            import tomllib
                        else:
                            import tomli as tomllib  # type: ignore[no-redef]

                        with open(config_path, "rb") as f:
                            config = tomllib.load(f)
                        if (
                            "mcp_servers" in config
                            and "napari_mcp" in config["mcp_servers"]
                        ):
                            status = "[green]\u2713[/green]"
                            details = "Installed"
                        else:
                            status = "[yellow]\u25cb[/yellow]"
                            details = "Config exists, server not configured"
                    except Exception as e:
                        status = "[red]\u2717[/red]"
                        details = f"Error: {e}"
                else:
                    from .install.utils import check_existing_server, read_json_config

                    config = read_json_config(config_path)
                    if check_existing_server(config, "napari-mcp"):
                        status = "[green]\u2713[/green]"
                        details = "Installed"
                    else:
                        status = "[yellow]\u25cb[/yellow]"
                        details = "Config exists, server not configured"
            else:
                status = "[dim]\u2212[/dim]"
                details = "Not configured"

            table.add_row(display_name, status, str(config_path), details)

        except Exception as e:
            table.add_row(
                get_app_display_name(app_key),
                "[red]\u2717[/red]",
                "Error",
                f"[red]{str(e)}[/red]",
            )

    console.print(table)
    console.print(
        "\n[dim]Legend: \u2713 Installed | \u25cb Partial | \u2212 Not configured | \u2717 Error[/dim]"
    )


if __name__ == "__main__":
    app()

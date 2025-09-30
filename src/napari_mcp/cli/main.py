"""Main CLI entry point for napari-mcp installer."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .install import (
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


@app.command("claude-desktop")
def install_claude_desktop(
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
):
    """Install napari-mcp for Claude Desktop."""
    installer = ClaudeDesktopInstaller(
        persistent=persistent,
        python_path=python_path,
        force=force,
        backup=backup,
        dry_run=dry_run,
    )
    success, message = installer.install()
    if not success:
        raise typer.Exit(1)


@app.command("claude-code")
def install_claude_code(
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
):
    """Install napari-mcp for Claude Code CLI."""
    installer = ClaudeCodeInstaller(
        persistent=persistent,
        python_path=python_path,
        force=force,
        backup=backup,
        dry_run=dry_run,
    )
    success, message = installer.install()
    if not success:
        raise typer.Exit(1)


@app.command("cursor")
def install_cursor(
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
        typer.Option("--global", help="Install globally instead of project-specific"),
    ] = False,
    project_dir: Annotated[
        str | None,
        typer.Option("--project", help="Project directory for installation"),
    ] = None,
):
    """Install napari-mcp for Cursor IDE."""
    installer = CursorInstaller(
        persistent=persistent,
        python_path=python_path,
        force=force,
        backup=backup,
        dry_run=dry_run,
        global_install=global_install,
        project_dir=project_dir,
    )
    success, message = installer.install()
    if not success:
        raise typer.Exit(1)


@app.command("cline-vscode")
def install_cline_vscode(
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
):
    """Install napari-mcp for Cline extension in VS Code."""
    installer = ClineVSCodeInstaller(
        persistent=persistent,
        python_path=python_path,
        force=force,
        backup=backup,
        dry_run=dry_run,
    )
    success, message = installer.install()
    if not success:
        raise typer.Exit(1)


@app.command("cline-cursor")
def install_cline_cursor(
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
):
    """Install napari-mcp for Cline extension in Cursor IDE."""
    installer = ClineCursorInstaller(
        persistent=persistent,
        python_path=python_path,
        force=force,
        backup=backup,
        dry_run=dry_run,
    )
    success, message = installer.install()
    if not success:
        raise typer.Exit(1)


@app.command("codex")
def install_codex(
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
):
    """Install napari-mcp for Codex CLI."""
    installer = CodexCLIInstaller(
        persistent=persistent,
        python_path=python_path,
        force=force,
        backup=backup,
        dry_run=dry_run,
    )
    success, message = installer.install()
    if not success:
        raise typer.Exit(1)


@app.command("gemini")
def install_gemini(
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
        typer.Option("--global", help="Install globally instead of project-specific"),
    ] = False,
    project_dir: Annotated[
        str | None,
        typer.Option("--project", help="Project directory for installation"),
    ] = None,
):
    """Install napari-mcp for Gemini CLI."""
    installer = GeminiCLIInstaller(
        persistent=persistent,
        python_path=python_path,
        force=force,
        backup=backup,
        dry_run=dry_run,
        global_install=global_install,
        project_dir=project_dir,
    )
    success, message = installer.install()
    if not success:
        raise typer.Exit(1)


@app.command("all")
def install_all(
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
):
    """Install napari-mcp for all supported applications."""
    console.print(
        "[bold cyan]Installing napari-mcp for all supported applications...[/bold cyan]\n"
    )

    results = {}

    # Install for each application
    installers = [
        ("claude-desktop", ClaudeDesktopInstaller),
        ("claude-code", ClaudeCodeInstaller),
        ("cursor", CursorInstaller),
        ("cline-vscode", ClineVSCodeInstaller),
        ("cline-cursor", ClineCursorInstaller),
        ("gemini", GeminiCLIInstaller),
        ("codex", CodexCLIInstaller),
    ]

    for app_key, installer_class in installers:
        try:
            console.print(
                f"[cyan]Installing for {get_app_display_name(app_key)}...[/cyan]"
            )

            # Special handling for project-specific installers
            if app_key in ["cursor", "gemini"]:
                installer = installer_class(
                    persistent=persistent,
                    python_path=python_path,
                    force=force,
                    backup=backup,
                    dry_run=dry_run,
                    global_install=True,  # Use global for 'all' command
                )
            else:
                installer = installer_class(
                    persistent=persistent,
                    python_path=python_path,
                    force=force,
                    backup=backup,
                    dry_run=dry_run,
                )

            success, message = installer.install()
            results[get_app_display_name(app_key)] = (success, message)

        except Exception as e:
            results[get_app_display_name(app_key)] = (False, str(e))

    # Show summary
    show_installation_summary(results)

    # Exit with error if any failed
    if not all(success for success, _ in results.values()):
        raise typer.Exit(1)


@app.command("uninstall")
def uninstall(
    app_name: Annotated[
        str,
        typer.Argument(
            help="Application to uninstall from (claude-desktop, claude-code, cursor, cline, gemini, all)"
        ),
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
    app_map = {
        "claude-desktop": ClaudeDesktopInstaller,
        "claude-code": ClaudeCodeInstaller,
        "cursor": CursorInstaller,
        "cline-vscode": ClineVSCodeInstaller,
        "cline-cursor": ClineCursorInstaller,
        "gemini": GeminiCLIInstaller,
        "codex": CodexCLIInstaller,
    }

    if app_name == "all":
        console.print(
            "[bold cyan]Uninstalling napari-mcp from all applications...[/bold cyan]\n"
        )
        results = {}

        for app_key, installer_class in app_map.items():
            try:
                console.print(
                    f"[cyan]Uninstalling from {get_app_display_name(app_key)}...[/cyan]"
                )

                # Special handling for project-specific installers
                if app_key in ["cursor", "gemini"]:
                    installer = installer_class(
                        force=force,
                        backup=backup,
                        dry_run=dry_run,
                        global_install=True,
                    )
                else:
                    installer = installer_class(
                        force=force,
                        backup=backup,
                        dry_run=dry_run,
                    )

                success, message = installer.uninstall()
                results[get_app_display_name(app_key)] = (success, message)

            except Exception as e:
                results[get_app_display_name(app_key)] = (False, str(e))

        show_installation_summary(results)

    elif app_name in app_map:
        installer_class = app_map[app_name]

        # Special handling for project-specific installers
        if app_name in ["cursor", "gemini"]:
            installer = installer_class(
                force=force,
                backup=backup,
                dry_run=dry_run,
                global_install=True,
            )
        else:
            installer = installer_class(
                force=force,
                backup=backup,
                dry_run=dry_run,
            )

        success, message = installer.uninstall()
        if not success:
            console.print(f"[red]Failed: {message}[/red]")
            raise typer.Exit(1)
    else:
        console.print(f"[red]Unknown application: {app_name}[/red]")
        console.print(
            "Available: claude-desktop, claude-code, cursor, cline-vscode, cline-cursor, gemini, codex, all"
        )
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

    # Check each application
    apps = [
        ("claude-desktop", ClaudeDesktopInstaller),
        ("claude-code", ClaudeCodeInstaller),
        ("cursor", CursorInstaller),
        ("cline-vscode", ClineVSCodeInstaller),
        ("cline-cursor", ClineCursorInstaller),
        ("gemini", GeminiCLIInstaller),
        ("codex", CodexCLIInstaller),
    ]

    for app_key, installer_class in apps:
        try:
            # Create installer to get config path (force=True to skip prompts)
            if app_key in ["cursor", "gemini"]:
                installer = installer_class(
                    force=True,  # Skip prompts in list command
                    global_install=True,
                )
            else:
                installer = installer_class(force=True)  # Skip prompts in list command

            config_path = installer.get_config_path()
            display_name = get_app_display_name(app_key)

            if config_path.exists():
                # Special handling for Codex CLI which uses TOML
                if app_key == "codex":
                    try:
                        import toml

                        with open(config_path) as f:
                            config = toml.load(f)
                        # Check for napari_mcp in mcp_servers
                        if (
                            "mcp_servers" in config
                            and "napari_mcp" in config["mcp_servers"]
                        ):
                            status = "[green]✓[/green]"
                            details = "Installed"
                        else:
                            status = "[yellow]○[/yellow]"
                            details = "Config exists, server not configured"
                    except Exception as e:
                        status = "[red]✗[/red]"
                        details = f"Error: {str(e)[:30]}"
                else:
                    from .install.utils import check_existing_server, read_json_config

                    config = read_json_config(config_path)
                    if check_existing_server(config, "napari-mcp"):
                        status = "[green]✓[/green]"
                        details = "Installed"
                    else:
                        status = "[yellow]○[/yellow]"
                        details = "Config exists, server not configured"
            else:
                status = "[dim]−[/dim]"
                details = "Not configured"

            table.add_row(display_name, status, str(config_path), details)

        except Exception as e:
            table.add_row(
                get_app_display_name(app_key),
                "[red]✗[/red]",
                "Error",
                f"[red]{str(e)}[/red]",
            )

    console.print(table)
    console.print(
        "\n[dim]Legend: ✓ Installed | ○ Partial | − Not configured | ✗ Error[/dim]"
    )


if __name__ == "__main__":
    app()

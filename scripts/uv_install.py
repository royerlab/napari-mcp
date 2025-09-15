#!/usr/bin/env python3
"""
Napari MCP Server UV-based Automatic Installer

A Python-based installer that uses uv for dependency management and
can be executed as a standalone uv command.

Usage:
    uv run scripts/uv_install.py [options] <target>
    uv run --with requests --with rich scripts/uv_install.py <target>
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

# Configuration
SERVER_URL = "https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py"
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

class InstallerError(Exception):
    """Custom exception for installer errors."""
    pass

class NapariMCPInstaller:
    """Main installer class."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.console = console if HAS_RICH else None
        
    def print_info(self, message: str) -> None:
        """Print info message."""
        if self.console:
            self.console.print(f"ℹ️  {message}", style="blue")
        else:
            print(f"ℹ️  {message}")
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        if self.console:
            self.console.print(f"✅ {message}", style="green")
        else:
            print(f"✅ {message}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message."""
        if self.console:
            self.console.print(f"⚠️  {message}", style="yellow")
        else:
            print(f"⚠️  {message}")
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        if self.console:
            self.console.print(f"❌ {message}", style="red")
        else:
            print(f"❌ {message}")
    
    def print_header(self) -> None:
        """Print installer header."""
        if self.console:
            panel = Panel(
                "Napari MCP Server Auto Installer",
                style="blue",
                width=64
            )
            self.console.print(panel)
        else:
            print("=" * 64)
            print(" " * 15 + "Napari MCP Server Auto Installer")
            print("=" * 64)
    
    def command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        return shutil.which(command) is not None
    
    def detect_os(self) -> str:
        """Detect the operating system."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        elif system in ["windows", "cygwin"]:
            return "windows"
        else:
            return "unknown"
    
    def get_claude_config_path(self) -> Path:
        """Get Claude Desktop config file path."""
        os_type = self.detect_os()
        
        if os_type == "macos":
            return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
        elif os_type == "linux":
            return Path.home() / ".config/Claude/claude_desktop_config.json"
        elif os_type == "windows":
            appdata = os.environ.get("APPDATA", "")
            if not appdata:
                raise InstallerError("APPDATA environment variable not found")
            return Path(appdata) / "Claude/claude_desktop_config.json"
        else:
            raise InstallerError(f"Unsupported OS for Claude Desktop: {os_type}")
    
    def download_server(self, target_path: Path) -> None:
        """Download server file from GitHub."""
        self.print_info("Downloading napari MCP server...")
        
        if HAS_REQUESTS:
            try:
                response = requests.get(SERVER_URL, timeout=30)
                response.raise_for_status()
                target_path.write_text(response.text, encoding='utf-8')
            except requests.RequestException as e:
                raise InstallerError(f"Failed to download server: {e}")
        else:
            # Fallback to curl/wget
            if self.command_exists("curl"):
                cmd = ["curl", "-fsSL", SERVER_URL, "-o", str(target_path)]
            elif self.command_exists("wget"):
                cmd = ["wget", "-q", SERVER_URL, "-O", str(target_path)]
            else:
                raise InstallerError(
                    "Neither requests module nor curl/wget found. "
                    "Install with: uv run --with requests scripts/uv_install.py"
                )
            
            try:
                subprocess.run(cmd, check=True, capture_output=not self.verbose)
            except subprocess.CalledProcessError as e:
                raise InstallerError(f"Failed to download server: {e}")
        
        target_path.chmod(0o755)
        self.print_success(f"Server downloaded to {target_path}")
    
    def check_dependencies(self) -> None:
        """Check for required dependencies."""
        missing_deps = []
        
        if not self.command_exists("uv"):
            missing_deps.append("uv")
        
        if not (self.command_exists("python3") or self.command_exists("python")):
            missing_deps.append("python3")
        
        if missing_deps:
            self.print_error(f"Missing dependencies: {', '.join(missing_deps)}")
            self.print_info("Please install missing dependencies:")
            for dep in missing_deps:
                if dep == "uv":
                    print("  - Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
                elif dep == "python3":
                    print("  - Install Python 3.10+: https://www.python.org/downloads/")
            raise InstallerError("Missing dependencies")
    
    def run_command(self, cmd: List[str], description: str = "") -> None:
        """Run a shell command with error handling."""
        if self.verbose:
            self.print_info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=not self.verbose,
                text=True
            )
            if self.verbose and result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {' '.join(cmd)}"
            if e.stderr:
                error_msg += f"\nError: {e.stderr}"
            raise InstallerError(error_msg)
        except FileNotFoundError:
            raise InstallerError(f"Command not found: {cmd[0]}")
    
    def install_claude_desktop(self, server_path: Path) -> None:
        """Install for Claude Desktop."""
        self.print_info("Installing for Claude Desktop...")
        
        config_path = self.get_claude_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        abs_server_path = server_path.resolve()
        
        config_data = {
            "mcpServers": {
                "napari": {
                    "command": "uv",
                    "args": [
                        "run", "--with", "Pillow", "--with", "PyQt6", "--with", "fastmcp",
                        "--with", "imageio", "--with", "napari", "--with", "numpy", "--with", "qtpy",
                        "fastmcp", "run", str(abs_server_path)
                    ]
                }
            }
        }
        
        # Handle existing config
        if config_path.exists():
            self.print_warning(f"Existing Claude Desktop config found at {config_path}")
            response = input("Do you want to backup and replace it? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                backup_path = config_path.with_suffix(f".backup.{int(os.time())}.json")
                shutil.copy2(config_path, backup_path)
                self.print_info(f"Backup created: {backup_path}")
            else:
                raise InstallerError("Installation cancelled")
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
        self.print_success(f"Claude Desktop configured at {config_path}")
        self.print_info("Please restart Claude Desktop to apply changes")
    
    def install_claude_code(self, server_path: Path) -> None:
        """Install for Claude Code."""
        self.print_info("Installing for Claude Code...")
        
        if not self.command_exists("fastmcp"):
            self.print_info("Installing fastmcp...")
            self.run_command(["uv", "tool", "install", "fastmcp"])
        
        abs_server_path = server_path.resolve()
        
        cmd = [
            "fastmcp", "install", "claude-code", str(abs_server_path),
            "--with", "napari",
            "--with", "imageio", 
            "--with", "Pillow",
            "--with", "PyQt6",
            "--with", "numpy",
            "--with", "qtpy"
        ]
        
        self.run_command(cmd, "Installing Claude Code integration")
        
        self.print_success("Claude Code integration installed")
        self.print_info("Server will be automatically available in Claude Code")
    
    def install_cursor(self, server_path: Path) -> None:
        """Install for Cursor."""
        self.print_info("Installing for Cursor...")
        
        if not self.command_exists("fastmcp"):
            self.print_info("Installing fastmcp...")
            self.run_command(["uv", "tool", "install", "fastmcp"])
        
        abs_server_path = server_path.resolve()
        
        cmd = [
            "fastmcp", "install", "cursor", str(abs_server_path),
            "--with", "napari",
            "--with", "imageio",
            "--with", "Pillow", 
            "--with", "PyQt6",
            "--with", "numpy",
            "--with", "qtpy"
        ]
        
        self.run_command(cmd, "Installing Cursor integration")
        
        self.print_success("Cursor integration installed")
        self.print_info("Server will be automatically available in Cursor's AI assistant")
    
    def install_chatgpt(self) -> None:
        """Show ChatGPT setup guide."""
        self.print_info("ChatGPT setup requires manual configuration...")
        
        if self.console:
            guide_text = """
ChatGPT (Deep Research only) setup steps:

1. Deploy server publicly (e.g., using ngrok):
   ngrok http 8000

2. Run server on public URL:
   uv run --with fastmcp --with napari --with imageio --with Pillow \\
       fastmcp serve napari_mcp_server.py --host 0.0.0.0 --port 8000

3. In ChatGPT:
   - Go to Settings → Connectors
   - Add custom connector with your public URL
   - Format: https://your-url.ngrok.io/mcp/

4. Use in Deep Research mode only

Note: Limited functionality compared to other integrations
            """
            panel = Panel(guide_text.strip(), title="ChatGPT Setup Guide", style="yellow")
            self.console.print(panel)
        else:
            print("\nChatGPT (Deep Research only) setup steps:")
            print("1. Deploy server publicly (e.g., using ngrok):")
            print("   ngrok http 8000")
            print("")
            print("2. Run server on public URL:")
            print("   uv run --with fastmcp --with napari --with imageio --with Pillow \\")
            print("       fastmcp serve napari_mcp_server.py --host 0.0.0.0 --port 8000")
            print("")
            print("3. In ChatGPT:")
            print("   - Go to Settings → Connectors")
            print("   - Add custom connector with your public URL")
            print("   - Format: https://your-url.ngrok.io/mcp/")
            print("")
            print("4. Use in Deep Research mode only")
            print("")
            self.print_warning("Note: Limited functionality compared to other integrations")
    
    def test_installation(self, target: str) -> None:
        """Test the installation."""
        self.print_info(f"Testing {target} installation...")
        
        if target == "claude-desktop":
            config_path = self.get_claude_config_path()
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    if "napari" in config.get("mcpServers", {}):
                        self.print_success("Claude Desktop config found and contains napari server")
                    else:
                        raise InstallerError("Claude Desktop config missing napari server")
                except (json.JSONDecodeError, KeyError) as e:
                    raise InstallerError(f"Invalid Claude Desktop config: {e}")
            else:
                raise InstallerError("Claude Desktop config not found")
                
        elif target in ["claude-code", "cursor"]:
            try:
                result = subprocess.run(
                    ["fastmcp", "list"], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                if target in result.stdout:
                    self.print_success(f"{target} integration found in fastmcp list")
                else:
                    raise InstallerError(f"{target} integration not found in fastmcp list")
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise InstallerError(f"Could not verify {target} installation")
                
        elif target == "chatgpt":
            self.print_info("ChatGPT requires manual testing in Deep Research mode")
    
    def install_target(self, target: str, server_path: Path) -> None:
        """Install for the specified target."""
        if target == "claude-desktop":
            self.install_claude_desktop(server_path)
        elif target == "claude-code":
            self.install_claude_code(server_path)
        elif target == "cursor":
            self.install_cursor(server_path)
        elif target == "chatgpt":
            self.install_chatgpt()
        elif target == "all":
            self.install_claude_desktop(server_path)
            self.install_claude_code(server_path)
            self.install_cursor(server_path)
            self.install_chatgpt()
        else:
            raise InstallerError(f"Unknown target: {target}")
    
    def install(self, target: str, server_path: Optional[Path] = None, 
                use_local: bool = False) -> None:
        """Main installation method."""
        self.print_header()
        
        # Check dependencies
        self.print_info("Checking dependencies...")
        self.check_dependencies()
        self.print_success("Dependencies check passed")
        
        # Determine server path
        if server_path:
            if not server_path.exists():
                raise InstallerError(f"Server file not found: {server_path}")
            server_file = server_path
        elif use_local:
            server_file = PROJECT_ROOT / "src/napari_mcp_server.py"
            if not server_file.exists():
                raise InstallerError(f"Local server file not found: {server_file}")
        else:
            server_file = Path("./napari_mcp_server.py")
            if not server_file.exists():
                self.download_server(server_file)
            else:
                self.print_info(f"Using existing server file: {server_file}")
        
        # Install for target
        if self.console and HAS_RICH:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task(f"Installing for {target}...", total=None)
                self.install_target(target, server_file)
        else:
            self.install_target(target, server_file)
        
        # Test installation (skip for 'all' and 'chatgpt')
        if target not in ["all", "chatgpt"]:
            self.test_installation(target)
        
        self.print_success(f"Installation completed for {target}!")
        
        if target == "all":
            self.print_info("\nNext steps:")
            print("1. Restart Claude Desktop")
            print("2. Claude Code and Cursor should have the server available immediately")
            print("3. For ChatGPT, follow the manual setup steps shown above")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Napari MCP Server automatic installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run scripts/uv_install.py claude-desktop
  uv run --with requests --with rich scripts/uv_install.py --verbose claude-code
  uv run scripts/uv_install.py --local cursor
        """
    )
    
    parser.add_argument(
        "target",
        choices=["claude-desktop", "claude-code", "cursor", "chatgpt", "all"],
        help="Installation target"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--local",
        action="store_true", 
        help="Use local server file instead of downloading"
    )
    
    parser.add_argument(
        "--server-path",
        type=Path,
        help="Path to server file"
    )
    
    args = parser.parse_args()
    
    try:
        installer = NapariMCPInstaller(verbose=args.verbose)
        installer.install(
            target=args.target,
            server_path=args.server_path,
            use_local=args.local
        )
    except InstallerError as e:
        print(f"❌ Installation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
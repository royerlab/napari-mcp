# Installation Guide for napari-mcp

This guide provides detailed instructions for installing napari-mcp across different AI assistants and development environments.

## Table of Contents
- [Quick Installation](#quick-installation)
- [Manual Configuration](#manual-configuration)
- [Platform-Specific Details](#platform-specific-details)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

## Quick Installation

The easiest way to install napari-mcp is using our automatic installer:

```bash
# Install the package
pip install napari-mcp

# Run the installer for your application
napari-mcp-install <application>
```

### Supported Applications

| Application | Command | Description |
|-------------|---------|-------------|
| `claude-desktop` | `napari-mcp-install claude-desktop` | Claude Desktop application |
| `claude-code` | `napari-mcp-install claude-code` | Claude Code CLI tool |
| `cursor` | `napari-mcp-install cursor` | Cursor IDE |
| `cline-vscode` | `napari-mcp-install cline-vscode` | Cline extension in VS Code |
| `cline-cursor` | `napari-mcp-install cline-cursor` | Cline extension in Cursor IDE |
| `gemini` | `napari-mcp-install gemini` | Gemini CLI |
| `codex` | `napari-mcp-install codex` | Codex CLI (OpenAI) |
| `all` | `napari-mcp-install all` | Install for all supported apps |

### Installer Options

```bash
# Use persistent Python environment instead of ephemeral uv
napari-mcp-install claude-desktop --persistent

# Specify custom Python executable
napari-mcp-install claude-desktop --python-path /path/to/python

# Force update without prompts
napari-mcp-install claude-desktop --force

# Preview changes without applying
napari-mcp-install claude-desktop --dry-run

# Skip backup creation
napari-mcp-install claude-desktop --no-backup

# For project-specific installations (Cursor, Gemini)
napari-mcp-install cursor --project /path/to/project
napari-mcp-install cursor --global  # Install globally instead
```

### Management Commands

```bash
# List all installations
napari-mcp-install list

# Uninstall from an application
napari-mcp-install uninstall claude-desktop

# Uninstall from all applications
napari-mcp-install uninstall all
```

## Manual Configuration

If you prefer manual setup or need to customize the configuration, here are the configuration file locations and formats for each application.

### Configuration File Locations

#### Claude Desktop
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

#### Claude Code
- **All platforms**: `~/.claude.json`

#### Cursor
- **Global**: `~/.cursor/mcp.json`
- **Project**: `.cursor/mcp.json` (in project root)

#### Cline (VS Code)
- **macOS**: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Windows**: `%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Linux**: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Note**: For VS Code Insiders, replace "Code" with "Code - Insiders" in the path

#### Cline (Cursor IDE)
- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Windows**: `%APPDATA%/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Linux**: `~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

#### Gemini CLI
- **Global**: `~/.gemini/settings.json`
- **Project**: `.gemini/settings.json` (in project root)

#### Codex CLI
- **All platforms**: `~/.codex/config.toml`

### Configuration Format

All applications use a similar JSON format with an `mcpServers` object:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"]
    }
  }
}
```

#### For Persistent Python Environment

If you want to use your existing Python environment instead of uv:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "/path/to/python",
      "args": ["-m", "napari_mcp.server"]
    }
  }
}
```

#### Application-Specific Fields

**Gemini CLI** supports additional configuration:
```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "cwd": ".",
      "timeout": 600000,
      "trust": false
    }
  }
}
```

**Cline** supports tool permissions:
```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "alwaysAllow": ["screenshot", "list_layers"],
      "disabled": false
    }
  }
}
```

**Codex CLI** uses TOML format:
```toml
[mcp_servers.napari_mcp]
command = "uv"
args = ["run", "--with", "napari-mcp", "napari-mcp"]
```

## Platform-Specific Details

### macOS

1. **Permissions**: You may need to grant terminal/application permissions for file access
2. **Python Path**: Use `which python3` to find your Python executable
3. **Environment Variables**: Use `launchctl setenv` for system-wide variables

### Windows

1. **Path Format**: Use forward slashes or escaped backslashes in JSON:
   - Good: `"C:/Python/python.exe"` or `"C:\\Python\\python.exe"`
   - Bad: `"C:\Python\python.exe"`

2. **Environment Variables**: Access with `%VARIABLE_NAME%` syntax
3. **Python Path**: Use `where python` to find your Python executable

### Linux

1. **Permissions**: Ensure config directories are writable
2. **Python Path**: Use `which python3` to find your Python executable
3. **Desktop Files**: Some applications may require `.desktop` file updates

## Troubleshooting

### Common Issues

#### "napari-mcp not found in Python environment"
**Solution**: Install napari-mcp in your Python environment:
```bash
pip install napari-mcp
```

#### "Configuration file not found"
**Solution**: The installer will create the file if it doesn't exist. For manual setup, create the parent directory first:
```bash
# Example for Claude Desktop on macOS
mkdir -p ~/Library/Application\ Support/Claude
```

#### "Permission denied" errors
**Solution**:
- Check file permissions: `ls -la <config-file>`
- Fix permissions: `chmod 644 <config-file>`
- Use `sudo` if necessary (not recommended)

#### "Command not found: uv"
**Solution**: Install uv package manager:
```bash
pip install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Application doesn't detect the server
**Solution**:
1. Restart the application after configuration
2. Check the application's MCP server logs
3. Verify JSON syntax is correct: `python -m json.tool < config-file.json`

### Debug Mode

To troubleshoot issues, you can test the server directly:

```bash
# Test with uv
uv run --with napari-mcp napari-mcp

# Test with Python
python -m napari_mcp.server
```

## Advanced Configuration

### Using Environment Variables

You can pass environment variables to the server:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "env": {
        "NAPARI_MCP_BRIDGE_PORT": "9999",
        "NAPARI_MCP_MAX_OUTPUT_ITEMS": "2000"
      }
    }
  }
}
```

### Multiple Server Instances

You can run multiple napari-mcp instances with different configurations:

```json
{
  "mcpServers": {
    "napari-main": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"]
    },
    "napari-dev": {
      "command": "/path/to/dev/python",
      "args": ["-m", "napari_mcp.server"],
      "env": {
        "NAPARI_MCP_BRIDGE_PORT": "10000"
      }
    }
  }
}
```

### Development Setup

For development, use the persistent mode with your development environment:

```bash
# Clone and install in development mode
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp
pip install -e ".[dev]"

# Install with your development Python
napari-mcp-install claude-desktop --persistent --python-path $(which python)
```

### External Viewer Mode

To connect to an external napari viewer:

1. Start napari and enable the MCP bridge:
   - Open napari
   - Go to Plugins → MCP Server Control
   - Click "Start Server" (note the port number)

2. Configure your application to use bridge mode:
```json
{
  "mcpServers": {
    "napari-bridge": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "env": {
        "NAPARI_MCP_BRIDGE_PORT": "9999"
      }
    }
  }
}
```

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Run `napari-mcp-install --help` for command help
3. Check application-specific MCP logs
4. Open an issue at [GitHub Issues](https://github.com/royerlab/napari-mcp/issues)

## Security Notes

- The installer creates backups by default (`.backup_<pid>` files)
- Configuration files may contain sensitive information - protect them appropriately
- Use `--dry-run` to preview changes before applying
- The `trust: true` option in Gemini CLI bypasses tool confirmations - use with caution
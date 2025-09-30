# Advanced Installation

Advanced installation options for napari MCP server including manual configuration, development setup, and zero-install approaches.

!!! tip "Quick Setup Available"
    Most users should use the **[Quick Start Guide](quickstart.md)** with the automated CLI installer. This guide is for advanced users who need manual configuration or development setups.

## CLI Installer (Recommended)

The easiest way is using the automated installer:

```bash
pip install napari-mcp
napari-mcp-install <application>
```

**→ See [Quick Start](quickstart.md) for step-by-step instructions**

---

## Manual Configuration

For users who prefer manual setup or need custom configurations.

### Configuration File Locations

The CLI installer auto-detects these locations. For manual setup, you need to know where each application stores its MCP config:

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

*Note: For VS Code Insiders, replace "Code" with "Code - Insiders"*

#### Cline (Cursor)
- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Windows**: `%APPDATA%/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Linux**: `~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

#### Gemini CLI
- **Global**: `~/.gemini/settings.json`
- **Project**: `.gemini/settings.json` (in project root)

#### Codex CLI
- **All platforms**: `~/.codex/config.toml` (TOML format)

### Standard Configuration (JSON)

Most applications use this JSON format:

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

This uses `uv` for zero-install execution (no permanent installation required).

### Using Persistent Python Environment

If you have napari-mcp installed in your Python environment:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "python",
      "args": ["-m", "napari_mcp.server"]
    }
  }
}
```

Or with a specific Python path:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "/path/to/your/python",
      "args": ["-m", "napari_mcp.server"]
    }
  }
}
```

### Application-Specific Configuration

#### Gemini CLI (Extended)

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

#### Cline (Tool Permissions)

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

#### Codex CLI (TOML Format)

```toml
[mcp_servers.napari_mcp]
command = "uv"
args = ["run", "--with", "napari-mcp", "napari-mcp"]
```

---

## Zero Install with uv

Run napari MCP without permanent installation using `uv`:

```bash
# Direct execution (for testing)
uv run --with napari-mcp napari-mcp
```

The configuration files use `uv` automatically. See **[Zero Install Guide](zero-install.md)** for details.

---

## Development Installation

For contributors and plugin developers:

### Clone and Install

```bash
# Clone repository
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp

# Install in editable mode with dev dependencies
pip install -e ".[test,dev]"

# Or with uv (recommended)
uv pip install -e ".[test,dev]"
```

### Configure for Development

```bash
# Configure to use your development installation
napari-mcp-install claude-desktop --persistent

# This will use your local Python with the editable installation
```

### Run Tests

```bash
# Fast tests (skip GUI)
pytest -m "not realgui"

# With coverage
pytest --cov=src --cov-report=html -m "not realgui"

# Include GUI tests (requires display)
pytest -m realgui
```

### Development Tools

```bash
# Install pre-commit hooks
pre-commit install

# Run linting
ruff check src/ tests/

# Format code
ruff format src/ tests/
```

---

## Virtual Environment Setup

### Using venv

```bash
# Create environment
python -m venv napari-mcp-env

# Activate (macOS/Linux)
source napari-mcp-env/bin/activate

# Activate (Windows)
napari-mcp-env\Scripts\activate

# Install
pip install napari-mcp

# Configure
napari-mcp-install <app> --persistent
```

### Using conda

```bash
# Create environment
conda create -n napari-mcp python=3.11

# Activate
conda activate napari-mcp

# Install
pip install napari-mcp

# Configure
napari-mcp-install <app> --persistent
```

---

## External Viewer Mode (Plugin Bridge)

Connect to an existing napari viewer via the plugin:

1. **Start napari** and open the MCP Server Control widget:
   - Plugins → MCP Server Control

2. **Click "Start Server"** (default port: 9999)

3. **Configure your AI app** with standard CLI installer:
   ```bash
   napari-mcp-install <app>
   ```

The server auto-detects the external viewer and proxies requests to it.

---

## Environment Variables

Advanced configuration via environment variables:

```bash
# Qt platform (for headless systems)
export QT_QPA_PLATFORM=offscreen

# MCP bridge port (for external viewer)
export NAPARI_MCP_BRIDGE_PORT=9999

# Output limits
export NAPARI_MCP_MAX_OUTPUT_ITEMS=2000

# Logging
export MCP_LOG_LEVEL=INFO
```

Add to your config:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "env": {
        "QT_QPA_PLATFORM": "offscreen",
        "NAPARI_MCP_BRIDGE_PORT": "9999"
      }
    }
  }
}
```

---

## Platform-Specific Notes

### macOS
- Permissions: Grant terminal access in System Preferences
- Python path: Use `which python3` to find interpreter
- M1/M2: Ensure native ARM Python for best performance

### Windows
- Path format: Use forward slashes in JSON: `"C:/Python/python.exe"`
- Environment variables: Access with `%VAR%` syntax
- PowerShell: May need execution policy changes

### Linux
- Display: X11 or Wayland required for GUI (or use offscreen mode)
- Permissions: Ensure config directories are writable
- Headless: Use `QT_QPA_PLATFORM=offscreen` for servers

---

## Troubleshooting

Common installation issues and solutions:

### Command Not Found

```bash
# Verify installation
pip list | grep napari-mcp

# Check PATH
which napari-mcp-install

# Reinstall
pip install --force-reinstall napari-mcp
```

### Configuration Not Applied

```bash
# Verify config created
napari-mcp-install list

# Check file syntax
python -m json.tool < config-file.json

# Force reinstall
napari-mcp-install <app> --force
```

### Python Environment Issues

```bash
# Check Python version
python --version  # Should be 3.10+

# Verify napari-mcp is accessible
python -c "import napari_mcp; print('OK')"

# Use specific Python
napari-mcp-install <app> --python-path $(which python)
```

**→ See [Troubleshooting Guide](../guides/troubleshooting.md) for comprehensive help**

---

## Next Steps

- **[Quick Start](quickstart.md)** - If you haven't tried the automated installer
- **[Integration Guides](../integrations/index.md)** - Application-specific setup
- **[API Reference](../api/index.md)** - Available tools and functions
- **[Troubleshooting](../guides/troubleshooting.md)** - Common issues

---

**For most users, the [Quick Start Guide](quickstart.md) with automated CLI installer is the recommended approach!**

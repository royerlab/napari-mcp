# Getting Started

Welcome to the Napari MCP Server! This section will help you get up and running with AI-controlled napari in just a few minutes.

## Choose Your Path

Two simple ways to set up napari MCP:

| Method | Description | Best For | Setup Time |
|--------|-------------|----------|------------|
| **[⚡ Quick Start](quickstart.md)** | CLI installer automatically configures your AI app | Most users | ~3 minutes |
| **[🛠️ Advanced Installation](installation.md)** | Manual configuration and development setup | Advanced users, developers | ~10 minutes |

## What You'll Need

### For Quick Start (Recommended)
- **Python 3.10+**
- **pip** (comes with Python)

### For Advanced Installation
- **Python 3.10+**
- **pip** or **uv**
- **Git** (for development install)

## Installation Overview

### Quick Start Method (Recommended)

```bash
# 1. Install package
pip install napari-mcp

# 2. Auto-configure your application
napari-mcp-install claude-desktop  # or claude-code, cursor, etc.

# 3. Restart application and start using!
```

### Advanced Method

For manual configuration, zero-install with uv, or development setup:
- **[Zero Install](zero-install.md)** - Use `uv` without permanent installation
- **[Manual Configuration](installation.md)** - Detailed setup for all platforms
- **Development Setup** - Clone repository and install in editable mode

## Expected Timeline

| Method | Setup Time | Use Case |
|--------|------------|----------|
| **Quick Start (CLI)** | ~3 minutes | First-time users, quick demo |
| **Manual Config** | ~5 minutes | Custom configurations |
| **Zero Install** | ~2 minutes | Testing, CI/CD pipelines |
| **Development** | ~10 minutes | Contributing, plugin development |

## Success Indicators

After following any guide, you should see:

- ✅ **No errors** during installation/configuration
- ✅ **Napari window** opens when AI app requests it
- ✅ **Your AI app** can call `session_information()` successfully
- ✅ **Screenshot tool** works and returns images

## Supported AI Applications

The CLI installer supports:

| Application | Command | Platform |
|-------------|---------|----------|
| **Claude Desktop** | `napari-mcp-install claude-desktop` | macOS, Windows, Linux |
| **Claude Code** | `napari-mcp-install claude-code` | macOS, Windows, Linux |
| **Cursor IDE** | `napari-mcp-install cursor` | macOS, Windows, Linux |
| **Cline (VS Code)** | `napari-mcp-install cline-vscode` | macOS, Windows, Linux |
| **Cline (Cursor)** | `napari-mcp-install cline-cursor` | macOS, Windows, Linux |
| **Gemini CLI** | `napari-mcp-install gemini` | macOS, Windows, Linux |
| **Codex CLI** | `napari-mcp-install codex` | macOS, Windows, Linux |
| **All** | `napari-mcp-install all` | Install for all apps |

**→ See [Integration Guides](../integrations/index.md) for app-specific details**

## Need Help?

If you run into issues:

1. **Check prerequisites** - Ensure Python 3.10+ and pip are installed
2. **Verify installation** - Run `napari-mcp-install --help`
3. **Restart AI apps** - Claude Desktop, Cursor, etc. after config changes
4. **Check logs** - Look for error messages in terminal output

**→ See our [Troubleshooting Guide](../guides/troubleshooting.md) for detailed help**

---

Ready to begin? Pick your preferred method above and let's get started! 🚀

# Getting Started

Welcome to the Napari MCP Server! This section will help you get up and running with AI-controlled napari in just a few minutes.

## Choose Your Path

Two simple ways to set up napari MCP:

| Method | Description | Best For | Setup Time |
|--------|-------------|----------|------------|
| **[⚡ MCP JSON Config](quickstart.md)** | Add a single JSON entry; your AI app auto-launches the server | Most users | ~2 minutes |
| **[🔌 Plugin Bridge](installation.md)** | Use napari’s MCP Server Control widget (external viewer) | Users who want to drive an existing napari window | ~5 minutes |
| **[📦 Zero Install](zero-install.md)** | Details on zero-install and optional manual runs | Advanced/CI | ~5 minutes |

## What You'll Need

### Prerequisites

=== "MCP JSON Config"
    - **[uv](https://docs.astral.sh/uv/)** - Modern Python package manager
    - **Python 3.10+** (managed automatically by uv)

=== "Plugin Bridge"
    - **Python 3.10+**
    - **pip** or **uv**

### Installing uv (if needed)

!!! tip "Installing uv"
    === "macOS/Linux"
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```

    === "Windows"
        ```powershell
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        ```

    === "With pip"
        ```bash
        pip install uv
        ```

## Expected Timeline

| Method | Setup Time | Use Case |
|--------|------------|----------|
| **Quick Start** | ~2 minutes | Demo, first try |
| **Zero Install** | ~5 minutes | Production use without installation |
| **Traditional** | ~10 minutes | Development, permanent setup |

## Common Success Indicators

After following any guide, you should see:

- ✅ **FastMCP banner** in terminal output
- ✅ **Napari window** opens automatically
- ✅ **"Starting MCP server"** message
- ✅ **Claude Desktop** (or your AI tool) can call `session_information()`

## Support Matrix

| Feature | Quick Start | Zero Install | Traditional |
|---------|-------------|--------------|-------------|
| **AI Integration** | ✅ Full | ✅ Full | ✅ Full |
| **All MCP Tools** | ✅ All 20+ | ✅ All 20+ | ✅ All 20+ |
| **Setup Complexity** | 🟢 Minimal | 🟡 Medium | 🔴 Complex |
| **Dependency Management** | 🟢 Automatic | 🟢 Automatic | 🔴 Manual |
| **Development Use** | 🔴 Limited | 🟡 Good | 🟢 Excellent |

## Need Help?

If you run into issues:

1. **Check prerequisites** - Ensure uv or Python is installed
2. **Verify paths** - Use absolute paths in configurations
3. **Restart AI apps** - Claude Desktop, Cursor, etc. after config changes
4. **Check logs** - Look for error messages in terminal output

**→ See our [Troubleshooting Guide](../guides/troubleshooting.md) for detailed help**

---

Ready to begin? Pick your preferred method above and let's get started! 🚀

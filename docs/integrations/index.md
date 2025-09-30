# LLM Application Integrations

Connect napari MCP server with your favorite AI assistant or development environment using our automated CLI installer.

## 🚀 Quick Installation

All integrations use the same simple command:

```bash
# Install napari-mcp
pip install napari-mcp

# Auto-configure your application
napari-mcp-install <application-name>
```

## Supported Platforms

| Platform | Command | Status | Guide |
|----------|---------|--------|-------|
| **Claude Desktop** | `napari-mcp-install claude-desktop` | ✅ Full Support | [Setup →](claude-desktop.md) |
| **Claude Code** | `napari-mcp-install claude-code` | ✅ Full Support | [Setup →](claude-code.md) |
| **Cursor IDE** | `napari-mcp-install cursor` | ✅ Full Support | [Setup →](cursor.md) |
| **Cline** | `napari-mcp-install cline-vscode` or `cline-cursor` | ✅ Full Support | [Setup →](cline.md) |
| **Gemini / Codex** | `napari-mcp-install gemini` or `codex` | ✅ Full Support | [Setup →](other-llms.md) |
| **Python** | Custom script | ✅ Full Support | [Guide →](python.md) |
| **ChatGPT** | N/A | ❌ Not Supported | [Why? →](chatgpt.md) |

## Feature Comparison

| Feature | Claude Desktop | Claude Code | Cursor | Cline | Gemini/Codex |
|---------|----------------|-------------|--------|-------|--------------|
| **Visual napari window** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **All MCP tools** | ✅ 20+ tools | ✅ 20+ tools | ✅ 20+ tools | ✅ 20+ tools | ✅ 20+ tools |
| **File system access** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Code execution** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Package installation** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Setup complexity** | 🟢 Easy | 🟢 Easy | 🟢 Easy | 🟢 Easy | 🟢 Easy |
| **Best for** | General use | Development | AI coding | VS Code users | Advanced users |

## Installation Workflow

### Step 1: Install Package

```bash
pip install napari-mcp
```

### Step 2: Auto-Configure

```bash
# For your specific application
napari-mcp-install <app-name>

# See all options
napari-mcp-install --help

# Preview changes before applying
napari-mcp-install <app-name> --dry-run
```

### Step 3: Restart & Test

1. Completely restart your application
2. Ask: `"Can you call session_information() to show my napari session?"`
3. Success! ✅

## Installation Options

The CLI installer supports several options:

```bash
# Use your Python environment instead of uv
napari-mcp-install claude-desktop --persistent

# Custom Python path
napari-mcp-install claude-desktop --python-path /path/to/python

# Preview changes only
napari-mcp-install claude-desktop --dry-run

# Force update without prompts
napari-mcp-install claude-desktop --force

# Install for all applications
napari-mcp-install all
```

## Management Commands

```bash
# List all installations
napari-mcp-install list

# Uninstall from an application
napari-mcp-install uninstall claude-desktop

# Uninstall from all
napari-mcp-install uninstall all
```

## Platform-Specific Guides

Choose your application for detailed setup instructions:

### 🖥️ Desktop Applications

- **[Claude Desktop](claude-desktop.md)** - Most popular choice for general use
- **[Claude Code](claude-code.md)** - CLI integration for development workflows

### 💻 IDE Integrations

- **[Cursor IDE](cursor.md)** - AI-powered coding with napari
- **[Cline](cline.md)** - VS Code and Cursor extensions

### 🌐 Other Platforms

- **[Gemini CLI & Codex](other-llms.md)** - Google Gemini and OpenAI Codex setup
- **[Python Integration](python.md)** - Custom scripts for workflow automation
- **[ChatGPT](chatgpt.md)** - Why ChatGPT doesn't work and what to use instead

## Common Configuration

All platforms support environment variables for advanced configuration:

```bash
export QT_QPA_PLATFORM=offscreen  # For headless servers
export NAPARI_ASYNC=1             # Enable async operations
export MCP_LOG_LEVEL=INFO         # Debug MCP communication
```

## Troubleshooting

### CLI Installer Issues

!!! failure "napari-mcp-install: command not found"
    ```bash
    # Reinstall package
    pip install --force-reinstall napari-mcp

    # Verify
    napari-mcp-install --version
    ```

!!! failure "Configuration not detected"
    ```bash
    # List what would be configured
    napari-mcp-install <app> --dry-run

    # Check current installations
    napari-mcp-install list
    ```

!!! failure "Permission errors"
    ```bash
    # Check config locations
    napari-mcp-install list

    # Fix permissions (macOS/Linux)
    chmod 644 <config-file-path>
    ```

### Application-Specific Issues

Each integration guide has troubleshooting sections for platform-specific problems:

- **Claude Desktop** - Config file location, restart issues
- **Claude Code** - CLI configuration, environment setup
- **Cursor** - Project vs global installation
- **Cline** - Extension detection, VS Code variants
- **Gemini/Codex** - TOML config, API setup

**→ See [Troubleshooting Guide](../guides/troubleshooting.md) for comprehensive help**

## Advanced: Python Scripting

For batch processing or custom pipelines, see **[Python Scripts](python.md)** to use napari MCP with any LLM in your own code.

## Next Steps

1. **Choose your platform** based on your primary use case
2. **Follow the specific setup guide** for detailed instructions
3. **Test the integration** with our provided examples
4. **Explore advanced features** once basic setup works

---

**Ready to connect your AI assistant?** Choose your platform above and let's get started! 🚀

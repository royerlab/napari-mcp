# Other LLM Integrations

Setup guides for Gemini CLI and Codex CLI - additional platforms with napari MCP support.

## 🌐 Gemini CLI

Setup guide for Google's Gemini CLI with napari MCP server.

### Quick Setup

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Auto-configure Gemini CLI (global)
napari-mcp-install install gemini --global

# OR configure for specific project
napari-mcp-install install gemini --project /path/to/project
```

### Configuration Locations

- **Global**: `~/.gemini/settings.json`
- **Project**: `.gemini/settings.json` in project root

### Installation Options

```bash
# Global installation (recommended)
napari-mcp-install install gemini --global

# Project-specific installation
napari-mcp-install install gemini --project .

# Preview changes
napari-mcp-install install gemini --dry-run

# Use persistent Python
napari-mcp-install install gemini --persistent
```

### Manual Configuration

Gemini CLI supports additional configuration options:

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

**Configuration fields:**
- **`cwd`**: Working directory for the server
- **`timeout`**: Timeout in milliseconds (default: 600000 = 10 minutes)
- **`trust`**: If `true`, bypasses tool confirmation prompts (use with caution)

### Management

```bash
# Check installation
napari-mcp-install list

# Update configuration
napari-mcp-install install gemini --global --force

# Uninstall
napari-mcp-install uninstall gemini
```

### Troubleshooting

!!! failure "Gemini doesn't see napari tools"
    1. Verify installation: `napari-mcp-install list`
    2. Check config file exists: `cat ~/.gemini/settings.json`
    3. Restart Gemini CLI
    4. Reinstall: `napari-mcp-install install gemini --global --force`

---

## 🤖 Codex CLI

Setup guide for OpenAI's Codex CLI with napari MCP server.

### Quick Setup

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Auto-configure Codex CLI
napari-mcp-install install codex

# 3. Restart Codex CLI
```

### Configuration Location

- **All platforms**: `~/.codex/config.toml`

!!! note "TOML Format"
    Codex CLI uses TOML configuration format instead of JSON.

### Installation Options

```bash
# Basic installation
napari-mcp-install install codex

# Preview changes
napari-mcp-install install codex --dry-run

# Use persistent Python
napari-mcp-install install codex --persistent

# Force update
napari-mcp-install install codex --force
```

### Manual Configuration

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.napari_mcp]
command = "uv"
args = ["run", "--with", "napari-mcp", "napari-mcp"]
```

### Using Persistent Environment

```toml
[mcp_servers.napari_mcp]
command = "python"
args = ["-m", "napari_mcp.server"]
```

### Management

```bash
# Check installation
napari-mcp-install list

# Update configuration
napari-mcp-install install codex --force

# Uninstall
napari-mcp-install uninstall codex
```

### Troubleshooting

!!! failure "Codex doesn't see napari tools"
    1. Verify installation: `napari-mcp-install list`
    2. Check config file: `cat ~/.codex/config.toml`
    3. Validate TOML syntax: `python -c "import toml; toml.load(open('.codex/config.toml'))"`
    4. Restart Codex CLI
    5. Reinstall: `napari-mcp-install install codex --force`

!!! failure "TOML syntax errors"
    The installer requires the `toml` package. Install it:
    ```bash
    pip install toml
    ```

---

## 🔄 Install for All Platforms

You can install napari-mcp for all supported platforms at once:

```bash
napari-mcp-install install all
```

This installs for:
- Claude Desktop
- Claude Code
- Cursor (global)
- Cline (VS Code and Cursor)
- Gemini (global)
- Codex

Use `--dry-run` to preview:
```bash
napari-mcp-install install all --dry-run
```

---

## ⚖️ Platform Comparison

| Feature | Gemini CLI | Codex CLI |
|---------|------------|-----------|
| **Config Format** | JSON | TOML |
| **Project-specific** | ✅ Yes | ❌ No |
| **Global install** | ✅ Yes | ✅ Yes |
| **Tool confirmations** | Configurable (`trust`) | Yes |
| **Timeout setting** | ✅ Configurable | Default |
| **maturity** | Beta | Stable |

---

## 🔐 Security Notes

### Gemini CLI

- **`trust: true`** bypasses all tool confirmation prompts
- Only set `trust: true` in controlled environments
- Use `trust: false` (default) for safety

### Codex CLI

- Always requires confirmation for code execution
- Runs with your user permissions
- TOML config file should have appropriate permissions

---

## 📚 Resources

### Gemini CLI
- **[Gemini CLI Documentation](https://ai.google.dev/gemini-api/docs/cli)** - Official docs
- **[Gemini API](https://ai.google.dev)** - API documentation

### Codex CLI
- **[OpenAI Codex](https://openai.com/codex)** - Product page
- **[OpenAI API Docs](https://platform.openai.com/docs)** - API documentation

---

## 📚 Next Steps

- **[Quick Start](../getting-started/quickstart.md)** - Get started quickly
- **[API Reference](../api/index.md)** - All available tools
- **[Troubleshooting](../guides/troubleshooting.md)** - Common issues

---

→ [Back to Integrations Overview](index.md)
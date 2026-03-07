# Claude Code Integration

Setup guide for using napari MCP server with Claude Code - perfect for development workflows and AI-assisted coding.

## 🚀 Quick Setup

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Auto-configure Claude Code
napari-mcp-install install claude-code

# 3. Restart Claude Code (if running)
```

## 📍 Configuration Location

- **All platforms**: `~/.claude.json`

The CLI installer automatically creates or updates this file.

## 💡 Why Use Claude Code with napari?

- **Development Focus**: Perfect for napari plugin development
- **Code Context**: AI understands your current code and project
- **File Integration**: Easy image loading from workspace
- **Live Testing**: Test changes immediately with napari viewer

## 🧪 Testing

After configuration, test with:

```
Can you call session_information() to show the napari session details?
```

```
Load the image from ./test_data/sample.tif and show it in napari
```

## 💻 Development Workflows

###Plugin Development

```
Help me create a new napari plugin that applies Gaussian filtering
```

```
Test this layer manipulation code in the current napari viewer
```

### Image Analysis Scripts

```
Create a Python script that loads this image, applies preprocessing, and saves the result
```

```
Debug why this napari layer isn't displaying correctly
```

### Documentation

```
Take screenshots of each step of this analysis workflow for documentation
```

## 🔧 Manual Configuration

If needed, manually edit `~/.claude.json`:

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

### Using Persistent Environment

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

## 🛠️ Management

```bash
# Check installation
napari-mcp-install list

# Update configuration
napari-mcp-install install claude-code --force

# Uninstall
napari-mcp-install uninstall claude-code
```

## ❌ Troubleshooting

### Configuration Not Loaded

!!! failure "Claude Code doesn't see napari tools"
    **Solutions:**

    1. Verify config file exists:
       ```bash
       cat ~/.claude.json
       ```

    2. Check JSON syntax:
       ```bash
       python -m json.tool < ~/.claude.json
       ```

    3. Reinstall:
       ```bash
       napari-mcp-install install claude-code --force
       ```

### Environment Issues

!!! failure "Module not found errors"
    **Solution:** Use persistent mode with your development environment:

    ```bash
    # Activate your environment
    source venv/bin/activate

    # Install napari-mcp
    pip install napari-mcp

    # Configure with persistent mode
    napari-mcp-install install claude-code --persistent
    ```

## 📚 Next Steps

- **[Quick Start](../getting-started/quickstart.md)** - Basic workflows
- **[API Reference](../api/index.md)** - All available tools
- **[Troubleshooting](../guides/troubleshooting.md)** - Common issues

---

→ [Back to Integrations Overview](index.md)

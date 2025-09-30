# Cursor IDE Integration

Setup guide for using napari MCP server with Cursor - AI-powered coding with full napari control.

## 🚀 Quick Setup

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Auto-configure Cursor (global)
napari-mcp-install cursor --global

# OR configure for specific project
napari-mcp-install cursor --project /path/to/project

# 3. Restart Cursor
```

## 📍 Configuration Location

### Global Installation (Recommended)

- **All platforms**: `~/.cursor/mcp.json`
- Available in all Cursor projects

### Project-Specific Installation

- **Location**: `.cursor/mcp.json` in project root
- Only available in that specific project
- Useful for project-specific napari configurations

## 💡 Why Use Cursor with napari?

- **AI-Enhanced Coding**: Next-level development experience
- **Project Awareness**: Understands your entire codebase
- **Smart Completions**: AI suggests napari operations
- **Workspace Integration**: Seamless file and project handling
- **Live Visualization**: See analysis results immediately

## 🧪 Testing

After restarting Cursor, test with:

```
Can you call session_information() to show napari details?
```

```
Open all TIFF files in the ./images/ directory in napari
```

## 💻 Development Workflows

### Image Analysis Projects

```
Create a processing pipeline that loads images from ./data/, applies filters, and saves results
```

```
Help me debug why this napari layer isn't rendering correctly
```

### Interactive Development

```
Load this microscopy image and help me find the optimal threshold for segmentation
```

```
Create a function that visualizes the intermediate steps of this analysis
```

### Documentation & Testing

```
Generate test data and visualize it in napari to verify my implementation
```

```
Take screenshots at each processing step for my documentation
```

## 🔧 Configuration Options

### Global Configuration

Best for most users:

```bash
napari-mcp-install cursor --global
```

Creates: `~/.cursor/mcp.json`

### Project-Specific Configuration

For project-specific setups:

```bash
cd /path/to/your/project
napari-mcp-install cursor --project .
```

Creates: `.cursor/mcp.json` in project directory

### Manual Configuration

Edit the appropriate config file:

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
# Check installation status
napari-mcp-install list

# Update global configuration
napari-mcp-install cursor --global --force

# Update project configuration
napari-mcp-install cursor --project . --force

# Uninstall
napari-mcp-install uninstall cursor
```

## ❌ Troubleshooting

### Cursor Doesn't See napari Tools

!!! failure "Tools not appearing"
    **Solutions:**

    1. **Verify installation:**
       ```bash
       napari-mcp-install list
       ```

    2. **Check which config is being used:**
       - Global: `~/.cursor/mcp.json`
       - Project: `.cursor/mcp.json`

    3. **Restart Cursor completely:**
       - Quit Cursor (don't just close windows)
       - Reopen Cursor

    4. **Reinstall:**
       ```bash
       napari-mcp-install cursor --global --force
       ```

### Project vs Global Confusion

!!! failure "Works in some projects but not others"
    **Explanation:** Project-specific configs override global configs.

    **Solution:** Choose one approach:

    - **Use global for all projects:**
      ```bash
      napari-mcp-install cursor --global
      # Remove project configs
      rm .cursor/mcp.json
      ```

    - **Use project-specific for this project:**
      ```bash
      napari-mcp-install cursor --project .
      ```

### Configuration File Not Found

!!! failure "Config file doesn't exist"
    **Solution:** The installer creates it automatically. For manual setup:

    ```bash
    # Global
    mkdir -p ~/.cursor

    # Project
    mkdir -p .cursor
    ```

## 🔐 Security Note

- Cursor runs MCP servers locally with your user permissions
- The server can execute Python code when asked
- Project-specific configs are committed to git - be cautious with sensitive settings

## 📚 Next Steps

- **[Quick Start](../getting-started/quickstart.md)** - Get started quickly
- **[API Reference](../api/index.md)** - Explore all tools
- **[Troubleshooting](../guides/troubleshooting.md)** - Solve issues

---

→ [Back to Integrations Overview](index.md)

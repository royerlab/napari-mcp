# Claude Desktop Integration

Complete setup guide for using napari MCP server with Claude Desktop - the most popular choice for AI-assisted microscopy analysis.

## 🚀 Quick Setup

### Automated Installation (Recommended)

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Auto-configure Claude Desktop
napari-mcp-install claude-desktop

# 3. Restart Claude Desktop
```

**That's it!** Claude Desktop will now have access to all napari MCP tools.

## 📍 Configuration Location

The installer automatically detects your platform and configures:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

## ⚙️ Installation Options

### Basic Installation

```bash
napari-mcp-install claude-desktop
```

### Advanced Options

```bash
# Preview changes without applying
napari-mcp-install claude-desktop --dry-run

# Use your Python environment instead of uv
napari-mcp-install claude-desktop --persistent

# Custom Python path
napari-mcp-install claude-desktop --python-path /path/to/python

# Force update without prompts
napari-mcp-install claude-desktop --force
```

## 🧪 Testing the Integration

After restarting Claude Desktop, test with:

### 1. Basic Connection Test
```
Can you call session_information() to show me details about my napari session?
```

**Expected**: Claude returns detailed information about the napari server, viewer state, and available tools.

### 2. Visual Test
```
Take a screenshot of my napari viewer
```

**Expected**: Claude returns a PNG image of the napari window.

### 3. Interactive Test
```
Create some random sample data and display it with a colormap of your choice
```

**Expected**: Napari window appears with colored image data.

## 💡 Example Workflows

### Basic Image Analysis

```
Load an image from ./data/sample.tif and apply a viridis colormap
```

```
Adjust the contrast and brightness to highlight the features
```

```
Take a screenshot and save it to ./output/processed.png
```

### Multi-dimensional Data

```
Load this 3D stack and switch to 3D view mode
```

```
Navigate to Z-slice 25 and take a screenshot
```

```
Create a maximum intensity projection of the stack
```

### Advanced Analysis

```
Execute this code to segment the image:
from skimage import filters
threshold = filters.threshold_otsu(viewer.layers[0].data)
binary = viewer.layers[0].data > threshold
viewer.add_labels(binary.astype(int), name='segmentation')
```

```
Install scikit-image and create a watershed segmentation
```

## 🔧 Manual Configuration (Optional)

If you prefer manual setup, add this to your config file:

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

### Using Persistent Python Environment

If napari-mcp is installed in your Python environment:

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

## 🛠️ Management

### Check Installation Status

```bash
napari-mcp-install list
```

### Update Configuration

```bash
napari-mcp-install claude-desktop --force
```

### Uninstall

```bash
napari-mcp-install uninstall claude-desktop
```

## ❌ Troubleshooting

### Claude Can't See napari Tools

!!! failure "Tools not appearing"
    **Solutions:**

    1. **Verify configuration exists:**
       ```bash
       napari-mcp-install list
       ```

    2. **Completely restart Claude Desktop:**
       - Quit Claude Desktop completely (⌘+Q on macOS)
       - Reopen Claude Desktop

    3. **Check config file syntax:**
       ```bash
       # macOS
       cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

       # Validate JSON
       python -m json.tool < claude_desktop_config.json
       ```

    4. **Reinstall:**
       ```bash
       napari-mcp-install claude-desktop --force
       ```

### Napari Window Doesn't Appear

!!! failure "No napari window"
    **Solutions:**

    - **On remote systems:** You may need X11 forwarding or offscreen mode
    - **Check Qt:** `python -c "from PyQt6.QtWidgets import QApplication; print('OK')"`
    - **Try offscreen mode:** Set `QT_QPA_PLATFORM=offscreen` in environment

### Configuration File Not Found

!!! failure "Can't find config file"
    **Solution:**

    The installer creates the directory and file automatically. If you're doing manual setup:

    ```bash
    # macOS
    mkdir -p ~/Library/Application\ Support/Claude

    # Linux
    mkdir -p ~/.config/Claude

    # Windows (PowerShell)
    New-Item -ItemType Directory -Force -Path "$env:APPDATA\Claude"
    ```

### Permission Errors

!!! failure "Permission denied"
    **Solution:**

    ```bash
    # Check permissions
    ls -la ~/Library/Application\ Support/Claude/

    # Fix permissions (macOS/Linux)
    chmod 644 ~/Library/Application\ Support/Claude/claude_desktop_config.json
    ```

## 🔐 Security Considerations

- Claude Desktop runs MCP servers locally with your user permissions
- The server can execute arbitrary Python code when you ask Claude to
- Only use with trusted code and in environments you control
- Never expose the server to untrusted networks

## 📚 Next Steps

- **[Quick Start Guide](../getting-started/quickstart.md)** - Get started with basic workflows
- **[API Reference](../api/index.md)** - Explore all available tools
- **[Troubleshooting](../guides/troubleshooting.md)** - Solve common issues

---

→ [Back to Integrations Overview](index.md)

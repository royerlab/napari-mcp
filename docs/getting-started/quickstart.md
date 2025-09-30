# Quick Start - 3 Minutes to AI-Controlled Napari

Get napari working with AI assistance in just 3 minutes using our automated CLI installer.

!!! success "What You'll Accomplish"
    By the end of this guide:

    - ✅ napari-mcp installed and configured
    - ✅ Your AI application automatically launches the server
    - ✅ Full control over a live napari viewer
    - ✅ Ready to load images and analyze data

## Step 1: Install the Package (30 seconds)

```bash
pip install napari-mcp
```

This installs:
- The napari MCP server
- CLI installer tool (`napari-mcp-install`)
- All required dependencies

## Step 2: Auto-Configure Your Application (1 minute)

The CLI installer automatically configures your AI application with the correct settings.

### For Claude Desktop

```bash
napari-mcp-install claude-desktop
```

### For Other Applications

```bash
# Claude Code CLI
napari-mcp-install claude-code

# Cursor IDE
napari-mcp-install cursor

# Cline in VS Code
napari-mcp-install cline-vscode

# See all options
napari-mcp-install --help
```

!!! tip "What the Installer Does"
    - Detects your application's config file location
    - Adds napari-mcp server configuration
    - Creates a backup of existing config
    - Validates Python environment
    - Shows you exactly what changed

### Installer Options

```bash
# Preview changes without applying
napari-mcp-install claude-desktop --dry-run

# Use your Python environment instead of uv
napari-mcp-install claude-desktop --persistent

# Install for all supported applications at once
napari-mcp-install all
```

## Step 3: Restart & Test (30 seconds)

1. **Restart your AI application** (completely quit and reopen)
2. **Test the connection** by asking your AI:

!!! example "Test Commands"
    === "Basic Connection"
        ```
        Can you call session_information() to tell me about my napari session?
        ```

        **Expected response:** Information about your napari viewer including system details, viewer state, and available features.

    === "Visual Test"
        ```
        Take a screenshot of my napari viewer
        ```

        **Expected response:** A PNG image of the napari window

    === "Interactive Test"
        ```
        Create some random sample data and display it with a viridis colormap
        ```

        **Expected response:** Napari window showing colored image data

## 🎉 Success! What's Next?

If the tests above work, you're ready to explore. Here are some immediate things to try:

### Basic Operations

=== "Image Loading"
    ```
    "Load an image from this path: /path/to/your/image.tif"
    "Apply a magma colormap and adjust the contrast"
    ```

=== "Annotations"
    ```
    "Create point annotations at coordinates [[100,100], [200,200], [150,150]]"
    "Add a labels layer from this segmentation file"
    ```

=== "Navigation"
    ```
    "Reset the view and zoom to 2x"
    "Switch to 3D display mode"
    "Navigate to Z-slice 15"
    ```

### Advanced Features

=== "Code Execution"
    ```
    "Execute this code to create synthetic data:
    import numpy as np
    data = np.random.random((512, 512))
    viewer.add_image(data, name='noise', colormap='gray')"
    ```

=== "Package Installation"
    ```
    "Install scikit-image and create a Gaussian filtered version of the current image"
    ```

=== "Analysis Workflows"
    ```
    "Take multiple screenshots while stepping through the Z-dimension"
    "Create an animation of this time-lapse data"
    ```

## 📚 Learning More

- **[User Guide](../guides/index.md)** - Learn common workflows and best practices
- **[API Reference](../api/index.md)** - Complete documentation of all available tools
- **[Integrations](../integrations/index.md)** - Application-specific guides

## ⚙️ Advanced Configuration

### Manual Configuration (Optional)

If you prefer to configure manually or need custom settings, the CLI installer creates this JSON:

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

**Config file locations:**
- **Claude Desktop (macOS)**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Desktop (Windows)**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Claude Desktop (Linux)**: `~/.config/Claude/claude_desktop_config.json`
- **Claude Code**: `~/.claude.json`
- **Cursor**: `~/.cursor/mcp.json` or `.cursor/mcp.json` (project-specific)

**→ See [Installation Guide](installation.md) for all config locations and formats**

### Using Your Python Environment

If you want to use an existing Python environment instead of uv:

```bash
# Install in your environment first
pip install napari-mcp

# Configure to use your Python
napari-mcp-install claude-desktop --persistent
```

This will use your Python interpreter directly: `python -m napari_mcp.server`

### External Viewer Mode (Plugin Bridge)

Prefer controlling an existing napari window?

1. Open napari → Plugins → **MCP Server Control**
2. Click **Start Server** (default port 9999)
3. Use the same CLI installer command (it will auto-detect and proxy to the external viewer)

## ❌ Common Issues

!!! failure "napari-mcp-install: command not found"
    **Solution:** The package wasn't installed correctly.
    ```bash
    # Reinstall
    pip install --force-reinstall napari-mcp

    # Verify
    napari-mcp-install --version
    ```

!!! failure "AI can't see napari tools"
    **Solutions:**

    1. Restart your AI application completely
    2. Check config was created: `napari-mcp-install list`
    3. Run with `--dry-run` to see what would be configured
    4. Check for error messages in the application's logs

!!! failure "Napari window doesn't appear"
    **Solutions:**

    - On remote systems: May need X11 forwarding or use offscreen mode
    - Check Qt installation: `python -c "from PyQt6.QtWidgets import QApplication; print('OK')"`
    - Try setting: `export QT_QPA_PLATFORM=offscreen` for headless mode

!!! failure "Permission errors"
    **Solution:**
    ```bash
    # Check file permissions
    napari-mcp-install list  # Shows config locations

    # Fix permissions if needed (macOS/Linux)
    chmod 644 ~/.config/Claude/claude_desktop_config.json
    ```

## 🛠️ Management Commands

```bash
# List all installations
napari-mcp-install list

# Uninstall from an application
napari-mcp-install uninstall claude-desktop

# Uninstall from all applications
napari-mcp-install uninstall all
```

## 🆘 Still Need Help?

- **[Troubleshooting Guide](../guides/troubleshooting.md)** - Comprehensive problem solving
- **[GitHub Issues](https://github.com/royerlab/napari-mcp/issues)** - Report bugs or ask questions
- **[Installation Guide](installation.md)** - More detailed setup instructions

---

**Congratulations! 🎊** You now have AI-controlled napari up and running. Time to explore the amazing possibilities of combining AI assistance with powerful microscopy analysis tools!

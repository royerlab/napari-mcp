# Quick Start - 2 Minutes to AI-Controlled Napari

Get napari working with AI assistance in just 2 minutes with zero installation!

!!! success "What You'll Accomplish"
    By the end of this guide:

    - ✅ Napari server running with AI control
    - ✅ Claude Desktop (or your AI) can control napari
    - ✅ Ready to load images and take screenshots

## Step 1: Run the Server (30 seconds)

=== "One-Line Command"
    ```bash
    curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py && \
    uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
      fastmcp run napari_mcp_server.py
    ```

=== "Step by Step"
    ```bash
    # Download the server file
    curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py

    # Run with all dependencies
    uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
      fastmcp run napari_mcp_server.py
    ```

!!! info "What This Does"
    - Downloads the napari MCP server (single Python file)
    - Automatically installs all required dependencies via `uv`
    - Starts the server with FastMCP protocol
    - Opens a napari viewer window

**Expected output:**
```
🚀 Starting FastMCP server...
📡 MCP server running on stdio
🔬 Napari viewer initialized
```

## Step 2: Configure Claude Desktop (1 minute)

1. **Open Claude Desktop settings** (⌘+, on macOS, Ctrl+, on Windows/Linux)

2. **Add this configuration:**
   ```json
   {
     "mcpServers": {
       "napari": {
         "command": "uv",
         "args": [
           "run",
           "--with", "Pillow",
           "--with", "PyQt6",
           "--with", "fastmcp",
           "--with", "imageio",
           "--with", "napari",
           "--with", "numpy",
           "--with", "qtpy",
           "fastmcp", "run",
           "/absolute/path/to/napari_mcp_server.py"
         ]
       }
     }
   }
   ```

3. **Update the path:** Replace `/absolute/path/to/napari_mcp_server.py` with your actual file location

   !!! tip "Finding the Absolute Path"
       ```bash
       # Get current directory + filename
       echo "$(pwd)/napari_mcp_server.py"
       ```

4. **Restart Claude Desktop**

## Step 3: Test the Connection (30 seconds)

Ask Claude Desktop:

!!! example "Test Commands"
    === "Basic Connection"
        ```
        Can you call session_information() to tell me about my napari session?
        ```

        **Expected response:** Information about your napari viewer including layers, camera settings, etc.

    === "Visual Test"
        ```
        Take a screenshot of my napari viewer
        ```

        **Expected response:** A PNG image of the napari window

    === "Interactive Test"
        ```
        Add some random sample data to napari and change the colormap to 'viridis'
        ```

## 🎉 Success! What's Next?

If the tests above work, you're ready to explore:

### Immediate Things to Try

=== "Basic Operations"
    ```
    "Load an image from this path: /path/to/your/image.tif"
    "Create annotation points at coordinates [[100,100], [200,200]]"
    "Reset the view and zoom to 2x"
    "Switch to 3D display mode"
    ```

=== "Advanced Features"
    ```
    "Execute this code: print(f'Napari version: {napari.__version__}')"
    "Install scikit-image and create a filtered version of the current image"
    "Take a screenshot and describe what you see in the napari viewer"
    ```

=== "Analysis Workflows"
    ```
    "Create a synthetic image with Gaussian noise and add it to napari"
    "Apply different colormaps to compare visualization of the data"
    "Navigate through different time points if this is a time series"
    ```

### Learning More

- **[User Guide](../guides/index.md)** - Learn common workflows and best practices
- **[API Reference](../api/index.md)** - Complete documentation of all available tools
- **[Integrations](../integrations/index.md)** - Setup with other AI assistants

## ❌ Common Issues

!!! failure "uv: command not found"
    **Solution:** Install uv first:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Restart your terminal
    ```

!!! failure "Claude can't see napari tools"
    **Solutions:**

    - Double-check the file path in your config is absolute
    - Restart Claude Desktop after making config changes
    - Verify the server is running (you should see terminal output)

!!! failure "Permission denied"
    **Solution:** Make the file executable:
    ```bash
    chmod +x napari_mcp_server.py
    ```

!!! failure "Napari window doesn't appear"
    **Solutions:**

    - Check if you're on a remote system (may need X11 forwarding)
    - Try setting: `export QT_QPA_PLATFORM=offscreen` for headless mode
    - Verify Qt dependencies are available

## 🆘 Still Need Help?

- **[Troubleshooting Guide](../guides/troubleshooting.md)** - Comprehensive problem solving
- **[GitHub Issues](https://github.com/royerlab/napari-mcp/issues)** - Report bugs or ask questions
- **[Zero Install Guide](zero-install.md)** - More detailed setup instructions

---

**Congratulations! 🎊** You now have AI-controlled napari up and running. Time to explore the amazing possibilities of combining AI assistance with powerful microscopy analysis tools!

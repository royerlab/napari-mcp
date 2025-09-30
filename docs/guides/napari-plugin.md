# Using napari-mcp as a napari Plugin

Learn how to use napari-mcp as a napari plugin for direct integration with your current napari session.

## Overview

napari-mcp offers **two integration modes**:

=== "🖥️ Standalone Server Mode (Default)"
    - MCP server creates and manages its own napari viewer
    - Best for: AI-driven workflows starting from scratch
    - Usage: Run via MCP client configuration (automatic)
    - The AI assistant controls a dedicated napari instance

=== "🔌 Plugin Mode"
    - MCP bridge server connects to your **current running napari session**
    - Best for: Integrating AI with existing workflows
    - Usage: Start napari → Open widget → Start bridge server
    - The AI assistant controls **your active napari session**

This guide covers **Plugin Mode** for direct integration with a running napari session.

---

## When to Use Plugin Mode

!!! tip "Ideal Use Cases"
    - **Working with existing data** - Already have napari open with layers loaded
    - **Interactive analysis** - Want to switch between manual and AI-assisted work
    - **Debugging workflows** - Need to inspect and modify data interactively
    - **Teaching/demos** - Show AI controlling a visible napari window
    - **Custom napari setups** - Have specific plugins or configurations loaded

!!! info "When to Use Standalone Mode"
    - **Automated processing** - Running batch analysis scripts
    - **Headless environments** - No display or GUI needed
    - **Fresh sessions** - Starting analysis from scratch
    - **Multiple viewers** - Need separate AI-controlled instances

---

## Installation

### Step 1: Install napari-mcp

```bash
pip install napari-mcp
```

napari-mcp is automatically registered as a napari plugin via the `napari.manifest` entry point.

### Step 2: Verify Plugin Installation

```bash
# Start napari
napari

# In napari: Plugins → napari-mcp: MCP Server Control
# You should see the widget in the plugins menu
```

---

## Quick Start

### 1. Start napari and Open the Widget

```bash
# Launch napari
napari

# Or with data
napari path/to/image.tif
```

In napari:
1. Go to **Plugins** menu
2. Select **napari-mcp: MCP Server Control**
3. The widget will appear as a docked panel

### 2. Start the Bridge Server

In the MCP Server Control widget:

1. **Configure port** (optional): Default is 9999
2. **Click "Start Server"** button
3. **Copy the connection URL**: `http://localhost:9999/mcp`

The widget displays:
- ✅ Server status (Running/Stopped)
- 🔌 Connection URL
- ⚙️ Port configuration
- 📝 Connection information

### 3. Configure Your AI Application

Run the standard installer:

```bash
# For Claude Desktop
napari-mcp-install claude-desktop

# For other applications
napari-mcp-install claude-code    # Claude Code
napari-mcp-install cursor         # Cursor IDE
napari-mcp-install cline-vscode   # Cline in VS Code
```

The installer automatically configures the AI app to detect and connect to your bridge server.

### 4. Test the Connection

Restart your AI application and try:

```
"Can you call session_information() to show my napari session details?"
```

The AI assistant should report information about **your current napari session**, including any layers you already have loaded!

---

## Using Plugin Mode

### Loading Data First

You can load data into napari **before** starting the bridge server:

```python
# Start napari with data
napari path/to/cells.tif

# Or load in napari GUI
# File → Open Files → Select your image

# Then start the MCP Server Control widget
# Plugins → napari-mcp: MCP Server Control → Start Server
```

Now ask your AI assistant:

```
"List the current layers and apply a better colormap to the image"
```

### Switching Between Manual and AI Control

The beauty of plugin mode is seamless integration:

1. **Manual work**: Load data, adjust view, add annotations
2. **AI assistance**: Start server, ask AI to process or analyze
3. **Manual refinement**: Stop server, manually adjust results
4. **Repeat**: Restart server for more AI help

### Working with Existing Layers

```
# You have layers: "raw_image", "segmentation", "measurements"

Ask AI: "Take a screenshot showing all three layers with the segmentation in red"

Ask AI: "Hide the measurements layer and zoom in on the center"

Ask AI: "Execute code to calculate the mean intensity of raw_image inside segmentation masks"
```

---

## Widget Interface

### Server Status

- **🔴 Server: Stopped** - Bridge server is not running
- **🟢 Server: Running (Port 9999)** - Bridge server is active on port 9999

### Configuration

- **Port**: TCP port for the bridge server (default: 9999)
  - Range: 1024-65535
  - Change only if port is already in use
  - **Important**: If you change the port, ensure your AI app uses the same port

### Control Buttons

- **Start Server** (Green) - Start the MCP bridge server
  - Exposes current viewer to MCP clients
  - Enables AI assistant control

- **Stop Server** (Red) - Stop the MCP bridge server
  - AI assistants can no longer connect
  - Your napari session remains open

### Connection Information

When server is running:
```
Server running on port 9999

Connection URL: http://localhost:9999/mcp

Clients will auto-detect this napari-mcp bridge. If you
customize the port, ensure your LLM agent is configured to
use the same URL.
```

---

## Custom Port Configuration

### When to Change the Port

Default port 9999 should work for most users. Change it if:

- Port 9999 is already in use by another application
- Running multiple napari instances with separate bridge servers
- Corporate firewall blocks default port

### Changing the Port

1. **In the widget**: Change the port number before starting the server
2. **Configure AI app** with custom port:

#### Manual Configuration

If you need to specify a custom port, edit your AI app config:

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "env": {
        "NAPARI_MCP_BRIDGE_PORT": "8888"
      }
    }
  }
}
```

**Other apps**: Similar pattern with `NAPARI_MCP_BRIDGE_PORT` environment variable.

---

## Architecture

### How Plugin Mode Works

```
┌─────────────────────────────────────┐
│   Your napari Session (GUI)         │
│   ├─ Image layers                   │
│   ├─ Labels, points, etc.           │
│   └─ Your existing workflow         │
└─────────────┬───────────────────────┘
              │
              │ Qt signals/slots
              │ (main thread)
              ↓
┌─────────────────────────────────────┐
│   MCP Server Control Widget         │
│   (Qt Widget - napari plugin)       │
└─────────────┬───────────────────────┘
              │
              │ Starts/stops
              ↓
┌─────────────────────────────────────┐
│   NapariBridgeServer                │
│   - HTTP server on port 9999        │
│   - FastMCP protocol handler        │
│   - Qt bridge for thread safety     │
└─────────────┬───────────────────────┘
              │
              │ HTTP + MCP protocol
              ↓
┌─────────────────────────────────────┐
│   AI Assistant (Claude, etc.)       │
│   - Detects bridge server           │
│   - Calls MCP tools                 │
│   - Controls your napari session    │
└─────────────────────────────────────┘
```

### Key Components

- **MCPControlWidget** (`widget.py`) - Qt widget UI
- **NapariBridgeServer** (`bridge_server.py`) - HTTP/MCP server
- **QtBridge** - Thread-safe operations between server and GUI
- **napari.yaml** - Plugin manifest

### Thread Safety

All napari GUI operations from the bridge server are executed on the main Qt thread via signal/slot mechanism, ensuring thread safety.

---

## Use Cases & Examples

### Example 1: Analyzing Pre-loaded Data

```bash
# 1. Start napari with your data
napari microscopy_data/*.tif

# 2. Open MCP Server Control widget
#    Plugins → napari-mcp: MCP Server Control

# 3. Start server

# 4. Ask AI:
"Calculate statistics for each channel and create a summary plot"
```

### Example 2: Iterative Segmentation

```bash
# 1. Load image in napari
# 2. Start bridge server
# 3. Ask AI: "Segment the cells using Otsu thresholding"
# 4. Inspect results manually
# 5. Ask AI: "The threshold is too high, try a lower value"
# 6. Iterate until satisfied
```

### Example 3: Teaching/Demonstration

```bash
# During a presentation:
# 1. Project napari window on screen
# 2. Start bridge server
# 3. Have AI assistant perform analysis in real-time
# 4. Audience sees napari respond to natural language commands
```

### Example 4: Custom Plugin Integration

```python
# You have other napari plugins loaded
# napari with specific configurations
napari --reset  # Or your custom setup

# Start bridge server
# Plugins → napari-mcp: MCP Server Control

# AI can now work with your custom setup
# "Use the annotator plugin to mark these regions"
```

---

## Troubleshooting

### Widget Not Appearing in Plugins Menu

**Problem**: Can't find "napari-mcp: MCP Server Control" in Plugins menu

**Solutions**:
```bash
# 1. Verify installation
pip list | grep napari-mcp

# 2. Check napari can see the plugin
napari --info
# Look for napari-mcp in the plugins list

# 3. Reinstall
pip uninstall napari-mcp
pip install napari-mcp

# 4. Check for plugin conflicts
napari --plugin-info napari-mcp
```

### Server Won't Start

**Problem**: Clicking "Start Server" doesn't work

**Solutions**:

- **Port in use**: Try a different port in widget settings
- **Check logs**: Look for errors in terminal where you started napari
- **Permissions**: Ensure you have permission to bind to the port

```bash
# Check if port is in use
lsof -i :9999  # macOS/Linux
netstat -ano | findstr :9999  # Windows
```

### AI Can't Connect to Bridge Server

**Problem**: AI assistant doesn't see the napari session

**Solutions**:

1. **Verify server is running**: Check widget shows "Server: Running"
2. **Check port configuration**: Ensure AI app uses correct port
3. **Test manually**:
   ```bash
   curl http://localhost:9999/mcp
   # Should return MCP server info
   ```
4. **Restart AI application**: Server must be running before AI app starts
5. **Check firewall**: Ensure localhost connections are allowed

### Operations Not Working

**Problem**: AI tries to control napari but nothing happens

**Solutions**:

- **Check napari is responding**: Try manual operations first
- **Look for errors**: Check terminal output from napari
- **Thread issues**: Restart both napari and bridge server
- **Qt platform**: Ensure proper Qt platform plugin is loaded

---

## Comparison: Plugin vs Standalone

| Feature | Plugin Mode | Standalone Mode |
|---------|-------------|-----------------|
| **Viewer Creation** | You start napari manually | MCP server creates viewer |
| **Existing Data** | ✅ Work with loaded data | ❌ Start from scratch |
| **Visibility** | ✅ See napari GUI | ⚙️ Optional (can be headless) |
| **Interactive Use** | ✅ Switch between manual/AI | ❌ Primarily AI-controlled |
| **Setup** | Start napari + widget | Automatic via MCP config |
| **Port Config** | Set in widget | Environment variable |
| **Use Case** | Interactive analysis | Automated workflows |

---

## Advanced Configuration

### Programmatic Widget Creation

You can create the widget programmatically in scripts:

```python
import napari
from napari_mcp.widget import MCPControlWidget

# Create viewer
viewer = napari.Viewer()

# Add data
viewer.add_image(data, name="my_image")

# Create and add widget
widget = MCPControlWidget(viewer, port=9999)
viewer.window.add_dock_widget(widget, name="MCP Control")

# Start server programmatically
widget._start_server()

# Now AI can connect to this specific viewer
napari.run()
```

### Multiple Viewers

Run multiple napari instances with different bridge ports:

```python
# Viewer 1 on port 9999
napari  # Start, use widget with port 9999

# Viewer 2 on port 9998
napari  # Start, use widget with port 9998

# Configure AI app to connect to specific viewer
# via NAPARI_MCP_BRIDGE_PORT environment variable
```

---

## Security Considerations

!!! warning "Local Network Only"
    The bridge server binds to `127.0.0.1` (localhost) and is only accessible from your computer. This is by design for security.

!!! danger "Code Execution"
    Like standalone mode, plugin mode allows `execute_code()` which can run arbitrary Python code in your napari environment. Only use with trusted AI assistants.

**Security Best Practices**:
- Never expose bridge server to public networks
- Only run with trusted AI assistants
- Review code before allowing AI to execute
- Stop server when not in use

---

## Next Steps

- **[Quick Start Guide](../getting-started/quickstart.md)** - Basic setup
- **[API Reference](../api/index.md)** - Available MCP tools
- **[Python Integration](../integrations/python.md)** - Custom scripts
- **[Troubleshooting](troubleshooting.md)** - Common issues

---

**Ready to integrate AI with your napari workflows?** Start napari, open the widget, and start exploring! 🔬✨
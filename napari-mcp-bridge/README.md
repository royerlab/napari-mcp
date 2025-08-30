# napari-mcp-bridge

A napari plugin that exposes the current viewer as an MCP (Model Context Protocol) server, allowing AI assistants to control your existing napari session.

## Installation

Install the plugin in development mode:

```bash
cd napari-mcp-bridge
pip install -e .
```

## Usage

### 1. Start napari and load the plugin

```python
import napari

viewer = napari.Viewer()
# Open the plugin from Plugins menu -> MCP Server Control
```

Or programmatically:

```python
import napari

viewer = napari.Viewer()
viewer.window.add_plugin_dock_widget('napari-mcp-bridge', 'MCP Server Control')
```

### 2. Start the MCP server

1. In the MCP Server Control widget, click "Start Server"
2. The server will run on port 9999 (configurable)
3. The widget shows the connection status and URL

### 3. Connect from napari-mcp

When using the main napari-mcp server, it will automatically detect the external viewer:

```bash
# Set environment variable to prefer external viewer
export NAPARI_MCP_USE_EXTERNAL=true

# Optional: Set custom port if not using default 9999
export NAPARI_MCP_BRIDGE_PORT=9999

napari-mcp

# Or use programmatically
# The init_viewer() function will detect and use the external viewer
```

## How it works

The plugin creates an HTTP-based MCP server that exposes the current napari viewer. The main napari-mcp server can detect this "bridge" server and use it instead of creating a new viewer.

This allows you to:
- Use your existing napari session with all loaded data
- Keep your manual adjustments and view settings
- Switch between manual and AI-assisted control seamlessly

## Features

- Start/stop MCP server with a button click
- Configurable port (default: 9999)
- Status indicator showing server state
- Connection information display
- Automatic cleanup on widget close

## Architecture

The plugin consists of:
- **widget.py**: Qt-based dock widget for server control
- **server.py**: FastMCP server implementation that wraps the viewer
- **napari.yaml**: Plugin manifest for napari integration

The server exposes the same tools as the main napari-mcp server but operates on the plugin's viewer instance instead of creating a new one.

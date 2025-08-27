# Napari MCP Server

[![Tests](https://github.com/USERNAME/napari-mcp/workflows/Tests/badge.svg)](https://github.com/USERNAME/napari-mcp/actions)
[![Coverage](https://codecov.io/gh/USERNAME/napari-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/napari-mcp)
[![PyPI version](https://badge.fury.io/py/napari-mcp.svg)](https://badge.fury.io/py/napari-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP server for remote control of napari viewers via Model Context Protocol (MCP). Perfect for AI-assisted analysis with Claude Desktop.

## 🚀 Quick Start

```bash
# Install
pip install -e .

# Run MCP server
napari-mcp
```

Add to Claude Desktop config:
```json
{
  "mcpServers": {
    "napari": {
      "command": "python",
      "args": ["-m", "napari_mcp_server"]
    }
  }
}
```

## 🔧 Installation

```bash
# With pip
pip install -e .

# With uv (recommended)
uv pip install -e .

# Include test dependencies
pip install -e ".[test]"
```

**Requirements:**
- Python 3.10+
- napari 0.5.5+  
- Qt Backend (PyQt6 installed automatically)

## 🛠 Available MCP Tools

### Session Information
- `session_information()` - Get comprehensive session info including viewer state, layers, system details

### Layer Management
- `list_layers()` - Get all layers and their properties
- `add_image(path, name?, colormap?, blending?, channel_axis?)` - Add image layer from file
- `add_labels(path, name?)` - Add segmentation labels from file  
- `add_points(points, name?, size?)` - Add point annotations
- `remove_layer(name)` - Remove layer by name
- `rename_layer(old_name, new_name)` - Rename layer
- `set_layer_properties(...)` - Modify layer visibility, opacity, colormap, etc.
- `reorder_layer(name, index?|before?|after?)` - Change layer order
- `set_active_layer(name)` - Set selected layer

### Viewer Controls
- `init_viewer(title?, width?, height?)` - Create or configure viewer
- `close_viewer()` - Close viewer window
- `start_gui(focus?)` - Start GUI event loop
- `stop_gui()` - Stop GUI event loop  
- `is_gui_running()` - Check GUI status
- `reset_view()` - Reset camera to fit all data
- `set_zoom(zoom)` - Set zoom level
- `set_camera(center?, zoom?, angle?)` - Position camera
- `set_ndisplay(2|3)` - Switch between 2D/3D display
- `set_dims_current_step(axis, value)` - Navigate dimensions (time, Z-stack)
- `set_grid(enabled?)` - Enable/disable grid view

### Utilities  
- `screenshot(canvas_only?)` - Capture PNG image as base64
- `execute_code(code)` - Run Python with access to viewer, napari, numpy
- `install_packages(packages, ...)` - Install Python packages dynamically

## ⚠️ **IMPORTANT SECURITY WARNING**

**This server includes powerful tools that allow arbitrary code execution:**

- **`execute_code()`** - Runs any Python code in the server environment
- **`install_packages()`** - Installs any Python package via pip

**Security Implications:**
- ✅ **Safe for local development** with trusted AI assistants like Claude
- ❌ **NEVER expose to untrusted networks** or public internet
- ❌ **Do not use in production environments** without proper sandboxing
- ❌ **Can access your filesystem, network, and install malware**

**Recommended Usage:**
- Use only on `localhost` connections
- Run in isolated virtual environments
- Monitor all code execution requests
- Consider disabling these tools for sensitive environments

## 🧪 Testing

```bash
# Install test dependencies
uv pip install -e ".[test]"

# Run all tests (96% coverage)
uv run pytest

# Run with coverage report
uv run pytest --cov=napari_mcp_server --cov-report=html
```

## 💡 Usage Examples

### Basic Layer Control
```python
# Ask Claude:
# "Create a new napari viewer and add a random image"
# "Take a screenshot of the current view"
# "What layers are currently loaded?"
```

### Image Analysis Workflow
```python
# Ask Claude:
# "Load this image file: /path/to/data.tif"
# "Add some annotation points at interesting features" 
# "Execute this analysis code: np.mean(viewer.layers[0].data)"
```

### Automated Visualization
```python
# Ask Claude:
# "Set up a nice colormap for the image layer"
# "Adjust the camera to focus on the center region"
# "Switch to 3D view and rotate the camera"
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Development Setup
1. Fork the repository
2. Install development dependencies: `uv pip install -e ".[test]"`  
3. Install pre-commit hooks: `pre-commit install`
4. Test your changes: `uv run pytest`
5. Submit pull request

For security-related contributions, please review our [Security Policy](SECURITY.md).

## 🐛 Troubleshooting

### Server Won't Start
- Check if port is already in use: `lsof -i :3000`
- Try different port or kill existing process

### Claude Desktop Connection Issues  
- Restart Claude Desktop after config changes
- Verify JSON config syntax is valid
- Check Python path in config is correct

### Performance Issues
- Large images may slow screenshot transfers
- Use localhost connections only
- Monitor memory usage for long sessions

## 📄 License

[Add your license information here]

## 🙋 Support

- **Issues**: Report bugs and request features on GitHub
- **Documentation**: See examples in the repository
- **MCP Protocol**: [Model Context Protocol docs](https://modelcontextprotocol.io/)
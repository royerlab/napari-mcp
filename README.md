# Napari MCP Server

[![Tests](https://github.com/royerlab/napari-mcp/workflows/Tests/badge.svg)](https://github.com/royerlab/napari-mcp/actions)
[![codecov](https://codecov.io/gh/royerlab/napari-mcp/graph/badge.svg?token=E1WY58V877)](https://codecov.io/gh/royerlab/napari-mcp)
[![PyPI version](https://badge.fury.io/py/napari-mcp.svg)](https://badge.fury.io/py/napari-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP server for remote control of napari viewers via Model Context Protocol (MCP). Perfect for AI-assisted analysis with Claude Desktop.

## 🚀 Quick Start

### Option 1: Install from PyPI (Recommended)
```bash
# Install the package
pip install napari-mcp

# Run the server (stdio transport; perfect for Claude Desktop)
napari-mcp
```

### Option 2: Zero-Install with uv
```bash
# Run the latest published version without installing
uv run --with napari-mcp napari-mcp
```

### Option 3: Development Install
```bash
# Clone and install
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp
uv pip install -e .

# Run the server
napari-mcp
```

**Claude Desktop config (Installed or Zero-Install):**
```json
{
  "mcpServers": {
    "napari": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"]
    }
  }
}
```

**Why uv run?**
- ✅ **Zero install** - No virtualenv or pip install required
- ✅ **Always up-to-date** - Pulls the latest published version
- ✅ **Reproducible** - uv caches and pins environments per command

## 🤖 Multi-LLM Support

Works with multiple AI assistants and IDEs:

| Application | Status | Setup Method |
|-------------|--------|--------------|
| **Claude Desktop** | ✅ Full Support | Manual config (recommended) |
| **Claude Code** | ✅ Full Support | `fastmcp install claude-code` |
| **Cursor** | ✅ Full Support | `fastmcp install cursor` |
| **ChatGPT** | 🟡 Limited | Remote deployment only |

**→ See [LLM_INTEGRATIONS.md](LLM_INTEGRATIONS.md) for complete setup guides**

## 🔧 Alternative Installation Methods

### Traditional Package Installation

```bash
# Clone and install
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp
pip install -e .

# Run
napari-mcp
```



### Development Installation

```bash
# With uv (recommended for development)
uv pip install -e ".[test,dev]"

# With pip
pip install -e ".[test,dev]"
```

**Requirements:**
- Python 3.10+
- napari 0.5.5+
- Qt Backend (PyQt6 installed automatically)

## 🛠 Available MCP Tools

### Session Information
- `session_information()` - Get comprehensive session info including viewer state, layers, system details
- `detect_viewers()` - Detect available local/external viewers

### Layer Management
- `list_layers()` - Get all layers and their properties
- `add_image(path, name?, colormap?, blending?, channel_axis?)` - Add image layer from file
- `add_labels(path, name?)` - Add segmentation labels from file
- `add_points(points, name?, size?)` - Add point annotations
- `remove_layer(name)` - Remove layer by name
- `set_layer_properties(...)` - Modify layer visibility, opacity, colormap, etc.
- `reorder_layer(name, index?|before?|after?)` - Change layer order
- `set_active_layer(name)` - Set selected layer

### Viewer Controls
- `init_viewer(title?, width?, height?)` - Create/configure viewer and start GUI
- `close_viewer()` - Close viewer window (also stops GUI)
- `reset_view()` - Reset camera to fit all data
- `set_camera(center?, zoom?, angle?)` - Position camera
- `set_ndisplay(2|3)` - Switch between 2D/3D display
- `set_dims_current_step(axis, value)` - Navigate dimensions (time, Z-stack)
- `set_grid(enabled?)` - Enable/disable grid view

### Utilities
- `screenshot(canvas_only?)` - Capture PNG image as base64
- `execute_code(code)` - Run Python with access to viewer, napari, numpy
- `install_packages(packages, ...)` - Install Python packages dynamically
- `read_output(output_id, start?, end?)` - Retrieve full/stdout/stderr from previous calls

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
- Only use with trusted AI assistants

## 📖 Usage Examples

### Basic Layer Operations

**Add and manipulate images:**
```
Ask Claude: "Add a sample image to napari and set its colormap to 'viridis'"
```

**Work with annotations:**
```
Ask Claude: "Create some point annotations at coordinates [[100,100], [200,200]] and make them size 10"
```

### Advanced Analysis

**Execute custom code:**
```
Ask Claude: "Execute this code to create a synthetic image:
import numpy as np
data = np.random.random((512, 512))
viewer.add_image(data, name='random_noise')"
```

**Install packages on-demand:**
```
Ask Claude: "Install scipy and create a Gaussian filtered version of the current image"
```

### View Management

**Control the camera:**
```
Ask Claude: "Reset the view, then zoom to 2x and center on coordinates [256, 256]"
```

**Switch display modes:**
```
Ask Claude: "Switch to 3D display mode and take a screenshot"
```

## 🧪 Testing

```bash
# Fast suite (skips GUI)
pytest -q -m "not realgui"

# Full suite with coverage (skips GUI)
pytest --cov=src --cov-report=html tests/ -m "not realgui"

# Include GUI tests (requires a display)
pytest -m realgui
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run pre-commit hooks: `pre-commit run --all-files`
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Development setup:**
```bash
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp
uv pip install -e ".[test,dev]"
pre-commit install
```

## 📋 Architecture

The server architecture consists of:

- **FastMCP Server**: Handles MCP protocol communication
- **Napari Integration**: Manages viewer lifecycle and operations
- **Qt Event Loop**: Asynchronous GUI event processing
- **Tool Layer**: Exposes napari functionality as MCP tools
- **External Bridge (optional)**: Auto-detects and proxies to an existing napari viewer started from the plugin widget

Key design decisions:
- **Thread-safe**: All napari operations are serialized through locks
- **Non-blocking**: Qt event loop runs asynchronously
- **Stateful**: Maintains viewer state across tool calls
- **Extensible**: Easy to add new tools and functionality

## 📚 Resources

- **[Quick Start](docs/getting-started/quickstart.md)** - Get running in 2 minutes
- **[LLM_INTEGRATIONS.md](LLM_INTEGRATIONS.md)** - Complete guide for Claude Desktop, Claude Code, Cursor, ChatGPT
- **[Model Context Protocol](https://modelcontextprotocol.io/)** - MCP specification
- **[FastMCP](https://github.com/jlowin/fastmcp)** - Python MCP framework
- **[napari](https://napari.org/)** - Multi-dimensional image viewer
- **[Claude Desktop](https://claude.ai/download)** - AI assistant with MCP support

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [napari team](https://napari.org/team/) for the excellent imaging platform
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework
- [Anthropic](https://www.anthropic.com/) for Claude and MCP development
- [astral-sh](https://astral.sh/) for uv dependency management

---

**Built with ❤️ for the microscopy and AI communities**

# Napari MCP Server

[![Tests](https://github.com/royerlab/napari-mcp/workflows/Tests/badge.svg)](https://github.com/royerlab/napari-mcp/actions)
[![codecov](https://codecov.io/gh/royerlab/napari-mcp/graph/badge.svg?token=E1WY58V877)](https://codecov.io/gh/royerlab/napari-mcp)
[![PyPI version](https://badge.fury.io/py/napari-mcp.svg)](https://badge.fury.io/py/napari-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

MCP server for remote control of napari viewers via Model Context Protocol (MCP). Perfect for AI-assisted microscopy analysis with Claude Desktop and other LLM applications.

https://github.com/user-attachments/assets/d261674c-9875-4671-8c60-a7f49d6f1b84

## 🚀 Quick Start (3 Steps)

### 1. Install the Package

```bash
pip install napari-mcp
```

### 2. Auto-Configure Your AI Application

```bash
# For Claude Desktop
napari-mcp-install install claude-desktop

# Include a napari GUI backend in the uv environment
napari-mcp-install install claude-desktop --backend pyqt6

# For other applications (Claude Code, Cursor, Cline, etc.)
napari-mcp-install install --help  # See all options
```

### 3. Restart Your Application & Start Using

Restart your AI app and you're ready! Try asking:
```
"Can you call session_information() to show my napari session details?"
```

**→ See [Full Documentation](https://royerlab.github.io/napari-mcp/) for detailed guides**

## 🔌 Using as a napari Plugin

napari-mcp can also be used as a **napari plugin** for direct integration with a running napari session:

1. **Start napari** normally: `napari`
2. **Open the widget**: Plugins → napari-mcp: MCP Server Control
3. **Click "Start Server"** to expose your current session to AI assistants
4. **Connect your AI app** using the standard installer: `napari-mcp-install install <app>`

This mode enables AI assistants to control your **current napari session** rather than starting a new viewer. Perfect for integrating with existing workflows!

**→ See [Plugin Guide](https://royerlab.github.io/napari-mcp/guides/napari-plugin/) for detailed instructions**

## 🎯 What Can You Do?

### Basic Image Analysis
```
"Load the image from ./data/sample.tif and apply a viridis colormap"
"Create point annotations at coordinates [[100,100], [200,200]]"
"Take a screenshot and save it"
```

### Advanced Workflows
```
"Execute this code to create a filtered version:
from scipy import ndimage
filtered = ndimage.gaussian_filter(viewer.layers[0].data, sigma=2)
viewer.add_image(filtered, name='filtered')"

"Install scikit-image and segment the cells in this microscopy image"
```

### 3D/4D Navigation
```
"Switch to 3D display mode"
"Navigate to time point 5, Z-slice 10"
"Create a rotating animation of this volume"
```

### Automated Workflows
Want to automate image processing with Python scripts? Use any LLM (OpenAI, Anthropic, etc.) with napari MCP:

**→ See [Python Integration Examples](docs/examples/README.md)** for batch processing and workflow automation

## 🤖 Supported AI Applications

| Application | Command | Status |
|-------------|---------|--------|
| **Claude Desktop** | `napari-mcp-install install claude-desktop` | ✅ Full Support |
| **Claude Code** | `napari-mcp-install install claude-code` | ✅ Full Support |
| **Cursor IDE** | `napari-mcp-install install cursor` | ✅ Full Support |
| **Cline (VS Code)** | `napari-mcp-install install cline-vscode` | ✅ Full Support |
| **Cline (Cursor)** | `napari-mcp-install install cline-cursor` | ✅ Full Support |
| **Gemini CLI** | `napari-mcp-install install gemini` | ✅ Full Support |
| **Codex CLI** | `napari-mcp-install install codex` | ✅ Full Support |

**→ See [Integration Guides](docs/integrations/index.md) for application-specific instructions**

## 🛠 Available MCP Tools

The server exposes 16 tools for complete napari control:

### Core Functions
- **Session Management**: `init_viewer`, `close_viewer`, `session_information`
- **Layer Operations**: `add_layer`, `list_layers`, `get_layer`, `remove_layer`, `set_layer_properties`, `reorder_layer`, `apply_to_layers`, `save_layer_data`
- **Viewer Controls**: `configure_viewer`
- **Utilities**: `screenshot`, `execute_code`, `install_packages`, `read_output`

## ⚠️ Security Notice

!!! warning "Code Execution Capabilities"
    This server includes powerful tools that allow arbitrary code execution:

    - **`execute_code()`** - Runs Python code in the server environment
    - **`install_packages()`** - Installs packages via pip

    The bridge server binds to `127.0.0.1` (localhost only) with no authentication.
    Any local process can invoke these tools.

    **Use only with trusted AI assistants on local networks.**
    Never expose to public internet without proper sandboxing.

## 📖 Documentation

- **[Quick Start Guide](docs/getting-started/quickstart.md)** - Get running in 3 minutes
- **[Installation Options](docs/getting-started/installation.md)** - Advanced installation methods
- **[Integration Guides](docs/integrations/index.md)** - Setup for specific AI applications
- **[Python Examples](docs/examples/README.md)** - Automate workflows with custom scripts
- **[Troubleshooting](docs/guides/troubleshooting.md)** - Common issues and solutions
- **[API Reference](https://royerlab.github.io/napari-mcp/api/)** - Complete tool documentation

## 🧪 Development Setup

```bash

# Clone repository
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest -m "not realgui"  # Skip GUI tests
pytest --cov=src --cov-report=html  # With coverage
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run pre-commit hooks: `pre-commit run --all-files`
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📋 Architecture

- **`state.py`** — `ServerState` holding all mutable state (viewer, locks, execution namespace)
- **`server.py`** — `create_server(state)` factory; tools defined as closures over state
- **`qt_helpers.py`** — Qt application and viewer lifecycle management
- **`output.py`** — Output truncation utility
- **`bridge_server.py`** — Plugin bridge server (overrides 3 tools for Qt thread safety)
- **`viewer_protocol.py`** — `ViewerProtocol` for typed viewer backends
- **`cli/`** — `napari-mcp-install` CLI for configuring AI applications

Key features:
- **Thread-safe**: All napari operations are serialized
- **Non-blocking**: Qt event loop runs asynchronously
- **Stateful**: Maintains viewer state across tool calls
- **Extensible**: Easy to add new tools

## 📚 Resources

- **[napari](https://napari.org/)** - Multi-dimensional image viewer
- **[Model Context Protocol](https://modelcontextprotocol.io/)** - MCP specification
- **[FastMCP](https://github.com/jlowin/fastmcp)** - Python MCP framework
- **[Claude Desktop](https://claude.ai/download)** - AI assistant with MCP support

## 📄 License

BSD-3-Clause License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [napari team](https://napari.org/) for the excellent imaging platform
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework
- [Anthropic](https://www.anthropic.com/) for Claude and MCP development
- [astral-sh](https://astral.sh/) for uv dependency management

---

**Built with ❤️ for the microscopy and AI communities**

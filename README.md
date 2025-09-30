# Napari MCP Server

[![Tests](https://github.com/royerlab/napari-mcp/workflows/Tests/badge.svg)](https://github.com/royerlab/napari-mcp/actions)
[![codecov](https://codecov.io/gh/royerlab/napari-mcp/graph/badge.svg?token=E1WY58V877)](https://codecov.io/gh/royerlab/napari-mcp)
[![PyPI version](https://badge.fury.io/py/napari-mcp.svg)](https://badge.fury.io/py/napari-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

MCP server for remote control of napari viewers via Model Context Protocol (MCP). Perfect for AI-assisted microscopy analysis with Claude Desktop and other LLM applications.

## 🚀 Quick Start (3 Steps)

### 1. Install the Package

```bash
pip install napari-mcp
```

### 2. Auto-Configure Your AI Application

```bash
# For Claude Desktop
napari-mcp-install claude-desktop

# For other applications (Claude Code, Cursor, Cline, etc.)
napari-mcp-install --help  # See all options
```

### 3. Restart Your Application & Start Using

Restart your AI app and you're ready! Try asking:
```
"Can you call session_information() to show my napari session details?"
```

**→ See [Full Documentation](https://napari-mcp.readthedocs.io) for detailed guides**

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
| **Claude Desktop** | `napari-mcp-install claude-desktop` | ✅ Full Support |
| **Claude Code** | `napari-mcp-install claude-code` | ✅ Full Support |
| **Cursor IDE** | `napari-mcp-install cursor` | ✅ Full Support |
| **Cline (VS Code)** | `napari-mcp-install cline-vscode` | ✅ Full Support |
| **Cline (Cursor)** | `napari-mcp-install cline-cursor` | ✅ Full Support |
| **Gemini CLI** | `napari-mcp-install gemini` | ✅ Full Support |
| **Codex CLI** | `napari-mcp-install codex` | ✅ Full Support |

**→ See [Integration Guides](docs/integrations/index.md) for application-specific instructions**

## 🛠 Available MCP Tools

The server exposes 20+ tools for complete napari control:

### Core Functions
- **Session Management**: `detect_viewers`, `init_viewer`, `close_viewer`, `session_information`
- **Layer Operations**: `add_image`, `add_labels`, `add_points`, `list_layers`, `remove_layer`
- **Viewer Controls**: `set_camera`, `reset_view`, `set_ndisplay`, `set_dims_current_step`
- **Utilities**: `screenshot`, `execute_code`, `install_packages`

**→ See [API Reference](docs/api/index.md) for complete documentation**

## ⚠️ Security Notice

!!! warning "Code Execution Capabilities"
    This server includes powerful tools that allow arbitrary code execution:

    - **`execute_code()`** - Runs Python code in the server environment
    - **`install_packages()`** - Installs packages via pip

    **Use only with trusted AI assistants on local networks.**
    Never expose to public internet without proper sandboxing.

## 📖 Documentation

- **[Quick Start Guide](docs/getting-started/quickstart.md)** - Get running in 3 minutes
- **[Installation Options](docs/getting-started/installation.md)** - Advanced installation methods
- **[Integration Guides](docs/integrations/index.md)** - Setup for specific AI applications
- **[Python Examples](docs/examples/README.md)** - Automate workflows with custom scripts
- **[Troubleshooting](docs/guides/troubleshooting.md)** - Common issues and solutions
- **[API Reference](docs/api/index.md)** - Complete tool documentation

## 🧪 Development Setup

```bash
# Clone repository
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp

# Install with development dependencies
pip install -e ".[test,dev]"

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

- **FastMCP Server**: Handles MCP protocol communication
- **Napari Integration**: Manages viewer lifecycle and operations
- **Qt Event Loop**: Asynchronous GUI event processing
- **Tool Layer**: Exposes napari functionality as MCP tools
- **External Bridge**: Optional connection to existing napari viewers

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

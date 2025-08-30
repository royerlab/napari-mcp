# Napari MCP Server

**MCP server for remote control of napari viewers via Model Context Protocol (MCP)**
*Perfect for AI-assisted microscopy analysis with Claude Desktop and other LLM applications.*

<p align="center">
  <a href="https://github.com/royerlab/napari-mcp/actions"><img src="https://img.shields.io/github/actions/workflow/status/royerlab/napari-mcp/tests.yml?branch=main&label=tests" alt="Tests"></a>
  <a href="https://codecov.io/gh/royerlab/napari-mcp"><img src="https://img.shields.io/codecov/c/github/royerlab/napari-mcp" alt="Coverage"></a>
  <a href="https://pypi.org/project/napari-mcp/"><img src="https://img.shields.io/pypi/v/napari-mcp" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

---

## 🎯 What is Napari MCP Server?

Napari MCP Server bridges the powerful [napari](https://napari.org/) multi-dimensional image viewer with AI assistants like Claude Desktop, enabling natural language control of microscopy workflows.

!!! tip "Zero Installation Required!"
    Run immediately without any pip install - just download and execute with `uv`!

### Key Features

=== "🤖 AI Integration"
    - **Claude Desktop** - Full MCP tool access
    - **Claude Code** - IDE integration for development
    - **Cursor** - AI-powered coding with napari
    - **ChatGPT** - Limited research functionality

=== "🔬 Napari Control"
    - **Viewer Management** - Create, configure, and control viewers
    - **Layer Operations** - Add images, labels, points with full property control
    - **Camera Control** - Zoom, pan, 3D navigation
    - **Screenshot Capture** - PNG export with base64 encoding

=== "⚡ Advanced Features"
    - **Code Execution** - Run Python with access to viewer and numpy
    - **Package Installation** - Install packages dynamically via pip
    - **Session Management** - Persistent state across operations
    - **Async Operations** - Non-blocking GUI event loop

---

## 🚀 Quick Start

Get napari working with AI assistance in 2 minutes:

### Option 1: Zero Install (Recommended)

```bash
# Download and run in one command
curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py
uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
  fastmcp run napari_mcp_server.py
```

### Option 2: Traditional Installation

```bash
# Clone and install
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp
pip install -e .

# Run
napari-mcp
```

### Configure Your AI Assistant

=== "Claude Desktop"
    ```json
    {
      "mcpServers": {
        "napari": {
          "command": "uv",
          "args": [
            "run", "--with", "Pillow", "--with", "PyQt6", "--with", "fastmcp",
            "--with", "imageio", "--with", "napari", "--with", "numpy", "--with", "qtpy",
            "fastmcp", "run", "/absolute/path/to/napari_mcp_server.py"
          ]
        }
      }
    }
    ```

=== "Claude Code"
    ```bash
    fastmcp install claude-code napari_mcp_server.py \
        --with napari --with imageio --with Pillow
    ```

=== "Cursor"
    ```bash
    fastmcp install cursor napari_mcp_server.py \
        --with napari --with imageio --with Pillow
    ```

**→ See the [Integrations](integrations/index.md) section for complete setup guides**

---

## 💡 Example Workflows

!!! example "Basic Image Analysis"
    ```
    Ask your AI: "Load the image from ./data/sample.tif and apply a viridis colormap"
    ```

!!! example "Multi-dimensional Data"
    ```
    Ask your AI: "Switch to 3D view mode and navigate to time point 5, Z-slice 10"
    ```

!!! example "Custom Analysis"
    ```
    Ask your AI: "Execute this code to create a filtered version:
    from scipy import ndimage
    filtered = ndimage.gaussian_filter(viewer.layers[0].data, sigma=2)
    viewer.add_image(filtered, name='filtered')"
    ```

---

## 🛠️ Available Tools

The server exposes 20+ MCP tools for complete napari control:

| Category | Tools | Description |
|----------|-------|-------------|
| **Session** | `init_viewer`, `close_viewer`, `session_information` | Viewer lifecycle management |
| **Layers** | `add_image`, `add_labels`, `add_points`, `list_layers` | Layer creation and management |
| **Properties** | `set_layer_properties`, `rename_layer`, `reorder_layer` | Layer customization |
| **Navigation** | `set_zoom`, `set_camera`, `reset_view`, `set_ndisplay` | Viewer navigation |
| **Utilities** | `screenshot`, `execute_code`, `install_packages` | Advanced functionality |

**→ See the [API Reference](api/index.md) for complete documentation**

---

## ⚠️ Security Notice

!!! warning "Code Execution Capabilities"
    This server includes powerful tools that allow arbitrary code execution:

    - **`execute_code()`** - Runs Python code in the server environment
    - **`install_packages()`** - Installs packages via pip

    **Use only with trusted AI assistants on local networks.**

---

## 🎯 Who This Is For

=== "🔬 Researchers"
    - **Microscopy Analysis** - Process and analyze imaging data
    - **Interactive Exploration** - Natural language data navigation
    - **Reproducible Workflows** - Document analysis steps

=== "👨‍💻 Developers"
    - **Napari Plugin Development** - Test and debug with AI assistance
    - **Image Processing Pipelines** - Rapid prototyping
    - **Educational Tools** - Teaching image analysis concepts

=== "🤖 AI Enthusiasts"
    - **Multi-modal AI** - Combine vision and language models
    - **Tool Integration** - Connect specialized software to LLMs
    - **Workflow Automation** - AI-driven scientific computing

---

## 🚦 Getting Started Paths

Choose your path based on your needs:

### 🚀 Choose Your Path

| Getting Started | Description |
|-----------------|-------------|
| **[⚡ Quick Start](getting-started/quickstart.md)** | Get running in 2 minutes with zero installation |
| **[📦 Zero Install](getting-started/zero-install.md)** | Run directly with uv - no pip install needed |
| **[🤖 Integrations](integrations/index.md)** | Set up with Claude Desktop, Cursor, or other AI tools |
| **[📚 API Reference](api/index.md)** | Complete documentation of all available tools |

---

## 🎉 Ready to Start?

1. **Choose your setup method** - Zero install or traditional
2. **Configure your AI assistant** - Claude Desktop, Cursor, etc.
3. **Start exploring** - Load images, analyze data, take screenshots
4. **Share your workflows** - Document and reproduce your analysis

**Happy analyzing! 🔬✨**

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

### Key Features

=== "🤖 AI Integration"
    - **Claude Desktop** - Full MCP tool access
    - **Claude Code** - IDE integration for development
    - **Cursor** - AI-powered coding with napari
    - **Cline** - VS Code and Cursor extensions
    - **More** - Gemini CLI, Codex CLI support

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
    - **Workflow Automation** - Python scripts for batch processing ([examples](examples/README.md))

---

## 🚀 Quick Start (3 Minutes)

Get napari working with AI assistance in just 3 minutes:

### Step 1: Install the Package

```bash
pip install napari-mcp
```

### Step 2: Auto-Configure Your Application

```bash
# For Claude Desktop
napari-mcp-install claude-desktop

# For other applications
napari-mcp-install claude-code    # Claude Code CLI
napari-mcp-install cursor         # Cursor IDE
napari-mcp-install cline-vscode   # Cline in VS Code
napari-mcp-install --help         # See all options
```

### Step 3: Restart & Test

Restart your AI application and try:
```
"Can you call session_information() to show my napari session?"
```

**That's it! 🎉** See the [Quick Start Guide](getting-started/quickstart.md) for more details.

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
| **Session** | `detect_viewers`, `init_viewer`, `close_viewer`, `session_information` | Viewer lifecycle management |
| **Layers** | `add_image`, `add_labels`, `add_points`, `list_layers` | Layer creation and management |
| **Properties** | `set_layer_properties`, `reorder_layer`, `set_active_layer` | Layer customization |
| **Navigation** | `set_camera`, `reset_view`, `set_ndisplay`, `set_dims_current_step` | Viewer navigation |
| **Utilities** | `screenshot`, `timelapse_screenshot`, `execute_code`, `install_packages` | Advanced functionality |

**→ See the [API Reference](api/index.md) for complete documentation**

---

## 🤖 Supported Applications

| Application | Command | Status |
|-------------|---------|--------|
| **Claude Desktop** | `napari-mcp-install claude-desktop` | ✅ Full Support |
| **Claude Code** | `napari-mcp-install claude-code` | ✅ Full Support |
| **Cursor IDE** | `napari-mcp-install cursor` | ✅ Full Support |
| **Cline (VS Code)** | `napari-mcp-install cline-vscode` | ✅ Full Support |
| **Cline (Cursor)** | `napari-mcp-install cline-cursor` | ✅ Full Support |
| **Gemini CLI** | `napari-mcp-install gemini` | ✅ Full Support |
| **Codex CLI** | `napari-mcp-install codex` | ✅ Full Support |

**→ See [Integration Guides](integrations/index.md) for application-specific setup**

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

## 🚦 Choose Your Path

| Getting Started | Description |
|-----------------|-------------|
| **[⚡ Quick Start](getting-started/quickstart.md)** | Get running in 3 minutes with CLI installer |
| **[🛠️ Installation Options](getting-started/installation.md)** | Advanced installation and manual configuration |
| **[🤖 Integrations](integrations/index.md)** | Set up with Claude Desktop, Cursor, or other AI tools |
| **[🐍 Python Automation](integrations/python.md)** | Build custom workflows with OpenAI, Anthropic, or any LLM |
| **[📚 API Reference](api/index.md)** | Complete documentation of all available tools |
| **[🔧 Troubleshooting](guides/troubleshooting.md)** | Common issues and solutions |

---

## 🎉 Ready to Start?

1. **Install the package** - `pip install napari-mcp`
2. **Configure your AI app** - `napari-mcp-install <app-name>`
3. **Start exploring** - Load images, analyze data, take screenshots
4. **Share your workflows** - Document and reproduce your analysis

**Happy analyzing! 🔬✨**

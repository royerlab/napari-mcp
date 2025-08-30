# Traditional Installation

Complete guide to installing napari MCP server using traditional Python package management.

!!! info "Alternative Methods Available"
    If you prefer zero-installation approaches, see our [Zero Install Guide](zero-install.md) or [Quick Start](quickstart.md).

## Method 1: Development Installation

Perfect for developers who want to modify the code or contribute to the project.

### Prerequisites

- **Python 3.10+**
- **Git** (for cloning the repository)
- **pip** or **uv** (package managers)

### Step-by-Step Installation

```bash
# Clone the repository
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp

# Install in development mode with all dependencies
pip install -e ".[test,dev]"

# Or with uv (recommended)
uv pip install -e ".[test,dev]"
```

### Verify Installation

```bash
# Check if the command is available
napari-mcp --help

# Or run directly
python -m napari_mcp_server --help
```

## Method 2: PyPI Installation (When Available)

Once published to PyPI, you can install directly:

```bash
# Install from PyPI (future)
pip install napari-mcp

# Or with uv
uv pip install napari-mcp
```

## Method 3: Direct Source Installation

Install directly from the source without cloning:

```bash
# Install from GitHub
pip install git+https://github.com/royerlab/napari-mcp.git

# With specific branch or tag
pip install git+https://github.com/royerlab/napari-mcp.git@main
```

## Running the Server

After installation, you have multiple ways to run the server:

### Command Line Interface

```bash
# Using the installed command
napari-mcp

# Using Python module
python -m napari_mcp_server

# With custom configuration
napari-mcp --port 8000 --host 0.0.0.0
```

### Python Script

```python
#!/usr/bin/env python
"""Run napari MCP server."""

from napari_mcp_server import main

if __name__ == "__main__":
    main()
```

## Claude Desktop Configuration

For traditional installations, use this configuration:

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

### Alternative Configuration

If you have the executable in your PATH:

```json
{
  "mcpServers": {
    "napari": {
      "command": "napari-mcp",
      "args": []
    }
  }
}
```

## Virtual Environment Setup

### Using venv

```bash
# Create virtual environment
python -m venv napari-mcp-env

# Activate (Linux/macOS)
source napari-mcp-env/bin/activate

# Activate (Windows)
napari-mcp-env\Scripts\activate

# Install
pip install -e ".[test,dev]"
```

### Using conda

```bash
# Create conda environment
conda create -n napari-mcp python=3.11

# Activate
conda activate napari-mcp

# Install
pip install -e ".[test,dev]"
```

## Dependencies Explained

### Core Dependencies

The package installs these automatically:

- **fastmcp** - MCP protocol framework
- **napari** - Multi-dimensional image viewer
- **PyQt6** - GUI backend
- **imageio** - Image I/O operations
- **Pillow** - Image processing
- **numpy** - Numerical computing
- **qtpy** - Qt abstraction

### Optional Dependencies

Install additional packages for enhanced functionality:

```bash
# Scientific computing
pip install scipy scikit-image

# Plotting
pip install matplotlib seaborn

# Additional formats
pip install tifffile imageio-ffmpeg
```

## Troubleshooting Installation

### Common Issues

!!! failure "Python version conflicts"
    **Problem:** `ERROR: This package requires Python >=3.10`

    **Solution:** Upgrade Python or use pyenv:
    ```bash
    pyenv install 3.11
    pyenv local 3.11
    ```

!!! failure "Qt backend issues"
    **Problem:** `qt.qpa.plugin: Could not find the Qt platform plugin`

    **Solutions:**
    - Install system Qt libraries
    - Set environment variable: `export QT_QPA_PLATFORM=offscreen`
    - Try different Qt backend: `pip install PyQt5` instead

!!! failure "Permission errors"
    **Problem:** `Permission denied` when installing

    **Solution:** Use user install:
    ```bash
    pip install --user -e .
    ```

!!! failure "Dependency conflicts"
    **Problem:** Package version conflicts

    **Solution:** Use virtual environment or update conflicting packages

### Debug Installation

```bash
# Check Python version
python --version

# Check pip version
pip --version

# List installed packages
pip list | grep -E "(napari|fastmcp|PyQt)"

# Check napari installation
python -c "import napari; print(napari.__version__)"

# Test MCP server import
python -c "import napari_mcp_server; print('Import successful')"
```

## Development Setup

For contributors and developers:

### Full Development Environment

```bash
# Clone with development focus
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp

# Install with all development tools
uv pip install -e ".[test,dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Run linting
ruff check src/ tests/
```

### IDE Configuration

#### VS Code
Add to `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"]
}
```

#### PyCharm
- Set interpreter to your virtual environment
- Mark `src/` as Sources Root
- Configure run configuration for `napari_mcp_server:main`

## Comparison with Zero Install

| Aspect | Traditional Install | Zero Install |
|--------|-------------------|--------------|
| **Setup Time** | 5-10 minutes | 30 seconds |
| **Disk Usage** | Permanent | Temporary |
| **Development** | Excellent | Limited |
| **Customization** | Full control | Limited |
| **Updates** | Manual `git pull` | Automatic |
| **Dependencies** | Manual management | Automatic |

## Next Steps

After successful installation:

1. **Configure your AI assistant** - See [Integrations](../integrations/index.md)
2. **Test basic functionality** - Try loading an image
3. **Explore advanced features** - Code execution, package installation
4. **Join the community** - Contribute to development

---

**Installation complete!** 🎉 You're ready to start using napari with AI assistance.

# Zero Install Guide

The ultimate way to run napari MCP server without any permanent installation - using `uv run --with` for automatic dependency management.

!!! tip "Perfect For"
    - **Quick demos** - No setup overhead
    - **Clean environments** - No leftover dependencies
    - **Team sharing** - Same setup everywhere
    - **CI/CD** - Reproducible deployments

## How Zero Install Works

The `uv run --with` approach automatically:

1. **Downloads dependencies** into a temporary environment
2. **Runs the server** with all required packages
3. **Cleans up** when finished (no permanent changes)

This means you can run napari MCP server on any system with just `uv` installed!

## Method 1: From GitHub (Latest Version)

### Direct GitHub Execution

```bash
uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
  fastmcp run https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py
```

!!! success "Benefits"
    - ✅ Always runs the latest version
    - ✅ No local files needed
    - ✅ Perfect for getting updates
    - ✅ Great for testing new features

### Download First, Then Run

```bash
# Download latest version
curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py

# Run locally
uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
  fastmcp run napari_mcp_server.py
```

## Method 2: From Local File

### Using Cloned Repository

```bash
# Clone the repository
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp

# Run with zero install
uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
  fastmcp run src/napari_mcp_server.py
```

### Using Downloaded File

```bash
# Download to specific location
curl -o ~/napari_mcp_server.py https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py

# Run from anywhere
uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
  fastmcp run ~/napari_mcp_server.py
```

## Claude Desktop Configuration

### Basic Configuration

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

### Advanced Configuration with Environment Variables

```json
{
  "mcpServers": {
    "napari": {
      "command": "uv",
      "args": [
        "run",
        "--with", "Pillow>=10.3.0",
        "--with", "PyQt6>=6.5.0",
        "--with", "fastmcp>=2.7.0",
        "--with", "imageio>=2.34.0",
        "--with", "napari>=0.5.5",
        "--with", "numpy>=1.26.0",
        "--with", "qtpy>=2.4.1",
        "fastmcp", "run",
        "/absolute/path/to/napari_mcp_server.py"
      ],
      "env": {
        "QT_QPA_PLATFORM": "offscreen",
        "NAPARI_ASYNC": "1"
      }
    }
  }
}
```

## Convenience Scripts

Use our pre-built scripts for even easier execution:

### Unix/macOS/Linux

```bash
# Download and run our convenience script
curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/scripts/run.sh
chmod +x run.sh

# Run with local file
./run.sh

# Run with specific path
./run.sh /path/to/napari_mcp_server.py
```

### Windows

```powershell
# Download and run our Windows script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/royerlab/napari-mcp/main/scripts/run.bat" -OutFile "run.bat"

# Run with local file
.\run.bat

# Run with specific path
.\run.bat C:\path\to\napari_mcp_server.py
```

## Understanding Dependencies

### Core Dependencies

| Package | Purpose | Why Needed |
|---------|---------|------------|
| **fastmcp** | MCP protocol implementation | Server framework |
| **napari** | Multi-dimensional image viewer | Core functionality |
| **PyQt6** | GUI backend | Window system |
| **imageio** | Image I/O operations | File loading/saving |
| **Pillow** | Image processing | Format support |
| **numpy** | Numerical computing | Array operations |
| **qtpy** | Qt abstraction layer | Cross-platform GUI |

### Optional Dependencies

Add these for enhanced functionality:

```bash
# Scientific computing
--with scipy --with scikit-image

# Plotting and visualization
--with matplotlib --with seaborn

# Additional image formats
--with tifffile --with imageio-ffmpeg
```

## Performance Optimization

### Faster Startup

Use a local uv cache to speed up repeated runs:

```bash
# Pre-populate cache
uv run --with napari --help

# Subsequent runs will be faster
uv run --with napari fastmcp run napari_mcp_server.py
```

### Memory Management

For large image processing:

```bash
uv run --with napari --with "numpy>=1.26.0" --with "Pillow>=10.3.0" \
  fastmcp run napari_mcp_server.py
```

## Troubleshooting

### Common Issues

!!! failure "uv: command not found"
    **Solution:** Install uv first:
    ```bash
    # macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Windows
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

!!! failure "Package conflicts"
    **Solution:** Use specific versions:
    ```bash
    uv run --with "napari==0.5.5" --with "PyQt6==6.5.0" \
      fastmcp run napari_mcp_server.py
    ```

!!! failure "Qt platform plugin not found"
    **Solution:** Add platform specification:
    ```bash
    export QT_QPA_PLATFORM=offscreen  # For headless
    # or
    export QT_QPA_PLATFORM=xcb       # For Linux with X11
    ```

!!! failure "Permission denied on downloaded file"
    **Solution:** Make executable:
    ```bash
    chmod +x napari_mcp_server.py
    ```

### Debugging

Enable verbose output:

```bash
uv run -v --with napari fastmcp run napari_mcp_server.py
```

Check environment:

```bash
uv run --with napari python -c "import napari; print(napari.__version__)"
```

## Advantages Over Traditional Installation

| Aspect | Zero Install | Traditional Install |
|--------|-------------|-------------------|
| **Setup time** | ~30 seconds | ~5-10 minutes |
| **Disk usage** | Temporary only | Permanent |
| **Dependency conflicts** | Isolated | Can conflict |
| **Version consistency** | Always specific | May drift |
| **Team deployment** | Identical everywhere | Environment dependent |
| **CI/CD friendly** | Perfect | Needs setup |
| **Cleanup needed** | None | Manual uninstall |

## Next Steps

Once you have zero install working:

1. **Test the connection** with your AI assistant
2. **Try basic operations** like loading images
3. **Explore advanced features** like code execution
4. **Set up convenience scripts** for regular use
5. **Share your setup** with team members

**→ Ready to configure your AI assistant? See [Integrations](../integrations/index.md)**

---

**Zero install = Zero hassle!** 🎉 Enjoy the freedom of dependency-free napari MCP server deployment.

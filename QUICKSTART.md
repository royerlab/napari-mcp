# 🚀 Zero-Install Quick Start - Napari MCP in 2 Minutes!

Run napari with AI control instantly - no installation required!

## ⚡ Super Quick Setup (Option 1: Direct Run)

### Step 1: Run Server (30 seconds)

**Fastest method - Run directly from GitHub (no download needed):**
```bash
# Run directly from GitHub - most convenient!
uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
  fastmcp run https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py
```

**Alternative - Download first then run:**
```bash
# Download and run in one command (requires uv)
curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py
uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy \
  fastmcp run napari_mcp_server.py
```

You should see:
- FastMCP banner
- "Starting MCP server" message  
- Napari window opens automatically

### Step 2: Configure Claude Desktop (1 minute)

**Option A: Direct GitHub execution (recommended):**
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
        "https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py"
      ]
    }
  }
}
```

**Option B: Downloaded file:**
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

**Note**: For Option B, replace `/absolute/path/to/napari_mcp_server.py` with the actual path to your downloaded file.

### Step 3: Test Connection (30 seconds)

Restart Claude Desktop and ask:
- **"Can you call session_information() to tell me about my napari session?"**
- Should return: `"session_type": "napari_mcp_standalone_session"`

## 🎯 Alternative: Traditional Installation

If you prefer installing as a package:

```bash
# Clone and install
git clone https://github.com/royerlab/napari-mcp.git
cd napari-mcp
pip install -e .

# Run
napari-mcp
```

Claude Desktop config for installed version:
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

## 🎯 First Things to Try

### Basic Operations
- **"Add a random image to the napari viewer"**
- **"Create some annotation points at random locations"**
- **"Change the colormap of the image layer to 'viridis'"**
- **"Reset the view to fit all data"**
- **"Take a screenshot of my napari viewer"**

### Advanced Experiments
- **"Execute this code: `print(f'Current zoom: {viewer.camera.zoom}')`"**
- **"Install the scipy package and create a Gaussian filtered image"**
- **"Switch to 3D view mode"**

## 🛠 Prerequisites

**Required:**
- [uv](https://docs.astral.sh/uv/getting-started/installation/) - Python package installer
- Python 3.10+ (automatically managed by uv)

**Install uv if needed:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pip
pip install uv
```

## ✅ Success Checklist

After following this guide:
- [ ] Server starts without errors and napari window opens
- [ ] Claude Desktop config added with correct file path
- [ ] Claude Desktop restarted
- [ ] `session_information()` returns standalone session type
- [ ] Screenshot and layer operations work via Claude

## ❌ Common Issues

### "uv: command not found"
```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh
# Restart terminal
```

### "fastmcp: command not found"
This is handled automatically by `--with fastmcp` - no action needed.

### "Claude can't see napari tools"
- Double-check the file path in Claude Desktop config is absolute
- Restart Claude Desktop after config changes
- Verify the server is running (should show FastMCP output)

### "File not found" error
- Use absolute paths in Claude Desktop config: `/Users/yourname/path/to/napari_mcp_server.py`
- Check file permissions: `chmod +x napari_mcp_server.py`

## 🆘 Need Help?

- **Download Issues**: Ensure you have internet connection and curl installed
- **Path Issues**: Use `pwd` to get current directory and construct absolute paths
- **Permission Issues**: Run `chmod +x napari_mcp_server.py` 
- **Advanced Usage**: Check the main README.md for more examples

## 🎉 Why This Approach?

✅ **Zero Installation** - No pip install, no virtual environments  
✅ **Single File** - Easy to share, version, and deploy  
✅ **Auto Dependencies** - uv handles all dependencies automatically  
✅ **Direct GitHub Execution** - Run latest version directly from repo without downloading  
✅ **Always Up-to-Date** - GitHub URL ensures you get the latest version  
✅ **Reproducible** - Same dependencies every time

**You're ready for AI-assisted microscopy analysis!**
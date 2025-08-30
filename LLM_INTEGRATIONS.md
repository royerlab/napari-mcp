# 🤖 LLM Application Integrations

Complete guide to integrating napari MCP server with different AI assistants and IDEs.

## 🎯 Quick Reference

| Application | Status | Method | Notes |
|-------------|--------|---------|-------|
| **Claude Desktop** | ✅ Full Support | Manual Config | Primary recommendation |
| **Claude Code** | ✅ Full Support | FastMCP CLI | IDE integration |
| **Cursor** | ✅ Full Support | FastMCP CLI | IDE integration |
| **ChatGPT** | 🟡 Limited | Remote Server | Deep Research only |

---

## 🖥️ Claude Desktop

**Recommended for most users** - Full MCP tool access with visual napari interaction.

### Zero-Install Method (Recommended)

**1. Download the server file:**
```bash
curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py
```

**2. Add to Claude Desktop config** (`claude_desktop_config.json`):
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

**3. Restart Claude Desktop**

### Using FastMCP CLI

```bash
# Install globally
fastmcp install claude-desktop napari_mcp_server.py --with napari --with imageio --with Pillow

# Or with dependencies file
fastmcp install claude-desktop napari_mcp_server.py --with-requirements requirements.txt
```

**Config location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

---

## 💻 Claude Code

**Perfect for development workflows** - Use napari tools directly in your coding environment.

### Setup

**1. Install via FastMCP CLI:**
```bash
fastmcp install claude-code napari_mcp_server.py \
    --with napari \
    --with imageio \
    --with Pillow \
    --with PyQt6 \
    --with numpy \
    --with qtpy
```

**2. Server will be automatically available in Claude Code**

### Features
- ✅ **Full MCP tool access** - All napari functions available
- ✅ **Code context** - Server can see your current code
- ✅ **File integration** - Easy image loading from workspace
- ✅ **Live development** - Make changes and test immediately

### Usage Tips
```
Ask Claude Code:
- "Load the image from ./data/sample.tif into napari"
- "Create an analysis script that uses the current napari viewer"
- "Take a screenshot of napari and save it to ./outputs/"
```

---

## 📝 Cursor

**Great for image analysis coding** - Integrate napari with AI-powered IDE features.

### Setup

**1. Install via FastMCP CLI:**
```bash
# Global installation
fastmcp install cursor napari_mcp_server.py \
    --with napari \
    --with imageio \
    --with Pillow \
    --with PyQt6

# Project-specific installation
fastmcp install cursor napari_mcp_server.py \
    --project-dir /path/to/your/project \
    --with napari --with imageio
```

**2. Available immediately in Cursor's AI assistant**

### Features
- ✅ **Project awareness** - Server knows your project structure
- ✅ **Code completion** - AI can suggest napari operations
- ✅ **Live visualization** - See changes in napari as you code
- ✅ **Workspace integration** - Easy access to project images

### Usage Examples
```
Ask Cursor:
- "Open all TIFF files in ./images/ directory in napari"
- "Create a function that processes the current napari layers"
- "Help me debug this image analysis by visualizing intermediate steps"
```

---

## 🔬 ChatGPT (Limited Support)

**For research workflows** - Limited to Deep Research feature only.

### ⚠️ Limitations
- Only works with **ChatGPT Plus/Team/Enterprise**
- **Deep Research mode only** - Not available in regular chat
- Requires **public server deployment**
- Limited to search/fetch patterns

### Setup (Advanced)

**1. Deploy server publicly:**
```bash
# Using ngrok for development
ngrok http 8000

# Run server on public URL
uv run --with fastmcp --with napari --with imageio --with Pillow \
    fastmcp serve napari_mcp_server.py --host 0.0.0.0 --port 8000
```

**2. Configure in ChatGPT:**
- Go to **Settings → Connectors**
- Add custom connector with your public URL
- Format: `https://your-url.ngrok.io/mcp/`

**3. Use in Deep Research:**
- Start new chat → "Run deep research"
- Select your napari connector
- Ask research questions about your images

### Use Cases
```
Research prompts:
- "Analyze the cell morphology patterns in my microscopy dataset"
- "Compare image quality metrics across different acquisition conditions"
- "Identify and quantify features in the loaded image stack"
```

---

## 🛠️ Advanced Configuration

### Environment Variables

Set these for all integrations:
```bash
export QT_QPA_PLATFORM=offscreen  # For headless servers
export NAPARI_ASYNC=1             # Enable async operations
export MCP_LOG_LEVEL=INFO         # Debug MCP communication
```

### Custom Dependencies

Add project-specific packages:
```bash
# With specific versions
fastmcp install claude-desktop napari_mcp_server.py \
    --with "scikit-image>=0.21" \
    --with "matplotlib>=3.7"

# With requirements file
fastmcp install cursor napari_mcp_server.py \
    --with-requirements requirements.txt
```

### Multiple Configurations

Run different servers for different use cases:
```json
{
  "mcpServers": {
    "napari-analysis": {
      "command": "uv",
      "args": ["run", "--with", "napari", "--with", "scikit-image",
               "fastmcp", "run", "/path/to/analysis_server.py"]
    },
    "napari-visualization": {
      "command": "uv",
      "args": ["run", "--with", "napari", "--with", "matplotlib",
               "fastmcp", "run", "/path/to/viz_server.py"]
    }
  }
}
```

---

## 🧪 Testing Your Integration

### 1. Verify Server Connection
```
Ask your AI assistant: "Can you call session_information() to check napari status?"
```

### 2. Test Basic Operations
```
Ask: "Take a screenshot of napari and describe what you see"
```

### 3. Test File Operations
```
Ask: "Add a sample image to napari from this path: /path/to/image.tif"
```

### 4. Test Code Execution
```
Ask: "Execute this code: print(f'Napari version: {napari.__version__}')"
```

---

## 📊 Feature Comparison

| Feature | Claude Desktop | Claude Code | Cursor | ChatGPT |
|---------|---------------|-------------|--------|---------|
| **Visual napari window** | ✅ Full | ✅ Full | ✅ Full | ❌ Server only |
| **All MCP tools** | ✅ 20+ tools | ✅ 20+ tools | ✅ 20+ tools | 🟡 Limited |
| **File system access** | ✅ Full | ✅ Full | ✅ Full | ❌ Remote only |
| **Code execution** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Package installation** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Setup complexity** | 🟢 Easy | 🟢 Easy | 🟢 Easy | 🔴 Complex |

---

## 🆘 Troubleshooting

### Common Issues

**"MCP server not found"**
- Check file paths are absolute
- Verify uv/fastmcp CLI is installed
- Restart the AI application

**"Dependencies missing"**
- Add `--with package-name` to installation
- Check Python version compatibility
- Verify virtual environment

**"Napari window doesn't open"**
- Check display settings (especially on remote systems)
- Verify Qt backend installation
- Try `QT_QPA_PLATFORM=offscreen` for headless

**"Permission denied"**
- Make server file executable: `chmod +x napari_mcp_server.py`
- Check file ownership and permissions
- Verify directory access rights

### Getting Help

1. **Check logs** - Most AI applications show MCP connection logs
2. **Test manually** - Run server directly to verify it works
3. **Verify config** - Use JSON validators for configuration files
4. **Start simple** - Begin with basic setup, add complexity gradually

---

## 🚀 Next Steps

After successful integration:

1. **Explore tools** - Try all available MCP tools
2. **Automate workflows** - Create scripts combining multiple operations
3. **Custom analysis** - Use `execute_code()` for specialized processing
4. **Share setups** - Document your configuration for team use

---

**🎉 Ready to supercharge your microscopy analysis with AI assistance!**

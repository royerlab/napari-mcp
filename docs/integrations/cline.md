# Cline Integration

Setup guide for using napari MCP server with Cline - the powerful AI coding assistant available as extensions for both VS Code and Cursor IDE.

## 🚀 Quick Setup

### For VS Code

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Auto-configure Cline in VS Code
napari-mcp-install cline-vscode

# 3. Restart VS Code (or reload window)
```

### For Cursor IDE

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Auto-configure Cline in Cursor
napari-mcp-install cline-cursor

# 3. Restart Cursor
```

## 📍 Configuration Locations

### Cline in VS Code

- **macOS**: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Windows**: `%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Linux**: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

!!! note "VS Code Insiders"
    For VS Code Insiders, replace `Code` with `Code - Insiders` in the path.

### Cline in Cursor IDE

- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Windows**: `%APPDATA%/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Linux**: `~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

## 💡 Why Use Cline with napari?

- **Powerful AI Assistant**: Advanced coding capabilities with full napari control
- **VS Code Integration**: Leverages VS Code's powerful editing features
- **Tool Permissions**: Fine-grained control over which tools to allow
- **Project Context**: Understands your workspace and files
- **Live Visualization**: See napari visualizations as you develop

## 🧪 Testing

After configuration, open the Cline extension and test:

```
Can you call session_information() to show the napari session?
```

```
Load images from ./data/ folder into napari
```

## 💻 Development Workflows

### Image Processing Development

```
Create a Python script that applies Gaussian blur to images in ./input/ and saves to ./output/
```

```
Help me debug why this segmentation isn't working as expected
```

### Napari Plugin Development

```
Help me create a napari widget for interactive thresholding
```

```
Test this plugin code and show the results in napari
```

### Batch Processing

```
Process all TIFF files in this directory with the filter pipeline we discussed
```

```
Create visualizations for each processing step
```

## 🔧 Manual Configuration

The CLI installer creates configurations with these features:

### Basic Configuration

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "alwaysAllow": [],
      "disabled": false
    }
  }
}
```

### With Tool Permissions

You can pre-approve specific tools to skip confirmation prompts:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "alwaysAllow": ["screenshot", "list_layers", "session_information"],
      "disabled": false
    }
  }
}
```

### Using Persistent Environment

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "python",
      "args": ["-m", "napari_mcp.server"],
      "always Allow": [],
      "disabled": false
    }
  }
}
```

## ⚙️ Tool Permissions

Cline supports configuring which tools can be called without confirmation:

- **`alwaysAllow`**: List of tool names that don't require confirmation
- **`disabled`**: Set to `true` to temporarily disable the server

**Recommended for `alwaysAllow`:**
- `session_information` - Safe read-only operation
- `list_layers` - Safe read-only operation
- `screenshot` - Safe read-only operation

**Use caution with:**
- `execute_code` - Runs arbitrary Python code
- `install_packages` - Installs packages via pip

## 🛠️ Management

```bash
# Check installation status
napari-mcp-install list

# Update VS Code configuration
napari-mcp-install cline-vscode --force

# Update Cursor configuration
napari-mcp-install cline-cursor --force

# Uninstall
napari-mcp-install uninstall cline-vscode
# or
napari-mcp-install uninstall cline-cursor
```

## ❌ Troubleshooting

### Cline Doesn't See napari MCP

!!! failure "MCP server not appearing"
    **Solutions:**

    1. **Verify Cline extension is installed:**
       - VS Code: Check Extensions panel
       - Cursor: Check Extensions panel

    2. **Check installation:**
       ```bash
       napari-mcp-install list
       ```

    3. **Open Cline MCP settings:**
       - Click the MCP icon in Cline extension
       - Verify napari-mcp appears in server list

    4. **Restart editor:**
       - VS Code: Reload window (Cmd/Ctrl + Shift + P → "Reload Window")
       - Cursor: Completely restart

    5. **Reinstall:**
       ```bash
       napari-mcp-install cline-vscode --force
       # or
       napari-mcp-install cline-cursor --force
       ```

### Wrong IDE Detected

!!! failure "Configured for wrong IDE"
    **Problem:** Accidentally used `cline-vscode` instead of `cline-cursor` (or vice versa)

    **Solution:** Uninstall and reinstall for correct IDE:

    ```bash
    # Uninstall wrong one
    napari-mcp-install uninstall cline-vscode

    # Install correct one
    napari-mcp-install cline-cursor
    ```

### VS Code Insiders

!!! failure "Config not found in VS Code Insiders"
    **Solution:** The path is different for Insiders. Manually create config at:

    - **macOS**: `~/Library/Application Support/Code - Insiders/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
    - **Windows**: `%APPDATA%/Code - Insiders/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
    - **Linux**: `~/.config/Code - Insiders/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

## 🔐 Security Considerations

- Cline runs with your user permissions
- The `alwaysAllow` list bypasses confirmation prompts - use carefully
- Code execution tools (`execute_code`, `install_packages`) should require confirmation
- Never add untrusted tools to `alwaysAllow`

## 📚 Next Steps

- **[Quick Start](../getting-started/quickstart.md)** - Get started quickly
- **[API Reference](../api/index.md)** - All available tools
- **[Troubleshooting](../guides/troubleshooting.md)** - Common issues

## 📖 Learn More About Cline

- **[Cline Extension](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev)** - VS Code Marketplace
- **[Cline GitHub](https://github.com/cline/cline)** - Source code and documentation

---

→ [Back to Integrations Overview](index.md)
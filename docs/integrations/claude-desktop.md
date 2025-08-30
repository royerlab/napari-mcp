# Claude Desktop Integration

*Coming soon - comprehensive Claude Desktop setup guide*

For now, please refer to our [Quick Start Guide](../getting-started/quickstart.md) which includes Claude Desktop configuration instructions.

## Quick Configuration

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

→ [Back to Integrations Overview](index.md)

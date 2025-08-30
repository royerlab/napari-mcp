# LLM Application Integrations

Connect napari MCP server with your favorite AI assistant or development environment.

## Supported Platforms

| Platform | Status | Setup Method | Features |
|----------|--------|--------------|----------|
| **🤖 Claude Desktop** | ✅ Full Support | Manual config | All 20+ MCP tools, visual napari control |
| **💻 Claude Code** | ✅ Full Support | FastMCP CLI | IDE integration, code context awareness |
| **📝 Cursor** | ✅ Full Support | FastMCP CLI | AI-powered coding, project integration |
| **💬 ChatGPT** | 🟡 Limited | Remote deployment | Deep Research mode only |

### Quick Links

- **[Claude Desktop Setup](claude-desktop.md)** - Most popular choice
- **[Claude Code Setup](claude-code.md)** - Perfect for development
- **[Cursor Setup](cursor.md)** - AI-enhanced coding
- **[ChatGPT Setup](chatgpt.md)** - Research workflows

## Feature Comparison

| Feature | Claude Desktop | Claude Code | Cursor | ChatGPT |
|---------|----------------|-------------|--------|---------|
| **Visual napari window** | ✅ Full | ✅ Full | ✅ Full | ❌ Server only |
| **All MCP tools** | ✅ 20+ tools | ✅ 20+ tools | ✅ 20+ tools | 🟡 Limited |
| **File system access** | ✅ Full | ✅ Full | ✅ Full | ❌ Remote only |
| **Code execution** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Package installation** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Setup complexity** | 🟢 Easy | 🟢 Easy | 🟢 Easy | 🔴 Complex |
| **Best for** | General use | Development | AI coding | Research |

## Quick Setup Overview

=== "Claude Desktop (Recommended)"
    ```json
    {
      "mcpServers": {
        "napari": {
          "command": "uv",
          "args": [
            "run", "--with", "napari", "--with", "fastmcp",
            "fastmcp", "run", "/path/to/napari_mcp_server.py"
          ]
        }
      }
    }
    ```

=== "Claude Code / Cursor"
    ```bash
    fastmcp install claude-code napari_mcp_server.py \
        --with napari --with imageio --with Pillow
    ```

=== "ChatGPT (Advanced)"
    ```bash
    # Deploy publicly accessible server
    uv run --with fastmcp --with napari \
      fastmcp serve napari_mcp_server.py --host 0.0.0.0
    ```

## Integration Benefits by Platform

### Claude Desktop
- **Zero configuration complexity** - Just edit a JSON file
- **Perfect for research** - Full napari visual interface
- **Immediate availability** - Works as soon as server starts
- **Best documentation** - Most comprehensive setup guides

### Claude Code
- **Development focused** - Perfect for napari plugin development
- **Code context awareness** - AI knows your current code
- **File system integration** - Easy image loading from workspace
- **Live development** - Test changes immediately

### Cursor
- **AI-enhanced coding** - Next-level development experience
- **Project awareness** - Understands your entire codebase
- **Smart completions** - AI suggests napari operations
- **Workspace integration** - Seamless file and project handling

### ChatGPT
- **Research workflows** - Designed for deep data analysis
- **Public accessibility** - Can be shared with team members
- **Advanced queries** - Complex multi-step analysis
- **Limited but specialized** - Focus on search/fetch patterns

## Common Configuration

All platforms support these environment variables:

```bash
export QT_QPA_PLATFORM=offscreen  # For headless servers
export NAPARI_ASYNC=1             # Enable async operations
export MCP_LOG_LEVEL=INFO         # Debug MCP communication
```

## Next Steps

1. **Choose your platform** based on your primary use case
2. **Follow the specific setup guide** for detailed instructions
3. **Test the integration** with our provided examples
4. **Explore advanced features** once basic setup works

## Need Help?

- **Setup issues?** Check our [Troubleshooting Guide](../guides/troubleshooting.md)
- **Feature requests?** Open an [issue on GitHub](https://github.com/royerlab/napari-mcp/issues)
- **Integration problems?** See platform-specific troubleshooting in each guide

---

**Ready to connect your AI assistant?** Choose your platform above and let's get started! 🚀

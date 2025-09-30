# ChatGPT Integration

## ⚠️ Important Notice

**ChatGPT Desktop and ChatGPT Web do not currently support Model Context Protocol (MCP).**

While **OpenAI does support MCP** through their [Python API and SDK](https://platform.openai.com/docs/guides/tools-connectors-mcp), the ChatGPT Desktop and Web applications don't have this capability built-in.

## 🤔 Understanding OpenAI's MCP Support

OpenAI has different products with different MCP capabilities:

| Product | MCP Support | napari-mcp Compatible | How to Use |
|---------|-------------|----------------------|------------|
| **ChatGPT Web** | ❌ No | ❌ No | N/A |
| **ChatGPT Desktop** | ❌ No | ❌ No | N/A |
| **ChatGPT Plus/Team/Enterprise** | ❌ No | ❌ No | N/A |
| **OpenAI Python API** | ✅ Yes | ✅ Yes | [Custom Python script](python.md) |
| **OpenAI SDK** | ✅ Yes | ✅ Yes | [Custom Python script](python.md) |

## ✅ Recommended Alternatives

If you want to use OpenAI models or ChatGPT-like experiences with napari MCP, here are your options:

### 1. Codex CLI (OpenAI)

OpenAI's Codex CLI **does support MCP** and works with napari-mcp:

```bash
pip install napari-mcp
napari-mcp-install codex
```

**→ See [Other LLMs Guide](other-llms.md#codex-cli) for setup instructions**

### 2. Cursor IDE (Uses OpenAI Models)

Cursor IDE supports MCP and uses OpenAI models under the hood:

```bash
pip install napari-mcp
napari-mcp-install cursor --global
```

**→ See [Cursor Integration Guide](cursor.md) for complete setup**

### 3. Claude Desktop (Anthropic)

While not OpenAI, Claude Desktop has excellent MCP support and is the most popular choice:

```bash
pip install napari-mcp
napari-mcp-install claude-desktop
```

**→ See [Claude Desktop Integration Guide](claude-desktop.md) for setup**

### 4. OpenAI Python API with MCP (Advanced)

For advanced users, you **can** use OpenAI models with napari-mcp through the Python API:

```python
# Example: Using OpenAI API with napari MCP server
# See the full guide for details
from openai import OpenAI

client = OpenAI()
# Connect to napari MCP server and use OpenAI models
```

**→ See [Python Integration Guide](python.md) for complete examples**

This approach gives you:
- ✅ Full MCP support with OpenAI models (GPT-4, etc.)
- ✅ Complete control over the integration
- ⚠️ Requires Python programming
- ⚠️ Not as convenient as desktop apps

## 🔮 Future Possibilities

### ChatGPT May Add MCP Support

OpenAI may add MCP support to ChatGPT in the future. When that happens, this page will be updated with setup instructions.

**How to stay updated:**
- Watch the [napari-mcp GitHub repository](https://github.com/royerlab/napari-mcp)
- Follow [MCP specification updates](https://modelcontextprotocol.io/)
- Check OpenAI's [product announcements](https://openai.com/blog)

### OpenAI GPT Store

The OpenAI GPT Store allows custom GPTs but doesn't currently support MCP servers. If this changes, we'll update the documentation.

## 💡 Why Use MCP-Compatible Tools?

MCP (Model Context Protocol) provides:
- **Direct tool access** - AI can directly control napari
- **Real-time interaction** - Immediate visual feedback
- **State management** - Maintains viewer state across requests
- **Rich capabilities** - Full access to napari's features

Without MCP support, you're limited to:
- Manual copy-paste of code
- No direct napari control
- No automatic screenshot capture
- No interactive workflows

## 📊 Comparison of Alternatives

| Platform | MCP Support | OpenAI Models | Setup Complexity | Best For |
|----------|-------------|---------------|------------------|----------|
| **Codex CLI** | ✅ Full | ✅ Yes | 🟢 Easy | Command-line users |
| **Cursor** | ✅ Full | ✅ Yes (optional) | 🟢 Easy | IDE users |
| **Claude Desktop** | ✅ Full | ❌ No (uses Claude) | 🟢 Easy | General use |
| **ChatGPT Desktop** | ❌ None | ✅ Yes | 🔴 N/A | Not compatible |

## 🚀 Get Started with Alternatives

Choose one of the supported options:

### Quick Start with Codex CLI

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Configure Codex CLI
napari-mcp-install codex

# 3. Use with Codex
# (Codex will now have access to napari MCP tools)
```

### Quick Start with Cursor

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Configure Cursor
napari-mcp-install cursor --global

# 3. Open Cursor IDE
# (Cursor AI will now have napari MCP access)
```

### Quick Start with Claude Desktop

```bash
# 1. Install napari-mcp
pip install napari-mcp

# 2. Configure Claude Desktop
napari-mcp-install claude-desktop

# 3. Restart Claude Desktop
# (Claude will now have napari MCP access)
```

## ❓ Frequently Asked Questions

### Can I use OpenAI API with napari-mcp?

Yes! OpenAI supports MCP through their Python API. You can write a Python script that uses OpenAI models (GPT-4, etc.) with napari-mcp as an MCP server.

**→ See [Python Integration Guide](python.md) for examples**

### What about ChatGPT Plus or Team?

ChatGPT Plus, Team, and Enterprise plans don't change MCP support - they still don't support it.

### Will OpenAI add MCP support?

We don't know. OpenAI hasn't announced plans for MCP support in ChatGPT. Use one of the alternatives above instead.

### Can I use GPT-4 with napari?

Yes! Use **Cursor** or **Codex CLI**, both of which support OpenAI models including GPT-4 and have MCP support.

## 📚 Next Steps

Since ChatGPT Desktop doesn't support MCP, we recommend:

1. **Try Codex CLI** - If you want OpenAI models with MCP support
   - **[Setup Guide](other-llms.md#codex-cli)**

2. **Try Cursor** - If you want an IDE with OpenAI model options
   - **[Setup Guide](cursor.md)**

3. **Try Claude Desktop** - If you want the best MCP experience (even if it's not OpenAI)
   - **[Setup Guide](claude-desktop.md)**

4. **See all options** - Compare all supported platforms
   - **[Integration Overview](index.md)**

---

## 📢 Summary

- ❌ **ChatGPT Desktop does not support MCP** and cannot use napari-mcp
- ✅ **Use Codex CLI instead** for OpenAI models with MCP support
- ✅ **Use Cursor** for IDE integration with OpenAI model options
- ✅ **Use Claude Desktop** for the most mature MCP implementation
- 📖 **See [Integrations Overview](index.md)** for all supported platforms

---

→ [Back to Integrations Overview](index.md)

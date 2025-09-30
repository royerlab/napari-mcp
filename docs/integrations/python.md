# Python Integration Guide

Advanced guide for using napari MCP server directly in Python scripts with any LLM provider.

!!! tip "For Most Users"
    Most users should use the desktop applications (Claude Desktop, Cursor, etc.) which handle MCP integration automatically. This guide is for advanced users who want to build custom integrations.

!!! example "Working Examples Available"
    Complete, tested examples are available in **[docs/examples/](../examples/README.md)**:

    - `openai_integration.py` - OpenAI GPT-4 with napari
    - `anthropic_integration.py` - Anthropic Claude with napari
    - `direct_mcp_client.py` - Direct automation without external LLMs

    Download and run these to get started quickly!

## Overview

napari-mcp is an MCP server that can be integrated into Python scripts, allowing you to:

- Use any LLM provider (OpenAI, Anthropic, etc.) with napari
- Build custom analysis pipelines
- Create automated workflows
- Integrate napari into larger applications

## Prerequisites

- Python 3.10+
- napari-mcp installed: `pip install napari-mcp`
- An LLM provider SDK: `pip install openai` or `pip install anthropic`
- MCP client library: `pip install mcp` (or use `uv run --with openai --with mcp`)

## Example: OpenAI with napari MCP

OpenAI supports MCP through their Python SDK. Here's a basic example:

```python
"""
Example: Using OpenAI GPT-4 with napari MCP server
Requires: pip install openai napari-mcp
"""

import asyncio
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Main function demonstrating OpenAI + napari MCP integration."""

    # Initialize OpenAI client
    client = OpenAI(api_key="your-api-key-here")

    # Start napari MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "napari_mcp.server"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")

            # Example: Get session information
            result = await session.call_tool("session_information", arguments={})
            print(f"Napari session: {result.content}")

            # Example: Use OpenAI to decide what to do with napari
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an assistant that controls napari."},
                    {"role": "user", "content": "Create a random test image and display it"}
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "execute_code",
                            "description": "Execute Python code in napari environment",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string"}
                                },
                                "required": ["code"]
                            }
                        }
                    }
                ]
            )

            # If OpenAI wants to call a tool
            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                if tool_call.function.name == "execute_code":
                    # Execute via napari MCP
                    import json
                    args = json.loads(tool_call.function.arguments)
                    result = await session.call_tool("execute_code", arguments=args)
                    print(f"Executed code: {result.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run the script:**
```bash
# If packages are installed in your environment
python script.py

# Or use uv for zero-install
uv run --with openai --with mcp python script.py
```

**→ See [OpenAI MCP Documentation](https://platform.openai.com/docs/guides/tools-connectors-mcp) for more details**

## Example: Anthropic Claude with napari MCP

You can also use Anthropic's Claude models:

```python
"""
Example: Using Anthropic Claude with napari MCP server
Requires: pip install anthropic napari-mcp
"""

import asyncio
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Main function demonstrating Anthropic + napari MCP integration."""

    # Initialize Anthropic client
    client = Anthropic(api_key="your-api-key-here")

    # Start napari MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "napari_mcp.server"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get available tools
            tools_result = await session.list_tools()

            # Convert MCP tools to Claude format
            tools = []
            for tool in tools_result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })

            # Use Claude to interact with napari
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                tools=tools,
                messages=[
                    {"role": "user", "content": "Take a screenshot of the napari viewer"}
                ]
            )

            # Process tool calls
            if message.stop_reason == "tool_use":
                for content_block in message.content:
                    if content_block.type == "tool_use":
                        # Execute the tool via MCP
                        result = await session.call_tool(
                            content_block.name,
                            arguments=content_block.input
                        )
                        print(f"Tool result: {result.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run the script:**
```bash
# If packages are installed in your environment
python script.py

# Or use uv for zero-install
uv run --with anthropic --with mcp python script.py
```

## Example: Simple Napari MCP Client

A minimal example without external LLM providers:

```python
"""
Simple napari MCP client without external LLM
Demonstrates direct tool calling
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def napari_workflow():
    """Example automated napari workflow."""

    # Start napari MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "napari_mcp.server"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # Step 1: Create synthetic data
            code = """
import numpy as np
data = np.random.random((512, 512))
viewer.add_image(data, name='test_image', colormap='viridis')
"""
            await session.call_tool("execute_code", arguments={"code": code})
            print("✓ Created test image")

            # Step 2: List layers
            result = await session.call_tool("list_layers", arguments={})
            print(f"✓ Current layers: {result.content}")

            # Step 3: Take screenshot
            screenshot = await session.call_tool("screenshot", arguments={})
            print("✓ Captured screenshot")

            # Step 4: Get session info
            info = await session.call_tool("session_information", arguments={})
            print(f"✓ Session info: {info.content}")

if __name__ == "__main__":
    asyncio.run(napari_workflow())
```

**Run the script:**
```bash
# No external dependencies needed for this example
python script.py

# Or with uv
uv run --with mcp python script.py
```

## Available MCP Tools

All napari-mcp tools are available in your Python integration. Common ones include:

### Session Management
- `session_information()` - Get comprehensive session info
- `init_viewer(title?, width?, height?)` - Create/configure viewer
- `close_viewer()` - Close viewer

### Layer Operations
- `add_image(path, name?, colormap?)` - Add image layer
- `add_labels(path, name?)` - Add labels layer
- `add_points(points, name?, size?)` - Add points
- `list_layers()` - List all layers
- `remove_layer(name)` - Remove layer

### Viewer Controls
- `set_camera(center?, zoom?, angle?)` - Control camera
- `reset_view()` - Reset view
- `set_ndisplay(2|3)` - Switch 2D/3D
- `screenshot(canvas_only?)` - Capture screenshot

### Advanced
- `execute_code(code)` - Run Python code
- `install_packages(packages)` - Install packages
- `read_output(output_id)` - Read stored output

**→ See [API Reference](../api/index.md) for complete tool documentation**

## Use Cases

### Automated Analysis Pipelines

```python
async def analyze_images(image_paths):
    """Process multiple images automatically."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            for path in image_paths:
                # Load image
                await session.call_tool("add_image", {"path": path})

                # Process
                code = """
from skimage import filters
threshold = filters.threshold_otsu(viewer.layers[-1].data)
binary = viewer.layers[-1].data > threshold
viewer.add_labels(binary.astype(int), name='segmentation')
"""
                await session.call_tool("execute_code", {"code": code})

                # Save results
                await session.call_tool("screenshot", {"canvas_only": True})
```

### Interactive LLM Workflows

Combine with LLMs for intelligent analysis:

```python
# User asks: "Find the brightest region in this image"
# LLM decides to:
# 1. Load the image
# 2. Execute code to find max intensity
# 3. Add a point marker at that location
# 4. Take a screenshot to show the result
```

### Custom Applications

Embed napari in larger applications:

```python
# Example: Flask web app with napari backend
# Example: Jupyter notebook with napari integration
# Example: Qt application with napari viewer
```

## Tips & Best Practices

### Error Handling

```python
try:
    result = await session.call_tool("add_image", {"path": "/invalid/path.tif"})
except Exception as e:
    print(f"Error: {e}")
```

### Resource Management

```python
# Always use context managers
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Your code here
        pass
# Server automatically cleaned up
```

### Environment Variables

```python
import os

server_params = StdioServerParameters(
    command="python",
    args=["-m", "napari_mcp.server"],
    env={
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",  # For headless servers
        "NAPARI_MCP_BRIDGE_PORT": "9999"
    }
)
```

## Limitations

!!! warning "Not for Production Use"
    - MCP server runs locally with full system access
    - Execute_code tool can run arbitrary Python code
    - Only use with trusted code and inputs
    - Not suitable for public-facing applications

## Resources

- **[OpenAI MCP Documentation](https://platform.openai.com/docs/guides/tools-connectors-mcp)** - Official OpenAI MCP guide
- **[MCP Specification](https://modelcontextprotocol.io/)** - Model Context Protocol spec
- **[napari-mcp API Reference](../api/index.md)** - Complete tool documentation
- **[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)** - MCP client library

## 📦 Download Complete Examples

All examples in this guide are available as working scripts:

**→ [Download Examples](../examples/README.md)**

- `openai_integration.py` - Tested with OpenAI GPT-4
- `anthropic_integration.py` - Tested with Claude 3.5 Sonnet
- `direct_mcp_client.py` - No API keys needed

Simply download, set your API key, and run!

## Next Steps

- **[Download Examples](../examples/README.md)** - Get the working code
- **[API Reference](../api/index.md)** - Explore all available tools
- **[ChatGPT Integration](../integrations/chatgpt.md)** - Why desktop apps don't work
- **[Troubleshooting](../guides/troubleshooting.md)** - Common issues

---

**This guide provides examples only.** For production use, consider using supported desktop applications like Claude Desktop, Cursor, or Codex CLI.

→ [Back to Integrations Overview](index.md)
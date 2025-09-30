"""Example: Using Anthropic Claude with napari MCP server.

Requires: pip install anthropic napari-mcp.
"""

import asyncio
import os

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    """Main function demonstrating Anthropic + napari MCP integration."""
    # Initialize Anthropic client
    api_key = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    client = Anthropic(api_key=api_key)

    # Start napari MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "napari_mcp.server"],
        env=None
    )

    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
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
                        print(f"Tool result of type {type(result.content[0])}")

if __name__ == "__main__":
    asyncio.run(main())

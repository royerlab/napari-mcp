"""Example: Using OpenAI GPT-4 with napari MCP server.

Requires: pip install openai napari-mcp.
"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI


async def main():
    """Main function demonstrating OpenAI + napari MCP integration."""
    # Initialize OpenAI client
    import os
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    client = OpenAI(api_key=api_key)

    # Start napari MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "napari_mcp.server"],
        env=None
    )

    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
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

"""Simple napari MCP client without external LLM.

Demonstrates direct tool calling.
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

    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
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
            await session.call_tool("screenshot", arguments={})
            print("✓ Captured screenshot")

            # Step 4: Get session info
            info = await session.call_tool("session_information", arguments={})
            print(f"✓ Session info: {info.content}")

if __name__ == "__main__":
    asyncio.run(napari_workflow())

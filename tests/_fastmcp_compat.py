"""Version-neutral access to a FastMCP server's tools in tests.

fastmcp 2 exposes ``await server.get_tools()`` (a name -> tool dict); fastmcp
3+ replaced it with ``await server.list_tools()`` (a list). Both return tool
objects with ``.name`` and ``.fn``.
"""

from typing import Any


async def tools_by_name(server: Any) -> dict[str, Any]:
    """Return the server's registered tools keyed by name."""
    if hasattr(server, "list_tools"):
        return {tool.name: tool for tool in await server.list_tools()}
    return dict(await server.get_tools())

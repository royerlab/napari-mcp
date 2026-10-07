# Adding tools from other packages

Any installed Python package can contribute its own MCP tools to napari-mcp,
both in standalone mode and in the napari plugin's bridge server. This keeps
domain-specific tools (for example, tools that drive another napari plugin's
widget) in that package rather than in napari-mcp.

## Declare an entry point

In the contributing package's `pyproject.toml`:

```toml
[project.entry-points."napari_mcp.tools"]
my_plugin = "my_plugin.mcp:register"
```

## Write the register function

`register(server, state)` receives the `FastMCP` server and napari-mcp's
`ServerState`. Register tools with `@server.tool()`. Run anything that touches
the GUI through `state.gui_execute(...)`. In the napari plugin it runs the
operation on the Qt main thread; standalone, it calls it directly. This is
what the built-in tools do:

```python
def register(server, state):
    @server.tool()
    async def count_layers() -> int:
        """Number of layers in the current viewer."""
        return state.gui_execute(lambda: len(state.viewer.layers))
```

Tools are registered once, after napari-mcp's built-in tools. Choose names
that do not collide with built-in tool names.

## Failure handling

A plugin that fails to import, or raises while registering, is logged and
skipped. The server and other plugins keep working.

To start a server without contributed tools, call
`create_server(state, load_plugins=False)`.

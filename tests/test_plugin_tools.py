"""Tools contributed by other packages through the napari_mcp.tools entry point."""

import asyncio
from unittest.mock import MagicMock

from napari_mcp import server as server_mod
from napari_mcp.server import TOOL_ENTRY_POINT_GROUP, create_server
from napari_mcp.state import ServerState
from tests._fastmcp_compat import tools_by_name


def _register_ok(server, state):
    @server.tool()
    async def plugin_echo(text: str) -> str:
        """Echo text back (test plugin tool)."""
        return text


def _register_broken(server, state):
    raise RuntimeError("plugin bug")


def _entry_point(name, fn):
    ep = MagicMock()
    ep.name = name
    ep.load.return_value = fn
    return ep


def _patch_entry_points(monkeypatch, eps):
    def fake(group):
        assert group == TOOL_ENTRY_POINT_GROUP
        return eps

    monkeypatch.setattr("importlib.metadata.entry_points", fake)


def test_plugin_tool_is_registered(monkeypatch):
    """A contributed tool appears alongside the built-in ones."""
    _patch_entry_points(monkeypatch, [_entry_point("demo", _register_ok)])
    names = set(asyncio.run(tools_by_name(create_server(ServerState()))))
    assert "plugin_echo" in names
    assert "screenshot" in names


def test_broken_plugin_is_skipped(monkeypatch):
    """A plugin that raises is logged and skipped; the others still load."""
    _patch_entry_points(
        monkeypatch,
        [_entry_point("broken", _register_broken), _entry_point("demo", _register_ok)],
    )
    srv = create_server(ServerState(), load_plugins=False)
    loaded = server_mod.register_plugin_tools(srv, ServerState())
    assert loaded == ["demo"]
    assert "plugin_echo" in asyncio.run(tools_by_name(srv))


def test_plugins_can_be_disabled(monkeypatch):
    """load_plugins=False registers only built-in tools."""
    _patch_entry_points(monkeypatch, [_entry_point("demo", _register_ok)])
    names = set(
        asyncio.run(tools_by_name(create_server(ServerState(), load_plugins=False)))
    )
    assert "plugin_echo" not in names

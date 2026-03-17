"""Integration and structural tests for the MCP tool registry.

- E2E workflow exercising all 16 tools in sequence
- MCP dispatch verification (tools callable via server.get_tool)
- Server factory (create_server returns FastMCP, sets state, registers tools)
- README completeness (every tool name appears in README)
"""

from pathlib import Path

import numpy as np
import pytest

from napari_mcp import server as napari_mcp_server

# Authoritative set of all registered MCP tool names.
# Update this when adding/removing tools in server.py.
EXPECTED_TOOLS = {
    "add_layer",
    "apply_to_layers",
    "close_viewer",
    "configure_viewer",
    "execute_code",
    "get_layer",
    "init_viewer",
    "install_packages",
    "list_layers",
    "read_output",
    "remove_layer",
    "reorder_layer",
    "save_layer_data",
    "screenshot",
    "session_information",
    "set_layer_properties",
}


def test_version_import() -> None:
    import napari_mcp

    assert hasattr(napari_mcp, "__version__")
    assert isinstance(napari_mcp.__version__, str)
    assert len(napari_mcp.__version__) > 0


@pytest.mark.asyncio
async def test_all_tools_end_to_end(make_napari_viewer, tmp_path: Path) -> None:
    """Smoke test: exercise every tool in a realistic workflow."""
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    import imageio.v3 as iio

    # init_viewer
    res = await napari_mcp_server.init_viewer(title="E2E")
    assert res["status"] == "ok"

    # add_layer (image from file)
    img = np.linspace(0, 255, 5 * 32 * 32, dtype=np.uint8).reshape(5, 32, 32)
    iio.imwrite(tmp_path / "img.tif", img)
    res = await napari_mcp_server.add_layer(
        "image", path=str(tmp_path / "img.tif"), name="img"
    )
    assert res["status"] == "ok"

    # add_layer (labels from file)
    iio.imwrite(tmp_path / "lbl.tif", np.random.randint(0, 4, (32, 32), dtype=np.uint8))
    assert (
        await napari_mcp_server.add_layer(
            "labels", path=str(tmp_path / "lbl.tif"), name="lbl"
        )
    )["status"] == "ok"

    # add_layer (points inline)
    res = await napari_mcp_server.add_layer(
        "points", data=[[5, 5], [10, 10]], name="pts", size=5
    )
    assert res["n_points"] == 2

    # list_layers
    names = {entry["name"] for entry in await napari_mcp_server.list_layers()}
    assert {"img", "lbl", "pts"} <= names

    # get_layer (metadata)
    info = await napari_mcp_server.get_layer("img")
    assert info["type"] == "Image" and info["data_shape"] == [5, 32, 32]

    # get_layer (data + slicing)
    data = await napari_mcp_server.get_layer("img", slicing="0, :2, :2")
    assert "data" in data and "statistics" in data

    # set_layer_properties (visibility, opacity, active, rename)
    await napari_mcp_server.set_layer_properties(
        "img", visible=False, opacity=0.5, active=True
    )
    assert viewer.layers["img"].visible is False

    # reorder_layer
    assert (await napari_mcp_server.reorder_layer("lbl", before="img"))[
        "status"
    ] == "ok"

    # apply_to_layers
    res = await napari_mcp_server.apply_to_layers(
        filter_type="Image", properties={"opacity": 0.8}
    )
    assert res["count"] == 1

    # configure_viewer
    assert (
        await napari_mcp_server.configure_viewer(reset_view=True, ndisplay=2, grid=True)
    )["status"] == "ok"
    assert (
        await napari_mcp_server.configure_viewer(zoom=1.5, dims_axis=0, dims_value=2)
    )["status"] == "ok"

    # screenshot (single)
    shot = await napari_mcp_server.screenshot(canvas_only=True)
    assert str(shot.mimeType).lower() in ("png", "image/png")

    # save_layer_data
    res = await napari_mcp_server.save_layer_data("pts", str(tmp_path / "pts.csv"))
    assert res["status"] == "ok"

    # execute_code
    res = await napari_mcp_server.execute_code("len(viewer.layers)")
    assert res["status"] == "ok"

    # session_information
    si = await napari_mcp_server.session_information()
    assert si["viewer"]["n_layers"] == len(viewer.layers)

    # remove + rename + close
    await napari_mcp_server.set_layer_properties("img", new_name="image1")
    assert (await napari_mcp_server.remove_layer("lbl"))["status"] == "removed"
    assert (await napari_mcp_server.close_viewer())["status"] in {"closed", "no_viewer"}


@pytest.mark.asyncio
async def test_add_layer_error_handling(make_napari_viewer, tmp_path: Path) -> None:
    """Error paths: bad file, bad data, nonexistent path."""
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer

    assert (await napari_mcp_server.add_layer("image", path="/nonexistent.tif"))[
        "status"
    ] == "error"
    assert (await napari_mcp_server.add_layer("points", data="bad"))[
        "status"
    ] == "error"


@pytest.mark.asyncio
async def test_mcp_tool_dispatch(make_napari_viewer) -> None:
    """All tools are registered and callable via MCP dispatch."""
    viewer = make_napari_viewer()
    napari_mcp_server._state.viewer = viewer
    server = napari_mcp_server.server

    for tool_name in EXPECTED_TOOLS:
        tool = await server.get_tool(tool_name)
        assert tool is not None, f"Tool '{tool_name}' not registered"
        assert callable(tool.fn), f"Tool '{tool_name}' fn is not callable"

    # Dispatch through MCP interface (not direct function call)
    tool = await server.get_tool("add_layer")
    result = await tool.fn("points", data=[[5, 5]], name="dispatch_pts")
    assert result["status"] == "ok"

    tool = await server.get_tool("remove_layer")
    assert (await tool.fn("dispatch_pts"))["status"] == "removed"


class TestCreateServer:
    def test_returns_fastmcp(self):
        from fastmcp import FastMCP

        from napari_mcp.server import create_server
        from napari_mcp.state import ServerState

        assert isinstance(create_server(ServerState()), FastMCP)

    def test_sets_module_state(self):
        from napari_mcp.server import create_server
        from napari_mcp.state import ServerState

        state = ServerState()
        create_server(state)
        assert napari_mcp_server._state is state

    def test_registers_all_tools(self):
        from napari_mcp.server import create_server
        from napari_mcp.state import ServerState

        create_server(ServerState())
        for name in EXPECTED_TOOLS:
            fn = getattr(napari_mcp_server, name, None)
            assert fn is not None and callable(fn), f"Tool {name} missing"


class TestToolListCompleteness:
    def test_readme_lists_all_tools(self):
        content = (Path(__file__).parent.parent / "README.md").read_text(
            encoding="utf-8"
        )
        missing = {t for t in EXPECTED_TOOLS if f"`{t}`" not in content}
        assert not missing, f"README.md missing tools: {missing}"

    @pytest.mark.asyncio
    async def test_expected_tools_matches_server(self):
        """EXPECTED_TOOLS stays in sync with actually registered tools."""
        from napari_mcp.server import create_server
        from napari_mcp.state import ServerState

        state = ServerState()
        srv = create_server(state)

        registered = set((await srv.get_tools()).keys())
        assert registered == EXPECTED_TOOLS, (
            f"Mismatch — registered: {registered - EXPECTED_TOOLS}, "
            f"expected but missing: {EXPECTED_TOOLS - registered}"
        )


class TestDeprecatedInstallCommand:
    def test_exits_with_error(self):
        from typer.testing import CliRunner

        from napari_mcp.server import app

        result = CliRunner().invoke(app, ["install"])
        assert result.exit_code == 1
        assert "napari-mcp-install" in result.stdout

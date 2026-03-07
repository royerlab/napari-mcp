from pathlib import Path

import numpy as np
import pytest

from napari_mcp import server as napari_mcp_server


def test_version_import() -> None:
    import napari_mcp

    assert hasattr(napari_mcp, "__version__")
    assert isinstance(napari_mcp.__version__, str)
    assert len(napari_mcp.__version__) > 0


@pytest.mark.asyncio
async def test_all_tools_end_to_end(make_napari_viewer, tmp_path: Path) -> None:
    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()

    # Set the viewer in the server state
    napari_mcp_server._state.viewer = viewer

    # init viewer
    res = await napari_mcp_server.init_viewer(title="Test Viewer")
    assert res["status"] == "ok"
    assert isinstance(res["layers"], list)

    # create sample image (T, Y, X) to exercise dims slider
    img = np.linspace(0, 255, 5 * 32 * 32, dtype=np.uint8).reshape(5, 32, 32)
    img_path = tmp_path / "img.tif"
    import imageio.v3 as iio

    iio.imwrite(img_path, img)

    # add image
    res = await napari_mcp_server.add_image(str(img_path), name="img")
    assert res["status"] == "ok"
    assert res["name"] == "img"

    # add labels
    labels = np.random.randint(0, 4, size=(32, 32), dtype=np.uint8)
    labels_path = tmp_path / "labels.tif"
    iio.imwrite(labels_path, labels)
    res = await napari_mcp_server.add_labels(str(labels_path), name="labels")
    assert res["status"] == "ok"

    # add points
    res = await napari_mcp_server.add_points([[5, 5], [10, 10]], name="pts", size=5)
    assert res["status"] == "ok" and res["n_points"] == 2

    # list layers
    layers = await napari_mcp_server.list_layers()
    layer_names = {lyr["name"] for lyr in layers}
    assert {"img", "labels", "pts"}.issubset(layer_names)

    # reorder layers: move labels before img
    res = await napari_mcp_server.reorder_layer("labels", before="img")
    assert res["status"] == "ok"

    # set active layer and properties
    res = await napari_mcp_server.set_active_layer("img")
    assert res["status"] == "ok" and res["active"] == "img"
    res = await napari_mcp_server.set_layer_properties(
        "img", visible=False, opacity=0.5
    )
    assert res["status"] == "ok"

    # view controls
    assert (await napari_mcp_server.reset_view())["status"] == "ok"
    assert (await napari_mcp_server.set_camera(zoom=1.5))["status"] == "ok"
    cam = await napari_mcp_server.set_camera(
        center=[10, 10], zoom=2.0, angles=[0.0, 0.0, 0.0]
    )
    assert cam["status"] == "ok"
    assert "angles" in cam
    assert isinstance(cam["angles"], list)

    # dims/grid controls
    # Keep ndisplay at 2 to avoid 3D requirements
    assert (await napari_mcp_server.set_ndisplay(2))["status"] == "ok"
    assert (await napari_mcp_server.set_dims_current_step(0, 2))["status"] == "ok"
    assert (await napari_mcp_server.set_grid(True))["status"] == "ok"

    # screenshot returns a valid PNG (FastMCP Image)
    shot = await napari_mcp_server.screenshot(canvas_only=True)
    fmt = shot.mimeType
    assert str(fmt).lower() in ("png", "image/png")

    import base64

    data = base64.b64decode(shot.data)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")

    # rename and remove layers
    assert (await napari_mcp_server.set_layer_properties("img", new_name="image1"))[
        "status"
    ] == "ok"
    assert (await napari_mcp_server.remove_layer("labels"))["status"] == "removed"

    # close viewer
    assert (await napari_mcp_server.close_viewer())["status"] in {"closed", "no_viewer"}


@pytest.mark.asyncio
async def test_execute_code_namespace_and_result(make_napari_viewer) -> None:
    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()

    napari_mcp_server._state.viewer = viewer

    # Simple expression
    res = await napari_mcp_server.execute_code("1 + 2")
    assert res["status"] == "ok"
    assert res.get("result_repr") == "3"

    # Set a variable and verify it's accessible
    res = await napari_mcp_server.execute_code("x = 42")
    assert res["status"] == "ok"

    res = await napari_mcp_server.execute_code("x * 2")
    assert res["status"] == "ok"
    assert res.get("result_repr") == "84"

    # Import a module in the namespace
    res = await napari_mcp_server.execute_code("import math")
    assert res["status"] == "ok"

    res = await napari_mcp_server.execute_code("math.pi")
    assert res["status"] == "ok"
    assert res.get("result_repr", "").startswith("3.14")

    # Clean up
    await napari_mcp_server.close_viewer()


@pytest.mark.asyncio
async def test_add_layers_error_handling(make_napari_viewer, tmp_path: Path) -> None:
    # Create a napari viewer using the built-in fixture
    viewer = make_napari_viewer()

    napari_mcp_server._state.viewer = viewer

    # Test adding image with bad path - should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        await napari_mcp_server.add_image("/nonexistent/file.tif", name="bad")

    # Test adding points with bad data - should raise ValueError
    with pytest.raises(ValueError):
        await napari_mcp_server.add_points("not_an_array", name="bad_points")


@pytest.mark.asyncio
async def test_mcp_tool_dispatch_local(make_napari_viewer) -> None:
    """Integration test: verify local server tools are registered and callable via MCP dispatch."""
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._state.viewer = viewer

    server = napari_mcp_server.server

    # Verify all expected tools are registered
    expected_tools = {
        "add_points",
        "add_image",
        "add_labels",
        "list_layers",
        "remove_layer",
        "set_active_layer",
        "set_camera",
        "set_ndisplay",
        "set_grid",
        "set_dims_current_step",
        "set_layer_properties",
        "reorder_layer",
        "reset_view",
        "screenshot",
        "timelapse_screenshot",
        "execute_code",
        "session_information",
        "close_viewer",
        "detect_viewers",
        "init_viewer",
        "install_packages",
        "read_output",
    }

    # get_tool should succeed for all expected tools
    for tool_name in expected_tools:
        tool = await server.get_tool(tool_name)
        assert tool is not None, f"Tool '{tool_name}' not registered"
        assert callable(tool.fn), f"Tool '{tool_name}' fn is not callable"

    # Exercise a few tools through MCP dispatch (not direct function calls)
    tool = await server.get_tool("add_points")
    result = await tool.fn([[5, 5], [10, 10]], name="mcp_dispatch_pts", size=3)
    assert result["status"] == "ok"
    assert result["n_points"] == 2

    tool = await server.get_tool("remove_layer")
    result = await tool.fn("mcp_dispatch_pts")
    assert result["status"] == "removed"

    tool = await server.get_tool("session_information")
    result = await tool.fn()
    assert result["status"] == "ok"
    assert "viewer" in result


class TestCreateServer:
    """Test server factory function."""

    def test_create_server_returns_fastmcp(self):
        from fastmcp import FastMCP

        from napari_mcp.server import create_server
        from napari_mcp.state import ServerState

        state = ServerState()
        srv = create_server(state)
        assert isinstance(srv, FastMCP)

    def test_create_server_sets_module_state(self):
        from napari_mcp.server import create_server
        from napari_mcp.state import ServerState

        state = ServerState()
        create_server(state)
        assert napari_mcp_server._state is state

    def test_create_server_registers_all_tools(self):
        from napari_mcp.server import create_server
        from napari_mcp.state import ServerState

        state = ServerState()
        create_server(state)

        expected_tools = [
            "detect_viewers",
            "init_viewer",
            "close_viewer",
            "session_information",
            "list_layers",
            "add_image",
            "add_labels",
            "add_points",
            "remove_layer",
            "set_layer_properties",
            "reorder_layer",
            "set_active_layer",
            "reset_view",
            "set_camera",
            "set_ndisplay",
            "set_dims_current_step",
            "set_grid",
            "screenshot",
            "timelapse_screenshot",
            "execute_code",
            "install_packages",
            "read_output",
        ]
        for tool_name in expected_tools:
            fn = getattr(napari_mcp_server, tool_name, None)
            assert fn is not None, f"Tool {tool_name} not found as module attribute"
            assert callable(fn), f"Tool {tool_name} is not callable"


class TestBackwardCompatStateAccess:
    """Test that old-style module-level state access still works."""

    def test_read_viewer_via_state(self):
        napari_mcp_server._state.viewer = "test_viewer"
        assert napari_mcp_server._state.viewer == "test_viewer"
        napari_mcp_server._state.viewer = None

    def test_read_exec_globals_via_state(self):
        napari_mcp_server._state.exec_globals["x"] = 1
        assert napari_mcp_server._state.exec_globals["x"] == 1
        napari_mcp_server._state.exec_globals.clear()

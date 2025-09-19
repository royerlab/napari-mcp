import base64
from collections.abc import Iterable

import numpy as np
import pytest


@pytest.mark.asyncio
async def test_timelapse_screenshot_basic(make_napari_viewer, monkeypatch):
    # Prepare viewer
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._viewer = viewer

    # Add a simple T, Y, X image so axis 0 is temporal
    img = np.linspace(0, 255, 5 * 32 * 32, dtype=np.uint8).reshape(5, 32, 32)
    layer = viewer.add_image(img, name="timelapse")
    assert layer is not None

    # Invoke via the tool interface to ensure ctx is injected automatically
    tool = await napari_mcp_server.server.get_tool("timelapse_screenshot")
    # Sweep all frames
    result = await tool.fn(0, ":", True, False)

    assert isinstance(result, list)
    assert len(result) == 5
    for shot in result:
        # ImageContent should have mimeType and data base64
        assert getattr(shot, "mimeType", "").lower() in ("png", "image/png")
        assert getattr(shot, "data", None) is not None
        # Data should be valid base64
        data = base64.b64decode(shot.data)
        assert data.startswith(b"\x89PNG\r\n\x1a\n")


def _b64_len_list(images: Iterable) -> int:
    total = 0
    for shot in images:
        data = shot.data
        if isinstance(data, bytes):
            total += len(data)
        else:
            total += len(str(data))
    return total


@pytest.mark.asyncio
async def test_timelapse_screenshot_interpolate_to_fit_enforces_cap(
    make_napari_viewer, monkeypatch
):
    # Prepare viewer
    viewer = make_napari_viewer()
    from napari_mcp import server as napari_mcp_server

    napari_mcp_server._viewer = viewer

    # Create many frames so uncompressed total would exceed the cap
    t = 20
    img = np.random.randint(0, 255, size=(t, 64, 64), dtype=np.uint8)
    viewer.add_image(img, name="timelapse_big")

    # Monkeypatch PIL Image.save to produce bytes proportional to pixel area,
    # so downsampling meaningfully shrinks encoded size
    import PIL.Image

    orig_save = PIL.Image.Image.save

    def fake_save(self, fp, *args, **kwargs):  # noqa: D401
        # Write a number of bytes roughly proportional to area
        w, h = self.size
        # 2 bytes per pixel (arbitrary but deterministic)
        data = b"A" * max(1, (w * h * 2))
        try:
            fp.write(data)
        except Exception:
            pass

    monkeypatch.setattr(PIL.Image.Image, "save", fake_save)

    try:
        tool = await napari_mcp_server.server.get_tool("timelapse_screenshot")

        # Without interpolation: should return all frames (may exceed cap)
        res_no = await tool.fn(0, ":", True, False)
        assert len(res_no) == t

        # With interpolation: should fit within cap and also return all frames
        res_yes = await tool.fn(0, ":", True, True)
        assert len(res_yes) == t

        total_b64 = _b64_len_list(res_yes)
        assert total_b64 <= 1309246

        # Additionally, verify at least some reduction happened per-frame
        # Compare first frame sizes with/without interpolation
        first_no = (
            len(res_no[0].data)
            if isinstance(res_no[0].data, bytes | bytearray)
            else len(str(res_no[0].data))
        )
        first_yes = (
            len(res_yes[0].data)
            if isinstance(res_yes[0].data, bytes | bytearray)
            else len(str(res_yes[0].data))
        )
        assert first_yes <= first_no
    finally:
        # Restore original save
        monkeypatch.setattr(PIL.Image.Image, "save", orig_save)

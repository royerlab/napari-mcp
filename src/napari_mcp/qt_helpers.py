"""Qt application and event loop management."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from napari_mcp.state import ServerState


def ensure_qt_app(state: ServerState) -> Any:
    """Return the Qt application, creating one if necessary, or a no-op stub."""
    from qtpy import QtWidgets

    if QtWidgets is None:

        class _StubApp:
            def processEvents(self, *_: Any) -> None:  # noqa: N802
                pass

            def setQuitOnLastWindowClosed(self, *_: Any) -> None:  # noqa: N802
                pass

        if state.qt_app is None:
            state.qt_app = _StubApp()
        return state.qt_app

    app = QtWidgets.QApplication.instance()
    if app is None:
        state.qt_app = QtWidgets.QApplication([])
        app = state.qt_app
    if isinstance(app, QtWidgets.QApplication):
        try:
            app.setQuitOnLastWindowClosed(False)
        except Exception:
            pass
    return app


def connect_window_destroyed_signal(state: ServerState, viewer: Any) -> None:
    """Connect to the Qt window destroyed signal to clear the viewer."""
    if state.window_close_connected:
        return
    try:
        qt_win = viewer.window._qt_window  # type: ignore[attr-defined]

        def _on_destroyed(*_args: Any) -> None:
            state.viewer = None
            state.window_close_connected = False
            state.request_shutdown()

        qt_win.destroyed.connect(_on_destroyed)  # type: ignore[attr-defined]
        state.window_close_connected = True
    except Exception:
        pass


def process_events(state: ServerState, cycles: int = 2) -> None:
    """Process pending Qt events."""
    app = ensure_qt_app(state)
    for _ in range(max(1, cycles)):
        app.processEvents()


async def qt_event_pump(state: ServerState) -> None:
    """Periodically process Qt events so the GUI remains responsive."""
    try:
        while True:
            try:
                process_events(state, 2)
            except Exception:
                pass  # Don't crash the pump on transient Qt errors
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        pass


def ensure_viewer(state: ServerState) -> Any:
    """Create or return the napari viewer singleton."""
    import napari

    ensure_qt_app(state)
    if state.viewer is None:
        state.viewer = napari.Viewer()
        connect_window_destroyed_signal(state, state.viewer)
    return state.viewer

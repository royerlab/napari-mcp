"""
Additional edge case tests to maximize coverage.
"""

import asyncio
import os
import sys
import types
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Ensure Qt runs headless
if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")


# Mock QtWidgets for testing Qt app functionality
class _MockQApplication:
    def __init__(self, args):
        self.args = args
        self._instance = self

    @classmethod
    def instance(cls):
        return None  # Force creation of new instance

    def setQuitOnLastWindowClosed(self, value):
        # Sometimes this fails in headless environments
        if os.environ.get("TEST_QT_FAILURE"):
            raise RuntimeError("Qt operation failed")

    def processEvents(self):
        pass


class _MockQtWidgets:
    QApplication = _MockQApplication


# Define a hashable layer class for sets
class _HashableLayer:
    def __init__(self, name, data=None, **kwargs):
        self.name = name
        self.data = data
        self.visible = kwargs.get("visible", True)
        self.opacity = kwargs.get("opacity", 1.0)
        self.size = kwargs.get("size", 10)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, _HashableLayer) and self.name == other.name


# Define a minimal fake viewer at module level
class _FakeViewer:
    def __init__(self):
        self.title = ""
        self.layers = _MockLayers()
        self.window = types.SimpleNamespace(
            qt_viewer=types.SimpleNamespace(
                canvas=types.SimpleNamespace(
                    native=types.SimpleNamespace(resize=lambda w, h: None),
                    size=lambda: types.SimpleNamespace(
                        width=lambda: 800, height=lambda: 600
                    ),
                )
            )
        )
        self.camera = types.SimpleNamespace(center=[0.0, 0.0], zoom=1.0, angles=(0.0,))
        self.dims = types.SimpleNamespace(
            ndisplay=2, current_step={}, set_current_step=lambda axis, value: None
        )
        self.grid = types.SimpleNamespace(enabled=False)

    def close(self):
        pass

    def reset_view(self):
        pass

    def add_image(self, data, **kwargs):
        name = kwargs.pop("name", "image")  # Remove name from kwargs to avoid duplicate
        layer = _HashableLayer(name=name, data=data, **kwargs)
        self.layers.append(layer)
        return layer

    def add_points(self, data, **kwargs):
        name = kwargs.pop(
            "name", "points"
        )  # Remove name from kwargs to avoid duplicate
        layer = _HashableLayer(name=name, data=data, **kwargs)
        self.layers.append(layer)
        return layer

    def add_labels(self, data, **kwargs):
        name = kwargs.pop(
            "name", "labels"
        )  # Remove name from kwargs to avoid duplicate
        layer = _HashableLayer(name=name, data=data, **kwargs)
        self.layers.append(layer)
        return layer

    def screenshot(self, canvas_only=True):
        return np.zeros((100, 100, 4), dtype=np.uint8)


class _MockLayers:
    def __init__(self):
        self._layers = []

    def __contains__(self, name):
        return any(layer.name == name for layer in self._layers)

    def __getitem__(self, key):
        if isinstance(key, str):
            for layer in self._layers:
                if layer.name == key:
                    return layer
            raise KeyError(f"Layer '{key}' not found")
        return self._layers[key]

    def __len__(self):
        return len(self._layers)

    def __iter__(self):
        return iter(self._layers)

    def append(self, layer):
        self._layers.append(layer)

    def remove(self, layer):
        if isinstance(layer, str):
            layer = self[layer]
        self._layers.remove(layer)

    def move(self, src_index, dst_index):
        layer = self._layers.pop(src_index)
        self._layers.insert(dst_index, layer)

    def index(self, layer):
        if isinstance(layer, str):
            for i, layer_obj in enumerate(self._layers):
                if layer_obj.name == layer:
                    return i
            raise ValueError(f"Layer '{layer}' not found")
        return self._layers.index(layer)


def _install_mock_napari():
    """Install minimal napari mock."""
    mock = types.ModuleType("napari")
    mock.__file__ = None  # Mark as fake
    mock.Viewer = _FakeViewer
    # Return a viewer instance when current_viewer is called
    _mock_viewer_instance = _FakeViewer()
    mock.current_viewer = lambda: _mock_viewer_instance
    sys.modules["napari"] = mock

    # Also create submodules with proper attributes
    mock_viewer = types.ModuleType("napari.viewer")
    mock_viewer.Viewer = _FakeViewer  # Add Viewer class to the submodule
    mock_viewer.current_viewer = lambda: _mock_viewer_instance  # Add this attribute
    sys.modules["napari.viewer"] = mock_viewer


# Clean up any existing napari modules first
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("napari"):
        del sys.modules[mod_name]

# Store original napari (None since we cleared it)
_original_napari = None

if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    _install_mock_napari()


@pytest.fixture(scope="module", autouse=True)
def cleanup_mocks():
    """Cleanup mock napari after tests."""
    yield
    # Clean up napari submodules
    if "napari.viewer" in sys.modules:
        del sys.modules["napari.viewer"]

    # Restore or remove napari
    if _original_napari is not None:
        sys.modules["napari"] = _original_napari
    elif "napari" in sys.modules and (
        not hasattr(sys.modules["napari"], "__file__")
        or not sys.modules["napari"].__file__
    ):
        del sys.modules["napari"]


from napari_mcp.server import (  # noqa: E402
    _connect_window_destroyed_signal,
    _ensure_qt_app,
    _process_events,
    _qt_event_pump,
    install_packages,
    start_gui,
    stop_gui,
)


def test_qt_app_creation(mock_napari):
    """Test Qt application creation and error handling."""
    # Test successful creation
    app = _ensure_qt_app()
    assert app is not None

    # Test error handling in setQuitOnLastWindowClosed
    with patch.dict(os.environ, {"TEST_QT_FAILURE": "1"}):
        # Should not raise exception, just continue
        app = _ensure_qt_app()
        assert app is not None


def test_process_events(mock_napari):
    """Test Qt event processing."""
    # Test with different cycle counts
    _process_events(1)
    _process_events(5)
    _process_events(0)  # Should default to 1


def test_connect_window_destroyed_signal(mock_napari):
    """Test window destroyed signal connection."""
    # Import the module-level variable
    from napari_mcp import server as napari_mcp_server

    # Reset the global flag first to ensure we test properly
    original_flag = napari_mcp_server._window_close_connected
    napari_mcp_server._window_close_connected = False

    try:
        # Create a mock viewer that mimics the structure
        viewer = types.SimpleNamespace()

        # Mock the window structure with proper Qt signal mocking
        viewer.window = MagicMock()
        viewer.window._qt_window = MagicMock()
        # Create a proper mock for the destroyed signal
        destroyed_mock = MagicMock()
        destroyed_mock.connect = MagicMock()
        viewer.window._qt_window.destroyed = destroyed_mock

        # Test successful connection
        _connect_window_destroyed_signal(viewer)
        destroyed_mock.connect.assert_called_once()

        # Reset flag for next test
        napari_mcp_server._window_close_connected = False

        # Test error handling when connection fails
        destroyed_mock.connect.side_effect = RuntimeError("Connection failed")
        _connect_window_destroyed_signal(viewer)  # Should not raise
    finally:
        # Restore original flag value
        napari_mcp_server._window_close_connected = original_flag


@pytest.mark.asyncio
async def test_start_gui_error_handling(mock_napari):
    """Test error handling in GUI start."""
    # Temporarily mock qtpy for this test
    original_qtpy = sys.modules.get("qtpy")
    mock_qtpy = types.ModuleType("qtpy")
    mock_qtpy.QtWidgets = _MockQtWidgets()
    mock_qtpy.API_NAME = "PyQt6"
    mock_qtpy.QT_VERSION = "6.0.0"
    mock_qtpy.QtCore = types.ModuleType("qtpy.QtCore")
    mock_qtpy.QtCore.__version__ = "6.0.0"
    sys.modules["qtpy"] = mock_qtpy

    try:
        # Test that start_gui handles errors gracefully
        # The function has built-in error handling with try/except blocks
        res = await start_gui(focus=True)
        assert res["status"] in ["started", "already_running"]

        # Test calling start_gui multiple times
        res2 = await start_gui(focus=False)
        assert res2["status"] in ["started", "already_running"]
    finally:
        # Restore original qtpy
        if original_qtpy is not None:
            sys.modules["qtpy"] = original_qtpy
        else:
            del sys.modules["qtpy"]


@pytest.mark.asyncio
async def test_qt_event_pump(mock_napari):
    """Test Qt event pump task."""
    # Test starting and cancelling the pump
    pump_task = asyncio.create_task(_qt_event_pump())

    # Let it run briefly
    await asyncio.sleep(0.02)

    # Cancel it
    pump_task.cancel()

    # Should handle cancellation gracefully
    try:
        await pump_task
        # If it completed without raising, that's also fine
    except asyncio.CancelledError:
        # This is the expected behavior
        pass


@pytest.mark.asyncio
async def test_install_packages_subprocess_error(mock_napari):
    """Test package installation with subprocess errors."""
    # Mock subprocess that fails
    with patch("napari_mcp.server.asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = MagicMock()

        # Make communicate async
        async def mock_communicate():
            return (b"stdout output", b"error output")

        mock_proc.communicate = mock_communicate
        mock_proc.returncode = 1  # Failure
        mock_subprocess.return_value = mock_proc

        res = await install_packages(["fake-package"])
        assert res["status"] == "error"
        assert res["returncode"] == 1
        assert "stdout output" in res["stdout"]
        assert "error output" in res["stderr"]


@pytest.mark.asyncio
async def test_install_packages_with_options(mock_napari):
    """Test package installation with all options."""
    with patch("napari_mcp.server.asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = MagicMock()

        # Make communicate async
        async def mock_communicate():
            return (b"success", b"")

        mock_proc.communicate = mock_communicate
        mock_proc.returncode = 0
        mock_subprocess.return_value = mock_proc

        res = await install_packages(
            packages=["package1", "package2"],
            upgrade=True,
            no_deps=True,
            index_url="https://custom.index.url",
            extra_index_url="https://extra.index.url",
            pre=True,
        )

        assert res["status"] == "ok"
        assert res["returncode"] == 0

        # Check that all options were included in the command
        call_args = mock_subprocess.call_args[0]
        assert "--upgrade" in call_args
        assert "--no-deps" in call_args
        assert "--pre" in call_args
        assert "--index-url" in call_args
        assert "https://custom.index.url" in call_args
        assert "--extra-index-url" in call_args
        assert "https://extra.index.url" in call_args
        assert "package1" in call_args
        assert "package2" in call_args


@pytest.mark.asyncio
async def test_gui_lifecycle_error_cases(mock_napari):
    """Test GUI lifecycle with error conditions."""
    # Temporarily mock qtpy for this test
    original_qtpy = sys.modules.get("qtpy")
    mock_qtpy = types.ModuleType("qtpy")
    mock_qtpy.QtWidgets = _MockQtWidgets()
    mock_qtpy.API_NAME = "PyQt6"
    mock_qtpy.QT_VERSION = "6.0.0"
    mock_qtpy.QtCore = types.ModuleType("qtpy.QtCore")
    mock_qtpy.QtCore.__version__ = "6.0.0"
    sys.modules["qtpy"] = mock_qtpy

    try:
        # Test stopping GUI when none is running
        res = await stop_gui()
        assert res["status"] == "stopped"

        # Test multiple start/stop cycles
        await start_gui()
        await start_gui()  # Should return "already_running"
        await stop_gui()
        await stop_gui()  # Should still work
    finally:
        # Restore original qtpy
        if original_qtpy is not None:
            sys.modules["qtpy"] = original_qtpy
        else:
            del sys.modules["qtpy"]


def test_main_function(mock_napari):
    """Test the main function."""
    from napari_mcp.server import main

    # Mock the server.run() method
    with patch("napari_mcp.server.server.run") as mock_run:
        main()
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_complex_code_execution(mock_napari):
    """Test complex code execution scenarios."""
    # Temporarily mock qtpy for this test
    original_qtpy = sys.modules.get("qtpy")
    mock_qtpy = types.ModuleType("qtpy")
    mock_qtpy.QtWidgets = _MockQtWidgets()
    mock_qtpy.API_NAME = "PyQt6"
    mock_qtpy.QT_VERSION = "6.0.0"
    mock_qtpy.QtCore = types.ModuleType("qtpy.QtCore")
    mock_qtpy.QtCore.__version__ = "6.0.0"
    sys.modules["qtpy"] = mock_qtpy

    try:
        from napari_mcp.server import execute_code, init_viewer

        await init_viewer()

        # Test multi-line code with imports
        code = """
import math
x = math.pi
y = math.sin(x)
print(f"sin(pi) = {y}")
abs(y) < 1e-10  # Should be approximately 0
"""
        res = await execute_code(code)
        assert res["status"] == "ok"
        assert "True" in res.get("result_repr", "")
        assert "sin(pi)" in res["stdout"]

        # Test code that modifies namespace
        code = """
test_var = 42
test_var
"""
        res = await execute_code(code)
        assert res["status"] == "ok"
        assert "42" in res.get("result_repr", "")

        # Test exception in the middle of multi-statement code
        code = """
x = 1
y = 2
z = x / 0  # This will fail
w = 3
"""
        res = await execute_code(code)
        assert res["status"] == "error"
        assert "ZeroDivisionError" in res["stderr"]
    finally:
        # Restore original qtpy
        if original_qtpy is not None:
            sys.modules["qtpy"] = original_qtpy
        else:
            del sys.modules["qtpy"]

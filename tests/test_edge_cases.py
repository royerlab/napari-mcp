"""
Additional edge case tests to maximize coverage.
"""

import os
import sys
import types
import asyncio
import subprocess
from unittest.mock import patch, MagicMock

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


# Create mock QtWidgets module
mock_qtpy = types.ModuleType("qtpy")
mock_qtpy.QtWidgets = _MockQtWidgets()
sys.modules["qtpy"] = mock_qtpy


def _install_mock_napari():
    """Install minimal napari mock."""
    try:
        from test_tools import _FakeViewer
    except ImportError:
        # Define a minimal fake viewer here
        class _FakeViewer:
            def __init__(self):
                self.title = ""
                self.layers = []
                self.window = None

            def close(self):
                pass

    mock = types.ModuleType("napari")
    mock.Viewer = _FakeViewer
    sys.modules["napari"] = mock


if os.environ.get("RUN_REAL_NAPARI_TESTS") != "1":
    _install_mock_napari()


from napari_mcp_server import (  # noqa: E402
    _ensure_qt_app,
    _connect_window_destroyed_signal,
    _process_events,
    start_gui,
    stop_gui,
    install_packages,
    _qt_event_pump,
)


def test_qt_app_creation():
    """Test Qt application creation and error handling."""
    # Test successful creation
    app = _ensure_qt_app()
    assert app is not None
    
    # Test error handling in setQuitOnLastWindowClosed
    with patch.dict(os.environ, {"TEST_QT_FAILURE": "1"}):
        # Should not raise exception, just continue
        app = _ensure_qt_app()
        assert app is not None


def test_process_events():
    """Test Qt event processing."""
    # Test with different cycle counts
    _process_events(1)
    _process_events(5)
    _process_events(0)  # Should default to 1


def test_connect_window_destroyed_signal():
    """Test window destroyed signal connection."""
    try:
        from test_tools import _FakeViewer
    except ImportError:
        from napari_mcp_server import _ensure_viewer
        viewer = _ensure_viewer()
    else:
        viewer = _FakeViewer()
    
    # Mock the window structure
    viewer.window = MagicMock()
    viewer.window._qt_window = MagicMock()
    viewer.window._qt_window.destroyed = MagicMock()
    
    # Test successful connection
    _connect_window_destroyed_signal(viewer)
    viewer.window._qt_window.destroyed.connect.assert_called_once()
    
    # Test error handling when connection fails
    viewer.window._qt_window.destroyed.connect.side_effect = RuntimeError("Connection failed")
    _connect_window_destroyed_signal(viewer)  # Should not raise


@pytest.mark.asyncio
async def test_start_gui_error_handling():
    """Test error handling in GUI start."""
    # Test with mock viewer that has window issues
    from napari_mcp_server import _ensure_viewer
    
    viewer = _ensure_viewer()
    
    # Mock window with problematic operations
    viewer.window = MagicMock()
    viewer.window._qt_window = MagicMock()
    viewer.window._qt_window.show.side_effect = RuntimeError("Show failed")
    viewer.window._qt_window.raise_.side_effect = RuntimeError("Raise failed")
    viewer.window._qt_window.activateWindow.side_effect = RuntimeError("Activate failed")
    
    # Should not raise exceptions
    res = await start_gui(focus=True)
    assert res["status"] in ["started", "already_running"]


@pytest.mark.asyncio
async def test_qt_event_pump():
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
async def test_install_packages_subprocess_error():
    """Test package installation with subprocess errors."""
    # Mock subprocess that fails
    with patch('napari_mcp_server.asyncio.create_subprocess_exec') as mock_subprocess:
        mock_proc = MagicMock()
        # Make communicate async
        async def mock_communicate():
            return (b'stdout output', b'error output')
        mock_proc.communicate = mock_communicate
        mock_proc.returncode = 1  # Failure
        mock_subprocess.return_value = mock_proc
        
        res = await install_packages(['fake-package'])
        assert res["status"] == "error"
        assert res["returncode"] == 1
        assert "stdout output" in res["stdout"]
        assert "error output" in res["stderr"]


@pytest.mark.asyncio
async def test_install_packages_with_options():
    """Test package installation with all options."""
    with patch('napari_mcp_server.asyncio.create_subprocess_exec') as mock_subprocess:
        mock_proc = MagicMock()
        # Make communicate async
        async def mock_communicate():
            return (b'success', b'')
        mock_proc.communicate = mock_communicate
        mock_proc.returncode = 0
        mock_subprocess.return_value = mock_proc
        
        res = await install_packages(
            packages=['package1', 'package2'],
            upgrade=True,
            no_deps=True,
            index_url='https://custom.index.url',
            extra_index_url='https://extra.index.url',
            pre=True
        )
        
        assert res["status"] == "ok"
        assert res["returncode"] == 0
        
        # Check that all options were included in the command
        call_args = mock_subprocess.call_args[0]
        assert '--upgrade' in call_args
        assert '--no-deps' in call_args
        assert '--pre' in call_args
        assert '--index-url' in call_args
        assert 'https://custom.index.url' in call_args
        assert '--extra-index-url' in call_args
        assert 'https://extra.index.url' in call_args
        assert 'package1' in call_args
        assert 'package2' in call_args


@pytest.mark.asyncio
async def test_gui_lifecycle_error_cases():
    """Test GUI lifecycle with error conditions."""
    # Test stopping GUI when none is running
    res = await stop_gui()
    assert res["status"] == "stopped"
    
    # Test multiple start/stop cycles
    await start_gui()
    await start_gui()  # Should return "already_running"
    await stop_gui()
    await stop_gui()  # Should still work


def test_main_function():
    """Test the main function."""
    from napari_mcp_server import main
    
    # Mock the server.run() method
    with patch('napari_mcp_server.server.run') as mock_run:
        main()
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_complex_code_execution():
    """Test complex code execution scenarios."""
    from napari_mcp_server import execute_code, init_viewer
    
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
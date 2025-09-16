"""Tests for the napari MCP control widget.

Tests the Qt widget interface for the MCP server using real Qt.
"""

import numpy as np
import pytest


class TestWidgetWithRealQt:
    """Test widget with real Qt and napari."""

    def test_widget_import(self):
        """Test that widget can be imported."""
        from napari_mcp.widget import MCPControlWidget

        assert MCPControlWidget is not None

    def test_widget_creation_with_viewer(self, make_napari_viewer, qtbot):
        """Test creating widget with real viewer."""
        from napari_mcp.widget import MCPControlWidget

        viewer = make_napari_viewer()
        widget = MCPControlWidget(viewer)
        qtbot.addWidget(widget)

        assert widget is not None
        assert widget.viewer is viewer
        assert hasattr(widget, "start_button")
        assert hasattr(widget, "stop_button")
        assert hasattr(widget, "status_label")

    def test_widget_initialization_properties(self, make_napari_viewer, qtbot):
        """Test widget initialization and properties."""
        from napari_mcp.widget import MCPControlWidget

        viewer = make_napari_viewer()
        widget = MCPControlWidget(viewer, port=8888)
        qtbot.addWidget(widget)

        assert widget.port == 8888
        assert widget.server is None
        assert widget.start_button.isEnabled() is True
        assert widget.stop_button.isEnabled() is False

    def test_server_lifecycle(self, make_napari_viewer, qtbot):
        """Test starting and stopping the server through widget."""
        from napari_mcp.widget import MCPControlWidget

        viewer = make_napari_viewer()
        widget = MCPControlWidget(viewer)
        qtbot.addWidget(widget)

        # Start server
        widget._start_server()
        assert widget.server is not None
        assert widget.start_button.isEnabled() is False
        assert widget.stop_button.isEnabled() is True

        # Stop server
        widget._stop_server()
        assert widget.start_button.isEnabled() is True
        assert widget.stop_button.isEnabled() is False

    def test_widget_with_napari_plugin_system(self, make_napari_viewer, qtbot):
        """Test widget works with napari plugin system."""
        from napari_mcp.widget import MCPControlWidget

        viewer = make_napari_viewer()

        # Create widget as napari would
        widget = MCPControlWidget(viewer)
        qtbot.addWidget(widget)

        assert widget is not None
        assert widget.viewer is viewer

        # Widget should be a QWidget
        assert hasattr(widget, "setLayout")
        assert hasattr(widget, "show")
        assert hasattr(widget, "close")


class TestWidgetIntegration:
    """Integration tests for widget with real napari."""

    def test_widget_add_to_viewer(self, make_napari_viewer, qtbot):
        """Test adding widget to napari viewer."""
        from napari_mcp.widget import MCPControlWidget

        viewer = make_napari_viewer()
        widget = MCPControlWidget(viewer)
        qtbot.addWidget(widget)

        # Add widget to viewer
        viewer.window.add_dock_widget(widget, name="MCP Control")

        # Widget should be in the viewer
        assert "MCP Control" in [w.name for w in viewer.window._dock_widgets.values()]

    def test_widget_operations_with_layers(self, make_napari_viewer, qtbot):
        """Test widget operations with layers in viewer."""
        from napari_mcp.widget import MCPControlWidget

        viewer = make_napari_viewer()

        # Add some layers
        viewer.add_image(np.random.rand(100, 100), name="test_image")
        viewer.add_labels(np.zeros((100, 100), dtype=int), name="test_labels")

        widget = MCPControlWidget(viewer)
        qtbot.addWidget(widget)

        assert widget.viewer.layers["test_image"] is not None
        assert widget.viewer.layers["test_labels"] is not None
        assert len(widget.viewer.layers) == 2

    def test_widget_cleanup(self, make_napari_viewer, qtbot):
        """Test widget cleanup on close."""
        from qtpy.QtCore import QEvent

        from napari_mcp.widget import MCPControlWidget

        viewer = make_napari_viewer()
        widget = MCPControlWidget(viewer)
        qtbot.addWidget(widget)

        # Start server
        widget._start_server()
        server = widget.server

        # Close widget
        close_event = QEvent(QEvent.Type.Close)
        widget.closeEvent(close_event)

        # Server should be stopped
        if server:
            assert not server.is_running

"""Tests for the napari MCP control widget.

Tests the Qt widget interface for the MCP server.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


@pytest.mark.unit
class TestWidgetImport:
    """Test widget module imports."""
    
    def test_widget_import(self):
        """Test that widget can be imported."""
        from napari_mcp.widget import MCPControlWidget
        assert MCPControlWidget is not None
    
    def test_widget_has_required_attributes(self):
        """Test widget has required napari plugin attributes."""
        from napari_mcp import widget
        
        # Check for napari plugin requirements
        assert hasattr(widget, "MCPControlWidget")


@pytest.mark.unit
class TestWidgetInitialization:
    """Test widget initialization."""
    
    def test_widget_creation_without_viewer(self):
        """Test creating widget without viewer."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            widget = MCPControlWidget()
            assert widget is not None
            assert widget.bridge_server is not None
    
    def test_widget_creation_with_viewer(self, viewer):
        """Test creating widget with viewer."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            widget = MCPControlWidget(viewer)
            assert widget is not None
            assert widget.viewer is viewer
            assert widget.bridge_server.viewer is viewer
    
    def test_widget_ui_setup(self):
        """Test widget UI setup."""
        with patch("napari_mcp.widget.QWidget"):
            with patch("napari_mcp.widget.QPushButton") as mock_button:
                with patch("napari_mcp.widget.QTextEdit") as mock_text:
                    with patch("napari_mcp.widget.QLabel") as mock_label:
                        from napari_mcp.widget import MCPControlWidget
                        
                        widget = MCPControlWidget()
                        
                        # Verify UI elements were created
                        mock_button.assert_called()
                        mock_text.assert_called()
                        mock_label.assert_called()


@pytest.mark.unit
class TestWidgetServerControl:
    """Test widget server control functionality."""
    
    @pytest.mark.asyncio
    async def test_start_server_button(self):
        """Test start server button functionality."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            widget = MCPControlWidget()
            widget.bridge_server = AsyncMock()
            widget.bridge_server.is_running = False
            
            # Simulate button click
            await widget.toggle_server()
            
            widget.bridge_server.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_server_button(self):
        """Test stop server button functionality."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            widget = MCPControlWidget()
            widget.bridge_server = AsyncMock()
            widget.bridge_server.is_running = True
            
            # Simulate button click
            await widget.toggle_server()
            
            widget.bridge_server.stop.assert_called_once()
    
    def test_server_status_display(self):
        """Test server status display updates."""
        with patch("napari_mcp.widget.QWidget"):
            with patch("napari_mcp.widget.QLabel") as mock_label:
                from napari_mcp.widget import MCPControlWidget
                
                widget = MCPControlWidget()
                widget.status_label = Mock()
                
                # Update status
                widget.update_status("Running")
                widget.status_label.setText.assert_called_with("Status: Running")


@pytest.mark.unit
class TestWidgetLogDisplay:
    """Test widget log display functionality."""
    
    def test_log_message_display(self):
        """Test displaying log messages."""
        with patch("napari_mcp.widget.QWidget"):
            with patch("napari_mcp.widget.QTextEdit") as mock_text:
                from napari_mcp.widget import MCPControlWidget
                
                widget = MCPControlWidget()
                widget.log_display = Mock()
                
                # Add log message
                widget.add_log("Test message")
                widget.log_display.append.assert_called_with("Test message")
    
    def test_clear_logs(self):
        """Test clearing log display."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            widget = MCPControlWidget()
            widget.log_display = Mock()
            
            # Clear logs
            widget.clear_logs()
            widget.log_display.clear.assert_called_once()
    
    def test_log_formatting(self):
        """Test log message formatting."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            from datetime import datetime
            
            widget = MCPControlWidget()
            widget.log_display = Mock()
            
            # Add formatted log
            message = "Test event"
            widget.add_log_with_timestamp(message)
            
            # Verify timestamp was added
            calls = widget.log_display.append.call_args_list
            assert len(calls) > 0
            logged_message = calls[0][0][0]
            assert message in logged_message


@pytest.mark.unit
class TestWidgetToolExecution:
    """Test executing tools through widget."""
    
    @pytest.mark.asyncio
    async def test_execute_tool_from_widget(self, viewer):
        """Test executing a tool from the widget interface."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            import numpy as np
            
            widget = MCPControlWidget(viewer)
            
            # Execute tool through widget's bridge
            result = await widget.bridge_server.tools.add_image_from_file(
                image_data=np.random.rand(10, 10).tolist(),
                name="widget_test"
            )
            
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_widget_tool_error_handling(self, viewer):
        """Test widget handles tool errors gracefully."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            widget = MCPControlWidget(viewer)
            widget.add_log = Mock()
            
            # Try invalid operation
            result = await widget.bridge_server.tools.remove_layer("nonexistent")
            
            assert result["success"] is False
            # Widget should log the error
            # Note: Actual implementation would need to connect to bridge signals


@pytest.mark.unit
class TestWidgetEventHandling:
    """Test widget event handling."""
    
    def test_widget_close_event(self):
        """Test widget cleanup on close."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            widget = MCPControlWidget()
            widget.bridge_server = Mock()
            widget.bridge_server.stop = AsyncMock()
            
            # Simulate close event
            event = Mock()
            widget.closeEvent(event)
            
            # Verify cleanup
            event.accept.assert_called_once()
    
    def test_widget_viewer_connection(self, viewer):
        """Test widget connects to viewer events."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            widget = MCPControlWidget(viewer)
            
            # Widget should be connected to viewer
            assert widget.viewer is viewer
            assert widget.bridge_server.viewer is viewer


@pytest.mark.integration
class TestWidgetIntegration:
    """Integration tests for widget functionality."""
    
    @pytest.mark.asyncio
    async def test_widget_full_workflow(self, viewer):
        """Test complete workflow through widget."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            import numpy as np
            
            widget = MCPControlWidget(viewer)
            
            # Start server
            widget.bridge_server.is_running = False
            await widget.toggle_server()
            
            # Execute operations
            await widget.bridge_server.tools.add_image_from_file(
                image_data=np.random.rand(50, 50).tolist(),
                name="test1"
            )
            await widget.bridge_server.tools.add_labels_layer(
                labels_data=np.random.randint(0, 5, size=(50, 50)).tolist(),
                name="test2"
            )
            
            # Get status
            info = await widget.bridge_server.tools.session_information()
            assert info["viewer_info"]["n_layers"] == 2
            
            # Stop server
            widget.bridge_server.is_running = True
            await widget.toggle_server()
    
    def test_widget_with_napari_plugin_system(self):
        """Test widget works with napari plugin system."""
        with patch("napari_mcp.widget.QWidget"):
            from napari_mcp.widget import MCPControlWidget
            
            # Simulate napari calling the widget factory
            widget = MCPControlWidget()
            assert widget is not None
            
            # Widget should be a QWidget
            assert hasattr(widget, "setLayout")
            assert hasattr(widget, "show")


@pytest.mark.gui
class TestWidgetWithQt:
    """Test widget with Qt."""
    
    def test_widget_creation_with_qt(self, qt_app, make_napari_viewer):
        """Test creating widget with Qt."""
        from napari_mcp.widget import MCPControlWidget
            
        # Create viewer
        viewer = make_napari_viewer()
        
        # Create widget
        widget = MCPControlWidget(viewer)
        assert widget is not None
        
        # Widget should have Qt properties
        assert hasattr(widget, "size")
        assert hasattr(widget, "isVisible")
    
    @pytest.mark.asyncio
    async def test_widget_server_control(self, qt_app, make_napari_viewer):
        """Test widget server control."""
        from napari_mcp.widget import MCPControlWidget
            
        viewer = make_napari_viewer()
        
        widget = MCPControlWidget(viewer)
        
        # Test server control
        await widget.toggle_server()  # Start
        assert widget.bridge_server.is_running
        
        await widget.toggle_server()  # Stop
        assert not widget.bridge_server.is_running


@pytest.mark.unit
class TestWidgetAccessibility:
    """Test widget accessibility features."""
    
    def test_widget_tooltips(self):
        """Test widget has helpful tooltips."""
        with patch("napari_mcp.widget.QWidget"):
            with patch("napari_mcp.widget.QPushButton") as mock_button:
                from napari_mcp.widget import MCPControlWidget
                
                widget = MCPControlWidget()
                
                # Verify tooltips are set
                for call in mock_button.return_value.setToolTip.call_args_list:
                    tooltip = call[0][0]
                    assert len(tooltip) > 0
    
    def test_widget_labels(self):
        """Test widget has descriptive labels."""
        with patch("napari_mcp.widget.QWidget"):
            with patch("napari_mcp.widget.QLabel") as mock_label:
                from napari_mcp.widget import MCPControlWidget
                
                widget = MCPControlWidget()
                
                # Verify labels are created with text
                assert mock_label.called
                for call in mock_label.call_args_list:
                    if call[0]:  # If args provided
                        label_text = call[0][0]
                        assert isinstance(label_text, str)
                        assert len(label_text) > 0
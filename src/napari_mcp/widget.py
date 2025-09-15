"""MCP Control Widget for napari."""

from __future__ import annotations

import napari
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .bridge_server import NapariBridgeServer


class MCPControlWidget(QWidget):
    """Widget to control MCP server for current napari viewer."""

    def __init__(self, napari_viewer: napari.Viewer = None, port: int = 9999):
        """Initialize the MCP control widget.

        Parameters
        ----------
        napari_viewer : napari.Viewer, optional
            The napari viewer instance. If not provided, will get current viewer.
        port : int, optional
            Port to run the MCP server on. Default is 9999.
        """
        super().__init__()
        # Get the current viewer if not provided
        self.viewer = napari_viewer or napari.current_viewer()
        if self.viewer is None:
            raise RuntimeError("No napari viewer found")

        self.server = None
        self.port = port
        self._setup_ui()

        # Timer to update status
        self.status_timer = QTimer(self)  # Set parent for proper cleanup
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("MCP Server Control")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Status group
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("Server: Stopped")
        self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        status_layout.addWidget(self.status_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Configuration group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()

        # Port configuration
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(self.port)
        self.port_spin.valueChanged.connect(self._on_port_changed)
        port_layout.addWidget(self.port_spin)
        port_layout.addStretch()
        config_layout.addLayout(port_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Server")
        self.start_button.clicked.connect(self._start_server)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Server")
        self.stop_button.clicked.connect(self._stop_server)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)

        # Connection info
        info_group = QGroupBox("Connection Information")
        info_layout = QVBoxLayout()

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setPlainText(
            "Server not running.\n\n"
            "Start the server to expose this napari viewer to MCP clients."
        )
        info_layout.addWidget(self.info_text)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Instructions
        instructions = QLabel(
            "Use this widget to expose your current napari viewer\n"
            "to AI assistants via the Model Context Protocol (MCP)."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
        layout.addWidget(instructions)

        layout.addStretch()
        self.setLayout(layout)

    def _on_port_changed(self, value: int):
        """Handle port change."""
        self.port = value
        if self.server and self.server.is_running:
            self.info_text.append("Note: Port change will take effect after restart.")

    def _start_server(self):
        """Start the MCP server."""
        if not self.server or not self.server.is_running:
            self.server = NapariBridgeServer(self.viewer, port=self.port)
            if self.server.start():
                self._update_ui_state(running=True)
                self.info_text.setPlainText(
                    f"Server running on port {self.port}\n\n"
                    f"Connection URL: http://localhost:{self.port}/mcp\n\n"
                    f"To connect from napari-mcp:\n"
                    f"  Use the --external flag or set NAPARI_MCP_USE_EXTERNAL=true\n\n"
                    f"The MCP client will automatically detect and use this viewer."
                )

    def _stop_server(self):
        """Stop the MCP server."""
        if self.server:
            self.server.stop()
            self._update_ui_state(running=False)
            self.info_text.setPlainText(
                "Server stopped.\n\n"
                "Start the server to expose this napari viewer to MCP clients."
            )

    def _update_ui_state(self, running: bool):
        """Update UI based on server state."""
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.port_spin.setEnabled(not running)

        if running:
            self.status_label.setText(f"Server: Running (Port {self.port})")
            self.status_label.setStyleSheet(
                "QLabel { color: green; font-weight: bold; }"
            )
        else:
            self.status_label.setText("Server: Stopped")
            self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")

    def _update_status(self):
        """Update status display."""
        if self.server:
            self._update_ui_state(self.server.is_running)

    def closeEvent(self, event):
        """Clean up when widget is closed."""
        try:
            if self.status_timer and self.status_timer.isActive():
                self.status_timer.stop()
        except Exception:
            pass

        try:
            if self.server and self.server.is_running:
                self.server.stop()
        except Exception:
            pass

        try:
            super().closeEvent(event)
        except Exception:
            # Accept generic events in tests that may not send QCloseEvent
            try:
                event.accept()
            except Exception:
                pass

"""Napari MCP - Model Context Protocol server for napari viewer control."""

__version__ = "0.1.0"

# Import main components
from .base import NapariMCPTools
from .bridge_server import NapariBridgeServer
from .server import main as server_main
from .widget import MCPControlWidget

__all__ = [
    "NapariMCPTools",
    "NapariBridgeServer",
    "MCPControlWidget",
    "server_main",
]

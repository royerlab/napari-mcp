"""Napari MCP Bridge Plugin."""

__version__ = "0.1.0"

# Import modules to make them accessible
from . import widget
from . import server

__all__ = ["widget", "server"]
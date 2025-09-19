"""Napari MCP - Model Context Protocol server for napari viewer control."""

# Version is provided by setuptools_scm; fall back to package metadata if needed
try:
    from ._version import version as __version__  # type: ignore
except Exception:  # pragma: no cover - fallback path
    try:
        from importlib.metadata import version as _get_version

        __version__ = _get_version("napari-mcp")
    except Exception:
        __version__ = "0.0.0"

# Import main components
from .bridge_server import NapariBridgeServer
from .server import NapariMCPTools
from .server import main as server_main
from .widget import MCPControlWidget

__all__ = [
    "NapariMCPTools",
    "NapariBridgeServer",
    "MCPControlWidget",
    "server_main",
]

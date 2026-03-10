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
from .server import create_server
from .server import main as server_main
from .state import ServerState, StartupMode
from .viewer_protocol import ViewerProtocol

# Qt-dependent components may not be available in headless environments
try:
    from .bridge_server import NapariBridgeServer
    from .widget import MCPControlWidget
except ImportError:  # pragma: no cover
    NapariBridgeServer = None  # type: ignore[assignment,misc]
    MCPControlWidget = None  # type: ignore[assignment,misc]

__all__ = [
    "NapariBridgeServer",
    "MCPControlWidget",
    "ServerState",
    "StartupMode",
    "ViewerProtocol",
    "create_server",
    "server_main",
]

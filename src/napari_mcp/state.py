"""Server state management for napari-mcp."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class StartupMode(Enum):
    """Server startup mode for external viewer detection."""

    STANDALONE = "standalone"
    AUTO_DETECT = "auto-detect"


class ServerState:
    """Encapsulates all mutable state for one MCP server instance.

    Replaces the module-level globals that previously lived in server.py.
    """

    def __init__(
        self,
        mode: StartupMode = StartupMode.STANDALONE,
        bridge_port: int | None = None,
    ):
        # Viewer
        self.viewer: Any | None = None
        self.viewer_lock: asyncio.Lock = asyncio.Lock()

        # Mode
        self.mode: StartupMode = mode
        self.bridge_port: int = bridge_port or int(
            os.environ.get("NAPARI_MCP_BRIDGE_PORT", "9999")
        )

        # Qt state
        self.qt_app: Any | None = None
        self.qt_pump_task: asyncio.Task | None = None
        self.window_close_connected: bool = False
        self.gui_executor: Any | None = None

        # Execution namespace (persists across execute_code calls)
        self.exec_globals: dict[str, Any] = {}

        # Output storage
        self.output_storage: dict[str, dict[str, Any]] = {}
        self.output_storage_lock: asyncio.Lock = asyncio.Lock()
        self.next_output_id: int = 1
        try:
            self.max_output_items: int = int(
                os.environ.get("NAPARI_MCP_MAX_OUTPUT_ITEMS", "1000")
            )
        except Exception:
            self.max_output_items = 1000

    def gui_execute(self, operation: Any) -> Any:
        """Run operation through GUI executor if set, else directly."""
        if self.gui_executor is not None:
            return self.gui_executor(operation)
        return operation()

    async def store_output(
        self,
        tool_name: str,
        stdout: str = "",
        stderr: str = "",
        result_repr: str | None = None,
        **metadata: Any,
    ) -> str:
        """Store tool output and return a unique ID."""
        async with self.output_storage_lock:
            output_id = str(self.next_output_id)
            self.next_output_id += 1

            self.output_storage[output_id] = {
                "tool_name": tool_name,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "stdout": stdout,
                "stderr": stderr,
                "result_repr": result_repr,
                **metadata,
            }
            # Evict oldest items if exceeding capacity
            if (
                self.max_output_items > 0
                and len(self.output_storage) > self.max_output_items
            ):
                overflow = len(self.output_storage) - self.max_output_items
                for victim in sorted(self.output_storage.keys(), key=lambda k: int(k))[
                    :overflow
                ]:
                    self.output_storage.pop(victim, None)

            return output_id

    async def proxy_to_external(
        self, tool_name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Proxy a tool call to an external viewer if in AUTO_DETECT mode.

        Returns None immediately in STANDALONE mode (zero overhead).
        """
        if self.mode != StartupMode.AUTO_DETECT:
            return None

        try:
            from fastmcp import Client

            client = Client(f"http://localhost:{self.bridge_port}/mcp")
            async with client:
                result = await client.call_tool(tool_name, params or {})
                if hasattr(result, "content"):
                    content = result.content
                    if content[0].type == "text":
                        response = (
                            content[0].text
                            if hasattr(content[0], "text")
                            else str(content[0])
                        )
                        try:
                            return json.loads(response)
                        except json.JSONDecodeError:
                            return {
                                "status": "error",
                                "message": f"Invalid JSON response: {response}",
                            }
                    else:
                        return content
                return {
                    "status": "error",
                    "message": "Invalid response format from external viewer",
                }
        except Exception:
            return None

    async def detect_external_viewer(
        self,
    ) -> tuple[Any | None, dict[str, Any] | None]:
        """Detect if an external napari viewer is available via MCP bridge."""
        if self.mode != StartupMode.AUTO_DETECT:
            return None, None

        try:
            from fastmcp import Client

            client = Client(f"http://localhost:{self.bridge_port}/mcp")
            async with client:
                result = await client.call_tool("session_information")
                if result and hasattr(result, "content"):
                    content = result.content
                    if isinstance(content, list) and len(content) > 0:
                        info = (
                            content[0].text
                            if hasattr(content[0], "text")
                            else str(content[0])
                        )
                        info_dict = json.loads(info) if isinstance(info, str) else info
                        if info_dict.get("session_type") == "napari_bridge_session":
                            return client, info_dict
                return None, None
        except Exception:
            return None, None

    async def external_session_information(self) -> dict[str, Any]:
        """Get session information from the external viewer."""
        from fastmcp import Client

        test_client = Client(f"http://localhost:{self.bridge_port}/mcp")
        async with test_client:
            result = await test_client.call_tool("session_information")
            if hasattr(result, "content"):
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    info = (
                        content[0].text
                        if hasattr(content[0], "text")
                        else str(content[0])
                    )
                    info_dict = json.loads(info) if isinstance(info, str) else info
                    if info_dict.get("session_type") == "napari_bridge_session":
                        return {
                            "status": "ok",
                            "viewer_type": "external",
                            "title": info_dict.get("viewer", {}).get(
                                "title", "External Viewer"
                            ),
                            "layers": info_dict.get("viewer", {}).get(
                                "layer_names", []
                            ),
                            "port": info_dict.get("bridge_port", self.bridge_port),
                        }

        return {
            "status": "error",
            "message": "Failed to get session information from external viewer",
        }

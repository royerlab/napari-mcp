#!/usr/bin/env python
"""Test script for napari-mcp-bridge plugin."""

import asyncio
import sys

from fastmcp import Client


async def test_external_viewer():
    """Test connecting to external viewer via bridge."""
    print("Testing napari-mcp-bridge connection...")

    try:
        # Try to connect to the bridge server
        client = Client("http://localhost:9999/mcp")

        print("Attempting to connect to bridge server...")
        async with client:
            # Get session information
            result = await client.call_tool("session_information")
            print(f"Connected! Session info: {result}")

            # List layers
            layers = await client.call_tool("list_layers")
            print(f"Current layers: {layers}")

            # Take a screenshot
            screenshot = await client.call_tool("screenshot")
            screenshot_length = (
                len(screenshot.get("base64_data", ""))
                if isinstance(screenshot, dict)
                else "N/A"
            )
            print(f"Screenshot taken (base64 length: {screenshot_length})")

            print("\nBridge server is working correctly!")
            return True

    except Exception as e:
        print(f"Failed to connect to bridge server: {e}")
        print("\nMake sure:")
        print("1. napari is running")
        print("2. The napari-mcp-bridge plugin is loaded")
        print("3. The MCP server is started in the plugin widget")
        return False


async def test_main_server_detection():
    """Test if main server can detect external viewer."""
    print("\nTesting main server detection of external viewer...")

    # Import the detection function
    sys.path.insert(0, "src")
    from napari_mcp_server import _detect_external_viewer

    client, info = await _detect_external_viewer()
    if client:
        print("External viewer detected!")
        print(f"Info: {info}")
        await client.close()
        return True
    else:
        print("No external viewer detected")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("napari-mcp-bridge Test Suite")
    print("=" * 60)

    # Test 1: Direct connection to bridge
    bridge_ok = await test_external_viewer()

    # Test 2: Detection from main server
    if bridge_ok:
        detection_ok = await test_main_server_detection()
    else:
        print("\nSkipping detection test (bridge not available)")
        detection_ok = False

    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Bridge connection: {'✓' if bridge_ok else '✗'}")
    print(f"  Main server detection: {'✓' if detection_ok else '✗'}")
    print("=" * 60)

    return bridge_ok and detection_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

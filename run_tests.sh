#!/bin/bash
# Run tests for napari-mcp and napari-mcp-bridge

echo "=================================="
echo "Running napari-mcp Tests"
echo "=================================="

# Test boolean parsing
echo -e "\n📝 Testing boolean parsing..."
uv run pytest tests/test_external_viewer.py::TestBooleanParsing -q

# Test external viewer detection
echo -e "\n🔍 Testing external viewer detection..."
uv run pytest tests/test_external_viewer.py::TestExternalViewerDetection -q

# Test proxy functionality
echo -e "\n🔄 Testing proxy functionality..."
uv run pytest tests/test_external_viewer.py::TestProxyFunctionality -q

# Test bridge server
echo -e "\n🌉 Testing bridge server..."
uv run pytest tests/test_bridge_simplified.py -q

# Test integration
echo -e "\n🔗 Testing integration..."
uv run pytest tests/test_integration.py -q

echo -e "\n=================================="
echo "Test Summary"
echo "=================================="

# Run all tests with summary (excluding GUI tests)
uv run pytest tests/ -m "not realgui" --tb=no -q

echo -e "\nNote: Real GUI tests not included."
echo "Run ./run_realgui_tests.sh for real napari GUI integration tests."
echo -e "\nDone!"
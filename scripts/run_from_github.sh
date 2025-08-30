#!/bin/bash
# Napari MCP Server - Run Latest Version Directly from GitHub
# This script always downloads and runs the latest version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Napari MCP Server - GitHub Runner${NC}"
echo -e "${BLUE}Always runs the latest version from GitHub${NC}"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
SERVER_FILE="$TEMP_DIR/napari_mcp_server.py"

# Download latest version
echo -e "${YELLOW}📥 Downloading latest version from GitHub...${NC}"
curl -o "$SERVER_FILE" https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Downloaded latest napari_mcp_server.py${NC}"
else
    echo -e "${RED}❌ Failed to download server file${NC}"
    exit 1
fi

# Make sure file is executable
chmod +x "$SERVER_FILE"

echo -e "${BLUE}🔧 Starting server with latest version from GitHub${NC}"
echo ""

# Cleanup function
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up temporary files...${NC}"
    rm -rf "$TEMP_DIR"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Show the command being run
echo -e "${YELLOW}Running:${NC}"
echo "uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy fastmcp run $SERVER_FILE"
echo ""

# Run the server
exec uv run \
    --with Pillow \
    --with PyQt6 \
    --with fastmcp \
    --with imageio \
    --with napari \
    --with numpy \
    --with qtpy \
    fastmcp run "$SERVER_FILE"

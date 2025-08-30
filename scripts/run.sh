#!/bin/bash
# Napari MCP Server - Zero Install Runner
# Usage: ./scripts/run.sh [path/to/napari_mcp_server.py]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Napari MCP Server - Zero Install Runner${NC}"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Determine server file path
SERVER_FILE=${1:-"src/napari_mcp_server.py"}

# If file doesn't exist locally, try to download it
if [ ! -f "$SERVER_FILE" ]; then
    echo -e "${YELLOW}📥 Server file not found locally, downloading...${NC}"
    SERVER_FILE="napari_mcp_server.py"
    curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Downloaded napari_mcp_server.py${NC}"
    else
        echo -e "${RED}❌ Failed to download server file${NC}"
        exit 1
    fi
fi

# Make sure file is executable
chmod +x "$SERVER_FILE"

echo -e "${BLUE}🔧 Starting server with file: $SERVER_FILE${NC}"
echo ""

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

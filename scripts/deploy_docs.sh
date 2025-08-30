#!/bin/bash
# Deploy napari-mcp documentation to HPC website
# Usage: ./scripts/deploy_docs.sh [--dry-run]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_PATH="/hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp"
BUILD_DIR="site"
DRY_RUN=false

# Parse arguments
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}🧪 DRY RUN MODE - No files will be copied${NC}"
fi

echo -e "${BLUE}🚀 Napari MCP Documentation Deployment${NC}"
echo -e "${BLUE}Target: $DEPLOY_PATH${NC}"
echo ""

# Check if we're in the right directory
if [[ ! -f "mkdocs.yml" ]]; then
    echo -e "${RED}❌ Error: mkdocs.yml not found${NC}"
    echo "Run this script from the napari-mcp root directory"
    exit 1
fi

# Check if deployment path exists
if [[ ! -d "$DEPLOY_PATH" ]]; then
    echo -e "${RED}❌ Error: Deployment path does not exist${NC}"
    echo "Path: $DEPLOY_PATH"
    echo "Please create the directory or check your HPC access"
    exit 1
fi

# Check if we can write to deployment path
if [[ ! -w "$DEPLOY_PATH" ]]; then
    echo -e "${RED}❌ Error: No write permission to deployment path${NC}"
    echo "Path: $DEPLOY_PATH"
    echo "Check your permissions or contact HPC admin"
    exit 1
fi

# Check dependencies
echo -e "${YELLOW}🔍 Checking dependencies...${NC}"

if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install documentation dependencies if needed
echo -e "${YELLOW}📦 Installing documentation dependencies...${NC}"
uv pip install -r requirements-docs.txt > /dev/null 2>&1

# Clean any existing build
echo -e "${YELLOW}🧹 Cleaning previous build...${NC}"
if [[ -d "$BUILD_DIR" ]]; then
    rm -rf "$BUILD_DIR"
fi

# Build documentation
echo -e "${YELLOW}🏗️ Building documentation...${NC}"
if uv run mkdocs build --strict; then
    echo -e "${GREEN}✅ Documentation built successfully${NC}"
else
    echo -e "${RED}❌ Documentation build failed${NC}"
    echo "Check the errors above and fix before deploying"
    exit 1
fi

# Verify build directory exists and has content
if [[ ! -d "$BUILD_DIR" ]] || [[ -z "$(ls -A $BUILD_DIR)" ]]; then
    echo -e "${RED}❌ Build directory is empty or missing${NC}"
    exit 1
fi

# Show build stats
echo -e "${BLUE}📊 Build Statistics:${NC}"
echo "  Files: $(find $BUILD_DIR -type f | wc -l | tr -d ' ')"
echo "  Size: $(du -sh $BUILD_DIR | cut -f1)"
echo "  Index: $(ls -la $BUILD_DIR/index.html | cut -d' ' -f5-) bytes"

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo -e "${YELLOW}🧪 DRY RUN: Would deploy the following files:${NC}"
    find "$BUILD_DIR" -type f | head -10
    total_files=$(find "$BUILD_DIR" -type f | wc -l | tr -d ' ')
    if [[ $total_files -gt 10 ]]; then
        echo "... and $(($total_files - 10)) more files"
    fi
    echo ""
    echo -e "${YELLOW}Target directory: $DEPLOY_PATH${NC}"
    echo -e "${YELLOW}Run without --dry-run to perform actual deployment${NC}"
    exit 0
fi

# Backup existing deployment (if it exists)
echo -e "${YELLOW}📋 Creating backup...${NC}"
BACKUP_DIR="${DEPLOY_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
if [[ -d "$DEPLOY_PATH" ]] && [[ -n "$(ls -A $DEPLOY_PATH)" ]]; then
    cp -r "$DEPLOY_PATH" "$BACKUP_DIR"
    echo -e "${GREEN}✅ Backup created: $BACKUP_DIR${NC}"
else
    echo "  No existing content to backup"
fi

# Deploy documentation
echo -e "${YELLOW}🚀 Deploying documentation...${NC}"

# Create target directory if it doesn't exist
mkdir -p "$DEPLOY_PATH"

# Copy built site to deployment path
if cp -r "$BUILD_DIR"/* "$DEPLOY_PATH/"; then
    echo -e "${GREEN}✅ Documentation deployed successfully${NC}"
else
    echo -e "${RED}❌ Deployment failed${NC}"
    echo "Restoring from backup if available..."
    if [[ -d "$BACKUP_DIR" ]]; then
        rm -rf "$DEPLOY_PATH"
        mv "$BACKUP_DIR" "$DEPLOY_PATH"
        echo -e "${YELLOW}⚠️ Restored from backup${NC}"
    fi
    exit 1
fi

# Set proper permissions
echo -e "${YELLOW}🔐 Setting permissions...${NC}"
chmod -R 755 "$DEPLOY_PATH"
find "$DEPLOY_PATH" -type f -name "*.html" -exec chmod 644 {} \;
find "$DEPLOY_PATH" -type f -name "*.css" -exec chmod 644 {} \;
find "$DEPLOY_PATH" -type f -name "*.js" -exec chmod 644 {} \;

# Verify deployment
echo -e "${YELLOW}🔍 Verifying deployment...${NC}"
if [[ -f "$DEPLOY_PATH/index.html" ]]; then
    echo -e "${GREEN}✅ index.html exists${NC}"
else
    echo -e "${RED}❌ index.html missing${NC}"
    exit 1
fi

# Show deployment info
echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${BLUE}📍 Location: $DEPLOY_PATH${NC}"
echo -e "${BLUE}📊 Files deployed: $(find $DEPLOY_PATH -type f | wc -l | tr -d ' ')${NC}"
echo -e "${BLUE}💾 Total size: $(du -sh $DEPLOY_PATH | cut -f1)${NC}"

# Show cleanup backup option
if [[ -d "$BACKUP_DIR" ]]; then
    echo ""
    echo -e "${YELLOW}📝 Note: Backup created at $BACKUP_DIR${NC}"
    echo -e "${YELLOW}💡 Remove with: rm -rf $BACKUP_DIR${NC}"
fi

# Show access URL (if applicable)
echo ""
echo -e "${GREEN}🌐 Documentation should be available at:${NC}"
echo -e "${BLUE}   https://onsite.czbiohub.org/royerlab/napari-mcp${NC}"

# Clean up local build directory
echo ""
echo -e "${YELLOW}🧹 Cleaning up local build...${NC}"
rm -rf "$BUILD_DIR"
echo -e "${GREEN}✅ Local cleanup complete${NC}"

echo ""
echo -e "${GREEN}🎊 Documentation deployment successful!${NC}"
echo -e "${GREEN}   Your napari-mcp docs are now live on the HPC website.${NC}"

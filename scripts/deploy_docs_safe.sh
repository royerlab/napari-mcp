#!/bin/bash
# Safe deployment script for napari-mcp documentation to HPC
# Includes additional safety checks and rollback capabilities

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_PATH="/hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp"
BUILD_DIR="site"
STAGING_DIR="${DEPLOY_PATH}_staging"
DRY_RUN=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--force] [--help]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be deployed without actually doing it"
            echo "  --force      Skip safety prompts and deploy immediately"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    Napari MCP Documentation Deployment                      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📍 Target: $DEPLOY_PATH${NC}"
if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}🧪 Mode: DRY RUN (no changes will be made)${NC}"
else
    echo -e "${GREEN}🚀 Mode: LIVE DEPLOYMENT${NC}"
fi
echo ""

# Safety checks
echo -e "${YELLOW}🔍 Running pre-deployment checks...${NC}"

# 1. Check if we're in the right directory
if [[ ! -f "mkdocs.yml" ]]; then
    echo -e "${RED}❌ Error: mkdocs.yml not found${NC}"
    echo "Run this script from the napari-mcp root directory"
    exit 1
fi

# 2. Check Git status
if [[ -d ".git" ]]; then
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}⚠️ Warning: You have uncommitted changes${NC}"
        if [[ "$FORCE" != "true" && "$DRY_RUN" != "true" ]]; then
            read -p "Deploy anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${YELLOW}📝 Commit your changes first, then re-run deployment${NC}"
                exit 1
            fi
        fi
    fi

    # Show current commit info
    echo -e "${BLUE}📝 Current commit:${NC}"
    echo "   $(git log --oneline -1)"
fi

# 3. Check deployment path exists and is writable
if [[ ! -d "$DEPLOY_PATH" ]]; then
    echo -e "${YELLOW}📁 Creating deployment directory: $DEPLOY_PATH${NC}"
    if [[ "$DRY_RUN" != "true" ]]; then
        mkdir -p "$DEPLOY_PATH"
    fi
elif [[ ! -w "$DEPLOY_PATH" ]]; then
    echo -e "${RED}❌ Error: No write permission to $DEPLOY_PATH${NC}"
    echo "Check your permissions or contact HPC admin"
    exit 1
fi

# 4. Check dependencies
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✅ All pre-deployment checks passed${NC}"
echo ""

# Install/update documentation dependencies
echo -e "${YELLOW}📦 Installing documentation dependencies...${NC}"
if [[ "$DRY_RUN" != "true" ]]; then
    uv pip install -r requirements-docs.txt > /dev/null 2>&1
fi
echo -e "${GREEN}✅ Dependencies ready${NC}"

# Clean any existing build
echo -e "${YELLOW}🧹 Cleaning previous build...${NC}"
if [[ -d "$BUILD_DIR" ]]; then
    rm -rf "$BUILD_DIR"
fi

# Build documentation
echo -e "${YELLOW}🏗️ Building documentation...${NC}"
if [[ "$DRY_RUN" == "true" ]]; then
    echo "   Would run: mkdocs build --strict"
else
    if uv run mkdocs build --strict; then
        echo -e "${GREEN}✅ Documentation built successfully${NC}"
    else
        echo -e "${RED}❌ Documentation build failed${NC}"
        echo "Fix the errors above before deploying"
        exit 1
    fi
fi

# Verify build
if [[ "$DRY_RUN" != "true" ]]; then
    if [[ ! -d "$BUILD_DIR" ]] || [[ -z "$(ls -A $BUILD_DIR)" ]]; then
        echo -e "${RED}❌ Build directory is empty or missing${NC}"
        exit 1
    fi

    # Check for critical files
    critical_files=("index.html" "search/search_index.json" "assets")
    for file in "${critical_files[@]}"; do
        if [[ ! -e "$BUILD_DIR/$file" ]]; then
            echo -e "${RED}❌ Critical file missing: $file${NC}"
            exit 1
        fi
    done
fi

# Show build statistics
echo -e "${BLUE}📊 Build Information:${NC}"
if [[ "$DRY_RUN" != "true" ]]; then
    file_count=$(find "$BUILD_DIR" -type f | wc -l | tr -d ' ')
    build_size=$(du -sh "$BUILD_DIR" 2>/dev/null | cut -f1 || echo "unknown")
    echo "   Files: $file_count"
    echo "   Size: $build_size"
    echo "   Index: $(stat -f%z "$BUILD_DIR/index.html" 2>/dev/null || echo "unknown") bytes"
else
    echo "   Would build documentation with mkdocs"
fi

# Staging deployment
echo ""
echo -e "${YELLOW}📦 Staging deployment...${NC}"
if [[ "$DRY_RUN" == "true" ]]; then
    echo "   Would copy $BUILD_DIR/* to $STAGING_DIR"
else
    # Create staging directory
    rm -rf "$STAGING_DIR"
    mkdir -p "$STAGING_DIR"

    # Copy to staging
    cp -r "$BUILD_DIR"/* "$STAGING_DIR/"
    echo -e "${GREEN}✅ Files staged successfully${NC}"
fi

# Show what will be deployed
echo ""
echo -e "${BLUE}📋 Deployment Preview:${NC}"
if [[ "$DRY_RUN" == "true" ]]; then
    echo "   Would deploy to: $DEPLOY_PATH"
    echo "   Files to deploy: (build output)"
else
    echo "   Deploying from: $STAGING_DIR"
    echo "   Deploying to: $DEPLOY_PATH"
    echo "   Sample files:"
    ls -la "$STAGING_DIR" | head -5
fi

# Final confirmation for live deployment
if [[ "$DRY_RUN" != "true" && "$FORCE" != "true" ]]; then
    echo ""
    echo -e "${YELLOW}⚠️ Ready to deploy to HPC website${NC}"
    echo -e "${YELLOW}   This will replace the current documentation${NC}"
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}📝 Deployment cancelled${NC}"
        rm -rf "$STAGING_DIR"
        exit 0
    fi
fi

# Create backup of current deployment
echo ""
echo -e "${YELLOW}💾 Creating backup of current deployment...${NC}"
BACKUP_DIR="${DEPLOY_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
if [[ "$DRY_RUN" != "true" ]]; then
    if [[ -d "$DEPLOY_PATH" ]] && [[ -n "$(ls -A $DEPLOY_PATH)" ]]; then
        cp -r "$DEPLOY_PATH" "$BACKUP_DIR"
        echo -e "${GREEN}✅ Backup created: $BACKUP_DIR${NC}"
    else
        echo "   No existing content to backup"
    fi
fi

# Deploy to production
echo -e "${YELLOW}🚀 Deploying to production...${NC}"
if [[ "$DRY_RUN" != "true" ]]; then
    # Clear existing content
    rm -rf "${DEPLOY_PATH:?}"/*

    # Copy from staging
    if cp -r "$STAGING_DIR"/* "$DEPLOY_PATH/"; then
        echo -e "${GREEN}✅ Files deployed successfully${NC}"
    else
        echo -e "${RED}❌ Deployment failed${NC}"
        # Attempt rollback
        if [[ -d "$BACKUP_DIR" ]]; then
            echo -e "${YELLOW}🔄 Attempting rollback...${NC}"
            rm -rf "${DEPLOY_PATH:?}"/*
            cp -r "$BACKUP_DIR"/* "$DEPLOY_PATH/"
            echo -e "${YELLOW}⚠️ Rolled back to previous version${NC}"
        fi
        exit 1
    fi
fi

# Set proper permissions
echo -e "${YELLOW}🔐 Setting file permissions...${NC}"
if [[ "$DRY_RUN" != "true" ]]; then
    # Set directory permissions
    find "$DEPLOY_PATH" -type d -exec chmod 755 {} \;

    # Set file permissions
    find "$DEPLOY_PATH" -type f -name "*.html" -exec chmod 644 {} \;
    find "$DEPLOY_PATH" -type f -name "*.css" -exec chmod 644 {} \;
    find "$DEPLOY_PATH" -type f -name "*.js" -exec chmod 644 {} \;
    find "$DEPLOY_PATH" -type f -name "*.png" -exec chmod 644 {} \;
    find "$DEPLOY_PATH" -type f -name "*.svg" -exec chmod 644 {} \;
    find "$DEPLOY_PATH" -type f -name "*.json" -exec chmod 644 {} \;

    echo -e "${GREEN}✅ Permissions set${NC}"
fi

# Final verification
echo -e "${YELLOW}🧪 Final verification...${NC}"
if [[ "$DRY_RUN" != "true" ]]; then
    # Check critical files exist
    critical_files=("$DEPLOY_PATH/index.html" "$DEPLOY_PATH/search/search_index.json")
    for file in "${critical_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            echo -e "${RED}❌ Critical file missing after deployment: $file${NC}"
            exit 1
        fi
    done

    # Check file count
    deployed_count=$(find "$DEPLOY_PATH" -type f | wc -l | tr -d ' ')
    if [[ $deployed_count -lt 10 ]]; then
        echo -e "${YELLOW}⚠️ Warning: Only $deployed_count files deployed (seems low)${NC}"
    fi

    echo -e "${GREEN}✅ Deployment verification passed${NC}"
fi

# Cleanup
echo -e "${YELLOW}🧹 Cleaning up temporary files...${NC}"
if [[ "$DRY_RUN" != "true" ]]; then
    rm -rf "$STAGING_DIR"
    rm -rf "$BUILD_DIR"
fi

# Success summary
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                           DEPLOYMENT SUCCESSFUL!                            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}🎉 Napari MCP documentation deployed successfully!${NC}"
echo ""
echo -e "${BLUE}📍 Location: $DEPLOY_PATH${NC}"
echo -e "${BLUE}🌐 URL: https://onsite.czbiohub.org/royerlab/napari-mcp${NC}"
if [[ -d "$BACKUP_DIR" ]]; then
    echo -e "${BLUE}💾 Backup: $BACKUP_DIR${NC}"
fi
echo ""
echo -e "${YELLOW}💡 Next steps:${NC}"
echo -e "${YELLOW}   1. Verify the site loads correctly in your browser${NC}"
echo -e "${YELLOW}   2. Test navigation and links${NC}"
echo -e "${YELLOW}   3. Share the URL with your team!${NC}"
echo ""
echo -e "${GREEN}Happy documenting! 📚✨${NC}"

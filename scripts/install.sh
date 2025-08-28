#!/bin/bash

# Napari MCP Server Automatic Installer
# Installs and configures napari MCP server for various AI tools

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER_URL="https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Print functions
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              Napari MCP Server Auto Installer               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS] <target>"
    echo ""
    echo "Targets:"
    echo "  claude-desktop    Install for Claude Desktop"
    echo "  claude-code       Install for Claude Code"
    echo "  cursor           Install for Cursor"
    echo "  chatgpt          Install for ChatGPT (shows setup guide)"
    echo "  all              Install for all supported tools"
    echo ""
    echo "Options:"
    echo "  -h, --help       Show this help message"
    echo "  -v, --verbose    Enable verbose output"
    echo "  --local          Use local server file instead of downloading"
    echo "  --server-path    Path to server file (default: ./napari_mcp_server.py)"
    echo ""
    echo "Examples:"
    echo "  $0 claude-desktop"
    echo "  $0 --local claude-code"
    echo "  $0 --server-path /path/to/server.py cursor"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*) echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

# Get Claude Desktop config path
get_claude_config_path() {
    local os="$1"
    case "$os" in
        macos)
            echo "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
            ;;
        linux)
            echo "$HOME/.config/Claude/claude_desktop_config.json"
            ;;
        windows)
            echo "$APPDATA/Claude/claude_desktop_config.json"
            ;;
        *)
            print_error "Unsupported OS for Claude Desktop: $os"
            return 1
            ;;
    esac
}

# Download server file
download_server() {
    local target_path="$1"
    print_info "Downloading napari MCP server..."
    
    if command_exists curl; then
        curl -fsSL "$SERVER_URL" -o "$target_path"
    elif command_exists wget; then
        wget -q "$SERVER_URL" -O "$target_path"
    else
        print_error "Neither curl nor wget found. Please install one of them."
        return 1
    fi
    
    chmod +x "$target_path"
    print_success "Server downloaded to $target_path"
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    if ! command_exists uv; then
        missing_deps+=("uv")
    fi
    
    if ! command_exists python3 && ! command_exists python; then
        missing_deps+=("python3")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_info "Please install missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            case "$dep" in
                uv)
                    echo "  - Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
                    ;;
                python3)
                    echo "  - Install Python 3.10+: https://www.python.org/downloads/"
                    ;;
            esac
        done
        return 1
    fi
}

# Install for Claude Desktop
install_claude_desktop() {
    local server_path="$1"
    local os
    os=$(detect_os)
    
    print_info "Installing for Claude Desktop..."
    
    # Get config path
    local config_path
    config_path=$(get_claude_config_path "$os")
    
    # Create config directory if it doesn't exist
    local config_dir
    config_dir=$(dirname "$config_path")
    mkdir -p "$config_dir"
    
    # Create or update config
    local abs_server_path
    abs_server_path=$(realpath "$server_path")
    
    local config_json
    config_json=$(cat <<EOF
{
  "mcpServers": {
    "napari": {
      "command": "uv",
      "args": [
        "run", "--with", "Pillow", "--with", "PyQt6", "--with", "fastmcp",
        "--with", "imageio", "--with", "napari", "--with", "numpy", "--with", "qtpy",
        "fastmcp", "run", "$abs_server_path"
      ]
    }
  }
}
EOF
)
    
    # Handle existing config
    if [ -f "$config_path" ]; then
        print_warning "Existing Claude Desktop config found at $config_path"
        read -p "Do you want to backup and replace it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp "$config_path" "${config_path}.backup.$(date +%s)"
            print_info "Backup created: ${config_path}.backup.$(date +%s)"
        else
            print_error "Installation cancelled"
            return 1
        fi
    fi
    
    echo "$config_json" > "$config_path"
    print_success "Claude Desktop configured at $config_path"
    print_info "Please restart Claude Desktop to apply changes"
}

# Install for Claude Code
install_claude_code() {
    local server_path="$1"
    
    print_info "Installing for Claude Code..."
    
    if ! command_exists fastmcp; then
        print_info "Installing fastmcp..."
        uv tool install fastmcp
    fi
    
    local abs_server_path
    abs_server_path=$(realpath "$server_path")
    
    fastmcp install claude-code "$abs_server_path" \
        --with napari \
        --with imageio \
        --with Pillow \
        --with PyQt6 \
        --with numpy \
        --with qtpy
    
    print_success "Claude Code integration installed"
    print_info "Server will be automatically available in Claude Code"
}

# Install for Cursor
install_cursor() {
    local server_path="$1"
    
    print_info "Installing for Cursor..."
    
    if ! command_exists fastmcp; then
        print_info "Installing fastmcp..."
        uv tool install fastmcp
    fi
    
    local abs_server_path
    abs_server_path=$(realpath "$server_path")
    
    fastmcp install cursor "$abs_server_path" \
        --with napari \
        --with imageio \
        --with Pillow \
        --with PyQt6 \
        --with numpy \
        --with qtpy
    
    print_success "Cursor integration installed"
    print_info "Server will be automatically available in Cursor's AI assistant"
}

# Show ChatGPT setup guide
install_chatgpt() {
    print_info "ChatGPT setup requires manual configuration..."
    echo ""
    echo "ChatGPT (Deep Research only) setup steps:"
    echo "1. Deploy server publicly (e.g., using ngrok):"
    echo "   ngrok http 8000"
    echo ""
    echo "2. Run server on public URL:"
    echo "   uv run --with fastmcp --with napari --with imageio --with Pillow \\"
    echo "       fastmcp serve napari_mcp_server.py --host 0.0.0.0 --port 8000"
    echo ""
    echo "3. In ChatGPT:"
    echo "   - Go to Settings → Connectors"
    echo "   - Add custom connector with your public URL"
    echo "   - Format: https://your-url.ngrok.io/mcp/"
    echo ""
    echo "4. Use in Deep Research mode only"
    echo ""
    print_warning "Note: Limited functionality compared to other integrations"
}

# Test installation
test_installation() {
    local target="$1"
    print_info "Testing $target installation..."
    
    case "$target" in
        claude-desktop)
            local os
            os=$(detect_os)
            local config_path
            config_path=$(get_claude_config_path "$os")
            
            if [ -f "$config_path" ] && grep -q "napari" "$config_path"; then
                print_success "Claude Desktop config found and contains napari server"
            else
                print_error "Claude Desktop config not found or missing napari server"
                return 1
            fi
            ;;
        claude-code|cursor)
            if fastmcp list | grep -q "$target"; then
                print_success "$target integration found in fastmcp list"
            else
                print_error "$target integration not found in fastmcp list"
                return 1
            fi
            ;;
        chatgpt)
            print_info "ChatGPT requires manual testing in Deep Research mode"
            ;;
    esac
}

# Main installation function
install_target() {
    local target="$1"
    local server_path="$2"
    
    case "$target" in
        claude-desktop)
            install_claude_desktop "$server_path"
            ;;
        claude-code)
            install_claude_code "$server_path"
            ;;
        cursor)
            install_cursor "$server_path"
            ;;
        chatgpt)
            install_chatgpt
            ;;
        all)
            install_claude_desktop "$server_path"
            install_claude_code "$server_path"
            install_cursor "$server_path"
            install_chatgpt
            ;;
        *)
            print_error "Unknown target: $target"
            usage
            return 1
            ;;
    esac
}

# Parse command line arguments
VERBOSE=false
USE_LOCAL=false
SERVER_PATH=""
TARGET=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --local)
            USE_LOCAL=true
            shift
            ;;
        --server-path)
            SERVER_PATH="$2"
            shift 2
            ;;
        *)
            TARGET="$1"
            shift
            ;;
    esac
done

# Main execution
main() {
    print_header
    
    if [ -z "$TARGET" ]; then
        print_error "No target specified"
        usage
        exit 1
    fi
    
    # Check dependencies
    print_info "Checking dependencies..."
    if ! check_dependencies; then
        exit 1
    fi
    print_success "Dependencies check passed"
    
    # Determine server path
    local server_file
    if [ -n "$SERVER_PATH" ]; then
        server_file="$SERVER_PATH"
        if [ ! -f "$server_file" ]; then
            print_error "Server file not found: $server_file"
            exit 1
        fi
    elif [ "$USE_LOCAL" = true ]; then
        server_file="$PROJECT_ROOT/src/napari_mcp_server.py"
        if [ ! -f "$server_file" ]; then
            print_error "Local server file not found: $server_file"
            exit 1
        fi
    else
        server_file="./napari_mcp_server.py"
        if [ ! -f "$server_file" ]; then
            download_server "$server_file"
        else
            print_info "Using existing server file: $server_file"
        fi
    fi
    
    # Install for target
    install_target "$TARGET" "$server_file"
    
    # Test installation (skip for 'all' and 'chatgpt')
    if [ "$TARGET" != "all" ] && [ "$TARGET" != "chatgpt" ]; then
        test_installation "$TARGET"
    fi
    
    print_success "Installation completed for $TARGET!"
    
    if [ "$TARGET" = "all" ]; then
        echo ""
        print_info "Next steps:"
        echo "1. Restart Claude Desktop"
        echo "2. Claude Code and Cursor should have the server available immediately"
        echo "3. For ChatGPT, follow the manual setup steps shown above"
    fi
}

# Run main function
main "$@"
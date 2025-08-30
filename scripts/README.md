# Convenience Scripts

These scripts make it even easier to run the napari MCP server with the zero-install method.

## Scripts Available

### 🖥️ Unix/Linux/macOS

- **`run.sh`** - Run the server with local or downloaded file
- **`run_from_github.sh`** - Always download and run the latest version from GitHub

### 🪟 Windows

- **`run.bat`** - Run the server with local or downloaded file

## Usage

### Basic Usage

```bash
# Make executable (Unix/macOS)
chmod +x scripts/run.sh

# Run with local file
./scripts/run.sh

# Run with specific file path
./scripts/run.sh /path/to/napari_mcp_server.py

# Windows
scripts\run.bat
scripts\run.bat C:\path\to\napari_mcp_server.py
```

### Always Use Latest from GitHub

```bash
# This downloads the latest version every time
./scripts/run_from_github.sh
```

## What the Scripts Do

1. **Check prerequisites** - Verify `uv` is installed
2. **Handle file location** - Download if not found locally
3. **Set permissions** - Make files executable
4. **Run the server** - Execute with all required dependencies
5. **Show progress** - Colorful output to track what's happening

## Claude Desktop Integration

After running any of these scripts, the server will be available for Claude Desktop. Use the configuration from the main README.md or QUICKSTART.md.

## Troubleshooting

### "uv: command not found"
Install uv first:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

### Permission denied (Unix/macOS)
```bash
chmod +x scripts/run.sh
chmod +x scripts/run_from_github.sh
```

### Download fails
- Check internet connection
- Verify GitHub is accessible
- Try manual download: `curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py`

## Benefits

- ✅ **One command** - Just run the script
- ✅ **Auto-download** - Handles missing files
- ✅ **Error checking** - Clear error messages
- ✅ **Cross-platform** - Works on Unix, macOS, and Windows
- ✅ **Always latest** - GitHub runner gets newest version

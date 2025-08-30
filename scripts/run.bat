@echo off
REM Napari MCP Server - Zero Install Runner for Windows
REM Usage: scripts\run.bat [path\to\napari_mcp_server.py]

echo 🚀 Napari MCP Server - Zero Install Runner
echo.

REM Check if uv is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo ❌ uv is not installed
    echo Install with: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

REM Determine server file path
set SERVER_FILE=%1
if "%SERVER_FILE%"=="" set SERVER_FILE=src\napari_mcp_server.py

REM If file doesn't exist locally, try to download it
if not exist "%SERVER_FILE%" (
    echo 📥 Server file not found locally, downloading...
    set SERVER_FILE=napari_mcp_server.py
    curl -O https://raw.githubusercontent.com/royerlab/napari-mcp/main/src/napari_mcp_server.py
    if errorlevel 1 (
        echo ❌ Failed to download server file
        pause
        exit /b 1
    )
    echo ✅ Downloaded napari_mcp_server.py
)

echo 🔧 Starting server with file: %SERVER_FILE%
echo.

REM Show the command being run
echo Running:
echo uv run --with Pillow --with PyQt6 --with fastmcp --with imageio --with napari --with numpy --with qtpy fastmcp run %SERVER_FILE%
echo.

REM Run the server
uv run ^
    --with Pillow ^
    --with PyQt6 ^
    --with fastmcp ^
    --with imageio ^
    --with napari ^
    --with numpy ^
    --with qtpy ^
    fastmcp run "%SERVER_FILE%"

if errorlevel 1 (
    echo.
    echo ❌ Server failed to start
    pause
)

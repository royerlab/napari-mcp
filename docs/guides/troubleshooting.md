# Troubleshooting

Common issues and solutions when using napari MCP server with AI assistants.

## 🚨 Common Setup Issues

### Server Won't Start

!!! failure "uv: command not found"
    **Problem:** The `uv` command isn't found when trying to run the server.

    **Solution:**
    ```bash
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Restart terminal or reload shell
    source ~/.bashrc  # or ~/.zshrc
    ```

!!! failure "napari-mcp: command not found"
    **Problem:** Traditional installation command not found.

    **Solutions:**
    ```bash
    # Reinstall in development mode
    pip install -e . --force-reinstall

    # Or use Python module directly
    python -m napari_mcp_server

    # Check if it's in your PATH
    which napari-mcp
    ```

!!! failure "Permission denied"
    **Problem:** File permission errors when running downloaded script.

    **Solution:**
    ```bash
    # Make file executable
    chmod +x napari_mcp_server.py

    # Or run with Python directly
    python napari_mcp_server.py
    ```

### Napari GUI Issues

!!! failure "Qt platform plugin not found"
    **Problem:** `qt.qpa.plugin: Could not find the Qt platform plugin`

    **Solutions:**
    ```bash
    # For headless/remote systems
    export QT_QPA_PLATFORM=offscreen

    # For Linux with X11
    export QT_QPA_PLATFORM=xcb

    # For debugging
    export QT_DEBUG_PLUGINS=1
    ```

!!! failure "Napari window doesn't appear"
    **Problem:** Server starts but no napari window shows.

    **Diagnosis:**
    ```bash
    # Check display connection (Linux/macOS)
    echo $DISPLAY

    # Test basic Qt
    python -c "from PyQt6.QtWidgets import QApplication; app = QApplication([]); print('Qt works')"

    # Test napari
    python -c "import napari; viewer = napari.Viewer(); print('Napari works')"
    ```

    **Solutions:**
    - **Remote systems:** Enable X11 forwarding or use offscreen mode
    - **macOS:** Check System Preferences > Security & Privacy
    - **Windows:** Ensure graphics drivers are updated

!!! failure "Import errors with napari"
    **Problem:** `ImportError: No module named 'napari'`

    **Solution:**
    ```bash
    # Check napari installation
    pip list | grep napari

    # Reinstall napari
    pip install --upgrade napari[all]

    # Or with uv
    uv pip install napari[all]
    ```

## 🔌 AI Assistant Connection Issues

### Claude Desktop

!!! failure "Claude can't see napari tools"
    **Problem:** MCP tools don't appear in Claude Desktop.

    **Checklist:**
    1. **Config file location correct?**
       - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
       - Windows: `%APPDATA%/Claude/claude_desktop_config.json`
       - Linux: `~/.config/Claude/claude_desktop_config.json`

    2. **JSON syntax valid?**
       ```bash
       # Validate JSON
       cat claude_desktop_config.json | python -m json.tool
       ```

    3. **File paths absolute?**
       ```json
       // Wrong - relative path
       "args": ["fastmcp", "run", "napari_mcp_server.py"]

       // Correct - absolute path
       "args": ["fastmcp", "run", "/full/path/to/napari_mcp_server.py"]
       ```

    4. **Claude Desktop restarted?**
       - Completely quit and restart Claude Desktop
       - Check for error messages in console

!!! failure "MCP server connection failed"
    **Problem:** Claude shows connection errors.

    **Debug steps:**
    ```bash
    # Test server starts manually
    uv run --with fastmcp fastmcp run napari_mcp_server.py

    # Check for error messages
    # Look for FastMCP startup banner

    # Test MCP protocol
    echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}' | \
      uv run --with fastmcp fastmcp run napari_mcp_server.py
    ```

### Cursor & Claude Code

!!! failure "FastMCP CLI installation failed"
    **Problem:** `fastmcp install` command fails.

    **Solutions:**
    ```bash
    # Update fastmcp
    pip install --upgrade fastmcp

    # Check installation
    fastmcp --version

    # Manual installation
    fastmcp install cursor napari_mcp_server.py --with napari --with imageio
    ```

!!! failure "Server not appearing in IDE"
    **Problem:** Installed server doesn't show up in Cursor/Claude Code.

    **Debug:**
    ```bash
    # Check installation location
    fastmcp list

    # Reinstall for specific IDE
    fastmcp uninstall cursor napari
    fastmcp install cursor napari_mcp_server.py --with napari
    ```

## 📦 Dependency Issues

### Package Installation Problems

!!! failure "Package conflicts"
    **Problem:** Version conflicts between dependencies.

    **Solution:**
    ```bash
    # Use virtual environment
    python -m venv fresh-env
    source fresh-env/bin/activate
    pip install -e .

    # Or specify versions
    uv run --with "napari>=0.5.5" --with "PyQt6>=6.5.0" \
      fastmcp run napari_mcp_server.py
    ```

!!! failure "Qt backend conflicts"
    **Problem:** Multiple Qt installations causing issues.

    **Diagnosis:**
    ```python
    import qtpy
    print(f"Using Qt API: {qtpy.API}")
    print(f"Qt version: {qtpy.QT_VERSION}")
    ```

    **Solution:**
    ```bash
    # Force specific Qt backend
    export QT_API=pyqt6

    # Or reinstall clean
    pip uninstall PyQt5 PyQt6 PySide2 PySide6
    pip install PyQt6
    ```

### Network and Firewall

!!! failure "Connection timeouts"
    **Problem:** Network timeouts when downloading dependencies.

    **Solutions:**
    ```bash
    # Increase timeout
    pip install --timeout=60 napari

    # Use different index
    pip install -i https://pypi.python.org/simple/ napari

    # Check proxy settings
    pip install --proxy http://proxy:port napari
    ```

## 🔧 Performance Issues

### Slow Startup

!!! failure "Server takes long to start"
    **Problem:** 30+ seconds to start server.

    **Optimizations:**
    ```bash
    # Pre-warm uv cache
    uv run --with napari --help

    # Use local installation
    pip install -e .
    napari-mcp  # Faster than uv run

    # Check startup time
    time uv run --with napari fastmcp run napari_mcp_server.py
    ```

### Memory Issues

!!! failure "High memory usage"
    **Problem:** Excessive memory consumption.

    **Monitoring:**
    ```bash
    # Monitor memory usage
    ps aux | grep napari

    # Python memory profiling
    python -m memory_profiler napari_mcp_server.py
    ```

    **Solutions:**
    - Close unused napari viewers
    - Reduce image resolution for testing
    - Use `gc.collect()` in custom code
    - Monitor for memory leaks in long-running sessions

## 🖥️ Platform-Specific Issues

### macOS

!!! failure "Gatekeeper blocks execution"
    **Problem:** "Cannot be opened because the developer cannot be verified"

    **Solution:**
    ```bash
    # Remove quarantine attribute
    xattr -d com.apple.quarantine napari_mcp_server.py

    # Or allow in System Preferences > Security & Privacy
    ```

!!! failure "Rosetta compatibility (Apple Silicon)"
    **Problem:** Performance issues on M1/M2 Macs.

    **Solution:**
    ```bash
    # Use native ARM Python
    /opt/homebrew/bin/python3 -m pip install napari

    # Check architecture
    python -c "import platform; print(platform.machine())"
    ```

### Windows

!!! failure "PowerShell execution policy"
    **Problem:** Scripts blocked by execution policy.

    **Solution:**
    ```powershell
    # Set execution policy
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

    # Or run directly
    python napari_mcp_server.py
    ```

!!! failure "Path length limitations"
    **Problem:** File paths too long on Windows.

    **Solution:**
    - Enable long path support in Windows
    - Use shorter directory names
    - Move project closer to root drive

### Linux

!!! failure "Display server issues"
    **Problem:** GUI doesn't work on headless systems.

    **Solutions:**
    ```bash
    # Virtual display
    sudo apt-get install xvfb
    xvfb-run -a python napari_mcp_server.py

    # Or use offscreen
    export QT_QPA_PLATFORM=offscreen
    ```

## 🐛 Debugging Tools

### Logging and Debug Output

```bash
# Enable verbose logging
export MCP_LOG_LEVEL=DEBUG
export NAPARI_ASYNC=1

# Python debugging
python -u napari_mcp_server.py  # Unbuffered output

# FastMCP debugging
fastmcp run --debug napari_mcp_server.py
```

### Testing Commands

```bash
# Test napari import
python -c "import napari; print('✅ napari works')"

# Test FastMCP
python -c "import fastmcp; print('✅ FastMCP works')"

# Test Qt
python -c "from PyQt6.QtWidgets import QApplication; app = QApplication([]); print('✅ Qt works')"

# Full integration test
python -c "
import napari
import fastmcp
viewer = napari.Viewer()
print('✅ Full integration works')
viewer.close()
"
```

### System Information

```bash
# Collect system info for bug reports
echo "=== System Information ==="
python --version
pip --version
uv --version
echo "Platform: $(python -c 'import platform; print(platform.platform())')"
echo "Qt API: $(python -c 'import qtpy; print(qtpy.API)')"
echo "Napari: $(python -c 'import napari; print(napari.__version__)')"
echo "FastMCP: $(python -c 'import fastmcp; print(fastmcp.__version__)')"
```

## 🆘 Getting Help

If you've tried all the solutions above and still have issues:

### Before Asking for Help

1. **Collect information:**
   - Error messages (full traceback)
   - System information (OS, Python version)
   - Steps to reproduce the issue
   - What you've tried already

2. **Create minimal example:**
   ```bash
   # Simplest possible test
   python -c "import napari; viewer = napari.Viewer()"
   ```

3. **Check existing issues:**
   - Search [GitHub Issues](https://github.com/royerlab/napari-mcp/issues)
   - Check napari and FastMCP issue trackers

### Where to Get Help

- **GitHub Issues:** [Report bugs and ask questions](https://github.com/royerlab/napari-mcp/issues/new)
- **Discussions:** [Community discussions](https://github.com/royerlab/napari-mcp/discussions)
- **Napari Community:** [Napari forum](https://forum.image.sc/tag/napari)

### Issue Template

When reporting bugs, please include:

```markdown
## Bug Description
Brief description of the issue

## Steps to Reproduce
1. First step
2. Second step
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens (include full error messages)

## Environment
- OS: [e.g., macOS 14.0, Ubuntu 22.04, Windows 11]
- Python: [e.g., 3.11.5]
- Napari: [e.g., 0.5.5]
- Installation method: [Zero install, traditional, etc.]

## Additional Context
Any other relevant information
```

---

**Still stuck?** Don't hesitate to ask for help! The community is here to support you. 🤝

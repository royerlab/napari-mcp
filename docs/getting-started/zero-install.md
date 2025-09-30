# Zero Install Guide

Run napari MCP server without permanent installation using `uv` - perfect for testing, CI/CD, and clean deployments.

!!! tip "CLI Installer Uses This Automatically"
    The **[Quick Start](quickstart.md)** CLI installer (`napari-mcp-install`) automatically configures your AI app to use zero-install with `uv`. This guide explains how it works and provides manual alternatives.

## What is Zero Install?

Zero install means running napari MCP without permanently installing it on your system. Instead, `uv` downloads dependencies to a temporary cache and runs the server in an ephemeral environment.

### Benefits

- ✅ **No permanent installation** - Nothing added to your Python environment
- ✅ **Always up-to-date** - Gets latest version from PyPI each time
- ✅ **Clean environments** - No dependency conflicts
- ✅ **Easy sharing** - Same command works everywhere
- ✅ **CI/CD friendly** - Reproducible deployments

### How It Works

When you use `napari-mcp-install`, it creates a configuration that runs:

```bash
uv run --with napari-mcp napari-mcp
```

This command:
1. Downloads napari-mcp and dependencies to uv's cache
2. Creates a temporary isolated environment
3. Runs the server
4. Cleans up when done

## Automated Setup (Recommended)

The CLI installer handles everything:

```bash
# Install the package (contains the CLI tool)
pip install napari-mcp

# Auto-configure your application
napari-mcp-install claude-desktop  # or claude-code, cursor, etc.
```

This creates a configuration file with:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"]
    }
  }
}
```

**→ See [Quick Start](quickstart.md) for step-by-step instructions**

---

## Manual Zero Install

If you prefer manual setup or need custom configurations:

### Step 1: Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pip
pip install uv
```

### Step 2: Test the Server

```bash
# Run directly to test
uv run --with napari-mcp napari-mcp
```

### Step 3: Configure Your AI Application

Manually add to your application's config file:

**Example for Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"]
    }
  }
}
```

**→ See [Advanced Installation](installation.md) for all config file locations**

---

## Advanced Zero Install

### With Additional Dependencies

```bash
# Include extra packages
uv run --with napari-mcp --with scikit-image --with scipy napari-mcp
```

Configure in your app:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--with", "napari-mcp",
        "--with", "scikit-image",
        "--with", "scipy",
        "napari-mcp"
      ]
    }
  }
}
```

### With Specific Versions

```bash
# Pin specific version
uv run --with "napari-mcp==0.1.0" napari-mcp
```

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp==0.1.0", "napari-mcp"]
    }
  }
}
```

### Debug Mode

```bash
# Verbose output
uv run -v --with napari-mcp napari-mcp
```

---

## CLI Installer Options

The CLI installer supports both zero-install and persistent modes:

### Zero Install (Default)

```bash
napari-mcp-install claude-desktop
```

Creates configuration using `uv run` (zero-install mode).

### Persistent Mode

```bash
# First install napari-mcp in your environment
pip install napari-mcp

# Then configure with persistent mode
napari-mcp-install claude-desktop --persistent
```

This uses your Python environment instead of uv:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "python",
      "args": ["-m", "napari_mcp.server"]
    }
  }
}
```

---

## Performance Optimization

### Faster Startup

uv caches dependencies, so subsequent runs are faster:

```bash
# First run (downloads dependencies)
uv run --with napari-mcp napari-mcp  # ~10-30 seconds

# Subsequent runs (uses cache)
uv run --with napari-mcp napari-mcp  # ~2-5 seconds
```

### Pre-populate Cache

```bash
# Pre-download dependencies
uv run --with napari-mcp --with napari --help

# Now actual runs will be faster
```

---

## Comparison: Zero Install vs Persistent

| Aspect | Zero Install (uv) | Persistent Install |
|--------|------------------|-------------------|
| **Setup time** | Instant | 5-10 minutes |
| **Disk usage** | Temporary cache | Permanent |
| **Dependencies** | Auto-managed | Manual |
| **Updates** | Automatic | Manual upgrade |
| **Conflicts** | Isolated | Can conflict |
| **Development** | Limited | Excellent |
| **CI/CD** | Perfect | Needs setup |

---

## When to Use Each Method

### Use Zero Install When:
- Testing napari MCP for the first time
- Don't want to permanently install anything
- Need consistent versions across team/CI
- Want automatic updates
- Running in clean/temporary environments

### Use Persistent When:
- Developing napari plugins
- Need offline access
- Require specific/custom dependencies
- Performance is critical (avoid startup time)
- Want full control over environment

---

## Troubleshooting Zero Install

### uv Not Found

!!! failure "uv: command not found"
    **Solution:** Install uv:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Restart terminal
    ```

### Slow First Run

!!! note "First run is slow"
    **Expected:** uv downloads dependencies on first run (~10-30 seconds).
    Subsequent runs use cache and are much faster (~2-5 seconds).

### Network Issues

!!! failure "Can't download dependencies"
    **Solutions:**
    1. Check internet connection
    2. Check firewall/proxy settings
    3. Use persistent mode instead:
       ```bash
       pip install napari-mcp
       napari-mcp-install <app> --persistent
       ```

### Cache Issues

!!! failure "Dependencies seem outdated"
    **Solution:** Clear uv cache:
    ```bash
    uv cache clean

    # Then try again
    uv run --with napari-mcp napari-mcp
    ```

---

## CLI Installer Management

```bash
# Check which mode is configured
napari-mcp-install list

# Switch to zero-install mode
napari-mcp-install <app>

# Switch to persistent mode
napari-mcp-install <app> --persistent

# Preview changes
napari-mcp-install <app> --dry-run
```

---

## Environment Variables

Configure behavior via environment variables:

```bash
# Increase timeout for slow networks
export UV_HTTP_TIMEOUT=300

# Use specific Python version
export UV_PYTHON=python3.11

# Verbose logging
export UV_LOG_LEVEL=debug
```

Add to config:

```json
{
  "mcpServers": {
    "napari-mcp": {
      "command": "uv",
      "args": ["run", "--with", "napari-mcp", "napari-mcp"],
      "env": {
        "UV_HTTP_TIMEOUT": "300"
      }
    }
  }
}
```

---

## For CI/CD Pipelines

Zero install is perfect for CI/CD:

```yaml
# .github/workflows/test.yml
jobs:
  test:
    steps:
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Run napari MCP tests
        run: uv run --with napari-mcp napari-mcp --help
```

No need to install dependencies - uv handles everything!

---

## Next Steps

- **[Quick Start](quickstart.md)** - Automated setup with CLI installer
- **[Advanced Installation](installation.md)** - Manual configuration and development
- **[Integration Guides](../integrations/index.md)** - Application-specific setup
- **[Troubleshooting](../guides/troubleshooting.md)** - Common issues

---

**Zero install = Zero hassle!** 🎉 The CLI installer uses this automatically for clean, reproducible deployments.

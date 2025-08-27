# Contributing to napari-mcp

Thank you for your interest in contributing to napari-mcp! This document provides guidelines and information for contributors.

## 🚀 Quick Start for Contributors

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/napari-mcp.git
   cd napari-mcp
   ```

2. **Set up development environment**
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install in development mode
   uv pip install -e ".[test]"
   ```

3. **Install pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=napari_mcp_server --cov-report=html

# Run only fast tests (no GUI)
uv run pytest -m "not realgui"

# Run real GUI tests (requires display)
RUN_REAL_NAPARI_TESTS=1 uv run pytest -m "realgui"
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/ --fix

# Type checking
mypy src/napari_mcp_server.py --ignore-missing-imports

# Security scanning
bandit -r src/
safety check
```

## 🎯 How to Contribute

### Types of Contributions

We welcome the following types of contributions:

- **🐛 Bug fixes** - Fix issues in existing functionality
- **✨ New features** - Add new MCP tools or napari integrations
- **📚 Documentation** - Improve README, add examples, API docs
- **🧪 Tests** - Improve test coverage or add new test cases
- **🔒 Security** - Security improvements and vulnerability fixes
- **🏗️ Infrastructure** - CI/CD, build system, tooling improvements

### Before You Start

1. **Check existing issues** - Look for related issues or feature requests
2. **Discuss major changes** - Open an issue to discuss large changes
3. **Follow security guidelines** - Be especially careful with code execution features

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Follow existing code style and patterns
   - Add tests for new functionality
   - Update documentation as needed
   - Consider security implications

3. **Test your changes**
   ```bash
   # Run the full test suite
   uv run pytest

   # Test manually with napari
   napari-mcp
   # Then test with Claude Desktop
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new MCP tool for layer filtering"
   # Follow conventional commit format
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   # Then create a Pull Request on GitHub
   ```

## 📋 Pull Request Guidelines

### PR Checklist

- [ ] **Tests pass** - All existing tests continue to pass
- [ ] **New tests added** - For new features or bug fixes
- [ ] **Documentation updated** - README, docstrings, examples
- [ ] **Security reviewed** - Especially for code execution features
- [ ] **Type hints added** - For new functions and methods
- [ ] **Conventional commits** - Use conventional commit messages

### PR Template

When creating a PR, please include:

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Security improvement
- [ ] Other (please describe)

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Manually tested with napari + Claude

## Security Considerations
(If applicable - especially for execute_code/install_packages changes)

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## 🔍 Code Style Guidelines

### General Principles

- **Readability** - Code should be easy to read and understand
- **Security** - Always consider security implications
- **Async/await** - Use async/await consistently for MCP tools
- **Error handling** - Provide clear error messages and proper exception handling
- **Documentation** - Document all public functions and complex logic

### Specific Guidelines

```python
# ✅ Good: Clear function signature with type hints
async def add_image(
    path: str,
    name: Optional[str] = None,
    colormap: Optional[str] = None
) -> Dict[str, Any]:
    """Add an image layer from a file path.

    Args:
        path: Path to an image readable by imageio
        name: Optional layer name
        colormap: Optional napari colormap name

    Returns:
        Dict with status, name, and shape information
    """

# ❌ Bad: No type hints, unclear parameters
def add_image(path, name=None, colormap=None):
    # Does stuff
    return result
```

### Naming Conventions

- **Functions**: `snake_case` (e.g., `add_image`, `set_layer_properties`)
- **Variables**: `snake_case` (e.g., `layer_name`, `current_zoom`)
- **Constants**: `UPPER_CASE` (e.g., `DEFAULT_TIMEOUT`)
- **Classes**: `PascalCase` (e.g., `LayerManager`)

## 🧪 Testing Guidelines

### Test Structure

```python
"""
tests/
├── test_tools.py          # Main tool functionality tests
├── test_tools_real.py     # Real napari GUI tests (marked as 'realgui')
├── test_coverage.py       # Edge cases and error conditions
└── test_edge_cases.py     # Additional edge cases
"""
```

### Writing Tests

```python
import pytest
from napari_mcp_server import add_image

@pytest.mark.asyncio
async def test_add_image_success():
    """Test successful image addition."""
    # Arrange
    test_image_path = "test_data/sample.png"

    # Act
    result = await add_image(test_image_path, name="test_image")

    # Assert
    assert result["status"] == "ok"
    assert result["name"] == "test_image"
    assert "shape" in result

@pytest.mark.realgui
@pytest.mark.asyncio
async def test_add_image_real_gui():
    """Test image addition with real napari GUI."""
    # This test requires RUN_REAL_NAPARI_TESTS=1
    # and will be skipped in headless CI
```

### Test Markers

- `@pytest.mark.realgui` - Tests requiring real napari GUI
- `@pytest.mark.asyncio` - Async tests (most MCP tools)
- `@pytest.mark.slow` - Slow tests that can be skipped for quick runs

## 🔒 Security Considerations

### High-Risk Areas

When contributing changes to these areas, extra security review is required:

- `execute_code()` function
- `install_packages()` function
- Any new code execution or system access features

### Security Review Process

1. **Self-review** - Consider all security implications
2. **Document risks** - Clearly document any security considerations
3. **Minimal permissions** - Use least privilege principle
4. **Input validation** - Validate all inputs thoroughly
5. **Error handling** - Don't leak sensitive information in errors

## 📞 Getting Help

### Community Support

- **GitHub Issues** - For bug reports and feature requests
- **GitHub Discussions** - For questions and general discussion
- **Security Issues** - Follow SECURITY.md for vulnerability reporting

### Development Questions

If you have questions about:
- **Architecture** - How the MCP server works
- **Testing** - How to write or run tests
- **napari Integration** - How napari APIs work
- **MCP Protocol** - Model Context Protocol details

Feel free to open a GitHub Discussion or comment on existing issues.

## 🎉 Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Special mentions for security improvements

Thank you for helping make napari-mcp better and more secure! 🚀

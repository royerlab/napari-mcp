# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🛑 CRITICAL: Before ANY Code Modification

### The Three-Step Rule (MANDATORY)
1. **READ**: Always use the Read tool to examine the ENTIRE file first
2. **UNDERSTAND**: Analyze the existing patterns, imports, and dependencies
3. **VERIFY**: Check related files and tests before making changes

### Pre-Modification Checklist
Before ANY code change, you MUST:
- [ ] Read the complete file using the Read tool
- [ ] Understand all imports and their usage
- [ ] Check if similar patterns exist elsewhere in the codebase
- [ ] Verify the change won't break existing tests
- [ ] Ensure thread-safety for any viewer operations
- [ ] Confirm the change follows existing code patterns

## ⚠️ SURGICAL CODING PRINCIPLES

### 1. Be Extremely Careful
- **NEVER** make assumptions about code structure
- **ALWAYS** verify before modifying
- **READ** files completely before editing
- **UNDERSTAND** the context and dependencies
- **TEST** changes thoroughly

### 2. Minimal Changes Philosophy
- Make the SMALLEST change that achieves the goal
- Prefer modifying existing code over creating new files
- NEVER create documentation files unless explicitly requested
- Avoid refactoring unless it's the primary task

### 3. Test-First Approach
When implementing features:
1. Write or modify tests FIRST
2. Run tests to confirm they fail
3. Implement the minimal code to pass tests
4. Run tests again to verify success
5. Check for any side effects on other tests

## 📚 Project Overview

**napari-mcp** is a Model Context Protocol (MCP) server enabling AI assistants to control napari image viewers. It bridges async MCP operations with Qt's event loop, requiring careful thread-safety considerations.

### Core Architecture Components

```
src/napari_mcp/
├── base.py           # Core NapariMCPTools - Thread-safe viewer operations
├── bridge_server.py  # NapariBridgeServer - MCP↔napari bridge with Qt integration
├── server.py         # FastMCP server entry point - Main executable
├── widget.py         # MCPControlWidget - Napari plugin GUI
└── napari.yaml       # Napari plugin manifest
```

### Critical Design Patterns

1. **Thread Safety**: ALL napari operations MUST be protected by locks
2. **Qt Event Loop**: Runs asynchronously, requires careful async/sync boundary management
3. **Viewer Lifecycle**: Single viewer instance managed across tool calls
4. **Error Handling**: Graceful degradation with detailed error messages

## 🔧 Development Commands

### Installation
```bash
# Standard development setup with ALL extras
uv sync --all-extras
uv pip install -e .

# Quick install for testing
pip install napari-mcp

# Install from GitHub (latest)
uv pip install git+https://github.com/royerlab/napari-mcp.git
```

### Testing Hierarchy (ALWAYS follow this order)

#### 1. Quick Validation (Run FIRST)
```bash
# Fastest smoke test - Run this FIRST to catch obvious issues
uv run pytest tests/test_tools.py::TestToolExecution::test_init_viewer -xvs

# Core functionality check
uv run pytest tests/test_tools.py tests/test_integration.py::TestBasicIntegration -xvs
```

#### 2. Standard Test Suite
```bash
# Run non-GUI tests (default)
uv run pytest tests/ -v -m "not realgui" --tb=short

# Run with coverage
uv run pytest tests/ -v -m "not realgui" --cov=napari_mcp --cov-report=term-missing

# Run in parallel for speed
uv run pytest tests/ -v -m "not realgui" -n auto --dist loadscope
```

#### 3. GUI Tests (Only if modifying viewer interactions)
```bash
# Requires display or virtual framebuffer
RUN_REAL_NAPARI_TESTS=1 QT_QPA_PLATFORM=offscreen PYTEST_QT_API=pyqt6 \
  uv run pytest tests/ -v -m realgui --tb=short
```

#### 4. Test Isolation (For debugging test dependencies)
```bash
# Run tests in random order to detect dependencies
uv run pytest tests/ --random-order

# Run tests in complete isolation
uv run pytest tests/ --forked

# Run a specific test in isolation
uv run pytest tests/test_tools.py::TestToolExecution::test_init_viewer --forked -xvs
```

### Code Quality Checks (Run BEFORE committing)

```bash
# Format code (do this FIRST)
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/

# Linting checks
uv run ruff check src/ tests/

# Type checking
uv run mypy src/napari_mcp/ --ignore-missing-imports

# Security audit
uv run bandit -r src/ --skip B110,B101,B102,B307
uv run safety check

# Pre-commit hooks (runs automatically on commit)
pre-commit run --all-files
```

### Using Makefile (Alternative)
```bash
make test           # Standard tests
make test-fast      # Quick smoke tests
make test-parallel  # Parallel execution
make test-coverage  # With coverage report
make lint           # All linting checks
make format         # Auto-format code
make dev            # format + lint + test-fast
```

## 🚨 CRITICAL CODE SECTIONS

### Thread-Safe Viewer Operations (base.py)
**NEVER modify without understanding threading implications:**
- All viewer operations MUST be wrapped in proper locks
- Qt operations must respect the event loop
- Async/sync boundaries need careful handling

### MCP Bridge (bridge_server.py)
**Critical for MCP↔napari communication:**
- QtBridge handles cross-thread operations
- Signal/slot mechanism for thread safety
- Server lifecycle management

### Test Isolation (conftest.py)
**Essential for reliable testing:**
- Mock napari module for non-GUI tests
- Proper cleanup between tests
- State reset mechanisms

## 📋 Common Development Tasks

### Adding a New MCP Tool

1. **FIRST**: Search for similar existing tools
```bash
uv run grep -r "async def.*tool" src/napari_mcp/
```

2. **READ** the entire base.py to understand patterns
```python
# Use Read tool on src/napari_mcp/base.py
```

3. **ADD** tool method to NapariMCPTools class following existing patterns
```python
async def new_tool(self, param1: str, param2: int = 10) -> dict[str, Any]:
    """Tool description following numpy docstring style."""
    viewer = self._ensure_viewer()
    # Implementation with proper error handling
```

4. **REGISTER** in bridge_server.py or server.py
```python
@server.tool()
async def new_tool(param1: str, param2: int = 10) -> dict[str, Any]:
    return await tools.new_tool(param1, param2)
```

5. **WRITE** test FIRST in tests/test_tools.py
```python
async def test_new_tool(mock_napari):
    # Test implementation
```

6. **RUN** tests to verify
```bash
uv run pytest tests/test_tools.py::test_new_tool -xvs
```

7. **UPDATE** README.md ONLY if adding user-facing functionality

### Debugging Issues

1. **Isolate the problem**
```bash
# Run single test with verbose output
uv run pytest path/to/test.py::test_name -xvs

# Run with debugging
uv run pytest path/to/test.py::test_name -xvs --pdb
```

2. **Check for test interference**
```bash
# Run in isolation
uv run pytest path/to/test.py::test_name --forked

# Run with random order
uv run pytest tests/ --random-order-seed=12345
```

3. **Verify thread safety**
- Check for missing locks in viewer operations
- Ensure Qt operations use proper thread mechanisms
- Look for race conditions in async code

### Fixing Test Failures

1. **ALWAYS read the full error message and traceback**
2. **Check if the test is marked with special requirements** (realgui, slow, etc.)
3. **Verify mock vs real napari usage** (RUN_REAL_NAPARI_TESTS environment variable)
4. **Look for state leakage** between tests (use --forked if needed)
5. **Check Qt platform settings** (QT_QPA_PLATFORM=offscreen for CI)

## 🔍 Code Review Checklist

Before submitting changes, verify:

### Functionality
- [ ] All existing tests pass
- [ ] New tests cover the changes
- [ ] No hardcoded values that should be configurable
- [ ] Error messages are descriptive and actionable

### Code Quality
- [ ] Follows existing code patterns exactly
- [ ] No unnecessary refactoring
- [ ] Proper error handling with try/except
- [ ] Thread-safe viewer operations
- [ ] Appropriate logging (not print statements)

### Testing
- [ ] Tests run in isolation (--forked)
- [ ] Tests pass with random order
- [ ] Coverage maintained or improved
- [ ] Both mock and real napari tests pass (if applicable)

### Documentation
- [ ] Docstrings follow numpy style
- [ ] Type hints are complete and accurate
- [ ] README updated ONLY if user-facing changes
- [ ] No unnecessary documentation files created

## 🚫 What NOT to Do

### NEVER:
- Create new files without explicit requirement
- Refactor code unless it's the primary task
- Add features not requested by the user
- Create documentation files proactively
- Modify thread-safety mechanisms without deep understanding
- Change test isolation mechanisms
- Add print statements (use logging instead)
- Commit without running tests
- Make assumptions about code structure

### AVOID:
- Large, sweeping changes
- Modifying multiple files simultaneously
- Creating helper functions unless absolutely necessary
- Adding dependencies without explicit need
- Changing established patterns

## 🎯 Testing Strategy

### Test Organization
```
tests/
├── conftest.py              # Test configuration and fixtures (DO NOT MODIFY WITHOUT UNDERSTANDING)
├── test_tools.py            # Core tool functionality tests
├── test_integration.py      # Integration tests without GUI
├── test_real_integration.py # Tests with real napari GUI
├── test_bridge_*.py         # Bridge-specific tests
├── test_coverage.py         # Coverage gap tests
├── test_edge_cases.py       # Edge case handling
└── test_performance.py      # Performance benchmarks
```

### Test Markers
- `@pytest.mark.realgui` - Requires real napari/Qt (skip in CI by default)
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.smoke` - Quick validation tests
- `@pytest.mark.isolated` - Must run in complete isolation

### Coverage Requirements
- Minimum: 70% overall coverage
- Target: 80% for new code
- Critical sections: 90%+ (thread safety, error handling)

## 🔐 Security Considerations

### High-Risk Tools
These tools can execute arbitrary code and MUST be handled carefully:
- `execute_code()` - Runs Python code with full system access
- `install_packages()` - Installs Python packages via pip

### Security Guidelines
1. Only use on localhost/trusted networks
2. Never expose to public internet
3. Validate all inputs thoroughly
4. Sanitize file paths and names
5. Use proper error handling to avoid information leakage

## 🏗️ CI/CD Pipeline

### GitHub Actions Workflows
- `test.yml` - Main test matrix (OS × Python versions)
- `test-realgui.yml` - GUI tests with virtual display
- `test-optimized.yml` - Parallel test execution
- `release.yml` - PyPI release automation
- `docs.yml` - Documentation building

### Pre-commit Hooks
Automatically run on commit:
1. Code formatting (ruff)
2. Linting checks
3. Type checking (mypy)
4. Quick smoke tests

## 💡 Performance Considerations

### Critical Performance Areas
1. **Qt Event Loop**: Don't block with long operations
2. **Thread Locks**: Hold for minimum time necessary
3. **Image Operations**: Use numpy efficiently
4. **MCP Communication**: Batch operations when possible

### Profiling Tools
```bash
# Run performance benchmarks
uv run pytest tests/test_performance.py --benchmark-only

# Profile specific operations
python -m cProfile -s cumulative your_script.py
```

## 📊 Monitoring and Debugging

### Debug Environment Variables
```bash
# Enable real napari tests
export RUN_REAL_NAPARI_TESTS=1

# Set Qt platform for headless
export QT_QPA_PLATFORM=offscreen

# Specify Qt API
export PYTEST_QT_API=pyqt6

# Enable debug logging
export NAPARI_MCP_DEBUG=1
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

## 🎓 Learning Resources

### Internal Documentation
- README.md - User-facing documentation
- LLM_INTEGRATIONS.md - AI assistant setup
- tests/conftest.py - Test infrastructure
- src/napari_mcp/base.py - Core patterns

### External Resources
- [napari documentation](https://napari.org/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP framework](https://github.com/jlowin/fastmcp)
- [Qt for Python](https://doc.qt.io/qtforpython/)

## 🔄 Workflow Summary

### For ANY Code Change:
1. **READ** the entire file first
2. **SEARCH** for similar patterns
3. **WRITE** tests first
4. **IMPLEMENT** minimal solution
5. **TEST** thoroughly
6. **VERIFY** no side effects
7. **FORMAT** and lint
8. **COMMIT** with clear message

### Remember:
- **Quality > Speed**
- **Surgical precision > Broad changes**
- **Understanding > Assuming**
- **Testing > Hoping**
- **Existing patterns > New patterns**

---

**FINAL REMINDER**: When in doubt, READ MORE CODE before making changes. Understanding the existing codebase thoroughly is the key to surgical, high-quality modifications.

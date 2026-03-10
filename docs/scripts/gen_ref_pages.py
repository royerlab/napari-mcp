"""Generate API reference pages by parsing tool function ASTs from server.py.

Since tools are closures inside create_server(), mkdocstrings cannot
introspect them directly. Instead, we parse the AST to extract function
signatures and docstrings, then generate markdown pages.
"""

from __future__ import annotations

import ast
from pathlib import Path

import mkdocs_gen_files

# ---------------------------------------------------------------------------
# Tool categories
# ---------------------------------------------------------------------------

function_categories = {
    "session": [
        "init_viewer",
        "close_viewer",
        "session_information",
    ],
    "layer_management": [
        "list_layers",
        "get_layer",
        "add_layer",
        "remove_layer",
        "set_layer_properties",
        "reorder_layer",
        "apply_to_layers",
        "save_layer_data",
    ],
    "viewer_controls": [
        "configure_viewer",
    ],
    "utilities": [
        "screenshot",
        "execute_code",
        "install_packages",
        "read_output",
    ],
}

ALL_TOOLS = [fn for fns in function_categories.values() for fn in fns]

category_titles = {
    "session": "Session & Viewer Controls",
    "layer_management": "Layer Management",
    "viewer_controls": "Viewer Controls",
    "utilities": "Utilities",
}

category_descriptions = {
    "session": (
        "Functions for managing the napari viewer lifecycle, GUI state, and "
        "session information."
    ),
    "layer_management": (
        "Functions for creating, modifying, and organizing layers in the napari viewer."
    ),
    "viewer_controls": (
        "Functions for controlling the camera, navigation, and display settings."
    ),
    "utilities": (
        "Advanced utility functions for screenshots, timelapse capture, code execution, "
        "package management, and output retrieval."
    ),
}

# ---------------------------------------------------------------------------
# AST extraction
# ---------------------------------------------------------------------------

src_file = Path("src/napari_mcp/server.py")


def _extract_tool_functions(source: str) -> dict[str, dict]:
    """Parse server.py and extract tool function signatures + docstrings.

    Looks for ``async def <name>(...)`` inside ``create_server()`` that are
    decorated with ``@_register``.
    """
    tree = ast.parse(source)
    tools: dict[str, dict] = {}

    # Find the create_server function
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "create_server":
                # Walk its body for @_register decorated functions
                for child in ast.walk(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if child.name in ALL_TOOLS:
                            docstring = ast.get_docstring(child) or ""
                            sig = _format_signature(child)
                            tools[child.name] = {
                                "signature": sig,
                                "docstring": docstring,
                                "lineno": child.lineno,
                            }
                break
    return tools


def _format_signature(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Format an AST function node into a human-readable signature string."""
    args = func_node.args
    params = []

    # positional + keyword args
    all_args = args.args
    defaults = args.defaults
    n_no_default = len(all_args) - len(defaults)

    for i, arg in enumerate(all_args):
        annotation = ""
        if arg.annotation:
            annotation = f": {ast.unparse(arg.annotation)}"

        if i >= n_no_default:
            default = ast.unparse(defaults[i - n_no_default])
            params.append(f"{arg.arg}{annotation} = {default}")
        else:
            params.append(f"{arg.arg}{annotation}")

    # keyword-only args
    for i, arg in enumerate(args.kwonlyargs):
        annotation = ""
        if arg.annotation:
            annotation = f": {ast.unparse(arg.annotation)}"
        default = ""
        if args.kw_defaults[i] is not None:
            default = f" = {ast.unparse(args.kw_defaults[i])}"
        params.append(f"{arg.arg}{annotation}{default}")

    ret = ""
    if func_node.returns:
        ret = f" -> {ast.unparse(func_node.returns)}"

    return f"({', '.join(params)}){ret}"


def _render_tool_markdown(name: str, info: dict) -> str:
    """Render a single tool as markdown."""
    lines = []
    lines.append(f"### `{name}`")
    lines.append("")
    lines.append(f"```python")
    lines.append(f"async def {name}{info['signature']}")
    lines.append(f"```")
    lines.append("")
    if info["docstring"]:
        lines.append(info["docstring"])
        lines.append("")
    lines.append(
        f'<small>[Source: server.py:{info["lineno"]}]'
        f"(https://github.com/royerlab/napari-mcp/blob/main/src/napari_mcp/server.py#L{info['lineno']})</small>"
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generate pages
# ---------------------------------------------------------------------------

source = src_file.read_text()
tools = _extract_tool_functions(source)

# --- Category pages ---
for category, func_names in function_categories.items():
    filename = f"api/{category.replace('_', '-')}.md"
    title = category_titles[category]
    description = category_descriptions[category]

    with mkdocs_gen_files.open(filename, "w") as f:
        print(f"# {title}", file=f)
        print("", file=f)
        print(description, file=f)
        print("", file=f)

        for func_name in func_names:
            if func_name in tools:
                print(_render_tool_markdown(func_name, tools[func_name]), file=f)
            else:
                print(f"### `{func_name}`", file=f)
                print("", file=f)
                print("*Documentation not available (function not found in AST).*", file=f)
                print("", file=f)

# --- Complete reference page ---
with mkdocs_gen_files.open("api/reference.md", "w") as f:
    print("# Complete API Reference", file=f)
    print("", file=f)
    print(
        "Auto-generated documentation for all 16 napari MCP server tools, "
        "extracted from source code.",
        file=f,
    )
    print("", file=f)

    for category, func_names in function_categories.items():
        title = category_titles[category]
        print(f"## {title}", file=f)
        print("", file=f)
        for func_name in func_names:
            if func_name in tools:
                print(_render_tool_markdown(func_name, tools[func_name]), file=f)

# --- Supporting modules (these can use mkdocstrings directly) ---
with mkdocs_gen_files.open("api/modules.md", "w") as f:
    print("# Supporting Modules", file=f)
    print("", file=f)
    print("## ServerState", file=f)
    print("", file=f)
    print("::: napari_mcp.state.ServerState", file=f)
    print("    options:", file=f)
    print("      show_root_toc_entry: false", file=f)
    print("      members_order: source", file=f)
    print("", file=f)
    print("## Output Utilities", file=f)
    print("", file=f)
    print("::: napari_mcp.output", file=f)
    print("    options:", file=f)
    print("      show_root_toc_entry: false", file=f)
    print("", file=f)
    print("## Shared Helpers", file=f)
    print("", file=f)
    print("::: napari_mcp._helpers", file=f)
    print("    options:", file=f)
    print("      show_root_toc_entry: false", file=f)
    print("      members_order: source", file=f)

# --- Index page ---
nav_content = """# API Reference

This section contains comprehensive documentation for all napari MCP server tools.

## Organization

The API is organized into logical categories:

- **[Session & Viewer](session.md)** - Viewer lifecycle and GUI management
- **[Layer Management](layer-management.md)** - Creating and managing layers
- **[Viewer Controls](viewer-controls.md)** - Camera and navigation controls
- **[Utilities](utilities.md)** - Advanced features and tools
- **[Supporting Modules](modules.md)** - ServerState, helpers, and utilities

## Complete Reference

For a single page with all functions, see the [Complete API Reference](reference.md).

## Function Overview

| Category | Functions | Description |
|----------|-----------|-------------|
| **Session** | 3 functions | Viewer creation and session info |
| **Layers** | 8 functions | All layer types with full CRUD |
| **Navigation** | 1 function | Camera, dimensions, display modes |
| **Utilities** | 4 functions | Screenshots, code execution, packages |

**Total: 16 MCP tools available**
"""

with mkdocs_gen_files.open("api/index.md", "w") as f:
    print(nav_content, file=f)

print(f"API docs generated: {len(tools)}/{len(ALL_TOOLS)} tools extracted from AST")

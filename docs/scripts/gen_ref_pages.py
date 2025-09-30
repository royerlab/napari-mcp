"""Generate API reference pages from source code."""

from pathlib import Path

import mkdocs_gen_files

# Define the source file
src_file = Path("src/napari_mcp/server.py")

# Function categories for organization
function_categories = {
    "session": [
        "detect_viewers",
        "init_viewer",
        "close_viewer",
        "session_information",
    ],
    "layer_management": [
        "list_layers",
        "add_image",
        "add_labels",
        "add_points",
        "remove_layer",
        "set_layer_properties",
        "reorder_layer",
        "set_active_layer",
    ],
    "viewer_controls": [
        "reset_view",
        "set_camera",
        "set_ndisplay",
        "set_dims_current_step",
        "set_grid",
    ],
    "utilities": [
        "screenshot",
        "timelapse_screenshot",
        "execute_code",
        "install_packages",
        "read_output",
    ],
}

# Generate main API reference page
with mkdocs_gen_files.open("api/reference.md", "w") as f:
    print("# Complete API Reference", file=f)
    print("", file=f)
    print("Auto-generated documentation for all napari MCP server functions.", file=f)
    print("", file=f)
    print('!!! info "Documentation Structure"', file=f)
    print(
        "    This page shows both the **MCP tool interface** (what you call from AI assistants) "
        "and the **implementation** (NapariMCPTools class methods).",
        file=f,
    )
    print(
        "    All functions use NumPy-style docstrings with detailed parameter and "
        "return information.",
        file=f,
    )
    print("", file=f)

    # Show the wrapper functions (MCP tool interface)
    print("## MCP Tool Interface (server.py wrappers)", file=f)
    print("", file=f)
    print("These are the functions exposed as MCP tools:", file=f)
    print("", file=f)
    print("::: napari_mcp.server", file=f)
    print("    options:", file=f)
    print("      members_order: source", file=f)
    print("      show_root_toc_entry: false", file=f)
    print("      show_source: true", file=f)
    print("      filters:", file=f)
    print("        - '!^_'", file=f)
    print("        - '!^NapariMCPTools$'", file=f)
    print("", file=f)

    # Show the implementation class
    print("## Implementation (NapariMCPTools class)", file=f)
    print("", file=f)
    print("The actual implementation behind the MCP tools:", file=f)
    print("", file=f)
    print("::: napari_mcp.server.NapariMCPTools", file=f)
    print("    options:", file=f)
    print("      members_order: source", file=f)
    print("      show_root_toc_entry: false", file=f)
    print("      show_source: true", file=f)
    print("      heading_level: 3", file=f)

# Generate category-specific pages
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

for category, functions in function_categories.items():
    filename = f"api/{category.replace('_', '-')}.md"
    title = category_titles[category]
    description = category_descriptions[category]

    with mkdocs_gen_files.open(filename, "w") as f:
        print(f"# {title}", file=f)
        print("", file=f)
        print(description, file=f)
        print("", file=f)

        for func in functions:
            print(f"## {func}", file=f)
            print("", file=f)

            # Show the wrapper function (MCP tool interface)
            print("### MCP Tool Interface", file=f)
            print("", file=f)
            print(f"::: napari_mcp.server.{func}", file=f)
            print("    options:", file=f)
            print("      show_root_toc_entry: false", file=f)
            print("      show_source: true", file=f)
            print("", file=f)

            # Show the actual implementation (NapariMCPTools class method)
            print("### Implementation", file=f)
            print("", file=f)
            print(f"::: napari_mcp.server.NapariMCPTools.{func}", file=f)
            print("    options:", file=f)
            print("      show_root_toc_entry: false", file=f)
            print("      show_source: true", file=f)
            print("      heading_level: 4", file=f)
            print("", file=f)

# Generate navigation file
nav_content = """# API Reference

This section contains comprehensive documentation for all napari MCP server functions.

## Organization

The API is organized into logical categories:

- **[Session & Viewer](session.md)** - Viewer lifecycle and GUI management
- **[Layer Management](layer-management.md)** - Creating and managing layers
- **[Viewer Controls](viewer-controls.md)** - Camera and navigation controls
- **[Utilities](utilities.md)** - Advanced features and tools

## Complete Reference

For a single page with all functions, see the [Complete API Reference](reference.md).

## Function Overview

| Category | Functions | Description |
|----------|-----------|-------------|
| **Session** | 4 functions | Viewer creation, detection, and session info |
| **Layers** | 8 functions | Image, label, point layers with full control |
| **Navigation** | 5 functions | Camera, dimensions, display modes |
| **Utilities** | 5 functions | Screenshots, timelapse, code execution, packages |

**Total: 22 MCP tools available**
"""

with mkdocs_gen_files.open("api/index.md", "w") as f:
    print(nav_content, file=f)

print("✅ API documentation pages generated successfully!")

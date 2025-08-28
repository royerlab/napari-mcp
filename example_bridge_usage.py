#!/usr/bin/env python
"""
Example script showing how to use napari-mcp-bridge plugin.

This demonstrates:
1. Starting napari with the plugin
2. Loading some sample data
3. Starting the MCP server
4. Connecting to it from the main napari-mcp server
"""

import napari
import numpy as np
try:
    from skimage import data
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False


def main():
    """Run the example."""
    print("Starting napari with MCP bridge plugin...")
    
    # Create viewer
    viewer = napari.Viewer(title="napari with MCP Bridge")
    
    # Load some sample data
    print("Loading sample data...")
    if HAS_SKIMAGE:
        viewer.add_image(data.astronaut(), name="astronaut")
        viewer.add_image(data.camera(), name="camera", colormap="viridis", opacity=0.5)
    else:
        # Create synthetic data if scikit-image not available
        viewer.add_image(np.random.rand(512, 512, 3), name="random_color")
        viewer.add_image(np.random.rand(512, 512), name="random_gray", colormap="viridis", opacity=0.5)
    
    # Add some points
    points = np.random.rand(20, 2) * 512
    viewer.add_points(points, size=10, name="random_points")
    
    # Try to load the plugin
    try:
        # Add the MCP control widget
        widget, plugin_widget = viewer.window.add_plugin_dock_widget(
            'napari-mcp-bridge', 'MCP Server Control'
        )
        print("MCP Bridge plugin loaded successfully!")
        print("\nInstructions:")
        print("1. Click 'Start Server' in the MCP Server Control widget")
        print("2. The server will run on port 9999")
        print("3. In another terminal, set: export NAPARI_MCP_USE_EXTERNAL=true")
        print("4. Run your napari-mcp client/LLM to connect to this viewer")
        print("\nThe AI assistant will be able to control THIS viewer session!")
        
    except Exception as e:
        print(f"Could not load plugin: {e}")
        print("\nMake sure the plugin is installed:")
        print("  cd napari-mcp-bridge")
        print("  pip install -e .")
    
    # Run napari
    napari.run()


if __name__ == "__main__":
    main()
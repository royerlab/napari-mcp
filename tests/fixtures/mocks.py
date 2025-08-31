"""Consolidated mock definitions for napari-mcp tests.

This module provides all mock objects and builders used across the test suite,
ensuring consistency and proper isolation between tests.
"""

import types
from typing import Any
from unittest.mock import AsyncMock, Mock

import numpy as np


class MockLayerBuilder:
    """Builder for creating customized mock layers."""

    def __init__(self):
        self._name = "test_layer"
        self._data = None
        self._visible = True
        self._opacity = 1.0
        self._size = 10
        self._colormap = None
        self._blending = None
        self._contrast_limits = [0.0, 1.0]
        self._gamma = 1.0
        self._layer_type = "Image"

    def with_name(self, name: str) -> "MockLayerBuilder":
        """Set the layer name."""
        self._name = name
        return self

    def with_data(self, data: np.ndarray) -> "MockLayerBuilder":
        """Set the layer data."""
        self._data = data
        return self

    def with_visibility(self, visible: bool) -> "MockLayerBuilder":
        """Set layer visibility."""
        self._visible = visible
        return self

    def with_opacity(self, opacity: float) -> "MockLayerBuilder":
        """Set layer opacity."""
        self._opacity = opacity
        return self

    def with_type(self, layer_type: str) -> "MockLayerBuilder":
        """Set layer type (Image, Points, Labels, etc.)."""
        self._layer_type = layer_type
        return self

    def build(self) -> Mock:
        """Build the mock layer."""
        layer = Mock()
        layer.name = self._name
        layer.__class__.__name__ = self._layer_type
        layer.data = self._data if self._data is not None else np.zeros((10, 10))
        layer.visible = self._visible
        layer.opacity = self._opacity
        layer.size = self._size
        layer.colormap = (
            Mock(name=self._colormap) if self._colormap else Mock(name="viridis")
        )
        layer.blending = self._blending
        layer.contrast_limits = self._contrast_limits
        layer.gamma = self._gamma

        # Make it hashable
        layer.__hash__ = lambda: hash(self._name)
        layer.__eq__ = lambda self, other: self.name == getattr(other, "name", None)

        return layer


class MockViewerBuilder:
    """Builder for creating customized mock viewers with specific configurations."""

    def __init__(self):
        self._title = "Test Viewer"
        self._layers = []
        self._ndisplay = 2
        self._camera_center = [0.0, 0.0]
        self._camera_zoom = 1.0
        self._camera_angles = [0.0]
        self._grid_enabled = False
        self._show = True

    def with_title(self, title: str) -> "MockViewerBuilder":
        """Set viewer title."""
        self._title = title
        return self

    def with_layers(self, layers: list[Any]) -> "MockViewerBuilder":
        """Add layers to the viewer."""
        self._layers = layers
        return self

    def with_camera(
        self, center: list[float], zoom: float, angles: list[float] | None = None
    ) -> "MockViewerBuilder":
        """Configure camera settings."""
        self._camera_center = center
        self._camera_zoom = zoom
        if angles:
            self._camera_angles = angles
        return self

    def with_dims(self, ndisplay: int) -> "MockViewerBuilder":
        """Set dimensions display mode."""
        self._ndisplay = ndisplay
        return self

    def build(self) -> Mock:
        """Build the mock viewer."""
        viewer = Mock()
        viewer.title = self._title
        viewer.show = self._show

        # Setup layers
        viewer.layers = MockLayersCollection(self._layers)

        # Setup window
        viewer.window = types.SimpleNamespace(
            qt_viewer=types.SimpleNamespace(
                canvas=types.SimpleNamespace(
                    native=types.SimpleNamespace(resize=Mock()),
                    size=Mock(
                        return_value=types.SimpleNamespace(
                            width=Mock(return_value=800), height=Mock(return_value=600)
                        )
                    ),
                )
            )
        )

        # Setup camera
        viewer.camera = types.SimpleNamespace(
            center=self._camera_center.copy(),
            zoom=self._camera_zoom,
            angles=tuple(self._camera_angles),
        )

        # Setup dims
        viewer.dims = types.SimpleNamespace(
            ndisplay=self._ndisplay, current_step={}, set_current_step=Mock()
        )

        # Setup grid
        viewer.grid = types.SimpleNamespace(enabled=self._grid_enabled)

        # Add methods
        viewer.close = Mock()
        viewer.reset_view = Mock()
        viewer.screenshot = Mock(return_value=np.zeros((100, 100, 4), dtype=np.uint8))

        # Add layer creation methods
        def add_image(data, **kwargs):
            layer = (
                MockLayerBuilder()
                .with_name(kwargs.get("name", "image"))
                .with_data(data)
                .build()
            )
            viewer.layers.append(layer)
            return layer

        def add_points(data, **kwargs):
            layer = (
                MockLayerBuilder()
                .with_name(kwargs.get("name", "points"))
                .with_data(data)
                .with_type("Points")
                .build()
            )
            viewer.layers.append(layer)
            return layer

        def add_labels(data, **kwargs):
            layer = (
                MockLayerBuilder()
                .with_name(kwargs.get("name", "labels"))
                .with_data(data)
                .with_type("Labels")
                .build()
            )
            viewer.layers.append(layer)
            return layer

        viewer.add_image = Mock(side_effect=add_image)
        viewer.add_points = Mock(side_effect=add_points)
        viewer.add_labels = Mock(side_effect=add_labels)

        return viewer


class MockLayersCollection:
    """Mock implementation of napari layers collection with proper isolation."""

    def __init__(self, initial_layers: list[Any] | None = None):
        self._layers = initial_layers or []
        self.selection = set()

    def __contains__(self, name: str) -> bool:
        return any(layer.name == name for layer in self._layers)

    def __getitem__(self, key):
        if isinstance(key, str):
            for layer in self._layers:
                if hasattr(layer, "name") and layer.name == key:
                    return layer
            raise KeyError(f"Layer '{key}' not found")
        return self._layers[key]

    def __len__(self) -> int:
        return len(self._layers)

    def __iter__(self):
        return iter(self._layers)

    def append(self, layer: Any) -> None:
        self._layers.append(layer)

    def remove(self, layer: Any) -> None:
        if isinstance(layer, str):
            layer = self[layer]
        self._layers.remove(layer)

    def move(self, src_index: int, dst_index: int) -> None:
        layer = self._layers.pop(src_index)
        self._layers.insert(dst_index, layer)

    def index(self, layer: Any) -> int:
        if isinstance(layer, str):
            for i, layer_obj in enumerate(self._layers):
                if layer_obj.name == layer:
                    return i
            raise ValueError(f"Layer '{layer}' not found")
        return self._layers.index(layer)


class MockNapariModule:
    """Factory for creating mock napari modules with proper isolation."""

    @staticmethod
    def create() -> dict[str, types.ModuleType]:
        """Create a complete set of mock napari modules."""
        # Main napari module
        mock_napari = types.ModuleType("napari")
        mock_napari.__file__ = None
        mock_napari.Viewer = Mock
        mock_napari.current_viewer = Mock(return_value=None)

        # Viewer submodule
        mock_viewer = types.ModuleType("napari.viewer")
        mock_viewer.Viewer = Mock

        # Window submodule
        mock_window = types.ModuleType("napari.window")

        # Layers submodule
        mock_layers = types.ModuleType("napari.layers")
        mock_layers.Image = Mock
        mock_layers.Points = Mock
        mock_layers.Labels = Mock
        mock_layers.Shapes = Mock
        mock_layers.Surface = Mock
        mock_layers.Tracks = Mock
        mock_layers.Vectors = Mock

        return {
            "napari": mock_napari,
            "napari.viewer": mock_viewer,
            "napari.window": mock_window,
            "napari.layers": mock_layers,
        }


class MockBridgeServer:
    """Mock implementation of NapariBridgeServer for testing."""

    def __init__(self, viewer: Any, port: int = 9999):
        self.viewer = viewer
        self.port = port
        self.is_running = False
        self.server = Mock()

    def start(self) -> bool:
        if not self.is_running:
            self.is_running = True
            return True
        return False

    def stop(self) -> bool:
        if self.is_running:
            self.is_running = False
            return True
        return False

    def _encode_png_base64(self, img: np.ndarray) -> dict[str, str]:
        return {"mime_type": "image/png", "base64_data": "mock_base64_data"}


class MockQtBridge:
    """Mock implementation of QtBridge for testing thread safety."""

    def __init__(self):
        self.signal_received = Mock()
        self.moveToThread = Mock()

    def run_in_main_thread(self, func, *args, **kwargs):
        """Execute function immediately (no thread switching in tests)."""
        return func(*args, **kwargs)


def create_async_mock_tools():
    """Create async mock tools for testing MCP server functionality."""
    tools = AsyncMock()

    # Mock tool methods
    tools.init_viewer = AsyncMock(return_value={"status": "ok", "viewer_id": 1})
    tools.list_layers = AsyncMock(return_value=[])
    tools.add_image = AsyncMock(return_value={"status": "ok", "layer": "image_1"})
    tools.add_points = AsyncMock(return_value={"status": "ok", "layer": "points_1"})
    tools.add_labels = AsyncMock(return_value={"status": "ok", "layer": "labels_1"})
    tools.remove_layer = AsyncMock(return_value={"status": "ok"})
    tools.rename_layer = AsyncMock(return_value={"status": "ok"})
    tools.set_layer_opacity = AsyncMock(return_value={"status": "ok"})
    tools.set_layer_visible = AsyncMock(return_value={"status": "ok"})
    tools.screenshot = AsyncMock(return_value={"status": "ok", "image": "base64_data"})
    tools.set_camera = AsyncMock(return_value={"status": "ok"})
    tools.set_zoom = AsyncMock(return_value={"status": "ok"})
    tools.reset_view = AsyncMock(return_value={"status": "ok"})
    tools.execute_code = AsyncMock(return_value={"status": "ok", "result": None})

    return tools


# Utility functions for test setup


def reset_all_mocks(*mocks):
    """Reset all provided mocks to their initial state."""
    for mock in mocks:
        if hasattr(mock, "reset_mock"):
            mock.reset_mock()


def assert_mock_viewer_state(
    viewer: Mock, expected_layers: int = 0, expected_title: str = ""
):
    """Assert the state of a mock viewer."""
    assert len(viewer.layers) == expected_layers
    if expected_title:
        assert viewer.title == expected_title

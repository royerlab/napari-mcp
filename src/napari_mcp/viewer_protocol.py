"""Protocol definition for napari viewer backends."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ViewerProtocol(Protocol):
    """Structural protocol for viewer backends.

    Both a real ``napari.Viewer`` and a bridge-proxied viewer satisfy this
    protocol without requiring inheritance.
    """

    title: str
    layers: Any  # napari LayerList or compatible collection
    dims: Any  # .ndisplay, .current_step, .set_current_step(), .nsteps
    camera: Any  # .center, .zoom, .angles
    grid: Any  # .enabled
    window: Any  # ._qt_window (optional, used for Qt integration)

    def add_image(self, data: Any, **kwargs: Any) -> Any:
        """Add an image layer."""
        ...

    def add_labels(self, data: Any, **kwargs: Any) -> Any:
        """Add a labels layer."""
        ...

    def add_points(self, data: Any, **kwargs: Any) -> Any:
        """Add a points layer."""
        ...

    def add_shapes(self, data: Any, **kwargs: Any) -> Any:
        """Add a shapes layer."""
        ...

    def add_vectors(self, data: Any, **kwargs: Any) -> Any:
        """Add a vectors layer."""
        ...

    def add_tracks(self, data: Any, **kwargs: Any) -> Any:
        """Add a tracks layer."""
        ...

    def add_surface(self, data: Any, **kwargs: Any) -> Any:
        """Add a surface layer."""
        ...

    def screenshot(self, **kwargs: Any) -> Any:
        """Take a screenshot, returning a numpy array."""
        ...

    def reset_view(self) -> None:
        """Reset camera view to fit data."""
        ...

    def close(self) -> None:
        """Close the viewer."""
        ...

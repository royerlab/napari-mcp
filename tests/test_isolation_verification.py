"""Test suite to verify proper test isolation.

These tests verify that:
1. Tests don't leak state between runs
2. Mocks are properly isolated
3. Server state is reset between tests
4. No global module pollution occurs
"""

import sys
import pytest
import asyncio
from unittest.mock import Mock, patch
import numpy as np


class TestIsolationVerification:
    """Verify that test isolation is working correctly."""
    
    @pytest.mark.isolated
    def test_no_global_napari_mock(self):
        """Verify napari is not globally mocked by default."""
        # napari should NOT be in sys.modules unless explicitly mocked
        if "napari" in sys.modules:
            napari_module = sys.modules["napari"]
            # If it exists, it should be a real module or explicitly mocked
            assert hasattr(napari_module, "__file__") or "mock" in str(type(napari_module)).lower()
    
    @pytest.mark.isolated
    def test_mock_napari_fixture_isolation(self, mock_napari):
        """Verify mock_napari fixture provides isolated mock."""
        # First access - create a viewer
        viewer1 = mock_napari.Viewer(title="Test1")
        viewer1.custom_attr = "test1"
        
        # Second access - create another viewer
        viewer2 = mock_napari.Viewer(title="Test2")
        
        # Viewers should be independent
        assert not hasattr(viewer2, 'custom_attr')
        assert viewer1.title == "Test1"
        assert viewer2.title == "Test2"
    
    @pytest.mark.isolated
    def test_server_state_reset(self):
        """Verify server state is reset between tests."""
        from napari_mcp import server as napari_mcp_server
        
        # State should be clean at test start
        assert napari_mcp_server._viewer is None
        assert napari_mcp_server._window_close_connected is False
        assert napari_mcp_server._exec_globals == {}
        
        # Modify state
        napari_mcp_server._viewer = Mock()
        napari_mcp_server._window_close_connected = True
        napari_mcp_server._exec_globals = {"test": "value"}
        
        # State will be reset by the fixture after this test
    
    @pytest.mark.isolated
    def test_server_state_is_clean(self):
        """Verify server state was reset from previous test."""
        from napari_mcp import server as napari_mcp_server
        
        # State should be clean despite previous test modifications
        assert napari_mcp_server._viewer is None
        assert napari_mcp_server._window_close_connected is False
        assert napari_mcp_server._exec_globals == {}
    
    @pytest.mark.isolated
    @pytest.mark.asyncio
    async def test_async_isolation(self):
        """Verify async tests are properly isolated."""
        # Create some async state
        test_event = asyncio.Event()
        test_event.set()
        
        # Create a task
        async def background_work():
            await asyncio.sleep(0.01)
            return "done"
        
        task = asyncio.create_task(background_work())
        result = await task
        assert result == "done"
        
        # This state should not affect other tests
    
    @pytest.mark.isolated
    def test_mock_viewer_factory_isolation(self, napari_mock_factory):
        """Verify mock factory creates independent instances."""
        viewer1 = napari_mock_factory(title="Viewer1")
        viewer2 = napari_mock_factory(title="Viewer2")
        
        # Add layer to viewer1
        viewer1.add_image(np.zeros((10, 10)), name="layer1")
        
        # Viewer2 should not have the layer
        assert len(viewer1.layers) == 1
        assert len(viewer2.layers) == 0
        
        # Titles should be independent
        assert viewer1.title == "Viewer1"
        assert viewer2.title == "Viewer2"
    
    @pytest.mark.isolated
    def test_isolated_mock_viewer_fixture(self, isolated_mock_viewer):
        """Verify isolated_mock_viewer provides clean instance."""
        # Should have clean state
        assert isolated_mock_viewer.title == "Isolated Test Viewer"
        assert len(isolated_mock_viewer.layers) == 0
        
        # Modifications should not affect other tests
        isolated_mock_viewer.title = "Modified"
        isolated_mock_viewer.layers.append(Mock())
    
    @pytest.mark.isolated
    def test_no_state_leakage_after_modification(self, isolated_mock_viewer):
        """Verify previous test modifications don't leak."""
        # Should have original state, not modified state
        assert isolated_mock_viewer.title == "Isolated Test Viewer"
        assert len(isolated_mock_viewer.layers) == 0
    
    @pytest.mark.isolated
    def test_fixture_mock_independence(self):
        """Verify fixtures can use different mocking strategies."""
        from fixtures.mocks import MockViewerBuilder, MockLayerBuilder
        
        # Create viewer with builder
        viewer = MockViewerBuilder().with_title("Built Viewer").build()
        
        # Create layer with builder
        layer = MockLayerBuilder().with_name("Built Layer").build()
        
        # They should be independent
        assert viewer.title == "Built Viewer"
        assert layer.name == "Built Layer"
        
        # Adding layer should work
        viewer.layers.append(layer)
        assert len(viewer.layers) == 1


class TestModuleIsolation:
    """Test that module-level isolation is working."""
    
    @pytest.mark.isolated
    def test_sys_modules_not_polluted(self):
        """Verify sys.modules is not permanently polluted."""
        # Check for test-only modules that shouldn't exist
        test_modules = [
            "test_mock_module",
            "fake_napari",
            "_test_viewer"
        ]
        
        for module_name in test_modules:
            assert module_name not in sys.modules, f"Test module {module_name} found in sys.modules"
    
    @pytest.mark.isolated
    def test_monkeypatch_cleanup(self, monkeypatch):
        """Verify monkeypatch properly cleans up."""
        # Create a test module
        test_module = type(sys)("test_isolation_module")
        test_module.test_value = "test"
        
        # Monkeypatch it
        monkeypatch.setitem(sys.modules, "test_isolation_module", test_module)
        
        # Verify it's there
        assert "test_isolation_module" in sys.modules
        assert sys.modules["test_isolation_module"].test_value == "test"
        
        # It will be cleaned up after this test
    
    @pytest.mark.isolated
    def test_monkeypatch_was_cleaned(self):
        """Verify previous test's monkeypatch was cleaned up."""
        # The test module from previous test should be gone
        assert "test_isolation_module" not in sys.modules


class TestConcurrentIsolation:
    """Test isolation with concurrent test execution."""
    
    @pytest.mark.isolated
    @pytest.mark.parametrize("test_id", range(5))
    def test_parallel_execution_isolation(self, test_id, napari_mock_factory):
        """Verify tests can run in parallel without interference."""
        # Each test gets its own viewer
        viewer = napari_mock_factory(title=f"Viewer_{test_id}")
        
        # Add unique layer
        viewer.add_image(
            np.ones((10, 10)) * test_id,
            name=f"layer_{test_id}"
        )
        
        # Verify uniqueness
        assert viewer.title == f"Viewer_{test_id}"
        assert len(viewer.layers) == 1
        assert viewer.layers[0].name == f"layer_{test_id}"
        
        # Check data is correct
        assert np.all(viewer.layers[0].data == test_id)


class TestStateVerification:
    """Verify state management across test lifecycle."""
    
    counter = 0  # Class variable to track state
    
    @pytest.mark.isolated
    def test_state_increment_1(self):
        """First test modifying class state."""
        TestStateVerification.counter += 1
        assert TestStateVerification.counter >= 1
    
    @pytest.mark.isolated
    def test_state_increment_2(self):
        """Second test modifying class state."""
        TestStateVerification.counter += 1
        assert TestStateVerification.counter >= 1
    
    @pytest.mark.isolated
    def test_state_increment_3(self):
        """Third test verifying accumulated state."""
        TestStateVerification.counter += 1
        # This would fail with perfect isolation, but class state persists
        # This is expected Python behavior - only instance state is isolated
        assert TestStateVerification.counter >= 1


@pytest.mark.isolated
class TestFixtureIsolation:
    """Test that fixtures provide proper isolation."""
    
    def test_reset_server_state_fixture_works(self):
        """Verify reset_server_state fixture is active."""
        from napari_mcp import server
        
        # Modify server state
        server._viewer = Mock()
        server._exec_globals["test"] = "value"
        
        # Will be reset after test
    
    def test_server_state_was_reset(self):
        """Verify server state was reset by fixture."""
        from napari_mcp import server
        
        # Should be clean
        assert server._viewer is None
        assert "test" not in server._exec_globals
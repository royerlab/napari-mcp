"""Async utilities for proper test synchronization and timing."""

import asyncio
import time
from typing import Callable, Any, Optional
from contextlib import asynccontextmanager


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 1.0,
    poll_interval: float = 0.01,
    error_message: Optional[str] = None
) -> None:
    """Wait for a condition to become true with timeout.
    
    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: Time between condition checks in seconds
        error_message: Custom error message if timeout occurs
    
    Raises:
        TimeoutError: If condition is not met within timeout
    """
    start_time = time.time()
    while not condition():
        if time.time() - start_time > timeout:
            msg = error_message or f"Condition not met within {timeout} seconds"
            raise TimeoutError(msg)
        await asyncio.sleep(poll_interval)


async def wait_for_async_condition(
    async_condition: Callable[[], Any],
    timeout: float = 1.0,
    poll_interval: float = 0.01,
    error_message: Optional[str] = None
) -> None:
    """Wait for an async condition to become true with timeout.
    
    Args:
        async_condition: Async callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: Time between condition checks in seconds
        error_message: Custom error message if timeout occurs
    
    Raises:
        TimeoutError: If condition is not met within timeout
    """
    start_time = time.time()
    while not await async_condition():
        if time.time() - start_time > timeout:
            msg = error_message or f"Async condition not met within {timeout} seconds"
            raise TimeoutError(msg)
        await asyncio.sleep(poll_interval)


@asynccontextmanager
async def timeout_context(seconds: float, error_message: Optional[str] = None):
    """Context manager for operations with timeout.
    
    Args:
        seconds: Timeout in seconds
        error_message: Custom error message if timeout occurs
    
    Raises:
        asyncio.TimeoutError: If operation doesn't complete within timeout
    """
    try:
        async with asyncio.timeout(seconds):
            yield
    except asyncio.TimeoutError:
        msg = error_message or f"Operation timed out after {seconds} seconds"
        raise asyncio.TimeoutError(msg)


class AsyncTestHelper:
    """Helper class for async testing with proper cleanup."""
    
    def __init__(self):
        self.tasks = []
        self.background_tasks = []
    
    async def run_with_timeout(
        self, 
        coro, 
        timeout: float = 1.0,
        cleanup: Optional[Callable] = None
    ) -> Any:
        """Run a coroutine with timeout and optional cleanup.
        
        Args:
            coro: Coroutine to run
            timeout: Timeout in seconds
            cleanup: Optional cleanup function to call on timeout
        
        Returns:
            Result of the coroutine
        
        Raises:
            asyncio.TimeoutError: If coroutine doesn't complete within timeout
        """
        try:
            async with asyncio.timeout(timeout):
                return await coro
        except asyncio.TimeoutError:
            if cleanup:
                await cleanup() if asyncio.iscoroutinefunction(cleanup) else cleanup()
            raise
    
    def create_background_task(self, coro) -> asyncio.Task:
        """Create a background task that will be cleaned up automatically.
        
        Args:
            coro: Coroutine to run in background
        
        Returns:
            The created task
        """
        task = asyncio.create_task(coro)
        self.background_tasks.append(task)
        return task
    
    async def cleanup_tasks(self) -> None:
        """Cancel and cleanup all background tasks."""
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.background_tasks.clear()
    
    async def wait_for_tasks(self, timeout: float = 1.0) -> None:
        """Wait for all background tasks to complete.
        
        Args:
            timeout: Maximum time to wait for all tasks
        
        Raises:
            asyncio.TimeoutError: If tasks don't complete within timeout
        """
        if self.background_tasks:
            async with asyncio.timeout(timeout):
                await asyncio.gather(*self.background_tasks, return_exceptions=True)


def replace_sleep_with_event(test_func):
    """Decorator to replace time.sleep with proper event-based waiting.
    
    This decorator patches time.sleep to use asyncio.sleep when in async context.
    """
    import functools
    from unittest.mock import patch
    
    @functools.wraps(test_func)
    async def wrapper(*args, **kwargs):
        original_sleep = time.sleep
        
        def smart_sleep(seconds):
            """Sleep that works in both sync and async contexts."""
            try:
                # Check if we're in an async context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in async context, create a task
                    loop.create_task(asyncio.sleep(seconds))
                else:
                    original_sleep(seconds)
            except RuntimeError:
                # No event loop, use regular sleep
                original_sleep(seconds)
        
        with patch('time.sleep', smart_sleep):
            return await test_func(*args, **kwargs)
    
    return wrapper


class ServerStartupHelper:
    """Helper for properly starting and stopping test servers."""
    
    def __init__(self, server, startup_timeout: float = 2.0):
        self.server = server
        self.startup_timeout = startup_timeout
    
    async def start_and_verify(self) -> bool:
        """Start server and verify it's running.
        
        Returns:
            True if server started successfully
        
        Raises:
            TimeoutError: If server doesn't start within timeout
        """
        # Start the server
        result = self.server.start()
        if not result:
            return False
        
        # Wait for server to be fully running
        await wait_for_condition(
            lambda: self.server.is_running,
            timeout=self.startup_timeout,
            error_message="Server failed to start"
        )
        
        return True
    
    async def stop_and_verify(self) -> bool:
        """Stop server and verify it's stopped.
        
        Returns:
            True if server stopped successfully
        """
        if not self.server.is_running:
            return True
        
        result = self.server.stop()
        if not result:
            return False
        
        # Wait for server to fully stop
        await wait_for_condition(
            lambda: not self.server.is_running,
            timeout=1.0,
            error_message="Server failed to stop"
        )
        
        return True


# Qt-specific timing utilities

def qt_process_events(qtbot, wait_ms: int = 10):
    """Process Qt events with proper waiting.
    
    Args:
        qtbot: pytest-qt fixture
        wait_ms: Time to wait in milliseconds
    """
    qtbot.wait(wait_ms)


def qt_wait_for_signal(qtbot, signal, timeout: int = 1000):
    """Wait for a Qt signal with timeout.
    
    Args:
        qtbot: pytest-qt fixture
        signal: Qt signal to wait for
        timeout: Timeout in milliseconds
    
    Returns:
        The signal arguments when emitted
    """
    with qtbot.waitSignal(signal, timeout=timeout) as blocker:
        return blocker.args
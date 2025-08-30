#!/usr/bin/env python
"""Run the GUI test directly without pytest.

Note: This file is a helper runner and not part of the pytest suite. It is
explicitly skipped during pytest collection to avoid forcing real GUI tests in
CI or local runs without the required Qt bindings.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Prevent pytest from collecting the imported test symbol below
pytestmark = pytest.mark.skip("Helper runner; excluded from pytest collection.")

# Set environment variables
os.environ["RUN_REAL_NAPARI_TESTS"] = "1"
os.environ["QT_API"] = "pyqt6"

# Add source to path
sys.path.insert(0, "src")
sys.path.insert(0, "tests")

# Import the test function
from test_tools_real import test_all_tools_with_real_napari


async def main():
    """Run the test."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            await test_all_tools_with_real_napari(Path(tmp_dir))
            print("✅ Test passed!")
            return 0
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            return 1
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback

            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

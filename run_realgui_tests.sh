#!/bin/bash
# Run real GUI tests with napari viewer
# These tests require a display (real or virtual)

echo "=================================="
echo "Real GUI Integration Tests"
echo "=================================="
echo ""
echo "These tests require a real Qt/napari environment."
echo "On headless systems, they need xvfb."
echo ""

# Check if we're on a headless system and xvfb is available
if [ -z "$DISPLAY" ]; then
    echo "No DISPLAY found. Checking for xvfb..."
    if command -v xvfb-run &> /dev/null; then
        echo "Running with xvfb..."
        xvfb-run -a --server-args="-screen 0 1024x768x24" \
            uv run pytest tests/test_real_integration.py -v -m realgui \
            --tb=short \
            --durations=5
    else
        echo "Error: No DISPLAY and xvfb not found."
        echo "Install xvfb or run with a display."
        exit 1
    fi
else
    echo "Display found: $DISPLAY"
    echo "Running tests with real display..."

    # Set Qt platform based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        export QT_QPA_PLATFORM=cocoa
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ]; then
            # SSH session - use offscreen
            export QT_QPA_PLATFORM=offscreen
        fi
    fi

    uv run pytest tests/test_real_integration.py -v -m realgui \
        --tb=short \
        --durations=5
fi

echo ""
echo "=================================="
echo "Test completed"
echo "=================================="

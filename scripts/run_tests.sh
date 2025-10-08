#!/bin/bash
set -e

echo "============================================================"
echo "🧪 Music-to-MIDI API - Test Suite"
echo "============================================================"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Install test dependencies if needed
echo "📚 Checking test dependencies..."
pip install -q pytest pytest-asyncio httpx

# Run tests with coverage
echo ""
echo "🧪 Running tests..."
echo "------------------------------------------------------------"

# Run pytest with verbose output
pytest tests/ -v --tb=short

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ All tests passed!"
    echo "============================================================"
    exit 0
else
    echo ""
    echo "============================================================"
    echo "❌ Some tests failed"
    echo "============================================================"
    exit 1
fi

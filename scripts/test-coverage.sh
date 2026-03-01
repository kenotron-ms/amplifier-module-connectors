#!/usr/bin/env bash
# Test runner with coverage reporting
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${YELLOW}=== Test Coverage Runner ===${NC}"

# Check if venv exists
if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Run: make setup"
    exit 1
fi

# Activate venv
source "${PROJECT_ROOT}/.venv/bin/activate"

# Check for pytest-cov
if ! python -c "import pytest_cov" 2>/dev/null; then
    echo -e "${YELLOW}Installing pytest-cov...${NC}"
    uv pip install pytest-cov --quiet
fi

# Add src to PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"

# Run tests with coverage
cd "${PROJECT_ROOT}"
echo -e "${GREEN}Running tests with coverage...${NC}"

python -m pytest \
    --cov=src \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=term:skip-covered \
    -v

TEST_EXIT_CODE=$?

# Open coverage report if successful
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Coverage report generated${NC}"
    echo "HTML report: file://${PROJECT_ROOT}/htmlcov/index.html"
    
    # Try to open in browser (macOS)
    if command -v open &> /dev/null; then
        echo "Opening coverage report in browser..."
        open htmlcov/index.html
    fi
else
    echo -e "${RED}✗ Tests failed${NC}"
fi

exit $TEST_EXIT_CODE

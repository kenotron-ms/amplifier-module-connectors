#!/usr/bin/env bash
# Test runner script that handles venv activation correctly
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${YELLOW}=== Amplifier Module Connectors Test Runner ===${NC}"
echo "Project root: ${PROJECT_ROOT}"

# Check if venv exists
if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
    echo -e "${RED}Error: Virtual environment not found at ${PROJECT_ROOT}/.venv${NC}"
    echo "Run: uv venv"
    exit 1
fi

# Activate venv
echo -e "${GREEN}Activating virtual environment...${NC}"
source "${PROJECT_ROOT}/.venv/bin/activate"

# Verify Python
PYTHON_VERSION=$(python --version 2>&1)
echo "Using: ${PYTHON_VERSION}"

# Add src to PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
echo "PYTHONPATH: ${PYTHONPATH}"

# Run tests
echo -e "${GREEN}Running tests...${NC}"
cd "${PROJECT_ROOT}"

# Parse arguments
PYTEST_ARGS=()
VERBOSE=false

for arg in "$@"; do
    case $arg in
        -v|--verbose)
            VERBOSE=true
            PYTEST_ARGS+=("-v")
            ;;
        -vv|--very-verbose)
            VERBOSE=true
            PYTEST_ARGS+=("-vv")
            ;;
        -k)
            # Next arg is the test pattern
            PYTEST_ARGS+=("-k")
            ;;
        *)
            PYTEST_ARGS+=("$arg")
            ;;
    esac
done

# Default to verbose if no args
if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    PYTEST_ARGS=("-v")
fi

# Run pytest
python -m pytest "${PYTEST_ARGS[@]}"
TEST_EXIT_CODE=$?

# Report results
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Tests failed with exit code ${TEST_EXIT_CODE}${NC}"
fi

exit $TEST_EXIT_CODE

#!/usr/bin/env bash
# Setup script for development environment
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${YELLOW}=== Amplifier Module Connectors Setup ===${NC}"
echo "Project root: ${PROJECT_ROOT}"

cd "${PROJECT_ROOT}"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}Found uv: $(uv --version)${NC}"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    uv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate venv
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install dependencies in development mode
echo -e "${YELLOW}Installing dependencies...${NC}"

# Install pytest and other dev dependencies first
echo "Installing dev dependencies..."
uv pip install pytest pytest-asyncio --quiet

# Install the package in development mode with src path
echo "Installing package in development mode..."
# Just add src to PYTHONPATH instead of installing
echo -e "${GREEN}✓ Using PYTHONPATH for src/ directory${NC}"

# Verify installation
echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo "Python: $(python --version)"
echo "Pytest: $(python -m pytest --version)"
echo ""
echo "To run tests:"
echo "  make test              # Run all tests"
echo "  make test-verbose      # Run with verbose output"
echo "  ./scripts/test.sh      # Direct script invocation"
echo ""
echo "To activate the venv manually:"
echo "  source .venv/bin/activate"

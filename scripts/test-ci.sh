#!/usr/bin/env bash
# CI-friendly test runner (no colors, strict mode)
set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== CI Test Runner ==="
echo "Project root: ${PROJECT_ROOT}"
echo "Python version: $(python --version)"

# Add src to PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
echo "PYTHONPATH: ${PYTHONPATH}"

# Run tests with JUnit XML output for CI
cd "${PROJECT_ROOT}"
python -m pytest \
    -v \
    --tb=short \
    --junit-xml=test-results.xml \
    "$@"

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed"
else
    echo "✗ Tests failed with exit code ${TEST_EXIT_CODE}"
fi

exit $TEST_EXIT_CODE

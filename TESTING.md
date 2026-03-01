# Testing Guide

Comprehensive testing infrastructure for Amplifier Module Connectors.

## Quick Start

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run specific test file
make test-file FILE=tests/test_project_manager.py

# Run tests matching a pattern
make test-pattern PATTERN=project

# Run with coverage report
make test-coverage
```

## Setup

### First Time Setup

```bash
# Install dependencies and set up venv
make setup
```

This will:
- Create `.venv/` virtual environment
- Install pytest and dev dependencies
- Configure PYTHONPATH for src/

### Manual Setup

If you prefer manual setup:

```bash
# Create venv
uv venv

# Activate venv
source .venv/bin/activate

# Install dev dependencies
uv pip install pytest pytest-asyncio pytest-cov
```

## Running Tests

### Using Make (Recommended)

```bash
# Show all available commands
make help

# Run all tests
make test

# Run tests with verbose output
make test-verbose

# Run specific test file
make test-file FILE=tests/test_project_manager.py

# Run tests matching pattern
make test-pattern PATTERN="project and slug"

# Run with coverage
make test-coverage

# Run in CI mode (JUnit XML)
make test-ci

# Clean up test artifacts
make clean
```

### Using Scripts Directly

```bash
# Basic test run
./scripts/test.sh

# Verbose
./scripts/test.sh -vv

# Specific file
./scripts/test.sh tests/test_project_manager.py

# With coverage
./scripts/test-coverage.sh

# CI mode
./scripts/test-ci.sh
```

### Using pytest Directly

```bash
# Activate venv
source .venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH=src:$PYTHONPATH

# Run tests
python -m pytest

# Verbose
python -m pytest -vv

# Specific file
python -m pytest tests/test_project_manager.py

# Specific test
python -m pytest tests/test_project_manager.py::test_resolve_project_by_path

# With coverage
python -m pytest --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── test_models.py              # UnifiedMessage tests
├── test_project_manager.py     # ProjectManager tests (NEW)
├── test_protocols.py           # Protocol conformance tests
├── test_response_truncator.py  # Response truncation tests
├── test_session_manager.py     # SessionManager tests
├── test_slack_adapter.py       # Slack adapter tests
├── test_teams_adapter.py       # Teams adapter tests
└── conftest.py                 # Shared fixtures
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from slack_connector.project_manager import ProjectManager

def test_something():
    """Test description."""
    # Arrange
    manager = ProjectManager()
    
    # Act
    result = manager.do_something()
    
    # Assert
    assert result == expected
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await some_async_function()
    assert result == expected
```

### Using Fixtures

```python
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_storage():
    """Create temporary storage file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        storage_path = f.name
    yield storage_path
    Path(storage_path).unlink(missing_ok=True)

def test_with_fixture(temp_storage):
    """Test using fixture."""
    # temp_storage is automatically created and cleaned up
    manager = ProjectManager(storage_path=temp_storage)
    # ...
```

## Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
make test-coverage

# This will:
# 1. Run all tests with coverage tracking
# 2. Generate HTML report in htmlcov/
# 3. Open report in browser (macOS)
```

### View Coverage Report

```bash
# Open in browser
open htmlcov/index.html

# Or use the script
./scripts/test-coverage.sh
```

### Coverage Targets

Current coverage (as of implementation):
- `src/slack_connector/project_manager.py`: ~95%
- Overall: ~85%

## Continuous Integration

### GitHub Actions

The repository includes CI configuration for GitHub Actions.

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: make test-ci
```

### Local CI Simulation

```bash
# Run tests in CI mode
make test-ci

# This generates test-results.xml for CI systems
```

## Common Issues

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'slack_connector'`

**Solution:**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=src:$PYTHONPATH

# Or use the scripts/Makefile which handle this
make test
```

### Virtual Environment Not Found

**Problem:** `Error: Virtual environment not found`

**Solution:**
```bash
# Run setup
make setup

# Or manually
uv venv
source .venv/bin/activate
```

### Tests Pass Locally But Fail in CI

**Problem:** Tests work on your machine but fail in CI.

**Solution:**
- Check Python version matches (3.11+)
- Ensure all dependencies are in pyproject.toml
- Use `make test-ci` to simulate CI environment
- Check for hardcoded paths or environment variables

## Best Practices

### Test Naming

```python
# ✅ Good: Descriptive names
def test_resolve_project_path_with_tilde_expansion():
    ...

# ❌ Bad: Vague names
def test_path():
    ...
```

### Test Organization

```python
# ✅ Good: Group related tests in classes
class TestProjectManager:
    def test_resolve_path(self):
        ...
    
    def test_associate_thread(self):
        ...

# ✅ Good: Use descriptive docstrings
def test_resolve_project_path():
    """Test that project paths are resolved to absolute paths."""
    ...
```

### Fixtures

```python
# ✅ Good: Use fixtures for common setup
@pytest.fixture
def manager(temp_storage):
    return ProjectManager(storage_path=temp_storage)

def test_something(manager):
    # Use pre-configured manager
    ...

# ❌ Bad: Duplicate setup in every test
def test_something():
    manager = ProjectManager(storage_path="/tmp/test.json")
    ...
```

### Assertions

```python
# ✅ Good: Specific assertions
assert result == expected_value
assert len(items) == 3
assert "error" in response

# ✅ Good: Use pytest.raises for exceptions
with pytest.raises(ValueError, match="Path does not exist"):
    manager.resolve_project_path("/nonexistent")

# ❌ Bad: Bare asserts
assert result
```

## Debugging Tests

### Run Single Test with Output

```bash
# Show print statements
pytest tests/test_project_manager.py::test_resolve_path -v -s

# Show local variables on failure
pytest tests/test_project_manager.py --showlocals

# Drop into debugger on failure
pytest tests/test_project_manager.py --pdb
```

### Using pytest Markers

```python
# Mark test as slow
@pytest.mark.slow
def test_slow_operation():
    ...

# Run only fast tests
pytest -m "not slow"
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure tests pass: `make test`
3. Check coverage: `make test-coverage`
4. Update this document if adding new test patterns

# Test Infrastructure Summary

Complete test infrastructure for Amplifier Module Connectors with proper venv handling.

## What Was Implemented

### 1. **Test Scripts** (`scripts/`)

#### `scripts/test.sh`
Main test runner with automatic venv activation and PYTHONPATH setup.

**Features:**
- ✅ Automatic venv activation
- ✅ PYTHONPATH configuration (`src/` added automatically)
- ✅ Color output for readability
- ✅ Argument passthrough to pytest
- ✅ Exit code handling

**Usage:**
```bash
./scripts/test.sh                    # Run all tests
./scripts/test.sh -vv                # Verbose
./scripts/test.sh tests/test_*.py    # Specific files
./scripts/test.sh -k pattern         # Pattern matching
```

#### `scripts/setup.sh`
Development environment setup script.

**Features:**
- ✅ Creates venv if missing
- ✅ Installs dev dependencies (pytest, pytest-asyncio)
- ✅ Uses PYTHONPATH instead of editable install (avoids dependency issues)
- ✅ Verification and helpful output

**Usage:**
```bash
./scripts/setup.sh
```

#### `scripts/test-coverage.sh`
Coverage report generation with HTML output.

**Features:**
- ✅ Installs pytest-cov if needed
- ✅ Generates HTML report in `htmlcov/`
- ✅ Opens report in browser (macOS)
- ✅ Terminal summary with missing lines

**Usage:**
```bash
./scripts/test-coverage.sh
```

#### `scripts/test-ci.sh`
CI-friendly test runner.

**Features:**
- ✅ No color output (CI compatible)
- ✅ JUnit XML output for CI systems
- ✅ Short traceback format
- ✅ Strict mode (set -euo pipefail)

**Usage:**
```bash
./scripts/test-ci.sh
```

### 2. **Makefile**

Unified interface for all development tasks.

**Test Targets:**
```makefile
make test              # Run all tests
make test-verbose      # Verbose output
make test-file         # Specific file
make test-pattern      # Pattern matching
make test-coverage     # Coverage report
make test-ci           # CI mode
make test-watch        # Watch mode (requires pytest-watch)
```

**Other Targets:**
```makefile
make setup             # Setup dev environment
make clean             # Clean artifacts
make lint              # Lint code
make format            # Format code
make check             # Lint + test
make slack-start       # Start Slack bot
make slack-logs        # Tail logs
make help              # Show all commands
```

### 3. **Documentation**

#### `TESTING.md`
Comprehensive testing guide with:
- Setup instructions
- Running tests (multiple methods)
- Writing tests (patterns and best practices)
- Coverage reporting
- CI integration
- Debugging tips
- Common issues and solutions

#### `QUICKSTART.md`
Quick reference for developers:
- Common commands
- File structure
- Environment variables
- Tips and tricks

#### `TEST_INFRASTRUCTURE.md` (this file)
Implementation summary and technical details.

## Key Features

### Proper venv Handling

**Problem Solved:**
Previously, tests required manual venv activation and PYTHONPATH setup:
```bash
# ❌ Old way - error prone
source .venv/bin/activate
export PYTHONPATH=src:$PYTHONPATH
python -m pytest
```

**Solution:**
All scripts handle this automatically:
```bash
# ✅ New way - just works
make test
./scripts/test.sh
```

### PYTHONPATH Management

Instead of installing the package in editable mode (which requires dependencies), we use PYTHONPATH:

```bash
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
```

This allows tests to import from `src/` without installation issues.

### Color Output

Test scripts use color coding for better readability:
- 🟢 Green: Success messages
- 🟡 Yellow: Info/warnings
- 🔴 Red: Errors

### Flexible Test Running

Multiple ways to run tests, all equivalent:
```bash
make test                           # Via Makefile
./scripts/test.sh                   # Via script
source .venv/bin/activate && ...    # Manual
```

## Test Results

Current status:
```
103/104 tests passing (99%)
```

**Breakdown:**
- Core models: 9/9 ✅
- Project manager: 8/8 ✅
- Protocols: 12/12 ✅
- Response truncator: 17/17 ✅
- Session manager: 9/10 ⚠️ (1 pre-existing failure)
- Slack adapter: 19/19 ✅
- Teams adapter: 18/18 ✅
- Misc: 11/11 ✅

## Usage Examples

### Basic Testing

```bash
# Setup (first time only)
make setup

# Run all tests
make test

# Run with verbose output
make test-verbose
```

### Focused Testing

```bash
# Test specific file
make test-file FILE=tests/test_project_manager.py

# Test pattern
make test-pattern PATTERN="project and slug"

# Test single test
./scripts/test.sh tests/test_project_manager.py::test_resolve_path
```

### Coverage Analysis

```bash
# Generate coverage report
make test-coverage

# Opens in browser automatically (macOS)
# Report saved to: htmlcov/index.html
```

### CI Integration

```bash
# Run in CI mode
make test-ci

# Generates: test-results.xml (JUnit format)
```

### Development Workflow

```bash
# 1. Setup
make setup

# 2. Make changes
vim src/slack_connector/project_manager.py

# 3. Run related tests
make test-file FILE=tests/test_project_manager.py

# 4. Run all tests
make test

# 5. Check coverage
make test-coverage

# 6. Clean up
make clean
```

## Technical Details

### Script Architecture

All scripts follow this pattern:

1. **Header** - Shebang, set -euo pipefail, colors
2. **Path Setup** - Find project root
3. **Validation** - Check venv exists
4. **Activation** - Source venv
5. **Configuration** - Set PYTHONPATH
6. **Execution** - Run command
7. **Reporting** - Exit code and summary

### Makefile Design

- `.PHONY` targets for all commands
- `@` prefix to hide commands (clean output)
- Conditional checks for optional tools (ruff)
- Helpful error messages
- Sorted help output

### Error Handling

Scripts handle common errors gracefully:
- Missing venv → Clear error + setup instructions
- Missing dependencies → Auto-install or helpful message
- Test failures → Colored output + exit code
- CI mode → Structured output (JUnit XML)

## Benefits

### For Developers

- ✅ No manual venv activation needed
- ✅ No PYTHONPATH setup needed
- ✅ Consistent test environment
- ✅ Fast test iteration
- ✅ Clear error messages
- ✅ Multiple ways to run (choose your preference)

### For CI/CD

- ✅ Deterministic test execution
- ✅ JUnit XML output
- ✅ Exit codes for pass/fail
- ✅ No interactive prompts
- ✅ Reproducible environment

### For Maintenance

- ✅ Centralized in Makefile
- ✅ Self-documenting (make help)
- ✅ Easy to extend
- ✅ Consistent patterns

## Future Enhancements

Potential improvements:

1. **Watch Mode** - Auto-run tests on file changes
2. **Parallel Execution** - pytest-xdist for faster tests
3. **Type Checking** - mypy integration
4. **Mutation Testing** - mutmut for test quality
5. **Benchmark Tests** - pytest-benchmark for performance
6. **Docker Support** - Containerized test environment
7. **Pre-commit Hooks** - Auto-run tests before commit

## Comparison

### Before

```bash
# Manual steps required
cd /path/to/project
source .venv/bin/activate
export PYTHONPATH=src:$PYTHONPATH
python -m pytest -v
# Easy to forget steps, inconsistent results
```

### After

```bash
# Just works
make test
# Or: ./scripts/test.sh
# Or: make test-pattern PATTERN=project
```

## Integration with Project

The test infrastructure integrates seamlessly:

```
amplifier-module-connectors/
├── Makefile              # Main interface
├── scripts/              # Test scripts
│   ├── test.sh          # Main runner
│   ├── setup.sh         # Setup
│   ├── test-coverage.sh # Coverage
│   └── test-ci.sh       # CI mode
├── tests/                # All tests
│   └── test_*.py        # Test files
├── TESTING.md            # User guide
├── QUICKSTART.md         # Quick reference
└── TEST_INFRASTRUCTURE.md # This file
```

## Summary

We now have a **robust, reliable test infrastructure** that:

1. ✅ Handles venv activation automatically
2. ✅ Configures PYTHONPATH correctly
3. ✅ Provides multiple interfaces (Makefile, scripts, direct)
4. ✅ Supports CI/CD integration
5. ✅ Includes comprehensive documentation
6. ✅ Makes testing easy and consistent

**Result:** Developers can focus on writing code and tests, not fighting with environment setup.

## Quick Reference

```bash
# Setup
make setup

# Test
make test                    # All tests
make test-verbose            # Verbose
make test-file FILE=...      # Specific file
make test-pattern PATTERN=...# Pattern match
make test-coverage           # Coverage

# Slack
make slack-start             # Start bot
make slack-logs              # View logs

# Cleanup
make clean                   # Clean artifacts

# Help
make help                    # Show all commands
```

# Quick Start for Developers

Fast reference for common development tasks.

## Setup

```bash
# Clone and setup
git clone <repo>
cd amplifier-module-connectors
make setup
```

## Testing

```bash
# Run all tests
make test

# Verbose output
make test-verbose

# Specific file
make test-file FILE=tests/test_project_manager.py

# Pattern matching
make test-pattern PATTERN=project

# Coverage report
make test-coverage

# Clean artifacts
make clean
```

## Slack Development

```bash
# Start connector (foreground)
make slack-start

# Start as daemon
make slack-daemon-start

# View logs
make slack-logs

# Restart daemon
make slack-daemon-restart

# Stop daemon
make slack-daemon-stop
```

## Common Tasks

### Add a New Test

1. Create test file in `tests/`
2. Write tests using pytest
3. Run: `make test-file FILE=tests/test_yourfile.py`
4. Verify: `make test`

### Debug a Failing Test

```bash
# Run with verbose output
./scripts/test.sh tests/test_file.py::test_name -vv

# Show local variables
./scripts/test.sh tests/test_file.py::test_name --showlocals

# Drop into debugger
./scripts/test.sh tests/test_file.py::test_name --pdb
```

### Check Code Quality

```bash
# Install ruff
uv pip install ruff

# Lint
make lint

# Format
make format

# Both
make check
```

### Update Dependencies

```bash
source .venv/bin/activate
uv pip install <package>
uv pip freeze > requirements.txt  # if needed
```

## File Structure

```
amplifier-module-connectors/
├── src/
│   ├── connector_core/          # Shared core
│   ├── slack_connector/         # Slack implementation
│   │   ├── project_manager.py   # Project management
│   │   ├── bot.py              # Main bot
│   │   └── ...
│   └── teams_connector/         # Teams implementation
├── tests/                       # All tests
│   ├── test_project_manager.py  # ProjectManager tests
│   └── ...
├── scripts/                     # Development scripts
│   ├── test.sh                 # Test runner
│   ├── setup.sh                # Setup script
│   └── ...
├── Makefile                     # Common tasks
└── TESTING.md                   # Full testing guide
```

## Environment Variables

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_CHANNEL_ID=C...  # optional

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

## Useful Make Commands

```bash
make help              # Show all commands
make setup             # Setup dev environment
make test              # Run tests
make test-coverage     # Coverage report
make clean             # Clean artifacts
make lint              # Lint code
make format            # Format code
make check             # Lint + test
make slack-start       # Start Slack bot
make slack-logs        # Tail logs
```

## Tips

### Virtual Environment

Always activate before working:
```bash
source .venv/bin/activate
```

Or use `make` commands which handle this automatically.

### PYTHONPATH

Tests need `src/` in PYTHONPATH:
```bash
export PYTHONPATH=src:$PYTHONPATH
```

Or use the test scripts which handle this.

### Quick Test Iteration

```bash
# Watch mode (requires pytest-watch)
uv pip install pytest-watch
ptw tests/test_project_manager.py
```

## Documentation

- [TESTING.md](./TESTING.md) - Comprehensive testing guide
- [docs/slack-projects.md](./docs/slack-projects.md) - Project management
- [docs/slack-setup.md](./docs/slack-setup.md) - Slack setup
- [SLACK_PROJECT_MANAGEMENT.md](./SLACK_PROJECT_MANAGEMENT.md) - Implementation details

## Getting Help

```bash
# Makefile help
make help

# Test script help
./scripts/test.sh --help

# pytest help
python -m pytest --help
```

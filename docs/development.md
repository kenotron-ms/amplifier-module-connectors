# Development Guide

Guide for developers contributing to or extending the Amplifier multi-platform connectors.

## Setup Development Environment

### 1. Clone Repository

```bash
git clone https://github.com/kenotron-ms/amplifier-module-connectors.git
cd amplifier-module-connectors
```

### 2. Install Development Dependencies

#### Using uv (Recommended)

```bash
# Create virtual environment
uv venv

# Activate
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install with dev dependencies
uv pip install -e .[dev]
```

#### Using pip

```bash
# Create virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate

# Install with dev dependencies
pip install -e .[dev]
```

### 3. Verify Installation

```bash
# Run tests
PYTHONPATH=src pytest tests/ -v

# Should see: 37 passed
```

## Project Structure

```
amplifier-module-connectors/
├── src/
│   ├── connector_core/          # Shared foundation
│   │   ├── models.py            # UnifiedMessage
│   │   ├── protocols.py         # PlatformAdapter protocol
│   │   └── session_manager.py  # Session management
│   ├── slack_connector/         # Slack implementation
│   │   ├── adapter.py           # SlackAdapter
│   │   ├── bot.py               # SlackAmplifierBot
│   │   ├── bridge.py            # Approval/Display/Streaming
│   │   └── cli.py               # CLI entry point
│   └── teams_connector/         # Teams implementation
│       ├── adapter.py           # TeamsAdapter
│       ├── bot.py               # TeamsAmplifierBot
│       └── cli.py               # CLI entry point
├── tests/                       # Test suite
│   ├── test_slack_adapter.py    # 19 Slack tests
│   └── test_teams_adapter.py    # 18 Teams tests
├── docs/                        # Documentation
│   ├── architecture.md          # System design
│   ├── slack-setup.md           # Slack guide
│   ├── teams-setup.md           # Teams guide
│   └── development.md           # This file
├── bundle.md                    # Default Amplifier bundle
├── pyproject.toml               # Package configuration
└── README.md                    # Main documentation
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit files, add features, fix bugs.

### 3. Write Tests

Add tests for new functionality:

```python
# tests/test_my_feature.py

import pytest
from src.connector_core.models import UnifiedMessage

def test_my_feature():
    # Arrange
    msg = UnifiedMessage(...)
    
    # Act
    result = my_function(msg)
    
    # Assert
    assert result == expected
```

### 4. Run Tests

```bash
# Run all tests
PYTHONPATH=src pytest tests/ -v

# Run specific test file
PYTHONPATH=src pytest tests/test_slack_adapter.py -v

# Run with coverage
PYTHONPATH=src pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 5. Format Code

```bash
# Format with black (if installed)
black src/ tests/

# Sort imports (if isort installed)
isort src/ tests/
```

### 6. Type Check

```bash
# Type check with mypy (if installed)
mypy src/
```

### 7. Commit and Push

```bash
git add .
git commit -m "feat: Add my feature"
git push origin feature/my-feature
```

### 8. Create Pull Request

1. Go to GitHub
2. Click "New Pull Request"
3. Select your branch
4. Fill in description
5. Request review

## Adding a New Platform

### Step 1: Create Module Structure

```bash
mkdir -p src/myplatform_connector
touch src/myplatform_connector/__init__.py
touch src/myplatform_connector/adapter.py
touch src/myplatform_connector/bot.py
touch src/myplatform_connector/cli.py
```

### Step 2: Implement Adapter

```python
# src/myplatform_connector/adapter.py

from typing import Callable, Awaitable, Optional
from connector_core.protocols import PlatformAdapter, ApprovalPrompt
from connector_core.models import UnifiedMessage

class MyPlatformAdapter:
    """MyPlatform implementation of PlatformAdapter protocol."""
    
    def __init__(self, token: str, **kwargs):
        self.token = token
        # Initialize platform client
    
    async def startup(self) -> None:
        """Initialize platform connection."""
        # Connect to platform API
        pass
    
    async def shutdown(self) -> None:
        """Cleanup platform resources."""
        # Disconnect, cleanup
        pass
    
    async def listen(
        self,
        message_handler: Callable[[UnifiedMessage], Awaitable[None]]
    ) -> None:
        """Start listening for messages."""
        # Set up event handlers
        # Convert platform events to UnifiedMessage
        # Call message_handler(unified_msg)
        pass
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None
    ) -> str:
        """Send message, return message ID."""
        # Send via platform API
        # Return message ID
        pass
    
    async def add_reaction(
        self,
        channel: str,
        message_id: str,
        emoji: str
    ) -> None:
        """Add reaction to message."""
        # Add reaction via platform API
        pass
    
    async def create_approval_prompt(
        self,
        channel: str,
        description: str,
        thread_id: Optional[str] = None
    ) -> ApprovalPrompt:
        """Create approval prompt."""
        # Create platform-specific approval UI
        # Return ApprovalPrompt instance
        pass
    
    def get_conversation_id(
        self,
        channel: str,
        thread_id: Optional[str] = None
    ) -> str:
        """Generate stable conversation ID."""
        if thread_id:
            return f"myplatform-{channel}-{thread_id}"
        return f"myplatform-{channel}"
```

### Step 3: Implement Bot

```python
# src/myplatform_connector/bot.py

import logging
from connector_core.session_manager import SessionManager
from connector_core.models import UnifiedMessage
from .adapter import MyPlatformAdapter

logger = logging.getLogger(__name__)

class MyPlatformAmplifierBot:
    """MyPlatform bot using Amplifier sessions."""
    
    def __init__(
        self,
        bundle_path: str,
        token: str,
        **adapter_kwargs
    ):
        self.session_manager = SessionManager(bundle_path)
        self.adapter = MyPlatformAdapter(token, **adapter_kwargs)
    
    async def run(self) -> None:
        """Start the bot."""
        logger.info("Starting MyPlatform bot...")
        
        # Initialize
        await self.session_manager.initialize()
        await self.adapter.startup()
        
        # Listen for messages
        await self.adapter.listen(self._handle_message)
    
    async def _handle_message(self, msg: UnifiedMessage) -> None:
        """Handle incoming message."""
        # Get conversation ID
        conv_id = self.adapter.get_conversation_id(
            msg.channel_id,
            msg.thread_id
        )
        
        # Get or create session
        session = await self.session_manager.get_or_create_session(conv_id)
        
        # Execute
        response = await session.execute(msg.text)
        
        # Send response
        await self.adapter.send_message(
            msg.channel_id,
            response,
            msg.thread_id
        )
```

### Step 4: Create CLI

```python
# src/myplatform_connector/cli.py

import asyncio
import click
import os
from .bot import MyPlatformAmplifierBot

@click.command()
@click.option(
    '--token',
    envvar='MYPLATFORM_TOKEN',
    required=True,
    help='MyPlatform API token'
)
@click.option(
    '--bundle',
    default='bundle.md',
    help='Path to Amplifier bundle'
)
@click.option(
    '--env-file',
    type=click.Path(exists=True),
    help='Path to .env file'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
def main(token: str, bundle: str, env_file: str, verbose: bool):
    """MyPlatform connector for Amplifier."""
    
    # Load .env if specified
    if env_file:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    # Set up logging
    import logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run bot
    bot = MyPlatformAmplifierBot(
        bundle_path=bundle,
        token=token
    )
    
    asyncio.run(bot.run())

if __name__ == '__main__':
    main()
```

### Step 5: Update pyproject.toml

```toml
[project.scripts]
myplatform-connector = "myplatform_connector.cli:main"

[project.optional-dependencies]
myplatform = [
    "myplatform-sdk>=1.0",
]
```

### Step 6: Write Tests

```python
# tests/test_myplatform_adapter.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.myplatform_connector.adapter import MyPlatformAdapter
from src.connector_core.models import UnifiedMessage

@pytest.fixture
def adapter():
    return MyPlatformAdapter(token="test-token")

class TestMyPlatformAdapter:
    @pytest.mark.asyncio
    async def test_startup(self, adapter):
        await adapter.startup()
        # Assert initialization happened
    
    @pytest.mark.asyncio
    async def test_send_message(self, adapter):
        await adapter.startup()
        msg_id = await adapter.send_message("channel1", "Hello")
        assert msg_id is not None
    
    def test_get_conversation_id(self, adapter):
        conv_id = adapter.get_conversation_id("channel1")
        assert conv_id == "myplatform-channel1"
    
    # Add more tests...
```

### Step 7: Test Your Implementation

```bash
# Install your platform dependencies
pip install -e .[myplatform]

# Run tests
PYTHONPATH=src pytest tests/test_myplatform_adapter.py -v

# Test CLI
myplatform-connector --token test --verbose
```

## Testing Best Practices

### Unit Tests

**What to test:**
- Adapter initialization
- All protocol methods
- UnifiedMessage conversion
- Error handling
- Edge cases

**How to test:**
- Mock platform APIs
- Use AsyncMock for async methods
- Test both success and failure paths
- Verify state changes

**Example:**

```python
@pytest.mark.asyncio
async def test_send_message_success(self, adapter, mock_client):
    """Test successful message sending."""
    # Arrange
    mock_client.send_message = AsyncMock(return_value={"id": "msg123"})
    await adapter.startup()
    
    # Act
    msg_id = await adapter.send_message("channel1", "Hello")
    
    # Assert
    assert msg_id == "msg123"
    mock_client.send_message.assert_called_once_with(
        channel="channel1",
        text="Hello",
        thread_id=None
    )
```

### Integration Tests

**What to test:**
- Real platform API interactions
- End-to-end message flow
- Session persistence
- Error recovery

**How to test:**
- Use test credentials
- Clean up after tests
- Use platform test environments
- Mock external dependencies (LLM API)

## Code Style

### Python Style

Follow PEP 8 with these conventions:

- **Line length:** 88 characters (Black default)
- **Imports:** Sorted with isort
- **Type hints:** Use for all public APIs
- **Docstrings:** Google style

**Example:**

```python
async def send_message(
    self,
    channel: str,
    text: str,
    thread_id: Optional[str] = None
) -> str:
    """
    Send a message to the platform.
    
    Args:
        channel: Platform-specific channel identifier
        text: Message text content
        thread_id: Optional thread/reply identifier
    
    Returns:
        Platform-specific message identifier
    
    Raises:
        ConnectionError: If platform API is unavailable
        ValueError: If channel or text is invalid
    
    Examples:
        >>> msg_id = await adapter.send_message("C123", "Hello!")
        >>> msg_id
        '1234567890.123456'
    """
    # Implementation
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Adding tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance

**Examples:**

```
feat(teams): Add JWT token validation

Implement JwtTokenValidation for Teams webhook endpoint
to verify Bot Framework authentication tokens.

Closes #30
```

```
fix(slack): Handle empty message text

Add validation to prevent errors when message text is empty.
```

```
docs: Update architecture diagram

Add Teams webhook flow to architecture documentation.
```

## Debugging

### Enable Verbose Logging

```bash
# CLI
slack-connector --verbose
teams-connector --verbose

# Python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Use Python Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use built-in (Python 3.7+)
breakpoint()
```

### View Platform Logs

**Slack:**
- Check Socket Mode connection status
- View API error responses
- Monitor rate limits

**Teams:**
- Check Bot Framework activity logs
- View webhook request/response
- Monitor Azure bot logs

## Common Issues

### Tests Fail with "ModuleNotFoundError"

**Fix:** Set PYTHONPATH

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/ -v
```

### "Protocol not implemented" errors

**Fix:** Ensure adapter implements all protocol methods

```python
# Check with mypy
mypy src/myplatform_connector/adapter.py
```

### Async tests don't run

**Fix:** Add pytest-asyncio and use @pytest.mark.asyncio

```bash
pip install pytest-asyncio
```

```python
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result == expected
```

## Release Process

### 1. Update Version

Edit `pyproject.toml`:

```toml
[project]
version = "0.2.0"
```

### 2. Update CHANGELOG

Document changes in CHANGELOG.md

### 3. Create Git Tag

```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

### 4. Build Package

```bash
pip install build
python -m build
```

### 5. Publish to PyPI

```bash
pip install twine
twine upload dist/*
```

## Resources

- **Amplifier:** https://github.com/microsoft/amplifier
- **Slack Bolt:** https://github.com/slackapi/bolt-python
- **Bot Framework:** https://github.com/microsoft/botbuilder-python
- **pytest:** https://docs.pytest.org/
- **Type Hints:** https://docs.python.org/3/library/typing.html

## Getting Help

- **Issues:** https://github.com/kenotron-ms/amplifier-module-connectors/issues
- **Discussions:** https://github.com/kenotron-ms/amplifier-module-connectors/discussions
- **Documentation:** https://github.com/kenotron-ms/amplifier-module-connectors/docs

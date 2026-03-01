# Integration Guide: Using Amplifier Connectors in Other Projects

This guide explains how to use the `amplifier-connectors` module in your own repositories and projects.

## Table of Contents

1. [Installation Methods](#installation-methods)
2. [As a Python Package](#1-as-a-python-package-recommended)
3. [As a Git Submodule](#2-as-a-git-submodule)
4. [As a Reference Implementation](#3-as-a-reference-implementation)
5. [As an Amplifier Module Source](#4-as-an-amplifier-module-source)
6. [Integration Patterns](#integration-patterns)
7. [Best Practices](#best-practices)

---

## Installation Methods

### Quick Comparison

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **Python Package** | Production deployments | Easy updates, versioned, standard | Requires publishing or git install |
| **Git Submodule** | Development, forking | Full source access, easy to customize | More complex git workflow |
| **Reference Implementation** | Building custom connectors | Maximum flexibility | Need to maintain your own copy |
| **Amplifier Module** | Extending Amplifier bundles | Modular, reusable tools | Limited to tool modules |

---

## 1. As a Python Package (Recommended)

### A. Install from Git (Current)

Install directly from the GitHub repository:

```bash
# Install with all dependencies
pip install git+https://github.com/kenotron-ms/amplifier-module-connectors.git

# Install specific version/branch
pip install git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0

# Install with only Slack support
pip install "git+https://github.com/kenotron-ms/amplifier-module-connectors.git#egg=amplifier-connectors[slack]"

# Install with only Teams support
pip install "git+https://github.com/kenotron-ms/amplifier-module-connectors.git#egg=amplifier-connectors[teams]"
```

### B. Install from Local Clone

```bash
# Clone the repository
git clone https://github.com/kenotron-ms/amplifier-module-connectors.git
cd amplifier-module-connectors

# Install in editable mode
pip install -e .

# Or with specific extras
pip install -e .[dev,teams]
```

### C. Add to requirements.txt

```txt
# requirements.txt
amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@main

# Or specify version
amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0
```

### D. Add to pyproject.toml

```toml
[project]
dependencies = [
    "amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@main",
]

# Or with optional dependencies
[project.optional-dependencies]
slack = [
    "amplifier-connectors[slack] @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@main",
]
```

### Usage in Your Project

```python
# Import the core components
from connector_core.models import UnifiedMessage
from connector_core.protocols import PlatformAdapter
from connector_core.session_manager import SessionManager

# Import Slack connector
from slack_connector.adapter import SlackAdapter
from slack_connector.bot import SlackAmplifierBot

# Import Teams connector
from teams_connector.adapter import TeamsAdapter
from teams_connector.bot import TeamsAmplifierBot

# Use in your application
session_manager = SessionManager(bundle_path="./my-bundle.md")
slack_adapter = SlackAdapter(bot_token="xoxb-...", app_token="xapp-...")
bot = SlackAmplifierBot(adapter=slack_adapter, session_manager=session_manager)
```

---

## 2. As a Git Submodule

Best for projects that need to customize or extend the connectors.

### Setup

```bash
# Add as submodule in your project
cd your-project/
git submodule add https://github.com/kenotron-ms/amplifier-module-connectors.git lib/connectors

# Initialize and update
git submodule init
git submodule update
```

### Project Structure

```
your-project/
├── lib/
│   └── connectors/          # Git submodule
│       ├── src/
│       ├── tests/
│       └── pyproject.toml
├── src/
│   └── your_app/
│       └── main.py
└── pyproject.toml
```

### Install from Submodule

```bash
# Install the submodule in editable mode
pip install -e lib/connectors

# Or reference in your pyproject.toml
[project]
dependencies = [
    "amplifier-connectors @ file:///lib/connectors",
]
```

### Updating the Submodule

```bash
# Update to latest
cd lib/connectors
git pull origin main
cd ../..
git add lib/connectors
git commit -m "Update connectors submodule"

# Update to specific version
cd lib/connectors
git checkout v0.2.0
cd ../..
git add lib/connectors
git commit -m "Pin connectors to v0.2.0"
```

---

## 3. As a Reference Implementation

Use the code as a template for building your own custom connectors.

### Copy Core Components

```bash
# Copy the core foundation
cp -r amplifier-module-connectors/src/connector_core your-project/src/

# Copy specific connector as template
cp -r amplifier-module-connectors/src/slack_connector your-project/src/discord_connector

# Copy tests as reference
cp -r amplifier-module-connectors/tests your-project/tests/
```

### Customize for Your Platform

```python
# your-project/src/discord_connector/adapter.py
from connector_core.protocols import PlatformAdapter
from connector_core.models import UnifiedMessage

class DiscordAdapter(PlatformAdapter):
    """Discord implementation of PlatformAdapter protocol."""
    
    async def send_message(self, message: UnifiedMessage) -> str:
        # Your Discord-specific implementation
        pass
    
    # Implement other protocol methods...
```

### Maintain Independence

- Fork the repository if you want to track upstream changes
- Cherry-pick updates you want to incorporate
- Build your own test suite based on the reference tests

---

## 4. As an Amplifier Module Source

The connector includes reusable Amplifier tool modules that can be referenced in your own bundles.

### Available Modules

Located in `modules/`:
- `tool-slack-reply` - Send messages to Slack threads
- `tool-todo-list` - Manage todo lists in conversations

### Reference in Your Bundle

```yaml
# your-bundle.md
---
bundle:
  name: my-custom-bot
  version: 1.0.0

tools:
  # Reference modules from this repo
  - module: tool-slack-reply
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-slack-reply
  
  - module: tool-todo-list
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-todo-list
  
  # Your own tools
  - module: tool-custom
    source: ./modules/tool-custom
---
```

### Local Development

```yaml
# For local development, use file:// paths
tools:
  - module: tool-slack-reply
    source: file:///path/to/amplifier-module-connectors/modules/tool-slack-reply
```

---

## Integration Patterns

### Pattern 1: Embedded Connector

Embed the connector directly in your application:

```python
# your-app/main.py
from slack_connector.bot import SlackAmplifierBot
from connector_core.session_manager import SessionManager

def main():
    session_manager = SessionManager(bundle_path="./bundle.md")
    bot = SlackAmplifierBot(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),
        app_token=os.getenv("SLACK_APP_TOKEN"),
        session_manager=session_manager
    )
    bot.start()

if __name__ == "__main__":
    main()
```

### Pattern 2: Multi-Platform Application

Support multiple platforms in one application:

```python
# your-app/multi_platform.py
import asyncio
from connector_core.session_manager import SessionManager
from slack_connector.bot import SlackAmplifierBot
from teams_connector.bot import TeamsAmplifierBot

async def main():
    # Shared session manager
    session_manager = SessionManager(bundle_path="./bundle.md")
    
    # Initialize both connectors
    slack_bot = SlackAmplifierBot(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),
        app_token=os.getenv("SLACK_APP_TOKEN"),
        session_manager=session_manager
    )
    
    teams_bot = TeamsAmplifierBot(
        app_id=os.getenv("TEAMS_APP_ID"),
        app_password=os.getenv("TEAMS_APP_PASSWORD"),
        session_manager=session_manager
    )
    
    # Run both concurrently
    await asyncio.gather(
        slack_bot.start_async(),
        teams_bot.start_async()
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Pattern 3: Custom Adapter

Build your own adapter using the protocol:

```python
# your-app/custom_adapter.py
from connector_core.protocols import PlatformAdapter
from connector_core.models import UnifiedMessage
from typing import Optional

class CustomPlatformAdapter(PlatformAdapter):
    """Your custom platform implementation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = CustomPlatformClient(api_key)
    
    async def send_message(
        self,
        message: UnifiedMessage,
        thread_id: Optional[str] = None
    ) -> str:
        response = await self.client.send(
            channel=message.channel_id,
            text=message.text,
            thread=thread_id
        )
        return response.id
    
    # Implement other required methods...
```

### Pattern 4: Microservices Architecture

Run connectors as separate services:

```yaml
# docker-compose.yml
version: '3.8'

services:
  slack-connector:
    build:
      context: .
      dockerfile: Dockerfile.slack
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
      - ./bundle.md:/app/bundle.md

  teams-connector:
    build:
      context: .
      dockerfile: Dockerfile.teams
    environment:
      - TEAMS_APP_ID=${TEAMS_APP_ID}
      - TEAMS_APP_PASSWORD=${TEAMS_APP_PASSWORD}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "3978:3978"
    volumes:
      - ./data:/app/data
      - ./bundle.md:/app/bundle.md
```

---

## Best Practices

### 1. Version Pinning

Always pin to specific versions in production:

```toml
# pyproject.toml
dependencies = [
    "amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0",
]
```

### 2. Environment Configuration

Use environment variables and .env files:

```bash
# .env
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
TEAMS_APP_ID=your-app-id
TEAMS_APP_PASSWORD=your-password
ANTHROPIC_API_KEY=your-api-key
```

```python
# Load in your app
from dotenv import load_dotenv
load_dotenv()
```

### 3. Custom Bundles

Create your own bundle configurations:

```yaml
# my-bundle.md
---
bundle:
  name: my-custom-bot
  version: 1.0.0

session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/microsoft/amplifier-module-loop-streaming@main

tools:
  - module: tool-slack-reply
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-slack-reply
  - module: my-custom-tool
    source: ./modules/my-custom-tool
---

Your custom system prompt here...
```

### 4. Testing

Write tests for your integration:

```python
# tests/test_integration.py
import pytest
from connector_core.session_manager import SessionManager
from slack_connector.adapter import SlackAdapter

@pytest.mark.asyncio
async def test_slack_integration():
    session_manager = SessionManager(bundle_path="./test-bundle.md")
    adapter = SlackAdapter(bot_token="test-token", app_token="test-app-token")
    
    # Your integration tests...
```

### 5. Monitoring and Logging

Configure logging for production:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('connector.log'),
        logging.StreamHandler()
    ]
)
```

### 6. Error Handling

Implement robust error handling:

```python
from slack_connector.bot import SlackAmplifierBot

try:
    bot = SlackAmplifierBot(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),
        app_token=os.getenv("SLACK_APP_TOKEN"),
        session_manager=session_manager
    )
    bot.start()
except KeyboardInterrupt:
    logging.info("Shutting down gracefully...")
except Exception as e:
    logging.error(f"Fatal error: {e}", exc_info=True)
    raise
```

---

## Examples by Use Case

### Use Case 1: Add Slack Support to Existing App

```bash
# Install connector
pip install git+https://github.com/kenotron-ms/amplifier-module-connectors.git

# Add to your app
# your_app/slack_integration.py
from slack_connector.bot import SlackAmplifierBot
from connector_core.session_manager import SessionManager

def add_slack_support(app):
    session_manager = SessionManager(bundle_path="./bundle.md")
    slack_bot = SlackAmplifierBot(
        bot_token=app.config["SLACK_BOT_TOKEN"],
        app_token=app.config["SLACK_APP_TOKEN"],
        session_manager=session_manager
    )
    return slack_bot
```

### Use Case 2: Build Custom Discord Connector

```bash
# Clone as reference
git clone https://github.com/kenotron-ms/amplifier-module-connectors.git reference/

# Copy core and use as template
cp -r reference/src/connector_core src/
cp -r reference/src/slack_connector src/discord_connector

# Modify for Discord
# src/discord_connector/adapter.py - implement DiscordAdapter
# src/discord_connector/bot.py - implement DiscordAmplifierBot
```

### Use Case 3: Reuse Amplifier Tools

```yaml
# your-bundle.md
tools:
  - module: tool-slack-reply
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-slack-reply
  - module: tool-todo-list
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-todo-list
```

---

## Troubleshooting

### Issue: Import Errors

```bash
# Ensure package is installed
pip list | grep amplifier-connectors

# Reinstall if needed
pip install --force-reinstall git+https://github.com/kenotron-ms/amplifier-module-connectors.git
```

### Issue: Submodule Not Updating

```bash
# Force submodule update
git submodule update --init --recursive --remote
```

### Issue: Version Conflicts

```bash
# Check installed version
pip show amplifier-connectors

# Uninstall and reinstall specific version
pip uninstall amplifier-connectors
pip install "git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0"
```

---

## Additional Resources

- **Main README**: [README.md](../README.md)
- **Architecture**: [docs/architecture.md](./architecture.md)
- **Development Guide**: [docs/development.md](./development.md)
- **Slack Setup**: [docs/slack-setup.md](./slack-setup.md)
- **Teams Setup**: [docs/teams-setup.md](./teams-setup.md)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/kenotron-ms/amplifier-module-connectors/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kenotron-ms/amplifier-module-connectors/discussions)

---

**Last Updated**: 2024-02-28
**Module Version**: 0.2.0

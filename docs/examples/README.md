# Integration Examples

Practical examples showing how to use `amplifier-connectors` in different scenarios.

## Available Examples

### 1. [New Project Example](./new-project-example.md)
**Creating a new Slack/Teams bot from scratch**

Learn how to:
- Set up a new Python project
- Configure dependencies
- Create a custom bundle
- Deploy with Docker

**Best for:** Starting a new bot project

---

### 2. [Existing Project Example](./existing-project-example.md)
**Adding chat interface to an existing application**

Learn how to:
- Integrate connectors into existing codebase
- Create custom tools for your app
- Run as integrated or separate service
- Maintain backward compatibility

**Best for:** Adding chat to existing apps

---

## Quick Start

### Install as Dependency

```bash
pip install git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0
```

### Basic Slack Bot

```python
from slack_connector.bot import SlackAmplifierBot
from connector_core.session_manager import SessionManager
import os

session_manager = SessionManager(bundle_path="./bundle.md")
bot = SlackAmplifierBot(
    bot_token=os.getenv("SLACK_BOT_TOKEN"),
    app_token=os.getenv("SLACK_APP_TOKEN"),
    session_manager=session_manager
)
bot.start()
```

### Basic Teams Bot

```python
from teams_connector.bot import TeamsAmplifierBot
from connector_core.session_manager import SessionManager
import os

session_manager = SessionManager(bundle_path="./bundle.md")
bot = TeamsAmplifierBot(
    app_id=os.getenv("TEAMS_APP_ID"),
    app_password=os.getenv("TEAMS_APP_PASSWORD"),
    session_manager=session_manager
)
bot.start()
```

## Common Integration Patterns

### Pattern 1: Standalone Bot
Run the connector as a dedicated bot application.

```python
# main.py
from slack_connector.bot import SlackAmplifierBot
from connector_core.session_manager import SessionManager

session_manager = SessionManager(bundle_path="./bundle.md")
bot = SlackAmplifierBot(...)
bot.start()
```

### Pattern 2: Embedded in Application
Integrate chat interface into existing application.

```python
# app.py
class Application:
    def __init__(self):
        self.api_server = APIServer()
        self.chat_interface = ChatInterface()
    
    def run(self):
        self.api_server.start()
        self.chat_interface.start()
```

### Pattern 3: Microservice
Run as separate service communicating via API.

```yaml
# docker-compose.yml
services:
  app:
    # Main application
  chat-service:
    # Separate chat service
    depends_on:
      - app
```

### Pattern 4: Multi-Platform
Support multiple chat platforms simultaneously.

```python
# multi_platform.py
import asyncio

async def main():
    session_manager = SessionManager(bundle_path="./bundle.md")
    
    slack_bot = SlackAmplifierBot(...)
    teams_bot = TeamsAmplifierBot(...)
    
    await asyncio.gather(
        slack_bot.start_async(),
        teams_bot.start_async()
    )
```

## Project Templates

### Minimal Template

```
my-bot/
├── bundle.md
├── .env
├── requirements.txt
└── main.py
```

### Standard Template

```
my-bot/
├── src/
│   └── my_bot/
│       ├── __init__.py
│       └── main.py
├── data/
│   ├── context/
│   ├── memory/
│   └── logs/
├── bundle.md
├── .env
├── pyproject.toml
└── README.md
```

### Production Template

```
my-bot/
├── src/
│   └── my_bot/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       └── chat_interface.py
├── tools/
│   └── custom-tool/
├── tests/
├── data/
├── bundle.md
├── .env
├── .env.example
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Installation Methods

### Method 1: Direct Git Install
```bash
pip install git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0
```

### Method 2: requirements.txt
```txt
amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0
```

### Method 3: pyproject.toml
```toml
dependencies = [
    "amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0",
]
```

### Method 4: Git Submodule
```bash
git submodule add https://github.com/kenotron-ms/amplifier-module-connectors.git lib/connectors
pip install -e lib/connectors
```

## Environment Setup

### Required Variables

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Teams
TEAMS_APP_ID=...
TEAMS_APP_PASSWORD=...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Optional Variables

```bash
# Slack
SLACK_CHANNEL_ID=C123456789

# Teams
TEAMS_PORT=3978

# Logging
LOG_LEVEL=INFO
```

## Bundle Configuration

### Minimal Bundle

```yaml
---
bundle:
  name: my-bot
  version: 1.0.0

session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/microsoft/amplifier-module-loop-streaming@main

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main

tools:
  - module: tool-slack-reply
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-slack-reply
---

You are a helpful AI assistant.
```

### Full Bundle

See [bundle.md](../../bundle.md) in the root directory for a complete example.

## Deployment Options

### Local Development
```bash
python main.py
```

### Docker
```bash
docker build -t my-bot .
docker run --env-file .env my-bot
```

### Docker Compose
```bash
docker-compose up -d
```

### Cloud Deployment
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances
- Kubernetes

## Testing

### Unit Tests
```python
import pytest
from my_bot.main import main

def test_initialization():
    # Test bot initialization
    pass
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_slack_integration():
    # Test Slack integration
    pass
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
pip install --force-reinstall git+https://github.com/kenotron-ms/amplifier-module-connectors.git
```

**Environment Variables Not Loading**
```python
from dotenv import load_dotenv
load_dotenv()
```

**Bundle Not Found**
```python
from pathlib import Path
bundle_path = Path(__file__).parent / "bundle.md"
```

## Additional Resources

- **[Integration Guide](../INTEGRATION_GUIDE.md)** - Comprehensive integration documentation
- **[Quick Reference](../QUICK_INTEGRATION.md)** - Fast setup snippets
- **[Architecture](../architecture.md)** - System design overview
- **[Slack Setup](../slack-setup.md)** - Slack configuration guide
- **[Teams Setup](../teams-setup.md)** - Teams configuration guide

## Support

- **GitHub Issues**: [Report issues](https://github.com/kenotron-ms/amplifier-module-connectors/issues)
- **Discussions**: [Ask questions](https://github.com/kenotron-ms/amplifier-module-connectors/discussions)
- **Documentation**: [Browse docs](../)

---

**Last Updated**: 2024-02-28

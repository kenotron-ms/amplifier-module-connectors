# Quick Integration Reference

Fast reference for integrating `amplifier-connectors` into your projects.

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/kenotron-ms/amplifier-module-connectors.git

# Install specific version
pip install git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0

# Install with extras
pip install "git+https://github.com/kenotron-ms/amplifier-module-connectors.git#egg=amplifier-connectors[slack]"
pip install "git+https://github.com/kenotron-ms/amplifier-module-connectors.git#egg=amplifier-connectors[teams]"
```

## requirements.txt

```txt
amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@main
```

## pyproject.toml

```toml
[project]
dependencies = [
    "amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@main",
]
```

## Basic Usage

### Slack Bot

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

### Teams Bot

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

### Custom Adapter

```python
from connector_core.protocols import PlatformAdapter
from connector_core.models import UnifiedMessage

class MyAdapter(PlatformAdapter):
    async def send_message(self, message: UnifiedMessage, thread_id=None):
        # Your implementation
        pass
```

## Git Submodule

```bash
# Add submodule
git submodule add https://github.com/kenotron-ms/amplifier-module-connectors.git lib/connectors

# Install from submodule
pip install -e lib/connectors
```

## Amplifier Bundle Reference

```yaml
# bundle.md
tools:
  - module: tool-slack-reply
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-slack-reply
  - module: tool-todo-list
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-todo-list
```

## Environment Variables

```bash
# .env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
TEAMS_APP_ID=...
TEAMS_APP_PASSWORD=...
ANTHROPIC_API_KEY=sk-ant-...
```

## Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install connector
RUN pip install git+https://github.com/kenotron-ms/amplifier-module-connectors.git

# Copy your config
COPY bundle.md .
COPY .env .

# Run
CMD ["slack-connector", "start"]
```

---

See [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) for detailed documentation.

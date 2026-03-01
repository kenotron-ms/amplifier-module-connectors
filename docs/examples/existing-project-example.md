# Example: Adding Connectors to Existing Project

This guide shows how to integrate `amplifier-connectors` into an existing Python project.

## Scenario

You have an existing application and want to add Slack/Teams chat interface powered by Amplifier.

## Existing Project Structure

```
my-existing-app/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── api.py
│       ├── models.py
│       └── utils.py
├── tests/
├── requirements.txt
└── pyproject.toml
```

## Integration Steps

### 1. Add Connector Dependency

#### Using pyproject.toml

```toml
# pyproject.toml
[project]
dependencies = [
    # ... your existing dependencies ...
    "amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0",
]

[project.optional-dependencies]
slack = [
    "amplifier-connectors[slack] @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0",
]
```

#### Using requirements.txt

```txt
# requirements.txt
# ... your existing dependencies ...
amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0
```

### 2. Create Chat Interface Module

```python
# src/myapp/chat_interface.py
"""
Chat interface integration for existing application.
"""
import os
import logging
from typing import Optional
from pathlib import Path

from slack_connector.bot import SlackAmplifierBot
from connector_core.session_manager import SessionManager

logger = logging.getLogger(__name__)

class ChatInterface:
    """Manages chat platform integration."""
    
    def __init__(
        self,
        bundle_path: str = "./chat-bundle.md",
        slack_enabled: bool = True,
        teams_enabled: bool = False,
    ):
        self.bundle_path = bundle_path
        self.slack_enabled = slack_enabled
        self.teams_enabled = teams_enabled
        self.session_manager = None
        self.slack_bot = None
        self.teams_bot = None
    
    def initialize(self):
        """Initialize the chat interface."""
        logger.info("Initializing chat interface...")
        
        # Create session manager
        self.session_manager = SessionManager(bundle_path=self.bundle_path)
        
        # Initialize Slack if enabled
        if self.slack_enabled:
            self._initialize_slack()
        
        # Initialize Teams if enabled
        if self.teams_enabled:
            self._initialize_teams()
    
    def _initialize_slack(self):
        """Initialize Slack bot."""
        bot_token = os.getenv("SLACK_BOT_TOKEN")
        app_token = os.getenv("SLACK_APP_TOKEN")
        
        if not bot_token or not app_token:
            logger.warning("Slack tokens not found. Skipping Slack integration.")
            return
        
        logger.info("Initializing Slack bot...")
        self.slack_bot = SlackAmplifierBot(
            bot_token=bot_token,
            app_token=app_token,
            session_manager=self.session_manager,
            channel_id=os.getenv("SLACK_CHANNEL_ID"),
        )
    
    def _initialize_teams(self):
        """Initialize Teams bot."""
        from teams_connector.bot import TeamsAmplifierBot
        
        app_id = os.getenv("TEAMS_APP_ID")
        app_password = os.getenv("TEAMS_APP_PASSWORD")
        
        if not app_id or not app_password:
            logger.warning("Teams credentials not found. Skipping Teams integration.")
            return
        
        logger.info("Initializing Teams bot...")
        self.teams_bot = TeamsAmplifierBot(
            app_id=app_id,
            app_password=app_password,
            session_manager=self.session_manager,
            port=int(os.getenv("TEAMS_PORT", 3978)),
        )
    
    def start(self):
        """Start all enabled chat bots."""
        if self.slack_bot:
            logger.info("Starting Slack bot...")
            self.slack_bot.start()
        
        if self.teams_bot:
            logger.info("Starting Teams bot...")
            self.teams_bot.start()
    
    def stop(self):
        """Stop all running bots."""
        logger.info("Stopping chat interface...")
        # Add cleanup logic if needed
```

### 3. Integrate with Existing Application

```python
# src/myapp/app.py
"""
Main application with chat interface integration.
"""
import logging
from .api import APIServer
from .chat_interface import ChatInterface

logger = logging.getLogger(__name__)

class Application:
    """Main application class."""
    
    def __init__(self):
        self.api_server = APIServer()
        self.chat_interface = None
    
    def initialize(self, enable_chat: bool = True):
        """Initialize all application components."""
        logger.info("Initializing application...")
        
        # Initialize existing components
        self.api_server.initialize()
        
        # Initialize chat interface if enabled
        if enable_chat:
            self.chat_interface = ChatInterface(
                bundle_path="./chat-bundle.md",
                slack_enabled=True,
                teams_enabled=False,
            )
            self.chat_interface.initialize()
    
    def run(self):
        """Run the application."""
        logger.info("Starting application...")
        
        # Start API server
        self.api_server.start()
        
        # Start chat interface
        if self.chat_interface:
            self.chat_interface.start()
    
    def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down application...")
        
        if self.chat_interface:
            self.chat_interface.stop()
        
        self.api_server.stop()

def main():
    """Main entry point."""
    app = Application()
    
    try:
        app.initialize(enable_chat=True)
        app.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        app.shutdown()

if __name__ == "__main__":
    main()
```

### 4. Create Chat Bundle

```yaml
# chat-bundle.md
---
bundle:
  name: myapp-chat-interface
  version: 1.0.0
  description: Chat interface for MyApp

session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/microsoft/amplifier-module-loop-streaming@main
  context:
    module: context-persistent
    source: git+https://github.com/microsoft/amplifier-module-context-persistent@main
    config:
      storage_path: ./data/chat-context

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      default_model: claude-sonnet-4-5

tools:
  - module: tool-slack-reply
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-slack-reply
  
  # Add custom tools that integrate with your app
  - module: tool-myapp-api
    source: ./tools/myapp-api
---

You are an AI assistant for MyApp. You can help users interact with the application through chat.

## Your Capabilities

- Answer questions about MyApp features
- Help users perform actions via chat commands
- Provide status updates and notifications
- Assist with troubleshooting

## Integration

You have access to MyApp's API through custom tools. Use them to:
- Query application data
- Trigger actions
- Monitor system status

Be helpful and concise in your responses!
```

### 5. Add Custom Tool for Your App

```python
# tools/myapp-api/tool.py
"""
Custom Amplifier tool that integrates with MyApp API.
"""
from typing import Any, Dict
from myapp.api import APIClient

class MyAppAPITool:
    """Tool for interacting with MyApp API."""
    
    def __init__(self):
        self.client = APIClient()
    
    async def execute(self, action: str, params: Dict[str, Any]) -> str:
        """Execute an API action."""
        if action == "get_status":
            return await self._get_status()
        elif action == "trigger_job":
            return await self._trigger_job(params)
        else:
            return f"Unknown action: {action}"
    
    async def _get_status(self) -> str:
        """Get application status."""
        status = await self.client.get_status()
        return f"Status: {status['state']}\nUptime: {status['uptime']}"
    
    async def _trigger_job(self, params: Dict[str, Any]) -> str:
        """Trigger a job."""
        job_id = params.get("job_id")
        result = await self.client.trigger_job(job_id)
        return f"Job {job_id} triggered. Status: {result['status']}"
```

### 6. Update Environment Variables

```bash
# .env
# Existing app variables
DATABASE_URL=postgresql://...
API_KEY=your-api-key

# Chat interface variables
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_CHANNEL_ID=C123456789
ANTHROPIC_API_KEY=sk-ant-...

# Feature flags
ENABLE_CHAT_INTERFACE=true
```

### 7. Update Configuration

```python
# src/myapp/config.py
"""Application configuration."""
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Existing settings
    database_url: str
    api_key: str
    
    # Chat interface settings
    enable_chat_interface: bool = True
    slack_bot_token: str = None
    slack_app_token: str = None
    slack_channel_id: str = None
    anthropic_api_key: str = None
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Updated Project Structure

```
my-existing-app/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── api.py
│       ├── models.py
│       ├── utils.py
│       ├── config.py          # Updated with chat settings
│       ├── app.py             # Updated with chat integration
│       └── chat_interface.py  # New: Chat interface wrapper
├── tools/
│   └── myapp-api/             # New: Custom tool for your app
│       ├── tool.py
│       └── module.md
├── data/
│   └── chat-context/          # New: Chat session data
├── tests/
│   └── test_chat_interface.py # New: Chat interface tests
├── chat-bundle.md             # New: Chat configuration
├── requirements.txt           # Updated
└── pyproject.toml            # Updated
```

## Running the Integrated Application

```bash
# Install updated dependencies
pip install -e .

# Run with chat interface enabled
python -m myapp.app

# Or disable chat interface
ENABLE_CHAT_INTERFACE=false python -m myapp.app
```

## Docker Integration

### Updated Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY tools/ ./tools/
COPY chat-bundle.md .

# Create data directories
RUN mkdir -p data/chat-context

# Run application
CMD ["python", "-m", "myapp.app"]
```

### docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  myapp:
    build: .
    environment:
      # Existing app variables
      - DATABASE_URL=${DATABASE_URL}
      - API_KEY=${API_KEY}
      
      # Chat interface variables
      - ENABLE_CHAT_INTERFACE=true
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN}
      - SLACK_CHANNEL_ID=${SLACK_CHANNEL_ID}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    
    volumes:
      - ./data:/app/data
    
    ports:
      - "8000:8000"  # Your API port
    
    restart: unless-stopped
```

## Testing

```python
# tests/test_chat_interface.py
import pytest
from unittest.mock import Mock, patch
from myapp.chat_interface import ChatInterface

def test_chat_interface_initialization():
    """Test chat interface initializes correctly."""
    chat = ChatInterface(
        bundle_path="./test-bundle.md",
        slack_enabled=True,
        teams_enabled=False,
    )
    assert chat.bundle_path == "./test-bundle.md"
    assert chat.slack_enabled is True
    assert chat.teams_enabled is False

@patch('os.getenv')
def test_slack_initialization_without_tokens(mock_getenv):
    """Test Slack initialization fails gracefully without tokens."""
    mock_getenv.return_value = None
    
    chat = ChatInterface()
    chat.initialize()
    
    assert chat.slack_bot is None

def test_chat_interface_integration():
    """Test chat interface integrates with existing app."""
    from myapp.app import Application
    
    app = Application()
    app.initialize(enable_chat=True)
    
    assert app.chat_interface is not None
```

## Optional: Separate Chat Service

If you prefer to run the chat interface as a separate service:

```python
# src/myapp/chat_service.py
"""
Standalone chat service that communicates with main app via API.
"""
import os
from slack_connector.bot import SlackAmplifierBot
from connector_core.session_manager import SessionManager

def main():
    """Run chat service independently."""
    session_manager = SessionManager(bundle_path="./chat-bundle.md")
    
    bot = SlackAmplifierBot(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),
        app_token=os.getenv("SLACK_APP_TOKEN"),
        session_manager=session_manager,
    )
    
    bot.start()

if __name__ == "__main__":
    main()
```

Update docker-compose.yml:

```yaml
services:
  myapp:
    # ... existing app service ...
  
  chat-service:
    build: .
    command: python -m myapp.chat_service
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - MYAPP_API_URL=http://myapp:8000
    depends_on:
      - myapp
```

## Best Practices

1. **Feature Flags**: Use environment variables to enable/disable chat
2. **Graceful Degradation**: App should work even if chat interface fails
3. **Separate Concerns**: Keep chat logic separate from core business logic
4. **Custom Tools**: Create tools that bridge chat and your app's API
5. **Monitoring**: Add logging and metrics for chat interactions
6. **Testing**: Test chat integration separately from main app

---

**See Also:**
- [New Project Example](./new-project-example.md)
- [Integration Guide](../INTEGRATION_GUIDE.md)
- [Architecture Overview](../architecture.md)

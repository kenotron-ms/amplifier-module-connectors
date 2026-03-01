# Example: New Project Using Amplifier Connectors

This example shows how to create a new project that uses `amplifier-connectors` as a dependency.

## Project Structure

```
my-slack-bot/
├── src/
│   └── my_bot/
│       ├── __init__.py
│       └── main.py
├── data/
│   ├── context/
│   ├── memory/
│   └── logs/
├── .env
├── .env.example
├── .gitignore
├── bundle.md
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Step-by-Step Setup

### 1. Create Project Directory

```bash
mkdir my-slack-bot
cd my-slack-bot
```

### 2. Create pyproject.toml

```toml
# pyproject.toml
[project]
name = "my-slack-bot"
version = "0.1.0"
description = "My custom Slack bot powered by Amplifier"
requires-python = ">=3.11"
dependencies = [
    "amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[project.scripts]
my-bot = "my_bot.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 3. Create Main Application

```python
# src/my_bot/main.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from slack_connector.bot import SlackAmplifierBot
from connector_core.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('my-bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the bot."""
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "ANTHROPIC_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return 1
    
    # Get bundle path
    bundle_path = Path(__file__).parent.parent.parent / "bundle.md"
    if not bundle_path.exists():
        logger.error(f"Bundle file not found: {bundle_path}")
        return 1
    
    logger.info("Starting My Slack Bot...")
    
    try:
        # Initialize session manager
        session_manager = SessionManager(bundle_path=str(bundle_path))
        
        # Initialize Slack bot
        bot = SlackAmplifierBot(
            bot_token=os.getenv("SLACK_BOT_TOKEN"),
            app_token=os.getenv("SLACK_APP_TOKEN"),
            session_manager=session_manager,
            channel_id=os.getenv("SLACK_CHANNEL_ID"),  # Optional
        )
        
        # Start the bot
        logger.info("Bot initialized successfully. Starting event loop...")
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal. Stopping bot...")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())
```

### 4. Create Bundle Configuration

```yaml
# bundle.md
---
bundle:
  name: my-slack-bot
  version: 1.0.0
  description: My custom Slack bot configuration

session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/microsoft/amplifier-module-loop-streaming@main
  context:
    module: context-persistent
    source: git+https://github.com/microsoft/amplifier-module-context-persistent@main
    config:
      max_tokens: 200000
      compact_threshold: 0.8
      auto_compact: true
      storage_path: ./data/context
  memory:
    module: engram
    source: git+https://github.com/microsoft/amplifier-module-engram@main
    config:
      storage_path: ./data/memory

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      default_model: claude-sonnet-4-5

tools:
  # Use tools from amplifier-connectors
  - module: tool-slack-reply
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-slack-reply
  - module: tool-todo-list
    source: git+https://github.com/kenotron-ms/amplifier-module-connectors@main#subdirectory=modules/tool-todo-list
  
  # Standard Amplifier tools
  - module: tool-web
    source: git+https://github.com/microsoft/amplifier-module-tool-web@main
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@main
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main

hooks:
  - module: hooks-logging
    source: git+https://github.com/microsoft/amplifier-module-hooks-logging@main
    config:
      output_dir: ./data/logs
---

You are a helpful AI assistant for the XYZ team. You are powered by Amplifier.

## Your Context

- You help with code reviews, documentation, and technical questions
- You have access to the team's Slack workspace
- You can execute commands and read/write files

## Response Style

- Be concise and professional
- Use Slack formatting for better readability
- Provide code examples when relevant
- Use the `slack_reply` tool for progress updates

## Capabilities

You have access to:
- `slack_reply` — send messages to Slack
- `todo_list` — manage team tasks
- `web` — browse documentation and resources
- `bash` — run commands
- `filesystem` — read and write files

Be helpful and efficient!
```

### 5. Create Environment Files

```bash
# .env.example
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_CHANNEL_ID=C123456789  # Optional: restrict to specific channel

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-key

# Optional: Logging
LOG_LEVEL=INFO
```

```bash
# .env (copy from .env.example and fill in real values)
cp .env.example .env
# Edit .env with your actual credentials
```

### 6. Create .gitignore

```gitignore
# .gitignore
# Environment
.env
.venv/
venv/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/

# Data
data/context/*
data/memory/*
data/logs/*
!data/context/.gitkeep
!data/memory/.gitkeep
!data/logs/.gitkeep

# Logs
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

### 7. Create Data Directories

```bash
mkdir -p data/context data/memory data/logs
touch data/context/.gitkeep data/memory/.gitkeep data/logs/.gitkeep
```

### 8. Install and Run

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install project
pip install -e .

# Or with dev dependencies
pip install -e .[dev]

# Run the bot
my-bot

# Or directly
python -m my_bot.main
```

## Alternative: Using requirements.txt

If you prefer `requirements.txt` over `pyproject.toml`:

```txt
# requirements.txt
amplifier-connectors @ git+https://github.com/kenotron-ms/amplifier-module-connectors.git@v0.2.0
python-dotenv>=1.0
```

```bash
pip install -r requirements.txt
python src/my_bot/main.py
```

## Docker Deployment

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY src/ ./src/
COPY bundle.md .
COPY .env .

# Create data directories
RUN mkdir -p data/context data/memory data/logs

# Run bot
CMD ["my-bot"]
```

### docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  my-slack-bot:
    build: .
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
      - ./bundle.md:/app/bundle.md
    restart: unless-stopped
```

### Run with Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Testing

### Create Test File

```python
# tests/test_bot.py
import pytest
from unittest.mock import Mock, patch
from my_bot.main import main

def test_main_missing_env_vars():
    """Test that main fails gracefully when env vars are missing."""
    with patch.dict('os.environ', {}, clear=True):
        result = main()
        assert result == 1

@pytest.mark.asyncio
async def test_bot_initialization():
    """Test that bot initializes correctly."""
    with patch.dict('os.environ', {
        'SLACK_BOT_TOKEN': 'xoxb-test',
        'SLACK_APP_TOKEN': 'xapp-test',
        'ANTHROPIC_API_KEY': 'sk-ant-test'
    }):
        # Test bot initialization
        pass
```

### Run Tests

```bash
pytest tests/ -v
```

## Next Steps

1. **Customize the bundle** - Add your own tools and prompts
2. **Add custom logic** - Extend the bot with your own handlers
3. **Configure Slack** - Follow [Slack Setup Guide](../slack-setup.md)
4. **Deploy** - Use Docker, systemd, or cloud services
5. **Monitor** - Set up logging and error tracking

## Additional Examples

- **Multi-platform bot**: See [multi-platform-example.md](./multi-platform-example.md)
- **Custom adapter**: See [custom-adapter-example.md](./custom-adapter-example.md)
- **Microservices**: See [microservices-example.md](./microservices-example.md)

---

**See Also:**
- [Integration Guide](../INTEGRATION_GUIDE.md)
- [Quick Reference](../QUICK_INTEGRATION.md)
- [Slack Setup](../slack-setup.md)

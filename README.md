# Amplifier Multi-Platform Connectors

Bridge chat platforms (Slack, Microsoft Teams) to [Amplifier](https://github.com/microsoft/amplifier) AI sessions with a unified, extensible architecture.

**What it does:** Users send messages in Slack/Teams → Amplifier processes them with AI → responses posted back. Each conversation has persistent context.

[![Tests](https://img.shields.io/badge/tests-103%2F104%20passing-brightgreen)](./TESTING.md)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

## 🚀 Quick Start

### Slack Connector

```bash
# 1. Create Slack app using manifest (automated)
#    See: docs/slack-app-manifest.md
#    Use: slack-app-manifest.yaml

# 2. Install
pip install -e .

# 3. Onboard (interactive setup verification)
slack-connector onboard

# 4. Run
slack-connector start
```

**Setup Guides:**
- [Slack App Manifest](./docs/slack-app-manifest.md) - Automated app configuration
- [Slack Setup Guide](./docs/slack-setup.md) - Complete setup instructions

### Teams Connector

```bash
# Install
pip install -e .[teams]

# Onboard (interactive setup verification)
teams-connector onboard

# Run
teams-connector start
```

**Setup Guide:** [src/teams_connector/docs/SETUP.md](./src/teams_connector/docs/SETUP.md)

## 📋 Features

### ✅ Slack Connector
- **Socket Mode** - Real-time bidirectional communication
- **Thread Support** - Each thread = separate conversation context
- **Project Management** - Associate threads with project directories via slash commands
- **Progressive Updates** - Show tool execution in real-time
- **Approval Prompts** - Interactive Block Kit buttons
- **Reactions** - Visual feedback (thinking, processing, done)
- **Fully Tested** - 19 unit tests passing

### ✅ Teams Connector
- **Bot Framework** - HTTP webhook integration
- **Activity Handling** - Convert Teams activities to unified format
- **Conversation Tracking** - Persistent conversation references
- **Thread Support** - Reply-to message threading
- **Fully Tested** - 18 unit tests passing

### 🏗️ Architecture

**Multi-Platform Foundation:**
- `UnifiedMessage` - Platform-agnostic message model
- `PlatformAdapter` - Protocol for platform implementations
- `SessionManager` - Shared session management
- `ProjectManager` - Thread → project associations (Slack)
- **103/104 tests passing** - Comprehensive test coverage ([Testing Guide](./TESTING.md))

## 📊 Status

| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| **Core** | ✅ Complete | - | UnifiedMessage, PlatformAdapter, SessionManager |
| **Slack** | ✅ Functional | 27/27 | Production ready + Project management |
| **Teams** | ✅ Functional | 18/18 | Webhook server working |

## 📚 Documentation

- **[Integration Guide](./docs/INTEGRATION_GUIDE.md)** - Using this module in your projects
- **[Quick Integration Reference](./docs/QUICK_INTEGRATION.md)** - Fast setup snippets
- **[Architecture Overview](./docs/architecture.md)** - System design and component interaction
- **[Slack Setup Guide](./docs/slack-setup.md)** - Complete Slack configuration
- **[Slack Project Management](./docs/slack-projects.md)** - Thread → project associations
- **[Teams Setup Guide](./docs/teams-setup.md)** - Complete Teams configuration
- **[Development Guide](./docs/development.md)** - Contributing and extending
- **[Testing Guide](./TESTING.md)** - Running and writing tests
- **[API Reference](./docs/api-reference.md)** - Code documentation

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Chat Platforms                          │
│                   (Slack, Teams, ...)                       │
└─────────────┬───────────────────────┬───────────────────────┘
              │                       │
      ┌───────▼────────┐      ┌──────▼────────┐
      │ SlackAdapter   │      │ TeamsAdapter  │
      │ (Socket Mode)  │      │ (Webhook)     │
      └───────┬────────┘      └──────┬────────┘
              │                      │
              └──────────┬───────────┘
                         │
              ┌──────────▼──────────┐
              │  SessionManager     │
              │  (shared sessions)  │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ AmplifierSession    │
              │ (AI processing)     │
              └─────────────────────┘
```

**Key Concepts:**

- **Adapters** - Platform-specific implementations of `PlatformAdapter` protocol
- **UnifiedMessage** - Common message format across all platforms
- **SessionManager** - Manages Amplifier sessions per conversation
- **Bridges** - Platform-specific systems (approvals, display, streaming)

## 🛠️ Installation

### Basic Installation (Slack only)

```bash
pip install -e .
```

### With Teams Support

```bash
pip install -e .[teams]
```

### Development Installation

```bash
# Install with dev dependencies
pip install -e .[dev]

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Using uv (Recommended)

```bash
# Create virtual environment
uv venv

# Activate
source .venv/bin/activate

# Install
uv pip install -e .[dev]

# Run tests
PYTHONPATH=src pytest tests/ -v
```

## 🔧 Configuration

### Environment Variables

**Slack:**
```bash
SLACK_BOT_TOKEN=xoxb-...        # Required: Bot OAuth token
SLACK_APP_TOKEN=xapp-...        # Required: App-level token (Socket Mode)
SLACK_CHANNEL_ID=C123...        # Optional: Restrict to specific channel
```

**Teams:**
```bash
TEAMS_APP_ID=abc123             # Required: Microsoft App ID
TEAMS_APP_PASSWORD=secret       # Required: Microsoft App Password
TEAMS_PORT=3978                 # Optional: Webhook server port
```

**Amplifier:**
```bash
ANTHROPIC_API_KEY=sk-ant-...    # Required: Anthropic API key
```

### Using .env Files

```bash
# Copy example
cp .env.example .env

# Edit with your values
nano .env

# Run with auto-loading
slack-connector --env-file .env
teams-connector --env-file .env
```

## 📦 Project Structure

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
├── tests/                       # Test suite (37 tests)
│   ├── test_slack_adapter.py    # 19 Slack tests
│   └── test_teams_adapter.py    # 18 Teams tests
├── docs/                        # Documentation
├── bundle.md                    # Default Amplifier bundle
└── pyproject.toml               # Package configuration
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific platform
pytest tests/test_slack_adapter.py -v
pytest tests/test_teams_adapter.py -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing

# Using uv
PYTHONPATH=src pytest tests/ -v
```

**Test Coverage:**
- ✅ 19 Slack adapter tests
- ✅ 18 Teams adapter tests
- ✅ All protocol methods tested
- ✅ Error handling verified
- ✅ UnifiedMessage conversion tested

## 🚀 Usage Examples

### Slack Connector

```bash
# Basic usage
slack-connector

# Specific channel
slack-connector --channel C0AJBKTR0JU

# Custom bundle
slack-connector --bundle my-bundle.md

# Debug mode
slack-connector --verbose

# Multi-message streaming mode
slack-connector --streaming-mode multi
```

### Teams Connector

```bash
# Basic usage
teams-connector --app-id abc123 --app-password secret

# Custom port
teams-connector --app-id abc123 --app-password secret --port 8080

# With .env file
teams-connector --env-file .env

# Verbose logging
teams-connector --app-id abc123 --app-password secret --verbose
```

## 🔌 Extending to New Platforms

Adding a new platform (Discord, WhatsApp, etc.) is straightforward:

1. **Create adapter** implementing `PlatformAdapter` protocol
2. **Implement bot** using `SessionManager`
3. **Add CLI** entry point
4. **Write tests** following existing patterns

See [Development Guide](./docs/development.md) for details.

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

**Areas for contribution:**
- Integration tests
- Teams proactive messaging
- Teams Adaptive Cards
- Additional platforms (Discord, WhatsApp)
- Documentation improvements

## 📝 License

MIT License - see [LICENSE](./LICENSE) for details.

## 🙏 Acknowledgments

Built on:
- [Amplifier](https://github.com/microsoft/amplifier) - AI agent framework
- [Slack Bolt for Python](https://github.com/slackapi/bolt-python) - Slack SDK
- [Bot Framework SDK](https://github.com/microsoft/botbuilder-python) - Teams integration

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/kenotron-ms/amplifier-module-connectors/issues)
- **Discussions:** [GitHub Discussions](https://github.com/kenotron-ms/amplifier-module-connectors/discussions)
- **Documentation:** [./docs/](./docs/)

---

**Status:** Production ready for Slack, functional for Teams. See [Issue #30](https://github.com/kenotron-ms/amplifier-module-connectors/issues/30) for optional enhancements.

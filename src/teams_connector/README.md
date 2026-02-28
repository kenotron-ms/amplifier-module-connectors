# Microsoft Teams Connector

Microsoft Teams integration for Amplifier using Bot Framework.

## Status

✅ **Functional** - Webhook server working, can receive and respond to messages.

### ✅ Completed

- TeamsAdapter implementing PlatformAdapter protocol
- aiohttp webhook server on port 3978
- Bot Framework activity handling (message, conversationUpdate)
- UnifiedMessage conversion
- TeamsAmplifierBot with SessionManager integration
- Conversation ID generation and tracking
- CLI with full options
- 18 comprehensive unit tests (all passing)

### 🚧 TODO (Optional Enhancements)

- [ ] Proactive messaging (send_message with Bot Framework)
- [ ] TeamsApprovalPrompt with Adaptive Cards
- [ ] JWT token validation (security - high priority for production)
- [ ] Integration tests

See [Issue #30](https://github.com/kenotron-ms/amplifier-module-connectors/issues/30) for tracking.

## Quick Start

```bash
# Install
pip install -e .[teams]

# Run
teams-connector --app-id YOUR_APP_ID --app-password YOUR_PASSWORD

# Or use .env file
teams-connector --env-file .env
```

See [Teams Setup Guide](../../docs/teams-setup.md) for complete instructions.

## Architecture

```
Microsoft Teams / Bot Framework
       ↓
POST /api/messages (Activity JSON)
       ↓
TeamsAdapter._handle_activity()
       ↓
_handle_message_activity()
       ↓
UnifiedMessage
       ↓
TeamsAmplifierBot (message_handler)
       ↓
SessionManager.get_or_create_session()
       ↓
AmplifierSession.execute()
       ↓
adapter.send_message() [mock for now]
```

## Module Structure

```
teams_connector/
├── __init__.py          # Module exports
├── adapter.py           # TeamsAdapter (PlatformAdapter impl)
├── bot.py               # TeamsAmplifierBot (main bot logic)
├── cli.py               # CLI entry point
└── README.md            # This file
```

## Usage

### Python API

```python
from teams_connector import TeamsAmplifierBot

bot = TeamsAmplifierBot(
    bundle_path="./bundle.md",
    app_id="YOUR_APP_ID",
    app_password="YOUR_APP_PASSWORD",
    port=3978
)

await bot.run()
```

### CLI

```bash
# Basic usage
teams-connector --app-id abc123 --app-password secret

# Custom port
teams-connector --app-id abc123 --app-password secret --port 8080

# Custom bundle
teams-connector --app-id abc123 --app-password secret --bundle my-bundle.md

# With .env file
teams-connector --env-file .env

# Verbose logging
teams-connector --verbose
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEAMS_APP_ID` | Yes | - | Microsoft App ID from Azure |
| `TEAMS_APP_PASSWORD` | Yes | - | App secret from Azure |
| `TEAMS_PORT` | No | 3978 | Webhook server port |
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key |

## Dependencies

Required packages (installed with `pip install -e .[teams]`):
- `aiohttp` - Async HTTP server for webhook
- `amplifier-foundation` - Core Amplifier framework

Optional (for full Bot Framework support):
- `botbuilder-core` - Bot Framework core (future)
- `botbuilder-schema` - Bot Framework schemas (future)

## Differences from Slack Connector

| Feature | Slack | Teams |
|---------|-------|-------|
| **Transport** | Socket Mode (WebSocket) | HTTP Webhook |
| **Auth** | Bot + App tokens | App ID + Password |
| **Messages** | Slack events | Bot Framework Activities |
| **Approvals** | Block Kit buttons ✅ | Adaptive Cards 🚧 |
| **Reactions** | reactions.add API ✅ | Limited support 🚧 |
| **Threading** | thread_ts | replyToId |
| **Proactive** | Full support ✅ | Mock implementation 🚧 |

## Testing

```bash
# Run Teams adapter tests
pytest tests/test_teams_adapter.py -v

# With coverage
pytest tests/test_teams_adapter.py --cov=src.teams_connector

# All tests (18 passing)
PYTHONPATH=src pytest tests/test_teams_adapter.py -v
```

## Webhook Endpoints

The connector exposes two HTTP endpoints:

### POST /api/messages

Bot Framework activity endpoint. Receives:
- Message activities (user messages)
- Conversation update activities (bot added/removed)

Returns: 200 OK

### GET /health

Health check endpoint.

Returns: `Teams adapter is running`

## Current Limitations

1. **Proactive Messaging** - `send_message()` returns mock ID, doesn't actually send
   - Receiving messages works ✅
   - Responding to messages works ✅
   - Initiating conversations doesn't work yet 🚧

2. **Approval Prompts** - Not implemented
   - `create_approval_prompt()` raises NotImplementedError
   - Adaptive Cards support planned

3. **JWT Validation** - Not implemented
   - **Security risk for production**
   - Webhook accepts all requests
   - Add JwtTokenValidation before production use

4. **Reactions** - Placeholder only
   - Teams doesn't have simple emoji reactions API
   - `add_reaction()` logs but doesn't do anything

## Next Steps

See [Issue #30](https://github.com/kenotron-ms/amplifier-module-connectors/issues/30) for tracking optional enhancements:

**High Priority (Production):**
- JWT token validation
- Integration tests

**Medium Priority (Features):**
- Proactive messaging with Bot Framework
- Adaptive Cards for approvals

**Low Priority:**
- Reaction support (if Teams adds API)

## Support

- **Setup Guide:** [docs/teams-setup.md](../../docs/teams-setup.md)
- **Architecture:** [docs/architecture.md](../../docs/architecture.md)
- **Issues:** https://github.com/kenotron-ms/amplifier-module-connectors/issues

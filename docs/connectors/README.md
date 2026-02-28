# Connector Documentation

This directory contains documentation for each platform connector.

## Available Connectors

### ✅ Slack Connector

**Status:** Production Ready  
**Transport:** Socket Mode (WebSocket)  
**Setup:** [../../src/slack_connector/docs/SETUP.md](../../src/slack_connector/docs/SETUP.md)

**Quick Start:**
```bash
pip install -e .
slack-connector onboard
slack-connector start
```

### ✅ Teams Connector

**Status:** Functional (webhook server working)  
**Transport:** HTTP Webhook (Bot Framework)  
**Setup:** [../../src/teams_connector/docs/SETUP.md](../../src/teams_connector/docs/SETUP.md)

**Quick Start:**
```bash
pip install -e .[teams]
teams-connector onboard
teams-connector start
```

## Connector Documentation Structure

Each connector has its own documentation in `src/{platform}_connector/docs/`:

```
src/{platform}_connector/docs/
├── SETUP.md           # Platform registration & configuration
├── USAGE.md           # How to use the connector (coming soon)
├── DEPLOYMENT.md      # Production deployment (coming soon)
└── TROUBLESHOOTING.md # Common issues (coming soon)
```

## Adding a New Connector

See [../development.md](../development.md) for a complete guide to adding support for new platforms (Discord, WhatsApp, etc.).

**Quick checklist:**

1. **Create module structure:**
   ```
   src/{platform}_connector/
   ├── __init__.py
   ├── adapter.py          # Implement PlatformAdapter protocol
   ├── bot.py              # Bot using SessionManager
   ├── cli.py              # CLI with 'onboard' and 'start' commands
   └── docs/
       └── SETUP.md        # Platform-specific setup guide
   ```

2. **Implement PlatformAdapter:**
   - `startup()` - Initialize connection
   - `shutdown()` - Cleanup
   - `listen()` - Receive messages
   - `send_message()` - Send messages
   - `add_reaction()` - Add reactions
   - `create_approval_prompt()` - Interactive prompts
   - `get_conversation_id()` - Generate stable IDs

3. **Create bot:**
   - Use `SessionManager` for session lifecycle
   - Convert platform events to `UnifiedMessage`
   - Handle messages with Amplifier sessions

4. **Add CLI:**
   - `{platform}-connector onboard` - Setup verification
   - `{platform}-connector start` - Run bot

5. **Write documentation:**
   - `SETUP.md` - How to register app/bot on platform
   - Include onboarding command usage
   - Link to main architecture docs

6. **Write tests:**
   - Follow pattern from `test_slack_adapter.py`
   - Test all protocol methods
   - Mock platform APIs

7. **Update pyproject.toml:**
   ```toml
   [project.scripts]
   {platform}-connector = "{platform}_connector.cli:main"
   
   [project.optional-dependencies]
   {platform} = [
       "platform-sdk>=1.0",
   ]
   ```

## Documentation Guidelines

### SETUP.md Template

Each connector's `SETUP.md` should follow this structure:

1. **Prerequisites** - What you need before starting
2. **Step-by-step platform registration** - Create app/bot on platform
3. **Get credentials** - Where to find tokens/keys
4. **Configure environment** - Create .env file
5. **Test configuration** - Run `{platform}-connector onboard`
6. **Next steps** - Links to usage, deployment docs
7. **Quick reference** - Table of credentials, scopes, etc.
8. **Common issues** - Quick troubleshooting

### Onboard Command

Every connector should have an `onboard` command that:

- ✅ Checks for required environment variables
- ✅ Validates credentials (if possible without side effects)
- ✅ Tests connectivity (basic API call)
- ✅ Shows configuration summary
- ✅ Provides next steps

**Example:**
```bash
$ slack-connector onboard

🚀 Slack Connector Onboarding

✅ Tokens found in environment
   SLACK_BOT_TOKEN: xoxb-012345...
   SLACK_APP_TOKEN: xapp-012345...

🔌 Testing Slack connection...
✅ Bot token is valid
   Bot User ID: U123ABC
   Bot Name: amplifier-bot
   Team: My Workspace

✅ Onboarding Complete!

Next steps:
  1. Run: slack-connector start
  2. Invite bot to a channel: /invite @amplifier-bot
  3. Send a message to test
```

## Connector Comparison

| Feature | Slack | Teams | Discord* | WhatsApp* |
|---------|-------|-------|----------|-----------|
| **Status** | ✅ Ready | ✅ Functional | 🚧 Planned | 🚧 Planned |
| **Transport** | Socket Mode | Webhook | Gateway | Webhook |
| **Auth** | 2 tokens | App ID + Password | Bot token | API key |
| **Threading** | ✅ Full | ✅ Full | ✅ Full | ⚠️ Limited |
| **Reactions** | ✅ Full | ⚠️ Limited | ✅ Full | ❌ None |
| **Approvals** | ✅ Block Kit | 🚧 Adaptive Cards | 🚧 Buttons | 🚧 Quick Replies |
| **Proactive** | ✅ Full | 🚧 TODO | - | - |

\* Planned for future implementation

## Resources

- **Architecture:** [../architecture.md](../architecture.md)
- **Development Guide:** [../development.md](../development.md)
- **Main README:** [../../README.md](../../README.md)

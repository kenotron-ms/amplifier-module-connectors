# Microsoft Teams Connector

Microsoft Teams integration for Amplifier using Bot Framework SDK.

## Status

🚧 **Work in Progress** - Basic structure in place, implementation incomplete.

### ✅ Completed
- TeamsAdapter skeleton implementing PlatformAdapter protocol
- TeamsAmplifierBot structure matching Slack connector
- SessionManager integration
- Conversation ID generation

### 🚧 TODO
- [ ] Implement Bot Framework adapter initialization
- [ ] Implement webhook server for receiving messages
- [ ] Implement send_message with Bot Framework
- [ ] Create TeamsApprovalPrompt with Adaptive Cards
- [ ] Create teams_reply tool module
- [ ] Add proper error handling
- [ ] Add unit tests
- [ ] Add integration tests

## Architecture

```
teams_connector/
├── __init__.py          # Module exports
├── adapter.py           # TeamsAdapter (PlatformAdapter impl)
├── bot.py               # TeamsAmplifierBot (main bot logic)
└── README.md            # This file
```

## Usage (Future)

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

## Dependencies

Required packages (not yet in pyproject.toml):
- `botbuilder-core` - Bot Framework core
- `botbuilder-schema` - Bot Framework schemas
- `aiohttp` - Async HTTP server

## Differences from Slack Connector

| Feature | Slack | Teams |
|---------|-------|-------|
| **Transport** | Socket Mode | HTTP Webhook |
| **Auth** | Bot + App tokens | App ID + Password |
| **Messages** | Slack events | Bot Framework Activities |
| **Approvals** | Block Kit buttons | Adaptive Cards |
| **Reactions** | reactions.add API | Limited support |
| **Threading** | thread_ts | replyToId |

## Next Steps

1. Install Bot Framework SDK dependencies
2. Implement Bot Framework adapter initialization
3. Implement webhook server (aiohttp)
4. Convert Activities to UnifiedMessage
5. Create TeamsApprovalPrompt with Adaptive Cards
6. Test with Teams Bot emulator
7. Deploy and test with real Teams

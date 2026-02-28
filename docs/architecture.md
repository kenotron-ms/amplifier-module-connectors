# Architecture Overview

This document describes the multi-platform connector architecture for Amplifier.

## Design Principles

1. **Platform Agnostic** - Core logic independent of chat platform
2. **Protocol-Based** - Adapters implement common `PlatformAdapter` protocol
3. **Shared Sessions** - `SessionManager` handles all session lifecycle
4. **Unified Messages** - `UnifiedMessage` model abstracts platform differences
5. **Testable** - Protocols enable comprehensive unit testing

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Chat Platforms                             │
│                                                                 │
│  ┌──────────────┐         ┌──────────────┐                    │
│  │    Slack     │         │    Teams     │         (Discord...) │
│  │ Socket Mode  │         │  Webhook     │                    │
│  └──────┬───────┘         └──────┬───────┘                    │
└─────────┼──────────────────────┼──────────────────────────────┘
          │                      │
          │                      │
┌─────────▼──────────────────────▼──────────────────────────────┐
│                    Platform Adapters                          │
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │SlackAdapter  │         │TeamsAdapter  │                  │
│  │              │         │              │                  │
│  │ • startup()  │         │ • startup()  │                  │
│  │ • listen()   │         │ • listen()   │                  │
│  │ • send_msg() │         │ • send_msg() │                  │
│  └──────┬───────┘         └──────┬───────┘                  │
└─────────┼──────────────────────┼──────────────────────────────┘
          │                      │
          │   UnifiedMessage     │
          │                      │
┌─────────▼──────────────────────▼──────────────────────────────┐
│                    Bot Layer                                  │
│                                                               │
│  ┌────────────────────────────────────────────────┐          │
│  │         SlackAmplifierBot / TeamsAmplifierBot  │          │
│  │                                                │          │
│  │  • Receives UnifiedMessage                     │          │
│  │  • Gets/creates session from SessionManager    │          │
│  │  • Executes session with user message          │          │
│  │  • Sends response via adapter                  │          │
│  └────────────────────┬───────────────────────────┘          │
└───────────────────────┼──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                  SessionManager                              │
│                                                              │
│  • Prepares Amplifier bundle (once)                         │
│  • Creates sessions per conversation                        │
│  • Caches sessions (conversation_id → session)              │
│  • Thread-safe locking                                      │
└───────────────────────┬──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                 AmplifierSession                             │
│                                                              │
│  • LLM provider (Claude, GPT, etc.)                         │
│  • Tools (web search, file access, etc.)                    │
│  • Memory/context management                                │
│  • Streaming responses                                      │
└──────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. UnifiedMessage

Platform-agnostic message representation.

**Purpose:** Abstract away platform-specific message formats

**Fields:**
- `platform` - Platform identifier ("slack", "teams")
- `channel_id` - Platform-specific channel/conversation ID
- `user_id` - Platform-specific user ID
- `text` - Message text content
- `message_id` - Platform-specific message ID
- `thread_id` - Optional thread/reply ID
- `timestamp` - When message was sent
- `raw_event` - Original platform event (for platform-specific handling)

**Example:**
```python
# Slack message
UnifiedMessage(
    platform="slack",
    channel_id="C123ABC",
    user_id="U456DEF",
    text="Hello bot!",
    message_id="1234567890.123456",
    thread_id=None,
    timestamp=datetime.now(),
    raw_event={...}  # Original Slack event
)

# Teams message
UnifiedMessage(
    platform="teams",
    channel_id="19:meeting_abc123",
    user_id="29:user_xyz789",
    text="Hello bot!",
    message_id="activity-123",
    thread_id=None,
    timestamp=datetime.now(),
    raw_event={...}  # Original Bot Framework Activity
)
```

### 2. PlatformAdapter Protocol

Defines the interface all platform adapters must implement.

**Methods:**

```python
async def startup() -> None:
    """Initialize platform connection."""

async def shutdown() -> None:
    """Cleanup platform resources."""

async def listen(
    message_handler: Callable[[UnifiedMessage], Awaitable[None]]
) -> None:
    """Start listening for messages, route to handler."""

async def send_message(
    channel: str,
    text: str,
    thread_id: str | None = None
) -> str:
    """Send message, return message ID."""

async def add_reaction(
    channel: str,
    message_id: str,
    emoji: str
) -> None:
    """Add reaction to message."""

async def create_approval_prompt(
    channel: str,
    description: str,
    thread_id: str | None = None
) -> ApprovalPrompt:
    """Create interactive approval prompt."""

def get_conversation_id(
    channel: str,
    thread_id: str | None = None
) -> str:
    """Generate stable conversation ID for session management."""
```

**Why a Protocol?**
- Enables duck typing (no inheritance required)
- Easy to test with mocks
- Clear contract for new platform implementations
- Type checking with mypy/pyright

### 3. SessionManager

Manages Amplifier session lifecycle.

**Responsibilities:**
- Prepare Amplifier bundle (once at startup)
- Create new sessions per conversation
- Cache sessions by conversation ID
- Thread-safe session access
- Session cleanup

**Key Methods:**

```python
async def initialize() -> None:
    """Prepare bundle, ready for session creation."""

async def get_or_create_session(conversation_id: str) -> AmplifierSession:
    """Get cached session or create new one."""
```

**Session Caching:**
```
conversation_id → AmplifierSession
"slack-C123ABC" → Session 1
"slack-C123ABC-1234567890.123456" → Session 2 (thread)
"teams-19:meeting_abc123" → Session 3
```

Each conversation (channel or thread) gets its own persistent session with memory.

### 4. Platform Adapters

#### SlackAdapter

**Transport:** Socket Mode (WebSocket)

**Key Features:**
- Bi-directional real-time communication
- No public endpoint required
- Built on Slack Bolt SDK

**Implementation:**
```python
class SlackAdapter:
    def __init__(self, app_token: str, bot_token: str):
        self.bolt_app = AsyncApp(token=bot_token)
        self.handler = AsyncSocketModeHandler(...)
    
    async def listen(self, message_handler):
        @self.bolt_app.event("message")
        async def handle_message(event):
            # Convert to UnifiedMessage
            unified = UnifiedMessage(
                platform="slack",
                channel_id=event["channel"],
                user_id=event["user"],
                text=event["text"],
                ...
            )
            await message_handler(unified)
        
        await self.handler.start_async()
```

#### TeamsAdapter

**Transport:** HTTP Webhook

**Key Features:**
- Bot Framework integration
- HTTP POST endpoint for activities
- Conversation reference caching

**Implementation:**
```python
class TeamsAdapter:
    def __init__(self, app_id: str, app_password: str, port: int = 3978):
        self._app = web.Application()
        self._app.router.add_post('/api/messages', self._handle_activity)
    
    async def listen(self, message_handler):
        # Start aiohttp server
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
    
    async def _handle_activity(self, request):
        activity = await request.json()
        
        if activity['type'] == 'message':
            # Convert to UnifiedMessage
            unified = UnifiedMessage(
                platform="teams",
                channel_id=activity['conversation']['id'],
                user_id=activity['from']['id'],
                text=activity['text'],
                ...
            )
            await self._message_handler(unified)
```

## Message Flow

### Receiving Messages

```
1. Platform sends event
   ↓
2. Adapter receives event
   ↓
3. Adapter converts to UnifiedMessage
   ↓
4. Adapter calls message_handler(unified_msg)
   ↓
5. Bot receives UnifiedMessage
   ↓
6. Bot gets conversation_id from message
   ↓
7. Bot gets/creates session from SessionManager
   ↓
8. Bot executes session with message text
   ↓
9. Bot sends response via adapter.send_message()
```

### Sending Messages

```
1. Bot calls adapter.send_message(channel, text, thread_id)
   ↓
2. Adapter converts to platform-specific format
   - Slack: chat.postMessage API
   - Teams: Bot Framework Activity
   ↓
3. Adapter sends via platform API
   ↓
4. Adapter returns message_id
```

## Conversation ID Generation

Stable conversation IDs are critical for session management.

**Format:**
- `{platform}-{channel_id}` - Channel-level conversation
- `{platform}-{channel_id}-{thread_id}` - Thread-level conversation

**Examples:**
```python
# Slack channel
"slack-C123ABC"

# Slack thread
"slack-C123ABC-1234567890.123456"

# Teams conversation
"teams-19:meeting_abc123"

# Teams reply
"teams-19:meeting_abc123-parent-activity-id"
```

**Why this matters:**
- Each conversation gets its own AmplifierSession
- Sessions persist across messages
- Memory/context maintained per conversation

## Bridge Systems

Platform-specific systems that don't fit the core protocol.

### Approval System

**Slack:** Block Kit buttons
```python
class SlackApprovalSystem:
    async def request_approval(self, description: str) -> bool:
        # Post Block Kit message with buttons
        # Wait for button click
        # Return approval result
```

**Teams:** Adaptive Cards (TODO)
```python
class TeamsApprovalPrompt:
    async def request_approval(self, description: str) -> bool:
        # Post Adaptive Card with actions
        # Wait for card action
        # Return approval result
```

### Display System

Handles progressive status updates during AI thinking.

**Modes:**
1. **Single Message** - Update one ephemeral message
2. **Multi Message** - Post separate messages per tool
3. **Blocks** - Post every content block separately

### Streaming Hook

Shows real-time tool execution progress.

## Testing Strategy

### Unit Tests

**What we test:**
- Adapter initialization
- Protocol method implementations
- UnifiedMessage conversion
- Error handling
- State management

**Approach:**
- Mock platform APIs (Slack Bolt, aiohttp)
- Test each protocol method
- Verify UnifiedMessage fields
- Check error scenarios

**Coverage:**
- SlackAdapter: 19 tests
- TeamsAdapter: 18 tests
- All protocol methods tested

### Integration Tests (TODO)

**What to test:**
- Real platform API interactions
- End-to-end message flow
- Session persistence
- Approval prompts
- Threading

## Adding New Platforms

To add support for a new platform (Discord, WhatsApp, etc.):

### 1. Create Adapter

```python
# src/{platform}_connector/adapter.py

class DiscordAdapter:
    """Discord implementation of PlatformAdapter protocol."""
    
    async def startup(self) -> None:
        # Initialize Discord client
        pass
    
    async def listen(self, message_handler) -> None:
        # Set up Discord event handlers
        # Convert Discord messages to UnifiedMessage
        # Call message_handler(unified_msg)
        pass
    
    async def send_message(self, channel, text, thread_id=None) -> str:
        # Send Discord message
        # Return message ID
        pass
    
    # ... implement other protocol methods
```

### 2. Create Bot

```python
# src/{platform}_connector/bot.py

class DiscordAmplifierBot:
    def __init__(self, bundle_path: str, token: str):
        self.session_manager = SessionManager(bundle_path)
        self.adapter = DiscordAdapter(token)
    
    async def run(self):
        await self.session_manager.initialize()
        await self.adapter.startup()
        await self.adapter.listen(self._handle_message)
    
    async def _handle_message(self, msg: UnifiedMessage):
        # Get conversation ID
        conv_id = self.adapter.get_conversation_id(
            msg.channel_id,
            msg.thread_id
        )
        
        # Get/create session
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

### 3. Add CLI

```python
# src/{platform}_connector/cli.py

@click.command()
@click.option('--token', required=True)
def main(token: str):
    bot = DiscordAmplifierBot(
        bundle_path="bundle.md",
        token=token
    )
    asyncio.run(bot.run())
```

### 4. Update pyproject.toml

```toml
[project.scripts]
discord-connector = "discord_connector.cli:main"

[project.optional-dependencies]
discord = [
    "discord.py>=2.0",
]
```

### 5. Write Tests

Follow the pattern from `test_slack_adapter.py` and `test_teams_adapter.py`.

## Performance Considerations

### Session Caching

- Sessions cached in memory by conversation ID
- No disk I/O per message
- Locks prevent race conditions

### Async/Await

- All I/O operations are async
- Non-blocking message handling
- Concurrent session execution

### Resource Management

- Graceful shutdown cleanup
- Connection pooling (platform-dependent)
- Memory limits on session cache (TODO)

## Security

### Slack

- Socket Mode (no public endpoint)
- Token-based authentication
- Scoped bot permissions

### Teams

- HTTP webhook (public endpoint)
- JWT token validation (TODO - high priority)
- App ID/Password authentication

### General

- Environment variables for secrets
- No secrets in code/logs
- Principle of least privilege

## Future Enhancements

See [Issue #30](https://github.com/kenotron-ms/amplifier-module-connectors/issues/30) for tracking.

**High Priority:**
- JWT validation for Teams
- Integration tests

**Medium Priority:**
- Teams proactive messaging
- Teams Adaptive Cards
- Session cache limits
- Metrics/monitoring

**Low Priority:**
- Additional platforms (Discord, WhatsApp)
- Message queuing
- Load balancing

# amplifier-connector-slack

A Slack bot that bridges Slack messages to [Amplifier](https://github.com/microsoft/amplifier) AI sessions via Socket Mode.

**What it does:** Users send messages to a Slack channel → an Amplifier session processes them → responses are posted back to Slack. Each thread has its own persistent conversation context.

## Architecture

```
Slack ──── Socket Mode ────► Bot Daemon (asyncio)
                                    │
                         ┌──────────▼──────────┐
                         │  SlackAmplifierBot  │
                         │  PreparedBundle ×1  │
                         │  Sessions: per-thrd │
                         └──────────┬──────────┘
                                    │ session.execute()
                                    ▼
                         ┌──────────────────────┐
                         │  AmplifierSession    │
                         │  (one per thread)    │
                         │  • provider-anthropic│
                         │  • loop-streaming    │
                         │  • tool-slack-reply  │
                         │  • tool-web/search   │
                         └──────────────────────┘
```

## Progressive Status Updates

The bot supports **three modes** for displaying AI activity:

### Single Message Mode (Default)
Updates one ephemeral status message, then deletes it:
```
🤔 Thinking...
→ 🔄 web_search...
→ ✓ web_search
  🤔 Processing...
→ [deleted, final response appears]
```

**Best for:** Clean UX, production use

### Multi Message Mode
Posts separate persistent messages for each tool (Claude Code style):
```
🤔 Thinking...
[New message] 🔧 `web_search`(query="Python") → ✅ `web_search`(query="Python")
[New message] 🔧 `read_file`(file_path="main.py") → ✅ `read_file`(file_path="main.py")
[Final response appears]
```

**Best for:** Debugging, auditing, tool transparency
**Features:** Concise args (max 3 params), success/failure indicators, no result dumps

### Blocks Mode
Posts separate messages for **each content block** (thinking, tools, intermediate text):
```
[Message 1] _thinking..._
[Message 2] _💭 I need to search for information..._
[Message 3] 🔧 `web_search`(query="Python")
[Message 4] ✅ `web_search`(query="Python")
[Message 5] Intermediate text response
[Message 6] 🔧 `read_file`(file_path="main.py")
[Message 7] ✅ `read_file`(file_path="main.py")
[Final response appears]
```

**Best for:** Maximum transparency, understanding AI reasoning, educational use
**Features:** Thinking in _italic_ (light treatment), concise tool display

**Usage:**
```bash
# Default (single message)
slack-connector start

# Multi message mode (tool transparency)
slack-connector start --streaming-mode multi

# Blocks mode (full content streaming)
slack-connector start --streaming-mode blocks
```

See [PROGRESSIVE_UPDATES.md](./PROGRESSIVE_UPDATES.md) for details.

## Setup

### 1. Create a Slack App

1. Go to https://api.slack.com/apps → **Create New App** → **From scratch**
2. **Enable Socket Mode**: Settings → Socket Mode → Enable
3. **Generate App-Level Token**:
   - Basic Information → App-level tokens → Generate Token and Scopes
   - Name: `socket-mode`, Scope: `connections:write`
   - Save the `xapp-...` token
4. **Add Bot Scopes** (OAuth & Permissions → Bot Token Scopes):
   - `chat:write` — send messages
   - `channels:history` — read channel messages
   - `channels:read` — list channels
   - `reactions:write` — add/remove reactions (loading indicator)
   - `app_mentions:read` — receive @mention events
   - `channels:join` — auto-join channels (optional)
5. **Subscribe to Events** (Event Subscriptions → Subscribe to bot events):
   - `message.channels` — messages in public channels
   - `app_mention` — @mentions
6. **Install to Workspace**: OAuth & Permissions → Install to Workspace
   - Save the `xoxb-...` Bot Token

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your tokens
```

### 3. Install

```bash
# Install the bot and its tool module
pip install -e .
pip install -e modules/tool-slack-reply
```

### 4. Run

```bash
# Watch a specific channel (recommended for testing)
slack-connector start --channel C0AJBKTR0JU

# Watch all channels the bot is in
slack-connector start

# Debug mode
slack-connector start --channel C0AJBKTR0JU --debug
```

### 5. Invite the bot to your channel

In Slack: `/invite @your-bot-name` in channel `#your-channel`

## Running as a macOS Daemon (launchd)

```bash
# Edit the plist with your actual paths and tokens
cp launchd/com.amplifier.slack-connector.plist \
   ~/Library/LaunchAgents/com.amplifier.slack-connector.plist

# Edit the plist file — fill in YOUR paths and tokens
nano ~/Library/LaunchAgents/com.amplifier.slack-connector.plist

# Load and start
launchctl load ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
launchctl start com.amplifier.slack-connector

# Check status
launchctl list com.amplifier.slack-connector

# View logs (multiple options)
./logs.sh                    # Simple: tail both logs
./tail-logs.sh               # Advanced: with color and filtering
./tail-logs.sh --help        # See all options
```

## Viewing Logs

Two scripts are provided for viewing daemon logs:

### Simple Log Viewer (`logs.sh`)
```bash
./logs.sh    # Tail both stdout and stderr logs
```

### Advanced Log Viewer (`tail-logs.sh`)
```bash
# Basic usage
./tail-logs.sh                      # Tail both logs with color

# Show only errors
./tail-logs.sh -e

# Show last 100 lines
./tail-logs.sh -n 100

# Filter for specific content
./tail-logs.sh --grep "tool"        # Show tool-related logs
./tail-logs.sh --level ERROR        # Show only ERROR level logs

# See all options
./tail-logs.sh --help
```

**Features:**
- Color-coded output (ERROR=red, WARNING=yellow, INFO=green, DEBUG=gray)
- Filter by log level or pattern
- Follow mode (default) or show last N lines
- Highlights tool execution and session events

## Configuration

| Environment Variable | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | Yes | Bot OAuth token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | Yes | App-level token (`xapp-...`) for Socket Mode |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `SLACK_CHANNEL_ID` | No | Restrict responses to this channel ID |

## Bundle Customization

Edit `bundle.md` to customize the bot's capabilities:

- Change the LLM model (`default_model`)
- Add more tools (`tool-filesystem`, `tool-bash` — be careful with public access)
- Modify the system prompt in the markdown body
- Add Amplifier behaviors via `includes:`

## Project Structure

```
amplifier-module-connectors/
├── bundle.md                      # Bot's Amplifier session config
├── pyproject.toml                 # Python package (slack-connector CLI)
├── src/slack_connector/
│   ├── bot.py                     # Core: SlackAmplifierBot (Pattern B)
│   ├── bridge.py                  # Protocol boundaries (Approval, Display, Streaming)
│   └── cli.py                     # CLI entry point
├── modules/tool-slack-reply/      # Custom Amplifier tool module
│   └── tool_slack_reply/tool.py
├── behaviors/slack-connector.yaml # Reusable behavior for other bundles
├── context/slack-instructions.md  # Slack-specific agent instructions
├── launchd/                       # macOS daemon configuration
└── .amplifier/bundle.md           # Dev environment bundle (for Amplifier CLI)
```

## Acknowledgments

Built on [Amplifier](https://github.com/microsoft/amplifier) and [Slack Bolt for Python](https://github.com/slackapi/bolt-python).

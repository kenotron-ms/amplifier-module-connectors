# Slack Connector Setup Guide

Complete guide to setting up and running the Slack connector for Amplifier.

## Prerequisites

- Python 3.11+
- Slack workspace with admin access
- Anthropic API key

## Step 1: Create Slack App

### Option A: Using App Manifest (Recommended - Automated)

**Easiest way** - All configuration automated:

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From an app manifest**
3. Select your workspace
4. Copy contents of `slack-app-manifest.yaml` from the repo
5. Paste into the YAML editor
6. Click **Next** → **Create**
7. ✅ Done! Slash commands, scopes, and events are auto-configured

**See:** [slack-app-manifest.md](./slack-app-manifest.md) for details.

### Option B: Manual Setup (If manifest doesn't work)

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. Enter app name (e.g., "Amplifier Bot")
4. Select your workspace
5. Click **Create App**

### 1.2 Enable Socket Mode

1. Go to **Settings** → **Socket Mode**
2. Toggle **Enable Socket Mode** to ON
3. Click **Generate Token and Scopes**
   - Token Name: `socket-mode`
   - Scope: `connections:write`
4. Click **Generate**
5. **Save the token** (starts with `xapp-`)

### 1.3 Add Bot Scopes

1. Go to **OAuth & Permissions** → **Scopes** → **Bot Token Scopes**
2. Add the following scopes:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages |
| `channels:history` | Read channel messages |
| `channels:read` | List channels |
| `reactions:write` | Add reactions (loading indicators) |
| `app_mentions:read` | Receive @mentions |
| `channels:join` | Auto-join channels (optional) |

### 1.4 Subscribe to Events

1. Go to **Event Subscriptions**
2. Toggle **Enable Events** to ON
3. Under **Subscribe to bot events**, add:
   - `message.channels` - Messages in public channels
   - `app_mention` - @mentions

### 1.5 Install to Workspace

1. Go to **OAuth & Permissions**
2. Click **Install to Workspace**
3. Review permissions
4. Click **Allow**
5. **Save the Bot Token** (starts with `xoxb-`)

## Step 2: Configure Environment

### 2.1 Create .env File

```bash
# Copy example
cp .env.example .env
```

### 2.2 Edit .env

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Optional: Restrict to specific channel
# SLACK_CHANNEL_ID=C0AJBKTR0JU

# Amplifier Configuration
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Optional: Custom bundle path
# BUNDLE_PATH=./my-bundle.md
```

### 2.3 Get Channel ID (Optional)

To restrict the bot to a specific channel:

1. Open Slack in browser
2. Navigate to your channel
3. Copy the channel ID from URL:
   ```
   https://app.slack.com/client/T.../C0AJBKTR0JU
                                      ^^^^^^^^^^^
                                      Channel ID
   ```
4. Add to `.env`: `SLACK_CHANNEL_ID=C0AJBKTR0JU`

## Step 3: Install

### 3.1 Using pip

```bash
# Install connector
pip install -e .

# Install Slack reply tool (optional but recommended)
pip install -e modules/tool-slack-reply
```

### 3.2 Using uv (Recommended)

```bash
# Create virtual environment
uv venv

# Activate
source .venv/bin/activate

# Install
uv pip install -e .
uv pip install -e modules/tool-slack-reply
```

## Step 4: Run

### 4.1 Basic Usage

```bash
# Run with auto-loaded .env
slack-connector

# Specify .env file explicitly
slack-connector --env-file .env

# Watch specific channel
slack-connector --channel C0AJBKTR0JU

# Verbose logging
slack-connector --verbose
```

### 4.2 Streaming Modes

The bot supports three streaming modes for displaying AI activity:

#### Single Message Mode (Default)
Updates one ephemeral message, then deletes it:

```bash
slack-connector
```

**Output in Slack:**
```
🤔 Thinking...
→ 🔄 web_search...
→ ✓ web_search
  🤔 Processing...
→ [deleted, final response appears]
```

#### Multi Message Mode
Posts separate messages for each tool:

```bash
slack-connector --streaming-mode multi
```

**Output in Slack:**
```
🤔 Thinking...
[New message] 🔧 `web_search`(query="Python") → ✅ `web_search`(query="Python")
[New message] 🔧 `read_file`(file_path="main.py") → ✅ `read_file`(file_path="main.py")
[Final response appears]
```

#### Blocks Mode
Posts every content block separately:

```bash
slack-connector --streaming-mode blocks
```

**Output in Slack:**
```
[Message 1] _thinking..._
[Message 2] _💭 I need to search for information..._
[Message 3] 🔧 `web_search`(query="Python")
[Message 4] ✅ `web_search`(query="Python")
[Message 5] Intermediate text response
[Final response appears]
```

### 4.3 Custom Bundle

```bash
slack-connector --bundle my-custom-bundle.md
```

## Step 5: Invite Bot to Channel

1. In Slack, go to your channel
2. Type: `/invite @your-bot-name`
3. Press Enter

The bot should now respond to messages in that channel!

## Step 6: Test

### 6.1 Basic Message

Send a message in the channel:
```
Hello bot!
```

You should see:
1. 👀 reaction added (bot is processing)
2. Status updates (depending on streaming mode)
3. Final response
4. ✅ reaction (bot is done)

### 6.2 Test Threading

Reply to a message in a thread. The bot should:
- Maintain separate context for each thread
- Remember previous messages in that thread
- Not mix context between threads

### 6.3 Test Tools

Try a message that requires tools:
```
What's the weather in Seattle?
```

You should see tool execution (`web_search`) in the status updates.

## Running as a Daemon

### macOS (launchd)

#### 1. Create plist file

```bash
cp launchd/com.amplifier.slack-connector.plist \
   ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
```

#### 2. Edit plist file

```bash
nano ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
```

Update paths and environment variables:
```xml
<key>ProgramArguments</key>
<array>
    <string>/path/to/your/venv/bin/slack-connector</string>
    <string>--channel</string>
    <string>C0AJBKTR0JU</string>
</array>

<key>EnvironmentVariables</key>
<dict>
    <key>SLACK_BOT_TOKEN</key>
    <string>xoxb-your-token</string>
    <key>SLACK_APP_TOKEN</key>
    <string>xapp-your-token</string>
    <key>ANTHROPIC_API_KEY</key>
    <string>sk-ant-your-key</string>
</dict>
```

#### 3. Load and start

```bash
# Load daemon
launchctl load ~/Library/LaunchAgents/com.amplifier.slack-connector.plist

# Start daemon
launchctl start com.amplifier.slack-connector

# Check status
launchctl list com.amplifier.slack-connector
```

#### 4. View logs

```bash
# Simple tail
./logs.sh

# Advanced with filtering
./tail-logs.sh --help
./tail-logs.sh -e              # Errors only
./tail-logs.sh --grep "tool"   # Tool-related logs
```

### Linux (systemd)

#### 1. Create service file

```bash
sudo nano /etc/systemd/system/slack-connector.service
```

```ini
[Unit]
Description=Amplifier Slack Connector
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/amplifier-module-connectors
Environment="SLACK_BOT_TOKEN=xoxb-your-token"
Environment="SLACK_APP_TOKEN=xapp-your-token"
Environment="ANTHROPIC_API_KEY=sk-ant-your-key"
ExecStart=/path/to/venv/bin/slack-connector --channel C0AJBKTR0JU
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable slack-connector

# Start service
sudo systemctl start slack-connector

# Check status
sudo systemctl status slack-connector

# View logs
sudo journalctl -u slack-connector -f
```

## Troubleshooting

### Bot doesn't respond

**Check:**
1. Bot is running: `launchctl list com.amplifier.slack-connector` or `systemctl status slack-connector`
2. Bot is in channel: `/invite @bot-name`
3. Tokens are correct in `.env`
4. Channel ID is correct (if restricted)

**View logs:**
```bash
./tail-logs.sh -e  # macOS
sudo journalctl -u slack-connector -f  # Linux
```

### "Invalid token" error

**Fix:**
1. Verify `SLACK_BOT_TOKEN` starts with `xoxb-`
2. Verify `SLACK_APP_TOKEN` starts with `xapp-`
3. Regenerate tokens if needed

### Bot responds in wrong channel

**Fix:**
- Remove `SLACK_CHANNEL_ID` to allow all channels
- Or set `SLACK_CHANNEL_ID` to correct channel ID

### Socket Mode connection fails

**Check:**
1. Socket Mode is enabled in Slack app settings
2. `connections:write` scope on app-level token
3. Network allows WebSocket connections

### Tool execution fails

**Check:**
1. `ANTHROPIC_API_KEY` is set correctly
2. Tool modules are installed:
   ```bash
   pip install -e modules/tool-slack-reply
   pip install -e modules/tool-web  # if using web tools
   ```
3. Bundle includes required tools in `includes:` section

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | Yes | - | Bot OAuth token (xoxb-...) |
| `SLACK_APP_TOKEN` | Yes | - | App-level token (xapp-...) |
| `SLACK_CHANNEL_ID` | No | All channels | Restrict to specific channel |
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key |
| `BUNDLE_PATH` | No | `./bundle.md` | Path to Amplifier bundle |

### CLI Options

```bash
slack-connector [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--bundle PATH` | Path to Amplifier bundle (default: bundle.md) |
| `--channel ID` | Slack channel ID to watch |
| `--streaming-mode MODE` | Streaming mode: single, multi, blocks (default: single) |
| `--env-file PATH` | Load environment from .env file |
| `--verbose`, `-v` | Enable verbose (DEBUG) logging |
| `--help` | Show help message |

## Next Steps

- **Set up projects** - See [Project Management](slack-projects.md) to associate threads with project directories
- **Customize bundle** - Edit `bundle.md` to change AI behavior
- **Add tools** - Install more Amplifier tool modules
- **Monitor logs** - Use `./tail-logs.sh` for real-time monitoring
- **Scale** - Run multiple instances for different channels

## Support

- **Issues:** https://github.com/kenotron-ms/amplifier-module-connectors/issues
- **Docs:** https://github.com/kenotron-ms/amplifier-module-connectors/docs

# Slack Connector Setup

Complete guide to registering and configuring a Slack app for Amplifier.

## Prerequisites

- Slack workspace with admin access
- Ability to create Slack apps

## Step 1: Create Slack App

### 1.1 Go to Slack API Portal

1. Visit https://api.slack.com/apps
2. Click **Create New App**
3. Select **From scratch**
4. Enter app details:
   - **App Name:** `Amplifier Bot` (or your preferred name)
   - **Workspace:** Select your workspace
5. Click **Create App**

### 1.2 Enable Socket Mode

Socket Mode allows the bot to connect via WebSocket without requiring a public endpoint.

1. In your app settings, go to **Settings** → **Socket Mode**
2. Toggle **Enable Socket Mode** to **ON**
3. You'll be prompted to create an app-level token:
   - Click **Generate Token and Scopes**
   - **Token Name:** `socket-mode`
   - **Scope:** Select `connections:write`
   - Click **Generate**
4. **Copy and save the token** (starts with `xapp-`)
   - ⚠️ This is your `SLACK_APP_TOKEN`

### 1.3 Add Bot Token Scopes

Configure what your bot can do in Slack.

1. Go to **OAuth & Permissions**
2. Scroll to **Scopes** → **Bot Token Scopes**
3. Click **Add an OAuth Scope** and add each of these:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages to channels |
| `channels:history` | Read messages in public channels |
| `channels:read` | View basic channel information |
| `reactions:write` | Add emoji reactions (for status indicators) |
| `app_mentions:read` | Receive @mentions of the bot |
| `channels:join` | Allow bot to join public channels (optional) |

### 1.4 Subscribe to Events

Tell Slack which events to send to your bot.

1. Go to **Event Subscriptions**
2. Toggle **Enable Events** to **ON**
3. Scroll to **Subscribe to bot events**
4. Click **Add Bot User Event** and add:
   - `message.channels` - Messages posted to public channels
   - `app_mention` - @mentions of your bot

5. Click **Save Changes**

### 1.5 Install App to Workspace

1. Go to **OAuth & Permissions**
2. Click **Install to Workspace**
3. Review the permissions your bot is requesting
4. Click **Allow**
5. **Copy and save the Bot User OAuth Token** (starts with `xoxb-`)
   - ⚠️ This is your `SLACK_BOT_TOKEN`

## Step 2: Get Your Tokens

You should now have two tokens:

```bash
# App-Level Token (for Socket Mode)
SLACK_APP_TOKEN=xapp-1-A01234567-012345678-abc...xyz

# Bot User OAuth Token
SLACK_BOT_TOKEN=xoxb-012345678-012345678-abc...xyz
```

## Step 3: Optional - Get Channel ID

If you want to restrict the bot to a specific channel:

1. Open Slack in a web browser
2. Navigate to the channel you want to use
3. Look at the URL in your browser:
   ```
   https://app.slack.com/client/T0ABC123DEF/C0AJBKTR0JU
                                           ^^^^^^^^^^^
                                           This is your Channel ID
   ```
4. Copy the Channel ID (starts with `C`)

## Step 4: Configure Environment

Create a `.env` file in your project root:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Optional: Restrict to specific channel
# SLACK_CHANNEL_ID=C0AJBKTR0JU

# Amplifier Configuration
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

## Step 5: Test Your Configuration

Run the onboarding command to verify your setup:

```bash
slack-connector onboard
```

This will:
- ✅ Verify your tokens are valid
- ✅ Check bot permissions
- ✅ Test Socket Mode connection
- ✅ Confirm event subscriptions

## Next Steps

- **[Usage Guide](./USAGE.md)** - Learn how to use the connector
- **[Deployment](./DEPLOYMENT.md)** - Deploy as a daemon/service
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Common issues and solutions

## Quick Reference

### Required Tokens

| Token | Starts With | Where to Find |
|-------|-------------|---------------|
| `SLACK_BOT_TOKEN` | `xoxb-` | OAuth & Permissions → Bot User OAuth Token |
| `SLACK_APP_TOKEN` | `xapp-` | Socket Mode → App-Level Tokens |

### Required Scopes

**Bot Token Scopes:**
- `chat:write`
- `channels:history`
- `channels:read`
- `reactions:write`
- `app_mentions:read`
- `channels:join` (optional)

**App-Level Token Scopes:**
- `connections:write`

### Required Event Subscriptions

- `message.channels`
- `app_mention`

## Support

- **Issues:** https://github.com/kenotron-ms/amplifier-module-connectors/issues
- **Main Docs:** [../../../docs/](../../../docs/)

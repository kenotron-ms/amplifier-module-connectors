# Teams Connector Setup Guide

Complete guide to setting up and running the Microsoft Teams connector for Amplifier.

## Prerequisites

- Python 3.11+
- Microsoft 365 tenant with admin access
- Anthropic API key
- Public HTTPS endpoint (for webhook) OR ngrok for testing

## Step 1: Register Bot in Azure

### 1.1 Create Azure Bot Resource

1. Go to https://portal.azure.com
2. Click **Create a resource**
3. Search for **Azure Bot**
4. Click **Create**
5. Fill in details:
   - **Bot handle:** `amplifier-bot` (unique name)
   - **Subscription:** Your subscription
   - **Resource group:** Create new or use existing
   - **Pricing tier:** F0 (Free) for testing
   - **Microsoft App ID:** Create new
6. Click **Review + create** → **Create**

### 1.2 Get App Credentials

1. Go to your bot resource
2. Click **Configuration** → **Manage** (next to Microsoft App ID)
3. **Save the Application (client) ID** - this is your `TEAMS_APP_ID`
4. Click **Certificates & secrets** → **New client secret**
5. Description: `amplifier-bot-secret`
6. Expires: Choose duration
7. Click **Add**
8. **Save the secret Value** - this is your `TEAMS_APP_PASSWORD`
   - ⚠️ You can only see this once!

### 1.3 Configure Messaging Endpoint

1. Go back to your bot resource
2. Click **Configuration**
3. Set **Messaging endpoint:**
   - Production: `https://your-domain.com/api/messages`
   - Testing: `https://your-ngrok-url/api/messages`
4. Click **Apply**

## Step 2: Configure Teams Channel

### 2.1 Add Teams Channel

1. In your bot resource, click **Channels**
2. Click **Microsoft Teams** icon
3. Click **Apply**
4. Click **Agree** to Terms of Service

### 2.2 Enable Required Features

1. In **Channels** → **Microsoft Teams**, click **Edit**
2. Enable:
   - **Messaging** - Required
   - **Calling** - Optional
   - **Video** - Optional
3. Click **Apply**

## Step 3: Create Teams App Manifest

### 3.1 Create Manifest Directory

```bash
mkdir teams-app
cd teams-app
```

### 3.2 Create manifest.json

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
  "manifestVersion": "1.16",
  "version": "1.0.0",
  "id": "YOUR_APP_ID_HERE",
  "packageName": "com.amplifier.bot",
  "developer": {
    "name": "Your Name",
    "websiteUrl": "https://your-website.com",
    "privacyUrl": "https://your-website.com/privacy",
    "termsOfUseUrl": "https://your-website.com/terms"
  },
  "name": {
    "short": "Amplifier Bot",
    "full": "Amplifier AI Assistant Bot"
  },
  "description": {
    "short": "AI assistant powered by Amplifier",
    "full": "An AI assistant that helps with tasks using Amplifier framework"
  },
  "icons": {
    "outline": "outline.png",
    "color": "color.png"
  },
  "accentColor": "#FFFFFF",
  "bots": [
    {
      "botId": "YOUR_APP_ID_HERE",
      "scopes": [
        "personal",
        "team",
        "groupchat"
      ],
      "supportsFiles": false,
      "isNotificationOnly": false
    }
  ],
  "permissions": [
    "identity",
    "messageTeamMembers"
  ],
  "validDomains": []
}
```

Replace `YOUR_APP_ID_HERE` with your Application ID from Step 1.2.

### 3.3 Add Icons

Create two PNG icons:
- `color.png` - 192x192px, color icon
- `outline.png` - 32x32px, transparent outline

Or use placeholders:
```bash
# Download sample icons
curl -o color.png https://via.placeholder.com/192
curl -o outline.png https://via.placeholder.com/32
```

### 3.4 Create App Package

```bash
# Zip the manifest and icons
zip amplifier-bot.zip manifest.json color.png outline.png
```

## Step 4: Install App to Teams

### 4.1 Upload Custom App

1. Open Microsoft Teams
2. Click **Apps** in sidebar
3. Click **Manage your apps**
4. Click **Upload an app** → **Upload a custom app**
5. Select `amplifier-bot.zip`
6. Click **Add**

### 4.2 Start Chat

1. Find your bot in **Apps**
2. Click **Add** or **Open**
3. Start a conversation!

## Step 5: Configure Environment

### 5.1 Create .env File

```bash
# Copy example
cp .env.example .env
```

### 5.2 Edit .env

```bash
# Teams Configuration
TEAMS_APP_ID=your-app-id-from-azure
TEAMS_APP_PASSWORD=your-app-secret-from-azure
TEAMS_PORT=3978

# Amplifier Configuration
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Optional: Custom bundle path
# BUNDLE_PATH=./my-bundle.md
```

## Step 6: Set Up Public Endpoint

### Option A: ngrok (Testing)

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start ngrok
ngrok http 3978

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update bot messaging endpoint in Azure:
# https://abc123.ngrok.io/api/messages
```

### Option B: Production Deployment

Deploy to a server with HTTPS:

**Requirements:**
- Public IP or domain
- HTTPS certificate (Let's Encrypt recommended)
- Port 3978 open (or use reverse proxy)

**Example with nginx reverse proxy:**

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /api/messages {
        proxy_pass http://localhost:3978/api/messages;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Step 7: Install

### 7.1 Using pip

```bash
# Install with Teams support
pip install -e .[teams]
```

### 7.2 Using uv (Recommended)

```bash
# Create virtual environment
uv venv

# Activate
source .venv/bin/activate

# Install with Teams support
uv pip install -e .[teams]
```

## Step 8: Run

### 8.1 Basic Usage

```bash
# Run with auto-loaded .env
teams-connector

# Specify .env file explicitly
teams-connector --env-file .env

# Specify credentials directly
teams-connector --app-id abc123 --app-password secret123

# Custom port
teams-connector --app-id abc123 --app-password secret123 --port 8080

# Verbose logging
teams-connector --verbose
```

### 8.2 Custom Bundle

```bash
teams-connector --bundle my-custom-bundle.md
```

### 8.3 Check Server is Running

The connector will output:
```
Teams webhook server listening on http://0.0.0.0:3978
Bot Framework endpoint: http://0.0.0.0:3978/api/messages
```

Test the health endpoint:
```bash
curl http://localhost:3978/health
# Should return: Teams adapter is running
```

## Step 9: Test

### 9.1 Send Message

1. Open Teams
2. Go to your bot chat
3. Send: `Hello bot!`

You should see:
1. Bot receives message (check logs)
2. Bot processes with Amplifier
3. Bot responds

### 9.2 Test in Channel

1. Add bot to a Teams channel:
   - Channel → **...** → **Manage channel**
   - **Apps** tab → **+** → Find your bot → **Add**
2. @mention the bot: `@Amplifier Bot hello!`
3. Bot should respond

### 9.3 Test Threading

Reply to a bot message. The bot should:
- Maintain separate context for the thread
- Remember previous messages in that thread

## Running as a Service

### Linux (systemd)

#### 1. Create service file

```bash
sudo nano /etc/systemd/system/teams-connector.service
```

```ini
[Unit]
Description=Amplifier Teams Connector
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/amplifier-module-connectors
Environment="TEAMS_APP_ID=your-app-id"
Environment="TEAMS_APP_PASSWORD=your-app-password"
Environment="TEAMS_PORT=3978"
Environment="ANTHROPIC_API_KEY=sk-ant-your-key"
ExecStart=/path/to/venv/bin/teams-connector
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
sudo systemctl enable teams-connector

# Start service
sudo systemctl start teams-connector

# Check status
sudo systemctl status teams-connector

# View logs
sudo journalctl -u teams-connector -f
```

### Docker

#### 1. Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install -e .[teams]

# Expose port
EXPOSE 3978

# Run connector
CMD ["teams-connector"]
```

#### 2. Build and run

```bash
# Build image
docker build -t amplifier-teams-connector .

# Run container
docker run -d \
  -p 3978:3978 \
  -e TEAMS_APP_ID=your-app-id \
  -e TEAMS_APP_PASSWORD=your-password \
  -e ANTHROPIC_API_KEY=your-key \
  --name teams-connector \
  amplifier-teams-connector

# View logs
docker logs -f teams-connector
```

## Troubleshooting

### Bot doesn't receive messages

**Check:**
1. Webhook server is running: `curl http://localhost:3978/health`
2. Messaging endpoint in Azure is correct
3. ngrok is running (if using ngrok)
4. Firewall allows incoming connections

**View logs:**
```bash
# If running directly
teams-connector --verbose

# If running as service
sudo journalctl -u teams-connector -f

# If running in Docker
docker logs -f teams-connector
```

### "Unauthorized" or 401 errors

**Fix:**
1. Verify `TEAMS_APP_ID` matches Azure Application ID
2. Verify `TEAMS_APP_PASSWORD` is correct (regenerate if needed)
3. Check app secret hasn't expired

### Webhook endpoint unreachable

**Check:**
1. Public endpoint is accessible:
   ```bash
   curl https://your-domain.com/api/messages
   # Should return 405 Method Not Allowed (POST expected)
   ```
2. HTTPS certificate is valid
3. Firewall/security groups allow traffic
4. ngrok is running (if using ngrok)

### Bot responds but context not maintained

**Check:**
1. Conversation IDs are stable (check logs)
2. SessionManager is initialized
3. No errors in session creation

### "Service URL not allowed" error

**Fix:**
1. Add service URL to bot's valid domains in Azure
2. Ensure HTTPS is used (not HTTP)

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEAMS_APP_ID` | Yes | - | Microsoft App ID from Azure |
| `TEAMS_APP_PASSWORD` | Yes | - | App secret from Azure |
| `TEAMS_PORT` | No | 3978 | Webhook server port |
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key |
| `BUNDLE_PATH` | No | `./bundle.md` | Path to Amplifier bundle |

### CLI Options

```bash
teams-connector [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--bundle PATH` | Path to Amplifier bundle (default: bundle.md) |
| `--app-id ID` | Microsoft App ID (or set TEAMS_APP_ID) |
| `--app-password PWD` | App password (or set TEAMS_APP_PASSWORD) |
| `--port PORT` | Webhook server port (default: 3978) |
| `--env-file PATH` | Load environment from .env file |
| `--verbose`, `-v` | Enable verbose (DEBUG) logging |
| `--help` | Show help message |

## Current Limitations

### ⚠️ Known Limitations

1. **Proactive Messaging** - `send_message` is mock implementation
   - Bot can respond to messages
   - Bot cannot initiate conversations yet
   
2. **Approval Prompts** - Not yet implemented
   - `create_approval_prompt` raises NotImplementedError
   - Adaptive Cards support coming soon

3. **JWT Validation** - Not implemented
   - Webhook accepts all requests
   - **Security risk for production** - add JWT validation

4. **Reactions** - Limited support
   - Teams doesn't have emoji reactions API like Slack
   - `add_reaction` is placeholder

See [Issue #30](https://github.com/kenotron-ms/amplifier-module-connectors/issues/30) for tracking these enhancements.

## Next Steps

- **Customize bundle** - Edit `bundle.md` to change AI behavior
- **Add JWT validation** - Secure webhook endpoint (high priority)
- **Implement Adaptive Cards** - For approval prompts
- **Monitor logs** - Watch for errors and performance
- **Scale** - Deploy to production infrastructure

## Support

- **Issues:** https://github.com/kenotron-ms/amplifier-module-connectors/issues
- **Docs:** https://github.com/kenotron-ms/amplifier-module-connectors/docs

# Teams Connector Setup

Complete guide to registering and configuring a Microsoft Teams bot for Amplifier.

## Prerequisites

- Microsoft 365 tenant with admin access
- Azure subscription (free tier works)
- Ability to upload custom apps to Teams

## Step 1: Register Bot in Azure

### 1.1 Create Azure Bot Resource

1. Go to https://portal.azure.com
2. Click **Create a resource**
3. Search for **Azure Bot**
4. Click **Create**
5. Fill in the details:
   - **Bot handle:** `amplifier-bot` (must be globally unique)
   - **Subscription:** Select your subscription
   - **Resource group:** Create new or select existing
   - **Location:** Choose closest region
   - **Pricing tier:** F0 (Free) for development/testing
   - **Microsoft App ID:** Select **Create new Microsoft App ID**
6. Click **Review + create**
7. Click **Create**
8. Wait for deployment to complete

### 1.2 Get Application Credentials

1. Go to your newly created bot resource
2. Click **Configuration** in the left menu
3. Next to **Microsoft App ID**, click **Manage**
4. **Copy and save the Application (client) ID**
   - ⚠️ This is your `TEAMS_APP_ID`

5. In the left menu, click **Certificates & secrets**
6. Click **New client secret**
7. Enter details:
   - **Description:** `amplifier-bot-secret`
   - **Expires:** Choose duration (recommend 24 months)
8. Click **Add**
9. **Copy and save the Value** immediately
   - ⚠️ This is your `TEAMS_APP_PASSWORD`
   - ⚠️ You can only see this once!

### 1.3 Configure Messaging Endpoint

Your bot needs a public HTTPS endpoint to receive messages from Teams.

#### For Development (using ngrok)

1. Install ngrok: https://ngrok.com/download
2. Start ngrok:
   ```bash
   ngrok http 3978
   ```
3. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
4. In Azure Portal, go to your bot resource
5. Click **Configuration**
6. Set **Messaging endpoint:**
   ```
   https://abc123.ngrok.io/api/messages
   ```
7. Click **Apply**

#### For Production

1. Deploy your bot to a server with HTTPS
2. In Azure Portal, go to your bot resource
3. Click **Configuration**
4. Set **Messaging endpoint:**
   ```
   https://your-domain.com/api/messages
   ```
5. Click **Apply**

## Step 2: Enable Teams Channel

### 2.1 Add Teams Channel

1. In your bot resource, click **Channels** in the left menu
2. Click the **Microsoft Teams** icon
3. Review and accept the Terms of Service
4. Click **Agree**
5. The Teams channel should now show as **Running**

### 2.2 Configure Channel Settings

1. Click **Edit** on the Microsoft Teams channel
2. Enable features as needed:
   - **Messaging** - ✅ Required
   - **Calling** - Optional
   - **Video** - Optional
3. Click **Apply**

## Step 3: Create Teams App Package

### 3.1 Create Manifest Directory

```bash
mkdir teams-app
cd teams-app
```

### 3.2 Create manifest.json

Create a file named `manifest.json` with this content:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
  "manifestVersion": "1.16",
  "version": "1.0.0",
  "id": "YOUR_APP_ID_HERE",
  "packageName": "com.amplifier.bot",
  "developer": {
    "name": "Your Organization",
    "websiteUrl": "https://example.com",
    "privacyUrl": "https://example.com/privacy",
    "termsOfUseUrl": "https://example.com/terms"
  },
  "name": {
    "short": "Amplifier Bot",
    "full": "Amplifier AI Assistant Bot"
  },
  "description": {
    "short": "AI assistant powered by Amplifier",
    "full": "An intelligent AI assistant that helps with tasks using the Amplifier framework and Claude AI"
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

**Replace `YOUR_APP_ID_HERE`** (appears twice) with your Application ID from Step 1.2.

### 3.3 Create Icons

You need two PNG icons:

- **color.png** - 192x192 pixels, full color icon
- **outline.png** - 32x32 pixels, transparent outline (white on transparent)

**Quick option - Use placeholders:**

```bash
# Download placeholder icons
curl -o color.png https://via.placeholder.com/192/4A90E2/FFFFFF?text=A
curl -o outline.png https://via.placeholder.com/32/FFFFFF/000000?text=A
```

**Better option - Create custom icons** that represent your bot's brand.

### 3.4 Create App Package

```bash
# Zip the manifest and icons together
zip amplifier-bot.zip manifest.json color.png outline.png
```

## Step 4: Install App to Teams

### 4.1 Upload Custom App

1. Open Microsoft Teams desktop or web app
2. Click **Apps** in the left sidebar
3. Click **Manage your apps** at the bottom
4. Click **Upload an app**
5. Select **Upload a custom app**
6. Choose your `amplifier-bot.zip` file
7. Click **Add** to install for yourself
   - Or click **Add to a team** to install for a team/channel

### 4.2 Start Conversation

1. Find your bot in the **Apps** list
2. Click **Open** or **Chat**
3. You can now message your bot!

## Step 5: Configure Environment

Create a `.env` file in your project root:

```bash
# Teams Configuration
TEAMS_APP_ID=your-app-id-from-step-1.2
TEAMS_APP_PASSWORD=your-app-password-from-step-1.2
TEAMS_PORT=3978

# Amplifier Configuration
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

## Step 6: Test Your Configuration

Run the onboarding command to verify your setup:

```bash
teams-connector onboard
```

This will:
- ✅ Verify your credentials
- ✅ Start the webhook server
- ✅ Test the /health endpoint
- ✅ Show you the messaging endpoint URL
- ✅ Guide you through testing with Teams

## Next Steps

- **[Usage Guide](./USAGE.md)** - Learn how to use the connector
- **[Deployment](./DEPLOYMENT.md)** - Deploy to production
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Common issues and solutions

## Quick Reference

### Required Credentials

| Credential | Where to Find |
|------------|---------------|
| `TEAMS_APP_ID` | Azure Portal → Bot Resource → Configuration → Microsoft App ID |
| `TEAMS_APP_PASSWORD` | Azure Portal → App Registration → Certificates & secrets → Client secrets |

### Messaging Endpoint Format

```
https://your-domain.com/api/messages
```

**Port:** Default 3978 (configurable with `TEAMS_PORT`)

### App Manifest Requirements

- `manifest.json` - App configuration
- `color.png` - 192x192px icon
- `outline.png` - 32x32px icon
- All three files zipped together

### Required Azure Resources

1. **Azure Bot** - The bot registration
2. **App Registration** - For authentication (auto-created)
3. **Teams Channel** - Enable Teams integration

## Common Issues

### "Endpoint unreachable" error

**Problem:** Teams can't reach your messaging endpoint

**Solutions:**
- Verify ngrok is running (development)
- Verify your server is accessible (production)
- Check firewall allows HTTPS traffic
- Ensure endpoint URL ends with `/api/messages`
- Verify HTTPS (not HTTP)

### "Unauthorized" error

**Problem:** App ID or password is incorrect

**Solutions:**
- Verify `TEAMS_APP_ID` matches Azure App ID exactly
- Verify `TEAMS_APP_PASSWORD` is correct (regenerate if needed)
- Check for extra spaces or quotes in .env file

### Can't upload app to Teams

**Problem:** Custom app upload is disabled

**Solutions:**
- Contact your Teams admin to enable custom app uploads
- Or ask admin to upload the app for you
- Or use App Studio in Teams to create the app

## Support

- **Issues:** https://github.com/kenotron-ms/amplifier-module-connectors/issues
- **Main Docs:** [../../../docs/](../../../docs/)
- **Azure Bot Docs:** https://docs.microsoft.com/azure/bot-service/

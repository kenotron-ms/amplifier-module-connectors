# Using the Slack App Manifest

The **app manifest** automates Slack app configuration, including slash commands. No manual clicking required!

## What It Does

The manifest (`slack-app-manifest.yaml`) defines:
- ✅ Bot user settings
- ✅ **Slash commands** (`/amplifier`, `/amplifier-status`, `/amplifier-list`)
- ✅ OAuth scopes (permissions)
- ✅ Event subscriptions
- ✅ Socket Mode enabled

## For New Apps

If you're creating a **new Slack app** from scratch:

1. Go to https://api.slack.com/apps
2. Click **Create New App**
3. Choose **From an app manifest**
4. Select your workspace
5. Copy the contents of `slack-app-manifest.yaml`
6. Paste into the YAML editor
7. Click **Next** → **Create**
8. Done! All commands are automatically configured.

## For Existing Apps

If you already have a Slack app and want to add the slash commands:

### Option 1: Update via Manifest (Recommended)

1. Go to https://api.slack.com/apps
2. Select your app
3. Click **App Manifest** in the left sidebar
4. Copy the contents of `slack-app-manifest.yaml`
5. Paste to replace the existing manifest
6. Click **Save Changes**
7. Review and confirm changes
8. Done! Commands are now configured.

### Option 2: Manual Update (If manifest update fails)

If the manifest update doesn't work (rare), you can manually add just the slash commands:

1. Go to **Slash Commands** in your app settings
2. Create these 3 commands:
   - `/amplifier` - Description: "Start a new Amplifier session for a project", Usage hint: `<path>`
   - `/amplifier-status` - Description: "Show active Amplifier sessions"
   - `/amplifier-list` - Description: "List discovered Amplifier projects"
3. Leave Request URL blank (Socket Mode handles routing)
4. Save each command

## After Configuration

1. **Get your tokens** from the app settings:
   - **Bot User OAuth Token** (starts with `xoxb-`)
   - **App-Level Token** (starts with `xapp-`, needs `connections:write` scope)

2. **Update your `.env` file:**
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_APP_TOKEN=xapp-your-token
   ANTHROPIC_API_KEY=sk-ant-your-key
   ```

3. **Install/Reinstall to workspace** if prompted

4. **Restart the bot:**
   ```bash
   make slack-daemon-restart
   ```

5. **Test in Slack:**
   ```
   /amplifier
   /amplifier-status
   /amplifier-list
   ```

## Manifest Benefits

✅ **Automated** - No manual configuration  
✅ **Version controlled** - Manifest is in git  
✅ **Reproducible** - Same config every time  
✅ **Shareable** - Others can create identical apps  
✅ **Documented** - All permissions in one place  

## Troubleshooting

### "Manifest validation failed"

**Problem:** Slack rejects the manifest.

**Solution:**
- Check YAML formatting (indentation matters!)
- Verify all scopes are valid
- Remove any unsupported features for your workspace plan

### "Some features couldn't be updated"

**Problem:** Partial manifest update.

**Solution:**
- Note which features failed
- Update those manually in the app settings
- Common issue: Can't change app name if already in use

### Commands still not working

**Problem:** Commands don't appear after manifest update.

**Solution:**
1. Go to **Slash Commands** section - verify they're listed
2. Reinstall app to workspace
3. Restart the bot
4. Try in a channel where the bot is present

## Updating the Manifest

When you add new features to the bot:

1. Update `slack-app-manifest.yaml`
2. Commit to git
3. Apply to your Slack app (Option 1 above)
4. Document the change

Example: Adding a new slash command:

```yaml
slash_commands:
  - command: /amplifier
    description: Start a new Amplifier session for a project
    usage_hint: <path>
    should_escape: false
  - command: /amplifier-new-command  # ADD THIS
    description: Description of new command
    should_escape: false
```

## See Also

- [Slack App Manifest Documentation](https://api.slack.com/reference/manifests)
- [Slack Setup Guide](./slack-setup.md)
- [Slash Commands Setup](./slack-slash-commands-setup.md)

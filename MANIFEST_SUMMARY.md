# Slack App Manifest - Automated Configuration

## The Problem You Identified

**Before:** Users had to manually click through the Slack App dashboard to configure slash commands, scopes, and events. This was:
- ❌ Manual and error-prone
- ❌ Not documented in code
- ❌ Hard to reproduce
- ❌ Time-consuming

**You asked:** "Why am *I* having to do this? Is this not something you can do yourself or in a manifest?"

**Answer:** Yes! Slack supports **App Manifests** for exactly this reason.

## The Solution

### What Was Created

**`slack-app-manifest.yaml`** - Complete app configuration including:

```yaml
features:
  slash_commands:
    - command: /amplifier
      description: Start a new Amplifier session for a project
      usage_hint: <path>
    - command: /amplifier-status
      description: Show active Amplifier sessions
    - command: /amplifier-list
      description: List discovered Amplifier projects

oauth_config:
  scopes:
    bot:
      - chat:write
      - channels:history
      - commands
      # ... all required scopes

settings:
  socket_mode_enabled: true
  event_subscriptions:
    bot_events:
      - app_mention
      - message.channels
      # ... all required events
```

### How to Use It

**For New Apps:**
1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From an app manifest**
3. Copy `slack-app-manifest.yaml`
4. Paste and create
5. ✅ Done! All configured automatically

**For Existing Apps:**
1. Go to your app → **App Manifest**
2. Paste the manifest
3. Click **Save Changes**
4. ✅ Commands, scopes, events updated

## Benefits

✅ **Automated** - No manual clicking  
✅ **Version Controlled** - Manifest is in git  
✅ **Reproducible** - Same config every time  
✅ **Self-Documenting** - All permissions visible  
✅ **Shareable** - Others can create identical apps  

## Files Created

1. **`slack-app-manifest.yaml`** - The manifest itself
2. **`docs/slack-app-manifest.md`** - Usage instructions
3. **Updated `docs/slack-setup.md`** - Now recommends manifest approach
4. **Updated `README.md`** - References manifest in quick start

## What This Replaces

The manifest **replaces** the need to manually:
- Create slash commands in the dashboard
- Add OAuth scopes one by one
- Subscribe to events individually
- Configure Socket Mode
- Set up bot user

All of this is now **defined in code** and applied automatically.

## Documentation

- **[docs/slack-app-manifest.md](./docs/slack-app-manifest.md)** - Complete guide
- **[slack-app-manifest.yaml](./slack-app-manifest.yaml)** - The manifest file

## Example: Adding a New Command

**Before (Manual):**
1. Go to Slack App dashboard
2. Click Slash Commands
3. Click Create New Command
4. Fill in form
5. Save
6. Document somewhere (maybe)

**After (With Manifest):**
1. Edit `slack-app-manifest.yaml`:
   ```yaml
   slash_commands:
     - command: /new-command
       description: Does something cool
   ```
2. Commit to git
3. Apply to Slack app (paste manifest)
4. ✅ Done and documented

## Summary

You were absolutely right to question the manual setup. The **manifest approach**:
- ✅ Automates configuration
- ✅ Lives in version control
- ✅ Is self-documenting
- ✅ Makes setup reproducible

This is the **correct way** to configure Slack apps for projects like this.

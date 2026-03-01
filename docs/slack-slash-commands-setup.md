# Slack Slash Commands Setup

To use the project management features (`/amplifier`, `/amplifier-status`, `/amplifier-list`), you need to configure slash commands in your Slack app.

## Prerequisites

- Slack app already created (see [slack-setup.md](slack-setup.md))
- Socket Mode enabled
- Bot installed to workspace

## Step 1: Create Slash Commands

1. Go to https://api.slack.com/apps
2. Select your Amplifier bot app
3. Go to **Slash Commands** in the left sidebar
4. Click **Create New Command** for each command below

### Command 1: `/amplifier`

- **Command:** `/amplifier`
- **Request URL:** Leave blank (Socket Mode handles this)
- **Short Description:** `Start a new Amplifier session for a project`
- **Usage Hint:** `<project-name-or-path>`
- Click **Save**

### Command 2: `/amplifier-status`

- **Command:** `/amplifier-status`
- **Request URL:** Leave blank (Socket Mode handles this)
- **Short Description:** `Show active Amplifier sessions`
- **Usage Hint:** (leave blank)
- Click **Save**

### Command 3: `/amplifier-list`

- **Command:** `/amplifier-list`
- **Request URL:** Leave blank (Socket Mode handles this)
- **Short Description:** `List available registered projects`
- **Usage Hint:** (leave blank)
- Click **Save**

## Step 2: Reinstall App (if needed)

If you get permission errors when using the commands:

1. Go to **OAuth & Permissions**
2. Click **Reinstall to Workspace**
3. Review and approve the new permissions
4. Update your `SLACK_BOT_TOKEN` if it changed

## Step 3: Test Commands

In any channel where the bot is present:

### Test `/amplifier`

```
/amplifier
```

Should show usage help.

### Test `/amplifier-list`

```
/amplifier-list
```

Should show registered projects (or a message about setting up projects.json).

### Test `/amplifier-status`

```
/amplifier-status
```

Should show active sessions (or "No active sessions" if none).

## Step 4: Set Up Projects (Optional)

To use project names instead of paths:

1. Create `~/.amplifier/projects.json`:

```json
{
  "projects": {
    "my-project": {
      "path": "/path/to/project",
      "description": "My awesome project"
    }
  }
}
```

2. Restart the bot:

```bash
./restart-daemon.sh
```

3. Test:

```
/amplifier my-project
```

## Troubleshooting

### "Command not found"

**Problem:** Slack says the command doesn't exist.

**Solutions:**
1. Verify commands are created in the Slack app settings
2. Check that Socket Mode is enabled
3. Restart the bot
4. Try reinstalling the app to workspace

### "dispatch_failed"

**Problem:** Command fails with a dispatch error.

**Solutions:**
1. Check that the bot is running (`./tail-logs.sh`)
2. Verify Socket Mode connection is active
3. Check bot logs for errors
4. Restart the bot

### Commands work but no response

**Problem:** Command executes but bot doesn't respond.

**Solutions:**
1. Check bot logs: `./tail-logs.sh -e`
2. Verify bot has `chat:write` permission
3. Check that bot is in the channel (invite with `/invite @bot-name`)
4. Try using the command in a different channel

### "Project not found"

**Problem:** `/amplifier my-project` says project not found.

**Solutions:**
1. Use `/amplifier-list` to see registered projects
2. Create `~/.amplifier/projects.json` if it doesn't exist
3. Use an explicit path: `/amplifier /path/to/project`
4. Check that the path in projects.json exists

## Next Steps

See [slack-projects.md](slack-projects.md) for full documentation on using the project management features.

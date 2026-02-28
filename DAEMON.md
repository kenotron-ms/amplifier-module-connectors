# Slack Connector Daemon Management

Quick reference for managing the Slack connector daemon during development and testing.

## Quick Start Scripts

### `./manage-daemon.sh` - Full Management Tool

Comprehensive daemon management with status, logs, and restart capabilities.

**Usage:**
```bash
./manage-daemon.sh <command>
```

**Commands:**

| Command | Description | Use Case |
|---------|-------------|----------|
| `status` | Show daemon status & PID | Check if running |
| `restart` | Quick restart (stop + start) | **Testing new features** |
| `start` | Start the daemon | After stopping |
| `stop` | Stop the daemon | Manual shutdown |
| `logs` | Show recent logs (last 50 lines) | Debug issues |
| `follow` | Follow logs in real-time | Watch live activity |
| `reload` | Full reload (unload + load) | After config changes |

### `./restart-daemon.sh` - Quick Restart

Simple script for quick restarts during testing. Just run:
```bash
./restart-daemon.sh
```

## Common Workflows

### Testing New Features

After making code changes:

```bash
# 1. Quick restart to load new code
./manage-daemon.sh restart

# 2. Watch logs to verify it started
./manage-daemon.sh follow

# 3. Test in Slack, then check status
./manage-daemon.sh status
```

### Debugging Issues

```bash
# Check if running
./manage-daemon.sh status

# View recent activity
./manage-daemon.sh logs

# Watch live logs
./manage-daemon.sh follow
```

### After Config Changes

If you modified the `.plist` file:

```bash
# Full reload to pick up config changes
./manage-daemon.sh reload
```

### Manual Control

```bash
# Stop the daemon
./manage-daemon.sh stop

# Start it again
./manage-daemon.sh start
```

## Log Files

- **stdout**: `/tmp/slack-connector.log`
- **stderr**: `/tmp/slack-connector-error.log`

Quick access:
```bash
tail -f /tmp/slack-connector.log        # Follow stdout
tail -f /tmp/slack-connector-error.log  # Follow stderr
```

## Direct launchctl Commands

If you prefer using launchctl directly:

```bash
# Status
launchctl list com.amplifier.slack-connector

# Stop
launchctl stop com.amplifier.slack-connector

# Start
launchctl start com.amplifier.slack-connector

# Reload (after plist changes)
launchctl unload ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
launchctl load ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
```

## Troubleshooting

### Daemon won't start

1. Check if it's loaded:
   ```bash
   launchctl list | grep slack-connector
   ```

2. If not loaded:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
   ```

3. Check logs for errors:
   ```bash
   ./manage-daemon.sh logs
   ```

### Process is running but not responding

```bash
# Force stop and restart
./manage-daemon.sh stop
sleep 2
./manage-daemon.sh start
```

### Need to completely reset

```bash
# Unload, kill all processes, reload
launchctl unload ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
pkill -9 -f "slack-connector start"
launchctl load ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
```

## Development Tips

- **After code changes**: Use `./manage-daemon.sh restart`
- **After bundle.md changes**: Just `restart` (bundle reloads automatically)
- **After .plist changes**: Use `./manage-daemon.sh reload`
- **Watch for errors**: Keep `./manage-daemon.sh follow` running in a terminal

## Session Persistence

With the thread session fix, conversation context persists across daemon restarts when using context-persistent storage. Each Slack thread maintains its own session ID: `slack-{channel}-{thread_ts}`

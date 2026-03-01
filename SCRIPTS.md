# Slack Connector Management Scripts

Quick reference for all management and utility scripts.

## Log Viewing

### `tail-logs.sh` - Log Viewer
**Powerful log viewer with filtering and colors**

```bash
# Basic usage
./tail-logs.sh                      # Tail both logs with color

# Show only errors
./tail-logs.sh -e
./tail-logs.sh --errors

# Show last N lines (default: 50)
./tail-logs.sh -n 100

# Filter by content
./tail-logs.sh --grep "tool"        # Show lines containing "tool"
./tail-logs.sh --grep "session"     # Show session-related logs

# Filter by log level
./tail-logs.sh --level ERROR        # Only ERROR level
./tail-logs.sh --level WARNING      # Only WARNING level
./tail-logs.sh --level DEBUG        # Only DEBUG level

# Disable colors (for piping)
./tail-logs.sh --no-color

# Combine filters
./tail-logs.sh --level ERROR --grep "tool"
```

**Color coding:**
- 🔴 **Red** - Errors, exceptions, tracebacks
- 🟡 **Yellow** - Warnings
- 🟢 **Green** - Info messages
- ⚪ **Gray** - Debug messages
- 🔵 **Cyan** - Tool execution
- 🔵 **Blue** - Session events

**Use when:** 
- Debugging issues
- Monitoring specific events
- Looking for errors
- Understanding tool execution flow

---

## Daemon Management

### `manage-daemon.sh` - Daemon Control
**Start, stop, restart, and check status**

```bash
# Check status
./manage-daemon.sh status

# Start daemon
./manage-daemon.sh start

# Stop daemon
./manage-daemon.sh stop

# Restart daemon
./manage-daemon.sh restart

# Unload daemon
./manage-daemon.sh unload
```

**Use when:** Managing the launchd daemon

---

### `restart-daemon.sh` - Quick Restart
**Quickly restart the daemon (for development)**

```bash
./restart-daemon.sh
```

Stops, unloads, reloads, and starts the daemon in one command.

**Use when:** 
- Testing code changes
- Quick iteration during development

---

## Development Workflow

### Quick Development Cycle

```bash
# 1. Make code changes
vim src/slack_connector/bridge.py

# 2. Restart daemon
./restart-daemon.sh

# 3. Watch logs
./tail-logs.sh --grep "tool"

# 4. Test in Slack
# Send a message to the bot

# 5. Check for errors
./tail-logs.sh -e
```

### Debugging a Specific Issue

```bash
# Watch tool execution in real-time
./tail-logs.sh --grep "tool" --level DEBUG

# Monitor errors only
./tail-logs.sh -e

# Search for specific patterns
./tail-logs.sh --grep "web_search"
./tail-logs.sh --grep "SlackStreamingHook"
```

### Production Monitoring

```bash
# Check daemon health
./manage-daemon.sh status

# Monitor for errors
./tail-logs.sh --level ERROR

# Watch recent activity
./tail-logs.sh -n 20
```

---

## Log Files

All logs are written to `/tmp/`:

| File | Content | Purpose |
|------|---------|---------|
| `/tmp/slack-connector.log` | stdout | Info, debug, normal operation |
| `/tmp/slack-connector-error.log` | stderr | Errors, warnings, exceptions |

**Rotating logs:**
```bash
# Clear old logs
> /tmp/slack-connector.log
> /tmp/slack-connector-error.log

# Or restart daemon (logs will be overwritten)
./restart-daemon.sh
```

---

## Tips & Tricks

### Filter for Tool Execution
```bash
./tail-logs.sh --grep "tool:"
```

### Watch Session Creation
```bash
./tail-logs.sh --grep "session"
```

### Monitor Slack Events
```bash
./tail-logs.sh --grep "message\|mention"
```

### Debug Streaming Updates
```bash
./tail-logs.sh --grep "SlackStreamingHook"
```

### Save Logs to File
```bash
./tail-logs.sh --no-color > debug.log
```

### Multiple Terminals
```bash
# Terminal 1: Watch all activity
./tail-logs.sh

# Terminal 2: Watch errors only
./tail-logs.sh -e

# Terminal 3: Test changes
./restart-daemon.sh && ./tail-logs.sh --grep "tool"
```

---

## Troubleshooting

### Daemon won't start
```bash
# Check launchd status
launchctl list com.amplifier.slack-connector

# Check error log
./tail-logs.sh -e -n 100

# Verify configuration
cat ~/Library/LaunchAgents/com.amplifier.slack-connector.plist
```

### No logs appearing
```bash
# Verify log files exist
ls -lh /tmp/slack-connector*.log

# Check daemon is running
./manage-daemon.sh status

# Try starting manually
slack-connector start --channel C0AJBKTR0JU --debug
```

### Bot not responding
```bash
# Check for errors
./tail-logs.sh -e

# Verify Slack connection
./tail-logs.sh --grep "Socket Mode\|authenticated"

# Check recent activity
./tail-logs.sh -n 50
```

---

## Quick Reference

| Task | Command |
|------|---------|
| View logs | `./tail-logs.sh` |
| Show only errors | `./tail-logs.sh -e` |
| Filter logs | `./tail-logs.sh --grep "pattern"` |
| Restart daemon | `./restart-daemon.sh` |
| Check status | `./manage-daemon.sh status` |
| Stop daemon | `./manage-daemon.sh stop` |
| Start daemon | `./manage-daemon.sh start` |

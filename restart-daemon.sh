#!/bin/bash
# Restart the Slack connector daemon (useful for testing new features)

set -e

DAEMON_LABEL="com.amplifier.slack-connector"
LOG_FILE="/tmp/slack-connector.log"
ERROR_LOG="/tmp/slack-connector-error.log"

echo "🔄 Restarting Slack connector daemon..."
echo ""

# Check if daemon is loaded
if launchctl list | grep -q "$DAEMON_LABEL"; then
    echo "📋 Current status:"
    launchctl list "$DAEMON_LABEL" | grep -E "PID|LastExitStatus"
    echo ""
    
    # Stop the daemon
    echo "⏹️  Stopping daemon..."
    launchctl stop "$DAEMON_LABEL"
    sleep 2
    
    # Kill any lingering processes
    if pgrep -f "slack-connector start" > /dev/null; then
        echo "🔪 Killing lingering processes..."
        pkill -f "slack-connector start" || true
        sleep 1
    fi
    
    # Start the daemon
    echo "▶️  Starting daemon..."
    launchctl start "$DAEMON_LABEL"
    sleep 2
    
    # Check new status
    echo ""
    echo "✅ Daemon restarted!"
    echo ""
    echo "📊 New status:"
    launchctl list "$DAEMON_LABEL" | grep -E "PID|LastExitStatus"
    
    # Show new PID
    NEW_PID=$(launchctl list "$DAEMON_LABEL" | grep "PID" | awk '{print $3}' | tr -d '";')
    if [ -n "$NEW_PID" ] && [ "$NEW_PID" != "-" ]; then
        echo ""
        echo "🆔 Process info:"
        ps -p "$NEW_PID" -o pid,lstart,command | tail -1
    fi
    
    echo ""
    echo "📝 Logs:"
    echo "   stdout: tail -f $LOG_FILE"
    echo "   stderr: tail -f $ERROR_LOG"
    echo ""
    echo "💡 Tip: Watch logs with: tail -f $LOG_FILE"
    
else
    echo "❌ Daemon not loaded!"
    echo ""
    echo "To load the daemon:"
    echo "  launchctl load ~/Library/LaunchAgents/$DAEMON_LABEL.plist"
    exit 1
fi

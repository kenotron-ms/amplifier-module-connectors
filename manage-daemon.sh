#!/bin/bash
# Manage the Slack connector daemon

set -e

DAEMON_LABEL="com.amplifier.slack-connector"
PLIST_PATH="$HOME/Library/LaunchAgents/$DAEMON_LABEL.plist"
LOG_FILE="/tmp/slack-connector.log"
ERROR_LOG="/tmp/slack-connector-error.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_status() {
    echo -e "${BLUE}📊 Daemon Status${NC}"
    echo ""
    
    if launchctl list | grep -q "$DAEMON_LABEL"; then
        launchctl list "$DAEMON_LABEL"
        echo ""
        
        PID=$(launchctl list "$DAEMON_LABEL" | grep '"PID"' | awk '{print $3}' | tr -d '";')
        if [ -n "$PID" ] && [ "$PID" != "-" ]; then
            echo -e "${GREEN}✅ Running (PID: $PID)${NC}"
            echo ""
            ps -p "$PID" -o pid,lstart,etime,command
        else
            echo -e "${RED}❌ Not running${NC}"
        fi
    else
        echo -e "${RED}❌ Daemon not loaded${NC}"
        echo ""
        echo "To load: launchctl load $PLIST_PATH"
    fi
}

restart_daemon() {
    echo -e "${YELLOW}🔄 Restarting daemon...${NC}"
    echo ""
    
    if ! launchctl list | grep -q "$DAEMON_LABEL"; then
        echo -e "${RED}❌ Daemon not loaded!${NC}"
        exit 1
    fi
    
    echo "⏹️  Stopping..."
    launchctl stop "$DAEMON_LABEL"
    sleep 2
    
    # Kill any lingering processes
    if pgrep -f "slack-connector start" > /dev/null; then
        echo "🔪 Cleaning up lingering processes..."
        pkill -f "slack-connector start" || true
        sleep 1
    fi
    
    echo "▶️  Starting..."
    launchctl start "$DAEMON_LABEL"
    sleep 2
    
    echo ""
    show_status
}

stop_daemon() {
    echo -e "${YELLOW}⏹️  Stopping daemon...${NC}"
    
    if ! launchctl list | grep -q "$DAEMON_LABEL"; then
        echo -e "${RED}❌ Daemon not loaded!${NC}"
        exit 1
    fi
    
    launchctl stop "$DAEMON_LABEL"
    sleep 1
    
    # Force kill if needed
    if pgrep -f "slack-connector start" > /dev/null; then
        echo "🔪 Force killing processes..."
        pkill -9 -f "slack-connector start" || true
    fi
    
    echo -e "${GREEN}✅ Stopped${NC}"
}

start_daemon() {
    echo -e "${YELLOW}▶️  Starting daemon...${NC}"
    
    if ! launchctl list | grep -q "$DAEMON_LABEL"; then
        echo -e "${RED}❌ Daemon not loaded!${NC}"
        exit 1
    fi
    
    launchctl start "$DAEMON_LABEL"
    sleep 2
    
    echo ""
    show_status
}

show_logs() {
    echo -e "${BLUE}📝 Recent logs (last 50 lines):${NC}"
    echo ""
    echo -e "${YELLOW}=== STDOUT ===${NC}"
    tail -50 "$LOG_FILE"
    echo ""
    echo -e "${YELLOW}=== STDERR ===${NC}"
    tail -50 "$ERROR_LOG"
}

follow_logs() {
    echo -e "${BLUE}📝 Following logs (Ctrl+C to stop)${NC}"
    echo ""
    tail -f "$LOG_FILE"
}

reload_daemon() {
    echo -e "${YELLOW}🔃 Reloading daemon (unload + load)${NC}"
    echo ""
    
    if launchctl list | grep -q "$DAEMON_LABEL"; then
        echo "⏹️  Unloading..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        sleep 1
    fi
    
    # Kill any lingering processes
    if pgrep -f "slack-connector start" > /dev/null; then
        echo "🔪 Cleaning up processes..."
        pkill -9 -f "slack-connector start" || true
        sleep 1
    fi
    
    echo "📥 Loading..."
    launchctl load "$PLIST_PATH"
    sleep 2
    
    echo ""
    show_status
}

case "${1:-}" in
    status)
        show_status
        ;;
    restart)
        restart_daemon
        ;;
    stop)
        stop_daemon
        ;;
    start)
        start_daemon
        ;;
    logs)
        show_logs
        ;;
    follow|tail)
        follow_logs
        ;;
    reload)
        reload_daemon
        ;;
    *)
        echo "Usage: $0 {status|restart|start|stop|logs|follow|reload}"
        echo ""
        echo "Commands:"
        echo "  status   - Show daemon status"
        echo "  restart  - Restart the daemon (quick, for testing)"
        echo "  start    - Start the daemon"
        echo "  stop     - Stop the daemon"
        echo "  logs     - Show recent logs"
        echo "  follow   - Follow logs in real-time"
        echo "  reload   - Full reload (unload + load, for config changes)"
        exit 1
        ;;
esac

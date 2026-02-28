#!/bin/bash
# Tail Slack connector logs with color and formatting

set -euo pipefail

STDOUT_LOG="/tmp/slack-connector.log"
STDERR_LOG="/tmp/slack-connector-error.log"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

show_help() {
    cat << HELP
Usage: ./tail-logs.sh [OPTIONS]

Tail Slack connector logs with optional filtering and color.

OPTIONS:
    -h, --help          Show this help message
    -e, --errors        Show only error log
    -b, --both          Show both stdout and stderr (default)
    -f, --follow        Follow logs (tail -f, default)
    -n NUM              Show last NUM lines (default: 50)
    --no-color          Disable color output
    --grep PATTERN      Filter lines matching PATTERN
    --level LEVEL       Filter by log level (DEBUG, INFO, WARNING, ERROR)

EXAMPLES:
    ./tail-logs.sh                      # Tail both logs with color
    ./tail-logs.sh -e                   # Tail only errors
    ./tail-logs.sh -n 100               # Show last 100 lines
    ./tail-logs.sh --grep "tool"        # Filter for tool-related logs
    ./tail-logs.sh --level ERROR        # Show only ERROR level logs

LOG FILES:
    stdout: $STDOUT_LOG
    stderr: $STDERR_LOG
HELP
}

# Parse arguments
SHOW_ERRORS_ONLY=false
SHOW_BOTH=true
FOLLOW=true
NUM_LINES=50
USE_COLOR=true
GREP_PATTERN=""
LOG_LEVEL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -e|--errors)
            SHOW_ERRORS_ONLY=true
            SHOW_BOTH=false
            shift
            ;;
        -b|--both)
            SHOW_BOTH=true
            SHOW_ERRORS_ONLY=false
            shift
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n)
            NUM_LINES="$2"
            shift 2
            ;;
        --no-color)
            USE_COLOR=false
            shift
            ;;
        --grep)
            GREP_PATTERN="$2"
            shift 2
            ;;
        --level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to colorize log lines
colorize_log() {
    if [ "$USE_COLOR" = false ]; then
        cat
        return
    fi
    
    while IFS= read -r line; do
        # Color by log level
        if [[ "$line" =~ ERROR|Exception|Traceback ]]; then
            echo -e "${RED}${line}${NC}"
        elif [[ "$line" =~ WARNING|Warning ]]; then
            echo -e "${YELLOW}${line}${NC}"
        elif [[ "$line" =~ INFO ]]; then
            echo -e "${GREEN}${line}${NC}"
        elif [[ "$line" =~ DEBUG ]]; then
            echo -e "${GRAY}${line}${NC}"
        elif [[ "$line" =~ "tool:" ]]; then
            echo -e "${CYAN}${line}${NC}"
        elif [[ "$line" =~ "session" ]]; then
            echo -e "${BLUE}${line}${NC}"
        else
            echo "$line"
        fi
    done
}

# Function to filter by log level
filter_level() {
    if [ -z "$LOG_LEVEL" ]; then
        cat
    else
        grep -i "$LOG_LEVEL"
    fi
}

# Function to filter by pattern
filter_pattern() {
    if [ -z "$GREP_PATTERN" ]; then
        cat
    else
        grep -i "$GREP_PATTERN"
    fi
}

# Check if log files exist
if [ "$SHOW_ERRORS_ONLY" = false ] && [ ! -f "$STDOUT_LOG" ]; then
    echo -e "${YELLOW}Warning: stdout log not found: $STDOUT_LOG${NC}"
    echo "The daemon may not be running or hasn't created logs yet."
fi

if [ ! -f "$STDERR_LOG" ]; then
    echo -e "${YELLOW}Warning: stderr log not found: $STDERR_LOG${NC}"
    echo "The daemon may not be running or hasn't created logs yet."
fi

# Display header
echo -e "${CYAN}=== Slack Connector Logs ===${NC}"
if [ "$SHOW_ERRORS_ONLY" = true ]; then
    echo -e "${CYAN}Showing: ${RED}errors only${NC}"
    echo -e "${CYAN}File: $STDERR_LOG${NC}"
elif [ "$SHOW_BOTH" = true ]; then
    echo -e "${CYAN}Showing: both stdout and stderr${NC}"
    echo -e "${CYAN}Files: $STDOUT_LOG, $STDERR_LOG${NC}"
fi
[ -n "$GREP_PATTERN" ] && echo -e "${CYAN}Filter: $GREP_PATTERN${NC}"
[ -n "$LOG_LEVEL" ] && echo -e "${CYAN}Level: $LOG_LEVEL${NC}"
echo -e "${CYAN}================================${NC}"
echo

# Tail the logs
if [ "$FOLLOW" = true ]; then
    if [ "$SHOW_ERRORS_ONLY" = true ]; then
        tail -f -n "$NUM_LINES" "$STDERR_LOG" 2>/dev/null | filter_level | filter_pattern | colorize_log
    elif [ "$SHOW_BOTH" = true ]; then
        # Use multitail if available, otherwise tail both with labels
        if command -v multitail &> /dev/null; then
            multitail -s 2 -l "tail -f -n $NUM_LINES $STDOUT_LOG | filter_level | filter_pattern" -l "tail -f -n $NUM_LINES $STDERR_LOG | filter_level | filter_pattern"
        else
            # Fallback: interleave both logs with labels
            (tail -f -n "$NUM_LINES" "$STDOUT_LOG" 2>/dev/null | sed "s/^/[OUT] /" & \
             tail -f -n "$NUM_LINES" "$STDERR_LOG" 2>/dev/null | sed "s/^/[ERR] /" &) | filter_level | filter_pattern | colorize_log
        fi
    fi
else
    # Non-follow mode: just show last N lines
    if [ "$SHOW_ERRORS_ONLY" = true ]; then
        tail -n "$NUM_LINES" "$STDERR_LOG" 2>/dev/null | filter_level | filter_pattern | colorize_log
    elif [ "$SHOW_BOTH" = true ]; then
        echo -e "${BLUE}=== STDOUT ===${NC}"
        tail -n "$NUM_LINES" "$STDOUT_LOG" 2>/dev/null | filter_level | filter_pattern | colorize_log
        echo
        echo -e "${RED}=== STDERR ===${NC}"
        tail -n "$NUM_LINES" "$STDERR_LOG" 2>/dev/null | filter_level | filter_pattern | colorize_log
    fi
fi

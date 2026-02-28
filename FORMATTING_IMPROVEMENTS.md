# Claude Code-Inspired Tool Display

This document describes the improvements made to tool execution display, inspired by Claude Code's approach to showing agentic work.

## The Problem

Previous tool display was overwhelming:
- **Full JSON dumps** of arguments (100+ lines for complex params)
- **Full result output** (thousands of lines of file contents, search results, etc.)
- **Heavy thinking display** that dominated the UI
- Hard to scan and understand what's happening at a glance

## The Solution: Claude Code Style

Show **just enough** to give users confidence without overwhelming them:

1. **Thinking** - Light, italic treatment, truncated to 100 chars
2. **Tool calls** - Concise args (max 3 params, truncated values)
3. **Results** - Simple success/failure indicators (✅/❌)

## Visual Comparison

### Before (verbose)

```
[Message 1] 🔄 Running: web_search
Arguments:
{
  "query": "Python asyncio best practices",
  "max_results": 10,
  "include_snippets": true,
  "filter_domains": ["stackoverflow.com", "docs.python.org"]
}

[Message 2] ✅ Completed: web_search
Result:
{
  "results": [
    {
      "title": "Asyncio Best Practices",
      "url": "https://...",
      "snippet": "Lorem ipsum dolor sit amet...",
      ...
    },
    ... [9 more results]
  ],
  "total_found": 247,
  "query_time_ms": 143
}
```

**Problems:**
- Takes up 30+ lines
- Hard to scan quickly
- Result dump doesn't help user understand what happened
- JSON formatting is technical and intimidating

### After (concise)

```
[Message 1] 🔧 `web_search`(query="Python asyncio best...", max_results=10, ... +2 more)
[Message 2] ✅ `web_search`(query="Python asyncio best...", max_results=10, ... +2 more)
```

**Benefits:**
- Takes up 2 lines
- Easy to scan
- Shows the essential info (what tool, what query)
- Success/failure is immediately clear
- Looks like code (familiar to developers)

## Implementation Details

### Tool Argument Formatting

The `_format_tool_args()` function in `bridge.py`:

```python
def _format_tool_args(args: dict[str, Any]) -> str:
    """Format tool arguments concisely."""
    # Show up to 3 key arguments
    # Truncate long strings to 50 chars
    # Show [N items] for lists/dicts instead of contents
    # Add "... +N more" if there are additional args
```

**Examples:**

| Input | Output |
|-------|--------|
| `{"query": "test"}` | `query="test"` |
| `{"query": "very long string..."}` | `query="very long str..."` |
| `{"items": [1,2,3,4,5]}` | `items=[5 items]` |
| `{"a": 1, "b": 2, "c": 3, "d": 4}` | `a=1, b=2, c=3, ... +1 more` |

### Thinking Display (Blocks Mode)

Thinking blocks are shown in **italic** (lighter treatment):

```
_💭 I need to search for recent information about Python asyncio..._
```

- Truncated to 100 characters
- Italic text = less visually prominent
- Emoji provides context without being heavy

### Result Display

Results are **not shown** - only success/failure:

```
✅ `tool_name`(args)  # Success
❌ `tool_name`(args) - Error message  # Failure
```

**Rationale:**
- Tool results are often huge (file contents, search results, etc.)
- The AI processes the result, user doesn't need to see it
- Success/failure is what matters for confidence
- Errors are shown (truncated to 100 chars) for debugging

## Mode Comparison

### Single Mode (Default)
**Use case:** Production, end users

```
:hourglass_flowing_sand: ...
→ ✓ `web_search`
→ ✓ `web_search`
  ✓ `read_file`
  :hourglass_flowing_sand: ...
→ [DELETED]

[Final response]
```

**Benefits:**
- Clean UX (status disappears)
- Minimal clutter
- Shows progress during execution

### Multi Mode (Debugging)
**Use case:** Development, debugging, auditing

```
🤔 Thinking...

🔧 `web_search`(query="Python asyncio")
→ ✅ `web_search`(query="Python asyncio")

🔧 `read_file`(file_path="src/main.py")
→ ✅ `read_file`(file_path="src/main.py")

[Final response]
[All messages remain visible]
```

**Benefits:**
- Full execution audit trail
- Can see what tools ran after completion
- Concise, scannable format
- Easy to spot failures

### Blocks Mode (Educational)
**Use case:** Understanding AI reasoning, learning

```
_thinking..._

_💭 I need to search for recent information..._

🔧 `web_search`(query="Python asyncio")
✅ `web_search`(query="Python asyncio")

Here's what I found based on the search...

🔧 `read_file`(file_path="src/main.py")
✅ `read_file`(file_path="src/main.py")

[Final response]
```

**Benefits:**
- See thinking process (lightly)
- See intermediate text responses
- Full transparency
- Educational value

## Usage

```bash
# Default: single message mode (clean UX)
slack-connector start

# Multi message mode (debugging, Claude Code style)
slack-connector start --streaming-mode multi

# Blocks mode (full transparency)
slack-connector start --streaming-mode blocks
```

## Design Principles

These improvements follow Claude Code's approach:

1. **Progressive disclosure** - Show just enough at each step
2. **Scannable** - Easy to skim and understand quickly
3. **Confidence-building** - User knows work is happening
4. **Non-overwhelming** - Don't dump raw data
5. **Familiar syntax** - Looks like function calls (code-like)
6. **Light thinking** - Show reasoning without dominating UI

## Future Improvements

Potential enhancements:

1. **Collapsible details** - Click to expand full args/results (Slack limitation: no native collapse)
2. **Timing info** - Show how long each tool took
3. **Custom emoji** - Workspace-specific animated indicators
4. **Color coding** - Use Slack's limited color options for status
5. **Threading** - Group related tool calls together

## References

- Claude Code CLI - Inspiration for concise tool display
- `src/slack_connector/bridge.py` - Implementation
- `PROGRESSIVE_UPDATES.md` - Full mode documentation

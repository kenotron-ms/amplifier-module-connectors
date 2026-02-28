# Slack Message Formatting Fixes

## Issues Fixed

### 1. ✅ Duplicate Messages at Conversation Start
**Problem:** When a conversation started, users saw two identical reply blocks from the bot.

**Root Cause:** Both the bot's `handle_message()` method AND the orchestrator were posting the final response:
- `SlackDisplaySystem.display()` was being called by the orchestrator (line 118 in bridge.py)
- Bot was also posting via `chat_postMessage()` (line 241 in bot.py)

**Fix:**
- Set `display_system=None` when creating sessions (bot.py:169)
- Added explicit comment explaining why we don't pass a display_system
- Now only the bot's `handle_message()` posts the final response (after formatting)

**Files Changed:**
- `src/slack_connector/bot.py` - Removed display_system from session creation

---

### 2. ✅ Thinking Blocks and Tool Calls Appearing in Messages
**Problem:** Agent responses contained raw thinking blocks (`<thinking>...</thinking>`), tool call XML, and other internal artifacts that shouldn't be shown to users.

**Root Cause:** The response from `session.execute()` includes all internal reasoning and tool execution details, which were being posted directly to Slack without filtering.

**Fix:**
- Created `formatter.py` module with `clean_response()` function
- Filters out:
  - `<thinking>...</thinking>` blocks
  - `<tool_call>...</tool_call>` blocks
  - `<function_calls>...</function_calls>` blocks
  - `<tool_result>...</tool_result>` blocks
  - Internal reasoning markers like `[THINKING:...]`, `[TOOL:...]`
- Cleans up excessive whitespace

**Files Changed:**
- `src/slack_connector/formatter.py` - New module (clean_response function)
- `src/slack_connector/bot.py` - Uses formatter before posting
- `src/slack_connector/bridge.py` - SlackDisplaySystem uses formatter

---

### 3. ✅ Markdown Formatting Not Rendering in Slack
**Problem:** Agent writes standard Markdown (headings, bold, links, code blocks) but Slack doesn't render it - users saw raw syntax like `**bold**`, `### heading`, etc.

**Root Cause:** Slack doesn't support standard Markdown. It has its own limited `mrkdwn` dialect:
- Bold: `*text*` (not `**text**`)
- Links: `<url|text>` (not `[text](url)`)
- No native heading support

**Fix:**
- Created `markdown_to_mrkdwn()` function that converts:
  - `**text**` / `__text__` → `*text*` (Slack bold)
  - `*text*` → `_text_` (Slack italic)
  - `[text](url)` → `<url|text>` (Slack links)
  - `### Heading` → `*Heading*` (bold, since Slack has no headings)
  - Code blocks (` ```lang...``` `) preserved as-is (Slack supports these)
- Created `markdown_to_blocks()` for future Block Kit rich text support
- Created `format_for_slack()` wrapper that:
  1. Cleans artifacts
  2. Converts Markdown
  3. Returns both `text` (fallback) and `blocks` (rich display)

**Files Changed:**
- `src/slack_connector/formatter.py` - New module (markdown conversion functions)
- `src/slack_connector/bot.py` - Uses formatter with `use_blocks=True`
- `src/slack_connector/bridge.py` - SlackDisplaySystem uses formatter

---

## New Files

### `src/slack_connector/formatter.py`
Comprehensive response formatting utilities:

**Functions:**
- `clean_response(text: str) -> str` - Remove thinking blocks and tool artifacts
- `markdown_to_mrkdwn(text: str) -> str` - Convert Markdown to Slack mrkdwn
- `markdown_to_blocks(text: str) -> list[dict]` - Convert to Block Kit (basic implementation)
- `format_for_slack(text: str, use_blocks: bool) -> dict` - Main entry point

**Usage:**
```python
from slack_connector.formatter import format_for_slack

formatted = format_for_slack(agent_response, use_blocks=True)
await client.chat_postMessage(
    channel=channel,
    text=formatted["text"],  # Fallback for notifications
    blocks=formatted.get("blocks"),  # Rich display
)
```

---

## Testing

All formatter functions have been tested with:
- Thinking block removal
- Tool call removal
- Bold/italic conversion
- Link conversion
- Heading conversion
- Code block preservation
- Complex mixed content

All tests pass ✅

---

## Related GitHub Issues

- **Issue #12**: Show progressive tool call log during agent thinking
  - Partially addressed: Tool calls no longer clutter final response
  - Still TODO: Progressive log display (separate enhancement)

- **Issue #13**: Convert agent markdown responses to Slack-native rich text
  - ✅ FIXED: Markdown now converts to Slack mrkdwn
  - Basic Block Kit support implemented
  - Future enhancement: Full rich_text block parsing

---

## Future Enhancements

1. **Full Block Kit rich_text support** (Issue #13)
   - Currently using simple section blocks with mrkdwn
   - Could parse Markdown into full rich_text block tree for better fidelity
   - Consider using library like `slack-markdown` or `markdown-it-py`

2. **Progressive tool call logging** (Issue #12)
   - Show accumulating log of tool calls as agent works
   - Options: Block Kit blocks, thread replies, or collapsible sections
   - Decide whether to keep or delete log after final response

3. **Message splitting for long responses**
   - Slack has 4000 char limit per message
   - Could split long responses into multiple messages
   - Preserve formatting across splits

4. **Smarter code block handling**
   - Could use Slack snippets for large code blocks
   - Syntax highlighting via Block Kit

---

## Migration Notes

**No breaking changes** - this is purely additive:
- Existing bots will work without modification
- Responses are now cleaner and better formatted
- No configuration changes required

**Deployment:**
1. Pull latest code
2. Restart the bot daemon
3. Test in a dev channel first
4. No bundle.md changes needed

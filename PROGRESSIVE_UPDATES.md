# Progressive Status Updates - Implementation

This document explains the progressive message updating patterns implemented in `SlackStreamingHook`.

## The Problem

When an AI assistant performs work (calling tools, thinking), showing all activity at once creates a poor UX:
- Hard to follow what's happening
- No sense of progress
- Wall of text appearing suddenly
- Mixes tool calls, thinking, and results in a confusing way

## The Solution: Two Modes

We implement **two display modes** for tool execution, each optimized for different use cases:

### Mode 1: Single Message (Default) - "Ephemeral Status"

**Best for:** Clean UX, minimal clutter, production use

1. **Post one status message** ("🤔 Thinking...")
2. **Update it progressively** as tools execute
3. **Delete it when done** (final response appears separately)

**Pros:**
- ✅ Clean - status disappears when work completes
- ✅ Minimal thread clutter
- ✅ Follows Slack's recommended pattern

**Cons:**
- ❌ No execution history after completion
- ❌ Can't see what tools were used after response appears

### Mode 2: Multi Message - "Persistent Tool Blocks"

**Best for:** Transparency, debugging, auditing

1. **Post separate messages for each tool**
2. **Update each message** when tool completes
3. **Keep all messages visible** after completion

**Inspired by Claude Code:** Shows thinking lightly, tool calls concisely, and results as success/failure indicators.

**Pros:**
- ✅ Full execution transparency
- ✅ Can see tool history after response
- ✅ Better for debugging/auditing
- ✅ Independent tool call blocks
- ✅ Concise tool arguments (not overwhelming JSON)
- ✅ Clean success/failure indicators

**Cons:**
- ❌ More messages in thread
- ❌ More visual clutter

## Visual Comparison

### Single Message Mode (Default)

One message updates in place, then disappears:

```
[Message 1 - updates in place]
🤔 Thinking...
→ 🔄 web_search...
→ ✓ web_search
  🤔 Processing...
→ ✓ web_search
  🔄 read_file...
→ ✓ web_search
  ✓ read_file
  🤔 Processing...
→ [DELETED]

[Message 2 - final response]
Here's what I found...
```

### Multi Message Mode (Claude Code Style)

Separate persistent messages for each tool with concise formatting:

```
[Message 1 - thinking]
🤔 Thinking...

[Message 2 - tool 1]
🔧 `web_search`(query="Python asyncio")
→ ✅ `web_search`(query="Python asyncio")

[Message 3 - tool 2]
🔧 `read_file`(file_path="src/main.py")
→ ✅ `read_file`(file_path="src/main.py")

[Message 4 - final response]
Here's what I found...

[All messages remain visible]
```

**Key improvements:**
- Tool arguments shown concisely (up to 3 params, truncated if long)
- Success/failure indicators (✅/❌) instead of full result dumps
- Single-line format for easy scanning

## Usage

### Command Line

```bash
# Default: single message mode (ephemeral status)
slack-connector start

# Multi message mode (persistent tool blocks)
slack-connector start --streaming-mode multi

# With channel restriction
slack-connector start --channel C0AJBKTR0JU --streaming-mode multi
```

### Environment Variable

You can also set the mode via environment:
```bash
export SLACK_STREAMING_MODE=multi  # or "single"
```

## Implementation Details

### SlackStreamingHook

Located in `src/slack_connector/bridge.py`, this hook supports both modes:

**Shared behavior:**
1. **Tracks tool history** - maintains a list of completed and in-progress tools
2. **Posts initial "Thinking..." message**

**Single message mode:**
1. **Renders progressively** - builds a status message showing all tools
2. **Updates in place** - uses `chat.update` to modify the same message
3. **Cleans up** - deletes the status message when done

**Multi message mode:**
1. **Posts separate message per tool** - each tool gets its own message
2. **Updates each independently** - tool message updates from "Running" to "Completed"
3. **Keeps messages visible** - no cleanup, full audit trail remains

### Key Methods

- `startup()` - Posts initial "Thinking..." message
- `on_tool_start()` - Single mode: updates status | Multi mode: posts new tool message
- `on_tool_end()` - Single mode: updates status | Multi mode: updates tool message
- `_render_status()` - Builds the formatted status text (single mode only)
- `_post_tool_message()` - Posts a new tool message (multi mode only)
- `_update_tool_message()` - Updates a tool message to show completion (multi mode only)
- `cleanup()` - Deletes status message in single mode, no-op in multi mode

### Hook Registration

The bot daemon registers these hooks temporarily during execution:

```python
# In bot.py handle_message()
stream_hook = SlackStreamingHook(client, channel, reply_ts)
await stream_hook.startup()

try:
    unreg_pre = session.coordinator.hooks.register(
        "tool:pre", stream_hook.on_tool_start, priority=50
    )
    unreg_post = session.coordinator.hooks.register(
        "tool:post", stream_hook.on_tool_end, priority=50
    )
    
    response = await session.execute(prompt)
    
finally:
    # Unregister hooks and cleanup
    unreg_pre()
    unreg_post()
    await stream_hook.cleanup()
```

## Typing Indicators

**Note:** Slack bots cannot send native typing indicators (the "Bot is typing..." message). This is a Slack API limitation - only human users can trigger the typing indicator.

### Workaround: Animated Emoji

We use **animated emoji** as a visual substitute:

- ⏳ `:hourglass_flowing_sand:` - Processing/thinking (animated in Slack)
- 🔄 `:arrows_counterclockwise:` - Working/loading
- ⚙️ `:gear:` - Tool execution

The hourglass emoji **animates automatically** in Slack, providing a visual "typing" effect.

### Custom Emoji Option

Workspaces can upload **custom animated GIF emoji** for better branding:
1. Create/find an animated typing indicator GIF
2. Upload to Slack workspace as custom emoji (`:typing:`, `:loading:`, etc.)
3. Modify `bridge.py` to use your custom emoji

## Choosing a Mode

| Consideration | Single Mode | Multi Mode | Blocks Mode |
|---------------|-------------|------------|-------------|
| **Thread clutter** | Minimal ✅ | More messages ⚠️ | Most messages ⚠️⚠️ |
| **Execution transparency** | Hidden after completion | Tool audit trail ✅ | Full transparency ✅✅ |
| **Shows thinking** | No | No | Yes ✅ |
| **Best for production** | Yes ✅ | Depends | No |
| **Best for debugging** | No | Yes ✅ | Yes ✅✅ |
| **Follows Slack patterns** | Yes ✅ | Yes ✅ | Yes ✅ |
| **User experience** | Clean, polished ✅ | Technical ⚠️ | Very technical ⚠️⚠️ |
| **Educational value** | Low | Medium | High ✅ |

**Recommendation:**
- **Production/end users:** Use `single` mode (default)
- **Development/debugging:** Use `multi` mode
- **Understanding AI reasoning:** Use `blocks` mode
- **Auditing/compliance:** Use `multi` or `blocks` mode  

## Testing

Run the test script to validate the logic:

```bash
python3 /tmp/test_streaming_hook.py
```

This simulates a typical execution flow without actually calling Slack, showing the progressive message updates.

## References

- [Slack Best Practices: Long-Running Operations](https://api.slack.com/best-practices/blueprints#long-running-operations)
- Amplifier Foundation: `docs/APPLICATION_INTEGRATION_GUIDE.md`
- Implementation: `src/slack_connector/bridge.py` (SlackStreamingHook)

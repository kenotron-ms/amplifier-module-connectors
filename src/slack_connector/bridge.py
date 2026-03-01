"""
Protocol boundary implementations for Slack ↔ Amplifier.

These classes implement the Amplifier ApprovalSystem, DisplaySystem,
and StreamingHook protocols with Slack-specific behavior.

References:
- foundation:docs/APPLICATION_INTEGRATION_GUIDE.md
- Slack Bolt: https://slack.dev/bolt-python/
"""
import asyncio
import logging
from typing import Any

from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class SlackApprovalSystem:
    """
    Implements the Amplifier ApprovalSystem protocol using Slack Block Kit buttons.

    When the agent needs human approval (e.g., before a destructive operation),
    this posts an interactive message with Allow/Deny buttons and waits up to
    5 minutes for the user to respond.

    The Slack action handler in bot.py calls resolve() when a button is clicked.
    """

    def __init__(self, client: Any, channel: str, thread_ts: str | None = None) -> None:
        self.client = client
        self.channel = channel
        self.thread_ts = thread_ts
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def request_approval(
        self,
        description: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Post Block Kit approval buttons and wait for response (max 5 minutes)."""
        loop = asyncio.get_event_loop()
        future: asyncio.Future[bool] = loop.create_future()
        action_prefix = f"approval_{id(future)}"
        self._pending[action_prefix] = future

        try:
            await self.client.chat_postMessage(
                channel=self.channel,
                thread_ts=self.thread_ts,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":warning: *Approval needed*\n{description}",
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Allow"},
                                "action_id": f"{action_prefix}_allow",
                                "style": "primary",
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Deny"},
                                "action_id": f"{action_prefix}_deny",
                                "style": "danger",
                            },
                        ],
                    },
                ],
                text=f"Approval needed: {description}",
            )
            return await asyncio.wait_for(future, timeout=300.0)
        except asyncio.TimeoutError:
            logger.warning("Approval request timed out after 5 minutes — defaulting to deny")
            return False
        except SlackApiError as e:
            logger.error(f"Could not post approval request: {e}")
            return False
        finally:
            self._pending.pop(action_prefix, None)

    def resolve(self, action_id: str, approved: bool) -> None:
        """Called by the bot's action handler when a button is clicked."""
        for suffix in ("_allow", "_deny"):
            if action_id.endswith(suffix):
                prefix = action_id[: -len(suffix)]
                future = self._pending.get(prefix)
                if future and not future.done():
                    future.set_result(approved)
                return


class SlackDisplaySystem:
    """
    Implements the Amplifier DisplaySystem protocol by posting to Slack.

    Used by the orchestrator to display structured output (formatted results,
    code blocks, etc.) during session execution. The agent can also trigger
    this by using the slack_reply tool directly.
    """

    def __init__(self, client: Any, channel: str, thread_ts: str | None = None) -> None:
        self.client = client
        self.channel = channel
        self.thread_ts = thread_ts

    async def display(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Post content as a Slack message with formatting."""
        try:
            from slack_connector.formatter import format_for_slack
            
            # Format the content (clean artifacts + convert Markdown)
            formatted = format_for_slack(content, use_blocks=True)
            
            if formatted["text"]:  # Only post if there's actual content
                await self.client.chat_postMessage(
                    channel=self.channel,
                    thread_ts=self.thread_ts,
                    text=formatted["text"],
                    blocks=formatted.get("blocks"),
                    unfurl_links=False,
                    unfurl_media=False,
                )
        except SlackApiError as e:
            logger.error(f"Could not display content in Slack: {e}")


def _unwrap_tool_result(result: Any) -> Any:
    """
    Unwrap common tool result structure: {'success': True, 'output': {...}}
    Returns the inner output or the original result if not wrapped.
    """
    import json
    
    try:
        # Parse string to dict if needed
        if isinstance(result, str):
            result_obj = json.loads(result)
        elif isinstance(result, dict):
            result_obj = result
        else:
            return result
        
        # Unwrap success/output wrapper
        if "output" in result_obj:
            return result_obj["output"]
        
        return result_obj
    except (json.JSONDecodeError, AttributeError, TypeError, KeyError):
        return result


def _escape_code_block(text: str) -> str:
    """
    Escape content for safe display in Slack code blocks.
    
    Replaces triple backticks with a safe alternative to prevent
    breaking out of code fence blocks.
    """
    # Replace ``` with `` ` (with space) to prevent breaking code fence
    return text.replace("```", "`` `")


def _format_tool_invocation(tool_name: str, args: dict[str, Any]) -> str:
    """
    Format tool invocation showing only what users care about.
    
    Design: Show tool name + key argument with appropriate icon.
    Optimized for scannability, not technical completeness.
    
    Returns multi-line string suitable for Slack message.
    """
    if not args:
        return f"🔧 `{tool_name}`"
    
    # File operations - show file path
    if tool_name in ("read_file", "write_file", "edit_file"):
        file_path = args.get("file_path", "")
        if file_path:
            return f"🔧 `{tool_name}`\n📄 {file_path}"
        return f"🔧 `{tool_name}`"
    
    # Bash - show command
    if tool_name == "bash":
        command = args.get("command", "")
        if command:
            # Truncate very long commands
            if len(command) > 200:
                command = command[:197] + "..."
            return f"🔧 `{tool_name}`\n$ {command}"
        return f"🔧 `{tool_name}`"
    
    # Grep - show pattern and path
    if tool_name == "grep":
        pattern = args.get("pattern", "")
        path = args.get("path", ".")
        if pattern:
            return f"🔧 `{tool_name}`\n🔍 \"{pattern}\" in {path}"
        return f"🔧 `{tool_name}`"
    
    # Glob - show pattern and path
    if tool_name == "glob":
        pattern = args.get("pattern", "")
        path = args.get("path", ".")
        if pattern:
            return f"🔧 `{tool_name}`\n📁 {pattern} in {path}"
        return f"🔧 `{tool_name}`"
    
    # Web fetch - show URL
    if tool_name == "web_fetch":
        url = args.get("url", "")
        if url:
            # Truncate very long URLs
            if len(url) > 150:
                url = url[:147] + "..."
            return f"🔧 `{tool_name}`\n🌐 {url}"
        return f"🔧 `{tool_name}`"
    
    # Web search - show query
    if tool_name == "web_search":
        query = args.get("query", "")
        if query:
            return f"🔧 `{tool_name}`\n🔍 \"{query}\""
        return f"🔧 `{tool_name}`"
    
    # Slack reply - meta tool
    if tool_name == "slack_reply":
        return f"🔧 `{tool_name}`\n💬 [sending intermediate message]"
    
    # Todo list - show action and task
    if tool_name == "todo_list":
        action = args.get("action", "")
        task = args.get("task", "")
        if action and task:
            # Truncate long task descriptions
            if len(task) > 100:
                task = task[:97] + "..."
            return f"🔧 `{tool_name}`\n✅ {action} \"{task}\""
        elif action:
            return f"🔧 `{tool_name}`\n✅ {action}"
        return f"🔧 `{tool_name}`"
    
    # Generic fallback - just show tool name
    return f"🔧 `{tool_name}`"


def _format_tool_result(tool_name: str, result: Any, args: dict[str, Any]) -> str:
    """
    Format tool result showing outcome, not raw data.
    
    Design: Show what happened (bytes written, matches found), not the data itself.
    For diffs: show FULL content, only truncate individual long lines.
    
    Returns formatted result string suitable for Slack message.
    """
    # Unwrap common result structure
    unwrapped = _unwrap_tool_result(result)
    
    # File operations
    if tool_name == "read_file":
        if isinstance(unwrapped, dict):
            content = unwrapped.get("content", "")
            if content:
                line_count = len(content.split('\n'))
                return f"✓ {line_count} lines read"
            # Try to get file size or other metrics
            total_lines = unwrapped.get("total_lines")
            if total_lines:
                return f"✓ {total_lines} lines read"
        return "✓ file read"
    
    if tool_name == "write_file":
        if isinstance(unwrapped, dict):
            bytes_written = unwrapped.get("bytes_written")
            if bytes_written:
                return f"✓ {bytes_written:,} bytes written"
        return "✓ file written"
    
    if tool_name == "edit_file":
        if isinstance(unwrapped, dict):
            replacements = unwrapped.get('replacements_made', 0)
            bytes_written = unwrapped.get('bytes_written', 0)
            
            # Get the old and new strings from the original args
            old_str = args.get("old_string", "")
            new_str = args.get("new_string", "")
            
            if old_str and new_str:
                # Show FULL diff - don't limit number of lines
                # Only truncate individual lines that are too long
                old_lines = old_str.split('\n')
                new_lines = new_str.split('\n')
                
                diff_lines = []
                diff_lines.append(f"✓ {replacements} replacement(s), {bytes_written:,} bytes")
                diff_lines.append("")  # Blank line for readability
                
                # Show ALL removed lines (truncate individual long lines)
                for line in old_lines:
                    if len(line) > 100:
                        diff_lines.append(f"- {line[:97]}...")
                    else:
                        diff_lines.append(f"- {line}")
                
                diff_lines.append("")  # Separator
                
                # Show ALL added lines (truncate individual long lines)
                for line in new_lines:
                    if len(line) > 100:
                        diff_lines.append(f"+ {line[:97]}...")
                    else:
                        diff_lines.append(f"+ {line}")
                
                return '\n'.join(diff_lines)
            else:
                return f"✓ {replacements} replacement(s), {bytes_written:,} bytes"
        return "✓ file edited"
    
    # Search/find operations
    if tool_name == "grep":
        if isinstance(unwrapped, dict):
            total_matches = unwrapped.get("total_matches", 0)
            files = unwrapped.get("files", [])
            if total_matches and files:
                file_count = len(files)
                return f"✓ {total_matches} matches in {file_count} files"
            elif total_matches:
                return f"✓ {total_matches} matches"
        return "✓ search complete"
    
    if tool_name == "glob":
        if isinstance(unwrapped, dict):
            total_files = unwrapped.get("total_files", 0)
            if total_files:
                return f"✓ {total_files} files found"
            files = unwrapped.get("files", [])
            if files:
                return f"✓ {len(files)} files found"
        return "✓ search complete"
    
    # Bash - show output (first ~10 lines)
    if tool_name == "bash":
        if isinstance(unwrapped, dict):
            stdout = unwrapped.get("stdout", "")
            stderr = unwrapped.get("stderr", "")
            returncode = unwrapped.get("returncode", 0)
            
            # Prefer stdout, fall back to stderr
            output = stdout if stdout else stderr
            
            if output:
                lines = output.split('\n')
                # Show first 10 lines
                preview_lines = lines[:10]
                result_str = '\n'.join(preview_lines)
                
                # Add truncation indicator if needed
                if len(lines) > 10:
                    result_str += f"\n... ({len(lines) - 10} more lines)"
                
                # Add return code if non-zero
                if returncode != 0:
                    result_str = f"⚠️ exit code {returncode}\n{result_str}"
                else:
                    result_str = f"✓ exit code 0\n{result_str}"
                
                return result_str
            elif returncode == 0:
                return "✓ exit code 0 (no output)"
            else:
                return f"⚠️ exit code {returncode}"
        return "✓ command executed"
    
    # Web operations
    if tool_name == "web_fetch":
        if isinstance(unwrapped, dict):
            total_bytes = unwrapped.get("total_bytes")
            returned_bytes = unwrapped.get("returned_bytes")
            if total_bytes:
                kb = total_bytes / 1024
                return f"✓ {kb:.1f}KB fetched"
            elif returned_bytes:
                kb = returned_bytes / 1024
                return f"✓ {kb:.1f}KB fetched"
        return "✓ fetched"
    
    if tool_name == "web_search":
        if isinstance(unwrapped, dict):
            results = unwrapped.get("results", [])
            if results:
                return f"✓ {len(results)} results"
        return "✓ search complete"
    
    # Platform tools
    if tool_name == "slack_reply":
        return "✓ sent"
    
    if tool_name == "todo_list":
        action = args.get("action", "")
        if action == "add":
            return "✓ task added"
        elif action == "complete":
            return "✓ task completed"
        elif action == "delete":
            return "✓ task deleted"
        elif action == "list":
            # Could show task count if available in result
            return "✓ listed tasks"
        return "✓ done"
    
    # Generic fallback - try to show something useful
    if isinstance(unwrapped, dict):
        # Look for common success indicators
        if unwrapped.get("success"):
            return "✓ success"
    
    return "✓ complete"


class SlackStreamingHook:
    """
    Progressive message updater that shows live tool activity during agent execution.

    Supports three modes:
    1. SINGLE (default): Updates one status message in place, then deletes it
    2. MULTI: Posts separate persistent messages for each tool execution
    3. BLOCKS: Posts separate messages for each content block (thinking, tool_use, tool_result, text)

    SINGLE mode (ephemeral status):
        ✓ Clean - status disappears when done
        ✓ Less clutter in thread
        ✗ No execution history visible after completion

    MULTI mode (persistent tool blocks):
        ✓ Full execution transparency - see what tools ran
        ✓ Independent messages for tool calls vs content
        ✓ Better for debugging/auditing
        ✗ More messages in thread

    BLOCKS mode (full content streaming):
        ✓ Maximum transparency - see every block (thinking, tools, text)
        ✓ Separate messages for thinking, tool execution, intermediate text
        ✓ Best for understanding AI reasoning process
        ✗ Most messages in thread

    Lifecycle:
        hook = SlackStreamingHook(client, channel, thread_ts, mode="single")
        await hook.startup()
        try:
            response = await session.execute(text)
        finally:
            await hook.cleanup()
    """

    def __init__(
        self, 
        client: Any, 
        channel: str, 
        thread_ts: str,
        mode: str = "single"  # "single", "multi", or "blocks"
    ) -> None:
        self.client = client
        self.channel = channel
        self.thread_ts = thread_ts
        self.mode = mode
        self._status_ts: str | None = None
        # Track tool execution history for progressive updates
        self._tool_history: list[dict[str, Any]] = []
        self._current_tool: str | None = None
        # For multi/blocks mode: track individual message timestamps
        self._tool_messages: dict[str, str] = {}  # tool_id -> message_ts
        self._thinking_blocks: dict[int, str] = {}  # block_index -> message_ts

    async def startup(self) -> None:
        """Post the initial thinking indicator."""
        try:
            # Note: Slack bots cannot send native typing indicators (user_typing event)
            # This is a visual workaround using an animated emoji or text
            result = await self.client.chat_postMessage(
                channel=self.channel,
                thread_ts=self.thread_ts,
                text=":hourglass_flowing_sand: ...",  # Animated hourglass simulates typing
            )
            self._status_ts = result["ts"]
        except SlackApiError as e:
            logger.debug(f"Could not post streaming indicator: {e}")

    async def on_tool_start(self, event: str, data: dict[str, Any]) -> None:
        """Update status when a tool starts - show it as in-progress."""
        tool_name = data.get("name", data.get("tool_name", "tool"))
        tool_id = str(id(data))  # Unique ID for this tool invocation
        self._current_tool = tool_name
        
        # Add to history as in-progress
        tool_entry = {
            "id": tool_id,
            "name": tool_name,
            "status": "running",
            "data": data,
        }
        self._tool_history.append(tool_entry)
        
        if self.mode == "multi":
            # Post a new message for this tool
            await self._post_tool_message(tool_entry)
        else:
            # Update the single status message
            await self._render_status()

    async def on_tool_end(self, event: str, data: dict[str, Any]) -> None:
        """Update status when a tool finishes - mark it as complete."""
        # Mark the most recent in-progress tool as complete
        for item in reversed(self._tool_history):
            if item["status"] == "running":
                item["status"] = "complete"
                item["end_data"] = data
                
                if self.mode == "multi":
                    # Update the tool's individual message
                    await self._update_tool_message(item)
                break
        
        self._current_tool = None
        
        if self.mode == "single":
            await self._render_status()

    async def _render_status(self) -> None:
        """Build and update the progressive status message."""
        if not self._status_ts:
            return
        
        lines = []
        has_running = False
        
        # Show completed tools with checkmarks
        for item in self._tool_history:
            if item["status"] == "complete":
                lines.append(f"✓ `{item['name']}`")
            elif item["status"] == "running":
                lines.append(f":arrows_counterclockwise: `{item['name']}`...")
                has_running = True
        
        # If no tools yet, show thinking (animated indicator)
        if not lines:
            text = ":hourglass_flowing_sand: _thinking..._"
        else:
            # ALWAYS show a status indicator at the end to indicate ongoing work
            # This makes it clear when the bot is still processing vs done
            if has_running:
                # Tools are actively running
                text = "\n".join(lines)
            else:
                # All tools complete, but still formulating response
                lines.append(":hourglass_flowing_sand: _formulating response..._")
                text = "\n".join(lines)
        
        await self._update(text)

    async def _update(self, text: str) -> None:
        """Update the status message in place."""
        if not self._status_ts:
            return
        try:
            await self.client.chat_update(
                channel=self.channel,
                ts=self._status_ts,
                text=text,
            )
        except SlackApiError as e:
            logger.debug(f"Could not update streaming indicator: {e}")

    async def _post_tool_message(self, tool_entry: dict[str, Any]) -> None:
        """Post a new message for a tool execution (multi-message mode)."""
        tool_name = tool_entry["name"]
        tool_id = tool_entry["id"]
        data = tool_entry.get("data", {})
        
        # Extract arguments from tool_input (Amplifier's tool call structure)
        args = data.get("tool_input", {})
        
        # Format invocation with new formatter (shows key args only)
        text = _format_tool_invocation(tool_name, args)
        
        try:
            result = await self.client.chat_postMessage(
                channel=self.channel,
                thread_ts=self.thread_ts,
                text=text,
            )
            self._tool_messages[tool_id] = result["ts"]
        except SlackApiError as e:
            logger.debug(f"Could not post tool message: {e}")

    async def _update_tool_message(self, tool_entry: dict[str, Any]) -> None:
        """Update a tool's message to show completion (multi-message mode)."""
        tool_name = tool_entry["name"]
        tool_id = tool_entry["id"]
        msg_ts = self._tool_messages.get(tool_id)
        
        if not msg_ts:
            return
        
        data = tool_entry.get("data", {})
        end_data = tool_entry.get("end_data", {})
        
        # Extract arguments from tool_input
        args = data.get("tool_input", {})
        
        # Check for errors in result - try multiple possible keys
        result = (
            end_data.get("result") or 
            end_data.get("output") or 
            end_data.get("tool_output") or
            end_data.get("content")
        )
        error = end_data.get("error")
        
        # Build updated message
        if error:
            # Error case - show invocation + error message
            invocation = _format_tool_invocation(tool_name, args)
            # Replace the tool icon/emoji with error indicator
            invocation = invocation.replace("🔧", "❌")
            text = f"{invocation}\n_{str(error)[:200]}_"
        else:
            # Success - show invocation + result
            invocation = _format_tool_invocation(tool_name, args)
            # Replace the tool icon with success indicator
            invocation = invocation.replace("🔧", "✅")
            
            # Format the result using new formatter
            result_str = _format_tool_result(tool_name, result, args)
            
            # Combine invocation and result
            # For results with newlines (like diffs), use code block
            if '\n' in result_str:
                # Escape any triple backticks in the result to prevent breaking code fence
                escaped_result = _escape_code_block(result_str)
                
                if tool_name == "edit_file":
                    # Edit file diffs - use diff syntax highlighting
                    text = f"{invocation}\n```diff\n{escaped_result}\n```"
                elif tool_name == "bash":
                    # Bash output - use code block for readability
                    text = f"{invocation}\n```\n{escaped_result}\n```"
                else:
                    # Other multi-line results - use plain code block
                    text = f"{invocation}\n```\n{escaped_result}\n```"
            else:
                # Single-line results - just append
                text = f"{invocation}\n{result_str}"
        
        try:
            await self.client.chat_update(
                channel=self.channel,
                ts=msg_ts,
                text=text,
            )
        except SlackApiError as e:
            logger.debug(f"Could not update tool message: {e}")

    async def on_content_block_start(self, event: str, data: dict[str, Any]) -> None:
        """Handle content block start (blocks mode only)."""
        if self.mode != "blocks":
            return
        
        block_type = data.get("block_type")
        block_index = data.get("block_index")
        
        if block_type in {"thinking", "reasoning"}:
            # Post thinking indicator (lighter treatment)
            try:
                result = await self.client.chat_postMessage(
                    channel=self.channel,
                    thread_ts=self.thread_ts,
                    text="_thinking..._",  # Italic = lighter treatment
                )
                if block_index is not None:
                    self._thinking_blocks[block_index] = result["ts"]
            except SlackApiError as e:
                logger.debug(f"Could not post thinking block: {e}")
    
    async def on_content_block_end(self, event: str, data: dict[str, Any]) -> None:
        """Handle content block end (blocks mode only)."""
        if self.mode != "blocks":
            return
        
        block_index = data.get("block_index")
        block = data.get("block", {})
        block_type = block.get("type")
        
        # Update thinking block with actual content (collapsed/light treatment)
        if block_type in {"thinking", "reasoning"} and block_index in self._thinking_blocks:
            thinking_text = (
                block.get("thinking", "")
                or block.get("text", "")
                or str(block)
            )
            
            if thinking_text:
                msg_ts = self._thinking_blocks[block_index]
                try:
                    # Show just a preview in italic (light treatment)
                    preview = thinking_text[:100].replace("\n", " ")
                    if len(thinking_text) > 100:
                        preview += "..."
                    await self.client.chat_update(
                        channel=self.channel,
                        ts=msg_ts,
                        text=f"_💭 {preview}_",
                    )
                except SlackApiError as e:
                    logger.debug(f"Could not update thinking block: {e}")
        
        # Post intermediate text blocks (text that appears before tool calls)
        elif block_type == "text":
            text = block.get("text", "").strip()
            if text:
                try:
                    await self.client.chat_postMessage(
                        channel=self.channel,
                        thread_ts=self.thread_ts,
                        text=text,
                    )
                except SlackApiError as e:
                    logger.debug(f"Could not post text block: {e}")

    async def cleanup(self) -> None:
        """Update status to show completion, then delete (single mode only)."""
        if self.mode == "single" and self._status_ts:
            try:
                # First, update to show we're done (brief visual confirmation)
                lines = []
                for item in self._tool_history:
                    if item["status"] == "complete":
                        lines.append(f"✓ `{item['name']}`")
                
                if lines:
                    lines.append("✓ _complete_")
                    await self._update("\n".join(lines))
                    # Keep the "complete" message visible for a moment
                    await asyncio.sleep(0.5)
                
                # Then delete the status message
                await self.client.chat_delete(
                    channel=self.channel,
                    ts=self._status_ts,
                )
                self._status_ts = None
            except SlackApiError as e:
                logger.debug(f"Could not clean up streaming indicator: {e}")
        # In multi/blocks mode, we keep the messages visible

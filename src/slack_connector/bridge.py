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


def _format_tool_args(args: dict[str, Any]) -> str:
    """
    Format tool arguments in a concise, readable way.
    
    Inspired by Claude Code - show just enough to give confidence,
    not overwhelming JSON dumps.
    """
    if not args:
        return ""
    
    # Show up to 3 key arguments concisely
    parts = []
    shown = 0
    max_shown = 3
    
    for key, value in args.items():
        if shown >= max_shown:
            remaining = len(args) - shown
            parts.append(f"... +{remaining} more")
            break
        
        # Format value concisely
        if isinstance(value, str):
            # Truncate long strings
            if len(value) > 50:
                value_str = f'"{value[:47]}..."'
            else:
                value_str = f'"{value}"'
        elif isinstance(value, (list, dict)):
            # Just show type and length
            if isinstance(value, list):
                value_str = f"[{len(value)} items]"
            else:
                value_str = f"{{{len(value)} keys}}"
        else:
            value_str = str(value)
        
        parts.append(f"{key}={value_str}")
        shown += 1
    
    return ", ".join(parts)


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
        
        # Show completed tools with checkmarks
        for item in self._tool_history:
            if item["status"] == "complete":
                lines.append(f"✓ `{item['name']}`")
            elif item["status"] == "running":
                lines.append(f":arrows_counterclockwise: `{item['name']}`...")
        
        # If no tools yet, show thinking (animated indicator)
        if not lines:
            text = ":hourglass_flowing_sand: ..."
        else:
            # Add a "Processing..." line if we're between tools (animated indicator)
            if self._current_tool is None:
                lines.append(":hourglass_flowing_sand: ...")
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
        
        # Format args concisely (Claude Code style)
        args_str = _format_tool_args(args) if args else ""
        
        # Build the message - concise, single line
        if args_str:
            text = f"🔧 `{tool_name}`({args_str})"
        else:
            text = f"🔧 `{tool_name}`()"
        
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
        
        # Extract arguments from tool_input (same as in _post_tool_message)
        args = data.get("tool_input", {})
        args_str = _format_tool_args(args) if args else ""
        
        # Check for errors in result - try multiple possible keys
        result = (
            end_data.get("result") or 
            end_data.get("output") or 
            end_data.get("tool_output") or
            end_data.get("content")
        )
        error = end_data.get("error")
        
        # Build updated message - show success/failure with result preview
        if error:
            if args_str:
                text = f"❌ `{tool_name}`({args_str})\n_{str(error)[:100]}_"
            else:
                text = f"❌ `{tool_name}`()\n_{str(error)[:100]}_"
        else:
            # Success - show checkmark with result preview (first few lines)
            result_preview = ""
            if result:
                result_str = str(result)
                # Show first 2-3 lines or ~150 chars
                lines = result_str.split('\n')
                preview_lines = lines[:3]
                result_preview = '\n'.join(preview_lines)
                if len(result_preview) > 150:
                    result_preview = result_preview[:147] + "..."
                elif len(lines) > 3:
                    result_preview += "\n..."
            
            if args_str:
                if result_preview:
                    text = f"✅ `{tool_name}`({args_str})\n```\n{result_preview}\n```"
                else:
                    text = f"✅ `{tool_name}`({args_str})"
            else:
                if result_preview:
                    text = f"✅ `{tool_name}`()\n```\n{result_preview}\n```"
                else:
                    text = f"✅ `{tool_name}`()"
        
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
        """Delete the status indicator message (single mode only)."""
        if self.mode == "single" and self._status_ts:
            try:
                await self.client.chat_delete(
                    channel=self.channel,
                    ts=self._status_ts,
                )
                self._status_ts = None
            except SlackApiError as e:
                logger.debug(f"Could not clean up streaming indicator: {e}")
        # In multi/blocks mode, we keep the messages visible

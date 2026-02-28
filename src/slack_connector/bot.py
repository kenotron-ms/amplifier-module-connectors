"""
Core bridge: Slack Socket Mode ↔ Amplifier sessions.

Implements Pattern B (Per-Conversation Sessions) from
foundation:docs/APPLICATION_INTEGRATION_GUIDE.md.

Session model:
- SessionManager: handles bundle prep + session caching + locks
- AmplifierSession: one per Slack channel, lazily created, cached
- asyncio.Lock: one per conversation, ensures ordered execution

Session IDs are stable ("slack-{channel_id}") so sessions persist
across bot restarts when using context-persistent.
"""
import asyncio
import logging
import re
from typing import Any

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError

from connector_core import SessionManager

logger = logging.getLogger(__name__)


class SlackAmplifierBot:
    """
    Bridges Slack Socket Mode to Amplifier sessions.

    Usage:
        bot = SlackAmplifierBot(bundle_path="./bundle.md", ...)
        await bot.run()  # blocks until interrupted
    """

    def __init__(
        self,
        bundle_path: str,
        slack_app_token: str,
        slack_bot_token: str,
        allowed_channel: str | None = None,
        streaming_mode: str = "single",  # "single" or "multi"
    ) -> None:
        self.bundle_path = bundle_path
        self.slack_app_token = slack_app_token
        self.slack_bot_token = slack_bot_token
        self.allowed_channel = allowed_channel
        self.streaming_mode = streaming_mode

        # Amplifier state - now managed by SessionManager
        self.session_manager = SessionManager(bundle_path)
        self._approval_systems: dict[str, Any] = {}  # conv_id -> SlackApprovalSystem

        # Slack state
        self.bolt_app: AsyncApp | None = None
        self.handler: AsyncSocketModeHandler | None = None
        self.bot_user_id: str | None = None
        self._active_threads: set[str] = set()  # Track threads where bot was mentioned

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Load bundle (once) and initialize Slack Bolt app."""
        # Initialize SessionManager (loads and prepares bundle)
        await self.session_manager.initialize()

        self.bolt_app = AsyncApp(token=self.slack_bot_token)
        self._register_handlers()

        try:
            auth = await self.bolt_app.client.auth_test()
            self.bot_user_id = auth.get("user_id")
            bot_name = auth.get("user", "unknown")
            logger.info(f"Authenticated as @{bot_name} ({self.bot_user_id})")
        except SlackApiError as e:
            logger.warning(f"Could not resolve bot user ID (loop prevention may not work): {e}")

    async def shutdown(self) -> None:
        """Gracefully disconnect and close all Amplifier sessions."""
        logger.info("Shutting down Slack connector...")

        if self.handler:
            try:
                await self.handler.close_async()
            except Exception:
                pass

        # Close all sessions via SessionManager
        await self.session_manager.close_all()

        self._approval_systems.clear()
        self._active_threads.clear()
        logger.info("Shutdown complete")

    async def run(self) -> None:
        """Start the bot and block until stopped."""
        await self.startup()

        channel_info = (
            f" (channel: {self.allowed_channel})"
            if self.allowed_channel
            else " (all channels + @mentions)"
        )
        logger.info(f"Slack connector running{channel_info}")

        self.handler = AsyncSocketModeHandler(
            app=self.bolt_app,
            app_token=self.slack_app_token,
        )

        try:
            await self.handler.start_async()
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            await self.shutdown()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _is_bot_mentioned(self, text: str) -> bool:
        """Check if the bot is mentioned in the message text."""
        if not self.bot_user_id or not text:
            return False
        # Slack mentions look like <@U0123456789>
        mention_pattern = f"<@{self.bot_user_id}>"
        return mention_pattern in text

    def _get_thread_id(self, channel: str, thread_ts: str | None) -> str:
        """Get a unique identifier for a thread."""
        if thread_ts:
            return f"{channel}-{thread_ts}"
        return channel

    def _conversation_id(self, channel: str, thread_ts: str | None = None) -> str:
        """
        Stable session key for Amplifier sessions.
        
        Each unique thread gets its own continuous conversation session.
        If thread_ts is None, falls back to channel-wide session (for backwards compatibility).
        
        This ensures that conversations in Slack threads maintain full context
        and never have fragmented/half conversations.
        """
        if thread_ts:
            return f"slack-{channel}-{thread_ts}"
        return f"slack-{channel}"

    async def _get_or_create_session(
        self,
        channel: str,
        thread_ts: str | None,
        reply_ts: str,
    ) -> tuple[Any, asyncio.Lock]:
        """Lazily create or retrieve the session and lock for a conversation."""
        conv_id = self._conversation_id(channel, thread_ts)

        # Create approval system if needed (track for this conversation)
        if conv_id not in self._approval_systems:
            from slack_connector.bridge import SlackApprovalSystem
            client = self.bolt_app.client
            approval = SlackApprovalSystem(client, channel, reply_ts)
            self._approval_systems[conv_id] = approval
        else:
            approval = self._approval_systems[conv_id]

        # Create SlackReplyTool for this conversation
        platform_tool = None
        try:
            from tool_slack_reply import SlackReplyTool  # type: ignore[import]
            client = self.bolt_app.client
            platform_tool = SlackReplyTool(client=client, channel=channel, thread_ts=reply_ts)
        except Exception as e:
            logger.warning(f"Could not create slack_reply tool: {e}")

        # Delegate to SessionManager
        # NOTE: We do NOT pass a display_system here to avoid duplicate messages.
        # The orchestrator would use display_system.display() to post the final
        # response, but we handle that manually in handle_message() after formatting.
        session, lock = await self.session_manager.get_or_create_session(
            conversation_id=conv_id,
            approval_system=approval,
            display_system=None,  # Explicitly None to prevent duplicate posting
            platform_tool=platform_tool,
        )

        return session, lock

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def handle_message(
        self,
        channel: str,
        user: str,
        text: str,
        ts: str,
        thread_ts: str | None = None,
    ) -> None:
        """Route a Slack message through an Amplifier session and reply."""
        if not text or not text.strip():
            return

        client = self.bolt_app.client
        # Always reply in a thread (start one if top-level message)
        reply_ts = thread_ts or ts

        # Use reply_ts for session identification to ensure each thread has its own session
        session, lock = await self._get_or_create_session(channel, reply_ts, reply_ts)

        # Show loading reaction
        try:
            await client.reactions_add(channel=channel, timestamp=ts, name="loading")
        except SlackApiError:
            pass

        async with lock:
            from slack_connector.bridge import SlackStreamingHook

            # Progressive status updates: Show tool execution in real-time
            # - "single" mode: One ephemeral status message (clean, disappears when done)
            # - "multi" mode: Separate persistent messages per tool (full transparency)
            # See: PROGRESSIVE_UPDATES.md for details
            stream_hook = SlackStreamingHook(client, channel, reply_ts, mode=self.streaming_mode)
            await stream_hook.startup()

            unreg_pre = None
            unreg_post = None

            unreg_content_start = None
            unreg_content_end = None
            
            try:
                # Register ephemeral streaming hooks (best-effort)
                # These fire on tool:pre and tool:post events to update the status message
                try:
                    unreg_pre = session.coordinator.hooks.register(
                        "tool:pre", stream_hook.on_tool_start, priority=50
                    )
                    unreg_post = session.coordinator.hooks.register(
                        "tool:post", stream_hook.on_tool_end, priority=50
                    )
                    
                    # For blocks mode, also register content block hooks
                    if self.streaming_mode == "blocks":
                        unreg_content_start = session.coordinator.hooks.register(
                            "content_block:start", stream_hook.on_content_block_start, priority=50
                        )
                        unreg_content_end = session.coordinator.hooks.register(
                            "content_block:end", stream_hook.on_content_block_end, priority=50
                        )
                except Exception as e:
                    logger.debug(f"Streaming hooks not available: {e}")

                # Execute through Amplifier
                prompt = f"<@{user}>: {text.strip()}"
                response = await session.execute(prompt)

                # Format and post the final response
                if response and response.strip():
                    from slack_connector.formatter import format_for_slack
                    
                    # Format response: clean artifacts + convert Markdown to Slack format
                    formatted = format_for_slack(response, use_blocks=True)
                    
                    if formatted["text"]:  # Only post if there's actual content
                        await client.chat_postMessage(
                            channel=channel,
                            thread_ts=reply_ts,
                            text=formatted["text"],
                            blocks=formatted.get("blocks"),
                            unfurl_links=False,
                            unfurl_media=False,
                        )

            except Exception as e:
                logger.exception(f"Error handling message from {user} in {channel}")
                try:
                    await client.chat_postMessage(
                        channel=channel,
                        thread_ts=reply_ts,
                        text=f":warning: An error occurred: {e}",
                    )
                except SlackApiError:
                    pass

            finally:
                # Unregister ephemeral hooks
                for unreg in (unreg_pre, unreg_post, unreg_content_start, unreg_content_end):
                    if unreg is not None:
                        try:
                            unreg()
                        except Exception:
                            pass

                await stream_hook.cleanup()

                try:
                    await client.reactions_remove(channel=channel, timestamp=ts, name="loading")
                except SlackApiError:
                    pass

    # ------------------------------------------------------------------
    # Slack event / action handlers
    # ------------------------------------------------------------------

    def _register_handlers(self) -> None:
        """Register all event and action handlers on self.bolt_app."""
        app = self.bolt_app

        @app.event("message")
        async def on_message(event: dict, say: Any) -> None:
            # Ignore bot messages (prevent infinite loops)
            if event.get("bot_id") or event.get("subtype") == "bot_message":
                return
            if self.bot_user_id and event.get("user") == self.bot_user_id:
                return
            # Ignore edits, deletions, file shares, etc.
            if event.get("subtype"):
                return

            channel = event.get("channel", "")
            text = event.get("text", "")
            ts = event.get("ts", "")
            thread_ts = event.get("thread_ts")

            # If restricted to a specific channel, only respond there
            if self.allowed_channel and channel != self.allowed_channel:
                return

            # Determine the thread identifier (for tracking if bot was mentioned)
            # If thread_ts exists, this is a threaded message
            # Otherwise, it's a top-level message (use ts as the thread anchor)
            is_mentioned = self._is_bot_mentioned(text)
            
            if thread_ts:
                # This is a reply in an existing thread
                thread_id = self._get_thread_id(channel, thread_ts)
                is_active_thread = thread_id in self._active_threads
                
                # Respond if bot was mentioned OR thread is already active
                if not (is_mentioned or is_active_thread):
                    return
                    
                # Mark thread as active if bot is mentioned
                if is_mentioned:
                    self._active_threads.add(thread_id)
            else:
                # This is a top-level message (not in a thread)
                # Only respond if bot is mentioned
                if not is_mentioned:
                    return
                
                # Mark this thread as active (bot's reply will create a thread anchored to ts)
                thread_id = self._get_thread_id(channel, ts)
                self._active_threads.add(thread_id)

            await self.handle_message(
                channel=channel,
                user=event.get("user", "unknown"),
                text=text,
                ts=ts,
                thread_ts=thread_ts,
            )

        @app.event("app_mention")
        async def on_mention(event: dict) -> None:
            # @mentions always get a response, regardless of channel restriction
            if event.get("bot_id"):
                return
            if self.bot_user_id and event.get("user") == self.bot_user_id:
                return
            ts = event.get("ts", "")
            # Each @mention owns its own thread+session.
            # If already inside a thread, use that thread ts so follow-up
            # messages in the same thread keep the same session.
            # If top-level, anchor to this message ts — the reply starts a
            # new thread, and on_message follow-ups will match via thread_ts.
            effective_thread_ts = event.get("thread_ts") or ts
            channel = event.get("channel", "")
            
            # Mark this thread as active (bot was mentioned)
            thread_id = self._get_thread_id(channel, effective_thread_ts)
            self._active_threads.add(thread_id)
            
            await self.handle_message(
                channel=channel,
                user=event.get("user", "unknown"),
                text=event.get("text", ""),
                ts=ts,
                thread_ts=effective_thread_ts,
            )

        @app.action(re.compile(r"approval_\d+_(allow|deny)"))
        async def on_approval(ack: Any, body: dict) -> None:
            """Handle Block Kit approval button clicks."""
            await ack()
            action = body.get("actions", [{}])[0]
            action_id = action.get("action_id", "")
            approved = action_id.endswith("_allow")

            # Resolve the channel from the action body
            channel = body.get("channel", {}).get("id", "")
            # Get thread_ts from the message, or use the message ts itself if it's a thread root
            msg = body.get("message", {})
            msg_thread_ts = msg.get("thread_ts") or msg.get("ts")
            conv_id = self._conversation_id(channel, msg_thread_ts)

            approval_system = self._approval_systems.get(conv_id)
            if approval_system:
                approval_system.resolve(action_id, approved)

        @app.error
        async def on_error(error: Exception) -> None:
            logger.error(f"Bolt app error: {error}", exc_info=error)

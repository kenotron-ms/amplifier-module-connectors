"""
Core bridge: Microsoft Teams Bot Framework ↔ Amplifier sessions.

Implements Pattern B (Per-Conversation Sessions) similar to Slack connector.

Session model:
- SessionManager: handles bundle prep + session caching + locks
- AmplifierSession: one per Teams conversation, lazily created, cached
- asyncio.Lock: one per conversation, ensures ordered execution

Session IDs are stable ("teams-{conversation_id}") so sessions persist
across bot restarts when using context-persistent.
"""

import asyncio
import logging
from typing import Any, Optional

from connector_core import SessionManager, UnifiedMessage
from teams_connector.adapter import TeamsAdapter

logger = logging.getLogger(__name__)


class TeamsAmplifierBot:
    """
    Bridges Microsoft Teams Bot Framework to Amplifier sessions.

    Usage:
        bot = TeamsAmplifierBot(
            bundle_path="./bundle.md",
            app_id="...",
            app_password="..."
        )
        await bot.run()  # blocks until interrupted
    """

    def __init__(self, bundle_path: str, app_id: str, app_password: str, port: int = 3978) -> None:
        self.bundle_path = bundle_path
        self.app_id = app_id
        self.app_password = app_password
        self.port = port

        # Amplifier state - managed by SessionManager
        self.session_manager = SessionManager(bundle_path)

        # Teams state
        self.adapter: Optional[TeamsAdapter] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Initialize SessionManager and Teams adapter."""
        # Initialize SessionManager (loads and prepares bundle)
        await self.session_manager.initialize()

        # Initialize Teams adapter
        self.adapter = TeamsAdapter(
            app_id=self.app_id, app_password=self.app_password, port=self.port
        )
        await self.adapter.startup()

        logger.info("Teams bot started successfully")

    async def shutdown(self) -> None:
        """Gracefully disconnect and close all Amplifier sessions."""
        logger.info("Shutting down Teams connector...")

        if self.adapter:
            await self.adapter.shutdown()

        # Close all sessions via SessionManager
        await self.session_manager.close_all()

        logger.info("Shutdown complete")

    async def run(self) -> None:
        """Start the bot and block until stopped."""
        await self.startup()

        logger.info(f"Teams bot listening on port {self.port}")
        logger.info("Bot is ready to receive messages")

        try:
            # Start listening for messages
            await self.adapter.listen(self.handle_message)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.shutdown()

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def handle_message(self, msg: UnifiedMessage) -> None:
        """
        Route a Teams message through an Amplifier session and reply.

        Args:
            msg: UnifiedMessage from TeamsAdapter
        """
        if not msg.text or not msg.text.strip():
            return

        # Get or create session for this conversation
        session, lock = await self._get_or_create_session(msg)

        # Prevent concurrent execution for same conversation
        async with lock:
            try:
                # Add "thinking" reaction
                if self.adapter:
                    await self.adapter.add_reaction(msg.channel, msg.message_id, "eyes")

                # Execute through Amplifier session
                prompt = f"<@{msg.user}>: {msg.text}"
                response = await session.execute(prompt)

                # Post response
                if self.adapter and response.text:
                    await self.adapter.send_message(
                        channel=msg.channel,
                        text=response.text,
                        thread_id=msg.thread_id or msg.message_id,
                    )

                # Add "done" reaction
                if self.adapter:
                    await self.adapter.add_reaction(msg.channel, msg.message_id, "white_check_mark")

            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)

                # Send error message
                if self.adapter:
                    error_text = f"Sorry, I encountered an error: {str(e)}"
                    await self.adapter.send_message(
                        channel=msg.channel,
                        text=error_text,
                        thread_id=msg.thread_id or msg.message_id,
                    )

    async def _get_or_create_session(self, msg: UnifiedMessage) -> tuple[Any, asyncio.Lock]:
        """Lazily create or retrieve the session and lock for a conversation."""
        if not self.adapter:
            raise RuntimeError("Adapter not initialized")

        conv_id = self.adapter.get_conversation_id(msg.channel, msg.thread_id)

        # TODO: Create approval system for Teams
        # For now, use None (no approvals)
        approval_system = None

        # TODO: Create Teams-specific tool (like slack_reply)
        platform_tool = None

        # Delegate to SessionManager
        session, lock = await self.session_manager.get_or_create_session(
            conversation_id=conv_id,
            approval_system=approval_system,
            display_system=None,  # We handle display manually
            platform_tool=platform_tool,
        )

        return session, lock

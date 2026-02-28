"""
Slack platform adapter implementing PlatformAdapter protocol.

This adapter wraps Slack Bolt and provides a consistent interface
for the connector core to interact with Slack.
"""

import logging
from typing import Callable, Awaitable, Optional

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError

from connector_core.protocols import PlatformAdapter, ApprovalPrompt
from connector_core.models import UnifiedMessage
from slack_connector.bridge import SlackApprovalSystem

logger = logging.getLogger(__name__)


class SlackAdapter:
    """
    Slack implementation of PlatformAdapter protocol.
    
    Wraps Slack Bolt (Socket Mode) to provide a platform-agnostic interface
    for message handling, sending, and interactive elements.
    
    Usage:
        adapter = SlackAdapter(
            app_token="xapp-...",
            bot_token="xoxb-...",
            allowed_channel="C123ABC"  # optional
        )
        await adapter.startup()
        await adapter.listen(message_handler)
    """
    
    def __init__(
        self,
        app_token: str,
        bot_token: str,
        allowed_channel: Optional[str] = None
    ) -> None:
        """
        Initialize Slack adapter.
        
        Args:
            app_token: Slack app-level token (xapp-...)
            bot_token: Slack bot token (xoxb-...)
            allowed_channel: Optional channel ID to restrict bot to
        """
        self.app_token = app_token
        self.bot_token = bot_token
        self.allowed_channel = allowed_channel
        
        # Slack state
        self.bolt_app: Optional[AsyncApp] = None
        self.handler: Optional[AsyncSocketModeHandler] = None
        self.bot_user_id: Optional[str] = None
        self._active_threads: set[str] = set()
        
        # Message handler (set by listen())
        self._message_handler: Optional[Callable[[UnifiedMessage], Awaitable[None]]] = None
    
    # ------------------------------------------------------------------
    # PlatformAdapter Protocol Implementation
    # ------------------------------------------------------------------
    
    async def startup(self) -> None:
        """Initialize Slack Bolt app and authenticate."""
        logger.info("Starting Slack adapter...")
        
        self.bolt_app = AsyncApp(token=self.bot_token)
        
        # Authenticate and get bot user ID
        try:
            auth = await self.bolt_app.client.auth_test()
            self.bot_user_id = auth.get("user_id")
            bot_name = auth.get("user", "unknown")
            logger.info(f"Authenticated as @{bot_name} ({self.bot_user_id})")
        except SlackApiError as e:
            logger.warning(f"Could not resolve bot user ID: {e}")
            raise ConnectionError(f"Slack authentication failed: {e}")
        
        logger.info("Slack adapter started")
    
    async def shutdown(self) -> None:
        """Cleanup Slack resources and close Socket Mode connection."""
        logger.info("Shutting down Slack adapter...")
        
        if self.handler:
            try:
                await self.handler.close_async()
            except Exception as e:
                logger.warning(f"Error closing Socket Mode handler: {e}")
        
        self._active_threads.clear()
        logger.info("Slack adapter shutdown complete")
    
    async def listen(
        self,
        message_handler: Callable[[UnifiedMessage], Awaitable[None]]
    ) -> None:
        """
        Start listening for Slack messages and route to handler.
        
        This sets up Slack Bolt event handlers and starts Socket Mode.
        """
        if not self.bolt_app:
            raise RuntimeError("Must call startup() before listen()")
        
        self._message_handler = message_handler
        
        # Register Slack Bolt event handlers
        self._register_handlers()
        
        # Start Socket Mode (blocks until shutdown)
        self.handler = AsyncSocketModeHandler(self.bolt_app, self.app_token)
        await self.handler.start_async()
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Send a message to Slack.
        
        Args:
            channel: Slack channel ID (e.g., "C123ABC")
            text: Message text (supports Slack mrkdwn)
            thread_id: Optional thread timestamp to reply in
        
        Returns:
            Message timestamp (Slack's message ID)
        """
        if not self.bolt_app:
            raise RuntimeError("Must call startup() before send_message()")
        
        try:
            result = await self.bolt_app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_id,
                text=text,
                unfurl_links=False,
                unfurl_media=False
            )
            return result["ts"]
        except SlackApiError as e:
            logger.error(f"Failed to send message: {e}")
            raise ValueError(f"Could not send message to {channel}: {e}")
    
    async def add_reaction(
        self,
        channel: str,
        message_id: str,
        emoji: str
    ) -> None:
        """
        Add a reaction emoji to a Slack message.
        
        Args:
            channel: Slack channel ID
            message_id: Message timestamp
            emoji: Emoji name without colons (e.g., "thumbsup")
        """
        if not self.bolt_app:
            raise RuntimeError("Must call startup() before add_reaction()")
        
        try:
            await self.bolt_app.client.reactions_add(
                channel=channel,
                timestamp=message_id,
                name=emoji
            )
        except SlackApiError as e:
            logger.warning(f"Could not add reaction {emoji}: {e}")
    
    async def create_approval_prompt(
        self,
        channel: str,
        description: str,
        thread_id: Optional[str] = None
    ) -> ApprovalPrompt:
        """
        Create a Slack approval prompt with interactive buttons.
        
        Args:
            channel: Slack channel ID
            description: Description of what is being approved
            thread_id: Optional thread timestamp
        
        Returns:
            SlackApprovalSystem instance
        """
        if not self.bolt_app:
            raise RuntimeError("Must call startup() before create_approval_prompt()")
        
        # Create approval system (will post interactive message)
        approval = SlackApprovalSystem(
            client=self.bolt_app.client,
            channel=channel,
            thread_ts=thread_id
        )
        
        return approval
    
    def get_conversation_id(
        self,
        channel: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Generate stable conversation ID for session management.
        
        Format: "slack-{channel}" or "slack-{channel}-{thread}"
        
        Args:
            channel: Slack channel ID
            thread_id: Optional thread timestamp
        
        Returns:
            Stable conversation identifier
        """
        if thread_id:
            return f"slack-{channel}-{thread_id}"
        return f"slack-{channel}"
    
    # ------------------------------------------------------------------
    # Slack-specific message handling
    # ------------------------------------------------------------------
    
    def _register_handlers(self) -> None:
        """Register Slack Bolt event handlers."""
        if not self.bolt_app:
            return
        
        # Handle @mentions
        @self.bolt_app.event("app_mention")
        async def handle_mention(event, say):
            await self._handle_slack_message(event)
        
        # Handle DMs
        @self.bolt_app.event("message")
        async def handle_message(event, say):
            # Ignore bot messages and threaded replies (handled separately)
            if event.get("subtype") or event.get("thread_ts"):
                return
            
            # Only handle DMs or allowed channel
            channel_type = event.get("channel_type")
            if channel_type == "im" or (
                self.allowed_channel and event.get("channel") == self.allowed_channel
            ):
                await self._handle_slack_message(event)
    
    async def _handle_slack_message(self, event: dict) -> None:
        """Convert Slack event to UnifiedMessage and route to handler."""
        if not self._message_handler:
            logger.warning("No message handler registered")
            return
        
        # Ignore bot's own messages
        if event.get("user") == self.bot_user_id:
            return
        
        # Convert to UnifiedMessage
        unified_msg = UnifiedMessage(
            platform="slack",
            channel=event.get("channel", ""),
            user=event.get("user", ""),
            text=event.get("text", ""),
            message_id=event.get("ts", ""),
            thread_id=event.get("thread_ts"),
            raw_event=event
        )
        
        # Route to handler
        await self._message_handler(unified_msg)

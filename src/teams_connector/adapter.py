"""
Microsoft Teams platform adapter implementing PlatformAdapter protocol.

This adapter wraps Bot Framework SDK and provides a consistent interface
for the connector core to interact with Teams.
"""

import asyncio
import logging
from typing import Callable, Awaitable, Optional, Any
from datetime import datetime

from aiohttp import web
from connector_core.protocols import PlatformAdapter, ApprovalPrompt
from connector_core.models import UnifiedMessage

logger = logging.getLogger(__name__)


class TeamsAdapter:
    """
    Microsoft Teams implementation of PlatformAdapter protocol.
    
    Wraps Bot Framework SDK to provide a platform-agnostic interface
    for message handling, sending, and interactive elements.
    
    Note: This is a simplified implementation that works without the full
    Bot Framework SDK. For production, integrate botbuilder-core.
    
    Usage:
        adapter = TeamsAdapter(
            app_id="...",
            app_password="..."
        )
        await adapter.startup()
        await adapter.listen(message_handler)
    """
    
    def __init__(
        self,
        app_id: str,
        app_password: str,
        port: int = 3978
    ) -> None:
        """
        Initialize Teams adapter.
        
        Args:
            app_id: Microsoft App ID
            app_password: Microsoft App Password
            port: Port for Bot Framework webhook server
        """
        self.app_id = app_id
        self.app_password = app_password
        self.port = port
        
        # Webhook server state
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._message_handler: Optional[Callable[[UnifiedMessage], Awaitable[None]]] = None
        
        # Conversation state (for sending messages)
        self._conversation_references: dict[str, dict] = {}
    
    # ------------------------------------------------------------------
    # PlatformAdapter Protocol Implementation
    # ------------------------------------------------------------------
    
    async def startup(self) -> None:
        """
        Initialize Bot Framework adapter and prepare webhook server.
        
        Raises:
            ConnectionError: If unable to start server
        """
        logger.info("Starting Teams adapter...")
        
        # Create aiohttp application
        self._app = web.Application()
        self._app.router.add_post('/api/messages', self._handle_activity)
        self._app.router.add_get('/health', self._health_check)
        
        logger.info(f"Teams adapter initialized on port {self.port}")
    
    async def shutdown(self) -> None:
        """Cleanup Teams resources and stop webhook server."""
        logger.info("Shutting down Teams adapter...")
        
        if self._site:
            await self._site.stop()
        
        if self._runner:
            await self._runner.cleanup()
        
        self._conversation_references.clear()
        logger.info("Teams adapter shutdown complete")
    
    async def listen(
        self,
        message_handler: Callable[[UnifiedMessage], Awaitable[None]]
    ) -> None:
        """
        Start listening for Teams messages via Bot Framework webhook.
        
        This starts an HTTP server to receive Bot Framework activities.
        """
        if not self._app:
            raise RuntimeError("Must call startup() before listen()")
        
        self._message_handler = message_handler
        
        # Start webhook server
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        self._site = web.TCPSite(self._runner, '0.0.0.0', self.port)
        await self._site.start()
        
        logger.info(f"Teams webhook server listening on http://0.0.0.0:{self.port}")
        logger.info(f"Bot Framework endpoint: http://0.0.0.0:{self.port}/api/messages")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep forever
        except asyncio.CancelledError:
            logger.info("Listen task cancelled")
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Send a message to Teams.
        
        Args:
            channel: Teams conversation ID
            text: Message text (supports Markdown)
            thread_id: Optional activity ID to reply to
        
        Returns:
            Activity ID (Teams' message ID)
        """
        # TODO: Implement actual Bot Framework message sending
        # For now, log and return a mock ID
        logger.info(f"[MOCK] Send message to {channel}: {text[:50]}...")
        
        # In production, this would use Bot Framework's proactive messaging:
        # 1. Get conversation reference from self._conversation_references
        # 2. Create Activity with text
        # 3. Use adapter.continue_conversation() to send
        # 4. Return activity.id
        
        return f"teams-msg-{datetime.now().timestamp()}"
    
    async def add_reaction(
        self,
        channel: str,
        message_id: str,
        emoji: str
    ) -> None:
        """
        Add a reaction to a Teams message.
        
        Note: Teams reactions work differently than Slack.
        This is a placeholder implementation.
        
        Args:
            channel: Teams conversation ID
            message_id: Activity ID
            emoji: Emoji name
        """
        logger.debug(f"[MOCK] Add reaction {emoji} to {message_id} in {channel}")
        # Teams doesn't have a simple reactions API like Slack
        # Would need to use message reactions API when available
    
    async def create_approval_prompt(
        self,
        channel: str,
        description: str,
        thread_id: Optional[str] = None
    ) -> ApprovalPrompt:
        """
        Create a Teams approval prompt with Adaptive Card.
        
        Args:
            channel: Teams conversation ID
            description: Description of what is being approved
            thread_id: Optional activity ID
        
        Returns:
            TeamsApprovalPrompt instance
        """
        # TODO: Implement TeamsApprovalPrompt with Adaptive Cards
        raise NotImplementedError("Teams approval prompts not yet implemented")
    
    def get_conversation_id(
        self,
        channel: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Generate stable conversation ID for session management.
        
        Format: "teams-{conversation_id}" or "teams-{conversation_id}-{activity_id}"
        
        Args:
            channel: Teams conversation ID
            thread_id: Optional activity ID
        
        Returns:
            Stable conversation identifier
        """
        if thread_id:
            return f"teams-{channel}-{thread_id}"
        return f"teams-{channel}"
    
    # ------------------------------------------------------------------
    # Webhook handlers
    # ------------------------------------------------------------------
    
    async def _handle_activity(self, request: web.Request) -> web.Response:
        """
        Handle incoming Bot Framework activity.
        
        This is called by Teams/Bot Framework when a message is sent.
        """
        try:
            # Parse activity JSON
            activity = await request.json()
            
            logger.debug(f"Received activity: {activity.get('type')}")
            
            # Handle different activity types
            activity_type = activity.get('type')
            
            if activity_type == 'message':
                await self._handle_message_activity(activity)
            elif activity_type == 'conversationUpdate':
                await self._handle_conversation_update(activity)
            else:
                logger.debug(f"Ignoring activity type: {activity_type}")
            
            # Bot Framework expects 200 OK
            return web.Response(status=200)
            
        except Exception as e:
            logger.error(f"Error handling activity: {e}", exc_info=True)
            return web.Response(status=500, text=str(e))
    
    async def _handle_message_activity(self, activity: dict) -> None:
        """Convert Teams message activity to UnifiedMessage and route to handler."""
        if not self._message_handler:
            logger.warning("No message handler registered")
            return
        
        # Store conversation reference for proactive messaging
        conversation_id = activity.get('conversation', {}).get('id', '')
        if conversation_id:
            self._conversation_references[conversation_id] = {
                'activity_id': activity.get('id'),
                'service_url': activity.get('serviceUrl'),
                'conversation': activity.get('conversation'),
                'from': activity.get('from'),
            }
        
        # Convert to UnifiedMessage
        unified_msg = UnifiedMessage(
            platform="teams",
            channel_id=conversation_id,
            user_id=activity.get('from', {}).get('id', ''),
            text=activity.get('text', ''),
            message_id=activity.get('id', ''),
            thread_id=activity.get('replyToId'),
            timestamp=datetime.now(),  # Could parse from activity.timestamp
            raw_event=activity
        )
        
        # Route to handler
        await self._message_handler(unified_msg)
    
    async def _handle_conversation_update(self, activity: dict) -> None:
        """Handle conversation update (bot added/removed, etc.)."""
        members_added = activity.get('membersAdded', [])
        
        for member in members_added:
            if member.get('id') != activity.get('recipient', {}).get('id'):
                # Someone else joined
                logger.info(f"New member joined: {member.get('name')}")
            else:
                # Bot was added
                logger.info("Bot added to conversation")
    
    async def _health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.Response(text="Teams adapter is running")

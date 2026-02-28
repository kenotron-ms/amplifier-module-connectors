"""
Microsoft Teams platform adapter implementing PlatformAdapter protocol.

This adapter wraps Bot Framework SDK and provides a consistent interface
for the connector core to interact with Teams.
"""

import logging
from typing import Callable, Awaitable, Optional

from connector_core.protocols import PlatformAdapter, ApprovalPrompt
from connector_core.models import UnifiedMessage

logger = logging.getLogger(__name__)


class TeamsAdapter:
    """
    Microsoft Teams implementation of PlatformAdapter protocol.
    
    Wraps Bot Framework SDK to provide a platform-agnostic interface
    for message handling, sending, and interactive elements.
    
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
        
        # Bot Framework state
        self.adapter: Optional[Any] = None  # BotFrameworkAdapter
        self.bot: Optional[Any] = None  # ActivityHandler
        self._message_handler: Optional[Callable[[UnifiedMessage], Awaitable[None]]] = None
    
    # ------------------------------------------------------------------
    # PlatformAdapter Protocol Implementation
    # ------------------------------------------------------------------
    
    async def startup(self) -> None:
        """
        Initialize Bot Framework adapter and start webhook server.
        
        Raises:
            ConnectionError: If unable to start server
        """
        logger.info("Starting Teams adapter...")
        
        # TODO: Initialize Bot Framework adapter
        # from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
        # settings = BotFrameworkAdapterSettings(self.app_id, self.app_password)
        # self.adapter = BotFrameworkAdapter(settings)
        
        logger.info(f"Teams adapter started on port {self.port}")
    
    async def shutdown(self) -> None:
        """Cleanup Teams resources and stop webhook server."""
        logger.info("Shutting down Teams adapter...")
        
        # TODO: Stop webhook server
        
        logger.info("Teams adapter shutdown complete")
    
    async def listen(
        self,
        message_handler: Callable[[UnifiedMessage], Awaitable[None]]
    ) -> None:
        """
        Start listening for Teams messages via Bot Framework webhook.
        
        This starts an HTTP server to receive Bot Framework activities.
        """
        if not self.adapter:
            raise RuntimeError("Must call startup() before listen()")
        
        self._message_handler = message_handler
        
        # TODO: Start webhook server
        # - Listen on self.port
        # - Handle POST /api/messages
        # - Convert Activity -> UnifiedMessage
        # - Call message_handler
        
        logger.info(f"Teams adapter listening on port {self.port}")
    
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
        if not self.adapter:
            raise RuntimeError("Must call startup() before send_message()")
        
        # TODO: Send message via Bot Framework
        # activity = Activity(
        #     type=ActivityTypes.message,
        #     text=text,
        #     conversation=ConversationAccount(id=channel),
        #     reply_to_id=thread_id
        # )
        # response = await self.adapter.send_activity(activity)
        # return response.id
        
        logger.info(f"Send message to {channel}: {text[:50]}...")
        return "teams-message-id"
    
    async def add_reaction(
        self,
        channel: str,
        message_id: str,
        emoji: str
    ) -> None:
        """
        Add a reaction to a Teams message.
        
        Note: Teams reactions work differently than Slack.
        This may be implemented using message reactions API when available.
        
        Args:
            channel: Teams conversation ID
            message_id: Activity ID
            emoji: Emoji name
        """
        # TODO: Implement Teams reactions if supported
        logger.debug(f"Teams reactions not yet implemented: {emoji}")
    
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
        if not self.adapter:
            raise RuntimeError("Must call startup() before create_approval_prompt()")
        
        # TODO: Create TeamsApprovalPrompt with Adaptive Card
        # approval = TeamsApprovalPrompt(
        #     adapter=self.adapter,
        #     channel=channel,
        #     thread_id=thread_id
        # )
        
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

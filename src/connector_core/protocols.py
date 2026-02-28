"""
Platform adapter protocols.

These protocols define the interfaces that each chat platform must implement
to work with the Amplifier connector core.
"""

from typing import Protocol, Callable, Awaitable, Optional, Any
from .models import UnifiedMessage


class ApprovalPrompt(Protocol):
    """
    Protocol for platform-specific approval prompts.
    
    Each platform implements approval UI differently (Slack Block Kit buttons,
    Teams Adaptive Cards, etc.), but they all need to provide a way to:
    1. Display an approval request to the user
    2. Wait for user decision
    3. Return the approval result
    """
    
    async def wait_for_decision(self) -> bool:
        """
        Wait for user to approve or deny.
        
        Returns:
            True if approved, False if denied
        """
        ...
    
    def get_prompt_id(self) -> str:
        """
        Get unique identifier for this prompt.
        
        Returns:
            Platform-specific prompt identifier
        """
        ...


class PlatformAdapter(Protocol):
    """
    Interface that each chat platform must implement.
    
    This protocol defines the contract for platform-specific adapters.
    Each adapter handles the unique characteristics of its platform
    (authentication, message format, interactive elements) while providing
    a consistent interface to the core bot logic.
    
    Examples:
        >>> # Slack adapter using Socket Mode
        >>> slack_adapter = SlackAdapter(
        ...     app_token="xapp-...",
        ...     bot_token="xoxb-..."
        ... )
        >>> await slack_adapter.startup()
        >>> await slack_adapter.listen(message_handler)
        
        >>> # Teams adapter using Bot Framework
        >>> teams_adapter = TeamsAdapter(
        ...     app_id="...",
        ...     app_password="..."
        ... )
        >>> await teams_adapter.startup()
        >>> await teams_adapter.listen(message_handler)
    """
    
    async def startup(self) -> None:
        """
        Initialize platform connection and authenticate.
        
        This is called once at bot startup to establish connection to the
        platform's API/service. For example:
        - Slack: Initialize Socket Mode connection
        - Teams: Start Bot Framework adapter and webhook server
        
        Raises:
            ConnectionError: If unable to connect to platform
            AuthenticationError: If credentials are invalid
        """
        ...
    
    async def shutdown(self) -> None:
        """
        Cleanup platform resources and close connections.
        
        This is called when the bot is shutting down. Should gracefully
        close any open connections, stop background tasks, etc.
        """
        ...
    
    async def listen(
        self,
        message_handler: Callable[[UnifiedMessage], Awaitable[None]]
    ) -> None:
        """
        Start listening for messages and route to handler.
        
        This method should:
        1. Listen for incoming messages from the platform
        2. Convert platform-specific message format to UnifiedMessage
        3. Call message_handler with the unified message
        4. Run indefinitely until shutdown() is called
        
        Args:
            message_handler: Async function to call for each message
        
        Examples:
            >>> async def handle_message(msg: UnifiedMessage):
            ...     print(f"Received: {msg.text}")
            >>> 
            >>> await adapter.listen(handle_message)
        """
        ...
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Send a message to the platform.
        
        Args:
            channel: Platform-specific channel identifier
            text: Message text to send
            thread_id: Optional thread/reply identifier
        
        Returns:
            Platform-specific message ID of the sent message
        
        Raises:
            ValueError: If channel is invalid
            PermissionError: If bot lacks permission to post
        
        Examples:
            >>> # Send to channel
            >>> msg_id = await adapter.send_message("C123ABC", "Hello!")
            >>> 
            >>> # Reply in thread
            >>> msg_id = await adapter.send_message(
            ...     "C123ABC",
            ...     "Reply",
            ...     thread_id="1234567890.123456"
            ... )
        """
        ...
    
    async def add_reaction(
        self,
        channel: str,
        message_id: str,
        emoji: str
    ) -> None:
        """
        Add a reaction emoji to a message.
        
        Not all platforms support reactions. Implementations should either:
        - Add the reaction if supported
        - Silently ignore if not supported
        - Log a warning if not supported
        
        Args:
            channel: Platform-specific channel identifier
            message_id: Platform-specific message identifier
            emoji: Emoji name (without colons, e.g., "thumbsup")
        
        Examples:
            >>> await adapter.add_reaction("C123ABC", "1234567890.123456", "eyes")
        """
        ...
    
    async def create_approval_prompt(
        self,
        channel: str,
        description: str,
        thread_id: Optional[str] = None
    ) -> ApprovalPrompt:
        """
        Create a platform-specific approval prompt.
        
        This creates an interactive UI element for approval (e.g., Slack buttons,
        Teams Adaptive Card). The returned ApprovalPrompt can be awaited to get
        the user's decision.
        
        Args:
            channel: Platform-specific channel identifier
            description: Description of what is being approved
            thread_id: Optional thread/reply identifier
        
        Returns:
            ApprovalPrompt instance that can be awaited for decision
        
        Examples:
            >>> prompt = await adapter.create_approval_prompt(
            ...     "C123ABC",
            ...     "Execute command: rm -rf /"
            ... )
            >>> approved = await prompt.wait_for_decision()
            >>> if approved:
            ...     print("User approved!")
        """
        ...
    
    def get_conversation_id(
        self,
        channel: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Generate a stable conversation identifier.
        
        This is used for session management - messages in the same conversation
        (channel + thread) should map to the same Amplifier session.
        
        The format should be: "{platform}-{channel}-{thread}" or
        "{platform}-{channel}" for top-level conversations.
        
        Args:
            channel: Platform-specific channel identifier
            thread_id: Optional thread/reply identifier
        
        Returns:
            Stable conversation ID string
        
        Examples:
            >>> # Top-level conversation
            >>> conv_id = adapter.get_conversation_id("C123ABC")
            >>> # "slack-C123ABC"
            >>> 
            >>> # Thread conversation
            >>> conv_id = adapter.get_conversation_id("C123ABC", "1234567890.123456")
            >>> # "slack-C123ABC-1234567890.123456"
        """
        ...

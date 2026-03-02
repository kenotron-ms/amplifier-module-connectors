"""
Platform-agnostic message models.

These models provide a unified representation of messages across different
chat platforms (Slack, Teams, Discord, etc.).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class UnifiedMessage:
    """
    Platform-agnostic message representation.

    This model abstracts away platform-specific message formats into a
    common structure that can be used by the core bot logic.

    Attributes:
        platform: Platform identifier (e.g., "slack", "teams")
        channel_id: Platform-specific channel/conversation identifier
        user_id: Platform-specific user identifier
        text: Message text content
        message_id: Platform-specific message identifier
        thread_id: Optional thread/reply identifier (None for top-level messages)
        timestamp: When the message was sent
        raw_event: Original platform event for platform-specific handling

    Examples:
        >>> # Slack message
        >>> msg = UnifiedMessage(
        ...     platform="slack",
        ...     channel_id="C123ABC",
        ...     user_id="U456DEF",
        ...     text="Hello, bot!",
        ...     message_id="1234567890.123456",
        ...     thread_id=None,
        ...     timestamp=datetime.now(),
        ...     raw_event={"type": "message", ...}
        ... )

        >>> # Teams message in a thread
        >>> msg = UnifiedMessage(
        ...     platform="teams",
        ...     channel_id="19:meeting_abc123",
        ...     user_id="29:user_xyz789",
        ...     text="Reply in thread",
        ...     message_id="1234567890",
        ...     thread_id="parent_msg_id",
        ...     timestamp=datetime.now(),
        ...     raw_event={"type": "message", ...}
        ... )
    """

    platform: str
    channel_id: str
    user_id: str
    text: str
    message_id: str
    thread_id: Optional[str]
    timestamp: datetime
    raw_event: dict[str, Any]

    def get_conversation_id(self) -> str:
        """
        Generate a stable conversation identifier.

        This is used for session management - messages in the same conversation
        (channel + thread) should map to the same Amplifier session.

        Returns:
            Stable conversation ID string
        """
        if self.thread_id:
            return f"{self.platform}-{self.channel_id}-{self.thread_id}"
        return f"{self.platform}-{self.channel_id}"

    def is_threaded(self) -> bool:
        """Check if this message is part of a thread."""
        return self.thread_id is not None

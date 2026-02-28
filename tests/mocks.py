"""
Mock implementations for testing.
"""

from typing import Callable, Awaitable, Optional
from datetime import datetime
from src.connector_core.models import UnifiedMessage
from src.connector_core.protocols import PlatformAdapter, ApprovalPrompt


class MockApprovalPrompt:
    """Mock approval prompt for testing."""
    
    def __init__(self, prompt_id: str, auto_approve: bool = True):
        self.prompt_id = prompt_id
        self.auto_approve = auto_approve
    
    async def wait_for_decision(self) -> bool:
        """Return predetermined decision."""
        return self.auto_approve
    
    def get_prompt_id(self) -> str:
        """Return prompt ID."""
        return self.prompt_id


class MockPlatformAdapter:
    """
    Mock platform adapter for testing.
    
    This implementation conforms to the PlatformAdapter protocol and can be
    used in tests without requiring actual platform connections.
    """
    
    def __init__(self, platform_name: str = "mock"):
        self.platform_name = platform_name
        self.is_started = False
        self.is_shutdown = False
        self.sent_messages: list[dict] = []
        self.reactions: list[dict] = []
        self.approval_prompts: list[MockApprovalPrompt] = []
    
    async def startup(self) -> None:
        """Mock startup."""
        self.is_started = True
    
    async def shutdown(self) -> None:
        """Mock shutdown."""
        self.is_shutdown = True
    
    async def listen(
        self,
        message_handler: Callable[[UnifiedMessage], Awaitable[None]]
    ) -> None:
        """Mock listen - doesn't actually listen."""
        # In a real test, you might inject messages here
        pass
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None
    ) -> str:
        """Mock send message - records the message."""
        message_id = f"msg_{len(self.sent_messages)}"
        self.sent_messages.append({
            "channel": channel,
            "text": text,
            "thread_id": thread_id,
            "message_id": message_id
        })
        return message_id
    
    async def add_reaction(
        self,
        channel: str,
        message_id: str,
        emoji: str
    ) -> None:
        """Mock add reaction - records the reaction."""
        self.reactions.append({
            "channel": channel,
            "message_id": message_id,
            "emoji": emoji
        })
    
    async def create_approval_prompt(
        self,
        channel: str,
        description: str,
        thread_id: Optional[str] = None
    ) -> ApprovalPrompt:
        """Mock create approval prompt."""
        prompt = MockApprovalPrompt(
            prompt_id=f"prompt_{len(self.approval_prompts)}",
            auto_approve=True
        )
        self.approval_prompts.append(prompt)
        return prompt
    
    def get_conversation_id(
        self,
        channel: str,
        thread_id: Optional[str] = None
    ) -> str:
        """Generate conversation ID."""
        if thread_id:
            return f"{self.platform_name}-{channel}-{thread_id}"
        return f"{self.platform_name}-{channel}"

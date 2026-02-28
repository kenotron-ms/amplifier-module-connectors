"""
Session management for Amplifier connectors.

Manages the lifecycle of Amplifier sessions across different chat platforms.
Handles bundle preparation, session caching, and lock management.
"""

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Platform-agnostic session manager for Amplifier.
    
    This class manages:
    - Bundle preparation (one-time, expensive operation)
    - Session caching (one session per conversation)
    - Lock management (prevents concurrent execution per conversation)
    
    Usage:
        manager = SessionManager("./bundle.md")
        await manager.initialize()
        session, lock = await manager.get_or_create_session(
            conversation_id="slack-C123ABC",
            approval_system=approval_system,
            display_system=None
        )
    """
    
    def __init__(self, bundle_path: str):
        """
        Initialize session manager.
        
        Args:
            bundle_path: Path to Amplifier bundle configuration file
        """
        self.bundle_path = bundle_path
        
        # Amplifier state (platform-agnostic)
        self.prepared: Any = None  # PreparedBundle from amplifier-foundation
        self.sessions: dict[str, Any] = {}  # conversation_id -> AmplifierSession
        self.locks: dict[str, asyncio.Lock] = {}  # conversation_id -> Lock
    
    async def initialize(self) -> None:
        """
        Load and prepare the Amplifier bundle.
        
        This is an expensive operation that should be done once at startup.
        The prepared bundle is cached in self.prepared for creating sessions.
        
        Raises:
            RuntimeError: If amplifier-foundation is not installed
            Exception: If bundle loading or preparation fails
        """
        logger.info(f"Loading Amplifier bundle: {self.bundle_path}")
        try:
            from amplifier_foundation import load_bundle  # type: ignore[import]
            
            bundle = await load_bundle(self.bundle_path)
            self.prepared = await bundle.prepare()
            logger.info("Amplifier bundle prepared successfully")
        except ImportError as e:
            raise RuntimeError(
                "amplifier-foundation not installed. Install with: uv pip install amplifier-foundation"
            ) from e
    
    async def get_or_create_session(
        self,
        conversation_id: str,
        approval_system: Any,
        display_system: Optional[Any] = None,
        platform_tool: Optional[Any] = None,
    ) -> tuple[Any, asyncio.Lock]:
        """
        Get existing session or create a new one for a conversation.
        
        Sessions are cached per conversation_id. Each session gets its own lock
        to prevent concurrent execution.
        
        Args:
            conversation_id: Stable identifier for the conversation
            approval_system: Platform-specific approval system
            display_system: Optional display system (None to prevent duplicate messages)
            platform_tool: Optional platform-specific tool to mount (e.g., slack_reply)
        
        Returns:
            Tuple of (session, lock) for the conversation
        
        Raises:
            RuntimeError: If initialize() hasn't been called yet
        """
        if self.prepared is None:
            raise RuntimeError("SessionManager.initialize() must be called before creating sessions")
        
        if conversation_id not in self.sessions:
            logger.info(f"Creating new session: {conversation_id}")
            
            # Create session using prepared bundle
            session = await self.prepared.create_session(
                session_id=conversation_id,
                approval_system=approval_system,
                display_system=display_system,
            )
            
            # Mount platform-specific tool if provided
            if platform_tool is not None:
                try:
                    tool_name = getattr(platform_tool, '__class__', type(platform_tool)).__name__
                    # Extract tool name from class name (e.g., SlackReplyTool -> slack_reply)
                    if tool_name.endswith('Tool'):
                        tool_name = tool_name[:-4]  # Remove 'Tool' suffix
                    # Convert CamelCase to snake_case
                    import re
                    tool_name = re.sub(r'(?<!^)(?=[A-Z])', '_', tool_name).lower()
                    
                    await session.coordinator.mount("tools", platform_tool, name=tool_name)
                    logger.debug(f"Mounted {tool_name} tool for {conversation_id}")
                except Exception as e:
                    logger.warning(f"Could not mount platform tool: {e}")
            
            # Cache session and create lock
            self.sessions[conversation_id] = session
            self.locks[conversation_id] = asyncio.Lock()
        
        return self.sessions[conversation_id], self.locks[conversation_id]
    
    async def close_all(self) -> None:
        """
        Close all active sessions and cleanup resources.
        
        This should be called during shutdown. Gracefully closes each session
        and clears all caches.
        """
        logger.info("Closing all sessions...")
        
        for conv_id, session in list(self.sessions.items()):
            try:
                await session.close()
                logger.debug(f"Closed session: {conv_id}")
            except Exception as e:
                logger.warning(f"Error closing session {conv_id}: {e}")
        
        self.sessions.clear()
        self.locks.clear()
        logger.info("All sessions closed")

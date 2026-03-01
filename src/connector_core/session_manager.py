"""
Session management for Amplifier connectors.

Manages the lifecycle of Amplifier sessions across different chat platforms.
Handles bundle preparation, session caching, lock management, and working directories.
"""

import asyncio
import logging
import os
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
    
    def __init__(self, bundle_path: str, default_workdir: Optional[str] = None):
        """
        Initialize session manager.
        
        Args:
            bundle_path: Path to Amplifier bundle configuration file
            default_workdir: Default working directory for new sessions (default: current dir)
        """
        import os
        self.bundle_path = bundle_path
        self.default_workdir = default_workdir or os.getcwd()
        
        # Amplifier state (platform-agnostic)
        self.prepared: Any = None  # PreparedBundle from amplifier-foundation
        self.sessions: dict[str, Any] = {}  # conversation_id -> AmplifierSession
        self.locks: dict[str, asyncio.Lock] = {}  # conversation_id -> Lock
        
        # Working directory tracking (per conversation)
        self.working_dirs: dict[str, str] = {}  # conversation_id -> working_dir
    
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
        
        # NOTE: We do NOT change directory here because it would cause race conditions
        # with concurrent sessions. The caller should change directory INSIDE the lock.
        # See ensure_working_directory() method below.
        
        if conversation_id not in self.sessions:
            logger.info(f"Creating new session: {conversation_id}")
            
            # Get working directory for this conversation
            working_dir = self.working_dirs.get(conversation_id, self.default_workdir)
            logger.info(f"Creating session with working directory: {working_dir}")
            
            # Create session using prepared bundle with session_cwd
            # The session_cwd parameter sets the working directory for this session
            # and registers the "session.working_dir" capability that tools can query
            from pathlib import Path
            session = await self.prepared.create_session(
                session_id=conversation_id,
                approval_system=approval_system,
                display_system=display_system,
                session_cwd=Path(working_dir),
            )
            
            # Try to restore working directory from session context
            try:
                if hasattr(session, 'context') and hasattr(session.context, 'get_metadata'):
                    saved_dir = await session.context.get_metadata('working_directory')
                    if saved_dir and os.path.isdir(saved_dir):
                        self.working_dirs[conversation_id] = saved_dir
                        logger.info(f"Restored working directory from context: {saved_dir}")
            except Exception as e:
                logger.debug(f"Could not restore working directory from context: {e}")
            
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
            
            # Mount project manager tool
            try:
                import sys
                import os as os_module
                # Add modules directory to path
                modules_dir = os_module.path.join(os_module.path.dirname(__file__), '..', '..', 'modules')
                if os_module.path.isdir(modules_dir):
                    sys.path.insert(0, modules_dir)
                
                from tool_project_manager.tool import ProjectManagerTool  # type: ignore[import]
                project_tool = ProjectManagerTool(self, conversation_id)
                await session.coordinator.mount("tools", project_tool, name="project_manager")
                logger.debug(f"Mounted project_manager tool for {conversation_id}")
            except Exception as e:
                logger.warning(f"Could not mount project_manager tool: {e}")
            
            # Cache session and create lock
            self.sessions[conversation_id] = session
            self.locks[conversation_id] = asyncio.Lock()
        
        return self.sessions[conversation_id], self.locks[conversation_id]
    
    def get_working_dir(self, conversation_id: str) -> str:
        """
        Get the working directory for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Working directory path (absolute)
        """
        return self.working_dirs.get(conversation_id, self.default_workdir)
    
    def set_working_dir(self, conversation_id: str, path: str) -> None:
        """
        Set the working directory for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            path: New working directory path
        """
        import os
        self.working_dirs[conversation_id] = os.path.abspath(path)
        logger.info(f"Set working directory for {conversation_id}: {path}")
    
    def ensure_working_directory(self, conversation_id: str) -> None:
        """
        Ensure the session's working directory is set correctly.
        
        This updates both:
        1. The "session.working_dir" capability (what tools use to discover CWD)
        2. The process CWD via os.chdir() (fallback for tools that use Path.cwd())
        
        This is important for existing sessions where the working directory may have
        changed after the session was created (e.g., via /amplifier open command).
        
        This should be called INSIDE the conversation's lock to avoid race conditions
        between concurrent conversations.
        
        Args:
            conversation_id: Conversation identifier
        """
        working_dir = self.working_dirs.get(conversation_id, self.default_workdir)
        
        # Update the session.working_dir capability if session exists
        session = self.sessions.get(conversation_id)
        if session:
            try:
                current_capability = session.coordinator.get_capability("session.working_dir")
                if current_capability != working_dir:
                    session.coordinator.register_capability("session.working_dir", working_dir)
                    logger.debug(f"Updated session.working_dir capability for {conversation_id}: {working_dir}")
            except Exception as e:
                logger.warning(f"Could not update session.working_dir capability: {e}")
        
        # Also update process CWD as fallback
        try:
            current_dir = os.getcwd()
            if current_dir != working_dir:
                os.chdir(working_dir)
                logger.debug(f"Changed process CWD for {conversation_id}: {working_dir}")
        except Exception as e:
            logger.warning(f"Could not change process CWD to {working_dir}: {e}")
    
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
        self.working_dirs.clear()
        logger.info("All sessions closed")

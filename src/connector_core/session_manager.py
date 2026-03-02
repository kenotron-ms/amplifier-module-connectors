"""
Session management for Amplifier connectors.

Manages the lifecycle of Amplifier sessions across different chat platforms.
Bundles are project-scoped: each project directory can define its own bundle.md
that controls the agent persona, skills, hooks, and tools for that project.
The default bundle (server project) is used when no project-specific bundle exists.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base (overlay wins on conflicts)."""
    result = base.copy()
    for k, v in overlay.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class SessionManager:
    """
    Platform-agnostic session manager for Amplifier.

    Bundles are project-scoped: each project directory can have its own bundle.md
    defining the agent, skills, and hooks for work in that project. Sessions are
    automatically recreated when a thread switches to a different project.

    Usage:
        manager = SessionManager("./bundle.md")
        await manager.initialize()
        session, lock = await manager.get_or_create_session(
            conversation_id="slack-C123ABC",
            approval_system=approval_system,
            project_path="/path/to/project",  # None = use default bundle
        )
    """

    def __init__(self, default_bundle_path: str, default_workdir: Optional[str] = None):
        """
        Initialize session manager.

        Args:
            default_bundle_path: Path to the default (server project) bundle.md.
                Used when a project has no bundle.md of its own.
            default_workdir: Default working directory for new sessions (default: current dir)
        """
        self.default_bundle_path = default_bundle_path
        self.default_workdir = default_workdir or os.getcwd()

        # Bundle cache: resolved bundle file path -> PreparedBundle
        self.prepared_bundles: dict[str, Any] = {}
        self._bundle_lock: asyncio.Lock = asyncio.Lock()
        self._initialized: bool = False

        # Session state
        self.sessions: dict[str, Any] = {}  # conversation_id -> AmplifierSession
        self.locks: dict[str, asyncio.Lock] = {}  # conversation_id -> Lock
        self.session_projects: dict[str, Optional[str]] = {}  # conversation_id -> project_path
        self.session_bundles: dict[str, str] = {}  # conversation_id -> resolved bundle path

        # Working directory tracking (per conversation)
        self.working_dirs: dict[str, str] = {}  # conversation_id -> working_dir

    def _resolve_bundle_path(self, project_path: Optional[str]) -> str:
        """
        Resolve the bundle file path for a project.

        Resolution order (first match wins):
          1. .amplifier/settings.yaml (+ settings.local.yaml override) — standard
             amplifier project config: bundle.active → bundle.added[name] → URI
          2. bundle.md in the project root — simple / legacy fallback
          3. Default server bundle — used when the project has no bundle config

        Args:
            project_path: Absolute path to the project directory, or None for default.

        Returns:
            Absolute path to the resolved bundle.md file to use.
        """
        if project_path is None:
            return str(Path(self.default_bundle_path).expanduser().resolve())

        project_dir = Path(project_path).expanduser().resolve()

        # --- 1. Read .amplifier/settings.yaml (project + local override) ---
        uri = self._read_active_bundle_uri(project_dir)
        if uri is not None:
            # Relative URIs are resolved relative to the project directory
            if uri.startswith("./") or uri.startswith("../"):
                resolved = str((project_dir / uri).resolve())
            else:
                resolved = uri
            if Path(resolved).is_file():
                logger.debug(f"Resolved bundle from settings.yaml: {resolved}")
                return resolved
            logger.warning(
                f"settings.yaml active bundle URI {uri!r} resolved to {resolved!r} "
                f"but file does not exist — falling back."
            )

        # --- 2. bundle.md in project root ---
        root_bundle = project_dir / "bundle.md"
        if root_bundle.is_file():
            logger.debug(f"Resolved bundle from project root: {root_bundle}")
            return str(root_bundle)

        # --- 3. Default server bundle ---
        logger.warning(
            f"No bundle found for {project_path} "
            f"(checked .amplifier/settings.yaml and bundle.md) — "
            f"using default server bundle. Add a bundle to the project for its own "
            f"agent/skills/hooks."
        )
        return str(Path(self.default_bundle_path).expanduser().resolve())

    def _read_active_bundle_uri(self, project_dir: Path) -> Optional[str]:
        """
        Read the active bundle URI from .amplifier/settings.yaml (and settings.local.yaml).

        Replicates the amplifier-app-cli merge order for the project scope:
          .amplifier/settings.yaml  (project, team-shared)
          .amplifier/settings.local.yaml  (machine-local override, gitignored)

        Returns the resolved URI string, or None if no active bundle is configured.
        """
        import yaml  # type: ignore[import]  # pyyaml — available as transitive dep of amplifier-foundation

        settings: dict = {}
        for settings_file in [
            project_dir / ".amplifier" / "settings.yaml",
            project_dir / ".amplifier" / "settings.local.yaml",
        ]:
            if settings_file.is_file():
                try:
                    with open(settings_file) as f:
                        content = yaml.safe_load(f) or {}
                    settings = _deep_merge(settings, content)
                except Exception as e:
                    logger.warning(f"Could not read {settings_file}: {e}")

        bundle_section = settings.get("bundle") or {}
        active_name = bundle_section.get("active")
        added = bundle_section.get("added") or {}

        if not active_name:
            return None
        if active_name not in added:
            logger.warning(
                f"settings.yaml declares active bundle {active_name!r} "
                f"but it is not in bundle.added — available: {list(added)}"
            )
            return None

        return added[active_name]

    async def _get_or_create_prepared(self, project_path: Optional[str]) -> Any:
        """
        Load and cache a PreparedBundle for the given project path.

        Uses double-check locking to safely handle concurrent first-time loads.

        Args:
            project_path: Project directory, or None for the default bundle.

        Returns:
            PreparedBundle instance (cached after first load).
        """
        bundle_file = self._resolve_bundle_path(project_path)

        # Fast path: already cached
        if bundle_file in self.prepared_bundles:
            return self.prepared_bundles[bundle_file]

        # Slow path: load under lock (double-check after acquiring)
        async with self._bundle_lock:
            if bundle_file in self.prepared_bundles:
                return self.prepared_bundles[bundle_file]

            logger.info(f"Loading Amplifier bundle: {bundle_file}")
            try:
                from amplifier_foundation import load_bundle  # type: ignore[import]

                bundle = await load_bundle(bundle_file)
                prepared = await bundle.prepare()
                self.prepared_bundles[bundle_file] = prepared
                logger.info(f"Bundle prepared: {bundle_file}")
                return prepared
            except ImportError as e:
                raise RuntimeError(
                    "amplifier-foundation not installed. Install with: uv pip install amplifier-foundation"
                ) from e

    async def initialize(self) -> None:
        """
        Pre-load the default (server project) bundle.

        This is an expensive one-time operation at startup. Additional project
        bundles are loaded lazily on first use.

        Raises:
            RuntimeError: If amplifier-foundation is not installed
            Exception: If bundle loading or preparation fails
        """
        logger.info(f"Loading default Amplifier bundle: {self.default_bundle_path}")
        try:
            await self._get_or_create_prepared(None)
            self._initialized = True
            logger.info("Default bundle prepared successfully")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to prepare default bundle: {e}") from e

    async def _close_session(self, conversation_id: str) -> None:
        """
        Close and discard a session (e.g., when the project changes).

        The conversation lock and working_dirs entry are preserved so they
        can be reused by the new session.

        Args:
            conversation_id: Conversation whose session to close.
        """
        session = self.sessions.pop(conversation_id, None)
        self.session_projects.pop(conversation_id, None)
        self.session_bundles.pop(conversation_id, None)
        # Keep self.locks[conversation_id] — reused by the replacement session
        # Keep self.working_dirs[conversation_id] — persists across bundle changes

        if session is not None:
            try:
                await session.close()
                logger.debug(f"Closed session for project change: {conversation_id}")
            except Exception as e:
                logger.warning(f"Error closing session {conversation_id}: {e}")

    async def get_or_create_session(
        self,
        conversation_id: str,
        approval_system: Any,
        project_path: Optional[str] = None,
        display_system: Optional[Any] = None,
        platform_tool: Optional[Any] = None,
    ) -> tuple[Any, asyncio.Lock]:
        """
        Get existing session or create a new one for a conversation.

        Sessions are cached per conversation_id. If the project changes for an
        existing session, the old session is closed and a new one is created
        with the correct project bundle.

        Args:
            conversation_id: Stable identifier for the conversation
            approval_system: Platform-specific approval system
            project_path: Absolute path to the project directory. If the
                directory contains bundle.md, that bundle is used. Otherwise
                falls back to the default bundle. None = use default bundle.
            display_system: Optional display system (None prevents duplicate messages)
            platform_tool: Optional platform-specific tool to mount (e.g., slack_reply)

        Returns:
            Tuple of (session, lock) for the conversation

        Raises:
            RuntimeError: If initialize() hasn't been called yet
        """
        if not self._initialized:
            raise RuntimeError(
                "SessionManager.initialize() must be called before creating sessions"
            )

        # Resolve the bundle for this project upfront — this is THE active bundle.
        # Uses the project's own bundle.md if present, otherwise the server default.
        active_bundle = self._resolve_bundle_path(project_path)

        # Detect bundle change → close old session so it gets recreated with the right bundle.
        # We compare the RESOLVED bundle path (not just the project directory) so that:
        #   - adding bundle.md to an existing project triggers a new session
        #   - switching between two projects that share the same bundle does not
        if conversation_id in self.sessions:
            old_bundle = self.session_bundles.get(conversation_id)
            if old_bundle != active_bundle:
                logger.info(
                    f"Bundle changed for {conversation_id}: "
                    f"{old_bundle!r} → {active_bundle!r}. Recreating session."
                )
                await self._close_session(conversation_id)

        if conversation_id not in self.sessions:
            logger.info(
                f"Creating session {conversation_id} "
                f"[bundle: {active_bundle}] [project: {project_path or '(default)'}]"
            )

            # Load (or retrieve cached) PreparedBundle for the active bundle path
            prepared = await self._get_or_create_prepared(project_path)

            # Working directory: explicit override > project path > default
            working_dir = self.working_dirs.get(
                conversation_id, project_path or self.default_workdir
            )
            logger.info(f"  working_dir: {working_dir}")

            # Create session using the project's prepared bundle
            session = await prepared.create_session(
                session_id=conversation_id,
                approval_system=approval_system,
                display_system=display_system,
                session_cwd=Path(working_dir),
            )

            # Try to restore working directory from session context
            try:
                if hasattr(session, "context") and hasattr(session.context, "get_metadata"):
                    saved_dir = await session.context.get_metadata("working_directory")
                    if saved_dir and os.path.isdir(saved_dir):
                        self.working_dirs[conversation_id] = saved_dir
                        logger.info(f"Restored working directory from context: {saved_dir}")
            except Exception as e:
                logger.debug(f"Could not restore working directory from context: {e}")

            # Mount platform-specific tool if provided
            if platform_tool is not None:
                try:
                    tool_name = getattr(platform_tool, "__class__", type(platform_tool)).__name__
                    if tool_name.endswith("Tool"):
                        tool_name = tool_name[:-4]
                    import re

                    tool_name = re.sub(r"(?<!^)(?=[A-Z])", "_", tool_name).lower()
                    await session.coordinator.mount("tools", platform_tool, name=tool_name)
                    logger.debug(f"Mounted {tool_name} tool for {conversation_id}")
                except Exception as e:
                    logger.warning(f"Could not mount platform tool: {e}")

            # Mount project manager tool
            try:
                import sys
                import os as os_module

                modules_dir = os_module.path.join(
                    os_module.path.dirname(__file__), "..", "..", "modules"
                )
                if os_module.path.isdir(modules_dir):
                    sys.path.insert(0, modules_dir)

                from tool_project_manager.tool import ProjectManagerTool  # type: ignore[import]

                project_tool = ProjectManagerTool(self, conversation_id)
                await session.coordinator.mount("tools", project_tool, name="project_manager")
                logger.debug(f"Mounted project_manager tool for {conversation_id}")
            except Exception as e:
                logger.warning(f"Could not mount project_manager tool: {e}")

            # Register spawn capability so tool-delegate can create sub-sessions
            async def _spawn(config: dict) -> Any:
                """Create a sub-session for agent delegation via tool-delegate."""
                import uuid

                sub_session_id = config.get("session_id") or str(uuid.uuid4())
                spawn_working_dir = self.working_dirs.get(conversation_id, self.default_workdir)
                # Spawn uses the same project bundle as the parent session
                spawn_project = self.session_projects.get(conversation_id)
                spawn_prepared = await self._get_or_create_prepared(spawn_project)
                return await spawn_prepared.create_session(
                    session_id=sub_session_id,
                    approval_system=approval_system,
                    display_system=None,
                    session_cwd=Path(spawn_working_dir),
                )

            try:
                session.coordinator.register_capability("spawn", _spawn)
                logger.debug(f"Registered spawn capability for {conversation_id}")
            except Exception as e:
                logger.warning(f"Could not register spawn capability: {e}")

            # Cache session; create lock if not already present (preserved across bundle changes)
            self.sessions[conversation_id] = session
            self.session_projects[conversation_id] = project_path
            self.session_bundles[conversation_id] = active_bundle
            if conversation_id not in self.locks:
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

        Also syncs the session.working_dir capability immediately if a session
        already exists for this conversation, so tools reflect the change
        without waiting for the next session creation.

        Args:
            conversation_id: Conversation identifier
            path: New working directory path
        """
        abs_path = os.path.abspath(path)
        self.working_dirs[conversation_id] = abs_path
        logger.info(f"Set working directory for {conversation_id}: {abs_path}")

        # Sync capability on existing session immediately
        session = self.sessions.get(conversation_id)
        if session:
            try:
                session.coordinator.register_capability("session.working_dir", abs_path)
                logger.debug(
                    f"Synced session.working_dir capability for {conversation_id}: {abs_path}"
                )
            except Exception as e:
                logger.warning(f"Could not sync session.working_dir capability: {e}")

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
        self.session_projects.clear()
        self.session_bundles.clear()
        self.prepared_bundles.clear()
        self._initialized = False
        logger.info("All sessions closed")

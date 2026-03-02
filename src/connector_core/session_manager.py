"""
Session management for Amplifier connectors.

Manages the lifecycle of Amplifier sessions across different chat platforms.
Bundle resolution uses the same machinery as the Amplifier CLI (amplifier_app_cli):
the "foundation" bundle is always the fallback, project settings are respected,
and providers are injected from ~/.amplifier/settings.yaml automatically.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Platform-agnostic session manager for Amplifier.

    Bundle resolution mirrors `amplifier run` exactly:
      1. bundle.active from the project's .amplifier/settings[.local].yaml
      2. bundle.active from ~/.amplifier/settings.yaml (global)
      3. "foundation" (hardcoded CLI default)

    Provider configuration is always injected from ~/.amplifier/settings.yaml
    by the CLI's own resolve_bundle_config() machinery — no hand-rolled YAML
    reading for providers.

    Sessions are automatically recreated when a thread switches to a project
    whose active bundle name differs from the current session's bundle name.

    Usage:
        manager = SessionManager()
        await manager.initialize()
        session, lock = await manager.get_or_create_session(
            conversation_id="slack-C123ABC",
            approval_system=approval_system,
            project_path="/path/to/project",  # None = use default bundle
        )
    """

    def __init__(self, default_bundle_path: str = "", default_workdir: Optional[str] = None):
        """
        Initialize session manager.

        Args:
            default_bundle_path: Accepted for backward compatibility but no longer used.
                Bundle resolution now always uses the CLI's waterfall (project settings
                → global settings → "foundation"). Callers may pass any string; it is
                stored but ignored for bundle loading.
            default_workdir: Default working directory for new sessions (default: cwd)
        """
        self.default_bundle_path = default_bundle_path  # kept for backward compat
        self.default_workdir = default_workdir or os.getcwd()

        # Bundle cache: (bundle_name, project_path) -> PreparedBundle
        # Keyed by (name, path) so different projects with the same bundle name
        # get their own PreparedBundle (which carries project-scoped tool overrides).
        self.prepared_bundles: dict[tuple[str, Optional[str]], Any] = {}
        self._bundle_lock: asyncio.Lock = asyncio.Lock()
        self._initialized: bool = False

        # Session state
        self.sessions: dict[str, Any] = {}  # conversation_id -> AmplifierSession
        self.locks: dict[str, asyncio.Lock] = {}  # conversation_id -> Lock
        self.session_projects: dict[str, Optional[str]] = {}  # conversation_id -> project_path
        self.session_bundles: dict[str, str] = {}  # conversation_id -> bundle name

        # Working directory tracking (per conversation)
        self.working_dirs: dict[str, str] = {}  # conversation_id -> working_dir

    # ------------------------------------------------------------------
    # Bundle resolution helpers
    # ------------------------------------------------------------------

    def _get_bundle_name(self, project_path: Optional[str]) -> str:
        """Resolve bundle name using the CLI's waterfall.

        Priority (first match wins):
          1. bundle.active in project's .amplifier/settings[.local].yaml
          2. bundle.active in ~/.amplifier/settings.yaml (global default)
          3. "foundation" — hardcoded fallback (same as `amplifier run`)

        Args:
            project_path: Absolute path to the project directory, or None.

        Returns:
            Bundle name string, e.g. "foundation" or "my-agent".
        """
        try:
            from amplifier_app_cli.lib.settings import AppSettings, SettingsPaths  # type: ignore[import]

            if project_path is not None:
                project_dir = Path(project_path).expanduser().resolve()
                paths = SettingsPaths(
                    global_settings=Path.home() / ".amplifier" / "settings.yaml",
                    project_settings=project_dir / ".amplifier" / "settings.yaml",
                    local_settings=project_dir / ".amplifier" / "settings.local.yaml",
                )
                app_settings = AppSettings(paths)
            else:
                # No specific project — read global settings only (connector CWD
                # typically has no .amplifier dir, so project scope is a no-op).
                app_settings = AppSettings()

            bundle = app_settings.get_active_bundle()
            if bundle:
                logger.debug(
                    f"Resolved bundle '{bundle}' from settings "
                    f"(project: {project_path or '(default)'})"
                )
                return bundle

        except ImportError:
            logger.warning(
                "amplifier_app_cli is not importable; falling back to 'foundation' bundle. "
                "Ensure you are running within the amplifier uv environment."
            )
        except Exception as e:
            logger.warning(f"Could not read bundle settings: {e}; falling back to 'foundation'")

        return "foundation"

    async def _get_or_create_prepared(
        self, project_path: Optional[str], bundle_name: Optional[str] = None
    ) -> Any:
        """Load and cache a PreparedBundle using the CLI's full bundle machinery.

        Delegates to ``resolve_bundle_config()`` from ``amplifier_app_cli``, which:
          - Discovers the bundle URI (well-known bundles, user-added bundles)
          - Downloads and installs modules from git sources
          - Composes app-level behaviors (modes, notifications, etc.)
          - Injects providers from ``~/.amplifier/settings.yaml``
          - Applies tool and hook overrides from settings
          - Expands environment variable references (``${API_KEY}``)

        The result is a ``PreparedBundle`` whose ``create_session()`` will have
        providers properly mounted — identical behavior to ``amplifier run``.

        Args:
            project_path: Project directory, or None for the default bundle.
            bundle_name: Pre-resolved bundle name (avoids a second settings read when
                the caller already resolved it via ``_get_bundle_name``).  If omitted,
                ``_get_bundle_name(project_path)`` is called internally.

        Returns:
            PreparedBundle instance (cached after first load).

        Raises:
            RuntimeError: If amplifier_app_cli is not installed, or preparation fails.
        """
        if bundle_name is None:
            bundle_name = self._get_bundle_name(project_path)
        cache_key = (bundle_name, project_path)

        # Fast path: already cached
        if cache_key in self.prepared_bundles:
            return self.prepared_bundles[cache_key]

        # Slow path: load under lock (double-check after acquiring)
        async with self._bundle_lock:
            if cache_key in self.prepared_bundles:
                return self.prepared_bundles[cache_key]

            logger.info(
                f"Loading Amplifier bundle '{bundle_name}' (project: {project_path or '(default)'})"
            )

            try:
                from amplifier_app_cli.lib.settings import AppSettings, SettingsPaths  # type: ignore[import]
                from amplifier_app_cli.runtime.config import resolve_bundle_config  # type: ignore[import]
            except ImportError as e:
                raise RuntimeError(
                    "amplifier_app_cli is not installed or not accessible. "
                    "This connector requires the Amplifier CLI. "
                    "Ensure you are running within the amplifier uv environment "
                    "(e.g. 'uv run slack-connector ...')."
                ) from e

            # Build AppSettings scoped to the project directory so that
            # provider overrides, tool overrides, and notification behaviors
            # are read from the right settings files.
            if project_path is not None:
                project_dir = Path(project_path).expanduser().resolve()
                paths = SettingsPaths(
                    global_settings=Path.home() / ".amplifier" / "settings.yaml",
                    project_settings=project_dir / ".amplifier" / "settings.yaml",
                    local_settings=project_dir / ".amplifier" / "settings.local.yaml",
                )
                app_settings = AppSettings(paths)
            else:
                app_settings = AppSettings()

            # Determine what to pass to resolve_bundle_config.
            #
            # AppBundleDiscovery (inside resolve_bundle_config) uses Path.cwd()
            # for its filesystem search paths.  Since the connector's CWD is not
            # the project directory, it won't find project-local bundles on disk.
            #
            # Work-around: if the project's settings.yaml has a URI registered
            # for the active bundle, pass that URI directly.  resolve_bundle_config
            # (and the underlying load_and_prepare_bundle) accept both names and
            # URIs — URIs skip filesystem discovery entirely.
            load_target = bundle_name

            if project_path is not None and bundle_name != "foundation":
                try:
                    added = app_settings.get_added_bundles()
                    raw_uri = added.get(bundle_name)
                    if raw_uri:
                        if raw_uri.startswith(("git+", "file://", "http://", "https://", "zip+")):
                            # Absolute URI — use directly
                            load_target = raw_uri
                            logger.debug(
                                f"Using registered URI for bundle '{bundle_name}': {raw_uri}"
                            )
                        elif raw_uri.startswith(("./", "../")):
                            # Relative path stored in project settings — resolve
                            # relative to the project directory
                            project_dir = Path(project_path).expanduser().resolve()
                            resolved = (project_dir / raw_uri).resolve()
                            load_target = f"file://{resolved}"
                            logger.debug(
                                f"Resolved relative bundle URI '{raw_uri}' → '{load_target}'"
                            )
                        else:
                            # Treat as a bundle name for discovery (e.g. user-added global)
                            load_target = raw_uri
                except Exception as e:
                    logger.debug(
                        f"Could not resolve bundle URI from settings: {e}; "
                        f"using name '{bundle_name}' for discovery"
                    )

            logger.debug(f"Calling resolve_bundle_config with load_target='{load_target}'")

            try:
                _, prepared = await resolve_bundle_config(
                    bundle_name=load_target,
                    app_settings=app_settings,
                    console=None,  # no CLI UI
                )
            except Exception as e:
                raise RuntimeError(f"Failed to prepare bundle '{bundle_name}': {e}") from e

            self.prepared_bundles[cache_key] = prepared
            logger.info(f"Bundle '{bundle_name}' prepared successfully")
            return prepared

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """
        Pre-load the default bundle using the CLI's bundle resolution machinery.

        This is an expensive one-time operation at startup (downloads/installs
        modules if needed).  Additional project bundles are loaded lazily on
        first use.

        Raises:
            RuntimeError: If amplifier_app_cli is not installed or accessible,
                or if bundle loading/preparation fails.
        """
        logger.info("Pre-loading default Amplifier bundle...")
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

        Sessions are cached per conversation_id. If the active bundle name
        changes for an existing session (e.g. the project switched from
        "foundation" to "my-agent"), the old session is closed and a new
        one is created with the correct bundle.

        Args:
            conversation_id: Stable identifier for the conversation
            approval_system: Platform-specific approval system
            project_path: Absolute path to the project directory. The project's
                .amplifier/settings.yaml is read to determine the active bundle.
                None = use the global/default bundle.
            display_system: Optional display system
            platform_tool: Optional platform-specific tool to mount (e.g. slack_reply)

        Returns:
            Tuple of (session, lock) for the conversation

        Raises:
            RuntimeError: If initialize() hasn't been called yet
        """
        if not self._initialized:
            raise RuntimeError(
                "SessionManager.initialize() must be called before creating sessions"
            )

        # Resolve the active bundle NAME for this project — this is THE key used
        # for change detection and session routing.
        active_bundle = self._get_bundle_name(project_path)

        # Detect bundle change → close old session so it's recreated with the right bundle.
        # We compare bundle NAMES (not file paths) so that:
        #   - switching from "foundation" to "my-agent" triggers a new session
        #   - two different projects both using "foundation" do NOT trigger recreation
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

            # Load (or retrieve cached) PreparedBundle for the active bundle.
            # Pass the already-resolved bundle_name so _get_or_create_prepared
            # doesn't need to call _get_bundle_name a second time.
            prepared = await self._get_or_create_prepared(project_path, bundle_name=active_bundle)

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

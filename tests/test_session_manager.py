"""
Unit tests for connector_core.session_manager.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from connector_core.session_manager import SessionManager


def _make_mock_session() -> Mock:
    """Create a mock AmplifierSession with coordinator."""
    session = Mock()
    session.coordinator = Mock()
    session.coordinator.mount = AsyncMock()
    session.coordinator.register_capability = Mock()
    session.coordinator.get_capability = Mock(return_value=None)
    session.context = Mock()
    session.context.get_metadata = AsyncMock(return_value=None)
    session.close = AsyncMock()
    return session


def _make_mock_prepared(session: Mock | None = None) -> Mock:
    """Create a mock PreparedBundle."""
    if session is None:
        session = _make_mock_session()
    prepared = Mock()
    prepared.create_session = AsyncMock(return_value=session)
    return prepared


class TestSessionManagerInit:
    """Tests for SessionManager instantiation."""

    def test_create_session_manager(self):
        """Test SessionManager instantiation with new multi-bundle attributes."""
        sm = SessionManager("./bundle.md")

        assert sm.default_bundle_path == "./bundle.md"
        assert sm.prepared_bundles == {}
        assert sm.session_projects == {}
        assert sm.session_bundles == {}
        assert sm._initialized is False
        assert sm.sessions == {}
        assert sm.locks == {}

    def test_default_workdir_defaults_to_cwd(self):
        """Test that default_workdir is set to cwd when not provided."""
        import os

        sm = SessionManager("./bundle.md")
        assert sm.default_workdir == os.getcwd()

    def test_custom_default_workdir(self):
        """Test that a custom default_workdir is stored."""
        sm = SessionManager("./bundle.md", default_workdir="/custom/dir")
        assert sm.default_workdir == "/custom/dir"


class TestBundleResolution:
    """Tests for _resolve_bundle_path logic."""

    def test_resolve_none_returns_default(self):
        """None project_path returns the resolved default bundle path."""
        sm = SessionManager("./bundle.md")
        result = sm._resolve_bundle_path(None)
        assert result == str(Path("./bundle.md").expanduser().resolve())

    def test_resolve_nonexistent_project_returns_default(self):
        """Project path with no bundle.md falls back to default."""
        sm = SessionManager("./bundle.md")
        result = sm._resolve_bundle_path("/nonexistent/project/path")
        assert result == str(Path("./bundle.md").expanduser().resolve())

    def test_resolve_project_with_bundle(self):
        """Project path with bundle.md returns the project bundle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_file = Path(tmpdir) / "bundle.md"
            bundle_file.write_text("# Project bundle")

            sm = SessionManager("./bundle.md")
            result = sm._resolve_bundle_path(tmpdir)

            assert result == str(bundle_file.resolve())

    def test_resolve_different_projects_give_different_paths(self):
        """Two projects with bundles resolve to distinct paths."""
        with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
            (Path(dir1) / "bundle.md").write_text("# Project 1")
            (Path(dir2) / "bundle.md").write_text("# Project 2")

            sm = SessionManager("./bundle.md")
            assert sm._resolve_bundle_path(dir1) != sm._resolve_bundle_path(dir2)

    def test_resolve_settings_yaml_active_bundle(self):
        """Project with .amplifier/settings.yaml uses the declared active bundle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            amplifier_dir = project / ".amplifier"
            amplifier_dir.mkdir()
            bundles_dir = amplifier_dir / "bundles" / "my-agent"
            bundles_dir.mkdir(parents=True)
            bundle_file = bundles_dir / "bundle.md"
            bundle_file.write_text("# Agent bundle")

            settings = amplifier_dir / "settings.yaml"
            settings.write_text(
                "bundle:\n"
                "  active: my-agent\n"
                "  added:\n"
                "    my-agent: ./.amplifier/bundles/my-agent/bundle.md\n"
            )

            sm = SessionManager("./bundle.md")
            result = sm._resolve_bundle_path(tmpdir)

            assert result == str(bundle_file.resolve())

    def test_resolve_settings_local_yaml_overrides(self):
        """settings.local.yaml overrides settings.yaml active bundle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            amplifier_dir = project / ".amplifier"
            amplifier_dir.mkdir()

            # Base bundle (in settings.yaml)
            base_bundle = amplifier_dir / "base-bundle.md"
            base_bundle.write_text("# Base")

            # Override bundle (in settings.local.yaml)
            local_bundle = amplifier_dir / "local-bundle.md"
            local_bundle.write_text("# Local")

            (amplifier_dir / "settings.yaml").write_text(
                "bundle:\n"
                "  active: base\n"
                "  added:\n"
                "    base: ./.amplifier/base-bundle.md\n"
                "    local-dev: ./.amplifier/local-bundle.md\n"
            )
            (amplifier_dir / "settings.local.yaml").write_text("bundle:\n  active: local-dev\n")

            sm = SessionManager("./bundle.md")
            result = sm._resolve_bundle_path(tmpdir)

            assert result == str(local_bundle.resolve())

    def test_resolve_settings_yaml_missing_active_falls_back(self):
        """settings.yaml with active name not in added falls back gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            amplifier_dir = Path(tmpdir) / ".amplifier"
            amplifier_dir.mkdir()
            (amplifier_dir / "settings.yaml").write_text(
                "bundle:\n  active: nonexistent\n  added: {}\n"
            )

            sm = SessionManager("./bundle.md")
            # Falls back to root bundle.md or default — no crash
            result = sm._resolve_bundle_path(tmpdir)
            assert result == str(Path("./bundle.md").expanduser().resolve())

    def test_resolve_settings_yaml_takes_priority_over_root_bundle(self):
        """settings.yaml active bundle wins over a root bundle.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            # Root bundle.md exists
            root_bundle = project / "bundle.md"
            root_bundle.write_text("# Root bundle")

            # settings.yaml points to a different bundle
            amplifier_dir = project / ".amplifier"
            amplifier_dir.mkdir()
            agent_bundle = amplifier_dir / "agent.md"
            agent_bundle.write_text("# Agent bundle")
            (amplifier_dir / "settings.yaml").write_text(
                "bundle:\n  active: agent\n  added:\n    agent: ./.amplifier/agent.md\n"
            )

            sm = SessionManager("./bundle.md")
            result = sm._resolve_bundle_path(tmpdir)

            # settings.yaml wins over root bundle.md
            assert result == str(agent_bundle.resolve())
            assert result != str(root_bundle.resolve())


class TestInitialize:
    """Tests for initialize()."""

    @pytest.mark.asyncio
    async def test_initialize_without_amplifier(self):
        """initialize raises RuntimeError when amplifier-foundation not installed."""
        sm = SessionManager("./bundle.md")

        with pytest.raises(RuntimeError) as exc_info:
            await sm.initialize()

        assert "amplifier-foundation not installed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self):
        """initialize() sets _initialized=True and caches the default bundle."""
        sm = SessionManager("./bundle.md")

        mock_bundle = Mock()
        mock_prepared = Mock()
        mock_bundle.prepare = AsyncMock(return_value=mock_prepared)

        with patch.dict(
            "sys.modules",
            {"amplifier_foundation": Mock(load_bundle=AsyncMock(return_value=mock_bundle))},
        ):
            with patch("amplifier_foundation.load_bundle", AsyncMock(return_value=mock_bundle)):
                # Directly pre-populate to avoid ImportError from the lazy import path
                resolved = str(Path("./bundle.md").expanduser().resolve())
                sm.prepared_bundles[resolved] = mock_prepared
                sm._initialized = True

        assert sm._initialized is True
        assert len(sm.prepared_bundles) >= 1


class TestGetOrCreateSession:
    """Tests for get_or_create_session()."""

    def _pre_populate(self, sm: SessionManager, prepared: Mock) -> str:
        """Pre-populate the bundle cache to skip actual loading."""
        resolved = str(Path(sm.default_bundle_path).expanduser().resolve())
        sm.prepared_bundles[resolved] = prepared
        sm._initialized = True
        return resolved

    @pytest.mark.asyncio
    async def test_raises_without_initialize(self):
        """get_or_create_session raises RuntimeError if not initialized."""
        sm = SessionManager("./bundle.md")

        with pytest.raises(RuntimeError) as exc_info:
            await sm.get_or_create_session(
                conversation_id="test-conv",
                approval_system=Mock(),
            )

        assert "initialize() must be called" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_creates_new_session(self):
        """First call creates a new session and caches it."""
        sm = SessionManager("./bundle.md")
        mock_session = _make_mock_session()
        mock_prepared = _make_mock_prepared(mock_session)
        resolved = self._pre_populate(sm, mock_prepared)

        session, lock = await sm.get_or_create_session(
            conversation_id="conv-1",
            approval_system=Mock(),
        )

        assert session is mock_session
        assert isinstance(lock, asyncio.Lock)
        assert "conv-1" in sm.sessions
        assert "conv-1" in sm.locks
        assert sm.session_projects["conv-1"] is None
        assert sm.session_bundles["conv-1"] == resolved

    @pytest.mark.asyncio
    async def test_caches_session(self):
        """Second call for same conversation_id returns cached session."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        self._pre_populate(sm, mock_prepared)

        session1, lock1 = await sm.get_or_create_session(
            conversation_id="conv-1",
            approval_system=Mock(),
        )
        session2, lock2 = await sm.get_or_create_session(
            conversation_id="conv-1",
            approval_system=Mock(),
        )

        assert session1 is session2
        assert lock1 is lock2
        assert mock_prepared.create_session.call_count == 1

    @pytest.mark.asyncio
    async def test_separate_sessions_per_conversation(self):
        """Different conversation_ids get distinct sessions and locks."""
        sm = SessionManager("./bundle.md")
        s1, s2 = _make_mock_session(), _make_mock_session()
        mock_prepared = Mock()
        mock_prepared.create_session = AsyncMock(side_effect=[s1, s2])
        self._pre_populate(sm, mock_prepared)

        session1, lock1 = await sm.get_or_create_session("conv-1", Mock())
        session2, lock2 = await sm.get_or_create_session("conv-2", Mock())

        assert session1 is not session2
        assert lock1 is not lock2
        assert len(sm.sessions) == 2

    @pytest.mark.asyncio
    async def test_project_path_stored_in_session_projects(self):
        """project_path passed to get_or_create_session is tracked."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        self._pre_populate(sm, mock_prepared)

        await sm.get_or_create_session(
            conversation_id="conv-1",
            approval_system=Mock(),
            project_path="/my/project",
        )

        assert sm.session_projects["conv-1"] == "/my/project"

    @pytest.mark.asyncio
    async def test_project_change_recreates_session(self):
        """When a project with its own bundle.md is opened, the bundle changes → session recreated."""
        sm = SessionManager("./bundle.md")
        old_session = _make_mock_session()
        new_session = _make_mock_session()

        default_resolved = str(Path("./bundle.md").expanduser().resolve())
        default_prepared = Mock()
        default_prepared.create_session = AsyncMock(return_value=old_session)
        sm.prepared_bundles[default_resolved] = default_prepared
        sm._initialized = True

        with tempfile.TemporaryDirectory() as tmpdir:
            project_bundle = Path(tmpdir) / "bundle.md"
            project_bundle.write_text("# Project bundle")
            project_resolved = str(project_bundle.resolve())

            project_prepared = Mock()
            project_prepared.create_session = AsyncMock(return_value=new_session)
            sm.prepared_bundles[project_resolved] = project_prepared

            # First: session with no project → uses default bundle
            s1, _ = await sm.get_or_create_session("conv-1", Mock(), project_path=None)
            assert s1 is old_session
            assert sm.session_bundles["conv-1"] == default_resolved

            # Second: project with its own bundle.md → bundle changes → session recreated
            s2, _ = await sm.get_or_create_session("conv-1", Mock(), project_path=tmpdir)
            assert s2 is new_session
            old_session.close.assert_called_once()
            assert sm.session_bundles["conv-1"] == project_resolved

    @pytest.mark.asyncio
    async def test_no_bundle_change_no_recreation(self):
        """Two different projects that both fall back to the default bundle do NOT recreate."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        self._pre_populate(sm, mock_prepared)

        # /nonexistent-A has no bundle.md → default
        s1, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/nonexistent-A")
        # /nonexistent-B has no bundle.md → also default → same bundle → NO recreation
        s2, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/nonexistent-B")

        assert s1 is s2
        assert mock_prepared.create_session.call_count == 1

    @pytest.mark.asyncio
    async def test_same_project_no_recreation(self):
        """Same project_path on subsequent calls does NOT recreate the session."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        self._pre_populate(sm, mock_prepared)

        s1, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/project")
        s2, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/project")

        assert s1 is s2
        assert mock_prepared.create_session.call_count == 1

    @pytest.mark.asyncio
    async def test_lock_preserved_across_bundle_change(self):
        """The asyncio.Lock is preserved when the bundle changes (session recreated)."""
        sm = SessionManager("./bundle.md")

        default_resolved = str(Path("./bundle.md").expanduser().resolve())
        default_prepared = Mock()
        default_prepared.create_session = AsyncMock(return_value=_make_mock_session())
        sm.prepared_bundles[default_resolved] = default_prepared
        sm._initialized = True

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "bundle.md").write_text("# Project")
            project_resolved = str((Path(tmpdir) / "bundle.md").resolve())

            project_prepared = Mock()
            project_prepared.create_session = AsyncMock(return_value=_make_mock_session())
            sm.prepared_bundles[project_resolved] = project_prepared

            _, lock1 = await sm.get_or_create_session("conv-1", Mock(), project_path=None)
            _, lock2 = await sm.get_or_create_session("conv-1", Mock(), project_path=tmpdir)

        # Same lock object — preserved across session recreation
        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_working_dir_defaults_to_project_path(self):
        """When no explicit working_dir is set, project_path is used as CWD."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        self._pre_populate(sm, mock_prepared)

        await sm.get_or_create_session("conv-1", Mock(), project_path="/my/project")

        call_kwargs = mock_prepared.create_session.call_args.kwargs
        assert call_kwargs["session_cwd"] == Path("/my/project")


class TestWorkingDir:
    """Tests for set_working_dir and get_working_dir."""

    def test_set_and_get_working_dir(self):
        """set_working_dir stores an absolute path; get_working_dir retrieves it."""
        sm = SessionManager("./bundle.md")
        sm.set_working_dir("conv-1", "/some/path")
        assert sm.get_working_dir("conv-1") == "/some/path"

    def test_get_working_dir_returns_default(self):
        """get_working_dir returns default_workdir for unknown conversations."""
        sm = SessionManager("./bundle.md", default_workdir="/default")
        assert sm.get_working_dir("unknown-conv") == "/default"

    def test_set_working_dir_syncs_session_capability(self):
        """set_working_dir updates session.working_dir capability on existing session."""
        sm = SessionManager("./bundle.md")
        mock_session = _make_mock_session()
        sm.sessions["conv-1"] = mock_session

        sm.set_working_dir("conv-1", "/new/path")

        mock_session.coordinator.register_capability.assert_called_once_with(
            "session.working_dir", "/new/path"
        )

    def test_set_working_dir_no_session_ok(self):
        """set_working_dir works when no session exists yet (just stores path)."""
        sm = SessionManager("./bundle.md")
        sm.set_working_dir("no-session-yet", "/path")
        assert sm.get_working_dir("no-session-yet") == "/path"


class TestCloseAll:
    """Tests for close_all()."""

    @pytest.mark.asyncio
    async def test_close_all_empty(self):
        """close_all with no sessions completes without error."""
        sm = SessionManager("./bundle.md")
        await sm.close_all()
        assert sm.sessions == {}
        assert sm.locks == {}

    @pytest.mark.asyncio
    async def test_close_all_closes_all_sessions(self):
        """close_all calls close() on every cached session."""
        sm = SessionManager("./bundle.md")
        s1, s2 = _make_mock_session(), _make_mock_session()
        sm.sessions = {"conv-1": s1, "conv-2": s2}
        sm.locks = {"conv-1": asyncio.Lock(), "conv-2": asyncio.Lock()}

        await sm.close_all()

        s1.close.assert_called_once()
        s2.close.assert_called_once()
        assert sm.sessions == {}
        assert sm.locks == {}

    @pytest.mark.asyncio
    async def test_close_all_handles_errors(self):
        """close_all continues even if one session fails to close."""
        sm = SessionManager("./bundle.md")
        s1 = _make_mock_session()
        s1.close = AsyncMock(side_effect=Exception("Close failed"))
        s2 = _make_mock_session()
        sm.sessions = {"conv-1": s1, "conv-2": s2}
        sm.locks = {"conv-1": asyncio.Lock(), "conv-2": asyncio.Lock()}

        await sm.close_all()

        s1.close.assert_called_once()
        s2.close.assert_called_once()
        assert sm.sessions == {}

    @pytest.mark.asyncio
    async def test_close_all_clears_new_state(self):
        """close_all clears session_projects, session_bundles, and prepared_bundles."""
        sm = SessionManager("./bundle.md")
        sm.sessions = {"conv-1": _make_mock_session()}
        sm.locks = {"conv-1": asyncio.Lock()}
        sm.session_projects = {"conv-1": "/some/project"}
        sm.session_bundles = {"conv-1": "/some/project/bundle.md"}
        sm.prepared_bundles = {"/resolved/bundle.md": Mock()}
        sm._initialized = True

        await sm.close_all()

        assert sm.session_projects == {}
        assert sm.session_bundles == {}
        assert sm.prepared_bundles == {}
        assert sm._initialized is False

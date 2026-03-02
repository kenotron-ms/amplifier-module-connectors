"""
Unit tests for connector_core.session_manager.
"""

import asyncio
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from connector_core.session_manager import SessionManager


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


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


@contextmanager
def _fake_cli(
    active_bundle: str | None = None,
    added_bundles: dict | None = None,
    prepared: Mock | None = None,
):
    """Context manager that injects a minimal fake amplifier_app_cli into sys.modules.

    This lets us test the connector's CLI-delegation logic without requiring
    the real amplifier_app_cli package to be installed in the test venv.

    Yields (mock_settings_instance, fake_config_module) so callers can inspect
    what was passed to AppSettings and resolve_bundle_config.
    """
    if added_bundles is None:
        added_bundles = {}
    if prepared is None:
        prepared = _make_mock_prepared()

    mock_settings_instance = Mock()
    mock_settings_instance.get_active_bundle = Mock(return_value=active_bundle)
    mock_settings_instance.get_added_bundles = Mock(return_value=added_bundles)

    fake_settings_lib = Mock()
    fake_settings_lib.AppSettings = Mock(return_value=mock_settings_instance)
    fake_settings_lib.SettingsPaths = Mock()

    fake_config = Mock()
    fake_config.resolve_bundle_config = AsyncMock(return_value=({}, prepared))

    modules = {
        "amplifier_app_cli": Mock(),
        "amplifier_app_cli.lib": Mock(),
        "amplifier_app_cli.lib.settings": fake_settings_lib,
        "amplifier_app_cli.runtime": Mock(),
        "amplifier_app_cli.runtime.config": fake_config,
    }
    with patch.dict("sys.modules", modules):
        yield mock_settings_instance, fake_config


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestSessionManagerInit:
    """Tests for SessionManager instantiation."""

    def test_create_session_manager(self):
        """Test SessionManager instantiation stores default_bundle_path for compat."""
        sm = SessionManager("./bundle.md")

        assert sm.default_bundle_path == "./bundle.md"
        assert sm.prepared_bundles == {}
        assert sm.session_projects == {}
        assert sm.session_bundles == {}
        assert sm._initialized is False
        assert sm.sessions == {}
        assert sm.locks == {}

    def test_create_session_manager_no_args(self):
        """SessionManager can be created with no arguments."""
        sm = SessionManager()
        assert sm.default_bundle_path == ""

    def test_default_workdir_defaults_to_cwd(self):
        """Test that default_workdir is set to cwd when not provided."""
        import os

        sm = SessionManager("./bundle.md")
        assert sm.default_workdir == os.getcwd()

    def test_custom_default_workdir(self):
        """Test that a custom default_workdir is stored."""
        sm = SessionManager("./bundle.md", default_workdir="/custom/dir")
        assert sm.default_workdir == "/custom/dir"

    def test_prepared_bundles_uses_tuple_keys(self):
        """prepared_bundles cache uses (bundle_name, project_path) tuple keys."""
        sm = SessionManager()
        mock_prepared = Mock()
        sm.prepared_bundles[("foundation", None)] = mock_prepared
        assert sm.prepared_bundles[("foundation", None)] is mock_prepared


# ---------------------------------------------------------------------------
# _get_bundle_name
# ---------------------------------------------------------------------------


class TestGetBundleName:
    """Tests for _get_bundle_name() — the CLI waterfall logic."""

    def test_returns_foundation_when_no_project(self):
        """None project_path returns 'foundation' when global settings have no bundle."""
        sm = SessionManager()
        with _fake_cli(active_bundle=None):
            result = sm._get_bundle_name(None)
        assert result == "foundation"

    def test_returns_foundation_when_project_has_no_settings(self):
        """Project with no .amplifier/settings.yaml returns 'foundation'."""
        sm = SessionManager()
        with _fake_cli(active_bundle=None):
            with tempfile.TemporaryDirectory() as tmpdir:
                result = sm._get_bundle_name(tmpdir)
        assert result == "foundation"

    def test_returns_active_bundle_from_project_settings(self):
        """Returns the bundle name given by AppSettings.get_active_bundle()."""
        sm = SessionManager()
        with _fake_cli(active_bundle="my-agent"):
            result = sm._get_bundle_name("/some/project")
        assert result == "my-agent"

    def test_uses_project_scoped_settings_paths(self):
        """When project_path is given, SettingsPaths is created with project-specific paths."""
        sm = SessionManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            with _fake_cli(active_bundle="my-agent") as (_, fake_config):
                fake_settings_lib = __import__(
                    "amplifier_app_cli.lib.settings", fromlist=["SettingsPaths"]
                )
                result = sm._get_bundle_name(tmpdir)
                # SettingsPaths should have been called (to build project-scoped paths)
                assert fake_settings_lib.SettingsPaths.called
        assert result == "my-agent"

    def test_falls_back_to_foundation_on_import_error(self):
        """Returns 'foundation' gracefully when amplifier_app_cli is not importable."""
        sm = SessionManager()
        with patch.dict(
            "sys.modules",
            {
                "amplifier_app_cli": None,
                "amplifier_app_cli.lib": None,
                "amplifier_app_cli.lib.settings": None,
            },
        ):
            result = sm._get_bundle_name(None)
        assert result == "foundation"

    def test_falls_back_to_foundation_on_exception(self):
        """Returns 'foundation' if AppSettings raises an unexpected exception."""
        sm = SessionManager()
        fake_settings_lib = Mock()
        fake_settings_lib.AppSettings = Mock(side_effect=RuntimeError("disk error"))
        fake_settings_lib.SettingsPaths = Mock()
        with patch.dict(
            "sys.modules",
            {
                "amplifier_app_cli": Mock(),
                "amplifier_app_cli.lib": Mock(),
                "amplifier_app_cli.lib.settings": fake_settings_lib,
            },
        ):
            result = sm._get_bundle_name(None)
        assert result == "foundation"

    def test_returns_global_bundle_when_no_project_path(self):
        """With project_path=None, uses default AppSettings (global scope).

        Verifies that AppSettings() was invoked (proving settings are read)
        by checking that get_active_bundle() returned the configured value.
        """
        sm = SessionManager()
        with _fake_cli(active_bundle="global-bundle") as (settings_instance, _):
            result = sm._get_bundle_name(None)
        # get_active_bundle() was called → AppSettings was used
        settings_instance.get_active_bundle.assert_called_once()
        assert result == "global-bundle"


# ---------------------------------------------------------------------------
# _get_or_create_prepared
# ---------------------------------------------------------------------------


class TestGetOrCreatePrepared:
    """Tests for _get_or_create_prepared() — CLI machinery delegation."""

    @pytest.mark.asyncio
    async def test_raises_when_amplifier_app_cli_missing(self):
        """_get_or_create_prepared raises RuntimeError if amplifier_app_cli not importable."""
        sm = SessionManager()
        sm._initialized = True

        with patch.dict(
            "sys.modules",
            {
                "amplifier_app_cli": None,
                "amplifier_app_cli.lib": None,
                "amplifier_app_cli.lib.settings": None,
                "amplifier_app_cli.runtime": None,
                "amplifier_app_cli.runtime.config": None,
            },
        ):
            with pytest.raises(RuntimeError) as exc_info:
                await sm._get_or_create_prepared(None)

        assert "amplifier_app_cli" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_calls_resolve_bundle_config(self):
        """_get_or_create_prepared delegates to resolve_bundle_config."""
        sm = SessionManager()
        sm._initialized = True
        mock_prepared = _make_mock_prepared()

        with _fake_cli(prepared=mock_prepared) as (_, fake_config):
            result = await sm._get_or_create_prepared(None)

        assert result is mock_prepared
        fake_config.resolve_bundle_config.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_caches_result(self):
        """Second call returns cached PreparedBundle without re-calling resolve_bundle_config."""
        sm = SessionManager()
        sm._initialized = True
        mock_prepared = _make_mock_prepared()

        with _fake_cli(prepared=mock_prepared) as (_, fake_config):
            result1 = await sm._get_or_create_prepared(None)
            result2 = await sm._get_or_create_prepared(None)

        assert result1 is result2
        assert fake_config.resolve_bundle_config.await_count == 1

    @pytest.mark.asyncio
    async def test_foundation_used_when_no_project(self):
        """When project_path=None, resolve_bundle_config receives 'foundation'."""
        sm = SessionManager()
        sm._initialized = True
        mock_prepared = _make_mock_prepared()
        captured: list = []

        async def capture_call(bundle_name, app_settings, console=None, **kwargs):
            captured.append(bundle_name)
            return {}, mock_prepared

        with _fake_cli() as (_, fake_config):
            fake_config.resolve_bundle_config = capture_call
            await sm._get_or_create_prepared(None, bundle_name="foundation")

        assert captured == ["foundation"]

    @pytest.mark.asyncio
    async def test_uses_git_uri_when_registered(self):
        """If project settings has a git URI for the active bundle, it is passed directly."""
        sm = SessionManager()
        sm._initialized = True
        mock_prepared = _make_mock_prepared()
        captured: list = []

        async def capture_call(bundle_name, app_settings, console=None, **kwargs):
            captured.append(bundle_name)
            return {}, mock_prepared

        git_uri = "git+https://github.com/org/my-bundle@main"
        with _fake_cli(active_bundle="my-agent", added_bundles={"my-agent": git_uri}) as (
            _,
            fake_config,
        ):
            fake_config.resolve_bundle_config = capture_call
            with tempfile.TemporaryDirectory() as tmpdir:
                await sm._get_or_create_prepared(tmpdir, bundle_name="my-agent")

        assert captured == [git_uri]

    @pytest.mark.asyncio
    async def test_resolves_relative_uri_to_file_uri(self):
        """Relative URIs in bundle.added are resolved to absolute file:// URIs."""
        sm = SessionManager()
        sm._initialized = True
        mock_prepared = _make_mock_prepared()
        captured: list = []

        async def capture_call(bundle_name, app_settings, console=None, **kwargs):
            captured.append(bundle_name)
            return {}, mock_prepared

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the bundle directory so the path exists
            bundle_dir = Path(tmpdir) / ".amplifier" / "bundles" / "my-agent"
            bundle_dir.mkdir(parents=True)
            (bundle_dir / "bundle.md").write_text("# Agent")

            relative_uri = "./.amplifier/bundles/my-agent"
            with _fake_cli(
                active_bundle="my-agent", added_bundles={"my-agent": relative_uri}
            ) as (_, fake_config):
                fake_config.resolve_bundle_config = capture_call
                await sm._get_or_create_prepared(tmpdir, bundle_name="my-agent")

        assert len(captured) == 1
        assert captured[0].startswith("file://")
        assert "my-agent" in captured[0]

    @pytest.mark.asyncio
    async def test_uses_preresolved_bundle_name(self):
        """When bundle_name is pre-supplied, _get_bundle_name is NOT called."""
        sm = SessionManager()
        sm._initialized = True
        mock_prepared = _make_mock_prepared()
        sm._get_bundle_name = Mock(return_value="should-not-be-called")

        with _fake_cli(prepared=mock_prepared):
            await sm._get_or_create_prepared(None, bundle_name="foundation")

        sm._get_bundle_name.assert_not_called()


# ---------------------------------------------------------------------------
# initialize()
# ---------------------------------------------------------------------------


class TestInitialize:
    """Tests for initialize()."""

    @pytest.mark.asyncio
    async def test_initialize_without_amplifier_app_cli(self):
        """initialize raises RuntimeError when amplifier_app_cli not installed."""
        sm = SessionManager("./bundle.md")

        with patch.dict(
            "sys.modules",
            {
                "amplifier_app_cli": None,
                "amplifier_app_cli.lib": None,
                "amplifier_app_cli.lib.settings": None,
                "amplifier_app_cli.runtime": None,
                "amplifier_app_cli.runtime.config": None,
            },
        ):
            with pytest.raises(RuntimeError) as exc_info:
                await sm.initialize()

        assert "amplifier_app_cli" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self):
        """initialize() sets _initialized=True and calls _get_or_create_prepared(None)."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()

        sm._get_or_create_prepared = AsyncMock(return_value=mock_prepared)

        await sm.initialize()

        assert sm._initialized is True
        sm._get_or_create_prepared.assert_awaited_once_with(None)


# ---------------------------------------------------------------------------
# get_or_create_session()
# ---------------------------------------------------------------------------


class TestGetOrCreateSession:
    """Tests for get_or_create_session()."""

    def _pre_populate(
        self,
        sm: SessionManager,
        prepared: Mock,
        bundle_name: str = "foundation",
        project_path: str | None = None,
    ) -> str:
        """Pre-populate the bundle cache and mock _get_bundle_name.

        This lets session tests run without any CLI imports.  Returns the
        bundle name (for use in assertions).
        """
        sm.prepared_bundles[(bundle_name, project_path)] = prepared
        sm._get_bundle_name = Mock(return_value=bundle_name)
        sm._initialized = True
        return bundle_name

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
        bundle_name = self._pre_populate(sm, mock_prepared)

        session, lock = await sm.get_or_create_session(
            conversation_id="conv-1",
            approval_system=Mock(),
        )

        assert session is mock_session
        assert isinstance(lock, asyncio.Lock)
        assert "conv-1" in sm.sessions
        assert "conv-1" in sm.locks
        assert sm.session_projects["conv-1"] is None
        assert sm.session_bundles["conv-1"] == bundle_name

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
        self._pre_populate(sm, mock_prepared, project_path="/my/project")

        await sm.get_or_create_session(
            conversation_id="conv-1",
            approval_system=Mock(),
            project_path="/my/project",
        )

        assert sm.session_projects["conv-1"] == "/my/project"

    @pytest.mark.asyncio
    async def test_project_change_recreates_session(self):
        """Switching to a project with a different bundle name forces session recreation."""
        sm = SessionManager("./bundle.md")
        old_session = _make_mock_session()
        new_session = _make_mock_session()

        default_prepared = Mock()
        default_prepared.create_session = AsyncMock(return_value=old_session)

        project_prepared = Mock()
        project_prepared.create_session = AsyncMock(return_value=new_session)

        sm.prepared_bundles[("foundation", None)] = default_prepared
        sm.prepared_bundles[("my-agent", "/project")] = project_prepared
        sm._initialized = True

        # Each call to get_or_create_session invokes _get_bundle_name exactly once
        # (the result is forwarded into _get_or_create_prepared, avoiding a second read).
        sm._get_bundle_name = Mock(side_effect=["foundation", "my-agent"])

        # First call: no project → "foundation"
        s1, _ = await sm.get_or_create_session("conv-1", Mock(), project_path=None)
        assert s1 is old_session
        assert sm.session_bundles["conv-1"] == "foundation"

        # Second call: different bundle name → session recreated
        s2, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/project")
        assert s2 is new_session
        old_session.close.assert_called_once()
        assert sm.session_bundles["conv-1"] == "my-agent"

    @pytest.mark.asyncio
    async def test_no_bundle_change_no_recreation(self):
        """Two projects both returning 'foundation' do NOT trigger session recreation."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        sm._initialized = True
        # Both project_paths resolve to the same bundle name
        sm._get_bundle_name = Mock(return_value="foundation")
        sm.prepared_bundles[("foundation", "/nonexistent-A")] = mock_prepared
        sm.prepared_bundles[("foundation", "/nonexistent-B")] = mock_prepared

        s1, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/nonexistent-A")
        s2, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/nonexistent-B")

        assert s1 is s2
        # create_session called only for the first get_or_create_session
        assert mock_prepared.create_session.call_count == 1

    @pytest.mark.asyncio
    async def test_same_project_no_recreation(self):
        """Same project_path on subsequent calls does NOT recreate the session."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        self._pre_populate(sm, mock_prepared, project_path="/project")

        s1, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/project")
        s2, _ = await sm.get_or_create_session("conv-1", Mock(), project_path="/project")

        assert s1 is s2
        assert mock_prepared.create_session.call_count == 1

    @pytest.mark.asyncio
    async def test_lock_preserved_across_bundle_change(self):
        """The asyncio.Lock is preserved when the bundle changes (session recreated)."""
        sm = SessionManager("./bundle.md")

        default_prepared = Mock()
        default_prepared.create_session = AsyncMock(return_value=_make_mock_session())
        project_prepared = Mock()
        project_prepared.create_session = AsyncMock(return_value=_make_mock_session())

        sm.prepared_bundles[("foundation", None)] = default_prepared
        sm.prepared_bundles[("my-agent", "/project")] = project_prepared
        sm._initialized = True
        sm._get_bundle_name = Mock(side_effect=["foundation", "my-agent"])

        _, lock1 = await sm.get_or_create_session("conv-1", Mock(), project_path=None)
        _, lock2 = await sm.get_or_create_session("conv-1", Mock(), project_path="/project")

        # Same lock object — preserved across session recreation
        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_working_dir_defaults_to_project_path(self):
        """When no explicit working_dir is set, project_path is used as CWD."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        self._pre_populate(sm, mock_prepared, project_path="/my/project")

        await sm.get_or_create_session("conv-1", Mock(), project_path="/my/project")

        call_kwargs = mock_prepared.create_session.call_args.kwargs
        assert call_kwargs["session_cwd"] == Path("/my/project")

    @pytest.mark.asyncio
    async def test_session_bundles_stores_bundle_name(self):
        """session_bundles[conv_id] stores the bundle NAME, not a file path."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        self._pre_populate(sm, mock_prepared, bundle_name="my-custom-bundle")

        await sm.get_or_create_session("conv-1", Mock())

        assert sm.session_bundles["conv-1"] == "my-custom-bundle"

    @pytest.mark.asyncio
    async def test_bundle_name_passed_to_get_or_create_prepared(self):
        """get_or_create_session passes the resolved bundle_name into _get_or_create_prepared
        so the name is resolved only once per request (not twice)."""
        sm = SessionManager("./bundle.md")
        mock_prepared = _make_mock_prepared()
        sm._initialized = True
        sm._get_bundle_name = Mock(return_value="foundation")
        sm._get_or_create_prepared = AsyncMock(return_value=mock_prepared)

        await sm.get_or_create_session("conv-1", Mock())

        # _get_bundle_name called once
        assert sm._get_bundle_name.call_count == 1
        # _get_or_create_prepared received the pre-resolved name
        sm._get_or_create_prepared.assert_awaited_once_with(None, bundle_name="foundation")


# ---------------------------------------------------------------------------
# set_working_dir / get_working_dir
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# close_all()
# ---------------------------------------------------------------------------


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
        sm.session_bundles = {"conv-1": "foundation"}  # bundle name, not file path
        sm.prepared_bundles = {("foundation", None): Mock()}
        sm._initialized = True

        await sm.close_all()

        assert sm.session_projects == {}
        assert sm.session_bundles == {}
        assert sm.prepared_bundles == {}
        assert sm._initialized is False

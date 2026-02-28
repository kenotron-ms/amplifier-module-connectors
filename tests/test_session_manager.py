"""
Unit tests for connector_core.session_manager.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.connector_core.session_manager import SessionManager


class TestSessionManager:
    """Tests for SessionManager class."""
    
    def test_create_session_manager(self):
        """Test SessionManager instantiation."""
        sm = SessionManager("./bundle.md")
        
        assert sm.bundle_path == "./bundle.md"
        assert sm.prepared is None
        assert sm.sessions == {}
        assert sm.locks == {}
    
    @pytest.mark.asyncio
    async def test_initialize_without_amplifier(self):
        """Test initialize raises RuntimeError when amplifier-foundation not installed."""
        sm = SessionManager("./bundle.md")
        
        with pytest.raises(RuntimeError) as exc_info:
            await sm.initialize()
        
        assert "amplifier-foundation not installed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_with_mock_amplifier(self):
        """Test initialize with mocked amplifier-foundation."""
        sm = SessionManager("./bundle.md")
        
        # Mock the amplifier-foundation module
        mock_bundle = Mock()
        mock_prepared = Mock()
        mock_bundle.prepare = AsyncMock(return_value=mock_prepared)
        
        with patch('src.connector_core.session_manager.load_bundle', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = mock_bundle
            
            # Patch the import
            with patch.dict('sys.modules', {'amplifier_foundation': Mock(load_bundle=mock_load)}):
                await sm.initialize()
        
        assert sm.prepared == mock_prepared
    
    @pytest.mark.asyncio
    async def test_get_or_create_session_without_initialize(self):
        """Test get_or_create_session raises error if not initialized."""
        sm = SessionManager("./bundle.md")
        
        with pytest.raises(RuntimeError) as exc_info:
            await sm.get_or_create_session(
                conversation_id="test-conv",
                approval_system=Mock()
            )
        
        assert "initialize() must be called" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new(self):
        """Test get_or_create_session creates new session."""
        sm = SessionManager("./bundle.md")
        
        # Mock prepared bundle
        mock_session = Mock()
        mock_session.coordinator = Mock()
        mock_session.coordinator.mount = AsyncMock()
        
        mock_prepared = Mock()
        mock_prepared.create_session = AsyncMock(return_value=mock_session)
        sm.prepared = mock_prepared
        
        approval_system = Mock()
        
        session, lock = await sm.get_or_create_session(
            conversation_id="test-conv-1",
            approval_system=approval_system
        )
        
        assert session == mock_session
        assert isinstance(lock, asyncio.Lock)
        assert "test-conv-1" in sm.sessions
        assert "test-conv-1" in sm.locks
    
    @pytest.mark.asyncio
    async def test_get_or_create_session_caching(self):
        """Test get_or_create_session returns cached session."""
        sm = SessionManager("./bundle.md")
        
        # Mock prepared bundle
        mock_session = Mock()
        mock_session.coordinator = Mock()
        mock_session.coordinator.mount = AsyncMock()
        
        mock_prepared = Mock()
        mock_prepared.create_session = AsyncMock(return_value=mock_session)
        sm.prepared = mock_prepared
        
        approval_system = Mock()
        
        # First call - creates session
        session1, lock1 = await sm.get_or_create_session(
            conversation_id="test-conv",
            approval_system=approval_system
        )
        
        # Second call - returns cached session
        session2, lock2 = await sm.get_or_create_session(
            conversation_id="test-conv",
            approval_system=approval_system
        )
        
        assert session1 is session2
        assert lock1 is lock2
        assert mock_prepared.create_session.call_count == 1  # Only called once
    
    @pytest.mark.asyncio
    async def test_get_or_create_session_different_conversations(self):
        """Test get_or_create_session creates separate sessions for different conversations."""
        sm = SessionManager("./bundle.md")
        
        # Mock prepared bundle
        mock_session1 = Mock()
        mock_session1.coordinator = Mock()
        mock_session1.coordinator.mount = AsyncMock()
        
        mock_session2 = Mock()
        mock_session2.coordinator = Mock()
        mock_session2.coordinator.mount = AsyncMock()
        
        mock_prepared = Mock()
        mock_prepared.create_session = AsyncMock(side_effect=[mock_session1, mock_session2])
        sm.prepared = mock_prepared
        
        approval_system = Mock()
        
        # Create two different sessions
        session1, lock1 = await sm.get_or_create_session(
            conversation_id="conv-1",
            approval_system=approval_system
        )
        
        session2, lock2 = await sm.get_or_create_session(
            conversation_id="conv-2",
            approval_system=approval_system
        )
        
        assert session1 is not session2
        assert lock1 is not lock2
        assert len(sm.sessions) == 2
        assert len(sm.locks) == 2
    
    @pytest.mark.asyncio
    async def test_close_all_empty(self):
        """Test close_all with no sessions."""
        sm = SessionManager("./bundle.md")
        
        # Should not raise error
        await sm.close_all()
        
        assert sm.sessions == {}
        assert sm.locks == {}
    
    @pytest.mark.asyncio
    async def test_close_all_with_sessions(self):
        """Test close_all closes all sessions."""
        sm = SessionManager("./bundle.md")
        
        # Create mock sessions
        mock_session1 = Mock()
        mock_session1.close = AsyncMock()
        mock_session2 = Mock()
        mock_session2.close = AsyncMock()
        
        sm.sessions = {
            "conv-1": mock_session1,
            "conv-2": mock_session2
        }
        sm.locks = {
            "conv-1": asyncio.Lock(),
            "conv-2": asyncio.Lock()
        }
        
        await sm.close_all()
        
        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()
        assert sm.sessions == {}
        assert sm.locks == {}
    
    @pytest.mark.asyncio
    async def test_close_all_handles_errors(self):
        """Test close_all continues even if a session fails to close."""
        sm = SessionManager("./bundle.md")
        
        # Create mock sessions - one raises error
        mock_session1 = Mock()
        mock_session1.close = AsyncMock(side_effect=Exception("Close failed"))
        mock_session2 = Mock()
        mock_session2.close = AsyncMock()
        
        sm.sessions = {
            "conv-1": mock_session1,
            "conv-2": mock_session2
        }
        sm.locks = {
            "conv-1": asyncio.Lock(),
            "conv-2": asyncio.Lock()
        }
        
        # Should not raise error
        await sm.close_all()
        
        # Both sessions should have been attempted
        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()
        assert sm.sessions == {}
        assert sm.locks == {}

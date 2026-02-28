"""
Tests for TeamsAdapter.

These tests verify the TeamsAdapter implements the PlatformAdapter protocol
correctly and handles Bot Framework activities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from src.connector_core.models import UnifiedMessage
from src.teams_connector.adapter import TeamsAdapter


@pytest.fixture
def teams_adapter():
    """Create a TeamsAdapter instance for testing."""
    return TeamsAdapter(
        app_id="test-app-id",
        app_password="test-app-password",
        port=3978
    )


class TestTeamsAdapterInitialization:
    """Test TeamsAdapter initialization and configuration."""
    
    def test_init_stores_credentials(self, teams_adapter):
        """Test that initialization stores credentials correctly."""
        assert teams_adapter.app_id == "test-app-id"
        assert teams_adapter.app_password == "test-app-password"
        assert teams_adapter.port == 3978
    
    def test_init_with_custom_port(self):
        """Test initialization with custom port."""
        adapter = TeamsAdapter(
            app_id="test",
            app_password="test",
            port=8080
        )
        assert adapter.port == 8080
    
    def test_initial_state(self, teams_adapter):
        """Test initial state before startup."""
        assert teams_adapter._app is None
        assert teams_adapter._runner is None
        assert teams_adapter._site is None
        assert teams_adapter._message_handler is None
        assert len(teams_adapter._conversation_references) == 0


class TestTeamsAdapterStartup:
    """Test TeamsAdapter startup and initialization."""
    
    @pytest.mark.asyncio
    async def test_startup_creates_app(self, teams_adapter):
        """Test that startup creates aiohttp application."""
        await teams_adapter.startup()
        
        assert teams_adapter._app is not None
        assert isinstance(teams_adapter._app, web.Application)
    
    @pytest.mark.asyncio
    async def test_startup_registers_routes(self, teams_adapter):
        """Test that startup registers webhook routes."""
        await teams_adapter.startup()
        
        # Check routes exist (use resource.canonical for path)
        routes = [r.resource.canonical for r in teams_adapter._app.router.routes()]
        assert '/api/messages' in routes
        assert '/health' in routes


class TestTeamsAdapterShutdown:
    """Test TeamsAdapter shutdown and cleanup."""
    
    @pytest.mark.asyncio
    async def test_shutdown_cleans_up(self, teams_adapter):
        """Test that shutdown cleans up resources."""
        await teams_adapter.startup()
        
        # Add some conversation references
        teams_adapter._conversation_references['conv1'] = {'test': 'data'}
        
        await teams_adapter.shutdown()
        
        # Verify cleanup
        assert len(teams_adapter._conversation_references) == 0
    
    @pytest.mark.asyncio
    async def test_shutdown_without_startup(self, teams_adapter):
        """Test that shutdown works even without startup."""
        # Should not raise
        await teams_adapter.shutdown()


class TestTeamsAdapterConversationId:
    """Test TeamsAdapter conversation ID generation."""
    
    def test_get_conversation_id_channel_only(self, teams_adapter):
        """Test conversation ID for conversation-level."""
        conv_id = teams_adapter.get_conversation_id("19:meeting_abc123")
        assert conv_id == "teams-19:meeting_abc123"
    
    def test_get_conversation_id_with_thread(self, teams_adapter):
        """Test conversation ID for threaded conversation."""
        conv_id = teams_adapter.get_conversation_id(
            "19:meeting_abc123",
            "1234567890"
        )
        assert conv_id == "teams-19:meeting_abc123-1234567890"
    
    def test_get_conversation_id_stability(self, teams_adapter):
        """Test that conversation IDs are stable across calls."""
        conv_id1 = teams_adapter.get_conversation_id("19:meeting_abc123", "123")
        conv_id2 = teams_adapter.get_conversation_id("19:meeting_abc123", "123")
        assert conv_id1 == conv_id2


class TestTeamsAdapterSendMessage:
    """Test TeamsAdapter message sending."""
    
    @pytest.mark.asyncio
    async def test_send_message_returns_id(self, teams_adapter):
        """Test that send_message returns a message ID."""
        await teams_adapter.startup()
        
        msg_id = await teams_adapter.send_message(
            channel="19:meeting_abc123",
            text="Hello, Teams!"
        )
        
        assert msg_id is not None
        assert msg_id.startswith("teams-msg-")
    
    @pytest.mark.asyncio
    async def test_send_message_with_thread(self, teams_adapter):
        """Test sending a message in a thread."""
        await teams_adapter.startup()
        
        msg_id = await teams_adapter.send_message(
            channel="19:meeting_abc123",
            text="Thread reply",
            thread_id="parent-activity-id"
        )
        
        assert msg_id is not None


class TestTeamsAdapterReactions:
    """Test TeamsAdapter reaction functionality."""
    
    @pytest.mark.asyncio
    async def test_add_reaction_does_not_raise(self, teams_adapter):
        """Test that add_reaction doesn't raise (placeholder)."""
        await teams_adapter.startup()
        
        # Should not raise (placeholder implementation)
        await teams_adapter.add_reaction(
            channel="19:meeting_abc123",
            message_id="1234567890",
            emoji="thumbsup"
        )


class TestTeamsAdapterApprovalPrompt:
    """Test TeamsAdapter approval prompt creation."""
    
    @pytest.mark.asyncio
    async def test_create_approval_prompt_not_implemented(self, teams_adapter):
        """Test that create_approval_prompt raises NotImplementedError."""
        await teams_adapter.startup()
        
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await teams_adapter.create_approval_prompt(
                channel="19:meeting_abc123",
                description="Approve this action?"
            )


class TestTeamsAdapterActivityHandling:
    """Test TeamsAdapter Bot Framework activity handling."""
    
    @pytest.mark.asyncio
    async def test_handle_message_activity_converts_to_unified(self, teams_adapter):
        """Test that message activities are converted to UnifiedMessage."""
        await teams_adapter.startup()
        
        # Set up message handler
        received_messages = []
        async def handler(msg: UnifiedMessage):
            received_messages.append(msg)
        
        teams_adapter._message_handler = handler
        
        # Simulate Bot Framework message activity
        activity = {
            'type': 'message',
            'id': 'activity-123',
            'conversation': {'id': '19:meeting_abc123'},
            'from': {'id': '29:user_xyz789', 'name': 'Test User'},
            'text': 'Hello bot!',
            'serviceUrl': 'https://smba.trafficmanager.net/teams/',
            'replyToId': None
        }
        
        await teams_adapter._handle_message_activity(activity)
        
        assert len(received_messages) == 1
        msg = received_messages[0]
        assert msg.platform == "teams"
        assert msg.channel_id == "19:meeting_abc123"
        assert msg.user_id == "29:user_xyz789"
        assert msg.text == "Hello bot!"
        assert msg.message_id == "activity-123"
        assert msg.thread_id is None
    
    @pytest.mark.asyncio
    async def test_handle_message_stores_conversation_reference(self, teams_adapter):
        """Test that message activities store conversation references."""
        await teams_adapter.startup()
        
        teams_adapter._message_handler = AsyncMock()
        
        activity = {
            'type': 'message',
            'id': 'activity-123',
            'conversation': {'id': '19:meeting_abc123'},
            'from': {'id': '29:user_xyz789'},
            'text': 'Test',
            'serviceUrl': 'https://smba.trafficmanager.net/teams/'
        }
        
        await teams_adapter._handle_message_activity(activity)
        
        # Verify conversation reference was stored
        assert '19:meeting_abc123' in teams_adapter._conversation_references
        ref = teams_adapter._conversation_references['19:meeting_abc123']
        assert ref['activity_id'] == 'activity-123'
        assert ref['service_url'] == 'https://smba.trafficmanager.net/teams/'
    
    @pytest.mark.asyncio
    async def test_handle_conversation_update_logs_member_added(self, teams_adapter):
        """Test that conversationUpdate activities are handled."""
        await teams_adapter.startup()
        
        activity = {
            'type': 'conversationUpdate',
            'membersAdded': [
                {'id': 'new-user-id', 'name': 'New User'}
            ],
            'recipient': {'id': 'bot-id'}
        }
        
        # Should not raise
        await teams_adapter._handle_conversation_update(activity)


class TestTeamsAdapterWebhook:
    """Test TeamsAdapter webhook endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, teams_adapter):
        """Test that health check endpoint works."""
        await teams_adapter.startup()
        
        # Create test request
        request = MagicMock(spec=web.Request)
        
        response = await teams_adapter._health_check(request)
        
        assert response.status == 200
        assert response.text == "Teams adapter is running"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

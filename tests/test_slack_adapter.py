"""
Tests for SlackAdapter.

These tests verify the SlackAdapter implements the PlatformAdapter protocol
correctly and handles Slack-specific functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.connector_core.models import UnifiedMessage
from src.slack_connector.adapter import SlackAdapter


@pytest.fixture
def slack_adapter():
    """Create a SlackAdapter instance for testing."""
    return SlackAdapter(
        app_token="xapp-test-token",
        bot_token="xoxb-test-token",
        allowed_channel="C123TEST"
    )


@pytest.fixture
def mock_bolt_app():
    """Create a mock Slack Bolt app."""
    app = MagicMock()
    app.client = AsyncMock()
    app.client.auth_test = AsyncMock(return_value={
        "user_id": "U123BOT",
        "user": "testbot"
    })
    app.client.chat_postMessage = AsyncMock(return_value={"ts": "1234567890.123456"})
    app.client.reactions_add = AsyncMock()
    return app


class TestSlackAdapterInitialization:
    """Test SlackAdapter initialization and configuration."""
    
    def test_init_stores_credentials(self, slack_adapter):
        """Test that initialization stores credentials correctly."""
        assert slack_adapter.app_token == "xapp-test-token"
        assert slack_adapter.bot_token == "xoxb-test-token"
        assert slack_adapter.allowed_channel == "C123TEST"
    
    def test_init_without_allowed_channel(self):
        """Test initialization without channel restriction."""
        adapter = SlackAdapter(
            app_token="xapp-test",
            bot_token="xoxb-test"
        )
        assert adapter.allowed_channel is None
    
    def test_initial_state(self, slack_adapter):
        """Test initial state before startup."""
        assert slack_adapter.bolt_app is None
        assert slack_adapter.handler is None
        assert slack_adapter.bot_user_id is None
        assert slack_adapter._message_handler is None


class TestSlackAdapterStartup:
    """Test SlackAdapter startup and authentication."""
    
    @pytest.mark.asyncio
    async def test_startup_initializes_bolt_app(self, slack_adapter, mock_bolt_app):
        """Test that startup creates Bolt app and authenticates."""
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        assert slack_adapter.bolt_app is not None
        assert slack_adapter.bot_user_id == "U123BOT"
        mock_bolt_app.client.auth_test.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_startup_handles_auth_failure(self, slack_adapter):
        """Test that startup raises ConnectionError on auth failure."""
        from slack_sdk.errors import SlackApiError
        
        mock_app = MagicMock()
        mock_app.client.auth_test = AsyncMock(
            side_effect=SlackApiError("Auth failed", response={"error": "invalid_auth"})
        )
        
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_app):
            with pytest.raises(ConnectionError, match="Slack authentication failed"):
                await slack_adapter.startup()


class TestSlackAdapterShutdown:
    """Test SlackAdapter shutdown and cleanup."""
    
    @pytest.mark.asyncio
    async def test_shutdown_closes_handler(self, slack_adapter, mock_bolt_app):
        """Test that shutdown closes Socket Mode handler."""
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        # Add a mock handler
        slack_adapter.handler = AsyncMock()
        slack_adapter.handler.close_async = AsyncMock()
        
        await slack_adapter.shutdown()
        
        slack_adapter.handler.close_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_handles_errors_gracefully(self, slack_adapter):
        """Test that shutdown handles errors without crashing."""
        slack_adapter.handler = AsyncMock()
        slack_adapter.handler.close_async = AsyncMock(side_effect=Exception("Close failed"))
        
        # Should not raise
        await slack_adapter.shutdown()


class TestSlackAdapterSendMessage:
    """Test SlackAdapter message sending."""
    
    @pytest.mark.asyncio
    async def test_send_message_to_channel(self, slack_adapter, mock_bolt_app):
        """Test sending a message to a channel."""
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        msg_id = await slack_adapter.send_message(
            channel="C123ABC",
            text="Hello, World!"
        )
        
        assert msg_id == "1234567890.123456"
        mock_bolt_app.client.chat_postMessage.assert_called_once_with(
            channel="C123ABC",
            thread_ts=None,
            text="Hello, World!",
            unfurl_links=False,
            unfurl_media=False
        )
    
    @pytest.mark.asyncio
    async def test_send_message_in_thread(self, slack_adapter, mock_bolt_app):
        """Test sending a message in a thread."""
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        await slack_adapter.send_message(
            channel="C123ABC",
            text="Thread reply",
            thread_id="1234567890.123456"
        )
        
        mock_bolt_app.client.chat_postMessage.assert_called_once_with(
            channel="C123ABC",
            thread_ts="1234567890.123456",
            text="Thread reply",
            unfurl_links=False,
            unfurl_media=False
        )
    
    @pytest.mark.asyncio
    async def test_send_message_before_startup_raises(self, slack_adapter):
        """Test that send_message raises if called before startup."""
        with pytest.raises(RuntimeError, match="Must call startup"):
            await slack_adapter.send_message("C123ABC", "Test")


class TestSlackAdapterReactions:
    """Test SlackAdapter reaction functionality."""
    
    @pytest.mark.asyncio
    async def test_add_reaction(self, slack_adapter, mock_bolt_app):
        """Test adding a reaction to a message."""
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        await slack_adapter.add_reaction(
            channel="C123ABC",
            message_id="1234567890.123456",
            emoji="thumbsup"
        )
        
        mock_bolt_app.client.reactions_add.assert_called_once_with(
            channel="C123ABC",
            timestamp="1234567890.123456",
            name="thumbsup"
        )
    
    @pytest.mark.asyncio
    async def test_add_reaction_handles_errors(self, slack_adapter, mock_bolt_app):
        """Test that reaction errors are handled gracefully."""
        from slack_sdk.errors import SlackApiError
        
        mock_bolt_app.client.reactions_add = AsyncMock(
            side_effect=SlackApiError("API error", response={"error": "already_reacted"})
        )
        
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        # Should not raise
        await slack_adapter.add_reaction("C123ABC", "1234567890.123456", "thumbsup")


class TestSlackAdapterConversationId:
    """Test SlackAdapter conversation ID generation."""
    
    def test_get_conversation_id_channel_only(self, slack_adapter):
        """Test conversation ID for channel-level conversation."""
        conv_id = slack_adapter.get_conversation_id("C123ABC")
        assert conv_id == "slack-C123ABC"
    
    def test_get_conversation_id_with_thread(self, slack_adapter):
        """Test conversation ID for threaded conversation."""
        conv_id = slack_adapter.get_conversation_id("C123ABC", "1234567890.123456")
        assert conv_id == "slack-C123ABC-1234567890.123456"
    
    def test_get_conversation_id_stability(self, slack_adapter):
        """Test that conversation IDs are stable across calls."""
        conv_id1 = slack_adapter.get_conversation_id("C123ABC", "1234567890.123456")
        conv_id2 = slack_adapter.get_conversation_id("C123ABC", "1234567890.123456")
        assert conv_id1 == conv_id2


class TestSlackAdapterApprovalPrompt:
    """Test SlackAdapter approval prompt creation."""
    
    @pytest.mark.asyncio
    async def test_create_approval_prompt(self, slack_adapter, mock_bolt_app):
        """Test creating an approval prompt."""
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        with patch('src.slack_connector.adapter.SlackApprovalSystem') as mock_approval:
            prompt = await slack_adapter.create_approval_prompt(
                channel="C123ABC",
                description="Approve this action?"
            )
            
            mock_approval.assert_called_once_with(
                client=mock_bolt_app.client,
                channel="C123ABC",
                thread_ts=None
            )
    
    @pytest.mark.asyncio
    async def test_create_approval_prompt_before_startup_raises(self, slack_adapter):
        """Test that create_approval_prompt raises if called before startup."""
        with pytest.raises(RuntimeError, match="Must call startup"):
            await slack_adapter.create_approval_prompt("C123ABC", "Test")


class TestSlackAdapterMessageHandling:
    """Test SlackAdapter message event handling."""
    
    @pytest.mark.asyncio
    async def test_handle_slack_message_converts_to_unified(self, slack_adapter, mock_bolt_app):
        """Test that Slack events are converted to UnifiedMessage."""
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        # Set up message handler
        received_messages = []
        async def handler(msg: UnifiedMessage):
            received_messages.append(msg)
        
        slack_adapter._message_handler = handler
        slack_adapter.bot_user_id = "U123BOT"
        
        # Simulate Slack event
        event = {
            "channel": "C123ABC",
            "user": "U456USER",
            "text": "Hello bot!",
            "ts": "1234567890.123456",
            "thread_ts": "1234567890.000000"
        }
        
        await slack_adapter._handle_slack_message(event)
        
        assert len(received_messages) == 1
        msg = received_messages[0]
        assert msg.platform == "slack"
        assert msg.channel_id == "C123ABC"
        assert msg.user_id == "U456USER"
        assert msg.text == "Hello bot!"
        assert msg.message_id == "1234567890.123456"
        assert msg.thread_id == "1234567890.000000"
    
    @pytest.mark.asyncio
    async def test_handle_slack_message_ignores_bot_messages(self, slack_adapter, mock_bolt_app):
        """Test that bot's own messages are ignored."""
        with patch('src.slack_connector.adapter.AsyncApp', return_value=mock_bolt_app):
            await slack_adapter.startup()
        
        received_messages = []
        async def handler(msg: UnifiedMessage):
            received_messages.append(msg)
        
        slack_adapter._message_handler = handler
        slack_adapter.bot_user_id = "U123BOT"
        
        # Bot's own message
        event = {
            "channel": "C123ABC",
            "user": "U123BOT",  # Same as bot_user_id
            "text": "My own message",
            "ts": "1234567890.123456"
        }
        
        await slack_adapter._handle_slack_message(event)
        
        assert len(received_messages) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

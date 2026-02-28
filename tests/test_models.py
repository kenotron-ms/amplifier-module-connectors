"""
Unit tests for connector_core.models.
"""

import pytest
from datetime import datetime
from src.connector_core.models import UnifiedMessage


class TestUnifiedMessage:
    """Tests for UnifiedMessage model."""
    
    def test_create_slack_message(self):
        """Test creating a Slack message."""
        now = datetime.now()
        msg = UnifiedMessage(
            platform="slack",
            channel_id="C123ABC",
            user_id="U456DEF",
            text="Hello, bot!",
            message_id="1234567890.123456",
            thread_id=None,
            timestamp=now,
            raw_event={"type": "message", "channel": "C123ABC"}
        )
        
        assert msg.platform == "slack"
        assert msg.channel_id == "C123ABC"
        assert msg.user_id == "U456DEF"
        assert msg.text == "Hello, bot!"
        assert msg.message_id == "1234567890.123456"
        assert msg.thread_id is None
        assert msg.timestamp == now
        assert msg.raw_event["type"] == "message"
    
    def test_create_teams_message(self):
        """Test creating a Teams message."""
        now = datetime.now()
        msg = UnifiedMessage(
            platform="teams",
            channel_id="19:meeting_abc123",
            user_id="29:user_xyz789",
            text="Hello from Teams!",
            message_id="1234567890",
            thread_id=None,
            timestamp=now,
            raw_event={"type": "message", "channelId": "msteams"}
        )
        
        assert msg.platform == "teams"
        assert msg.channel_id == "19:meeting_abc123"
        assert msg.user_id == "29:user_xyz789"
        assert msg.text == "Hello from Teams!"
    
    def test_threaded_message(self):
        """Test message with thread_id."""
        now = datetime.now()
        msg = UnifiedMessage(
            platform="slack",
            channel_id="C123ABC",
            user_id="U456DEF",
            text="Reply in thread",
            message_id="1234567890.123457",
            thread_id="1234567890.123456",
            timestamp=now,
            raw_event={}
        )
        
        assert msg.thread_id == "1234567890.123456"
        assert msg.is_threaded() is True
    
    def test_non_threaded_message(self):
        """Test message without thread_id."""
        now = datetime.now()
        msg = UnifiedMessage(
            platform="slack",
            channel_id="C123ABC",
            user_id="U456DEF",
            text="Top-level message",
            message_id="1234567890.123456",
            thread_id=None,
            timestamp=now,
            raw_event={}
        )
        
        assert msg.thread_id is None
        assert msg.is_threaded() is False
    
    def test_conversation_id_without_thread(self):
        """Test conversation ID generation for top-level message."""
        now = datetime.now()
        msg = UnifiedMessage(
            platform="slack",
            channel_id="C123ABC",
            user_id="U456DEF",
            text="Hello",
            message_id="1234567890.123456",
            thread_id=None,
            timestamp=now,
            raw_event={}
        )
        
        assert msg.get_conversation_id() == "slack-C123ABC"
    
    def test_conversation_id_with_thread(self):
        """Test conversation ID generation for threaded message."""
        now = datetime.now()
        msg = UnifiedMessage(
            platform="slack",
            channel_id="C123ABC",
            user_id="U456DEF",
            text="Reply",
            message_id="1234567890.123457",
            thread_id="1234567890.123456",
            timestamp=now,
            raw_event={}
        )
        
        assert msg.get_conversation_id() == "slack-C123ABC-1234567890.123456"
    
    def test_conversation_id_stability(self):
        """Test that conversation IDs are stable across message instances."""
        now = datetime.now()
        
        msg1 = UnifiedMessage(
            platform="teams",
            channel_id="19:meeting_abc",
            user_id="29:user_1",
            text="First message",
            message_id="msg1",
            thread_id="thread1",
            timestamp=now,
            raw_event={}
        )
        
        msg2 = UnifiedMessage(
            platform="teams",
            channel_id="19:meeting_abc",
            user_id="29:user_2",
            text="Second message",
            message_id="msg2",
            thread_id="thread1",
            timestamp=now,
            raw_event={}
        )
        
        # Same channel + thread = same conversation
        assert msg1.get_conversation_id() == msg2.get_conversation_id()
    
    def test_empty_text(self):
        """Test message with empty text (edge case)."""
        now = datetime.now()
        msg = UnifiedMessage(
            platform="slack",
            channel_id="C123ABC",
            user_id="U456DEF",
            text="",
            message_id="1234567890.123456",
            thread_id=None,
            timestamp=now,
            raw_event={}
        )
        
        assert msg.text == ""
    
    def test_raw_event_preservation(self):
        """Test that raw_event is preserved for platform-specific handling."""
        now = datetime.now()
        raw_event = {
            "type": "message",
            "channel": "C123ABC",
            "user": "U456DEF",
            "ts": "1234567890.123456",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Hello"}}]
        }
        
        msg = UnifiedMessage(
            platform="slack",
            channel_id="C123ABC",
            user_id="U456DEF",
            text="Hello",
            message_id="1234567890.123456",
            thread_id=None,
            timestamp=now,
            raw_event=raw_event
        )
        
        # Raw event should be preserved exactly
        assert msg.raw_event == raw_event
        assert msg.raw_event["blocks"][0]["type"] == "section"

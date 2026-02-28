"""
Unit tests for connector_core.protocols.
"""

import pytest
from typing import get_type_hints
from src.connector_core.protocols import PlatformAdapter, ApprovalPrompt
from tests.mocks import MockPlatformAdapter, MockApprovalPrompt


class TestApprovalPrompt:
    """Tests for ApprovalPrompt protocol."""
    
    def test_mock_approval_prompt_conforms(self):
        """Test that MockApprovalPrompt conforms to protocol."""
        # This would fail at type-check time if it didn't conform
        prompt: ApprovalPrompt = MockApprovalPrompt("test", auto_approve=True)
        assert prompt.get_prompt_id() == "test"
    
    @pytest.mark.asyncio
    async def test_approval_prompt_approval(self):
        """Test approval prompt returning approval."""
        prompt = MockApprovalPrompt("test", auto_approve=True)
        decision = await prompt.wait_for_decision()
        assert decision is True
    
    @pytest.mark.asyncio
    async def test_approval_prompt_denial(self):
        """Test approval prompt returning denial."""
        prompt = MockApprovalPrompt("test", auto_approve=False)
        decision = await prompt.wait_for_decision()
        assert decision is False


class TestPlatformAdapter:
    """Tests for PlatformAdapter protocol."""
    
    def test_mock_adapter_conforms(self):
        """Test that MockPlatformAdapter conforms to protocol."""
        # This would fail at type-check time if it didn't conform
        adapter: PlatformAdapter = MockPlatformAdapter("test")
        assert adapter.get_conversation_id("C123") == "test-C123"
    
    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self):
        """Test adapter startup and shutdown."""
        adapter = MockPlatformAdapter("test")
        
        assert adapter.is_started is False
        assert adapter.is_shutdown is False
        
        await adapter.startup()
        assert adapter.is_started is True
        
        await adapter.shutdown()
        assert adapter.is_shutdown is True
    
    @pytest.mark.asyncio
    async def test_send_message_without_thread(self):
        """Test sending a message to a channel."""
        adapter = MockPlatformAdapter("test")
        
        msg_id = await adapter.send_message("C123ABC", "Hello, world!")
        
        assert len(adapter.sent_messages) == 1
        assert adapter.sent_messages[0]["channel"] == "C123ABC"
        assert adapter.sent_messages[0]["text"] == "Hello, world!"
        assert adapter.sent_messages[0]["thread_id"] is None
        assert msg_id == "msg_0"
    
    @pytest.mark.asyncio
    async def test_send_message_with_thread(self):
        """Test sending a message in a thread."""
        adapter = MockPlatformAdapter("test")
        
        msg_id = await adapter.send_message(
            "C123ABC",
            "Reply",
            thread_id="1234567890.123456"
        )
        
        assert len(adapter.sent_messages) == 1
        assert adapter.sent_messages[0]["thread_id"] == "1234567890.123456"
    
    @pytest.mark.asyncio
    async def test_send_multiple_messages(self):
        """Test sending multiple messages."""
        adapter = MockPlatformAdapter("test")
        
        msg1 = await adapter.send_message("C123", "First")
        msg2 = await adapter.send_message("C123", "Second")
        msg3 = await adapter.send_message("C456", "Third")
        
        assert len(adapter.sent_messages) == 3
        assert msg1 == "msg_0"
        assert msg2 == "msg_1"
        assert msg3 == "msg_2"
    
    @pytest.mark.asyncio
    async def test_add_reaction(self):
        """Test adding a reaction to a message."""
        adapter = MockPlatformAdapter("test")
        
        await adapter.add_reaction("C123ABC", "1234567890.123456", "thumbsup")
        
        assert len(adapter.reactions) == 1
        assert adapter.reactions[0]["channel"] == "C123ABC"
        assert adapter.reactions[0]["message_id"] == "1234567890.123456"
        assert adapter.reactions[0]["emoji"] == "thumbsup"
    
    @pytest.mark.asyncio
    async def test_add_multiple_reactions(self):
        """Test adding multiple reactions."""
        adapter = MockPlatformAdapter("test")
        
        await adapter.add_reaction("C123", "msg1", "eyes")
        await adapter.add_reaction("C123", "msg1", "rocket")
        await adapter.add_reaction("C456", "msg2", "tada")
        
        assert len(adapter.reactions) == 3
    
    @pytest.mark.asyncio
    async def test_create_approval_prompt(self):
        """Test creating an approval prompt."""
        adapter = MockPlatformAdapter("test")
        
        prompt = await adapter.create_approval_prompt(
            "C123ABC",
            "Execute dangerous command?"
        )
        
        assert len(adapter.approval_prompts) == 1
        assert prompt.get_prompt_id() == "prompt_0"
        
        decision = await prompt.wait_for_decision()
        assert decision is True
    
    def test_conversation_id_without_thread(self):
        """Test conversation ID generation for top-level conversation."""
        adapter = MockPlatformAdapter("slack")
        
        conv_id = adapter.get_conversation_id("C123ABC")
        
        assert conv_id == "slack-C123ABC"
    
    def test_conversation_id_with_thread(self):
        """Test conversation ID generation for threaded conversation."""
        adapter = MockPlatformAdapter("slack")
        
        conv_id = adapter.get_conversation_id("C123ABC", "1234567890.123456")
        
        assert conv_id == "slack-C123ABC-1234567890.123456"
    
    def test_conversation_id_stability(self):
        """Test that conversation IDs are stable."""
        adapter = MockPlatformAdapter("teams")
        
        conv_id1 = adapter.get_conversation_id("19:meeting_abc", "thread1")
        conv_id2 = adapter.get_conversation_id("19:meeting_abc", "thread1")
        
        # Same inputs should produce same ID
        assert conv_id1 == conv_id2
    
    def test_conversation_id_different_platforms(self):
        """Test that different platforms produce different IDs."""
        slack_adapter = MockPlatformAdapter("slack")
        teams_adapter = MockPlatformAdapter("teams")
        
        slack_id = slack_adapter.get_conversation_id("C123")
        teams_id = teams_adapter.get_conversation_id("C123")
        
        # Different platforms should produce different IDs
        assert slack_id != teams_id
        assert slack_id == "slack-C123"
        assert teams_id == "teams-C123"

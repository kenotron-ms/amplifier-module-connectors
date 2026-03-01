"""
Response formatting utilities for Slack messages.

Handles:
1. Filtering out thinking blocks and tool call artifacts
2. Converting Markdown to Slack mrkdwn or Block Kit
3. Truncating long responses (especially file operations)
4. Splitting long responses into multiple messages
"""
import re
import logging
from typing import Any

from slack_connector.response_truncator import smart_truncate

logger = logging.getLogger(__name__)


def clean_response(text: str) -> str:
    """
    Remove thinking blocks, tool call XML, and other internal artifacts
    from the agent's response to extract only user-facing content.
    
    Common patterns to filter:
    - <thinking>...</thinking> blocks
    - <tool_call>...</tool_call> blocks  
    - Function call JSON blocks
    - Internal reasoning markers
    """
    if not text:
        return ""
    
    # Remove thinking blocks (various formats)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove tool call blocks
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<function_calls>.*?</function_calls>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove tool result blocks
    text = re.sub(r'<tool_result>.*?</tool_result>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove internal reasoning markers
    text = re.sub(r'\[THINKING:.*?\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[TOOL:.*?\]', '', text, flags=re.DOTALL)
    
    # Clean up excessive whitespace
    text = re.sub(r'\n\n\n+', '\n\n', text)
    text = text.strip()
    
    return text


def markdown_to_mrkdwn(text: str) -> str:
    """
    Convert common Markdown patterns to Slack mrkdwn format.
    
    This is a lightweight conversion for basic formatting.
    For full Block Kit support, use markdown_to_blocks().
    """
    if not text:
        return ""
    
    # Use placeholders to avoid conflicts between bold and italic
    # 1. Bold: **text** or __text__ -> temporary placeholder
    text = re.sub(r'\*\*(.+?)\*\*', r'<<<BOLD>>>\1<<</BOLD>>>', text)
    text = re.sub(r'__(.+?)__', r'<<<BOLD>>>\1<<</BOLD>>>', text)
    
    # 2. Italic: *text* or _text_ (single, not part of bold) -> temporary placeholder  
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<<<ITALIC>>>\1<<</ITALIC>>>', text)
    # Note: _text_ already works in Slack, but let's normalize it
    # text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<<<ITALIC>>>\1<<</ITALIC>>>', text)
    
    # 3. Replace placeholders with Slack format
    text = text.replace('<<<BOLD>>>', '*').replace('<<</BOLD>>>', '*')
    text = text.replace('<<<ITALIC>>>', '_').replace('<<</ITALIC>>>', '_')
    
    # Links: [text](url) -> <url|text>
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<\2|\1>', text)
    
    # Inline code: `code` stays as `code` (same in both)
    
    # Code blocks: ```lang\ncode\n``` stays as-is (Slack supports this)
    
    # Headings: ### Heading -> *Heading* (bold, since Slack has no heading in mrkdwn)
    text = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)
    
    # Block quotes: > quote -> stays as-is (Slack supports this)
    
    return text


def markdown_to_blocks(text: str) -> list[dict[str, Any]]:
    """
    Convert Markdown to Slack Block Kit rich_text blocks.
    
    This provides full visual fidelity for headings, lists, code blocks, etc.
    Returns a list of Block Kit block objects.
    
    Note: This is a simplified implementation. For production, consider
    using a proper Markdown parser like markdown-it-py or mistune.
    """
    blocks: list[dict[str, Any]] = []
    
    # For now, use a simple section block with mrkdwn
    # TODO: Implement full Block Kit rich_text parsing
    if text and text.strip():
        mrkdwn_text = markdown_to_mrkdwn(text)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": mrkdwn_text
            }
        })
    
    return blocks


def format_for_slack(text: str, use_blocks: bool = False, truncate: bool = True) -> dict[str, Any]:
    """
    Prepare agent response for posting to Slack.
    
    Args:
        text: Raw agent response (may contain thinking blocks, Markdown, etc.)
        use_blocks: If True, return Block Kit blocks; if False, return mrkdwn text
        truncate: If True, intelligently truncate long responses (default: True)
    
    Returns:
        Dictionary with 'text' (fallback) and optionally 'blocks' (rich display)
    """
    # Step 1: Clean out internal artifacts
    cleaned = clean_response(text)
    
    if not cleaned:
        return {"text": ""}
    
    # Step 2: Intelligently truncate if needed (especially for file operations)
    if truncate:
        cleaned = smart_truncate(cleaned)
    
    # Step 3: Convert Markdown to Slack format
    if use_blocks:
        # Full Block Kit (rich formatting)
        blocks = markdown_to_blocks(cleaned)
        # Always include text fallback (required by Slack for notifications)
        fallback = markdown_to_mrkdwn(cleaned)
        return {
            "text": fallback,
            "blocks": blocks
        }
    else:
        # Simple mrkdwn conversion
        mrkdwn_text = markdown_to_mrkdwn(cleaned)
        return {"text": mrkdwn_text}

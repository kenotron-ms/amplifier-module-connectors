"""
Response truncation utilities for Slack messages.

Intelligently truncates long responses, especially file operation outputs,
to prevent hitting Slack message size limits while preserving useful information.
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Slack message limits
SLACK_TEXT_LIMIT = 40000  # characters (Slack's limit)
SLACK_BLOCK_TEXT_LIMIT = 3000  # characters per block text element

# Truncation thresholds
MAX_FILE_LINES_IN_RESPONSE = 20  # Show first N lines of file operations
MAX_RESPONSE_LINES = 100  # Max total lines in any response
TRUNCATION_MESSAGE = "\n\n_... (output truncated, showing first {shown} lines of {total})_"


def detect_file_operation(text: str) -> dict[str, Any] | None:
    """
    Detect if the response contains file write/edit operation output.
    
    Returns:
        Dictionary with operation details if detected, None otherwise
        {
            'type': 'write_file' | 'edit_file' | 'read_file',
            'file_path': str,
            'content_start': int,  # Index where file content starts
            'content_end': int,    # Index where file content ends
        }
    """
    # Pattern for write_file output (common format from filesystem tools)
    write_pattern = r'(?:wrote|created|writing)\s+(?:file\s+)?[`\']?([^\s`\']+)[`\']?.*?(?:\n|$)(.*?)(?:\n\n|$)'
    
    # Pattern for edit_file output
    edit_pattern = r'(?:edited|modified|updated)\s+(?:file\s+)?[`\']?([^\s`\']+)[`\']?.*?(?:\n|$)(.*?)(?:\n\n|$)'
    
    # Pattern for file content blocks (code blocks with file content)
    content_block_pattern = r'```(?:\w+)?\n(.*?)\n```'
    
    # Check for write_file
    match = re.search(write_pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return {
            'type': 'write_file',
            'file_path': match.group(1),
            'content_start': match.start(2),
            'content_end': match.end(2)
        }
    
    # Check for edit_file
    match = re.search(edit_pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return {
            'type': 'edit_file',
            'file_path': match.group(1),
            'content_start': match.start(2),
            'content_end': match.end(2)
        }
    
    # Check for large code blocks (likely file content)
    match = re.search(content_block_pattern, text, re.DOTALL)
    if match:
        content = match.group(1)
        line_count = len(content.split('\n'))
        if line_count > MAX_FILE_LINES_IN_RESPONSE:
            return {
                'type': 'code_block',
                'file_path': None,
                'content_start': match.start(1),
                'content_end': match.end(1)
            }
    
    return None


def truncate_file_content(content: str, max_lines: int = MAX_FILE_LINES_IN_RESPONSE) -> tuple[str, bool]:
    """
    Truncate file content to first N lines.
    
    Args:
        content: File content to truncate
        max_lines: Maximum number of lines to keep
        
    Returns:
        Tuple of (truncated_content, was_truncated)
    """
    lines = content.split('\n')
    total_lines = len(lines)
    
    if total_lines <= max_lines:
        return content, False
    
    # Keep first max_lines
    truncated_lines = lines[:max_lines]
    truncated = '\n'.join(truncated_lines)
    
    # Add truncation notice
    truncation_notice = TRUNCATION_MESSAGE.format(
        shown=max_lines,
        total=total_lines
    )
    
    return truncated + truncation_notice, True


def truncate_code_block(text: str, max_lines: int = MAX_FILE_LINES_IN_RESPONSE) -> str:
    """
    Truncate code blocks within text to first N lines.
    
    Args:
        text: Text containing code blocks
        max_lines: Maximum lines per code block
        
    Returns:
        Text with truncated code blocks
    """
    def replace_code_block(match):
        lang = match.group(1) or ''
        content = match.group(2)
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        if total_lines <= max_lines:
            return match.group(0)  # Return original
        
        # Truncate
        truncated_lines = lines[:max_lines]
        truncated_content = '\n'.join(truncated_lines)
        
        truncation_notice = f"\n... (showing first {max_lines} of {total_lines} lines)"
        
        return f"```{lang}\n{truncated_content}{truncation_notice}\n```"
    
    # Pattern: ```lang\ncontent\n```
    pattern = r'```(\w+)?\n(.*?)\n```'
    return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)


def truncate_response(text: str, max_lines: int = MAX_RESPONSE_LINES) -> tuple[str, bool]:
    """
    Truncate overall response if it's too long.
    
    Args:
        text: Response text
        max_lines: Maximum total lines
        
    Returns:
        Tuple of (truncated_text, was_truncated)
    """
    lines = text.split('\n')
    total_lines = len(lines)
    
    if total_lines <= max_lines:
        return text, False
    
    # Keep first max_lines
    truncated_lines = lines[:max_lines]
    truncated = '\n'.join(truncated_lines)
    
    # Add truncation notice
    truncation_notice = f"\n\n_... (response truncated, showing first {max_lines} of {total_lines} lines)_"
    
    return truncated + truncation_notice, True


def smart_truncate(text: str) -> str:
    """
    Intelligently truncate response based on content type.
    
    This is the main entry point for response truncation. It:
    1. Detects file operations and truncates file content
    2. Truncates large code blocks
    3. Applies overall line limit if still too long
    4. Ensures we stay under Slack's character limit
    
    Args:
        text: Raw response text
        
    Returns:
        Truncated text suitable for Slack
    """
    if not text:
        return text
    
    # Step 1: Truncate code blocks
    text = truncate_code_block(text, max_lines=MAX_FILE_LINES_IN_RESPONSE)
    
    # Step 2: Check overall line count
    lines = text.split('\n')
    if len(lines) > MAX_RESPONSE_LINES:
        text, _ = truncate_response(text, max_lines=MAX_RESPONSE_LINES)
    
    # Step 3: Check character limit (hard limit from Slack)
    if len(text) > SLACK_TEXT_LIMIT:
        # Truncate by characters, try to break at a line boundary
        truncated = text[:SLACK_TEXT_LIMIT - 200]  # Leave room for notice
        
        # Find last newline
        last_newline = truncated.rfind('\n')
        if last_newline > 0:
            truncated = truncated[:last_newline]
        
        char_count = len(text)
        truncated += f"\n\n_... (response truncated, showing first ~{len(truncated)} of {char_count} characters)_"
        text = truncated
    
    return text


def format_file_operation_summary(operation_type: str, file_path: str, line_count: int, shown_lines: int) -> str:
    """
    Create a concise summary for file operations.
    
    Args:
        operation_type: 'write', 'edit', or 'read'
        file_path: Path to the file
        line_count: Total lines in file
        shown_lines: Number of lines shown
        
    Returns:
        Formatted summary string
    """
    action_verb = {
        'write': 'Created',
        'edit': 'Updated',
        'read': 'Read'
    }.get(operation_type, 'Modified')
    
    if line_count <= shown_lines:
        return f"✅ {action_verb} `{file_path}` ({line_count} lines)"
    else:
        return f"✅ {action_verb} `{file_path}` ({line_count} lines, showing first {shown_lines})"


def should_truncate(text: str) -> bool:
    """
    Determine if text should be truncated.
    
    Args:
        text: Text to check
        
    Returns:
        True if truncation is recommended
    """
    if not text:
        return False
    
    # Check line count
    lines = text.split('\n')
    if len(lines) > MAX_FILE_LINES_IN_RESPONSE:
        return True
    
    # Check character count
    if len(text) > SLACK_TEXT_LIMIT * 0.8:  # 80% of limit
        return True
    
    # Check for large code blocks
    code_blocks = re.findall(r'```.*?\n(.*?)\n```', text, re.DOTALL)
    for block in code_blocks:
        block_lines = len(block.split('\n'))
        if block_lines > MAX_FILE_LINES_IN_RESPONSE:
            return True
    
    return False

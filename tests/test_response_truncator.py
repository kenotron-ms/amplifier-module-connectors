"""
Tests for Slack response truncation utilities.
"""

import pytest
from slack_connector.response_truncator import (
    truncate_file_content,
    truncate_code_block,
    truncate_response,
    smart_truncate,
    should_truncate,
    format_file_operation_summary,
    MAX_FILE_LINES_IN_RESPONSE,
)


class TestTruncateFileContent:
    """Test file content truncation."""
    
    def test_short_content_not_truncated(self):
        """Short content should not be truncated."""
        content = "line 1\nline 2\nline 3"
        result, was_truncated = truncate_file_content(content, max_lines=10)
        
        assert result == content
        assert was_truncated is False
    
    def test_long_content_truncated(self):
        """Long content should be truncated to max_lines."""
        lines = [f"line {i}" for i in range(50)]
        content = "\n".join(lines)
        
        result, was_truncated = truncate_file_content(content, max_lines=10)
        
        assert was_truncated is True
        assert "line 0" in result
        assert "line 9" in result
        assert "line 10" not in result
        assert "showing first 10" in result
        assert "of 50" in result
    
    def test_exact_limit_not_truncated(self):
        """Content exactly at limit should not be truncated."""
        lines = [f"line {i}" for i in range(20)]
        content = "\n".join(lines)
        
        result, was_truncated = truncate_file_content(content, max_lines=20)
        
        assert was_truncated is False
        assert result == content


class TestTruncateCodeBlock:
    """Test code block truncation."""
    
    def test_short_code_block_not_truncated(self):
        """Short code blocks should not be truncated."""
        text = "Here's some code:\n```python\nprint('hello')\nprint('world')\n```\nDone!"
        result = truncate_code_block(text, max_lines=10)
        
        assert result == text
    
    def test_long_code_block_truncated(self):
        """Long code blocks should be truncated."""
        code_lines = [f"line_{i} = {i}" for i in range(50)]
        code = "\n".join(code_lines)
        text = f"Here's the code:\n```python\n{code}\n```\nDone!"
        
        result = truncate_code_block(text, max_lines=10)
        
        assert "line_0" in result
        assert "line_9" in result
        assert "line_10" not in result
        assert "showing first 10 of 50 lines" in result
    
    def test_multiple_code_blocks(self):
        """Should truncate all code blocks independently."""
        text = """
First block:
```python
line 1
line 2
```

Second block:
```javascript
""" + "\n".join([f"line {i}" for i in range(30)]) + """
```
"""
        result = truncate_code_block(text, max_lines=5)
        
        # First block should be unchanged
        assert "line 1" in result
        assert "line 2" in result
        
        # Second block should be truncated
        assert "showing first 5 of 30 lines" in result
    
    def test_code_block_without_language(self):
        """Code blocks without language specifier should work."""
        code_lines = [f"line {i}" for i in range(30)]
        code = "\n".join(code_lines)
        text = f"```\n{code}\n```"
        
        result = truncate_code_block(text, max_lines=10)
        
        assert "line 0" in result
        assert "line 9" in result
        assert "showing first 10 of 30 lines" in result


class TestTruncateResponse:
    """Test overall response truncation."""
    
    def test_short_response_not_truncated(self):
        """Short responses should not be truncated."""
        text = "Short response\nwith a few lines"
        result, was_truncated = truncate_response(text, max_lines=100)
        
        assert result == text
        assert was_truncated is False
    
    def test_long_response_truncated(self):
        """Long responses should be truncated."""
        lines = [f"line {i}" for i in range(150)]
        text = "\n".join(lines)
        
        result, was_truncated = truncate_response(text, max_lines=50)
        
        assert was_truncated is True
        assert "line 0" in result
        assert "line 49" in result
        assert "line 50" not in result
        assert "showing first 50 of 150 lines" in result


class TestSmartTruncate:
    """Test smart truncation logic."""
    
    def test_short_text_unchanged(self):
        """Short text should pass through unchanged."""
        text = "This is a short response."
        result = smart_truncate(text)
        
        assert result == text
    
    def test_truncates_code_blocks(self):
        """Should truncate long code blocks."""
        code_lines = [f"line {i}" for i in range(50)]
        code = "\n".join(code_lines)
        text = f"Here's the file:\n```python\n{code}\n```"
        
        result = smart_truncate(text)
        
        assert "line 0" in result
        assert f"line {MAX_FILE_LINES_IN_RESPONSE - 1}" in result
        assert f"line {MAX_FILE_LINES_IN_RESPONSE}" not in result
    
    def test_truncates_very_long_responses(self):
        """Should truncate responses with too many lines."""
        lines = [f"line {i}" for i in range(200)]
        text = "\n".join(lines)
        
        result = smart_truncate(text)
        
        assert "truncated" in result.lower()
    
    def test_handles_empty_text(self):
        """Should handle empty text gracefully."""
        result = smart_truncate("")
        assert result == ""
        
        result = smart_truncate(None)
        assert result is None
    
    def test_preserves_structure_outside_code_blocks(self):
        """Should preserve text outside code blocks."""
        text = """Here's what I did:

1. Created the file
2. Added content

```python
print('hello')
```

Done!"""
        result = smart_truncate(text)
        
        assert "Here's what I did:" in result
        assert "Created the file" in result
        assert "Done!" in result


class TestShouldTruncate:
    """Test truncation decision logic."""
    
    def test_short_text_no_truncation(self):
        """Short text should not need truncation."""
        text = "Short message"
        assert should_truncate(text) is False
    
    def test_many_lines_needs_truncation(self):
        """Text with many lines should be truncated."""
        lines = [f"line {i}" for i in range(100)]
        text = "\n".join(lines)
        assert should_truncate(text) is True
    
    def test_large_code_block_needs_truncation(self):
        """Large code blocks should trigger truncation."""
        code_lines = [f"line {i}" for i in range(50)]
        code = "\n".join(code_lines)
        text = f"```python\n{code}\n```"
        assert should_truncate(text) is True
    
    def test_very_long_text_needs_truncation(self):
        """Very long text should be truncated."""
        text = "x" * 35000  # Near Slack's limit
        assert should_truncate(text) is True


class TestFormatFileOperationSummary:
    """Test file operation summary formatting."""
    
    def test_write_operation_full_file(self):
        """Format summary for write operation showing full file."""
        result = format_file_operation_summary('write', 'test.py', 10, 10)
        assert "Created" in result
        assert "test.py" in result
        assert "10 lines" in result
        assert "showing first" not in result
    
    def test_write_operation_truncated(self):
        """Format summary for write operation with truncation."""
        result = format_file_operation_summary('write', 'test.py', 100, 20)
        assert "Created" in result
        assert "test.py" in result
        assert "100 lines" in result
        assert "showing first 20" in result
    
    def test_edit_operation(self):
        """Format summary for edit operation."""
        result = format_file_operation_summary('edit', 'main.py', 50, 20)
        assert "Updated" in result
        assert "main.py" in result
    
    def test_read_operation(self):
        """Format summary for read operation."""
        result = format_file_operation_summary('read', 'config.json', 30, 20)
        assert "Read" in result
        assert "config.json" in result


class TestIntegration:
    """Integration tests for realistic scenarios."""
    
    def test_file_write_response(self):
        """Test truncating a typical file write response."""
        file_content = "\n".join([f"line {i}" for i in range(100)])
        response = f"""I've created the file with the following content:

```python
{file_content}
```

The file has been written successfully."""
        
        result = smart_truncate(response)
        
        # Should preserve intro and conclusion
        assert "I've created the file" in result
        assert "successfully" in result
        
        # Should truncate code block
        assert "line 0" in result
        assert f"line {MAX_FILE_LINES_IN_RESPONSE - 1}" in result
        assert "truncated" in result.lower() or "showing first" in result.lower()
    
    def test_multiple_operations(self):
        """Test response with multiple file operations."""
        response = """I've completed the following:

1. Created `file1.py`:
```python
""" + "\n".join([f"line {i}" for i in range(30)]) + """
```

2. Created `file2.py`:
```python
""" + "\n".join([f"line {i}" for i in range(30)]) + """
```

All done!"""
        
        result = smart_truncate(response)
        
        # Should preserve structure
        assert "I've completed" in result
        assert "All done!" in result
        
        # Both code blocks should be truncated
        result_lines = result.count("showing first")
        assert result_lines >= 1  # At least one truncation
    
    def test_normal_conversation_unchanged(self):
        """Normal conversation responses should pass through."""
        response = """Sure! I can help with that.

Here's what you need to do:
1. First step
2. Second step
3. Third step

Let me know if you have questions!"""
        
        result = smart_truncate(response)
        assert result == response

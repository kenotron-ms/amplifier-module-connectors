# Response Truncation

## Overview

The Slack connector automatically truncates long responses to prevent hitting Slack's message size limits and improve readability. This is especially important for file operations that can include hundreds of lines of code.

## Why Truncation?

### Slack Message Limits
- **Text limit**: 40,000 characters per message
- **Block text limit**: 3,000 characters per block element
- **Practical limit**: Messages over ~100 lines become hard to read in Slack

### Common Issues Without Truncation
- File write/edit operations showing entire file contents (100+ lines)
- Tool outputs flooding the chat
- Slow message rendering
- Poor user experience

## How It Works

### Smart Truncation Strategy

The truncation system uses a multi-layered approach:

1. **Code Block Truncation** - Truncates code blocks to first 20 lines
2. **Overall Line Limit** - Limits total response to 100 lines
3. **Character Limit** - Hard limit at 40,000 characters (Slack's max)

### What Gets Truncated

#### Code Blocks
```python
# Before truncation (50 lines)
```python
line 0
line 1
...
line 49
```

# After truncation (20 lines shown)
```python
line 0
line 1
...
line 19
... (showing first 20 of 50 lines)
```
```

#### File Operations
When you write or edit a file, only the first 20 lines are shown:

```
User: Create a main.py file with a Flask app
Bot: ✅ Created `main.py` (100 lines, showing first 20)

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

... (showing first 20 of 100 lines)
```
```

#### Long Responses
Responses with more than 100 lines are truncated:

```
Line 1
Line 2
...
Line 100

... (response truncated, showing first 100 of 200 lines)
```

### What Doesn't Get Truncated

- **Normal conversation**: Regular chat messages pass through unchanged
- **Short code blocks**: Code blocks under 20 lines shown in full
- **Structured output**: Lists, headings, and formatting preserved
- **Error messages**: Error output shown completely

## Configuration

### Default Limits

```python
# src/slack_connector/response_truncator.py

MAX_FILE_LINES_IN_RESPONSE = 20  # Lines shown in code blocks
MAX_RESPONSE_LINES = 100         # Total lines in response
SLACK_TEXT_LIMIT = 40000         # Slack's character limit
```

### Customizing Limits

You can adjust truncation behavior by modifying the formatter call:

```python
# In bot.py
formatted = format_for_slack(response, use_blocks=True, truncate=True)

# To disable truncation
formatted = format_for_slack(response, use_blocks=True, truncate=False)
```

### Per-Response Control

```python
from slack_connector.response_truncator import smart_truncate

# Custom truncation
truncated = smart_truncate(response)

# Or use individual functions
from slack_connector.response_truncator import (
    truncate_code_block,
    truncate_response,
)

# Truncate only code blocks
result = truncate_code_block(text, max_lines=30)

# Truncate entire response
result, was_truncated = truncate_response(text, max_lines=50)
```

## Examples

### Example 1: File Write Operation

**User Request:**
```
@bot Create a Python FastAPI application in main.py
```

**Without Truncation (bad):**
```
Created main.py:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
... (100 more lines of boilerplate)
```

Done!
```
*(Floods the chat, hard to read)*

**With Truncation (good):**
```
✅ Created `main.py` (120 lines, showing first 20)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="My API",
    description="API documentation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

... (showing first 20 of 120 lines)
```

Done! The full file has been created.
```
*(Clean, readable, with clear indication of truncation)*

### Example 2: Multiple File Operations

**User Request:**
```
@bot Create a basic Flask app with routes and models
```

**Response:**
```
I've created the following files:

1. `app.py` (50 lines, showing first 20):
```python
from flask import Flask, jsonify
from models import User, db

app = Flask(__name__)
... (showing first 20 of 50 lines)
```

2. `models.py` (30 lines, showing first 20):
```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
... (showing first 20 of 30 lines)
```

All files created successfully!
```

### Example 3: Normal Conversation (Not Truncated)

**User Request:**
```
@bot How do I deploy this to production?
```

**Response:**
```
Here's how to deploy your Flask app to production:

1. **Prepare your app**
   - Set up environment variables
   - Configure production database
   - Add gunicorn to requirements.txt

2. **Choose a platform**
   - Heroku (easiest)
   - AWS Elastic Beanstalk
   - DigitalOcean App Platform

3. **Deploy steps**
   - Create a Procfile
   - Set up your database
   - Deploy your code

Would you like detailed steps for a specific platform?
```
*(No truncation - normal conversation flow)*

## Benefits

### For Users
- ✅ **Cleaner chat** - No more 100-line code dumps
- ✅ **Faster reading** - See the important parts immediately
- ✅ **Better context** - Know when content is truncated
- ✅ **Full access** - Files are fully created, just not fully shown

### For the System
- ✅ **Reliability** - Never hit Slack's message limits
- ✅ **Performance** - Faster message rendering
- ✅ **Scalability** - Handle large file operations gracefully

## Technical Details

### Truncation Algorithm

```python
def smart_truncate(text: str) -> str:
    """
    1. Truncate all code blocks to MAX_FILE_LINES_IN_RESPONSE
    2. Check overall line count, truncate if > MAX_RESPONSE_LINES
    3. Check character count, truncate if > SLACK_TEXT_LIMIT
    4. Add truncation notices
    """
```

### Detection Logic

The system detects different content types:

```python
# Code blocks
pattern = r'```(\w+)?\n(.*?)\n```'

# File operations (heuristic)
- "Created file.py"
- "Updated file.py"
- Large code blocks (>20 lines)
```

### Truncation Notices

Clear indicators show when content is truncated:

```
... (showing first 20 of 100 lines)
... (response truncated, showing first 100 of 200 lines)
... (response truncated, showing first ~35000 of 45000 characters)
```

## Testing

Comprehensive test suite ensures truncation works correctly:

```bash
# Run truncation tests
pytest tests/test_response_truncator.py -v

# 25 tests covering:
# - File content truncation
# - Code block truncation
# - Overall response truncation
# - Smart truncation logic
# - Integration scenarios
```

## Future Enhancements

### Planned Features
- **Pagination** - "Show more" buttons for truncated content
- **Collapsible blocks** - Expandable sections for long content
- **Smart summaries** - AI-generated summaries of truncated content
- **User preferences** - Per-user truncation settings

### Potential Improvements
- **Syntax-aware truncation** - Preserve code structure
- **Diff-based truncation** - For file edits, show only changes
- **Interactive truncation** - "Show next 20 lines" commands

## Troubleshooting

### Issue: Important content is truncated

**Solution**: The full file is still created, only the display is truncated. You can:
- Use `@bot read file.py` to see specific parts
- Use `@bot show lines 50-70 of file.py` for specific ranges
- Check the file directly in your editor

### Issue: Want to see full output

**Solution**: Disable truncation for specific operations:
```python
# In custom integration
formatted = format_for_slack(response, truncate=False)
```

### Issue: Truncation too aggressive/lenient

**Solution**: Adjust the limits in `response_truncator.py`:
```python
MAX_FILE_LINES_IN_RESPONSE = 30  # Increase from 20
MAX_RESPONSE_LINES = 150         # Increase from 100
```

## Best Practices

### For Bot Responses
1. **Summarize first** - Give overview before code
2. **Use truncation notices** - Make it clear when content is truncated
3. **Offer alternatives** - Suggest ways to see full content

### For Users
1. **Check the files** - Full content is in the actual files
2. **Ask for specific parts** - "Show me lines 50-100"
3. **Use file tools** - `read_file`, `grep`, etc. for exploration

### For Developers
1. **Test with large files** - Ensure truncation works
2. **Monitor message sizes** - Track truncation frequency
3. **Adjust limits** - Based on usage patterns

## See Also

- **[Formatter Documentation](./FORMATTER.md)** - Response formatting details
- **[Slack Setup Guide](./slack-setup.md)** - Slack configuration
- **[Progressive Updates](./PROGRESSIVE_UPDATES.md)** - Real-time status updates

---

**Last Updated**: 2024-02-28
**Module Version**: 0.2.0

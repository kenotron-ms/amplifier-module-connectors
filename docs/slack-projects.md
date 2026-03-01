# Slack Project Management

The Slack connector supports associating threads with specific project directories, allowing you to work on different projects across multiple threads while maintaining context.

## Quick Start

### 1. Start a New Session

In any Slack channel where the bot is present, use the `/amplifier` slash command:

```
/amplifier <project-name-or-path>
```

**Examples:**
```
/amplifier my-project              # Use registered project name
/amplifier /path/to/project        # Use explicit path
/amplifier ~/workspace/my-app      # Path with ~
/amplifier .                       # Current directory (if accessible)
```

This creates a new thread and associates it with the specified project directory. All file operations in that thread will be relative to the project directory.

### 2. Work in the Thread

Once the session is started, you can:
- Ask questions about the project
- Request file edits, searches, or operations
- Run commands
- All operations happen in the project's directory context

### 3. Continue Across Sessions

The thread → project association persists even if the bot restarts. You can continue working in the same thread later, and the bot will remember the project context.

## Slash Commands

### `/amplifier <project>`
Start a new Amplifier session in a thread.

**Arguments:**
- `<project>` - A directory path (absolute or relative, `~` supported)

**Creates:**
- A new thread in the current channel
- Associates the thread with the specified project
- Sets the working directory for all operations in that thread
- Uses Amplifier's existing `~/.amplifier/projects/` structure for session storage

**Example:**
```
/amplifier /Users/ken/workspace/amplifier-module-connectors
/amplifier ~/workspace/my-project
/amplifier .
```

**Response:**
```
✅ Session started for amplifier-module-connectors
/Users/ken/workspace/amplifier-module-connectors

You can now ask me anything about this project.
All file operations will be relative to this directory.
```

### `/amplifier-status`
Show active Amplifier sessions in the current channel.

**Example:**
```
/amplifier-status
```

**Response:**
```
📋 Active Amplifier Sessions

• amplifier-module-connectors - /Users/ken/workspace/amplifier-module-connectors
• my-app - /Users/ken/workspace/my-app
```

### `/amplifier-list`
List projects discovered from `~/.amplifier/projects/`.

**Example:**
```
/amplifier-list
```

**Response:**
```
📁 Amplifier Projects

• amplifier-module-connectors-32b3236f
• my-app-a1b2c3d4
• frontend-b5c6d7e8
```

**Note:** This shows projects that have been used with Amplifier before (have session data).

## Integration with Amplifier

This feature leverages **Amplifier CLI's existing project infrastructure** - no new configuration needed!

### How It Works

When you use `/amplifier /path/to/project`, the bot:

1. **Changes working directory** to your project path
2. **Amplifier automatically detects the project** from `cwd` (current working directory)
3. **Creates project slug** using Amplifier CLI's algorithm:
   ```
   /Users/ken/workspace/my-project → -Users-ken-workspace-my-project
   ```
4. **Stores sessions** in `~/.amplifier/projects/<slug>/sessions/`

### Project Storage

Amplifier CLI automatically creates:

```
~/.amplifier/projects/<project-slug>/
  sessions/
    <session-id>/
      context-messages.jsonl
      ...
  repl_history
```

The project slug format (from Amplifier CLI's `project_utils.py`):
- Replaces `/` with `-`
- Adds leading `-` for readability
- Example: `/Users/ken/workspace/my-app` → `-Users-ken-workspace-my-app`

### Benefits

- ✅ **No configuration needed** - Uses Amplifier's existing system
- ✅ **Compatible with CLI** - Same project detection as `amplifier session list`
- ✅ **Persistent sessions** - Sessions stored per-project automatically
- ✅ **Works with existing projects** - Detects projects you've already used

## Persistence

### Thread Associations

Thread → project mappings are stored in:
```
~/.amplifier/slack-threads.json
```

This file is automatically created and updated. It persists across bot restarts, so you can continue working in existing threads without losing project context.

### Session History

Amplifier sessions themselves may persist depending on your Amplifier configuration. The project association ensures that when you return to a thread, the working directory is set correctly.

## Use Cases

### Multiple Projects

Work on different projects simultaneously in different threads:

```
Thread 1: /amplifier my-frontend
Thread 2: /amplifier my-backend
Thread 3: /amplifier infrastructure
```

Each thread maintains its own project context and conversation history.

### Long-Running Work

Start a session, work on it, take a break, and come back later:

```
Day 1: /amplifier my-project
       "Refactor the authentication module"
       [bot makes changes]

Day 2: [continue in same thread]
       "Now add rate limiting"
       [bot continues with full context]
```

### Team Collaboration

Multiple team members can work in the same thread, all operating in the same project context:

```
Alice: /amplifier shared-project
       "Add a new API endpoint for user profiles"

Bob:   [replies in thread]
       "Can you also add validation?"

Bot:   [makes both changes in the same project]
```

## Troubleshooting

### "Project not found"

**Problem:** `/amplifier my-project` returns an error.

**Solutions:**
1. Check that the project is registered in `~/.amplifier/projects.json`
2. Use an explicit path instead: `/amplifier /path/to/project`
3. Verify the path exists and is accessible to the bot

### "Path does not exist"

**Problem:** The specified path doesn't exist.

**Solutions:**
1. Check for typos in the path
2. Ensure the path is absolute or uses `~`
3. Verify the bot has permission to access the directory

### Thread lost project association

**Problem:** An old thread no longer knows its project.

**Solution:** The association is stored in `~/.amplifier/slack-threads.json`. If this file was deleted or corrupted, you'll need to start a new thread with `/amplifier`.

## Best Practices

### 1. Use Registered Projects

For frequently-used projects, register them in `~/.amplifier/projects.json` for easier access:

```
✅ /amplifier my-project
❌ /amplifier /Users/ken/workspace/my-project
```

### 2. One Thread Per Task

Start a new thread for each distinct task or feature:

```
Thread 1: /amplifier my-app
          "Implement user authentication"

Thread 2: /amplifier my-app
          "Add dark mode support"
```

This keeps conversations focused and makes it easier to find past work.

### 3. Descriptive First Message

After starting a session, immediately describe what you want to work on:

```
/amplifier my-app
"I want to refactor the database layer to use SQLAlchemy instead of raw SQL"
```

This helps set context for the conversation.

### 4. Check Status

Use `/amplifier-status` to see what sessions are active before starting a new one. You might already have a thread for that project!

## Security Considerations

### Path Access

The bot runs with the permissions of the user account running it. It can access any directory that user can access.

**Recommendations:**
- Run the bot with a dedicated user account
- Use file system permissions to restrict access
- Only register trusted projects in the registry

### Team Access

Anyone in the Slack workspace can use slash commands and access registered projects.

**Recommendations:**
- Use Slack's channel permissions to control access
- Consider running separate bot instances for different teams
- Audit `~/.amplifier/slack-threads.json` periodically

## Advanced Configuration

### Custom Storage Location

You can specify a custom location for thread associations by modifying the bot initialization:

```python
bot = SlackAmplifierBot(
    bundle_path=bundle_path,
    slack_app_token=app_token,
    slack_bot_token=bot_token,
    project_storage_path="/custom/path/threads.json",
)
```

### System-Wide Projects

For shared/team setups, create `/etc/amplifier/projects.json`:

```json
{
  "projects": {
    "shared-frontend": {
      "path": "/opt/projects/frontend",
      "description": "Team frontend repository"
    },
    "shared-backend": {
      "path": "/opt/projects/backend",
      "description": "Team backend repository"
    }
  }
}
```

All users will have access to these registered projects.

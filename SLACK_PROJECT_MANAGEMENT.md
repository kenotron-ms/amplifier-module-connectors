# Slack Project Management - Implementation Summary

## Overview

This feature allows users to associate Slack threads with specific project directories using slash commands. This solves the problem of working on multiple projects and maintaining context across sessions.

## What Was Implemented

### 1. **ProjectManager** (`src/slack_connector/project_manager.py`)

A new module that manages:
- **Thread Associations**: Persistent mapping of Slack threads to project directories
- **Path Resolution**: Resolves paths to absolute directories with validation
- **Amplifier CLI Integration**: Uses **Amplifier CLI's** `project_utils.py` slug algorithm

**Key Features:**
- Persistent storage in `~/.amplifier/slack-threads.json`
- **Uses Amplifier CLI's `get_project_slug()` algorithm** - exact match with CLI behavior
- Thread associations survive bot restarts
- Automatic path validation and expansion (`~` support)
- No new configuration files needed - leverages Amplifier's existing infrastructure
- Compatible with `amplifier session list --project PATH`

### 2. **Slash Commands**

Three new slash commands integrated into the Slack bot:

#### `/amplifier <path>`
- Creates a new thread
- Associates it with the specified project directory
- Sets working directory for all operations in that thread
- Creates project structure in `~/.amplifier/projects/`

**Examples:**
```
/amplifier /path/to/project        # Absolute path
/amplifier ~/workspace/my-app      # Home directory expansion
/amplifier .                       # Current directory
```

#### `/amplifier-status`
- Shows all active Amplifier sessions in the current channel
- Displays project paths

#### `/amplifier-list`
- Lists projects discovered from `~/.amplifier/projects/`
- Shows projects that have been used with Amplifier before

### 3. **Working Directory Management**

Modified `SlackAmplifierBot._get_or_create_session()` to:
- Look up the project path for the current thread
- Change working directory to that project before executing commands
- Ensures all file operations are relative to the project directory

### 4. **Documentation**

Created comprehensive documentation:
- **[docs/slack-projects.md](docs/slack-projects.md)**: Full user guide for project management
- **[docs/slack-slash-commands-setup.md](docs/slack-slash-commands-setup.md)**: Setup instructions for Slack app
- **[projects.json.example](projects.json.example)**: Example project registry

### 5. **Tests**

Added comprehensive test suite (`tests/test_project_manager.py`):
- ✅ 10 tests covering all ProjectManager functionality
- All tests passing
- Tests path resolution, persistence, thread associations, etc.

## How It Works

### User Flow

1. **User runs slash command:**
   ```
   /amplifier my-project
   ```

2. **Bot creates a thread and associates it:**
   - Resolves `my-project` → `/Users/ken/workspace/my-project`
   - Creates new thread in Slack
   - Stores mapping: `thread_id` → `project_path`
   - Confirms in thread with project details

3. **User works in the thread:**
   ```
   User: "Show me the README file"
   Bot: [reads /Users/ken/workspace/my-project/README.md]
   
   User: "Edit the package.json to update the version"
   Bot: [edits /Users/ken/workspace/my-project/package.json]
   ```

4. **Context persists:**
   - User can close Slack, bot can restart
   - When user returns to the thread, project association is still active
   - All operations continue in the same project directory

### Technical Flow

```
Slash Command → ProjectManager.resolve_project_path()
              → ProjectManager.associate_thread()
              → Store in ~/.amplifier/slack-threads.json

Message in Thread → _get_or_create_session()
                  → ProjectManager.get_thread_project()
                  → os.chdir(project_path)
                  → Execute Amplifier session
```

## Configuration

### No New Configuration Needed!

This feature leverages Amplifier's existing infrastructure:

#### Thread Storage

Thread associations are stored in:
```
~/.amplifier/slack-threads.json
```

Format:
```json
{
  "threads": {
    "C123ABC-1234567890.123": "/Users/ken/workspace/my-project",
    "C456DEF-9876543210.456": "/Users/ken/workspace/another-project"
  }
}
```

#### Project Storage

When you use `/amplifier /path/to/project`, Amplifier automatically creates:

```
~/.amplifier/projects/<project-slug>/
  sessions/
    <session-id>/
      context-messages.jsonl
      ...
```

The project slug is generated using **Amplifier CLI's algorithm**:
```
Replace / with -, add leading -
```

Example: `/Users/ken/workspace/my-project` → `-Users-ken-workspace-my-project`

This matches exactly what `amplifier session list` uses!

## Slack App Configuration

To enable slash commands, you need to configure them in your Slack app:

1. Go to https://api.slack.com/apps
2. Select your app
3. Go to **Slash Commands**
4. Create these commands:
   - `/amplifier` - Start a new session
   - `/amplifier-status` - Show active sessions
   - `/amplifier-list` - List projects
5. Leave Request URL blank (Socket Mode handles it)
6. Reinstall app if needed

See [docs/slack-slash-commands-setup.md](docs/slack-slash-commands-setup.md) for detailed setup.

## Benefits

### 1. **Multi-Project Support**
Work on multiple projects simultaneously in different threads:
```
Thread 1: /amplifier frontend
Thread 2: /amplifier backend
Thread 3: /amplifier docs
```

### 2. **Context Persistence**
Start work, take a break, come back later:
```
Monday: /amplifier my-project
        "Refactor the auth module"
        [bot makes changes]

Tuesday: [continue in same thread]
         "Now add rate limiting"
         [bot continues with full context]
```

### 3. **Team Collaboration**
Multiple people can work in the same thread on the same project:
```
Alice: /amplifier shared-project
       "Add user profiles API"

Bob:   [replies in thread]
       "Can you add validation?"

Bot:   [makes both changes in the same project]
```

### 4. **Simplified Workflow**
No need to specify paths in every command:
```
❌ Before: "Read the file /Users/ken/workspace/my-project/src/main.py"
✅ After:  "Read the file src/main.py"  (in project-associated thread)
```

## Code Changes

### Modified Files

1. **`src/slack_connector/bot.py`**
   - Added `ProjectManager` integration
   - Added slash command handlers
   - Modified `_get_or_create_session()` to use project paths

2. **`src/slack_connector/cli.py`**
   - Added `project_storage_path` parameter

3. **`docs/slack-setup.md`**
   - Added link to project management docs

4. **`README.md`**
   - Added project management to features list

### New Files

1. **`src/slack_connector/project_manager.py`** - Core project management logic
2. **`tests/test_project_manager.py`** - Comprehensive test suite (8 tests)
3. **`docs/slack-projects.md`** - User guide
4. **`docs/slack-slash-commands-setup.md`** - Setup instructions
5. **`SLACK_PROJECT_MANAGEMENT.md`** - This summary

## Testing

Run tests:
```bash
source .venv/bin/activate
PYTHONPATH=src python -m pytest tests/test_project_manager.py -v
```

Results:
```
8 passed in 0.02s ✅
```

## Future Enhancements

Potential improvements:
1. **Web UI** for managing projects and viewing active sessions
2. **Project templates** for common setups
3. **Environment variables** per project (loaded from `.env` files)
4. **Git integration** to show branch/commit info
5. **Access control** - restrict certain projects to specific users
6. **Analytics** - track which projects are used most
7. **Auto-detection** - suggest project based on file paths mentioned

## Migration

### For Existing Users

No migration needed! The feature is opt-in:
- Old behavior (no project association) still works
- Users can start using `/amplifier` whenever they want
- Existing threads continue to work as before

### For New Users

Recommended workflow:
1. Set up Slack app with slash commands
2. Create `~/.amplifier/projects.json` with your projects
3. Use `/amplifier <project>` to start new sessions
4. Enjoy project-scoped conversations!

## Support

- **Issues**: Report bugs or request features on GitHub
- **Documentation**: See [docs/slack-projects.md](docs/slack-projects.md)
- **Setup Help**: See [docs/slack-slash-commands-setup.md](docs/slack-slash-commands-setup.md)

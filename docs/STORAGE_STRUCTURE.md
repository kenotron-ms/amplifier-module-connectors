# Storage Structure - Slack Connector

## Overview

The Slack connector uses a dedicated `workspaces/` subdirectory within `~/.amplifier/` to store its configuration and state, keeping it isolated from Amplifier's core settings.

## Directory Layout

```
~/.amplifier/
├── projects/                       # Amplifier Core
│   └── <project-slug>/            # Project-specific sessions
│       ├── sessions/              # Session history
│       └── context/               # Session context
│
├── settings.yaml                   # Amplifier Core Config
│
└── workspaces/                     # Slack Connector (ISOLATED)
    ├── config.json                # Workspace configuration
    └── thread-associations.json   # Thread -> project mappings
```

## File Descriptions

### Amplifier Core Files (Unchanged)

#### `~/.amplifier/settings.yaml`
Amplifier's main configuration file containing:
- AI provider settings (API keys, model selection)
- Orchestrator configuration
- Global preferences

**Not modified by Slack connector.**

#### `~/.amplifier/projects/<project-slug>/`
Project-specific Amplifier data:
- Session history and context
- Project-scoped settings
- Conversation memory

**Used by Slack connector for session management, but structure is unchanged.**

### Slack Connector Files (Isolated)

#### `~/.amplifier/workspaces/config.json`
Slack connector workspace configuration:

```json
{
  "workspace": "~/workspace",
  "template_repo": "kenotron-ms/amplifier-template",
  "auto_init_git": true,
  "auto_switch": true
}
```

**Purpose:**
- Define where projects are created by default
- Specify which GitHub template to use
- Control git initialization behavior

**Modified by:**
- `/amplifier config set <key> <value>` command
- Automatically created on first use

#### `~/.amplifier/workspaces/thread-associations.json`
Slack thread to project path mappings:

```json
{
  "threads": {
    "C123456-1234567890.123": "/Users/ken/workspace/my-api",
    "C123456-1234567891.456": "/Users/ken/workspace/frontend",
    "C789012-1234567892.789": "/Users/ken/projects/backend"
  }
}
```

**Purpose:**
- Map Slack thread IDs to project directories
- Enable thread-scoped project context
- Persist across bot restarts

**Modified by:**
- `/amplifier new <name>` command
- `/amplifier fork <url>` command
- `/amplifier open <path>` command

## Why Isolation?

### Prevents Conflicts
- Slack connector settings don't interfere with Amplifier core
- Multiple connectors (Slack, Teams, etc.) can coexist
- Clear separation of concerns

### Maintains Compatibility
- Amplifier CLI continues to work normally
- Core settings remain untouched
- Standard Amplifier workflows unaffected

### Enables Flexibility
- Each connector can have its own configuration
- Workspace settings are connector-specific
- Thread associations are platform-specific

## User Workspace

In addition to `~/.amplifier/`, users have a workspace directory for actual project files:

```
~/workspace/                        # User Projects (Default)
├── my-api/                        # Created by /amplifier new
│   ├── .amplifier/                # From template
│   │   ├── bundle.md
│   │   └── settings.yaml
│   ├── .git/                      # Fresh git repo
│   └── README.md
│
├── frontend/                      # Created by /amplifier fork
│   ├── .amplifier/                # May or may not exist
│   ├── .git/                      # Original git history
│   └── src/
│
└── backend/                       # Opened by /amplifier open
    └── ...
```

**This location is configurable:**
```
/amplifier config set workspace ~/my-projects
```

## Data Flow

### Creating a New Project

```
User: /amplifier new my-api
  ↓
1. Read config from ~/.amplifier/workspaces/config.json
2. Clone template to ~/workspace/my-api
3. Initialize git
4. Save thread association to ~/.amplifier/workspaces/thread-associations.json
5. Amplifier creates session in ~/.amplifier/projects/<slug>/
```

### Opening Existing Project

```
User: /amplifier open my-api
  ↓
1. Read config from ~/.amplifier/workspaces/config.json
2. Resolve path: ~/workspace/my-api
3. Save thread association to ~/.amplifier/workspaces/thread-associations.json
4. Amplifier creates/loads session in ~/.amplifier/projects/<slug>/
```

### Sending Messages

```
User: "What files are in this project?"
  ↓
1. Look up thread in ~/.amplifier/workspaces/thread-associations.json
2. Get project path: ~/workspace/my-api
3. Set working directory for session
4. Execute command in project context
5. Store session in ~/.amplifier/projects/<slug>/
```

## Migration from Old Structure

If you were using an earlier version with `~/.amplifier/slack-config.json`:

### Old Structure
```
~/.amplifier/
├── slack-config.json          # OLD
└── slack-threads.json         # OLD
```

### New Structure
```
~/.amplifier/
└── workspaces/
    ├── config.json            # NEW
    └── thread-associations.json  # NEW
```

### Migration (Automatic)
The connector will automatically use the new paths. Old files can be safely removed:

```bash
rm ~/.amplifier/slack-config.json
rm ~/.amplifier/slack-threads.json
```

Or manually migrate:

```bash
# Create new directory
mkdir -p ~/.amplifier/workspaces/

# Move config
mv ~/.amplifier/slack-config.json ~/.amplifier/workspaces/config.json

# Move threads
mv ~/.amplifier/slack-threads.json ~/.amplifier/workspaces/thread-associations.json
```

## Backup and Restore

### Backing Up Slack Connector State

```bash
# Backup workspace config and thread associations
tar -czf slack-connector-backup.tar.gz -C ~/.amplifier workspaces/
```

### Restoring

```bash
# Restore workspace config and thread associations
tar -xzf slack-connector-backup.tar.gz -C ~/.amplifier/
```

**Note:** This only backs up Slack connector state. To backup full Amplifier state including sessions:

```bash
# Backup everything
tar -czf amplifier-full-backup.tar.gz -C ~ .amplifier/
```

## Security Considerations

### File Permissions

```bash
# Recommended permissions
chmod 700 ~/.amplifier/workspaces/
chmod 600 ~/.amplifier/workspaces/config.json
chmod 600 ~/.amplifier/workspaces/thread-associations.json
```

### Sensitive Data

The workspace configuration may contain:
- Workspace paths (usually safe)
- GitHub repository names (usually safe)

Thread associations contain:
- Slack thread IDs (semi-sensitive)
- Project paths (usually safe)

**No API keys or credentials are stored in workspace files.**

API keys remain in Amplifier's core `settings.yaml` which should already have restricted permissions.

## Troubleshooting

### Config not found

```
Error: Could not load config
```

**Solution:**
The connector will automatically create default config. If issues persist:

```bash
# Manually create directory
mkdir -p ~/.amplifier/workspaces/

# Restart bot - it will create default config.json
```

### Thread associations lost

```
No project associated with this thread
```

**Solution:**
Thread associations are stored in `thread-associations.json`. If lost:

```
/amplifier open <project-path>
```

This will re-associate the current thread with the project.

### Workspace directory conflicts

```
Project already exists
```

**Solution:**
Check your workspace setting:

```
/amplifier config get workspace
```

Projects are created in this directory. Either:
1. Use a different project name
2. Change workspace location: `/amplifier config set workspace ~/other-location`
3. Delete existing project if no longer needed

## Summary

The isolated `workspaces/` structure provides:

✅ **Clean separation** from Amplifier core  
✅ **No conflicts** with core settings  
✅ **Easy backup** of connector state  
✅ **Clear organization** of files  
✅ **Platform-specific** configuration  
✅ **Future-proof** for multiple connectors  

This design ensures the Slack connector enhances Amplifier without disrupting its core functionality.

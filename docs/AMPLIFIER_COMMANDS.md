# Amplifier Slash Commands

The `/amplifier` command provides project management capabilities for the Slack connector.

## Quick Start

```
/amplifier new my-project          # Create new project from template
/amplifier fork <github-url>       # Clone existing repository
/amplifier open my-project         # Switch to existing project
```

## Commands

### Project Management

#### `/amplifier new <name>`
Create a new project from the Amplifier template.

**Example:**
```
/amplifier new my-api
```

**What it does:**
1. Clones `kenotron-ms/amplifier-template` from GitHub
2. Creates project in `~/workspace/<name>` (configurable)
3. Removes original git history
4. Re-initializes git with fresh commit
5. Associates the thread with the project

**Result:**
- New project directory with `.amplifier/` configuration
- Fresh git repository
- Thread scoped to the project

---

#### `/amplifier fork <github-url> [name]`
Clone an existing GitHub repository.

**Examples:**
```
/amplifier fork https://github.com/user/repo
/amplifier fork https://github.com/user/repo my-custom-name
```

**What it does:**
1. Clones the repository to `~/workspace/`
2. Uses repo name or custom name for directory
3. Keeps original git history
4. Associates the thread with the project

---

#### `/amplifier open <name-or-path>`
Switch to an existing project.

**Examples:**
```
/amplifier open my-project                    # Name in workspace
/amplifier open ~/projects/my-app             # Absolute path
/amplifier open /Users/ken/workspace/api      # Full path
```

**What it does:**
1. Looks for project in workspace first
2. Falls back to absolute/relative path resolution
3. Associates the thread with the project

---

#### `/amplifier list`
List all projects in the workspace.

**Example:**
```
/amplifier list
```

**Output:**
```
📁 Projects in `~/workspace`

• my-api 🔗
• frontend
• data-processor 🔗

Found 3 project(s)
```

The 🔗 icon indicates a git repository.

---

#### `/amplifier pwd`
Show the current working directory for this thread.

**Example:**
```
/amplifier pwd
```

**Output:**
```
📁 Current project: my-api
`/Users/ken/workspace/my-api`
```

---

### Configuration

#### `/amplifier config`
Show all configuration settings.

**Example:**
```
/amplifier config
```

**Output:**
```
⚙️ Amplifier Configuration

• `workspace`: `~/workspace`
• `template_repo`: `kenotron-ms/amplifier-template`
• `auto_init_git`: `True`
• `auto_switch`: `True`
```

---

#### `/amplifier config get <key>`
Get a specific configuration value.

**Example:**
```
/amplifier config get workspace
```

**Output:**
```
⚙️ `workspace` = `~/workspace`
```

---

#### `/amplifier config set <key> <value>`
Update a configuration setting.

**Examples:**
```
/amplifier config set workspace ~/my-projects
/amplifier config set template_repo myorg/my-template
/amplifier config set auto_init_git false
```

**Available settings:**
- `workspace` - Base directory for projects (default: `~/workspace`)
- `template_repo` - GitHub repo for new projects (default: `kenotron-ms/amplifier-template`)
- `auto_init_git` - Initialize git for new projects (default: `true`)
- `auto_switch` - Auto-switch to project after creation (default: `true`)

---

#### `/amplifier config reset`
Reset all configuration to defaults.

**Example:**
```
/amplifier config reset
```

---

## Configuration

Configuration is stored in `~/.amplifier/workspaces/config.json` (separate from Amplifier's core settings).

**Default configuration:**
```json
{
  "workspace": "~/workspace",
  "template_repo": "kenotron-ms/amplifier-template",
  "auto_init_git": true,
  "auto_switch": true
}
```

**Storage Structure:**
```
~/.amplifier/
├── projects/                    # Amplifier core (unchanged)
├── settings.yaml                # Amplifier core (unchanged)
└── workspaces/                  # Slack connector (isolated)
    ├── config.json              # Workspace settings
    └── thread-associations.json # Thread -> project mappings
```

---

## Workflow Examples

### Starting a New Project

```
/amplifier new my-api
```

Creates a new project from the template, ready to use.

---

### Working on an Existing GitHub Repo

```
/amplifier fork https://github.com/myorg/existing-project
```

Clones the repo and sets up the session.

---

### Switching Between Projects

In thread 1:
```
/amplifier open frontend
```

In thread 2:
```
/amplifier open backend
```

Each thread maintains its own project context.

---

### Custom Workspace Location

```
/amplifier config set workspace ~/my-projects
/amplifier new api-service
```

Creates project in `~/my-projects/api-service`.

---

### Using a Custom Template

```
/amplifier config set template_repo myorg/custom-template
/amplifier new new-project
```

Creates project from your custom template.

---

## Thread Associations

Each Slack thread is associated with a project path. This means:

- **File operations** are relative to the project directory
- **Git commands** operate on the project repository
- **Multiple threads** can work on different projects simultaneously
- **Associations persist** across bot restarts

Thread associations are stored in `~/.amplifier/workspaces/thread-associations.json`.

---

## Template Structure

The default template (`kenotron-ms/amplifier-template`) includes:

```
amplifier-template/
├── .amplifier/
│   ├── bundle.md       # Amplifier behaviors
│   └── settings.yaml   # Amplifier settings
└── README.md           # Project documentation
```

When you create a new project:
1. Template is cloned
2. Original `.git` is removed
3. Fresh git repo is initialized
4. You get a clean starting point with Amplifier pre-configured

---

## Backward Compatibility

The original `/amplifier <path>` syntax still works:

```
/amplifier ~/workspace/my-project
```

This is equivalent to:
```
/amplifier open ~/workspace/my-project
```

---

## Other Commands

- `/amplifier-status` - Show active sessions in the channel
- `/amplifier-list` - List Amplifier projects from `~/.amplifier/projects/`

---

## Troubleshooting

### Project already exists

```
❌ Project already exists: `/Users/ken/workspace/my-project`
```

**Solution:** Use a different name or delete the existing project.

---

### Failed to clone repository

```
❌ Failed to clone repository: fatal: repository not found
```

**Solution:** Check the GitHub URL and ensure you have access to the repository.

---

### Project not found

```
❌ Project not found: `my-project`
```

**Solution:** 
- Use `/amplifier list` to see available projects
- Provide a full path: `/amplifier open ~/workspace/my-project`
- Create the project: `/amplifier new my-project`

---

## Implementation Details

**Components:**
- `ConfigManager` - Manages persistent configuration
- `AmplifierCommands` - Handles command routing and execution
- `ProjectManager` - Manages thread-project associations
- `SlackAmplifierBot` - Integrates commands with Slack

**Storage:**
- Slack connector config: `~/.amplifier/workspaces/config.json`
- Thread associations: `~/.amplifier/workspaces/thread-associations.json`
- Amplifier core projects: `~/.amplifier/projects/<project-slug>/` (unchanged)
- Amplifier core settings: `~/.amplifier/settings.yaml` (unchanged)

**Isolation:**
The Slack connector uses a dedicated `workspaces/` subdirectory to avoid conflicts with Amplifier's core configuration files.

**Security:**
- Commands validate paths before operations
- Git operations use subprocess with proper error handling
- Failed operations clean up partial state

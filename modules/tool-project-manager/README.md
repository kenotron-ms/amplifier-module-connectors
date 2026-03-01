# Project Manager Tool

Manage working directories and create new projects from within Amplifier sessions.

## Overview

The Project Manager tool enables multi-project workflows in Amplifier by allowing each conversation (Slack thread, Teams chat, etc.) to maintain its own working directory context. This means you can:

- Work on different projects in different Slack threads simultaneously
- Create new projects directly from chat
- Switch between projects without losing context
- Isolate work environments per conversation

## Features

### 🗂️ Working Directory Management
- Each conversation has its own working directory
- Switch directories with a simple command
- All file operations (`bash`, `filesystem`) respect the current working directory
- Working directory persists for the session lifetime

### 🆕 Project Creation
- Bootstrap new Python, Node.js, or generic projects
- Automatic git repository initialization
- Project-specific scaffolding (directory structure, config files)
- Appropriate `.gitignore` templates

### 📋 Project Listing
- Browse available projects in a directory
- Git repository indicators
- Easy navigation between projects

### 🔒 Security
- Path validation prevents directory traversal
- Configurable allowed root directories
- Sandboxing to prevent unauthorized access

## Installation

The tool is automatically mounted by the SessionManager when creating new sessions. No manual installation required.

To use in a standalone Amplifier bundle:

```yaml
# bundle.md
tools:
  - module: tool-project-manager
    source: ./modules/tool-project-manager
    config:
      allowed_roots:
        - "~/workspace"
        - "~/projects"
```

## API Reference

### `get_current_directory()`

Get the current working directory for this conversation.

**Returns**: String with current directory path

**Example**:
```python
result = await project_manager.get_current_directory()
# "📂 Current working directory: `/Users/ken/workspace/my-project`"
```

### `change_directory(path: str)`

Change the working directory for this conversation.

**Parameters**:
- `path` (str): Absolute or relative path to change to

**Returns**: Confirmation message

**Example**:
```python
result = await project_manager.change_directory("~/workspace/api-service")
# "✅ Changed working directory to: `/Users/ken/workspace/api-service`"
```

### `create_project(name: str, parent_dir: str = None, init_git: bool = True, project_type: str = "generic")`

Create a new project directory with appropriate scaffolding.

**Parameters**:
- `name` (str): Project name (directory name)
- `parent_dir` (str, optional): Parent directory (default: current working dir)
- `init_git` (bool): Initialize git repository (default: True)
- `project_type` (str): "python", "node", or "generic" (default: "generic")

**Returns**: Status message with project path

**Example**:
```python
result = await project_manager.create_project(
    name="my-api",
    project_type="python",
    init_git=True
)
# "✅ Created python project (with git): `/Users/ken/workspace/my-api`
#  
#  Actions performed:
#    • initialized git repository
#    • created .gitignore
#    • created Python project structure
#  
#  📂 Working directory switched to: `/Users/ken/workspace/my-api`"
```

### `list_projects(directory: str = None)`

List projects (directories) in a directory.

**Parameters**:
- `directory` (str, optional): Directory to list (default: current working dir)

**Returns**: Formatted list of projects

**Example**:
```python
result = await project_manager.list_projects("~/workspace")
# "Projects in `/Users/ken/workspace`:
#  📁 amplifier-module-connectors 🔗
#  📁 api-service 🔗
#  📁 frontend-app 🔗
#  📁 scripts"
```

## Project Types

### Python Projects

Creates:
```
my-project/
├── src/
│   └── my_project/
│       └── __init__.py
├── tests/
├── pyproject.toml
├── README.md
└── .gitignore
```

**pyproject.toml** includes:
- Basic project metadata
- Dev dependencies (pytest, ruff)
- Build system configuration

### Node.js Projects

Creates:
```
my-project/
├── src/
├── package.json
├── README.md
└── .gitignore
```

**package.json** includes:
- Basic project metadata
- Test script placeholder
- MIT license

### Generic Projects

Creates:
```
my-project/
├── README.md
└── .gitignore
```

Minimal structure for any project type.

## Usage Examples

### From Slack

**Create a new Python project:**
```
User: @bot create a new Python project called "user-service"
Bot: ✅ Created python project (with git): `/Users/ken/workspace/user-service`
     
     Actions performed:
       • initialized git repository
       • created .gitignore
       • created Python project structure
     
     📂 Working directory switched to: `/Users/ken/workspace/user-service`

User: @bot create a main.py file with a FastAPI app
Bot: [creates file in /Users/ken/workspace/user-service/src/user_service/main.py]
```

**Switch between projects:**
```
User: @bot switch to the frontend project
Bot: ✅ Changed working directory to: `/Users/ken/workspace/frontend-app`

User: @bot what files are here?
Bot: [lists files in frontend-app directory]
```

**List available projects:**
```
User: @bot what projects do I have?
Bot: Projects in `/Users/ken/workspace`:
     📁 amplifier-module-connectors 🔗
     📁 user-service 🔗
     📁 frontend-app 🔗
     📁 scripts
```

### From Python

```python
from tool_project_manager.tool import ProjectManagerTool

# Initialize (usually done by SessionManager)
tool = ProjectManagerTool(
    session_manager=session_manager,
    conversation_id="slack-C123-1234567890.123456",
    allowed_roots=["~/workspace", "~/projects"]
)

# Get current directory
current = await tool.get_current_directory()
print(current)  # "📂 Current working directory: `/Users/ken/workspace`"

# Create a new project
result = await tool.create_project(
    name="my-api",
    project_type="python",
    init_git=True
)
print(result)

# Switch to existing project
result = await tool.change_directory("~/workspace/frontend-app")
print(result)

# List projects
projects = await tool.list_projects("~/workspace")
print(projects)
```

## Configuration

### Allowed Root Directories

Configure which directories can be accessed:

```yaml
# bundle.md
tools:
  - module: tool-project-manager
    source: ./modules/tool-project-manager
    config:
      allowed_roots:
        - "~/workspace"
        - "~/projects"
        - "/opt/company/repos"
```

Or in Python:

```python
tool = ProjectManagerTool(
    session_manager=session_manager,
    conversation_id=conv_id,
    allowed_roots=[
        os.path.expanduser("~/workspace"),
        os.path.expanduser("~/projects"),
    ]
)
```

### Default Working Directory

Set the default working directory for new sessions:

```python
session_manager = SessionManager(
    bundle_path="./bundle.md",
    default_workdir=os.path.expanduser("~/workspace")
)
```

## Persistence

Working directories are stored in two places:

1. **In-memory** - `SessionManager.working_dirs` dictionary
2. **Session context** - Persisted to disk (if context-persistent module is used)

When a session is recreated (e.g., after bot restart), the working directory is automatically restored from the session context.

## Security Considerations

### Path Validation

All paths are validated against `allowed_roots` to prevent:
- Directory traversal attacks (`../../etc/passwd`)
- Access to unauthorized directories
- Accidental operations in system directories

### Path Resolution

Paths are resolved as follows:
1. Expand user home directory (`~` → `/Users/ken`)
2. Convert to absolute path
3. Validate against allowed roots
4. Check directory exists

### Recommended Configuration

```python
# Restrict to specific workspace directories
allowed_roots = [
    os.path.expanduser("~/workspace"),
    os.path.expanduser("~/projects"),
]

# Or for team environments
allowed_roots = [
    "/opt/company/repos",
    "/home/shared/projects",
]
```

## Thread Isolation

Each conversation (Slack thread, Teams chat) maintains its own working directory:

```
Thread A: @bot pwd
Bot: 📂 Current working directory: `/Users/ken/workspace/project-1`

Thread B: @bot pwd
Bot: 📂 Current working directory: `/Users/ken/workspace/project-2`
```

This allows:
- Multiple developers working on different projects simultaneously
- Context isolation between different work streams
- No interference between conversations

## Integration with Other Tools

The working directory affects:

- **bash tool**: Commands execute in the current working directory
- **filesystem tool**: File paths are relative to the current working directory
- **git operations**: Git commands operate on the current project

Example workflow:
```
User: @bot create a new Python project called "api"
Bot: ✅ Created python project: `/Users/ken/workspace/api`
     📂 Working directory switched to: `/Users/ken/workspace/api`

User: @bot create src/api/main.py with a FastAPI app
Bot: [filesystem tool creates file at /Users/ken/workspace/api/src/api/main.py]

User: @bot run pytest
Bot: [bash tool executes in /Users/ken/workspace/api]
```

## Troubleshooting

### "Access denied" errors

**Problem**: Path is outside allowed roots

**Solution**: Add the directory to `allowed_roots` configuration

```python
tool = ProjectManagerTool(
    session_manager=session_manager,
    conversation_id=conv_id,
    allowed_roots=[
        "~/workspace",
        "~/new-location",  # Add this
    ]
)
```

### Working directory not persisting

**Problem**: Directory resets after bot restart

**Solution**: Ensure you're using `context-persistent` module in your bundle:

```yaml
session:
  context:
    module: context-persistent
    source: git+https://github.com/microsoft/amplifier-module-context-persistent@main
```

### "Directory does not exist" errors

**Problem**: Trying to change to non-existent directory

**Solution**: Create the directory first or use `create_project`:

```python
# Instead of:
await project_manager.change_directory("~/workspace/new-project")  # Fails

# Do:
await project_manager.create_project("new-project", parent_dir="~/workspace")
```

## Future Enhancements

- **Git integration**: Clone repos, create branches, commit/push
- **Project templates**: Custom scaffolding templates
- **Project bookmarks**: Save favorite project paths
- **Multi-project support**: Work on multiple projects in one thread
- **Project search**: Find projects by name or attributes

## Contributing

See the main [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](../../LICENSE) for details.

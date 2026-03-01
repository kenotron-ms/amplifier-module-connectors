---
module:
  name: tool-project-manager
  version: 1.0.0
  type: tool
  description: Manage working directories and projects for Amplifier sessions

config:
  allowed_roots:
    - "~/workspace"
    - "~/projects"
---

# Project Manager Tool

Manage working directories and create new projects from within Amplifier sessions.

## Features

- **Change Directory**: Switch the working directory for the current conversation
- **Create Projects**: Bootstrap new Python, Node.js, or generic projects
- **List Projects**: Browse available projects in a directory
- **Git Integration**: Automatically initialize git repositories

## Usage

This tool is automatically mounted in Amplifier sessions and provides the following functions:

### `get_current_directory()`
Get the current working directory for this conversation.

**Returns**: Current working directory path

**Example**:
```python
await project_manager.get_current_directory()
# Returns: "📂 Current working directory: `/Users/ken/workspace/my-project`"
```

### `change_directory(path: str)`
Change the working directory for this conversation.

**Parameters**:
- `path` (str): Absolute or relative path to change to

**Returns**: Confirmation message with new working directory

**Example**:
```python
await project_manager.change_directory("~/workspace/api-service")
# Returns: "✅ Changed working directory to: `/Users/ken/workspace/api-service`"
```

### `create_project(name: str, parent_dir: str = None, init_git: bool = True, project_type: str = "generic")`
Create a new project directory and optionally initialize it.

**Parameters**:
- `name` (str): Project name (will be the directory name)
- `parent_dir` (str, optional): Parent directory (default: current working dir)
- `init_git` (bool): Whether to initialize a git repository (default: True)
- `project_type` (str): Type of project - "python", "node", or "generic" (default: "generic")

**Returns**: Status message with project path

**Example**:
```python
await project_manager.create_project(
    name="my-api",
    project_type="python",
    init_git=True
)
# Returns: "✅ Created python project (with git): `/Users/ken/workspace/my-api`
#           📂 Working directory switched to: `/Users/ken/workspace/my-api`"
```

### `list_projects(directory: str = None)`
List projects in a directory.

**Parameters**:
- `directory` (str, optional): Directory to list (default: current working dir)

**Returns**: Formatted list of projects

**Example**:
```python
await project_manager.list_projects("~/workspace")
# Returns: "Projects in `/Users/ken/workspace`:
#           📁 amplifier-module-connectors 🔗
#           📁 api-service 🔗
#           📁 frontend-app"
```

## Project Types

### Python Projects
Creates:
- `src/{name}/` directory with `__init__.py`
- `tests/` directory
- `pyproject.toml` with basic configuration
- `README.md`
- `.gitignore` for Python

### Node.js Projects
Creates:
- `src/` directory
- `package.json` with basic configuration
- `README.md`
- `.gitignore` for Node.js

### Generic Projects
Creates:
- Basic `.gitignore`
- Empty project directory

## Security

The tool validates paths to prevent:
- Directory traversal attacks
- Access to unauthorized directories
- Operations outside allowed root directories

Configure `allowed_roots` in the module config to restrict access.

## Integration

This tool is designed to work seamlessly with other Amplifier tools:

- **filesystem tool**: File operations use the current working directory
- **bash tool**: Commands execute in the current working directory
- **git operations**: Work within the current project context

## Thread Isolation

Each Slack thread (or conversation) maintains its own working directory:
- Thread A can work on `~/workspace/project-1`
- Thread B can work on `~/workspace/project-2`
- Working directories persist for the session lifetime

## Examples

### Create and Work on New Project

```
User: Create a new Python API project called "user-service"
Bot: [executes create_project("user-service", project_type="python")]
     ✅ Created python project (with git): `/Users/ken/workspace/user-service`
     📂 Working directory switched to: `/Users/ken/workspace/user-service`

User: Create a main.py file with a FastAPI app
Bot: [filesystem tool creates file in /Users/ken/workspace/user-service/src/user_service/main.py]
     ✅ Created main.py with FastAPI application
```

### Switch Between Projects

```
User: Switch to the frontend project
Bot: [executes change_directory("~/workspace/frontend-app")]
     ✅ Changed working directory to: `/Users/ken/workspace/frontend-app`

User: What files are here?
Bot: [bash tool lists files in /Users/ken/workspace/frontend-app]
     ...
```

### Browse Available Projects

```
User: What projects do I have?
Bot: [executes list_projects("~/workspace")]
     Projects in `/Users/ken/workspace`:
     📁 amplifier-module-connectors 🔗
     📁 user-service 🔗
     📁 frontend-app 🔗
     📁 scripts
```

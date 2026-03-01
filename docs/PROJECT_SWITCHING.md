# Project Switching Feature

## Overview

Allow users to switch the working directory for a Slack thread's Amplifier session, enabling:
- Working on different projects in different threads
- Creating new project folders/repos from Slack
- Isolating work contexts per conversation

## Architecture

### Current State
- Each Slack thread has its own Amplifier session
- Sessions use a shared bundle and work from the connector's working directory
- All threads share the same filesystem context

### Proposed State
- Each session can have its own working directory
- Users can switch directories with a command like `@bot /cd /path/to/project`
- Users can create new projects with `@bot /new-project my-app`
- Working directory is stored in session metadata

## Implementation Plan

### 1. Session Working Directory Tracking

```python
# src/connector_core/session_manager.py

class SessionManager:
    def __init__(self, bundle_path: str, default_workdir: str = None):
        self.bundle_path = bundle_path
        self.default_workdir = default_workdir or os.getcwd()
        
        # Track working directory per session
        self.working_dirs: dict[str, str] = {}  # conversation_id -> workdir
        
        # Existing fields...
        self.prepared: Any = None
        self.sessions: dict[str, Any] = {}
        self.locks: dict[str, asyncio.Lock] = {}
    
    def get_working_dir(self, conversation_id: str) -> str:
        """Get the working directory for a conversation."""
        return self.working_dirs.get(conversation_id, self.default_workdir)
    
    def set_working_dir(self, conversation_id: str, path: str) -> None:
        """Set the working directory for a conversation."""
        self.working_dirs[conversation_id] = os.path.abspath(path)
```

### 2. Project Management Tool

Create a new Amplifier tool for project/directory management:

```python
# modules/tool-project-manager/tool.py

import os
import subprocess
from pathlib import Path
from typing import Literal, Optional

class ProjectManagerTool:
    """
    Manage working directories and projects for Amplifier sessions.
    
    Allows switching between projects, creating new ones, and initializing repos.
    """
    
    def __init__(self, session_manager, conversation_id: str):
        self.session_manager = session_manager
        self.conversation_id = conversation_id
    
    async def change_directory(self, path: str) -> str:
        """
        Change the working directory for this conversation.
        
        Args:
            path: Absolute or relative path to change to
            
        Returns:
            Confirmation message with new working directory
        """
        # Resolve path
        current_dir = self.session_manager.get_working_dir(self.conversation_id)
        
        if os.path.isabs(path):
            new_dir = path
        else:
            new_dir = os.path.join(current_dir, path)
        
        new_dir = os.path.abspath(new_dir)
        
        # Validate directory exists
        if not os.path.isdir(new_dir):
            return f"❌ Directory does not exist: {new_dir}"
        
        # Update working directory
        self.session_manager.set_working_dir(self.conversation_id, new_dir)
        
        return f"✅ Changed working directory to: `{new_dir}`"
    
    async def get_current_directory(self) -> str:
        """Get the current working directory for this conversation."""
        workdir = self.session_manager.get_working_dir(self.conversation_id)
        return f"📂 Current working directory: `{workdir}`"
    
    async def create_project(
        self,
        name: str,
        parent_dir: Optional[str] = None,
        init_git: bool = True,
        project_type: Literal["python", "node", "generic"] = "generic"
    ) -> str:
        """
        Create a new project directory and optionally initialize it.
        
        Args:
            name: Project name (will be the directory name)
            parent_dir: Parent directory (default: current working dir)
            init_git: Whether to initialize a git repository
            project_type: Type of project to scaffold
            
        Returns:
            Status message with project path
        """
        # Determine parent directory
        if parent_dir:
            parent = os.path.abspath(parent_dir)
        else:
            parent = self.session_manager.get_working_dir(self.conversation_id)
        
        # Create project directory
        project_path = os.path.join(parent, name)
        
        if os.path.exists(project_path):
            return f"❌ Project already exists: {project_path}"
        
        try:
            os.makedirs(project_path, exist_ok=False)
            
            # Initialize git if requested
            if init_git:
                subprocess.run(
                    ["git", "init"],
                    cwd=project_path,
                    check=True,
                    capture_output=True
                )
                
                # Create .gitignore
                gitignore_content = self._get_gitignore_template(project_type)
                with open(os.path.join(project_path, ".gitignore"), "w") as f:
                    f.write(gitignore_content)
            
            # Scaffold based on project type
            if project_type == "python":
                self._scaffold_python_project(project_path, name)
            elif project_type == "node":
                self._scaffold_node_project(project_path, name)
            
            # Switch to the new project
            self.session_manager.set_working_dir(self.conversation_id, project_path)
            
            git_status = " (with git)" if init_git else ""
            return (
                f"✅ Created {project_type} project{git_status}: `{project_path}`\n"
                f"📂 Working directory switched to: `{project_path}`"
            )
            
        except Exception as e:
            return f"❌ Failed to create project: {e}"
    
    async def list_projects(self, directory: Optional[str] = None) -> str:
        """
        List projects in a directory.
        
        Args:
            directory: Directory to list (default: current working dir)
            
        Returns:
            Formatted list of projects
        """
        if directory:
            target_dir = os.path.abspath(directory)
        else:
            target_dir = self.session_manager.get_working_dir(self.conversation_id)
        
        if not os.path.isdir(target_dir):
            return f"❌ Not a directory: {target_dir}"
        
        try:
            entries = []
            for entry in sorted(os.listdir(target_dir)):
                full_path = os.path.join(target_dir, entry)
                if os.path.isdir(full_path):
                    # Check if it's a git repo
                    is_git = os.path.isdir(os.path.join(full_path, ".git"))
                    git_marker = " 🔗" if is_git else ""
                    entries.append(f"📁 {entry}{git_marker}")
            
            if not entries:
                return f"No directories found in: `{target_dir}`"
            
            return f"Projects in `{target_dir}`:\n" + "\n".join(entries)
            
        except Exception as e:
            return f"❌ Error listing directory: {e}"
    
    def _get_gitignore_template(self, project_type: str) -> str:
        """Get .gitignore template for project type."""
        templates = {
            "python": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.venv/
venv/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
""",
            "node": """# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.env

# Build
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
""",
            "generic": """# Environment
.env
.venv/
venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
        }
        return templates.get(project_type, templates["generic"])
    
    def _scaffold_python_project(self, path: str, name: str) -> None:
        """Create basic Python project structure."""
        # Create directories
        os.makedirs(os.path.join(path, "src", name), exist_ok=True)
        os.makedirs(os.path.join(path, "tests"), exist_ok=True)
        
        # Create __init__.py
        Path(os.path.join(path, "src", name, "__init__.py")).touch()
        
        # Create pyproject.toml
        pyproject = f"""[project]
name = "{name}"
version = "0.1.0"
description = ""
requires-python = ">=3.11"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
        with open(os.path.join(path, "pyproject.toml"), "w") as f:
            f.write(pyproject)
        
        # Create README.md
        readme = f"# {name}\n\nA new Python project.\n"
        with open(os.path.join(path, "README.md"), "w") as f:
            f.write(readme)
    
    def _scaffold_node_project(self, path: str, name: str) -> None:
        """Create basic Node.js project structure."""
        # Create directories
        os.makedirs(os.path.join(path, "src"), exist_ok=True)
        
        # Create package.json
        package_json = {
            "name": name,
            "version": "0.1.0",
            "description": "",
            "main": "src/index.js",
            "scripts": {
                "test": "echo \"Error: no test specified\" && exit 1"
            }
        }
        import json
        with open(os.path.join(path, "package.json"), "w") as f:
            json.dump(package_json, f, indent=2)
        
        # Create README.md
        readme = f"# {name}\n\nA new Node.js project.\n"
        with open(os.path.join(path, "README.md"), "w") as f:
            f.write(readme)
```

### 3. Update SessionManager to Pass Working Directory

```python
# src/connector_core/session_manager.py

async def get_or_create_session(
    self,
    conversation_id: str,
    approval_system: Any,
    display_system: Optional[Any] = None,
    platform_tool: Optional[Any] = None,
) -> tuple[Any, asyncio.Lock]:
    """Get existing session or create a new one for a conversation."""
    if self.prepared is None:
        raise RuntimeError("SessionManager.initialize() must be called first")
    
    if conversation_id not in self.sessions:
        logger.info(f"Creating new session: {conversation_id}")
        
        # Get working directory for this conversation
        working_dir = self.get_working_dir(conversation_id)
        
        # Create session with working directory
        session = await self.prepared.create_session(
            session_id=conversation_id,
            approval_system=approval_system,
            display_system=display_system,
            working_directory=working_dir,  # Pass working directory
        )
        
        # Mount platform-specific tool if provided
        if platform_tool is not None:
            # ... existing tool mounting code ...
        
        # Mount project manager tool
        from tool_project_manager import ProjectManagerTool
        project_tool = ProjectManagerTool(self, conversation_id)
        await session.coordinator.mount("tools", project_tool, name="project_manager")
        
        # Cache session and create lock
        self.sessions[conversation_id] = session
        self.locks[conversation_id] = asyncio.Lock()
    
    return self.sessions[conversation_id], self.locks[conversation_id]
```

### 4. Update Bundle to Include Project Manager Tool

```yaml
# bundle.md

tools:
  - module: tool-project-manager
    source: ./modules/tool-project-manager
  - module: tool-slack-reply
    source: ./modules/tool-slack-reply
  # ... other tools ...
```

### 5. Add Commands to System Prompt

```markdown
# bundle.md (system prompt section)

## Project Management

You can manage projects and working directories for this conversation:

- `project_manager.get_current_directory()` - Show current working directory
- `project_manager.change_directory(path)` - Switch to a different directory
- `project_manager.create_project(name, project_type="python"|"node"|"generic", init_git=True)` - Create a new project
- `project_manager.list_projects(directory=None)` - List projects in a directory

Each Slack thread maintains its own working directory. When you switch directories or create a project, 
all subsequent file operations (bash, filesystem) will use that directory as the working context.

### Example Usage

User: "Create a new Python project called my-api"
You: Use `project_manager.create_project("my-api", project_type="python", init_git=True)`

User: "Switch to the other project in ~/workspace/frontend"
You: Use `project_manager.change_directory("~/workspace/frontend")`
```

## Usage Examples

### Switch to Existing Project

```
User: @bot switch to ~/workspace/my-project
Bot: ✅ Changed working directory to: `/Users/ken/workspace/my-project`
```

### Create New Python Project

```
User: @bot create a new Python project called "api-service"
Bot: [executes project_manager.create_project("api-service", project_type="python")]
     ✅ Created python project (with git): `/Users/ken/workspace/api-service`
     📂 Working directory switched to: `/Users/ken/workspace/api-service`
```

### List Available Projects

```
User: @bot what projects are in ~/workspace?
Bot: [executes project_manager.list_projects("~/workspace")]
     Projects in `/Users/ken/workspace`:
     📁 amplifier-module-connectors 🔗
     📁 api-service 🔗
     📁 frontend-app 🔗
     📁 scripts
```

### Check Current Directory

```
User: @bot where am I working?
Bot: [executes project_manager.get_current_directory()]
     📂 Current working directory: `/Users/ken/workspace/api-service`
```

## Benefits

1. **Thread Isolation** - Each Slack thread can work on a different project
2. **Project Creation** - Bootstrap new projects without leaving Slack
3. **Context Switching** - Easily switch between projects mid-conversation
4. **Persistent State** - Working directory persists for the thread's session
5. **No Confusion** - Clear which project you're working on in each thread

## Persistence Considerations

### Session Restart Behavior

When the bot restarts, working directory mappings are lost. Options:

1. **Store in Session Context** (Recommended)
   - Save working directory in session's persistent context
   - Automatically restore on session recreation
   
2. **Store in Database**
   - Persist mappings to SQLite/JSON file
   - Load on startup
   
3. **Default Behavior**
   - Start with default working directory
   - User re-specifies if needed

### Implementation: Context Storage

```python
# When changing directory
async def change_directory(self, path: str) -> str:
    # ... existing validation ...
    
    # Update session manager
    self.session_manager.set_working_dir(self.conversation_id, new_dir)
    
    # Store in session context for persistence
    session = self.session_manager.sessions.get(self.conversation_id)
    if session and hasattr(session, 'context'):
        await session.context.set_metadata('working_directory', new_dir)
    
    return f"✅ Changed working directory to: `{new_dir}`"

# When creating session
async def get_or_create_session(...):
    # ... create session ...
    
    # Try to restore working directory from context
    if hasattr(session, 'context'):
        saved_dir = await session.context.get_metadata('working_directory')
        if saved_dir and os.path.isdir(saved_dir):
            self.working_dirs[conversation_id] = saved_dir
            logger.info(f"Restored working directory: {saved_dir}")
```

## Security Considerations

1. **Path Validation** - Prevent directory traversal attacks
2. **Permissions** - Only allow access to authorized directories
3. **Sandboxing** - Consider restricting to specific parent directories

```python
# Add to ProjectManagerTool

def __init__(self, session_manager, conversation_id: str, allowed_roots: list[str] = None):
    self.session_manager = session_manager
    self.conversation_id = conversation_id
    self.allowed_roots = allowed_roots or [os.path.expanduser("~/workspace")]

def _validate_path(self, path: str) -> bool:
    """Ensure path is within allowed roots."""
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(root) for root in self.allowed_roots)

async def change_directory(self, path: str) -> str:
    # ... resolve path ...
    
    # Validate path is allowed
    if not self._validate_path(new_dir):
        return f"❌ Access denied: Path must be within allowed directories"
    
    # ... rest of implementation ...
```

## Future Enhancements

1. **Git Integration**
   - Clone repos directly from Slack
   - Create branches per thread
   - Commit/push from conversation

2. **Project Templates**
   - Custom scaffolding templates
   - Organization-specific boilerplates

3. **Multi-Project Support**
   - Work on multiple projects in one thread
   - Quick switching with shortcuts

4. **Project Bookmarks**
   - Save favorite project paths
   - Quick access with aliases

## Migration Path

1. **Phase 1**: Add `tool-project-manager` module
2. **Phase 2**: Update `SessionManager` to track working directories
3. **Phase 3**: Add persistence via session context
4. **Phase 4**: Add security/sandboxing features
5. **Phase 5**: Enhanced git integration

---

**Status**: Design Complete - Ready for Implementation
**Priority**: High - Core feature for multi-project workflows

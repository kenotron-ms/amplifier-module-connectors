"""
Project Manager Tool for Amplifier

Manages working directories and project creation within Amplifier sessions.
Each conversation can have its own working directory, enabling multi-project workflows.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Literal, Optional, Any


class ProjectManagerTool:
    """
    Manage working directories and projects for Amplifier sessions.
    
    Allows switching between projects, creating new ones, and initializing repos.
    Each conversation maintains its own working directory context.
    """
    
    def __init__(
        self,
        session_manager: Any,
        conversation_id: str,
        allowed_roots: Optional[list[str]] = None
    ):
        """
        Initialize the project manager tool.
        
        Args:
            session_manager: The SessionManager instance managing this session
            conversation_id: Unique identifier for this conversation
            allowed_roots: List of allowed root directories (for security)
        """
        self.session_manager = session_manager
        self.conversation_id = conversation_id
        
        # Security: restrict to specific root directories
        if allowed_roots:
            self.allowed_roots = [os.path.abspath(os.path.expanduser(r)) for r in allowed_roots]
        else:
            # Default: allow workspace and projects directories
            self.allowed_roots = [
                os.path.abspath(os.path.expanduser("~/workspace")),
                os.path.abspath(os.path.expanduser("~/projects")),
            ]
    
    def _validate_path(self, path: str) -> tuple[bool, str]:
        """
        Validate that a path is within allowed root directories.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (is_valid, absolute_path)
        """
        abs_path = os.path.abspath(os.path.expanduser(path))
        
        # Check if path is within any allowed root
        for root in self.allowed_roots:
            if abs_path.startswith(root):
                return True, abs_path
        
        return False, abs_path
    
    async def get_current_directory(self) -> str:
        """
        Get the current working directory for this conversation.
        
        Returns:
            Current working directory path with emoji indicator
        """
        workdir = self.session_manager.get_working_dir(self.conversation_id)
        return f"📂 Current working directory: `{workdir}`"
    
    async def change_directory(self, path: str) -> str:
        """
        Change the working directory for this conversation.
        
        All subsequent file operations will use this directory as the working context.
        
        Args:
            path: Absolute or relative path to change to
            
        Returns:
            Confirmation message with new working directory
        """
        # Resolve path (relative to current working dir if not absolute)
        current_dir = self.session_manager.get_working_dir(self.conversation_id)
        
        if os.path.isabs(path):
            new_dir = os.path.expanduser(path)
        else:
            new_dir = os.path.join(current_dir, path)
        
        new_dir = os.path.abspath(new_dir)
        
        # Validate path is allowed
        is_valid, validated_path = self._validate_path(new_dir)
        if not is_valid:
            allowed = "\n".join(f"  - {root}" for root in self.allowed_roots)
            return (
                f"❌ Access denied: Path must be within allowed directories:\n{allowed}\n\n"
                f"Attempted path: `{validated_path}`"
            )
        
        # Validate directory exists
        if not os.path.isdir(validated_path):
            return f"❌ Directory does not exist: `{validated_path}`"
        
        # Update working directory in session manager
        self.session_manager.set_working_dir(self.conversation_id, validated_path)
        
        # Try to persist to session context (if available)
        try:
            session = self.session_manager.sessions.get(self.conversation_id)
            if session and hasattr(session, 'context') and hasattr(session.context, 'set_metadata'):
                await session.context.set_metadata('working_directory', validated_path)
        except Exception:
            # Best effort - don't fail if persistence isn't available
            pass
        
        return f"✅ Changed working directory to: `{validated_path}`"
    
    async def create_project(
        self,
        name: str,
        parent_dir: Optional[str] = None,
        init_git: bool = True,
        project_type: Literal["python", "node", "generic"] = "generic"
    ) -> str:
        """
        Create a new project directory and optionally initialize it.
        
        Creates a new project with appropriate scaffolding based on type.
        Automatically switches the working directory to the new project.
        
        Args:
            name: Project name (will be the directory name)
            parent_dir: Parent directory (default: current working dir)
            init_git: Whether to initialize a git repository (default: True)
            project_type: Type of project - "python", "node", or "generic"
            
        Returns:
            Status message with project path and actions taken
        """
        # Determine parent directory
        if parent_dir:
            parent = os.path.abspath(os.path.expanduser(parent_dir))
        else:
            parent = self.session_manager.get_working_dir(self.conversation_id)
        
        # Validate parent directory is allowed
        is_valid, validated_parent = self._validate_path(parent)
        if not is_valid:
            allowed = "\n".join(f"  - {root}" for root in self.allowed_roots)
            return (
                f"❌ Access denied: Parent directory must be within allowed directories:\n{allowed}\n\n"
                f"Attempted path: `{validated_parent}`"
            )
        
        # Create project path
        project_path = os.path.join(validated_parent, name)
        
        # Check if project already exists
        if os.path.exists(project_path):
            return f"❌ Project already exists: `{project_path}`"
        
        try:
            # Create project directory
            os.makedirs(project_path, exist_ok=False)
            
            actions = []
            
            # Initialize git if requested
            if init_git:
                result = subprocess.run(
                    ["git", "init"],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                    text=True
                )
                actions.append("initialized git repository")
                
                # Create .gitignore
                gitignore_content = self._get_gitignore_template(project_type)
                with open(os.path.join(project_path, ".gitignore"), "w") as f:
                    f.write(gitignore_content)
                actions.append("created .gitignore")
            
            # Scaffold based on project type
            if project_type == "python":
                self._scaffold_python_project(project_path, name)
                actions.append("created Python project structure")
            elif project_type == "node":
                self._scaffold_node_project(project_path, name)
                actions.append("created Node.js project structure")
            else:
                # Generic project - just create README
                readme = f"# {name}\n\nA new project.\n"
                with open(os.path.join(project_path, "README.md"), "w") as f:
                    f.write(readme)
                actions.append("created README.md")
            
            # Switch to the new project
            self.session_manager.set_working_dir(self.conversation_id, project_path)
            
            # Try to persist to session context
            try:
                session = self.session_manager.sessions.get(self.conversation_id)
                if session and hasattr(session, 'context') and hasattr(session.context, 'set_metadata'):
                    await session.context.set_metadata('working_directory', project_path)
            except Exception:
                pass
            
            actions_str = "\n".join(f"  • {action}" for action in actions)
            git_status = " (with git)" if init_git else ""
            
            return (
                f"✅ Created {project_type} project{git_status}: `{project_path}`\n\n"
                f"Actions performed:\n{actions_str}\n\n"
                f"📂 Working directory switched to: `{project_path}`"
            )
            
        except subprocess.CalledProcessError as e:
            return f"❌ Git initialization failed: {e.stderr}"
        except Exception as e:
            # Clean up on failure
            if os.path.exists(project_path):
                import shutil
                try:
                    shutil.rmtree(project_path)
                except Exception:
                    pass
            return f"❌ Failed to create project: {e}"
    
    async def list_projects(self, directory: Optional[str] = None) -> str:
        """
        List projects (directories) in a directory.
        
        Displays directories with indicators for git repositories.
        
        Args:
            directory: Directory to list (default: current working dir)
            
        Returns:
            Formatted list of projects with git indicators
        """
        # Determine target directory
        if directory:
            target_dir = os.path.abspath(os.path.expanduser(directory))
        else:
            target_dir = self.session_manager.get_working_dir(self.conversation_id)
        
        # Validate directory is allowed
        is_valid, validated_dir = self._validate_path(target_dir)
        if not is_valid:
            allowed = "\n".join(f"  - {root}" for root in self.allowed_roots)
            return (
                f"❌ Access denied: Directory must be within allowed directories:\n{allowed}\n\n"
                f"Attempted path: `{validated_dir}`"
            )
        
        # Validate directory exists
        if not os.path.isdir(validated_dir):
            return f"❌ Not a directory: `{validated_dir}`"
        
        try:
            entries = []
            for entry in sorted(os.listdir(validated_dir)):
                full_path = os.path.join(validated_dir, entry)
                if os.path.isdir(full_path):
                    # Check if it's a git repo
                    is_git = os.path.isdir(os.path.join(full_path, ".git"))
                    git_marker = " 🔗" if is_git else ""
                    entries.append(f"📁 {entry}{git_marker}")
            
            if not entries:
                return f"No directories found in: `{validated_dir}`"
            
            entries_str = "\n".join(entries)
            return f"Projects in `{validated_dir}`:\n{entries_str}"
            
        except PermissionError:
            return f"❌ Permission denied: `{validated_dir}`"
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

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100
"""
        with open(os.path.join(path, "pyproject.toml"), "w") as f:
            f.write(pyproject)
        
        # Create README.md
        readme = f"""# {name}

A new Python project.

## Installation

```bash
pip install -e .
```

## Development

```bash
pip install -e .[dev]
pytest tests/
```
"""
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
            },
            "keywords": [],
            "author": "",
            "license": "MIT"
        }
        with open(os.path.join(path, "package.json"), "w") as f:
            json.dump(package_json, f, indent=2)
            f.write("\n")  # Add trailing newline
        
        # Create README.md
        readme = f"""# {name}

A new Node.js project.

## Installation

```bash
npm install
```

## Development

```bash
npm test
```
"""
        with open(os.path.join(path, "README.md"), "w") as f:
            f.write(readme)

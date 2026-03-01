"""
Project and thread management for Slack connector.

Manages:
- Thread -> project associations using Amplifier's existing project structure
- Leverages ~/.amplifier/projects/ for session storage
- Uses Amplifier CLI's project slug system

Storage:
- Thread associations: ~/.amplifier/workspaces/thread-associations.json
- Amplifier projects: ~/.amplifier/projects/ (unchanged)
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_project_slug(project_path: Path) -> str:
    """
    Generate project slug from path (matches Amplifier CLI's project_utils.py).
    
    The slug is a deterministic identifier based on the absolute path.
    This enables project-scoped session storage and filtering.
    
    Examples:
        /Users/ken/workspace/myapp -> -Users-ken-workspace-myapp
        /tmp -> -tmp
    """
    resolved = project_path.resolve()
    
    # Replace path separators and colons with hyphens
    slug = str(resolved).replace("/", "-").replace("\\", "-").replace(":", "")
    
    # Ensure it starts with hyphen for readability
    if not slug.startswith("-"):
        slug = "-" + slug
    
    return slug


class ProjectManager:
    """
    Manages thread associations using Amplifier's existing project infrastructure.
    
    Instead of inventing a new registry, we leverage:
    - ~/.amplifier/projects/<project-slug>/ for project data
    - Existing project slug system for path -> identifier mapping
    - Simple JSON file for thread -> path associations
    """
    
    def __init__(self, storage_path: Optional[str] = None) -> None:
        """
        Initialize project manager.
        
        Args:
            storage_path: Path to JSON file for thread associations.
                         Defaults to ~/.amplifier/workspaces/thread-associations.json
        """
        if storage_path is None:
            # Use dedicated workspaces directory to avoid conflicts with Amplifier core
            workspaces_dir = Path.home() / ".amplifier" / "workspaces"
            storage_path = str(workspaces_dir / "thread-associations.json")
        
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread associations: thread_id -> project_path
        self._thread_projects: dict[str, str] = {}
        
        self._load()
    
    def _load(self) -> None:
        """Load thread associations from disk."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self._thread_projects = data.get("threads", {})
            logger.info(f"Loaded {len(self._thread_projects)} thread associations")
        except Exception as e:
            logger.warning(f"Could not load thread associations: {e}")
    
    def _save(self) -> None:
        """Save thread associations to disk."""
        try:
            data = {
                "threads": self._thread_projects,
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save thread associations: {e}")
    
    def _discover_amplifier_projects(self) -> list[str]:
        """
        Discover projects from ~/.amplifier/projects/ directory.
        
        Returns:
            List of project slugs that have sessions
        """
        projects_dir = Path.home() / ".amplifier" / "projects"
        if not projects_dir.exists():
            return []
        
        projects = []
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            
            # Check if this is a real project with sessions
            sessions_dir = project_dir / "sessions"
            if sessions_dir.exists():
                projects.append(project_dir.name)
        
        return sorted(projects)
    
    def resolve_project_path(self, name_or_path: str) -> tuple[str, str]:
        """
        Resolve a project name or path to an absolute path.
        
        Args:
            name_or_path: Either a directory path (absolute or relative)
        
        Returns:
            Tuple of (resolved_path, display_name)
        
        Raises:
            ValueError: If path doesn't exist or isn't a directory
        """
        # Treat as a path and resolve it
        resolved = Path(name_or_path).expanduser().resolve()
        
        if not resolved.exists():
            raise ValueError(f"Path does not exist: {resolved}")
        
        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")
        
        # Use directory name as display name
        display_name = resolved.name
        return str(resolved), display_name
    
    def associate_thread(self, thread_id: str, project_path: str) -> None:
        """
        Associate a thread with a project path.
        
        Args:
            thread_id: Unique thread identifier (e.g., "C123-1234567890.123")
            project_path: Absolute path to project directory
        """
        self._thread_projects[thread_id] = project_path
        self._save()
        logger.info(f"Associated thread {thread_id} with {project_path}")
    
    def get_thread_project(self, thread_id: str) -> Optional[str]:
        """
        Get the project path associated with a thread.
        
        Args:
            thread_id: Unique thread identifier
        
        Returns:
            Project path or None if not associated
        """
        return self._thread_projects.get(thread_id)
    
    def clear_thread_association(self, thread_id: str) -> bool:
        """
        Clear the project association for a thread.
        
        Args:
            thread_id: Unique thread identifier
        
        Returns:
            True if association was cleared, False if none existed
        """
        if thread_id in self._thread_projects:
            del self._thread_projects[thread_id]
            self._save()
            logger.info(f"Cleared association for thread {thread_id}")
            return True
        return False
    
    def list_projects(self) -> list[str]:
        """
        List projects discovered from ~/.amplifier/projects/.
        
        Returns:
            List of project slugs
        """
        return self._discover_amplifier_projects()
    
    def get_thread_display_name(self, thread_id: str) -> Optional[str]:
        """
        Get a display name for the project associated with a thread.
        
        Args:
            thread_id: Unique thread identifier
        
        Returns:
            Display name (directory name) or None if not associated
        """
        project_path = self.get_thread_project(thread_id)
        if not project_path:
            return None
        
        # Use directory name as display name
        return Path(project_path).name
    
    def get_project_slug(self, project_path: str) -> str:
        """
        Get the Amplifier project slug for a path.
        
        Args:
            project_path: Absolute path to project directory
        
        Returns:
            Project slug (e.g., "amplifier-module-connectors-32b3236f")
        """
        return get_project_slug(Path(project_path))

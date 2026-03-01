"""Tests for ProjectManager."""
import json
import tempfile
from pathlib import Path

import pytest

from slack_connector.project_manager import ProjectManager


@pytest.fixture
def temp_storage():
    """Create a temporary storage file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        storage_path = f.name
    yield storage_path
    Path(storage_path).unlink(missing_ok=True)


@pytest.fixture
def temp_projects():
    """Create a temporary projects registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        projects_file = Path(tmpdir) / "projects.json"
        projects_data = {
            "projects": {
                "test-project": {
                    "path": str(tmpdir),
                    "description": "Test project"
                }
            }
        }
        with open(projects_file, 'w') as f:
            json.dump(projects_data, f)
        
        # Temporarily set the project registry location
        yield tmpdir, projects_file


def test_resolve_project_by_path(temp_storage):
    """Test resolving a project by explicit path."""
    manager = ProjectManager(storage_path=temp_storage)
    
    # Use current directory as test path
    current_dir = Path.cwd()
    path, display_name = manager.resolve_project_path(str(current_dir))
    
    assert path == str(current_dir.resolve())
    assert display_name == current_dir.name


def test_resolve_nonexistent_path(temp_storage):
    """Test that nonexistent paths raise ValueError."""
    manager = ProjectManager(storage_path=temp_storage)
    
    with pytest.raises(ValueError, match="Path does not exist"):
        manager.resolve_project_path("/nonexistent/path")


def test_resolve_tilde_expansion(temp_storage):
    """Test that ~ is expanded in paths."""
    manager = ProjectManager(storage_path=temp_storage)
    
    # Resolve ~ to home directory
    path, display_name = manager.resolve_project_path("~")
    
    assert path == str(Path.home().resolve())
    assert display_name == Path.home().name


def test_associate_thread(temp_storage):
    """Test associating a thread with a project."""
    manager = ProjectManager(storage_path=temp_storage)
    
    thread_id = "C123-1234567890.123"
    project_path = "/path/to/project"
    
    manager.associate_thread(thread_id, project_path)
    
    assert manager.get_thread_project(thread_id) == project_path


def test_thread_association_persistence(temp_storage):
    """Test that thread associations persist across manager instances."""
    thread_id = "C123-1234567890.123"
    project_path = "/path/to/project"
    
    # Create first manager and associate thread
    manager1 = ProjectManager(storage_path=temp_storage)
    manager1.associate_thread(thread_id, project_path)
    
    # Create second manager with same storage
    manager2 = ProjectManager(storage_path=temp_storage)
    
    # Should load the association
    assert manager2.get_thread_project(thread_id) == project_path


def test_clear_thread_association(temp_storage):
    """Test clearing a thread association."""
    manager = ProjectManager(storage_path=temp_storage)
    
    thread_id = "C123-1234567890.123"
    project_path = "/path/to/project"
    
    manager.associate_thread(thread_id, project_path)
    assert manager.get_thread_project(thread_id) == project_path
    
    result = manager.clear_thread_association(thread_id)
    assert result is True
    assert manager.get_thread_project(thread_id) is None
    
    # Clearing again should return False
    result = manager.clear_thread_association(thread_id)
    assert result is False


def test_get_thread_display_name(temp_storage):
    """Test getting display name for a thread's project."""
    manager = ProjectManager(storage_path=temp_storage)
    
    thread_id = "C123-1234567890.123"
    project_path = "/path/to/my-project"
    
    manager.associate_thread(thread_id, project_path)
    
    display_name = manager.get_thread_display_name(thread_id)
    assert display_name == "my-project"  # Directory name


def test_get_project_slug(temp_storage):
    """Test getting Amplifier project slug from path."""
    manager = ProjectManager(storage_path=temp_storage)
    
    project_path = "/Users/ken/workspace/my-project"
    slug = manager.get_project_slug(project_path)
    
    # Should match Amplifier CLI format: -Users-ken-workspace-my-project
    assert slug == "-Users-ken-workspace-my-project"
    assert slug.startswith("-")

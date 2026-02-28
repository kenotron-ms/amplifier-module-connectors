"""
Amplifier Tool: todo_list

Allows the agent to manage a todo list within the conversation.
Tasks are stored in-memory and persist for the duration of the session.

The agent can:
- Add new tasks
- List all tasks
- Mark tasks as complete
- Delete tasks
"""
import logging
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Represents a single todo item."""
    id: int
    description: str
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class TodoListTool:
    """
    Amplifier Tool: Manage a todo list within the conversation.
    
    The agent can use this to track tasks, action items, and work to be done.
    Tasks persist for the duration of the conversation session.
    """
    
    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1
    
    @property
    def name(self) -> str:
        return "todo_list"
    
    @property
    def description(self) -> str:
        return (
            "Manage a todo list within this conversation. "
            "Use this to track tasks, action items, and work to be done. "
            "Available actions: add, list, complete, delete. "
            "Tasks persist for the duration of this conversation session."
        )
    
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "complete", "delete"],
                    "description": "Action to perform: add a task, list all tasks, mark complete, or delete",
                },
                "task": {
                    "type": "string",
                    "description": "Task description (required for 'add' action)",
                },
                "task_id": {
                    "type": "integer",
                    "description": "Task ID (required for 'complete' and 'delete' actions)",
                },
            },
            "required": ["action"],
        }
    
    async def execute(
        self,
        action: str,
        task: Optional[str] = None,
        task_id: Optional[int] = None,
        **kwargs: Any
    ) -> dict:
        """Execute a todo list action."""
        
        if action == "add":
            return self._add_task(task)
        elif action == "list":
            return self._list_tasks()
        elif action == "complete":
            return self._complete_task(task_id)
        elif action == "delete":
            return self._delete_task(task_id)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def _add_task(self, description: Optional[str]) -> dict:
        """Add a new task."""
        if not description or not description.strip():
            return {"success": False, "error": "Task description cannot be empty"}
        
        task = Task(
            id=self._next_id,
            description=description.strip()
        )
        self._tasks[task.id] = task
        self._next_id += 1
        
        return {
            "success": True,
            "output": f"✅ Added task #{task.id}: {task.description}",
            "task_id": task.id
        }
    
    def _list_tasks(self) -> dict:
        """List all tasks."""
        if not self._tasks:
            return {
                "success": True,
                "output": "📋 Todo list is empty",
                "tasks": []
            }
        
        # Format tasks
        lines = ["📋 **Todo List**\n"]
        pending_tasks = []
        completed_tasks = []
        
        for task in sorted(self._tasks.values(), key=lambda t: t.id):
            if task.completed:
                completed_tasks.append(task)
            else:
                pending_tasks.append(task)
        
        # Show pending tasks first
        if pending_tasks:
            lines.append("**Pending:**")
            for task in pending_tasks:
                lines.append(f"  ☐ #{task.id}: {task.description}")
        
        # Then completed tasks
        if completed_tasks:
            if pending_tasks:
                lines.append("")
            lines.append("**Completed:**")
            for task in completed_tasks:
                lines.append(f"  ✓ #{task.id}: ~{task.description}~")
        
        output = "\n".join(lines)
        
        return {
            "success": True,
            "output": output,
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "completed": t.completed
                }
                for t in self._tasks.values()
            ],
            "total": len(self._tasks),
            "pending": len(pending_tasks),
            "completed": len(completed_tasks)
        }
    
    def _complete_task(self, task_id: Optional[int]) -> dict:
        """Mark a task as complete."""
        if task_id is None:
            return {"success": False, "error": "task_id is required"}
        
        if task_id not in self._tasks:
            return {"success": False, "error": f"Task #{task_id} not found"}
        
        task = self._tasks[task_id]
        
        if task.completed:
            return {
                "success": True,
                "output": f"ℹ️ Task #{task_id} was already completed",
                "task_id": task_id
            }
        
        task.completed = True
        task.completed_at = datetime.now()
        
        return {
            "success": True,
            "output": f"✅ Completed task #{task_id}: ~{task.description}~",
            "task_id": task_id
        }
    
    def _delete_task(self, task_id: Optional[int]) -> dict:
        """Delete a task."""
        if task_id is None:
            return {"success": False, "error": "task_id is required"}
        
        if task_id not in self._tasks:
            return {"success": False, "error": f"Task #{task_id} not found"}
        
        task = self._tasks.pop(task_id)
        
        return {
            "success": True,
            "output": f"🗑️ Deleted task #{task_id}: {task.description}",
            "task_id": task_id
        }


async def mount(coordinator: Any, config: Optional[dict] = None) -> None:
    """
    Amplifier module entry point.
    
    Registers the todo list tool with the coordinator.
    Each session gets its own todo list instance.
    """
    tool = TodoListTool()
    await coordinator.mount("tools", tool, name=tool.name)

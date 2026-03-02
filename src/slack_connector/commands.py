"""
Command handlers for /amplifier slash commands.

Implements subcommands for project management:
- new: Create project from template
- fork: Clone GitHub repository
- open: Switch to existing project
- list: List projects in workspace
- pwd: Show current directory
- config: Manage configuration
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AmplifierCommands:
    """Handles /amplifier subcommands."""

    def __init__(self, config_manager: Any, project_manager: Any, session_manager: Any):
        """
        Initialize command handler.

        Args:
            config_manager: ConfigManager instance
            project_manager: ProjectManager instance
            session_manager: SessionManager instance
        """
        self.config = config_manager
        self.project_manager = project_manager
        self.session_manager = session_manager

    async def handle_command(
        self, text: str, thread_id: str, channel: str, user: str, client: Any
    ) -> dict[str, Any]:
        """
        Route command to appropriate handler.

        Args:
            text: Command text (after /amplifier)
            thread_id: Thread identifier
            channel: Slack channel ID
            user: Slack user ID
            client: Slack client

        Returns:
            Dict with 'success' bool and 'message' str
        """
        parts = text.split(maxsplit=1)
        if not parts:
            return await self.show_help()

        subcommand = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers = {
            "new": self.cmd_new,
            "fork": self.cmd_fork,
            "open": self.cmd_open,
            "list": self.cmd_list,
            "pwd": self.cmd_pwd,
            "config": self.cmd_config,
        }

        handler = handlers.get(subcommand)
        if handler:
            return await handler(args, thread_id, channel, user, client)

        # If not a subcommand, treat as path (backward compatibility)
        return await self.cmd_open(text, thread_id, channel, user, client)

    async def show_help(self) -> dict[str, Any]:
        """Show help message."""
        return {
            "success": True,
            "message": (
                ":wave: *Amplifier Bot*\n\n"
                "*Project Management:*\n"
                "• `/amplifier new <name>` - Create project from template\n"
                "• `/amplifier fork <github-url> [name]` - Clone GitHub repo\n"
                "• `/amplifier open <name>` - Switch to project in workspace\n"
                "• `/amplifier list` - List projects in workspace\n"
                "• `/amplifier pwd` - Show current working directory\n\n"
                "*Configuration:*\n"
                "• `/amplifier config` - Show current settings\n"
                "• `/amplifier config set <key> <value>` - Update setting\n"
                "• `/amplifier config get <key>` - Get specific setting\n"
                "• `/amplifier config reset` - Reset to defaults\n\n"
                "*Other Commands:*\n"
                "• `/amplifier-status` - Show active sessions\n"
                "• `/amplifier-list` - List Amplifier projects"
            ),
        }

    async def cmd_new(
        self, args: str, thread_id: str, channel: str, user: str, client: Any
    ) -> dict[str, Any]:
        """
        Create a new project from template.

        Usage: /amplifier new <project-name>
        """
        if not args:
            return {"success": False, "message": ":x: Usage: `/amplifier new <project-name>`"}

        project_name = args.strip()
        workspace = self.config.get_workspace_path()
        project_path = workspace / project_name
        template_repo = self.config.get_template_repo()

        # Check if project already exists
        if project_path.exists():
            return {"success": False, "message": f":x: Project already exists: `{project_path}`"}

        # Ensure workspace exists
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            # Clone template
            template_url = f"https://github.com/{template_repo}.git"
            logger.info(f"Cloning template from {template_url} to {project_path}")

            subprocess.run(
                ["git", "clone", template_url, str(project_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            # Remove .git directory (fresh start)
            git_dir = project_path / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir)

            # Re-initialize git if configured
            if self.config.get("auto_init_git", True):
                subprocess.run(
                    ["git", "init"], cwd=str(project_path), capture_output=True, check=True
                )
                subprocess.run(
                    ["git", "add", "."], cwd=str(project_path), capture_output=True, check=True
                )
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit from amplifier-template"],
                    cwd=str(project_path),
                    capture_output=True,
                    check=True,
                )

            # Associate thread with project — the next message in this thread will
            # load the project's bundle automatically via get_or_create_session.
            self.project_manager.associate_thread(thread_id, str(project_path))

            return {
                "success": True,
                "message": (
                    f":white_check_mark: Created project *{project_name}* from template\n"
                    f"`{project_path}`\n\n"
                    f"Template: `{template_repo}`\n"
                    f"Git initialized: {'Yes' if self.config.get('auto_init_git') else 'No'}\n\n"
                    "You can now ask me anything about this project!"
                ),
            }

        except subprocess.CalledProcessError as e:
            # Clean up on failure
            if project_path.exists():
                shutil.rmtree(project_path)

            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"Failed to create project: {error_msg}")

            return {"success": False, "message": f":x: Failed to create project: {error_msg}"}
        except Exception as e:
            # Clean up on failure
            if project_path.exists():
                shutil.rmtree(project_path)

            logger.exception(f"Error creating project: {e}")
            return {"success": False, "message": f":x: Error: {e}"}

    async def cmd_fork(
        self, args: str, thread_id: str, channel: str, user: str, client: Any
    ) -> dict[str, Any]:
        """
        Clone a GitHub repository.

        Usage: /amplifier fork <github-url> [name]
        """
        if not args:
            return {
                "success": False,
                "message": (
                    ":x: Usage: `/amplifier fork <github-url> [name]`\n\n"
                    "Examples:\n"
                    "• `/amplifier fork https://github.com/user/repo`\n"
                    "• `/amplifier fork https://github.com/user/repo my-project`"
                ),
            }

        parts = args.split(maxsplit=1)
        github_url = parts[0]
        custom_name = parts[1] if len(parts) > 1 else None

        # Extract repo name from URL if no custom name provided
        if not custom_name:
            # Handle various GitHub URL formats
            repo_part = github_url.rstrip("/").split("/")[-1]
            custom_name = repo_part.replace(".git", "")

        workspace = self.config.get_workspace_path()
        project_path = workspace / custom_name

        # Check if project already exists
        if project_path.exists():
            return {"success": False, "message": f":x: Project already exists: `{project_path}`"}

        # Ensure workspace exists
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            # Clone repository
            logger.info(f"Cloning {github_url} to {project_path}")

            subprocess.run(
                ["git", "clone", github_url, str(project_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            # Associate thread with project — the next message in this thread will
            # load the project's bundle automatically via get_or_create_session.
            self.project_manager.associate_thread(thread_id, str(project_path))

            return {
                "success": True,
                "message": (
                    f":white_check_mark: Cloned repository to *{custom_name}*\n"
                    f"`{project_path}`\n\n"
                    f"Source: `{github_url}`\n\n"
                    "You can now ask me anything about this project!"
                ),
            }

        except subprocess.CalledProcessError as e:
            # Clean up on failure
            if project_path.exists():
                shutil.rmtree(project_path)

            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"Failed to clone repository: {error_msg}")

            return {"success": False, "message": f":x: Failed to clone repository: {error_msg}"}
        except Exception as e:
            # Clean up on failure
            if project_path.exists():
                shutil.rmtree(project_path)

            logger.exception(f"Error cloning repository: {e}")
            return {"success": False, "message": f":x: Error: {e}"}

    async def cmd_open(
        self, args: str, thread_id: str, channel: str, user: str, client: Any
    ) -> dict[str, Any]:
        """
        Switch to an existing project.

        Usage: /amplifier open <name-or-path>
        """
        if not args:
            return {"success": False, "message": ":x: Usage: `/amplifier open <name-or-path>`"}

        path_str = args.strip()

        # Try as workspace-relative name first
        workspace = self.config.get_workspace_path()
        project_path = workspace / path_str

        # If not found in workspace, try as absolute/relative path
        if not project_path.exists():
            project_path = Path(path_str).expanduser().resolve()

        if not project_path.exists():
            return {"success": False, "message": f":x: Project not found: `{path_str}`"}

        if not project_path.is_dir():
            return {"success": False, "message": f":x: Not a directory: `{project_path}`"}

        # Validate that we can load this project's bundle before associating
        # This catches configuration errors early with better error messages
        try:
            # Test bundle resolution without creating a full session
            bundle_name = self.session_manager._get_bundle_name(str(project_path))
            logger.debug(f"Project '{project_path.name}' will use bundle: {bundle_name}")
            
            # Optional: Validate provider configuration
            try:
                from amplifier_app_cli.lib.settings import AppSettings, SettingsPaths
                from pathlib import Path as PathLib
                
                paths = SettingsPaths(
                    global_settings=PathLib.home() / ".amplifier" / "settings.yaml",
                    project_settings=project_path / ".amplifier" / "settings.yaml",
                    local_settings=project_path / ".amplifier" / "settings.local.yaml",
                )
                app_settings = AppSettings(paths)
                providers = app_settings.get_providers()
                
                if not providers:
                    return {
                        "success": False,
                        "message": (
                            f":x: *No providers configured*\n\n"
                            f"Project: `{project_path}`\n\n"
                            f"Please ensure `~/.amplifier/settings.yaml` contains provider configuration:\n"
                            f"```\n"
                            f"providers:\n"
                            f"  anthropic:\n"
                            f"    api_key: ${{ANTHROPIC_API_KEY}}\n"
                            f"    default_model: claude-3-5-sonnet-20241022\n"
                            f"```"
                        ),
                    }
            except AttributeError:
                # get_providers() not available - skip validation
                logger.debug("Provider validation skipped (method not available)")
            except Exception as e:
                logger.warning(f"Could not validate providers: {e}")
                # Continue anyway - let session creation handle it
                
        except Exception as e:
            logger.error(f"Failed to validate project bundle: {e}")
            return {
                "success": False,
                "message": (
                    f":x: *Failed to validate project*\n\n"
                    f"Project: `{project_path}`\n"
                    f"Error: ```{str(e)[:500]}```\n\n"
                    f"_Please check the project's `.amplifier/` configuration._"
                ),
            }

        # Associate thread with project — the next message in this thread will
        # load the project's bundle automatically via get_or_create_session.
        self.project_manager.associate_thread(thread_id, str(project_path))

        return {
            "success": True,
            "message": (
                f":white_check_mark: Switched to *{project_path.name}*\n"
                f"`{project_path}`\n\n"
                "You can now ask me anything about this project!"
            ),
        }

    async def cmd_list(
        self, args: str, thread_id: str, channel: str, user: str, client: Any
    ) -> dict[str, Any]:
        """
        List projects in workspace.

        Usage: /amplifier list
        """
        workspace = self.config.get_workspace_path()

        if not workspace.exists():
            return {
                "success": True,
                "message": (
                    f":information_source: Workspace directory does not exist yet: `{workspace}`\n\n"
                    "Create your first project with:\n"
                    "`/amplifier new my-project`"
                ),
            }

        try:
            # List directories in workspace
            projects = [p for p in workspace.iterdir() if p.is_dir() and not p.name.startswith(".")]

            if not projects:
                return {
                    "success": True,
                    "message": (
                        f":information_source: No projects in workspace: `{workspace}`\n\n"
                        "Create your first project with:\n"
                        "`/amplifier new my-project`"
                    ),
                }

            # Build project list with git indicators
            lines = [f":file_folder: *Projects in `{workspace}`*\n"]
            for project in sorted(projects):
                git_marker = " :link:" if (project / ".git").exists() else ""
                lines.append(f"• {project.name}{git_marker}")

            lines.append(f"\n_Found {len(projects)} project(s)_")

            return {"success": True, "message": "\n".join(lines)}

        except Exception as e:
            logger.exception(f"Error listing projects: {e}")
            return {"success": False, "message": f":x: Error listing projects: {e}"}

    async def cmd_pwd(
        self, args: str, thread_id: str, channel: str, user: str, client: Any
    ) -> dict[str, Any]:
        """
        Show current working directory for this thread.

        Usage: /amplifier pwd
        """
        project_path = self.project_manager.get_thread_project(thread_id)

        if not project_path:
            workspace = self.config.get_workspace_path()
            return {
                "success": True,
                "message": (
                    ":information_source: No project associated with this thread.\n\n"
                    f"Default workspace: `{workspace}`\n\n"
                    "Start a project with:\n"
                    "• `/amplifier new <name>`\n"
                    "• `/amplifier fork <github-url>`\n"
                    "• `/amplifier open <name>`"
                ),
            }

        display_name = self.project_manager.get_thread_display_name(thread_id)

        return {
            "success": True,
            "message": (f":file_folder: Current project: *{display_name}*\n`{project_path}`"),
        }

    async def cmd_config(
        self, args: str, thread_id: str, channel: str, user: str, client: Any
    ) -> dict[str, Any]:
        """
        Manage configuration.

        Usage:
          /amplifier config
          /amplifier config get <key>
          /amplifier config set <key> <value>
          /amplifier config reset
        """
        if not args:
            # Show all config
            config = self.config.get_all()
            lines = [":gear: *Amplifier Configuration*\n"]
            for key, value in sorted(config.items()):
                lines.append(f"• `{key}`: `{value}`")

            lines.append("\n*Commands:*")
            lines.append("• `/amplifier config get <key>`")
            lines.append("• `/amplifier config set <key> <value>`")
            lines.append("• `/amplifier config reset`")

            return {"success": True, "message": "\n".join(lines)}

        parts = args.split(maxsplit=2)
        action = parts[0].lower()

        if action == "get":
            if len(parts) < 2:
                return {"success": False, "message": ":x: Usage: `/amplifier config get <key>`"}

            key = parts[1]
            value = self.config.get(key)

            if value is None:
                return {"success": False, "message": f":x: Unknown configuration key: `{key}`"}

            return {"success": True, "message": f":gear: `{key}` = `{value}`"}

        elif action == "set":
            if len(parts) < 3:
                return {
                    "success": False,
                    "message": ":x: Usage: `/amplifier config set <key> <value>`",
                }

            key = parts[1]
            value = parts[2]

            # Parse boolean values
            if value.lower() in ("true", "yes", "1"):
                value = True
            elif value.lower() in ("false", "no", "0"):
                value = False

            self.config.set(key, value)

            return {"success": True, "message": f":white_check_mark: Set `{key}` = `{value}`"}

        elif action == "reset":
            self.config.reset()
            return {
                "success": True,
                "message": ":white_check_mark: Configuration reset to defaults",
            }

        else:
            return {
                "success": False,
                "message": (
                    f":x: Unknown config action: `{action}`\n\nValid actions: `get`, `set`, `reset`"
                ),
            }

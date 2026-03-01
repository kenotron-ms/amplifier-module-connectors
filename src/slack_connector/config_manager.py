"""
Configuration manager for Slack Amplifier connector.

Manages persistent configuration for workspace paths, templates, and other settings.

Storage structure:
  ~/.amplifier/workspaces/
    ├── config.json           # Workspace configuration
    └── thread-associations.json  # Thread -> project mappings
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages configuration for the Slack Amplifier connector.
    
    Configuration is stored in ~/.amplifier/workspaces/config.json and includes:
    - workspace: Base directory for projects (default: ~/workspace)
    - template_repo: GitHub repo for new projects (default: kenotron-ms/amplifier-template)
    - auto_init_git: Whether to initialize git for new projects (default: True)
    - auto_switch: Whether to auto-switch to project after creation (default: True)
    
    This is separate from Amplifier's core settings to avoid conflicts.
    """
    
    DEFAULT_CONFIG = {
        "workspace": "~/workspace",
        "template_repo": "kenotron-ms/amplifier-template",
        "auto_init_git": True,
        "auto_switch": True,
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to config file. Defaults to ~/.amplifier/workspaces/config.json
        """
        if config_path is None:
            # Use dedicated workspaces directory to avoid conflicts with Amplifier core
            workspaces_dir = Path.home() / ".amplifier" / "workspaces"
            config_path = str(workspaces_dir / "config.json")
        
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._config: dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """Load configuration from disk."""
        if not self.config_path.exists():
            # Create default config
            self._config = self.DEFAULT_CONFIG.copy()
            self._save()
            logger.info("Created default configuration")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to ensure all keys exist
                self._config = {**self.DEFAULT_CONFIG, **loaded}
            logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
    
    def _save(self) -> None:
        """Save configuration to disk."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.debug(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Could not save configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self._config[key] = value
        self._save()
        logger.info(f"Set {key} = {value}")
    
    def get_all(self) -> dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of all configuration
        """
        return self._config.copy()
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = self.DEFAULT_CONFIG.copy()
        self._save()
        logger.info("Reset configuration to defaults")
    
    def get_workspace_path(self) -> Path:
        """
        Get the workspace directory as a Path object.
        
        Returns:
            Expanded and resolved workspace path
        """
        workspace = self._config.get("workspace", "~/workspace")
        return Path(workspace).expanduser().resolve()
    
    def get_template_repo(self) -> str:
        """
        Get the template repository.
        
        Returns:
            Template repo (e.g., "kenotron-ms/amplifier-template")
        """
        return self._config.get("template_repo", "kenotron-ms/amplifier-template")

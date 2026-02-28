"""
Connector Core - Platform-agnostic abstractions for chat connectors.

This module provides shared models, protocols, and utilities that work
across different chat platforms (Slack, Teams, etc.).
"""

from .models import UnifiedMessage
from .protocols import PlatformAdapter, ApprovalPrompt
from .session_manager import SessionManager

__all__ = ["UnifiedMessage", "PlatformAdapter", "ApprovalPrompt", "SessionManager"]

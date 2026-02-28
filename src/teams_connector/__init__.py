"""
Microsoft Teams connector for Amplifier.

This module provides Teams integration using the Bot Framework SDK.
"""

from .bot import TeamsAmplifierBot
from .adapter import TeamsAdapter

__all__ = ["TeamsAmplifierBot", "TeamsAdapter"]

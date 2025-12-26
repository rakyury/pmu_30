"""
Models Package

Contains data models and managers for PMU-30 Configurator.
"""

from .channel import ChannelType, CHANNEL_PREFIX_MAP
from .channel_display_service import ChannelDisplayService, ChannelIdGenerator
from .config_manager import ConfigManager
from .undo_manager import (
    Command,
    AddChannelCommand,
    RemoveChannelCommand,
    UpdateChannelCommand,
    CompositeCommand,
    UndoManager,
    get_undo_manager,
)

__all__ = [
    'ChannelType',
    'ChannelDisplayService',
    'ChannelIdGenerator',
    'CHANNEL_PREFIX_MAP',
    'ConfigManager',
    'Command',
    'AddChannelCommand',
    'RemoveChannelCommand',
    'UpdateChannelCommand',
    'CompositeCommand',
    'UndoManager',
    'get_undo_manager',
]

"""
Undo/Redo Manager for Configuration Changes

Implements Command pattern for reversible configuration operations.
"""

from typing import Any, Dict, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import copy
import logging

logger = logging.getLogger(__name__)


class Command(ABC):
    """Abstract base class for reversible commands."""

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command. Returns True if successful."""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Undo the command. Returns True if successful."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of the command."""
        pass

    def can_merge(self, other: 'Command') -> bool:
        """Check if this command can be merged with another."""
        return False

    def merge(self, other: 'Command') -> 'Command':
        """Merge this command with another. Returns merged command."""
        return self


@dataclass
class AddChannelCommand(Command):
    """Command for adding a channel."""
    channel_type: str
    channel_data: Dict[str, Any]
    add_callback: Callable[[str, Dict], bool]
    remove_callback: Callable[[str], bool]
    _executed: bool = False

    def execute(self) -> bool:
        result = self.add_callback(self.channel_type, self.channel_data)
        self._executed = result
        return result

    def undo(self) -> bool:
        if not self._executed:
            return False
        channel_id = self.channel_data.get('name', self.channel_data.get('id', ''))
        return self.remove_callback(channel_id)

    def get_description(self) -> str:
        name = self.channel_data.get('name', self.channel_data.get('id', 'channel'))
        return f"Add {self.channel_type}: {name}"


@dataclass
class RemoveChannelCommand(Command):
    """Command for removing a channel."""
    channel_type: str
    channel_data: Dict[str, Any]
    add_callback: Callable[[str, Dict], bool]
    remove_callback: Callable[[str], bool]
    _executed: bool = False

    def execute(self) -> bool:
        channel_id = self.channel_data.get('name', self.channel_data.get('id', ''))
        result = self.remove_callback(channel_id)
        self._executed = result
        return result

    def undo(self) -> bool:
        if not self._executed:
            return False
        return self.add_callback(self.channel_type, self.channel_data)

    def get_description(self) -> str:
        name = self.channel_data.get('name', self.channel_data.get('id', 'channel'))
        return f"Remove {self.channel_type}: {name}"


@dataclass
class UpdateChannelCommand(Command):
    """Command for updating a channel."""
    channel_id: str
    old_data: Dict[str, Any]
    new_data: Dict[str, Any]
    update_callback: Callable[[str, Dict], bool]
    _executed: bool = False

    def execute(self) -> bool:
        result = self.update_callback(self.channel_id, self.new_data)
        self._executed = result
        return result

    def undo(self) -> bool:
        if not self._executed:
            return False
        return self.update_callback(self.channel_id, self.old_data)

    def get_description(self) -> str:
        return f"Update: {self.channel_id}"

    def can_merge(self, other: 'Command') -> bool:
        """Can merge consecutive updates to the same channel."""
        if isinstance(other, UpdateChannelCommand):
            return self.channel_id == other.channel_id
        return False

    def merge(self, other: 'UpdateChannelCommand') -> 'UpdateChannelCommand':
        """Merge with another update command (keep original old_data, use latest new_data)."""
        return UpdateChannelCommand(
            channel_id=self.channel_id,
            old_data=self.old_data,  # Keep original state
            new_data=other.new_data,  # Use latest change
            update_callback=self.update_callback,
        )


@dataclass
class PropertyChangeCommand(Command):
    """Command for changing a single property."""
    target: Any
    property_name: str
    old_value: Any
    new_value: Any
    _executed: bool = False

    def execute(self) -> bool:
        try:
            setattr(self.target, self.property_name, self.new_value)
            self._executed = True
            return True
        except Exception as e:
            logger.error(f"Failed to set {self.property_name}: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed:
            return False
        try:
            setattr(self.target, self.property_name, self.old_value)
            return True
        except Exception as e:
            logger.error(f"Failed to restore {self.property_name}: {e}")
            return False

    def get_description(self) -> str:
        return f"Change {self.property_name}"


@dataclass
class CompositeCommand(Command):
    """Command that groups multiple commands together."""
    commands: List[Command] = field(default_factory=list)
    description: str = "Multiple changes"
    _executed_count: int = 0

    def add(self, command: Command):
        """Add a command to the composite."""
        self.commands.append(command)

    def execute(self) -> bool:
        self._executed_count = 0
        for cmd in self.commands:
            if cmd.execute():
                self._executed_count += 1
            else:
                # Rollback on failure
                for i in range(self._executed_count - 1, -1, -1):
                    self.commands[i].undo()
                self._executed_count = 0
                return False
        return True

    def undo(self) -> bool:
        # Undo in reverse order
        success = True
        for cmd in reversed(self.commands[:self._executed_count]):
            if not cmd.undo():
                success = False
        return success

    def get_description(self) -> str:
        return self.description


class UndoManager(QObject):
    """
    Manages undo/redo stack for configuration changes.

    Emits signals when undo/redo availability changes.
    """

    # Signals
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)
    stack_changed = pyqtSignal()  # Any change to the stack

    def __init__(self, max_stack_size: int = 100, parent=None):
        super().__init__(parent)
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_stack_size = max_stack_size
        self._merge_timeout_ms = 500  # Merge commands within this time
        self._last_command_time = 0
        self._is_executing = False  # Prevent re-entrant execution

    def execute(self, command: Command, merge: bool = True) -> bool:
        """
        Execute a command and add it to the undo stack.

        Args:
            command: The command to execute
            merge: Whether to attempt merging with previous command

        Returns:
            True if command executed successfully
        """
        if self._is_executing:
            logger.warning("Ignoring re-entrant command execution")
            return False

        self._is_executing = True
        try:
            if not command.execute():
                return False

            # Clear redo stack on new command
            if self._redo_stack:
                self._redo_stack.clear()
                self.can_redo_changed.emit(False)

            # Try to merge with previous command
            import time
            current_time = time.time() * 1000

            if (merge and self._undo_stack and
                (current_time - self._last_command_time) < self._merge_timeout_ms):
                last_cmd = self._undo_stack[-1]
                if last_cmd.can_merge(command):
                    self._undo_stack[-1] = last_cmd.merge(command)
                    self._last_command_time = current_time
                    self.stack_changed.emit()
                    return True

            # Add to undo stack
            self._undo_stack.append(command)
            self._last_command_time = current_time

            # Enforce stack size limit
            while len(self._undo_stack) > self._max_stack_size:
                self._undo_stack.pop(0)

            # Emit signals
            if len(self._undo_stack) == 1:
                self.can_undo_changed.emit(True)
            self.stack_changed.emit()

            logger.debug(f"Executed: {command.get_description()}")
            return True

        finally:
            self._is_executing = False

    def undo(self) -> bool:
        """Undo the last command. Returns True if successful."""
        if not self._undo_stack:
            return False

        if self._is_executing:
            return False

        self._is_executing = True
        try:
            command = self._undo_stack.pop()

            if command.undo():
                self._redo_stack.append(command)

                # Emit signals
                if not self._undo_stack:
                    self.can_undo_changed.emit(False)
                if len(self._redo_stack) == 1:
                    self.can_redo_changed.emit(True)
                self.stack_changed.emit()

                logger.debug(f"Undone: {command.get_description()}")
                return True
            else:
                # Failed to undo - put it back
                self._undo_stack.append(command)
                return False

        finally:
            self._is_executing = False

    def redo(self) -> bool:
        """Redo the last undone command. Returns True if successful."""
        if not self._redo_stack:
            return False

        if self._is_executing:
            return False

        self._is_executing = True
        try:
            command = self._redo_stack.pop()

            if command.execute():
                self._undo_stack.append(command)

                # Emit signals
                if not self._redo_stack:
                    self.can_redo_changed.emit(False)
                if len(self._undo_stack) == 1:
                    self.can_undo_changed.emit(True)
                self.stack_changed.emit()

                logger.debug(f"Redone: {command.get_description()}")
                return True
            else:
                # Failed to redo - put it back
                self._redo_stack.append(command)
                return False

        finally:
            self._is_executing = False

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> str:
        """Get description of the command that would be undone."""
        if self._undo_stack:
            return self._undo_stack[-1].get_description()
        return ""

    def get_redo_description(self) -> str:
        """Get description of the command that would be redone."""
        if self._redo_stack:
            return self._redo_stack[-1].get_description()
        return ""

    def clear(self):
        """Clear both undo and redo stacks."""
        had_undo = bool(self._undo_stack)
        had_redo = bool(self._redo_stack)

        self._undo_stack.clear()
        self._redo_stack.clear()

        if had_undo:
            self.can_undo_changed.emit(False)
        if had_redo:
            self.can_redo_changed.emit(False)
        self.stack_changed.emit()

    def get_undo_count(self) -> int:
        """Get number of commands in undo stack."""
        return len(self._undo_stack)

    def get_redo_count(self) -> int:
        """Get number of commands in redo stack."""
        return len(self._redo_stack)

    def begin_group(self, description: str = "Multiple changes") -> CompositeCommand:
        """
        Begin a command group for grouping multiple operations.

        Usage:
            group = undo_manager.begin_group("Paste channels")
            group.add(AddChannelCommand(...))
            group.add(AddChannelCommand(...))
            undo_manager.end_group(group)
        """
        return CompositeCommand(description=description)

    def end_group(self, group: CompositeCommand) -> bool:
        """Execute and commit a command group."""
        if group.commands:
            return self.execute(group, merge=False)
        return True


# Singleton instance
_undo_manager: Optional[UndoManager] = None


def get_undo_manager() -> UndoManager:
    """Get the global undo manager instance."""
    global _undo_manager
    if _undo_manager is None:
        _undo_manager = UndoManager()
    return _undo_manager


def reset_undo_manager():
    """Reset the global undo manager (for testing)."""
    global _undo_manager
    if _undo_manager:
        _undo_manager.clear()
    _undo_manager = None

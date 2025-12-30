"""
Unit Tests: Undo/Redo Manager

Tests for undo_manager.py - reversible configuration operations.
Covers:
- Command execution and undo
- Redo functionality
- Stack limits
- Command merging
- Composite commands
- Signals
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models.undo_manager import (
    Command,
    AddChannelCommand,
    RemoveChannelCommand,
    UpdateChannelCommand,
    PropertyChangeCommand,
    CompositeCommand,
    UndoManager,
    get_undo_manager,
    reset_undo_manager,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def undo_manager():
    """Create a fresh UndoManager for each test."""
    return UndoManager(max_stack_size=10)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton between tests."""
    reset_undo_manager()
    yield
    reset_undo_manager()


class SimpleCommand(Command):
    """Simple test command for testing."""

    def __init__(self, value=0, can_fail=False):
        self.value = value
        self.can_fail = can_fail
        self.executed = False
        self.undone = False

    def execute(self) -> bool:
        if self.can_fail:
            return False
        self.executed = True
        return True

    def undo(self) -> bool:
        if self.can_fail:
            return False
        self.undone = True
        return True

    def get_description(self) -> str:
        return f"Simple command {self.value}"


class MergeableCommand(Command):
    """Command that supports merging."""

    def __init__(self, value=0):
        self.value = value
        self.merge_count = 0

    def execute(self) -> bool:
        return True

    def undo(self) -> bool:
        return True

    def get_description(self) -> str:
        return f"Mergeable {self.value}"

    def can_merge(self, other: 'Command') -> bool:
        return isinstance(other, MergeableCommand)

    def merge(self, other: 'MergeableCommand') -> 'MergeableCommand':
        merged = MergeableCommand(other.value)
        merged.merge_count = self.merge_count + 1
        return merged


# ============================================================================
# UndoManager Basic Tests
# ============================================================================

class TestUndoManagerBasic:
    """Test basic UndoManager functionality."""

    def test_create_manager(self, undo_manager):
        """Test creating an undo manager."""
        assert undo_manager is not None
        assert undo_manager.get_undo_count() == 0
        assert undo_manager.get_redo_count() == 0

    def test_can_undo_empty(self, undo_manager):
        """Test can_undo on empty stack."""
        assert undo_manager.can_undo() is False

    def test_can_redo_empty(self, undo_manager):
        """Test can_redo on empty stack."""
        assert undo_manager.can_redo() is False

    def test_execute_command(self, undo_manager):
        """Test executing a command."""
        cmd = SimpleCommand(1)
        result = undo_manager.execute(cmd)

        assert result is True
        assert cmd.executed is True
        assert undo_manager.get_undo_count() == 1
        assert undo_manager.can_undo() is True

    def test_execute_failing_command(self, undo_manager):
        """Test executing a failing command."""
        cmd = SimpleCommand(1, can_fail=True)
        result = undo_manager.execute(cmd)

        assert result is False
        assert undo_manager.get_undo_count() == 0

    def test_undo_command(self, undo_manager):
        """Test undoing a command."""
        cmd = SimpleCommand(1)
        undo_manager.execute(cmd)

        result = undo_manager.undo()

        assert result is True
        assert cmd.undone is True
        assert undo_manager.get_undo_count() == 0
        assert undo_manager.get_redo_count() == 1

    def test_undo_empty_stack(self, undo_manager):
        """Test undo on empty stack."""
        result = undo_manager.undo()
        assert result is False

    def test_redo_command(self, undo_manager):
        """Test redoing a command."""
        cmd = SimpleCommand(1)
        undo_manager.execute(cmd)
        undo_manager.undo()

        result = undo_manager.redo()

        assert result is True
        assert undo_manager.get_undo_count() == 1
        assert undo_manager.get_redo_count() == 0

    def test_redo_empty_stack(self, undo_manager):
        """Test redo on empty stack."""
        result = undo_manager.redo()
        assert result is False

    def test_new_command_clears_redo(self, undo_manager):
        """Test that new command clears redo stack."""
        cmd1 = SimpleCommand(1)
        cmd2 = SimpleCommand(2)

        undo_manager.execute(cmd1)
        undo_manager.undo()
        assert undo_manager.get_redo_count() == 1

        undo_manager.execute(cmd2)
        assert undo_manager.get_redo_count() == 0


# ============================================================================
# Stack Limit Tests
# ============================================================================

class TestStackLimits:
    """Test stack size limits."""

    def test_stack_limit_enforced(self, undo_manager):
        """Test that stack size limit is enforced."""
        # max_stack_size is 10
        for i in range(15):
            undo_manager.execute(SimpleCommand(i))

        assert undo_manager.get_undo_count() == 10

    def test_oldest_commands_removed(self, undo_manager):
        """Test that oldest commands are removed when limit exceeded."""
        for i in range(15):
            undo_manager.execute(SimpleCommand(i))

        # The first 5 commands (0-4) should have been removed
        # The last command should be value 14
        desc = undo_manager.get_undo_description()
        assert "14" in desc


# ============================================================================
# Command Merging Tests
# ============================================================================

class TestCommandMerging:
    """Test command merging functionality."""

    def test_merge_enabled(self, undo_manager):
        """Test that mergeable commands are merged."""
        with patch('time.time', side_effect=[0.0, 0.1, 0.2]):  # Within merge timeout
            cmd1 = MergeableCommand(1)
            cmd2 = MergeableCommand(2)

            undo_manager.execute(cmd1)
            undo_manager.execute(cmd2)

            # Should have merged into one command
            assert undo_manager.get_undo_count() == 1

    def test_merge_disabled(self, undo_manager):
        """Test merging can be disabled."""
        cmd1 = MergeableCommand(1)
        cmd2 = MergeableCommand(2)

        undo_manager.execute(cmd1, merge=False)
        undo_manager.execute(cmd2, merge=False)

        # Should not merge
        assert undo_manager.get_undo_count() == 2

    def test_non_mergeable_commands(self, undo_manager):
        """Test non-mergeable commands don't merge."""
        cmd1 = SimpleCommand(1)
        cmd2 = SimpleCommand(2)

        undo_manager.execute(cmd1)
        undo_manager.execute(cmd2)

        assert undo_manager.get_undo_count() == 2


# ============================================================================
# Description Tests
# ============================================================================

class TestDescriptions:
    """Test command description functionality."""

    def test_get_undo_description(self, undo_manager):
        """Test getting undo description."""
        cmd = SimpleCommand(42)
        undo_manager.execute(cmd)

        desc = undo_manager.get_undo_description()
        assert "42" in desc

    def test_get_undo_description_empty(self, undo_manager):
        """Test undo description on empty stack."""
        desc = undo_manager.get_undo_description()
        assert desc == ""

    def test_get_redo_description(self, undo_manager):
        """Test getting redo description."""
        cmd = SimpleCommand(99)
        undo_manager.execute(cmd)
        undo_manager.undo()

        desc = undo_manager.get_redo_description()
        assert "99" in desc

    def test_get_redo_description_empty(self, undo_manager):
        """Test redo description on empty stack."""
        desc = undo_manager.get_redo_description()
        assert desc == ""


# ============================================================================
# Clear Tests
# ============================================================================

class TestClear:
    """Test clearing stacks."""

    def test_clear_stacks(self, undo_manager):
        """Test clearing both stacks."""
        undo_manager.execute(SimpleCommand(1))
        undo_manager.execute(SimpleCommand(2))
        undo_manager.undo()

        undo_manager.clear()

        assert undo_manager.get_undo_count() == 0
        assert undo_manager.get_redo_count() == 0

    def test_clear_already_empty(self, undo_manager):
        """Test clearing already empty stacks."""
        undo_manager.clear()  # Should not raise
        assert undo_manager.get_undo_count() == 0


# ============================================================================
# Composite Command Tests
# ============================================================================

class TestCompositeCommand:
    """Test CompositeCommand functionality."""

    def test_create_composite(self):
        """Test creating a composite command."""
        composite = CompositeCommand(description="Test group")
        assert composite.get_description() == "Test group"
        assert len(composite.commands) == 0

    def test_add_commands_to_composite(self):
        """Test adding commands to composite."""
        composite = CompositeCommand()
        composite.add(SimpleCommand(1))
        composite.add(SimpleCommand(2))

        assert len(composite.commands) == 2

    def test_execute_composite(self):
        """Test executing composite command."""
        cmd1 = SimpleCommand(1)
        cmd2 = SimpleCommand(2)

        composite = CompositeCommand()
        composite.add(cmd1)
        composite.add(cmd2)

        result = composite.execute()

        assert result is True
        assert cmd1.executed is True
        assert cmd2.executed is True

    def test_undo_composite(self):
        """Test undoing composite command."""
        cmd1 = SimpleCommand(1)
        cmd2 = SimpleCommand(2)

        composite = CompositeCommand()
        composite.add(cmd1)
        composite.add(cmd2)
        composite.execute()

        result = composite.undo()

        assert result is True
        assert cmd1.undone is True
        assert cmd2.undone is True

    def test_composite_rollback_on_failure(self):
        """Test composite rollback when command fails."""
        cmd1 = SimpleCommand(1)
        cmd2 = SimpleCommand(2, can_fail=True)  # Will fail
        cmd3 = SimpleCommand(3)

        composite = CompositeCommand()
        composite.add(cmd1)
        composite.add(cmd2)
        composite.add(cmd3)

        result = composite.execute()

        assert result is False
        # cmd1 should have been rolled back
        assert cmd1.undone is True
        # cmd3 should never have executed
        assert cmd3.executed is False

    def test_begin_end_group(self, undo_manager):
        """Test begin_group and end_group."""
        group = undo_manager.begin_group("Test batch")
        group.add(SimpleCommand(1))
        group.add(SimpleCommand(2))

        result = undo_manager.end_group(group)

        assert result is True
        assert undo_manager.get_undo_count() == 1  # One composite

    def test_end_group_empty(self, undo_manager):
        """Test ending empty group."""
        group = undo_manager.begin_group("Empty")
        result = undo_manager.end_group(group)

        assert result is True
        assert undo_manager.get_undo_count() == 0


# ============================================================================
# AddChannelCommand Tests
# ============================================================================

class TestAddChannelCommand:
    """Test AddChannelCommand."""

    def test_execute_add(self):
        """Test executing add channel command."""
        add_mock = MagicMock(return_value=True)
        remove_mock = MagicMock()

        cmd = AddChannelCommand(
            channel_type="digital_input",
            channel_data={"name": "din_1", "pin": 0},
            add_callback=add_mock,
            remove_callback=remove_mock
        )

        result = cmd.execute()

        assert result is True
        add_mock.assert_called_once_with("digital_input", {"name": "din_1", "pin": 0})

    def test_undo_add(self):
        """Test undoing add channel command."""
        add_mock = MagicMock(return_value=True)
        remove_mock = MagicMock(return_value=True)

        cmd = AddChannelCommand(
            channel_type="digital_input",
            channel_data={"name": "din_1"},
            add_callback=add_mock,
            remove_callback=remove_mock
        )

        cmd.execute()
        result = cmd.undo()

        assert result is True
        remove_mock.assert_called_once_with("din_1")

    def test_get_description(self):
        """Test add command description."""
        cmd = AddChannelCommand(
            channel_type="power_output",
            channel_data={"name": "pout_1"},
            add_callback=MagicMock(),
            remove_callback=MagicMock()
        )

        desc = cmd.get_description()
        assert "power_output" in desc
        assert "pout_1" in desc


# ============================================================================
# RemoveChannelCommand Tests
# ============================================================================

class TestRemoveChannelCommand:
    """Test RemoveChannelCommand."""

    def test_execute_remove(self):
        """Test executing remove channel command."""
        add_mock = MagicMock()
        remove_mock = MagicMock(return_value=True)

        cmd = RemoveChannelCommand(
            channel_type="analog_input",
            channel_data={"name": "ain_1"},
            add_callback=add_mock,
            remove_callback=remove_mock
        )

        result = cmd.execute()

        assert result is True
        remove_mock.assert_called_once_with("ain_1")

    def test_undo_remove(self):
        """Test undoing remove channel command (re-adds channel)."""
        add_mock = MagicMock(return_value=True)
        remove_mock = MagicMock(return_value=True)

        cmd = RemoveChannelCommand(
            channel_type="analog_input",
            channel_data={"name": "ain_1", "pin": 5},
            add_callback=add_mock,
            remove_callback=remove_mock
        )

        cmd.execute()
        result = cmd.undo()

        assert result is True
        add_mock.assert_called_once_with("analog_input", {"name": "ain_1", "pin": 5})


# ============================================================================
# UpdateChannelCommand Tests
# ============================================================================

class TestUpdateChannelCommand:
    """Test UpdateChannelCommand."""

    def test_execute_update(self):
        """Test executing update channel command."""
        update_mock = MagicMock(return_value=True)

        cmd = UpdateChannelCommand(
            channel_id="ch_1",
            old_data={"value": 10},
            new_data={"value": 20},
            update_callback=update_mock
        )

        result = cmd.execute()

        assert result is True
        update_mock.assert_called_with("ch_1", {"value": 20})

    def test_undo_update(self):
        """Test undoing update channel command."""
        update_mock = MagicMock(return_value=True)

        cmd = UpdateChannelCommand(
            channel_id="ch_1",
            old_data={"value": 10},
            new_data={"value": 20},
            update_callback=update_mock
        )

        cmd.execute()
        result = cmd.undo()

        assert result is True
        # Should restore old data
        update_mock.assert_called_with("ch_1", {"value": 10})

    def test_can_merge_same_channel(self):
        """Test UpdateChannelCommand can merge with same channel."""
        update_mock = MagicMock(return_value=True)

        cmd1 = UpdateChannelCommand(
            channel_id="ch_1",
            old_data={"value": 10},
            new_data={"value": 20},
            update_callback=update_mock
        )

        cmd2 = UpdateChannelCommand(
            channel_id="ch_1",
            old_data={"value": 20},
            new_data={"value": 30},
            update_callback=update_mock
        )

        assert cmd1.can_merge(cmd2) is True

    def test_cannot_merge_different_channels(self):
        """Test UpdateChannelCommand cannot merge different channels."""
        update_mock = MagicMock(return_value=True)

        cmd1 = UpdateChannelCommand(
            channel_id="ch_1",
            old_data={"value": 10},
            new_data={"value": 20},
            update_callback=update_mock
        )

        cmd2 = UpdateChannelCommand(
            channel_id="ch_2",  # Different channel
            old_data={"value": 20},
            new_data={"value": 30},
            update_callback=update_mock
        )

        assert cmd1.can_merge(cmd2) is False

    def test_merge_keeps_original_old_data(self):
        """Test merge keeps original old_data, uses latest new_data."""
        update_mock = MagicMock(return_value=True)

        cmd1 = UpdateChannelCommand(
            channel_id="ch_1",
            old_data={"value": 10},
            new_data={"value": 20},
            update_callback=update_mock
        )

        cmd2 = UpdateChannelCommand(
            channel_id="ch_1",
            old_data={"value": 20},
            new_data={"value": 30},
            update_callback=update_mock
        )

        merged = cmd1.merge(cmd2)

        assert merged.old_data == {"value": 10}  # Original
        assert merged.new_data == {"value": 30}  # Latest


# ============================================================================
# PropertyChangeCommand Tests
# ============================================================================

class TestPropertyChangeCommand:
    """Test PropertyChangeCommand."""

    def test_execute_property_change(self):
        """Test executing property change."""

        class Target:
            value = 10

        target = Target()
        cmd = PropertyChangeCommand(
            target=target,
            property_name="value",
            old_value=10,
            new_value=20
        )

        result = cmd.execute()

        assert result is True
        assert target.value == 20

    def test_undo_property_change(self):
        """Test undoing property change."""

        class Target:
            value = 10

        target = Target()
        cmd = PropertyChangeCommand(
            target=target,
            property_name="value",
            old_value=10,
            new_value=20
        )

        cmd.execute()
        cmd.undo()

        assert target.value == 10

    def test_property_change_description(self):
        """Test property change description."""

        class Target:
            pass

        cmd = PropertyChangeCommand(
            target=Target(),
            property_name="my_prop",
            old_value=1,
            new_value=2
        )

        desc = cmd.get_description()
        assert "my_prop" in desc


# ============================================================================
# Singleton Tests
# ============================================================================

class TestSingleton:
    """Test singleton pattern."""

    def test_get_undo_manager_singleton(self):
        """Test get_undo_manager returns same instance."""
        manager1 = get_undo_manager()
        manager2 = get_undo_manager()

        assert manager1 is manager2

    def test_reset_undo_manager(self):
        """Test reset clears and creates new instance."""
        manager1 = get_undo_manager()
        manager1.execute(SimpleCommand(1))

        reset_undo_manager()

        manager2 = get_undo_manager()
        assert manager2.get_undo_count() == 0


# ============================================================================
# Re-entrant Prevention Tests
# ============================================================================

class TestReentrantPrevention:
    """Test prevention of re-entrant execution."""

    def test_no_reentrant_during_execute(self, undo_manager):
        """Test that execute is blocked during execution."""

        class ReentrantCommand(Command):
            def __init__(self, manager):
                self.manager = manager
                self.nested_result = None

            def execute(self):
                # Try to execute another command during this one
                self.nested_result = self.manager.execute(SimpleCommand(2))
                return True

            def undo(self):
                return True

            def get_description(self):
                return "Reentrant test"

        undo_manager._is_executing = False
        cmd = ReentrantCommand(undo_manager)
        undo_manager.execute(cmd)

        # Nested execute should have been blocked
        assert cmd.nested_result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

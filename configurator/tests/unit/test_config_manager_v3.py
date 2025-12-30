"""
Unit tests for ConfigManager v3.0 API (unified channel architecture)

Tests the new channel-based API introduced in v3.0:
- get_next_channel_id()
- add_channel() / get_channel_by_name() / update_channel() / remove_channel()
- get_all_channels() / get_channels_by_type()
- CAN message methods
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from models.config_manager import ConfigManager
from models.channel import ChannelType


class TestConfigManagerChannelId:
    """Tests for channel ID generation."""

    def test_get_next_channel_id_empty(self):
        """Test get_next_channel_id with no channels returns 200."""
        manager = ConfigManager()
        manager.config["channels"] = []

        next_id = manager.get_next_channel_id()

        assert next_id == 200  # User channel range starts at 200

    def test_get_next_channel_id_sequential(self):
        """Test get_next_channel_id returns next sequential ID."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "ch1"},
            {"channel_id": 201, "channel_name": "ch2"},
        ]

        next_id = manager.get_next_channel_id()

        assert next_id == 202

    def test_get_next_channel_id_fills_gaps(self):
        """Test get_next_channel_id fills gaps in ID sequence."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "ch1"},
            {"channel_id": 202, "channel_name": "ch3"},  # Gap at 201
            {"channel_id": 203, "channel_name": "ch4"},
        ]

        next_id = manager.get_next_channel_id()

        assert next_id == 201  # Should fill the gap

    def test_get_next_channel_id_ignores_system_channels(self):
        """Test that system channel IDs (1000+) are ignored."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "ch1"},
            {"channel_id": 1000, "channel_name": "system"},  # System channel
        ]

        next_id = manager.get_next_channel_id()

        assert next_id == 201  # Should not be affected by 1000


class TestConfigManagerChannelCRUD:
    """Tests for channel CRUD operations."""

    def test_add_channel(self):
        """Test adding a new channel."""
        manager = ConfigManager()
        manager.config["channels"] = []

        channel_config = {
            "channel_id": 200,
            "channel_name": "test_logic",
            "channel_type": "logic",
            "operation": "and"
        }

        result = manager.add_channel(channel_config)

        assert result is True
        assert len(manager.config["channels"]) == 1
        assert manager.config["channels"][0]["channel_name"] == "test_logic"
        assert manager.is_modified() is True

    def test_add_channel_duplicate_name(self):
        """Test adding channel with duplicate name fails."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "existing", "channel_type": "logic"}
        ]

        channel_config = {
            "channel_id": 201,
            "channel_name": "existing",  # Duplicate name
            "channel_type": "logic"
        }

        result = manager.add_channel(channel_config)

        assert result is False
        assert len(manager.config["channels"]) == 1

    def test_get_channel_by_name(self):
        """Test retrieving channel by name."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "logic1", "channel_type": "logic"},
            {"channel_id": 201, "channel_name": "logic2", "channel_type": "logic"},
        ]

        channel = manager.get_channel_by_name("logic2")

        assert channel is not None
        assert channel["channel_id"] == 201

    def test_get_channel_by_name_not_found(self):
        """Test retrieving non-existent channel returns None."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "logic1", "channel_type": "logic"},
        ]

        channel = manager.get_channel_by_name("nonexistent")

        assert channel is None

    def test_update_channel(self):
        """Test updating an existing channel."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "logic1", "channel_type": "logic", "operation": "and"}
        ]
        manager.modified = False

        new_config = {
            "channel_id": 200,
            "channel_name": "logic1",
            "channel_type": "logic",
            "operation": "or"  # Changed
        }

        result = manager.update_channel("logic1", new_config)

        assert result is True
        assert manager.config["channels"][0]["operation"] == "or"
        assert manager.is_modified() is True

    def test_update_channel_not_found(self):
        """Test updating non-existent channel fails."""
        manager = ConfigManager()
        manager.config["channels"] = []

        result = manager.update_channel("nonexistent", {"channel_name": "test"})

        assert result is False

    def test_remove_channel(self):
        """Test removing a channel."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "logic1", "channel_type": "logic"},
            {"channel_id": 201, "channel_name": "logic2", "channel_type": "logic"},
        ]

        result = manager.remove_channel("logic1")

        assert result is True
        assert len(manager.config["channels"]) == 1
        assert manager.config["channels"][0]["channel_name"] == "logic2"

    def test_remove_channel_not_found(self):
        """Test removing non-existent channel fails."""
        manager = ConfigManager()
        manager.config["channels"] = []

        result = manager.remove_channel("nonexistent")

        assert result is False


class TestConfigManagerChannelQueries:
    """Tests for channel query methods."""

    def test_get_all_channels(self):
        """Test get_all_channels returns all channels."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "ch1"},
            {"channel_id": 201, "channel_name": "ch2"},
        ]

        channels = manager.get_all_channels()

        assert len(channels) == 2

    def test_get_channels_by_type(self):
        """Test filtering channels by type."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "logic1", "channel_type": "logic"},
            {"channel_id": 201, "channel_name": "timer1", "channel_type": "timer"},
            {"channel_id": 202, "channel_name": "logic2", "channel_type": "logic"},
        ]

        logic_channels = manager.get_channels_by_type(ChannelType.LOGIC)

        assert len(logic_channels) == 2
        assert all(ch["channel_type"] == "logic" for ch in logic_channels)

    def test_channel_exists(self):
        """Test channel_exists method."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "logic1", "channel_type": "logic"},
        ]

        assert manager.channel_exists("logic1") is True
        assert manager.channel_exists("nonexistent") is False

    def test_get_channel_count(self):
        """Test get_channel_count method."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "logic1", "channel_type": "logic"},
            {"channel_id": 201, "channel_name": "timer1", "channel_type": "timer"},
            {"channel_id": 202, "channel_name": "logic2", "channel_type": "logic"},
        ]

        total = manager.get_channel_count()
        logic_count = manager.get_channel_count(ChannelType.LOGIC)
        timer_count = manager.get_channel_count(ChannelType.TIMER)

        assert total == 3
        assert logic_count == 2
        assert timer_count == 1


class TestConfigManagerCANMessages:
    """Tests for CAN message methods."""

    def test_get_all_can_messages(self):
        """Test retrieving all CAN messages."""
        manager = ConfigManager()
        manager.config["can_messages"] = [
            {"name": "msg1", "message_id": 0x100},
            {"name": "msg2", "message_id": 0x200},
        ]

        messages = manager.get_all_can_messages()

        assert len(messages) == 2

    def test_get_can_message_by_name(self):
        """Test retrieving CAN message by name."""
        manager = ConfigManager()
        manager.config["can_messages"] = [
            {"name": "msg1", "message_id": 0x100},
            {"name": "msg2", "message_id": 0x200},
        ]

        message = manager.get_can_message_by_name("msg2")

        assert message is not None
        assert message["message_id"] == 0x200

    def test_can_message_exists(self):
        """Test can_message_exists method."""
        manager = ConfigManager()
        manager.config["can_messages"] = [
            {"name": "msg1", "message_id": 0x100},
        ]

        assert manager.can_message_exists("msg1") is True
        assert manager.can_message_exists("nonexistent") is False


class TestConfigManagerValidation:
    """Tests for validation methods."""

    def test_validate_channel_references_valid(self):
        """Test validation with valid channel references."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 200, "channel_name": "input1", "channel_type": "digital_input"},
            {"channel_id": 201, "channel_name": "logic1", "channel_type": "logic", "inputs": ["input1"]},
        ]

        errors = manager.validate_channel_references()

        assert len(errors) == 0

    def test_validate_channel_references_invalid(self):
        """Test validation detects undefined channel references."""
        manager = ConfigManager()
        manager.config["channels"] = [
            {"channel_id": 201, "channel_name": "logic1", "channel_type": "logic", "inputs": ["nonexistent"]},
        ]

        errors = manager.validate_channel_references()

        assert len(errors) > 0
        assert "nonexistent" in errors[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

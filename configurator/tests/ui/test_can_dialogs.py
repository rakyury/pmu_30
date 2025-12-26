"""Tests for CAN Input and CAN Output dialogs."""

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for the test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_message_ids():
    """Sample CAN message IDs for testing."""
    return ["msg_engine", "msg_transmission", "msg_chassis"]


@pytest.fixture
def sample_available_channels():
    """Sample available channels for testing."""
    return {
        "Inputs": [
            (10, "FuelLevel", "L", 1),
            (21, "StartButton", "", 0),
        ],
        "Functions": [
            (50, "CalculatedValue", "V", 2),
        ],
    }


class TestCANInputDialog:
    """Tests for CANInputDialog."""

    def test_create_empty_dialog(self, qapp, sample_message_ids):
        """Test creating empty CAN input dialog."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        dialog = CANInputDialog(
            message_ids=sample_message_ids,
            existing_channel_ids=[]
        )

        assert dialog is not None
        assert dialog.windowTitle() == "CAN Input"
        assert dialog.name_edit.text() == ""
        dialog.close()

    def test_create_edit_dialog(self, qapp, sample_message_ids):
        """Test creating CAN input dialog for editing."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        config = {
            "name": "EngineRPM",
            "message_ref": "msg_engine",
            "frame_offset": 0,
            "data_type": "unsigned",
            "data_format": "16bit",
            "byte_order": "little_endian",
            "byte_offset": 2,
            "multiplier": 1.0,
            "divider": 1.0,
            "offset": 0.0,
            "decimal_places": 0,
            "default_value": 0.0,
            "timeout_behavior": "use_default",
        }

        dialog = CANInputDialog(
            input_config=config,
            message_ids=sample_message_ids,
            existing_channel_ids=[]
        )

        assert dialog.windowTitle() == "Edit CAN Input: EngineRPM"
        assert dialog.name_edit.text() == "EngineRPM"
        dialog.close()

    def test_get_config_returns_valid_structure(self, qapp, sample_message_ids):
        """Test that get_config returns valid config structure."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        dialog = CANInputDialog(
            message_ids=sample_message_ids,
            existing_channel_ids=[]
        )

        # Fill minimal required fields
        dialog.name_edit.setText("TestSignal")
        if sample_message_ids:
            dialog.message_combo.setCurrentIndex(1)  # Select first message

        config = dialog.get_config()

        assert "name" in config
        assert "channel_type" in config
        assert config["channel_type"] == "can_rx"
        assert "data_type" in config
        assert "data_format" in config
        assert "byte_order" in config
        assert "multiplier" in config
        assert "divider" in config
        dialog.close()

    def test_data_types_available(self, qapp, sample_message_ids):
        """Test that data types are properly configured."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        dialog = CANInputDialog(
            message_ids=sample_message_ids,
            existing_channel_ids=[]
        )

        # Check data types
        assert len(CANInputDialog.DATA_TYPES) >= 3
        assert any("unsigned" in dt[1].lower() for dt in CANInputDialog.DATA_TYPES)
        assert any("signed" in dt[1].lower() for dt in CANInputDialog.DATA_TYPES)
        dialog.close()

    def test_data_formats_available(self, qapp, sample_message_ids):
        """Test that data formats are properly configured."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        assert len(CANInputDialog.DATA_FORMATS) >= 3
        assert any("8bit" in df[1] for df in CANInputDialog.DATA_FORMATS)
        assert any("16bit" in df[1] for df in CANInputDialog.DATA_FORMATS)
        assert any("32bit" in df[1] for df in CANInputDialog.DATA_FORMATS)

    def test_byte_orders_available(self, qapp):
        """Test that byte orders are properly configured."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        assert len(CANInputDialog.BYTE_ORDERS) == 2
        byte_order_values = [bo[1] for bo in CANInputDialog.BYTE_ORDERS]
        assert "little_endian" in byte_order_values
        assert "big_endian" in byte_order_values

    def test_templates_available(self, qapp):
        """Test that templates are defined."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        assert len(CANInputDialog.TEMPLATES) > 0
        # Check template structure
        for name, template in CANInputDialog.TEMPLATES.items():
            assert "data_type" in template
            assert "data_format" in template

    def test_load_config_preserves_values(self, qapp, sample_message_ids):
        """Test that loading config preserves all values."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        original_config = {
            "name": "CoolantTemp",
            "message_ref": "msg_engine",
            "frame_offset": 2,
            "data_type": "signed",
            "data_format": "16bit",
            "byte_order": "big_endian",
            "byte_offset": 4,
            "multiplier": 0.1,
            "divider": 1.0,
            "offset": -40.0,
            "decimal_places": 1,
            "default_value": 20.0,
            "timeout_behavior": "hold_last",
        }

        dialog = CANInputDialog(
            input_config=original_config,
            message_ids=sample_message_ids,
            existing_channel_ids=[]
        )

        result_config = dialog.get_config()

        assert result_config["name"] == original_config["name"]
        assert result_config["frame_offset"] == original_config["frame_offset"]
        assert result_config["byte_offset"] == original_config["byte_offset"]
        assert result_config["data_type"] == original_config["data_type"]
        assert result_config["byte_order"] == original_config["byte_order"]
        dialog.close()

    def test_no_messages_available(self, qapp):
        """Test dialog behavior when no messages are available."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        dialog = CANInputDialog(
            message_ids=[],
            existing_channel_ids=[]
        )

        # Should still create dialog, but message combo should be disabled
        assert dialog is not None
        assert not dialog.message_combo.isEnabled()
        dialog.close()


class TestCANOutputDialog:
    """Tests for CANOutputDialog."""

    def test_create_empty_dialog(self, qapp, sample_available_channels):
        """Test creating empty CAN output dialog."""
        from ui.dialogs.can_output_dialog import CANOutputDialog

        dialog = CANOutputDialog(
            available_channels=sample_available_channels,
            existing_ids=[]
        )

        assert dialog is not None
        assert dialog.windowTitle() == "CAN Output"
        assert dialog.name_edit.text() == ""
        dialog.close()

    def test_create_edit_dialog(self, qapp, sample_available_channels):
        """Test creating CAN output dialog for editing."""
        from ui.dialogs.can_output_dialog import CANOutputDialog

        config = {
            "name": "tx_engine_data",
            "can_bus": 0,
            "can_id": 0x100,
            "extended_id": False,
            "transmit_mode": "cycle",
            "cycle_time_ms": 100,
            "channels": [],
        }

        dialog = CANOutputDialog(
            output_config=config,
            available_channels=sample_available_channels,
            existing_ids=[]
        )

        assert dialog.windowTitle() == "Edit CAN Output: tx_engine_data"
        assert dialog.name_edit.text() == "tx_engine_data"
        dialog.close()

    def test_get_config_returns_valid_structure(self, qapp, sample_available_channels):
        """Test that get_config returns valid config structure."""
        from ui.dialogs.can_output_dialog import CANOutputDialog

        dialog = CANOutputDialog(
            available_channels=sample_available_channels,
            existing_ids=[]
        )

        # Fill required fields
        dialog.name_edit.setText("TestOutput")

        config = dialog.get_config()

        assert "name" in config
        assert "can_bus" in config
        assert "message_id" in config  # API uses message_id, not can_id
        assert "transmit_mode" in config
        dialog.close()

    def test_transmit_modes_available(self, qapp):
        """Test that transmit modes are properly configured."""
        from ui.dialogs.can_output_dialog import CANOutputDialog

        assert len(CANOutputDialog.TRANSMIT_MODES) >= 2
        mode_values = [m[1] for m in CANOutputDialog.TRANSMIT_MODES]
        assert "cycle" in mode_values
        assert "triggered" in mode_values

    def test_channel_slots_widget(self, qapp):
        """Test ChannelSlotWidget creation."""
        from ui.dialogs.can_output_dialog import ChannelSlotWidget

        slot = ChannelSlotWidget(slot_index=0)

        assert slot is not None
        assert slot.slot_index == 0
        assert slot.channel_edit is not None
        assert slot.type_combo is not None

    def test_channel_slot_set_config(self, qapp):
        """Test ChannelSlotWidget config loading."""
        from ui.dialogs.can_output_dialog import ChannelSlotWidget

        slot = ChannelSlotWidget(slot_index=1)

        config = {
            "data_type": "16bit_le",
            "channel": "EngineRPM",
            "multiplier": 0.1,
        }

        slot.set_config(config)

        assert slot.channel_edit.text() == "EngineRPM"

    def test_channel_slot_get_config(self, qapp):
        """Test ChannelSlotWidget config export."""
        from ui.dialogs.can_output_dialog import ChannelSlotWidget

        slot = ChannelSlotWidget(slot_index=2)
        slot.channel_edit.setText("TestChannel")

        config = slot.get_config()

        assert "channel" in config
        assert config["channel"] == "TestChannel"
        assert "data_type" in config
        assert "multiplier" in config


class TestCANDialogValidation:
    """Tests for CAN dialog validation."""

    def test_can_input_empty_name_check(self, qapp, sample_message_ids):
        """Test that empty name can be detected for CAN input."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        dialog = CANInputDialog(
            message_ids=sample_message_ids,
            existing_channel_ids=[]
        )

        # Empty name should be empty string
        dialog.name_edit.setText("")
        config = dialog.get_config()
        assert config["name"] == ""
        dialog.close()

    def test_can_input_with_existing_channel_ids(self, qapp, sample_message_ids):
        """Test CAN input with existing channel IDs provided."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        existing_ids = ["ExistingChannel1", "ExistingChannel2"]
        dialog = CANInputDialog(
            message_ids=sample_message_ids,
            existing_channel_ids=existing_ids
        )

        # Dialog should be created with existing channel IDs tracked
        assert dialog is not None
        dialog.close()

    def test_can_output_empty_name_check(self, qapp, sample_available_channels):
        """Test that empty name can be detected for CAN output."""
        from ui.dialogs.can_output_dialog import CANOutputDialog

        dialog = CANOutputDialog(
            available_channels=sample_available_channels,
            existing_ids=[]
        )

        dialog.name_edit.setText("")
        config = dialog.get_config()
        assert config["name"] == ""
        dialog.close()


class TestCANDialogRoundTrip:
    """Tests for config round-trip (load -> modify -> save)."""

    def test_can_input_round_trip(self, qapp, sample_message_ids):
        """Test CAN input config round-trip."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        original = {
            "name": "EngineRPM",
            "message_ref": "msg_engine",
            "frame_offset": 1,
            "data_type": "unsigned",
            "data_format": "16bit",
            "byte_order": "little_endian",
            "byte_offset": 0,
            "multiplier": 1.0,
            "divider": 1.0,
            "offset": 0.0,
            "decimal_places": 0,
            "default_value": 0.0,
            "timeout_behavior": "use_default",
        }

        dialog = CANInputDialog(
            input_config=original,
            message_ids=sample_message_ids,
            existing_channel_ids=[]
        )

        result = dialog.get_config()

        # Key fields should match
        assert result["name"] == original["name"]
        assert result["data_type"] == original["data_type"]
        assert result["data_format"] == original["data_format"]
        assert result["byte_order"] == original["byte_order"]
        assert result["frame_offset"] == original["frame_offset"]
        assert result["byte_offset"] == original["byte_offset"]
        dialog.close()

    def test_can_output_round_trip(self, qapp, sample_available_channels):
        """Test CAN output config round-trip."""
        from ui.dialogs.can_output_dialog import CANOutputDialog

        original = {
            "name": "tx_dashboard",
            "can_bus": 1,
            "can_id": 0x200,
            "extended_id": True,
            "transmit_mode": "cycle",
            "cycle_time_ms": 50,
            "channels": [
                {"data_type": "16bit_le", "channel": "RPM", "multiplier": 1.0},
            ],
        }

        dialog = CANOutputDialog(
            output_config=original,
            available_channels=sample_available_channels,
            existing_ids=[]
        )

        result = dialog.get_config()

        # Key fields should match
        assert result["name"] == original["name"]
        assert result["transmit_mode"] == original["transmit_mode"]
        dialog.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

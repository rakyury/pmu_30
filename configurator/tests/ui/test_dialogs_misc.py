"""
UI Tests for Miscellaneous Dialogs
Tests: TimerDialog, CANMessageDialog, FilterDialog, PIDControllerDialog, etc.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt

from ui.dialogs.timer_dialog import TimerDialog
from ui.dialogs.can_message_dialog import CANMessageDialog
from models.channel import TimerMode, EdgeType


class TestTimerDialog:
    """Tests for TimerDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new timer dialog"""
        dialog = TimerDialog()
        assert dialog is not None
        assert dialog.windowTitle().startswith("New")
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        config = {
            "channel_id": 10,
            "name": "Cooldown Timer",
            "start_channel": "ignition_off",
            "start_edge": "rising",
            "stop_edge": "falling",
            "mode": "count_down",
            "limit_seconds": 300
        }
        dialog = TimerDialog(config=config)
        assert dialog.windowTitle().startswith("Edit")
        assert dialog.name_edit.text() == "Cooldown Timer"
        dialog.close()

    def test_mode_options(self, qapp):
        """Test timer mode options"""
        dialog = TimerDialog()

        modes = []
        for i in range(dialog.mode_combo.count()):
            modes.append(dialog.mode_combo.itemData(i))

        assert TimerMode.COUNT_UP.value in modes
        assert TimerMode.COUNT_DOWN.value in modes
        dialog.close()

    def test_edge_options(self, qapp):
        """Test edge options available"""
        dialog = TimerDialog()

        edges = []
        for i in range(dialog.start_edge_combo.count()):
            edges.append(dialog.start_edge_combo.itemData(i))

        assert "rising" in edges
        assert "falling" in edges
        dialog.close()

    def test_time_limit_spinboxes(self, qapp):
        """Test time limit spinbox ranges"""
        dialog = TimerDialog()

        assert dialog.hours_spin.minimum() == 0
        assert dialog.hours_spin.maximum() == 999
        assert dialog.minutes_spin.minimum() == 0
        assert dialog.minutes_spin.maximum() == 59
        assert dialog.seconds_spin.minimum() == 0
        assert dialog.seconds_spin.maximum() == 59
        dialog.close()

    def test_total_seconds_calculation(self, qapp):
        """Test total seconds label updates"""
        dialog = TimerDialog()

        dialog.hours_spin.setValue(1)
        dialog.minutes_spin.setValue(30)
        dialog.seconds_spin.setValue(15)

        # Total should be 1*3600 + 30*60 + 15 = 5415 seconds
        assert "5415" in dialog.total_label.text() or "5,415" in dialog.total_label.text()
        dialog.close()

    def test_get_config(self, qapp):
        """Test get_config returns complete configuration"""
        dialog = TimerDialog()
        dialog.name_edit.setText("Test Timer")
        dialog.start_channel_edit.setText("trigger_channel")
        dialog.hours_spin.setValue(0)
        dialog.minutes_spin.setValue(5)
        dialog.seconds_spin.setValue(0)

        config = dialog.get_config()

        assert config["name"] == "Test Timer"
        assert config["start_channel"] == "trigger_channel"
        assert "mode" in config
        assert "limit_seconds" in config or "limit_ms" in config
        dialog.close()

    def test_validation_start_channel_required(self, qapp):
        """Test validation requires start channel"""
        dialog = TimerDialog()
        dialog.name_edit.setText("Test")
        dialog.start_channel_edit.setText("")

        errors = dialog._validate_specific()
        assert len(errors) > 0
        dialog.close()


class TestCANMessageDialog:
    """Tests for CANMessageDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new CAN message dialog"""
        dialog = CANMessageDialog()
        assert dialog is not None
        assert "CAN Message" in dialog.windowTitle()
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        config = {
            "id": "msg_engine",
            "name": "Engine Data",
            "can_bus": 1,
            "base_id": 0x100,
            "dlc": 8,
            "is_extended": False,
            "message_type": "normal"
        }
        dialog = CANMessageDialog(message_config=config)
        assert "Edit" in dialog.windowTitle()
        dialog.close()

    def test_templates_available(self, qapp):
        """Test templates are available for new messages"""
        dialog = CANMessageDialog()

        # Check template combo exists
        assert hasattr(dialog, 'template_combo')
        assert dialog.template_combo.count() > 1  # At least "Select" + templates
        dialog.close()

    def test_message_types_available(self, qapp):
        """Test message types available"""
        dialog = CANMessageDialog()

        expected_types = ["normal", "compound"]
        found_types = []

        # Find the message type combo
        if hasattr(dialog, 'message_type_combo'):
            for i in range(dialog.message_type_combo.count()):
                found_types.append(dialog.message_type_combo.itemData(i))

            for t in expected_types:
                assert t in found_types
        dialog.close()

    def test_can_id_input(self, qapp):
        """Test CAN ID input field exists"""
        dialog = CANMessageDialog()

        # Should have ID spin field (base_id_spin) and name edit
        assert hasattr(dialog, 'base_id_spin')
        assert hasattr(dialog, 'name_edit')
        dialog.close()


class TestBaseChannelDialog:
    """Tests for BaseChannelDialog common functionality"""

    def test_channel_id_auto_generated(self, qapp):
        """Test channel ID is auto-generated for new channels"""
        dialog = TimerDialog()

        # Channel ID should be generated
        channel_id = dialog._channel_id
        assert channel_id is not None
        assert channel_id > 0
        dialog.close()

    def test_channel_id_preserved_when_editing(self, qapp):
        """Test channel ID is preserved when editing"""
        config = {
            "channel_id": 42,
            "name": "Test Timer",
            "start_channel": "test"
        }
        dialog = TimerDialog(config=config)

        assert dialog._channel_id == 42
        dialog.close()

    def test_name_auto_generated(self, qapp):
        """Test name is auto-generated for new channels"""
        dialog = TimerDialog()

        name = dialog.name_edit.text()
        assert name != ""
        assert "Timer" in name
        dialog.close()

    def test_name_preserved_when_editing(self, qapp):
        """Test name is preserved when editing"""
        config = {
            "channel_id": 1,
            "name": "My Custom Timer",
            "start_channel": "test"
        }
        dialog = TimerDialog(config=config)

        assert dialog.name_edit.text() == "My Custom Timer"
        dialog.close()

    def test_validation_name_required(self, qapp):
        """Test validation requires name"""
        dialog = TimerDialog()
        dialog.name_edit.setText("")

        errors = dialog._validate_base()
        assert len(errors) > 0
        assert any("Name" in e for e in errors)
        dialog.close()

    def test_get_base_config(self, qapp):
        """Test get_base_config returns common fields"""
        dialog = TimerDialog()
        dialog.name_edit.setText("Test Channel")

        config = dialog.get_base_config()

        assert "channel_id" in config
        assert "name" in config
        assert config["name"] == "Test Channel"
        assert "channel_type" in config
        dialog.close()


class TestDialogHelpers:
    """Tests for dialog helper widgets and methods"""

    def test_channel_selector_created(self, qapp):
        """Test channel selector widget is created correctly"""
        dialog = TimerDialog()

        # Should have channel selector widgets
        assert hasattr(dialog, 'start_channel_widget')
        assert hasattr(dialog, 'start_channel_edit')
        dialog.close()

    def test_edge_combo_created(self, qapp):
        """Test edge combo is created correctly"""
        dialog = TimerDialog()

        assert hasattr(dialog, 'start_edge_combo')
        assert dialog.start_edge_combo.count() >= 2
        dialog.close()


class TestFilterDialog:
    """Tests for FilterDialog"""

    def test_dialog_import(self, qapp):
        """Test FilterDialog can be imported"""
        try:
            from ui.dialogs.filter_dialog import FilterDialog
            dialog = FilterDialog()
            assert dialog is not None
            dialog.close()
        except ImportError:
            pytest.skip("FilterDialog not available")


class TestSwitchDialog:
    """Tests for SwitchDialog"""

    def test_dialog_import(self, qapp):
        """Test SwitchDialog can be imported"""
        try:
            from ui.dialogs.switch_dialog import SwitchDialog
            dialog = SwitchDialog()
            assert dialog is not None
            dialog.close()
        except ImportError:
            pytest.skip("SwitchDialog not available")


class TestTable2DDialog:
    """Tests for Table2DDialog"""

    def test_dialog_import(self, qapp):
        """Test Table2DDialog can be imported"""
        try:
            from ui.dialogs.table_2d_dialog import Table2DDialog
            dialog = Table2DDialog()
            assert dialog is not None
            dialog.close()
        except ImportError:
            pytest.skip("Table2DDialog not available")


class TestTable3DDialog:
    """Tests for Table3DDialog"""

    def test_dialog_import(self, qapp):
        """Test Table3DDialog can be imported"""
        try:
            from ui.dialogs.table_3d_dialog import Table3DDialog
            dialog = Table3DDialog()
            assert dialog is not None
            dialog.close()
        except ImportError:
            pytest.skip("Table3DDialog not available")


class TestPIDControllerDialog:
    """Tests for PIDControllerDialog"""

    def test_dialog_import(self, qapp):
        """Test PIDControllerDialog can be imported"""
        try:
            from ui.dialogs.pid_controller_dialog import PIDControllerDialog
            dialog = PIDControllerDialog()
            assert dialog is not None
            dialog.close()
        except ImportError:
            pytest.skip("PIDControllerDialog not available")


class TestLuaScriptDialog:
    """Tests for LuaScriptDialog"""

    def test_dialog_import(self, qapp):
        """Test LuaScriptDialog can be imported"""
        try:
            from ui.dialogs.lua_script_dialog import LuaScriptDialog
            dialog = LuaScriptDialog()
            assert dialog is not None
            dialog.close()
        except ImportError:
            pytest.skip("LuaScriptDialog not available")


class TestConnectionDialog:
    """Tests for ConnectionDialog"""

    def test_dialog_import(self, qapp):
        """Test ConnectionDialog can be imported"""
        try:
            from ui.dialogs.connection_dialog import ConnectionDialog
            dialog = ConnectionDialog()
            assert dialog is not None
            dialog.close()
        except ImportError:
            pytest.skip("ConnectionDialog not available")


class TestChannelSelectorDialog:
    """Tests for ChannelSelectorDialog"""

    def test_dialog_import(self, qapp, available_channels):
        """Test ChannelSelectorDialog can be imported"""
        try:
            from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog
            dialog = ChannelSelectorDialog(channels_data=available_channels)
            assert dialog is not None
            dialog.close()
        except ImportError:
            pytest.skip("ChannelSelectorDialog not available")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

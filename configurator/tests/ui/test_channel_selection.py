"""
UI Tests for Channel Selection Logic
Tests the channel_id vs channel_name display/save behavior across dialogs.

The key behavior being tested:
- Display: Show channel_name (user-friendly) in UI input fields
- Store: Save channel_id (numeric int) in config
- Lookup: Convert between channel_id and channel_name

Channel data format (4-element tuple):
  (channel_id, display_name, units, decimal_places)

Example:
  (45, "FuelLevel", "L", 1) -> Displays as "FuelLevel  [#45]  (L, .1)"
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QDialog, QLineEdit
from PyQt6.QtCore import Qt


@pytest.fixture
def available_channels_with_ids():
    """Available channels in 4-element tuple format:
    (channel_id, display_name, units, decimal_places)
    """
    return {
        "analog_inputs": [
            (10, "FuelLevel", "L", 1),
            (11, "OilPressure", "bar", 2),
            (12, "Coolant Temp", "°C", 0),
        ],
        "digital_inputs": [
            (20, "Ignition", "", None),
            (21, "StartButton", "", None),
        ],
        "power_outputs": [
            (30, "FuelPump", "", None),
            (31, "Headlights", "", None),
        ],
        "logic": [
            (40, "EngineRunning", "", None),
            (41, "SafetyCheck", "", None),
        ],
        "numbers": [
            (50, "MaxRPM", "rpm", 0),
            (51, "IdleSpeed", "rpm", 0),
        ],
        "timers": [
            (60, "StartupTimer", "s", 1),
        ],
        "filters": [
            (70, "FilteredOilPressure", "bar", 2),
        ],
        "tables_2d": [
            (80, "FuelMap", "", 2),
        ],
        "tables_3d": [
            (90, "IgnitionMap", "", 1),
        ],
    }


@pytest.fixture
def existing_channels():
    """Sample existing channels for dialog testing."""
    return [
        {"channel_id": 10, "name": "FuelLevel", "channel_type": "analog_input"},
        {"channel_id": 20, "name": "Ignition", "channel_type": "digital_input"},
        {"channel_id": 30, "name": "FuelPump", "channel_type": "power_output"},
        {"channel_id": 40, "name": "EngineRunning", "channel_type": "logic"},
    ]


class TestBaseChannelDialogHelpers:
    """Tests for BaseChannelDialog channel selection helper methods."""

    def test_get_channel_display_name_user_channel(self, qapp, available_channels_with_ids):
        """Test looking up display name for user channel by numeric ID."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # Test looking up user channel by numeric ID
        display_name = dialog._get_channel_display_name(10)
        assert display_name == "FuelLevel"

        display_name = dialog._get_channel_display_name(21)
        assert display_name == "StartButton"

        dialog.close()

    def test_get_channel_display_name_not_found(self, qapp, available_channels_with_ids):
        """Test fallback when channel ID not found."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # Non-existent channel should return "#ID" format
        display_name = dialog._get_channel_display_name(999)
        assert display_name == "#999"

        dialog.close()

    def test_get_channel_display_name_none(self, qapp, available_channels_with_ids):
        """Test handling None channel ID."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        display_name = dialog._get_channel_display_name(None)
        assert display_name == ""

        dialog.close()

    def test_set_channel_edit_value(self, qapp, available_channels_with_ids):
        """Test _set_channel_edit_value stores ID and displays name."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # Set channel by ID
        dialog._set_channel_edit_value(dialog.start_channel_edit, 10)

        # Check display shows channel name
        assert dialog.start_channel_edit.text() == "FuelLevel"

        # Check property stores channel ID
        stored_id = dialog.start_channel_edit.property("channel_id")
        assert stored_id == 10

        dialog.close()

    def test_set_channel_edit_value_clears_on_none(self, qapp, available_channels_with_ids):
        """Test _set_channel_edit_value clears field when None."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # First set a value
        dialog._set_channel_edit_value(dialog.start_channel_edit, 10)
        assert dialog.start_channel_edit.text() == "FuelLevel"

        # Then clear with None
        dialog._set_channel_edit_value(dialog.start_channel_edit, None)
        assert dialog.start_channel_edit.text() == ""

        dialog.close()

    def test_get_channel_id_from_edit(self, qapp, available_channels_with_ids):
        """Test _get_channel_id_from_edit retrieves stored ID."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # Set channel by ID
        dialog._set_channel_edit_value(dialog.start_channel_edit, 10)

        # Retrieve should return numeric ID
        retrieved_id = dialog._get_channel_id_from_edit(dialog.start_channel_edit)
        assert retrieved_id == 10

        dialog.close()

    def test_get_channel_id_from_edit_empty(self, qapp, available_channels_with_ids):
        """Test _get_channel_id_from_edit returns None for empty field."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # Empty field should return None
        retrieved_id = dialog._get_channel_id_from_edit(dialog.start_channel_edit)
        assert retrieved_id is None

        dialog.close()


class TestTimerDialogChannelSelection:
    """Tests for Timer dialog channel ID handling."""

    def test_load_config_displays_channel_name(self, qapp, available_channels_with_ids):
        """Test loading config displays channel_name but stores channel_id."""
        from ui.dialogs.timer_dialog import TimerDialog

        config = {
            "channel_id": 100,
            "name": "TestTimer",
            "start_channel": 10,  # Numeric ID
            "stop_channel": 20,   # Numeric ID
        }

        dialog = TimerDialog(config=config, available_channels=available_channels_with_ids)

        # Display should show names
        assert dialog.start_channel_edit.text() == "FuelLevel"
        assert dialog.stop_channel_edit.text() == "Ignition"

        # Properties should store IDs
        assert dialog.start_channel_edit.property("channel_id") == 10
        assert dialog.stop_channel_edit.property("channel_id") == 20

        dialog.close()

    def test_get_config_returns_channel_id(self, qapp, available_channels_with_ids):
        """Test get_config returns numeric channel_id not display name."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)
        dialog.name_edit.setText("TestTimer")

        # Set channels by ID
        dialog._set_channel_edit_value(dialog.start_channel_edit, 10)
        dialog._set_channel_edit_value(dialog.stop_channel_edit, 20)

        config = dialog.get_config()

        # Config should contain numeric IDs
        assert config["start_channel"] == 10
        assert config["stop_channel"] == 20

        dialog.close()


class TestFilterDialogChannelSelection:
    """Tests for Filter dialog channel ID handling."""

    def test_load_config_displays_channel_name(self, qapp, available_channels_with_ids):
        """Test loading config displays channel_name."""
        from ui.dialogs.filter_dialog import FilterDialog

        config = {
            "channel_id": 100,
            "name": "TestFilter",
            "input_channel": 10,  # Numeric ID
            "filter_type": "lowpass",
        }

        dialog = FilterDialog(config=config, available_channels=available_channels_with_ids)

        # Display should show name (FilterDialog uses input_edit not input_channel_edit)
        assert dialog.input_edit.text() == "FuelLevel"

        # Property should store ID
        assert dialog.input_edit.property("channel_id") == 10

        dialog.close()

    def test_get_config_returns_channel_id(self, qapp, available_channels_with_ids):
        """Test get_config returns numeric channel_id."""
        from ui.dialogs.filter_dialog import FilterDialog

        dialog = FilterDialog(available_channels=available_channels_with_ids)
        dialog.name_edit.setText("TestFilter")

        # Set channel by ID (FilterDialog uses input_edit)
        dialog._set_channel_edit_value(dialog.input_edit, 11)

        config = dialog.get_config()

        # Config should contain numeric ID
        assert config["input_channel"] == 11

        dialog.close()


class TestPIDDialogChannelSelection:
    """Tests for PID Controller dialog channel ID handling."""

    def test_load_config_displays_channel_names(self, qapp, available_channels_with_ids):
        """Test loading config displays channel_names."""
        from ui.dialogs.pid_controller_dialog import PIDControllerDialog

        config = {
            "channel_id": 100,
            "name": "TestPID",
            "setpoint_channel": 50,    # MaxRPM
            "process_channel": 10,     # FuelLevel
            "output_channel": 30,      # FuelPump
            "kp": 1.0, "ki": 0.1, "kd": 0.01,
        }

        dialog = PIDControllerDialog(config=config, available_channels=available_channels_with_ids)

        # Display should show names
        assert dialog.setpoint_edit.text() == "MaxRPM"
        assert dialog.process_edit.text() == "FuelLevel"
        assert dialog.output_edit.text() == "FuelPump"

        dialog.close()

    def test_get_config_returns_channel_ids(self, qapp, available_channels_with_ids):
        """Test get_config returns numeric channel_ids."""
        from ui.dialogs.pid_controller_dialog import PIDControllerDialog

        dialog = PIDControllerDialog(available_channels=available_channels_with_ids)
        dialog.name_edit.setText("TestPID")

        # Set channels by ID
        dialog._set_channel_edit_value(dialog.setpoint_edit, 50)
        dialog._set_channel_edit_value(dialog.process_edit, 10)
        dialog._set_channel_edit_value(dialog.output_edit, 30)

        config = dialog.get_config()

        # Config should contain numeric IDs
        assert config["setpoint_channel"] == 50
        assert config["process_channel"] == 10
        assert config["output_channel"] == 30

        dialog.close()


class TestTable2DDialogChannelSelection:
    """Tests for Table2D dialog channel ID handling."""

    def test_load_config_displays_channel_name(self, qapp, available_channels_with_ids):
        """Test loading config displays channel_name."""
        from ui.dialogs.table_2d_dialog import Table2DDialog

        config = {
            "channel_id": 100,
            "name": "TestTable2D",
            "x_axis_channel": 10,  # FuelLevel
            "x_min": 0, "x_max": 100, "x_step": 10,
            "x_values": [0, 10, 20],
            "output_values": [0, 5, 10],
        }

        dialog = Table2DDialog(config=config, available_channels=available_channels_with_ids)

        # Display should show name
        assert dialog.x_channel_edit.text() == "FuelLevel"

        dialog.close()

    def test_get_config_returns_channel_id(self, qapp, available_channels_with_ids):
        """Test get_config returns numeric channel_id."""
        from ui.dialogs.table_2d_dialog import Table2DDialog

        dialog = Table2DDialog(available_channels=available_channels_with_ids)
        dialog.name_edit.setText("TestTable2D")

        # Set channel by ID
        dialog._set_channel_edit_value(dialog.x_channel_edit, 10)

        # Create table so validation passes
        dialog.x_min_spin.setValue(0)
        dialog.x_max_spin.setValue(100)
        dialog.x_step_spin.setValue(50)
        dialog._create_table()

        config = dialog.get_config()

        # Config should contain numeric ID
        assert config["x_axis_channel"] == 10

        dialog.close()


class TestTable3DDialogChannelSelection:
    """Tests for Table3D dialog channel ID handling."""

    def test_load_config_displays_channel_names(self, qapp, available_channels_with_ids):
        """Test loading config displays channel_names."""
        from ui.dialogs.table_3d_dialog import Table3DDialog

        config = {
            "channel_id": 100,
            "name": "TestTable3D",
            "x_axis_channel": 10,  # FuelLevel
            "y_axis_channel": 11,  # OilPressure
            "x_min": 0, "x_max": 100, "x_step": 50,
            "y_min": 0, "y_max": 10, "y_step": 5,
            "x_values": [0, 50, 100],
            "y_values": [0, 5, 10],
            "data": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        }

        dialog = Table3DDialog(config=config, available_channels=available_channels_with_ids)

        # Display should show names
        assert dialog.x_channel_edit.text() == "FuelLevel"
        assert dialog.y_channel_edit.text() == "OilPressure"

        dialog.close()

    def test_get_config_returns_channel_ids(self, qapp, available_channels_with_ids):
        """Test get_config returns numeric channel_ids."""
        from ui.dialogs.table_3d_dialog import Table3DDialog

        dialog = Table3DDialog(available_channels=available_channels_with_ids)
        dialog.name_edit.setText("TestTable3D")

        # Set channels by ID
        dialog._set_channel_edit_value(dialog.x_channel_edit, 10)
        dialog._set_channel_edit_value(dialog.y_channel_edit, 11)

        # Create table so validation passes
        dialog.x_min_spin.setValue(0)
        dialog.x_max_spin.setValue(100)
        dialog.x_step_spin.setValue(50)
        dialog.y_min_spin.setValue(0)
        dialog.y_max_spin.setValue(10)
        dialog.y_step_spin.setValue(5)
        dialog._create_table()

        config = dialog.get_config()

        # Config should contain numeric IDs
        assert config["x_axis_channel"] == 10
        assert config["y_axis_channel"] == 11

        dialog.close()


class TestNumberDialogChannelSelection:
    """Tests for Number dialog channel ID handling."""

    def test_channel_operation_displays_name(self, qapp, available_channels_with_ids):
        """Test channel operation displays channel_name."""
        from ui.dialogs.number_dialog import NumberDialog

        config = {
            "channel_id": 100,
            "name": "TestNumber",
            "operation": "channel",
            "inputs": [10],  # FuelLevel
        }

        dialog = NumberDialog(config=config, available_channels=available_channels_with_ids)

        # For channel operation, input should show name
        assert dialog.channel_edit.text() == "FuelLevel"

        dialog.close()

    def test_add_operation_displays_names(self, qapp, available_channels_with_ids):
        """Test add operation displays both channel_names."""
        from ui.dialogs.number_dialog import NumberDialog

        config = {
            "channel_id": 100,
            "name": "TestNumber",
            "operation": "add",
            "inputs": [10, 11],  # FuelLevel + OilPressure
        }

        dialog = NumberDialog(config=config, available_channels=available_channels_with_ids)

        # Both inputs should show names
        assert dialog.add_input1_edit.text() == "FuelLevel"
        assert dialog.add_input2_edit.text() == "OilPressure"

        dialog.close()

    def test_get_config_returns_channel_ids(self, qapp, available_channels_with_ids):
        """Test get_config returns numeric channel_ids."""
        from ui.dialogs.number_dialog import NumberDialog

        dialog = NumberDialog(available_channels=available_channels_with_ids)
        dialog.name_edit.setText("TestNumber")

        # Select "add" operation
        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == "add":
                dialog.operation_combo.setCurrentIndex(i)
                break

        # Set channels by ID
        dialog._set_channel_edit_value(dialog.add_input1_edit, 10)
        dialog._set_channel_edit_value(dialog.add_input2_edit, 11)

        config = dialog.get_config()

        # Config inputs should contain numeric IDs
        assert config["inputs"][0] == 10
        assert config["inputs"][1] == 11

        dialog.close()


class TestChannelSelectorDialog:
    """Tests for ChannelSelectorDialog selection and display behavior."""

    def test_dialog_creation(self, qapp, available_channels_with_ids):
        """Test dialog can be created with channel data."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        dialog = ChannelSelectorDialog(channels_data=available_channels_with_ids)
        assert dialog is not None
        dialog.close()

    def test_select_channel_static_method(self, qapp, available_channels_with_ids):
        """Test static select_channel method exists."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        # Just verify the static method exists
        assert hasattr(ChannelSelectorDialog, 'select_channel')
        assert callable(ChannelSelectorDialog.select_channel)

    def test_dialog_shows_system_channels(self, qapp, available_channels_with_ids):
        """Test dialog shows system channels category."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        dialog = ChannelSelectorDialog(channels_data=available_channels_with_ids)

        # System channels should be available as a category
        assert hasattr(dialog, 'SYSTEM_CHANNELS')
        assert len(dialog.SYSTEM_CHANNELS) > 0

        dialog.close()


class TestSystemChannelNameResolution:
    """Tests for system channel name resolution by numeric ID.

    This tests the critical feature: when a system channel is selected,
    the display should show the string name (e.g., "pmu.status") not
    just the numeric ID (e.g., "#1007").
    """

    def test_get_system_channel_name_predefined(self, qapp):
        """Test lookup of predefined system channels."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        # Test predefined system channels
        assert ChannelSelectorDialog.get_system_channel_name(1000) == "pmu.batteryVoltage"
        assert ChannelSelectorDialog.get_system_channel_name(1001) == "pmu.totalCurrent"
        assert ChannelSelectorDialog.get_system_channel_name(1006) == "pmu.uptime"
        assert ChannelSelectorDialog.get_system_channel_name(1007) == "pmu.status"
        assert ChannelSelectorDialog.get_system_channel_name(1012) == "zero"
        assert ChannelSelectorDialog.get_system_channel_name(1013) == "one"

    def test_get_system_channel_name_rtc(self, qapp):
        """Test lookup of RTC system channels."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(1020) == "pmu.rtc.time"
        assert ChannelSelectorDialog.get_system_channel_name(1022) == "pmu.rtc.hour"
        assert ChannelSelectorDialog.get_system_channel_name(1027) == "pmu.rtc.year"

    def test_get_system_channel_name_analog_inputs(self, qapp):
        """Test lookup of hardware analog input channels (1220-1239)."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(1220) == "pmu.a1.voltage"
        assert ChannelSelectorDialog.get_system_channel_name(1221) == "pmu.a2.voltage"
        assert ChannelSelectorDialog.get_system_channel_name(1239) == "pmu.a20.voltage"

    def test_get_system_channel_name_digital_inputs(self, qapp):
        """Test lookup of hardware digital input channels (0-19)."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(0) == "pmu.d1.state"
        assert ChannelSelectorDialog.get_system_channel_name(1) == "pmu.d2.state"
        assert ChannelSelectorDialog.get_system_channel_name(19) == "pmu.d20.state"

    def test_get_system_channel_name_output_status(self, qapp):
        """Test lookup of output status sub-channels (1100-1129)."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(1100) == "pmu.o1.status"
        assert ChannelSelectorDialog.get_system_channel_name(1101) == "pmu.o2.status"
        assert ChannelSelectorDialog.get_system_channel_name(1129) == "pmu.o30.status"

    def test_get_system_channel_name_output_current(self, qapp):
        """Test lookup of output current sub-channels (1130-1159)."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(1130) == "pmu.o1.current"
        assert ChannelSelectorDialog.get_system_channel_name(1131) == "pmu.o2.current"
        assert ChannelSelectorDialog.get_system_channel_name(1159) == "pmu.o30.current"

    def test_get_system_channel_name_output_voltage(self, qapp):
        """Test lookup of output voltage sub-channels (1160-1189)."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(1160) == "pmu.o1.voltage"
        assert ChannelSelectorDialog.get_system_channel_name(1189) == "pmu.o30.voltage"

    def test_get_system_channel_name_output_active(self, qapp):
        """Test lookup of output active sub-channels (1190-1219)."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(1190) == "pmu.o1.active"
        assert ChannelSelectorDialog.get_system_channel_name(1219) == "pmu.o30.active"

    def test_get_system_channel_name_output_duty_cycle(self, qapp):
        """Test lookup of output duty cycle sub-channels (1250-1279)."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(1250) == "pmu.o1.dutyCycle"
        assert ChannelSelectorDialog.get_system_channel_name(1279) == "pmu.o30.dutyCycle"

    def test_get_system_channel_name_unknown(self, qapp):
        """Test that unknown IDs return None."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        # User channel range (should return None - not a system channel)
        assert ChannelSelectorDialog.get_system_channel_name(100) is None
        assert ChannelSelectorDialog.get_system_channel_name(500) is None

        # Gaps in system channel ranges
        assert ChannelSelectorDialog.get_system_channel_name(1050) is None
        assert ChannelSelectorDialog.get_system_channel_name(1300) is None

    def test_get_system_channel_name_none_input(self, qapp):
        """Test that None input returns None."""
        from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog

        assert ChannelSelectorDialog.get_system_channel_name(None) is None


class TestBaseDialogSystemChannelDisplay:
    """Tests for system channel display in BaseChannelDialog._get_channel_display_name."""

    def test_display_name_for_system_channel(self, qapp, available_channels_with_ids):
        """Test that system channel shows string name, not #ID."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # System channel 1007 should display as "pmu.status", not "#1007"
        display_name = dialog._get_channel_display_name(1007)
        assert display_name == "pmu.status"
        assert display_name != "#1007"

        # System channel 1000 should display as "pmu.batteryVoltage"
        display_name = dialog._get_channel_display_name(1000)
        assert display_name == "pmu.batteryVoltage"

        dialog.close()

    def test_display_name_for_output_subchannel(self, qapp, available_channels_with_ids):
        """Test that output sub-channel shows string name."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # Output current sub-channel
        display_name = dialog._get_channel_display_name(1130)
        assert display_name == "pmu.o1.current"

        # Output status sub-channel
        display_name = dialog._get_channel_display_name(1100)
        assert display_name == "pmu.o1.status"

        dialog.close()

    def test_display_name_for_analog_voltage(self, qapp, available_channels_with_ids):
        """Test that analog voltage channel shows string name."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # Analog voltage sub-channel
        display_name = dialog._get_channel_display_name(1220)
        assert display_name == "pmu.a1.voltage"

        display_name = dialog._get_channel_display_name(1225)
        assert display_name == "pmu.a6.voltage"

        dialog.close()

    def test_user_channel_still_works(self, qapp, available_channels_with_ids):
        """Test that user channel lookup still works after system channel addition."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # User channels should still be found
        display_name = dialog._get_channel_display_name(10)
        assert display_name == "FuelLevel"

        display_name = dialog._get_channel_display_name(21)
        assert display_name == "StartButton"

        dialog.close()

    def test_set_channel_value_with_system_channel(self, qapp, available_channels_with_ids):
        """Test _set_channel_edit_value works with system channels."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # Set a system channel
        dialog._set_channel_edit_value(dialog.start_channel_edit, 1007)

        # Display should show "pmu.status"
        assert dialog.start_channel_edit.text() == "pmu.status"

        # Property should store numeric ID
        assert dialog.start_channel_edit.property("channel_id") == 1007

        dialog.close()

    def test_load_config_with_system_channel(self, qapp, available_channels_with_ids):
        """Test loading config with system channel displays correctly."""
        from ui.dialogs.timer_dialog import TimerDialog

        config = {
            "channel_id": 100,
            "name": "TestTimer",
            "start_channel": 1007,  # System channel: pmu.status
            "stop_channel": 10,     # User channel: FuelLevel
        }

        dialog = TimerDialog(config=config, available_channels=available_channels_with_ids)

        # System channel should show string name
        assert dialog.start_channel_edit.text() == "pmu.status"
        assert dialog.start_channel_edit.property("channel_id") == 1007

        # User channel should still work
        assert dialog.stop_channel_edit.text() == "FuelLevel"
        assert dialog.stop_channel_edit.property("channel_id") == 10

        dialog.close()

    def test_get_config_preserves_system_channel_id(self, qapp, available_channels_with_ids):
        """Test get_config returns numeric ID for system channel."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)
        dialog.name_edit.setText("TestTimer")

        # Set a system channel
        dialog._set_channel_edit_value(dialog.start_channel_edit, 1007)
        dialog._set_channel_edit_value(dialog.stop_channel_edit, 1000)

        config = dialog.get_config()

        # Config should contain numeric IDs
        assert config["start_channel"] == 1007
        assert config["stop_channel"] == 1000

        dialog.close()

    def test_display_name_from_string_channel_id(self, qapp, available_channels_with_ids):
        """Test that string channel IDs (from JSON) resolve to display names."""
        from ui.dialogs.timer_dialog import TimerDialog

        dialog = TimerDialog(available_channels=available_channels_with_ids)

        # String ID should also resolve to system channel name
        display_name = dialog._get_channel_display_name("1007")
        assert display_name == "pmu.status"

        # String with # prefix should also work
        display_name = dialog._get_channel_display_name("#1007")
        assert display_name == "pmu.status"

        # User channel as string
        display_name = dialog._get_channel_display_name("10")
        assert display_name == "FuelLevel"

        dialog.close()

    def test_load_config_with_string_system_channel(self, qapp, available_channels_with_ids):
        """Test loading config where system channel is stored as string."""
        from ui.dialogs.timer_dialog import TimerDialog

        # Config from JSON may have channel as string
        config = {
            "channel_id": 100,
            "name": "TestTimer",
            "start_channel": "1007",  # String, not int
            "stop_channel": 10,
        }

        dialog = TimerDialog(config=config, available_channels=available_channels_with_ids)

        # System channel should show string name even from string input
        assert dialog.start_channel_edit.text() == "pmu.status"

        dialog.close()


class TestOutputConfigDialogChannelSelection:
    """Tests for OutputConfigDialog channel ID handling."""

    def test_get_channel_name_by_id_4tuple(self, qapp, available_channels_with_ids):
        """Test _get_channel_name_by_id handles 4-element tuples."""
        from ui.dialogs.output_config_dialog import OutputConfigDialog

        dialog = OutputConfigDialog(
            available_channels=available_channels_with_ids
        )

        # Should find name from 4-tuple
        name = dialog._get_channel_name_by_id(10)
        assert name == "FuelLevel"

        name = dialog._get_channel_name_by_id(21)
        assert name == "StartButton"

        dialog.close()

    def test_get_channel_name_by_id_not_found(self, qapp, available_channels_with_ids):
        """Test _get_channel_name_by_id fallback for unknown ID."""
        from ui.dialogs.output_config_dialog import OutputConfigDialog

        dialog = OutputConfigDialog(
            available_channels=available_channels_with_ids
        )

        # Unknown ID should return #ID format
        name = dialog._get_channel_name_by_id(999)
        assert name == "#999"

        dialog.close()

    def test_get_channel_name_by_id_system_channel(self, qapp, available_channels_with_ids):
        """Test _get_channel_name_by_id returns system channel name."""
        from ui.dialogs.output_config_dialog import OutputConfigDialog

        dialog = OutputConfigDialog(
            available_channels=available_channels_with_ids
        )

        # System channel should return string name
        name = dialog._get_channel_name_by_id(1007)
        assert name == "pmu.status"

        name = dialog._get_channel_name_by_id(1130)
        assert name == "pmu.o1.current"

        # String ID should also work
        name = dialog._get_channel_name_by_id("1007")
        assert name == "pmu.status"

        dialog.close()


class TestRoundTripChannelId:
    """Tests for complete round-trip: config -> dialog -> config."""

    def test_timer_round_trip(self, qapp, available_channels_with_ids):
        """Test Timer dialog preserves channel_id through edit cycle."""
        from ui.dialogs.timer_dialog import TimerDialog

        original_config = {
            "channel_id": 100,
            "name": "TestTimer",
            "start_channel": 10,
            "stop_channel": 20,
            "mode": "count_up",
            "limit_seconds": 60,
        }

        # Load config into dialog
        dialog = TimerDialog(config=original_config, available_channels=available_channels_with_ids)

        # Get config back
        result_config = dialog.get_config()

        # Channel IDs should be preserved
        assert result_config["start_channel"] == 10
        assert result_config["stop_channel"] == 20

        dialog.close()

    def test_filter_round_trip(self, qapp, available_channels_with_ids):
        """Test Filter dialog preserves channel_id through edit cycle."""
        from ui.dialogs.filter_dialog import FilterDialog

        original_config = {
            "channel_id": 100,
            "name": "TestFilter",
            "input_channel": 11,
            "filter_type": "lowpass",
            "cutoff_frequency": 10.0,
        }

        # Load config into dialog
        dialog = FilterDialog(config=original_config, available_channels=available_channels_with_ids)

        # Get config back
        result_config = dialog.get_config()

        # Channel ID should be preserved
        assert result_config["input_channel"] == 11

        dialog.close()

    def test_pid_round_trip(self, qapp, available_channels_with_ids):
        """Test PID dialog preserves channel_ids through edit cycle."""
        from ui.dialogs.pid_controller_dialog import PIDControllerDialog

        original_config = {
            "channel_id": 100,
            "name": "TestPID",
            "setpoint_channel": 50,
            "process_channel": 10,
            "output_channel": 30,
            "kp": 1.0, "ki": 0.1, "kd": 0.01,
        }

        # Load config into dialog
        dialog = PIDControllerDialog(config=original_config, available_channels=available_channels_with_ids)

        # Get config back
        result_config = dialog.get_config()

        # Channel IDs should be preserved
        assert result_config["setpoint_channel"] == 50
        assert result_config["process_channel"] == 10
        assert result_config["output_channel"] == 30

        dialog.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

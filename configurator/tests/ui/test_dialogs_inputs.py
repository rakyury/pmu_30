"""
UI Tests for Input Configuration Dialogs
Tests: DigitalInputDialog, AnalogInputDialog
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt

from ui.dialogs.digital_input_dialog import DigitalInputDialog
from ui.dialogs.analog_input_dialog import AnalogInputDialog
from models.channel import DigitalInputSubtype, AnalogInputSubtype


class TestDigitalInputDialog:
    """Tests for DigitalInputDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new digital input dialog"""
        dialog = DigitalInputDialog()
        assert dialog is not None
        assert dialog.windowTitle().startswith("New")
        assert "Digital" in dialog.windowTitle()
        dialog.close()

    def test_dialog_creation_edit(self, qapp, sample_channels):
        """Test creating edit dialog with existing config"""
        config = {
            "channel_id": 10,
            "name": "Test Switch",
            "subtype": "switch_active_low",
            "input_pin": 3,
            "enable_pullup": True,
            "threshold_voltage": 2.5,
            "debounce_ms": 100
        }
        dialog = DigitalInputDialog(config=config)
        assert dialog.windowTitle().startswith("Edit")
        assert dialog.name_edit.text() == "Test Switch"
        assert dialog.pullup_check.isChecked() == True
        assert dialog.threshold_spin.value() == 2.5
        assert dialog.debounce_spin.value() == 100  # debounce in milliseconds
        dialog.close()

    @pytest.mark.parametrize("subtype", [
        DigitalInputSubtype.SWITCH_ACTIVE_LOW,
        DigitalInputSubtype.SWITCH_ACTIVE_HIGH,
        DigitalInputSubtype.FREQUENCY,
        DigitalInputSubtype.RPM,
        DigitalInputSubtype.FLEX_FUEL,
        DigitalInputSubtype.BEACON,
        DigitalInputSubtype.PULS_OIL_SENSOR
    ])
    def test_all_subtypes_selectable(self, qapp, subtype):
        """Test all digital input subtypes can be selected"""
        dialog = DigitalInputDialog()

        # Find and select subtype
        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == subtype.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        assert dialog.subtype_combo.currentData() == subtype.value
        dialog.close()

    def test_switch_subtype_shows_debounce(self, qapp):
        """Test switch subtypes show debounce control"""
        dialog = DigitalInputDialog()
        dialog.show()  # Need to show dialog for visibility checks

        # Select switch active low
        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == DigitalInputSubtype.SWITCH_ACTIVE_LOW.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        # Check visibility by hidden state (inverted)
        assert not dialog.debounce_spin.isHidden()
        assert dialog.freq_group.isHidden()
        assert dialog.rpm_group.isHidden()
        dialog.close()

    def test_frequency_subtype_shows_freq_settings(self, qapp):
        """Test frequency subtype shows frequency settings"""
        dialog = DigitalInputDialog()
        dialog.show()

        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == DigitalInputSubtype.FREQUENCY.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        assert not dialog.freq_group.isHidden()
        assert dialog.rpm_group.isHidden()
        dialog.close()

    def test_rpm_subtype_shows_rpm_settings(self, qapp):
        """Test RPM subtype shows teeth setting"""
        dialog = DigitalInputDialog()
        dialog.show()

        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == DigitalInputSubtype.RPM.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        assert not dialog.freq_group.isHidden()
        assert not dialog.rpm_group.isHidden()
        dialog.close()

    def test_get_config_returns_complete_config(self, qapp):
        """Test get_config returns all required fields"""
        dialog = DigitalInputDialog()
        dialog.name_edit.setText("Test Input")
        dialog.pullup_check.setChecked(True)
        dialog.threshold_spin.setValue(3.0)

        config = dialog.get_config()

        assert "channel_id" in config
        assert config["name"] == "Test Input"
        assert config["enable_pullup"] == True
        assert config["threshold_voltage"] == 3.0
        assert "subtype" in config
        assert "input_pin" in config
        dialog.close()

    def test_used_pins_filtered(self, qapp):
        """Test used pins are filtered from selection"""
        used_pins = [0, 1, 2, 3]
        dialog = DigitalInputDialog(used_pins=used_pins)

        available_pins = []
        for i in range(dialog.input_pin_combo.count()):
            available_pins.append(dialog.input_pin_combo.itemData(i))

        # None of the used pins should be available
        for pin in used_pins:
            assert pin not in available_pins

        dialog.close()

    def test_current_pin_available_when_editing(self, qapp):
        """Test current pin remains available when editing"""
        config = {
            "channel_id": 1,
            "name": "Test",
            "subtype": "switch_active_low",
            "input_pin": 2  # This is the field that determines current pin
        }
        used_pins = [0, 1, 2, 3]
        dialog = DigitalInputDialog(config=config, used_pins=used_pins)

        available_pins = []
        for i in range(dialog.input_pin_combo.count()):
            available_pins.append(dialog.input_pin_combo.itemData(i))

        # Current pin (2) should be available since it's the pin being edited
        assert 2 in available_pins
        dialog.close()

    def test_validation_divider_range(self, qapp):
        """Test divider spinbox has proper range constraints"""
        dialog = DigitalInputDialog()
        dialog.name_edit.setText("Test")

        # Divider should have a minimum value > 0
        assert dialog.divider_spin.minimum() >= 0.001
        dialog.close()

    def test_validation_rpm_teeth_minimum(self, qapp):
        """Test RPM teeth spinbox has proper minimum"""
        dialog = DigitalInputDialog()
        dialog.name_edit.setText("Test")

        # Select RPM mode
        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == DigitalInputSubtype.RPM.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        # Teeth spinbox should have a minimum of 1
        assert dialog.teeth_spin.minimum() >= 1
        dialog.close()


class TestAnalogInputDialog:
    """Tests for AnalogInputDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new analog input dialog"""
        dialog = AnalogInputDialog()
        assert dialog is not None
        assert dialog.windowTitle().startswith("New")
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        config = {
            "channel_id": 5,
            "name": "Temperature Sensor",
            "subtype": "linear",
            "input_pin": 0,
            "pullup_option": "10k_up",
            "min_value": 0,
            "max_value": 100,
            "min_voltage": 0.5,
            "max_voltage": 4.5
        }
        dialog = AnalogInputDialog(config=config)
        assert dialog.name_edit.text() == "Temperature Sensor"
        assert dialog.min_value_spin.value() == 0
        assert dialog.max_value_spin.value() == 100
        dialog.close()

    @pytest.mark.parametrize("subtype", [
        AnalogInputSubtype.SWITCH_ACTIVE_LOW,
        AnalogInputSubtype.SWITCH_ACTIVE_HIGH,
        AnalogInputSubtype.ROTARY_SWITCH,
        AnalogInputSubtype.LINEAR,
        AnalogInputSubtype.CALIBRATED
    ])
    def test_all_subtypes_selectable(self, qapp, subtype):
        """Test all analog input subtypes can be selected"""
        dialog = AnalogInputDialog()

        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == subtype.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        assert dialog.subtype_combo.currentData() == subtype.value
        dialog.close()

    def test_switch_subtype_shows_thresholds(self, qapp):
        """Test switch subtype shows threshold settings"""
        dialog = AnalogInputDialog()
        dialog.show()

        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == AnalogInputSubtype.SWITCH_ACTIVE_LOW.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        assert not dialog.switch_group.isHidden()
        assert dialog.linear_group.isHidden()
        assert dialog.calib_group.isHidden()
        dialog.close()

    def test_linear_subtype_shows_mapping(self, qapp):
        """Test linear subtype shows value mapping"""
        dialog = AnalogInputDialog()
        dialog.show()

        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == AnalogInputSubtype.LINEAR.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        assert not dialog.linear_group.isHidden()
        assert dialog.switch_group.isHidden()
        assert dialog.calib_group.isHidden()
        dialog.close()

    def test_calibrated_subtype_shows_table(self, qapp):
        """Test calibrated subtype shows calibration table"""
        dialog = AnalogInputDialog()
        dialog.show()

        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == AnalogInputSubtype.CALIBRATED.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        assert not dialog.calib_group.isHidden()
        assert dialog.linear_group.isHidden()
        dialog.close()

    def test_rotary_switch_shows_positions(self, qapp):
        """Test rotary switch shows position settings"""
        dialog = AnalogInputDialog()
        dialog.show()

        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == AnalogInputSubtype.ROTARY_SWITCH.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        assert not dialog.rotary_group.isHidden()
        dialog.close()

    def test_calibration_table_add_row(self, qapp):
        """Test adding rows to calibration table"""
        dialog = AnalogInputDialog()
        initial_rows = dialog.calib_table.rowCount()

        dialog._add_calibration_row()
        assert dialog.calib_table.rowCount() == initial_rows + 1
        dialog.close()

    def test_calibration_table_remove_row(self, qapp):
        """Test removing rows from calibration table"""
        dialog = AnalogInputDialog()
        dialog._add_calibration_row()
        initial_rows = dialog.calib_table.rowCount()

        dialog.calib_table.setCurrentCell(0, 0)
        dialog._remove_calibration_row()
        assert dialog.calib_table.rowCount() == initial_rows - 1
        dialog.close()

    def test_calibration_table_sort(self, qapp):
        """Test sorting calibration table by voltage"""
        dialog = AnalogInputDialog()

        # Clear and add unsorted data
        dialog.calib_table.setRowCount(0)
        test_data = [(3.0, 30), (1.0, 10), (2.0, 20)]
        for voltage, value in test_data:
            row = dialog.calib_table.rowCount()
            dialog.calib_table.insertRow(row)
            from PyQt6.QtWidgets import QTableWidgetItem
            dialog.calib_table.setItem(row, 0, QTableWidgetItem(str(voltage)))
            dialog.calib_table.setItem(row, 1, QTableWidgetItem(str(value)))

        dialog._sort_calibration_table()

        # Check sorted order
        voltages = []
        for i in range(dialog.calib_table.rowCount()):
            item = dialog.calib_table.item(i, 0)
            if item:
                voltages.append(float(item.text()))

        assert voltages == sorted(voltages)
        dialog.close()

    def test_pullup_options_available(self, qapp):
        """Test all pullup options are available"""
        dialog = AnalogInputDialog()

        expected_options = ["1m_down", "none", "10k_up", "10k_down", "100k_up", "100k_down"]
        actual_options = []
        for i in range(dialog.pullup_combo.count()):
            actual_options.append(dialog.pullup_combo.itemData(i))

        for opt in expected_options:
            assert opt in actual_options
        dialog.close()

    def test_get_config_includes_calibration_points(self, qapp):
        """Test get_config includes calibration table data"""
        dialog = AnalogInputDialog()
        dialog.name_edit.setText("Cal Sensor")

        # Select calibrated mode
        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == AnalogInputSubtype.CALIBRATED.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        config = dialog.get_config()
        assert "calibration_points" in config
        assert isinstance(config["calibration_points"], list)
        dialog.close()

    def test_validation_calibration_points(self, qapp):
        """Test validation requires at least 2 calibration points"""
        dialog = AnalogInputDialog()
        dialog.name_edit.setText("Test")

        # Select calibrated mode
        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == AnalogInputSubtype.CALIBRATED.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break

        # Remove all rows except one
        while dialog.calib_table.rowCount() > 1:
            dialog.calib_table.removeRow(0)

        errors = dialog._validate_specific()
        assert len(errors) > 0
        assert any("2 points" in e for e in errors)
        dialog.close()

    def test_decimal_places_visibility(self, qapp):
        """Test decimal places visible only for linear/calibrated"""
        dialog = AnalogInputDialog()
        dialog.show()

        # Switch mode - decimal not needed
        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == AnalogInputSubtype.SWITCH_ACTIVE_LOW.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break
        assert dialog.decimal_spin.isHidden()

        # Linear mode - decimal visible
        for i in range(dialog.subtype_combo.count()):
            if dialog.subtype_combo.itemData(i) == AnalogInputSubtype.LINEAR.value:
                dialog.subtype_combo.setCurrentIndex(i)
                break
        assert not dialog.decimal_spin.isHidden()
        dialog.close()


class TestAnalogInputPinValidation:
    """Tests for AnalogInputDialog pin validation"""

    def test_used_pins_filtered(self, qapp):
        """Test used pins are filtered from selection"""
        used_pins = [0, 1, 2, 3, 4]
        dialog = AnalogInputDialog(used_pins=used_pins)

        available_pins = []
        for i in range(dialog.pin_combo.count()):
            available_pins.append(dialog.pin_combo.itemData(i))

        # None of the used pins should be available
        for pin in used_pins:
            assert pin not in available_pins

        dialog.close()

    def test_current_pin_available_when_editing(self, qapp):
        """Test current pin remains available when editing"""
        config = {
            "channel_id": 1,
            "name": "Test Analog",
            "subtype": "linear",
            "input_pin": 5  # This is the field that determines current pin
        }
        used_pins = [3, 4, 5, 6, 7]  # Pin 5 is in used list but should still be available
        dialog = AnalogInputDialog(config=config, used_pins=used_pins)

        available_pins = []
        for i in range(dialog.pin_combo.count()):
            available_pins.append(dialog.pin_combo.itemData(i))

        # Current pin (5) should be available since it's the pin being edited
        assert 5 in available_pins
        # Other used pins should NOT be available
        assert 3 not in available_pins
        assert 4 not in available_pins
        assert 6 not in available_pins
        dialog.close()

    def test_pin_correctly_selected_when_some_pins_used(self, qapp):
        """Test pin selection works correctly when some pins are filtered out"""
        config = {
            "channel_id": 1,
            "name": "Test",
            "subtype": "linear",
            "input_pin": 10  # Select pin 10
        }
        used_pins = [0, 1, 2, 3, 4]  # Filter out pins 0-4
        dialog = AnalogInputDialog(config=config, used_pins=used_pins)

        # Verify pin 10 is selected (by data, not index)
        selected_pin = dialog.pin_combo.currentData()
        assert selected_pin == 10
        dialog.close()


class TestInputDialogIntegration:
    """Integration tests for input dialogs"""

    def test_digital_input_roundtrip(self, qapp):
        """Test config can be saved and loaded correctly"""
        original_config = {
            "channel_id": 1,
            "name": "RPM Sensor",
            "subtype": "rpm",
            "input_pin": 5,
            "enable_pullup": True,
            "threshold_voltage": 2.0,
            "trigger_edge": "rising",
            "multiplier": 1.0,
            "divider": 1.0,
            "timeout_ms": 2000,
            "number_of_teeth": 60
        }

        dialog = DigitalInputDialog(config=original_config)
        saved_config = dialog.get_config()

        # Key fields should match
        assert saved_config["name"] == original_config["name"]
        assert saved_config["subtype"] == original_config["subtype"]
        assert saved_config["enable_pullup"] == original_config["enable_pullup"]
        assert saved_config["number_of_teeth"] == original_config["number_of_teeth"]
        dialog.close()

    def test_analog_input_roundtrip(self, qapp):
        """Test analog config can be saved and loaded correctly"""
        original_config = {
            "channel_id": 2,
            "name": "Fuel Level",
            "subtype": "linear",
            "input_pin": 3,
            "pullup_option": "10k_down",
            "min_value": 0,
            "max_value": 100,
            "min_voltage": 0.5,
            "max_voltage": 4.5,
            "decimal_places": 1
        }

        dialog = AnalogInputDialog(config=original_config)
        saved_config = dialog.get_config()

        assert saved_config["name"] == original_config["name"]
        assert saved_config["subtype"] == original_config["subtype"]
        assert saved_config["min_value"] == original_config["min_value"]
        assert saved_config["max_value"] == original_config["max_value"]
        dialog.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

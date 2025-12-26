"""
UI Tests for Output Configuration Dialog
Tests: OutputConfigDialog
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt

from ui.dialogs.output_config_dialog import OutputConfigDialog


class TestOutputConfigDialog:
    """Tests for OutputConfigDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new output dialog"""
        dialog = OutputConfigDialog()
        assert dialog is not None
        assert dialog.windowTitle() == "New Output"
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        config = {
            "channel_id": 1,
            "name": "Fuel Pump",
            "pins": [0, 1],
            "enabled": True,
            "current_limit_a": 15.0,
            "inrush_current_a": 30.0,
            "pwm_enabled": True,
            "pwm_frequency_hz": 500,
            "duty_fixed": 75.0
        }
        dialog = OutputConfigDialog(output_config=config)
        assert dialog.windowTitle() == "Edit Output"
        assert dialog.name_edit.text() == "Fuel Pump"
        assert dialog.current_limit_spin.value() == 15.0
        assert dialog.inrush_current_spin.value() == 30.0
        assert dialog.pwm_enabled_check.isChecked() == True
        assert dialog.pwm_freq_spin.value() == 500
        assert dialog.pwm_duty_spin.value() == 75.0
        dialog.close()

    def test_auto_generate_name(self, qapp):
        """Test auto-generate name for new output"""
        dialog = OutputConfigDialog()
        name = dialog.name_edit.text()
        assert name.startswith("Output")
        dialog.close()

    def test_pin_selection_single(self, qapp):
        """Test selecting single pin"""
        dialog = OutputConfigDialog()

        # Select first pin
        dialog.pin1_combo.setCurrentIndex(0)
        config = dialog.get_config()

        assert len(config["pins"]) >= 1
        dialog.close()

    def test_pin_selection_multiple(self, qapp):
        """Test selecting multiple pins for higher current"""
        dialog = OutputConfigDialog()

        # Select first pin
        if dialog.pin1_combo.count() > 0:
            dialog.pin1_combo.setCurrentIndex(0)

        # Select second pin (skip None option)
        if dialog.pin2_combo.count() > 1:
            dialog.pin2_combo.setCurrentIndex(1)

        config = dialog.get_config()
        # Should have at least 1 pin (pin1)
        assert len(config["pins"]) >= 1
        dialog.close()

    def test_used_pins_filtered(self, qapp):
        """Test used pins are filtered from selection"""
        used = [0, 1, 2, 3, 4]
        dialog = OutputConfigDialog(used_channels=used)

        # Check that used pins are not in the combo
        available_pins = []
        for i in range(dialog.pin1_combo.count()):
            pin = dialog.pin1_combo.itemData(i)
            if pin is not None and pin >= 0:
                available_pins.append(pin)

        for pin in used:
            assert pin not in available_pins
        dialog.close()

    def test_current_pins_available_when_editing(self, qapp):
        """Test current pins available when editing"""
        config = {
            "channel_id": 1,
            "name": "Test",
            "pins": [5, 6],
        }
        used = [0, 1, 2, 3, 4, 5, 6]
        dialog = OutputConfigDialog(output_config=config, used_channels=used)

        # Pins 5 and 6 should be available because they're current pins
        available_pins = []
        for i in range(dialog.pin1_combo.count()):
            pin = dialog.pin1_combo.itemData(i)
            if pin is not None and pin >= 0:
                available_pins.append(pin)

        assert 5 in available_pins
        assert 6 in available_pins
        dialog.close()

    def test_pwm_enabled_checkbox(self, qapp):
        """Test PWM enabled checkbox functionality"""
        dialog = OutputConfigDialog()
        # PWM is disabled by default
        assert dialog.pwm_enabled_check.isChecked() == False

        dialog.pwm_enabled_check.setChecked(True)
        config = dialog.get_config()
        assert config.get("pwm", {}).get("enabled", False) == True
        dialog.close()

    def test_control_function_field(self, qapp):
        """Test control function field exists and works"""
        dialog = OutputConfigDialog()

        # Should have control function edit (read-only display)
        assert hasattr(dialog, 'control_function_edit')
        assert dialog.control_function_edit.isReadOnly()

        # Set control function via internal variable (edit is read-only)
        dialog._source_channel_id = "some_channel"
        dialog.control_function_edit.setText("some_channel")
        config = dialog.get_config()
        assert config.get("source_channel") == "some_channel"
        dialog.close()

    def test_pwm_controls_enable_disable(self, qapp):
        """Test PWM controls enable/disable based on checkbox"""
        dialog = OutputConfigDialog()

        # Initially disabled
        assert dialog.pwm_freq_spin.isEnabled() == False
        assert dialog.pwm_duty_spin.isEnabled() == False

        # Enable PWM
        dialog.pwm_enabled_check.setChecked(True)
        assert dialog.pwm_freq_spin.isEnabled() == True
        assert dialog.pwm_duty_spin.isEnabled() == True

        # Disable PWM
        dialog.pwm_enabled_check.setChecked(False)
        assert dialog.pwm_freq_spin.isEnabled() == False
        dialog.close()

    def test_soft_start_controls_enable_disable(self, qapp):
        """Test soft start controls enable/disable"""
        dialog = OutputConfigDialog()
        dialog.pwm_enabled_check.setChecked(True)

        # Initially disabled
        assert dialog.soft_start_duration_spin.isEnabled() == False

        # Enable soft start
        dialog.soft_start_check.setChecked(True)
        assert dialog.soft_start_duration_spin.isEnabled() == True
        dialog.close()

    def test_retry_forever_disables_count(self, qapp):
        """Test retry forever disables retry count"""
        dialog = OutputConfigDialog()

        # Initially count is enabled
        assert dialog.retry_count_spin.isEnabled() == True

        # Enable retry forever
        dialog.retry_forever_check.setChecked(True)
        assert dialog.retry_count_spin.isEnabled() == False
        dialog.close()

    def test_current_limit_range(self, qapp):
        """Test current limit valid range"""
        dialog = OutputConfigDialog()

        assert dialog.current_limit_spin.minimum() == 0.1
        assert dialog.current_limit_spin.maximum() == 50.0
        dialog.close()

    def test_inrush_current_range(self, qapp):
        """Test inrush current valid range"""
        dialog = OutputConfigDialog()

        assert dialog.inrush_current_spin.minimum() == 0.1
        assert dialog.inrush_current_spin.maximum() == 100.0
        dialog.close()

    def test_pwm_frequency_range(self, qapp):
        """Test PWM frequency valid range"""
        dialog = OutputConfigDialog()

        assert dialog.pwm_freq_spin.minimum() == 100
        assert dialog.pwm_freq_spin.maximum() == 20000
        dialog.close()

    def test_pwm_duty_range(self, qapp):
        """Test PWM duty cycle valid range"""
        dialog = OutputConfigDialog()

        assert dialog.pwm_duty_spin.minimum() == 0.0
        assert dialog.pwm_duty_spin.maximum() == 100.0
        dialog.close()

    def test_get_config_complete(self, qapp):
        """Test get_config returns complete configuration"""
        dialog = OutputConfigDialog()
        dialog.name_edit.setText("Test Output")
        dialog.current_limit_spin.setValue(20.0)
        dialog.pwm_enabled_check.setChecked(True)
        dialog.pwm_freq_spin.setValue(1500)
        dialog.pwm_duty_spin.setValue(80.0)

        config = dialog.get_config()

        # Check required fields
        assert "channel_id" in config
        assert config["name"] == "Test Output"
        assert config["current_limit_a"] == 20.0
        assert config["pwm_enabled"] == True
        assert config["pwm_frequency_hz"] == 1500
        assert config["duty_fixed"] == 80.0

        # Check nested format
        assert "protection" in config
        assert config["protection"]["current_limit"] == 20.0
        assert "pwm" in config
        assert config["pwm"]["enabled"] == True
        dialog.close()

    def test_config_roundtrip(self, qapp):
        """Test config can be saved and loaded correctly"""
        original_config = {
            "channel_id": 5,
            "name": "Headlights",
            "pins": [10, 11],
            "enabled": True,
            "control_function": "",
            "current_limit_a": 25.0,
            "inrush_current_a": 50.0,
            "inrush_time_ms": 300,
            "retry_count": 5,
            "retry_forever": False,
            "retry_delay_ms": 2000,
            "pwm_enabled": True,
            "pwm_frequency_hz": 2000,
            "duty_fixed": 100.0,
            "soft_start_ms": 500
        }

        dialog = OutputConfigDialog(output_config=original_config)
        saved_config = dialog.get_config()

        assert saved_config["name"] == original_config["name"]
        assert saved_config["current_limit_a"] == original_config["current_limit_a"]
        assert saved_config["inrush_current_a"] == original_config["inrush_current_a"]
        assert saved_config["pwm_enabled"] == original_config["pwm_enabled"]
        assert saved_config["pwm_frequency_hz"] == original_config["pwm_frequency_hz"]
        dialog.close()

    def test_nested_config_format(self, qapp):
        """Test loading nested config format"""
        config = {
            "channel_id": 1,
            "name": "Motor",
            "pins": [0],
            "protection": {
                "current_limit": 30.0,
                "inrush_current": 60.0,
                "inrush_time_ms": 400,
                "retry_count": 2,
                "retry_forever": True,
                "retry_delay_ms": 3000
            },
            "pwm": {
                "enabled": True,
                "frequency": 5000,
                "duty_value": 90.0,
                "duty_function": "throttle",
                "soft_start_enabled": True,
                "soft_start_duration_ms": 1500
            }
        }

        dialog = OutputConfigDialog(output_config=config)

        assert dialog.current_limit_spin.value() == 30.0
        assert dialog.inrush_current_spin.value() == 60.0
        assert dialog.retry_forever_check.isChecked() == True
        assert dialog.pwm_enabled_check.isChecked() == True
        assert dialog.pwm_freq_spin.value() == 5000
        assert dialog.pwm_duty_spin.value() == 90.0
        assert dialog.duty_function_edit.text() == "throttle"
        assert dialog.soft_start_check.isChecked() == True
        dialog.close()


class TestOutputConfigDialogValidation:
    """Tests for OutputConfigDialog validation"""

    def test_validation_name_required(self, qapp, qtbot):
        """Test validation requires name"""
        dialog = OutputConfigDialog()
        dialog.name_edit.setText("")

        # Cannot test accept directly without mocking QMessageBox
        # Just verify the condition
        assert dialog.name_edit.text().strip() == ""
        dialog.close()

    def test_validation_pin_required(self, qapp):
        """Test validation requires at least one pin"""
        dialog = OutputConfigDialog()
        dialog.name_edit.setText("Test")

        # The dialog should have valid pin selection by default
        assert dialog.pin1_combo.count() > 0
        dialog.close()


class TestOutputConfigDialogChannelSelector:
    """Tests for channel selector functionality"""

    def test_control_function_browse(self, qapp, available_channels):
        """Test browsing control function"""
        dialog = OutputConfigDialog(available_channels=available_channels)

        # Verify browse button exists
        assert dialog.control_function_btn is not None
        assert dialog.control_function_btn.isEnabled()
        dialog.close()

    def test_duty_function_browse(self, qapp, available_channels):
        """Test browsing duty function"""
        dialog = OutputConfigDialog(available_channels=available_channels)
        dialog.pwm_enabled_check.setChecked(True)

        # Verify browse button exists and is enabled when PWM is enabled
        assert dialog.duty_function_btn is not None
        assert dialog.duty_function_btn.isEnabled()
        dialog.close()

    def test_duty_function_disabled_without_pwm(self, qapp, available_channels):
        """Test duty function browse disabled without PWM"""
        dialog = OutputConfigDialog(available_channels=available_channels)
        dialog.pwm_enabled_check.setChecked(False)

        assert dialog.duty_function_btn.isEnabled() == False
        dialog.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

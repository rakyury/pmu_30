"""
UI Tests for Logic and Number Configuration Dialogs
Tests: LogicDialog, NumberDialog
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt

from ui.dialogs.logic_dialog import LogicDialog
from ui.dialogs.number_dialog import NumberDialog
from models.channel import LogicOperation, MathOperation


class TestLogicDialog:
    """Tests for LogicDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new logic dialog"""
        dialog = LogicDialog()
        assert dialog is not None
        assert dialog.windowTitle().startswith("New")
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        config = {
            "channel_id": 10,
            "name": "Ignition Check",
            "operation": "is_true",
            "channel": "ignition_switch"
        }
        dialog = LogicDialog(config=config)
        assert dialog.windowTitle().startswith("Edit")
        assert dialog.name_edit.text() == "Ignition Check"
        dialog.close()

    @pytest.mark.parametrize("operation", [
        LogicOperation.IS_TRUE,
        LogicOperation.IS_FALSE,
        LogicOperation.EQUAL,
        LogicOperation.NOT_EQUAL,
        LogicOperation.LESS,
        LogicOperation.GREATER,
        LogicOperation.AND,
        LogicOperation.OR,
        LogicOperation.XOR,
        LogicOperation.NOT,
        LogicOperation.HYSTERESIS,
        LogicOperation.PULSE,
        LogicOperation.FLASH,
        LogicOperation.TOGGLE,
    ])
    def test_all_operations_selectable(self, qapp, operation):
        """Test all logic operations can be selected"""
        dialog = LogicDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == operation.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.operation_combo.currentData() == operation.value
        dialog.close()

    def test_is_true_page_shown(self, qapp):
        """Test Is True operation shows correct page"""
        dialog = LogicDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.IS_TRUE.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.params_stack.currentIndex() == 0
        dialog.close()

    def test_comparison_page_shown(self, qapp):
        """Test comparison operation shows correct page"""
        dialog = LogicDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.GREATER.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.params_stack.currentIndex() == 1
        dialog.close()

    def test_and_or_page_shown(self, qapp):
        """Test AND operation shows correct page"""
        dialog = LogicDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.AND.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.params_stack.currentIndex() == 2
        dialog.close()

    def test_hysteresis_page_shown(self, qapp):
        """Test hysteresis shows correct page"""
        dialog = LogicDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.HYSTERESIS.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.params_stack.currentIndex() == 4
        dialog.close()

    def test_pulse_page_shown(self, qapp):
        """Test pulse shows correct page"""
        dialog = LogicDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.PULSE.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.params_stack.currentIndex() == 7
        dialog.close()

    def test_flash_page_shown(self, qapp):
        """Test flash shows correct page"""
        dialog = LogicDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.FLASH.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.params_stack.currentIndex() == 8
        dialog.close()

    def test_operation_description_updates(self, qapp):
        """Test operation description updates when selection changes"""
        dialog = LogicDialog()

        # Select IS_TRUE
        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.IS_TRUE.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.op_description.text() != ""
        desc1 = dialog.op_description.text()

        # Select AND
        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.AND.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.op_description.text() != desc1
        dialog.close()

    def test_get_config_is_true(self, qapp):
        """Test get_config for Is True operation"""
        dialog = LogicDialog()
        dialog.name_edit.setText("Test Logic")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.IS_TRUE.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.is_tf_channel_edit.setText("test_channel")
        dialog.is_tf_true_delay.setValue(1.5)
        dialog.is_tf_false_delay.setValue(0.5)

        config = dialog.get_config()

        assert config["operation"] == LogicOperation.IS_TRUE.value
        assert config["channel"] == "test_channel"
        assert config["true_delay_s"] == 1.5
        assert config["false_delay_s"] == 0.5
        dialog.close()

    def test_get_config_comparison(self, qapp):
        """Test get_config for comparison operation"""
        dialog = LogicDialog()
        dialog.name_edit.setText("Test Comparison")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.GREATER.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.cmp_channel_edit.setText("voltage")
        dialog.cmp_constant.setValue(12.0)

        config = dialog.get_config()

        assert config["operation"] == LogicOperation.GREATER.value
        assert config["channel"] == "voltage"
        assert config["constant"] == 12.0
        dialog.close()

    def test_get_config_and(self, qapp):
        """Test get_config for AND operation"""
        dialog = LogicDialog()
        dialog.name_edit.setText("Test AND")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.AND.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.and_or_ch1_edit.setText("switch1")
        dialog.and_or_ch2_edit.setText("switch2")

        config = dialog.get_config()

        assert config["operation"] == LogicOperation.AND.value
        assert config["channel"] == "switch1"
        assert config["channel_2"] == "switch2"
        dialog.close()

    def test_get_config_hysteresis(self, qapp):
        """Test get_config for hysteresis operation"""
        dialog = LogicDialog()
        dialog.name_edit.setText("Test Hysteresis")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.HYSTERESIS.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.hyst_channel_edit.setText("temperature")
        dialog.hyst_upper.setValue(90.0)
        dialog.hyst_lower.setValue(80.0)

        config = dialog.get_config()

        assert config["operation"] == LogicOperation.HYSTERESIS.value
        assert config["channel"] == "temperature"
        assert config["upper_value"] == 90.0
        assert config["lower_value"] == 80.0
        dialog.close()

    def test_validation_is_true_requires_channel(self, qapp):
        """Test validation for Is True requires channel"""
        dialog = LogicDialog()
        dialog.name_edit.setText("Test")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.IS_TRUE.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.is_tf_channel_edit.setText("")
        errors = dialog._validate_specific()

        assert len(errors) > 0
        assert any("Channel" in e for e in errors)
        dialog.close()

    def test_validation_and_requires_both_channels(self, qapp):
        """Test validation for AND requires both channels"""
        dialog = LogicDialog()
        dialog.name_edit.setText("Test")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.AND.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.and_or_ch1_edit.setText("switch1")
        dialog.and_or_ch2_edit.setText("")
        errors = dialog._validate_specific()

        assert len(errors) > 0
        assert any("#2" in e for e in errors)
        dialog.close()

    def test_validation_hysteresis_upper_lower(self, qapp):
        """Test validation for hysteresis upper/lower values"""
        dialog = LogicDialog()
        dialog.name_edit.setText("Test")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == LogicOperation.HYSTERESIS.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.hyst_channel_edit.setText("temp")
        dialog.hyst_upper.setValue(50.0)
        dialog.hyst_lower.setValue(60.0)  # Lower > Upper - invalid
        errors = dialog._validate_specific()

        assert len(errors) > 0
        assert any("less than" in e for e in errors)
        dialog.close()

    def test_config_roundtrip(self, qapp):
        """Test config can be saved and loaded correctly"""
        original_config = {
            "channel_id": 5,
            "name": "Fan Control",
            "operation": "hysteresis",
            "channel": "coolant_temp",
            "polarity": "normal",
            "upper_value": 95.0,
            "lower_value": 85.0
        }

        dialog = LogicDialog(config=original_config)
        saved_config = dialog.get_config()

        assert saved_config["name"] == original_config["name"]
        assert saved_config["operation"] == original_config["operation"]
        assert saved_config["upper_value"] == original_config["upper_value"]
        assert saved_config["lower_value"] == original_config["lower_value"]
        dialog.close()


class TestNumberDialog:
    """Tests for NumberDialog (Math channels)"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new number dialog"""
        dialog = NumberDialog()
        assert dialog is not None
        assert dialog.windowTitle().startswith("New")
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        config = {
            "channel_id": 20,
            "name": "Voltage Sum",
            "operation": "add",
            "inputs": ["battery_voltage", "aux_voltage"],
            "decimal_places": 2
        }
        dialog = NumberDialog(config=config)
        assert dialog.windowTitle().startswith("Edit")
        assert dialog.name_edit.text() == "Voltage Sum"
        dialog.close()

    @pytest.mark.parametrize("operation", [
        MathOperation.CONSTANT,
        MathOperation.CHANNEL,
        MathOperation.ADD,
        MathOperation.SUBTRACT,
        MathOperation.MULTIPLY,
        MathOperation.DIVIDE,
        MathOperation.MIN,
        MathOperation.MAX,
        MathOperation.CLAMP,
    ])
    def test_all_operations_selectable(self, qapp, operation):
        """Test all math operations can be selected"""
        dialog = NumberDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == operation.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.operation_combo.currentData() == operation.value
        dialog.close()

    def test_constant_page_shown(self, qapp):
        """Test constant operation shows correct page"""
        dialog = NumberDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.CONSTANT.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.stacked_widget.currentIndex() == 0
        dialog.close()

    def test_channel_page_shown(self, qapp):
        """Test channel operation shows correct page"""
        dialog = NumberDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.CHANNEL.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.stacked_widget.currentIndex() == 1
        dialog.close()

    def test_add_page_shown(self, qapp):
        """Test add operation shows correct page"""
        dialog = NumberDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.ADD.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.stacked_widget.currentIndex() == 2
        dialog.close()

    def test_clamp_page_shown(self, qapp):
        """Test clamp operation shows correct page"""
        dialog = NumberDialog()

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.CLAMP.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        assert dialog.stacked_widget.currentIndex() == 9
        dialog.close()

    def test_get_config_constant(self, qapp):
        """Test get_config for constant operation"""
        dialog = NumberDialog()
        dialog.name_edit.setText("PI")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.CONSTANT.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.constant_value_spin.setValue(3.14159)

        config = dialog.get_config()

        assert config["operation"] == MathOperation.CONSTANT.value
        assert abs(config["constant_value"] - 3.14159) < 0.0001
        dialog.close()

    def test_get_config_add(self, qapp):
        """Test get_config for add operation"""
        dialog = NumberDialog()
        dialog.name_edit.setText("Sum")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.ADD.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.add_input1_edit.setText("value1")
        dialog.add_input2_edit.setText("value2")

        config = dialog.get_config()

        assert config["operation"] == MathOperation.ADD.value
        assert config["inputs"] == ["value1", "value2"]
        dialog.close()

    def test_get_config_clamp(self, qapp):
        """Test get_config for clamp operation"""
        dialog = NumberDialog()
        dialog.name_edit.setText("Clamped Value")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.CLAMP.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.clamp_edit.setText("input_value")
        dialog.clamp_min_spin.setValue(0.0)
        dialog.clamp_max_spin.setValue(100.0)

        config = dialog.get_config()

        assert config["operation"] == MathOperation.CLAMP.value
        assert config["inputs"] == ["input_value"]
        assert config["clamp_min"] == 0.0
        assert config["clamp_max"] == 100.0
        dialog.close()

    def test_decimal_places(self, qapp):
        """Test decimal places setting"""
        dialog = NumberDialog()
        dialog.name_edit.setText("Test")
        dialog.decimal_spin.setValue(4)

        config = dialog.get_config()

        assert config["decimal_places"] == 4
        dialog.close()

    def test_validation_channel_required(self, qapp):
        """Test validation for channel operation requires channel"""
        dialog = NumberDialog()
        dialog.name_edit.setText("Test")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.CHANNEL.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.channel_edit.setText("")
        errors = dialog._validate_specific()

        assert len(errors) > 0
        assert any("Channel" in e for e in errors)
        dialog.close()

    def test_validation_add_requires_both_inputs(self, qapp):
        """Test validation for add requires both inputs"""
        dialog = NumberDialog()
        dialog.name_edit.setText("Test")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.ADD.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.add_input1_edit.setText("value1")
        dialog.add_input2_edit.setText("")
        errors = dialog._validate_specific()

        assert len(errors) > 0
        assert any("Input 2" in e for e in errors)
        dialog.close()

    def test_validation_clamp_min_max(self, qapp):
        """Test validation for clamp min < max"""
        dialog = NumberDialog()
        dialog.name_edit.setText("Test")

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.CLAMP.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        dialog.clamp_edit.setText("input")
        dialog.clamp_min_spin.setValue(100.0)
        dialog.clamp_max_spin.setValue(50.0)  # Max < Min - invalid
        errors = dialog._validate_specific()

        assert len(errors) > 0
        assert any("less than" in e for e in errors)
        dialog.close()

    def test_multiplier_options_available(self, qapp):
        """Test all multiplier options are available"""
        dialog = NumberDialog()

        expected = ["*1", "*10", "*100", "*1000", "raw"]

        for i in range(dialog.operation_combo.count()):
            if dialog.operation_combo.itemData(i) == MathOperation.ADD.value:
                dialog.operation_combo.setCurrentIndex(i)
                break

        actual_labels = []
        for i in range(dialog.add_input1_mult.count()):
            actual_labels.append(dialog.add_input1_mult.itemText(i))

        for opt in expected:
            assert opt in actual_labels
        dialog.close()

    def test_config_roundtrip(self, qapp):
        """Test config can be saved and loaded correctly"""
        original_config = {
            "channel_id": 15,
            "name": "Duty Cycle",
            "operation": "clamp",
            "inputs": ["raw_duty"],
            "input_multipliers": ["*1"],
            "clamp_min": 0.0,
            "clamp_max": 100.0,
            "decimal_places": 1
        }

        dialog = NumberDialog(config=original_config)
        saved_config = dialog.get_config()

        assert saved_config["name"] == original_config["name"]
        assert saved_config["operation"] == original_config["operation"]
        assert saved_config["clamp_min"] == original_config["clamp_min"]
        assert saved_config["clamp_max"] == original_config["clamp_max"]
        dialog.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

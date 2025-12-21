"""
Logic Function Configuration Dialog
Based on ECUMaster ADU logic function implementation
Dynamic UI based on operation type
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGridLayout, QGroupBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QLabel, QStackedWidget, QWidget, QVBoxLayout, QCheckBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_gpio_dialog import BaseGPIODialog
from models.gpio import GPIOType, LogicOperation, LogicPolarity, LogicDefaultState, EdgeType


class LogicDialog(BaseGPIODialog):
    """Dialog for configuring logic function channels (ECUMaster ADU style)"""

    # All operations with display names and descriptions
    OPERATIONS = [
        (LogicOperation.IS_TRUE, "Is True", "Output = 1 if Channel != 0"),
        (LogicOperation.IS_FALSE, "Is False", "Output = 1 if Channel == 0"),
        (LogicOperation.EQUAL, "Equal", "Output = 1 if Channel == Constant"),
        (LogicOperation.NOT_EQUAL, "Not Equal", "Output = 1 if Channel != Constant"),
        (LogicOperation.LESS, "Less", "Output = 1 if Channel < Constant"),
        (LogicOperation.GREATER, "Greater", "Output = 1 if Channel > Constant"),
        (LogicOperation.LESS_EQUAL, "Less or Equal", "Output = 1 if Channel <= Constant"),
        (LogicOperation.GREATER_EQUAL, "Greater or Equal", "Output = 1 if Channel >= Constant"),
        (LogicOperation.AND, "And", "Output = 1 if Channel1 AND Channel2"),
        (LogicOperation.OR, "Or", "Output = 1 if Channel1 OR Channel2"),
        (LogicOperation.XOR, "Xor", "Output = 1 if Channel1 XOR Channel2 (one but not both)"),
        (LogicOperation.CHANGED, "Changed", "Output = 1 if value changed by threshold"),
        (LogicOperation.HYSTERESIS, "Hysteresis", "Output with upper/lower thresholds"),
        (LogicOperation.SET_RESET_LATCH, "Set-Reset Latch", "SR flip-flop"),
        (LogicOperation.TOGGLE, "Toggle", "Toggle output on edge"),
        (LogicOperation.PULSE, "Pulse", "Generate pulse(s) on edge"),
        (LogicOperation.FLASH, "Flash", "Periodic on/off when active"),
    ]

    # Mapping operation to page index
    OPERATION_PAGE_MAP = {
        LogicOperation.IS_TRUE: 0,
        LogicOperation.IS_FALSE: 0,
        LogicOperation.EQUAL: 1,
        LogicOperation.NOT_EQUAL: 1,
        LogicOperation.LESS: 1,
        LogicOperation.GREATER: 1,
        LogicOperation.LESS_EQUAL: 1,
        LogicOperation.GREATER_EQUAL: 1,
        LogicOperation.AND: 2,
        LogicOperation.OR: 2,
        LogicOperation.XOR: 2,
        LogicOperation.CHANGED: 3,
        LogicOperation.HYSTERESIS: 4,
        LogicOperation.SET_RESET_LATCH: 5,
        LogicOperation.TOGGLE: 6,
        LogicOperation.PULSE: 7,
        LogicOperation.FLASH: 8,
    }

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None):
        super().__init__(parent, config, available_channels, GPIOType.LOGIC)

        self._create_operation_group()
        self._create_params_group()

        # Connect operation change handler
        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        # Update visibility based on current operation
        self._on_operation_changed()

    def _create_operation_group(self):
        """Create operation selection group"""
        op_group = QGroupBox("Operation")
        op_layout = QFormLayout()

        # Operation selection
        self.operation_combo = QComboBox()
        for op_enum, display_name, description in self.OPERATIONS:
            self.operation_combo.addItem(display_name, op_enum.value)
        op_layout.addRow("Operation:", self.operation_combo)

        # Operation description
        self.op_description = QLabel("")
        self.op_description.setStyleSheet("color: #666; font-style: italic;")
        self.op_description.setWordWrap(True)
        op_layout.addRow("", self.op_description)

        op_group.setLayout(op_layout)
        self.content_layout.addWidget(op_group)

    def _create_params_group(self):
        """Create parameters group with stacked widget for different operations"""
        self.params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout()

        self.params_stack = QStackedWidget()

        # Page 0: Is True / Is False (channel + delays)
        self._create_is_true_false_page()

        # Page 1: Comparison (channel + constant + delays)
        self._create_comparison_page()

        # Page 2: And / Or / Xor (channel1 + channel2 + delays)
        self._create_and_or_page()

        # Page 3: Changed (channel + threshold + time_on)
        self._create_changed_page()

        # Page 4: Hysteresis (channel + polarity + upper/lower)
        self._create_hysteresis_page()

        # Page 5: Set-Reset Latch (set + reset + default)
        self._create_set_reset_page()

        # Page 6: Toggle (edge + toggle + set + reset + default)
        self._create_toggle_page()

        # Page 7: Pulse (edge + channel + count + time_on + retrigger)
        self._create_pulse_page()

        # Page 8: Flash (channel + time_on + time_off)
        self._create_flash_page()

        params_layout.addWidget(self.params_stack)
        self.params_group.setLayout(params_layout)
        self.content_layout.addWidget(self.params_group)

    def _create_is_true_false_page(self):
        """Page for Is True / Is False operations"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Channel (full width)
        layout.addWidget(QLabel("Channel: *"), 0, 0)
        self.is_tf_channel_widget, self.is_tf_channel_edit = self._create_channel_selector(
            "Select channel..."
        )
        layout.addWidget(self.is_tf_channel_widget, 0, 1, 1, 3)

        # Row 1: True delay | False delay
        layout.addWidget(QLabel("True delay:"), 1, 0)
        self.is_tf_true_delay = QDoubleSpinBox()
        self.is_tf_true_delay.setRange(0, 3600)
        self.is_tf_true_delay.setDecimals(2)
        self.is_tf_true_delay.setSuffix(" s")
        self.is_tf_true_delay.setValue(0)
        layout.addWidget(self.is_tf_true_delay, 1, 1)

        layout.addWidget(QLabel("False delay:"), 1, 2)
        self.is_tf_false_delay = QDoubleSpinBox()
        self.is_tf_false_delay.setRange(0, 3600)
        self.is_tf_false_delay.setDecimals(2)
        self.is_tf_false_delay.setSuffix(" s")
        self.is_tf_false_delay.setValue(0)
        layout.addWidget(self.is_tf_false_delay, 1, 3)

        self.params_stack.addWidget(page)

    def _create_comparison_page(self):
        """Page for comparison operations (==, !=, <, >, <=, >=)"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Channel (full width)
        layout.addWidget(QLabel("Channel: *"), 0, 0)
        self.cmp_channel_widget, self.cmp_channel_edit = self._create_channel_selector(
            "Select channel..."
        )
        layout.addWidget(self.cmp_channel_widget, 0, 1, 1, 3)

        # Row 1: Constant | (empty)
        layout.addWidget(QLabel("Constant:"), 1, 0)
        self.cmp_constant = QDoubleSpinBox()
        self.cmp_constant.setRange(-1000000, 1000000)
        self.cmp_constant.setDecimals(4)
        self.cmp_constant.setValue(0)
        layout.addWidget(self.cmp_constant, 1, 1)

        # Row 2: True delay | False delay
        layout.addWidget(QLabel("True delay:"), 2, 0)
        self.cmp_true_delay = QDoubleSpinBox()
        self.cmp_true_delay.setRange(0, 3600)
        self.cmp_true_delay.setDecimals(2)
        self.cmp_true_delay.setSuffix(" s")
        self.cmp_true_delay.setValue(0)
        layout.addWidget(self.cmp_true_delay, 2, 1)

        layout.addWidget(QLabel("False delay:"), 2, 2)
        self.cmp_false_delay = QDoubleSpinBox()
        self.cmp_false_delay.setRange(0, 3600)
        self.cmp_false_delay.setDecimals(2)
        self.cmp_false_delay.setSuffix(" s")
        self.cmp_false_delay.setValue(0)
        layout.addWidget(self.cmp_false_delay, 2, 3)

        self.params_stack.addWidget(page)

    def _create_and_or_page(self):
        """Page for And / Or / Xor operations"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Channel 1 (full width)
        layout.addWidget(QLabel("Channel #1: *"), 0, 0)
        self.and_or_ch1_widget, self.and_or_ch1_edit = self._create_channel_selector(
            "Select channel #1..."
        )
        layout.addWidget(self.and_or_ch1_widget, 0, 1, 1, 3)

        # Row 1: Channel 2 (full width)
        layout.addWidget(QLabel("Channel #2: *"), 1, 0)
        self.and_or_ch2_widget, self.and_or_ch2_edit = self._create_channel_selector(
            "Select channel #2..."
        )
        layout.addWidget(self.and_or_ch2_widget, 1, 1, 1, 3)

        # Row 2: True delay | False delay
        layout.addWidget(QLabel("True delay:"), 2, 0)
        self.and_or_true_delay = QDoubleSpinBox()
        self.and_or_true_delay.setRange(0, 3600)
        self.and_or_true_delay.setDecimals(2)
        self.and_or_true_delay.setSuffix(" s")
        self.and_or_true_delay.setValue(0)
        layout.addWidget(self.and_or_true_delay, 2, 1)

        layout.addWidget(QLabel("False delay:"), 2, 2)
        self.and_or_false_delay = QDoubleSpinBox()
        self.and_or_false_delay.setRange(0, 3600)
        self.and_or_false_delay.setDecimals(2)
        self.and_or_false_delay.setSuffix(" s")
        self.and_or_false_delay.setValue(0)
        layout.addWidget(self.and_or_false_delay, 2, 3)

        self.params_stack.addWidget(page)

    def _create_changed_page(self):
        """Page for Changed operation"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Channel (full width)
        layout.addWidget(QLabel("Channel: *"), 0, 0)
        self.changed_channel_widget, self.changed_channel_edit = self._create_channel_selector(
            "Select channel..."
        )
        layout.addWidget(self.changed_channel_widget, 0, 1, 1, 3)

        # Row 1: Threshold | Time on
        layout.addWidget(QLabel("Threshold:"), 1, 0)
        self.changed_threshold = QDoubleSpinBox()
        self.changed_threshold.setRange(0, 1000000)
        self.changed_threshold.setDecimals(4)
        self.changed_threshold.setValue(1.0)
        layout.addWidget(self.changed_threshold, 1, 1)

        layout.addWidget(QLabel("Time on:"), 1, 2)
        self.changed_time_on = QDoubleSpinBox()
        self.changed_time_on.setRange(0, 3600)
        self.changed_time_on.setDecimals(2)
        self.changed_time_on.setSuffix(" s")
        self.changed_time_on.setValue(0.5)
        layout.addWidget(self.changed_time_on, 1, 3)

        self.params_stack.addWidget(page)

    def _create_hysteresis_page(self):
        """Page for Hysteresis operation"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Channel (full width)
        layout.addWidget(QLabel("Source channel: *"), 0, 0)
        self.hyst_channel_widget, self.hyst_channel_edit = self._create_channel_selector(
            "Select source channel..."
        )
        layout.addWidget(self.hyst_channel_widget, 0, 1, 1, 3)

        # Row 1: Polarity | (empty)
        layout.addWidget(QLabel("Polarity:"), 1, 0)
        self.hyst_polarity = QComboBox()
        self.hyst_polarity.addItem("Normal", LogicPolarity.NORMAL.value)
        self.hyst_polarity.addItem("Inverted", LogicPolarity.INVERTED.value)
        layout.addWidget(self.hyst_polarity, 1, 1)

        # Row 2: Upper value | Lower value
        layout.addWidget(QLabel("Upper value:"), 2, 0)
        self.hyst_upper = QDoubleSpinBox()
        self.hyst_upper.setRange(-1000000, 1000000)
        self.hyst_upper.setDecimals(2)
        self.hyst_upper.setValue(100.0)
        layout.addWidget(self.hyst_upper, 2, 1)

        layout.addWidget(QLabel("Lower value:"), 2, 2)
        self.hyst_lower = QDoubleSpinBox()
        self.hyst_lower.setRange(-1000000, 1000000)
        self.hyst_lower.setDecimals(2)
        self.hyst_lower.setValue(0.0)
        layout.addWidget(self.hyst_lower, 2, 3)

        self.params_stack.addWidget(page)

    def _create_set_reset_page(self):
        """Page for Set-Reset Latch operation"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Set channel (full width)
        layout.addWidget(QLabel("Set channel: *"), 0, 0)
        self.sr_set_widget, self.sr_set_edit = self._create_channel_selector(
            "Select set channel..."
        )
        layout.addWidget(self.sr_set_widget, 0, 1, 1, 3)

        # Row 1: Reset channel (full width)
        layout.addWidget(QLabel("Reset channel: *"), 1, 0)
        self.sr_reset_widget, self.sr_reset_edit = self._create_channel_selector(
            "Select reset channel..."
        )
        layout.addWidget(self.sr_reset_widget, 1, 1, 1, 3)

        # Row 2: Default state
        layout.addWidget(QLabel("Default state:"), 2, 0)
        self.sr_default = QComboBox()
        self.sr_default.addItem("Off", LogicDefaultState.OFF.value)
        self.sr_default.addItem("On", LogicDefaultState.ON.value)
        layout.addWidget(self.sr_default, 2, 1)

        self.params_stack.addWidget(page)

    def _create_toggle_page(self):
        """Page for Toggle operation"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Edge | Default state
        layout.addWidget(QLabel("Edge:"), 0, 0)
        self.toggle_edge = QComboBox()
        self.toggle_edge.addItem("Rising", EdgeType.RISING.value)
        self.toggle_edge.addItem("Falling", EdgeType.FALLING.value)
        layout.addWidget(self.toggle_edge, 0, 1)

        layout.addWidget(QLabel("Default state:"), 0, 2)
        self.toggle_default = QComboBox()
        self.toggle_default.addItem("Off", LogicDefaultState.OFF.value)
        self.toggle_default.addItem("On", LogicDefaultState.ON.value)
        layout.addWidget(self.toggle_default, 0, 3)

        # Row 1: Toggle channel (full width)
        layout.addWidget(QLabel("Toggle channel: *"), 1, 0)
        self.toggle_channel_widget, self.toggle_channel_edit = self._create_channel_selector(
            "Select toggle channel..."
        )
        layout.addWidget(self.toggle_channel_widget, 1, 1, 1, 3)

        # Row 2: Set channel (full width)
        layout.addWidget(QLabel("Set channel:"), 2, 0)
        self.toggle_set_widget, self.toggle_set_edit = self._create_channel_selector(
            "Select set channel (optional)..."
        )
        layout.addWidget(self.toggle_set_widget, 2, 1, 1, 3)

        # Row 3: Reset channel (full width)
        layout.addWidget(QLabel("Reset channel:"), 3, 0)
        self.toggle_reset_widget, self.toggle_reset_edit = self._create_channel_selector(
            "Select reset channel (optional)..."
        )
        layout.addWidget(self.toggle_reset_widget, 3, 1, 1, 3)

        self.params_stack.addWidget(page)

    def _create_pulse_page(self):
        """Page for Pulse operation"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Channel (full width)
        layout.addWidget(QLabel("Channel: *"), 0, 0)
        self.pulse_channel_widget, self.pulse_channel_edit = self._create_channel_selector(
            "Select channel..."
        )
        layout.addWidget(self.pulse_channel_widget, 0, 1, 1, 3)

        # Row 1: Edge | Count
        layout.addWidget(QLabel("Edge:"), 1, 0)
        self.pulse_edge = QComboBox()
        self.pulse_edge.addItem("Rising", EdgeType.RISING.value)
        self.pulse_edge.addItem("Falling", EdgeType.FALLING.value)
        layout.addWidget(self.pulse_edge, 1, 1)

        layout.addWidget(QLabel("Count:"), 1, 2)
        self.pulse_count = QSpinBox()
        self.pulse_count.setRange(1, 100)
        self.pulse_count.setValue(1)
        layout.addWidget(self.pulse_count, 1, 3)

        # Row 2: Time on | Retrigger
        layout.addWidget(QLabel("Time on:"), 2, 0)
        self.pulse_time_on = QDoubleSpinBox()
        self.pulse_time_on.setRange(0.01, 3600)
        self.pulse_time_on.setDecimals(2)
        self.pulse_time_on.setSuffix(" s")
        self.pulse_time_on.setValue(0.5)
        layout.addWidget(self.pulse_time_on, 2, 1)

        self.pulse_retrigger = QCheckBox("Retrigger")
        self.pulse_retrigger.setToolTip("Restart pulse if triggered again before completion")
        layout.addWidget(self.pulse_retrigger, 2, 2, 1, 2)

        self.params_stack.addWidget(page)

    def _create_flash_page(self):
        """Page for Flash operation"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 0: Channel (full width)
        layout.addWidget(QLabel("Channel: *"), 0, 0)
        self.flash_channel_widget, self.flash_channel_edit = self._create_channel_selector(
            "Select channel..."
        )
        layout.addWidget(self.flash_channel_widget, 0, 1, 1, 3)

        # Row 1: Time on | Time off
        layout.addWidget(QLabel("Time on:"), 1, 0)
        self.flash_time_on = QDoubleSpinBox()
        self.flash_time_on.setRange(0.01, 3600)
        self.flash_time_on.setDecimals(2)
        self.flash_time_on.setSuffix(" s")
        self.flash_time_on.setValue(0.5)
        layout.addWidget(self.flash_time_on, 1, 1)

        layout.addWidget(QLabel("Time off:"), 1, 2)
        self.flash_time_off = QDoubleSpinBox()
        self.flash_time_off.setRange(0.01, 3600)
        self.flash_time_off.setDecimals(2)
        self.flash_time_off.setSuffix(" s")
        self.flash_time_off.setValue(0.5)
        layout.addWidget(self.flash_time_off, 1, 3)

        self.params_stack.addWidget(page)

    def _on_operation_changed(self):
        """Handle operation selection change - switch UI page"""
        op_value = self.operation_combo.currentData()

        # Find operation enum
        op_enum = None
        for op, name, desc in self.OPERATIONS:
            if op.value == op_value:
                op_enum = op
                self.op_description.setText(desc)
                break

        # Switch to appropriate page
        if op_enum:
            page_index = self.OPERATION_PAGE_MAP.get(op_enum, 0)
            self.params_stack.setCurrentIndex(page_index)

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        operation = config.get("operation", "is_true")

        # Set operation combo
        for i in range(self.operation_combo.count()):
            if self.operation_combo.itemData(i) == operation:
                self.operation_combo.setCurrentIndex(i)
                break

        # Load based on operation type
        op_enum = LogicOperation(operation)
        page_index = self.OPERATION_PAGE_MAP.get(op_enum, 0)

        if page_index == 0:  # Is True / Is False
            self.is_tf_channel_edit.setText(config.get("channel", ""))
            self.is_tf_true_delay.setValue(config.get("true_delay_s", 0))
            self.is_tf_false_delay.setValue(config.get("false_delay_s", 0))

        elif page_index == 1:  # Comparison
            self.cmp_channel_edit.setText(config.get("channel", ""))
            self.cmp_constant.setValue(config.get("constant", 0))
            self.cmp_true_delay.setValue(config.get("true_delay_s", 0))
            self.cmp_false_delay.setValue(config.get("false_delay_s", 0))

        elif page_index == 2:  # And / Or / Xor
            self.and_or_ch1_edit.setText(config.get("channel", ""))
            self.and_or_ch2_edit.setText(config.get("channel_2", ""))
            self.and_or_true_delay.setValue(config.get("true_delay_s", 0))
            self.and_or_false_delay.setValue(config.get("false_delay_s", 0))

        elif page_index == 3:  # Changed
            self.changed_channel_edit.setText(config.get("channel", ""))
            self.changed_threshold.setValue(config.get("threshold", 1.0))
            self.changed_time_on.setValue(config.get("time_on_s", 0.5))

        elif page_index == 4:  # Hysteresis
            self.hyst_channel_edit.setText(config.get("channel", ""))
            polarity = config.get("polarity", "normal")
            for i in range(self.hyst_polarity.count()):
                if self.hyst_polarity.itemData(i) == polarity:
                    self.hyst_polarity.setCurrentIndex(i)
                    break
            self.hyst_upper.setValue(config.get("upper_value", 100))
            self.hyst_lower.setValue(config.get("lower_value", 0))

        elif page_index == 5:  # Set-Reset Latch
            self.sr_set_edit.setText(config.get("set_channel", ""))
            self.sr_reset_edit.setText(config.get("reset_channel", ""))
            default = config.get("default_state", "off")
            for i in range(self.sr_default.count()):
                if self.sr_default.itemData(i) == default:
                    self.sr_default.setCurrentIndex(i)
                    break

        elif page_index == 6:  # Toggle
            edge = config.get("edge", "rising")
            for i in range(self.toggle_edge.count()):
                if self.toggle_edge.itemData(i) == edge:
                    self.toggle_edge.setCurrentIndex(i)
                    break
            self.toggle_channel_edit.setText(config.get("toggle_channel", ""))
            self.toggle_set_edit.setText(config.get("set_channel", ""))
            self.toggle_reset_edit.setText(config.get("reset_channel", ""))
            default = config.get("default_state", "off")
            for i in range(self.toggle_default.count()):
                if self.toggle_default.itemData(i) == default:
                    self.toggle_default.setCurrentIndex(i)
                    break

        elif page_index == 7:  # Pulse
            edge = config.get("edge", "rising")
            for i in range(self.pulse_edge.count()):
                if self.pulse_edge.itemData(i) == edge:
                    self.pulse_edge.setCurrentIndex(i)
                    break
            self.pulse_channel_edit.setText(config.get("channel", ""))
            self.pulse_count.setValue(config.get("pulse_count", 1))
            self.pulse_time_on.setValue(config.get("time_on_s", 0.5))
            self.pulse_retrigger.setChecked(config.get("retrigger", False))

        elif page_index == 8:  # Flash
            self.flash_channel_edit.setText(config.get("channel", ""))
            self.flash_time_on.setValue(config.get("time_on_s", 0.5))
            self.flash_time_off.setValue(config.get("time_off_s", 0.5))

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []
        op_value = self.operation_combo.currentData()
        op_enum = LogicOperation(op_value)
        page_index = self.OPERATION_PAGE_MAP.get(op_enum, 0)

        if page_index == 0:  # Is True / Is False
            if not self.is_tf_channel_edit.text().strip():
                errors.append("Channel is required")

        elif page_index == 1:  # Comparison
            if not self.cmp_channel_edit.text().strip():
                errors.append("Channel is required")

        elif page_index == 2:  # And / Or / Xor
            if not self.and_or_ch1_edit.text().strip():
                errors.append("Channel #1 is required")
            if not self.and_or_ch2_edit.text().strip():
                errors.append("Channel #2 is required")

        elif page_index == 3:  # Changed
            if not self.changed_channel_edit.text().strip():
                errors.append("Channel is required")

        elif page_index == 4:  # Hysteresis
            if not self.hyst_channel_edit.text().strip():
                errors.append("Source channel is required")
            if self.hyst_lower.value() >= self.hyst_upper.value():
                errors.append("Lower value must be less than upper value")

        elif page_index == 5:  # Set-Reset Latch
            if not self.sr_set_edit.text().strip():
                errors.append("Set channel is required")
            if not self.sr_reset_edit.text().strip():
                errors.append("Reset channel is required")

        elif page_index == 6:  # Toggle
            if not self.toggle_channel_edit.text().strip():
                errors.append("Toggle channel is required")

        elif page_index == 7:  # Pulse
            if not self.pulse_channel_edit.text().strip():
                errors.append("Channel is required")

        elif page_index == 8:  # Flash
            if not self.flash_channel_edit.text().strip():
                errors.append("Channel is required")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()
        op_value = self.operation_combo.currentData()
        op_enum = LogicOperation(op_value)
        page_index = self.OPERATION_PAGE_MAP.get(op_enum, 0)

        config["operation"] = op_value

        # Initialize all fields with defaults
        config["channel"] = ""
        config["channel_2"] = ""
        config["true_delay_s"] = 0.0
        config["false_delay_s"] = 0.0
        config["constant"] = 0.0
        config["threshold"] = 0.0
        config["time_on_s"] = 0.0
        config["polarity"] = LogicPolarity.NORMAL.value
        config["upper_value"] = 100.0
        config["lower_value"] = 0.0
        config["set_channel"] = ""
        config["reset_channel"] = ""
        config["default_state"] = LogicDefaultState.OFF.value
        config["edge"] = EdgeType.RISING.value
        config["toggle_channel"] = ""
        config["pulse_count"] = 1
        config["retrigger"] = False
        config["time_off_s"] = 0.5

        # Fill specific fields based on operation
        if page_index == 0:  # Is True / Is False
            config["channel"] = self.is_tf_channel_edit.text().strip()
            config["true_delay_s"] = self.is_tf_true_delay.value()
            config["false_delay_s"] = self.is_tf_false_delay.value()

        elif page_index == 1:  # Comparison
            config["channel"] = self.cmp_channel_edit.text().strip()
            config["constant"] = self.cmp_constant.value()
            config["true_delay_s"] = self.cmp_true_delay.value()
            config["false_delay_s"] = self.cmp_false_delay.value()

        elif page_index == 2:  # And / Or / Xor
            config["channel"] = self.and_or_ch1_edit.text().strip()
            config["channel_2"] = self.and_or_ch2_edit.text().strip()
            config["true_delay_s"] = self.and_or_true_delay.value()
            config["false_delay_s"] = self.and_or_false_delay.value()

        elif page_index == 3:  # Changed
            config["channel"] = self.changed_channel_edit.text().strip()
            config["threshold"] = self.changed_threshold.value()
            config["time_on_s"] = self.changed_time_on.value()

        elif page_index == 4:  # Hysteresis
            config["channel"] = self.hyst_channel_edit.text().strip()
            config["polarity"] = self.hyst_polarity.currentData()
            config["upper_value"] = self.hyst_upper.value()
            config["lower_value"] = self.hyst_lower.value()

        elif page_index == 5:  # Set-Reset Latch
            config["set_channel"] = self.sr_set_edit.text().strip()
            config["reset_channel"] = self.sr_reset_edit.text().strip()
            config["default_state"] = self.sr_default.currentData()

        elif page_index == 6:  # Toggle
            config["edge"] = self.toggle_edge.currentData()
            config["toggle_channel"] = self.toggle_channel_edit.text().strip()
            config["set_channel"] = self.toggle_set_edit.text().strip()
            config["reset_channel"] = self.toggle_reset_edit.text().strip()
            config["default_state"] = self.toggle_default.currentData()

        elif page_index == 7:  # Pulse
            config["edge"] = self.pulse_edge.currentData()
            config["channel"] = self.pulse_channel_edit.text().strip()
            config["pulse_count"] = self.pulse_count.value()
            config["time_on_s"] = self.pulse_time_on.value()
            config["retrigger"] = self.pulse_retrigger.isChecked()

        elif page_index == 8:  # Flash
            config["channel"] = self.flash_channel_edit.text().strip()
            config["time_on_s"] = self.flash_time_on.value()
            config["time_off_s"] = self.flash_time_off.value()

        return config

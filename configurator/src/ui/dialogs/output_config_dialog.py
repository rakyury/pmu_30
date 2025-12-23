"""
Output Channel Configuration Dialog
Configures one of 30 high-side switch outputs
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional
from .channel_selector_dialog import ChannelSelectorDialog


class OutputConfigDialog(QDialog):
    """Dialog for configuring a single high-side output channel."""

    def __init__(self, parent=None, output_config: Optional[Dict[str, Any]] = None, used_channels=None, available_channels=None):
        super().__init__(parent)
        self.output_config = output_config
        self.used_channels = used_channels or []
        self.available_channels = available_channels or {}  # Dict of all available channels/functions

        self.setWindowTitle("Output Channel Configuration")
        self.setModal(True)
        self.resize(600, 480)

        self._init_ui()

        if output_config:
            self._load_config(output_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Fuel Pump, Starter, Headlights")
        basic_layout.addRow("Name: *", self.name_edit)

        # Pin selection - up to 3 pins for increased current capacity
        pin_selection_layout = QVBoxLayout()
        pin_selection_layout.addWidget(QLabel("Pins (select 1-3 for higher current):"))

        pins_layout = QHBoxLayout()
        self.pin1_combo = QComboBox()
        self.pin1_combo.setToolTip("Primary output pin (O1-O30)")
        self._populate_available_pins(self.pin1_combo)
        pins_layout.addWidget(QLabel("Pin 1:"))
        pins_layout.addWidget(self.pin1_combo)

        self.pin2_combo = QComboBox()
        self.pin2_combo.setToolTip("Optional second pin for higher current")
        self._populate_available_pins(self.pin2_combo, include_none=True)
        pins_layout.addWidget(QLabel("Pin 2:"))
        pins_layout.addWidget(self.pin2_combo)

        self.pin3_combo = QComboBox()
        self.pin3_combo.setToolTip("Optional third pin for maximum current")
        self._populate_available_pins(self.pin3_combo, include_none=True)
        pins_layout.addWidget(QLabel("Pin 3:"))
        pins_layout.addWidget(self.pin3_combo)

        pin_selection_layout.addLayout(pins_layout)
        basic_layout.addRow("", pin_selection_layout)

        # On/Off enable checkbox
        self.enabled_check = QCheckBox("On/Off")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("", self.enabled_check)

        # Function control (always visible)
        control_function_layout = QHBoxLayout()
        self.control_function_edit = QLineEdit()
        self.control_function_edit.setPlaceholderText("Select function/channel...")
        self.control_function_edit.setReadOnly(True)
        self.control_function_edit.textChanged.connect(self._on_control_function_changed)
        control_function_layout.addWidget(self.control_function_edit, stretch=1)

        self.control_function_btn = QPushButton("Browse...")
        self.control_function_btn.clicked.connect(self._browse_control_function)
        control_function_layout.addWidget(self.control_function_btn)

        basic_layout.addRow("Control Function:", control_function_layout)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Current protection group - organized in 2 columns
        protection_group = QGroupBox("Current Protection")
        protection_layout = QGridLayout()

        # Row 0: Current Limit | Inrush Current
        protection_layout.addWidget(QLabel("Current Limit:"), 0, 0)
        self.current_limit_spin = QDoubleSpinBox()
        self.current_limit_spin.setRange(0.1, 50.0)
        self.current_limit_spin.setValue(10.0)
        self.current_limit_spin.setSuffix(" A")
        self.current_limit_spin.setDecimals(1)
        self.current_limit_spin.setSingleStep(0.5)
        self.current_limit_spin.setToolTip("Overcurrent shutdown threshold (0.1-50A)")
        protection_layout.addWidget(self.current_limit_spin, 0, 1)

        protection_layout.addWidget(QLabel("Inrush Current:"), 0, 2)
        self.inrush_current_spin = QDoubleSpinBox()
        self.inrush_current_spin.setRange(0.1, 100.0)
        self.inrush_current_spin.setValue(20.0)
        self.inrush_current_spin.setSuffix(" A")
        self.inrush_current_spin.setDecimals(1)
        self.inrush_current_spin.setSingleStep(1.0)
        self.inrush_current_spin.setToolTip("Peak current allowed during startup")
        protection_layout.addWidget(self.inrush_current_spin, 0, 3)

        # Row 1: Inrush Time | Retry Count
        protection_layout.addWidget(QLabel("Inrush Time:"), 1, 0)
        self.inrush_time_spin = QSpinBox()
        self.inrush_time_spin.setRange(10, 5000)
        self.inrush_time_spin.setValue(500)
        self.inrush_time_spin.setSuffix(" ms")
        self.inrush_time_spin.setToolTip("Time to allow inrush current")
        protection_layout.addWidget(self.inrush_time_spin, 1, 1)

        protection_layout.addWidget(QLabel("Retry Count:"), 1, 2)
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(3)
        self.retry_count_spin.setToolTip("Auto-retry attempts after fault (0 = disabled)")
        protection_layout.addWidget(self.retry_count_spin, 1, 3)

        # Row 2: Retry forever | Retry Delay
        self.retry_forever_check = QCheckBox("Retry forever")
        self.retry_forever_check.toggled.connect(self._on_retry_forever_toggled)
        protection_layout.addWidget(self.retry_forever_check, 2, 0, 1, 2)

        protection_layout.addWidget(QLabel("Retry Delay:"), 2, 2)
        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(100, 10000)
        self.retry_delay_spin.setValue(1000)
        self.retry_delay_spin.setSuffix(" ms")
        self.retry_delay_spin.setToolTip("Delay between retry attempts")
        protection_layout.addWidget(self.retry_delay_spin, 2, 3)

        protection_group.setLayout(protection_layout)
        layout.addWidget(protection_group)

        # PWM settings group - organized in 2 columns
        pwm_group = QGroupBox("PWM Settings")
        pwm_layout = QGridLayout()

        # Row 0: Enable PWM checkbox (full width)
        self.pwm_enabled_check = QCheckBox("Enable PWM Control")
        self.pwm_enabled_check.toggled.connect(self._on_pwm_toggled)
        pwm_layout.addWidget(self.pwm_enabled_check, 0, 0, 1, 4)

        # Row 1: PWM Frequency | Duty Value
        pwm_layout.addWidget(QLabel("PWM Frequency:"), 1, 0)
        self.pwm_freq_spin = QSpinBox()
        self.pwm_freq_spin.setRange(100, 20000)
        self.pwm_freq_spin.setValue(1000)
        self.pwm_freq_spin.setSuffix(" Hz")
        self.pwm_freq_spin.setToolTip("PWM frequency (100-20000 Hz)")
        pwm_layout.addWidget(self.pwm_freq_spin, 1, 1)

        pwm_layout.addWidget(QLabel("Duty Value:"), 1, 2)
        self.pwm_duty_spin = QDoubleSpinBox()
        self.pwm_duty_spin.setRange(0.0, 100.0)
        self.pwm_duty_spin.setValue(50.0)
        self.pwm_duty_spin.setSuffix(" %")
        self.pwm_duty_spin.setDecimals(1)
        self.pwm_duty_spin.setSingleStep(5.0)
        self.pwm_duty_spin.setToolTip("Fixed PWM duty cycle (0-100%)")
        pwm_layout.addWidget(self.pwm_duty_spin, 1, 3)

        # Row 2: Duty Function (full width)
        pwm_layout.addWidget(QLabel("Duty Function:"), 2, 0)
        duty_function_layout = QHBoxLayout()
        self.duty_function_edit = QLineEdit()
        self.duty_function_edit.setPlaceholderText("Select channel/function for duty...")
        self.duty_function_edit.setReadOnly(True)
        duty_function_layout.addWidget(self.duty_function_edit, stretch=1)

        self.duty_function_btn = QPushButton("Browse...")
        self.duty_function_btn.clicked.connect(self._browse_duty_function)
        duty_function_layout.addWidget(self.duty_function_btn)
        pwm_layout.addLayout(duty_function_layout, 2, 1, 1, 3)

        # Row 3: Enable Soft Start | Soft Start Duration
        self.soft_start_check = QCheckBox("Enable Soft Start")
        self.soft_start_check.toggled.connect(self._on_soft_start_toggled)
        pwm_layout.addWidget(self.soft_start_check, 3, 0, 1, 2)

        pwm_layout.addWidget(QLabel("Soft Start Duration:"), 3, 2)
        self.soft_start_duration_spin = QSpinBox()
        self.soft_start_duration_spin.setRange(10, 10000)
        self.soft_start_duration_spin.setValue(1000)
        self.soft_start_duration_spin.setSuffix(" ms")
        self.soft_start_duration_spin.setToolTip("Soft start ramp duration")
        pwm_layout.addWidget(self.soft_start_duration_spin, 3, 3)

        pwm_group.setLayout(pwm_layout)
        layout.addWidget(pwm_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize controls state
        self._on_pwm_toggled(False)
        self._on_soft_start_toggled(False)
        self._on_retry_forever_toggled(False)

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        # Validate that at least one pin is selected
        pin1 = self.pin1_combo.currentData()
        if pin1 is None or pin1 < 0:
            QMessageBox.warning(self, "Validation Error", "At least Pin 1 must be selected!")
            self.pin1_combo.setFocus()
            return

        # Validate no duplicate pins
        pins = []
        if pin1 is not None and pin1 >= 0:
            pins.append(pin1)

        pin2 = self.pin2_combo.currentData()
        if pin2 is not None and pin2 >= 0:
            if pin2 in pins:
                QMessageBox.warning(self, "Validation Error", "Pin 2 cannot be the same as Pin 1!")
                self.pin2_combo.setFocus()
                return
            pins.append(pin2)

        pin3 = self.pin3_combo.currentData()
        if pin3 is not None and pin3 >= 0:
            if pin3 in pins:
                QMessageBox.warning(self, "Validation Error", "Pin 3 cannot be the same as Pin 1 or Pin 2!")
                self.pin3_combo.setFocus()
                return

        self.accept()

    def _populate_available_pins(self, combo: QComboBox, include_none: bool = False):
        """Populate pin dropdown with available pins."""
        combo.clear()

        # Add "None" option for optional pins
        if include_none:
            combo.addItem("None", -1)

        # Get currently used pins if editing
        current_pins = []
        if self.output_config:
            current_pins = self.output_config.get("pins", [])

        # Add available pins (O1-O30)
        for pin in range(30):
            if pin not in self.used_channels or pin in current_pins:
                combo.addItem(f"O{pin + 1}", pin)

        # If no pins available and not optional, add a placeholder
        if combo.count() == 0 and not include_none:
            combo.addItem("No pins available", -1)

    def _on_control_function_changed(self, text: str):
        """Handle control function change - disable checkbox if function is set."""
        has_function = bool(text.strip())
        self.enabled_check.setEnabled(not has_function)
        if has_function:
            self.enabled_check.setChecked(False)

    def _on_retry_forever_toggled(self, enabled: bool):
        """Handle retry forever enable/disable."""
        self.retry_count_spin.setEnabled(not enabled)

    def _on_soft_start_toggled(self, enabled: bool):
        """Handle soft start enable/disable."""
        self.soft_start_duration_spin.setEnabled(enabled)

    def _on_pwm_toggled(self, enabled: bool):
        """Handle PWM enable/disable."""
        self.pwm_freq_spin.setEnabled(enabled)
        self.pwm_duty_spin.setEnabled(enabled)
        self.duty_function_edit.setEnabled(enabled)
        self.duty_function_btn.setEnabled(enabled)
        self.soft_start_check.setEnabled(enabled)
        self.soft_start_duration_spin.setEnabled(enabled and self.soft_start_check.isChecked())

    def _browse_control_function(self):
        """Browse and select control function channel."""
        current = self.control_function_edit.text()
        channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if channel:
            self.control_function_edit.setText(channel)

    def _browse_duty_function(self):
        """Browse and select duty function channel."""
        current = self.duty_function_edit.text()
        channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if channel:
            self.duty_function_edit.setText(channel)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))

        # Load pins (up to 3)
        pins = config.get("pins", [])
        if len(pins) > 0:
            index = self.pin1_combo.findData(pins[0])
            if index >= 0:
                self.pin1_combo.setCurrentIndex(index)
        if len(pins) > 1:
            index = self.pin2_combo.findData(pins[1])
            if index >= 0:
                self.pin2_combo.setCurrentIndex(index)
        if len(pins) > 2:
            index = self.pin3_combo.findData(pins[2])
            if index >= 0:
                self.pin3_combo.setCurrentIndex(index)

        # Control settings
        self.control_function_edit.setText(config.get("control_function", ""))
        self.enabled_check.setChecked(config.get("enabled", True))

        # Protection settings
        protection = config.get("protection", {})
        self.current_limit_spin.setValue(protection.get("current_limit", 10.0))
        self.inrush_current_spin.setValue(protection.get("inrush_current", 20.0))
        self.inrush_time_spin.setValue(protection.get("inrush_time_ms", 500))
        self.retry_count_spin.setValue(protection.get("retry_count", 3))
        self.retry_forever_check.setChecked(protection.get("retry_forever", False))
        self.retry_delay_spin.setValue(protection.get("retry_delay_ms", 1000))

        # PWM settings
        pwm = config.get("pwm", {})
        self.pwm_enabled_check.setChecked(pwm.get("enabled", False))
        self.pwm_freq_spin.setValue(pwm.get("frequency", 1000))

        # Duty settings (both value and function are always available)
        self.pwm_duty_spin.setValue(pwm.get("duty_value", 50.0))
        self.duty_function_edit.setText(pwm.get("duty_function", ""))

        # Soft start
        self.soft_start_check.setChecked(pwm.get("soft_start_enabled", False))
        self.soft_start_duration_spin.setValue(pwm.get("soft_start_duration_ms", 1000))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        import re

        # Collect selected pins (1-3)
        pins = []
        pin1 = self.pin1_combo.currentData()
        if pin1 is not None and pin1 >= 0:
            pins.append(pin1)

        pin2 = self.pin2_combo.currentData()
        if pin2 is not None and pin2 >= 0:
            pins.append(pin2)

        pin3 = self.pin3_combo.currentData()
        if pin3 is not None and pin3 >= 0:
            pins.append(pin3)

        name = self.name_edit.text().strip()

        # Generate ID from name if editing existing config, preserve original id
        # Otherwise create id from name (lowercase, replace spaces with underscores)
        if self.output_config and self.output_config.get("id"):
            channel_id = self.output_config.get("id")
        else:
            # Convert name to valid id: lowercase, alphanumeric and underscores only
            channel_id = re.sub(r'[^a-z0-9_]', '_', name.lower())
            channel_id = re.sub(r'_+', '_', channel_id).strip('_')
            if not channel_id:
                channel_id = f"out_{pins[0] if pins else 0}"

        config = {
            "id": channel_id,
            "pins": pins,
            "name": name,
            "enabled": self.enabled_check.isChecked(),
            "control_function": self.control_function_edit.text(),
            "protection": {
                "current_limit": self.current_limit_spin.value(),
                "inrush_current": self.inrush_current_spin.value(),
                "inrush_time_ms": self.inrush_time_spin.value(),
                "retry_count": self.retry_count_spin.value(),
                "retry_forever": self.retry_forever_check.isChecked(),
                "retry_delay_ms": self.retry_delay_spin.value()
            },
            "pwm": {
                "enabled": self.pwm_enabled_check.isChecked(),
                "frequency": self.pwm_freq_spin.value(),
                "duty_value": self.pwm_duty_spin.value(),
                "duty_function": self.duty_function_edit.text(),
                "soft_start_enabled": self.soft_start_check.isChecked(),
                "soft_start_duration_ms": self.soft_start_duration_spin.value()
            }
        }

        return config

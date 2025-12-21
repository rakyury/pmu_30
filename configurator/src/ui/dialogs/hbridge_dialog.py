"""
H-Bridge Configuration Dialog
Configures a single H-Bridge channel for DC motor control
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class HBridgeDialog(QDialog):
    """Dialog for configuring a single H-Bridge channel."""

    MODES = [
        "Disabled",
        "Forward Only",
        "Reverse Only",
        "Bidirectional"
    ]

    CONTROL_MODES = [
        "PWM (0-100%)",
        "On/Off"
    ]

    INPUT_TYPES = [
        "Physical Input (0-19)",
        "Virtual Channel (0-255)",
        "CAN Signal",
        "Manual Control"
    ]

    PWM_FREQUENCIES = ["100 Hz", "500 Hz", "1 kHz", "5 kHz", "10 kHz", "20 kHz"]

    def __init__(self, parent=None, channel: int = 0, config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.channel = channel
        self.config = config

        self.setWindowTitle(f"H-Bridge {channel} Configuration")
        self.setModal(True)
        self.resize(550, 600)

        self._init_ui()

        if config:
            self._load_config(config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(f"e.g., Cooling Fan, Wiper Motor")
        basic_layout.addRow("Name: *", self.name_edit)

        self.enabled_check = QCheckBox("H-Bridge Enabled")
        self.enabled_check.setChecked(True)
        self.enabled_check.toggled.connect(self._on_enabled_changed)
        basic_layout.addRow("", self.enabled_check)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.MODES)
        self.mode_combo.setCurrentIndex(3)  # Bidirectional
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        basic_layout.addRow("Operating Mode:", self.mode_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Control settings
        control_group = QGroupBox("Control Settings")
        control_layout = QFormLayout()

        self.control_mode_combo = QComboBox()
        self.control_mode_combo.addItems(self.CONTROL_MODES)
        control_layout.addRow("Control Mode:", self.control_mode_combo)

        # Forward control
        self.forward_input_type = QComboBox()
        self.forward_input_type.addItems(self.INPUT_TYPES)
        control_layout.addRow("Forward Input Type:", self.forward_input_type)

        self.forward_channel_spin = QSpinBox()
        self.forward_channel_spin.setRange(0, 255)
        self.forward_channel_spin.setToolTip("Input channel for forward control")
        control_layout.addRow("Forward Channel:", self.forward_channel_spin)

        # Reverse control
        self.reverse_input_type = QComboBox()
        self.reverse_input_type.addItems(self.INPUT_TYPES)
        control_layout.addRow("Reverse Input Type:", self.reverse_input_type)

        self.reverse_channel_spin = QSpinBox()
        self.reverse_channel_spin.setRange(0, 255)
        self.reverse_channel_spin.setToolTip("Input channel for reverse control")
        control_layout.addRow("Reverse Channel:", self.reverse_channel_spin)

        # Speed control for PWM mode
        self.speed_input_type = QComboBox()
        self.speed_input_type.addItems(self.INPUT_TYPES)
        control_layout.addRow("Speed Input Type:", self.speed_input_type)

        self.speed_channel_spin = QSpinBox()
        self.speed_channel_spin.setRange(0, 255)
        self.speed_channel_spin.setToolTip("Input channel for speed control (0-100%)")
        control_layout.addRow("Speed Channel:", self.speed_channel_spin)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # PWM settings
        pwm_group = QGroupBox("PWM Settings")
        pwm_layout = QFormLayout()

        self.pwm_freq_combo = QComboBox()
        self.pwm_freq_combo.addItems(self.PWM_FREQUENCIES)
        self.pwm_freq_combo.setCurrentIndex(3)  # 5 kHz default
        pwm_layout.addRow("PWM Frequency:", self.pwm_freq_combo)

        self.min_duty_spin = QSpinBox()
        self.min_duty_spin.setRange(0, 100)
        self.min_duty_spin.setValue(10)
        self.min_duty_spin.setSuffix(" %")
        self.min_duty_spin.setToolTip("Minimum duty cycle (deadband)")
        pwm_layout.addRow("Min Duty Cycle:", self.min_duty_spin)

        self.max_duty_spin = QSpinBox()
        self.max_duty_spin.setRange(0, 100)
        self.max_duty_spin.setValue(100)
        self.max_duty_spin.setSuffix(" %")
        pwm_layout.addRow("Max Duty Cycle:", self.max_duty_spin)

        pwm_group.setLayout(pwm_layout)
        layout.addWidget(pwm_group)

        # Protection settings
        protection_group = QGroupBox("Protection Settings")
        protection_layout = QFormLayout()

        self.current_limit_spin = QDoubleSpinBox()
        self.current_limit_spin.setRange(0.1, 50.0)
        self.current_limit_spin.setValue(10.0)
        self.current_limit_spin.setSingleStep(0.5)
        self.current_limit_spin.setDecimals(1)
        self.current_limit_spin.setSuffix(" A")
        self.current_limit_spin.setToolTip("Maximum current per channel")
        protection_layout.addRow("Current Limit:", self.current_limit_spin)

        self.thermal_protection_check = QCheckBox("Enable Thermal Protection")
        self.thermal_protection_check.setChecked(True)
        protection_layout.addRow("", self.thermal_protection_check)

        self.overcurrent_action_combo = QComboBox()
        self.overcurrent_action_combo.addItems(["Disable Output", "Reduce Power", "Log Only"])
        self.overcurrent_action_combo.setCurrentIndex(0)
        protection_layout.addRow("Overcurrent Action:", self.overcurrent_action_combo)

        protection_group.setLayout(protection_layout)
        layout.addWidget(protection_group)

        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout()

        self.soft_start_spin = QSpinBox()
        self.soft_start_spin.setRange(0, 5000)
        self.soft_start_spin.setValue(100)
        self.soft_start_spin.setSuffix(" ms")
        self.soft_start_spin.setToolTip("Soft start ramp time")
        advanced_layout.addRow("Soft Start Time:", self.soft_start_spin)

        self.soft_stop_spin = QSpinBox()
        self.soft_stop_spin.setRange(0, 5000)
        self.soft_stop_spin.setValue(100)
        self.soft_stop_spin.setSuffix(" ms")
        self.soft_stop_spin.setToolTip("Soft stop ramp time")
        advanced_layout.addRow("Soft Stop Time:", self.soft_stop_spin)

        self.brake_check = QCheckBox("Enable Active Braking")
        self.brake_check.setChecked(False)
        self.brake_check.setToolTip("Short both outputs to brake the motor")
        advanced_layout.addRow("", self.brake_check)

        self.invert_check = QCheckBox("Invert Direction")
        self.invert_check.setChecked(False)
        advanced_layout.addRow("", self.invert_check)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

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

        # Initialize state
        self._on_mode_changed(self.mode_combo.currentText())

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _on_enabled_changed(self, enabled: bool):
        """Handle enabled state change."""
        # Enable/disable all controls based on enabled state
        pass

    def _on_mode_changed(self, mode: str):
        """Update UI based on operating mode."""
        is_bidirectional = mode == "Bidirectional"
        is_forward_only = mode == "Forward Only"
        is_reverse_only = mode == "Reverse Only"

        # Enable/disable reverse controls based on mode
        self.reverse_input_type.setEnabled(is_bidirectional or is_reverse_only)
        self.reverse_channel_spin.setEnabled(is_bidirectional or is_reverse_only)

        # Enable/disable forward controls
        self.forward_input_type.setEnabled(mode != "Disabled")
        self.forward_channel_spin.setEnabled(mode != "Disabled")

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))
        self.enabled_check.setChecked(config.get("enabled", True))

        mode = config.get("mode", "Bidirectional")
        index = self.mode_combo.findText(mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)

        control = config.get("control", {})
        control_mode = control.get("mode", "PWM (0-100%)")
        index = self.control_mode_combo.findText(control_mode)
        if index >= 0:
            self.control_mode_combo.setCurrentIndex(index)

        # Forward control
        forward = control.get("forward", {})
        fwd_type = forward.get("type", "Physical Input (0-19)")
        index = self.forward_input_type.findText(fwd_type)
        if index >= 0:
            self.forward_input_type.setCurrentIndex(index)
        self.forward_channel_spin.setValue(forward.get("channel", 0))

        # Reverse control
        reverse = control.get("reverse", {})
        rev_type = reverse.get("type", "Physical Input (0-19)")
        index = self.reverse_input_type.findText(rev_type)
        if index >= 0:
            self.reverse_input_type.setCurrentIndex(index)
        self.reverse_channel_spin.setValue(reverse.get("channel", 1))

        # Speed control
        speed = control.get("speed", {})
        speed_type = speed.get("type", "Physical Input (0-19)")
        index = self.speed_input_type.findText(speed_type)
        if index >= 0:
            self.speed_input_type.setCurrentIndex(index)
        self.speed_channel_spin.setValue(speed.get("channel", 2))

        # PWM settings
        pwm = config.get("pwm", {})
        pwm_freq = pwm.get("frequency", "5 kHz")
        index = self.pwm_freq_combo.findText(pwm_freq)
        if index >= 0:
            self.pwm_freq_combo.setCurrentIndex(index)
        self.min_duty_spin.setValue(pwm.get("min_duty", 10))
        self.max_duty_spin.setValue(pwm.get("max_duty", 100))

        # Protection
        protection = config.get("protection", {})
        self.current_limit_spin.setValue(protection.get("current_limit_a", 10.0))
        self.thermal_protection_check.setChecked(protection.get("thermal_protection", True))

        overcurrent_action = protection.get("overcurrent_action", "Disable Output")
        index = self.overcurrent_action_combo.findText(overcurrent_action)
        if index >= 0:
            self.overcurrent_action_combo.setCurrentIndex(index)

        # Advanced
        advanced = config.get("advanced", {})
        self.soft_start_spin.setValue(advanced.get("soft_start_ms", 100))
        self.soft_stop_spin.setValue(advanced.get("soft_stop_ms", 100))
        self.brake_check.setChecked(advanced.get("active_braking", False))
        self.invert_check.setChecked(advanced.get("invert_direction", False))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        config = {
            "name": self.name_edit.text(),
            "enabled": self.enabled_check.isChecked(),
            "mode": self.mode_combo.currentText(),
            "control": {
                "mode": self.control_mode_combo.currentText(),
                "forward": {
                    "type": self.forward_input_type.currentText(),
                    "channel": self.forward_channel_spin.value()
                },
                "reverse": {
                    "type": self.reverse_input_type.currentText(),
                    "channel": self.reverse_channel_spin.value()
                },
                "speed": {
                    "type": self.speed_input_type.currentText(),
                    "channel": self.speed_channel_spin.value()
                }
            },
            "pwm": {
                "frequency": self.pwm_freq_combo.currentText(),
                "min_duty": self.min_duty_spin.value(),
                "max_duty": self.max_duty_spin.value()
            },
            "protection": {
                "current_limit_a": self.current_limit_spin.value(),
                "thermal_protection": self.thermal_protection_check.isChecked(),
                "overcurrent_action": self.overcurrent_action_combo.currentText()
            },
            "advanced": {
                "soft_start_ms": self.soft_start_spin.value(),
                "soft_stop_ms": self.soft_stop_spin.value(),
                "active_braking": self.brake_check.isChecked(),
                "invert_direction": self.invert_check.isChecked()
            }
        }

        return config

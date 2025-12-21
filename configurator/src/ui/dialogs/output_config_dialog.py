"""
Output Channel Configuration Dialog
Configures one of 30 high-side switch outputs
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class OutputConfigDialog(QDialog):
    """Dialog for configuring a single high-side output channel."""

    def __init__(self, parent=None, output_config: Optional[Dict[str, Any]] = None, used_channels=None, available_channels=None):
        super().__init__(parent)
        self.output_config = output_config
        self.used_channels = used_channels or []
        self.available_channels = available_channels or []  # List of all available channels/functions

        self.setWindowTitle("Output Channel Configuration")
        self.setModal(True)
        self.resize(500, 650)

        self._init_ui()

        if output_config:
            self._load_config(output_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        # Channel selection - dropdown with available channels only
        self.channel_combo = QComboBox()
        self.channel_combo.setToolTip("Physical output channel (0-29)")
        self._populate_available_channels()
        basic_layout.addRow("Channel:", self.channel_combo)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Fuel Pump, Starter, Headlights")
        basic_layout.addRow("Name:", self.name_edit)

        # Control mode selection
        self.control_mode_combo = QComboBox()
        self.control_mode_combo.addItems(["Manual (Checkbox)", "Controlled by Function"])
        self.control_mode_combo.currentTextChanged.connect(self._on_control_mode_changed)
        basic_layout.addRow("Control Mode:", self.control_mode_combo)

        # Manual enable checkbox
        self.enabled_check = QCheckBox("Output Enabled")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("", self.enabled_check)

        # Function control
        self.control_function_combo = QComboBox()
        self.control_function_combo.setEditable(True)
        self.control_function_combo.addItems(self.available_channels)
        self.control_function_combo.setPlaceholderText("Select function/channel...")
        basic_layout.addRow("Control Function:", self.control_function_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Current protection group
        protection_group = QGroupBox("Current Protection")
        protection_layout = QFormLayout()

        self.current_limit_spin = QDoubleSpinBox()
        self.current_limit_spin.setRange(0.1, 50.0)
        self.current_limit_spin.setValue(10.0)
        self.current_limit_spin.setSuffix(" A")
        self.current_limit_spin.setDecimals(1)
        self.current_limit_spin.setSingleStep(0.5)
        self.current_limit_spin.setToolTip("Overcurrent shutdown threshold (0.1-50A)")
        protection_layout.addRow("Current Limit:", self.current_limit_spin)

        self.inrush_current_spin = QDoubleSpinBox()
        self.inrush_current_spin.setRange(0.1, 100.0)
        self.inrush_current_spin.setValue(20.0)
        self.inrush_current_spin.setSuffix(" A")
        self.inrush_current_spin.setDecimals(1)
        self.inrush_current_spin.setSingleStep(1.0)
        self.inrush_current_spin.setToolTip("Peak current allowed during startup")
        protection_layout.addRow("Inrush Current:", self.inrush_current_spin)

        self.inrush_time_spin = QSpinBox()
        self.inrush_time_spin.setRange(10, 5000)
        self.inrush_time_spin.setValue(500)
        self.inrush_time_spin.setSuffix(" ms")
        self.inrush_time_spin.setToolTip("Time to allow inrush current")
        protection_layout.addRow("Inrush Time:", self.inrush_time_spin)

        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(3)
        self.retry_count_spin.setToolTip("Auto-retry attempts after fault (0 = disabled)")
        protection_layout.addRow("Retry Count:", self.retry_count_spin)

        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(100, 10000)
        self.retry_delay_spin.setValue(1000)
        self.retry_delay_spin.setSuffix(" ms")
        self.retry_delay_spin.setToolTip("Delay between retry attempts")
        protection_layout.addRow("Retry Delay:", self.retry_delay_spin)

        protection_group.setLayout(protection_layout)
        layout.addWidget(protection_group)

        # PWM settings group
        pwm_group = QGroupBox("PWM Settings")
        pwm_layout = QFormLayout()

        self.pwm_enabled_check = QCheckBox("Enable PWM Control")
        pwm_layout.addRow("", self.pwm_enabled_check)
        self.pwm_enabled_check.toggled.connect(self._on_pwm_toggled)

        self.pwm_freq_spin = QSpinBox()
        self.pwm_freq_spin.setRange(100, 20000)
        self.pwm_freq_spin.setValue(1000)
        self.pwm_freq_spin.setSuffix(" Hz")
        self.pwm_freq_spin.setToolTip("PWM frequency (100-20000 Hz)")
        pwm_layout.addRow("PWM Frequency:", self.pwm_freq_spin)

        self.pwm_duty_spin = QDoubleSpinBox()
        self.pwm_duty_spin.setRange(0.0, 100.0)
        self.pwm_duty_spin.setValue(50.0)
        self.pwm_duty_spin.setSuffix(" %")
        self.pwm_duty_spin.setDecimals(1)
        self.pwm_duty_spin.setSingleStep(5.0)
        self.pwm_duty_spin.setToolTip("Default PWM duty cycle (0-100%)")
        pwm_layout.addRow("Default Duty:", self.pwm_duty_spin)

        pwm_group.setLayout(pwm_layout)
        layout.addWidget(pwm_group)

        # Advanced settings group
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout()

        self.diagnostic_check = QCheckBox("Enable Diagnostics")
        self.diagnostic_check.setChecked(True)
        self.diagnostic_check.setToolTip("Monitor current, faults, and open load")
        advanced_layout.addRow("", self.diagnostic_check)

        self.open_load_check = QCheckBox("Detect Open Load")
        self.open_load_check.setChecked(True)
        self.open_load_check.setToolTip("Detect disconnected or missing load")
        advanced_layout.addRow("", self.open_load_check)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize PWM controls state
        self._on_pwm_toggled(False)

    def _populate_available_channels(self):
        """Populate channel dropdown with available channels."""
        self.channel_combo.clear()

        # Get current channel if editing
        current_channel = None
        if self.output_config:
            current_channel = self.output_config.get("channel")

        # Add available channels (0-29)
        for ch in range(30):
            if ch not in self.used_channels or ch == current_channel:
                self.channel_combo.addItem(f"Channel {ch}", ch)

        # If no channels available, add a placeholder
        if self.channel_combo.count() == 0:
            self.channel_combo.addItem("No channels available", -1)

    def _on_pwm_toggled(self, enabled: bool):
        """Handle PWM enable/disable."""
        self.pwm_freq_spin.setEnabled(enabled)
        self.pwm_duty_spin.setEnabled(enabled)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        # Find and select the channel in combo box
        channel = config.get("channel", 0)
        index = self.channel_combo.findData(channel)
        if index >= 0:
            self.channel_combo.setCurrentIndex(index)
        self.name_edit.setText(config.get("name", ""))
        self.enabled_check.setChecked(config.get("enabled", True))

        # Protection settings
        protection = config.get("protection", {})
        self.current_limit_spin.setValue(protection.get("current_limit", 10.0))
        self.inrush_current_spin.setValue(protection.get("inrush_current", 20.0))
        self.inrush_time_spin.setValue(protection.get("inrush_time_ms", 500))
        self.retry_count_spin.setValue(protection.get("retry_count", 3))
        self.retry_delay_spin.setValue(protection.get("retry_delay_ms", 1000))

        # PWM settings
        pwm = config.get("pwm", {})
        self.pwm_enabled_check.setChecked(pwm.get("enabled", False))
        self.pwm_freq_spin.setValue(pwm.get("frequency", 1000))
        self.pwm_duty_spin.setValue(pwm.get("default_duty", 50.0))

        # Advanced settings
        advanced = config.get("advanced", {})
        self.diagnostic_check.setChecked(advanced.get("diagnostics", True))
        self.open_load_check.setChecked(advanced.get("open_load_detection", True))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        config = {
            "channel": self.channel_combo.currentData(),
            "name": self.name_edit.text(),
            "enabled": self.enabled_check.isChecked(),
            "protection": {
                "current_limit": self.current_limit_spin.value(),
                "inrush_current": self.inrush_current_spin.value(),
                "inrush_time_ms": self.inrush_time_spin.value(),
                "retry_count": self.retry_count_spin.value(),
                "retry_delay_ms": self.retry_delay_spin.value()
            },
            "pwm": {
                "enabled": self.pwm_enabled_check.isChecked(),
                "frequency": self.pwm_freq_spin.value(),
                "default_duty": self.pwm_duty_spin.value()
            },
            "advanced": {
                "diagnostics": self.diagnostic_check.isChecked(),
                "open_load_detection": self.open_load_check.isChecked()
            }
        }

        return config

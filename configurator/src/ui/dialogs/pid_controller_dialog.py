"""
PID Controller Configuration Dialog
Configures a single PID controller for the PMU-30
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QDoubleSpinBox, QCheckBox, QLabel
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class PIDControllerDialog(QDialog):
    """Dialog for configuring a single PID controller."""

    INPUT_SOURCES = ["Physical Input (0-19)", "Virtual Channel (0-255)"]
    OUTPUT_TARGETS = ["Physical Output (0-29)", "Virtual Channel (0-255)"]

    def __init__(self, parent=None, pid_config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.pid_config = pid_config

        self.setWindowTitle("PID Controller Configuration")
        self.setModal(True)
        self.resize(500, 550)

        self._init_ui()

        if pid_config:
            self._load_config(pid_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Temperature Control, Speed Regulation")
        basic_layout.addRow("Name: *", self.name_edit)

        self.enabled_check = QCheckBox("Controller Enabled")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("", self.enabled_check)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Input/Output configuration
        io_group = QGroupBox("Input/Output")
        io_layout = QFormLayout()

        # Input source
        input_layout = QHBoxLayout()
        self.input_type_combo = QComboBox()
        self.input_type_combo.addItems(self.INPUT_SOURCES)
        input_layout.addWidget(self.input_type_combo)

        self.input_channel_spin = QDoubleSpinBox()
        self.input_channel_spin.setRange(0, 255)
        self.input_channel_spin.setDecimals(0)
        self.input_channel_spin.setToolTip("Input channel number")
        input_layout.addWidget(self.input_channel_spin)

        io_layout.addRow("Input Source:", input_layout)

        # Output target
        output_layout = QHBoxLayout()
        self.output_type_combo = QComboBox()
        self.output_type_combo.addItems(self.OUTPUT_TARGETS)
        output_layout.addWidget(self.output_type_combo)

        self.output_channel_spin = QDoubleSpinBox()
        self.output_channel_spin.setRange(0, 255)
        self.output_channel_spin.setDecimals(0)
        self.output_channel_spin.setToolTip("Output channel number")
        output_layout.addWidget(self.output_channel_spin)

        io_layout.addRow("Output Target:", output_layout)

        io_group.setLayout(io_layout)
        layout.addWidget(io_group)

        # PID Parameters
        pid_group = QGroupBox("PID Parameters")
        pid_layout = QFormLayout()

        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(-1000.0, 1000.0)
        self.kp_spin.setValue(1.0)
        self.kp_spin.setDecimals(3)
        self.kp_spin.setSingleStep(0.1)
        self.kp_spin.setToolTip("Proportional gain")
        pid_layout.addRow("Kp (Proportional):", self.kp_spin)

        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(-1000.0, 1000.0)
        self.ki_spin.setValue(0.0)
        self.ki_spin.setDecimals(3)
        self.ki_spin.setSingleStep(0.01)
        self.ki_spin.setToolTip("Integral gain")
        pid_layout.addRow("Ki (Integral):", self.ki_spin)

        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(-1000.0, 1000.0)
        self.kd_spin.setValue(0.0)
        self.kd_spin.setDecimals(3)
        self.kd_spin.setSingleStep(0.01)
        self.kd_spin.setToolTip("Derivative gain")
        pid_layout.addRow("Kd (Derivative):", self.kd_spin)

        pid_group.setLayout(pid_layout)
        layout.addWidget(pid_group)

        # Setpoint and limits
        limits_group = QGroupBox("Setpoint and Limits")
        limits_layout = QFormLayout()

        self.setpoint_spin = QDoubleSpinBox()
        self.setpoint_spin.setRange(-10000.0, 10000.0)
        self.setpoint_spin.setValue(0.0)
        self.setpoint_spin.setDecimals(2)
        self.setpoint_spin.setToolTip("Target value (setpoint)")
        limits_layout.addRow("Setpoint:", self.setpoint_spin)

        self.output_min_spin = QDoubleSpinBox()
        self.output_min_spin.setRange(-10000.0, 10000.0)
        self.output_min_spin.setValue(0.0)
        self.output_min_spin.setDecimals(2)
        self.output_min_spin.setToolTip("Minimum output value")
        limits_layout.addRow("Output Min:", self.output_min_spin)

        self.output_max_spin = QDoubleSpinBox()
        self.output_max_spin.setRange(-10000.0, 10000.0)
        self.output_max_spin.setValue(100.0)
        self.output_max_spin.setDecimals(2)
        self.output_max_spin.setToolTip("Maximum output value")
        limits_layout.addRow("Output Max:", self.output_max_spin)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout()

        self.sample_time_spin = QDoubleSpinBox()
        self.sample_time_spin.setRange(1, 10000)
        self.sample_time_spin.setValue(100)
        self.sample_time_spin.setDecimals(0)
        self.sample_time_spin.setSuffix(" ms")
        self.sample_time_spin.setToolTip("PID loop execution period")
        advanced_layout.addRow("Sample Time:", self.sample_time_spin)

        self.anti_windup_check = QCheckBox("Anti-Windup (Integral Clamp)")
        self.anti_windup_check.setChecked(True)
        self.anti_windup_check.setToolTip("Prevent integral term from accumulating excessively")
        advanced_layout.addRow("", self.anti_windup_check)

        self.derivative_filter_check = QCheckBox("Derivative Filter")
        self.derivative_filter_check.setChecked(True)
        self.derivative_filter_check.setToolTip("Apply low-pass filter to derivative term")
        advanced_layout.addRow("", self.derivative_filter_check)

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

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))
        self.enabled_check.setChecked(config.get("enabled", True))

        # Input source
        input_src = config.get("input_source", {})
        input_type = input_src.get("type", "Physical Input")
        if "Physical Input" in input_type:
            self.input_type_combo.setCurrentIndex(0)
        else:
            self.input_type_combo.setCurrentIndex(1)
        self.input_channel_spin.setValue(input_src.get("channel", 0))

        # Output target
        output_tgt = config.get("output_target", {})
        output_type = output_tgt.get("type", "Physical Output")
        if "Physical Output" in output_type:
            self.output_type_combo.setCurrentIndex(0)
        else:
            self.output_type_combo.setCurrentIndex(1)
        self.output_channel_spin.setValue(output_tgt.get("channel", 0))

        # PID parameters
        params = config.get("parameters", {})
        self.kp_spin.setValue(params.get("kp", 1.0))
        self.ki_spin.setValue(params.get("ki", 0.0))
        self.kd_spin.setValue(params.get("kd", 0.0))

        # Setpoint and limits
        self.setpoint_spin.setValue(config.get("setpoint", 0.0))
        self.output_min_spin.setValue(config.get("output_min", 0.0))
        self.output_max_spin.setValue(config.get("output_max", 100.0))

        # Advanced
        advanced = config.get("advanced", {})
        self.sample_time_spin.setValue(advanced.get("sample_time_ms", 100))
        self.anti_windup_check.setChecked(advanced.get("anti_windup", True))
        self.derivative_filter_check.setChecked(advanced.get("derivative_filter", True))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        config = {
            "name": self.name_edit.text(),
            "enabled": self.enabled_check.isChecked(),
            "input_source": {
                "type": self.input_type_combo.currentText(),
                "channel": int(self.input_channel_spin.value())
            },
            "output_target": {
                "type": self.output_type_combo.currentText(),
                "channel": int(self.output_channel_spin.value())
            },
            "parameters": {
                "kp": self.kp_spin.value(),
                "ki": self.ki_spin.value(),
                "kd": self.kd_spin.value()
            },
            "setpoint": self.setpoint_spin.value(),
            "output_min": self.output_min_spin.value(),
            "output_max": self.output_max_spin.value(),
            "advanced": {
                "sample_time_ms": int(self.sample_time_spin.value()),
                "anti_windup": self.anti_windup_check.isChecked(),
                "derivative_filter": self.derivative_filter_check.isChecked()
            }
        }

        return config

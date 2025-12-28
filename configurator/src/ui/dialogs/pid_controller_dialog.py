"""
PID Controller Configuration Dialog
Configures a single PID controller channel for the PMU-30
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QCheckBox, QSpinBox,
    QLineEdit, QWidget, QHBoxLayout, QPushButton, QTabWidget, QVBoxLayout
)
from typing import Dict, Any, Optional, List

from models.channel import ChannelType
from ui.widgets.constant_spinbox import ConstantSpinBox
from .base_channel_dialog import BaseChannelDialog


class PIDControllerDialog(BaseChannelDialog):
    """Dialog for configuring a PID controller channel."""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            parent=parent,
            config=config,
            available_channels=available_channels,
            channel_type=ChannelType.PID,
            existing_channels=existing_channels
        )

        self._init_pid_ui()

        if config:
            self._load_pid_config(config)

        # Finalize UI sizing
        self._finalize_ui()

    def _init_pid_ui(self):
        """Initialize PID-specific UI components with tabs."""
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.content_layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_main_tab()
        self._create_advanced_tab()

    def _create_main_tab(self):
        """Create the main configuration tab."""
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)

        # Input/Output Configuration
        io_group = QGroupBox("Input/Output Configuration")
        io_layout = QFormLayout()

        # Setpoint channel (optional - can use fixed value)
        self.setpoint_container, self.setpoint_edit = self._create_channel_selector(
            "Select channel for dynamic setpoint (optional)..."
        )
        io_layout.addRow("Setpoint Channel:", self.setpoint_container)

        # Fixed setpoint value
        self.setpoint_value_spin = ConstantSpinBox()
        self.setpoint_value_spin.setRange(-100000.0, 100000.0)
        self.setpoint_value_spin.setValue(0.0)
        self.setpoint_value_spin.setToolTip("Fixed setpoint value (used if no setpoint channel)")
        io_layout.addRow("Setpoint Value:", self.setpoint_value_spin)

        # Process variable (feedback) channel - required
        self.process_container, self.process_edit = self._create_channel_selector(
            "Select process variable channel..."
        )
        io_layout.addRow("Process Variable: *", self.process_container)

        # Output channel (optional - the PID output value is available as channel)
        self.output_container, self.output_edit = self._create_channel_selector(
            "Select output target channel (optional)..."
        )
        io_layout.addRow("Output Channel:", self.output_container)

        io_group.setLayout(io_layout)
        main_layout.addWidget(io_group)

        # PID Parameters (2 decimal places)
        pid_group = QGroupBox("PID Parameters")
        pid_layout = QFormLayout()

        self.kp_spin = ConstantSpinBox()
        self.kp_spin.setRange(-10000.0, 10000.0)
        self.kp_spin.setValue(1.0)
        self.kp_spin.setSingleStep(0.1)
        self.kp_spin.setToolTip("Proportional gain - responds to current error")
        pid_layout.addRow("Kp (Proportional):", self.kp_spin)

        self.ki_spin = ConstantSpinBox()
        self.ki_spin.setRange(-10000.0, 10000.0)
        self.ki_spin.setValue(0.0)
        self.ki_spin.setSingleStep(0.01)
        self.ki_spin.setToolTip("Integral gain - responds to accumulated error")
        pid_layout.addRow("Ki (Integral):", self.ki_spin)

        self.kd_spin = ConstantSpinBox()
        self.kd_spin.setRange(-10000.0, 10000.0)
        self.kd_spin.setValue(0.0)
        self.kd_spin.setSingleStep(0.01)
        self.kd_spin.setToolTip("Derivative gain - responds to rate of error change")
        pid_layout.addRow("Kd (Derivative):", self.kd_spin)

        pid_group.setLayout(pid_layout)
        main_layout.addWidget(pid_group)

        main_layout.addStretch()
        self.tab_widget.addTab(main_tab, "Main")

    def _create_advanced_tab(self):
        """Create the advanced settings tab."""
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)

        # Output Limits
        limits_group = QGroupBox("Output Limits")
        limits_layout = QFormLayout()

        self.output_min_spin = ConstantSpinBox()
        self.output_min_spin.setRange(-100000.0, 100000.0)
        self.output_min_spin.setValue(0.0)
        self.output_min_spin.setToolTip("Minimum output value (clamp)")
        limits_layout.addRow("Output Min:", self.output_min_spin)

        self.output_max_spin = ConstantSpinBox()
        self.output_max_spin.setRange(-100000.0, 100000.0)
        self.output_max_spin.setValue(100.0)
        self.output_max_spin.setToolTip("Maximum output value (clamp)")
        limits_layout.addRow("Output Max:", self.output_max_spin)

        limits_group.setLayout(limits_layout)
        advanced_layout.addWidget(limits_group)

        # Advanced Settings
        settings_group = QGroupBox("Controller Settings")
        settings_layout = QFormLayout()

        self.sample_time_spin = QSpinBox()
        self.sample_time_spin.setRange(1, 10000)
        self.sample_time_spin.setValue(100)
        self.sample_time_spin.setSuffix(" ms")
        self.sample_time_spin.setToolTip("PID loop execution period")
        settings_layout.addRow("Sample Time:", self.sample_time_spin)

        self.anti_windup_check = QCheckBox("Enable Anti-Windup")
        self.anti_windup_check.setChecked(True)
        self.anti_windup_check.setToolTip("Prevent integral term from accumulating excessively")
        settings_layout.addRow("", self.anti_windup_check)

        self.derivative_filter_check = QCheckBox("Enable Derivative Filter")
        self.derivative_filter_check.setChecked(True)
        self.derivative_filter_check.setToolTip("Apply low-pass filter to derivative term to reduce noise")
        settings_layout.addRow("", self.derivative_filter_check)

        self.filter_coeff_spin = ConstantSpinBox()
        self.filter_coeff_spin.setRange(0.0, 1.0)
        self.filter_coeff_spin.setValue(0.1)
        self.filter_coeff_spin.setSingleStep(0.01)
        self.filter_coeff_spin.setToolTip("Derivative filter coefficient (0-1, lower = more filtering)")
        settings_layout.addRow("Filter Coefficient:", self.filter_coeff_spin)

        self.reversed_check = QCheckBox("Reverse Acting")
        self.reversed_check.setChecked(False)
        self.reversed_check.setToolTip("Invert controller action (for cooling applications)")
        settings_layout.addRow("", self.reversed_check)

        self.enabled_check = QCheckBox("Controller Enabled")
        self.enabled_check.setChecked(True)
        self.enabled_check.setToolTip("Enable or disable the PID controller")
        settings_layout.addRow("", self.enabled_check)

        settings_group.setLayout(settings_layout)
        advanced_layout.addWidget(settings_group)

        advanced_layout.addStretch()
        self.tab_widget.addTab(advanced_tab, "Advanced")

    def _load_pid_config(self, config: Dict[str, Any]):
        """Load PID configuration into dialog."""
        # Input/Output - use _set_channel_edit_value to show display name
        self._set_channel_edit_value(self.setpoint_edit, config.get("setpoint_channel"))
        self.setpoint_value_spin.setValue(config.get("setpoint_value", 0.0))
        self._set_channel_edit_value(self.process_edit, config.get("process_channel"))
        self._set_channel_edit_value(self.output_edit, config.get("output_channel"))

        # PID parameters
        self.kp_spin.setValue(config.get("kp", 1.0))
        self.ki_spin.setValue(config.get("ki", 0.0))
        self.kd_spin.setValue(config.get("kd", 0.0))

        # Output limits
        self.output_min_spin.setValue(config.get("output_min", 0.0))
        self.output_max_spin.setValue(config.get("output_max", 100.0))

        # Advanced
        self.sample_time_spin.setValue(config.get("sample_time_ms", 100))
        self.anti_windup_check.setChecked(config.get("anti_windup", True))
        self.derivative_filter_check.setChecked(config.get("derivative_filter", True))
        self.filter_coeff_spin.setValue(config.get("derivative_filter_coeff", 0.1))
        self.reversed_check.setChecked(config.get("reversed", False))
        self.enabled_check.setChecked(config.get("enabled", True))

    def _validate_specific(self) -> List[str]:
        """Validate PID-specific fields."""
        errors = []

        # Process variable is required
        if not self.process_edit.text().strip():
            errors.append("Process variable channel is required")

        # Output limits
        if self.output_min_spin.value() >= self.output_max_spin.value():
            errors.append("Output min must be less than output max")

        # Sample time
        if self.sample_time_spin.value() < 1:
            errors.append("Sample time must be at least 1ms")

        # Filter coefficient
        if self.filter_coeff_spin.value() < 0 or self.filter_coeff_spin.value() > 1:
            errors.append("Filter coefficient must be between 0 and 1")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full PID configuration."""
        config = self.get_base_config()
        config.update({
            "setpoint_channel": self._get_channel_id_from_edit(self.setpoint_edit),
            "setpoint_value": self.setpoint_value_spin.value(),
            "process_channel": self._get_channel_id_from_edit(self.process_edit),
            "output_channel": self._get_channel_id_from_edit(self.output_edit),
            "kp": self.kp_spin.value(),
            "ki": self.ki_spin.value(),
            "kd": self.kd_spin.value(),
            "output_min": self.output_min_spin.value(),
            "output_max": self.output_max_spin.value(),
            "sample_time_ms": self.sample_time_spin.value(),
            "anti_windup": self.anti_windup_check.isChecked(),
            "derivative_filter": self.derivative_filter_check.isChecked(),
            "derivative_filter_coeff": self.filter_coeff_spin.value(),
            "reversed": self.reversed_check.isChecked(),
            "enabled": self.enabled_check.isChecked(),
        })
        return config

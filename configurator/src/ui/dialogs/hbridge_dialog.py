"""
H-Bridge Motor Configuration Dialog
Configures H-Bridge motor controller channels
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QLabel, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List
from .channel_selector_dialog import ChannelSelectorDialog
from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType
from models.channel_display_service import ChannelDisplayService


class HBridgeDialog(BaseChannelDialog):
    """Dialog for configuring an H-Bridge motor controller channel."""

    # H-Bridge modes matching firmware
    MODES = [
        ("coast", "Coast (Free spin)"),
        ("forward", "Forward"),
        ("reverse", "Reverse"),
        ("brake", "Brake (Short outputs)"),
        ("wiper_park", "Wiper Park"),
        ("pid_position", "PID Position Control"),
    ]

    # PWM Source modes (matching ECUMaster)
    PWM_SOURCE_MODES = [
        ("fixed", "Fixed Value"),
        ("channel", "Channel"),
        ("channel_offset", "Channel (Bidirectional)"),
    ]

    # Direction Source modes
    DIR_SOURCE_MODES = [
        ("fixed", "Fixed"),
        ("channel", "Channel"),
        ("channel_inverted", "Channel (Inverted)"),
    ]

    # Motor presets matching emulator
    MOTOR_PRESETS = [
        ("wiper", "Wiper Motor"),
        ("window", "Window Motor"),
        ("seat", "Seat Motor"),
        ("valve", "Valve Actuator"),
        ("pump", "Pump Motor"),
        ("custom", "Custom"),
    ]

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None,
                 available_channels=None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None,
                 **kwargs):
        """Initialize HBridgeDialog.

        Args:
            parent: Parent widget
            config: H-Bridge configuration (for editing) or None (for creating)
            available_channels: Dict of available channels for source selection
            existing_channels: List of existing channel configs
            **kwargs: Additional arguments:
                - used_bridges: List of already used H-Bridge numbers
                - hbridge_config: Alias for config (backwards compatibility)
                - used_numbers: Alias for used_bridges (backwards compatibility)
        """
        # Handle backwards compatibility aliases
        if config is None:
            config = kwargs.get('hbridge_config')

        # Handle used_bridges/used_numbers naming - store before super().__init__
        self.used_bridges = kwargs.get('used_bridges') or kwargs.get('used_numbers') or []
        self._config_for_bridge = config  # Store for bridge combo population

        # Initialize base class (creates Basic Settings with name, channel_id, enabled)
        super().__init__(parent, config, available_channels, ChannelType.HBRIDGE, existing_channels)

        self.resize(650, 700)

        # Create H-Bridge specific UI
        self._create_hbridge_ui()

        if config:
            self._load_specific_config(config)

    def _create_hbridge_ui(self):
        """Create H-Bridge specific UI components."""
        # Create tabs for organized settings
        tabs = QTabWidget()

        # Control tab (includes bridge number and motor settings)
        control_tab = QWidget()
        control_layout = QVBoxLayout(control_tab)
        control_layout.addWidget(self._create_bridge_settings_group())
        control_layout.addWidget(self._create_control_group())
        control_layout.addStretch()
        tabs.addTab(control_tab, "Control")

        # Position Control tab
        position_tab = QWidget()
        position_layout = QVBoxLayout(position_tab)
        position_layout.addWidget(self._create_position_group())
        position_layout.addWidget(self._create_pid_group())
        position_layout.addStretch()
        tabs.addTab(position_tab, "Position Control")

        # Protection tab
        protection_tab = QWidget()
        protection_layout = QVBoxLayout(protection_tab)
        protection_layout.addWidget(self._create_protection_group())
        protection_layout.addWidget(self._create_stall_group())
        protection_layout.addWidget(self._create_failsafe_group())
        protection_layout.addStretch()
        tabs.addTab(protection_tab, "Protection")

        # Add tabs to base class content_layout
        self.content_layout.addWidget(tabs)

    def _create_bridge_settings_group(self) -> QGroupBox:
        """Create bridge-specific settings group (bridge number, preset)."""
        group = QGroupBox("H-Bridge Settings")
        layout = QFormLayout()

        # Bridge Number (HB1-HB4)
        bridge_layout = QHBoxLayout()
        self.bridge_combo = QComboBox()
        self._populate_bridge_combo()
        bridge_layout.addWidget(self.bridge_combo)
        bridge_layout.addStretch()
        layout.addRow("H-Bridge:", bridge_layout)

        # Motor Preset
        self.preset_combo = QComboBox()
        for value, label in self.MOTOR_PRESETS:
            self.preset_combo.addItem(label, value)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        layout.addRow("Motor Preset:", self.preset_combo)

        group.setLayout(layout)
        return group

    def _create_control_group(self) -> QGroupBox:
        """Create control settings group."""
        group = QGroupBox("Control Settings")
        layout = QGridLayout()

        # Mode
        layout.addWidget(QLabel("Mode:"), 0, 0)
        self.mode_combo = QComboBox()
        for value, label in self.MODES:
            self.mode_combo.addItem(label, value)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo, 0, 1)

        # Direction
        layout.addWidget(QLabel("Direction:"), 0, 2)
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Forward", "forward")
        self.direction_combo.addItem("Reverse", "reverse")
        layout.addWidget(self.direction_combo, 0, 3)

        # Source Channel (control on/off)
        layout.addWidget(QLabel("Control Source:"), 1, 0)
        source_layout = QHBoxLayout()
        self.source_channel_edit = QLineEdit()
        self.source_channel_edit.setPlaceholderText("Select channel...")
        self.source_channel_edit.setReadOnly(True)
        source_layout.addWidget(self.source_channel_edit, stretch=1)
        self.source_channel_clear_btn = QPushButton("✕")
        self.source_channel_clear_btn.setFixedWidth(24)
        self.source_channel_clear_btn.setToolTip("Clear")
        self.source_channel_clear_btn.clicked.connect(lambda: self.source_channel_edit.clear())
        source_layout.addWidget(self.source_channel_clear_btn)
        self.source_channel_btn = QPushButton("...")
        self.source_channel_btn.setFixedWidth(30)
        self.source_channel_btn.clicked.connect(self._browse_source_channel)
        source_layout.addWidget(self.source_channel_btn)
        layout.addLayout(source_layout, 1, 1, 1, 3)

        # Direction Source Channel
        layout.addWidget(QLabel("Direction Source:"), 2, 0)
        dir_layout = QHBoxLayout()
        self.direction_source_edit = QLineEdit()
        self.direction_source_edit.setPlaceholderText("Optional - select channel...")
        self.direction_source_edit.setReadOnly(True)
        dir_layout.addWidget(self.direction_source_edit, stretch=1)
        self.direction_source_clear_btn = QPushButton("✕")
        self.direction_source_clear_btn.setFixedWidth(24)
        self.direction_source_clear_btn.setToolTip("Clear")
        self.direction_source_clear_btn.clicked.connect(lambda: self.direction_source_edit.clear())
        dir_layout.addWidget(self.direction_source_clear_btn)
        self.direction_source_btn = QPushButton("...")
        self.direction_source_btn.setFixedWidth(30)
        self.direction_source_btn.clicked.connect(self._browse_direction_source)
        dir_layout.addWidget(self.direction_source_btn)
        layout.addLayout(dir_layout, 2, 1, 1, 3)

        # PWM Source Mode (Fixed / Channel / Bidirectional)
        layout.addWidget(QLabel("PWM Mode:"), 3, 0)
        self.pwm_mode_combo = QComboBox()
        for value, label in self.PWM_SOURCE_MODES:
            self.pwm_mode_combo.addItem(label, value)
        self.pwm_mode_combo.currentIndexChanged.connect(self._on_pwm_mode_changed)
        self.pwm_mode_combo.setToolTip(
            "Fixed: Use fixed PWM value\n"
            "Channel: PWM from channel (0-100%)\n"
            "Bidirectional: 0-50%=Rev, 50-100%=Fwd (like ECUMaster offset mode)"
        )
        layout.addWidget(self.pwm_mode_combo, 3, 1)

        # PWM Value (fixed)
        layout.addWidget(QLabel("PWM Value:"), 3, 2)
        self.pwm_spin = QSpinBox()
        self.pwm_spin.setRange(0, 255)
        self.pwm_spin.setValue(255)
        self.pwm_spin.setToolTip("Fixed PWM value (0-255)")
        layout.addWidget(self.pwm_spin, 3, 3)

        # PWM Source Channel
        layout.addWidget(QLabel("PWM Source:"), 4, 0)
        pwm_layout = QHBoxLayout()
        self.pwm_source_edit = QLineEdit()
        self.pwm_source_edit.setPlaceholderText("Select channel...")
        self.pwm_source_edit.setReadOnly(True)
        pwm_layout.addWidget(self.pwm_source_edit, stretch=1)
        self.pwm_source_clear_btn = QPushButton("✕")
        self.pwm_source_clear_btn.setFixedWidth(24)
        self.pwm_source_clear_btn.setToolTip("Clear")
        self.pwm_source_clear_btn.clicked.connect(lambda: self.pwm_source_edit.clear())
        pwm_layout.addWidget(self.pwm_source_clear_btn)
        self.pwm_source_btn = QPushButton("...")
        self.pwm_source_btn.setFixedWidth(30)
        self.pwm_source_btn.clicked.connect(self._browse_pwm_source)
        pwm_layout.addWidget(self.pwm_source_btn)
        layout.addLayout(pwm_layout, 4, 1, 1, 3)

        # Duty Cycle Limit
        layout.addWidget(QLabel("Duty Limit:"), 5, 0)
        self.duty_limit_spin = QSpinBox()
        self.duty_limit_spin.setRange(0, 100)
        self.duty_limit_spin.setValue(100)
        self.duty_limit_spin.setSuffix(" %")
        self.duty_limit_spin.setToolTip("Maximum PWM duty cycle (limits output power)")
        layout.addWidget(self.duty_limit_spin, 5, 1)

        # PWM Frequency
        layout.addWidget(QLabel("PWM Freq:"), 5, 2)
        self.pwm_freq_combo = QComboBox()
        self.pwm_freq_combo.addItem("1 kHz", 1000)
        self.pwm_freq_combo.addItem("4 kHz", 4000)
        self.pwm_freq_combo.addItem("10 kHz", 10000)
        self.pwm_freq_combo.addItem("20 kHz", 20000)
        self.pwm_freq_combo.setCurrentIndex(0)  # Default 1kHz
        self.pwm_freq_combo.setToolTip("PWM output frequency")
        layout.addWidget(self.pwm_freq_combo, 5, 3)

        # Invert Direction
        self.invert_direction_check = QCheckBox("Invert Direction")
        layout.addWidget(self.invert_direction_check, 6, 0, 1, 2)

        group.setLayout(layout)
        return group

    def _create_position_group(self) -> QGroupBox:
        """Create position control settings group."""
        group = QGroupBox("Position Control")
        layout = QGridLayout()

        # Enable position feedback
        self.position_feedback_check = QCheckBox("Enable Position Feedback")
        self.position_feedback_check.toggled.connect(self._on_position_feedback_toggled)
        layout.addWidget(self.position_feedback_check, 0, 0, 1, 4)

        # Position feedback source
        layout.addWidget(QLabel("Position Source:"), 1, 0)
        pos_layout = QHBoxLayout()
        self.position_source_edit = QLineEdit()
        self.position_source_edit.setPlaceholderText("Select analog input...")
        self.position_source_edit.setReadOnly(True)
        pos_layout.addWidget(self.position_source_edit, stretch=1)
        self.position_source_clear_btn = QPushButton("✕")
        self.position_source_clear_btn.setFixedWidth(24)
        self.position_source_clear_btn.setToolTip("Clear")
        self.position_source_clear_btn.clicked.connect(lambda: self.position_source_edit.clear())
        pos_layout.addWidget(self.position_source_clear_btn)
        self.position_source_btn = QPushButton("...")
        self.position_source_btn.setFixedWidth(30)
        self.position_source_btn.clicked.connect(self._browse_position_source)
        pos_layout.addWidget(self.position_source_btn)
        layout.addLayout(pos_layout, 1, 1, 1, 3)

        # Target position value
        layout.addWidget(QLabel("Target Position:"), 2, 0)
        self.target_position_spin = QSpinBox()
        self.target_position_spin.setRange(0, 65535)
        self.target_position_spin.setValue(0)
        layout.addWidget(self.target_position_spin, 2, 1)

        # Target position source
        layout.addWidget(QLabel("Target Source:"), 2, 2)
        target_layout = QHBoxLayout()
        self.target_source_edit = QLineEdit()
        self.target_source_edit.setPlaceholderText("Optional...")
        self.target_source_edit.setReadOnly(True)
        target_layout.addWidget(self.target_source_edit, stretch=1)
        self.target_source_clear_btn = QPushButton("✕")
        self.target_source_clear_btn.setFixedWidth(24)
        self.target_source_clear_btn.setToolTip("Clear")
        self.target_source_clear_btn.clicked.connect(lambda: self.target_source_edit.clear())
        target_layout.addWidget(self.target_source_clear_btn)
        self.target_source_btn = QPushButton("...")
        self.target_source_btn.setFixedWidth(30)
        self.target_source_btn.clicked.connect(self._browse_target_source)
        target_layout.addWidget(self.target_source_btn)
        layout.addLayout(target_layout, 2, 3)

        # Position limits
        layout.addWidget(QLabel("Position Min:"), 3, 0)
        self.position_min_spin = QSpinBox()
        self.position_min_spin.setRange(0, 65535)
        self.position_min_spin.setValue(0)
        layout.addWidget(self.position_min_spin, 3, 1)

        layout.addWidget(QLabel("Position Max:"), 3, 2)
        self.position_max_spin = QSpinBox()
        self.position_max_spin.setRange(0, 65535)
        self.position_max_spin.setValue(65535)
        layout.addWidget(self.position_max_spin, 3, 3)

        # Position deadband
        layout.addWidget(QLabel("Deadband:"), 4, 0)
        self.deadband_spin = QSpinBox()
        self.deadband_spin.setRange(0, 1000)
        self.deadband_spin.setValue(50)
        self.deadband_spin.setToolTip("Position tolerance (stops when within deadband)")
        layout.addWidget(self.deadband_spin, 4, 1)

        # Valid voltage range (ECUMaster feature)
        layout.addWidget(QLabel("Valid Min V:"), 5, 0)
        self.valid_voltage_min_spin = QDoubleSpinBox()
        self.valid_voltage_min_spin.setRange(0.0, 5.0)
        self.valid_voltage_min_spin.setValue(0.2)
        self.valid_voltage_min_spin.setSuffix(" V")
        self.valid_voltage_min_spin.setDecimals(2)
        self.valid_voltage_min_spin.setToolTip("Min valid feedback voltage (output disabled if below)")
        layout.addWidget(self.valid_voltage_min_spin, 5, 1)

        layout.addWidget(QLabel("Valid Max V:"), 5, 2)
        self.valid_voltage_max_spin = QDoubleSpinBox()
        self.valid_voltage_max_spin.setRange(0.0, 5.0)
        self.valid_voltage_max_spin.setValue(4.8)
        self.valid_voltage_max_spin.setSuffix(" V")
        self.valid_voltage_max_spin.setDecimals(2)
        self.valid_voltage_max_spin.setToolTip("Max valid feedback voltage (output disabled if above)")
        layout.addWidget(self.valid_voltage_max_spin, 5, 3)

        # Position margins (ECUMaster feature - avoid hitting end stops)
        layout.addWidget(QLabel("Lower Margin:"), 6, 0)
        self.lower_margin_spin = QSpinBox()
        self.lower_margin_spin.setRange(0, 1000)
        self.lower_margin_spin.setValue(50)
        self.lower_margin_spin.setToolTip("Lower position margin to avoid hitting end stop")
        layout.addWidget(self.lower_margin_spin, 6, 1)

        layout.addWidget(QLabel("Upper Margin:"), 6, 2)
        self.upper_margin_spin = QSpinBox()
        self.upper_margin_spin.setRange(0, 1000)
        self.upper_margin_spin.setValue(50)
        self.upper_margin_spin.setToolTip("Upper position margin to avoid hitting end stop")
        layout.addWidget(self.upper_margin_spin, 6, 3)

        group.setLayout(layout)
        return group

    def _create_pid_group(self) -> QGroupBox:
        """Create PID control settings group."""
        group = QGroupBox("PID Parameters")
        layout = QGridLayout()

        # Kp
        layout.addWidget(QLabel("Kp (Proportional):"), 0, 0)
        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(0.0, 100.0)
        self.kp_spin.setValue(1.0)
        self.kp_spin.setDecimals(2)
        self.kp_spin.setSingleStep(0.1)
        layout.addWidget(self.kp_spin, 0, 1)

        # Ki
        layout.addWidget(QLabel("Ki (Integral):"), 0, 2)
        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0.0, 100.0)
        self.ki_spin.setValue(0.0)
        self.ki_spin.setDecimals(2)
        self.ki_spin.setSingleStep(0.01)
        layout.addWidget(self.ki_spin, 0, 3)

        # Kd
        layout.addWidget(QLabel("Kd (Derivative):"), 1, 0)
        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0.0, 100.0)
        self.kd_spin.setValue(0.0)
        self.kd_spin.setDecimals(2)
        self.kd_spin.setSingleStep(0.01)
        layout.addWidget(self.kd_spin, 1, 1)

        # Kd Filter (ECUMaster feature - reduces rattle)
        layout.addWidget(QLabel("Kd Filter:"), 1, 2)
        self.kd_filter_spin = QDoubleSpinBox()
        self.kd_filter_spin.setRange(0.0, 1.0)
        self.kd_filter_spin.setValue(0.1)
        self.kd_filter_spin.setDecimals(2)
        self.kd_filter_spin.setSingleStep(0.05)
        self.kd_filter_spin.setToolTip(
            "Derivative filter coefficient (0-1)\n"
            "Higher value = more filtering, reduces rattle\n"
            "Lower value = faster response"
        )
        layout.addWidget(self.kd_filter_spin, 1, 3)

        # Output limits
        layout.addWidget(QLabel("Min Output:"), 2, 0)
        self.pid_min_spin = QSpinBox()
        self.pid_min_spin.setRange(-255, 255)
        self.pid_min_spin.setValue(-255)
        layout.addWidget(self.pid_min_spin, 2, 1)

        layout.addWidget(QLabel("Max Output:"), 2, 2)
        self.pid_max_spin = QSpinBox()
        self.pid_max_spin.setRange(-255, 255)
        self.pid_max_spin.setValue(255)
        layout.addWidget(self.pid_max_spin, 2, 3)

        group.setLayout(layout)
        return group

    def _create_protection_group(self) -> QGroupBox:
        """Create protection settings group."""
        group = QGroupBox("Current Protection")
        layout = QGridLayout()

        # Current limit
        layout.addWidget(QLabel("Current Limit:"), 0, 0)
        self.current_limit_spin = QDoubleSpinBox()
        self.current_limit_spin.setRange(0.1, 50.0)
        self.current_limit_spin.setValue(10.0)
        self.current_limit_spin.setSuffix(" A")
        self.current_limit_spin.setDecimals(2)
        self.current_limit_spin.setSingleStep(0.5)
        layout.addWidget(self.current_limit_spin, 0, 1)

        # Inrush current
        layout.addWidget(QLabel("Inrush Current:"), 0, 2)
        self.inrush_current_spin = QDoubleSpinBox()
        self.inrush_current_spin.setRange(0.1, 100.0)
        self.inrush_current_spin.setValue(30.0)
        self.inrush_current_spin.setSuffix(" A")
        self.inrush_current_spin.setDecimals(2)
        layout.addWidget(self.inrush_current_spin, 0, 3)

        # Inrush time
        layout.addWidget(QLabel("Inrush Time:"), 1, 0)
        self.inrush_time_spin = QSpinBox()
        self.inrush_time_spin.setRange(10, 5000)
        self.inrush_time_spin.setValue(500)
        self.inrush_time_spin.setSuffix(" ms")
        layout.addWidget(self.inrush_time_spin, 1, 1)

        # Retry count
        layout.addWidget(QLabel("Retry Count:"), 1, 2)
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(3)
        layout.addWidget(self.retry_count_spin, 1, 3)

        # Retry delay
        layout.addWidget(QLabel("Retry Delay:"), 2, 0)
        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(100, 10000)
        self.retry_delay_spin.setValue(1000)
        self.retry_delay_spin.setSuffix(" ms")
        layout.addWidget(self.retry_delay_spin, 2, 1)

        group.setLayout(layout)
        return group

    def _create_stall_group(self) -> QGroupBox:
        """Create stall detection settings group."""
        group = QGroupBox("Stall Detection")
        layout = QGridLayout()

        # Enable stall detection
        self.stall_detection_check = QCheckBox("Enable Stall Detection")
        self.stall_detection_check.setChecked(True)
        self.stall_detection_check.toggled.connect(self._on_stall_detection_toggled)
        layout.addWidget(self.stall_detection_check, 0, 0, 1, 4)

        # Stall current threshold
        layout.addWidget(QLabel("Stall Current:"), 1, 0)
        self.stall_current_spin = QDoubleSpinBox()
        self.stall_current_spin.setRange(0.1, 50.0)
        self.stall_current_spin.setValue(5.0)
        self.stall_current_spin.setSuffix(" A")
        self.stall_current_spin.setDecimals(2)
        self.stall_current_spin.setToolTip("Current threshold indicating stall")
        layout.addWidget(self.stall_current_spin, 1, 1)

        # Stall time threshold
        layout.addWidget(QLabel("Stall Time:"), 1, 2)
        self.stall_time_spin = QSpinBox()
        self.stall_time_spin.setRange(10, 5000)
        self.stall_time_spin.setValue(500)
        self.stall_time_spin.setSuffix(" ms")
        self.stall_time_spin.setToolTip("Time above stall current before stopping")
        layout.addWidget(self.stall_time_spin, 1, 3)

        # Overtemperature threshold
        layout.addWidget(QLabel("Max Temperature:"), 2, 0)
        self.overtemp_spin = QSpinBox()
        self.overtemp_spin.setRange(50, 200)
        self.overtemp_spin.setValue(120)
        self.overtemp_spin.setSuffix(" C")
        self.overtemp_spin.setToolTip("Motor overtemperature shutdown threshold")
        layout.addWidget(self.overtemp_spin, 2, 1)

        group.setLayout(layout)
        return group

    def _create_failsafe_group(self) -> QGroupBox:
        """Create signal loss failsafe settings group."""
        group = QGroupBox("Signal Loss Failsafe")
        layout = QGridLayout()

        # Enable failsafe
        self.failsafe_enabled_check = QCheckBox("Enable Signal Loss Protection")
        self.failsafe_enabled_check.setChecked(True)
        self.failsafe_enabled_check.setToolTip(
            "When enabled, H-Bridge will go to safe mode if control signal is lost"
        )
        self.failsafe_enabled_check.toggled.connect(self._on_failsafe_toggled)
        layout.addWidget(self.failsafe_enabled_check, 0, 0, 1, 4)

        # Signal timeout
        layout.addWidget(QLabel("Signal Timeout:"), 1, 0)
        self.signal_timeout_spin = QSpinBox()
        self.signal_timeout_spin.setRange(10, 5000)
        self.signal_timeout_spin.setValue(100)
        self.signal_timeout_spin.setSuffix(" ms")
        self.signal_timeout_spin.setToolTip(
            "Time without valid control signal before entering safe mode\n"
            "(CAN message timeout, wire break detection, etc.)"
        )
        layout.addWidget(self.signal_timeout_spin, 1, 1)

        # Failsafe mode
        layout.addWidget(QLabel("Safe Mode:"), 1, 2)
        self.failsafe_mode_combo = QComboBox()
        self.failsafe_mode_combo.addItem("Park Position", "park")
        self.failsafe_mode_combo.addItem("Brake (Hold)", "brake")
        self.failsafe_mode_combo.addItem("Coast (Free)", "coast")
        self.failsafe_mode_combo.addItem("Custom Position", "custom_position")
        self.failsafe_mode_combo.currentIndexChanged.connect(self._on_failsafe_mode_changed)
        self.failsafe_mode_combo.setToolTip(
            "Action when control signal is lost:\n"
            "- Park Position: Move to configured park position\n"
            "- Brake: Active brake (hold position)\n"
            "- Coast: Free spin (release motor)\n"
            "- Custom Position: Move to specific position"
        )
        layout.addWidget(self.failsafe_mode_combo, 1, 3)

        # Custom failsafe position
        layout.addWidget(QLabel("Safe Position:"), 2, 0)
        self.failsafe_position_spin = QSpinBox()
        self.failsafe_position_spin.setRange(0, 65535)
        self.failsafe_position_spin.setValue(0)
        self.failsafe_position_spin.setToolTip(
            "Target position for safe mode (used with Park or Custom Position modes)"
        )
        layout.addWidget(self.failsafe_position_spin, 2, 1)

        # Failsafe PWM (for safe mode operation)
        layout.addWidget(QLabel("Safe Mode PWM:"), 2, 2)
        self.failsafe_pwm_spin = QSpinBox()
        self.failsafe_pwm_spin.setRange(0, 255)
        self.failsafe_pwm_spin.setValue(100)
        self.failsafe_pwm_spin.setToolTip(
            "PWM value to use when moving to safe position"
        )
        layout.addWidget(self.failsafe_pwm_spin, 2, 3)

        # Recovery options
        self.auto_recovery_check = QCheckBox("Auto Recovery on Signal Restore")
        self.auto_recovery_check.setChecked(True)
        self.auto_recovery_check.setToolTip(
            "Automatically resume normal operation when control signal returns"
        )
        layout.addWidget(self.auto_recovery_check, 3, 0, 1, 4)

        group.setLayout(layout)
        return group

    def _on_failsafe_toggled(self, enabled):
        """Handle failsafe enable toggle."""
        self.signal_timeout_spin.setEnabled(enabled)
        self.failsafe_mode_combo.setEnabled(enabled)
        self.failsafe_position_spin.setEnabled(enabled)
        self.failsafe_pwm_spin.setEnabled(enabled)
        self.auto_recovery_check.setEnabled(enabled)

    def _on_failsafe_mode_changed(self, index):
        """Handle failsafe mode change."""
        mode = self.failsafe_mode_combo.currentData()
        # Enable position only for park and custom_position modes
        self.failsafe_position_spin.setEnabled(mode in ("park", "custom_position"))

    def _populate_bridge_combo(self):
        """Populate H-Bridge dropdown with available bridges."""
        self.bridge_combo.clear()

        # Get current bridge if editing
        current_bridge = None
        if self._config_for_bridge:
            current_bridge = self._config_for_bridge.get("bridge_number")

        # Add available bridges (HB1-HB4)
        for bridge in range(4):
            if bridge not in self.used_bridges or bridge == current_bridge:
                self.bridge_combo.addItem(f"HB{bridge + 1}", bridge)

        if self.bridge_combo.count() == 0:
            self.bridge_combo.addItem("No bridges available", -1)

    # Channel helper method
    def _get_channel_display_name(self, channel_id) -> str:
        """Get display name for a channel using central lookup."""
        return ChannelDisplayService.get_display_name(channel_id, self.available_channels)

    def _browse_source_channel(self):
        """Browse and select control source channel."""
        current = self.source_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.source_channel_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_direction_source(self):
        """Browse and select direction source channel."""
        current = self.direction_source_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.direction_source_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_pwm_source(self):
        """Browse and select PWM source channel."""
        current = self.pwm_source_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.pwm_source_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_position_source(self):
        """Browse and select position feedback source."""
        current = self.position_source_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.position_source_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_target_source(self):
        """Browse and select target position source."""
        current = self.target_source_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.target_source_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _on_preset_changed(self, index):
        """Handle motor preset change - apply preset defaults."""
        preset = self.preset_combo.currentData()

        # Apply preset defaults (matching emulator physics)
        presets = {
            "wiper": {"current_limit": 10.0, "stall_current": 8.0, "stall_time": 1000},
            "window": {"current_limit": 15.0, "stall_current": 12.0, "stall_time": 500},
            "seat": {"current_limit": 20.0, "stall_current": 15.0, "stall_time": 800},
            "valve": {"current_limit": 5.0, "stall_current": 4.0, "stall_time": 300},
            "pump": {"current_limit": 8.0, "stall_current": 6.0, "stall_time": 200},
        }

        if preset in presets:
            defaults = presets[preset]
            self.current_limit_spin.setValue(defaults["current_limit"])
            self.stall_current_spin.setValue(defaults["stall_current"])
            self.stall_time_spin.setValue(defaults["stall_time"])

    def _on_pwm_mode_changed(self, index):
        """Handle PWM mode change - enable/disable relevant controls."""
        mode = self.pwm_mode_combo.currentData()
        is_fixed = mode == "fixed"
        is_channel = mode in ("channel", "channel_offset")

        self.pwm_spin.setEnabled(is_fixed)
        self.pwm_source_edit.setEnabled(is_channel)
        self.pwm_source_btn.setEnabled(is_channel)
        self.pwm_source_clear_btn.setEnabled(is_channel)

    def _on_mode_changed(self, index):
        """Handle mode change - enable/disable position controls."""
        mode = self.mode_combo.currentData()
        is_pid_mode = mode == "pid_position"
        is_wiper_mode = mode == "wiper_park"

        # Enable position controls for PID and wiper modes
        self.position_feedback_check.setEnabled(is_pid_mode or is_wiper_mode)
        self._on_position_feedback_toggled(self.position_feedback_check.isChecked())

    def _on_position_feedback_toggled(self, enabled):
        """Handle position feedback toggle."""
        mode = self.mode_combo.currentData()
        is_position_mode = mode in ("pid_position", "wiper_park")
        enabled = enabled and is_position_mode

        self.position_source_edit.setEnabled(enabled)
        self.position_source_btn.setEnabled(enabled)
        self.position_source_clear_btn.setEnabled(enabled)
        self.target_position_spin.setEnabled(enabled)
        self.target_source_edit.setEnabled(enabled)
        self.target_source_btn.setEnabled(enabled)
        self.target_source_clear_btn.setEnabled(enabled)
        self.position_min_spin.setEnabled(enabled)
        self.position_max_spin.setEnabled(enabled)
        self.deadband_spin.setEnabled(enabled)
        self.valid_voltage_min_spin.setEnabled(enabled)
        self.valid_voltage_max_spin.setEnabled(enabled)
        self.lower_margin_spin.setEnabled(enabled)
        self.upper_margin_spin.setEnabled(enabled)
        self.kp_spin.setEnabled(enabled)
        self.ki_spin.setEnabled(enabled)
        self.kd_spin.setEnabled(enabled)
        self.kd_filter_spin.setEnabled(enabled)
        self.pid_min_spin.setEnabled(enabled)
        self.pid_max_spin.setEnabled(enabled)

    def _on_stall_detection_toggled(self, enabled):
        """Handle stall detection toggle."""
        self.stall_current_spin.setEnabled(enabled)
        self.stall_time_spin.setEnabled(enabled)

    def _validate_specific(self) -> list:
        """Validate H-Bridge specific fields."""
        errors = []

        # Validate bridge selection
        bridge = self.bridge_combo.currentData()
        if bridge is None or bridge < 0:
            errors.append("Please select an H-Bridge")

        return errors

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load H-Bridge specific configuration."""
        # Bridge number
        bridge = config.get("bridge_number", 0)
        index = self.bridge_combo.findData(bridge)
        if index >= 0:
            self.bridge_combo.setCurrentIndex(index)

        # Motor preset
        preset = config.get("motor_preset", "custom")
        if hasattr(preset, 'value'):
            preset = preset.value
        index = self.preset_combo.findData(preset)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)

        # Mode
        mode = config.get("mode", "coast")
        if hasattr(mode, 'value'):
            mode = mode.value
        index = self.mode_combo.findData(mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)

        # Direction
        direction = config.get("direction", "forward")
        if hasattr(direction, 'value'):
            direction = direction.value
        index = self.direction_combo.findData(direction)
        if index >= 0:
            self.direction_combo.setCurrentIndex(index)

        # Source channels - convert channel IDs to display names
        self.source_channel_edit.setText(self._get_channel_display_name(config.get("source_channel", "")))
        self.direction_source_edit.setText(self._get_channel_display_name(config.get("direction_source_channel", "")))
        self.pwm_source_edit.setText(self._get_channel_display_name(config.get("pwm_source_channel", "")))

        # PWM mode and settings
        pwm_mode = config.get("pwm_mode", "fixed")
        index = self.pwm_mode_combo.findData(pwm_mode)
        if index >= 0:
            self.pwm_mode_combo.setCurrentIndex(index)
        self.pwm_spin.setValue(config.get("pwm_value", 255))
        self.duty_limit_spin.setValue(config.get("duty_limit_percent", 100))

        # PWM frequency
        pwm_freq = config.get("pwm_frequency", 1000)
        index = self.pwm_freq_combo.findData(pwm_freq)
        if index >= 0:
            self.pwm_freq_combo.setCurrentIndex(index)

        self.invert_direction_check.setChecked(config.get("invert_direction", False))

        # Position control - convert channel IDs to display names
        self.position_feedback_check.setChecked(config.get("position_feedback_enabled", False))
        self.position_source_edit.setText(self._get_channel_display_name(config.get("position_source_channel", "")))
        self.target_position_spin.setValue(config.get("target_position", 0))
        self.target_source_edit.setText(self._get_channel_display_name(config.get("target_source_channel", "")))
        self.position_min_spin.setValue(config.get("position_min", 0))
        self.position_max_spin.setValue(config.get("position_max", 65535))
        self.deadband_spin.setValue(config.get("position_deadband", 50))

        # Valid voltage range (ECUMaster feature)
        self.valid_voltage_min_spin.setValue(config.get("valid_voltage_min", 0.2))
        self.valid_voltage_max_spin.setValue(config.get("valid_voltage_max", 4.8))

        # Position margins (ECUMaster feature)
        self.lower_margin_spin.setValue(config.get("lower_margin", 50))
        self.upper_margin_spin.setValue(config.get("upper_margin", 50))

        # PID
        self.kp_spin.setValue(config.get("pid_kp", 1.0))
        self.ki_spin.setValue(config.get("pid_ki", 0.0))
        self.kd_spin.setValue(config.get("pid_kd", 0.0))
        self.kd_filter_spin.setValue(config.get("pid_kd_filter", 0.1))
        self.pid_min_spin.setValue(config.get("pid_output_min", -255))
        self.pid_max_spin.setValue(config.get("pid_output_max", 255))

        # Protection
        self.current_limit_spin.setValue(config.get("current_limit_a", 10.0))
        self.inrush_current_spin.setValue(config.get("inrush_current_a", 30.0))
        self.inrush_time_spin.setValue(config.get("inrush_time_ms", 500))
        self.retry_count_spin.setValue(config.get("retry_count", 3))
        self.retry_delay_spin.setValue(config.get("retry_delay_ms", 1000))

        # Stall detection
        self.stall_detection_check.setChecked(config.get("stall_detection_enabled", True))
        self.stall_current_spin.setValue(config.get("stall_current_threshold_a", 5.0))
        self.stall_time_spin.setValue(config.get("stall_time_threshold_ms", 500))
        self.overtemp_spin.setValue(config.get("overtemperature_threshold_c", 120))

        # Failsafe settings
        self.failsafe_enabled_check.setChecked(config.get("failsafe_enabled", True))
        self.signal_timeout_spin.setValue(config.get("signal_timeout_ms", 100))
        failsafe_mode = config.get("failsafe_mode", "park")
        if hasattr(failsafe_mode, 'value'):
            failsafe_mode = failsafe_mode.value
        index = self.failsafe_mode_combo.findData(failsafe_mode)
        if index >= 0:
            self.failsafe_mode_combo.setCurrentIndex(index)
        self.failsafe_position_spin.setValue(config.get("failsafe_position", 0))
        self.failsafe_pwm_spin.setValue(config.get("failsafe_pwm", 100))
        self.auto_recovery_check.setChecked(config.get("auto_recovery", True))

        # Update control states
        self._on_mode_changed(0)
        self._on_pwm_mode_changed(0)
        self._on_stall_detection_toggled(self.stall_detection_check.isChecked())
        self._on_failsafe_toggled(self.failsafe_enabled_check.isChecked())

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        # Get base config (channel_id, name, enabled, channel_type)
        config = self.get_base_config()

        # Add H-Bridge specific fields
        config.update({
            "bridge_number": self.bridge_combo.currentData(),
            "motor_preset": self.preset_combo.currentData(),
            "mode": self.mode_combo.currentData(),
            "direction": self.direction_combo.currentData(),
            "source_channel": self.source_channel_edit.text(),
            "direction_source_channel": self.direction_source_edit.text(),
            "pwm_mode": self.pwm_mode_combo.currentData(),
            "pwm_value": self.pwm_spin.value(),
            "pwm_source_channel": self.pwm_source_edit.text(),
            "duty_limit_percent": self.duty_limit_spin.value(),
            "pwm_frequency": self.pwm_freq_combo.currentData(),
            "invert_direction": self.invert_direction_check.isChecked(),

            # Position control
            "position_feedback_enabled": self.position_feedback_check.isChecked(),
            "position_source_channel": self.position_source_edit.text(),
            "target_position": self.target_position_spin.value(),
            "target_source_channel": self.target_source_edit.text(),
            "position_min": self.position_min_spin.value(),
            "position_max": self.position_max_spin.value(),
            "position_deadband": self.deadband_spin.value(),
            "valid_voltage_min": self.valid_voltage_min_spin.value(),
            "valid_voltage_max": self.valid_voltage_max_spin.value(),
            "lower_margin": self.lower_margin_spin.value(),
            "upper_margin": self.upper_margin_spin.value(),

            # PID
            "pid_kp": self.kp_spin.value(),
            "pid_ki": self.ki_spin.value(),
            "pid_kd": self.kd_spin.value(),
            "pid_kd_filter": self.kd_filter_spin.value(),
            "pid_output_min": self.pid_min_spin.value(),
            "pid_output_max": self.pid_max_spin.value(),

            # Protection
            "current_limit_a": self.current_limit_spin.value(),
            "inrush_current_a": self.inrush_current_spin.value(),
            "inrush_time_ms": self.inrush_time_spin.value(),
            "retry_count": self.retry_count_spin.value(),
            "retry_delay_ms": self.retry_delay_spin.value(),

            # Stall detection
            "stall_detection_enabled": self.stall_detection_check.isChecked(),
            "stall_current_threshold_a": self.stall_current_spin.value(),
            "stall_time_threshold_ms": self.stall_time_spin.value(),
            "overtemperature_threshold_c": self.overtemp_spin.value(),

            # Failsafe (signal loss protection)
            "failsafe_enabled": self.failsafe_enabled_check.isChecked(),
            "signal_timeout_ms": self.signal_timeout_spin.value(),
            "failsafe_mode": self.failsafe_mode_combo.currentData(),
            "failsafe_position": self.failsafe_position_spin.value(),
            "failsafe_pwm": self.failsafe_pwm_spin.value(),
            "auto_recovery": self.auto_recovery_check.isChecked(),
        })

        return config

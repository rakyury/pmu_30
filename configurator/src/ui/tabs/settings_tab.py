"""
Settings Tab
System and device configuration settings with tabbed interface
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QLabel, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any


class SettingsTab(QWidget):
    """System settings configuration tab with tabbed interface."""

    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize user interface with tabs."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create tabs
        self._create_device_tab()
        self._create_can_tab()
        self._create_power_tab()
        self._create_system_tab()
        self._create_safety_tab()
        self._create_about_tab()

        main_layout.addWidget(self.tab_widget)

        # Legacy compatibility - keep old attribute for status bar
        self.can_bitrate_combo = self.can_a_bitrate_combo

    def _create_device_tab(self):
        """Create Device Information tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Device Information Group
        device_group = QGroupBox("Device Information")
        device_layout = QFormLayout()

        self.device_name_edit = QLineEdit()
        self.device_name_edit.setPlaceholderText("e.g., PMU-30 Main, PDU Front")
        self.device_name_edit.textChanged.connect(self._on_config_changed)
        device_layout.addRow("Device Name:", self.device_name_edit)

        self.device_description_edit = QLineEdit()
        self.device_description_edit.setPlaceholderText("Brief description of this device")
        self.device_description_edit.textChanged.connect(self._on_config_changed)
        device_layout.addRow("Description:", self.device_description_edit)

        self.serial_number_edit = QLineEdit()
        self.serial_number_edit.setPlaceholderText("Device serial number")
        self.serial_number_edit.textChanged.connect(self._on_config_changed)
        device_layout.addRow("Serial Number:", self.serial_number_edit)

        self.hardware_version_label = QLabel("N/A (read from device)")
        device_layout.addRow("Hardware Version:", self.hardware_version_label)

        self.firmware_version_label = QLabel("N/A (read from device)")
        device_layout.addRow("Firmware Version:", self.firmware_version_label)

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        layout.addStretch()

        self.tab_widget.addTab(tab, "Device")

    def _create_can_tab(self):
        """Create CAN Bus Settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # CAN A Bus Settings Group
        can_a_group = QGroupBox("CAN A Bus (FDCAN1)")
        can_a_layout = QFormLayout()

        self.can_a_enabled_check = QCheckBox("Enable CAN A")
        self.can_a_enabled_check.setChecked(True)
        self.can_a_enabled_check.toggled.connect(self._on_config_changed)
        can_a_layout.addRow("", self.can_a_enabled_check)

        self.can_a_bitrate_combo = QComboBox()
        self.can_a_bitrate_combo.addItems(["125 kbps", "250 kbps", "500 kbps", "1000 kbps"])
        self.can_a_bitrate_combo.setCurrentIndex(2)  # 500 kbps default
        self.can_a_bitrate_combo.currentTextChanged.connect(self._on_config_changed)
        can_a_layout.addRow("Bitrate:", self.can_a_bitrate_combo)

        self.can_a_fd_enabled_check = QCheckBox("Enable CAN FD")
        self.can_a_fd_enabled_check.setChecked(False)
        self.can_a_fd_enabled_check.setToolTip("Enable CAN FD mode (up to 8 Mbps data rate)")
        self.can_a_fd_enabled_check.toggled.connect(self._on_config_changed)
        can_a_layout.addRow("", self.can_a_fd_enabled_check)

        self.can_a_fd_bitrate_combo = QComboBox()
        self.can_a_fd_bitrate_combo.addItems(["1 Mbps", "2 Mbps", "4 Mbps", "5 Mbps", "8 Mbps"])
        self.can_a_fd_bitrate_combo.setCurrentIndex(1)  # 2 Mbps default
        self.can_a_fd_bitrate_combo.currentTextChanged.connect(self._on_config_changed)
        can_a_layout.addRow("FD Data Rate:", self.can_a_fd_bitrate_combo)

        self.can_a_terminator_check = QCheckBox("Enable Terminator (120Ω)")
        self.can_a_terminator_check.setChecked(False)
        self.can_a_terminator_check.toggled.connect(self._on_config_changed)
        can_a_layout.addRow("", self.can_a_terminator_check)

        self.can_a_listen_only_check = QCheckBox("Listen Only Mode")
        self.can_a_listen_only_check.setChecked(False)
        self.can_a_listen_only_check.toggled.connect(self._on_config_changed)
        can_a_layout.addRow("", self.can_a_listen_only_check)

        can_a_group.setLayout(can_a_layout)
        layout.addWidget(can_a_group)

        # CAN B Bus Settings Group
        can_b_group = QGroupBox("CAN B Bus (FDCAN2)")
        can_b_layout = QFormLayout()

        self.can_b_enabled_check = QCheckBox("Enable CAN B")
        self.can_b_enabled_check.setChecked(False)
        self.can_b_enabled_check.toggled.connect(self._on_config_changed)
        can_b_layout.addRow("", self.can_b_enabled_check)

        self.can_b_bitrate_combo = QComboBox()
        self.can_b_bitrate_combo.addItems(["125 kbps", "250 kbps", "500 kbps", "1000 kbps"])
        self.can_b_bitrate_combo.setCurrentIndex(2)  # 500 kbps default
        self.can_b_bitrate_combo.currentTextChanged.connect(self._on_config_changed)
        can_b_layout.addRow("Bitrate:", self.can_b_bitrate_combo)

        self.can_b_fd_enabled_check = QCheckBox("Enable CAN FD")
        self.can_b_fd_enabled_check.setChecked(False)
        self.can_b_fd_enabled_check.setToolTip("Enable CAN FD mode (up to 8 Mbps data rate)")
        self.can_b_fd_enabled_check.toggled.connect(self._on_config_changed)
        can_b_layout.addRow("", self.can_b_fd_enabled_check)

        self.can_b_fd_bitrate_combo = QComboBox()
        self.can_b_fd_bitrate_combo.addItems(["1 Mbps", "2 Mbps", "4 Mbps", "5 Mbps", "8 Mbps"])
        self.can_b_fd_bitrate_combo.setCurrentIndex(1)  # 2 Mbps default
        self.can_b_fd_bitrate_combo.currentTextChanged.connect(self._on_config_changed)
        can_b_layout.addRow("FD Data Rate:", self.can_b_fd_bitrate_combo)

        self.can_b_terminator_check = QCheckBox("Enable Terminator (120Ω)")
        self.can_b_terminator_check.setChecked(False)
        self.can_b_terminator_check.toggled.connect(self._on_config_changed)
        can_b_layout.addRow("", self.can_b_terminator_check)

        self.can_b_listen_only_check = QCheckBox("Listen Only Mode")
        self.can_b_listen_only_check.setChecked(False)
        self.can_b_listen_only_check.toggled.connect(self._on_config_changed)
        can_b_layout.addRow("", self.can_b_listen_only_check)

        can_b_group.setLayout(can_b_layout)
        layout.addWidget(can_b_group)

        # CAN General Settings
        can_general_group = QGroupBox("CAN General Settings")
        can_general_layout = QFormLayout()

        self.can_node_id_spin = QSpinBox()
        self.can_node_id_spin.setRange(0, 127)
        self.can_node_id_spin.setValue(1)
        self.can_node_id_spin.setToolTip("CAN Node ID for this device")
        self.can_node_id_spin.valueChanged.connect(self._on_config_changed)
        can_general_layout.addRow("Node ID:", self.can_node_id_spin)

        self.can_auto_retransmit_check = QCheckBox("Automatic Retransmission")
        self.can_auto_retransmit_check.setChecked(True)
        self.can_auto_retransmit_check.toggled.connect(self._on_config_changed)
        can_general_layout.addRow("", self.can_auto_retransmit_check)

        can_general_group.setLayout(can_general_layout)
        layout.addWidget(can_general_group)

        layout.addStretch()

        self.tab_widget.addTab(tab, "CAN Bus")

    def _create_power_tab(self):
        """Create Power Settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Power Settings Group
        power_group = QGroupBox("Power Settings")
        power_layout = QFormLayout()

        self.nominal_voltage_spin = QDoubleSpinBox()
        self.nominal_voltage_spin.setRange(6.0, 36.0)
        self.nominal_voltage_spin.setValue(12.0)
        self.nominal_voltage_spin.setSingleStep(0.1)
        self.nominal_voltage_spin.setDecimals(1)
        self.nominal_voltage_spin.setSuffix(" V")
        self.nominal_voltage_spin.valueChanged.connect(self._on_config_changed)
        power_layout.addRow("Nominal Voltage:", self.nominal_voltage_spin)

        self.low_voltage_warning_spin = QDoubleSpinBox()
        self.low_voltage_warning_spin.setRange(6.0, 36.0)
        self.low_voltage_warning_spin.setValue(10.5)
        self.low_voltage_warning_spin.setSingleStep(0.1)
        self.low_voltage_warning_spin.setDecimals(1)
        self.low_voltage_warning_spin.setSuffix(" V")
        self.low_voltage_warning_spin.setToolTip("Trigger warning when voltage drops below this level")
        self.low_voltage_warning_spin.valueChanged.connect(self._on_config_changed)
        power_layout.addRow("Low Voltage Warning:", self.low_voltage_warning_spin)

        self.low_voltage_cutoff_spin = QDoubleSpinBox()
        self.low_voltage_cutoff_spin.setRange(6.0, 36.0)
        self.low_voltage_cutoff_spin.setValue(9.0)
        self.low_voltage_cutoff_spin.setSingleStep(0.1)
        self.low_voltage_cutoff_spin.setDecimals(1)
        self.low_voltage_cutoff_spin.setSuffix(" V")
        self.low_voltage_cutoff_spin.setToolTip("Disable all outputs when voltage drops below this level")
        self.low_voltage_cutoff_spin.valueChanged.connect(self._on_config_changed)
        power_layout.addRow("Low Voltage Cutoff:", self.low_voltage_cutoff_spin)

        self.high_voltage_cutoff_spin = QDoubleSpinBox()
        self.high_voltage_cutoff_spin.setRange(6.0, 40.0)
        self.high_voltage_cutoff_spin.setValue(16.0)
        self.high_voltage_cutoff_spin.setSingleStep(0.1)
        self.high_voltage_cutoff_spin.setDecimals(1)
        self.high_voltage_cutoff_spin.setSuffix(" V")
        self.high_voltage_cutoff_spin.setToolTip("Disable all outputs when voltage exceeds this level")
        self.high_voltage_cutoff_spin.valueChanged.connect(self._on_config_changed)
        power_layout.addRow("High Voltage Cutoff:", self.high_voltage_cutoff_spin)

        power_group.setLayout(power_layout)
        layout.addWidget(power_group)

        # Standard CAN Stream Group
        stream_group = QGroupBox("Standard CAN Stream")
        stream_layout = QFormLayout()

        self.stream_enabled_check = QCheckBox("Enable Standard CAN Stream")
        self.stream_enabled_check.setChecked(False)
        self.stream_enabled_check.setToolTip(
            "Broadcast predefined PMU parameters over CAN bus.\n"
            "Standard CAN Stream format for real-time monitoring."
        )
        self.stream_enabled_check.toggled.connect(self._on_stream_enabled_changed)
        self.stream_enabled_check.toggled.connect(self._on_config_changed)
        stream_layout.addRow("", self.stream_enabled_check)

        self.stream_can_bus_combo = QComboBox()
        self.stream_can_bus_combo.addItems(["CAN A", "CAN B"])
        self.stream_can_bus_combo.setCurrentIndex(0)
        self.stream_can_bus_combo.setToolTip("CAN bus for stream transmission")
        self.stream_can_bus_combo.currentTextChanged.connect(self._on_config_changed)
        stream_layout.addRow("CAN Bus:", self.stream_can_bus_combo)

        # Base ID with hex input
        base_id_layout = QHBoxLayout()
        base_id_label = QLabel("0x")
        self.stream_base_id_edit = QLineEdit()
        self.stream_base_id_edit.setPlaceholderText("600")
        self.stream_base_id_edit.setText("600")
        self.stream_base_id_edit.setMaximumWidth(80)
        self.stream_base_id_edit.setToolTip(
            "Base CAN ID (hex). Stream uses 8 consecutive IDs:\n"
            "BaseID+0: System Status & Temperatures\n"
            "BaseID+1: Output States\n"
            "BaseID+2: Analog Inputs a1-a8\n"
            "BaseID+3: Analog Inputs a9-a16\n"
            "BaseID+4: Output Currents o1-o8\n"
            "BaseID+5: Output Currents o9-o16\n"
            "BaseID+6: Output Voltages o1-o8\n"
            "BaseID+7: Output Voltages o9-o16"
        )
        self.stream_base_id_edit.textChanged.connect(self._on_config_changed)
        base_id_layout.addWidget(base_id_label)
        base_id_layout.addWidget(self.stream_base_id_edit)
        base_id_layout.addStretch()
        stream_layout.addRow("Base ID:", base_id_layout)

        self.stream_extended_id_check = QCheckBox("Use Extended (29-bit) CAN IDs")
        self.stream_extended_id_check.setChecked(False)
        self.stream_extended_id_check.toggled.connect(self._on_config_changed)
        stream_layout.addRow("", self.stream_extended_id_check)

        self.stream_include_extended_check = QCheckBox("Include PMU-30 Extended Frames (BaseID+8 to +15)")
        self.stream_include_extended_check.setChecked(False)
        self.stream_include_extended_check.setToolTip(
            "Include additional 8 frames for PMU-30 specific data:\n"
            "BaseID+8:  Output States o17-o30\n"
            "BaseID+9:  Output Currents o17-o24\n"
            "BaseID+10: Output Currents o25-o30\n"
            "BaseID+11: Output Voltages o17-o24\n"
            "BaseID+12: Output Voltages o25-o30\n"
            "BaseID+13: Analog Inputs a17-a20\n"
            "BaseID+14: Digital Inputs\n"
            "BaseID+15: H-Bridge Status"
        )
        self.stream_include_extended_check.toggled.connect(self._on_config_changed)
        stream_layout.addRow("", self.stream_include_extended_check)

        # Stream info label
        stream_info = QLabel(
            "<i>Standard CAN Stream transmits PMU data at 20 Hz and 62.5 Hz rates.<br>"
            "Compatible with standard CAN loggers for real-time monitoring.</i>"
        )
        stream_info.setWordWrap(True)
        stream_info.setTextFormat(Qt.TextFormat.RichText)
        stream_layout.addRow("", stream_info)

        stream_group.setLayout(stream_layout)
        layout.addWidget(stream_group)

        # Initial state update
        self._on_stream_enabled_changed(False)

        layout.addStretch()

        self.tab_widget.addTab(tab, "Power & Stream")

    def _create_system_tab(self):
        """Create System Settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # System Settings Group
        system_group = QGroupBox("System Settings")
        system_layout = QFormLayout()

        self.units_combo = QComboBox()
        self.units_combo.addItems(["Metric (C, km/h)", "Imperial (F, mph)"])
        self.units_combo.setCurrentIndex(0)
        self.units_combo.currentTextChanged.connect(self._on_config_changed)
        system_layout.addRow("Units:", self.units_combo)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["Off", "Error", "Warning", "Info", "Debug"])
        self.log_level_combo.setCurrentIndex(2)  # Warning
        self.log_level_combo.setToolTip("System logging verbosity")
        self.log_level_combo.currentTextChanged.connect(self._on_config_changed)
        system_layout.addRow("Log Level:", self.log_level_combo)

        self.watchdog_timeout_spin = QSpinBox()
        self.watchdog_timeout_spin.setRange(100, 10000)
        self.watchdog_timeout_spin.setValue(1000)
        self.watchdog_timeout_spin.setSingleStep(100)
        self.watchdog_timeout_spin.setSuffix(" ms")
        self.watchdog_timeout_spin.setToolTip("Watchdog timer timeout")
        self.watchdog_timeout_spin.valueChanged.connect(self._on_config_changed)
        system_layout.addRow("Watchdog Timeout:", self.watchdog_timeout_spin)

        self.heartbeat_interval_spin = QSpinBox()
        self.heartbeat_interval_spin.setRange(100, 10000)
        self.heartbeat_interval_spin.setValue(1000)
        self.heartbeat_interval_spin.setSingleStep(100)
        self.heartbeat_interval_spin.setSuffix(" ms")
        self.heartbeat_interval_spin.setToolTip("CAN heartbeat message interval")
        self.heartbeat_interval_spin.valueChanged.connect(self._on_config_changed)
        system_layout.addRow("Heartbeat Interval:", self.heartbeat_interval_spin)

        system_group.setLayout(system_layout)
        layout.addWidget(system_group)

        layout.addStretch()

        self.tab_widget.addTab(tab, "System")

    def _create_safety_tab(self):
        """Create Safety Settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Safety Settings Group
        safety_group = QGroupBox("Safety Settings")
        safety_layout = QFormLayout()

        self.safe_state_combo = QComboBox()
        self.safe_state_combo.addItems([
            "All Outputs Off",
            "Maintain Last State",
            "Custom Profile"
        ])
        self.safe_state_combo.setCurrentIndex(0)
        self.safe_state_combo.setToolTip("Safe state when error occurs or connection lost")
        self.safe_state_combo.currentTextChanged.connect(self._on_config_changed)
        safety_layout.addRow("Safe State:", self.safe_state_combo)

        self.startup_delay_spin = QSpinBox()
        self.startup_delay_spin.setRange(0, 10000)
        self.startup_delay_spin.setValue(500)
        self.startup_delay_spin.setSingleStep(100)
        self.startup_delay_spin.setSuffix(" ms")
        self.startup_delay_spin.setToolTip("Delay before outputs are enabled after power-on")
        self.startup_delay_spin.valueChanged.connect(self._on_config_changed)
        safety_layout.addRow("Startup Delay:", self.startup_delay_spin)

        self.max_total_current_spin = QDoubleSpinBox()
        self.max_total_current_spin.setRange(1.0, 200.0)
        self.max_total_current_spin.setValue(100.0)
        self.max_total_current_spin.setSingleStep(1.0)
        self.max_total_current_spin.setDecimals(1)
        self.max_total_current_spin.setSuffix(" A")
        self.max_total_current_spin.setToolTip("Maximum total current draw from all outputs")
        self.max_total_current_spin.valueChanged.connect(self._on_config_changed)
        safety_layout.addRow("Max Total Current:", self.max_total_current_spin)

        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)

        # Calibration Group
        calibration_group = QGroupBox("Calibration")
        calibration_layout = QVBoxLayout()

        calib_info = QLabel(
            "Calibration values are read from and written to the device.\n"
            "Factory calibration is performed during production."
        )
        calib_info.setWordWrap(True)
        calibration_layout.addWidget(calib_info)

        calib_button_layout = QHBoxLayout()

        self.read_calibration_btn = QPushButton("Read from Device")
        self.read_calibration_btn.setEnabled(False)
        calib_button_layout.addWidget(self.read_calibration_btn)

        self.write_calibration_btn = QPushButton("Write to Device")
        self.write_calibration_btn.setEnabled(False)
        calib_button_layout.addWidget(self.write_calibration_btn)

        self.reset_calibration_btn = QPushButton("Reset to Factory")
        self.reset_calibration_btn.setEnabled(False)
        calib_button_layout.addWidget(self.reset_calibration_btn)

        calibration_layout.addLayout(calib_button_layout)
        calibration_group.setLayout(calibration_layout)
        layout.addWidget(calibration_group)

        layout.addStretch()

        self.tab_widget.addTab(tab, "Safety")

    def _create_about_tab(self):
        """Create About tab with device specifications."""
        tab = QWidget()

        # Use scroll area for long content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)

        # Device Specifications Group
        specs_group = QGroupBox("Device Specifications")
        specs_layout = QVBoxLayout()

        specs_text = QLabel(
            "<b>PMU-30 Power Management Unit</b><br>"
            "<br>"
            "<b>MCU:</b> STM32H723ZGT6 (Cortex-M7 @ 550MHz)<br>"
            "<br>"
            "<b>Power Outputs:</b><br>"
            "  30x High-Side Outputs (PROFET Smart Switches)<br>"
            "  Per-channel current sensing and protection<br>"
            "  PWM capable (1Hz - 20kHz)<br>"
            "  Soft-start and inrush current handling<br>"
            "  Automatic retry on overcurrent<br>"
            "<br>"
            "<b>H-Bridge Motor Drivers:</b><br>"
            "  4x Dual H-Bridge outputs<br>"
            "  Bidirectional motor control<br>"
            "  PWM speed control<br>"
            "<br>"
            "<b>Inputs:</b><br>"
            "  8x Digital Inputs (5-30V tolerant)<br>"
            "  20x Analog Inputs (0-5V, 12-bit ADC)<br>"
            "  Configurable pull-up/pull-down resistors<br>"
            "  Frequency measurement up to 20kHz<br>"
            "<br>"
            "<b>CAN Bus:</b><br>"
            "  2x CAN FD interfaces (FDCAN1, FDCAN2)<br>"
            "  Up to 8 Mbps data rate in FD mode<br>"
            "  Software-selectable 120 termination<br>"
            "  Isolated transceiver option<br>"
            "<br>"
            "<b>Logic Engine:</b><br>"
            "  256 Virtual Channels<br>"
            "  Boolean operations (AND, OR, XOR, etc.)<br>"
            "  Comparisons with hysteresis<br>"
            "  Timers and delays<br>"
            "  2D/3D Lookup tables<br>"
            "  Math operations<br>"
            "<br>"
            "<b>Advanced Features:</b><br>"
            "  PID Controllers<br>"
            "  Lua 5.4 Scripting engine<br>"
            "  Real-time data logging<br>"
            "  OTA firmware updates<br>"
            "<br>"
            "<b>Environmental:</b><br>"
            "  Operating voltage: 8-32V DC<br>"
            "  Operating temperature: -40C to +85C<br>"
            "  IP67 enclosure (optional)<br>"
        )
        specs_text.setWordWrap(True)
        specs_text.setTextFormat(Qt.TextFormat.RichText)
        specs_layout.addWidget(specs_text)

        specs_group.setLayout(specs_layout)
        layout.addWidget(specs_group)

        # About Group
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout()

        about_text = QLabel(
            "<b>PMU-30 Configurator</b><br>"
            "Version: 2.0.0<br>"
            "<br>"
            "2025 R2 m-sport. All rights reserved.<br>"
        )
        about_text.setWordWrap(True)
        about_text.setTextFormat(Qt.TextFormat.RichText)
        about_layout.addWidget(about_text)

        about_group.setLayout(about_layout)
        layout.addWidget(about_group)

        layout.addStretch()

        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        self.tab_widget.addTab(tab, "About")

    def _on_config_changed(self):
        """Handle configuration change."""
        self.configuration_changed.emit()

    def _on_stream_enabled_changed(self, enabled: bool):
        """Handle stream enable/disable state change."""
        self.stream_can_bus_combo.setEnabled(enabled)
        self.stream_base_id_edit.setEnabled(enabled)
        self.stream_extended_id_check.setEnabled(enabled)
        self.stream_include_extended_check.setEnabled(enabled)

    def load_configuration(self, config: dict):
        """Load settings from configuration."""
        settings = config.get("settings", {})

        # Device information
        device = settings.get("device", {})
        self.device_name_edit.setText(device.get("name", ""))
        self.device_description_edit.setText(device.get("description", ""))
        self.serial_number_edit.setText(device.get("serial_number", ""))

        # CAN A bus settings
        can_a = settings.get("can_a", settings.get("can", {}))  # Fallback to legacy "can" key
        self.can_a_enabled_check.setChecked(can_a.get("enabled", True))
        bitrate = can_a.get("bitrate", "500 kbps")
        index = self.can_a_bitrate_combo.findText(bitrate)
        if index >= 0:
            self.can_a_bitrate_combo.setCurrentIndex(index)
        self.can_a_fd_enabled_check.setChecked(can_a.get("fd_enabled", False))
        fd_bitrate = can_a.get("fd_bitrate", "2 Mbps")
        index = self.can_a_fd_bitrate_combo.findText(fd_bitrate)
        if index >= 0:
            self.can_a_fd_bitrate_combo.setCurrentIndex(index)
        self.can_a_terminator_check.setChecked(can_a.get("terminator", False))
        self.can_a_listen_only_check.setChecked(can_a.get("listen_only", False))

        # CAN B bus settings
        can_b = settings.get("can_b", {})
        self.can_b_enabled_check.setChecked(can_b.get("enabled", False))
        bitrate = can_b.get("bitrate", "500 kbps")
        index = self.can_b_bitrate_combo.findText(bitrate)
        if index >= 0:
            self.can_b_bitrate_combo.setCurrentIndex(index)
        self.can_b_fd_enabled_check.setChecked(can_b.get("fd_enabled", False))
        fd_bitrate = can_b.get("fd_bitrate", "2 Mbps")
        index = self.can_b_fd_bitrate_combo.findText(fd_bitrate)
        if index >= 0:
            self.can_b_fd_bitrate_combo.setCurrentIndex(index)
        self.can_b_terminator_check.setChecked(can_b.get("terminator", False))
        self.can_b_listen_only_check.setChecked(can_b.get("listen_only", False))

        # CAN general settings (legacy compatibility)
        can = settings.get("can", {})
        self.can_node_id_spin.setValue(can.get("node_id", 1))
        self.can_auto_retransmit_check.setChecked(can.get("auto_retransmit", True))

        # Standard CAN Stream settings
        stream = settings.get("standard_can_stream", {})
        stream_enabled = stream.get("enabled", False)
        self.stream_enabled_check.setChecked(stream_enabled)
        can_bus = stream.get("can_bus", 1)
        self.stream_can_bus_combo.setCurrentIndex(0 if can_bus == 1 else 1)
        base_id = stream.get("base_id", 0x600)
        self.stream_base_id_edit.setText(f"{base_id:X}")
        self.stream_extended_id_check.setChecked(stream.get("is_extended", False))
        self.stream_include_extended_check.setChecked(stream.get("include_extended_frames", False))
        self._on_stream_enabled_changed(stream_enabled)

        # Power settings
        power = settings.get("power", {})
        self.nominal_voltage_spin.setValue(power.get("nominal_voltage", 12.0))
        self.low_voltage_warning_spin.setValue(power.get("low_voltage_warning", 10.5))
        self.low_voltage_cutoff_spin.setValue(power.get("low_voltage_cutoff", 9.0))
        self.high_voltage_cutoff_spin.setValue(power.get("high_voltage_cutoff", 16.0))

        # System settings
        system = settings.get("system", {})
        units = system.get("units", "Metric (C, km/h)")
        index = self.units_combo.findText(units)
        if index >= 0:
            self.units_combo.setCurrentIndex(index)

        log_level = system.get("log_level", "Warning")
        index = self.log_level_combo.findText(log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)

        self.watchdog_timeout_spin.setValue(system.get("watchdog_timeout_ms", 1000))
        self.heartbeat_interval_spin.setValue(system.get("heartbeat_interval_ms", 1000))

        # Safety settings
        safety = settings.get("safety", {})
        safe_state = safety.get("safe_state", "All Outputs Off")
        index = self.safe_state_combo.findText(safe_state)
        if index >= 0:
            self.safe_state_combo.setCurrentIndex(index)

        self.startup_delay_spin.setValue(safety.get("startup_delay_ms", 500))
        self.max_total_current_spin.setValue(safety.get("max_total_current_a", 100.0))

    def get_configuration(self) -> dict:
        """Get current settings configuration."""
        return {
            "settings": {
                "device": {
                    "name": self.device_name_edit.text(),
                    "description": self.device_description_edit.text(),
                    "serial_number": self.serial_number_edit.text()
                },
                "can_a": {
                    "enabled": self.can_a_enabled_check.isChecked(),
                    "bitrate": self.can_a_bitrate_combo.currentText(),
                    "fd_enabled": self.can_a_fd_enabled_check.isChecked(),
                    "fd_bitrate": self.can_a_fd_bitrate_combo.currentText(),
                    "terminator": self.can_a_terminator_check.isChecked(),
                    "listen_only": self.can_a_listen_only_check.isChecked()
                },
                "can_b": {
                    "enabled": self.can_b_enabled_check.isChecked(),
                    "bitrate": self.can_b_bitrate_combo.currentText(),
                    "fd_enabled": self.can_b_fd_enabled_check.isChecked(),
                    "fd_bitrate": self.can_b_fd_bitrate_combo.currentText(),
                    "terminator": self.can_b_terminator_check.isChecked(),
                    "listen_only": self.can_b_listen_only_check.isChecked()
                },
                "can": {
                    "node_id": self.can_node_id_spin.value(),
                    "auto_retransmit": self.can_auto_retransmit_check.isChecked()
                },
                "standard_can_stream": {
                    "enabled": self.stream_enabled_check.isChecked(),
                    "can_bus": 1 if self.stream_can_bus_combo.currentIndex() == 0 else 2,
                    "base_id": int(self.stream_base_id_edit.text() or "600", 16),
                    "is_extended": self.stream_extended_id_check.isChecked(),
                    "include_extended_frames": self.stream_include_extended_check.isChecked()
                },
                "power": {
                    "nominal_voltage": self.nominal_voltage_spin.value(),
                    "low_voltage_warning": self.low_voltage_warning_spin.value(),
                    "low_voltage_cutoff": self.low_voltage_cutoff_spin.value(),
                    "high_voltage_cutoff": self.high_voltage_cutoff_spin.value()
                },
                "system": {
                    "units": self.units_combo.currentText(),
                    "log_level": self.log_level_combo.currentText(),
                    "watchdog_timeout_ms": self.watchdog_timeout_spin.value(),
                    "heartbeat_interval_ms": self.heartbeat_interval_spin.value()
                },
                "safety": {
                    "safe_state": self.safe_state_combo.currentText(),
                    "startup_delay_ms": self.startup_delay_spin.value(),
                    "max_total_current_a": self.max_total_current_spin.value()
                }
            }
        }

    def reset_to_defaults(self):
        """Reset to default settings."""
        self.device_name_edit.clear()
        self.device_description_edit.clear()
        self.serial_number_edit.clear()

        # CAN A defaults
        self.can_a_enabled_check.setChecked(True)
        self.can_a_bitrate_combo.setCurrentIndex(2)  # 500 kbps
        self.can_a_fd_enabled_check.setChecked(False)
        self.can_a_fd_bitrate_combo.setCurrentIndex(1)  # 2 Mbps
        self.can_a_terminator_check.setChecked(False)
        self.can_a_listen_only_check.setChecked(False)

        # CAN B defaults
        self.can_b_enabled_check.setChecked(False)
        self.can_b_bitrate_combo.setCurrentIndex(2)  # 500 kbps
        self.can_b_fd_enabled_check.setChecked(False)
        self.can_b_fd_bitrate_combo.setCurrentIndex(1)  # 2 Mbps
        self.can_b_terminator_check.setChecked(False)
        self.can_b_listen_only_check.setChecked(False)

        # CAN general defaults
        self.can_node_id_spin.setValue(1)
        self.can_auto_retransmit_check.setChecked(True)

        # Standard CAN Stream defaults
        self.stream_enabled_check.setChecked(False)
        self.stream_can_bus_combo.setCurrentIndex(0)  # CAN A
        self.stream_base_id_edit.setText("600")
        self.stream_extended_id_check.setChecked(False)
        self.stream_include_extended_check.setChecked(False)
        self._on_stream_enabled_changed(False)

        self.nominal_voltage_spin.setValue(12.0)
        self.low_voltage_warning_spin.setValue(10.5)
        self.low_voltage_cutoff_spin.setValue(9.0)
        self.high_voltage_cutoff_spin.setValue(16.0)

        self.units_combo.setCurrentIndex(0)
        self.log_level_combo.setCurrentIndex(2)
        self.watchdog_timeout_spin.setValue(1000)
        self.heartbeat_interval_spin.setValue(1000)

        self.safe_state_combo.setCurrentIndex(0)
        self.startup_delay_spin.setValue(500)
        self.max_total_current_spin.setValue(100.0)

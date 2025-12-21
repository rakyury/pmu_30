"""
Settings Tab
System and device configuration settings
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QTextEdit, QLabel, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any


class SettingsTab(QWidget):
    """System settings configuration tab."""

    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize user interface."""
        # Create scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container widget
        container = QWidget()
        layout = QVBoxLayout(container)

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

        # CAN Bus Settings Group
        can_group = QGroupBox("CAN Bus Settings")
        can_layout = QFormLayout()

        self.can_bitrate_combo = QComboBox()
        self.can_bitrate_combo.addItems(["125 kbps", "250 kbps", "500 kbps", "1000 kbps"])
        self.can_bitrate_combo.setCurrentIndex(2)  # 500 kbps default
        self.can_bitrate_combo.currentTextChanged.connect(self._on_config_changed)
        can_layout.addRow("CAN Bitrate:", self.can_bitrate_combo)

        self.can_node_id_spin = QSpinBox()
        self.can_node_id_spin.setRange(0, 127)
        self.can_node_id_spin.setValue(1)
        self.can_node_id_spin.setToolTip("CAN Node ID for this device")
        self.can_node_id_spin.valueChanged.connect(self._on_config_changed)
        can_layout.addRow("Node ID:", self.can_node_id_spin)

        self.can_terminator_check = QCheckBox("Enable CAN Terminator (120Ω)")
        self.can_terminator_check.setChecked(False)
        self.can_terminator_check.toggled.connect(self._on_config_changed)
        can_layout.addRow("", self.can_terminator_check)

        self.can_listen_only_check = QCheckBox("Listen Only Mode")
        self.can_listen_only_check.setChecked(False)
        self.can_listen_only_check.setToolTip("Device will not transmit on CAN bus")
        self.can_listen_only_check.toggled.connect(self._on_config_changed)
        can_layout.addRow("", self.can_listen_only_check)

        self.can_auto_retransmit_check = QCheckBox("Automatic Retransmission")
        self.can_auto_retransmit_check.setChecked(True)
        self.can_auto_retransmit_check.toggled.connect(self._on_config_changed)
        can_layout.addRow("", self.can_auto_retransmit_check)

        can_group.setLayout(can_layout)
        layout.addWidget(can_group)

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

        # System Settings Group
        system_group = QGroupBox("System Settings")
        system_layout = QFormLayout()

        self.units_combo = QComboBox()
        self.units_combo.addItems(["Metric (°C, km/h)", "Imperial (°F, mph)"])
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

        self.read_calibration_btn = QPushButton("Read Calibration from Device")
        self.read_calibration_btn.setEnabled(False)
        calib_button_layout.addWidget(self.read_calibration_btn)

        self.write_calibration_btn = QPushButton("Write Calibration to Device")
        self.write_calibration_btn.setEnabled(False)
        calib_button_layout.addWidget(self.write_calibration_btn)

        self.reset_calibration_btn = QPushButton("Reset to Factory")
        self.reset_calibration_btn.setEnabled(False)
        calib_button_layout.addWidget(self.reset_calibration_btn)

        calibration_layout.addLayout(calib_button_layout)
        calibration_group.setLayout(calibration_layout)
        layout.addWidget(calibration_group)

        # About Group
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout()

        about_text = QLabel(
            "<b>PMU-30 Power Distribution Module Configurator</b><br>"
            "<br>"
            "Version: 1.0.0<br>"
            "© 2025 R2 m-sport. All rights reserved.<br>"
            "<br>"
            "<b>Device Specifications:</b><br>"
            "• 30 PROFET High-Side Outputs<br>"
            "• 4 Dual H-Bridge Motor Drivers<br>"
            "• 20 Analog/Digital Inputs<br>"
            "• CAN FD Interface<br>"
            "• Logic Engine with 256 Virtual Channels<br>"
            "• PID Controllers<br>"
            "• LUA 5.4 Scripting<br>"
            "<br>"
            "<b>Features:</b><br>"
            "• Current monitoring and protection<br>"
            "• Thermal management<br>"
            "• Diagnostic feedback<br>"
            "• Flexible configuration<br>"
        )
        about_text.setWordWrap(True)
        about_text.setTextFormat(Qt.TextFormat.RichText)
        about_layout.addWidget(about_text)

        about_group.setLayout(about_layout)
        layout.addWidget(about_group)

        layout.addStretch()

        # Set container as scroll widget
        scroll.setWidget(container)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _on_config_changed(self):
        """Handle configuration change."""
        self.configuration_changed.emit()

    def load_configuration(self, config: dict):
        """Load settings from configuration."""
        settings = config.get("settings", {})

        # Device information
        device = settings.get("device", {})
        self.device_name_edit.setText(device.get("name", ""))
        self.device_description_edit.setText(device.get("description", ""))
        self.serial_number_edit.setText(device.get("serial_number", ""))

        # CAN bus settings
        can = settings.get("can", {})
        bitrate = can.get("bitrate", "500 kbps")
        index = self.can_bitrate_combo.findText(bitrate)
        if index >= 0:
            self.can_bitrate_combo.setCurrentIndex(index)

        self.can_node_id_spin.setValue(can.get("node_id", 1))
        self.can_terminator_check.setChecked(can.get("terminator", False))
        self.can_listen_only_check.setChecked(can.get("listen_only", False))
        self.can_auto_retransmit_check.setChecked(can.get("auto_retransmit", True))

        # Power settings
        power = settings.get("power", {})
        self.nominal_voltage_spin.setValue(power.get("nominal_voltage", 12.0))
        self.low_voltage_warning_spin.setValue(power.get("low_voltage_warning", 10.5))
        self.low_voltage_cutoff_spin.setValue(power.get("low_voltage_cutoff", 9.0))
        self.high_voltage_cutoff_spin.setValue(power.get("high_voltage_cutoff", 16.0))

        # System settings
        system = settings.get("system", {})
        units = system.get("units", "Metric (°C, km/h)")
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
                "can": {
                    "bitrate": self.can_bitrate_combo.currentText(),
                    "node_id": self.can_node_id_spin.value(),
                    "terminator": self.can_terminator_check.isChecked(),
                    "listen_only": self.can_listen_only_check.isChecked(),
                    "auto_retransmit": self.can_auto_retransmit_check.isChecked()
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

        self.can_bitrate_combo.setCurrentIndex(2)  # 500 kbps
        self.can_node_id_spin.setValue(1)
        self.can_terminator_check.setChecked(False)
        self.can_listen_only_check.setChecked(False)
        self.can_auto_retransmit_check.setChecked(True)

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

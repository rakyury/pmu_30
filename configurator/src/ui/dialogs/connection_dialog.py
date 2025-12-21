"""
Connection Dialog for PMU-30 Device
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any, Optional


class ConnectionDialog(QDialog):
    """Dialog for configuring device connection."""

    connection_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to PMU-30")
        self.setModal(True)
        self.resize(450, 350)

        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Header
        header = QLabel("<b>Connect to PMU-30 Device</b>")
        header.setStyleSheet("font-size: 14px; padding: 5px;")
        layout.addWidget(header)

        # Connection type group
        type_group = QGroupBox("Connection Type")
        type_layout = QFormLayout()

        self.connection_type_combo = QComboBox()
        self.connection_type_combo.addItems(["USB Serial", "WiFi", "Bluetooth", "CAN Bus"])
        self.connection_type_combo.currentTextChanged.connect(self._on_type_changed)
        type_layout.addRow("Type:", self.connection_type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Parameters group (dynamic based on connection type)
        self.params_group = QGroupBox("Connection Parameters")
        self.params_layout = QFormLayout()
        self.params_group.setLayout(self.params_layout)
        layout.addWidget(self.params_group)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._on_test)
        button_layout.addWidget(self.test_btn)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.accept)
        self.connect_btn.setDefault(True)
        button_layout.addWidget(self.connect_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize with USB Serial
        self._on_type_changed("USB Serial")

    def _clear_params_layout(self):
        """Clear all widgets from parameters layout."""
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)

    def _on_type_changed(self, connection_type: str):
        """Handle connection type change."""
        self._clear_params_layout()

        if connection_type == "USB Serial":
            self._setup_usb_params()
        elif connection_type == "WiFi":
            self._setup_wifi_params()
        elif connection_type == "Bluetooth":
            self._setup_bluetooth_params()
        elif connection_type == "CAN Bus":
            self._setup_can_params()

    def _setup_usb_params(self):
        """Setup USB Serial parameters."""
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        # Add common ports
        self.port_combo.addItems([
            "COM1", "COM2", "COM3", "COM4", "COM5",
            "/dev/ttyUSB0", "/dev/ttyACM0"
        ])
        self.params_layout.addRow("Serial Port:", self.port_combo)

        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems([
            "9600", "19200", "38400", "57600", "115200",
            "230400", "460800", "921600"
        ])
        self.baudrate_combo.setCurrentText("115200")
        self.params_layout.addRow("Baud Rate:", self.baudrate_combo)

        refresh_btn = QPushButton("Refresh Ports")
        refresh_btn.clicked.connect(self._refresh_serial_ports)
        self.params_layout.addRow("", refresh_btn)

        self.status_label.setText("Select serial port and click Connect")

    def _setup_wifi_params(self):
        """Setup WiFi parameters."""
        self.wifi_ip_edit = QLineEdit()
        self.wifi_ip_edit.setPlaceholderText("192.168.4.1")
        self.wifi_ip_edit.setText("192.168.4.1")
        self.params_layout.addRow("IP Address:", self.wifi_ip_edit)

        self.wifi_port_spin = QSpinBox()
        self.wifi_port_spin.setRange(1, 65535)
        self.wifi_port_spin.setValue(8080)
        self.params_layout.addRow("Port:", self.wifi_port_spin)

        self.wifi_ssid_edit = QLineEdit()
        self.wifi_ssid_edit.setPlaceholderText("PMU30-XXXXXX")
        self.wifi_ssid_edit.setEnabled(False)
        self.params_layout.addRow("SSID (info):", self.wifi_ssid_edit)

        self.status_label.setText("Default IP: 192.168.4.1 (AP mode)")

    def _setup_bluetooth_params(self):
        """Setup Bluetooth parameters."""
        self.bt_device_combo = QComboBox()
        self.bt_device_combo.setEditable(True)
        self.bt_device_combo.addItem("PMU30-XXXXXX")
        self.params_layout.addRow("Device:", self.bt_device_combo)

        self.bt_address_edit = QLineEdit()
        self.bt_address_edit.setPlaceholderText("00:11:22:33:44:55")
        self.bt_address_edit.setEnabled(False)
        self.params_layout.addRow("MAC Address:", self.bt_address_edit)

        scan_btn = QPushButton("Scan for Devices")
        scan_btn.clicked.connect(self._scan_bluetooth)
        self.params_layout.addRow("", scan_btn)

        self.status_label.setText("Scan for nearby PMU-30 devices")

    def _setup_can_params(self):
        """Setup CAN Bus parameters."""
        self.can_interface_combo = QComboBox()
        self.can_interface_combo.addItems(["can0", "can1", "vcan0"])
        self.params_layout.addRow("Interface:", self.can_interface_combo)

        self.can_bitrate_combo = QComboBox()
        self.can_bitrate_combo.addItems([
            "125000", "250000", "500000", "1000000"
        ])
        self.can_bitrate_combo.setCurrentText("500000")
        self.params_layout.addRow("Bitrate:", self.can_bitrate_combo)

        self.can_id_spin = QSpinBox()
        self.can_id_spin.setRange(0, 0x7FF)
        self.can_id_spin.setValue(0x100)
        self.can_id_spin.setDisplayIntegerBase(16)
        self.can_id_spin.setPrefix("0x")
        self.params_layout.addRow("Device ID:", self.can_id_spin)

        self.status_label.setText("CAN interface for embedded systems")

    def _refresh_serial_ports(self):
        """Refresh available serial ports."""
        try:
            import serial.tools.list_ports
            ports = [port.device for port in serial.tools.list_ports.comports()]

            current = self.port_combo.currentText()
            self.port_combo.clear()
            self.port_combo.addItems(ports if ports else ["No ports found"])

            # Restore previous selection if still available
            if current in ports:
                self.port_combo.setCurrentText(current)

            self.status_label.setText(f"Found {len(ports)} serial port(s)")
        except ImportError:
            self.status_label.setText("pyserial not installed")

    def _scan_bluetooth(self):
        """Scan for Bluetooth devices."""
        self.status_label.setText("Scanning for Bluetooth devices...")
        # TODO: Implement Bluetooth scanning
        self.status_label.setText("Bluetooth scanning not yet implemented")

    def _on_test(self):
        """Test connection."""
        self.status_label.setText("Testing connection...")
        # TODO: Implement connection test
        self.status_label.setText("Connection test not yet implemented")

    def get_connection_config(self) -> Dict[str, Any]:
        """Get connection configuration."""
        connection_type = self.connection_type_combo.currentText()

        config = {
            "type": connection_type
        }

        if connection_type == "USB Serial":
            config["port"] = self.port_combo.currentText()
            config["baudrate"] = int(self.baudrate_combo.currentText())

        elif connection_type == "WiFi":
            config["ip"] = self.wifi_ip_edit.text()
            config["port"] = self.wifi_port_spin.value()

        elif connection_type == "Bluetooth":
            config["device"] = self.bt_device_combo.currentText()
            config["address"] = self.bt_address_edit.text()

        elif connection_type == "CAN Bus":
            config["interface"] = self.can_interface_combo.currentText()
            config["bitrate"] = int(self.can_bitrate_combo.currentText())
            config["device_id"] = self.can_id_spin.value()

        return config

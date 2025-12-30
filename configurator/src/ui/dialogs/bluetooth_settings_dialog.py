"""Bluetooth Settings Dialog for PMU-30 Configurator"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QDialogButtonBox, QTabWidget, QWidget,
    QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class BluetoothSettingsDialog(QDialog):
    """Dialog for configuring Bluetooth settings."""

    # Bluetooth modes
    BT_MODES = [
        ("Bluetooth Low Energy (BLE)", "ble"),
        ("Bluetooth Classic (SPP)", "classic"),
        ("Dual Mode (BLE + Classic)", "dual"),
    ]

    # Security levels
    SECURITY_TYPES = [
        ("No Security", "none"),
        ("Pairing Only", "pair"),
        ("Authentication (PIN)", "auth"),
        ("Secure (Bonding + Encryption)", "secure"),
    ]

    def __init__(
        self,
        parent=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Bluetooth Settings")
        self.setMinimumWidth(500)

        self._config = config or {}
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Enable Bluetooth checkbox
        self.bt_enabled = QCheckBox("Enable Bluetooth")
        layout.addWidget(self.bt_enabled)

        # Tabs for different settings
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # General tab
        general_tab = QWidget()
        self.tabs.addTab(general_tab, "General")
        self._setup_general_tab(general_tab)

        # Classic (SPP) tab
        classic_tab = QWidget()
        self.tabs.addTab(classic_tab, "Classic (SPP)")
        self._setup_classic_tab(classic_tab)

        # BLE tab
        ble_tab = QWidget()
        self.tabs.addTab(ble_tab, "BLE")
        self._setup_ble_tab(ble_tab)

        # Telemetry tab
        telemetry_tab = QWidget()
        self.tabs.addTab(telemetry_tab, "Telemetry")
        self._setup_telemetry_tab(telemetry_tab)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Connect enable checkbox
        self.bt_enabled.toggled.connect(self._on_bt_enabled_changed)

    def _setup_general_tab(self, parent: QWidget):
        """Setup the General settings tab."""
        layout = QFormLayout(parent)

        # Bluetooth Mode
        self.mode_combo = QComboBox()
        for label, value in self.BT_MODES:
            self.mode_combo.addItem(label, value)
        layout.addRow("Bluetooth Mode:", self.mode_combo)

        # Mode description
        mode_info = QLabel(
            "<small>"
            "<b>BLE:</b> Low power, modern devices (phones, tablets)<br>"
            "<b>Classic:</b> Serial Port Profile for legacy devices<br>"
            "<b>Dual:</b> Both modes active (higher power consumption)"
            "</small>"
        )
        mode_info.setWordWrap(True)
        layout.addRow(mode_info)

    def _setup_classic_tab(self, parent: QWidget):
        """Setup the Bluetooth Classic (SPP) settings tab."""
        layout = QFormLayout(parent)

        # Device Name
        self.classic_name_edit = QLineEdit()
        self.classic_name_edit.setMaxLength(31)
        self.classic_name_edit.setPlaceholderText("PMU30")
        layout.addRow("Device Name:", self.classic_name_edit)

        # PIN Code
        self.classic_pin_edit = QLineEdit()
        self.classic_pin_edit.setMaxLength(16)
        self.classic_pin_edit.setPlaceholderText("1234")
        layout.addRow("PIN Code:", self.classic_pin_edit)

        # Security
        self.classic_security_combo = QComboBox()
        for label, value in self.SECURITY_TYPES:
            self.classic_security_combo.addItem(label, value)
        self.classic_security_combo.setCurrentIndex(2)  # Auth default
        layout.addRow("Security:", self.classic_security_combo)

        # Discoverable
        self.classic_discoverable = QCheckBox("Device is discoverable")
        self.classic_discoverable.setChecked(True)
        layout.addRow("", self.classic_discoverable)

        # Connectable
        self.classic_connectable = QCheckBox("Accept incoming connections")
        self.classic_connectable.setChecked(True)
        layout.addRow("", self.classic_connectable)

        # Max connections
        self.classic_max_conn_spin = QSpinBox()
        self.classic_max_conn_spin.setRange(1, 7)
        self.classic_max_conn_spin.setValue(1)
        layout.addRow("Max Connections:", self.classic_max_conn_spin)

    def _setup_ble_tab(self, parent: QWidget):
        """Setup the BLE settings tab."""
        layout = QFormLayout(parent)

        # Device Name
        self.ble_name_edit = QLineEdit()
        self.ble_name_edit.setMaxLength(31)
        self.ble_name_edit.setPlaceholderText("PMU30")
        layout.addRow("Device Name:", self.ble_name_edit)

        # Advertising enabled
        self.ble_advertising = QCheckBox("Enable advertising")
        self.ble_advertising.setChecked(True)
        layout.addRow("", self.ble_advertising)

        # Advertising interval
        self.ble_adv_interval_spin = QSpinBox()
        self.ble_adv_interval_spin.setRange(20, 10240)
        self.ble_adv_interval_spin.setValue(100)
        self.ble_adv_interval_spin.setSuffix(" ms")
        layout.addRow("Advertising Interval:", self.ble_adv_interval_spin)

        # Security
        self.ble_security_combo = QComboBox()
        for label, value in self.SECURITY_TYPES:
            self.ble_security_combo.addItem(label, value)
        self.ble_security_combo.setCurrentIndex(1)  # Pairing default
        layout.addRow("Security:", self.ble_security_combo)

        # Require bonding
        self.ble_require_bonding = QCheckBox("Require device bonding")
        layout.addRow("", self.ble_require_bonding)

        # Connection parameters group
        conn_group = QGroupBox("Connection Parameters")
        conn_layout = QFormLayout(conn_group)

        self.ble_conn_min_spin = QSpinBox()
        self.ble_conn_min_spin.setRange(6, 3200)
        self.ble_conn_min_spin.setValue(20)
        self.ble_conn_min_spin.setToolTip("1.25ms units (20 = 25ms)")
        conn_layout.addRow("Min Interval:", self.ble_conn_min_spin)

        self.ble_conn_max_spin = QSpinBox()
        self.ble_conn_max_spin.setRange(6, 3200)
        self.ble_conn_max_spin.setValue(40)
        self.ble_conn_max_spin.setToolTip("1.25ms units (40 = 50ms)")
        conn_layout.addRow("Max Interval:", self.ble_conn_max_spin)

        self.ble_supervision_spin = QSpinBox()
        self.ble_supervision_spin.setRange(10, 3200)
        self.ble_supervision_spin.setValue(400)
        self.ble_supervision_spin.setToolTip("10ms units (400 = 4000ms)")
        conn_layout.addRow("Supervision Timeout:", self.ble_supervision_spin)

        layout.addRow(conn_group)

    def _setup_telemetry_tab(self, parent: QWidget):
        """Setup the Telemetry service settings tab."""
        layout = QFormLayout(parent)

        # Enable telemetry
        self.telemetry_enabled = QCheckBox("Enable Telemetry Service")
        self.telemetry_enabled.setChecked(True)
        layout.addRow("", self.telemetry_enabled)

        # Update rate
        self.telemetry_rate_spin = QSpinBox()
        self.telemetry_rate_spin.setRange(10, 10000)
        self.telemetry_rate_spin.setValue(100)
        self.telemetry_rate_spin.setSuffix(" ms")
        layout.addRow("Update Rate:", self.telemetry_rate_spin)

        # Notify on changes only
        self.telemetry_notify_changes = QCheckBox("Notify on value changes only")
        self.telemetry_notify_changes.setToolTip(
            "Only send notifications when values change instead of periodic updates"
        )
        layout.addRow("", self.telemetry_notify_changes)

        # Info label
        info = QLabel(
            "<small>"
            "The telemetry service exposes PMU channel values via BLE characteristics. "
            "Connected devices can subscribe to notifications to receive real-time updates."
            "</small>"
        )
        info.setWordWrap(True)
        layout.addRow(info)

    def _on_bt_enabled_changed(self, enabled: bool):
        """Handle Bluetooth enabled checkbox toggle."""
        self.tabs.setEnabled(enabled)

    def _load_config(self):
        """Load configuration into the dialog."""
        bt = self._config.get("bluetooth", {})

        # General
        self.bt_enabled.setChecked(bt.get("enabled", False))
        mode = bt.get("mode", "ble")
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == mode:
                self.mode_combo.setCurrentIndex(i)
                break

        # Classic
        classic = bt.get("classic", {})
        self.classic_name_edit.setText(classic.get("device_name", "PMU30"))
        self.classic_pin_edit.setText(classic.get("pin", "1234"))
        self.classic_discoverable.setChecked(classic.get("discoverable", True))
        self.classic_connectable.setChecked(classic.get("connectable", True))
        self.classic_max_conn_spin.setValue(classic.get("max_connections", 1))
        security = classic.get("security", "auth")
        for i in range(self.classic_security_combo.count()):
            if self.classic_security_combo.itemData(i) == security:
                self.classic_security_combo.setCurrentIndex(i)
                break

        # BLE
        ble = bt.get("ble", {})
        self.ble_name_edit.setText(ble.get("device_name", "PMU30"))
        self.ble_advertising.setChecked(ble.get("advertising", True))
        self.ble_adv_interval_spin.setValue(ble.get("adv_interval_ms", 100))
        self.ble_conn_min_spin.setValue(ble.get("conn_interval_min", 20))
        self.ble_conn_max_spin.setValue(ble.get("conn_interval_max", 40))
        self.ble_supervision_spin.setValue(ble.get("supervision_timeout", 400))
        self.ble_require_bonding.setChecked(ble.get("require_bonding", False))
        security = ble.get("security", "pair")
        for i in range(self.ble_security_combo.count()):
            if self.ble_security_combo.itemData(i) == security:
                self.ble_security_combo.setCurrentIndex(i)
                break

        # Telemetry
        telemetry = bt.get("telemetry", {})
        self.telemetry_enabled.setChecked(telemetry.get("enabled", True))
        self.telemetry_rate_spin.setValue(telemetry.get("update_rate_ms", 100))
        self.telemetry_notify_changes.setChecked(telemetry.get("notify_changes", False))

        # Update enabled states
        self._on_bt_enabled_changed(self.bt_enabled.isChecked())

    def _validate(self) -> bool:
        """Validate the configuration."""
        if not self.bt_enabled.isChecked():
            return True

        mode = self.mode_combo.currentData()

        # Validate Classic settings if Classic mode enabled
        if mode in ("classic", "dual"):
            if len(self.classic_name_edit.text().strip()) == 0:
                QMessageBox.warning(
                    self, "Validation Error",
                    "Classic device name cannot be empty."
                )
                return False

        # Validate BLE settings if BLE mode enabled
        if mode in ("ble", "dual"):
            if len(self.ble_name_edit.text().strip()) == 0:
                QMessageBox.warning(
                    self, "Validation Error",
                    "BLE device name cannot be empty."
                )
                return False

            # Validate connection parameters
            if self.ble_conn_min_spin.value() > self.ble_conn_max_spin.value():
                QMessageBox.warning(
                    self, "Validation Error",
                    "BLE min connection interval cannot be greater than max."
                )
                return False

        return True

    def _on_accept(self):
        """Handle dialog accept."""
        if self._validate():
            self.accept()

    def get_config(self) -> Dict[str, Any]:
        """Get the Bluetooth configuration."""
        return {
            "bluetooth": {
                "enabled": self.bt_enabled.isChecked(),
                "mode": self.mode_combo.currentData(),
                "classic": {
                    "device_name": self.classic_name_edit.text() or "PMU30",
                    "pin": self.classic_pin_edit.text() or "1234",
                    "security": self.classic_security_combo.currentData(),
                    "discoverable": self.classic_discoverable.isChecked(),
                    "connectable": self.classic_connectable.isChecked(),
                    "max_connections": self.classic_max_conn_spin.value(),
                },
                "ble": {
                    "device_name": self.ble_name_edit.text() or "PMU30",
                    "advertising": self.ble_advertising.isChecked(),
                    "adv_interval_ms": self.ble_adv_interval_spin.value(),
                    "security": self.ble_security_combo.currentData(),
                    "require_bonding": self.ble_require_bonding.isChecked(),
                    "conn_interval_min": self.ble_conn_min_spin.value(),
                    "conn_interval_max": self.ble_conn_max_spin.value(),
                    "supervision_timeout": self.ble_supervision_spin.value(),
                },
                "telemetry": {
                    "enabled": self.telemetry_enabled.isChecked(),
                    "update_rate_ms": self.telemetry_rate_spin.value(),
                    "notify_changes": self.telemetry_notify_changes.isChecked(),
                },
            }
        }

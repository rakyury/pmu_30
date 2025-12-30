"""WiFi Settings Dialog for PMU-30 Configurator"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QDialogButtonBox, QTabWidget, QWidget,
    QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class WiFiSettingsDialog(QDialog):
    """Dialog for configuring WiFi settings."""

    # WiFi modes
    WIFI_MODES = [
        ("Access Point", "ap"),
        ("Station (Client)", "sta"),
        ("AP + Station", "ap_sta"),
    ]

    # Security types
    SECURITY_TYPES = [
        ("Open (No Security)", "open"),
        ("WPA", "wpa"),
        ("WPA2", "wpa2"),
        ("WPA3", "wpa3"),
    ]

    def __init__(
        self,
        parent=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("WiFi Settings")
        self.setMinimumWidth(500)

        self._config = config or {}
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Enable WiFi checkbox
        self.wifi_enabled = QCheckBox("Enable WiFi")
        layout.addWidget(self.wifi_enabled)

        # Tabs for different settings
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # General tab
        general_tab = QWidget()
        self.tabs.addTab(general_tab, "General")
        self._setup_general_tab(general_tab)

        # Access Point tab
        ap_tab = QWidget()
        self.tabs.addTab(ap_tab, "Access Point")
        self._setup_ap_tab(ap_tab)

        # Station tab
        sta_tab = QWidget()
        self.tabs.addTab(sta_tab, "Station (Client)")
        self._setup_sta_tab(sta_tab)

        # Web Server tab
        web_tab = QWidget()
        self.tabs.addTab(web_tab, "Web Server")
        self._setup_web_tab(web_tab)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Connect enable checkbox
        self.wifi_enabled.toggled.connect(self._on_wifi_enabled_changed)

    def _setup_general_tab(self, parent: QWidget):
        """Setup the General settings tab."""
        layout = QFormLayout(parent)

        # WiFi Mode
        self.mode_combo = QComboBox()
        for label, value in self.WIFI_MODES:
            self.mode_combo.addItem(label, value)
        layout.addRow("WiFi Mode:", self.mode_combo)

        # Hostname
        self.hostname_edit = QLineEdit()
        self.hostname_edit.setMaxLength(31)
        self.hostname_edit.setPlaceholderText("pmu30")
        layout.addRow("Hostname:", self.hostname_edit)

        # Mode description
        mode_info = QLabel(
            "<small>"
            "<b>Access Point:</b> PMU creates its own WiFi network<br>"
            "<b>Station:</b> PMU connects to your existing WiFi<br>"
            "<b>AP + Station:</b> Both modes active simultaneously"
            "</small>"
        )
        mode_info.setWordWrap(True)
        layout.addRow(mode_info)

    def _setup_ap_tab(self, parent: QWidget):
        """Setup the Access Point settings tab."""
        layout = QFormLayout(parent)

        # SSID
        self.ap_ssid_edit = QLineEdit()
        self.ap_ssid_edit.setMaxLength(32)
        self.ap_ssid_edit.setPlaceholderText("PMU30-Config")
        layout.addRow("Network Name (SSID):", self.ap_ssid_edit)

        # Password
        self.ap_password_edit = QLineEdit()
        self.ap_password_edit.setMaxLength(64)
        self.ap_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ap_password_edit.setPlaceholderText("Minimum 8 characters")
        layout.addRow("Password:", self.ap_password_edit)

        # Show password checkbox
        self.ap_show_password = QCheckBox("Show password")
        self.ap_show_password.toggled.connect(
            lambda checked: self.ap_password_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        layout.addRow("", self.ap_show_password)

        # Security
        self.ap_security_combo = QComboBox()
        for label, value in self.SECURITY_TYPES:
            self.ap_security_combo.addItem(label, value)
        self.ap_security_combo.setCurrentIndex(2)  # WPA2 default
        layout.addRow("Security:", self.ap_security_combo)

        # Channel
        self.ap_channel_spin = QSpinBox()
        self.ap_channel_spin.setRange(1, 14)
        self.ap_channel_spin.setValue(6)
        layout.addRow("WiFi Channel:", self.ap_channel_spin)

        # Hidden SSID
        self.ap_hidden_check = QCheckBox("Hidden network")
        layout.addRow("", self.ap_hidden_check)

        # Max clients
        self.ap_max_clients_spin = QSpinBox()
        self.ap_max_clients_spin.setRange(1, 8)
        self.ap_max_clients_spin.setValue(4)
        layout.addRow("Max Clients:", self.ap_max_clients_spin)

    def _setup_sta_tab(self, parent: QWidget):
        """Setup the Station (Client) settings tab."""
        layout = QFormLayout(parent)

        # SSID
        self.sta_ssid_edit = QLineEdit()
        self.sta_ssid_edit.setMaxLength(32)
        self.sta_ssid_edit.setPlaceholderText("Your WiFi network name")
        layout.addRow("Network Name (SSID):", self.sta_ssid_edit)

        # Password
        self.sta_password_edit = QLineEdit()
        self.sta_password_edit.setMaxLength(64)
        self.sta_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Password:", self.sta_password_edit)

        # Show password
        self.sta_show_password = QCheckBox("Show password")
        self.sta_show_password.toggled.connect(
            lambda checked: self.sta_password_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        layout.addRow("", self.sta_show_password)

        # Auto reconnect
        self.sta_auto_reconnect = QCheckBox("Auto-reconnect on disconnect")
        self.sta_auto_reconnect.setChecked(True)
        layout.addRow("", self.sta_auto_reconnect)

        # DHCP
        self.sta_dhcp_check = QCheckBox("Use DHCP (automatic IP)")
        self.sta_dhcp_check.setChecked(True)
        layout.addRow("", self.sta_dhcp_check)

        # Static IP group
        self.static_ip_group = QGroupBox("Static IP Configuration")
        self.static_ip_group.setEnabled(False)
        static_layout = QFormLayout(self.static_ip_group)

        self.sta_ip_edit = QLineEdit()
        self.sta_ip_edit.setPlaceholderText("192.168.1.100")
        static_layout.addRow("IP Address:", self.sta_ip_edit)

        self.sta_gateway_edit = QLineEdit()
        self.sta_gateway_edit.setPlaceholderText("192.168.1.1")
        static_layout.addRow("Gateway:", self.sta_gateway_edit)

        self.sta_netmask_edit = QLineEdit()
        self.sta_netmask_edit.setPlaceholderText("255.255.255.0")
        static_layout.addRow("Subnet Mask:", self.sta_netmask_edit)

        layout.addRow(self.static_ip_group)

        # Connect DHCP toggle
        self.sta_dhcp_check.toggled.connect(
            lambda checked: self.static_ip_group.setEnabled(not checked)
        )

    def _setup_web_tab(self, parent: QWidget):
        """Setup the Web Server settings tab."""
        layout = QFormLayout(parent)

        # Enable web server
        self.web_enabled_check = QCheckBox("Enable Web Server")
        self.web_enabled_check.setChecked(True)
        layout.addRow("", self.web_enabled_check)

        # HTTP port
        self.web_http_port_spin = QSpinBox()
        self.web_http_port_spin.setRange(1, 65535)
        self.web_http_port_spin.setValue(80)
        layout.addRow("HTTP Port:", self.web_http_port_spin)

        # WebSocket port
        self.web_ws_port_spin = QSpinBox()
        self.web_ws_port_spin.setRange(1, 65535)
        self.web_ws_port_spin.setValue(81)
        layout.addRow("WebSocket Port:", self.web_ws_port_spin)

        # Authentication group
        self.auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout(self.auth_group)

        self.web_auth_enabled = QCheckBox("Require login")
        auth_layout.addRow("", self.web_auth_enabled)

        self.web_username_edit = QLineEdit()
        self.web_username_edit.setPlaceholderText("admin")
        self.web_username_edit.setEnabled(False)
        auth_layout.addRow("Username:", self.web_username_edit)

        self.web_password_edit = QLineEdit()
        self.web_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.web_password_edit.setEnabled(False)
        auth_layout.addRow("Password:", self.web_password_edit)

        layout.addRow(self.auth_group)

        # Connect auth toggle
        self.web_auth_enabled.toggled.connect(self._on_auth_enabled_changed)

    def _on_wifi_enabled_changed(self, enabled: bool):
        """Handle WiFi enabled checkbox toggle."""
        self.tabs.setEnabled(enabled)

    def _on_auth_enabled_changed(self, enabled: bool):
        """Handle auth enabled checkbox toggle."""
        self.web_username_edit.setEnabled(enabled)
        self.web_password_edit.setEnabled(enabled)

    def _load_config(self):
        """Load configuration into the dialog."""
        wifi = self._config.get("wifi", {})

        # General
        self.wifi_enabled.setChecked(wifi.get("enabled", False))
        mode = wifi.get("mode", "ap")
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == mode:
                self.mode_combo.setCurrentIndex(i)
                break
        self.hostname_edit.setText(wifi.get("hostname", "pmu30"))

        # Access Point
        ap = wifi.get("ap", {})
        self.ap_ssid_edit.setText(ap.get("ssid", "PMU30-Config"))
        self.ap_password_edit.setText(ap.get("password", ""))
        security = ap.get("security", "wpa2")
        for i in range(self.ap_security_combo.count()):
            if self.ap_security_combo.itemData(i) == security:
                self.ap_security_combo.setCurrentIndex(i)
                break
        self.ap_channel_spin.setValue(ap.get("channel", 6))
        self.ap_hidden_check.setChecked(ap.get("hidden", False))
        self.ap_max_clients_spin.setValue(ap.get("max_clients", 4))

        # Station
        sta = wifi.get("sta", {})
        self.sta_ssid_edit.setText(sta.get("ssid", ""))
        self.sta_password_edit.setText(sta.get("password", ""))
        self.sta_auto_reconnect.setChecked(sta.get("auto_reconnect", True))
        self.sta_dhcp_check.setChecked(sta.get("dhcp", True))
        self.sta_ip_edit.setText(sta.get("ip", ""))
        self.sta_gateway_edit.setText(sta.get("gateway", ""))
        self.sta_netmask_edit.setText(sta.get("netmask", ""))

        # Web
        web = wifi.get("web", {})
        self.web_enabled_check.setChecked(web.get("enabled", True))
        self.web_http_port_spin.setValue(web.get("http_port", 80))
        self.web_ws_port_spin.setValue(web.get("ws_port", 81))
        self.web_auth_enabled.setChecked(web.get("auth_enabled", False))
        self.web_username_edit.setText(web.get("username", ""))
        self.web_password_edit.setText(web.get("password", ""))

        # Update enabled states
        self._on_wifi_enabled_changed(self.wifi_enabled.isChecked())
        self._on_auth_enabled_changed(self.web_auth_enabled.isChecked())

    def _validate(self) -> bool:
        """Validate the configuration."""
        if not self.wifi_enabled.isChecked():
            return True

        mode = self.mode_combo.currentData()

        # Validate AP settings if AP mode enabled
        if mode in ("ap", "ap_sta"):
            if len(self.ap_ssid_edit.text().strip()) == 0:
                QMessageBox.warning(
                    self, "Validation Error",
                    "Access Point SSID cannot be empty."
                )
                return False

            security = self.ap_security_combo.currentData()
            if security != "open":
                if len(self.ap_password_edit.text()) < 8:
                    QMessageBox.warning(
                        self, "Validation Error",
                        "Access Point password must be at least 8 characters."
                    )
                    return False

        # Validate STA settings if STA mode enabled
        if mode in ("sta", "ap_sta"):
            if len(self.sta_ssid_edit.text().strip()) == 0:
                QMessageBox.warning(
                    self, "Validation Error",
                    "Station network SSID cannot be empty."
                )
                return False

        return True

    def _on_accept(self):
        """Handle dialog accept."""
        if self._validate():
            self.accept()

    def get_config(self) -> Dict[str, Any]:
        """Get the WiFi configuration."""
        return {
            "wifi": {
                "enabled": self.wifi_enabled.isChecked(),
                "mode": self.mode_combo.currentData(),
                "hostname": self.hostname_edit.text() or "pmu30",
                "ap": {
                    "ssid": self.ap_ssid_edit.text() or "PMU30-Config",
                    "password": self.ap_password_edit.text(),
                    "security": self.ap_security_combo.currentData(),
                    "channel": self.ap_channel_spin.value(),
                    "hidden": self.ap_hidden_check.isChecked(),
                    "max_clients": self.ap_max_clients_spin.value(),
                },
                "sta": {
                    "ssid": self.sta_ssid_edit.text(),
                    "password": self.sta_password_edit.text(),
                    "auto_reconnect": self.sta_auto_reconnect.isChecked(),
                    "dhcp": self.sta_dhcp_check.isChecked(),
                    "ip": self.sta_ip_edit.text(),
                    "gateway": self.sta_gateway_edit.text(),
                    "netmask": self.sta_netmask_edit.text(),
                },
                "web": {
                    "enabled": self.web_enabled_check.isChecked(),
                    "http_port": self.web_http_port_spin.value(),
                    "ws_port": self.web_ws_port_spin.value(),
                    "auth_enabled": self.web_auth_enabled.isChecked(),
                    "username": self.web_username_edit.text(),
                    "password": self.web_password_edit.text(),
                },
            }
        }

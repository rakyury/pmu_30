"""
PMU-30 Configurator - Main Window

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QMenuBar, QToolBar, QStatusBar,
    QPushButton, QLabel, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

from .tabs.outputs_tab import OutputsTab
from .tabs.inputs_tab import InputsTab
from .tabs.can_tab import CANTab
from .tabs.logic_tab import LogicTab
from .tabs.hbridge_tab import HBridgeTab
from .tabs.lua_tab import LuaTab
from .tabs.monitoring_tab import MonitoringTab
from .tabs.settings_tab import SettingsTab

from controllers.device_controller import DeviceController


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for PMU-30 Configurator."""

    # Signals
    device_connected = pyqtSignal()
    device_disconnected = pyqtSignal()
    configuration_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.device_controller = DeviceController()
        self.config_modified = False

        self.init_ui()
        self.setup_connections()
        self.setup_toolbar()
        self.setup_menubar()
        self.setup_statusbar()

        logger.info("Main window initialized")

    def init_ui(self):
        """Initialize user interface."""

        self.setWindowTitle("PMU-30 Configurator - R2 m-sport")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Device connection panel
        connection_panel = self.create_connection_panel()
        main_layout.addWidget(connection_panel)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # Create tabs
        self.outputs_tab = OutputsTab()
        self.inputs_tab = InputsTab()
        self.can_tab = CANTab()
        self.logic_tab = LogicTab()
        self.hbridge_tab = HBridgeTab()
        self.lua_tab = LuaTab()
        self.monitoring_tab = MonitoringTab()
        self.settings_tab = SettingsTab()

        # Add tabs
        self.tab_widget.addTab(self.monitoring_tab, "Monitor")
        self.tab_widget.addTab(self.outputs_tab, "Outputs (30)")
        self.tab_widget.addTab(self.hbridge_tab, "H-Bridge (4x)")
        self.tab_widget.addTab(self.inputs_tab, "Inputs (20)")
        self.tab_widget.addTab(self.can_tab, "CAN Bus")
        self.tab_widget.addTab(self.logic_tab, "Logic Engine")
        self.tab_widget.addTab(self.lua_tab, "Lua Scripts")
        self.tab_widget.addTab(self.settings_tab, "Settings")

        main_layout.addWidget(self.tab_widget)

    def create_connection_panel(self):
        """Create device connection panel."""

        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-bottom: 1px solid #3a3a3a;
            }
            QLabel {
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #14b8a6;
            }
            QPushButton:pressed {
                background-color: #0a5d61;
            }
            QPushButton:disabled {
                background-color: #4a4a4a;
                color: #888888;
            }
            QComboBox {
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #4a4a4a;
                padding: 6px;
                border-radius: 4px;
            }
        """)

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 8, 16, 8)

        # PMU-30 Logo/Title
        title_label = QLabel("PMU-30 Configurator")
        title_label.setStyleSheet("font-size: 18px; color: #14b8a6;")
        layout.addWidget(title_label)

        layout.addStretch()

        # Connection type
        self.connection_type_combo = QComboBox()
        self.connection_type_combo.addItems(["USB", "WiFi", "Bluetooth"])
        layout.addWidget(QLabel("Connection:"))
        layout.addWidget(self.connection_type_combo)

        # Port/Address selection
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(200)
        layout.addWidget(QLabel("Port/Address:"))
        layout.addWidget(self.port_combo)

        # Refresh ports button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_btn)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)

        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #ef4444; font-size: 16px;")
        layout.addWidget(self.status_indicator)

        self.status_label = QLabel("Disconnected")
        layout.addWidget(self.status_label)

        return panel

    def setup_connections(self):
        """Setup signal/slot connections."""

        # Device controller signals
        self.device_controller.connected.connect(self.on_device_connected)
        self.device_controller.disconnected.connect(self.on_device_disconnected)
        self.device_controller.error.connect(self.on_device_error)

        # Configuration change tracking
        self.outputs_tab.configuration_changed.connect(self.on_configuration_changed)
        self.inputs_tab.configuration_changed.connect(self.on_configuration_changed)
        self.can_tab.configuration_changed.connect(self.on_configuration_changed)
        self.logic_tab.configuration_changed.connect(self.on_configuration_changed)
        self.hbridge_tab.configuration_changed.connect(self.on_configuration_changed)

        # Refresh ports on startup
        QTimer.singleShot(100, self.refresh_ports)

    def setup_toolbar(self):
        """Setup main toolbar."""

        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # File operations
        new_action = QAction("New Config", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_configuration)
        toolbar.addAction(new_action)

        open_action = QAction("Open Config", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_configuration)
        toolbar.addAction(open_action)

        save_action = QAction("Save Config", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_configuration)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # Device operations
        read_action = QAction("Read from Device", self)
        read_action.triggered.connect(self.read_from_device)
        toolbar.addAction(read_action)

        write_action = QAction("Write to Device", self)
        write_action.triggered.connect(self.write_to_device)
        toolbar.addAction(write_action)

        toolbar.addSeparator()

        # Firmware update
        firmware_action = QAction("Update Firmware", self)
        firmware_action.triggered.connect(self.update_firmware)
        toolbar.addAction(firmware_action)

    def setup_menubar(self):
        """Setup menu bar."""

        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        new_action = QAction("New Configuration", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_configuration)
        file_menu.addAction(new_action)

        open_action = QAction("Open Configuration", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_configuration)
        file_menu.addAction(open_action)

        save_action = QAction("Save Configuration", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_configuration_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        import_dbc_action = QAction("Import DBC...", self)
        import_dbc_action.triggered.connect(self.import_dbc)
        file_menu.addAction(import_dbc_action)

        export_dbc_action = QAction("Export DBC...", self)
        export_dbc_action.triggered.connect(self.export_dbc)
        file_menu.addAction(export_dbc_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Device menu
        device_menu = menubar.addMenu("Device")

        connect_action = QAction("Connect", self)
        connect_action.triggered.connect(self.toggle_connection)
        device_menu.addAction(connect_action)

        read_action = QAction("Read Configuration", self)
        read_action.triggered.connect(self.read_from_device)
        device_menu.addAction(read_action)

        write_action = QAction("Write Configuration", self)
        write_action.triggered.connect(self.write_to_device)
        device_menu.addAction(write_action)

        device_menu.addSeparator()

        update_fw_action = QAction("Update Firmware", self)
        update_fw_action.triggered.connect(self.update_firmware)
        device_menu.addAction(update_fw_action)

        reset_action = QAction("Reset to Defaults", self)
        reset_action.triggered.connect(self.reset_device)
        device_menu.addAction(reset_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        can_monitor_action = QAction("CAN Monitor", self)
        can_monitor_action.triggered.connect(self.open_can_monitor)
        tools_menu.addAction(can_monitor_action)

        data_logger_action = QAction("Data Logger", self)
        data_logger_action.triggered.connect(self.open_data_logger)
        tools_menu.addAction(data_logger_action)

        live_tuning_action = QAction("Live Tuning", self)
        live_tuning_action.triggered.connect(self.open_live_tuning)
        tools_menu.addAction(live_tuning_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        docs_action = QAction("Documentation", self)
        docs_action.triggered.connect(self.open_documentation)
        help_menu.addAction(docs_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_statusbar(self):
        """Setup status bar."""

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")

    def refresh_ports(self):
        """Refresh available ports/devices."""

        connection_type = self.connection_type_combo.currentText()
        self.port_combo.clear()

        if connection_type == "USB":
            ports = self.device_controller.get_available_serial_ports()
            self.port_combo.addItems(ports)
        elif connection_type == "WiFi":
            self.port_combo.addItem("PMU30-XXXXXX (192.168.4.1)")
        elif connection_type == "Bluetooth":
            devices = self.device_controller.get_available_bluetooth_devices()
            self.port_combo.addItems(devices)

    def toggle_connection(self):
        """Toggle device connection."""

        if self.device_controller.is_connected():
            self.device_controller.disconnect()
        else:
            connection_type = self.connection_type_combo.currentText()
            port = self.port_combo.currentText()

            if not port:
                QMessageBox.warning(self, "No Device", "Please select a device/port")
                return

            self.device_controller.connect(connection_type, port)

    def on_device_connected(self):
        """Handle device connected event."""

        self.status_indicator.setStyleSheet("color: #10b981; font-size: 16px;")
        self.status_label.setText("Connected")
        self.connect_btn.setText("Disconnect")
        self.statusbar.showMessage("Device connected successfully")

        logger.info("Device connected")

    def on_device_disconnected(self):
        """Handle device disconnected event."""

        self.status_indicator.setStyleSheet("color: #ef4444; font-size: 16px;")
        self.status_label.setText("Disconnected")
        self.connect_btn.setText("Connect")
        self.statusbar.showMessage("Device disconnected")

        logger.info("Device disconnected")

    def on_device_error(self, error_msg):
        """Handle device error."""

        QMessageBox.critical(self, "Device Error", error_msg)
        logger.error(f"Device error: {error_msg}")

    def on_configuration_changed(self):
        """Handle configuration changes."""

        self.config_modified = True
        self.setWindowTitle("PMU-30 Configurator - R2 m-sport *")

    # File operations
    def new_configuration(self):
        """Create new configuration."""
        logger.info("New configuration")
        # TODO: Implement

    def open_configuration(self):
        """Open configuration file."""
        logger.info("Open configuration")
        # TODO: Implement

    def save_configuration(self):
        """Save configuration."""
        logger.info("Save configuration")
        # TODO: Implement

    def save_configuration_as(self):
        """Save configuration as new file."""
        logger.info("Save configuration as")
        # TODO: Implement

    def import_dbc(self):
        """Import DBC file."""
        logger.info("Import DBC")
        # TODO: Implement

    def export_dbc(self):
        """Export DBC file."""
        logger.info("Export DBC")
        # TODO: Implement

    # Device operations
    def read_from_device(self):
        """Read configuration from device."""
        logger.info("Read from device")
        # TODO: Implement

    def write_to_device(self):
        """Write configuration to device."""
        logger.info("Write to device")
        # TODO: Implement

    def update_firmware(self):
        """Update device firmware."""
        logger.info("Update firmware")
        # TODO: Implement

    def reset_device(self):
        """Reset device to factory defaults."""
        logger.info("Reset device")
        # TODO: Implement

    # Tools
    def open_can_monitor(self):
        """Open CAN bus monitor."""
        logger.info("Open CAN monitor")
        # TODO: Implement

    def open_data_logger(self):
        """Open data logger."""
        logger.info("Open data logger")
        # TODO: Implement

    def open_live_tuning(self):
        """Open live tuning interface."""
        logger.info("Open live tuning")
        # TODO: Implement

    # Help
    def open_documentation(self):
        """Open documentation."""
        logger.info("Open documentation")
        # TODO: Implement

    def show_about(self):
        """Show about dialog."""

        about_text = f"""
        <h2>PMU-30 Configurator</h2>
        <p>Version 1.0.0</p>
        <p>Professional 30-channel Power Distribution Module</p>
        <br>
        <p><b>Owner:</b> R2 m-sport</p>
        <p><b>Date:</b> 2025</p>
        <br>
        <p>© 2025 R2 m-sport. All rights reserved.</p>
        """

        QMessageBox.about(self, "About PMU-30 Configurator", about_text)

    def closeEvent(self, event):
        """Handle window close event."""

        if self.config_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Configuration has been modified. Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                self.save_configuration()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

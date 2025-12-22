"""
PMU-30 Configurator - Main Window

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QMenuBar, QToolBar, QStatusBar,
    QPushButton, QLabel, QComboBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QScreen

from .tabs.outputs_tab import OutputsTab
from .tabs.inputs_tab import InputsTab
from .tabs.can_tab import CANTab
from .tabs.logic_tab import LogicTab
from .tabs.hbridge_tab import HBridgeTab
from .tabs.lua_tab import LuaTab
from .tabs.monitoring_tab import MonitoringTab
from .tabs.settings_tab import SettingsTab
from .tabs.pid_tab import PIDTab

from .dialogs.connection_dialog import ConnectionDialog

from controllers.device_controller import DeviceController
from models.config_manager import ConfigManager
from utils.theme import ThemeManager


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for PMU-30 Configurator."""

    # Signals
    device_connected = pyqtSignal()
    device_disconnected = pyqtSignal()
    configuration_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Initialize configuration manager
        self.config_manager = ConfigManager()

        # Initialize device controller
        self.device_controller = DeviceController()
        self.config_modified = False

        # Dark mode state
        self.dark_mode = True

        self.init_ui()
        self.setup_connections()
        self.setup_toolbar()
        self.setup_menubar()
        self.setup_statusbar()

        # Apply dark theme by default
        self.apply_theme()

        logger.info("Main window initialized")

    def init_ui(self):
        """Initialize user interface."""

        self.setWindowTitle("PMU-30 Configurator - R2 m-sport")

        # Set window size to 70% of screen size
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        width = int(screen_geometry.width() * 0.7)
        height = int(screen_geometry.height() * 0.7)

        # Center window on screen
        x = (screen_geometry.width() - width) // 2
        y = (screen_geometry.height() - height) // 2
        self.setGeometry(x, y, width, height)

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
        self.pid_tab = PIDTab()
        self.wiper_tab = SettingsTab()  # Placeholder for wiper tab
        self.turn_signal_tab = SettingsTab()  # Placeholder for turn signal tab
        self.lua_tab = LuaTab()
        self.monitoring_tab = MonitoringTab()
        self.settings_tab = SettingsTab()

        # Connect configuration changed signals
        self.inputs_tab.configuration_changed.connect(self._on_config_changed)
        self.outputs_tab.configuration_changed.connect(self._on_config_changed)

        # Add tabs
        self.tab_widget.addTab(self.monitoring_tab, "Monitor")
        self.tab_widget.addTab(self.outputs_tab, "Outputs (30)")
        self.tab_widget.addTab(self.hbridge_tab, "H-Bridge (4x)")
        self.tab_widget.addTab(self.inputs_tab, "Inputs (20)")
        self.tab_widget.addTab(self.can_tab, "CAN Bus")
        self.tab_widget.addTab(self.logic_tab, "Logic Engine")
        self.tab_widget.addTab(self.pid_tab, "PID Controllers")
        self.tab_widget.addTab(self.lua_tab, "Lua Scripts")
        self.tab_widget.addTab(self.settings_tab, "Settings")

        main_layout.addWidget(self.tab_widget)

    def create_connection_panel(self):
        """Create device connection panel."""

        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 4)

        # PMU-30 Logo/Title
        title_label = QLabel("<b>PMU-30 Configurator</b>")
        title_label.setStyleSheet("font-size: 16px; padding: 4px;")
        layout.addWidget(title_label)

        layout.addStretch()

        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #ef4444; font-size: 16px;")
        layout.addWidget(self.status_indicator)

        self.status_label = QLabel("Disconnected")
        layout.addWidget(self.status_label)

        # Connect button - opens dialog
        self.connect_btn = QPushButton("Connect to Device...")
        self.connect_btn.clicked.connect(self.show_connection_dialog)
        layout.addWidget(self.connect_btn)

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
        self.pid_tab.configuration_changed.connect(self.on_configuration_changed)
        self.lua_tab.configuration_changed.connect(self.on_configuration_changed)
        self.settings_tab.configuration_changed.connect(self.on_configuration_changed)

    def setup_toolbar(self):
        """Toolbar removed - all functions moved to menu."""
        pass

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

        connect_action = QAction("Connect...", self)
        connect_action.setShortcut("Ctrl+D")
        connect_action.triggered.connect(self.show_connection_dialog)
        device_menu.addAction(connect_action)

        disconnect_action = QAction("Disconnect", self)
        disconnect_action.triggered.connect(self.disconnect_device)
        device_menu.addAction(disconnect_action)

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

        # View menu
        view_menu = menubar.addMenu("View")

        self.dark_mode_action = QAction("Dark Mode", self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setChecked(True)
        self.dark_mode_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.dark_mode_action)

        view_menu.addSeparator()

        # Style submenu
        style_menu = view_menu.addMenu("Application Style")

        # Get available styles
        from PyQt6.QtWidgets import QStyleFactory
        available_styles = QStyleFactory.keys()

        # Create action group for exclusive selection
        from PyQt6.QtGui import QActionGroup
        self.style_group = QActionGroup(self)
        self.style_group.setExclusive(True)

        # Add "Fluent Design" (our custom theme) option
        fluent_action = QAction("Fluent Design (Custom)", self)
        fluent_action.setCheckable(True)
        fluent_action.setChecked(True)  # Default
        fluent_action.triggered.connect(lambda: self.change_style("Fluent"))
        self.style_group.addAction(fluent_action)
        style_menu.addAction(fluent_action)

        style_menu.addSeparator()

        # Add Qt built-in styles
        for style_name in available_styles:
            action = QAction(style_name, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, s=style_name: self.change_style(s))
            self.style_group.addAction(action)
            style_menu.addAction(action)

        self.current_style = "Fluent"

        # Help menu
        help_menu = menubar.addMenu("Help")

        docs_action = QAction("Documentation", self)
        docs_action.triggered.connect(self.open_documentation)
        help_menu.addAction(docs_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_statusbar(self):
        """Setup status bar with detailed system information."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Main status message (left)
        self.status_message = QLabel("Ready")
        self.statusbar.addWidget(self.status_message)

        # Separator
        separator1 = QLabel(" | ")
        self.statusbar.addWidget(separator1)

        # CAN Bus Status
        self.can_status_label = QLabel("CAN: Idle")
        self.can_status_label.setToolTip("CAN Bus Status: Bitrate, TX/RX counters, errors")
        self.statusbar.addWidget(self.can_status_label)

        separator2 = QLabel(" | ")
        self.statusbar.addWidget(separator2)

        # Channel Status
        self.channels_label = QLabel("Outputs: 0/30 | Inputs: 0/20")
        self.channels_label.setToolTip("Active channels status")
        self.statusbar.addWidget(self.channels_label)

        separator3 = QLabel(" | ")
        self.statusbar.addWidget(separator3)

        # H-Bridge Status
        self.hbridge_label = QLabel("H-Bridge: 0/4")
        self.hbridge_label.setToolTip("Active H-Bridge channels")
        self.statusbar.addWidget(self.hbridge_label)

        separator4 = QLabel(" | ")
        self.statusbar.addWidget(separator4)

        # Voltage Status
        self.voltage_label = QLabel("Voltage: N/A")
        self.voltage_label.setToolTip("System voltage")
        self.statusbar.addWidget(self.voltage_label)

        separator5 = QLabel(" | ")
        self.statusbar.addWidget(separator5)

        # Temperature Status
        self.temp_label = QLabel("Temp: N/A")
        self.temp_label.setToolTip("Device temperature")
        self.statusbar.addWidget(self.temp_label)

        separator6 = QLabel(" | ")
        self.statusbar.addWidget(separator6)

        # Current Total
        self.current_label = QLabel("Current: 0.0A")
        self.current_label.setToolTip("Total current draw")
        self.statusbar.addWidget(self.current_label)

        # Stretch to push remaining items to right
        self.statusbar.addPermanentWidget(QLabel(""))

        # Configuration status (right side)
        self.config_status_label = QLabel("Not Modified")
        self.statusbar.addPermanentWidget(self.config_status_label)

        # Start status update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_statusbar)
        self.status_timer.start(500)  # Update every 500ms

    def _update_statusbar(self):
        """Update status bar with current system state."""
        # Update channel counts from tabs
        try:
            # Outputs
            output_count = sum(1 for out in self.outputs_tab.outputs if out.get("enabled", False))
            # Inputs
            input_count = sum(1 for inp in self.inputs_tab.inputs if inp.get("enabled", False))
            self.channels_label.setText(f"Outputs: {output_count}/30 | Inputs: {input_count}/20")

            # H-Bridge
            hbridge_count = sum(1 for hb in self.hbridge_tab.hbridge_channels if hb.get("enabled", False))
            self.hbridge_label.setText(f"H-Bridge: {hbridge_count}/4")

            # Configuration status
            if self.config_manager.is_modified():
                self.config_status_label.setText("Modified *")
                self.config_status_label.setStyleSheet("color: #f59e0b;")
            else:
                self.config_status_label.setText("Saved")
                self.config_status_label.setStyleSheet("color: #10b981;")

            # CAN status (will be updated when device is connected)
            # For now, show configured bitrate
            can_bitrate = self.settings_tab.can_bitrate_combo.currentText()
            self.can_status_label.setText(f"CAN: {can_bitrate}")

        except Exception as e:
            logger.error(f"Error updating status bar: {e}")

    def _on_config_changed(self):
        """Handle configuration changes from tabs."""
        self.config_manager.modified = True

    def show_connection_dialog(self):
        """Show connection dialog."""
        dialog = ConnectionDialog(self)

        if dialog.exec():
            config = dialog.get_connection_config()
            logger.info(f"Connection config: {config}")

            # Connect to device
            connection_type = config.get("type", "USB Serial")

            if connection_type == "USB Serial":
                port = config.get("port", "")
                baudrate = config.get("baudrate", 115200)
                if port:
                    self.device_controller.connect(connection_type, port)
            elif connection_type == "WiFi":
                ip = config.get("ip", "192.168.4.1")
                port = config.get("port", 8080)
                self.device_controller.connect(connection_type, f"{ip}:{port}")
            elif connection_type == "Bluetooth":
                device = config.get("device", "")
                if device:
                    self.device_controller.connect(connection_type, device)
            elif connection_type == "CAN Bus":
                interface = config.get("interface", "can0")
                self.device_controller.connect(connection_type, interface)

    def disconnect_device(self):
        """Disconnect from device."""
        if self.device_controller.is_connected():
            self.device_controller.disconnect()

    def apply_theme(self):
        """Apply current theme."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            ThemeManager.toggle_theme(app, self.dark_mode)

    def toggle_theme(self):
        """Toggle between dark and light theme."""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        logger.info(f"Theme changed to: {'dark' if self.dark_mode else 'light'}")

    def change_style(self, style_name: str):
        """Change application style."""
        from PyQt6.QtWidgets import QApplication, QStyleFactory

        app = QApplication.instance()
        if not app:
            return

        self.current_style = style_name

        if style_name == "Fluent":
            # Apply our custom Fluent Design theme
            app.setStyle("Fusion")  # Use Fusion as base
            ThemeManager.toggle_theme(app, self.dark_mode)
            logger.info("Applied Fluent Design custom theme")
        else:
            # Apply Qt built-in style
            app.setStyle(QStyleFactory.create(style_name))
            # Clear custom stylesheet when using built-in styles
            app.setStyleSheet("")
            logger.info(f"Applied Qt style: {style_name}")

        # Update UI
        self.update()

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
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.disconnect_device)
        self.status_message.setText("Device connected successfully")

        logger.info("Device connected")

    def on_device_disconnected(self):
        """Handle device disconnected event."""

        self.status_indicator.setStyleSheet("color: #ef4444; font-size: 16px;")
        self.status_label.setText("Disconnected")
        self.connect_btn.setText("Connect to Device...")
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.show_connection_dialog)
        self.status_message.setText("Device disconnected")

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
        if self.config_manager.is_modified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Current configuration has unsaved changes. Do you want to save?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Yes:
                if not self.save_configuration():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.config_manager.new_config()
        self.load_config_to_ui()
        self.setWindowTitle("PMU-30 Configurator - R2 m-sport")
        self.status_message.setText("Created new configuration")
        logger.info("Created new configuration")

    def open_configuration(self):
        """Open configuration file."""
        if self.config_manager.is_modified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Current configuration has unsaved changes. Do you want to save?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Yes:
                if not self.save_configuration():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Configuration",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )

        if filename:
            success, error_msg = self.config_manager.load_from_file(filename)

            if success:
                self.load_config_to_ui()
                self.setWindowTitle(f"PMU-30 Configurator - {filename}")
                self.status_message.setText(f"Loaded configuration from {filename}")
                logger.info(f"Opened configuration: {filename}")
            else:
                QMessageBox.critical(
                    self, "Configuration Load Error",
                    error_msg or f"Failed to load configuration from {filename}"
                )

    def save_configuration(self) -> bool:
        """Save configuration."""
        current_file = self.config_manager.get_current_file()

        if current_file:
            self.save_config_from_ui()
            if self.config_manager.save_to_file():
                self.setWindowTitle(f"PMU-30 Configurator - {current_file}")
                self.status_message.setText(f"Saved configuration to {current_file}")
                logger.info(f"Saved configuration to {current_file}")
                return True
            else:
                QMessageBox.critical(
                    self, "Error",
                    "Failed to save configuration"
                )
                return False
        else:
            return self.save_configuration_as()

    def save_configuration_as(self) -> bool:
        """Save configuration as new file."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration As",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )

        if filename:
            self.save_config_from_ui()
            if self.config_manager.save_to_file(filename):
                self.setWindowTitle(f"PMU-30 Configurator - {filename}")
                self.status_message.setText(f"Saved configuration to {filename}")
                logger.info(f"Saved configuration to {filename}")
                return True
            else:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to save configuration to {filename}"
                )
                return False
        return False

    def import_dbc(self):
        """Import DBC file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import DBC File",
            "",
            "DBC Files (*.dbc);;All Files (*.*)"
        )

        if filename:
            # TODO: Implement DBC import
            logger.info(f"Import DBC: {filename}")
            QMessageBox.information(
                self, "Import DBC",
                f"DBC import from {filename} will be implemented"
            )

    def export_dbc(self):
        """Export DBC file."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export DBC File",
            "",
            "DBC Files (*.dbc);;All Files (*.*)"
        )

        if filename:
            # TODO: Implement DBC export
            logger.info(f"Export DBC: {filename}")
            QMessageBox.information(
                self, "Export DBC",
                f"DBC export to {filename} will be implemented"
            )

    def load_config_to_ui(self):
        """Load configuration from manager to UI tabs."""
        logger.info("Loading configuration to UI")
        config = self.config_manager.get_config()

        # Load each tab
        self.inputs_tab.load_configuration(config)
        self.outputs_tab.load_configuration(config)
        self.hbridge_tab.load_configuration(config)
        self.logic_tab.load_configuration(config)
        self.pid_tab.load_configuration(config)
        self.lua_tab.load_configuration(config)
        self.can_tab.load_configuration(config)
        self.settings_tab.load_configuration(config)
        self.wiper_tab.load_configuration(config)
        self.turn_signal_tab.load_configuration(config)

    def save_config_from_ui(self):
        """Save configuration from UI tabs to manager."""
        logger.info("Saving configuration from UI")

        # Get configuration from each tab and update manager
        self.config_manager.config.update(self.inputs_tab.get_configuration())
        self.config_manager.config.update(self.outputs_tab.get_configuration())
        self.config_manager.config.update(self.hbridge_tab.get_configuration())
        self.config_manager.config.update(self.logic_tab.get_configuration())
        self.config_manager.config.update(self.pid_tab.get_configuration())
        self.config_manager.config.update(self.lua_tab.get_configuration())

        # Handle CAN tab specially - merge can_inputs into channels array
        can_config = self.can_tab.get_configuration()
        self.config_manager.config["can_messages"] = can_config.get("can_messages", [])
        self.config_manager.config["can_buses"] = can_config.get("can_buses", [])

        # Merge CAN inputs into channels array (removing old can_rx channels first)
        channels = self.config_manager.config.get("channels", [])
        # Remove existing can_rx channels
        channels = [ch for ch in channels if ch.get("channel_type") != "can_rx"]
        # Add new CAN inputs
        can_inputs = can_config.get("can_inputs", [])
        channels.extend(can_inputs)
        self.config_manager.config["channels"] = channels

        # Remove stale can_inputs key if present
        if "can_inputs" in self.config_manager.config:
            del self.config_manager.config["can_inputs"]

        self.config_manager.config.update(self.settings_tab.get_configuration())
        self.config_manager.config.update(self.wiper_tab.get_configuration())
        self.config_manager.config.update(self.turn_signal_tab.get_configuration())

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
        <p>Professional 30-channel Power Management Unit</p>
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

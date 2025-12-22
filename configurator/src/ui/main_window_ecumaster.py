"""
Main Window - Modern Style
Dock-based layout with project tree and monitoring panels
Unified GPIO architecture support
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QMenuBar, QStatusBar, QMessageBox,
    QFileDialog, QLabel
)
from PyQt6.QtCore import Qt, QTimer, QSettings, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup

from .widgets import ProjectTree, OutputMonitor, AnalogMonitor, VariablesInspector

# New GPIO dialogs
from .dialogs.digital_input_dialog import DigitalInputDialog
from .dialogs.analog_input_dialog import AnalogInputDialog
from .dialogs.logic_dialog import LogicDialog
from .dialogs.timer_dialog import TimerDialog
from .dialogs.enum_dialog import EnumDialog
from .dialogs.number_dialog import NumberDialog
from .dialogs.filter_dialog import FilterDialog
from .dialogs.table_2d_dialog import Table2DDialog
from .dialogs.table_3d_dialog import Table3DDialog

# Existing dialogs (to be migrated later)
from .dialogs.output_config_dialog import OutputConfigDialog
from .dialogs.input_config_dialog import InputConfigDialog
from .dialogs.switch_dialog import SwitchDialog
from .dialogs.can_message_dialog import CANMessageDialog
from .dialogs.connection_dialog import ConnectionDialog

from controllers.device_controller import DeviceController
from models.config_manager import ConfigManager
from models.gpio import GPIOType
from utils.theme import ThemeManager

logger = logging.getLogger(__name__)


class MainWindowECUMaster(QMainWindow):
    """Main window with modern dock-based layout and unified GPIO architecture."""

    # Signals
    configuration_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Initialize managers
        self.config_manager = ConfigManager()
        self.device_controller = DeviceController()

        # Settings for saving/restoring layout
        self.settings = QSettings("R2msport", "PMU30Configurator")

        self._init_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._setup_connections()

        # Apply light theme by default
        self.apply_theme()

        # Apply Fusion style by default
        self.change_style("Fusion")

        # Restore window geometry and state
        self._restore_layout()

        logger.info("Main window initialized with GPIO architecture")

    def _init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("PMU-30 Configurator - R2 m-sport")

        # Set window size to 70% of screen
        from PyQt6.QtWidgets import QApplication, QWidget
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        width = int(screen_geometry.width() * 0.7)
        height = int(screen_geometry.height() * 0.7)

        # Center window
        x = (screen_geometry.width() - width) // 2
        y = (screen_geometry.height() - height) // 2
        self.setGeometry(x, y, width, height)

        # Enable animated docks for magnetic snapping
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks |
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AllowTabbedDocks
        )

        # Hide central widget - all content in docks
        central = QWidget()
        central.hide()
        self.setCentralWidget(central)

        # Create dock widgets
        self._create_dock_widgets()

    def _create_dock_widgets(self):
        """Create dock widgets for monitoring."""

        # Project Tree Dock
        self.project_tree_dock = QDockWidget("Project Tree", self)
        self.project_tree_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.project_tree = ProjectTree()
        self.project_tree_dock.setWidget(self.project_tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_tree_dock)

        # Output Monitor Dock
        self.output_dock = QDockWidget("Output Monitor", self)
        self.output_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.output_monitor = OutputMonitor()
        self.output_dock.setWidget(self.output_monitor)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.output_dock)

        # Analog Monitor Dock
        self.analog_dock = QDockWidget("Analog Monitor", self)
        self.analog_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.analog_monitor = AnalogMonitor()
        self.analog_dock.setWidget(self.analog_monitor)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.analog_dock)

        # Variables Inspector Dock
        self.variables_dock = QDockWidget("Variables Inspector", self)
        self.variables_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.variables_inspector = VariablesInspector()
        self.variables_dock.setWidget(self.variables_inspector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.variables_dock)

        # Stack monitors vertically on the right
        self.tabifyDockWidget(self.output_dock, self.analog_dock)
        self.tabifyDockWidget(self.analog_dock, self.variables_dock)

        # Show output monitor by default
        self.output_dock.raise_()

    def _setup_menubar(self):
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

        save_as_action = QAction("Save Configuration As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_configuration_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)

        # Device menu
        device_menu = menubar.addMenu("Device")

        connect_action = QAction("Connect...", self)
        connect_action.setShortcut("Ctrl+D")
        connect_action.triggered.connect(self.connect_device)
        device_menu.addAction(connect_action)

        disconnect_action = QAction("Disconnect", self)
        disconnect_action.triggered.connect(self.disconnect_device)
        device_menu.addAction(disconnect_action)

        device_menu.addSeparator()

        read_config_action = QAction("Read Configuration", self)
        read_config_action.triggered.connect(self.read_from_device)
        device_menu.addAction(read_config_action)

        write_config_action = QAction("Write Configuration", self)
        write_config_action.triggered.connect(self.write_to_device)
        device_menu.addAction(write_config_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        can_monitor_action = QAction("CAN Monitor", self)
        tools_menu.addAction(can_monitor_action)

        data_logger_action = QAction("Data Logger", self)
        tools_menu.addAction(data_logger_action)

        # Windows menu
        windows_menu = menubar.addMenu("Windows")

        project_tree_action = self.project_tree_dock.toggleViewAction()
        project_tree_action.setText("Project Tree")
        project_tree_action.setShortcut("Shift+F7")
        windows_menu.addAction(project_tree_action)

        windows_menu.addSeparator()

        output_monitor_action = self.output_dock.toggleViewAction()
        output_monitor_action.setText("Output Monitor")
        output_monitor_action.setShortcut("Shift+F8")
        windows_menu.addAction(output_monitor_action)

        analog_monitor_action = self.analog_dock.toggleViewAction()
        analog_monitor_action.setText("Analog Monitor")
        analog_monitor_action.setShortcut("Shift+F10")
        windows_menu.addAction(analog_monitor_action)

        variables_action = self.variables_dock.toggleViewAction()
        variables_action.setText("Variables Inspector")
        variables_action.setShortcut("Shift+F11")
        windows_menu.addAction(variables_action)

        # View menu
        view_menu = menubar.addMenu("View")

        # Style submenu
        style_menu = view_menu.addMenu("Application Style")

        from PyQt6.QtWidgets import QStyleFactory
        available_styles = QStyleFactory.keys()

        self.style_group = QActionGroup(self)
        self.style_group.setExclusive(True)

        fluent_action = QAction("Fluent Design (Custom)", self)
        fluent_action.setCheckable(True)
        fluent_action.triggered.connect(lambda: self.change_style("Fluent"))
        self.style_group.addAction(fluent_action)
        style_menu.addAction(fluent_action)

        style_menu.addSeparator()

        for style_name in available_styles:
            action = QAction(style_name, self)
            action.setCheckable(True)
            if style_name == "Fusion":
                action.setChecked(True)
            action.triggered.connect(lambda checked, s=style_name: self.change_style(s))
            self.style_group.addAction(action)
            style_menu.addAction(action)

        self.current_style = "Fusion"

        # Help menu
        help_menu = menubar.addMenu("Help")

        docs_action = QAction("Documentation", self)
        help_menu.addAction(docs_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.status_message = QLabel("Ready")
        self.statusbar.addWidget(self.status_message)

        self.statusbar.addWidget(QLabel(" | "))

        self.device_status_label = QLabel("OFFLINE")
        self.device_status_label.setStyleSheet("color: #ef4444;")
        self.statusbar.addWidget(self.device_status_label)

        self.statusbar.addWidget(QLabel(" | "))

        self.can1_label = QLabel("CAN1:")
        self.statusbar.addWidget(self.can1_label)

        self.statusbar.addWidget(QLabel(" | "))

        self.can2_label = QLabel("CAN2: ?")
        self.statusbar.addWidget(self.can2_label)

        self.statusbar.addWidget(QLabel(" | "))

        self.outputs_status_label = QLabel("OUTPUTS:")
        self.statusbar.addPermanentWidget(self.outputs_status_label)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_statusbar)
        self.status_timer.start(500)

    def _update_statusbar(self):
        """Update status bar."""
        pass

    def _setup_connections(self):
        """Setup signal connections."""
        self.project_tree.item_added.connect(self._on_item_add_requested)
        self.project_tree.item_edited.connect(self._on_item_edit_requested)
        self.project_tree.configuration_changed.connect(self._on_config_changed)

    def _on_item_add_requested(self, gpio_type_str: str):
        """Handle request to add new item by GPIO type."""
        try:
            gpio_type = GPIOType(gpio_type_str)
        except ValueError:
            return

        available_channels = self._get_available_channels()

        if gpio_type == GPIOType.DIGITAL_INPUT:
            dialog = DigitalInputDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.ANALOG_INPUT:
            dialog = AnalogInputDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.POWER_OUTPUT:
            dialog = OutputConfigDialog(self, None, [], available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.LOGIC:
            dialog = LogicDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.NUMBER:
            dialog = NumberDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.TIMER:
            dialog = TimerDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.SWITCH:
            dialog = SwitchDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.TABLE_2D:
            dialog = Table2DDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.TABLE_3D:
            dialog = Table3DDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.ENUM:
            dialog = EnumDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.FILTER:
            dialog = FilterDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

        elif gpio_type == GPIOType.CAN_RX or gpio_type == GPIOType.CAN_TX:
            dialog = CANMessageDialog(self, None)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(gpio_type, config)
                self.configuration_changed.emit()

    def _on_item_edit_requested(self, gpio_type_str: str, data: dict):
        """Handle request to edit item by GPIO type."""
        try:
            gpio_type = GPIOType(gpio_type_str)
        except ValueError:
            return

        item_data = data.get("data", {})
        available_channels = self._get_available_channels()

        if gpio_type == GPIOType.DIGITAL_INPUT:
            dialog = DigitalInputDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.ANALOG_INPUT:
            dialog = AnalogInputDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)
                self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())

        elif gpio_type == GPIOType.POWER_OUTPUT:
            dialog = OutputConfigDialog(self, item_data, [], available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)
                self.output_monitor.set_outputs(self.project_tree.get_all_outputs())

        elif gpio_type == GPIOType.LOGIC:
            dialog = LogicDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.NUMBER:
            dialog = NumberDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.TIMER:
            dialog = TimerDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.SWITCH:
            dialog = SwitchDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.TABLE_2D:
            dialog = Table2DDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.TABLE_3D:
            dialog = Table3DDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.ENUM:
            dialog = EnumDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.FILTER:
            dialog = FilterDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif gpio_type == GPIOType.CAN_RX or gpio_type == GPIOType.CAN_TX:
            dialog = CANMessageDialog(self, item_data)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

    def _get_available_channels(self) -> dict:
        """Get all available channels for selection organized by GPIO type."""
        channels = {
            # New GPIO format
            "digital_inputs": [],
            "analog_inputs": [],
            "power_outputs": [],
            "logic": [],
            "numbers": [],
            "tables_2d": [],
            "tables_3d": [],
            "switches": [],
            "timers": [],
            "filters": [],
            "enums": [],
            "can_rx": [],
            "can_tx": [],
            # Legacy format for backwards compatibility
            "inputs_physical": [f"in.{i}" for i in range(20)],
            "outputs_physical": [f"out.{i}" for i in range(30)],
        }

        # Add channels from project tree
        for ch in self.project_tree.get_channels_by_type(GPIOType.DIGITAL_INPUT):
            channels["digital_inputs"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.ANALOG_INPUT):
            channels["analog_inputs"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.POWER_OUTPUT):
            channels["power_outputs"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.LOGIC):
            channels["logic"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.NUMBER):
            channels["numbers"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.TABLE_2D):
            channels["tables_2d"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.TABLE_3D):
            channels["tables_3d"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.SWITCH):
            channels["switches"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.TIMER):
            channels["timers"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.FILTER):
            channels["filters"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.ENUM):
            channels["enums"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.CAN_RX):
            channels["can_rx"].append(ch.get("id", ""))

        for ch in self.project_tree.get_channels_by_type(GPIOType.CAN_TX):
            channels["can_tx"].append(ch.get("id", ""))

        return channels

    def _on_config_changed(self):
        """Handle configuration change."""
        self.config_manager.modified = True

    # ========== Menu actions ==========

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
        self.project_tree.clear_all()
        self.status_message.setText("Created new configuration")

    def open_configuration(self):
        """Open configuration file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration", "",
            "JSON Files (*.json);;All Files (*.*)"
        )

        if filename:
            success, error_msg = self.config_manager.load_from_file(filename)
            if success:
                self._load_config_to_ui()
                self.status_message.setText(f"Loaded: {filename}")
            else:
                QMessageBox.critical(self, "Error", error_msg)

    def save_configuration(self) -> bool:
        """Save configuration."""
        current_file = self.config_manager.get_current_file()

        if current_file:
            self._save_config_from_ui()
            if self.config_manager.save_to_file():
                self.status_message.setText(f"Saved: {current_file}")
                return True
            else:
                QMessageBox.critical(self, "Error", "Failed to save configuration")
                return False
        else:
            return self.save_configuration_as()

    def save_configuration_as(self) -> bool:
        """Save configuration as."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration As", "",
            "JSON Files (*.json);;All Files (*.*)"
        )

        if filename:
            self._save_config_from_ui()
            if self.config_manager.save_to_file(filename):
                self.status_message.setText(f"Saved: {filename}")
                return True
            else:
                QMessageBox.critical(self, "Error", "Failed to save")
                return False
        return False

    def _load_config_to_ui(self):
        """Load configuration to UI."""
        config = self.config_manager.get_config()

        # Clear tree
        self.project_tree.clear_all()

        # Load channels (new format)
        channels = config.get("channels", [])
        if channels:
            self.project_tree.load_channels(channels)
        else:
            # Legacy format support
            for output in config.get("outputs", []):
                self.project_tree.add_output(output)

            for input_data in config.get("inputs", []):
                self.project_tree.add_input(input_data)

            for logic in config.get("logic_functions", []):
                self.project_tree.add_logic_function(logic)

            for timer in config.get("timers", []):
                self.project_tree.add_timer(timer)

            for num in config.get("numbers", []):
                self.project_tree.add_number(num)

            for switch in config.get("switches", []):
                self.project_tree.add_switch(switch)

            for table in config.get("tables", []):
                self.project_tree.add_table(table)

        # Update monitors
        self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
        self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())

    def _save_config_from_ui(self):
        """Save configuration from UI."""
        config = self.config_manager.get_config()

        # Save as new format with channels array
        config["channels"] = self.project_tree.get_all_channels()

        # Clear legacy arrays
        config["outputs"] = []
        config["inputs"] = []
        config["logic_functions"] = []
        config["timers"] = []
        config["numbers"] = []
        config["switches"] = []
        config["tables"] = []

        self.config_manager.modified = True

    def connect_device(self):
        """Connect to device."""
        dialog = ConnectionDialog(self)
        if dialog.exec() == ConnectionDialog.DialogCode.Accepted:
            config = dialog.get_connection_config()
            self.status_message.setText(f"Connecting to {config.get('type')}...")

            success = self.device_controller.connect(config)

            if success:
                self.status_message.setText(f"Connected via {config.get('type')}")
                self.device_status_label.setText("ONLINE")
                self.device_status_label.setStyleSheet("color: #10b981;")
                QMessageBox.information(self, "Connected", "Successfully connected to PMU-30 device.")
            else:
                self.status_message.setText("Connection failed")
                QMessageBox.warning(self, "Connection Failed", "Could not connect to the device.")
        else:
            self.status_message.setText("Connection cancelled")

    def disconnect_device(self):
        """Disconnect from device."""
        self.status_message.setText("Disconnected")
        self.device_status_label.setText("OFFLINE")
        self.device_status_label.setStyleSheet("color: #ef4444;")

    def read_from_device(self):
        """Read configuration from device."""
        pass

    def write_to_device(self):
        """Write configuration to device."""
        pass

    def show_settings(self):
        """Show settings dialog."""
        from .tabs.settings_tab import SettingsTab
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.resize(600, 700)

        layout = QVBoxLayout()
        settings_tab = SettingsTab()
        layout.addWidget(settings_tab)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About PMU-30 Configurator",
            "<b>PMU-30 Power Management Unit Configurator</b><br><br>"
            "Version: 2.0.0<br>"
            "GPIO Architecture: Unified Channels<br><br>"
            "© 2025 R2 m-sport. All rights reserved."
        )

    def save_layout(self):
        """Save current layout."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.status_message.setText("Layout saved")

    def restore_default_layout(self):
        """Restore default layout."""
        self.settings.remove("geometry")
        self.settings.remove("windowState")
        self._restore_layout()
        self.status_message.setText("Layout restored to default")

    def _restore_layout(self):
        """Restore saved layout."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def apply_theme(self):
        """Apply light theme by default."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            ThemeManager.toggle_theme(app, False)

    def change_style(self, style_name: str):
        """Change application style."""
        from PyQt6.QtWidgets import QApplication, QStyleFactory

        app = QApplication.instance()
        if not app:
            return

        self.current_style = style_name

        if style_name == "Fluent":
            app.setStyle("Fusion")
            ThemeManager.toggle_theme(app, False)
        else:
            app.setStyle(QStyleFactory.create(style_name))
            app.setStyleSheet("")

        self.update()

    def closeEvent(self, event):
        """Handle window close."""
        self.save_layout()

        if self.config_manager.is_modified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Yes:
                if not self.save_configuration():
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        event.accept()

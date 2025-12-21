"""
Main Window - ECUMaster Style
Dock-based layout with project tree and monitoring panels
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QMenuBar, QStatusBar, QMessageBox,
    QFileDialog, QLabel
)
from PyQt6.QtCore import Qt, QTimer, QSettings, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup

from .widgets import ProjectTree, OutputMonitor, AnalogMonitor, VariablesInspector
from .dialogs.output_config_dialog import OutputConfigDialog
from .dialogs.input_config_dialog import InputConfigDialog
from .dialogs.logic_function_dialog import LogicFunctionDialog
from .dialogs.hbridge_dialog import HBridgeDialog
from .dialogs.pid_controller_dialog import PIDControllerDialog
from .dialogs.lua_script_dialog import LuaScriptDialog
from .dialogs.number_dialog import NumberDialog
from .dialogs.switch_dialog import SwitchDialog
from .dialogs.table_dialog import TableDialog
from .dialogs.timer_dialog import TimerDialog
from .dialogs.can_message_dialog import CANMessageDialog
from .dialogs.connection_dialog import ConnectionDialog

from controllers.device_controller import DeviceController
from models.config_manager import ConfigManager
from utils.theme import ThemeManager

logger = logging.getLogger(__name__)


class MainWindowECUMaster(QMainWindow):
    """Main window with ECUMaster-style layout."""

    # Signals
    configuration_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Initialize managers
        self.config_manager = ConfigManager()
        self.device_controller = DeviceController()

        # Settings for saving/restoring layout
        self.settings = QSettings("R2msport", "PMU30Configurator")

        # Desktop management
        self.desktops = {}  # name -> {geometry, state}
        self.current_desktop = "Default"
        self._load_desktops()

        self._init_ui()
        self._setup_menubar()
        self._update_desktop_menu()  # Update desktop menu after it's created
        self._setup_statusbar()
        self._setup_connections()

        # Apply light theme by default
        self.apply_theme()

        # Apply Fusion style by default
        self.change_style("Fusion")

        # Restore window geometry and state
        self._restore_layout()

        logger.info("ECUMaster-style main window initialized")

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

        # Create empty central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Create dock widgets (including Project Tree)
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

        # Desktops menu (for layouts)
        desktops_menu = menubar.addMenu("Desktops")

        restore_desktops_action = QAction("Restore desktops", self)
        restore_desktops_action.triggered.connect(self._restore_desktops)
        desktops_menu.addAction(restore_desktops_action)

        store_desktops_action = QAction("Store desktops", self)
        store_desktops_action.triggered.connect(self._store_desktops)
        desktops_menu.addAction(store_desktops_action)

        desktops_menu.addSeparator()

        open_template_action = QAction("Open desktops template...", self)
        open_template_action.triggered.connect(self._open_desktop_template)
        desktops_menu.addAction(open_template_action)

        save_template_action = QAction("Save desktops template...", self)
        save_template_action.triggered.connect(self._save_desktop_template)
        desktops_menu.addAction(save_template_action)

        desktops_menu.addSeparator()

        add_pane_action = QAction("Add new pane", self)
        add_pane_action.setShortcut("F9")
        add_pane_action.triggered.connect(self._add_new_pane)
        desktops_menu.addAction(add_pane_action)

        replace_pane_action = QAction("Replace pane", self)
        replace_pane_action.setShortcut("Shift+F9")
        replace_pane_action.triggered.connect(self._replace_pane)
        desktops_menu.addAction(replace_pane_action)

        desktops_menu.addSeparator()

        # Switch desktop submenu
        self.switch_desktop_menu = desktops_menu.addMenu("Switch desktop to...")

        prev_desktop_action = QAction("Previous desktop", self)
        prev_desktop_action.setShortcut("Ctrl+PgUp")
        prev_desktop_action.triggered.connect(self._previous_desktop)
        desktops_menu.addAction(prev_desktop_action)

        next_desktop_action = QAction("Next desktop", self)
        next_desktop_action.setShortcut("Ctrl+PgDown")
        next_desktop_action.triggered.connect(self._next_desktop)
        desktops_menu.addAction(next_desktop_action)

        # Devices menu
        devices_menu = menubar.addMenu("Devices")

        connect_action = QAction("Connect...", self)
        connect_action.setShortcut("Ctrl+D")
        connect_action.triggered.connect(self.connect_device)
        devices_menu.addAction(connect_action)

        disconnect_action = QAction("Disconnect", self)
        disconnect_action.triggered.connect(self.disconnect_device)
        devices_menu.addAction(disconnect_action)

        devices_menu.addSeparator()

        read_config_action = QAction("Read Configuration", self)
        read_config_action.triggered.connect(self.read_from_device)
        devices_menu.addAction(read_config_action)

        write_config_action = QAction("Write Configuration", self)
        write_config_action.triggered.connect(self.write_to_device)
        devices_menu.addAction(write_config_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        can_monitor_action = QAction("CAN Monitor", self)
        tools_menu.addAction(can_monitor_action)

        data_logger_action = QAction("Data Logger", self)
        tools_menu.addAction(data_logger_action)

        # Windows menu (for dock widgets)
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

        from PyQt6.QtGui import QActionGroup
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
            # Set Fusion as default
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

        # Status message
        self.status_message = QLabel("Ready")
        self.statusbar.addWidget(self.status_message)

        self.statusbar.addWidget(QLabel(" | "))

        # Device status
        self.device_status_label = QLabel("OFFLINE")
        self.device_status_label.setStyleSheet("color: #ef4444;")
        self.statusbar.addWidget(self.device_status_label)

        self.statusbar.addWidget(QLabel(" | "))

        # CAN status
        self.can1_label = QLabel("CAN1:")
        self.statusbar.addWidget(self.can1_label)

        self.statusbar.addWidget(QLabel(" | "))

        self.can2_label = QLabel("CAN2: ?")
        self.statusbar.addWidget(self.can2_label)

        self.statusbar.addWidget(QLabel(" | "))

        # Outputs status
        self.outputs_status_label = QLabel("OUTPUTS:")
        self.statusbar.addPermanentWidget(self.outputs_status_label)

        # Update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_statusbar)
        self.status_timer.start(500)

    def _update_statusbar(self):
        """Update status bar."""
        # Update from configuration
        pass

    def _setup_connections(self):
        """Setup signal connections."""
        # Project tree signals
        self.project_tree.item_added.connect(self._on_item_add_requested)
        self.project_tree.item_edited.connect(self._on_item_edit_requested)
        self.project_tree.configuration_changed.connect(self._on_config_changed)

    def _on_item_add_requested(self, category: str):
        """Handle request to add new item."""
        if category == "outputs":
            self._add_output()
        elif category == "inputs":
            self._add_input()
        elif category == "logic":
            self._add_logic_function()
        elif category == "hbridge":
            self._add_hbridge()
        elif category == "pid":
            self._add_pid_controller()
        elif category == "lua":
            self._add_lua_script()
        elif category == "numbers":
            self._add_number()
        elif category == "switches":
            self._add_switch()
        elif category == "tables":
            self._add_table()
        elif category == "timers":
            self._add_timer()
        elif category == "can":
            self._add_can_message()

    def _on_item_edit_requested(self, category: str, data: dict):
        """Handle request to edit item."""
        item_data = data.get("data", {})

        if category == "outputs":
            available_channels = self._get_available_channels()
            dialog = OutputConfigDialog(self, item_data, [], available_channels)
            if dialog.exec():
                # Get updated config from dialog
                updated_config = dialog.get_config()
                # Update the tree item
                self.project_tree.update_current_item(updated_config)
                # Update monitor
                self.output_monitor.set_outputs(self.project_tree.get_all_outputs())

        elif category == "inputs":
            dialog = InputConfigDialog(self, item_data, [])
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)
                # Update monitor
                self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())

        elif category == "logic":
            dialog = LogicFunctionDialog(self, item_data)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif category == "hbridge":
            channel = item_data.get("channel", 0)
            dialog = HBridgeDialog(self, channel, item_data)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif category == "pid":
            dialog = PIDControllerDialog(self, item_data)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif category == "lua":
            dialog = LuaScriptDialog(self, item_data)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif category == "switches":
            available_channels = self._get_available_channels()
            dialog = SwitchDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

        elif category == "numbers":
            available_channels = self._get_available_channels()
            dialog = NumberDialog(self, item_data, available_channels)
            if dialog.exec():
                updated_config = dialog.get_config()
                self.project_tree.update_current_item(updated_config)

    def _get_available_channels(self) -> dict:
        """Get all available channels for selection."""
        channels = {
            "inputs_physical": [f"in.{i}" for i in range(20)],
            "outputs_physical": [f"out.{i}" for i in range(30)],
            "functions": [],
            "tables": [],
            "numbers": [],
            "switches": [],
            "timers": [],
            "pid_controllers": [],
            "hbridge": [],
            "can_signals": []
        }

        # Add logic functions
        for func in self.project_tree.get_all_logic_functions():
            channels["functions"].append(func.get("name", ""))

        # Add tables
        for table in self.project_tree.get_all_tables():
            channels["tables"].append(table.get("name", ""))

        # Add numbers
        for num in self.project_tree.get_all_numbers():
            channels["numbers"].append(num.get("name", ""))

        # Add switches
        for switch in self.project_tree.get_all_switches():
            channels["switches"].append(switch.get("name", ""))

        # Add timers
        for timer in self.project_tree.get_all_timers():
            channels["timers"].append(timer.get("name", ""))

        # Add PID controllers
        for pid in self.project_tree.get_all_pid_controllers():
            channels["pid_controllers"].append(pid.get("name", ""))

        # Add H-Bridges
        for hb in self.project_tree.get_all_hbridges():
            channels["hbridge"].append(hb.get("name", ""))

        return channels

    def _add_output(self):
        """Add new output."""
        available_channels = self._get_available_channels()
        dialog = OutputConfigDialog(self, None, [], available_channels)
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_output(config)
            # Update monitor
            self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
            self.configuration_changed.emit()

    def _add_input(self):
        """Add new input."""
        dialog = InputConfigDialog(self, None, [])
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_input(config)
            # Update monitor
            self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
            self.configuration_changed.emit()

    def _add_logic_function(self):
        """Add new logic function."""
        dialog = LogicFunctionDialog(self, None)
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_logic_function(config)
            self.configuration_changed.emit()

    def _add_hbridge(self):
        """Add new H-Bridge."""
        dialog = HBridgeDialog(self, 0, None)
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_hbridge(config)
            self.configuration_changed.emit()

    def _add_pid_controller(self):
        """Add new PID controller."""
        dialog = PIDControllerDialog(self, None)
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_pid_controller(config)
            self.configuration_changed.emit()

    def _add_lua_script(self):
        """Add new LUA script."""
        dialog = LuaScriptDialog(self, None)
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_lua_script(config)
            self.configuration_changed.emit()

    def _add_number(self):
        """Add new number constant."""
        available_channels = self._get_available_channels()
        dialog = NumberDialog(self, None, available_channels)
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_number(config)
            self.configuration_changed.emit()

    def _add_switch(self):
        """Add new switch."""
        available_channels = self._get_available_channels()
        dialog = SwitchDialog(self, None, available_channels)
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_switch(config)
            self.configuration_changed.emit()

    def _add_table(self):
        """Add new lookup table."""
        dialog = TableDialog(self, None, [])
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_table(config)
            self.configuration_changed.emit()

    def _add_timer(self):
        """Add new timer."""
        dialog = TimerDialog(self, None, [])
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_timer(config)
            self.configuration_changed.emit()

    def _add_can_message(self):
        """Add new CAN message."""
        dialog = CANMessageDialog(self, None)
        if dialog.exec():
            config = dialog.get_config()
            self.project_tree.add_can_message(config)
            self.configuration_changed.emit()

    def _on_config_changed(self):
        """Handle configuration change."""
        self.config_manager.modified = True

    # Menu actions
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

        # Load outputs
        for output in config.get("outputs", []):
            self.project_tree.add_output(output)

        # Load inputs
        for input_data in config.get("inputs", []):
            self.project_tree.add_input(input_data)

        # Load logic functions
        for logic in config.get("logic_functions", []):
            self.project_tree.add_logic_function(logic)

        # Load H-Bridge
        for hb in config.get("hbridge", []):
            self.project_tree.add_hbridge(hb)

        # Load PID
        for pid in config.get("pid_controllers", []):
            self.project_tree.add_pid_controller(pid)

        # Load LUA
        for lua in config.get("lua_scripts", []):
            self.project_tree.add_lua_script(lua)

        # Update monitors
        self.output_monitor.set_outputs(config.get("outputs", []))
        self.analog_monitor.set_inputs(config.get("inputs", []))

    def _save_config_from_ui(self):
        """Save configuration from UI."""
        # Collect all data from project tree
        config = self.config_manager.get_config()

        # Update outputs
        config["outputs"] = self.project_tree.get_all_outputs()

        # Update inputs
        config["inputs"] = self.project_tree.get_all_inputs()

        # Update logic functions
        config["logic_functions"] = self.project_tree.get_all_logic_functions()

        # Update H-Bridge
        config["hbridge"] = self.project_tree.get_all_hbridges()

        # Update PID controllers
        config["pid_controllers"] = self.project_tree.get_all_pid_controllers()

        # Update LUA scripts
        config["lua_scripts"] = self.project_tree.get_all_lua_scripts()

        # CAN messages and settings would be handled separately when those tabs are implemented
        # For now, preserve existing values if any
        if "can_messages" not in config:
            config["can_messages"] = []
        if "settings" not in config:
            config["settings"] = {}

        # No need to call set_config - we modified the dict directly (it's a reference)
        # Mark as modified so save will work
        self.config_manager.modified = True

    def connect_device(self):
        """Connect to device."""
        dialog = ConnectionDialog(self)
        if dialog.exec() == ConnectionDialog.DialogCode.Accepted:
            config = dialog.get_connection_config()
            self.status_message.setText(f"Connecting to {config.get('type')}...")

            # Attempt connection using device controller
            success = self.device_controller.connect(config)

            if success:
                self.status_message.setText(f"Connected via {config.get('type')}")
                self.device_status_label.setText("ONLINE")
                self.device_status_label.setStyleSheet("color: #10b981;")
                QMessageBox.information(self, "Connected", "Successfully connected to PMU-30 device.")
            else:
                self.status_message.setText("Connection failed")
                QMessageBox.warning(self, "Connection Failed", "Could not connect to the device.\nPlease check connection settings and try again.")
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
            "<b>PMU-30 Power Distribution Module Configurator</b><br><br>"
            "Version: 1.0.0<br>"
            "© 2025 R2 m-sport. All rights reserved.<br><br>"
            "ECUMaster-style interface"
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
            # Always apply light theme (dark_mode = False)
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
            # Always use light theme
            ThemeManager.toggle_theme(app, False)
        else:
            app.setStyle(QStyleFactory.create(style_name))
            app.setStyleSheet("")

        self.update()

    # Desktop management methods
    def _load_desktops(self):
        """Load saved desktops from settings."""
        desktop_count = self.settings.value("desktops/count", 1, type=int)
        for i in range(desktop_count):
            name = self.settings.value(f"desktops/{i}/name", f"Desktop {i+1}")
            geometry = self.settings.value(f"desktops/{i}/geometry")
            state = self.settings.value(f"desktops/{i}/state")
            if geometry and state:
                self.desktops[name] = {"geometry": geometry, "state": state}

        # Always have at least a default desktop
        if "Default" not in self.desktops:
            self.desktops["Default"] = {}

        self._update_desktop_menu()

    def _update_desktop_menu(self):
        """Update switch desktop submenu."""
        # Check if menu exists (it's created in _setup_menubar)
        if not hasattr(self, 'switch_desktop_menu'):
            return

        self.switch_desktop_menu.clear()
        for name in sorted(self.desktops.keys()):
            action = QAction(name, self)
            action.triggered.connect(lambda checked, n=name: self._switch_to_desktop(n))
            if name == self.current_desktop:
                action.setCheckable(True)
                action.setChecked(True)
            self.switch_desktop_menu.addAction(action)

    def _restore_desktops(self):
        """Restore all saved desktops."""
        self._load_desktops()
        QMessageBox.information(self, "Desktops", "Desktops restored successfully.")

    def _store_desktops(self):
        """Store current layout as a desktop."""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Store Desktop", "Desktop name:")
        if ok and name:
            self.desktops[name] = {
                "geometry": self.saveGeometry(),
                "state": self.saveState()
            }
            self._save_desktops()
            self._update_desktop_menu()
            QMessageBox.information(self, "Desktop Saved", f"Desktop '{name}' saved successfully.")

    def _save_desktops(self):
        """Save all desktops to settings."""
        self.settings.setValue("desktops/count", len(self.desktops))
        for i, (name, data) in enumerate(self.desktops.items()):
            self.settings.setValue(f"desktops/{i}/name", name)
            if "geometry" in data:
                self.settings.setValue(f"desktops/{i}/geometry", data["geometry"])
            if "state" in data:
                self.settings.setValue(f"desktops/{i}/state", data["state"])

    def _open_desktop_template(self):
        """Open desktop template from file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Desktop Template", "",
            "Desktop Files (*.desktop);;All Files (*.*)"
        )
        if filename:
            import json
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                for name, layout in data.items():
                    if "geometry" in layout and "state" in layout:
                        from PyQt6.QtCore import QByteArray
                        self.desktops[name] = {
                            "geometry": QByteArray.fromBase64(layout["geometry"].encode()),
                            "state": QByteArray.fromBase64(layout["state"].encode())
                        }
                self._update_desktop_menu()
                QMessageBox.information(self, "Success", "Desktop template loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load template: {str(e)}")

    def _save_desktop_template(self):
        """Save desktops as template file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Desktop Template", "",
            "Desktop Files (*.desktop);;All Files (*.*)"
        )
        if filename:
            import json
            data = {}
            for name, layout in self.desktops.items():
                if "geometry" in layout and "state" in layout:
                    data[name] = {
                        "geometry": bytes(layout["geometry"].toBase64()).decode(),
                        "state": bytes(layout["state"].toBase64()).decode()
                    }
            try:
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                QMessageBox.information(self, "Success", "Desktop template saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save template: {str(e)}")

    def _add_new_pane(self):
        """Add new dock widget pane."""
        from PyQt6.QtWidgets import QInputDialog
        items = ["Project Tree", "Output Monitor", "Analog Monitor", "Variables Inspector"]
        item, ok = QInputDialog.getItem(self, "Add Pane", "Select pane to add:", items, 0, False)
        if ok and item:
            if item == "Project Tree":
                self.project_tree_dock.show()
            elif item == "Output Monitor":
                self.output_dock.show()
            elif item == "Analog Monitor":
                self.analog_dock.show()
            elif item == "Variables Inspector":
                self.variables_dock.show()

    def _replace_pane(self):
        """Replace current pane with another."""
        QMessageBox.information(self, "Replace Pane", "Close the pane you want to replace, then use 'Add new pane' to add the desired pane.")

    def _switch_to_desktop(self, name: str):
        """Switch to specified desktop."""
        if name in self.desktops:
            layout = self.desktops[name]
            if "geometry" in layout:
                self.restoreGeometry(layout["geometry"])
            if "state" in layout:
                self.restoreState(layout["state"])
            self.current_desktop = name
            self._update_desktop_menu()

    def _previous_desktop(self):
        """Switch to previous desktop."""
        names = sorted(self.desktops.keys())
        if len(names) > 1:
            current_idx = names.index(self.current_desktop) if self.current_desktop in names else 0
            prev_idx = (current_idx - 1) % len(names)
            self._switch_to_desktop(names[prev_idx])

    def _next_desktop(self):
        """Switch to next desktop."""
        names = sorted(self.desktops.keys())
        if len(names) > 1:
            current_idx = names.index(self.current_desktop) if self.current_desktop in names else 0
            next_idx = (current_idx + 1) % len(names)
            self._switch_to_desktop(names[next_idx])

    def closeEvent(self, event):
        """Handle window close."""
        # Save layout
        self.save_layout()

        # Check for unsaved changes
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

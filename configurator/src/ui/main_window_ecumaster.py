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
        self.dark_mode = True

        # Settings for saving/restoring layout
        self.settings = QSettings("R2msport", "PMU30Configurator")

        self._init_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._setup_connections()

        # Apply dark theme by default
        self.apply_theme()

        # Restore window geometry and state
        self._restore_layout()

        logger.info("ECUMaster-style main window initialized")

    def _init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("PMU-30 Configurator - R2 m-sport")

        # Set window size to 70% of screen
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        width = int(screen_geometry.width() * 0.7)
        height = int(screen_geometry.height() * 0.7)

        # Center window
        x = (screen_geometry.width() - width) // 2
        y = (screen_geometry.height() - height) // 2
        self.setGeometry(x, y, width, height)

        # Create central widget - Project Tree
        self.project_tree = ProjectTree()
        self.setCentralWidget(self.project_tree)

        # Create dock widgets
        self._create_dock_widgets()

    def _create_dock_widgets(self):
        """Create dock widgets for monitoring."""

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

        save_layout_action = QAction("Save Layout", self)
        save_layout_action.triggered.connect(self.save_layout)
        desktops_menu.addAction(save_layout_action)

        restore_layout_action = QAction("Restore Default Layout", self)
        restore_layout_action.triggered.connect(self.restore_default_layout)
        desktops_menu.addAction(restore_layout_action)

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

        output_monitor_action = self.output_dock.toggleViewAction()
        output_monitor_action.setText("Output Monitor")
        windows_menu.addAction(output_monitor_action)

        analog_monitor_action = self.analog_dock.toggleViewAction()
        analog_monitor_action.setText("Analog Monitor")
        windows_menu.addAction(analog_monitor_action)

        variables_action = self.variables_dock.toggleViewAction()
        variables_action.setText("Variables Inspector")
        windows_menu.addAction(variables_action)

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

        from PyQt6.QtWidgets import QStyleFactory
        available_styles = QStyleFactory.keys()

        from PyQt6.QtGui import QActionGroup
        self.style_group = QActionGroup(self)
        self.style_group.setExclusive(True)

        fluent_action = QAction("Fluent Design (Custom)", self)
        fluent_action.setCheckable(True)
        fluent_action.setChecked(True)
        fluent_action.triggered.connect(lambda: self.change_style("Fluent"))
        self.style_group.addAction(fluent_action)
        style_menu.addAction(fluent_action)

        style_menu.addSeparator()

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

    def _on_item_edit_requested(self, category: str, data: dict):
        """Handle request to edit item."""
        item_data = data.get("data", {})

        if category == "outputs":
            dialog = OutputConfigDialog(self, item_data, [])
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

    def _add_output(self):
        """Add new output."""
        dialog = OutputConfigDialog(self, None, [])
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
        self.status_message.setText("Connecting...")
        # TODO: Show connection dialog

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
        """Apply current theme."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            ThemeManager.toggle_theme(app, self.dark_mode)

    def toggle_theme(self):
        """Toggle theme."""
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def change_style(self, style_name: str):
        """Change application style."""
        from PyQt6.QtWidgets import QApplication, QStyleFactory

        app = QApplication.instance()
        if not app:
            return

        self.current_style = style_name

        if style_name == "Fluent":
            app.setStyle("Fusion")
            ThemeManager.toggle_theme(app, self.dark_mode)
        else:
            app.setStyle(QStyleFactory.create(style_name))
            app.setStyleSheet("")

        self.update()

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

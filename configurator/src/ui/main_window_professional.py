"""
Main Window - Modern Style
Dock-based layout with project tree and monitoring panels
Unified Channel architecture support
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QMenuBar, QStatusBar, QMessageBox,
    QFileDialog, QLabel, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, QSettings, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup

from .widgets import (
    ProjectTree, OutputMonitor, AnalogMonitor, DigitalMonitor, VariablesInspector,
    PMUMonitorWidget, HBridgeMonitor, PIDTuner, CANMonitor, DataLoggerWidget,
    ChannelGraphWidget, LogViewerWidget
)

# Channel dialogs
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
from .dialogs.can_input_dialog import CANInputDialog
from .dialogs.can_output_dialog import CANOutputDialog
from .dialogs.can_messages_manager_dialog import CANMessagesManagerDialog
from .dialogs.can_import_dialog import CANImportDialog
from .dialogs.connection_dialog import ConnectionDialog
from .dialogs.lua_script_tree_dialog import LuaScriptTreeDialog
from .dialogs.pid_controller_dialog import PIDControllerDialog
from .dialogs.hbridge_dialog import HBridgeDialog
from .dialogs.handler_dialog import HandlerDialog
from .dialogs.config_diff_dialog import ConfigDiffDialog
from .dialogs.blinkmarine_keypad_dialog import BlinkMarineKeypadDialog
from .dialogs.wifi_settings_dialog import WiFiSettingsDialog
from .dialogs.bluetooth_settings_dialog import BluetoothSettingsDialog

from controllers.device_controller import DeviceController
from models.config_manager import ConfigManager
from models.channel import ChannelType
from utils.theme import ThemeManager

logger = logging.getLogger(__name__)


class MainWindowProfessional(QMainWindow):
    """Main window with modern dock-based layout and unified Channel architecture."""

    # Signals
    configuration_changed = pyqtSignal()
    _config_loaded_signal = pyqtSignal(dict)  # Internal signal for thread-safe config loading
    _config_load_error_signal = pyqtSignal()  # Internal signal for config load errors

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

        # Apply dark theme with Fusion style
        self.apply_theme()

        # Restore window geometry and state
        self._restore_layout()

        logger.info("Main window initialized with Channel architecture")

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
        """Create dock widgets for monitoring.

        Layout:
        +------------------+------------------------+
        |                  |  [PMU] [Outputs] [Ana] |
        |  Project Tree    |     Tab Content        |
        |  (Config)        |     (Real-time)        |
        |                  |                        |
        +------------------+------------------------+
        |     Status Bar (Connection/Telemetry)     |
        +-------------------------------------------+
        """

        # === LEFT SIDE: Project Tree ===
        self.project_tree_dock = QDockWidget("Configuration", self)
        self.project_tree_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.project_tree_dock.setMinimumWidth(280)
        self.project_tree = ProjectTree()
        self.project_tree_dock.setWidget(self.project_tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_tree_dock)

        # === RIGHT SIDE: Tabbed Monitor Panel ===
        self.monitor_dock = QDockWidget("Monitor", self)
        self.monitor_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )

        # Create tab widget for monitors
        self.monitor_tabs = QTabWidget()
        self.monitor_tabs.setTabPosition(QTabWidget.TabPosition.North)
        # Ensure tabs expand to fill available space
        from PyQt6.QtWidgets import QSizePolicy
        self.monitor_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # PMU Monitor tab (system overview)
        self.pmu_monitor = PMUMonitorWidget()
        self.monitor_tabs.addTab(self.pmu_monitor, "PMU")

        # Output Monitor tab
        self.output_monitor = OutputMonitor()
        self.monitor_tabs.addTab(self.output_monitor, "Outputs")

        # Analog Monitor tab
        self.analog_monitor = AnalogMonitor()
        self.monitor_tabs.addTab(self.analog_monitor, "Analog")

        # Digital Input Monitor tab
        self.digital_monitor = DigitalMonitor()
        self.monitor_tabs.addTab(self.digital_monitor, "Digital")

        # H-Bridge Monitor tab
        self.hbridge_monitor = HBridgeMonitor()
        self.hbridge_monitor.hbridge_command.connect(self._on_hbridge_command)
        self.monitor_tabs.addTab(self.hbridge_monitor, "H-Bridge")

        # Variables Inspector tab
        self.variables_inspector = VariablesInspector()
        self.monitor_tabs.addTab(self.variables_inspector, "Variables")

        # PID Tuner tab
        self.pid_tuner = PIDTuner()
        self.pid_tuner.parameters_changed.connect(self._on_pid_parameters_changed)
        self.pid_tuner.controller_reset.connect(self._on_pid_controller_reset)
        self.monitor_tabs.addTab(self.pid_tuner, "PID Tuner")

        # CAN Monitor tab
        self.can_monitor = CANMonitor()
        self.can_monitor.send_message.connect(self._on_can_send_message)
        self.monitor_tabs.addTab(self.can_monitor, "CAN Live")

        # Data Logger is now a separate dock widget (see below)

        # Channel Graph tab (dependency visualization)
        self.channel_graph = ChannelGraphWidget()
        self.channel_graph.channel_edit_requested.connect(self._on_graph_channel_edit)
        self.channel_graph.refresh_requested.connect(self._on_graph_refresh_requested)
        self.monitor_tabs.addTab(self.channel_graph, "Dependencies")

        # Log Viewer tab (firmware logs)
        self.log_viewer = LogViewerWidget()
        self.monitor_tabs.addTab(self.log_viewer, "Logs")

        self.monitor_dock.setWidget(self.monitor_tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.monitor_dock)

        # === BOTTOM AREA: Data Logger ===
        self.data_logger_dock = QDockWidget("Data Logger", self)
        self.data_logger_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea |
            Qt.DockWidgetArea.TopDockWidgetArea |
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.data_logger = DataLoggerWidget()
        self.data_logger_dock.setWidget(self.data_logger)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.data_logger_dock)
        # Hide by default - can be shown via View menu
        self.data_logger_dock.hide()

        # For backwards compatibility
        self.pmu_monitor_dock = self.monitor_dock
        self.pmu_output_dock = self.monitor_dock

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

        can_messages_action = QAction("CAN Messages...", self)
        can_messages_action.setShortcut("Ctrl+M")
        can_messages_action.triggered.connect(self.show_can_messages_manager)
        edit_menu.addAction(can_messages_action)

        import_can_action = QAction("Import CAN Channels...", self)
        import_can_action.setShortcut("Ctrl+I")
        import_can_action.triggered.connect(self.show_can_import_dialog)
        edit_menu.addAction(import_can_action)

        edit_menu.addSeparator()

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

        # Note: Read/Write Configuration removed - auto-sync on connect and changes
        save_flash_action = QAction("Save to Flash (Permanent)", self)
        save_flash_action.setShortcut("F2")
        save_flash_action.triggered.connect(self.save_to_flash)
        device_menu.addAction(save_flash_action)

        device_menu.addSeparator()

        compare_config_action = QAction("Compare Configurations...", self)
        compare_config_action.setShortcut("Ctrl+Shift+C")
        compare_config_action.triggered.connect(self.compare_configurations)
        device_menu.addAction(compare_config_action)

        device_menu.addSeparator()

        restart_action = QAction("Restart Device", self)
        restart_action.triggered.connect(self.restart_device)
        device_menu.addAction(restart_action)

        device_menu.addSeparator()

        wifi_settings_action = QAction("WiFi Settings...", self)
        wifi_settings_action.triggered.connect(self.show_wifi_settings)
        device_menu.addAction(wifi_settings_action)

        bluetooth_settings_action = QAction("Bluetooth Settings...", self)
        bluetooth_settings_action.triggered.connect(self.show_bluetooth_settings)
        device_menu.addAction(bluetooth_settings_action)

        # Windows menu
        windows_menu = menubar.addMenu("Windows")

        # Main panels
        config_action = self.project_tree_dock.toggleViewAction()
        config_action.setText("Configuration Panel")
        config_action.setShortcut("F7")
        windows_menu.addAction(config_action)

        monitor_action = self.monitor_dock.toggleViewAction()
        monitor_action.setText("Monitor Panel")
        monitor_action.setShortcut("F8")
        windows_menu.addAction(monitor_action)

        data_logger_action = self.data_logger_dock.toggleViewAction()
        data_logger_action.setText("Data Logger (Bottom)")
        data_logger_action.setShortcut("Ctrl+D")
        windows_menu.addAction(data_logger_action)

        windows_menu.addSeparator()

        # Monitor tab shortcuts
        windows_menu.addAction(QAction("--- Monitor Tabs ---", self))

        pmu_tab_action = QAction("PMU Monitor", self)
        pmu_tab_action.setShortcut("F9")
        pmu_tab_action.triggered.connect(lambda: self._switch_monitor_tab(0))
        windows_menu.addAction(pmu_tab_action)

        outputs_tab_action = QAction("Outputs Monitor", self)
        outputs_tab_action.setShortcut("F10")
        outputs_tab_action.triggered.connect(lambda: self._switch_monitor_tab(1))
        windows_menu.addAction(outputs_tab_action)

        analog_tab_action = QAction("Analog Monitor", self)
        analog_tab_action.setShortcut("F11")
        analog_tab_action.triggered.connect(lambda: self._switch_monitor_tab(2))
        windows_menu.addAction(analog_tab_action)

        variables_tab_action = QAction("Variables Inspector", self)
        variables_tab_action.setShortcut("F12")
        variables_tab_action.triggered.connect(lambda: self._switch_monitor_tab(3))
        windows_menu.addAction(variables_tab_action)

        windows_menu.addSeparator()

        # Reset layout
        reset_layout_action = QAction("Reset Layout", self)
        reset_layout_action.triggered.connect(self._reset_layout)
        windows_menu.addAction(reset_layout_action)

        # View menu
        view_menu = menubar.addMenu("View")

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
        self.project_tree.item_deleted.connect(self._on_item_deleted)
        self.project_tree.configuration_changed.connect(self._on_config_changed)

        # Device controller signals - use QueuedConnection for thread safety
        # (signals may be emitted from background receive thread)
        self.device_controller.telemetry_received.connect(
            self._on_telemetry_received, Qt.ConnectionType.QueuedConnection)
        self.device_controller.log_received.connect(
            self._on_log_received, Qt.ConnectionType.QueuedConnection)
        self.device_controller.disconnected.connect(
            self._on_device_disconnected, Qt.ConnectionType.QueuedConnection)
        self.device_controller.error.connect(
            self._on_device_error, Qt.ConnectionType.QueuedConnection)
        self.device_controller.reconnecting.connect(
            self._on_device_reconnecting, Qt.ConnectionType.QueuedConnection)
        self.device_controller.reconnect_failed.connect(
            self._on_device_reconnect_failed, Qt.ConnectionType.QueuedConnection)
        self.device_controller.connected.connect(
            self._on_device_connected, Qt.ConnectionType.QueuedConnection)

        # Internal signals for config loading from thread
        self._config_loaded_signal.connect(self._load_config_from_device)
        self._config_load_error_signal.connect(self._show_read_error)

    def _on_device_disconnected(self):
        """Handle device disconnection."""
        self.device_status_label.setText("OFFLINE")
        self.device_status_label.setStyleSheet("color: #ef4444;")
        self.status_message.setText("Disconnected from device")
        self.pmu_monitor.set_connected(False)
        self.output_monitor.set_connected(False)
        self.analog_monitor.set_connected(False)
        self.digital_monitor.set_connected(False)
        self.variables_inspector.set_connected(False)
        self.pid_tuner.set_connected(False)
        self.can_monitor.set_connected(False)

    def _on_device_error(self, error_msg: str):
        """Handle device error."""
        self.status_message.setText(f"Error: {error_msg}")
        logger.error(f"Device error: {error_msg}")

    def _on_device_reconnecting(self, attempt: int, max_attempts: int):
        """Handle reconnection attempt."""
        max_str = str(max_attempts) if max_attempts > 0 else "∞"
        self.device_status_label.setText("RECONNECTING...")
        self.device_status_label.setStyleSheet("color: #f59e0b;")  # Orange/amber
        self.status_message.setText(f"Reconnecting... attempt {attempt}/{max_str}")
        logger.info(f"Reconnection attempt {attempt}/{max_str}")

    def _on_device_reconnect_failed(self):
        """Handle reconnection failure (all attempts exhausted)."""
        self.device_status_label.setText("OFFLINE")
        self.device_status_label.setStyleSheet("color: #ef4444;")
        self.status_message.setText("Reconnection failed - all attempts exhausted")
        logger.warning("All reconnection attempts exhausted")

    def _on_device_connected(self):
        """Handle device connection (including after reconnect)."""
        self.device_status_label.setText("ONLINE")
        self.device_status_label.setStyleSheet("color: #22c55e;")  # Green
        self.status_message.setText("Connected to device")
        self.pmu_monitor.set_connected(True)
        self.output_monitor.set_connected(True)
        self.analog_monitor.set_connected(True)
        self.digital_monitor.set_connected(True)
        self.variables_inspector.set_connected(True)
        self.pid_tuner.set_connected(True)
        self.can_monitor.set_connected(True)

    def _on_item_add_requested(self, channel_type_str: str):
        """Handle request to add new item by Channel type."""
        try:
            channel_type = ChannelType(channel_type_str)
        except ValueError:
            return

        available_channels = self._get_available_channels()

        # Get all existing channels for ID generation
        existing_channels = self.project_tree.get_all_channels()

        if channel_type == ChannelType.DIGITAL_INPUT:
            used_pins = self.project_tree.get_all_used_digital_input_pins()
            logger.debug(f"Creating new digital input, used_pins={used_pins}")
            dialog = DigitalInputDialog(self, None, available_channels, used_pins, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                logger.debug(f"New digital input config: input_pin={config.get('input_pin')}, name={config.get('name')}")
                self.project_tree.add_channel(channel_type, config)
                self.digital_monitor.set_inputs(self.project_tree.get_all_inputs())
                self.configuration_changed.emit()

        elif channel_type == ChannelType.ANALOG_INPUT:
            used_pins = self.project_tree.get_all_used_analog_input_pins()
            logger.debug(f"Creating new analog input, used_pins={used_pins}")
            dialog = AnalogInputDialog(self, None, available_channels, used_pins, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                logger.debug(f"New analog input config: input_pin={config.get('input_pin')}, name={config.get('name')}")
                self.project_tree.add_channel(channel_type, config)
                self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
                self.configuration_changed.emit()

        elif channel_type == ChannelType.POWER_OUTPUT:
            used_pins = self.project_tree.get_all_used_output_pins()
            dialog = OutputConfigDialog(self, None, used_pins, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
                self.configuration_changed.emit()
                # Apply channel state immediately to device
                self._apply_output_to_device(config)

        elif channel_type == ChannelType.HBRIDGE:
            used_bridges = self.project_tree.get_all_used_hbridge_numbers()
            dialog = HBridgeDialog(self, None, used_bridges, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.hbridge_monitor.set_hbridges(self.project_tree.get_all_hbridges())
                self.configuration_changed.emit()

        elif channel_type == ChannelType.LOGIC:
            dialog = LogicDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.NUMBER:
            dialog = NumberDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.TIMER:
            dialog = TimerDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.SWITCH:
            dialog = SwitchDialog(self, None, available_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.TABLE_2D:
            dialog = Table2DDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.TABLE_3D:
            dialog = Table3DDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.ENUM:
            dialog = EnumDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.FILTER:
            dialog = FilterDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.CAN_RX:
            # CAN RX = CAN Input (signal extraction from CAN Message)
            # Get list of CAN messages from config_manager
            message_ids = [msg.get("id", "") for msg in self.config_manager.get_config().get("can_messages", [])]
            if not message_ids:
                QMessageBox.warning(
                    self, "No CAN Messages",
                    "Please create at least one CAN Message before adding CAN Inputs.\n\n"
                    "Use the CAN Bus tab to create CAN Messages first."
                )
                return

            existing_ids = [ch.get("id", "") for ch in self.project_tree.get_all_channels()]

            dialog = CANInputDialog(
                self,
                input_config=None,
                message_ids=message_ids,
                existing_channel_ids=existing_ids
            )
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.CAN_TX:
            existing_ids = [ch.get("id", "") for ch in self.project_tree.get_all_channels()]
            available_channels = self._get_available_channels()

            dialog = CANOutputDialog(
                self,
                output_config=None,
                existing_ids=existing_ids,
                available_channels=available_channels
            )
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.LUA_SCRIPT:
            dialog = LuaScriptTreeDialog(self, None, available_channels, existing_channels)
            dialog.run_requested.connect(self._on_lua_run_requested)
            dialog.stop_requested.connect(self._on_lua_stop_requested)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.PID:
            dialog = PIDControllerDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.BLINKMARINE_KEYPAD:
            dialog = BlinkMarineKeypadDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                # Auto-create virtual channels for each button (ECUMaster style)
                self._sync_keypad_button_channels(config)
                self.configuration_changed.emit()

        elif channel_type == ChannelType.HANDLER:
            dialog = HandlerDialog(self, None, available_channels, existing_channels)
            if dialog.exec():
                config = dialog.get_config()
                self.project_tree.add_channel(channel_type, config)
                self.configuration_changed.emit()

    def _on_item_edit_requested(self, channel_type_str: str, data: dict):
        """Handle request to edit item by Channel type."""
        logger.info(f"Edit requested: type={channel_type_str}, id={data.get('data', {}).get('id', 'unknown')}")

        try:
            channel_type = ChannelType(channel_type_str)
        except ValueError:
            logger.error(f"Invalid channel type: {channel_type_str}")
            return

        item_data = data.get("data", {})
        if not item_data:
            logger.warning("Edit requested but no item data provided")
            return

        available_channels = self._get_available_channels()
        logger.debug(f"Opening dialog for {channel_type.value}: {item_data.get('id', 'unnamed')}")

        # Prevent double-click re-entry while dialog is open
        if hasattr(self, '_edit_dialog_open') and self._edit_dialog_open:
            logger.warning("Edit dialog already open, ignoring duplicate request")
            return
        self._edit_dialog_open = True

        try:
            # Get all existing channels for ID generation
            existing_channels = self.project_tree.get_all_channels()

            if channel_type == ChannelType.DIGITAL_INPUT:
                # Check if this is a keypad button - those are edited via the keypad dialog
                from models.channel import DigitalInputSubtype
                if item_data and item_data.get('subtype') == DigitalInputSubtype.KEYPAD_BUTTON.value:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self, "Keypad Button",
                        "This is a virtual button from a CAN keypad.\n"
                        "Edit it via the CAN Keypads section."
                    )
                    return

                # Exclude current channel's pin from used list when editing
                channel_id = item_data.get('name') if item_data else None
                used_pins = self.project_tree.get_all_used_digital_input_pins(exclude_channel_id=channel_id)
                dialog = DigitalInputDialog(self, item_data, available_channels, used_pins, existing_channels)
                logger.debug("Opening DigitalInputDialog")
                result = dialog.exec()
                logger.debug(f"DigitalInputDialog result: {result}")
                if result:
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)
                    logger.info(f"Digital input updated: {updated_config.get('name')}")

            elif channel_type == ChannelType.ANALOG_INPUT:
                # Exclude current channel's pin from used list when editing
                channel_id = item_data.get('name') if item_data else None
                used_pins = self.project_tree.get_all_used_analog_input_pins(exclude_channel_id=channel_id)
                dialog = AnalogInputDialog(self, item_data, available_channels, used_pins, existing_channels)
                logger.debug("Opening AnalogInputDialog")
                result = dialog.exec()
                logger.debug(f"AnalogInputDialog result: {result}")
                if result:
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)
                    self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
                    logger.info(f"Analog input updated: {updated_config.get('name')}")

            elif channel_type == ChannelType.POWER_OUTPUT:
                # Exclude current channel's pins from used list when editing
                channel_id = item_data.get('name') if item_data else None
                used_pins = self.project_tree.get_all_used_output_pins(exclude_channel_id=channel_id)
                dialog = OutputConfigDialog(self, item_data, used_pins, available_channels, existing_channels)
                logger.debug("Opening OutputConfigDialog")
                result = dialog.exec()
                logger.debug(f"OutputConfigDialog result: {result}")
                if result:
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)
                    self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
                    # Apply channel state immediately to device (without flash save)
                    self._apply_output_to_device(updated_config)
                    logger.info(f"Output updated and applied: {updated_config.get('name')}")

            elif channel_type == ChannelType.HBRIDGE:
                # Exclude current channel's bridge from used list when editing
                channel_id = item_data.get('name') if item_data else None
                used_bridges = self.project_tree.get_all_used_hbridge_numbers(exclude_channel_id=channel_id)
                dialog = HBridgeDialog(self, item_data, used_bridges, available_channels, existing_channels)
                logger.debug("Opening HBridgeDialog")
                result = dialog.exec()
                logger.debug(f"HBridgeDialog result: {result}")
                if result:
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)
                    self.hbridge_monitor.set_hbridges(self.project_tree.get_all_hbridges())
                    logger.info(f"H-Bridge updated: {updated_config.get('name')}")

            elif channel_type == ChannelType.LOGIC:
                dialog = LogicDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.NUMBER:
                dialog = NumberDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.TIMER:
                dialog = TimerDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.SWITCH:
                dialog = SwitchDialog(self, item_data, available_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.TABLE_2D:
                dialog = Table2DDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.TABLE_3D:
                dialog = Table3DDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.ENUM:
                dialog = EnumDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.FILTER:
                dialog = FilterDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.CAN_RX:
                # CAN RX = CAN Input (signal extraction from CAN Message)
                message_ids = [msg.get("id", "") for msg in self.config_manager.get_config().get("can_messages", [])]
                existing_ids = [ch.get("id", "") for ch in self.project_tree.get_all_channels()]

                dialog = CANInputDialog(
                    self,
                    input_config=item_data,
                    message_ids=message_ids,
                    existing_channel_ids=existing_ids
                )
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.CAN_TX:
                existing_ids = [ch.get("id", "") for ch in self.project_tree.get_all_channels()]
                available_channels = self._get_available_channels()

                dialog = CANOutputDialog(
                    self,
                    output_config=item_data,
                    existing_ids=existing_ids,
                    available_channels=available_channels
                )
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.LUA_SCRIPT:
                dialog = LuaScriptTreeDialog(self, item_data, available_channels, existing_channels)
                dialog.run_requested.connect(self._on_lua_run_requested)
                dialog.stop_requested.connect(self._on_lua_stop_requested)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.PID:
                dialog = PIDControllerDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

            elif channel_type == ChannelType.BLINKMARINE_KEYPAD:
                old_keypad_id = item_data.get("id", "")
                dialog = BlinkMarineKeypadDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)
                    # Sync virtual channels for keypad buttons (ECUMaster style)
                    self._sync_keypad_button_channels(updated_config, old_keypad_id)

            elif channel_type == ChannelType.HANDLER:
                dialog = HandlerDialog(self, item_data, available_channels, existing_channels)
                if dialog.exec():
                    updated_config = dialog.get_config()
                    self.project_tree.update_current_item(updated_config)

        except Exception as e:
            logger.error(f"Error in channel edit dialog: {e}")
        finally:
            self._edit_dialog_open = False

    def _get_available_channels(self) -> dict:
        """Get all available channels for selection organized by Channel type.

        Returns dict with lists of tuples: (string_id: str, display_name: str)
        where string_id is the channel's 'id' field used for firmware references.
        The firmware expects string channel names like "Timer_7", not numeric IDs.
        """
        def get_channel_info(ch):
            """Extract (string_id, display_name) from channel config."""
            # Use string 'id' field for firmware references, not numeric channel_id
            string_id = ch.get("id", ch.get("name", ""))
            display_name = ch.get("name", string_id)
            return (string_id, display_name)

        channels = {
            # Channel format - lists of (string_id, display_name) tuples
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
            "lua_scripts": [],
            "pid_controllers": [],
        }

        # Add channels from project tree
        for ch in self.project_tree.get_channels_by_type(ChannelType.DIGITAL_INPUT):
            channels["digital_inputs"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.ANALOG_INPUT):
            channels["analog_inputs"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.POWER_OUTPUT):
            channels["power_outputs"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.LOGIC):
            channels["logic"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.NUMBER):
            channels["numbers"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.TABLE_2D):
            channels["tables_2d"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.TABLE_3D):
            channels["tables_3d"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.SWITCH):
            channels["switches"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.TIMER):
            channels["timers"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.FILTER):
            channels["filters"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.ENUM):
            channels["enums"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.CAN_RX):
            channels["can_rx"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.CAN_TX):
            channels["can_tx"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.LUA_SCRIPT):
            channels["lua_scripts"].append(get_channel_info(ch))

        for ch in self.project_tree.get_channels_by_type(ChannelType.PID):
            channels["pid_controllers"].append(get_channel_info(ch))

        return channels

    def _sync_keypad_button_channels(self, keypad_config: dict, old_keypad_id: str = None):
        """
        Sync virtual channels for keypad buttons (ECUMaster style).

        Each button on a BlinkMarine keypad creates a virtual digital input channel
        with ID format: {keypad_id}.btn{N} (e.g., "keypad1.btn1", "keypad1.btn2")

        These channels can be used as Control Function sources for power outputs.
        """
        from models.channel import DigitalInputSubtype, ButtonMode

        keypad_id = keypad_config.get("id", "")
        keypad_type = keypad_config.get("keypad_type", "2x6")
        button_count = 12 if keypad_type == "2x6" else 16
        button_configs = keypad_config.get("buttons", {})

        # If keypad ID changed, remove old button channels
        if old_keypad_id and old_keypad_id != keypad_id:
            self._remove_keypad_button_channels(old_keypad_id)

        # Create/update virtual channels for each button
        for btn_idx in range(button_count):
            btn_channel_id = f"{keypad_id}.btn{btn_idx + 1}"
            btn_config = button_configs.get(btn_idx, button_configs.get(str(btn_idx), {}))

            # Get button-specific settings
            btn_name = btn_config.get("name", f"Button {btn_idx + 1}")
            press_action = btn_config.get("press_action", "Set High")

            # Determine button mode from press action
            if "Toggle" in press_action:
                button_mode = ButtonMode.TOGGLE.value
            elif "Latching" in press_action or "Latch" in press_action:
                button_mode = ButtonMode.LATCHING.value
            else:
                button_mode = ButtonMode.MOMENTARY.value

            # Create virtual channel config
            channel_config = {
                "channel_type": "digital_input",
                "id": btn_channel_id,
                "name": f"{keypad_config.get('name', keypad_id)} - {btn_name}",
                "subtype": DigitalInputSubtype.KEYPAD_BUTTON.value,
                "keypad_id": keypad_id,
                "button_index": btn_idx,
                "button_mode": button_mode,
                "invert": False,
            }

            # Check if channel already exists
            existing = self._find_channel_by_id(btn_channel_id)
            if existing:
                # Update existing channel
                self.project_tree.update_channel_by_id(btn_channel_id, channel_config)
            else:
                # Add new channel
                self.project_tree.add_channel(ChannelType.DIGITAL_INPUT, channel_config)

        logger.info(f"Synced {button_count} button channels for keypad '{keypad_id}'")

    def _remove_keypad_button_channels(self, keypad_id: str):
        """Remove all button channels for a keypad."""
        for btn_idx in range(16):  # Max buttons
            btn_channel_id = f"{keypad_id}.btn{btn_idx + 1}"
            self.project_tree.remove_channel_by_id(btn_channel_id)
        logger.info(f"Removed button channels for keypad '{keypad_id}'")

    def _find_channel_by_id(self, channel_id: str) -> dict:
        """Find a channel by its ID."""
        all_channels = self.project_tree.get_all_channels()
        for ch in all_channels:
            if ch.get("id") == channel_id:
                return ch
        return None

    def _on_item_deleted(self, channel_type_str: str, data: dict):
        """Handle item deletion - cleanup related channels."""
        try:
            channel_type = ChannelType(channel_type_str)
        except ValueError:
            return

        item_data = data.get("data", {})

        # When a BlinkMarine keypad is deleted, remove all its button channels
        if channel_type == ChannelType.BLINKMARINE_KEYPAD:
            keypad_id = item_data.get("id", "")
            if keypad_id:
                self._remove_keypad_button_channels(keypad_id)
                logger.info(f"Removed button channels for deleted keypad '{keypad_id}'")

    def _on_config_changed(self):
        """Handle configuration change."""
        self.config_manager.modified = True

        # Sync channels from project_tree to config_manager
        config = self.config_manager.get_config()
        config["channels"] = self.project_tree.get_all_channels()

        # Refresh Variables Inspector to show new channels
        self.variables_inspector.populate_from_config(self.config_manager)

        # Refresh Data Logger with virtual channels
        self.data_logger.populate_from_config(self.config_manager)

        # Auto-send configuration to device (without flash save)
        self._send_config_to_device_silent()

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
            "PMU-30 Configuration (*.pmu30 *.json);;All Files (*.*)"
        )

        if filename:
            self._load_configuration_file(filename)

    def _load_configuration_file(self, filename: str):
        """Load configuration from a specific file path."""
        success, error_msg = self.config_manager.load_from_file(filename)
        if success:
            self._load_config_to_ui()
            self.status_message.setText(f"Loaded: {filename}")
            logger.info(f"Configuration loaded from file: {filename}")
        else:
            QMessageBox.critical(self, "Error", error_msg)
            logger.error(f"Failed to load configuration: {error_msg}")

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

        # Sync keypad button channels for all keypads (ECUMaster style)
        keypads = self.project_tree.get_all_blinkmarine_keypads()
        for keypad_config in keypads:
            self._sync_keypad_button_channels(keypad_config)

        # Update monitors
        self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
        self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
        self.digital_monitor.set_inputs(self.project_tree.get_all_inputs())
        self.hbridge_monitor.set_hbridges(self.project_tree.get_all_hbridges())

        # Update PID tuner with available PID controllers
        pid_controllers = [ch for ch in channels if ch.get("channel_type") == "pid"]
        self.pid_tuner.set_controllers(pid_controllers)

        # Update CAN monitor with CAN configuration
        can_messages = config.get("can_messages", [])
        can_inputs = [ch for ch in channels if ch.get("channel_type") == "can_rx"]
        self.can_monitor.set_configuration(can_messages, can_inputs)

        # Update variables inspector
        self.variables_inspector.populate_from_config(self.config_manager)

        # Update data logger with virtual channels
        self.data_logger.populate_from_config(self.config_manager)

        # Update channel dependency graph
        self._update_channel_graph(channels)

    def _update_channel_graph(self, channels: list):
        """Update channel dependency graph."""
        # Prepare channel data with input_channels for graph
        graph_data = []
        for ch in channels:
            ch_data = {
                'id': ch.get('id', ''),
                'name': ch.get('name', ch.get('id', '')),
                'type': ch.get('channel_type', 'logic'),
                'channel_id': ch.get('channel_id'),  # Numeric ID for resolving references
                'input_channels': []
            }

            # Extract input channels based on channel type
            ch_type = ch.get('channel_type', '')

            if ch_type == 'power_output':
                if ch.get('source_channel'):
                    ch_data['input_channels'].append(ch['source_channel'])
                if ch.get('duty_channel'):
                    ch_data['input_channels'].append(ch['duty_channel'])

            elif ch_type == 'logic':
                for inp in ch.get('inputs', []):
                    if isinstance(inp, dict) and inp.get('channel'):
                        ch_data['input_channels'].append(inp['channel'])
                    elif isinstance(inp, str):
                        ch_data['input_channels'].append(inp)
                if ch.get('set_channel'):
                    ch_data['input_channels'].append(ch['set_channel'])
                if ch.get('reset_channel'):
                    ch_data['input_channels'].append(ch['reset_channel'])
                if ch.get('toggle_channel'):
                    ch_data['input_channels'].append(ch['toggle_channel'])

            elif ch_type == 'timer':
                if ch.get('start_channel'):
                    ch_data['input_channels'].append(ch['start_channel'])
                if ch.get('stop_channel'):
                    ch_data['input_channels'].append(ch['stop_channel'])

            elif ch_type == 'filter':
                if ch.get('input_channel'):
                    ch_data['input_channels'].append(ch['input_channel'])

            elif ch_type == 'table_2d':
                if ch.get('x_axis_channel'):
                    ch_data['input_channels'].append(ch['x_axis_channel'])

            elif ch_type == 'table_3d':
                if ch.get('x_axis_channel'):
                    ch_data['input_channels'].append(ch['x_axis_channel'])
                if ch.get('y_axis_channel'):
                    ch_data['input_channels'].append(ch['y_axis_channel'])

            elif ch_type == 'number':
                for inp in ch.get('inputs', []):
                    if isinstance(inp, dict) and inp.get('channel'):
                        ch_data['input_channels'].append(inp['channel'])

            elif ch_type == 'pid':
                if ch.get('setpoint_channel'):
                    ch_data['input_channels'].append(ch['setpoint_channel'])
                if ch.get('process_channel'):
                    ch_data['input_channels'].append(ch['process_channel'])

            elif ch_type == 'hbridge':
                if ch.get('source_channel'):
                    ch_data['input_channels'].append(ch['source_channel'])
                if ch.get('duty_channel'):
                    ch_data['input_channels'].append(ch['duty_channel'])
                if ch.get('direction_channel'):
                    ch_data['input_channels'].append(ch['direction_channel'])
                if ch.get('pid_setpoint_channel'):
                    ch_data['input_channels'].append(ch['pid_setpoint_channel'])

            elif ch_type == 'enum':
                if ch.get('input_up_channel'):
                    ch_data['input_channels'].append(ch['input_up_channel'])
                if ch.get('input_down_channel'):
                    ch_data['input_channels'].append(ch['input_down_channel'])

            elif ch_type == 'can_tx':
                for sig in ch.get('signals', []):
                    if sig.get('source_channel'):
                        ch_data['input_channels'].append(sig['source_channel'])

            graph_data.append(ch_data)

        self.channel_graph.set_channels(graph_data)

    def _on_graph_channel_edit(self, channel_id: str):
        """Handle double-click on graph node to edit channel."""
        # Find channel in tree and open editor
        logger.info(f"Edit channel from graph: {channel_id}")
        item = self.project_tree.find_channel_item(channel_id)
        if item:
            self.project_tree.setCurrentItem(item)
            self._on_project_item_double_clicked(item, 0)

    def _on_graph_refresh_requested(self):
        """Handle refresh request from dependency graph."""
        # Get current channels from project tree
        channels = self.project_tree.get_all_channels()
        if channels:
            self._update_channel_graph(channels)
        else:
            # Try from config manager
            config = self.config_manager.get_config()
            channels = config.get("channels", [])
            self._update_channel_graph(channels)

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
                self.pmu_monitor.set_connected(True)
                self.output_monitor.set_connected(True)
                self.analog_monitor.set_connected(True)
                self.variables_inspector.set_connected(True)

                # Auto-read configuration from device
                QTimer.singleShot(500, self.read_from_device)
            else:
                self.status_message.setText("Connection failed")
                QMessageBox.warning(self, "Connection Failed", "Could not connect to the device.")
        else:
            self.status_message.setText("Connection cancelled")

    def disconnect_device(self):
        """Disconnect from device."""
        self.device_controller.disconnect()
        self.status_message.setText("Disconnected")
        self.device_status_label.setText("OFFLINE")
        self.device_status_label.setStyleSheet("color: #ef4444;")
        self.pmu_monitor.set_connected(False)
        self.output_monitor.set_connected(False)
        self.analog_monitor.set_connected(False)
        self.variables_inspector.set_connected(False)
        self.pid_tuner.set_connected(False)
        self.can_monitor.set_connected(False)

    def read_from_device(self):
        """Read configuration from device."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to device first."
            )
            return

        self.status_message.setText("Reading configuration...")

        # Run in thread to not block UI
        import threading

        def read_config_thread():
            config = self.device_controller.read_configuration(timeout=5.0)
            if config:
                # Use signal to update UI from main thread
                self._config_loaded_signal.emit(config)
            else:
                self._config_load_error_signal.emit()

        thread = threading.Thread(target=read_config_thread, daemon=True)
        thread.start()

    def _load_config_from_device(self, config: dict):
        """Load configuration received from device into UI."""
        try:
            # Clear current project tree
            self.project_tree.clear_all()

            # Load channels from config (suppress signal during bulk loading)
            channels = config.get("channels", [])
            for ch_data in channels:
                ch_type_str = ch_data.get("channel_type", "")
                try:
                    ch_type = ChannelType(ch_type_str)
                    self.project_tree.add_channel(ch_type, ch_data, emit_signal=False)
                except ValueError:
                    logger.warning(f"Unknown channel type: {ch_type_str}")

            # Update monitors
            self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
            self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
            self.digital_monitor.set_inputs(self.project_tree.get_all_inputs())
            self.hbridge_monitor.set_hbridges(self.project_tree.get_all_hbridges())

            # Store config in config_manager
            self.config_manager.load_from_dict(config)

            # Update variables inspector
            self.variables_inspector.populate_from_config(self.config_manager)

            # Update data logger with virtual channels
            self.data_logger.populate_from_config(self.config_manager)

            self.status_message.setText(f"Configuration loaded: {len(channels)} channels")
            logger.info(f"Loaded configuration with {len(channels)} channels")

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.status_message.setText(f"Error loading config: {e}")

    def _show_read_error(self):
        """Show error when config read fails."""
        self.status_message.setText("Failed to read configuration")
        QMessageBox.warning(
            self,
            "Read Failed",
            "Failed to read configuration from device."
        )

    def _apply_output_to_device(self, output_config: dict):
        """Apply output channel state to device immediately (without flash save).

        Sends SET_CHANNEL command for each pin in the output config.
        Channel IDs for PROFET outputs are 100-129 (pin + 100).
        """
        if not self.device_controller.is_connected():
            return

        pins = output_config.get("pins", [])
        enabled = output_config.get("enabled", False)
        pwm_config = output_config.get("pwm", {})

        # Determine value: 0=OFF, 1000=ON, or PWM duty (0-1000)
        if enabled:
            if pwm_config.get("enabled", False):
                # PWM mode: duty value 0-100% -> 0-1000
                value = pwm_config.get("duty_value", 100.0) * 10.0
            else:
                # ON mode: full duty
                value = 1000.0
        else:
            # OFF
            value = 0.0

        # Send SET_CHANNEL for each pin
        for pin in pins:
            channel_id = 100 + pin  # PROFET channel IDs are 100-129
            self.device_controller.set_channel(channel_id, value)
            logger.debug(f"Applied output O{pin+1} = {value}")

        self.status_message.setText(f"Applied output state: {'ON' if enabled else 'OFF'}")

    def _send_config_to_device_silent(self):
        """Send configuration to device silently (no dialogs, no flash save).

        Called automatically when configuration changes in UI.
        """
        if not self.device_controller.is_connected():
            return

        try:
            import json
            import struct

            # Get current configuration as JSON
            config = self.config_manager.get_config()
            config["channels"] = self.project_tree.get_all_channels()
            config["can_messages"] = self.config_manager.get_all_can_messages()

            config_json = json.dumps(config, indent=2).encode('utf-8')

            # Split into chunks (1024 bytes each)
            chunk_size = 1024
            chunks = [
                config_json[i:i + chunk_size]
                for i in range(0, len(config_json), chunk_size)
            ]
            total_chunks = len(chunks)

            # Send each chunk
            for idx, chunk in enumerate(chunks):
                header = struct.pack('<HH', idx, total_chunks)
                payload = header + chunk
                msg_type = 0x22  # SET_CONFIG
                frame_data = struct.pack('<BHB', 0xAA, len(payload), msg_type) + payload

                # Calculate CRC16-CCITT
                crc = 0xFFFF
                for byte in frame_data[1:]:
                    crc ^= byte << 8
                    for _ in range(8):
                        if crc & 0x8000:
                            crc = (crc << 1) ^ 0x1021
                        else:
                            crc <<= 1
                        crc &= 0xFFFF

                frame = frame_data + struct.pack('<H', crc)
                self.device_controller.send_command(frame)

            self.status_message.setText(f"Config synced ({len(config_json)} bytes)")
            logger.debug(f"Config sent to device: {len(config_json)} bytes, {total_chunks} chunks")

        except Exception as e:
            logger.error(f"Failed to send config silently: {e}")
            self.status_message.setText("Config sync failed")

    def write_to_device(self):
        """Write configuration to device (with confirmation dialog)."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to device first."
            )
            return

        try:
            import json
            import struct

            # Get current configuration as JSON
            config = self.config_manager.get_config()

            # Sync channels from project_tree to config
            # (channels are stored in project_tree, not config_manager)
            config["channels"] = self.project_tree.get_all_channels()

            # Sync CAN messages from config_manager
            config["can_messages"] = self.config_manager.get_all_can_messages()

            config_json = json.dumps(config, indent=2).encode('utf-8')

            self.status_message.setText(f"Writing configuration ({len(config_json)} bytes)...")

            # Split into chunks (1024 bytes each)
            chunk_size = 1024
            chunks = [
                config_json[i:i + chunk_size]
                for i in range(0, len(config_json), chunk_size)
            ]
            total_chunks = len(chunks)

            # Send each chunk
            for idx, chunk in enumerate(chunks):
                # Build SET_CONFIG frame
                # Header: chunk_index (2 bytes) + total_chunks (2 bytes)
                header = struct.pack('<HH', idx, total_chunks)
                payload = header + chunk

                # Build protocol frame: 0xAA | len (2B) | msg_type (1B) | payload | CRC (2B)
                msg_type = 0x22  # SET_CONFIG
                frame_data = struct.pack('<BHB', 0xAA, len(payload), msg_type) + payload

                # Calculate CRC16-CCITT
                crc = 0xFFFF
                for byte in frame_data[1:]:  # Skip start byte
                    crc ^= byte << 8
                    for _ in range(8):
                        if crc & 0x8000:
                            crc = (crc << 1) ^ 0x1021
                        else:
                            crc <<= 1
                        crc &= 0xFFFF

                frame = frame_data + struct.pack('<H', crc)

                # Send frame
                self.device_controller.send_command(frame)

                # Update progress
                progress = int((idx + 1) / total_chunks * 100)
                self.status_message.setText(f"Writing configuration... {progress}%")

            # Wait for ACK (simple approach - just wait a bit)
            import time
            time.sleep(0.5)

            self.status_message.setText("Configuration written successfully")
            QMessageBox.information(
                self,
                "Success",
                f"Configuration written to device.\n"
                f"Size: {len(config_json)} bytes\n"
                f"Chunks: {total_chunks}"
            )

        except Exception as e:
            logger.error(f"Failed to write configuration: {e}")
            self.status_message.setText("Write failed")
            QMessageBox.critical(
                self,
                "Write Failed",
                f"Failed to write configuration:\n{str(e)}"
            )

    def save_to_flash(self):
        """Save current configuration to flash (permanent)."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to device first."
            )
            return

        result = QMessageBox.question(
            self,
            "Save to Flash",
            "This will permanently save the current configuration to device flash memory.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            if self.device_controller.save_to_flash():
                self.status_message.setText("Configuration saved to flash")
                QMessageBox.information(self, "Success", "Configuration saved to flash memory.")
            else:
                QMessageBox.warning(self, "Error", "Failed to save configuration to flash.")

    def restart_device(self):
        """Restart the connected device."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to device first."
            )
            return

        result = QMessageBox.question(
            self,
            "Restart Device",
            "Are you sure you want to restart the device?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            if self.device_controller.restart_device():
                self.status_message.setText("Device restart requested")
            else:
                QMessageBox.warning(self, "Error", "Failed to restart device.")

    def show_wifi_settings(self):
        """Show WiFi settings dialog."""
        # Get current WiFi config from system settings
        system_settings = self.config_manager.get_system_settings()
        wifi_config = {"wifi": system_settings.get("wifi", {})}

        dialog = WiFiSettingsDialog(self, config=wifi_config)
        if dialog.exec():
            # Get updated config
            new_config = dialog.get_config()

            # Update WiFi in system settings
            system_settings["wifi"] = new_config.get("wifi", {})
            self.config_manager.update_system_settings(system_settings)

            self.status_message.setText("WiFi settings updated")
            self.configuration_changed.emit()
            logger.info("WiFi settings updated")

    def show_bluetooth_settings(self):
        """Show Bluetooth settings dialog."""
        # Get current Bluetooth config from system settings
        system_settings = self.config_manager.get_system_settings()
        bt_config = {"bluetooth": system_settings.get("bluetooth", {})}

        dialog = BluetoothSettingsDialog(self, config=bt_config)
        if dialog.exec():
            # Get updated config
            new_config = dialog.get_config()

            # Update Bluetooth in system settings
            system_settings["bluetooth"] = new_config.get("bluetooth", {})
            self.config_manager.update_system_settings(system_settings)

            self.status_message.setText("Bluetooth settings updated")
            self.configuration_changed.emit()
            logger.info("Bluetooth settings updated")

    def compare_configurations(self):
        """Compare device configuration with UI configuration."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to device first to compare configurations."
            )
            return

        self.status_message.setText("Reading configuration from device...")

        # Read device config in background
        def read_device_config():
            return self.device_controller.read_configuration(timeout=10.0)

        import threading
        result = [None]
        error = [None]

        def worker():
            try:
                result[0] = read_device_config()
            except Exception as e:
                error[0] = str(e)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=15.0)

        if error[0]:
            QMessageBox.warning(self, "Error", f"Failed to read device config: {error[0]}")
            return

        device_config = result[0]
        if not device_config:
            QMessageBox.warning(self, "Error", "Failed to read configuration from device.")
            return

        # Get UI config
        ui_config = self.config_manager.get_config()

        # Show diff dialog
        dialog = ConfigDiffDialog(self, device_config, ui_config)
        result = dialog.exec()

        if result == 1:  # Sync UI → Device
            reply = QMessageBox.question(
                self,
                "Apply UI to Device",
                "This will overwrite the device configuration with the UI configuration.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.write_to_device()

        elif result == 2:  # Sync Device → UI
            reply = QMessageBox.question(
                self,
                "Apply Device to UI",
                "This will overwrite the UI configuration with the device configuration.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._load_config_from_device(device_config)
                self.status_message.setText("Configuration loaded from device")

    def _on_pid_parameters_changed(self, controller_id: str, params: dict):
        """Handle PID parameter changes from tuner."""
        if not self.device_controller.is_connected():
            self.status_message.setText("Not connected - parameters not sent to device")
            return

        # Update the channel configuration in config manager
        channels = self.project_tree.get_all_channels()
        for ch in channels:
            if ch.get("id") == controller_id or ch.get("channel_id") == controller_id:
                ch["kp"] = params.get("kp", ch.get("kp", 1.0))
                ch["ki"] = params.get("ki", ch.get("ki", 0.0))
                ch["kd"] = params.get("kd", ch.get("kd", 0.0))
                ch["setpoint_value"] = params.get("setpoint", ch.get("setpoint_value", 0.0))
                break

        # TODO: Send live PID parameter update to device via protocol
        # For now, log the change
        logger.info(f"PID parameters changed for {controller_id}: Kp={params.get('kp')}, "
                    f"Ki={params.get('ki')}, Kd={params.get('kd')}, SP={params.get('setpoint')}")
        self.status_message.setText(f"PID {controller_id}: Kp={params.get('kp'):.3f} Ki={params.get('ki'):.3f} Kd={params.get('kd'):.3f}")

    def _on_pid_controller_reset(self, controller_id: str):
        """Handle PID controller reset request from tuner."""
        if not self.device_controller.is_connected():
            self.status_message.setText("Not connected - reset not sent to device")
            return

        # TODO: Send PID reset command to device via protocol
        logger.info(f"PID controller reset requested for {controller_id}")
        self.status_message.setText(f"PID controller {controller_id} reset requested")

    def _on_lua_run_requested(self, script_id: str, script_code: str):
        """Handle Lua script run request from dialog."""
        if not self.device_controller.is_connected():
            self.status_message.setText("Not connected - cannot run Lua script")
            logger.warning(f"Lua run requested but device not connected: {script_id}")
            return

        # TODO: Implement Lua execution via protocol
        # This requires adding PMU_CMD_EXEC_LUA command to firmware protocol
        logger.info(f"Lua script run requested: {script_id}")
        logger.debug(f"Lua code:\n{script_code[:200]}...")  # Log first 200 chars
        self.status_message.setText(f"Lua '{script_id}' execution requested (not yet implemented)")

        # For now, show informative message
        # The actual implementation would send the script to the device and receive output

    def _on_lua_stop_requested(self, script_id: str):
        """Handle Lua script stop request from dialog."""
        if not self.device_controller.is_connected():
            return

        # TODO: Implement Lua stop via protocol
        logger.info(f"Lua script stop requested: {script_id}")
        self.status_message.setText(f"Lua '{script_id}' stop requested")

    def _on_can_send_message(self, arb_id: int, data: bytes, is_extended: bool):
        """Handle CAN message send request from CAN monitor."""
        if not self.device_controller.is_connected():
            self.status_message.setText("Not connected - CAN message not sent")
            return

        # TODO: Send CAN message to device via protocol
        id_str = f"0x{arb_id:08X}" if is_extended else f"0x{arb_id:03X}"
        data_str = " ".join(f"{b:02X}" for b in data)
        logger.info(f"CAN TX: {id_str} [{len(data)}] {data_str}")
        self.status_message.setText(f"CAN TX: {id_str} [{len(data)}] {data_str}")

    def _on_hbridge_command(self, bridge: int, command: str, pwm: int):
        """Handle H-Bridge control command from monitor widget.

        Args:
            bridge: Bridge number (0-3)
            command: Command string ("coast", "forward", "reverse", "brake", "stop")
            pwm: PWM value (0-255)
        """
        # Convert command string to mode number
        mode_map = {
            "coast": 0,
            "stop": 0,
            "forward": 1,
            "reverse": 2,
            "brake": 3,
            "wiper_park": 4,
            "pid": 5
        }
        mode = mode_map.get(command.lower(), 0)

        # Convert PWM 0-255 to duty 0-1000
        duty = (pwm * 1000) // 255

        if self.device_controller.is_connected():
            # Send via protocol
            import asyncio
            asyncio.create_task(
                self.device_controller.comm_manager.set_hbridge(bridge, mode, duty)
            )
            logger.info(f"H-Bridge command: HB{bridge + 1} mode={command} PWM={pwm}")
            self.status_message.setText(f"H-Bridge HB{bridge + 1}: {command.upper()} PWM={pwm}")
        else:
            # Send to emulator via WebSocket if available
            logger.info(f"H-Bridge command (no device): HB{bridge + 1} mode={command} PWM={pwm}")
            self.status_message.setText(f"H-Bridge HB{bridge + 1}: {command.upper()} (not connected)")

    def _on_telemetry_received(self, telemetry):
        """Handle telemetry data from device."""
        try:
            logger.debug(f"Telemetry received: voltage={telemetry.input_voltage_mv}mV, temp={telemetry.temperature_c}C")
            # Update PMU monitor with telemetry data
            data = {
                'voltage_v': telemetry.input_voltage_mv / 1000.0,
                'temperature_c': telemetry.temperature_c,
                'current_a': telemetry.total_current_ma / 1000.0,
                'channel_states': [s.value if hasattr(s, 'value') else s for s in telemetry.profet_states],
                'channel_currents': telemetry.profet_duties,  # PWM duty as current placeholder
                'analog_values': telemetry.adc_values[:8],
                'fault_flags': telemetry.fault_flags.value if hasattr(telemetry.fault_flags, 'value') else 0,
                # Extended telemetry fields
                'board_temp_2': telemetry.board_temp_2,
                'output_5v_mv': telemetry.output_5v_mv,
                'output_3v3_mv': telemetry.output_3v3_mv,
                'flash_temp': telemetry.flash_temp,
                'system_status': telemetry.system_status,
                'uptime_ms': telemetry.timestamp_ms,
            }
            self.pmu_monitor.update_from_telemetry(data)

            # Update output monitor with full telemetry data
            # Convert ChannelState enum values to integers for the output monitor
            states = [int(s) if hasattr(s, 'value') else s for s in telemetry.profet_states]
            duties = list(telemetry.profet_duties)
            currents = list(telemetry.output_currents)  # Estimated from duties
            battery_v = telemetry.input_voltage  # Get battery voltage in V

            self.output_monitor.update_from_telemetry(states, duties, currents, battery_v)

            # Update analog monitor with ADC values (uses switch logic for switch inputs)
            self.analog_monitor.update_from_telemetry(telemetry.adc_values)

            # Update digital monitor with digital input states from telemetry
            self.digital_monitor.update_from_telemetry(telemetry.digital_inputs)

            # Update variables inspector with telemetry data
            variables_data = {
                'board_temp_l': telemetry.temperature_c,
                'board_temp_r': telemetry.board_temp_2,
                'battery_voltage': telemetry.input_voltage,
                'battery_voltage_mv': telemetry.input_voltage_mv,
                'voltage_5v': telemetry.output_5v_mv / 1000.0 if telemetry.output_5v_mv else 0,
                'voltage_3v3': telemetry.output_3v3_mv / 1000.0 if telemetry.output_3v3_mv else 0,
                'pmu_status': telemetry.system_status,
                'user_error': 0,  # TODO: Add user error tracking
                'profet_states': states,
                'profet_currents': currents,
                'profet_duties': duties,  # PWM duty cycles (0-1000)
                'adc_values': list(telemetry.adc_values),
            }

            # Add CAN RX channel values from telemetry (if available)
            if hasattr(telemetry, 'can_rx_values') and telemetry.can_rx_values:
                variables_data['can_rx_values'] = telemetry.can_rx_values
            else:
                # Get CAN inputs from config and show placeholder/last values
                can_rx_values = {}
                try:
                    can_inputs = self.config_manager.get_can_inputs()
                    for ch in can_inputs:
                        ch_id = ch.get('id', '')
                        if ch_id:
                            # Use default value or "?" for now
                            can_rx_values[ch_id] = ch.get('default_value', '?')
                except Exception:
                    pass
                if can_rx_values:
                    variables_data['can_rx_values'] = can_rx_values

            # Add virtual channel values (logic, timer, switch, number)
            if hasattr(telemetry, 'virtual_channels') and telemetry.virtual_channels:
                variables_data['virtual_channels'] = telemetry.virtual_channels
                # Also pass virtual channels to data logger
                data['virtual_channels'] = telemetry.virtual_channels

            self.variables_inspector.update_from_telemetry(variables_data)

            # Update data logger with telemetry data
            self.data_logger.update_from_telemetry(data)
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}")

    def _on_log_received(self, level: int, source: str, message: str):
        """Handle log message from device."""
        level_names = {0: 'DEBUG', 1: 'INFO', 2: 'WARN', 3: 'ERROR'}
        level_name = level_names.get(level, 'INFO')

        log_text = f"[{source}] {message}"
        self.status_message.setText(log_text)

        # Send to log viewer widget
        self.log_viewer.add_log(level_name, source, message)

        # Log to Python logger as well
        if level == 0:
            logger.debug(f"Device: {log_text}")
        elif level == 1:
            logger.info(f"Device: {log_text}")
        elif level == 2:
            logger.warning(f"Device: {log_text}")
        else:
            logger.error(f"Device: {log_text}")

    def show_can_messages_manager(self):
        """Show CAN Messages manager dialog."""
        dialog = CANMessagesManagerDialog(self, self.config_manager)
        dialog.messages_changed.connect(self._on_config_changed)
        dialog.exec()

    def show_can_import_dialog(self):
        """Show CAN Import dialog for importing from .canx and .dbc files."""
        dialog = CANImportDialog(self, self.config_manager)
        dialog.import_completed.connect(self._on_can_import_completed)
        dialog.exec()

    def _on_can_import_completed(self, messages: list, channels: list):
        """Handle imported CAN messages and channels."""
        config = self.config_manager.get_config()

        # Add imported CAN messages
        if "can_messages" not in config:
            config["can_messages"] = []
        config["can_messages"].extend(messages)

        # Add imported channels
        if "channels" not in config:
            config["channels"] = []
        config["channels"].extend(channels)

        self.config_manager.modified = True
        self._on_config_changed()

        # Add imported CAN inputs directly to project tree (don't clear and reload)
        if hasattr(self, 'project_tree'):
            for channel in channels:
                channel_type_str = channel.get("channel_type", "")
                try:
                    channel_type = ChannelType(channel_type_str)
                    self.project_tree.add_channel(channel_type, channel, emit_signal=False)
                except ValueError:
                    logger.warning(f"Unknown channel type: {channel_type_str}")
            self.project_tree.configuration_changed.emit()

        logger.info(f"Imported {len(messages)} CAN message(s) and {len(channels)} CAN input(s)")

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
            "Architecture: Unified Channels<br><br>"
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

    def _reset_layout(self):
        """Reset dock layout to default."""
        # Clear saved state
        self.settings.remove("windowState")

        # Show main panels
        self.project_tree_dock.show()
        self.monitor_dock.show()

        # Reset positions
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_tree_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.monitor_dock)

        # Data Logger dock - reset to bottom, hidden by default
        self.data_logger_dock.hide()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.data_logger_dock)

        # Reset to first tab (PMU Monitor)
        self.monitor_tabs.setCurrentIndex(0)

        logger.info("Layout reset to default")

    def _switch_monitor_tab(self, index: int):
        """Switch to specific monitor tab."""
        self.monitor_dock.show()
        self.monitor_tabs.setCurrentIndex(index)

    def apply_theme(self):
        """Apply dark theme by default."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.setStyle("Fusion")
            ThemeManager.apply_dark_theme(app)

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

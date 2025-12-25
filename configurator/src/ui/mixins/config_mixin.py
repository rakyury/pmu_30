"""
Configuration Management Mixin
Handles configuration file operations and UI sync
"""

import logging
from PyQt6.QtWidgets import QMessageBox, QFileDialog

from models.channel import ChannelType

logger = logging.getLogger(__name__)


class MainWindowConfigMixin:
    """Mixin for configuration file operations."""

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

    def _save_config_from_ui(self):
        """Sync UI state to config manager."""
        config = self.config_manager.get_config()
        config["channels"] = self.project_tree.get_all_channels()
        config["inputs"] = []
        config["outputs"] = []
        config["logic_functions"] = []
        config["timers"] = []
        config["numbers"] = []
        config["switches"] = []
        config["tables"] = []
        self.config_manager.modified = True

    def _load_config_to_ui(self):
        """Load configuration to UI."""
        config = self.config_manager.get_config()
        self.project_tree.clear_all()

        channels = config.get("channels", [])
        if channels:
            self.project_tree.load_channels(channels)
        else:
            self._load_legacy_config(config)

        # Sync keypad button channels
        for keypad_config in self.project_tree.get_all_blinkmarine_keypads():
            self._sync_keypad_button_channels(keypad_config)

        self._update_monitors_from_config(config, channels)
        self._update_channel_graph(channels)

    def _load_legacy_config(self, config: dict):
        """Load legacy format configuration."""
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

    def _update_monitors_from_config(self, config: dict, channels: list):
        """Update all monitors with configuration data."""
        self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
        self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
        self.digital_monitor.set_inputs(self.project_tree.get_all_inputs())
        self.hbridge_monitor.set_hbridges(self.project_tree.get_all_hbridges())

        pid_controllers = [ch for ch in channels if ch.get("channel_type") == "pid"]
        self.pid_tuner.set_controllers(pid_controllers)

        can_messages = config.get("can_messages", [])
        can_inputs = [ch for ch in channels if ch.get("channel_type") == "can_rx"]
        self.can_monitor.set_configuration(can_messages, can_inputs)

        self.variables_inspector.populate_from_config(self.config_manager)
        self.data_logger.populate_from_config(self.config_manager)

    def _on_config_changed(self):
        """Handle configuration change."""
        self.config_manager.modified = True
        config = self.config_manager.get_config()
        config["channels"] = self.project_tree.get_all_channels()

        self.variables_inspector.populate_from_config(self.config_manager)
        self.data_logger.populate_from_config(self.config_manager)
        self._send_config_to_device_silent()

    def _update_channel_graph(self, channels: list):
        """Update channel dependency graph."""
        graph_data = []
        for ch in channels:
            ch_data = {
                'id': ch.get('id', ''),
                'name': ch.get('name', ch.get('id', '')),
                'type': ch.get('channel_type', 'logic'),
                'channel_id': ch.get('channel_id'),
                'input_channels': self._extract_input_channels(ch)
            }
            graph_data.append(ch_data)

        self.channel_graph.set_channels(graph_data)

    def _extract_input_channels(self, ch: dict) -> list:
        """Extract input channel references from a channel config."""
        inputs = []
        ch_type = ch.get('channel_type', '')

        if ch_type == 'power_output':
            if ch.get('source_channel'):
                inputs.append(ch['source_channel'])
            if ch.get('duty_channel'):
                inputs.append(ch['duty_channel'])

        elif ch_type == 'logic':
            # Handle new format with 'channel' and 'channel_2'
            if ch.get('channel'):
                inputs.append(ch['channel'])
            if ch.get('channel_2'):
                inputs.append(ch['channel_2'])
            # Handle legacy format with 'inputs' list
            for inp in ch.get('inputs', []):
                if isinstance(inp, dict) and inp.get('channel'):
                    inputs.append(inp['channel'])
                elif isinstance(inp, str):
                    inputs.append(inp)
            if ch.get('set_channel'):
                inputs.append(ch['set_channel'])
            if ch.get('reset_channel'):
                inputs.append(ch['reset_channel'])
            if ch.get('toggle_channel'):
                inputs.append(ch['toggle_channel'])

        elif ch_type == 'timer':
            if ch.get('start_channel'):
                inputs.append(ch['start_channel'])
            if ch.get('stop_channel'):
                inputs.append(ch['stop_channel'])

        elif ch_type == 'filter':
            if ch.get('input_channel'):
                inputs.append(ch['input_channel'])

        elif ch_type == 'table_2d':
            if ch.get('input_channel'):
                inputs.append(ch['input_channel'])

        elif ch_type == 'table_3d':
            if ch.get('x_input'):
                inputs.append(ch['x_input'])
            if ch.get('y_input'):
                inputs.append(ch['y_input'])

        elif ch_type == 'pid':
            if ch.get('setpoint_channel'):
                inputs.append(ch['setpoint_channel'])
            if ch.get('process_channel'):
                inputs.append(ch['process_channel'])

        elif ch_type == 'hbridge':
            if ch.get('control_channel'):
                inputs.append(ch['control_channel'])
            if ch.get('pwm_channel'):
                inputs.append(ch['pwm_channel'])

        return inputs

    def compare_configurations(self):
        """Compare current configuration with device configuration."""
        from .dialogs.config_diff_dialog import ConfigDiffDialog

        if not self.device_controller.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
            return

        import threading

        self.status_message.setText("Reading device configuration for comparison...")

        def read_device_config():
            return self.device_controller.read_configuration(timeout=5.0)

        def worker():
            device_config = read_device_config()
            if device_config:
                local_config = self.config_manager.get_config()
                local_config["channels"] = self.project_tree.get_all_channels()

                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_show_diff_dialog",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(dict, local_config),
                    Q_ARG(dict, device_config)
                )
            else:
                self.status_message.setText("Failed to read device configuration")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _show_diff_dialog(self, local_config: dict, device_config: dict):
        """Show configuration diff dialog."""
        from .dialogs.config_diff_dialog import ConfigDiffDialog
        dialog = ConfigDiffDialog(self, local_config, device_config)
        dialog.exec()
        self.status_message.setText("Configuration comparison complete")

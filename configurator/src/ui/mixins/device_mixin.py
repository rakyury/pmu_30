"""
Device Communication Mixin
Handles device connection, read/write operations
"""

import logging
import threading
import struct

from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QTimer, Qt

from models.channel import ChannelType
from models.config_migration import ConfigMigration
from models.binary_config import serialize_ui_channels_for_executor

logger = logging.getLogger(__name__)


class MainWindowDeviceMixin:
    """Mixin for device communication operations.

    Requires the following attributes on the main window:
    - device_controller: DeviceController instance
    - status_message: QLabel for status text
    - device_status_label: QLabel for connection status
    - pmu_monitor, output_monitor, analog_monitor, digital_monitor,
      variables_inspector, pid_tuner, can_monitor: Monitor widgets
    - led_indicator: LEDIndicator widget
    - output_leds: OutputLEDs widget
    - _config_loaded_signal: pyqtSignal(dict)
    - _config_load_error_signal: pyqtSignal()
    """

    def connect_device(self):
        """Connect to device."""
        from ui.dialogs.connection_dialog import ConnectionDialog

        dialog = ConnectionDialog(self)
        if dialog.exec() == ConnectionDialog.DialogCode.Accepted:
            config = dialog.get_connection_config()
            self.status_message.setText(f"Connecting to {config.get('type')}...")

            success = self.device_controller.connect(config)

            if success:
                self._set_connected_state(True, config.get('type'))
                # Auto-sync is triggered by connected signal -> _on_device_connected
            else:
                self.status_message.setText("Connection failed")
                QMessageBox.warning(self, "Connection Failed", "Could not connect to the device.")
        else:
            self.status_message.setText("Connection cancelled")

    def connect_to_emulator(self):
        """Quick connect to emulator at localhost:9876 (Ctrl+E)."""
        self.status_message.setText("Connecting to Emulator...")

        config = {
            'type': 'Emulator',
            'host': 'localhost',
            'port': 9876
        }

        success = self.device_controller.connect(config)

        if success:
            self._set_connected_state(True, 'Emulator')
            # Auto-sync is triggered by connected signal -> _on_device_connected
        else:
            self.status_message.setText("Emulator connection failed")
            QMessageBox.warning(self, "Connection Failed",
                              "Could not connect to emulator.\n\n"
                              "Make sure the emulator is running at localhost:9876")

    def disconnect_device(self):
        """Disconnect from device."""
        self.device_controller.disconnect()
        self._set_connected_state(False)

    def _set_connected_state(self, connected: bool, connection_type: str = None):
        """Update UI for connection state including LED indicators."""
        # Update monitor widgets
        widgets = [
            self.pmu_monitor, self.output_monitor, self.analog_monitor,
            self.digital_monitor, self.variables_inspector, self.pid_tuner, self.can_monitor
        ]
        for widget in widgets:
            widget.set_connected(connected)

        # Update status labels
        if connected:
            self.status_message.setText(f"Connected via {connection_type}")
            self.device_status_label.setText("ONLINE")
            self.device_status_label.setStyleSheet("color: #22c55e;")  # Green
            # Update LED indicators
            self.led_indicator.set_connection_status(True, False)
            self.led_indicator.set_can_status(1, True)
        else:
            self.status_message.setText("Disconnected")
            self.device_status_label.setText("OFFLINE")
            self.device_status_label.setStyleSheet("color: #ef4444;")  # Red
            # Update LED indicators
            self.led_indicator.set_connection_status(False, False)
            self.led_indicator.set_can_status(1, False)
            self.led_indicator.set_can_status(2, False)
            self.led_indicator.set_output_status(0, 0)
            self.output_leds.set_all_disconnected()

    def _on_device_disconnected(self):
        """Handle device disconnection."""
        self._set_connected_state(False)

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
        # Update LED indicator
        self.led_indicator.set_connection_status(False, True)

    def _on_device_reconnect_failed(self):
        """Handle reconnection failure."""
        self.device_status_label.setText("OFFLINE")
        self.device_status_label.setStyleSheet("color: #ef4444;")
        self.status_message.setText("Reconnection failed - all attempts exhausted")
        logger.warning("All reconnection attempts exhausted")

    def _on_device_connected(self):
        """Handle device connection (including after reconnect).

        Auto-syncs configuration:
        - Read from device (device is source of truth)
        """
        self._set_connected_state(True, "device")

        # Give device time to fully initialize before syncing config
        # IMPORTANT: Must wait 3000ms for firmware dead period after STOP_STREAM
        # See CLAUDE.md Serial Communication Dead Period section
        QTimer.singleShot(3000, self._auto_sync_config)

    def _auto_sync_config(self):
        """Auto-sync configuration on connection.

        On connection, READ config from device (device is source of truth).
        The device may have config saved in flash from a previous session.
        """
        if not self.device_controller.is_connected():
            return

        # Read config from device - device is source of truth
        # Device may have config in flash from previous session
        logger.info("Auto-syncing: reading config from device")
        self.status_message.setText("Reading configuration from device...")
        self.read_from_device()

    def read_from_device(self):
        """Read configuration from device."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
            return

        self.status_message.setText("Reading configuration...")

        # Show progress dialog
        self._progress = QProgressDialog("Reading configuration from device...", None, 0, 0, self)
        self._progress.setWindowTitle("Please Wait")
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.show()

        def read_config_thread():
            # Use longer timeout (15s) for large configurations
            config = self.device_controller.read_configuration(timeout=15.0)
            if config:
                self._config_loaded_signal.emit(config)
            else:
                self._config_load_error_signal.emit()

        thread = threading.Thread(target=read_config_thread, daemon=True)
        thread.start()

    def _load_config_from_device(self, config: dict):
        """Load configuration received from device into UI."""
        # Close progress dialog if open
        if hasattr(self, '_progress') and self._progress:
            self._progress.close()
            self._progress = None

        try:
            # Ensure all channels have valid channel_id before populating UI
            config = ConfigMigration.ensure_channel_ids(config)
            config = ConfigMigration.ensure_numeric_channel_ids(config)

            # Auto-create missing referenced channels (e.g., DIN 50, 51 for Logic)
            config = self._create_missing_referenced_channels(config)

            # Convert numeric channel IDs to names for dialogs
            config = self._convert_channel_ids_to_names(config)

            self.project_tree.clear_all()

            channels = config.get("channels", [])
            logger.info(f"[DEBUG] Loading {len(channels)} channels into UI")
            for ch_data in channels:
                ch_type_str = ch_data.get("channel_type", "")
                logger.info(f"[DEBUG] Channel: type={ch_type_str}, name={ch_data.get('name')}")
                try:
                    ch_type = ChannelType(ch_type_str)
                    result = self.project_tree.add_channel(ch_type, ch_data, emit_signal=False)
                    logger.info(f"[DEBUG]   -> Added to tree: {result is not None}")
                except ValueError as e:
                    logger.warning(f"Unknown channel type: {ch_type_str} - {e}")
            # Rebind channel references (resolve IDs to names) after all channels loaded
            self.project_tree.rebind_channel_references()

            # Update monitors
            self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
            self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
            self.digital_monitor.set_inputs(self.project_tree.get_all_inputs())
            self.hbridge_monitor.set_hbridges(self.project_tree.get_all_hbridges())

            self.config_manager.load_from_dict(config)
            self.variables_inspector.populate_from_config(self.config_manager)
            self.data_logger.populate_from_config(self.config_manager)

            self.status_message.setText(f"Configuration loaded: {len(channels)} channels")
            logger.info(f"Loaded configuration with {len(channels)} channels")

            # Start telemetry streaming after config is loaded
            if self.device_controller.is_connected():
                self.device_controller.subscribe_telemetry(rate_hz=10)
                logger.info("Telemetry subscription started")

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.status_message.setText(f"Error loading config: {e}")

    def _convert_channel_ids_to_names(self, config: dict) -> dict:
        """Convert numeric channel IDs to channel names for dialog compatibility.

        Logic/Timer/etc. dialogs expect 'channel' and 'channel_2' as names,
        but binary config provides 'input_channels' as numeric IDs.
        """
        channels = config.get("channels", [])

        # Build channel_id -> name mapping
        id_to_name = {}
        for ch in channels:
            ch_id = ch.get("channel_id")
            name = ch.get("name")
            if ch_id is not None and name:
                id_to_name[ch_id] = name

        # Convert Logic channels
        for ch in channels:
            ch_type = ch.get("channel_type", "")

            if ch_type == "logic":
                input_channels = ch.get("input_channels", [])
                if input_channels:
                    # First input -> channel
                    if len(input_channels) >= 1 and input_channels[0] in id_to_name:
                        ch["channel"] = id_to_name[input_channels[0]]
                    # Second input -> channel_2
                    if len(input_channels) >= 2 and input_channels[1] in id_to_name:
                        ch["channel_2"] = id_to_name[input_channels[1]]
                    logger.debug(f"Converted Logic inputs {input_channels} -> "
                                f"channel='{ch.get('channel')}', channel_2='{ch.get('channel_2')}'")

            elif ch_type in ("timer", "filter"):
                # input_channel -> channel
                input_id = ch.get("input_channel")
                if input_id and input_id in id_to_name:
                    ch["channel"] = id_to_name[input_id]
                # start_channel -> channel (for timers)
                start_id = ch.get("start_channel")
                if start_id and start_id in id_to_name:
                    ch["channel"] = id_to_name[start_id]

            elif ch_type in ("table_2d", "table_3d"):
                # x_axis_channel -> channel
                x_id = ch.get("x_axis_channel")
                if x_id and x_id in id_to_name:
                    ch["channel"] = id_to_name[x_id]

            elif ch_type == "pid":
                # setpoint_channel, feedback_channel
                sp_id = ch.get("setpoint_channel")
                if sp_id and sp_id in id_to_name:
                    ch["setpoint_channel"] = id_to_name[sp_id]
                fb_id = ch.get("feedback_channel")
                if fb_id and fb_id in id_to_name:
                    ch["feedback_channel"] = id_to_name[fb_id]

        return config

    def _create_missing_referenced_channels(self, config: dict) -> dict:
        """Auto-create placeholder channels for missing references.

        When config from device contains Logic/Timer/etc. that reference
        channels (e.g., DIN 50, 51) that weren't explicitly saved, create
        placeholder Digital Input channels for them.
        """
        channels = config.get("channels", [])

        # Collect existing channel IDs
        existing_ids = set()
        for ch in channels:
            ch_id = ch.get("channel_id")
            if ch_id is not None:
                existing_ids.add(ch_id)

        # Collect all referenced channel IDs
        referenced_ids = set()
        for ch in channels:
            ch_type = ch.get("channel_type", "")

            # Logic channels reference input_channels
            if ch_type == "logic":
                for ref_id in ch.get("input_channels", []):
                    if isinstance(ref_id, int) and ref_id > 0:
                        referenced_ids.add(ref_id)

            # Timer, Filter, Table reference single input
            if ch_type in ("timer", "filter", "table_2d", "table_3d"):
                ref_id = ch.get("input_channel") or ch.get("start_channel") or ch.get("x_axis_channel")
                if isinstance(ref_id, int) and ref_id > 0:
                    referenced_ids.add(ref_id)

            # PID references setpoint and feedback
            if ch_type == "pid":
                for key in ("setpoint_channel", "feedback_channel"):
                    ref_id = ch.get(key)
                    if isinstance(ref_id, int) and ref_id > 0:
                        referenced_ids.add(ref_id)

            # Power Output references source_id
            if ch_type == "power_output":
                ref_id = ch.get("source_id")
                if isinstance(ref_id, int) and ref_id > 0:
                    referenced_ids.add(ref_id)

        # Find missing references
        missing_ids = referenced_ids - existing_ids

        if missing_ids:
            logger.info(f"Creating placeholder channels for missing refs: {sorted(missing_ids)}")

            for ch_id in sorted(missing_ids):
                # Determine channel type based on ID range
                # 50-57: Digital Inputs (DIN0-DIN7)
                # 0-19: Analog Inputs (AI0-AI19)
                if 50 <= ch_id <= 57:
                    din_idx = ch_id - 50
                    placeholder = {
                        "channel_id": ch_id,
                        "channel_type": "digital_input",
                        "name": f"Digital Input {din_idx}",
                        "enabled": True,
                        "hw_device": 0x11,  # DIN device
                        "hw_index": din_idx,
                        "debounce_ms": 50,
                        "active_high": True,
                        "use_pullup": True,
                    }
                elif 0 <= ch_id <= 19:
                    placeholder = {
                        "channel_id": ch_id,
                        "channel_type": "analog_input",
                        "name": f"Analog Input {ch_id}",
                        "enabled": True,
                        "hw_device": 0x01,  # ADC device
                        "hw_index": ch_id,
                        "raw_min": 0,
                        "raw_max": 4095,
                        "scaled_min": 0,
                        "scaled_max": 1000,
                    }
                else:
                    # Generic placeholder
                    placeholder = {
                        "channel_id": ch_id,
                        "channel_type": "digital_input",
                        "name": f"Channel {ch_id}",
                        "enabled": True,
                    }

                channels.append(placeholder)
                logger.debug(f"Created placeholder: {placeholder['name']} (id={ch_id})")

        config["channels"] = channels
        return config

    def _show_read_error(self):
        """Show error when config read fails."""
        # Close progress dialog if open
        if hasattr(self, '_progress') and self._progress:
            self._progress.close()
            self._progress = None

        self.status_message.setText("Failed to read configuration")
        QMessageBox.warning(self, "Read Failed", "Failed to read configuration from device.")

    def write_to_device(self):
        """Write binary configuration to device."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
            return

        # Show progress dialog
        progress = QProgressDialog("Writing configuration to device...", None, 0, 0, self)
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            channels = self.project_tree.get_all_channels()
            binary_data = serialize_ui_channels_for_executor(channels)
            channel_count = struct.unpack('<H', binary_data[:2])[0] if len(binary_data) >= 2 else 0

            self.status_message.setText(f"Writing configuration ({len(binary_data)} bytes)...")
            QApplication.processEvents()

            # Use upload_binary_config which waits for ACK
            success = self.device_controller.upload_binary_config(binary_data, timeout=10.0)

            progress.close()

            if success:
                self.status_message.setText("Configuration written successfully")
                # Restart telemetry stream (firmware stops it during config load)
                self.device_controller.subscribe_telemetry(rate_hz=10)
                QMessageBox.information(
                    self, "Success",
                    f"Configuration written to device.\n"
                    f"Channels: {channel_count}\n"
                    f"Size: {len(binary_data)} bytes"
                )
            else:
                self.status_message.setText("Write failed - no ACK from device")
                # Try to restart telemetry anyway
                self.device_controller.subscribe_telemetry(rate_hz=10)
                QMessageBox.warning(
                    self, "Write Failed",
                    "Configuration was sent but device did not acknowledge.\n"
                    "Please check device connection and try again."
                )

        except Exception as e:
            progress.close()
            logger.error(f"Failed to write configuration: {e}")
            self.status_message.setText("Write failed")
            QMessageBox.critical(self, "Write Failed", f"Failed to write configuration:\n{str(e)}")

    def _send_config_to_device_silent(self):
        """Send binary configuration to device silently (no dialogs).

        Sends binary config for Channel Executor virtual channels.
        Called automatically when channel configuration changes.

        IMPORTANT: Firmware stops telemetry stream during config load,
        so we must restart it after successful upload.
        """
        if not self.device_controller.is_connected():
            return

        try:
            channels = self.project_tree.get_all_channels()
            binary_data = serialize_ui_channels_for_executor(channels)

            if len(binary_data) > 2:  # More than just channel count
                channel_count = struct.unpack('<H', binary_data[:2])[0]

                # Use upload_binary_config which waits for ACK
                success = self.device_controller.upload_binary_config(binary_data, timeout=5.0)

                if success:
                    self.status_message.setText(f"Config synced ({channel_count} channels, {len(binary_data)} bytes)")
                    logger.info(f"Binary config uploaded: {channel_count} channels, {len(binary_data)} bytes")

                    # CRITICAL: Restart telemetry stream after config upload
                    # Firmware stops the stream during LOAD_BINARY_CONFIG processing
                    self.device_controller.subscribe_telemetry(rate_hz=10)
                    logger.info("Telemetry subscription restarted after config upload")
                else:
                    self.status_message.setText("Config sync failed - no ACK from device")
                    logger.error("Binary config upload failed - no ACK")
                    # Try to restart telemetry anyway in case firmware is in weird state
                    self.device_controller.subscribe_telemetry(rate_hz=10)
            else:
                self.status_message.setText("Config synced (no virtual channels)")
                logger.debug("No virtual channels to sync")
                # Still need to start telemetry even with no channels
                self.device_controller.subscribe_telemetry(rate_hz=10)
                logger.info("Telemetry subscription started (no virtual channels)")

        except Exception as e:
            logger.error(f"Failed to send config silently: {e}")
            self.status_message.setText("Config sync failed")

    def _apply_output_to_device(self, output_config: dict):
        """Apply output channel state to device immediately (on/off only)."""
        if not self.device_controller.is_connected():
            return

        pins = output_config.get("pins", [])
        enabled = output_config.get("enabled", False)

        for pin in pins:
            self.device_controller.set_output(pin, enabled)
            logger.debug(f"Applied output O{pin+1} = {'ON' if enabled else 'OFF'}")

        self.status_message.setText(f"Applied output state: {'ON' if enabled else 'OFF'}")

    def save_to_flash(self):
        """Save current configuration to flash."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
            return

        reply = QMessageBox.question(
            self, "Save to Flash",
            "Save current configuration to device flash memory?\n\n"
            "This will make the configuration permanent.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.status_message.setText("Saving configuration to flash...")

                # Use device controller's save_to_flash which waits for ACK
                success = self.device_controller.save_to_flash(timeout=5.0)

                if success:
                    self.status_message.setText("Configuration saved to flash")
                    # Restart telemetry stream after flash save
                    self.device_controller.subscribe_telemetry(rate_hz=10)
                    logger.info("Telemetry restarted after flash save")
                    QMessageBox.information(self, "Success", "Configuration saved to flash memory.")
                else:
                    self.status_message.setText("Flash save failed")
                    # Try to restart telemetry anyway
                    self.device_controller.subscribe_telemetry(rate_hz=10)
                    QMessageBox.warning(self, "Save Failed",
                                       "Failed to save configuration to flash.\n"
                                       "Device may not have responded.")

            except Exception as e:
                logger.error(f"Failed to save to flash: {e}")
                # Try to restart telemetry on error
                self.device_controller.subscribe_telemetry(rate_hz=10)
                QMessageBox.critical(self, "Error", f"Failed to save to flash:\n{str(e)}")

    def restart_device(self):
        """Restart the device. Configuration will be reloaded when BOOT_COMPLETE is received."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
            return

        reply = QMessageBox.question(
            self, "Restart Device",
            "Restart the device?\n\nThe configuration will be reloaded automatically after restart.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Send RESTART command (0x70)
                frame = struct.pack('<BHB', 0xAA, 0, 0x70)
                crc = self._calculate_crc(frame[1:])
                frame += struct.pack('<H', crc)
                self.device_controller.send_command(frame)

                self.status_message.setText("Device restarting... waiting for BOOT_COMPLETE")
                logger.info("Device restart command sent, waiting for BOOT_COMPLETE signal...")

                # Config will be reloaded when BOOT_COMPLETE signal is received
                # See _on_boot_complete() handler

            except Exception as e:
                logger.error(f"Failed to restart device: {e}")
                QMessageBox.critical(self, "Error", f"Failed to restart device:\n{str(e)}")

    def _on_boot_complete(self):
        """Handle BOOT_COMPLETE signal from device - reload configuration."""
        self.status_message.setText("Boot complete - reading configuration...")
        logger.info("BOOT_COMPLETE received - reloading configuration from device")

        # Read configuration from device (this triggers the full reload)
        self.read_from_device()

    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC16-CCITT."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc

"""
Device Communication Mixin
Handles device connection, read/write operations
"""

import logging
import threading
import struct

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer

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
                # Give device/emulator time to fully initialize before reading config
                QTimer.singleShot(1500, self.read_from_device)
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
            # Give emulator time to fully initialize before reading config
            QTimer.singleShot(1500, self.read_from_device)
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
        """Handle device connection (including after reconnect)."""
        self._set_connected_state(True, "device")

    def read_from_device(self):
        """Read configuration from device."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
            return

        self.status_message.setText("Reading configuration...")

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
        try:
            # Ensure all channels have valid channel_id before populating UI
            config = ConfigMigration.ensure_channel_ids(config)
            config = ConfigMigration.ensure_numeric_channel_ids(config)

            self.project_tree.clear_all()

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

    def _show_read_error(self):
        """Show error when config read fails."""
        self.status_message.setText("Failed to read configuration")
        QMessageBox.warning(self, "Read Failed", "Failed to read configuration from device.")

    def write_to_device(self):
        """Write binary configuration to device."""
        if not self.device_controller.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
            return

        try:
            channels = self.project_tree.get_all_channels()
            binary_data = serialize_ui_channels_for_executor(channels)

            self.status_message.setText(f"Writing configuration ({len(binary_data)} bytes)...")
            total_chunks = self._send_binary_config_chunks(binary_data)

            import time
            time.sleep(0.5)

            # Parse channel count from binary data
            channel_count = struct.unpack('<H', binary_data[:2])[0] if len(binary_data) >= 2 else 0

            self.status_message.setText("Configuration written successfully")
            QMessageBox.information(
                self, "Success",
                f"Configuration written to device.\n"
                f"Channels: {channel_count}\n"
                f"Size: {len(binary_data)} bytes\n"
                f"Chunks: {total_chunks}"
            )

        except Exception as e:
            logger.error(f"Failed to write configuration: {e}")
            self.status_message.setText("Write failed")
            QMessageBox.critical(self, "Write Failed", f"Failed to write configuration:\n{str(e)}")

    def _send_config_to_device_silent(self):
        """Send binary configuration to device silently (no dialogs).

        Sends binary config for Channel Executor virtual channels.
        Called automatically when channel configuration changes.
        """
        if not self.device_controller.is_connected():
            return

        try:
            channels = self.project_tree.get_all_channels()
            binary_data = serialize_ui_channels_for_executor(channels)

            if len(binary_data) > 2:  # More than just channel count
                self._send_binary_config_chunks(binary_data, silent=True)
                channel_count = struct.unpack('<H', binary_data[:2])[0]
                self.status_message.setText(f"Config synced ({channel_count} channels, {len(binary_data)} bytes)")
                logger.debug(f"Binary config sent: {channel_count} channels, {len(binary_data)} bytes")
            else:
                self.status_message.setText("Config synced (no virtual channels)")
                logger.debug("No virtual channels to sync")

        except Exception as e:
            logger.error(f"Failed to send config silently: {e}")
            self.status_message.setText("Config sync failed")

    def _send_binary_config_chunks(self, binary_data: bytes, silent: bool = False) -> int:
        """Send binary config as chunks to device. Returns number of chunks."""
        chunk_size = 1024
        chunks = [binary_data[i:i + chunk_size] for i in range(0, len(binary_data), chunk_size)]
        total_chunks = len(chunks)

        for idx, chunk in enumerate(chunks):
            frame = self._build_binary_config_frame(idx, total_chunks, chunk)
            self.device_controller.send_command(frame)

            if not silent:
                progress = int((idx + 1) / total_chunks * 100)
                self.status_message.setText(f"Writing binary config... {progress}%")

        return total_chunks

    def _build_binary_config_frame(self, chunk_idx: int, total_chunks: int, chunk: bytes) -> bytes:
        """Build protocol frame for binary config chunk."""
        header = struct.pack('<HH', chunk_idx, total_chunks)
        payload = header + chunk
        msg_type = 0x68  # LOAD_BINARY_CONFIG

        frame_data = struct.pack('<BHB', 0xAA, len(payload), msg_type) + payload

        # CRC16-CCITT
        crc = 0xFFFF
        for byte in frame_data[1:]:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF

        return frame_data + struct.pack('<H', crc)

    def _apply_output_to_device(self, output_config: dict):
        """Apply output channel state to device immediately."""
        if not self.device_controller.is_connected():
            return

        pins = output_config.get("pins", [])
        enabled = output_config.get("enabled", False)
        pwm_config = output_config.get("pwm", {})

        if enabled:
            if pwm_config.get("enabled", False):
                value = pwm_config.get("duty_value", 100.0) * 10.0
            else:
                value = 1000.0
        else:
            value = 0.0

        for pin in pins:
            channel_id = 100 + pin
            self.device_controller.set_channel(channel_id, value)
            logger.debug(f"Applied output O{pin+1} = {value}")

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
                # Send SAVE_CONFIG command (0x24)
                frame = struct.pack('<BHB', 0xAA, 0, 0x24)
                crc = self._calculate_crc(frame[1:])
                frame += struct.pack('<H', crc)
                self.device_controller.send_command(frame)

                self.status_message.setText("Configuration saved to flash")
                QMessageBox.information(self, "Success", "Configuration saved to flash memory.")

            except Exception as e:
                logger.error(f"Failed to save to flash: {e}")
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

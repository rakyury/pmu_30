"""
Telemetry Handling Mixin
Handles telemetry data processing and distribution
"""

import logging

logger = logging.getLogger(__name__)


class MainWindowTelemetryMixin:
    """Mixin for telemetry handling."""

    def _on_telemetry_received(self, telemetry):
        """Handle telemetry data from device."""
        try:
            logger.debug(f"Telemetry received: voltage={telemetry.input_voltage_mv}mV, temp={telemetry.temperature_c}C")
            self._update_pmu_monitor(telemetry)
            states = self._update_output_monitor(telemetry)
            self._update_input_monitors(telemetry)
            self._update_variables_inspector(telemetry)
            self._update_data_logger(telemetry)
            self._update_led_indicator(telemetry, states)
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}")

    def _update_pmu_monitor(self, telemetry):
        """Update PMU monitor widget."""
        data = {
            'voltage_v': telemetry.input_voltage_mv / 1000.0,
            'temperature_c': telemetry.temperature_c,
            'current_a': telemetry.total_current_ma / 1000.0,
            'channel_states': [s.value if hasattr(s, 'value') else s for s in telemetry.profet_states],
            'channel_currents': telemetry.profet_duties,
            'analog_values': telemetry.adc_values[:8],
            'fault_flags': telemetry.fault_flags.value if hasattr(telemetry.fault_flags, 'value') else 0,
            'board_temp_2': telemetry.board_temp_2,
            'output_5v_mv': telemetry.output_5v_mv,
            'output_3v3_mv': telemetry.output_3v3_mv,
            'flash_temp': telemetry.flash_temp,
            'system_status': telemetry.system_status,
            'uptime_ms': telemetry.timestamp_ms,
        }
        self.pmu_monitor.update_from_telemetry(data)

    def _update_output_monitor(self, telemetry) -> list:
        """Update output monitor widget. Returns states list for LED update."""
        states = [int(s) if hasattr(s, 'value') else s for s in telemetry.profet_states]
        duties = list(telemetry.profet_duties)
        currents = list(telemetry.output_currents)
        battery_v = telemetry.input_voltage
        self.output_monitor.update_from_telemetry(states, duties, currents, battery_v)
        return states

    def _update_input_monitors(self, telemetry):
        """Update analog and digital monitors."""
        self.analog_monitor.update_from_telemetry(telemetry.adc_values)
        self.digital_monitor.update_from_telemetry(telemetry.digital_inputs)

    def _update_variables_inspector(self, telemetry):
        """Update variables inspector with all telemetry data."""
        states = [int(s) if hasattr(s, 'value') else s for s in telemetry.profet_states]
        currents = list(telemetry.output_currents)
        duties = list(telemetry.profet_duties)

        variables_data = {
            'board_temp_l': telemetry.temperature_c,
            'board_temp_r': telemetry.board_temp_2,
            'battery_voltage': telemetry.input_voltage,
            'battery_voltage_mv': telemetry.input_voltage_mv,
            'voltage_5v': telemetry.output_5v_mv / 1000.0 if telemetry.output_5v_mv else 0,
            'voltage_3v3': telemetry.output_3v3_mv / 1000.0 if telemetry.output_3v3_mv else 0,
            'pmu_status': telemetry.system_status,
            'user_error': 0,
            'profet_states': states,
            'profet_currents': currents,
            'profet_duties': duties,
            'adc_values': list(telemetry.adc_values),
        }

        # Add CAN RX channel values
        if hasattr(telemetry, 'can_rx_values') and telemetry.can_rx_values:
            variables_data['can_rx_values'] = telemetry.can_rx_values
        else:
            variables_data['can_rx_values'] = self._get_can_rx_defaults()

        # Add virtual channel values
        if hasattr(telemetry, 'virtual_channels') and telemetry.virtual_channels:
            variables_data['virtual_channels'] = telemetry.virtual_channels

        self.variables_inspector.update_from_telemetry(variables_data)

    def _update_data_logger(self, telemetry):
        """Update data logger with telemetry data."""
        data = {
            'voltage_v': telemetry.input_voltage_mv / 1000.0,
            'temperature_c': telemetry.temperature_c,
            'current_a': telemetry.total_current_ma / 1000.0,
            'channel_states': [s.value if hasattr(s, 'value') else s for s in telemetry.profet_states],
            'channel_currents': telemetry.profet_duties,
            'analog_values': telemetry.adc_values[:8],
            'uptime_ms': telemetry.timestamp_ms,
        }

        if hasattr(telemetry, 'virtual_channels') and telemetry.virtual_channels:
            data['virtual_channels'] = telemetry.virtual_channels

        self.data_logger.update_from_telemetry(data)

    def _get_can_rx_defaults(self) -> dict:
        """Get CAN RX default values from config."""
        can_rx_values = {}
        try:
            can_inputs = self.config_manager.get_can_inputs()
            for ch in can_inputs:
                ch_id = ch.get('id', '')
                if ch_id:
                    can_rx_values[ch_id] = ch.get('default_value', '?')
        except Exception:
            pass
        return can_rx_values

    def _on_log_received(self, level: int, source: str, message: str):
        """Handle log message from device."""
        level_names = {0: 'DEBUG', 1: 'INFO', 2: 'WARN', 3: 'ERROR'}
        level_name = level_names.get(level, 'INFO')

        log_text = f"[{source}] {message}"
        self.status_message.setText(log_text)
        self.log_viewer.add_log(level_name, source, message)

        # Log to Python logger
        log_funcs = {0: logger.debug, 1: logger.info, 2: logger.warning, 3: logger.error}
        log_funcs.get(level, logger.error)(f"Device: {log_text}")

    def _update_led_indicator(self, telemetry, output_states: list):
        """Update LED indicator bar from telemetry data."""
        from ..widgets.led_indicator import SystemStatus

        try:
            # Count active outputs and faults
            active_count = sum(1 for s in output_states if s in (1, 2))  # ON or PWM
            fault_count = 0

            # Check fault flags from telemetry - per-channel faults
            fault_flags = telemetry.fault_flags.value if hasattr(telemetry.fault_flags, 'value') else telemetry.fault_flags

            # Create per-channel fault list (convert bitmask to list)
            channel_faults = []
            for i in range(min(len(output_states), 40)):
                if fault_flags and (fault_flags & (1 << i)):
                    channel_faults.append(1)
                    fault_count += 1
                else:
                    channel_faults.append(0)

            # Update output channel LEDs (40 channels)
            self.output_leds.update_all_channels(output_states[:40], channel_faults)

            self.led_indicator.set_output_status(active_count, fault_count)

            # Update system status based on protection
            system_status = telemetry.system_status if hasattr(telemetry, 'system_status') else 0
            if system_status >= 4:  # Critical
                self.led_indicator.set_system_status(SystemStatus.CRITICAL)
            elif system_status >= 3:  # Fault
                self.led_indicator.set_system_status(SystemStatus.FAULT)
            elif system_status >= 2:  # Warning
                self.led_indicator.set_system_status(SystemStatus.WARNING)
            else:
                self.led_indicator.set_system_status(SystemStatus.CONNECTED)

            # Flash telemetry LED
            self.led_indicator.telemetry_received()

            # CAN bus status (simplified - just show as online when connected)
            self.led_indicator.set_can_status(1, True, True)
            self.led_indicator.set_can_status(2, True, False)

        except Exception as e:
            logger.debug(f"LED indicator update error: {e}")

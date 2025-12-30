"""
Shared helpers for integration tests.

Provides configuration templates and async test utilities.
"""

import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from communication.emulator_transport import EmulatorTransport
from communication.telemetry import TelemetryPacket, parse_telemetry, ChannelState
from communication.protocol import MessageType, FrameBuilder, encode_frame
from controllers.protocol_handler import ProtocolHandler


# Re-export commonly used types
__all__ = [
    'ChannelState',
    'TelemetryPacket',
    'MessageType',
    'ConfigResponse',
    'AsyncProtocolHandler',
    'EmulatorTransport',
    'BASE_CONFIG',
    'COMPREHENSIVE_TEST_CONFIG',
    'make_output_config',
    'make_digital_input_config',
    'make_analog_input_config',
    'make_logic_config',
    'make_number_config',
    'make_timer_config',
    'make_filter_config',
]


@dataclass
class ConfigResponse:
    """Response from send_config operation."""
    success: bool
    error: Optional[str] = None


class AsyncProtocolHandler:
    """
    Async wrapper for emulator communication.

    Provides an async interface compatible with integration tests.
    """

    def __init__(self, transport: EmulatorTransport):
        self.transport = transport
        self._protocol = ProtocolHandler()
        self._last_telemetry: Optional[TelemetryPacket] = None
        self._receive_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start receiving messages."""
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def stop(self):
        """Stop receiving messages."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

    async def _receive_loop(self):
        """Background task to receive and parse messages."""
        import logging
        logger = logging.getLogger(__name__)

        while True:
            try:
                data = await asyncio.wait_for(
                    self.transport.receive(timeout=0.1),
                    timeout=0.2
                )
                if data:
                    messages = self._protocol.feed_data(data)
                    for msg in messages:
                        # TELEMETRY_DATA = 0x32 (not TELEMETRY)
                        if msg.msg_type == MessageType.TELEMETRY_DATA:
                            self._last_telemetry = parse_telemetry(msg.payload)
                            logger.debug(f"Received telemetry: {len(self._last_telemetry.channel_states)} channels")
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.warning(f"Receive loop error: {e}")
            await asyncio.sleep(0.01)

    async def send_config(self, config_json: str) -> ConfigResponse:
        """Send configuration to the device."""
        try:
            config_bytes = config_json.encode('utf-8')
            chunk_size = 4000
            chunks = [config_bytes[i:i+chunk_size]
                     for i in range(0, len(config_bytes), chunk_size)]

            for idx, chunk in enumerate(chunks):
                frame = self._protocol.build_config_frame(idx, len(chunks), chunk)
                await self.transport.send(frame)
                await asyncio.sleep(0.05)

            return ConfigResponse(success=True)
        except Exception as e:
            return ConfigResponse(success=False, error=str(e))

    async def set_digital_input(self, channel: int, state: bool):
        """Set a digital input state (for emulator testing)."""
        frame = FrameBuilder.emu_set_digital_input(channel, state)
        frame_bytes = encode_frame(frame)
        await self.transport.send(frame_bytes)

    async def set_analog_input(self, channel: int, voltage: float):
        """Set an analog input voltage (for emulator testing).

        Args:
            channel: Input channel number (0-19)
            voltage: Voltage value in volts (0.0-5.0V typical)
        """
        # Convert voltage to millivolts for the protocol
        voltage_mv = int(voltage * 1000)
        frame = FrameBuilder.emu_set_analog_input(channel, voltage_mv)
        frame_bytes = encode_frame(frame)
        await self.transport.send(frame_bytes)

    async def inject_can_message(self, bus_id: int, can_id: int, data: bytes):
        """Inject a CAN message for testing CAN input channels.

        Args:
            bus_id: CAN bus index (0 or 1)
            can_id: CAN message ID (11-bit standard or 29-bit extended)
            data: CAN data bytes (up to 8 bytes)
        """
        frame = FrameBuilder.emu_inject_can(bus_id, can_id, data)
        frame_bytes = encode_frame(frame)
        await self.transport.send(frame_bytes)

    async def get_telemetry(self, timeout: float = 2.0) -> Optional[TelemetryPacket]:
        """Get the latest telemetry packet.

        Subscribes to telemetry if not already subscribed, actively waits for a packet.

        Args:
            timeout: Maximum time to wait for telemetry (seconds)

        Returns:
            TelemetryPacket or None if timeout
        """
        # Clear previous telemetry to ensure we get fresh data
        self._last_telemetry = None

        # Subscribe to telemetry at 10 Hz
        frame = FrameBuilder.subscribe_telemetry(rate_hz=10)
        frame_bytes = encode_frame(frame)
        await self.transport.send(frame_bytes)

        # Actively wait for telemetry to arrive
        start_time = asyncio.get_event_loop().time()
        while self._last_telemetry is None:
            await asyncio.sleep(0.05)  # Give receive loop time to process
            if asyncio.get_event_loop().time() - start_time > timeout:
                break

        return self._last_telemetry

    async def subscribe_telemetry(self, rate_hz: int = 10):
        """Subscribe to telemetry updates."""
        frame = FrameBuilder.subscribe_telemetry(rate_hz=rate_hz)
        frame_bytes = encode_frame(frame)
        await self.transport.send(frame_bytes)

    async def save_to_flash(self) -> bool:
        """Save current configuration to flash."""
        frame = self._protocol.build_frame(MessageType.SAVE_TO_FLASH)
        await self.transport.send(frame)
        await asyncio.sleep(0.5)
        return True


# Test configuration templates
BASE_CONFIG = {
    "version": "1.0",
    "device": {"name": "Test PMU", "type": "PMU-30"},
    "channels": []
}

# =============================================================================
# COMPREHENSIVE TEST CONFIG
# =============================================================================
# This config contains ALL channel types with REAL logic for integration testing.
# It demonstrates proper channel linking:
#   Digital Inputs → Logic Functions → Power Outputs → CAN TX
#   Analog Inputs → Number Functions → Logic Functions → Power Outputs
#
# CRITICAL: All logic/number channels MUST have real operations, not empty!
# =============================================================================

COMPREHENSIVE_TEST_CONFIG = {
    "version": "2.0",
    "device": {"name": "Integration Test PMU", "type": "PMU-30"},
    "channels": [
        # =====================================================================
        # DIGITAL INPUTS (D1-D5)
        # =====================================================================
        {
            "id": "di_ignition",
            "channel_type": "digital_input",
            "enabled": True,
            "subtype": "switch_active_low",  # Default ON
            "input_pin": 0,
            "debounce_ms": 50,
            "threshold_voltage": 2.5
        },
        {
            "id": "di_start_btn",
            "channel_type": "digital_input",
            "enabled": True,
            "subtype": "switch_active_high",  # Default OFF
            "input_pin": 1,
            "debounce_ms": 50,
            "threshold_voltage": 2.5
        },
        {
            "id": "di_brake",
            "channel_type": "digital_input",
            "enabled": True,
            "subtype": "switch_active_low",
            "input_pin": 2,
            "debounce_ms": 20,
            "threshold_voltage": 2.5
        },
        {
            "id": "di_launch_btn",
            "channel_type": "digital_input",
            "enabled": True,
            "subtype": "switch_active_high",
            "input_pin": 3,
            "debounce_ms": 50,
            "threshold_voltage": 2.5
        },
        {
            "id": "di_pit_limiter",
            "channel_type": "digital_input",
            "enabled": True,
            "subtype": "switch_active_high",
            "input_pin": 4,
            "debounce_ms": 50,
            "threshold_voltage": 2.5
        },

        # =====================================================================
        # ANALOG INPUTS (A1-A3)
        # =====================================================================
        {
            "id": "ai_coolant_temp",
            "channel_type": "analog_input",
            "enabled": True,
            "subtype": "linear",
            "input_pin": 5,
            "min_voltage": 0.0,
            "max_voltage": 5.0,
            "min_value": -40.0,
            "max_value": 150.0
        },
        {
            "id": "ai_oil_pressure",
            "channel_type": "analog_input",
            "enabled": True,
            "subtype": "linear",
            "input_pin": 6,
            "min_voltage": 0.5,
            "max_voltage": 4.5,
            "min_value": 0.0,
            "max_value": 10.0
        },
        {
            "id": "ai_throttle",
            "channel_type": "analog_input",
            "enabled": True,
            "subtype": "linear",
            "input_pin": 7,
            "min_voltage": 0.5,
            "max_voltage": 4.5,
            "min_value": 0.0,
            "max_value": 100.0
        },

        # =====================================================================
        # NUMBER CHANNELS - All operation types
        # =====================================================================
        # Constant value
        {
            "id": "n_rpm_threshold",
            "channel_type": "number",
            "enabled": True,
            "operation": "constant",
            "value": 3000.0
        },
        # Maximum of two inputs
        {
            "id": "n_max_temp",
            "channel_type": "number",
            "enabled": True,
            "operation": "max",
            "inputs": ["ai_coolant_temp", "ai_oil_pressure"],
            "input_multipliers": ["*1", "*10"]
        },
        # Minimum of inputs
        {
            "id": "n_min_sensor",
            "channel_type": "number",
            "enabled": True,
            "operation": "min",
            "inputs": ["ai_coolant_temp", "ai_throttle"]
        },
        # Addition
        {
            "id": "n_sum_sensors",
            "channel_type": "number",
            "enabled": True,
            "operation": "add",
            "inputs": ["ai_coolant_temp", "ai_throttle"]
        },
        # Subtraction
        {
            "id": "n_temp_diff",
            "channel_type": "number",
            "enabled": True,
            "operation": "subtract",
            "inputs": ["ai_coolant_temp", "ai_oil_pressure"],
            "input_multipliers": ["*1", "*10"]
        },
        # Multiplication
        {
            "id": "n_product",
            "channel_type": "number",
            "enabled": True,
            "operation": "multiply",
            "inputs": ["ai_throttle", "ai_oil_pressure"]
        },
        # Division
        {
            "id": "n_ratio",
            "channel_type": "number",
            "enabled": True,
            "operation": "divide",
            "inputs": ["ai_throttle", "n_rpm_threshold"]
        },
        # Average
        {
            "id": "n_avg_sensors",
            "channel_type": "number",
            "enabled": True,
            "operation": "average",
            "inputs": ["ai_coolant_temp", "ai_oil_pressure", "ai_throttle"],
            "input_multipliers": ["*1", "*10", "*1"]
        },
        # Scale with multiplier and offset
        {
            "id": "n_scaled_throttle",
            "channel_type": "number",
            "enabled": True,
            "operation": "scale",
            "inputs": ["ai_throttle"],
            "input_multipliers": ["*2.5"],
            "offset": 10.0
        },
        # Clamp to range
        {
            "id": "n_clamped_temp",
            "channel_type": "number",
            "enabled": True,
            "operation": "clamp",
            "inputs": ["ai_coolant_temp"],
            "clamp_min": 0.0,
            "clamp_max": 100.0
        },
        # Absolute value
        {
            "id": "n_abs_diff",
            "channel_type": "number",
            "enabled": True,
            "operation": "abs",
            "inputs": ["n_temp_diff"]
        },

        # =====================================================================
        # LOGIC CHANNELS - All operation types
        # =====================================================================
        # --- Boolean Gates ---
        # AND gate
        {
            "id": "l_start_ready",
            "channel_type": "logic",
            "enabled": True,
            "operation": "and",
            "channel": "di_ignition",
            "channel_2": "di_brake"
        },
        # OR gate
        {
            "id": "l_any_button",
            "channel_type": "logic",
            "enabled": True,
            "operation": "or",
            "channel": "di_start_btn",
            "channel_2": "di_launch_btn"
        },
        # NOT gate
        {
            "id": "l_not_ignition",
            "channel_type": "logic",
            "enabled": True,
            "operation": "not",
            "channel": "di_ignition"
        },
        # XOR gate
        {
            "id": "l_xor_buttons",
            "channel_type": "logic",
            "enabled": True,
            "operation": "xor",
            "channel": "di_start_btn",
            "channel_2": "di_launch_btn"
        },
        # NAND gate
        {
            "id": "l_nand_inputs",
            "channel_type": "logic",
            "enabled": True,
            "operation": "nand",
            "channel": "di_ignition",
            "channel_2": "di_brake"
        },
        # NOR gate
        {
            "id": "l_nor_buttons",
            "channel_type": "logic",
            "enabled": True,
            "operation": "nor",
            "channel": "di_start_btn",
            "channel_2": "di_pit_limiter"
        },

        # --- Comparison Operations ---
        # Greater than constant
        {
            "id": "l_temp_high",
            "channel_type": "logic",
            "enabled": True,
            "operation": "greater",
            "channel": "ai_coolant_temp",
            "constant": 95.0
        },
        # Less than constant
        {
            "id": "l_throttle_low",
            "channel_type": "logic",
            "enabled": True,
            "operation": "less",
            "channel": "ai_throttle",
            "constant": 10.0
        },
        # Equal to constant
        {
            "id": "l_throttle_zero",
            "channel_type": "logic",
            "enabled": True,
            "operation": "equal",
            "channel": "ai_throttle",
            "constant": 0.0
        },
        # Not equal
        {
            "id": "l_throttle_not_zero",
            "channel_type": "logic",
            "enabled": True,
            "operation": "not_equal",
            "channel": "ai_throttle",
            "constant": 0.0
        },
        # Greater or equal
        {
            "id": "l_pressure_ok",
            "channel_type": "logic",
            "enabled": True,
            "operation": "greater_equal",
            "channel": "ai_oil_pressure",
            "constant": 2.0
        },
        # Less or equal
        {
            "id": "l_temp_normal",
            "channel_type": "logic",
            "enabled": True,
            "operation": "less_equal",
            "channel": "ai_coolant_temp",
            "constant": 90.0
        },
        # In range check
        {
            "id": "l_temp_in_range",
            "channel_type": "logic",
            "enabled": True,
            "operation": "in_range",
            "channel": "ai_coolant_temp",
            "range_min": 70.0,
            "range_max": 100.0
        },

        # --- Special Logic ---
        # Hysteresis (Schmitt trigger)
        {
            "id": "l_fan_control",
            "channel_type": "logic",
            "enabled": True,
            "operation": "hysteresis",
            "channel": "ai_coolant_temp",
            "polarity": "normal",
            "threshold_on": 95.0,
            "threshold_off": 85.0
        },
        # Flash/blink
        {
            "id": "l_warning_flash",
            "channel_type": "logic",
            "enabled": True,
            "operation": "flash",
            "channel": "l_temp_high",
            "time_on_s": 0.5,
            "time_off_s": 0.5
        },
        # Pulse (one-shot)
        {
            "id": "l_start_pulse",
            "channel_type": "logic",
            "enabled": True,
            "operation": "pulse",
            "channel": "di_start_btn",
            "pulse_duration_s": 2.0
        },
        # Toggle (flip-flop)
        {
            "id": "l_toggle_mode",
            "channel_type": "logic",
            "enabled": True,
            "operation": "toggle",
            "channel": "di_launch_btn"
        },
        # SR Latch
        {
            "id": "l_fuel_pump_latch",
            "channel_type": "logic",
            "enabled": True,
            "operation": "set_reset_latch",
            "set_channel": "di_ignition",
            "reset_channel": "l_not_ignition"
        },

        # --- Complex Logic Chain ---
        # Combines multiple conditions
        {
            "id": "l_engine_safe",
            "channel_type": "logic",
            "enabled": True,
            "operation": "and",
            "channel": "l_pressure_ok",
            "channel_2": "l_temp_normal"
        },

        # =====================================================================
        # POWER OUTPUTS - Linked to logic/inputs
        # =====================================================================
        # Direct from digital input
        {
            "id": "o_fuel_pump",
            "channel_type": "power_output",
            "enabled": True,
            "output_pins": [0],
            "source_channel": "di_ignition",
            "current_limit_a": 10.0
        },
        # From AND logic
        {
            "id": "o_starter",
            "channel_type": "power_output",
            "enabled": True,
            "output_pins": [1],
            "source_channel": "l_start_ready",
            "current_limit_a": 25.0
        },
        # From hysteresis logic
        {
            "id": "o_fan",
            "channel_type": "power_output",
            "enabled": True,
            "output_pins": [2],
            "source_channel": "l_fan_control",
            "current_limit_a": 15.0,
            "pwm_enabled": True,
            "pwm_frequency_hz": 100
        },
        # From flash logic
        {
            "id": "o_warning_lamp",
            "channel_type": "power_output",
            "enabled": True,
            "output_pins": [3],
            "source_channel": "l_warning_flash",
            "current_limit_a": 2.0
        },
        # From latch logic
        {
            "id": "o_fuel_relay",
            "channel_type": "power_output",
            "enabled": True,
            "output_pins": [4],
            "source_channel": "l_fuel_pump_latch",
            "current_limit_a": 5.0
        },
        # Complex chain: input → number → logic → output
        {
            "id": "o_boost_solenoid",
            "channel_type": "power_output",
            "enabled": True,
            "output_pins": [5],
            "source_channel": "l_engine_safe",
            "current_limit_a": 3.0
        },

        # =====================================================================
        # FILTER CHANNELS
        # =====================================================================
        {
            "id": "flt_throttle",
            "channel_type": "filter",
            "enabled": True,
            "filter_type": "moving_avg",
            "input_channel": "ai_throttle",
            "window_size": 10
        },
        {
            "id": "flt_temp_lp",
            "channel_type": "filter",
            "enabled": True,
            "filter_type": "low_pass",
            "input_channel": "ai_coolant_temp",
            "time_constant": 0.5
        },

        # =====================================================================
        # TIMER CHANNELS
        # =====================================================================
        {
            "id": "tm_engine_runtime",
            "channel_type": "timer",
            "enabled": True,
            "start_channel": "di_ignition",
            "start_edge": "rising",
            "mode": "count_up"
        },
        {
            "id": "tm_starter_timeout",
            "channel_type": "timer",
            "enabled": True,
            "start_channel": "l_start_ready",
            "mode": "oneshot",
            "duration_ms": 5000
        },

        # =====================================================================
        # TABLE CHANNELS
        # =====================================================================
        {
            "id": "t2d_fan_curve",
            "channel_type": "table_2d",
            "enabled": True,
            "x_axis_channel": "ai_coolant_temp",
            "x_values": [70, 80, 90, 100, 110],
            "output_values": [0, 20, 50, 80, 100]
        }
    ],

    # =========================================================================
    # CAN BUS CONFIGURATION
    # =========================================================================
    "can_buses": [
        {
            "bus_id": 0,
            "enabled": True,
            "bitrate": 500000,
            "messages": [
                # Transmit PMU status
                {
                    "id": "ctx_pmu_status",
                    "can_id": 0x600,
                    "direction": "tx",
                    "interval_ms": 100,
                    "signals": [
                        {"name": "ignition", "start_bit": 0, "length": 1, "source_channel": "di_ignition"},
                        {"name": "engine_safe", "start_bit": 1, "length": 1, "source_channel": "l_engine_safe"},
                        {"name": "coolant_temp", "start_bit": 8, "length": 8, "source_channel": "ai_coolant_temp", "scale": 1.0, "offset": 40},
                        {"name": "throttle", "start_bit": 16, "length": 8, "source_channel": "ai_throttle"}
                    ]
                },
                # Transmit outputs status
                {
                    "id": "ctx_outputs",
                    "can_id": 0x601,
                    "direction": "tx",
                    "interval_ms": 100,
                    "signals": [
                        {"name": "fuel_pump", "start_bit": 0, "length": 1, "source_channel": "o_fuel_pump"},
                        {"name": "fan", "start_bit": 1, "length": 1, "source_channel": "o_fan"},
                        {"name": "starter", "start_bit": 2, "length": 1, "source_channel": "o_starter"},
                        {"name": "warning", "start_bit": 3, "length": 1, "source_channel": "o_warning_lamp"}
                    ]
                }
            ]
        }
    ],

    "system": {
        "telemetry_rate_hz": 10,
        "watchdog_timeout_ms": 1000
    }
}


def make_output_config(output_num: int, name: str, source_channel: str,
                       pwm_enabled: bool = False, pwm_frequency: int = 1000,
                       soft_start: bool = False) -> dict:
    """Create power output configuration.

    Note: Uses firmware field names (channel_name, output_pins, etc.)
    """
    config = {
        "channel_id": 100 + output_num,
        "channel_type": "power_output",
        "channel_name": name,  # Firmware uses channel_name
        "output_pins": [output_num - 1],  # Array of output pins (0-based)
        "source_channel": source_channel,
        "pwm_enabled": pwm_enabled,
        "pwm_frequency_hz": pwm_frequency,
        "current_limit_a": 25.0,
    }
    if soft_start:
        config["soft_start_ms"] = 100
    return config


def make_digital_input_config(input_num: int, name: str,
                              input_type: str = "switch_active_high",
                              debounce_ms: int = 50) -> dict:
    """Create digital input configuration.

    Note: Uses firmware field names (channel_name, input_pin, subtype)
    """
    return {
        "channel_id": 200 + input_num,
        "channel_type": "digital_input",
        "channel_name": name,  # Firmware uses channel_name
        "input_pin": input_num - 1,  # Firmware uses input_pin (0-based)
        "subtype": input_type,  # Firmware uses subtype
        "debounce_ms": debounce_ms,
        "threshold_voltage": 2.5,
    }


def make_analog_input_config(input_num: int, name: str,
                             subtype: str = "linear",
                             min_value: float = 0.0,
                             max_value: float = 100.0) -> dict:
    """Create analog input configuration.

    Note: Uses firmware field names (channel_name, input_pin, subtype)
    """
    return {
        "channel_id": 300 + input_num,
        "channel_type": "analog_input",
        "channel_name": name,  # Firmware uses channel_name
        "input_pin": input_num - 1,  # Firmware uses input_pin (0-based)
        "subtype": subtype,  # linear, switch_active_high, etc.
        "min_voltage": 0.0,
        "max_voltage": 5.0,
        "min_value": min_value,
        "max_value": max_value,
    }


def make_logic_config(channel_id: int, name: str, operation: str,
                      input1: str, input2: str = None,
                      constant: float = None) -> dict:
    """Create logic channel configuration.

    Note: Uses firmware field names (channel_name, channel, channel_2)
    """
    config = {
        "channel_id": channel_id,
        "channel_type": "logic",
        "channel_name": name,  # Firmware uses channel_name
        "operation": operation,
        "channel": input1,  # Firmware uses "channel" for input1
    }
    if input2:
        config["channel_2"] = input2  # Firmware uses "channel_2"
    if constant is not None:
        config["constant"] = constant
    return config


def make_timer_config(channel_id: int, name: str, start_channel: str,
                      mode: str = "oneshot", duration_ms: int = 1000) -> dict:
    """Create timer channel configuration.

    Note: Uses firmware field names (channel_name, start_channel_id)
    """
    return {
        "channel_id": channel_id,
        "channel_type": "timer",
        "channel_name": name,  # Firmware uses channel_name
        "start_channel": start_channel,
        "mode": mode,
        "duration_ms": duration_ms,
    }


def make_filter_config(channel_id: int, name: str, input_channel: str,
                       filter_type: str = "lowpass", cutoff_hz: float = 10.0) -> dict:
    """Create filter channel configuration.

    Note: Uses firmware field names (channel_name, input_channel_id)
    """
    return {
        "channel_id": channel_id,
        "channel_type": "filter",
        "channel_name": name,  # Firmware uses channel_name
        "input_channel": input_channel,
        "filter_type": filter_type,
        "cutoff_hz": cutoff_hz,
    }


def make_switch_config(channel_id: int, name: str, input_channel: str,
                       cases: list = None) -> dict:
    """Create switch channel configuration.

    Note: Uses firmware field names (channel_name, input_channel_id)
    """
    return {
        "channel_id": channel_id,
        "channel_type": "switch",
        "channel_name": name,  # Firmware uses channel_name
        "input_channel": input_channel,
        "cases": cases or [],
    }


def make_number_config(channel_id: int, name: str, operation: str,
                       inputs: list = None, value: float = None,
                       multipliers: list = None, offset: float = None,
                       clamp_min: float = None, clamp_max: float = None) -> dict:
    """Create number channel configuration.

    Note: Uses firmware field names (channel_name, operation, inputs)

    Args:
        channel_id: Unique channel ID
        name: Channel name
        operation: One of: constant, add, subtract, multiply, divide,
                   min, max, average, abs, scale, clamp, conditional, lookup3
        inputs: List of input channel names (for non-constant operations)
        value: Constant value (for constant operation)
        multipliers: List of multiplier strings like ["*1", "*2.5"]
        offset: Offset value for scale operation
        clamp_min: Minimum value for clamp operation
        clamp_max: Maximum value for clamp operation
    """
    config = {
        "channel_id": channel_id,
        "channel_type": "number",
        "channel_name": name,
        "operation": operation,
    }
    if operation == "constant":
        config["value"] = value if value is not None else 0.0
    else:
        config["inputs"] = inputs or []
        if multipliers:
            config["input_multipliers"] = multipliers
        if offset is not None:
            config["offset"] = offset
        if clamp_min is not None:
            config["clamp_min"] = clamp_min
        if clamp_max is not None:
            config["clamp_max"] = clamp_max
    return config


def make_table_2d_config(channel_id: int, name: str, input_channel: str,
                         x_values: list = None, y_values: list = None) -> dict:
    """Create 2D table channel configuration.

    Note: Uses firmware field names (channel_name, x_axis_channel)
    """
    return {
        "channel_id": channel_id,
        "channel_type": "table_2d",
        "channel_name": name,  # Firmware uses channel_name
        "x_axis_channel": input_channel,  # Firmware uses x_axis_channel
        "x_values": x_values or [0, 100],
        "y_values": y_values or [0, 100],
    }

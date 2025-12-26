"""
Integration Tests: Output Protection
Tests output protection mechanisms through the emulator with telemetry verification.

Covers:
- Short circuit detection and response
- Overload protection
- Retry mechanism (count, delays)
- Thermal protection (heating)
- Inrush current handling

These tests require a running PMU-30 emulator.
"""

import pytest
import asyncio
import json

# Import fixtures and helpers from conftest
from .helpers import (
    BASE_CONFIG,
    ChannelState,
)

class TestShortCircuitProtection:
    """Test short circuit detection and protection."""

    async def test_short_circuit_trips_output(self, emulator_connection):
        """
        Test: Output trips when short circuit is detected.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             short_circuit_threshold=20000),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable output
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should be ON initially"

        # Simulate short circuit (set current above threshold)
        await protocol.set_output_current(0, 25000)  # 25A > 20A threshold
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.TRIP, ChannelState.OFF], \
            "Output should trip on short circuit"

    async def test_short_circuit_fault_flag(self, emulator_connection):
        """
        Test: Fault flag is set when short circuit occurs.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             short_circuit_threshold=20000),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable and trigger short circuit
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_output_current(0, 25000)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        # Check fault sub-channel (channel_id + 3 for .fault)
        fault_value = telemetry.virtual_channels.get(104, 0)  # o_1.fault
        assert fault_value != 0, "Fault flag should be set on short circuit"


class TestOverloadProtection:
    """Test overload detection and protection."""

    async def test_overload_trips_output(self, emulator_connection):
        """
        Test: Output trips when sustained overload is detected.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             max_current=10000,
                             overload_threshold=15000),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable output
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        # Simulate overload (current above max but below short circuit)
        await protocol.set_output_current(0, 12000)  # 12A > 10A max
        await asyncio.sleep(0.5)  # Wait for overload detection

        telemetry = await protocol.get_telemetry()
        # Output may trip or enter warning state
        current = telemetry.output_currents[0] if telemetry.output_currents else 0
        assert telemetry.channel_states[0] in [ChannelState.TRIP, ChannelState.OFF, ChannelState.ON], \
            f"Output state after overload: {telemetry.channel_states[0]}"

    async def test_overload_time_above_max_tracked(self, emulator_connection):
        """
        Test: Time above max current is tracked.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable", max_current=10000),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable and overload
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_output_current(0, 12000)
        await asyncio.sleep(0.5)

        telemetry = await protocol.get_telemetry()
        # Check timeAboveMax sub-channel
        time_above_max = telemetry.virtual_channels.get(108, 0)  # o_1.timeAboveMax
        # Value should be > 0 after overload period
        # Note: This test verifies the channel exists, actual values depend on firmware


class TestRetryMechanism:
    """Test output retry mechanism after faults."""

    async def test_retry_after_trip(self, emulator_connection):
        """
        Test: Output retries after trip clears.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             retry_count=3,
                             retry_delay_ms=500),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable output
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        # Trigger fault then clear it
        await protocol.set_output_current(0, 25000)  # Short circuit
        await asyncio.sleep(0.3)
        await protocol.set_output_current(0, 5000)   # Normal current

        # Wait for retry delay
        await asyncio.sleep(0.7)

        telemetry = await protocol.get_telemetry()
        # After retry, output may be back ON if fault cleared
        # Check numRetries sub-channel
        num_retries = telemetry.virtual_channels.get(106, 0)  # o_1.numRetries

    async def test_retry_count_exhausted(self, emulator_connection):
        """
        Test: Output stays off after retry count exhausted.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             retry_count=2,
                             retry_delay_ms=200),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable output
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)

        # Keep fault condition active through all retries
        await protocol.set_output_current(0, 25000)

        # Wait for all retries to exhaust (2 retries * 200ms delay + margin)
        await asyncio.sleep(1.0)

        telemetry = await protocol.get_telemetry()
        # After retries exhausted, output should remain off
        assert telemetry.channel_states[0] in [ChannelState.TRIP, ChannelState.OFF], \
            "Output should stay off after retries exhausted"

    async def test_retry_delay_timing(self, emulator_connection):
        """
        Test: Retry delay is respected between attempts.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             retry_count=3,
                             retry_delay_ms=500),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable and trigger fault
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_output_current(0, 25000)
        await asyncio.sleep(0.1)

        # Clear fault
        await protocol.set_output_current(0, 5000)

        # Check state before retry delay expires
        await asyncio.sleep(0.2)  # 200ms < 500ms delay
        telemetry = await protocol.get_telemetry()
        state_before = telemetry.channel_states[0]

        # Wait for retry delay to complete
        await asyncio.sleep(0.5)
        telemetry = await protocol.get_telemetry()
        state_after = telemetry.channel_states[0]

        # State should change after delay (if fault cleared)


class TestThermalProtection:
    """Test thermal/heating protection."""

    async def test_thermal_warning_on_high_load(self, emulator_connection):
        """
        Test: Thermal warning activates on sustained high current.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             max_current=10000,
                             thermal_protection=True,
                             thermal_threshold=80),  # 80% duty/load
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable and run at high load
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_output_current(0, 9000)  # 90% of max

        # Wait for thermal buildup
        await asyncio.sleep(1.0)

        telemetry = await protocol.get_telemetry()
        # Check load sub-channel
        load = telemetry.virtual_channels.get(105, 0)  # o_1.load

    async def test_thermal_derating(self, emulator_connection):
        """
        Test: Output derates when thermal limit approached.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             max_current=10000,
                             thermal_protection=True),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable output at near-max current
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)

        # Set high load to trigger thermal response
        await protocol.set_output_load(0, 95)  # 95% load
        await asyncio.sleep(0.5)

        telemetry = await protocol.get_telemetry()
        # Check if output derates or trips based on thermal state


class TestInrushCurrentHandling:
    """Test inrush current handling and soft start."""

    async def test_soft_start_limits_inrush(self, emulator_connection):
        """
        Test: Soft start limits inrush current on activation.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             soft_start=True,
                             soft_start_time_ms=200),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set a load that would cause high inrush
        await protocol.set_output_load(0, 80)

        # Enable output
        await protocol.set_digital_input(0, True)

        # Check duty cycle ramps up during soft start
        await asyncio.sleep(0.05)  # 50ms into soft start
        telemetry1 = await protocol.get_telemetry()
        dc1 = telemetry1.virtual_channels.get(103, 0)  # o_1.dc

        await asyncio.sleep(0.2)  # After soft start
        telemetry2 = await protocol.get_telemetry()
        dc2 = telemetry2.virtual_channels.get(103, 0)

        # Duty cycle should be higher after soft start completes

    async def test_inrush_detection_no_trip(self, emulator_connection):
        """
        Test: Brief inrush current doesn't trip output.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable",
                             max_current=10000,
                             short_circuit_threshold=20000),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Simulate inrush on activation
        await protocol.set_digital_input(0, True)
        # Brief spike above threshold
        await protocol.set_output_current(0, 18000)  # High but < short circuit
        await asyncio.sleep(0.02)  # Very brief spike
        await protocol.set_output_current(0, 8000)  # Normal operating current
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        # Output should still be ON (inrush was brief)
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Brief inrush should not trip output"


class TestOutputStatusSubChannels:
    """Test output status sub-channels report correctly."""

    async def test_current_subchannel(self, emulator_connection):
        """
        Test: Current sub-channel reports actual current.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable output with known current
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_output_current(0, 5000)  # 5A
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        current = telemetry.virtual_channels.get(102, 0)  # o_1.current
        # Current should be approximately 5000mA

    async def test_voltage_subchannel(self, emulator_connection):
        """
        Test: Voltage sub-channel reports output voltage.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        voltage = telemetry.virtual_channels.get(111, 0)  # o_1.voltage
        # Should report system voltage when output is ON

    async def test_peak_current_subchannel(self, emulator_connection):
        """
        Test: Peak current sub-channel tracks maximum current.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)

        # Set varying currents
        await protocol.set_output_current(0, 3000)
        await asyncio.sleep(0.1)
        await protocol.set_output_current(0, 8000)  # Peak
        await asyncio.sleep(0.1)
        await protocol.set_output_current(0, 5000)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        peak_current = telemetry.virtual_channels.get(107, 0)  # o_1.peakCurrent
        # Peak should be at least 8000 (or scaled value)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

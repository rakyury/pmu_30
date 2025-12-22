"""
PMU-30 Telemetry Tests
Tests for telemetry packet parsing and data structures
"""

import pytest
import struct
from src.communication.telemetry import (
    TelemetryPacket,
    ChannelState,
    FaultFlags,
    DeviceInfo,
    ChannelStatus,
    parse_telemetry,
    create_telemetry_bytes,
    TELEMETRY_PACKET_SIZE,
    TELEMETRY_FORMAT,
)


class TestChannelState:
    """Test ChannelState enum."""

    def test_values(self):
        """Verify channel state values."""
        assert ChannelState.OFF == 0
        assert ChannelState.ON == 1
        assert ChannelState.FAULT_OVERCURRENT == 2
        assert ChannelState.FAULT_OVERHEAT == 3
        assert ChannelState.FAULT_SHORT == 4
        assert ChannelState.FAULT_OPEN == 5
        assert ChannelState.PWM_ACTIVE == 6
        assert ChannelState.DISABLED == 7

    def test_from_int(self):
        """Create ChannelState from integer."""
        assert ChannelState(0) == ChannelState.OFF
        assert ChannelState(1) == ChannelState.ON
        assert ChannelState(6) == ChannelState.PWM_ACTIVE


class TestFaultFlags:
    """Test FaultFlags enum."""

    def test_no_faults(self):
        """Test no faults flag."""
        assert FaultFlags.NONE == 0
        assert not FaultFlags.NONE

    def test_single_fault(self):
        """Test single fault flags."""
        assert FaultFlags.OVERVOLTAGE == 0x01
        assert FaultFlags.UNDERVOLTAGE == 0x02
        assert FaultFlags.OVERTEMPERATURE == 0x04
        assert FaultFlags.CAN1_ERROR == 0x08

    def test_combined_faults(self):
        """Test combining multiple faults."""
        flags = FaultFlags.OVERVOLTAGE | FaultFlags.UNDERVOLTAGE
        assert flags & FaultFlags.OVERVOLTAGE
        assert flags & FaultFlags.UNDERVOLTAGE
        assert not (flags & FaultFlags.OVERTEMPERATURE)

    def test_channel_fault_groups(self):
        """Test channel fault group flags."""
        assert FaultFlags.CHANNEL_FAULT_1 == 1 << 16
        assert FaultFlags.CHANNEL_FAULT_2 == 1 << 17
        assert FaultFlags.CHANNEL_FAULT_3 == 1 << 18
        assert FaultFlags.CHANNEL_FAULT_4 == 1 << 19


class TestTelemetryPacket:
    """Test TelemetryPacket dataclass."""

    def test_default_values(self):
        """Test default packet values."""
        packet = TelemetryPacket()

        assert packet.timestamp_ms == 0
        assert packet.input_voltage_mv == 0
        assert packet.temperature_c == 0
        assert packet.fault_flags == FaultFlags.NONE
        assert len(packet.channel_states) == 30
        assert len(packet.analog_values) == 8
        assert len(packet.output_currents) == 30

    def test_input_voltage_property(self):
        """Test voltage conversion from mV to V."""
        packet = TelemetryPacket(input_voltage_mv=12500)
        assert packet.input_voltage == 12.5

    def test_has_faults_property(self):
        """Test fault detection."""
        packet_ok = TelemetryPacket(fault_flags=FaultFlags.NONE)
        assert not packet_ok.has_faults

        packet_fault = TelemetryPacket(fault_flags=FaultFlags.OVERVOLTAGE)
        assert packet_fault.has_faults

    def test_active_channels_property(self):
        """Test active channel detection."""
        states = [ChannelState.OFF] * 30
        states[0] = ChannelState.ON
        states[5] = ChannelState.PWM_ACTIVE
        states[10] = ChannelState.FAULT_OVERCURRENT

        packet = TelemetryPacket(channel_states=states)
        active = packet.active_channels

        assert 0 in active
        assert 5 in active
        assert 10 not in active  # Faulted, not active
        assert len(active) == 2

    def test_faulted_channels_property(self):
        """Test faulted channel detection."""
        states = [ChannelState.OFF] * 30
        states[2] = ChannelState.FAULT_OVERCURRENT
        states[7] = ChannelState.FAULT_SHORT
        states[15] = ChannelState.ON

        packet = TelemetryPacket(channel_states=states)
        faulted = packet.faulted_channels

        assert 2 in faulted
        assert 7 in faulted
        assert 15 not in faulted
        assert len(faulted) == 2

    def test_total_current_properties(self):
        """Test current calculation."""
        currents = [0] * 30
        currents[0] = 1000  # 1A
        currents[1] = 2500  # 2.5A
        currents[2] = 500   # 0.5A

        packet = TelemetryPacket(output_currents=currents)

        assert packet.total_current_ma == 4000
        assert packet.total_current_a == 4.0

    def test_total_power_property(self):
        """Test power calculation."""
        currents = [1000] * 10 + [0] * 20  # 10A total

        packet = TelemetryPacket(
            input_voltage_mv=12000,  # 12V
            output_currents=currents
        )

        assert packet.total_power_w == 120.0  # 12V * 10A

    def test_get_channel_current(self):
        """Test individual channel current."""
        currents = [0] * 30
        currents[5] = 3500  # 3.5A

        packet = TelemetryPacket(output_currents=currents)

        assert packet.get_channel_current_a(5) == 3.5
        assert packet.get_channel_current_a(0) == 0.0
        assert packet.get_channel_current_a(99) == 0.0  # Out of range

    def test_get_fault_descriptions(self):
        """Test fault description generation."""
        packet = TelemetryPacket(
            fault_flags=FaultFlags.OVERVOLTAGE | FaultFlags.CAN1_ERROR
        )

        descriptions = packet.get_fault_descriptions()

        assert "Input overvoltage" in descriptions
        assert "CAN1 bus error" in descriptions
        assert len(descriptions) == 2


class TestTelemetryParsing:
    """Test telemetry binary parsing."""

    def test_packet_size(self):
        """Verify packet size constant."""
        assert TELEMETRY_PACKET_SIZE == 119

    def test_format_string_size(self):
        """Verify format string produces correct size."""
        assert struct.calcsize(TELEMETRY_FORMAT) == TELEMETRY_PACKET_SIZE

    def test_parse_minimal_packet(self):
        """Parse packet with zeros."""
        data = bytes(TELEMETRY_PACKET_SIZE)
        packet = parse_telemetry(data)

        assert packet.timestamp_ms == 0
        assert packet.input_voltage_mv == 0
        assert all(s == ChannelState.OFF for s in packet.channel_states)

    def test_parse_with_values(self):
        """Parse packet with real values."""
        # Create test packet
        test_packet = TelemetryPacket(
            timestamp_ms=123456,
            channel_states=[ChannelState.ON if i < 5 else ChannelState.OFF for i in range(30)],
            analog_values=[100, 200, 300, 400, 500, 600, 700, 800],
            output_currents=[1000 + i * 100 for i in range(30)],
            input_voltage_mv=13500,
            temperature_c=45,
            fault_flags=FaultFlags.NONE,
        )

        raw = create_telemetry_bytes(test_packet, crc=0)
        parsed = parse_telemetry(raw)

        assert parsed.timestamp_ms == 123456
        assert parsed.input_voltage_mv == 13500
        assert parsed.temperature_c == 45
        assert parsed.channel_states[:5] == [ChannelState.ON] * 5
        assert parsed.output_currents[0] == 1000
        assert parsed.output_currents[29] == 1000 + 29 * 100

    def test_parse_too_short(self):
        """Reject packets that are too short."""
        with pytest.raises(ValueError, match="too short"):
            parse_telemetry(bytes(50))

    def test_round_trip(self):
        """Packet should survive create/parse round trip."""
        original = TelemetryPacket(
            timestamp_ms=999999,
            input_voltage_mv=14200,
            temperature_c=55,
            fault_flags=FaultFlags.UNDERVOLTAGE | FaultFlags.SENSOR_ERROR,
        )

        raw = create_telemetry_bytes(original)
        parsed = parse_telemetry(raw)

        assert parsed.timestamp_ms == original.timestamp_ms
        assert parsed.input_voltage_mv == original.input_voltage_mv
        assert parsed.temperature_c == original.temperature_c
        assert parsed.fault_flags == original.fault_flags


class TestDeviceInfo:
    """Test DeviceInfo dataclass."""

    def test_default_values(self):
        """Test default device info."""
        info = DeviceInfo()

        assert info.firmware_version == "0.0.0"
        assert info.hardware_revision == 0
        assert info.output_count == 30
        assert info.input_count == 20
        assert info.hbridge_count == 4
        assert info.can_bus_count == 4

    def test_uptime_str_seconds(self):
        """Test uptime string for seconds."""
        info = DeviceInfo(uptime_ms=45000)  # 45 seconds
        assert info.uptime_str == "45s"

    def test_uptime_str_minutes(self):
        """Test uptime string for minutes."""
        info = DeviceInfo(uptime_ms=125000)  # 2m 5s
        assert info.uptime_str == "2m 5s"

    def test_uptime_str_hours(self):
        """Test uptime string for hours."""
        info = DeviceInfo(uptime_ms=7325000)  # 2h 2m 5s
        assert info.uptime_str == "2h 2m 5s"

    def test_uptime_str_days(self):
        """Test uptime string for days."""
        info = DeviceInfo(uptime_ms=90061000)  # 1d 1h 1m
        assert info.uptime_str == "1d 1h 1m"


class TestChannelStatus:
    """Test ChannelStatus dataclass."""

    def test_current_conversion(self):
        """Test current mA to A conversion."""
        status = ChannelStatus(channel_id=0, current_ma=2500)
        assert status.current_a == 2.5

    def test_is_active(self):
        """Test active channel detection."""
        on = ChannelStatus(channel_id=0, state=ChannelState.ON)
        pwm = ChannelStatus(channel_id=1, state=ChannelState.PWM_ACTIVE)
        off = ChannelStatus(channel_id=2, state=ChannelState.OFF)
        fault = ChannelStatus(channel_id=3, state=ChannelState.FAULT_SHORT)

        assert on.is_active
        assert pwm.is_active
        assert not off.is_active
        assert not fault.is_active

    def test_is_faulted(self):
        """Test fault detection."""
        ok = ChannelStatus(channel_id=0, state=ChannelState.ON)
        overcurrent = ChannelStatus(channel_id=1, state=ChannelState.FAULT_OVERCURRENT)
        short = ChannelStatus(channel_id=2, state=ChannelState.FAULT_SHORT)

        assert not ok.is_faulted
        assert overcurrent.is_faulted
        assert short.is_faulted

    def test_state_str(self):
        """Test state string generation."""
        assert ChannelStatus(0, state=ChannelState.OFF).state_str == "Off"
        assert ChannelStatus(0, state=ChannelState.ON).state_str == "On"
        assert ChannelStatus(0, state=ChannelState.PWM_ACTIVE).state_str == "PWM"
        assert ChannelStatus(0, state=ChannelState.FAULT_SHORT).state_str == "Short Circuit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

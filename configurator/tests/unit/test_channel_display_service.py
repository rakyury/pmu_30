"""Tests for ChannelDisplayService and ChannelIdGenerator."""

import pytest
from models.channel_display_service import ChannelDisplayService, ChannelIdGenerator


class TestGetSystemChannelName:
    """Tests for get_system_channel_name() method."""

    def test_predefined_system_channels(self):
        """Test lookup of predefined system channels."""
        assert ChannelDisplayService.get_system_channel_name(1000) == "pmu.batteryVoltage"
        assert ChannelDisplayService.get_system_channel_name(1001) == "pmu.totalCurrent"
        assert ChannelDisplayService.get_system_channel_name(1006) == "pmu.uptime"
        assert ChannelDisplayService.get_system_channel_name(1007) == "pmu.status"
        assert ChannelDisplayService.get_system_channel_name(1012) == "zero"
        assert ChannelDisplayService.get_system_channel_name(1013) == "one"

    def test_rtc_channels(self):
        """Test lookup of RTC system channels."""
        assert ChannelDisplayService.get_system_channel_name(1020) == "pmu.rtc.time"
        assert ChannelDisplayService.get_system_channel_name(1022) == "pmu.rtc.hour"
        assert ChannelDisplayService.get_system_channel_name(1027) == "pmu.rtc.year"

    def test_analog_input_channels(self):
        """Test lookup of hardware analog input channels (1220-1239)."""
        assert ChannelDisplayService.get_system_channel_name(1220) == "pmu.a1.voltage"
        assert ChannelDisplayService.get_system_channel_name(1221) == "pmu.a2.voltage"
        assert ChannelDisplayService.get_system_channel_name(1239) == "pmu.a20.voltage"

    def test_digital_input_channels(self):
        """Test lookup of hardware digital input channels (0-19)."""
        assert ChannelDisplayService.get_system_channel_name(0) == "pmu.d1.state"
        assert ChannelDisplayService.get_system_channel_name(1) == "pmu.d2.state"
        assert ChannelDisplayService.get_system_channel_name(19) == "pmu.d20.state"

    def test_output_status_channels(self):
        """Test lookup of output status sub-channels (1100-1129)."""
        assert ChannelDisplayService.get_system_channel_name(1100) == "pmu.o1.status"
        assert ChannelDisplayService.get_system_channel_name(1101) == "pmu.o2.status"
        assert ChannelDisplayService.get_system_channel_name(1129) == "pmu.o30.status"

    def test_output_current_channels(self):
        """Test lookup of output current sub-channels (1130-1159)."""
        assert ChannelDisplayService.get_system_channel_name(1130) == "pmu.o1.current"
        assert ChannelDisplayService.get_system_channel_name(1131) == "pmu.o2.current"
        assert ChannelDisplayService.get_system_channel_name(1159) == "pmu.o30.current"

    def test_output_voltage_channels(self):
        """Test lookup of output voltage sub-channels (1160-1189)."""
        assert ChannelDisplayService.get_system_channel_name(1160) == "pmu.o1.voltage"
        assert ChannelDisplayService.get_system_channel_name(1189) == "pmu.o30.voltage"

    def test_output_active_channels(self):
        """Test lookup of output active sub-channels (1190-1219)."""
        assert ChannelDisplayService.get_system_channel_name(1190) == "pmu.o1.active"
        assert ChannelDisplayService.get_system_channel_name(1219) == "pmu.o30.active"

    def test_output_duty_cycle_channels(self):
        """Test lookup of output duty cycle sub-channels (1250-1279)."""
        assert ChannelDisplayService.get_system_channel_name(1250) == "pmu.o1.dutyCycle"
        assert ChannelDisplayService.get_system_channel_name(1279) == "pmu.o30.dutyCycle"

    def test_unknown_channel_returns_none(self):
        """Test that unknown IDs return None."""
        # User channel range (should return None - not a system channel)
        assert ChannelDisplayService.get_system_channel_name(100) is None
        assert ChannelDisplayService.get_system_channel_name(500) is None

        # Gaps in system channel ranges
        assert ChannelDisplayService.get_system_channel_name(1050) is None
        assert ChannelDisplayService.get_system_channel_name(1300) is None

    def test_none_input_returns_none(self):
        """Test that None input returns None."""
        assert ChannelDisplayService.get_system_channel_name(None) is None


class TestGetDisplayName:
    """Tests for get_display_name() method."""

    @pytest.fixture
    def available_channels(self):
        """Sample available channels for testing."""
        return {
            "Inputs": [
                (10, "FuelLevel", "L", 1),
                (21, "StartButton", "", 0),
            ],
            "Functions": [
                (50, "CalculatedValue", "V", 2),
            ],
        }

    def test_user_channel_lookup(self, available_channels):
        """Test lookup of user channels."""
        assert ChannelDisplayService.get_display_name(10, available_channels) == "FuelLevel"
        assert ChannelDisplayService.get_display_name(21, available_channels) == "StartButton"
        assert ChannelDisplayService.get_display_name(50, available_channels) == "CalculatedValue"

    def test_system_channel_lookup(self, available_channels):
        """Test lookup of system channels."""
        assert ChannelDisplayService.get_display_name(1007, available_channels) == "pmu.status"
        assert ChannelDisplayService.get_display_name(1130, available_channels) == "pmu.o1.current"

    def test_system_channel_without_available_channels(self):
        """Test system channel lookup without available_channels."""
        assert ChannelDisplayService.get_display_name(1007) == "pmu.status"
        assert ChannelDisplayService.get_display_name(1000) == "pmu.batteryVoltage"

    def test_string_channel_id(self, available_channels):
        """Test lookup with string channel ID."""
        assert ChannelDisplayService.get_display_name("1007", available_channels) == "pmu.status"
        assert ChannelDisplayService.get_display_name("10", available_channels) == "FuelLevel"

    def test_hash_prefixed_channel_id(self, available_channels):
        """Test lookup with #-prefixed channel ID."""
        assert ChannelDisplayService.get_display_name("#1007", available_channels) == "pmu.status"
        assert ChannelDisplayService.get_display_name("#10", available_channels) == "FuelLevel"

    def test_unknown_channel_fallback(self, available_channels):
        """Test fallback for unknown channels."""
        assert ChannelDisplayService.get_display_name(999, available_channels) == "#999"
        assert ChannelDisplayService.get_display_name(9999, available_channels) == "#9999"

    def test_empty_input(self, available_channels):
        """Test empty input returns empty string."""
        assert ChannelDisplayService.get_display_name(None, available_channels) == ""
        assert ChannelDisplayService.get_display_name("", available_channels) == ""


class TestHelperMethods:
    """Tests for helper methods."""

    def test_is_system_channel(self):
        """Test is_system_channel() method."""
        assert ChannelDisplayService.is_system_channel(1000) is True
        assert ChannelDisplayService.is_system_channel(1007) is True
        assert ChannelDisplayService.is_system_channel(1130) is True
        assert ChannelDisplayService.is_system_channel(0) is True  # Digital input
        assert ChannelDisplayService.is_system_channel(100) is False  # User range
        assert ChannelDisplayService.is_system_channel(500) is False  # User range
        assert ChannelDisplayService.is_system_channel(None) is False

    def test_is_user_channel(self):
        """Test is_user_channel() method."""
        assert ChannelDisplayService.is_user_channel(200) is True
        assert ChannelDisplayService.is_user_channel(500) is True
        assert ChannelDisplayService.is_user_channel(999) is True
        assert ChannelDisplayService.is_user_channel(100) is False  # Physical output
        assert ChannelDisplayService.is_user_channel(1000) is False  # System
        assert ChannelDisplayService.is_user_channel(None) is False

    def test_get_all_system_channels(self):
        """Test get_all_system_channels() returns list."""
        channels = ChannelDisplayService.get_all_system_channels()
        assert isinstance(channels, list)
        assert len(channels) > 0
        # Check format: (channel_id, string_name, description)
        for ch in channels:
            assert isinstance(ch, tuple)
            assert len(ch) == 3
            assert isinstance(ch[0], int)
            assert isinstance(ch[1], str)
            assert isinstance(ch[2], str)

    def test_get_system_channel_description(self):
        """Test get_system_channel_description() method."""
        desc = ChannelDisplayService.get_system_channel_description(1000)
        assert desc == "Battery Voltage (mV)"

        desc = ChannelDisplayService.get_system_channel_description(1007)
        assert desc == "System Status"

        # Unknown channel
        assert ChannelDisplayService.get_system_channel_description(9999) is None


class TestNormalizeChannelId:
    """Tests for _normalize_channel_id() helper."""

    def test_int_input(self):
        """Test with integer input."""
        assert ChannelDisplayService._normalize_channel_id(1007) == 1007
        assert ChannelDisplayService._normalize_channel_id(0) == 0

    def test_string_input(self):
        """Test with string input."""
        assert ChannelDisplayService._normalize_channel_id("1007") == 1007
        assert ChannelDisplayService._normalize_channel_id("0") == 0

    def test_hash_prefix(self):
        """Test with #-prefixed string."""
        assert ChannelDisplayService._normalize_channel_id("#1007") == 1007
        assert ChannelDisplayService._normalize_channel_id("# 1007") == 1007

    def test_invalid_input(self):
        """Test with invalid input."""
        assert ChannelDisplayService._normalize_channel_id("abc") is None
        assert ChannelDisplayService._normalize_channel_id(None) is None
        assert ChannelDisplayService._normalize_channel_id([]) is None


class TestChannelIdGenerator:
    """Tests for ChannelIdGenerator - centralized ID generation."""

    def test_get_next_channel_id_empty(self):
        """Test ID generation with no existing channels."""
        next_id = ChannelIdGenerator.get_next_channel_id([])
        assert next_id == 200  # Minimum user channel ID

    def test_get_next_channel_id_none(self):
        """Test ID generation with None input."""
        next_id = ChannelIdGenerator.get_next_channel_id(None)
        assert next_id == 200

    def test_get_next_channel_id_with_existing(self):
        """Test ID generation skips existing IDs."""
        existing = [
            {"channel_id": 200},
            {"channel_id": 201},
            {"channel_id": 202},
        ]
        next_id = ChannelIdGenerator.get_next_channel_id(existing)
        assert next_id == 203

    def test_get_next_channel_id_fills_gaps(self):
        """Test ID generation fills gaps in sequence."""
        existing = [
            {"channel_id": 200},
            {"channel_id": 202},  # Gap at 201
            {"channel_id": 203},
        ]
        next_id = ChannelIdGenerator.get_next_channel_id(existing)
        assert next_id == 201  # Should fill the gap

    def test_get_next_channel_id_ignores_none(self):
        """Test ID generation ignores None channel_id."""
        existing = [
            {"channel_id": None},
            {"channel_id": 200},
        ]
        next_id = ChannelIdGenerator.get_next_channel_id(existing)
        assert next_id == 201

    def test_get_next_channel_id_ignores_system_channels(self):
        """Test that existing system channels don't affect user ID generation."""
        existing = [
            {"channel_id": 1000},  # System channel
            {"channel_id": 1007},  # System channel
        ]
        next_id = ChannelIdGenerator.get_next_channel_id(existing)
        assert next_id == 200  # Still starts at 200

    def test_is_valid_user_channel_id(self):
        """Test user channel ID validation."""
        assert ChannelIdGenerator.is_valid_user_channel_id(200) is True
        assert ChannelIdGenerator.is_valid_user_channel_id(500) is True
        assert ChannelIdGenerator.is_valid_user_channel_id(999) is True
        assert ChannelIdGenerator.is_valid_user_channel_id(199) is False
        assert ChannelIdGenerator.is_valid_user_channel_id(1000) is False
        assert ChannelIdGenerator.is_valid_user_channel_id(None) is False

    def test_channel_id_ranges_constants(self):
        """Test that ID range constants are correct."""
        assert ChannelIdGenerator.USER_CHANNEL_MIN == 200
        assert ChannelIdGenerator.USER_CHANNEL_MAX == 999
        assert ChannelIdGenerator.SYSTEM_CHANNEL_MIN == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

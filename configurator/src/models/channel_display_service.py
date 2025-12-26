"""Channel Display Service - centralized channel name resolution.

This module provides a single source of truth for:
1. System channel definitions (SYSTEM_CHANNELS)
2. Channel ID to display name resolution
3. System channel name lookup by numeric ID
4. Channel ID generation (ChannelIdGenerator)

All UI components should use this service instead of duplicating lookup logic.
"""

from typing import Dict, List, Optional, Tuple, Any


class ChannelIdGenerator:
    """Centralized channel ID generation.

    Replaces the global _next_user_channel_id counter in base_channel_dialog.
    Stateless and testable - no global mutable state.

    Usage:
        from models.channel_display_service import ChannelIdGenerator

        existing = [{"channel_id": 200}, {"channel_id": 201}]
        next_id = ChannelIdGenerator.get_next_channel_id(existing)
        # Returns: 202
    """

    # Channel ID ranges (from pmu_channel.h)
    USER_CHANNEL_MIN = 200
    USER_CHANNEL_MAX = 999
    SYSTEM_CHANNEL_MIN = 1000

    @classmethod
    def get_next_channel_id(cls, existing_channels: List[Dict[str, Any]] = None) -> int:
        """Get next available channel ID based on existing channels.

        Args:
            existing_channels: List of existing channel configs

        Returns:
            Next available channel ID in user range (200-999)
        """
        used_ids = set()
        if existing_channels:
            for ch in existing_channels:
                ch_id = ch.get("channel_id")
                if ch_id is not None:
                    used_ids.add(ch_id)

        # Find next free ID in user range (200-999)
        for candidate in range(cls.USER_CHANNEL_MIN, cls.USER_CHANNEL_MAX + 1):
            if candidate not in used_ids:
                return candidate

        # Fallback - return max + 1 (shouldn't happen in practice)
        return max(used_ids) + 1 if used_ids else cls.USER_CHANNEL_MIN

    @classmethod
    def is_valid_user_channel_id(cls, channel_id: int) -> bool:
        """Check if channel_id is in valid user range (200-999)."""
        if channel_id is None:
            return False
        return cls.USER_CHANNEL_MIN <= channel_id <= cls.USER_CHANNEL_MAX


class ChannelDisplayService:
    """Centralized service for channel display name resolution.

    This class consolidates channel lookup logic that was previously duplicated
    across multiple UI components (ChannelSelectorDialog, ChannelsMixin,
    BaseChannelDialog, etc.).

    Usage:
        from models.channel_display_service import ChannelDisplayService

        # Get display name for any channel
        name = ChannelDisplayService.get_display_name(1007, available_channels)
        # Returns: "pmu.status"

        # Get system channel name only
        name = ChannelDisplayService.get_system_channel_name(1130)
        # Returns: "pmu.o1.current"
    """

    # =========================================================================
    # SYSTEM CHANNEL DEFINITIONS
    # =========================================================================
    # Source: firmware/include/pmu_channel.h
    # Format: (channel_id: int, string_name: str, description: str)

    SYSTEM_CHANNELS: List[Tuple[int, str, str]] = [
        # Constant values (always return 0 or 1)
        (1012, "zero", "Zero (constant 0)"),
        (1013, "one", "One (constant 1)"),

        # PMU System channels (1000-1011)
        (1000, "pmu.batteryVoltage", "Battery Voltage (mV)"),
        (1001, "pmu.totalCurrent", "Total Current (mA)"),
        (1002, "pmu.mcuTemperature", "MCU Temperature (°C)"),
        (1003, "pmu.boardTemperatureL", "Board Temperature L (°C)"),
        (1004, "pmu.boardTemperatureR", "Board Temperature R (°C)"),
        (1005, "pmu.boardTemperatureMax", "Board Temperature Max (°C)"),
        (1006, "pmu.uptime", "Uptime (s)"),
        (1007, "pmu.status", "System Status"),
        (1008, "pmu.userError", "User Error"),
        (1009, "pmu.5VOutput", "5V Output (mV)"),
        (1010, "pmu.3V3Output", "3.3V Output (mV)"),
        (1011, "pmu.isTurningOff", "Is Turning Off"),

        # RTC channels (1020-1027)
        (1020, "pmu.rtc.time", "RTC Time"),
        (1021, "pmu.rtc.date", "RTC Date"),
        (1022, "pmu.rtc.hour", "RTC Hour"),
        (1023, "pmu.rtc.minute", "RTC Minute"),
        (1024, "pmu.rtc.second", "RTC Second"),
        (1025, "pmu.rtc.day", "RTC Day"),
        (1026, "pmu.rtc.month", "RTC Month"),
        (1027, "pmu.rtc.year", "RTC Year"),

        # Serial number channels (1030-1031)
        (1030, "pmu.serialNumber.high", "Serial Number (high)"),
        (1031, "pmu.serialNumber.low", "Serial Number (low)"),
    ]

    # Build lookup dict for O(1) access
    _SYSTEM_CHANNELS_DICT: Dict[int, str] = {
        ch_id: str_name for ch_id, str_name, _ in SYSTEM_CHANNELS
    }

    # =========================================================================
    # CHANNEL ID RANGES (from pmu_channel.h)
    # =========================================================================
    # 0-19:       Digital inputs (pmu.d1.state ... pmu.d20.state)
    # 0-99:       Physical inputs
    # 100-199:    Physical outputs
    # 200-999:    Virtual/user channels
    # 1000-1023:  System channels
    # 1100-1129:  Output status
    # 1130-1159:  Output current
    # 1160-1189:  Output voltage
    # 1190-1219:  Output active
    # 1220-1239:  Analog voltage
    # 1250-1279:  Output duty cycle

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    @classmethod
    def get_system_channel_name(cls, channel_id: int) -> Optional[str]:
        """Get string_name for a system channel by its numeric ID.

        This is the central lookup for resolving numeric system channel IDs
        to their human-readable string names (e.g., 1007 -> "pmu.status").

        Args:
            channel_id: Numeric channel ID

        Returns:
            String name (e.g., "pmu.status") or None if not a system channel
        """
        if channel_id is None:
            return None

        # 1. Check predefined system channels (O(1) lookup)
        if channel_id in cls._SYSTEM_CHANNELS_DICT:
            return cls._SYSTEM_CHANNELS_DICT[channel_id]

        # 2. Hardware analog input channels (1220-1239)
        if 1220 <= channel_id <= 1239:
            idx = channel_id - 1220 + 1
            return f"pmu.a{idx}.voltage"

        # 3. Hardware digital input channels (0-19)
        if 0 <= channel_id <= 19:
            return f"pmu.d{channel_id + 1}.state"

        # 4. Output status sub-channels (1100-1129)
        if 1100 <= channel_id <= 1129:
            idx = channel_id - 1100 + 1
            return f"pmu.o{idx}.status"

        # 5. Output current sub-channels (1130-1159)
        if 1130 <= channel_id <= 1159:
            idx = channel_id - 1130 + 1
            return f"pmu.o{idx}.current"

        # 6. Output voltage sub-channels (1160-1189)
        if 1160 <= channel_id <= 1189:
            idx = channel_id - 1160 + 1
            return f"pmu.o{idx}.voltage"

        # 7. Output active sub-channels (1190-1219)
        if 1190 <= channel_id <= 1219:
            idx = channel_id - 1190 + 1
            return f"pmu.o{idx}.active"

        # 8. Output duty cycle sub-channels (1250-1279)
        if 1250 <= channel_id <= 1279:
            idx = channel_id - 1250 + 1
            return f"pmu.o{idx}.dutyCycle"

        return None

    @classmethod
    def get_display_name(cls, channel_id: Any,
                         available_channels: Optional[Dict[str, List]] = None) -> str:
        """Get display name for any channel (user or system).

        This is the universal lookup for resolving channel_id to display name.
        Use this in any dialog that needs to display a channel name.

        Args:
            channel_id: Channel ID (numeric int or string)
            available_channels: Dict of available channels for user channel lookup

        Returns:
            Display name string (e.g., "FuelLevel", "pmu.status") or "#{id}" fallback
        """
        if channel_id is None or channel_id == "":
            return ""

        # Normalize to int if possible
        numeric_id = cls._normalize_channel_id(channel_id)

        # 1. Search user channels in available_channels
        if available_channels:
            for category, channels in available_channels.items():
                for ch in channels:
                    if isinstance(ch, tuple) and len(ch) >= 2:
                        ch_id = ch[0]
                        ch_name = ch[1]
                        if ch_id == channel_id or (numeric_id is not None and ch_id == numeric_id):
                            return str(ch_name)

        # 2. Check system channels
        if numeric_id is not None:
            system_name = cls.get_system_channel_name(numeric_id)
            if system_name:
                return system_name

        # 3. Fallback
        if numeric_id is not None:
            return f"#{numeric_id}"
        return str(channel_id) if channel_id else ""

    @classmethod
    def get_all_system_channels(cls) -> List[Tuple[int, str, str]]:
        """Get all predefined system channels.

        Returns:
            List of (channel_id, string_name, description) tuples
        """
        return cls.SYSTEM_CHANNELS.copy()

    @classmethod
    def get_system_channel_description(cls, channel_id: int) -> Optional[str]:
        """Get human-readable description for a system channel.

        Args:
            channel_id: Numeric channel ID

        Returns:
            Description string or None if not found
        """
        for ch_id, _, description in cls.SYSTEM_CHANNELS:
            if ch_id == channel_id:
                return description
        return None

    @classmethod
    def is_system_channel(cls, channel_id: int) -> bool:
        """Check if channel_id belongs to a system channel.

        Args:
            channel_id: Numeric channel ID

        Returns:
            True if this is a system channel, False otherwise
        """
        if channel_id is None:
            return False
        return cls.get_system_channel_name(channel_id) is not None

    @classmethod
    def is_user_channel(cls, channel_id: int) -> bool:
        """Check if channel_id is in the user channel range (200-999).

        Args:
            channel_id: Numeric channel ID

        Returns:
            True if this is a user/virtual channel, False otherwise
        """
        if channel_id is None:
            return False
        return 200 <= channel_id <= 999

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    @staticmethod
    def _normalize_channel_id(channel_id: Any) -> Optional[int]:
        """Normalize channel_id to int if possible.

        Handles string formats like "1007", "#1007", etc.

        Args:
            channel_id: Input channel ID (int, str, or other)

        Returns:
            Integer channel_id or None if conversion not possible
        """
        if isinstance(channel_id, int):
            return channel_id
        if isinstance(channel_id, str):
            clean_id = channel_id.lstrip('#').strip()
            if clean_id.isdigit():
                return int(clean_id)
        return None

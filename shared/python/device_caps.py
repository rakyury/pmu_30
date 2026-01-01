"""
PMU-30 Device Capabilities - Python implementation

Mirrors device_caps.h for Python compatibility.
"""

import struct
from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import Optional


class HwCapsFlags(IntFlag):
    """Hardware capability flags"""
    NONE = 0

    HAS_PROFET = 1 << 0
    HAS_HBRIDGE = 1 << 1
    HAS_ADC = 1 << 2
    HAS_DAC = 1 << 3
    HAS_DIN = 1 << 4
    HAS_DOUT = 1 << 5
    HAS_FREQ = 1 << 6
    HAS_PWM = 1 << 7

    HAS_CAN1 = 1 << 8
    HAS_CAN2 = 1 << 9
    HAS_CAN3 = 1 << 10
    HAS_CAN4 = 1 << 11
    HAS_LIN = 1 << 12

    HAS_WIFI = 1 << 16
    HAS_BLUETOOTH = 1 << 17
    HAS_GPS = 1 << 18
    HAS_GSM = 1 << 19

    HAS_SDCARD = 1 << 20
    HAS_USB = 1 << 21
    HAS_ETHERNET = 1 << 22

    HAS_RTC = 1 << 24
    HAS_EEPROM = 1 << 25
    HAS_FLASH_EXT = 1 << 26


class SwCapsFlags(IntFlag):
    """Software capability flags"""
    NONE = 0

    PID = 1 << 0
    TABLES_2D = 1 << 1
    TABLES_3D = 1 << 2
    LOGIC = 1 << 3
    TIMERS = 1 << 4
    FILTERS = 1 << 5
    MATH = 1 << 6
    LUA = 1 << 7
    DATALOG = 1 << 8
    BLINKMARINE = 1 << 9
    WIPER_PARK = 1 << 10
    CAN_STREAM = 1 << 11


class DeviceType(IntEnum):
    """Device type enumeration"""
    UNKNOWN = 0
    PMU30 = 1
    NUCLEO_F446 = 2
    NUCLEO_H7 = 3
    PMU30_LITE = 4
    EMULATOR = 0xFF


# Constants
CAPS_MAGIC = 0x4350  # "CP"
CAPS_VERSION = 1
CAPS_SIZE = 64


@dataclass
class DeviceCaps:
    """Device capabilities structure"""

    # Magic and version
    magic: int = CAPS_MAGIC
    version: int = CAPS_VERSION

    # Device identification
    device_type: DeviceType = DeviceType.UNKNOWN
    hw_revision: int = 0
    fw_version: tuple[int, int, int] = (0, 0, 0)
    serial_number: int = 0

    # Capability flags
    hw_flags: HwCapsFlags = HwCapsFlags.NONE
    sw_flags: SwCapsFlags = SwCapsFlags.NONE

    # Channel counts
    profet_count: int = 0
    hbridge_count: int = 0
    adc_count: int = 0
    din_count: int = 0
    freq_count: int = 0
    pwm_count: int = 0
    can_count: int = 0
    lin_count: int = 0
    dac_count: int = 0
    dout_count: int = 0

    # Channel limits
    max_channels: int = 0
    max_logic: int = 0
    max_timers: int = 0
    max_tables: int = 0

    # Memory info
    flash_size_kb: int = 0
    ram_size_kb: int = 0

    # Current limits
    max_current_ma: int = 0
    per_channel_ma: int = 0
    hbridge_current_ma: int = 0

    # Feature checks
    def has_hw(self, flag: HwCapsFlags) -> bool:
        """Check if hardware capability is present"""
        return bool(self.hw_flags & flag)

    def has_sw(self, flag: SwCapsFlags) -> bool:
        """Check if software capability is present"""
        return bool(self.sw_flags & flag)

    @property
    def has_profet(self) -> bool:
        return self.has_hw(HwCapsFlags.HAS_PROFET)

    @property
    def has_hbridge(self) -> bool:
        return self.has_hw(HwCapsFlags.HAS_HBRIDGE)

    @property
    def has_can(self) -> bool:
        return self.has_hw(HwCapsFlags.HAS_CAN1)

    @property
    def has_wifi(self) -> bool:
        return self.has_hw(HwCapsFlags.HAS_WIFI)

    @property
    def has_bluetooth(self) -> bool:
        return self.has_hw(HwCapsFlags.HAS_BLUETOOTH)

    @property
    def has_gps(self) -> bool:
        return self.has_hw(HwCapsFlags.HAS_GPS)

    @property
    def has_pid(self) -> bool:
        return self.has_sw(SwCapsFlags.PID)

    @property
    def has_lua(self) -> bool:
        return self.has_sw(SwCapsFlags.LUA)

    @property
    def has_datalog(self) -> bool:
        return self.has_sw(SwCapsFlags.DATALOG)

    @property
    def fw_version_str(self) -> str:
        """Firmware version as string"""
        return f"{self.fw_version[0]}.{self.fw_version[1]}.{self.fw_version[2]}"

    @property
    def device_name(self) -> str:
        """Human-readable device name"""
        names = {
            DeviceType.PMU30: "PMU-30",
            DeviceType.NUCLEO_F446: "Nucleo-F446RE",
            DeviceType.NUCLEO_H7: "Nucleo-H723ZG",
            DeviceType.PMU30_LITE: "PMU-30 Lite",
            DeviceType.EMULATOR: "PMU-30 Emulator",
        }
        return names.get(self.device_type, "Unknown Device")

    def get_supported_features(self) -> list[str]:
        """Get list of supported feature names"""
        features = []

        # Hardware features
        if self.has_profet:
            features.append(f"Power Outputs ({self.profet_count})")
        if self.has_hbridge:
            features.append(f"H-Bridge ({self.hbridge_count})")
        if self.has_hw(HwCapsFlags.HAS_ADC):
            features.append(f"Analog Inputs ({self.adc_count})")
        if self.has_hw(HwCapsFlags.HAS_DIN):
            features.append(f"Digital Inputs ({self.din_count})")
        if self.has_hw(HwCapsFlags.HAS_FREQ):
            features.append(f"Frequency Inputs ({self.freq_count})")
        if self.has_can:
            features.append(f"CAN Bus ({self.can_count})")
        if self.has_hw(HwCapsFlags.HAS_LIN):
            features.append(f"LIN Bus ({self.lin_count})")
        if self.has_wifi:
            features.append("WiFi")
        if self.has_bluetooth:
            features.append("Bluetooth")
        if self.has_gps:
            features.append("GPS")

        # Software features
        if self.has_pid:
            features.append("PID Controllers")
        if self.has_sw(SwCapsFlags.TABLES_2D):
            features.append("2D Tables")
        if self.has_sw(SwCapsFlags.TABLES_3D):
            features.append("3D Tables")
        if self.has_sw(SwCapsFlags.LOGIC):
            features.append("Logic Channels")
        if self.has_sw(SwCapsFlags.TIMERS):
            features.append("Timer Channels")
        if self.has_lua:
            features.append("Lua Scripting")
        if self.has_datalog:
            features.append("Data Logging")

        return features


# Struct format for parsing: 64 bytes
# magic(2) + version(1) + reserved(1) = 4
# device_type(1) + hw_rev(1) + fw_major(2) + fw_minor(2) + fw_patch(2) + serial(4) + reserved(4) = 16
# hw_flags(4) + sw_flags(4) = 8
# counts: profet(1)+hbridge(1)+adc(1)+din(1)+freq(1)+pwm(1)+can(1)+lin(1)+dac(1)+dout(1)+reserved(2) = 12
# limits: max_ch(2)+max_logic(2)+max_timers(2)+max_tables(2) = 8
# memory: flash(4)+ram(4) = 8
# current: max(2)+per_ch(2)+hbridge(2)+reserved(2) = 8
CAPS_FORMAT = "<HBx BBHHHII II BBBBBBBBBBH HHHH II HHHH"


def parse_caps(data: bytes) -> Optional[DeviceCaps]:
    """
    Parse device capabilities from raw bytes.

    Args:
        data: Raw capability data (64 bytes)

    Returns:
        Parsed DeviceCaps or None if invalid
    """
    if len(data) < CAPS_SIZE:
        return None

    try:
        values = struct.unpack(CAPS_FORMAT, data[:CAPS_SIZE])
    except struct.error:
        return None

    magic = values[0]
    if magic != CAPS_MAGIC:
        return None

    return DeviceCaps(
        magic=magic,
        version=values[1],
        device_type=DeviceType(values[2]),
        hw_revision=values[3],
        fw_version=(values[4], values[5], values[6]),
        serial_number=values[7],
        # values[8] is reserved
        hw_flags=HwCapsFlags(values[9]),
        sw_flags=SwCapsFlags(values[10]),
        profet_count=values[11],
        hbridge_count=values[12],
        adc_count=values[13],
        din_count=values[14],
        freq_count=values[15],
        pwm_count=values[16],
        can_count=values[17],
        lin_count=values[18],
        dac_count=values[19],
        dout_count=values[20],
        # values[21] is reserved
        max_channels=values[22],
        max_logic=values[23],
        max_timers=values[24],
        max_tables=values[25],
        flash_size_kb=values[26],
        ram_size_kb=values[27],
        max_current_ma=values[28],
        per_channel_ma=values[29],
        hbridge_current_ma=values[30],
        # values[31] is reserved
    )


def build_caps(caps: DeviceCaps) -> bytes:
    """
    Build raw bytes from device capabilities.

    Args:
        caps: DeviceCaps to serialize

    Returns:
        Raw bytes (64 bytes)
    """
    return struct.pack(
        CAPS_FORMAT,
        caps.magic,
        caps.version,
        caps.device_type,
        caps.hw_revision,
        caps.fw_version[0],
        caps.fw_version[1],
        caps.fw_version[2],
        caps.serial_number,
        0,  # reserved
        caps.hw_flags,
        caps.sw_flags,
        caps.profet_count,
        caps.hbridge_count,
        caps.adc_count,
        caps.din_count,
        caps.freq_count,
        caps.pwm_count,
        caps.can_count,
        caps.lin_count,
        caps.dac_count,
        caps.dout_count,
        0,  # reserved
        caps.max_channels,
        caps.max_logic,
        caps.max_timers,
        caps.max_tables,
        caps.flash_size_kb,
        caps.ram_size_kb,
        caps.max_current_ma,
        caps.per_channel_ma,
        caps.hbridge_current_ma,
        0,  # reserved
    )


# Predefined capabilities for known devices
def get_pmu30_caps() -> DeviceCaps:
    """Get default capabilities for PMU-30"""
    return DeviceCaps(
        device_type=DeviceType.PMU30,
        hw_revision=1,
        hw_flags=(
            HwCapsFlags.HAS_PROFET | HwCapsFlags.HAS_HBRIDGE |
            HwCapsFlags.HAS_ADC | HwCapsFlags.HAS_DIN | HwCapsFlags.HAS_FREQ |
            HwCapsFlags.HAS_PWM |
            HwCapsFlags.HAS_CAN1 | HwCapsFlags.HAS_CAN2 |
            HwCapsFlags.HAS_CAN3 | HwCapsFlags.HAS_CAN4 |
            HwCapsFlags.HAS_LIN |
            HwCapsFlags.HAS_WIFI | HwCapsFlags.HAS_BLUETOOTH |
            HwCapsFlags.HAS_SDCARD | HwCapsFlags.HAS_USB |
            HwCapsFlags.HAS_RTC | HwCapsFlags.HAS_EEPROM
        ),
        sw_flags=(
            SwCapsFlags.PID | SwCapsFlags.TABLES_2D | SwCapsFlags.TABLES_3D |
            SwCapsFlags.LOGIC | SwCapsFlags.TIMERS | SwCapsFlags.FILTERS |
            SwCapsFlags.MATH | SwCapsFlags.LUA | SwCapsFlags.DATALOG |
            SwCapsFlags.BLINKMARINE | SwCapsFlags.WIPER_PARK | SwCapsFlags.CAN_STREAM
        ),
        profet_count=30,
        hbridge_count=4,
        adc_count=20,
        din_count=20,
        freq_count=4,
        pwm_count=8,
        can_count=4,
        lin_count=1,
        dac_count=2,
        dout_count=4,
        max_channels=256,
        max_logic=32,
        max_timers=16,
        max_tables=32,
        flash_size_kb=2048,
        ram_size_kb=512,
        max_current_ma=100000,
        per_channel_ma=20000,
        hbridge_current_ma=30000,
    )


def get_nucleo_f446_caps() -> DeviceCaps:
    """Get default capabilities for Nucleo-F446RE"""
    return DeviceCaps(
        device_type=DeviceType.NUCLEO_F446,
        hw_revision=1,
        hw_flags=(
            HwCapsFlags.HAS_ADC | HwCapsFlags.HAS_DIN | HwCapsFlags.HAS_DOUT |
            HwCapsFlags.HAS_PWM | HwCapsFlags.HAS_CAN1 |
            HwCapsFlags.HAS_USB
        ),
        sw_flags=(
            SwCapsFlags.LOGIC | SwCapsFlags.TIMERS | SwCapsFlags.TABLES_2D
        ),
        profet_count=0,
        hbridge_count=0,
        adc_count=8,
        din_count=8,
        freq_count=2,
        pwm_count=4,
        can_count=1,
        lin_count=0,
        dac_count=2,
        dout_count=8,
        max_channels=64,
        max_logic=8,
        max_timers=4,
        max_tables=8,
        flash_size_kb=512,
        ram_size_kb=128,
        max_current_ma=0,
        per_channel_ma=0,
        hbridge_current_ma=0,
    )


def get_emulator_caps() -> DeviceCaps:
    """Get default capabilities for Emulator"""
    return DeviceCaps(
        device_type=DeviceType.EMULATOR,
        hw_revision=0,
        hw_flags=(
            HwCapsFlags.HAS_PROFET | HwCapsFlags.HAS_HBRIDGE |
            HwCapsFlags.HAS_ADC | HwCapsFlags.HAS_DIN | HwCapsFlags.HAS_FREQ |
            HwCapsFlags.HAS_PWM |
            HwCapsFlags.HAS_CAN1 | HwCapsFlags.HAS_CAN2 |
            HwCapsFlags.HAS_USB
        ),
        sw_flags=(
            SwCapsFlags.PID | SwCapsFlags.TABLES_2D | SwCapsFlags.TABLES_3D |
            SwCapsFlags.LOGIC | SwCapsFlags.TIMERS | SwCapsFlags.FILTERS |
            SwCapsFlags.MATH | SwCapsFlags.DATALOG |
            SwCapsFlags.BLINKMARINE | SwCapsFlags.WIPER_PARK | SwCapsFlags.CAN_STREAM
        ),
        profet_count=30,
        hbridge_count=4,
        adc_count=20,
        din_count=20,
        freq_count=4,
        pwm_count=8,
        can_count=2,
        lin_count=0,
        dac_count=0,
        dout_count=0,
        max_channels=256,
        max_logic=32,
        max_timers=16,
        max_tables=32,
        flash_size_kb=8192,
        ram_size_kb=1024,
        max_current_ma=100000,
        per_channel_ma=20000,
        hbridge_current_ma=30000,
    )

"""
CANX Parser - Parse ECUMaster .canx XML files

The .canx format contains CAN message object definitions with frames and channels.

Supported formats:
- CANbuseXport root with mob elements
- Direct mob element
- Type codes (numeric) or type strings (u16-le, s16-le, etc.)
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import re


# Data type mapping from .canx type codes to our model
CANX_TYPE_MAP = {
    2: ("signed", "8bit"),      # Signed 8-bit
    3: ("unsigned", "8bit"),    # Unsigned 8-bit
    4: ("unsigned", "16bit"),   # Unsigned 16-bit
    5: ("signed", "16bit"),     # Signed 16-bit
    6: ("unsigned", "32bit"),   # Unsigned 32-bit
    7: ("signed", "32bit"),     # Signed 32-bit
    10: ("float", "32bit"),     # Float 32-bit
}

# String type mapping for newer .canx format
CANX_TYPE_STRING_MAP = {
    "u8": ("unsigned", "8bit"),
    "u8-le": ("unsigned", "8bit"),
    "u8-be": ("unsigned", "8bit"),
    "s8": ("signed", "8bit"),
    "s8-le": ("signed", "8bit"),
    "s8-be": ("signed", "8bit"),
    "u16": ("unsigned", "16bit"),
    "u16-le": ("unsigned", "16bit"),
    "u16-be": ("unsigned", "16bit"),
    "s16": ("signed", "16bit"),
    "s16-le": ("signed", "16bit"),
    "s16-be": ("signed", "16bit"),
    "u32": ("unsigned", "32bit"),
    "u32-le": ("unsigned", "32bit"),
    "u32-be": ("unsigned", "32bit"),
    "s32": ("signed", "32bit"),
    "s32-le": ("signed", "32bit"),
    "s32-be": ("signed", "32bit"),
    "f32": ("float", "32bit"),
    "f32-le": ("float", "32bit"),
    "float": ("float", "32bit"),
}


def parse_type_string(type_str: str) -> Tuple[str, str, str]:
    """
    Parse type string like 'u16-le' into (data_type, data_format, byte_order).

    Returns:
        Tuple of (data_type, data_format, byte_order)
    """
    type_lower = type_str.lower().strip()

    # Check string type map first
    if type_lower in CANX_TYPE_STRING_MAP:
        data_type, data_format = CANX_TYPE_STRING_MAP[type_lower]
        byte_order = "big_endian" if "-be" in type_lower else "little_endian"
        return data_type, data_format, byte_order

    # Try numeric type code
    try:
        type_code = int(type_str)
        if type_code in CANX_TYPE_MAP:
            data_type, data_format = CANX_TYPE_MAP[type_code]
            return data_type, data_format, "little_endian"
    except ValueError:
        pass

    # Default to unsigned 16-bit little endian
    return "unsigned", "16bit", "little_endian"


def parse_hex_or_int(value: str, default: int = 0) -> int:
    """Parse a value that could be hex (with or without 0x) or decimal."""
    if not value:
        return default

    value = value.strip()

    # Try hex first (with 0x prefix)
    if value.lower().startswith("0x"):
        try:
            return int(value, 16)
        except ValueError:
            pass

    # Try as plain hex (common in .canx files like "3E8")
    try:
        # Check if it looks like hex (contains A-F)
        if re.match(r'^[0-9A-Fa-f]+$', value) and re.search(r'[A-Fa-f]', value):
            return int(value, 16)
    except ValueError:
        pass

    # Try as decimal
    try:
        return int(value)
    except ValueError:
        return default


@dataclass
class CanxChannel:
    """Represents a single CAN channel/signal from .canx file."""
    id: str
    frame_id: int = 0
    frame_offset: int = 0
    data_type: str = "unsigned"
    data_format: str = "16bit"
    byte_order: str = "little_endian"
    byte_offset: int = 0
    bit_count: int = 16
    bit_position: int = 0
    multiplier: float = 1.0
    divider: float = 1.0
    offset: float = 0.0
    decimal_places: int = 0
    unit: str = ""
    min_value: float = 0.0
    max_value: float = 0.0
    override: str = ""  # ECUMaster channel override name

    def to_can_input_config(self, message_ref: str) -> Dict[str, Any]:
        """Convert to CAN input channel configuration dict."""
        # Sanitize ID for our model - only allow letters, numbers, underscores
        # Replace common separators with underscores, remove other invalid chars
        sanitized = self.id.replace(".", "_").replace("-", "_").replace(" ", "_")
        # Remove any remaining invalid characters
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = "ch_" + sanitized
        # Collapse multiple underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        # Remove trailing underscores
        sanitized = sanitized.strip("_")
        channel_id = "crx_" + sanitized

        # Determine if we need custom bit format
        data_format = self.data_format
        expected_bits = {"8bit": 8, "16bit": 16, "32bit": 32}
        if data_format in expected_bits and self.bit_count != expected_bits[data_format]:
            data_format = "custom"

        return {
            "id": channel_id,
            "channel_type": "can_rx",
            "message_ref": message_ref,
            "frame_offset": self.frame_offset,
            "data_type": self.data_type,
            "data_format": data_format,
            "byte_order": self.byte_order,
            "byte_offset": self.byte_offset,
            "start_bit": self.bit_position,
            "bit_length": self.bit_count,
            "multiplier": self.multiplier,
            "divider": self.divider if self.divider != 0 else 1.0,
            "offset": self.offset,
            "decimal_places": self.decimal_places,
            "default_value": 0.0,
            "timeout_behavior": "use_default",
        }


@dataclass
class CanxFrame:
    """Represents a CAN frame from .canx file."""
    offset: int = 0
    frame_id: str = ""  # Original ID string (e.g., "frame +0")
    can_id: int = 0  # Actual CAN ID if different from mob
    frequency: int = 50
    channels: List[CanxChannel] = field(default_factory=list)


@dataclass
class CanxMob:
    """Represents a Message Object (MOB) from .canx file."""
    id: str = ""  # MOB identifier (e.g., "m_linkecu_A")
    can_id: int = 0  # CAN ID (hex parsed from canbusID)
    can_bus_if: int = 1  # CAN interface (1 or 2)
    width: int = 8  # Frame width in bytes
    msg_type: str = "normal"  # Message type (Normal, Compound8, etc.)
    compound_offset: int = 0
    frames: List[CanxFrame] = field(default_factory=list)

    def to_can_message_config(self, msg_id: str, name: str = "") -> Dict[str, Any]:
        """Convert to CAN message configuration dict."""
        # Use CAN ID from mob
        base_id = self.can_id

        # Calculate timeout from frequency (timeout = 2 * period)
        frequency = self.frames[0].frequency if self.frames else 50
        timeout_ms = int(2000 / frequency) if frequency > 0 else 500

        # Determine message type
        is_compound = "compound" in self.msg_type.lower() or len(self.frames) > 1
        message_type = "compound" if is_compound else "normal"

        return {
            "id": msg_id,
            "name": name or self.id or msg_id,
            "can_bus": self.can_bus_if,
            "base_id": base_id,
            "is_extended": base_id > 0x7FF,
            "message_type": message_type,
            "frame_count": len(self.frames),
            "dlc": self.width,
            "timeout_ms": timeout_ms,
            "enabled": True,
            "description": f"Imported from .canx file"
        }


@dataclass
class CanxData:
    """Container for all parsed .canx data."""
    mobs: List[CanxMob] = field(default_factory=list)
    filename: str = ""

    def get_all_channels(self) -> List[CanxChannel]:
        """Get flat list of all channels from all MOBs."""
        channels = []
        for mob in self.mobs:
            for frame in mob.frames:
                channels.extend(frame.channels)
        return channels

    def get_channels_by_frame(self) -> Dict[int, List[CanxChannel]]:
        """Get channels grouped by frame offset."""
        result = {}
        for mob in self.mobs:
            for frame in mob.frames:
                if frame.offset not in result:
                    result[frame.offset] = []
                result[frame.offset].extend(frame.channels)
        return result


class CanxParser:
    """Parser for ECUMaster .canx XML files."""

    def parse_file(self, filepath: str) -> CanxData:
        """Parse a .canx file from disk."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Try different encodings
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Could not decode file: {filepath}")

        data = self.parse_string(content)
        data.filename = path.stem
        return data

    def parse_string(self, xml_content: str) -> CanxData:
        """Parse .canx XML content from string."""
        data = CanxData()

        try:
            # Try to parse as complete XML document
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            # If it fails, try wrapping in a root element
            try:
                root = ET.fromstring(f"<root>{xml_content}</root>")
            except ET.ParseError as e:
                raise ValueError(f"Invalid XML content: {e}")

        # Find all mob elements (handle both CANbuseXport and direct mob)
        mob_elements = root.findall(".//mob")
        if not mob_elements and root.tag == "mob":
            mob_elements = [root]

        for mob_elem in mob_elements:
            mob = self._parse_mob(mob_elem)
            data.mobs.append(mob)

        return data

    def _parse_mob(self, mob_elem: ET.Element) -> CanxMob:
        """Parse a single MOB element."""
        # Parse CAN ID (could be hex string like "3E8")
        can_id_str = mob_elem.get("canbusID", "0")
        can_id = parse_hex_or_int(can_id_str, 0)

        mob = CanxMob(
            id=mob_elem.get("id", ""),
            can_id=can_id,
            can_bus_if=int(mob_elem.get("canbusIF", 1)),
            width=int(mob_elem.get("width", 8)),
            msg_type=mob_elem.get("type", "normal"),
            compound_offset=int(mob_elem.get("compoundOffset", 0)),
        )

        # Parse frames
        for frame_elem in mob_elem.findall("frame"):
            frame = self._parse_frame(frame_elem, mob)
            mob.frames.append(frame)

        return mob

    def _parse_frame(self, frame_elem: ET.Element, mob: CanxMob) -> CanxFrame:
        """Parse a single frame element."""
        # Frame offset
        offset = int(frame_elem.get("offset", 0))

        # Frame ID string (e.g., "frame +0")
        frame_id_str = frame_elem.get("id", f"frame +{offset}")

        # Calculate actual CAN ID for this frame
        # For compound messages, CAN ID increments with frame offset
        can_id = mob.can_id + offset

        frame = CanxFrame(
            offset=offset,
            frame_id=frame_id_str,
            can_id=can_id,
            frequency=int(frame_elem.get("frequency", 50)),
        )

        # Parse channels
        for channel_elem in frame_elem.findall("channel"):
            channel = self._parse_channel(channel_elem, frame)
            frame.channels.append(channel)

        return frame

    def _parse_channel(self, channel_elem: ET.Element, frame: CanxFrame) -> CanxChannel:
        """Parse a single channel element."""
        # Parse type string (e.g., "u16-le" or numeric "4")
        type_str = channel_elem.get("type", "u16-le")
        data_type, data_format, byte_order = parse_type_string(type_str)

        # Determine bit count from data format if not specified
        bit_count_str = channel_elem.get("bitCount")
        if bit_count_str:
            bit_count = int(bit_count_str)
        else:
            # Default bit count based on data format
            bit_count = {"8bit": 8, "16bit": 16, "32bit": 32}.get(data_format, 16)

        return CanxChannel(
            id=channel_elem.get("id", ""),
            frame_id=frame.can_id,
            frame_offset=frame.offset,
            data_type=data_type,
            data_format=data_format,
            byte_order=byte_order,
            byte_offset=int(channel_elem.get("byteOffset", 0)),
            bit_count=bit_count,
            bit_position=int(channel_elem.get("bitPosition", 0)),
            multiplier=float(channel_elem.get("multiplier", 1.0)),
            divider=float(channel_elem.get("divider", 1.0)),
            offset=float(channel_elem.get("offset", 0.0)),
            decimal_places=int(channel_elem.get("decimalPlaces", 0)),
            unit=channel_elem.get("unit", ""),
            min_value=float(channel_elem.get("min", 0.0)),
            max_value=float(channel_elem.get("max", 0.0)),
            override=channel_elem.get("override", ""),
        )

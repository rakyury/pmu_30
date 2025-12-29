"""
CAN Channels - CAN message and signal channel types

This module contains CAN-related channel classes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from .enums import (
    ChannelType,
    CanMessageType,
    CanTimeoutBehavior,
    CanDataType,
    CanDataFormat,
)
from .base import ChannelBase


@dataclass
class CanMessage:
    """CAN Message Object - defines CAN frame structure (Level 1)

    This is NOT a channel, but a container for CAN frame properties.
    Multiple CanRxChannels (CAN Inputs) can reference the same CanMessage.
    """
    name: str  # Unique identifier (user-editable)
    can_bus: int = 1                           # CAN bus (1-4)
    base_id: int = 0                           # Base CAN ID (11-bit or 29-bit)
    is_extended: bool = False                  # Extended (29-bit) ID
    message_type: CanMessageType = CanMessageType.NORMAL
    frame_count: int = 1                       # 1-8 for compound messages
    dlc: int = 8                               # Data Length Code (0-64)
    timeout_ms: int = 500                      # Reception timeout
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "can_bus": self.can_bus,
            "base_id": self.base_id,
            "is_extended": self.is_extended,
            "message_type": self.message_type.value,
            "frame_count": self.frame_count,
            "dlc": self.dlc,
            "timeout_ms": self.timeout_ms,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanMessage':
        """Create from dictionary - CAN messages use 'name' field"""
        msg_type_str = data.get("message_type", "normal")
        try:
            msg_type = CanMessageType(msg_type_str)
        except ValueError:
            msg_type = CanMessageType.NORMAL

        return cls(
            name=data.get("name", ""),
            can_bus=data.get("can_bus", 1),
            base_id=data.get("base_id", 0),
            is_extended=data.get("is_extended", False),
            message_type=msg_type,
            frame_count=data.get("frame_count", 1),
            dlc=data.get("dlc", 8),
            timeout_ms=data.get("timeout_ms", 500),
            description=data.get("description", "")
        )

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = []
        if not self.name:
            errors.append("Message name is required")
        if self.can_bus < 1 or self.can_bus > 4:
            errors.append("CAN bus must be between 1 and 4")
        if self.is_extended:
            if self.base_id < 0 or self.base_id > 0x1FFFFFFF:
                errors.append("Extended CAN ID must be between 0 and 0x1FFFFFFF")
        else:
            if self.base_id < 0 or self.base_id > 0x7FF:
                errors.append("Standard CAN ID must be between 0 and 0x7FF")
        if self.frame_count < 1 or self.frame_count > 8:
            errors.append("Frame count must be between 1 and 8")
        if self.dlc < 0 or self.dlc > 64:
            errors.append("DLC must be between 0 and 64")
        if self.timeout_ms < 0 or self.timeout_ms > 65535:
            errors.append("Timeout must be between 0 and 65535 ms")
        return errors

    def get_id_string(self) -> str:
        """Get formatted CAN ID string (hex)"""
        if self.is_extended:
            return f"0x{self.base_id:08X}"
        return f"0x{self.base_id:03X}"


@dataclass
class CanRxChannel(ChannelBase):
    """CAN Input (Signal) - extracts data from CAN Message Object (Level 2)

    New architecture: References a CanMessage by message_ref.
    Legacy fields (can_bus, message_id, is_extended) kept for backwards compatibility.
    """
    # New fields - Message reference
    message_ref: str = ""                      # Reference to CanMessage.id

    # Frame offset (for compound/multiplexed messages)
    frame_offset: int = 0                      # +0 to +7 for compound messages

    # Data extraction
    data_type: CanDataType = CanDataType.UNSIGNED
    data_format: CanDataFormat = CanDataFormat.BIT_16
    byte_order: str = "little_endian"          # little_endian or big_endian
    byte_offset: int = 0                       # 0-7 byte position

    # Custom bitfield (when data_format == CUSTOM)
    start_bit: int = 0
    bit_length: int = 16

    # Scaling (multiplier/divider instead of factor)
    multiplier: float = 1.0
    divider: float = 1.0
    offset: float = 0.0
    decimal_places: int = 0

    # Timeout behavior
    default_value: float = 0.0
    timeout_behavior: CanTimeoutBehavior = CanTimeoutBehavior.USE_DEFAULT

    # Legacy fields (kept for backwards compatibility / migration)
    can_bus: int = 1                           # Deprecated - use message_ref
    message_id: int = 0                        # Deprecated - use message_ref
    is_extended: bool = False                  # Deprecated - use message_ref
    length: int = 8                            # Deprecated - use bit_length
    value_type: str = "unsigned"               # Deprecated - use data_type
    factor: float = 1.0                        # Deprecated - use multiplier
    timeout_ms: int = 1000                     # Deprecated - use CanMessage.timeout_ms

    def __post_init__(self):
        self.channel_type = ChannelType.CAN_RX

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()

        # New architecture fields (always saved)
        data.update({
            "message_ref": self.message_ref,
            "frame_offset": self.frame_offset,
            "data_type": self.data_type.value if isinstance(self.data_type, CanDataType) else self.data_type,
            "data_format": self.data_format.value if isinstance(self.data_format, CanDataFormat) else self.data_format,
            "byte_order": self.byte_order,
            "byte_offset": self.byte_offset,
            "start_bit": self.start_bit,
            "bit_length": self.bit_length,
            "multiplier": self.multiplier,
            "divider": self.divider,
            "offset": self.offset,
            "decimal_places": self.decimal_places,
            "default_value": self.default_value,
            "timeout_behavior": self.timeout_behavior.value if isinstance(self.timeout_behavior, CanTimeoutBehavior) else self.timeout_behavior,
        })

        # Legacy fields (for backwards compatibility)
        if not self.message_ref:
            # Only include legacy fields if message_ref is not set
            data.update({
                "can_bus": self.can_bus,
                "message_id": self.message_id,
                "is_extended": self.is_extended,
                "length": self.length,
                "value_type": self.value_type,
                "factor": self.factor,
                "timeout_ms": self.timeout_ms
            })

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanRxChannel':
        # Parse data_type
        data_type_str = data.get("data_type", data.get("value_type", "unsigned"))
        try:
            data_type = CanDataType(data_type_str)
        except ValueError:
            data_type = CanDataType.UNSIGNED

        # Parse data_format
        data_format_str = data.get("data_format", "16bit")
        try:
            data_format = CanDataFormat(data_format_str)
        except ValueError:
            data_format = CanDataFormat.BIT_16

        # Parse timeout_behavior
        timeout_beh_str = data.get("timeout_behavior", "use_default")
        try:
            timeout_behavior = CanTimeoutBehavior(timeout_beh_str)
        except ValueError:
            timeout_behavior = CanTimeoutBehavior.USE_DEFAULT

        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.CAN_RX,
            channel_id=data.get("channel_id", 0),
            # New fields
            message_ref=data.get("message_ref", ""),
            frame_offset=data.get("frame_offset", 0),
            data_type=data_type,
            data_format=data_format,
            byte_order=data.get("byte_order", "little_endian"),
            byte_offset=data.get("byte_offset", 0),
            start_bit=data.get("start_bit", 0),
            bit_length=data.get("bit_length", data.get("length", 16)),
            multiplier=data.get("multiplier", data.get("factor", 1.0)),
            divider=data.get("divider", 1.0),
            offset=data.get("offset", 0.0),
            decimal_places=data.get("decimal_places", 0),
            default_value=data.get("default_value", 0.0),
            timeout_behavior=timeout_behavior,
            # Legacy fields
            can_bus=data.get("can_bus", 1),
            message_id=data.get("message_id", 0),
            is_extended=data.get("is_extended", False),
            length=data.get("length", 8),
            value_type=data.get("value_type", "unsigned"),
            factor=data.get("factor", 1.0),
            timeout_ms=data.get("timeout_ms", 1000)
        )

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = super().validate()

        # New architecture validation
        if self.message_ref:
            if self.frame_offset < 0 or self.frame_offset > 7:
                errors.append("Frame offset must be between 0 and 7")
            if self.byte_offset < 0 or self.byte_offset > 7:
                errors.append("Byte offset must be between 0 and 7")
            if self.data_format == CanDataFormat.CUSTOM:
                if self.start_bit < 0 or self.start_bit > 63:
                    errors.append("Start bit must be between 0 and 63")
                if self.bit_length < 1 or self.bit_length > 64:
                    errors.append("Bit length must be between 1 and 64")
            if self.divider == 0:
                errors.append("Divider cannot be zero")

        return errors


@dataclass
class CanTxSignal:
    """Single CAN transmit signal"""
    source_channel: str
    start_bit: int = 0
    length: int = 8
    byte_order: str = "little_endian"
    factor: float = 1.0
    offset: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_channel": self.source_channel,
            "start_bit": self.start_bit,
            "length": self.length,
            "byte_order": self.byte_order,
            "factor": self.factor,
            "offset": self.offset
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanTxSignal':
        return cls(
            source_channel=data.get("source_channel", ""),
            start_bit=data.get("start_bit", 0),
            length=data.get("length", 8),
            byte_order=data.get("byte_order", "little_endian"),
            factor=data.get("factor", 1.0),
            offset=data.get("offset", 0.0)
        )


@dataclass
class CanTxChannel(ChannelBase):
    """CAN transmit channel"""
    can_bus: int = 1
    message_id: int = 0
    is_extended: bool = False
    cycle_time_ms: int = 100
    signals: List[CanTxSignal] = field(default_factory=list)

    def __post_init__(self):
        self.channel_type = ChannelType.CAN_TX

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "can_bus": self.can_bus,
            "message_id": self.message_id,
            "is_extended": self.is_extended,
            "cycle_time_ms": self.cycle_time_ms,
            "signals": [sig.to_dict() for sig in self.signals]
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanTxChannel':
        signals = [CanTxSignal.from_dict(sig) for sig in data.get("signals", [])]
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.CAN_TX,
            channel_id=data.get("channel_id", 0),
            can_bus=data.get("can_bus", 1),
            message_id=data.get("message_id", 0),
            is_extended=data.get("is_extended", False),
            cycle_time_ms=data.get("cycle_time_ms", 100),
            signals=signals
        )

    def get_input_channels(self) -> List[str]:
        return [sig.source_channel for sig in self.signals if sig.source_channel]

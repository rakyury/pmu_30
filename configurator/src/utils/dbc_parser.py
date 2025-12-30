"""
DBC Parser - Parse industry-standard .dbc CAN database files

The DBC format is a standard for defining CAN messages and signals.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class DbcSignal:
    """Represents a single CAN signal from .dbc file."""
    name: str
    start_bit: int = 0
    length: int = 8
    byte_order: str = "little_endian"  # 1 = little endian (Intel), 0 = big endian (Motorola)
    value_type: str = "unsigned"  # + = unsigned, - = signed
    factor: float = 1.0
    offset: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    unit: str = ""
    receivers: List[str] = field(default_factory=list)
    message_id: int = 0
    message_name: str = ""

    def to_can_input_config(self, message_ref: str) -> Dict[str, Any]:
        """Convert to CAN input channel configuration dict."""
        # Sanitize ID for our model
        channel_id = "crx_" + self.name.replace(" ", "_").replace("-", "_").lower()

        # Determine data format from bit length
        if self.length <= 8:
            data_format = "8bit"
        elif self.length <= 16:
            data_format = "16bit"
        elif self.length <= 32:
            data_format = "32bit"
        else:
            data_format = "custom"

        # If bit length doesn't match standard, use custom
        if self.length not in [8, 16, 32]:
            data_format = "custom"

        # Calculate byte offset from start bit (approximate for display)
        byte_offset = self.start_bit // 8

        return {
            "id": channel_id,
            "channel_type": "can_rx",
            "message_ref": message_ref,
            "frame_offset": 0,
            "data_type": self.value_type,
            "data_format": data_format,
            "byte_order": self.byte_order,
            "byte_offset": byte_offset,
            "start_bit": self.start_bit,
            "bit_length": self.length,
            "multiplier": self.factor,
            "divider": 1.0,
            "offset": self.offset,
            "decimal_places": self._guess_decimal_places(),
            "default_value": 0.0,
            "timeout_behavior": "use_default",
        }

    def _guess_decimal_places(self) -> int:
        """Guess decimal places from factor."""
        if self.factor == 0:
            return 0
        if self.factor >= 1:
            return 0
        # Count decimal places in factor
        factor_str = f"{self.factor:.10f}".rstrip('0')
        if '.' in factor_str:
            return len(factor_str.split('.')[1])
        return 0


@dataclass
class DbcMessage:
    """Represents a CAN message from .dbc file."""
    id: int
    name: str
    length: int = 8
    transmitter: str = ""
    signals: List[DbcSignal] = field(default_factory=list)

    def to_can_message_config(self, msg_id: str = "") -> Dict[str, Any]:
        """Convert to CAN message configuration dict."""
        if not msg_id:
            msg_id = "msg_" + self.name.replace(" ", "_").replace("-", "_").lower()

        # Check if extended ID (29-bit)
        is_extended = self.id > 0x7FF

        return {
            "id": msg_id,
            "name": self.name,
            "can_bus": 1,  # Default to CAN 1, user can change
            "base_id": self.id & 0x1FFFFFFF,  # Mask to 29 bits
            "is_extended": is_extended,
            "message_type": "normal",
            "frame_count": 1,
            "dlc": self.length,
            "timeout_ms": 500,
            "enabled": True,
            "description": f"Imported from DBC: {self.transmitter}" if self.transmitter else "Imported from DBC"
        }


@dataclass
class DbcData:
    """Container for all parsed .dbc data."""
    messages: List[DbcMessage] = field(default_factory=list)
    filename: str = ""
    version: str = ""
    description: str = ""

    def get_all_signals(self) -> List[DbcSignal]:
        """Get flat list of all signals from all messages."""
        signals = []
        for msg in self.messages:
            signals.extend(msg.signals)
        return signals

    def get_signals_by_message(self) -> Dict[int, List[DbcSignal]]:
        """Get signals grouped by message ID."""
        result = {}
        for msg in self.messages:
            result[msg.id] = msg.signals
        return result


class DbcParser:
    """Parser for .dbc CAN database files."""

    # Regex patterns for DBC parsing
    VERSION_PATTERN = re.compile(r'VERSION\s+"([^"]*)"')
    MESSAGE_PATTERN = re.compile(r'BO_\s+(\d+)\s+(\w+)\s*:\s*(\d+)\s+(\w+)?')
    SIGNAL_PATTERN = re.compile(
        r'SG_\s+(\w+)\s*:\s*(\d+)\|(\d+)@([01])([+-])\s*'
        r'\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)\s*'
        r'\[\s*([-\d.eE+]+)\|([-\d.eE+]+)\s*\]\s*'
        r'"([^"]*)"\s*(.*)'
    )
    COMMENT_PATTERN = re.compile(r'CM_\s+"([^"]*)"')
    SIG_COMMENT_PATTERN = re.compile(r'CM_\s+SG_\s+(\d+)\s+(\w+)\s+"([^"]*)"')
    MSG_COMMENT_PATTERN = re.compile(r'CM_\s+BO_\s+(\d+)\s+"([^"]*)"')

    def parse_file(self, filepath: str) -> DbcData:
        """Parse a .dbc file from disk."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Try different encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
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

    def parse_string(self, dbc_content: str) -> DbcData:
        """Parse .dbc content from string."""
        data = DbcData()

        # Parse version
        version_match = self.VERSION_PATTERN.search(dbc_content)
        if version_match:
            data.version = version_match.group(1)

        # Current message being parsed
        current_message: Optional[DbcMessage] = None

        # Process line by line
        lines = dbc_content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and comments
            if not line or line.startswith('//'):
                i += 1
                continue

            # Check for message definition
            msg_match = self.MESSAGE_PATTERN.match(line)
            if msg_match:
                # Save previous message
                if current_message:
                    data.messages.append(current_message)

                msg_id = int(msg_match.group(1))
                msg_name = msg_match.group(2)
                msg_len = int(msg_match.group(3))
                transmitter = msg_match.group(4) or ""

                current_message = DbcMessage(
                    id=msg_id,
                    name=msg_name,
                    length=msg_len,
                    transmitter=transmitter
                )
                i += 1
                continue

            # Check for signal definition (must be within a message)
            if line.startswith('SG_') and current_message:
                sig_match = self.SIGNAL_PATTERN.match(line)
                if sig_match:
                    signal = self._parse_signal(sig_match, current_message)
                    current_message.signals.append(signal)
                i += 1
                continue

            # If we hit a new section, save current message
            if line.startswith(('CM_', 'BA_', 'VAL_', 'NS_', 'BS_')):
                if current_message:
                    data.messages.append(current_message)
                    current_message = None

            i += 1

        # Don't forget the last message
        if current_message:
            data.messages.append(current_message)

        return data

    def _parse_signal(self, match: re.Match, message: DbcMessage) -> DbcSignal:
        """Parse a signal from regex match."""
        name = match.group(1)
        start_bit = int(match.group(2))
        length = int(match.group(3))
        byte_order_code = match.group(4)
        value_type_code = match.group(5)
        factor = float(match.group(6))
        offset = float(match.group(7))
        min_val = float(match.group(8))
        max_val = float(match.group(9))
        unit = match.group(10)
        receivers_str = match.group(11)

        # Parse byte order (1 = little endian, 0 = big endian)
        byte_order = "little_endian" if byte_order_code == "1" else "big_endian"

        # Parse value type (+ = unsigned, - = signed)
        value_type = "unsigned" if value_type_code == "+" else "signed"

        # Parse receivers (comma-separated list)
        receivers = [r.strip() for r in receivers_str.split(',') if r.strip()]

        return DbcSignal(
            name=name,
            start_bit=start_bit,
            length=length,
            byte_order=byte_order,
            value_type=value_type,
            factor=factor,
            offset=offset,
            min_value=min_val,
            max_value=max_val,
            unit=unit,
            receivers=receivers,
            message_id=message.id,
            message_name=message.name
        )

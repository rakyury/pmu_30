"""
Shared Validation Integration for Configurator

This module bridges the shared channel validation library
with the Configurator's UI dialogs.

Uses shared/python/channel_validation.py for validation logic
to ensure consistency between Configurator, Firmware, and Tests.
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

# Add shared/python to path for imports
# Path: configurator/src/utils/validation.py -> 3 levels up to configurator, then sibling shared/python
SHARED_PYTHON_PATH = Path(__file__).parent.parent.parent.parent / "shared" / "python"
if str(SHARED_PYTHON_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PYTHON_PATH))

# Import from shared library
try:
    from channel_validation import (
        validate_channel,
        ValidationResult,
        ValidationError,
        ValidationLimits,
        get_error_message,
    )
    SHARED_VALIDATION_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Shared validation not available: {e}")
    SHARED_VALIDATION_AVAILABLE = False


# Mapping from ChannelType string values to numeric codes (from channel_types.h)
CHANNEL_TYPE_CODES = {
    "digital_input": 0x01,    # CH_TYPE_DIGITAL_INPUT
    "analog_input": 0x02,     # CH_TYPE_ANALOG_INPUT
    "frequency_input": 0x03,  # CH_TYPE_FREQUENCY_INPUT
    "can_rx": 0x04,           # CH_TYPE_CAN_INPUT
    "power_output": 0x10,     # CH_TYPE_POWER_OUTPUT
    "pwm_output": 0x11,       # CH_TYPE_PWM_OUTPUT
    "hbridge": 0x12,          # CH_TYPE_HBRIDGE
    "can_tx": 0x13,           # CH_TYPE_CAN_OUTPUT
    "timer": 0x20,            # CH_TYPE_TIMER
    "logic": 0x21,            # CH_TYPE_LOGIC
    "math": 0x22,             # CH_TYPE_MATH
    "table_2d": 0x23,         # CH_TYPE_TABLE_2D
    "table_3d": 0x24,         # CH_TYPE_TABLE_3D
    "filter": 0x25,           # CH_TYPE_FILTER
    "pid": 0x26,              # CH_TYPE_PID
    "number": 0x27,           # CH_TYPE_NUMBER
    "switch": 0x28,           # CH_TYPE_SWITCH
    "counter": 0x2A,          # CH_TYPE_COUNTER
    "hysteresis": 0x2B,       # CH_TYPE_HYSTERESIS
    "flipflop": 0x2C,         # CH_TYPE_FLIPFLOP
    # These don't have shared validation yet
    "lua_script": None,
    "handler": None,
    "blinkmarine_keypad": None,
    "wiper": None,
    "blinker": None,
    "system": None,
    "output_status": None,
}


# ============================================================================
# Config Transformers: UI format -> Shared validation format
# ============================================================================

def _transform_timer_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform timer config from UI to shared validation format."""
    result = dict(config)

    # Convert hours/minutes/seconds to delay_ms
    hours = config.get('limit_hours', 0)
    minutes = config.get('limit_minutes', 0)
    seconds = config.get('limit_seconds', 0)
    delay_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
    result['delay_ms'] = delay_ms

    # Map start_channel to trigger_id
    start_ch = config.get('start_channel')
    if start_ch and isinstance(start_ch, int):
        result['trigger_id'] = start_ch

    return result


def _transform_logic_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform logic config from UI to shared validation format."""
    result = dict(config)

    # Map input_channels list to input_ids
    inputs = config.get('input_channels', [])
    if inputs:
        result['input_ids'] = [ch if isinstance(ch, int) else 0 for ch in inputs]
        result['num_inputs'] = len(inputs)

    return result


def _transform_power_output_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform power output config from UI to shared validation format."""
    result = dict(config)

    # Convert current_limit_a to current_limit_ma
    current_a = config.get('current_limit', 0)
    if isinstance(current_a, (int, float)):
        result['current_limit_ma'] = int(current_a * 1000)

    return result


CONFIG_TRANSFORMERS = {
    "timer": _transform_timer_config,
    "logic": _transform_logic_config,
    "power_output": _transform_power_output_config,
}


def validate_channel_config(
    channel_type: str,
    config: Dict[str, Any],
    limits: Optional[ValidationLimits] = None
) -> List[str]:
    """
    Validate channel configuration using shared validation logic.

    Args:
        channel_type: Channel type string (e.g., "timer", "logic")
        config: Configuration dictionary from dialog
        limits: Optional custom validation limits

    Returns:
        List of error message strings (empty if valid)
    """
    if not SHARED_VALIDATION_AVAILABLE:
        # Fallback: no shared validation, assume valid
        return []

    # Get numeric type code
    type_code = CHANNEL_TYPE_CODES.get(channel_type)
    if type_code is None:
        # Type not supported by shared validation
        return []

    # Transform config if transformer exists
    transformer = CONFIG_TRANSFORMERS.get(channel_type)
    if transformer:
        config = transformer(config)

    # Call shared validation
    result = validate_channel(type_code, config, limits)

    if result.is_valid:
        return []

    # Format error message
    message = result.message or f"Validation error: {result.error.name}"
    if result.field:
        message = f"{result.field}: {message}"
    if result.expected_min or result.expected_max:
        message += f" (expected: {result.expected_min}-{result.expected_max}, got: {result.actual_value})"

    return [message]


def validate_with_shared(
    channel_type_enum,  # ChannelType enum
    config: Dict[str, Any]
) -> List[str]:
    """
    Convenience wrapper that accepts ChannelType enum.

    Args:
        channel_type_enum: ChannelType enum value
        config: Configuration dictionary

    Returns:
        List of error message strings
    """
    type_str = channel_type_enum.value if hasattr(channel_type_enum, 'value') else str(channel_type_enum)
    return validate_channel_config(type_str, config)


def is_shared_validation_available() -> bool:
    """Check if shared validation is available."""
    return SHARED_VALIDATION_AVAILABLE

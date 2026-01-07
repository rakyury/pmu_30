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

    # Convert string mode to integer for validation
    # UI uses "count_up"/"count_down" strings, validation expects integers 0-6
    mode_str = config.get('mode', 'count_up')
    mode_map = {
        'count_up': 0,      # TIMER_MODE_ONE_SHOT
        'count_down': 1,    # TIMER_MODE_RETRIGGERABLE
        'one_shot': 0,
        'retriggerable': 1,
        'delay': 2,
        'pulse': 3,
        'blink': 4,
    }
    result['mode'] = mode_map.get(mode_str, 0) if isinstance(mode_str, str) else mode_str

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


def _transform_filter_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform filter config from UI to shared validation format."""
    result = dict(config)

    # Map input_channel to input_id
    input_ch = config.get('input_channel')
    if input_ch and isinstance(input_ch, int):
        result['input_id'] = input_ch

    # Convert time_constant (seconds) to time_constant_ms
    time_const = config.get('time_constant', 0.1)
    if isinstance(time_const, (int, float)):
        result['time_constant_ms'] = int(time_const * 1000)

    return result


def _transform_switch_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform switch config from UI to shared validation format."""
    result = dict(config)

    # Map input_channel_up to selector_id
    input_up = config.get('input_channel_up')
    if input_up and isinstance(input_up, int):
        result['selector_id'] = input_up

    # Create cases list from first_state to last_state
    first_state = config.get('first_state', 0)
    last_state = config.get('last_state', 2)
    cases = list(range(first_state, last_state + 1))
    result['cases'] = cases

    return result


def _transform_number_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform number config from UI to shared validation format."""
    result = dict(config)

    # For constant operation, set value from constant_value
    if config.get('operation') == 'constant':
        result['value'] = int(config.get('constant_value', 0) * 100)  # Scale for fixed-point

    # Set reasonable defaults if not present
    if 'min_value' not in result:
        result['min_value'] = -1000000
    if 'max_value' not in result:
        result['max_value'] = 1000000

    return result


def _transform_can_input_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform CAN input config from UI to shared validation format."""
    result = dict(config)

    # Most fields have same names, just ensure types
    if 'can_id' in config:
        result['can_id'] = int(config['can_id'])

    return result


def _transform_analog_input_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform analog input config from UI to shared validation format."""
    result = dict(config)

    # Map calibration values to raw values
    if 'cal_raw_low' in config:
        result['raw_min'] = config['cal_raw_low']
    if 'cal_raw_high' in config:
        result['raw_max'] = config['cal_raw_high']

    return result


def _transform_pid_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform PID config from UI to shared validation format."""
    result = dict(config)

    # Map setpoint_channel to setpoint_id
    setpoint_ch = config.get('setpoint_channel')
    if setpoint_ch and isinstance(setpoint_ch, int):
        result['setpoint_id'] = setpoint_ch

    # Map feedback_channel to feedback_id
    feedback_ch = config.get('feedback_channel')
    if feedback_ch and isinstance(feedback_ch, int):
        result['feedback_id'] = feedback_ch

    return result


def _transform_table_2d_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform 2D table config from UI to shared validation format."""
    result = dict(config)

    # Map x_axis_channel to input_id
    x_channel = config.get('x_axis_channel')
    if x_channel and isinstance(x_channel, int):
        result['input_id'] = x_channel

    # Get point count from x_values length
    x_values = config.get('x_values', [])
    result['point_count'] = len(x_values)

    # Convert float values to integers for int16 storage
    output_values = config.get('output_values', [])
    result['x_values'] = [int(v) for v in x_values]
    result['y_values'] = [int(v) for v in output_values]

    return result


def _transform_digital_input_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform digital input config from UI to shared validation format."""
    result = dict(config)

    # Map UI field names to shared validation names
    if 'debounce_time' in config:
        result['debounce_ms'] = int(config['debounce_time'])

    return result


CONFIG_TRANSFORMERS = {
    "timer": _transform_timer_config,
    "logic": _transform_logic_config,
    "power_output": _transform_power_output_config,
    "filter": _transform_filter_config,
    "switch": _transform_switch_config,
    "number": _transform_number_config,
    "can_rx": _transform_can_input_config,
    "analog_input": _transform_analog_input_config,
    "pid": _transform_pid_config,
    "table_2d": _transform_table_2d_config,
    "digital_input": _transform_digital_input_config,
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

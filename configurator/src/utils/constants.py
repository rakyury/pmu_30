"""
Constants Display/Storage Utilities for PMU-30 Configurator

GLOBAL RULE: All numeric constants are displayed with 2 decimal places
but stored internally as integers (multiplied by 100).

Example:
  - User sees: 12.34
  - Stored as: 1234 (integer)
  - Display: 1234 / 100 = 12.34

This applies to:
  - Constant values in Number channels
  - Lookup table values
  - Threshold values
  - Scaling factors (multiplier, divider, offset)
  - Clamp min/max values
  - Any user-configurable numeric constant
"""

from typing import Union

# Global constant: 2 decimal places (scale factor = 100)
CONSTANT_DECIMAL_PLACES = 2
CONSTANT_SCALE = 100  # 10 ** CONSTANT_DECIMAL_PLACES


def display_to_internal(display_value: float) -> int:
    """
    Convert a display value to internal integer storage.

    Args:
        display_value: The value shown to the user (e.g., 12.34)

    Returns:
        Integer value for storage (e.g., 1234)
    """
    return int(round(display_value * CONSTANT_SCALE))


def internal_to_display(internal_value: int) -> float:
    """
    Convert an internal integer value to display format.

    Args:
        internal_value: The stored integer value (e.g., 1234)

    Returns:
        Float value for display (e.g., 12.34)
    """
    return internal_value / CONSTANT_SCALE


def format_constant(internal_value: int, suffix: str = "") -> str:
    """
    Format an internal integer constant for display.

    Args:
        internal_value: The stored integer value
        suffix: Optional suffix (e.g., " V", " A")

    Returns:
        Formatted string (e.g., "12.34 V")
    """
    display_val = internal_to_display(internal_value)
    formatted = f"{display_val:.{CONSTANT_DECIMAL_PLACES}f}"
    if suffix:
        return f"{formatted}{suffix}"
    return formatted


def parse_constant(text: str) -> int:
    """
    Parse a display string to internal integer value.

    Args:
        text: User input text (may include unit suffix)

    Returns:
        Integer value for storage
    """
    # Extract numeric part
    cleaned = ""
    for char in text:
        if char.isdigit() or char == '-' or char == '.':
            cleaned += char

    if not cleaned or cleaned == "-" or cleaned == ".":
        return 0

    try:
        display_val = float(cleaned)
        return display_to_internal(display_val)
    except ValueError:
        return 0


def clamp_internal(value: int, min_internal: int, max_internal: int) -> int:
    """
    Clamp an internal value within bounds.

    Args:
        value: Internal integer value
        min_internal: Minimum internal value
        max_internal: Maximum internal value

    Returns:
        Clamped internal value
    """
    return max(min_internal, min(max_internal, value))


# Convenience functions for common ranges (in display units)
def display_range_to_internal(min_display: float, max_display: float) -> tuple:
    """
    Convert a display range to internal range.

    Args:
        min_display: Minimum display value
        max_display: Maximum display value

    Returns:
        Tuple of (min_internal, max_internal)
    """
    return (display_to_internal(min_display), display_to_internal(max_display))


# Legacy conversion helpers for migration
def migrate_float_to_internal(old_value: Union[int, float]) -> int:
    """
    Migrate an old float config value to new internal integer format.

    Args:
        old_value: Old config value (might be float or already int)

    Returns:
        Internal integer value
    """
    if isinstance(old_value, int):
        # Check if it's already in internal format (large absolute value)
        # or a small integer that should be converted
        if abs(old_value) > 1000000:
            # Likely already internal format
            return old_value
        # Small integer, convert to internal
        return old_value * CONSTANT_SCALE
    elif isinstance(old_value, float):
        return display_to_internal(old_value)
    return 0


def is_likely_internal_format(value: Union[int, float]) -> bool:
    """
    Heuristic to detect if a value is already in internal format.

    Args:
        value: The value to check

    Returns:
        True if value appears to be in internal format
    """
    if isinstance(value, float):
        return False
    # Integers above this threshold are likely internal format
    return isinstance(value, int)

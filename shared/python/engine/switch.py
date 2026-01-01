"""
Logic Engine - Switch/Selector Functions

Pure functions for switching and selecting values.
No state required.
"""

from dataclasses import dataclass
from typing import List, Sequence, Optional


@dataclass
class SwitchCase:
    """Case for switch statement"""
    match_value: int
    result: int


@dataclass
class RangeCase:
    """Range-based case for switch"""
    min_value: int
    max_value: int
    result: int


def switch_select(values: Sequence[int], selector: int) -> int:
    """
    Select value by index.

    Args:
        values: Array of values to select from
        selector: Index to select (0-based)

    Returns:
        Selected value, or 0 if out of range
    """
    if not values:
        return 0
    if selector < 0 or selector >= len(values):
        return 0
    return values[selector]


def switch_case(
    input_value: int,
    cases: Sequence[SwitchCase],
    default_value: int = 0
) -> int:
    """
    Switch/case selection.

    Args:
        input_value: Value to match
        cases: List of SwitchCase to check
        default_value: Value if no match

    Returns:
        Matched result or default
    """
    for case in cases:
        if input_value == case.match_value:
            return case.result
    return default_value


def switch_range_case(
    input_value: int,
    cases: Sequence[RangeCase],
    default_value: int = 0
) -> int:
    """
    Range-based switch selection.

    Args:
        input_value: Value to check
        cases: List of RangeCase to check
        default_value: Value if no match

    Returns:
        Matched result or default
    """
    for case in cases:
        if case.min_value <= input_value <= case.max_value:
            return case.result
    return default_value


def switch_mux(
    inputs: Sequence[int],
    selectors: Sequence[int]
) -> int:
    """
    Multiplexer - select input based on first active selector.

    Args:
        inputs: Values to select from
        selectors: Selector signals (non-zero = active)

    Returns:
        First input where corresponding selector is active,
        or last input if none active
    """
    if not inputs:
        return 0

    n = min(len(inputs), len(selectors))

    for i in range(n):
        if selectors[i] != 0:
            return inputs[i]

    # No selector active - return last input as fallback
    return inputs[-1] if inputs else 0


def switch_priority(inputs: Sequence[int], enable: Sequence[int]) -> int:
    """
    Priority encoder - returns first enabled input.

    Args:
        inputs: Input values
        enable: Enable signals (non-zero = enabled)

    Returns:
        First enabled input value, or 0 if none enabled
    """
    if not inputs or not enable:
        return 0

    n = min(len(inputs), len(enable))

    for i in range(n):
        if enable[i] != 0:
            return inputs[i]

    return 0


def switch_ternary(condition: int, true_value: int, false_value: int) -> int:
    """
    Ternary operator: condition ? true_value : false_value

    Args:
        condition: Condition to test (non-zero = true)
        true_value: Value if condition is true
        false_value: Value if condition is false

    Returns:
        Selected value
    """
    return true_value if condition != 0 else false_value


def switch_decode(selector: int, count: int) -> List[int]:
    """
    Binary decoder - activates one output based on selector.

    Args:
        selector: Which output to activate (0-based)
        count: Number of outputs

    Returns:
        List with all zeros except 1 at selector position
    """
    result = [0] * count
    if 0 <= selector < count:
        result[selector] = 1
    return result


def switch_encode(inputs: Sequence[int]) -> int:
    """
    Binary encoder - returns index of first active input.

    Args:
        inputs: Input signals

    Returns:
        Index of first non-zero input, or -1 if none active
    """
    for i, val in enumerate(inputs):
        if val != 0:
            return i
    return -1

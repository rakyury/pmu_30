"""
Logic Engine - Hysteresis Comparator

Schmitt trigger and hysteresis comparator implementations.
"""

from dataclasses import dataclass, field
from typing import List, Optional


HYST_MAX_LEVELS = 8


# ============================================================================
# Simple Hysteresis
# ============================================================================

@dataclass
class HysteresisConfig:
    """Simple hysteresis configuration"""
    threshold_high: int = 100   # Upper threshold (turn on)
    threshold_low: int = 50     # Lower threshold (turn off)
    invert: bool = False


@dataclass
class HysteresisState:
    """Simple hysteresis state"""
    output: int = 0
    initialized: bool = False


def hysteresis_init(state: Optional[HysteresisState] = None) -> HysteresisState:
    """Initialize hysteresis state"""
    if state is None:
        return HysteresisState()
    state.output = 0
    state.initialized = False
    return state


def hysteresis_reset(state: HysteresisState, output: int = 0) -> None:
    """Reset hysteresis to specific output"""
    state.output = 1 if output != 0 else 0
    state.initialized = True


def hysteresis_update(
    state: HysteresisState,
    config: HysteresisConfig,
    input_val: int
) -> int:
    """
    Update hysteresis comparator.

    Args:
        state: Hysteresis state (modified)
        config: Comparator configuration
        input_val: Input value

    Returns:
        Output (0 or 1)
    """
    if not state.initialized:
        # Initial state based on input vs midpoint
        mid = (config.threshold_high + config.threshold_low) // 2
        state.output = 1 if input_val >= mid else 0
        state.initialized = True
    else:
        if state.output:
            # Currently HIGH, check for transition LOW
            if input_val <= config.threshold_low:
                state.output = 0
        else:
            # Currently LOW, check for transition HIGH
            if input_val >= config.threshold_high:
                state.output = 1

    return (0 if state.output else 1) if config.invert else state.output


def hysteresis_config_from_band(center: int, band: int) -> HysteresisConfig:
    """Create hysteresis config from center and band width"""
    half_band = band // 2
    return HysteresisConfig(
        threshold_high=center + half_band,
        threshold_low=center - half_band,
        invert=False
    )


# ============================================================================
# Window Comparator
# ============================================================================

@dataclass
class WindowConfig:
    """Window comparator configuration"""
    low_threshold: int = 0
    high_threshold: int = 100
    hysteresis: int = 5
    invert: bool = False    # Invert: outside window = HIGH


@dataclass
class WindowState:
    """Window comparator state"""
    output: int = 0
    initialized: bool = False


def window_init(state: Optional[WindowState] = None) -> WindowState:
    """Initialize window state"""
    if state is None:
        return WindowState()
    state.output = 0
    state.initialized = False
    return state


def window_update(
    state: WindowState,
    config: WindowConfig,
    input_val: int
) -> int:
    """
    Update window comparator.

    Args:
        state: Window state (modified)
        config: Window configuration
        input_val: Input value

    Returns:
        Output (1 = in window, 0 = outside)
    """
    hyst = config.hysteresis

    if not state.initialized:
        # Initial state based on whether input is in window
        in_window = config.low_threshold <= input_val <= config.high_threshold
        state.output = 1 if in_window else 0
        state.initialized = True
    else:
        if state.output:
            # Currently IN window, check for exit
            if (input_val < (config.low_threshold - hyst) or
                input_val > (config.high_threshold + hyst)):
                state.output = 0
        else:
            # Currently OUT of window, check for entry
            if ((config.low_threshold + hyst) <= input_val <=
                (config.high_threshold - hyst)):
                state.output = 1

    return (0 if state.output else 1) if config.invert else state.output


# ============================================================================
# Multi-Level Hysteresis
# ============================================================================

@dataclass
class LevelThreshold:
    """Level threshold definition"""
    threshold_up: int = 0     # Threshold to move up to this level
    threshold_down: int = 0   # Threshold to move down from this level


@dataclass
class MultiLevelConfig:
    """Multi-level hysteresis configuration"""
    thresholds: List[LevelThreshold] = field(default_factory=list)
    level_count: int = 2


@dataclass
class MultiLevelState:
    """Multi-level hysteresis state"""
    current_level: int = 0
    initialized: bool = False


def multilevel_init(state: Optional[MultiLevelState] = None) -> MultiLevelState:
    """Initialize multi-level state"""
    if state is None:
        return MultiLevelState()
    state.current_level = 0
    state.initialized = False
    return state


def multilevel_reset(state: MultiLevelState, level: int = 0) -> None:
    """Reset multi-level to specific level"""
    state.current_level = level
    state.initialized = True


def multilevel_update(
    state: MultiLevelState,
    config: MultiLevelConfig,
    input_val: int
) -> int:
    """
    Update multi-level hysteresis.

    Args:
        state: Multi-level state (modified)
        config: Multi-level configuration
        input_val: Input value

    Returns:
        Current level (0 to level_count-1)
    """
    count = max(2, min(config.level_count, HYST_MAX_LEVELS, len(config.thresholds)))

    if not state.initialized:
        # Find initial level
        state.current_level = 0
        for i in range(1, count):
            if i < len(config.thresholds) and input_val >= config.thresholds[i].threshold_up:
                state.current_level = i
            else:
                break
        state.initialized = True
    else:
        level = state.current_level

        # Check for level up
        while level < count - 1:
            if (level + 1 < len(config.thresholds) and
                input_val >= config.thresholds[level + 1].threshold_up):
                level += 1
            else:
                break

        # Check for level down
        while level > 0:
            if (level < len(config.thresholds) and
                input_val <= config.thresholds[level].threshold_down):
                level -= 1
            else:
                break

        state.current_level = level

    return state.current_level


# ============================================================================
# Pure Comparator Functions (Stateless)
# ============================================================================

def compare_ge(input_val: int, threshold: int) -> int:
    """Simple threshold compare: input >= threshold"""
    return 1 if input_val >= threshold else 0


def compare_gt(input_val: int, threshold: int) -> int:
    """Simple threshold compare: input > threshold"""
    return 1 if input_val > threshold else 0


def compare_in_range(input_val: int, low: int, high: int) -> int:
    """Range check: low <= input <= high"""
    return 1 if low <= input_val <= high else 0


def deadband(input_val: int, center: int, band: int) -> int:
    """
    Deadband function.
    Returns 0 if input is within deadband of center.

    Args:
        input_val: Input value
        center: Center value
        band: Deadband radius

    Returns:
        0 if in deadband, else (input - center) adjusted for deadband
    """
    diff = input_val - center

    if diff > 0:
        if diff <= band:
            return 0
        return diff - band
    elif diff < 0:
        if diff >= -band:
            return 0
        return diff + band

    return 0

"""
Logic Engine - Counter

Counter with increment/decrement/reset triggers and external state.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CounterConfig:
    """Counter configuration"""
    initial_value: int = 0
    min_value: int = 0
    max_value: int = 100
    step: int = 1
    wrap: bool = False      # Wrap around at limits vs clamp
    edge_mode: bool = True  # Trigger on edge vs level


@dataclass
class CounterState:
    """Counter state (externally managed)"""
    value: int = 0
    last_inc: int = 0
    last_dec: int = 0
    last_reset: int = 0


def _apply_limits(value: int, config: CounterConfig) -> int:
    """Apply min/max limits with wrap or clamp"""
    if config.wrap:
        range_size = config.max_value - config.min_value + 1
        if range_size <= 0:
            return value

        while value > config.max_value:
            value -= range_size
        while value < config.min_value:
            value += range_size
    else:
        if value < config.min_value:
            value = config.min_value
        if value > config.max_value:
            value = config.max_value

    return value


def _detect_rising_edge(last_state: int, current: int) -> tuple[bool, int]:
    """Detect rising edge. Returns (edge_detected, new_last_state)"""
    curr_high = 1 if current != 0 else 0
    prev_high = 1 if last_state != 0 else 0
    return (curr_high and not prev_high), curr_high


def counter_init(state: Optional[CounterState] = None,
                 config: Optional[CounterConfig] = None) -> CounterState:
    """Initialize counter state"""
    if state is None:
        state = CounterState()

    state.value = config.initial_value if config else 0
    state.last_inc = 0
    state.last_dec = 0
    state.last_reset = 0

    return state


def counter_reset(state: CounterState, config: CounterConfig) -> None:
    """Reset counter to initial value"""
    state.value = config.initial_value


def counter_update(
    state: CounterState,
    config: CounterConfig,
    inc_trigger: int,
    dec_trigger: int,
    reset_trigger: int
) -> int:
    """
    Update counter based on triggers.

    Args:
        state: Counter state (modified)
        config: Counter configuration
        inc_trigger: Increment trigger
        dec_trigger: Decrement trigger
        reset_trigger: Reset trigger

    Returns:
        Current counter value
    """
    # Check reset first
    if config.edge_mode:
        edge, state.last_reset = _detect_rising_edge(state.last_reset, reset_trigger)
        if edge:
            counter_reset(state, config)
            return state.value
    else:
        if reset_trigger != 0:
            counter_reset(state, config)
            return state.value

    # Check increment
    do_increment = False
    if config.edge_mode:
        do_increment, state.last_inc = _detect_rising_edge(state.last_inc, inc_trigger)
    else:
        do_increment = inc_trigger != 0
        state.last_inc = 1 if inc_trigger != 0 else 0

    if do_increment:
        state.value += config.step
        state.value = _apply_limits(state.value, config)

    # Check decrement
    do_decrement = False
    if config.edge_mode:
        do_decrement, state.last_dec = _detect_rising_edge(state.last_dec, dec_trigger)
    else:
        do_decrement = dec_trigger != 0
        state.last_dec = 1 if dec_trigger != 0 else 0

    if do_decrement:
        state.value -= config.step
        state.value = _apply_limits(state.value, config)

    return state.value


def counter_increment(state: CounterState, config: CounterConfig) -> int:
    """Direct increment (bypasses triggers)"""
    state.value += config.step
    state.value = _apply_limits(state.value, config)
    return state.value


def counter_decrement(state: CounterState, config: CounterConfig) -> int:
    """Direct decrement (bypasses triggers)"""
    state.value -= config.step
    state.value = _apply_limits(state.value, config)
    return state.value


def counter_set_value(state: CounterState, config: CounterConfig, value: int) -> None:
    """Set counter value directly"""
    state.value = _apply_limits(value, config)


def counter_is_at_min(state: CounterState, config: CounterConfig) -> bool:
    """Check if counter is at minimum"""
    return state.value <= config.min_value


def counter_is_at_max(state: CounterState, config: CounterConfig) -> bool:
    """Check if counter is at maximum"""
    return state.value >= config.max_value

"""
Logic Engine - Timer Functions

Timer implementations with external state management.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class TimerMode(IntEnum):
    """Timer operation modes"""
    DELAY_ON = 0       # Delay before output goes high
    DELAY_OFF = 1      # Delay before output goes low
    PULSE = 2          # Output pulse for duration
    BLINK = 3          # Alternating on/off
    ONESHOT = 4        # Single trigger, stays high until reset
    RETRIGGERABLE = 5  # Restarts on each trigger
    MONOSTABLE = 6     # Pulse that ignores triggers during output


class TimerTrigger(IntEnum):
    """Timer trigger modes"""
    LEVEL = 0          # Level-sensitive
    RISING_EDGE = 1    # Rising edge only
    FALLING_EDGE = 2   # Falling edge only
    ANY_EDGE = 3       # Any edge


class TimerStateEnum(IntEnum):
    """Timer state values"""
    IDLE = 0
    RUNNING = 1
    EXPIRED = 2
    PAUSED = 3


@dataclass
class TimerConfig:
    """Timer configuration"""
    mode: TimerMode = TimerMode.DELAY_ON
    trigger_mode: TimerTrigger = TimerTrigger.LEVEL
    delay_ms: int = 1000
    on_time_ms: int = 500      # For BLINK mode
    off_time_ms: int = 500     # For BLINK mode
    auto_reset: bool = False


@dataclass
class TimerState:
    """Timer state (externally managed)"""
    state: TimerStateEnum = TimerStateEnum.IDLE
    output: int = 0
    last_trigger: int = 0
    start_time_ms: int = 0
    elapsed_ms: int = 0
    blink_phase: int = 0


def timer_init(state: Optional[TimerState] = None) -> TimerState:
    """Initialize timer state"""
    if state is None:
        return TimerState()
    state.state = TimerStateEnum.IDLE
    state.output = 0
    state.last_trigger = 0
    state.start_time_ms = 0
    state.elapsed_ms = 0
    state.blink_phase = 0
    return state


def timer_reset(state: TimerState) -> None:
    """Reset timer to idle state"""
    state.state = TimerStateEnum.IDLE
    state.output = 0
    state.elapsed_ms = 0
    state.blink_phase = 0


def _detect_edge(last_state: int, current: int, trigger_mode: TimerTrigger) -> tuple[bool, int]:
    """Detect edge based on trigger mode. Returns (triggered, new_last_state)"""
    curr_high = 1 if current != 0 else 0
    prev_high = 1 if last_state != 0 else 0

    triggered = False

    if trigger_mode == TimerTrigger.LEVEL:
        triggered = curr_high != 0
    elif trigger_mode == TimerTrigger.RISING_EDGE:
        triggered = curr_high and not prev_high
    elif trigger_mode == TimerTrigger.FALLING_EDGE:
        triggered = not curr_high and prev_high
    elif trigger_mode == TimerTrigger.ANY_EDGE:
        triggered = curr_high != prev_high

    return triggered, curr_high


def timer_update(state: TimerState, config: TimerConfig, trigger: int, now_ms: int) -> int:
    """
    Update timer state and return output.

    Args:
        state: Timer state (modified)
        config: Timer configuration
        trigger: Trigger input value
        now_ms: Current time in milliseconds

    Returns:
        Timer output (0 or 1)
    """
    # Detect trigger edge
    triggered, new_last = _detect_edge(state.last_trigger, trigger, config.trigger_mode)
    state.last_trigger = new_last

    mode = config.mode

    # State machine
    if state.state == TimerStateEnum.IDLE:
        if triggered:
            state.state = TimerStateEnum.RUNNING
            state.start_time_ms = now_ms
            state.elapsed_ms = 0
            state.blink_phase = 0

            # Some modes start with output high
            if mode in (TimerMode.PULSE, TimerMode.ONESHOT, TimerMode.RETRIGGERABLE,
                        TimerMode.MONOSTABLE, TimerMode.BLINK):
                state.output = 1
            else:
                state.output = 0

    elif state.state == TimerStateEnum.RUNNING:
        state.elapsed_ms = now_ms - state.start_time_ms

        if mode == TimerMode.DELAY_ON:
            if state.elapsed_ms >= config.delay_ms:
                state.output = 1
                state.state = TimerStateEnum.EXPIRED
            else:
                state.output = 0

            # Check if trigger released
            if config.trigger_mode == TimerTrigger.LEVEL and not triggered:
                timer_reset(state)

        elif mode == TimerMode.DELAY_OFF:
            if not triggered:
                if state.elapsed_ms >= config.delay_ms:
                    state.output = 0
                    state.state = TimerStateEnum.EXPIRED
            else:
                state.output = 1
                state.start_time_ms = now_ms  # Reset delay while triggered

        elif mode == TimerMode.PULSE:
            if state.elapsed_ms >= config.delay_ms:
                state.output = 0
                state.state = TimerStateEnum.EXPIRED

        elif mode == TimerMode.BLINK:
            period = config.on_time_ms + config.off_time_ms
            if period > 0:
                cycle_time = state.elapsed_ms % period
                state.output = 1 if cycle_time < config.on_time_ms else 0

            # Check if trigger released
            if config.trigger_mode == TimerTrigger.LEVEL and not triggered:
                timer_reset(state)

        elif mode == TimerMode.ONESHOT:
            if state.elapsed_ms >= config.delay_ms:
                state.output = 0
                state.state = TimerStateEnum.EXPIRED

        elif mode == TimerMode.RETRIGGERABLE:
            if triggered:
                # Retrigger - restart timer
                state.start_time_ms = now_ms
                state.elapsed_ms = 0
                state.output = 1

            if state.elapsed_ms >= config.delay_ms:
                state.output = 0
                state.state = TimerStateEnum.EXPIRED

        elif mode == TimerMode.MONOSTABLE:
            if state.elapsed_ms >= config.delay_ms:
                state.output = 0
                state.state = TimerStateEnum.EXPIRED

    elif state.state == TimerStateEnum.EXPIRED:
        if config.auto_reset:
            state.state = TimerStateEnum.IDLE
            state.output = 0 if mode != TimerMode.DELAY_ON else 1

    return state.output


def timer_pause(state: TimerState, now_ms: int) -> None:
    """Pause running timer"""
    if state.state == TimerStateEnum.RUNNING:
        state.elapsed_ms = now_ms - state.start_time_ms
        state.state = TimerStateEnum.PAUSED


def timer_resume(state: TimerState, now_ms: int) -> None:
    """Resume paused timer"""
    if state.state == TimerStateEnum.PAUSED:
        state.start_time_ms = now_ms - state.elapsed_ms
        state.state = TimerStateEnum.RUNNING

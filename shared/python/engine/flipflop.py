"""
Logic Engine - Flip-Flops and Latches

Digital flip-flop and latch implementations with external state.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class FlipFlopState:
    """Generic flip-flop state"""
    q: int = 0
    last_clk: int = 0
    initialized: bool = False


def ff_init(state: Optional[FlipFlopState] = None) -> FlipFlopState:
    """Initialize flip-flop state"""
    if state is None:
        return FlipFlopState()
    state.q = 0
    state.last_clk = 0
    state.initialized = False
    return state


def ff_reset(state: FlipFlopState, q_value: int = 0) -> None:
    """Reset flip-flop to known state"""
    state.q = 1 if q_value != 0 else 0
    state.last_clk = 0
    state.initialized = True


# ============================================================================
# Edge Detection
# ============================================================================

def detect_rising_edge(last_state: int, current: int) -> Tuple[int, int]:
    """
    Detect rising edge.

    Args:
        last_state: Previous state value
        current: Current input value

    Returns:
        Tuple of (edge_detected, new_last_state)
    """
    curr_high = 1 if current != 0 else 0
    prev_high = 1 if last_state != 0 else 0
    return (1 if (curr_high and not prev_high) else 0), curr_high


def detect_falling_edge(last_state: int, current: int) -> Tuple[int, int]:
    """
    Detect falling edge.

    Args:
        last_state: Previous state value
        current: Current input value

    Returns:
        Tuple of (edge_detected, new_last_state)
    """
    curr_high = 1 if current != 0 else 0
    prev_high = 1 if last_state != 0 else 0
    return (1 if (not curr_high and prev_high) else 0), curr_high


def detect_any_edge(last_state: int, current: int) -> Tuple[int, int]:
    """
    Detect any edge (rising or falling).

    Args:
        last_state: Previous state value
        current: Current input value

    Returns:
        Tuple of (edge_detected, new_last_state)
    """
    curr_high = 1 if current != 0 else 0
    prev_high = 1 if last_state != 0 else 0
    return (1 if curr_high != prev_high else 0), curr_high


# ============================================================================
# SR Latch
# ============================================================================

def sr_latch_update(state: FlipFlopState, set_input: int, reset_input: int) -> int:
    """
    Update SR Latch (level-sensitive).

    Truth table:
        S=0, R=0: Q unchanged (hold)
        S=0, R=1: Q = 0 (reset)
        S=1, R=0: Q = 1 (set)
        S=1, R=1: Invalid (Q = 0 in this impl)

    Args:
        state: Flip-flop state (modified)
        set_input: Set input
        reset_input: Reset input

    Returns:
        Q output (0 or 1)
    """
    s = 1 if set_input != 0 else 0
    r = 1 if reset_input != 0 else 0

    if s and r:
        # Invalid state - reset wins
        state.q = 0
    elif s:
        state.q = 1
    elif r:
        state.q = 0
    # else: hold

    state.initialized = True
    return state.q


def sr_latch_priority(
    state: FlipFlopState,
    set_input: int,
    reset_input: int,
    reset_priority: bool = True
) -> int:
    """SR Latch with configurable priority when both active"""
    s = 1 if set_input != 0 else 0
    r = 1 if reset_input != 0 else 0

    if s and r:
        state.q = 0 if reset_priority else 1
    elif s:
        state.q = 1
    elif r:
        state.q = 0

    state.initialized = True
    return state.q


# ============================================================================
# D Flip-Flop
# ============================================================================

def d_flipflop_update(state: FlipFlopState, d: int, clk: int) -> int:
    """
    Update D Flip-Flop (edge-triggered).
    Captures D input on rising edge of clock.

    Args:
        state: Flip-flop state (modified)
        d: Data input
        clk: Clock input

    Returns:
        Q output
    """
    clk_high = 1 if clk != 0 else 0

    # Detect rising edge of clock
    if clk_high and not state.last_clk:
        state.q = 1 if d != 0 else 0

    state.last_clk = clk_high
    state.initialized = True
    return state.q


def d_latch_update(state: FlipFlopState, d: int, enable: int) -> int:
    """
    Update D Latch (level-sensitive).
    Transparent when enable is high, holds when low.

    Args:
        state: Flip-flop state (modified)
        d: Data input
        enable: Enable input

    Returns:
        Q output
    """
    if enable != 0:
        state.q = 1 if d != 0 else 0

    state.initialized = True
    return state.q


# ============================================================================
# T Flip-Flop
# ============================================================================

def t_flipflop_update(state: FlipFlopState, t: int, clk: int) -> int:
    """
    Update T Flip-Flop (Toggle).
    Toggles output on rising edge when T=1.

    Args:
        state: Flip-flop state (modified)
        t: Toggle input
        clk: Clock input

    Returns:
        Q output
    """
    clk_high = 1 if clk != 0 else 0

    if clk_high and not state.last_clk:
        if t != 0:
            state.q = 0 if state.q else 1

    state.last_clk = clk_high
    state.initialized = True
    return state.q


def toggle_update(state: FlipFlopState, trigger: int) -> int:
    """
    Simple toggle on rising edge.
    Toggles output on every rising edge of input.

    Args:
        state: Flip-flop state (modified)
        trigger: Trigger input

    Returns:
        Q output
    """
    trig_high = 1 if trigger != 0 else 0

    if trig_high and not state.last_clk:
        state.q = 0 if state.q else 1

    state.last_clk = trig_high
    state.initialized = True
    return state.q


# ============================================================================
# JK Flip-Flop
# ============================================================================

def jk_flipflop_update(state: FlipFlopState, j: int, k: int, clk: int) -> int:
    """
    Update JK Flip-Flop (edge-triggered).

    Truth table (on clock rising edge):
        J=0, K=0: Q unchanged (hold)
        J=0, K=1: Q = 0 (reset)
        J=1, K=0: Q = 1 (set)
        J=1, K=1: Q = !Q (toggle)

    Args:
        state: Flip-flop state (modified)
        j: J input
        k: K input
        clk: Clock input

    Returns:
        Q output
    """
    clk_high = 1 if clk != 0 else 0

    if clk_high and not state.last_clk:
        j_active = j != 0
        k_active = k != 0

        if j_active and k_active:
            state.q = 0 if state.q else 1  # Toggle
        elif j_active:
            state.q = 1
        elif k_active:
            state.q = 0

    state.last_clk = clk_high
    state.initialized = True
    return state.q


# ============================================================================
# Getters
# ============================================================================

def ff_get_q(state: FlipFlopState) -> int:
    """Get Q output"""
    return state.q


def ff_get_q_bar(state: FlipFlopState) -> int:
    """Get Q-bar output (inverted Q)"""
    return 0 if state.q else 1

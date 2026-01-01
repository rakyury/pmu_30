"""
Logic Engine - PID Controller

PID controller with external state management.
Uses fixed-point arithmetic with configurable scale.
"""

from dataclasses import dataclass
from typing import Optional


# Constants
PID_DEFAULT_SCALE = 1000
PID_MAX_INTEGRAL = 2**30  # Prevent overflow


@dataclass
class PIDConfig:
    """PID configuration"""
    kp: int = 1000          # Proportional gain (scaled)
    ki: int = 0             # Integral gain (scaled)
    kd: int = 0             # Derivative gain (scaled)
    scale: int = PID_DEFAULT_SCALE
    output_min: int = 0
    output_max: int = 10000
    integral_min: int = 0
    integral_max: int = 10000
    deadband: int = 0
    d_on_measurement: bool = True   # D term on measurement (reduces derivative kick)
    reset_integral_on_setpoint: bool = False


@dataclass
class PIDState:
    """PID state (externally managed)"""
    integral: int = 0
    prev_error: int = 0
    prev_measurement: int = 0
    prev_setpoint: int = 0
    output: int = 0
    initialized: bool = False


def _clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp value to range"""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


def _apply_deadband(error: int, deadband: int) -> int:
    """Apply deadband to error"""
    if deadband <= 0:
        return error

    if error > 0:
        if error <= deadband:
            return 0
        return error - deadband
    else:
        if error >= -deadband:
            return 0
        return error + deadband


def pid_init(state: Optional[PIDState] = None) -> PIDState:
    """Initialize PID state"""
    if state is None:
        return PIDState()

    state.integral = 0
    state.prev_error = 0
    state.prev_measurement = 0
    state.prev_setpoint = 0
    state.output = 0
    state.initialized = False
    return state


def pid_reset(state: PIDState) -> None:
    """Reset PID state"""
    state.integral = 0
    state.prev_error = 0
    state.prev_measurement = 0
    state.output = 0
    state.initialized = False


def pid_update(
    state: PIDState,
    config: PIDConfig,
    setpoint: int,
    measurement: int,
    dt_ms: int
) -> int:
    """
    Compute PID output.

    Args:
        state: PID state (modified)
        config: PID configuration
        setpoint: Desired value
        measurement: Current measured value
        dt_ms: Time delta in milliseconds

    Returns:
        PID output (clamped to output_min/max)
    """
    if dt_ms == 0:
        return state.output

    scale = config.scale if config.scale > 0 else PID_DEFAULT_SCALE

    # Check for setpoint change (for integral reset)
    if config.reset_integral_on_setpoint and state.initialized:
        if setpoint != state.prev_setpoint:
            state.integral = 0
    state.prev_setpoint = setpoint

    # Calculate error with deadband
    raw_error = setpoint - measurement
    error = _apply_deadband(raw_error, config.deadband)

    # Initialize on first run
    if not state.initialized:
        state.prev_error = error
        state.prev_measurement = measurement
        state.initialized = True

    # Calculate P term
    p_term = (config.kp * error) // scale

    # Calculate I term with anti-windup
    i_delta = (config.ki * error * dt_ms) // scale // 1000
    state.integral += i_delta

    # Anti-windup: clamp integral
    i_min = config.integral_min * scale
    i_max = config.integral_max * scale
    if i_min == 0 and i_max == 0:
        i_min = -PID_MAX_INTEGRAL
        i_max = PID_MAX_INTEGRAL

    state.integral = _clamp(state.integral, i_min, i_max)
    i_term = state.integral // scale

    # Calculate D term
    if config.d_on_measurement:
        d_input = measurement - state.prev_measurement
        d_term = -(config.kd * d_input * 1000) // (scale * dt_ms)
    else:
        d_input = error - state.prev_error
        d_term = (config.kd * d_input * 1000) // (scale * dt_ms)

    # Store for next iteration
    state.prev_error = error
    state.prev_measurement = measurement

    # Sum and clamp output
    output = p_term + i_term + d_term
    state.output = _clamp(output, config.output_min, config.output_max)

    return state.output


def pid_get_output(state: PIDState) -> int:
    """Get current PID output without updating"""
    return state.output


def pid_get_integral(state: PIDState) -> int:
    """Get current integral value"""
    return state.integral // PID_DEFAULT_SCALE


def pid_set_integral(state: PIDState, config: PIDConfig, value: int) -> None:
    """Set integral value (for bumpless transfer)"""
    scale = config.scale if config.scale > 0 else PID_DEFAULT_SCALE
    state.integral = value * scale

    # Apply limits
    i_min = config.integral_min * scale
    i_max = config.integral_max * scale
    if i_min != 0 or i_max != 0:
        state.integral = _clamp(state.integral, i_min, i_max)


def pid_default_config(
    kp: int,
    ki: int,
    kd: int,
    out_min: int,
    out_max: int
) -> PIDConfig:
    """Create default PID configuration"""
    return PIDConfig(
        kp=kp,
        ki=ki,
        kd=kd,
        scale=PID_DEFAULT_SCALE,
        output_min=out_min,
        output_max=out_max,
        integral_min=out_min,
        integral_max=out_max,
        deadband=0,
        d_on_measurement=True,
        reset_integral_on_setpoint=False,
    )

"""
Logic Engine - Signal Filters

Various signal filtering algorithms with external state management.
"""

from dataclasses import dataclass, field
from typing import List, Optional


FILTER_MAX_SAMPLES = 16
FILTER_ALPHA_SCALE = 256


# ============================================================================
# Simple Moving Average
# ============================================================================

@dataclass
class SMAConfig:
    """Simple Moving Average configuration"""
    window_size: int = 4


@dataclass
class SMAState:
    """Simple Moving Average state"""
    samples: List[int] = field(default_factory=list)
    index: int = 0
    count: int = 0
    total: int = 0


def sma_init(state: Optional[SMAState] = None) -> SMAState:
    """Initialize SMA state"""
    if state is None:
        return SMAState()
    state.samples = []
    state.index = 0
    state.count = 0
    state.total = 0
    return state


def sma_update(state: SMAState, config: SMAConfig, input_val: int) -> int:
    """Update SMA with new sample and return filtered value"""
    window = min(max(1, config.window_size), FILTER_MAX_SAMPLES)

    # Initialize samples list if needed
    if len(state.samples) < window:
        state.samples = [0] * window

    # If buffer is full, subtract oldest sample
    if state.count >= window:
        state.total -= state.samples[state.index]

    # Add new sample
    state.samples[state.index] = input_val
    state.total += input_val

    # Update index (circular)
    state.index = (state.index + 1) % window

    # Update count
    if state.count < window:
        state.count += 1

    return state.total // state.count if state.count > 0 else 0


# ============================================================================
# Exponential Moving Average
# ============================================================================

@dataclass
class EMAConfig:
    """Exponential Moving Average configuration"""
    alpha: int = 128  # 0-255, higher = more responsive


@dataclass
class EMAState:
    """Exponential Moving Average state"""
    value: int = 0
    initialized: bool = False


def ema_init(state: Optional[EMAState] = None) -> EMAState:
    """Initialize EMA state"""
    if state is None:
        return EMAState()
    state.value = 0
    state.initialized = False
    return state


def ema_update(state: EMAState, config: EMAConfig, input_val: int) -> int:
    """Update EMA with new sample and return filtered value"""
    if not state.initialized:
        state.value = input_val
        state.initialized = True
        return input_val

    alpha = max(1, min(255, config.alpha))
    result = (alpha * input_val + (FILTER_ALPHA_SCALE - alpha) * state.value) // FILTER_ALPHA_SCALE
    state.value = result
    return state.value


# ============================================================================
# Low-Pass Filter
# ============================================================================

@dataclass
class LPFConfig:
    """Low-Pass Filter configuration"""
    time_constant_ms: int = 100
    scale: int = 1000


@dataclass
class LPFState:
    """Low-Pass Filter state"""
    value: int = 0
    initialized: bool = False


def lpf_init(state: Optional[LPFState] = None) -> LPFState:
    """Initialize LPF state"""
    if state is None:
        return LPFState()
    state.value = 0
    state.initialized = False
    return state


def lpf_update(state: LPFState, config: LPFConfig, input_val: int, dt_ms: int) -> int:
    """Update LPF with new sample and return filtered value"""
    if dt_ms == 0:
        return state.value // config.scale if state.initialized else input_val

    scale = config.scale if config.scale > 0 else 1000

    if not state.initialized:
        state.value = input_val * scale
        state.initialized = True
        return input_val

    tau = max(1, config.time_constant_ms)
    scaled_input = input_val * scale
    denom = tau + dt_ms

    state.value = (dt_ms * scaled_input + tau * state.value) // denom
    return state.value // scale


# ============================================================================
# Median Filter
# ============================================================================

@dataclass
class MedianConfig:
    """Median Filter configuration"""
    window_size: int = 3


@dataclass
class MedianState:
    """Median Filter state"""
    samples: List[int] = field(default_factory=list)
    index: int = 0
    count: int = 0


def median_init(state: Optional[MedianState] = None) -> MedianState:
    """Initialize Median state"""
    if state is None:
        return MedianState()
    state.samples = []
    state.index = 0
    state.count = 0
    return state


def _find_median(samples: List[int], count: int) -> int:
    """Find median of samples"""
    if count == 0:
        return 0
    if count == 1:
        return samples[0]

    # Sort copy of samples
    sorted_samples = sorted(samples[:count])
    mid = count // 2

    if count % 2 == 1:
        return sorted_samples[mid]
    else:
        return (sorted_samples[mid - 1] + sorted_samples[mid]) // 2


def median_update(state: MedianState, config: MedianConfig, input_val: int) -> int:
    """Update Median filter with new sample and return filtered value"""
    window = min(max(3, config.window_size), FILTER_MAX_SAMPLES)

    # Initialize samples list if needed
    if len(state.samples) < window:
        state.samples = [0] * window

    # Add new sample
    state.samples[state.index] = input_val
    state.index = (state.index + 1) % window

    if state.count < window:
        state.count += 1

    return _find_median(state.samples, state.count)


# ============================================================================
# Rate Limiter
# ============================================================================

@dataclass
class RateLimiterConfig:
    """Rate Limiter configuration"""
    rise_rate: int = 1000   # Max rise per second
    fall_rate: int = 1000   # Max fall per second


@dataclass
class RateLimiterState:
    """Rate Limiter state"""
    value: int = 0
    initialized: bool = False


def rate_limiter_init(state: Optional[RateLimiterState] = None) -> RateLimiterState:
    """Initialize Rate Limiter state"""
    if state is None:
        return RateLimiterState()
    state.value = 0
    state.initialized = False
    return state


def rate_limiter_update(
    state: RateLimiterState,
    config: RateLimiterConfig,
    target: int,
    dt_ms: int
) -> int:
    """Update Rate Limiter and return rate-limited value"""
    if not state.initialized:
        state.value = target
        state.initialized = True
        return target

    if dt_ms == 0:
        return state.value

    diff = target - state.value

    if diff > 0:
        max_rise = max(1, (config.rise_rate * dt_ms) // 1000)
        if diff > max_rise:
            state.value += max_rise
        else:
            state.value = target
    elif diff < 0:
        max_fall = max(1, (config.fall_rate * dt_ms) // 1000)
        if -diff > max_fall:
            state.value -= max_fall
        else:
            state.value = target

    return state.value


# ============================================================================
# Debounce Filter
# ============================================================================

@dataclass
class DebounceConfig:
    """Debounce Filter configuration"""
    debounce_ms: int = 50
    hysteresis: int = 0


@dataclass
class DebounceState:
    """Debounce Filter state"""
    stable_value: int = 0
    pending_value: int = 0
    pending_time_ms: int = 0
    initialized: bool = False


def debounce_init(state: Optional[DebounceState] = None) -> DebounceState:
    """Initialize Debounce state"""
    if state is None:
        return DebounceState()
    state.stable_value = 0
    state.pending_value = 0
    state.pending_time_ms = 0
    state.initialized = False
    return state


def debounce_update(
    state: DebounceState,
    config: DebounceConfig,
    input_val: int,
    dt_ms: int
) -> int:
    """Update Debounce filter and return debounced value"""
    if not state.initialized:
        state.stable_value = input_val
        state.pending_value = input_val
        state.pending_time_ms = 0
        state.initialized = True
        return input_val

    # Check if input has changed significantly
    diff = abs(input_val - state.stable_value)
    threshold = config.hysteresis

    input_changed = diff > threshold if threshold > 0 else input_val != state.stable_value

    if not input_changed:
        # Input matches stable value, reset pending
        state.pending_value = state.stable_value
        state.pending_time_ms = 0
        return state.stable_value

    # Input is different from stable value
    if input_val == state.pending_value:
        # Same as pending, accumulate time
        state.pending_time_ms += dt_ms

        if state.pending_time_ms >= config.debounce_ms:
            # Debounce period elapsed, accept new value
            state.stable_value = input_val
            state.pending_time_ms = 0
    else:
        # New pending value
        state.pending_value = input_val
        state.pending_time_ms = dt_ms

    return state.stable_value

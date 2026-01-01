"""
Logic Engine - Python Port

Pure function implementations of logic operations that can run
on desktop or be used for testing/simulation without hardware.

All functions are designed to match the C implementation exactly,
using the same algorithms and data types where applicable.

Modules:
    logic      - Boolean logic operations (AND, OR, XOR, comparisons)
    math_ops   - Math operations (Add, Mul, Map, Clamp, etc.)
    timer      - Timer functions (delay, pulse, blink)
    table      - 2D/3D lookup tables with interpolation
    switch     - Switch/selector functions
    counter    - Counter with inc/dec/reset
    pid        - PID controller
    filter     - Signal filters (SMA, EMA, LPF, median, etc.)
    flipflop   - Flip-flops and latches (SR, D, T, JK)
    hysteresis - Hysteresis comparator / Schmitt trigger
"""

from .logic import (
    LogicOp,
    logic_and,
    logic_or,
    logic_xor,
    logic_nand,
    logic_nor,
    logic_not,
    logic_gt,
    logic_gte,
    logic_lt,
    logic_lte,
    logic_eq,
    logic_neq,
    logic_in_range,
    logic_outside_range,
    logic_evaluate,
)

from .math_ops import (
    MathOp,
    math_add,
    math_sub,
    math_mul,
    math_div,
    math_mod,
    math_abs,
    math_neg,
    math_min,
    math_max,
    math_avg,
    math_clamp,
    math_map,
    math_scale,
    math_lerp,
    math_evaluate,
)

from .timer import (
    TimerMode,
    TimerTrigger,
    TimerStateEnum,
    TimerConfig,
    TimerState,
    timer_init,
    timer_reset,
    timer_update,
)

from .table import (
    Table2D,
    Table3D,
    table2d_lookup,
    table3d_lookup,
)

from .switch import (
    SwitchCase,
    RangeCase,
    switch_select,
    switch_case,
    switch_range_case,
    switch_mux,
    switch_priority,
    switch_ternary,
)

from .counter import (
    CounterConfig,
    CounterState,
    counter_init,
    counter_reset,
    counter_update,
    counter_increment,
    counter_decrement,
)

from .pid import (
    PIDConfig,
    PIDState,
    pid_init,
    pid_reset,
    pid_update,
    pid_default_config,
)

from .filter import (
    SMAConfig,
    SMAState,
    EMAConfig,
    EMAState,
    LPFConfig,
    LPFState,
    MedianConfig,
    MedianState,
    RateLimiterConfig,
    RateLimiterState,
    DebounceConfig,
    DebounceState,
    sma_init,
    sma_update,
    ema_init,
    ema_update,
    lpf_init,
    lpf_update,
    median_init,
    median_update,
    rate_limiter_init,
    rate_limiter_update,
    debounce_init,
    debounce_update,
)

from .flipflop import (
    FlipFlopState,
    ff_init,
    sr_latch_update,
    d_flipflop_update,
    d_latch_update,
    t_flipflop_update,
    toggle_update,
    jk_flipflop_update,
    detect_rising_edge,
    detect_falling_edge,
    detect_any_edge,
)

from .hysteresis import (
    HysteresisConfig,
    HysteresisState,
    WindowConfig,
    WindowState,
    MultiLevelConfig,
    MultiLevelState,
    hysteresis_init,
    hysteresis_update,
    window_init,
    window_update,
    multilevel_init,
    multilevel_update,
    compare_ge,
    compare_gt,
    compare_in_range,
    deadband,
)

__all__ = [
    # Logic
    "LogicOp",
    "logic_and", "logic_or", "logic_xor", "logic_nand", "logic_nor", "logic_not",
    "logic_gt", "logic_gte", "logic_lt", "logic_lte", "logic_eq", "logic_neq",
    "logic_in_range", "logic_outside_range", "logic_evaluate",
    # Math
    "MathOp",
    "math_add", "math_sub", "math_mul", "math_div", "math_mod",
    "math_abs", "math_neg", "math_min", "math_max", "math_avg",
    "math_clamp", "math_map", "math_scale", "math_lerp", "math_evaluate",
    # Timer
    "TimerMode", "TimerTrigger", "TimerStateEnum",
    "TimerConfig", "TimerState",
    "timer_init", "timer_reset", "timer_update",
    # Table
    "Table2D", "Table3D",
    "table2d_lookup", "table3d_lookup",
    # Switch
    "SwitchCase", "RangeCase",
    "switch_select", "switch_case", "switch_range_case",
    "switch_mux", "switch_priority", "switch_ternary",
    # Counter
    "CounterConfig", "CounterState",
    "counter_init", "counter_reset", "counter_update",
    "counter_increment", "counter_decrement",
    # PID
    "PIDConfig", "PIDState",
    "pid_init", "pid_reset", "pid_update", "pid_default_config",
    # Filter
    "SMAConfig", "SMAState", "EMAConfig", "EMAState",
    "LPFConfig", "LPFState", "MedianConfig", "MedianState",
    "RateLimiterConfig", "RateLimiterState", "DebounceConfig", "DebounceState",
    "sma_init", "sma_update", "ema_init", "ema_update",
    "lpf_init", "lpf_update", "median_init", "median_update",
    "rate_limiter_init", "rate_limiter_update", "debounce_init", "debounce_update",
    # FlipFlop
    "FlipFlopState",
    "ff_init", "sr_latch_update", "d_flipflop_update", "d_latch_update",
    "t_flipflop_update", "toggle_update", "jk_flipflop_update",
    "detect_rising_edge", "detect_falling_edge", "detect_any_edge",
    # Hysteresis
    "HysteresisConfig", "HysteresisState",
    "WindowConfig", "WindowState",
    "MultiLevelConfig", "MultiLevelState",
    "hysteresis_init", "hysteresis_update",
    "window_init", "window_update",
    "multilevel_init", "multilevel_update",
    "compare_ge", "compare_gt", "compare_in_range", "deadband",
]

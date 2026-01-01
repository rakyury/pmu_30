"""
Channel Executor - Bridge between Channel System and Logic Engine

The executor is the bridge between the channel system and the Logic Engine.
It reads channel values, feeds them to pure functions, and writes results.

Design:
- Channel Manager owns channel definitions and current values
- Executor processes channels using Logic Engine functions
- State for stateful functions (Timer, PID, etc.) is stored per-channel
- No hardware access - works with channel values only

Version: 1.0
Date: January 2026
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Any

# Import Logic Engine modules
from .engine.logic import *
from .engine.math_ops import *
from .engine.timer import *
from .engine.counter import *
from .engine.pid import *
from .engine.filter import *
from .engine.table import *
from .engine.switch import *
from .engine.hysteresis import *
from .engine.flipflop import *

# Import channel config types (includes ChannelType)
from .channel_config import *

# =============================================================================
# Constants
# =============================================================================

EXEC_MAX_CHANNELS = 256
EXEC_MAX_INPUTS = 8
CH_REF_NONE = 0xFFFF

# ChannelType is imported from channel_config


# =============================================================================
# Channel State Union (Python equivalent)
# =============================================================================

@dataclass
class ChannelState:
    """
    Channel runtime state container.
    Holds state for any stateful channel type.
    """
    timer: Optional[TimerState] = None
    counter: Optional[CounterState] = None
    pid: Optional[PIDState] = None
    sma: Optional[SMAState] = None
    ema: Optional[EMAState] = None
    lpf: Optional[LPFState] = None
    median: Optional[MedianState] = None
    rate_limiter: Optional[RateLimiterState] = None
    debounce: Optional[DebounceState] = None
    flipflop: Optional[FlipFlopState] = None
    hysteresis: Optional[HysteresisState] = None
    window: Optional[WindowState] = None
    multilevel: Optional[MultiLevelState] = None


# =============================================================================
# Channel Runtime
# =============================================================================

@dataclass
class ChannelRuntime:
    """
    Runtime channel data.
    """
    id: int = 0
    type: ChannelType = ChannelType.NONE
    flags: int = 0
    value: int = 0
    prev_value: int = 0
    config: Any = None
    state: ChannelState = field(default_factory=ChannelState)


# =============================================================================
# Executor Context
# =============================================================================

# Type aliases for callbacks
GetValueFunc = Callable[[int], int]  # channel_id -> value
SetValueFunc = Callable[[int, int], None]  # channel_id, value -> None


@dataclass
class ExecContext:
    """
    Executor context with value provider callbacks.
    """
    get_value: Optional[GetValueFunc] = None
    set_value: Optional[SetValueFunc] = None
    user_data: Any = None
    now_ms: int = 0
    last_ms: int = 0
    dt_ms: int = 0


# =============================================================================
# Executor Class
# =============================================================================

class ChannelExecutor:
    """
    Channel Executor - connects channel system to Logic Engine.

    Example usage:
        executor = ChannelExecutor()
        executor.init(get_value_func, set_value_func)

        # Each cycle:
        executor.update_time(current_time_ms)
        for channel in channels:
            new_value = executor.process_channel(channel)
    """

    def __init__(self):
        self.ctx = ExecContext()

    def init(self,
             get_value: GetValueFunc,
             set_value: SetValueFunc,
             user_data: Any = None):
        """
        Initialize executor with value provider callbacks.

        Args:
            get_value: Function to get channel value by ID
            set_value: Function to set channel value by ID
            user_data: Optional user data
        """
        self.ctx = ExecContext(
            get_value=get_value,
            set_value=set_value,
            user_data=user_data,
            now_ms=0,
            last_ms=0,
            dt_ms=0
        )

    def update_time(self, now_ms: int):
        """
        Update executor timestamp and calculate delta.

        Args:
            now_ms: Current time in milliseconds
        """
        self.ctx.dt_ms = (now_ms - self.ctx.last_ms) if self.ctx.last_ms > 0 else 0
        self.ctx.last_ms = self.ctx.now_ms
        self.ctx.now_ms = now_ms

    # =========================================================================
    # Helper: Get Input Values
    # =========================================================================

    def _get_input(self, channel_id: int) -> int:
        """Get value of a single input channel."""
        if self.ctx.get_value is None or channel_id == CH_REF_NONE:
            return 0
        return self.ctx.get_value(channel_id)

    def _get_inputs(self, input_ids: list, count: int) -> list:
        """Get values of multiple input channels."""
        values = []
        for i in range(min(count, EXEC_MAX_INPUTS)):
            if i < len(input_ids):
                values.append(self._get_input(input_ids[i]))
            else:
                values.append(0)
        return values

    # =========================================================================
    # Type-Specific Execution Functions
    # =========================================================================

    def exec_logic(self, config: CfgLogic) -> int:
        """Execute logic channel."""
        inputs = self._get_inputs(config.inputs, config.input_count)

        op = config.operation

        if op == LogicOp.AND:
            result = logic_and(inputs)
        elif op == LogicOp.OR:
            result = logic_or(inputs)
        elif op == LogicOp.XOR:
            result = logic_xor(inputs)
        elif op == LogicOp.NAND:
            result = logic_nand(inputs)
        elif op == LogicOp.NOR:
            result = logic_nor(inputs)
        elif op == LogicOp.NOT:
            result = logic_not(inputs[0] if inputs else 0)
        elif op == LogicOp.GT:
            result = logic_gt(inputs[0] if inputs else 0, config.compare_value)
        elif op == LogicOp.GTE:
            result = logic_gte(inputs[0] if inputs else 0, config.compare_value)
        elif op == LogicOp.LT:
            result = logic_lt(inputs[0] if inputs else 0, config.compare_value)
        elif op == LogicOp.LTE:
            result = logic_lte(inputs[0] if inputs else 0, config.compare_value)
        elif op == LogicOp.EQ:
            result = logic_eq(inputs[0] if inputs else 0, config.compare_value)
        elif op == LogicOp.NEQ:
            result = logic_neq(inputs[0] if inputs else 0, config.compare_value)
        elif op == LogicOp.IN_RANGE:
            result = logic_in_range(
                inputs[0] if len(inputs) > 0 else 0,
                inputs[1] if len(inputs) > 1 else 0,
                config.compare_value
            )
        else:
            result = 0

        return int(not result) if config.invert_output else int(result)

    def exec_math(self, config: CfgMath) -> int:
        """Execute math channel."""
        inputs = self._get_inputs(config.inputs, config.input_count)

        op = config.operation
        a = inputs[0] if len(inputs) > 0 else 0
        b = inputs[1] if len(inputs) > 1 else 0

        if op == MathOp.ADD:
            result = math_add(a, b)
        elif op == MathOp.SUB:
            result = math_sub(a, b)
        elif op == MathOp.MUL:
            result = math_mul(a, b)
        elif op == MathOp.DIV:
            result = math_div(a, b)
        elif op == MathOp.MOD:
            result = math_mod(a, b)
        elif op == MathOp.ABS:
            result = math_abs(a)
        elif op == MathOp.NEG:
            result = math_neg(a)
        elif op == MathOp.MIN:
            result = math_min(inputs)
        elif op == MathOp.MAX:
            result = math_max(inputs)
        elif op == MathOp.AVG:
            result = math_avg(inputs)
        elif op == MathOp.CLAMP:
            result = math_clamp(a, config.min_value, config.max_value)
        elif op == MathOp.MAP:
            # Map from input range to output range
            c = inputs[2] if len(inputs) > 2 else 0
            result = math_map(a, b, c, config.min_value, config.max_value)
        elif op == MathOp.SCALE:
            result = math_scale(a, config.scale_num, config.scale_den)
        else:
            result = a

        # Apply output clamping
        result = math_clamp(result, config.min_value, config.max_value)

        # Apply output scaling
        if config.scale_den != 0 and config.scale_den != 1:
            result = math_scale(result, config.scale_num, config.scale_den)

        return result

    def exec_timer(self, state: ChannelState, config: CfgTimer) -> int:
        """Execute timer channel."""
        trigger = self._get_input(config.trigger_id)

        # Initialize state if needed
        if state.timer is None:
            state.timer = TimerState()

        timer_cfg = TimerConfig(
            mode=TimerMode(config.mode),
            trigger_mode=TimerTrigger(config.trigger_mode),
            delay_ms=config.delay_ms,
            on_time_ms=config.on_time_ms,
            off_time_ms=config.off_time_ms,
            auto_reset=config.auto_reset
        )

        return timer_update(state.timer, timer_cfg, trigger, self.ctx.now_ms)

    def exec_pid(self, state: ChannelState, config: CfgPid) -> int:
        """Execute PID channel."""
        setpoint = self._get_input(config.setpoint_id)
        feedback = self._get_input(config.feedback_id)

        # Initialize state if needed
        if state.pid is None:
            state.pid = PIDState()

        pid_cfg = PIDConfig(
            kp=config.kp,
            ki=config.ki,
            kd=config.kd,
            scale=PID_DEFAULT_SCALE,
            output_min=config.output_min,
            output_max=config.output_max,
            integral_min=config.integral_min,
            integral_max=config.integral_max,
            deadband=config.deadband,
            d_on_measurement=config.d_on_measurement,
            reset_integral_on_setpoint=False
        )

        return pid_update(state.pid, pid_cfg, setpoint, feedback, self.ctx.dt_ms)

    def exec_filter(self, state: ChannelState, config: CfgFilter) -> int:
        """Execute filter channel."""
        input_val = self._get_input(config.input_id)
        filter_type = config.filter_type

        if filter_type == FilterType.SMA:
            if state.sma is None:
                state.sma = SMAState()
            cfg = SMAConfig(window_size=config.window_size)
            return sma_update(state.sma, cfg, input_val)

        elif filter_type == FilterType.EMA:
            if state.ema is None:
                state.ema = EMAState()
            cfg = EMAConfig(alpha=config.alpha)
            return ema_update(state.ema, cfg, input_val)

        elif filter_type == FilterType.LOWPASS:
            if state.lpf is None:
                state.lpf = LPFState()
            cfg = LPFConfig(time_constant_ms=config.time_constant_ms, scale=1000)
            return lpf_update(state.lpf, cfg, input_val, self.ctx.dt_ms)

        elif filter_type == FilterType.MEDIAN:
            if state.median is None:
                state.median = MedianState()
            cfg = MedianConfig(window_size=config.window_size)
            return median_update(state.median, cfg, input_val)

        elif filter_type == FilterType.RATE_LIMIT:
            if state.rate_limiter is None:
                state.rate_limiter = RateLimiterState()
            cfg = RateLimiterConfig(
                rise_rate=config.time_constant_ms,  # Reuse field
                fall_rate=config.time_constant_ms
            )
            return rate_limiter_update(state.rate_limiter, cfg, input_val, self.ctx.dt_ms)

        elif filter_type == FilterType.DEBOUNCE:
            if state.debounce is None:
                state.debounce = DebounceState()
            cfg = DebounceConfig(
                debounce_ms=config.time_constant_ms,
                hysteresis=0
            )
            return debounce_update(state.debounce, cfg, input_val, self.ctx.dt_ms)

        else:
            return input_val

    def exec_table2d(self, config: CfgTable2D) -> int:
        """Execute 2D table channel."""
        input_val = self._get_input(config.input_id)

        # Build table
        table = Table2D(
            size=config.point_count,
            x_values=list(config.x_values[:config.point_count]),
            y_values=list(config.y_values[:config.point_count])
        )

        return table2d_lookup(table, input_val)

    def exec_switch(self, config: CfgSwitch) -> int:
        """Execute switch channel."""
        selector = self._get_input(config.selector_id)

        # Mode 2: index-based selection
        if config.mode == 2:
            if 0 <= selector < config.case_count:
                return config.cases[selector].result
            return config.default_value

        # Mode 0: value match, Mode 1: range match
        for i in range(config.case_count):
            case = config.cases[i]
            if config.mode == 0:
                # Exact match
                if selector == case.match_value:
                    return case.result
            else:
                # Range match
                if case.match_value <= selector <= case.max_value:
                    return case.result

        return config.default_value

    def exec_counter(self, state: ChannelState, config: CfgCounter) -> int:
        """Execute counter channel."""
        inc_trigger = self._get_input(config.inc_trigger_id)
        dec_trigger = self._get_input(config.dec_trigger_id)
        reset_trigger = self._get_input(config.reset_trigger_id)

        # Initialize state if needed
        if state.counter is None:
            state.counter = CounterState()

        counter_cfg = CounterConfig(
            initial_value=config.initial_value,
            min_value=config.min_value,
            max_value=config.max_value,
            step=config.step,
            wrap=config.wrap,
            edge_mode=config.edge_mode
        )

        return counter_update(state.counter, counter_cfg, inc_trigger, dec_trigger, reset_trigger)

    def exec_hysteresis(self, state: ChannelState, config: CfgHysteresis) -> int:
        """Execute hysteresis channel."""
        input_val = self._get_input(config.input_id)

        # Initialize state if needed
        if state.hysteresis is None:
            state.hysteresis = HysteresisState()

        hyst_cfg = HysteresisConfig(
            threshold_high=config.threshold_high,
            threshold_low=config.threshold_low,
            invert=config.invert
        )

        return hysteresis_update(state.hysteresis, hyst_cfg, input_val)

    # =========================================================================
    # Main Processing Function
    # =========================================================================

    def process_channel(self, runtime: ChannelRuntime) -> int:
        """
        Process a single channel.

        Args:
            runtime: Channel runtime data

        Returns:
            New channel value
        """
        runtime.prev_value = runtime.value
        result = runtime.value

        ch_type = runtime.type
        config = runtime.config
        state = runtime.state

        if ch_type == ChannelType.LOGIC:
            if config:
                result = self.exec_logic(config)

        elif ch_type == ChannelType.MATH:
            if config:
                result = self.exec_math(config)

        elif ch_type == ChannelType.TIMER:
            if config:
                result = self.exec_timer(state, config)

        elif ch_type == ChannelType.PID:
            if config:
                result = self.exec_pid(state, config)

        elif ch_type == ChannelType.FILTER:
            if config:
                result = self.exec_filter(state, config)

        elif ch_type == ChannelType.TABLE_2D:
            if config:
                result = self.exec_table2d(config)

        elif ch_type == ChannelType.SWITCH:
            if config:
                result = self.exec_switch(config)

        elif ch_type == ChannelType.COUNTER:
            if config:
                result = self.exec_counter(state, config)

        elif ch_type == ChannelType.HYSTERESIS:
            if config:
                result = self.exec_hysteresis(state, config)

        elif ch_type == ChannelType.NUMBER:
            if config:
                if not config.readonly:
                    result = runtime.value
                else:
                    result = config.value

        # Input/output channels are handled by hardware layer

        runtime.value = result
        return result

    # =========================================================================
    # State Initialization
    # =========================================================================

    @staticmethod
    def init_channel_state(runtime: ChannelRuntime, ch_type: ChannelType):
        """
        Initialize channel runtime state.

        Args:
            runtime: Channel runtime to initialize
            ch_type: Channel type
        """
        runtime.state = ChannelState()
        runtime.type = ch_type

        if ch_type == ChannelType.TIMER:
            runtime.state.timer = TimerState()
        elif ch_type == ChannelType.PID:
            runtime.state.pid = PIDState()
        elif ch_type == ChannelType.COUNTER:
            runtime.state.counter = CounterState()
        # Filter states are created on first use based on filter_type

    @staticmethod
    def reset_channel_state(runtime: ChannelRuntime):
        """
        Reset channel state to defaults.

        Args:
            runtime: Channel runtime to reset
        """
        ch_type = runtime.type

        if ch_type == ChannelType.TIMER:
            if runtime.state.timer:
                timer_reset(runtime.state.timer)
        elif ch_type == ChannelType.PID:
            if runtime.state.pid:
                pid_reset(runtime.state.pid)
        elif ch_type == ChannelType.FILTER:
            runtime.state = ChannelState()

        runtime.value = 0
        runtime.prev_value = 0


# =============================================================================
# Convenience Functions (matching C API)
# =============================================================================

def exec_init(ctx: ExecContext,
              get_value: GetValueFunc,
              set_value: SetValueFunc,
              user_data: Any = None):
    """Initialize executor context."""
    ctx.get_value = get_value
    ctx.set_value = set_value
    ctx.user_data = user_data
    ctx.now_ms = 0
    ctx.last_ms = 0
    ctx.dt_ms = 0


def exec_update_time(ctx: ExecContext, now_ms: int):
    """Update executor timestamp and calculate delta."""
    ctx.dt_ms = (now_ms - ctx.last_ms) if ctx.last_ms > 0 else 0
    ctx.last_ms = ctx.now_ms
    ctx.now_ms = now_ms

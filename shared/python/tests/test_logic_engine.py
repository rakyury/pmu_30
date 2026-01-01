"""
Logic Engine Integration Tests

Tests all Logic Engine modules and Channel Executor integration.
"""

import sys
import os
import unittest
from typing import Dict

# Add shared/python to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import Logic Engine modules directly (not as package)
from engine.logic import *
from engine.math_ops import *
from engine.timer import *
from engine.counter import *
from engine.pid import *
from engine.filter import *
from engine.table import *
from engine.switch import *
from engine.hysteresis import *
from engine.flipflop import *

# Import Channel Config enums and dataclasses
from channel_config import ChannelType, CfgLogic, CfgMath, CfgTimer, CfgFilter

# Import Channel Executor - need to handle relative import issue
# by temporarily modifying channel_executor.py imports
import importlib.util
spec = importlib.util.spec_from_file_location(
    "channel_executor_test",
    os.path.join(_parent_dir, "channel_executor.py")
)

# Create a mock module loader that patches imports
import types

# Load channel_executor with absolute imports
_ce_source = open(os.path.join(_parent_dir, "channel_executor.py")).read()
_ce_source = _ce_source.replace("from .engine.", "from engine.")
_ce_source = _ce_source.replace("from .channel_config", "from channel_config")

_ce_module = types.ModuleType("channel_executor_test")
exec(_ce_source, _ce_module.__dict__)

ChannelExecutor = _ce_module.ChannelExecutor
ChannelRuntime = _ce_module.ChannelRuntime
ChannelState = _ce_module.ChannelState
EXEC_MAX_INPUTS = _ce_module.EXEC_MAX_INPUTS
CH_REF_NONE = _ce_module.CH_REF_NONE


class TestLogicFunctions(unittest.TestCase):
    """Test pure logic functions."""

    def test_and(self):
        self.assertEqual(logic_and([1, 1, 1]), 1)
        self.assertEqual(logic_and([1, 0, 1]), 0)
        self.assertEqual(logic_and([0, 0, 0]), 0)
        # Empty list returns 0 (false) for safety
        self.assertEqual(logic_and([]), 0)

    def test_or(self):
        self.assertEqual(logic_or([0, 0, 0]), 0)
        self.assertEqual(logic_or([1, 0, 0]), 1)
        self.assertEqual(logic_or([1, 1, 1]), 1)
        # Empty list returns 0 (false) for safety
        self.assertEqual(logic_or([]), 0)

    def test_xor(self):
        self.assertEqual(logic_xor([1, 0]), 1)
        self.assertEqual(logic_xor([1, 1]), 0)
        self.assertEqual(logic_xor([0, 0]), 0)
        self.assertEqual(logic_xor([1, 1, 1]), 1)  # Odd number of 1s

    def test_comparisons(self):
        self.assertEqual(logic_gt(10, 5), 1)
        self.assertEqual(logic_gt(5, 10), 0)
        self.assertEqual(logic_gte(10, 10), 1)
        self.assertEqual(logic_lt(5, 10), 1)
        self.assertEqual(logic_lte(10, 10), 1)
        self.assertEqual(logic_eq(10, 10), 1)
        self.assertEqual(logic_neq(10, 5), 1)

    def test_in_range(self):
        self.assertEqual(logic_in_range(5, 0, 10), 1)  # 5 in [0, 10]
        self.assertEqual(logic_in_range(15, 0, 10), 0)  # 15 not in [0, 10]
        self.assertEqual(logic_in_range(0, 0, 10), 1)  # Edge: 0 in [0, 10]
        self.assertEqual(logic_in_range(10, 0, 10), 1)  # Edge: 10 in [0, 10]


class TestMathFunctions(unittest.TestCase):
    """Test pure math functions."""

    def test_basic_ops(self):
        self.assertEqual(math_add(10, 5), 15)
        self.assertEqual(math_sub(10, 5), 5)
        self.assertEqual(math_mul(10, 5), 50)
        self.assertEqual(math_div(10, 5), 2)
        # Division by zero returns INT32_MAX (saturating behavior)
        self.assertEqual(math_div(10, 0), 0x7FFFFFFF)
        self.assertEqual(math_div(-10, 0), -0x80000000)
        self.assertEqual(math_div(0, 0), 0)
        self.assertEqual(math_mod(10, 3), 1)

    def test_clamp(self):
        self.assertEqual(math_clamp(5, 0, 10), 5)
        self.assertEqual(math_clamp(-5, 0, 10), 0)
        self.assertEqual(math_clamp(15, 0, 10), 10)

    def test_map(self):
        # Map 50 from [0, 100] to [0, 1000]
        result = math_map(50, 0, 100, 0, 1000)
        self.assertEqual(result, 500)

        # Map 0 from [0, 100] to [0, 1000]
        result = math_map(0, 0, 100, 0, 1000)
        self.assertEqual(result, 0)

    def test_scale(self):
        # Scale 100 by 3/2
        result = math_scale(100, 3, 2)
        self.assertEqual(result, 150)

    def test_min_max_avg(self):
        values = [10, 5, 20, 15]
        self.assertEqual(math_min(values), 5)
        self.assertEqual(math_max(values), 20)
        self.assertEqual(math_avg(values), 12)  # (10+5+20+15)/4 = 12.5 -> 12


class TestTimerFunctions(unittest.TestCase):
    """Test timer state machine."""

    def test_delay_on(self):
        """Test delay-on timer: output turns on after delay when input is high."""
        state = TimerState()
        config = TimerConfig(
            mode=TimerMode.DELAY_ON,
            trigger_mode=TimerTrigger.LEVEL,
            delay_ms=100
        )

        # Initially off
        result = timer_update(state, config, 0, 0)
        self.assertEqual(result, 0)

        # Input goes high at t=0
        result = timer_update(state, config, 1, 0)
        self.assertEqual(result, 0)  # Still off, waiting for delay

        # t=50ms (not yet)
        result = timer_update(state, config, 1, 50)
        self.assertEqual(result, 0)

        # t=100ms (delay passed)
        result = timer_update(state, config, 1, 100)
        self.assertEqual(result, 1)  # Now on (EXPIRED state)

        # Once expired, output stays high until reset
        result = timer_update(state, config, 0, 150)
        self.assertEqual(result, 1)  # Stays on until explicit reset

        # Test auto-reset behavior
        state2 = TimerState()
        config2 = TimerConfig(
            mode=TimerMode.DELAY_ON,
            trigger_mode=TimerTrigger.LEVEL,
            delay_ms=100,
            auto_reset=True
        )

        timer_update(state2, config2, 1, 0)
        timer_update(state2, config2, 1, 100)  # Expires
        self.assertEqual(state2.output, 1)

    def test_delay_on_abort(self):
        """Test delay-on timer aborts if trigger released during delay."""
        state = TimerState()
        config = TimerConfig(
            mode=TimerMode.DELAY_ON,
            trigger_mode=TimerTrigger.LEVEL,
            delay_ms=100
        )

        # Trigger high at t=0
        timer_update(state, config, 1, 0)
        timer_update(state, config, 1, 50)  # Still waiting

        # Trigger released before delay completes
        result = timer_update(state, config, 0, 60)
        self.assertEqual(result, 0)  # Timer reset, output off

    def test_pulse(self):
        """Test pulse timer: outputs pulse for duration after trigger."""
        state = TimerState()
        config = TimerConfig(
            mode=TimerMode.PULSE,
            trigger_mode=TimerTrigger.RISING_EDGE,
            delay_ms=100  # Pulse uses delay_ms as duration
        )

        # First call with 0 -> sets last_trigger
        timer_update(state, config, 0, 0)

        # Trigger rising edge at t=10
        result = timer_update(state, config, 1, 10)
        self.assertEqual(result, 1)  # Pulse starts

        # t=60ms (still pulsing)
        result = timer_update(state, config, 1, 60)
        self.assertEqual(result, 1)

        # t=110ms (pulse ends, 100ms after trigger)
        result = timer_update(state, config, 1, 110)
        self.assertEqual(result, 0)


class TestPIDController(unittest.TestCase):
    """Test PID controller."""

    def test_proportional(self):
        """Test P-only control."""
        state = PIDState()
        config = PIDConfig(
            kp=100,  # 100/1000 = 0.1
            ki=0,
            kd=0,
            scale=1000,
            output_min=-1000,
            output_max=1000
        )

        # Error = setpoint - feedback = 100 - 0 = 100
        # P term = 100 * 100 / 1000 = 10
        result = pid_update(state, config, 100, 0, 10)
        self.assertEqual(result, 10)

    def test_integral(self):
        """Test I term accumulation."""
        state = PIDState()
        config = PIDConfig(
            kp=0,
            ki=1000,  # 1.0 when scale=1000
            kd=0,
            scale=1000,
            output_min=-10000,
            output_max=10000,
            integral_min=-10000,
            integral_max=10000
        )

        # With ki=1000, scale=1000: ki/scale = 1.0
        # i_delta = (ki * error * dt) // scale // 1000
        #         = (1000 * 100 * 100) // 1000 // 1000
        #         = 10000000 // 1000 // 1000 = 10
        result = pid_update(state, config, 100, 0, 100)  # 100ms dt for larger delta
        # integral = 10, i_term = 10 // 1000 = 0 (still too small)

        # Use larger values to test
        state2 = PIDState()
        config2 = PIDConfig(
            kp=0,
            ki=10000,  # 10.0 when scale=1000
            kd=0,
            scale=1000,
            output_min=-100000,
            output_max=100000,
            integral_min=-100000,
            integral_max=100000
        )

        # i_delta = (10000 * 1000 * 1000) // 1000 // 1000 = 10000
        # integral = 10000
        # i_term = 10000 // 1000 = 10
        result = pid_update(state2, config2, 1000, 0, 1000)
        # The integral accumulates, check it's non-zero
        self.assertGreater(result, 0)


class TestFilters(unittest.TestCase):
    """Test filter functions."""

    def test_sma(self):
        """Test Simple Moving Average."""
        state = SMAState()
        config = SMAConfig(window_size=4)

        # Add values
        self.assertEqual(sma_update(state, config, 10), 10)  # [10]
        self.assertEqual(sma_update(state, config, 20), 15)  # [10, 20] -> avg = 15
        self.assertEqual(sma_update(state, config, 30), 20)  # [10, 20, 30] -> avg = 20
        self.assertEqual(sma_update(state, config, 40), 25)  # [10, 20, 30, 40] -> avg = 25

        # Window full, oldest drops out
        self.assertEqual(sma_update(state, config, 50), 35)  # [20, 30, 40, 50] -> avg = 35

    def test_ema(self):
        """Test Exponential Moving Average."""
        state = EMAState()
        # Alpha is 0-255 with scale 256
        # alpha=128 means 0.5
        config = EMAConfig(alpha=128)

        # First value initializes
        result = ema_update(state, config, 1000)
        self.assertEqual(result, 1000)

        # Second value: ema = (128 * 0 + 128 * 1000) // 256 = 500
        result = ema_update(state, config, 0)
        self.assertEqual(result, 500)

    def test_median(self):
        """Test Median filter."""
        state = MedianState()
        config = MedianConfig(window_size=5)

        # Add values with outliers
        median_update(state, config, 10)
        median_update(state, config, 11)
        median_update(state, config, 100)  # Outlier
        median_update(state, config, 12)
        result = median_update(state, config, 13)

        # Sorted: [10, 11, 12, 13, 100], median = 12
        self.assertEqual(result, 12)


class TestTable2D(unittest.TestCase):
    """Test 2D lookup table."""

    def test_exact_lookup(self):
        """Test exact point lookup."""
        table = Table2D(
            x_values=[0, 50, 100],
            y_values=[0, 500, 1000]
        )

        self.assertEqual(table2d_lookup(table, 0), 0)
        self.assertEqual(table2d_lookup(table, 50), 500)
        self.assertEqual(table2d_lookup(table, 100), 1000)

    def test_interpolation(self):
        """Test linear interpolation."""
        table = Table2D(
            x_values=[0, 50, 100],
            y_values=[0, 500, 1000]
        )

        # x=25 should interpolate to 250
        result = table2d_lookup(table, 25)
        self.assertEqual(result, 250)

        # x=75 should interpolate to 750
        result = table2d_lookup(table, 75)
        self.assertEqual(result, 750)


class TestSwitch(unittest.TestCase):
    """Test switch/selector."""

    def test_switch_case(self):
        """Test value-based switch."""
        cases = [
            SwitchCase(match_value=0, result=100),
            SwitchCase(match_value=1, result=200),
            SwitchCase(match_value=2, result=300),
        ]

        self.assertEqual(switch_case(0, cases, default_value=-1), 100)
        self.assertEqual(switch_case(1, cases, default_value=-1), 200)
        self.assertEqual(switch_case(2, cases, default_value=-1), 300)
        self.assertEqual(switch_case(99, cases, default_value=-1), -1)  # Default

    def test_switch_select(self):
        """Test index-based selection."""
        values = [100, 200, 300, 400]

        self.assertEqual(switch_select(values, 0), 100)
        self.assertEqual(switch_select(values, 1), 200)
        self.assertEqual(switch_select(values, 3), 400)
        self.assertEqual(switch_select(values, 10), 0)  # Out of range


class TestHysteresis(unittest.TestCase):
    """Test hysteresis/Schmitt trigger."""

    def test_schmitt_trigger(self):
        """Test Schmitt trigger behavior."""
        state = HysteresisState()
        config = HysteresisConfig(
            threshold_high=60,
            threshold_low=40
        )

        # Start low, go up
        self.assertEqual(hysteresis_update(state, config, 30), 0)  # Below low
        self.assertEqual(hysteresis_update(state, config, 50), 0)  # Between thresholds
        self.assertEqual(hysteresis_update(state, config, 70), 1)  # Above high -> ON

        # Now high, go down
        self.assertEqual(hysteresis_update(state, config, 50), 1)  # Between thresholds, stay on
        self.assertEqual(hysteresis_update(state, config, 30), 0)  # Below low -> OFF


class TestChannelExecutor(unittest.TestCase):
    """Test Channel Executor integration."""

    def setUp(self):
        """Set up channel values dictionary and executor."""
        self.channel_values: Dict[int, int] = {}

        def get_value(channel_id: int) -> int:
            return self.channel_values.get(channel_id, 0)

        def set_value(channel_id: int, value: int) -> None:
            self.channel_values[channel_id] = value

        self.executor = ChannelExecutor()
        self.executor.init(get_value, set_value)

    def test_logic_channel(self):
        """Test logic channel execution through executor."""
        # Set up input channels
        self.channel_values[1] = 1  # Input A
        self.channel_values[2] = 1  # Input B

        # Create logic channel config
        config = CfgLogic(
            operation=LogicOp.AND,
            input_count=2,
            inputs=[1, 2, 0, 0, 0, 0, 0, 0]
        )

        # Create runtime
        runtime = ChannelRuntime(
            id=100,
            type=ChannelType.LOGIC,
            config=config
        )

        # Process
        self.executor.update_time(0)
        result = self.executor.process_channel(runtime)

        self.assertEqual(result, 1)  # 1 AND 1 = 1

        # Change input
        self.channel_values[2] = 0
        result = self.executor.process_channel(runtime)
        self.assertEqual(result, 0)  # 1 AND 0 = 0

    def test_timer_channel(self):
        """Test timer channel with state management."""
        # Set up trigger channel
        self.channel_values[1] = 0

        # Create timer config
        config = CfgTimer(
            trigger_id=1,
            mode=TimerMode.DELAY_ON.value,
            trigger_mode=TimerTrigger.LEVEL.value,
            delay_ms=100
        )

        # Create runtime with state
        runtime = ChannelRuntime(
            id=100,
            type=ChannelType.TIMER,
            config=config
        )

        # Initial: trigger low
        self.executor.update_time(0)
        result = self.executor.process_channel(runtime)
        self.assertEqual(result, 0)

        # Trigger goes high at t=0
        self.channel_values[1] = 1
        result = self.executor.process_channel(runtime)
        self.assertEqual(result, 0)  # Not yet, waiting for delay

        # t=50ms
        self.executor.update_time(50)
        result = self.executor.process_channel(runtime)
        self.assertEqual(result, 0)  # Still waiting

        # t=100ms - delay passed
        self.executor.update_time(100)
        result = self.executor.process_channel(runtime)
        self.assertEqual(result, 1)  # Now on!

    def test_math_channel(self):
        """Test math channel with multiple inputs."""
        # Set up input channels
        self.channel_values[1] = 100
        self.channel_values[2] = 50
        self.channel_values[3] = 30

        # Create math config for average
        config = CfgMath(
            operation=MathOp.AVG,
            input_count=3,
            inputs=[1, 2, 3, 0, 0, 0, 0, 0]
        )

        runtime = ChannelRuntime(
            id=100,
            type=ChannelType.MATH,
            config=config
        )

        self.executor.update_time(0)
        result = self.executor.process_channel(runtime)

        # (100 + 50 + 30) / 3 = 60
        self.assertEqual(result, 60)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_inputs(self):
        """Test functions with empty inputs."""
        # Empty lists return 0 for safety
        self.assertEqual(logic_and([]), 0)
        self.assertEqual(logic_or([]), 0)
        self.assertEqual(math_min([]), 0)
        self.assertEqual(math_max([]), 0)
        self.assertEqual(math_avg([]), 0)

    def test_division_by_zero(self):
        """Test division by zero handling."""
        # Division by zero returns INT32_MAX for positive, INT32_MIN for negative
        self.assertEqual(math_div(100, 0), 0x7FFFFFFF)
        self.assertEqual(math_div(-100, 0), -0x80000000)
        self.assertEqual(math_div(0, 0), 0)

        # Modulo by zero returns 0
        self.assertEqual(math_mod(100, 0), 0)

        # Scale by zero returns INT32_MAX (saturating)
        self.assertEqual(math_scale(100, 1, 0), 0x7FFFFFFF)

    def test_overflow_protection(self):
        """Test that large values don't overflow."""
        # Large multiplication
        result = math_mul(1000000, 1000)
        self.assertEqual(result, 1000000000)

        # Clamp should handle large values
        result = math_clamp(2000000000, -1000000000, 1000000000)
        self.assertEqual(result, 1000000000)


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)

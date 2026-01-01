"""
PMU-30 Shared Channel Configuration Validation (Python Port)

This module mirrors the C validation logic in channel_validation.c.
Used by:
- Configurator: validate user input in dialogs
- Integration tests: verify config correctness

@version 1.0
@date January 2026
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Any


class ValidationError(IntEnum):
    """Validation error codes (matches C enum)"""
    OK = 0

    # General errors (1-99)
    INVALID_TYPE = 1
    INVALID_ID = 2
    NAME_TOO_LONG = 3
    EMPTY_NAME = 4
    INVALID_FLAGS = 5
    INVALID_HW_DEVICE = 6
    INVALID_HW_INDEX = 7
    INVALID_SOURCE_ID = 8
    CONFIG_SIZE_MISMATCH = 9

    # Input validation errors (100-199)
    INPUT_INVALID_DEBOUNCE = 100
    INPUT_INVALID_FILTER_MS = 101
    INPUT_INVALID_FILTER_TYPE = 102
    INPUT_INVALID_SAMPLES = 103
    INPUT_INVALID_RANGE = 104
    INPUT_INVALID_TIMEOUT = 105
    INPUT_INVALID_EDGE_MODE = 106
    INPUT_ZERO_DIVISOR = 107

    # CAN errors (200-249)
    CAN_INVALID_BUS = 200
    CAN_INVALID_ID = 201
    CAN_INVALID_DLC = 202
    CAN_INVALID_BIT_POS = 203
    CAN_INVALID_BYTE_ORDER = 204
    CAN_ZERO_DIVISOR = 205
    CAN_INVALID_PERIOD = 206

    # Output validation errors (300-399)
    OUTPUT_INVALID_CURRENT_LIMIT = 300
    OUTPUT_INVALID_PWM_FREQ = 301
    OUTPUT_INVALID_RETRY_COUNT = 302
    OUTPUT_INVALID_SOFT_START = 303
    OUTPUT_INVALID_INRUSH = 304
    PWM_INVALID_DUTY_RANGE = 305
    HBRIDGE_INVALID_DEADBAND = 306
    HBRIDGE_INVALID_RATE = 307

    # Logic/Math errors (400-499)
    LOGIC_INVALID_OPERATION = 400
    LOGIC_NO_INPUTS = 401
    LOGIC_TOO_MANY_INPUTS = 402
    LOGIC_INVALID_INPUT_ID = 403
    LOGIC_INSUFFICIENT_INPUTS = 404
    MATH_INVALID_OPERATION = 405
    MATH_NO_INPUTS = 406
    MATH_TOO_MANY_INPUTS = 407
    MATH_INVALID_INPUT_ID = 408
    MATH_ZERO_DIVISOR = 409
    MATH_INVALID_RANGE = 410

    # Timer errors (500-549)
    TIMER_INVALID_MODE = 500
    TIMER_INVALID_TRIGGER_MODE = 501
    TIMER_INVALID_TRIGGER_ID = 502
    TIMER_ZERO_DELAY = 503
    TIMER_INVALID_BLINK_TIMES = 504

    # Table errors (550-599)
    TABLE_INVALID_INPUT = 550
    TABLE_INSUFFICIENT_POINTS = 551
    TABLE_TOO_MANY_POINTS = 552
    TABLE_X_NOT_MONOTONIC = 553
    TABLE_3D_INVALID_Y_INPUT = 554
    TABLE_3D_INSUFFICIENT_X = 555
    TABLE_3D_INSUFFICIENT_Y = 556

    # Filter errors (600-649)
    FILTER_INVALID_INPUT = 600
    FILTER_INVALID_TYPE = 601
    FILTER_INVALID_WINDOW = 602
    FILTER_INVALID_ALPHA = 603
    FILTER_ZERO_TIME_CONST = 604

    # PID errors (650-699)
    PID_INVALID_SETPOINT = 650
    PID_INVALID_FEEDBACK = 651
    PID_INVALID_OUTPUT_RANGE = 652
    PID_INVALID_INTEGRAL_RANGE = 653

    # Counter errors (700-749)
    COUNTER_INVALID_TRIGGER = 700
    COUNTER_INVALID_RANGE = 701
    COUNTER_ZERO_STEP = 702

    # FlipFlop errors (750-799)
    FF_INVALID_TYPE = 750
    FF_INVALID_INPUT = 751

    # Hysteresis errors (800-849)
    HYST_INVALID_INPUT = 800
    HYST_INVALID_TYPE = 801
    HYST_INVALID_THRESHOLDS = 802

    # Switch errors (850-899)
    SWITCH_INVALID_SELECTOR = 850
    SWITCH_NO_CASES = 851
    SWITCH_TOO_MANY_CASES = 852
    SWITCH_INVALID_MODE = 853

    # Number errors (900-949)
    NUMBER_INVALID_RANGE = 900
    NUMBER_ZERO_STEP = 901
    NUMBER_VALUE_OUT_OF_RANGE = 902


@dataclass
class ValidationResult:
    """Validation result with error details"""
    error: ValidationError = ValidationError.OK
    field: Optional[str] = None
    actual_value: int = 0
    expected_min: int = 0
    expected_max: int = 0

    @property
    def is_valid(self) -> bool:
        return self.error == ValidationError.OK

    @property
    def message(self) -> str:
        return get_error_message(self.error)

    def __bool__(self) -> bool:
        return self.is_valid


@dataclass
class ValidationLimits:
    """Configurable validation limits"""
    max_channel_id: int = 4095
    max_name_length: int = 31
    max_debounce_ms: int = 1000
    max_filter_ms: int = 10000
    max_samples: int = 64
    max_can_bus: int = 3
    max_current_ma: int = 40000
    max_pwm_freq: int = 25000
    min_pwm_freq: int = 100
    max_delay_ms: int = 3600000
    min_table_points: int = 2
    max_window_size: int = 32
    max_inputs: int = 8
    max_table_2d_size: int = 16
    max_table_3d_x: int = 8
    max_table_3d_y: int = 8
    max_switch_cases: int = 8


# Default limits instance
DEFAULT_LIMITS = ValidationLimits()

# Special channel reference value (no reference)
CH_REF_NONE = 0xFFFF


def success() -> ValidationResult:
    """Create success result"""
    return ValidationResult()


def error(code: ValidationError, field: str,
          actual: int = 0, min_val: int = 0, max_val: int = 0) -> ValidationResult:
    """Create error result"""
    return ValidationResult(
        error=code,
        field=field,
        actual_value=actual,
        expected_min=min_val,
        expected_max=max_val
    )


def is_valid_channel_id(id: int, max_id: int) -> bool:
    """Check if channel ID is valid"""
    return 0 < id <= max_id


def is_valid_channel_ref(id: int, max_id: int) -> bool:
    """Check if channel reference is valid (allows CH_REF_NONE)"""
    return id == CH_REF_NONE or (0 < id <= max_id)


def validate_digital_input(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate digital input configuration"""
    lim = limits or DEFAULT_LIMITS

    debounce = config.get('debounce_ms', 0)
    if debounce > lim.max_debounce_ms:
        return error(ValidationError.INPUT_INVALID_DEBOUNCE, 'debounce_ms',
                     debounce, 0, lim.max_debounce_ms)

    active_high = config.get('active_high', 1)
    if active_high not in (0, 1):
        return error(ValidationError.INVALID_FLAGS, 'active_high',
                     active_high, 0, 1)

    use_pullup = config.get('use_pullup', 0)
    if use_pullup not in (0, 1):
        return error(ValidationError.INVALID_FLAGS, 'use_pullup',
                     use_pullup, 0, 1)

    return success()


def validate_analog_input(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate analog input configuration"""
    lim = limits or DEFAULT_LIMITS

    raw_min = config.get('raw_min', 0)
    raw_max = config.get('raw_max', 4095)
    if raw_min == raw_max:
        return error(ValidationError.INPUT_INVALID_RANGE, 'raw_min/raw_max',
                     raw_min, 0, 0)

    filter_ms = config.get('filter_ms', 0)
    if filter_ms > lim.max_filter_ms:
        return error(ValidationError.INPUT_INVALID_FILTER_MS, 'filter_ms',
                     filter_ms, 0, lim.max_filter_ms)

    samples = config.get('samples', 1)
    if samples > lim.max_samples:
        return error(ValidationError.INPUT_INVALID_SAMPLES, 'samples',
                     samples, 1, lim.max_samples)

    return success()


def validate_frequency_input(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate frequency input configuration"""
    min_freq = config.get('min_freq_hz', 0)
    max_freq = config.get('max_freq_hz', 10000)
    if min_freq >= max_freq:
        return error(ValidationError.INPUT_INVALID_RANGE, 'min_freq_hz',
                     min_freq, 0, max_freq)

    edge_mode = config.get('edge_mode', 0)
    if edge_mode > 2:
        return error(ValidationError.INPUT_INVALID_EDGE_MODE, 'edge_mode',
                     edge_mode, 0, 2)

    scale_den = config.get('scale_den', 1)
    if scale_den == 0:
        return error(ValidationError.INPUT_ZERO_DIVISOR, 'scale_den',
                     0, 1, 2**31 - 1)

    return success()


def validate_can_input(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate CAN input configuration"""
    lim = limits or DEFAULT_LIMITS

    bus = config.get('bus', 0)
    if bus > lim.max_can_bus:
        return error(ValidationError.CAN_INVALID_BUS, 'bus',
                     bus, 0, lim.max_can_bus)

    can_id = config.get('can_id', 0)
    is_extended = config.get('is_extended', False)
    max_id = 0x1FFFFFFF if is_extended else 0x7FF
    if can_id > max_id:
        return error(ValidationError.CAN_INVALID_ID, 'can_id',
                     can_id, 0, max_id)

    start_bit = config.get('start_bit', 0)
    bit_length = config.get('bit_length', 8)
    if start_bit + bit_length > 64:
        return error(ValidationError.CAN_INVALID_BIT_POS, 'start_bit+bit_length',
                     start_bit + bit_length, 0, 64)

    if bit_length == 0 or bit_length > 32:
        return error(ValidationError.CAN_INVALID_BIT_POS, 'bit_length',
                     bit_length, 1, 32)

    byte_order = config.get('byte_order', 0)
    if byte_order > 1:
        return error(ValidationError.CAN_INVALID_BYTE_ORDER, 'byte_order',
                     byte_order, 0, 1)

    scale_den = config.get('scale_den', 1)
    if scale_den == 0:
        return error(ValidationError.CAN_ZERO_DIVISOR, 'scale_den',
                     0, 1, 32767)

    return success()


def validate_power_output(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate power output configuration"""
    lim = limits or DEFAULT_LIMITS

    current_limit = config.get('current_limit_ma', 5000)
    if current_limit > lim.max_current_ma:
        return error(ValidationError.OUTPUT_INVALID_CURRENT_LIMIT, 'current_limit_ma',
                     current_limit, 0, lim.max_current_ma)

    inrush_limit = config.get('inrush_limit_ma', current_limit)
    if inrush_limit < current_limit:
        return error(ValidationError.OUTPUT_INVALID_INRUSH, 'inrush_limit_ma',
                     inrush_limit, current_limit, lim.max_current_ma)

    pwm_freq = config.get('pwm_frequency', 0)
    if pwm_freq > 0:
        if pwm_freq < lim.min_pwm_freq or pwm_freq > lim.max_pwm_freq:
            return error(ValidationError.OUTPUT_INVALID_PWM_FREQ, 'pwm_frequency',
                         pwm_freq, lim.min_pwm_freq, lim.max_pwm_freq)

    retry_count = config.get('retry_count', 3)
    if retry_count > 10:
        return error(ValidationError.OUTPUT_INVALID_RETRY_COUNT, 'retry_count',
                     retry_count, 0, 10)

    return success()


def validate_pwm_output(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate PWM output configuration"""
    lim = limits or DEFAULT_LIMITS

    freq = config.get('frequency_hz', 1000)
    if freq < lim.min_pwm_freq or freq > lim.max_pwm_freq:
        return error(ValidationError.OUTPUT_INVALID_PWM_FREQ, 'frequency_hz',
                     freq, lim.min_pwm_freq, lim.max_pwm_freq)

    min_duty = config.get('min_duty', 0)
    max_duty = config.get('max_duty', 10000)
    if min_duty > max_duty:
        return error(ValidationError.PWM_INVALID_DUTY_RANGE, 'min_duty',
                     min_duty, 0, max_duty)

    if max_duty > 10000:
        return error(ValidationError.PWM_INVALID_DUTY_RANGE, 'max_duty',
                     max_duty, 0, 10000)

    default_duty = config.get('default_duty', 0)
    if default_duty < min_duty or default_duty > max_duty:
        return error(ValidationError.PWM_INVALID_DUTY_RANGE, 'default_duty',
                     default_duty, min_duty, max_duty)

    return success()


def validate_logic(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate logic channel configuration"""
    lim = limits or DEFAULT_LIMITS

    operation = config.get('operation', 0)
    if operation > 0x21:  # LOGIC_OP_OUTSIDE
        return error(ValidationError.LOGIC_INVALID_OPERATION, 'operation',
                     operation, 0, 0x21)

    inputs = config.get('inputs', [])
    input_count = len(inputs)

    if input_count == 0:
        return error(ValidationError.LOGIC_NO_INPUTS, 'input_count',
                     0, 1, lim.max_inputs)

    if input_count > lim.max_inputs:
        return error(ValidationError.LOGIC_TOO_MANY_INPUTS, 'input_count',
                     input_count, 1, lim.max_inputs)

    # Multi-input operations need at least 2 inputs
    if operation in (0, 1, 2) and input_count < 2:  # AND, OR, XOR
        return error(ValidationError.LOGIC_INSUFFICIENT_INPUTS, 'input_count',
                     input_count, 2, lim.max_inputs)

    # Validate input IDs
    for i, input_id in enumerate(inputs):
        if not is_valid_channel_ref(input_id, lim.max_channel_id):
            return error(ValidationError.LOGIC_INVALID_INPUT_ID, f'inputs[{i}]',
                         input_id, 0, lim.max_channel_id)

    return success()


def validate_math(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate math channel configuration"""
    lim = limits or DEFAULT_LIMITS

    operation = config.get('operation', 0)
    if operation > 0x0C:  # MATH_OP_SCALE
        return error(ValidationError.MATH_INVALID_OPERATION, 'operation',
                     operation, 0, 0x0C)

    inputs = config.get('inputs', [])
    input_count = len(inputs)

    if input_count == 0:
        return error(ValidationError.MATH_NO_INPUTS, 'input_count',
                     0, 1, lim.max_inputs)

    if input_count > lim.max_inputs:
        return error(ValidationError.MATH_TOO_MANY_INPUTS, 'input_count',
                     input_count, 1, lim.max_inputs)

    # Validate input IDs
    for i, input_id in enumerate(inputs):
        if not is_valid_channel_ref(input_id, lim.max_channel_id):
            return error(ValidationError.MATH_INVALID_INPUT_ID, f'inputs[{i}]',
                         input_id, 0, lim.max_channel_id)

    # Division check
    if operation == 3:  # MATH_OP_DIV
        constant = config.get('constant', 1)
        if constant == 0:
            return error(ValidationError.MATH_ZERO_DIVISOR, 'constant',
                         0, 1, 2**31 - 1)

    scale_den = config.get('scale_den', 1)
    if scale_den == 0:
        return error(ValidationError.MATH_ZERO_DIVISOR, 'scale_den',
                     0, 1, 32767)

    # Clamp range
    if operation == 0x0A:  # MATH_OP_CLAMP
        min_val = config.get('min_value', 0)
        max_val = config.get('max_value', 1000)
        if min_val >= max_val:
            return error(ValidationError.MATH_INVALID_RANGE, 'min_value',
                         min_val, -(2**31), max_val - 1)

    return success()


def validate_timer(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate timer configuration"""
    lim = limits or DEFAULT_LIMITS

    mode = config.get('mode', 0)
    if mode > 6:  # TIMER_MODE_MONOSTABLE
        return error(ValidationError.TIMER_INVALID_MODE, 'mode',
                     mode, 0, 6)

    trigger_mode = config.get('trigger_mode', 0)
    if trigger_mode > 3:
        return error(ValidationError.TIMER_INVALID_TRIGGER_MODE, 'trigger_mode',
                     trigger_mode, 0, 3)

    trigger_id = config.get('trigger_id', CH_REF_NONE)
    if not is_valid_channel_ref(trigger_id, lim.max_channel_id):
        return error(ValidationError.TIMER_INVALID_TRIGGER_ID, 'trigger_id',
                     trigger_id, 0, lim.max_channel_id)

    delay_ms = config.get('delay_ms', 1000)
    if delay_ms == 0 and mode != 3:  # Not BLINK mode
        return error(ValidationError.TIMER_ZERO_DELAY, 'delay_ms',
                     0, 1, lim.max_delay_ms)

    if delay_ms > lim.max_delay_ms:
        return error(ValidationError.TIMER_ZERO_DELAY, 'delay_ms',
                     delay_ms, 0, lim.max_delay_ms)

    # Blink times
    if mode == 3:  # BLINK
        on_time = config.get('on_time_ms', 500)
        off_time = config.get('off_time_ms', 500)
        if on_time == 0 or off_time == 0:
            return error(ValidationError.TIMER_INVALID_BLINK_TIMES,
                         'on_time_ms/off_time_ms', 0, 1, 60000)

    return success()


def validate_table_2d(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate 2D table configuration"""
    lim = limits or DEFAULT_LIMITS

    input_id = config.get('input_id', 0)
    if not is_valid_channel_ref(input_id, lim.max_channel_id):
        return error(ValidationError.TABLE_INVALID_INPUT, 'input_id',
                     input_id, 0, lim.max_channel_id)

    x_values = config.get('x_values', [])
    y_values = config.get('y_values', [])
    point_count = len(x_values)

    if point_count < lim.min_table_points:
        return error(ValidationError.TABLE_INSUFFICIENT_POINTS, 'point_count',
                     point_count, lim.min_table_points, lim.max_table_2d_size)

    if point_count > lim.max_table_2d_size:
        return error(ValidationError.TABLE_TOO_MANY_POINTS, 'point_count',
                     point_count, lim.min_table_points, lim.max_table_2d_size)

    # Check X values are monotonically increasing
    for i in range(1, point_count):
        if x_values[i] <= x_values[i - 1]:
            return error(ValidationError.TABLE_X_NOT_MONOTONIC, f'x_values[{i}]',
                         i, 0, 0)

    return success()


def validate_filter(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate filter configuration"""
    lim = limits or DEFAULT_LIMITS

    input_id = config.get('input_id', 0)
    if not is_valid_channel_ref(input_id, lim.max_channel_id):
        return error(ValidationError.FILTER_INVALID_INPUT, 'input_id',
                     input_id, 0, lim.max_channel_id)

    filter_type = config.get('filter_type', 0)
    if filter_type > 6:  # Max filter type
        return error(ValidationError.FILTER_INVALID_TYPE, 'filter_type',
                     filter_type, 0, 6)

    # Window size for SMA/Median
    if filter_type in (1, 4):  # SMA, MEDIAN
        window_size = config.get('window_size', 4)
        if window_size < 2 or window_size > lim.max_window_size:
            return error(ValidationError.FILTER_INVALID_WINDOW, 'window_size',
                         window_size, 2, lim.max_window_size)

    # Time constant for LPF
    if filter_type == 3:  # LOWPASS
        time_const = config.get('time_constant_ms', 100)
        if time_const == 0:
            return error(ValidationError.FILTER_ZERO_TIME_CONST, 'time_constant_ms',
                         0, 1, 60000)

    return success()


def validate_pid(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate PID configuration"""
    lim = limits or DEFAULT_LIMITS

    setpoint_id = config.get('setpoint_id', 0)
    if not is_valid_channel_ref(setpoint_id, lim.max_channel_id):
        return error(ValidationError.PID_INVALID_SETPOINT, 'setpoint_id',
                     setpoint_id, 0, lim.max_channel_id)

    feedback_id = config.get('feedback_id', 0)
    if not is_valid_channel_ref(feedback_id, lim.max_channel_id):
        return error(ValidationError.PID_INVALID_FEEDBACK, 'feedback_id',
                     feedback_id, 0, lim.max_channel_id)

    output_min = config.get('output_min', 0)
    output_max = config.get('output_max', 10000)
    if output_min >= output_max:
        return error(ValidationError.PID_INVALID_OUTPUT_RANGE, 'output_min',
                     output_min, -32768, output_max - 1)

    integral_min = config.get('integral_min', -10000)
    integral_max = config.get('integral_max', 10000)
    if integral_min >= integral_max:
        return error(ValidationError.PID_INVALID_INTEGRAL_RANGE, 'integral_min',
                     integral_min, -32768, integral_max - 1)

    return success()


def validate_counter(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate counter configuration"""
    lim = limits or DEFAULT_LIMITS

    inc_id = config.get('inc_trigger_id', CH_REF_NONE)
    dec_id = config.get('dec_trigger_id', CH_REF_NONE)
    reset_id = config.get('reset_trigger_id', CH_REF_NONE)

    has_inc = is_valid_channel_ref(inc_id, lim.max_channel_id)
    has_dec = is_valid_channel_ref(dec_id, lim.max_channel_id)
    has_reset = is_valid_channel_ref(reset_id, lim.max_channel_id)

    if not (has_inc or has_dec or has_reset):
        return error(ValidationError.COUNTER_INVALID_TRIGGER, 'triggers',
                     0, 0, 0)

    min_val = config.get('min_value', 0)
    max_val = config.get('max_value', 100)
    if min_val >= max_val:
        return error(ValidationError.COUNTER_INVALID_RANGE, 'min_value',
                     min_val, -32768, max_val - 1)

    step = config.get('step', 1)
    if step == 0:
        return error(ValidationError.COUNTER_ZERO_STEP, 'step',
                     0, 1, 32767)

    initial = config.get('initial_value', 0)
    if initial < min_val or initial > max_val:
        return error(ValidationError.COUNTER_INVALID_RANGE, 'initial_value',
                     initial, min_val, max_val)

    return success()


def validate_flipflop(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate flipflop configuration"""
    lim = limits or DEFAULT_LIMITS

    ff_type = config.get('ff_type', 0)
    if ff_type > 5:  # FF_TYPE_D_LATCH
        return error(ValidationError.FF_INVALID_TYPE, 'ff_type',
                     ff_type, 0, 5)

    set_id = config.get('set_input_id', CH_REF_NONE)
    reset_id = config.get('reset_input_id', CH_REF_NONE)
    clock_id = config.get('clock_input_id', CH_REF_NONE)

    # Type-specific input validation
    if ff_type in (0, 4):  # SR, SR_LATCH
        if not is_valid_channel_ref(set_id, lim.max_channel_id):
            return error(ValidationError.FF_INVALID_INPUT, 'set_input_id', 0, 0, 0)
        if not is_valid_channel_ref(reset_id, lim.max_channel_id):
            return error(ValidationError.FF_INVALID_INPUT, 'reset_input_id', 0, 0, 0)

    elif ff_type in (1, 5):  # D, D_LATCH
        if not is_valid_channel_ref(set_id, lim.max_channel_id):
            return error(ValidationError.FF_INVALID_INPUT, 'set_input_id', 0, 0, 0)
        if not is_valid_channel_ref(clock_id, lim.max_channel_id):
            return error(ValidationError.FF_INVALID_INPUT, 'clock_input_id', 0, 0, 0)

    elif ff_type == 2:  # T
        if not is_valid_channel_ref(set_id, lim.max_channel_id):
            return error(ValidationError.FF_INVALID_INPUT, 'set_input_id', 0, 0, 0)

    elif ff_type == 3:  # JK
        if not is_valid_channel_ref(set_id, lim.max_channel_id):
            return error(ValidationError.FF_INVALID_INPUT, 'set_input_id', 0, 0, 0)
        if not is_valid_channel_ref(reset_id, lim.max_channel_id):
            return error(ValidationError.FF_INVALID_INPUT, 'reset_input_id', 0, 0, 0)
        if not is_valid_channel_ref(clock_id, lim.max_channel_id):
            return error(ValidationError.FF_INVALID_INPUT, 'clock_input_id', 0, 0, 0)

    return success()


def validate_hysteresis(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate hysteresis configuration"""
    lim = limits or DEFAULT_LIMITS

    input_id = config.get('input_id', 0)
    if not is_valid_channel_ref(input_id, lim.max_channel_id):
        return error(ValidationError.HYST_INVALID_INPUT, 'input_id',
                     input_id, 0, lim.max_channel_id)

    hyst_type = config.get('hyst_type', 0)
    if hyst_type > 2:  # HYST_TYPE_MULTILEVEL
        return error(ValidationError.HYST_INVALID_TYPE, 'hyst_type',
                     hyst_type, 0, 2)

    low = config.get('threshold_low', 0)
    high = config.get('threshold_high', 100)
    if low >= high:
        return error(ValidationError.HYST_INVALID_THRESHOLDS, 'threshold_low',
                     low, -(2**31), high - 1)

    return success()


def validate_switch(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate switch configuration"""
    lim = limits or DEFAULT_LIMITS

    selector_id = config.get('selector_id', 0)
    if not is_valid_channel_ref(selector_id, lim.max_channel_id):
        return error(ValidationError.SWITCH_INVALID_SELECTOR, 'selector_id',
                     selector_id, 0, lim.max_channel_id)

    cases = config.get('cases', [])
    case_count = len(cases)

    if case_count == 0:
        return error(ValidationError.SWITCH_NO_CASES, 'case_count',
                     0, 1, lim.max_switch_cases)

    if case_count > lim.max_switch_cases:
        return error(ValidationError.SWITCH_TOO_MANY_CASES, 'case_count',
                     case_count, 1, lim.max_switch_cases)

    mode = config.get('mode', 0)
    if mode > 2:
        return error(ValidationError.SWITCH_INVALID_MODE, 'mode',
                     mode, 0, 2)

    return success()


def validate_number(config: dict, limits: ValidationLimits = None) -> ValidationResult:
    """Validate number/constant configuration"""
    min_val = config.get('min_value', 0)
    max_val = config.get('max_value', 1000)

    if min_val >= max_val:
        return error(ValidationError.NUMBER_INVALID_RANGE, 'min_value',
                     min_val, -(2**31), max_val - 1)

    readonly = config.get('readonly', False)
    step = config.get('step', 1)
    if not readonly and step == 0:
        return error(ValidationError.NUMBER_ZERO_STEP, 'step',
                     0, 1, 2**31 - 1)

    value = config.get('value', 0)
    if value < min_val or value > max_val:
        return error(ValidationError.NUMBER_VALUE_OUT_OF_RANGE, 'value',
                     value, min_val, max_val)

    return success()


# Channel type to validator mapping
VALIDATORS = {
    0x01: validate_digital_input,   # CH_TYPE_DIGITAL_INPUT
    0x02: validate_analog_input,    # CH_TYPE_ANALOG_INPUT
    0x03: validate_frequency_input,  # CH_TYPE_FREQUENCY_INPUT
    0x04: validate_can_input,        # CH_TYPE_CAN_INPUT
    0x10: validate_power_output,     # CH_TYPE_POWER_OUTPUT
    0x11: validate_pwm_output,       # CH_TYPE_PWM_OUTPUT
    0x20: validate_timer,            # CH_TYPE_TIMER
    0x21: validate_logic,            # CH_TYPE_LOGIC
    0x22: validate_math,             # CH_TYPE_MATH
    0x23: validate_table_2d,         # CH_TYPE_TABLE_2D
    0x25: validate_filter,           # CH_TYPE_FILTER
    0x26: validate_pid,              # CH_TYPE_PID
    0x27: validate_number,           # CH_TYPE_NUMBER
    0x28: validate_switch,           # CH_TYPE_SWITCH
    0x2A: validate_counter,          # CH_TYPE_COUNTER
    0x2B: validate_hysteresis,       # CH_TYPE_HYSTERESIS
    0x2C: validate_flipflop,         # CH_TYPE_FLIPFLOP
}


def validate_channel(channel_type: int, config: dict,
                     limits: ValidationLimits = None) -> ValidationResult:
    """
    Validate channel configuration based on type.

    Args:
        channel_type: Channel type code
        config: Configuration dictionary
        limits: Optional custom validation limits

    Returns:
        ValidationResult with error details if invalid
    """
    validator = VALIDATORS.get(channel_type)
    if validator is None:
        return error(ValidationError.INVALID_TYPE, 'type',
                     channel_type, 0, 0x2C)

    return validator(config, limits)


def get_error_message(err: ValidationError) -> str:
    """Get human-readable error message"""
    messages = {
        ValidationError.OK: "OK",
        ValidationError.INVALID_TYPE: "Invalid channel type",
        ValidationError.INVALID_ID: "Invalid channel ID",
        ValidationError.NAME_TOO_LONG: "Name too long",
        ValidationError.EMPTY_NAME: "Name cannot be empty",
        ValidationError.INPUT_INVALID_DEBOUNCE: "Invalid debounce time",
        ValidationError.INPUT_INVALID_RANGE: "Invalid input range",
        ValidationError.INPUT_ZERO_DIVISOR: "Scale divisor cannot be zero",
        ValidationError.CAN_INVALID_BUS: "Invalid CAN bus number",
        ValidationError.CAN_INVALID_ID: "Invalid CAN message ID",
        ValidationError.CAN_INVALID_BIT_POS: "Invalid bit position",
        ValidationError.CAN_ZERO_DIVISOR: "Scale divisor cannot be zero",
        ValidationError.OUTPUT_INVALID_CURRENT_LIMIT: "Invalid current limit",
        ValidationError.OUTPUT_INVALID_PWM_FREQ: "Invalid PWM frequency",
        ValidationError.PWM_INVALID_DUTY_RANGE: "Invalid duty cycle range",
        ValidationError.LOGIC_INVALID_OPERATION: "Invalid logic operation",
        ValidationError.LOGIC_NO_INPUTS: "Logic channel needs inputs",
        ValidationError.LOGIC_INSUFFICIENT_INPUTS: "Insufficient inputs for operation",
        ValidationError.MATH_ZERO_DIVISOR: "Division by zero",
        ValidationError.TIMER_INVALID_MODE: "Invalid timer mode",
        ValidationError.TIMER_ZERO_DELAY: "Timer delay must be > 0",
        ValidationError.TABLE_X_NOT_MONOTONIC: "X values must be ascending",
        ValidationError.FILTER_ZERO_TIME_CONST: "Time constant must be > 0",
        ValidationError.PID_INVALID_OUTPUT_RANGE: "Invalid output range",
        ValidationError.COUNTER_ZERO_STEP: "Counter step must be > 0",
        ValidationError.FF_INVALID_INPUT: "Invalid flipflop input",
        ValidationError.HYST_INVALID_THRESHOLDS: "Low threshold must be < high",
        ValidationError.NUMBER_VALUE_OUT_OF_RANGE: "Value out of range",
    }
    return messages.get(err, f"Validation error {err.value}")

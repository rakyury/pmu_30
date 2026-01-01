"""
Logic Engine - Math Operations

Pure functions for math operations.
Uses integer arithmetic to match C implementation.
"""

from enum import IntEnum
from typing import Sequence


class MathOp(IntEnum):
    """Math operation types"""
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    MOD = 4
    ABS = 5
    NEG = 6
    MIN = 16
    MAX = 17
    AVG = 18
    CLAMP = 32
    MAP = 33
    SCALE = 34
    LERP = 35


# Constants matching C implementation
INT32_MAX = 2147483647
INT32_MIN = -2147483648


def _clamp_i32(value: int) -> int:
    """Clamp to int32 range"""
    if value > INT32_MAX:
        return INT32_MAX
    if value < INT32_MIN:
        return INT32_MIN
    return value


def math_add(a: int, b: int) -> int:
    """Add two values with overflow protection"""
    return _clamp_i32(a + b)


def math_sub(a: int, b: int) -> int:
    """Subtract two values with overflow protection"""
    return _clamp_i32(a - b)


def math_mul(a: int, b: int) -> int:
    """Multiply two values with overflow protection"""
    return _clamp_i32(a * b)


def math_div(a: int, b: int) -> int:
    """Divide two values (returns 0 on division by zero)"""
    if b == 0:
        return INT32_MAX if a > 0 else (INT32_MIN if a < 0 else 0)
    return a // b


def math_mod(a: int, b: int) -> int:
    """Modulo operation (returns 0 on division by zero)"""
    if b == 0:
        return 0
    return a % b


def math_abs(value: int) -> int:
    """Absolute value"""
    if value == INT32_MIN:
        return INT32_MAX  # Prevent overflow
    return abs(value)


def math_neg(value: int) -> int:
    """Negate value"""
    if value == INT32_MIN:
        return INT32_MAX
    return -value


def math_min(inputs: Sequence[int]) -> int:
    """Find minimum of all inputs"""
    if not inputs:
        return 0
    return min(inputs)


def math_max(inputs: Sequence[int]) -> int:
    """Find maximum of all inputs"""
    if not inputs:
        return 0
    return max(inputs)


def math_avg(inputs: Sequence[int]) -> int:
    """Calculate average of all inputs (integer division)"""
    if not inputs:
        return 0
    return sum(inputs) // len(inputs)


def math_clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp value to range [min_val, max_val]"""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


def math_map(value: int, in_min: int, in_max: int, out_min: int, out_max: int) -> int:
    """
    Map value from input range to output range.

    Equivalent to Arduino map() function.
    Uses 64-bit intermediate to prevent overflow.
    """
    in_range = in_max - in_min
    if in_range == 0:
        return out_min

    out_range = out_max - out_min
    result = (value - in_min) * out_range // in_range + out_min

    return _clamp_i32(result)


def math_scale(value: int, multiplier: int, divisor: int) -> int:
    """
    Scale value by multiplier/divisor.
    Uses 64-bit intermediate to prevent overflow.
    """
    if divisor == 0:
        return INT32_MAX if value * multiplier > 0 else INT32_MIN
    return _clamp_i32(value * multiplier // divisor)


def math_lerp(a: int, b: int, t: int, t_max: int = 1000) -> int:
    """
    Linear interpolation between a and b.
    t=0 returns a, t=t_max returns b.
    Default t_max=1000 for 0.1% resolution.
    """
    if t_max == 0:
        return a
    if t <= 0:
        return a
    if t >= t_max:
        return b

    return _clamp_i32(a + (b - a) * t // t_max)


def math_evaluate(op: MathOp, inputs: Sequence[int]) -> int:
    """
    Evaluate math operation.

    Args:
        op: Math operation to perform
        inputs: Input values (meaning depends on operation)

    Returns:
        Operation result
    """
    if not inputs:
        return 0

    if op == MathOp.ADD:
        return math_add(inputs[0], inputs[1]) if len(inputs) >= 2 else inputs[0]
    elif op == MathOp.SUB:
        return math_sub(inputs[0], inputs[1]) if len(inputs) >= 2 else inputs[0]
    elif op == MathOp.MUL:
        return math_mul(inputs[0], inputs[1]) if len(inputs) >= 2 else inputs[0]
    elif op == MathOp.DIV:
        return math_div(inputs[0], inputs[1]) if len(inputs) >= 2 else inputs[0]
    elif op == MathOp.MOD:
        return math_mod(inputs[0], inputs[1]) if len(inputs) >= 2 else inputs[0]
    elif op == MathOp.ABS:
        return math_abs(inputs[0])
    elif op == MathOp.NEG:
        return math_neg(inputs[0])
    elif op == MathOp.MIN:
        return math_min(inputs)
    elif op == MathOp.MAX:
        return math_max(inputs)
    elif op == MathOp.AVG:
        return math_avg(inputs)
    elif op == MathOp.CLAMP:
        return math_clamp(inputs[0], inputs[1], inputs[2]) if len(inputs) >= 3 else inputs[0]
    elif op == MathOp.MAP:
        return math_map(inputs[0], inputs[1], inputs[2], inputs[3], inputs[4]) if len(inputs) >= 5 else inputs[0]
    elif op == MathOp.SCALE:
        return math_scale(inputs[0], inputs[1], inputs[2]) if len(inputs) >= 3 else inputs[0]
    elif op == MathOp.LERP:
        if len(inputs) >= 4:
            return math_lerp(inputs[0], inputs[1], inputs[2], inputs[3])
        elif len(inputs) >= 3:
            return math_lerp(inputs[0], inputs[1], inputs[2])
        return inputs[0]

    return 0

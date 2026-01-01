"""
Logic Engine - Boolean Logic Operations

Pure functions for boolean logic operations.
All functions return int32 values (0 or 1 for boolean, comparison results).
"""

from enum import IntEnum
from typing import Sequence


class LogicOp(IntEnum):
    """Logic operation types"""
    AND = 0
    OR = 1
    XOR = 2
    NAND = 3
    NOR = 4
    NOT = 5
    GT = 16
    GTE = 17
    LT = 18
    LTE = 19
    EQ = 20
    NEQ = 21
    IN_RANGE = 32
    OUTSIDE_RANGE = 33


def logic_and(inputs: Sequence[int]) -> int:
    """
    Logical AND of all inputs.
    Returns 1 if ALL inputs are non-zero.
    """
    if not inputs:
        return 0
    return 1 if all(x != 0 for x in inputs) else 0


def logic_or(inputs: Sequence[int]) -> int:
    """
    Logical OR of all inputs.
    Returns 1 if ANY input is non-zero.
    """
    if not inputs:
        return 0
    return 1 if any(x != 0 for x in inputs) else 0


def logic_xor(inputs: Sequence[int]) -> int:
    """
    Logical XOR of all inputs.
    Returns 1 if ODD number of inputs are non-zero.
    """
    if not inputs:
        return 0
    result = 0
    for x in inputs:
        if x != 0:
            result ^= 1
    return result


def logic_nand(inputs: Sequence[int]) -> int:
    """Logical NAND (NOT AND)"""
    return 1 if logic_and(inputs) == 0 else 0


def logic_nor(inputs: Sequence[int]) -> int:
    """Logical NOR (NOT OR)"""
    return 1 if logic_or(inputs) == 0 else 0


def logic_not(value: int) -> int:
    """Logical NOT"""
    return 0 if value != 0 else 1


def logic_gt(a: int, b: int) -> int:
    """Greater than comparison: a > b"""
    return 1 if a > b else 0


def logic_gte(a: int, b: int) -> int:
    """Greater than or equal: a >= b"""
    return 1 if a >= b else 0


def logic_lt(a: int, b: int) -> int:
    """Less than comparison: a < b"""
    return 1 if a < b else 0


def logic_lte(a: int, b: int) -> int:
    """Less than or equal: a <= b"""
    return 1 if a <= b else 0


def logic_eq(a: int, b: int) -> int:
    """Equality comparison: a == b"""
    return 1 if a == b else 0


def logic_neq(a: int, b: int) -> int:
    """Not equal comparison: a != b"""
    return 1 if a != b else 0


def logic_in_range(value: int, low: int, high: int) -> int:
    """Check if value is in range [low, high] inclusive"""
    return 1 if low <= value <= high else 0


def logic_outside_range(value: int, low: int, high: int) -> int:
    """Check if value is outside range [low, high]"""
    return 1 if value < low or value > high else 0


def logic_evaluate(op: LogicOp, inputs: Sequence[int]) -> int:
    """
    Evaluate logic operation.

    Args:
        op: Logic operation to perform
        inputs: Input values (meaning depends on operation)

    Returns:
        Operation result (0 or 1 for boolean ops)
    """
    if not inputs:
        return 0

    if op == LogicOp.AND:
        return logic_and(inputs)
    elif op == LogicOp.OR:
        return logic_or(inputs)
    elif op == LogicOp.XOR:
        return logic_xor(inputs)
    elif op == LogicOp.NAND:
        return logic_nand(inputs)
    elif op == LogicOp.NOR:
        return logic_nor(inputs)
    elif op == LogicOp.NOT:
        return logic_not(inputs[0])
    elif op == LogicOp.GT:
        return logic_gt(inputs[0], inputs[1]) if len(inputs) >= 2 else 0
    elif op == LogicOp.GTE:
        return logic_gte(inputs[0], inputs[1]) if len(inputs) >= 2 else 0
    elif op == LogicOp.LT:
        return logic_lt(inputs[0], inputs[1]) if len(inputs) >= 2 else 0
    elif op == LogicOp.LTE:
        return logic_lte(inputs[0], inputs[1]) if len(inputs) >= 2 else 0
    elif op == LogicOp.EQ:
        return logic_eq(inputs[0], inputs[1]) if len(inputs) >= 2 else 0
    elif op == LogicOp.NEQ:
        return logic_neq(inputs[0], inputs[1]) if len(inputs) >= 2 else 0
    elif op == LogicOp.IN_RANGE:
        return logic_in_range(inputs[0], inputs[1], inputs[2]) if len(inputs) >= 3 else 0
    elif op == LogicOp.OUTSIDE_RANGE:
        return logic_outside_range(inputs[0], inputs[1], inputs[2]) if len(inputs) >= 3 else 0

    return 0

/**
 * @file logic.c
 * @brief Logic Engine - Logic Operations Implementation
 */

#include "logic.h"

/*============================================================================
 * Boolean Logic Functions
 *============================================================================*/

int32_t Logic_AND(const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    for (uint8_t i = 0; i < count; i++) {
        if (inputs[i] == 0) return 0;
    }
    return 1;
}

int32_t Logic_OR(const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    for (uint8_t i = 0; i < count; i++) {
        if (inputs[i] != 0) return 1;
    }
    return 0;
}

int32_t Logic_XOR(const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    uint8_t true_count = 0;
    for (uint8_t i = 0; i < count; i++) {
        if (inputs[i] != 0) true_count++;
    }
    return (true_count & 1);  /* Odd number of true inputs */
}

int32_t Logic_NAND(const int32_t* inputs, uint8_t count)
{
    return Logic_AND(inputs, count) ? 0 : 1;
}

int32_t Logic_NOR(const int32_t* inputs, uint8_t count)
{
    return Logic_OR(inputs, count) ? 0 : 1;
}

int32_t Logic_IsTrue(int32_t input)
{
    return (input != 0) ? 1 : 0;
}

int32_t Logic_IsFalse(int32_t input)
{
    return (input == 0) ? 1 : 0;
}

/*============================================================================
 * Comparison Functions
 *============================================================================*/

int32_t Logic_GT(int32_t a, int32_t b)
{
    return (a > b) ? 1 : 0;
}

int32_t Logic_GTE(int32_t a, int32_t b)
{
    return (a >= b) ? 1 : 0;
}

int32_t Logic_LT(int32_t a, int32_t b)
{
    return (a < b) ? 1 : 0;
}

int32_t Logic_LTE(int32_t a, int32_t b)
{
    return (a <= b) ? 1 : 0;
}

int32_t Logic_EQ(int32_t a, int32_t b)
{
    return (a == b) ? 1 : 0;
}

int32_t Logic_NEQ(int32_t a, int32_t b)
{
    return (a != b) ? 1 : 0;
}

/*============================================================================
 * Range Functions
 *============================================================================*/

int32_t Logic_InRange(int32_t value, int32_t min, int32_t max)
{
    return (value >= min && value <= max) ? 1 : 0;
}

int32_t Logic_OutsideRange(int32_t value, int32_t min, int32_t max)
{
    return (value < min || value > max) ? 1 : 0;
}

/*============================================================================
 * Generic Evaluate Function
 *============================================================================*/

int32_t Logic_Evaluate(LogicOp_t op, const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    switch (op) {
        /* Boolean operations */
        case LOGIC_OP_AND:
            return Logic_AND(inputs, count);

        case LOGIC_OP_OR:
            return Logic_OR(inputs, count);

        case LOGIC_OP_XOR:
            return Logic_XOR(inputs, count);

        case LOGIC_OP_NAND:
            return Logic_NAND(inputs, count);

        case LOGIC_OP_NOR:
            return Logic_NOR(inputs, count);

        case LOGIC_OP_IS_TRUE:
            return Logic_IsTrue(inputs[0]);

        case LOGIC_OP_IS_FALSE:
            return Logic_IsFalse(inputs[0]);

        /* Comparison operations (need 2 inputs) */
        case LOGIC_OP_GT:
            return (count >= 2) ? Logic_GT(inputs[0], inputs[1]) : 0;

        case LOGIC_OP_GTE:
            return (count >= 2) ? Logic_GTE(inputs[0], inputs[1]) : 0;

        case LOGIC_OP_LT:
            return (count >= 2) ? Logic_LT(inputs[0], inputs[1]) : 0;

        case LOGIC_OP_LTE:
            return (count >= 2) ? Logic_LTE(inputs[0], inputs[1]) : 0;

        case LOGIC_OP_EQ:
            return (count >= 2) ? Logic_EQ(inputs[0], inputs[1]) : 0;

        case LOGIC_OP_NEQ:
            return (count >= 2) ? Logic_NEQ(inputs[0], inputs[1]) : 0;

        /* Range operations (need 3 inputs: value, min, max) */
        case LOGIC_OP_RANGE:
            return (count >= 3) ? Logic_InRange(inputs[0], inputs[1], inputs[2]) : 0;

        case LOGIC_OP_OUTSIDE:
            return (count >= 3) ? Logic_OutsideRange(inputs[0], inputs[1], inputs[2]) : 0;

        default:
            return 0;
    }
}

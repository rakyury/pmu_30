/**
 * @file math_ops.c
 * @brief Logic Engine - Math Operations Implementation
 */

#include "math_ops.h"

/*============================================================================
 * Basic Arithmetic
 *============================================================================*/

int32_t Math_Add(const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    int32_t sum = 0;
    for (uint8_t i = 0; i < count; i++) {
        sum += inputs[i];
    }
    return sum;
}

int32_t Math_Sub(int32_t a, int32_t b)
{
    return a - b;
}

int32_t Math_Mul(int32_t a, int32_t b)
{
    return a * b;
}

int32_t Math_Div(int32_t a, int32_t b)
{
    if (b == 0) return 0;  /* Safe division */
    return a / b;
}

int32_t Math_Mod(int32_t a, int32_t b)
{
    if (b == 0) return 0;  /* Safe modulo */
    return a % b;
}

int32_t Math_Abs(int32_t value)
{
    return (value < 0) ? -value : value;
}

int32_t Math_Neg(int32_t value)
{
    return -value;
}

/*============================================================================
 * Min/Max/Average
 *============================================================================*/

int32_t Math_Min(const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    int32_t min = inputs[0];
    for (uint8_t i = 1; i < count; i++) {
        if (inputs[i] < min) min = inputs[i];
    }
    return min;
}

int32_t Math_Max(const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    int32_t max = inputs[0];
    for (uint8_t i = 1; i < count; i++) {
        if (inputs[i] > max) max = inputs[i];
    }
    return max;
}

int32_t Math_Avg(const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    int32_t sum = Math_Add(inputs, count);
    return sum / (int32_t)count;
}

/*============================================================================
 * Range Operations
 *============================================================================*/

int32_t Math_Clamp(int32_t value, int32_t min, int32_t max)
{
    if (value < min) return min;
    if (value > max) return max;
    return value;
}

int32_t Math_Map(int32_t value, int32_t in_min, int32_t in_max,
                 int32_t out_min, int32_t out_max)
{
    /* Avoid division by zero */
    int32_t in_range = in_max - in_min;
    if (in_range == 0) return out_min;

    /* Calculate mapped value using 64-bit to avoid overflow */
    int64_t out_range = (int64_t)(out_max - out_min);
    int64_t value_offset = (int64_t)(value - in_min);

    return out_min + (int32_t)((value_offset * out_range) / in_range);
}

int32_t Math_Scale(int32_t value, int32_t multiplier, int32_t scale_factor)
{
    if (scale_factor == 0) return 0;

    /* Use 64-bit to avoid overflow */
    int64_t result = ((int64_t)value * multiplier) / scale_factor;

    /* Clamp to int32 range */
    if (result > INT32_MAX) return INT32_MAX;
    if (result < INT32_MIN) return INT32_MIN;

    return (int32_t)result;
}

int32_t Math_Lerp(int32_t a, int32_t b, int32_t t)
{
    /* t is 0-1000 (representing 0.0 to 1.0) */
    if (t <= 0) return a;
    if (t >= 1000) return b;

    /* a + (b - a) * t / 1000 */
    int64_t diff = (int64_t)(b - a);
    return a + (int32_t)((diff * t) / 1000);
}

/*============================================================================
 * Generic Evaluate Function
 *============================================================================*/

int32_t Math_Evaluate(MathOp_t op, const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return 0;

    switch (op) {
        case MATH_OP_ADD:
            return Math_Add(inputs, count);

        case MATH_OP_SUB:
            return (count >= 2) ? Math_Sub(inputs[0], inputs[1]) : inputs[0];

        case MATH_OP_MUL:
            return (count >= 2) ? Math_Mul(inputs[0], inputs[1]) : inputs[0];

        case MATH_OP_DIV:
            return (count >= 2) ? Math_Div(inputs[0], inputs[1]) : inputs[0];

        case MATH_OP_MOD:
            return (count >= 2) ? Math_Mod(inputs[0], inputs[1]) : inputs[0];

        case MATH_OP_ABS:
            return Math_Abs(inputs[0]);

        case MATH_OP_NEG:
            return Math_Neg(inputs[0]);

        case MATH_OP_MIN:
            return Math_Min(inputs, count);

        case MATH_OP_MAX:
            return Math_Max(inputs, count);

        case MATH_OP_AVG:
            return Math_Avg(inputs, count);

        case MATH_OP_CLAMP:
            /* inputs[0]=value, inputs[1]=min, inputs[2]=max */
            return (count >= 3) ? Math_Clamp(inputs[0], inputs[1], inputs[2]) : inputs[0];

        case MATH_OP_MAP:
            /* inputs[0]=value, [1]=in_min, [2]=in_max, [3]=out_min, [4]=out_max */
            return (count >= 5) ?
                Math_Map(inputs[0], inputs[1], inputs[2], inputs[3], inputs[4]) : inputs[0];

        case MATH_OP_SCALE:
            /* inputs[0]=value, inputs[1]=multiplier, inputs[2]=scale_factor */
            return (count >= 3) ?
                Math_Scale(inputs[0], inputs[1], inputs[2]) : inputs[0];

        default:
            return 0;
    }
}

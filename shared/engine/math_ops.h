/**
 * @file math_ops.h
 * @brief Logic Engine - Math Operations (Pure Functions)
 *
 * Note: Named math_ops.h to avoid conflict with standard math.h
 *
 * All functions are stateless and have no side effects.
 * Uses fixed-point arithmetic for embedded systems compatibility.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef ENGINE_MATH_OPS_H
#define ENGINE_MATH_OPS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Math Operation Types
 *============================================================================*/

typedef enum {
    MATH_OP_ADD        = 0x00,  /**< Sum of all inputs */
    MATH_OP_SUB        = 0x01,  /**< a - b */
    MATH_OP_MUL        = 0x02,  /**< a * b */
    MATH_OP_DIV        = 0x03,  /**< a / b (integer division) */
    MATH_OP_MOD        = 0x04,  /**< a % b */
    MATH_OP_ABS        = 0x05,  /**< Absolute value */
    MATH_OP_NEG        = 0x06,  /**< Negate */
    MATH_OP_MIN        = 0x07,  /**< Minimum of inputs */
    MATH_OP_MAX        = 0x08,  /**< Maximum of inputs */
    MATH_OP_AVG        = 0x09,  /**< Average of inputs */
    MATH_OP_CLAMP      = 0x0A,  /**< Clamp to range */
    MATH_OP_MAP        = 0x0B,  /**< Map from one range to another */
    MATH_OP_SCALE      = 0x0C,  /**< Multiply by scale factor (fixed-point) */
} MathOp_t;

/*============================================================================
 * Basic Arithmetic
 *============================================================================*/

/**
 * Sum of all inputs.
 *
 * @param inputs Array of input values
 * @param count Number of inputs
 * @return Sum of all values
 */
int32_t Math_Add(const int32_t* inputs, uint8_t count);

/**
 * Subtraction: a - b.
 */
int32_t Math_Sub(int32_t a, int32_t b);

/**
 * Multiplication: a * b.
 * Note: Be careful of overflow with large values.
 */
int32_t Math_Mul(int32_t a, int32_t b);

/**
 * Integer division: a / b.
 * Returns 0 if b is 0 (no exception).
 */
int32_t Math_Div(int32_t a, int32_t b);

/**
 * Modulo: a % b.
 * Returns 0 if b is 0.
 */
int32_t Math_Mod(int32_t a, int32_t b);

/**
 * Absolute value.
 */
int32_t Math_Abs(int32_t value);

/**
 * Negate value.
 */
int32_t Math_Neg(int32_t value);

/*============================================================================
 * Min/Max/Average
 *============================================================================*/

/**
 * Minimum of all inputs.
 */
int32_t Math_Min(const int32_t* inputs, uint8_t count);

/**
 * Maximum of all inputs.
 */
int32_t Math_Max(const int32_t* inputs, uint8_t count);

/**
 * Average of all inputs (integer division, rounds toward zero).
 */
int32_t Math_Avg(const int32_t* inputs, uint8_t count);

/*============================================================================
 * Range Operations
 *============================================================================*/

/**
 * Clamp value to range [min, max].
 *
 * @param value Input value
 * @param min Minimum output
 * @param max Maximum output
 * @return Clamped value
 */
int32_t Math_Clamp(int32_t value, int32_t min, int32_t max);

/**
 * Map value from one range to another (linear interpolation).
 *
 * Example: Map 500 from [0,1000] to [0,100] = 50
 *
 * @param value Input value
 * @param in_min Input range minimum
 * @param in_max Input range maximum
 * @param out_min Output range minimum
 * @param out_max Output range maximum
 * @return Mapped value
 */
int32_t Math_Map(int32_t value, int32_t in_min, int32_t in_max,
                 int32_t out_min, int32_t out_max);

/**
 * Scale value by fixed-point multiplier.
 *
 * Result = (value * multiplier) / scale_factor
 *
 * Example: Scale 1000 by 1.5 using scale_factor=1000:
 *          Math_Scale(1000, 1500, 1000) = 1500
 *
 * @param value Input value
 * @param multiplier Multiplier (fixed-point)
 * @param scale_factor Divisor for fixed-point (e.g., 1000 for 3 decimal places)
 * @return Scaled value
 */
int32_t Math_Scale(int32_t value, int32_t multiplier, int32_t scale_factor);

/**
 * Linear interpolation between two values.
 *
 * Result = a + (b - a) * t / 1000
 * where t is 0-1000 (0.0 to 1.0 in fixed-point)
 *
 * @param a Start value
 * @param b End value
 * @param t Interpolation factor (0-1000)
 * @return Interpolated value
 */
int32_t Math_Lerp(int32_t a, int32_t b, int32_t t);

/*============================================================================
 * Generic Evaluate Function
 *============================================================================*/

/**
 * Evaluate math operation by type.
 *
 * @param op Math operation type
 * @param inputs Input values array
 * @param count Number of inputs
 * @return Result of operation
 */
int32_t Math_Evaluate(MathOp_t op, const int32_t* inputs, uint8_t count);

#ifdef __cplusplus
}
#endif

#endif /* ENGINE_MATH_OPS_H */

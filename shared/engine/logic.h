/**
 * @file logic.h
 * @brief Logic Engine - Logic Operations (Pure Functions)
 *
 * All functions are stateless and have no side effects.
 * Can be used in firmware, desktop apps, or unit tests.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef ENGINE_LOGIC_H
#define ENGINE_LOGIC_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Logic Operation Types
 *============================================================================*/

typedef enum {
    LOGIC_OP_AND       = 0x00,  /**< All inputs must be true */
    LOGIC_OP_OR        = 0x01,  /**< Any input must be true */
    LOGIC_OP_XOR       = 0x02,  /**< Odd number of true inputs */
    LOGIC_OP_NAND      = 0x03,  /**< NOT AND */
    LOGIC_OP_NOR       = 0x04,  /**< NOT OR */
    LOGIC_OP_NOT       = 0x05,  /**< Invert single input */

    LOGIC_OP_GT        = 0x10,  /**< a > b */
    LOGIC_OP_GTE       = 0x11,  /**< a >= b */
    LOGIC_OP_LT        = 0x12,  /**< a < b */
    LOGIC_OP_LTE       = 0x13,  /**< a <= b */
    LOGIC_OP_EQ        = 0x14,  /**< a == b */
    LOGIC_OP_NEQ       = 0x15,  /**< a != b */

    LOGIC_OP_RANGE     = 0x20,  /**< min <= value <= max */
    LOGIC_OP_OUTSIDE   = 0x21,  /**< value < min OR value > max */
} LogicOp_t;

/*============================================================================
 * Boolean Logic Functions
 *============================================================================*/

/**
 * Logical AND - returns 1 if ALL inputs are non-zero.
 *
 * @param inputs Array of input values
 * @param count Number of inputs (1-8)
 * @return 1 if all non-zero, 0 otherwise
 */
int32_t Logic_AND(const int32_t* inputs, uint8_t count);

/**
 * Logical OR - returns 1 if ANY input is non-zero.
 *
 * @param inputs Array of input values
 * @param count Number of inputs (1-8)
 * @return 1 if any non-zero, 0 otherwise
 */
int32_t Logic_OR(const int32_t* inputs, uint8_t count);

/**
 * Logical XOR - returns 1 if ODD number of inputs are non-zero.
 *
 * @param inputs Array of input values
 * @param count Number of inputs (1-8)
 * @return 1 if odd count of non-zero, 0 otherwise
 */
int32_t Logic_XOR(const int32_t* inputs, uint8_t count);

/**
 * Logical NAND - returns NOT(AND(inputs)).
 */
int32_t Logic_NAND(const int32_t* inputs, uint8_t count);

/**
 * Logical NOR - returns NOT(OR(inputs)).
 */
int32_t Logic_NOR(const int32_t* inputs, uint8_t count);

/**
 * Logical NOT - inverts single input.
 *
 * @param input Input value
 * @return 1 if input is 0, 0 otherwise
 */
int32_t Logic_NOT(int32_t input);

/*============================================================================
 * Comparison Functions
 *============================================================================*/

/**
 * Greater than comparison.
 *
 * @param a First operand
 * @param b Second operand
 * @return 1 if a > b, 0 otherwise
 */
int32_t Logic_GT(int32_t a, int32_t b);

/**
 * Greater than or equal comparison.
 */
int32_t Logic_GTE(int32_t a, int32_t b);

/**
 * Less than comparison.
 */
int32_t Logic_LT(int32_t a, int32_t b);

/**
 * Less than or equal comparison.
 */
int32_t Logic_LTE(int32_t a, int32_t b);

/**
 * Equality comparison.
 */
int32_t Logic_EQ(int32_t a, int32_t b);

/**
 * Not equal comparison.
 */
int32_t Logic_NEQ(int32_t a, int32_t b);

/*============================================================================
 * Range Functions
 *============================================================================*/

/**
 * Check if value is within range [min, max].
 *
 * @param value Value to check
 * @param min Minimum (inclusive)
 * @param max Maximum (inclusive)
 * @return 1 if min <= value <= max, 0 otherwise
 */
int32_t Logic_InRange(int32_t value, int32_t min, int32_t max);

/**
 * Check if value is outside range (value < min OR value > max).
 */
int32_t Logic_OutsideRange(int32_t value, int32_t min, int32_t max);

/*============================================================================
 * Generic Evaluate Function
 *============================================================================*/

/**
 * Evaluate logic operation by type.
 *
 * This is a dispatcher that calls the appropriate function based on op type.
 * For comparison ops, uses inputs[0] and inputs[1] as a and b.
 * For range ops, uses inputs[0] as value, inputs[1] as min, inputs[2] as max.
 *
 * @param op Logic operation type
 * @param inputs Input values array
 * @param count Number of inputs
 * @return Result of operation (0 or 1 for boolean ops)
 */
int32_t Logic_Evaluate(LogicOp_t op, const int32_t* inputs, uint8_t count);

#ifdef __cplusplus
}
#endif

#endif /* ENGINE_LOGIC_H */

/**
 * @file switch.h
 * @brief Logic Engine - Switch/Selector Functions (Pure Functions)
 *
 * Switch is a pure selector - no state required.
 * Selects one of N values based on selector input.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef ENGINE_SWITCH_H
#define ENGINE_SWITCH_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Switch Limits
 *============================================================================*/

#define SWITCH_MAX_CASES    16   /**< Maximum case statements */
#define SWITCH_MAX_VALUES   16   /**< Maximum values for selector */

/*============================================================================
 * Switch Case Structure
 *============================================================================*/

/**
 * Case definition for Switch_Case function.
 */
typedef struct {
    int32_t match_value;    /**< Value to match against input */
    int32_t output_value;   /**< Output when matched */
} SwitchCase_t;

/*============================================================================
 * Switch Functions
 *============================================================================*/

/**
 * Select one of N values based on selector index.
 *
 * Similar to array indexing: values[selector]
 * Selector is clamped to valid range [0, count-1].
 *
 * @param values Array of values to select from
 * @param count Number of values (1-16)
 * @param selector Index to select (0-based)
 * @return Selected value
 */
int32_t Switch_Select(const int32_t* values, uint8_t count, int32_t selector);

/**
 * Case statement - match input against cases.
 *
 * Similar to C switch statement. Returns output_value for first matching case.
 * If no match, returns default_value.
 *
 * @param input Input value to match
 * @param cases Array of case definitions
 * @param count Number of cases (1-16)
 * @param default_value Value to return if no match
 * @return Output value from matched case, or default_value
 */
int32_t Switch_Case(int32_t input, const SwitchCase_t* cases, uint8_t count,
                    int32_t default_value);

/**
 * Range case - select output based on which range input falls into.
 *
 * Each threshold defines the start of a new range.
 * Example: thresholds={0, 100, 200}, outputs={0, 1, 2}
 *   input < 0    -> outputs[0] = 0
 *   0 <= x < 100 -> outputs[0] = 0
 *   100 <= x < 200 -> outputs[1] = 1
 *   x >= 200     -> outputs[2] = 2
 *
 * @param input Input value
 * @param thresholds Array of threshold values (sorted ascending)
 * @param outputs Array of output values
 * @param count Number of thresholds/outputs
 * @return Output value for the range containing input
 */
int32_t Switch_RangeCase(int32_t input, const int32_t* thresholds,
                         const int32_t* outputs, uint8_t count);

/**
 * Multiplexer - select based on multiple boolean conditions.
 *
 * Checks conditions in order, returns first matching output.
 * Like if-else-if chain.
 *
 * @param conditions Array of condition values (non-zero = true)
 * @param outputs Array of output values
 * @param count Number of conditions
 * @param default_value Value to return if no condition is true
 * @return Output for first true condition, or default_value
 */
int32_t Switch_Mux(const int32_t* conditions, const int32_t* outputs,
                   uint8_t count, int32_t default_value);

/**
 * Priority encoder - return index of first non-zero input.
 *
 * @param inputs Array of input values
 * @param count Number of inputs
 * @return Index of first non-zero input (0-based), or -1 if all zero
 */
int32_t Switch_Priority(const int32_t* inputs, uint8_t count);

/**
 * Ternary operator: condition ? true_value : false_value
 */
int32_t Switch_Ternary(int32_t condition, int32_t true_value, int32_t false_value);

#ifdef __cplusplus
}
#endif

#endif /* ENGINE_SWITCH_H */

/**
 * @file switch.c
 * @brief Logic Engine - Switch/Selector Implementation
 */

#include "switch.h"

/*============================================================================
 * Switch Functions
 *============================================================================*/

int32_t Switch_Select(const int32_t* values, uint8_t count, int32_t selector)
{
    if (!values || count == 0) return 0;

    /* Clamp selector to valid range */
    if (selector < 0) selector = 0;
    if (selector >= (int32_t)count) selector = count - 1;

    return values[selector];
}

int32_t Switch_Case(int32_t input, const SwitchCase_t* cases, uint8_t count,
                    int32_t default_value)
{
    if (!cases || count == 0) return default_value;

    for (uint8_t i = 0; i < count; i++) {
        if (input == cases[i].match_value) {
            return cases[i].output_value;
        }
    }

    return default_value;
}

int32_t Switch_RangeCase(int32_t input, const int32_t* thresholds,
                         const int32_t* outputs, uint8_t count)
{
    if (!thresholds || !outputs || count == 0) return 0;

    /* Find which range the input falls into */
    /* Thresholds are sorted ascending, find last threshold <= input */
    uint8_t index = 0;
    for (uint8_t i = 0; i < count; i++) {
        if (input >= thresholds[i]) {
            index = i;
        } else {
            break;
        }
    }

    return outputs[index];
}

int32_t Switch_Mux(const int32_t* conditions, const int32_t* outputs,
                   uint8_t count, int32_t default_value)
{
    if (!conditions || !outputs || count == 0) return default_value;

    for (uint8_t i = 0; i < count; i++) {
        if (conditions[i] != 0) {
            return outputs[i];
        }
    }

    return default_value;
}

int32_t Switch_Priority(const int32_t* inputs, uint8_t count)
{
    if (!inputs || count == 0) return -1;

    for (uint8_t i = 0; i < count; i++) {
        if (inputs[i] != 0) {
            return i;
        }
    }

    return -1;
}

int32_t Switch_Ternary(int32_t condition, int32_t true_value, int32_t false_value)
{
    return (condition != 0) ? true_value : false_value;
}

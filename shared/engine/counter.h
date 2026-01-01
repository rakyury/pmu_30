/**
 * @file counter.h
 * @brief Logic Engine - Counter Functions (Stateful but Pure)
 *
 * Counter with increment/decrement/reset triggers.
 * State is passed as parameter - function has no internal state.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef ENGINE_COUNTER_H
#define ENGINE_COUNTER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Counter State
 *============================================================================*/

typedef struct {
    int32_t value;          /**< Current counter value */
    uint8_t  last_inc;      /**< Last increment trigger state (for edge) */
    uint8_t  last_dec;      /**< Last decrement trigger state */
    uint8_t  last_reset;    /**< Last reset trigger state */
    uint8_t  reserved;
} Counter_State_t;

/*============================================================================
 * Counter Configuration
 *============================================================================*/

typedef struct {
    int32_t initial_value;  /**< Initial value after reset */
    int32_t min_value;      /**< Minimum value (clamp or wrap) */
    int32_t max_value;      /**< Maximum value (clamp or wrap) */
    int32_t step;           /**< Increment/decrement step (default: 1) */
    uint8_t  wrap;          /**< 1=wrap at limits, 0=clamp */
    uint8_t  edge_mode;     /**< 0=level, 1=rising edge triggers */
    uint8_t  reserved[2];
} Counter_Config_t;

/*============================================================================
 * Counter Functions
 *============================================================================*/

/**
 * Initialize counter state.
 *
 * @param state Counter state to initialize
 * @param config Counter configuration (for initial value)
 */
void Counter_Init(Counter_State_t* state, const Counter_Config_t* config);

/**
 * Reset counter to initial value.
 */
void Counter_Reset(Counter_State_t* state, const Counter_Config_t* config);

/**
 * Update counter and get current value.
 *
 * @param state Counter state (modified)
 * @param config Counter configuration
 * @param inc_trigger Increment trigger (non-zero = active)
 * @param dec_trigger Decrement trigger (non-zero = active)
 * @param reset_trigger Reset trigger (non-zero = reset)
 * @return Current counter value
 */
int32_t Counter_Update(Counter_State_t* state, const Counter_Config_t* config,
                       int32_t inc_trigger, int32_t dec_trigger,
                       int32_t reset_trigger);

/**
 * Get current counter value.
 */
int32_t Counter_GetValue(const Counter_State_t* state);

/**
 * Set counter value directly.
 */
void Counter_SetValue(Counter_State_t* state, const Counter_Config_t* config,
                      int32_t value);

/**
 * Increment counter by step.
 */
int32_t Counter_Increment(Counter_State_t* state, const Counter_Config_t* config);

/**
 * Decrement counter by step.
 */
int32_t Counter_Decrement(Counter_State_t* state, const Counter_Config_t* config);

/**
 * Check if counter is at minimum.
 */
bool Counter_IsAtMin(const Counter_State_t* state, const Counter_Config_t* config);

/**
 * Check if counter is at maximum.
 */
bool Counter_IsAtMax(const Counter_State_t* state, const Counter_Config_t* config);

#ifdef __cplusplus
}
#endif

#endif /* ENGINE_COUNTER_H */

/**
 * @file counter.c
 * @brief Logic Engine - Counter Implementation
 */

#include "counter.h"
#include <string.h>

/*============================================================================
 * Helper Functions
 *============================================================================*/

static int32_t apply_limits(int32_t value, const Counter_Config_t* config)
{
    if (config->wrap) {
        /* Wrap around */
        int32_t range = config->max_value - config->min_value + 1;
        if (range <= 0) return value;

        while (value > config->max_value) {
            value -= range;
        }
        while (value < config->min_value) {
            value += range;
        }
    } else {
        /* Clamp */
        if (value < config->min_value) value = config->min_value;
        if (value > config->max_value) value = config->max_value;
    }
    return value;
}

static bool detect_rising_edge(uint8_t* last_state, int32_t current)
{
    bool current_high = (current != 0);
    bool last_high = (*last_state != 0);
    *last_state = current_high ? 1 : 0;
    return current_high && !last_high;
}

/*============================================================================
 * Counter Functions
 *============================================================================*/

void Counter_Init(Counter_State_t* state, const Counter_Config_t* config)
{
    if (!state) return;
    memset(state, 0, sizeof(Counter_State_t));

    if (config) {
        state->value = config->initial_value;
    }
}

void Counter_Reset(Counter_State_t* state, const Counter_Config_t* config)
{
    if (!state) return;

    state->value = config ? config->initial_value : 0;
    /* Don't reset edge detection state */
}

int32_t Counter_Update(Counter_State_t* state, const Counter_Config_t* config,
                       int32_t inc_trigger, int32_t dec_trigger,
                       int32_t reset_trigger)
{
    if (!state || !config) return 0;

    /* Check reset first */
    if (config->edge_mode) {
        if (detect_rising_edge(&state->last_reset, reset_trigger)) {
            Counter_Reset(state, config);
            return state->value;
        }
    } else {
        if (reset_trigger != 0) {
            Counter_Reset(state, config);
            return state->value;
        }
    }

    /* Check increment */
    bool do_increment = false;
    if (config->edge_mode) {
        do_increment = detect_rising_edge(&state->last_inc, inc_trigger);
    } else {
        do_increment = (inc_trigger != 0);
        state->last_inc = (inc_trigger != 0) ? 1 : 0;
    }

    if (do_increment) {
        state->value += config->step;
        state->value = apply_limits(state->value, config);
    }

    /* Check decrement */
    bool do_decrement = false;
    if (config->edge_mode) {
        do_decrement = detect_rising_edge(&state->last_dec, dec_trigger);
    } else {
        do_decrement = (dec_trigger != 0);
        state->last_dec = (dec_trigger != 0) ? 1 : 0;
    }

    if (do_decrement) {
        state->value -= config->step;
        state->value = apply_limits(state->value, config);
    }

    return state->value;
}

int32_t Counter_GetValue(const Counter_State_t* state)
{
    return state ? state->value : 0;
}

void Counter_SetValue(Counter_State_t* state, const Counter_Config_t* config,
                      int32_t value)
{
    if (!state) return;

    state->value = config ? apply_limits(value, config) : value;
}

int32_t Counter_Increment(Counter_State_t* state, const Counter_Config_t* config)
{
    if (!state || !config) return 0;

    state->value += config->step;
    state->value = apply_limits(state->value, config);
    return state->value;
}

int32_t Counter_Decrement(Counter_State_t* state, const Counter_Config_t* config)
{
    if (!state || !config) return 0;

    state->value -= config->step;
    state->value = apply_limits(state->value, config);
    return state->value;
}

bool Counter_IsAtMin(const Counter_State_t* state, const Counter_Config_t* config)
{
    if (!state || !config) return false;
    return state->value <= config->min_value;
}

bool Counter_IsAtMax(const Counter_State_t* state, const Counter_Config_t* config)
{
    if (!state || !config) return false;
    return state->value >= config->max_value;
}

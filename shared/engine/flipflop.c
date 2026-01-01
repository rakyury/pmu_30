/**
 * @file flipflop.c
 * @brief Logic Engine - Flip-Flops and Latches Implementation
 */

#include "flipflop.h"
#include <string.h>

/*============================================================================
 * Initialization Functions
 *============================================================================*/

void FF_Init(FlipFlop_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(FlipFlop_State_t));
}

void FF_Reset(FlipFlop_State_t* state, uint8_t q_value)
{
    if (!state) return;
    state->q = q_value ? 1 : 0;
    state->last_clk = 0;
    state->initialized = 1;
}

/*============================================================================
 * Edge Detection Helpers
 *============================================================================*/

int32_t DetectRisingEdge(uint8_t* last_state, int32_t current)
{
    if (!last_state) return 0;

    uint8_t curr_high = (current != 0) ? 1 : 0;
    uint8_t prev_high = *last_state;
    *last_state = curr_high;

    return (curr_high && !prev_high) ? 1 : 0;
}

int32_t DetectFallingEdge(uint8_t* last_state, int32_t current)
{
    if (!last_state) return 0;

    uint8_t curr_high = (current != 0) ? 1 : 0;
    uint8_t prev_high = *last_state;
    *last_state = curr_high;

    return (!curr_high && prev_high) ? 1 : 0;
}

int32_t DetectAnyEdge(uint8_t* last_state, int32_t current)
{
    if (!last_state) return 0;

    uint8_t curr_high = (current != 0) ? 1 : 0;
    uint8_t prev_high = *last_state;
    *last_state = curr_high;

    return (curr_high != prev_high) ? 1 : 0;
}

/*============================================================================
 * SR Latch Implementation
 *============================================================================*/

int32_t SR_Latch_Update(FlipFlop_State_t* state, int32_t set, int32_t reset)
{
    if (!state) return 0;

    uint8_t s = (set != 0) ? 1 : 0;
    uint8_t r = (reset != 0) ? 1 : 0;

    if (s && r) {
        /* Invalid state - reset wins (common implementation) */
        state->q = 0;
    } else if (s) {
        state->q = 1;
    } else if (r) {
        state->q = 0;
    }
    /* else: hold current state */

    state->initialized = 1;
    return state->q;
}

int32_t SR_Latch_Priority(FlipFlop_State_t* state, int32_t set, int32_t reset,
                          bool reset_priority)
{
    if (!state) return 0;

    uint8_t s = (set != 0) ? 1 : 0;
    uint8_t r = (reset != 0) ? 1 : 0;

    if (s && r) {
        /* Both active - use priority */
        state->q = reset_priority ? 0 : 1;
    } else if (s) {
        state->q = 1;
    } else if (r) {
        state->q = 0;
    }
    /* else: hold current state */

    state->initialized = 1;
    return state->q;
}

/*============================================================================
 * D Flip-Flop Implementation
 *============================================================================*/

int32_t D_FlipFlop_Update(FlipFlop_State_t* state, int32_t d, int32_t clk)
{
    if (!state) return 0;

    uint8_t clk_high = (clk != 0) ? 1 : 0;

    /* Detect rising edge of clock */
    if (clk_high && !state->last_clk) {
        /* Rising edge - capture D */
        state->q = (d != 0) ? 1 : 0;
    }

    state->last_clk = clk_high;
    state->initialized = 1;
    return state->q;
}

int32_t D_Latch_Update(FlipFlop_State_t* state, int32_t d, int32_t enable)
{
    if (!state) return 0;

    if (enable != 0) {
        /* Transparent - follow D */
        state->q = (d != 0) ? 1 : 0;
    }
    /* else: hold current state */

    state->initialized = 1;
    return state->q;
}

/*============================================================================
 * T Flip-Flop Implementation
 *============================================================================*/

int32_t T_FlipFlop_Update(FlipFlop_State_t* state, int32_t t, int32_t clk)
{
    if (!state) return 0;

    uint8_t clk_high = (clk != 0) ? 1 : 0;

    /* Detect rising edge of clock */
    if (clk_high && !state->last_clk) {
        if (t != 0) {
            /* Toggle on rising edge when T=1 */
            state->q = !state->q;
        }
    }

    state->last_clk = clk_high;
    state->initialized = 1;
    return state->q;
}

int32_t Toggle_Update(FlipFlop_State_t* state, int32_t trigger)
{
    if (!state) return 0;

    uint8_t trig_high = (trigger != 0) ? 1 : 0;

    /* Detect rising edge */
    if (trig_high && !state->last_clk) {
        state->q = !state->q;
    }

    state->last_clk = trig_high;
    state->initialized = 1;
    return state->q;
}

/*============================================================================
 * JK Flip-Flop Implementation
 *============================================================================*/

int32_t JK_FlipFlop_Update(FlipFlop_State_t* state,
                           int32_t j, int32_t k, int32_t clk)
{
    if (!state) return 0;

    uint8_t clk_high = (clk != 0) ? 1 : 0;

    /* Detect rising edge of clock */
    if (clk_high && !state->last_clk) {
        uint8_t j_active = (j != 0) ? 1 : 0;
        uint8_t k_active = (k != 0) ? 1 : 0;

        if (j_active && k_active) {
            /* Toggle */
            state->q = !state->q;
        } else if (j_active) {
            /* Set */
            state->q = 1;
        } else if (k_active) {
            /* Reset */
            state->q = 0;
        }
        /* else: hold */
    }

    state->last_clk = clk_high;
    state->initialized = 1;
    return state->q;
}

/*============================================================================
 * Getter Functions
 *============================================================================*/

int32_t FF_GetQ(const FlipFlop_State_t* state)
{
    return state ? state->q : 0;
}

int32_t FF_GetQBar(const FlipFlop_State_t* state)
{
    return state ? !state->q : 1;
}

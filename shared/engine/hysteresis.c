/**
 * @file hysteresis.c
 * @brief Logic Engine - Hysteresis Comparator Implementation
 */

#include "hysteresis.h"
#include <string.h>

/*============================================================================
 * Simple Hysteresis Implementation
 *============================================================================*/

void Hysteresis_Init(Hysteresis_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(Hysteresis_State_t));
}

int32_t Hysteresis_Update(Hysteresis_State_t* state,
                          const Hysteresis_Config_t* config,
                          int32_t input)
{
    if (!state || !config) return 0;

    if (!state->initialized) {
        /* Initial state based on input vs midpoint */
        int32_t mid = (config->threshold_high + config->threshold_low) / 2;
        state->output = (input >= mid) ? 1 : 0;
        state->initialized = 1;
    } else {
        /* Apply hysteresis */
        if (state->output) {
            /* Currently HIGH, check for transition LOW */
            if (input <= config->threshold_low) {
                state->output = 0;
            }
        } else {
            /* Currently LOW, check for transition HIGH */
            if (input >= config->threshold_high) {
                state->output = 1;
            }
        }
    }

    return config->invert ? !state->output : state->output;
}

int32_t Hysteresis_GetOutput(const Hysteresis_State_t* state)
{
    return state ? state->output : 0;
}

void Hysteresis_Reset(Hysteresis_State_t* state, uint8_t output)
{
    if (!state) return;
    state->output = output ? 1 : 0;
    state->initialized = 1;
}

Hysteresis_Config_t Hysteresis_ConfigFromBand(int32_t center, int32_t band)
{
    Hysteresis_Config_t config = {0};
    int32_t half_band = band / 2;
    config.threshold_high = center + half_band;
    config.threshold_low = center - half_band;
    config.invert = 0;
    return config;
}

/*============================================================================
 * Window Comparator Implementation
 *============================================================================*/

void Window_Init(Window_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(Window_State_t));
}

int32_t Window_Update(Window_State_t* state,
                      const Window_Config_t* config,
                      int32_t input)
{
    if (!state || !config) return 0;

    int32_t hyst = config->hysteresis;

    if (!state->initialized) {
        /* Initial state based on whether input is in window */
        state->output = (input >= config->low_threshold &&
                         input <= config->high_threshold) ? 1 : 0;
        state->initialized = 1;
    } else {
        if (state->output) {
            /* Currently IN window, check for exit */
            /* Must go below (low - hyst) or above (high + hyst) */
            if (input < (config->low_threshold - hyst) ||
                input > (config->high_threshold + hyst)) {
                state->output = 0;
            }
        } else {
            /* Currently OUT of window, check for entry */
            /* Must be within (low + hyst) to (high - hyst) */
            if (input >= (config->low_threshold + hyst) &&
                input <= (config->high_threshold - hyst)) {
                state->output = 1;
            }
        }
    }

    return config->invert ? !state->output : state->output;
}

int32_t Window_GetOutput(const Window_State_t* state)
{
    return state ? state->output : 0;
}

void Window_Reset(Window_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(Window_State_t));
}

/*============================================================================
 * Multi-Level Implementation
 *============================================================================*/

void MultiLevel_Init(MultiLevel_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(MultiLevel_State_t));
}

int32_t MultiLevel_Update(MultiLevel_State_t* state,
                          const MultiLevel_Config_t* config,
                          int32_t input)
{
    if (!state || !config) return 0;

    uint8_t count = config->level_count;
    if (count < 2) count = 2;
    if (count > HYST_MAX_LEVELS) count = HYST_MAX_LEVELS;

    if (!state->initialized) {
        /* Find initial level based on input */
        state->current_level = 0;
        for (uint8_t i = 1; i < count; i++) {
            if (input >= config->thresholds[i].threshold_up) {
                state->current_level = i;
            } else {
                break;
            }
        }
        state->initialized = 1;
    } else {
        uint8_t level = state->current_level;

        /* Check for level up */
        while (level < count - 1) {
            if (input >= config->thresholds[level + 1].threshold_up) {
                level++;
            } else {
                break;
            }
        }

        /* Check for level down */
        while (level > 0) {
            if (input <= config->thresholds[level].threshold_down) {
                level--;
            } else {
                break;
            }
        }

        state->current_level = level;
    }

    return state->current_level;
}

int32_t MultiLevel_GetLevel(const MultiLevel_State_t* state)
{
    return state ? state->current_level : 0;
}

void MultiLevel_Reset(MultiLevel_State_t* state, uint8_t level)
{
    if (!state) return;
    state->current_level = level;
    state->initialized = 1;
}

/*============================================================================
 * Pure Comparator Functions
 *============================================================================*/

int32_t Compare_GE(int32_t input, int32_t threshold)
{
    return (input >= threshold) ? 1 : 0;
}

int32_t Compare_GT(int32_t input, int32_t threshold)
{
    return (input > threshold) ? 1 : 0;
}

int32_t Compare_InRange(int32_t input, int32_t low, int32_t high)
{
    return (input >= low && input <= high) ? 1 : 0;
}

int32_t Deadband(int32_t input, int32_t center, int32_t deadband)
{
    int32_t diff = input - center;

    if (diff > 0) {
        if (diff <= deadband) return 0;
        return diff - deadband;
    } else if (diff < 0) {
        if (diff >= -deadband) return 0;
        return diff + deadband;
    }

    return 0;
}

/**
 * @file filter.c
 * @brief Logic Engine - Signal Filters Implementation
 */

#include "filter.h"
#include <string.h>

/*============================================================================
 * Simple Moving Average Implementation
 *============================================================================*/

void SMA_Init(SMA_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(SMA_State_t));
}

int32_t SMA_Update(SMA_State_t* state, const SMA_Config_t* config, int32_t input)
{
    if (!state || !config) return input;

    uint8_t window = config->window_size;
    if (window == 0 || window > FILTER_MAX_SAMPLES) {
        window = 1;
    }

    /* If buffer is full, subtract oldest sample from sum */
    if (state->count >= window) {
        state->sum -= state->samples[state->index];
    }

    /* Add new sample */
    state->samples[state->index] = input;
    state->sum += input;

    /* Update index (circular) */
    state->index = (state->index + 1) % window;

    /* Update count */
    if (state->count < window) {
        state->count++;
    }

    /* Return average */
    return state->sum / state->count;
}

int32_t SMA_GetValue(const SMA_State_t* state, const SMA_Config_t* config)
{
    (void)config;
    if (!state || state->count == 0) return 0;
    return state->sum / state->count;
}

void SMA_Reset(SMA_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(SMA_State_t));
}

/*============================================================================
 * Exponential Moving Average Implementation
 *============================================================================*/

void EMA_Init(EMA_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(EMA_State_t));
}

int32_t EMA_Update(EMA_State_t* state, const EMA_Config_t* config, int32_t input)
{
    if (!state || !config) return input;

    if (!state->initialized) {
        state->value = input;
        state->initialized = 1;
        return input;
    }

    /*
     * EMA formula: output = alpha * input + (1 - alpha) * prev
     * With integer math: output = (alpha * input + (256 - alpha) * prev) / 256
     */
    uint8_t alpha = config->alpha;
    if (alpha == 0) alpha = 1;  /* Prevent division issues */

    int64_t result = ((int64_t)alpha * input +
                      (int64_t)(FILTER_ALPHA_SCALE - alpha) * state->value)
                     / FILTER_ALPHA_SCALE;

    state->value = (int32_t)result;
    return state->value;
}

int32_t EMA_GetValue(const EMA_State_t* state)
{
    return state ? state->value : 0;
}

void EMA_Reset(EMA_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(EMA_State_t));
}

/*============================================================================
 * Low-Pass Filter Implementation
 *============================================================================*/

void LPF_Init(LPF_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(LPF_State_t));
}

int32_t LPF_Update(LPF_State_t* state, const LPF_Config_t* config,
                   int32_t input, uint32_t dt_ms)
{
    if (!state || !config) return input;
    if (dt_ms == 0) return LPF_GetValue(state, config);

    uint16_t scale = config->scale > 0 ? config->scale : 1000;

    if (!state->initialized) {
        state->value = (int64_t)input * scale;
        state->initialized = 1;
        return input;
    }

    uint16_t tau = config->time_constant_ms;
    if (tau == 0) tau = 1;  /* Prevent division by zero */

    /*
     * First-order low-pass IIR:
     * alpha = dt / (tau + dt)
     * output = alpha * input + (1 - alpha) * prev
     *
     * Rewritten for integer math:
     * output = (dt * input + tau * prev) / (tau + dt)
     */
    int64_t scaled_input = (int64_t)input * scale;
    uint32_t denom = tau + dt_ms;

    state->value = ((int64_t)dt_ms * scaled_input +
                    (int64_t)tau * state->value) / denom;

    return (int32_t)(state->value / scale);
}

int32_t LPF_GetValue(const LPF_State_t* state, const LPF_Config_t* config)
{
    if (!state) return 0;
    uint16_t scale = (config && config->scale > 0) ? config->scale : 1000;
    return (int32_t)(state->value / scale);
}

void LPF_Reset(LPF_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(LPF_State_t));
}

/*============================================================================
 * Median Filter Implementation
 *============================================================================*/

void Median_Init(Median_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(Median_State_t));
}

/**
 * Find median of array using partial selection sort.
 * Efficient for small arrays (window_size <= 16).
 */
static int32_t find_median(const int32_t* samples, uint8_t count)
{
    if (count == 0) return 0;
    if (count == 1) return samples[0];

    /* Copy to temp array for sorting */
    int32_t temp[FILTER_MAX_SAMPLES];
    memcpy(temp, samples, count * sizeof(int32_t));

    /* Partial sort - only need to find middle element(s) */
    uint8_t mid = count / 2;

    /* Selection sort up to mid+1 elements */
    for (uint8_t i = 0; i <= mid; i++) {
        uint8_t min_idx = i;
        for (uint8_t j = i + 1; j < count; j++) {
            if (temp[j] < temp[min_idx]) {
                min_idx = j;
            }
        }
        if (min_idx != i) {
            int32_t swap = temp[i];
            temp[i] = temp[min_idx];
            temp[min_idx] = swap;
        }
    }

    /* Return median */
    if (count % 2 == 1) {
        return temp[mid];
    } else {
        /* Average of two middle elements */
        return (temp[mid - 1] + temp[mid]) / 2;
    }
}

int32_t Median_Update(Median_State_t* state, const Median_Config_t* config,
                      int32_t input)
{
    if (!state || !config) return input;

    uint8_t window = config->window_size;
    if (window == 0 || window > FILTER_MAX_SAMPLES) {
        window = 3;  /* Default to 3-sample median */
    }

    /* Add new sample */
    state->samples[state->index] = input;
    state->index = (state->index + 1) % window;

    if (state->count < window) {
        state->count++;
    }

    return find_median(state->samples, state->count);
}

int32_t Median_GetValue(const Median_State_t* state, const Median_Config_t* config)
{
    (void)config;
    if (!state || state->count == 0) return 0;
    return find_median(state->samples, state->count);
}

void Median_Reset(Median_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(Median_State_t));
}

/*============================================================================
 * Rate Limiter Implementation
 *============================================================================*/

void RateLimiter_Init(RateLimiter_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(RateLimiter_State_t));
}

int32_t RateLimiter_Update(RateLimiter_State_t* state,
                           const RateLimiter_Config_t* config,
                           int32_t target, uint32_t dt_ms)
{
    if (!state || !config) return target;

    if (!state->initialized) {
        state->value = target;
        state->initialized = 1;
        return target;
    }

    if (dt_ms == 0) return state->value;

    int32_t diff = target - state->value;

    if (diff > 0) {
        /* Rising */
        int32_t max_rise = (int32_t)(((int64_t)config->rise_rate * dt_ms) / 1000);
        if (max_rise < 1) max_rise = 1;  /* Always allow some movement */

        if (diff > max_rise) {
            state->value += max_rise;
        } else {
            state->value = target;
        }
    } else if (diff < 0) {
        /* Falling */
        int32_t max_fall = (int32_t)(((int64_t)config->fall_rate * dt_ms) / 1000);
        if (max_fall < 1) max_fall = 1;

        if (-diff > max_fall) {
            state->value -= max_fall;
        } else {
            state->value = target;
        }
    }

    return state->value;
}

int32_t RateLimiter_GetValue(const RateLimiter_State_t* state)
{
    return state ? state->value : 0;
}

void RateLimiter_Reset(RateLimiter_State_t* state, int32_t value)
{
    if (!state) return;
    state->value = value;
    state->initialized = 1;
}

/*============================================================================
 * Debounce Filter Implementation
 *============================================================================*/

void Debounce_Init(Debounce_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(Debounce_State_t));
}

int32_t Debounce_Update(Debounce_State_t* state, const Debounce_Config_t* config,
                        int32_t input, uint32_t dt_ms)
{
    if (!state || !config) return input;

    if (!state->initialized) {
        state->stable_value = input;
        state->pending_value = input;
        state->pending_time_ms = 0;
        state->initialized = 1;
        return input;
    }

    /* Apply hysteresis if configured */
    int32_t threshold = config->hysteresis;
    int32_t diff = input - state->stable_value;
    if (diff < 0) diff = -diff;

    /* Check if input has changed significantly */
    bool input_changed;
    if (threshold > 0) {
        input_changed = (diff > threshold);
    } else {
        input_changed = (input != state->stable_value);
    }

    if (!input_changed) {
        /* Input matches stable value, reset pending */
        state->pending_value = state->stable_value;
        state->pending_time_ms = 0;
        return state->stable_value;
    }

    /* Input is different from stable value */
    if (input == state->pending_value) {
        /* Same as pending, accumulate time */
        state->pending_time_ms += dt_ms;

        if (state->pending_time_ms >= config->debounce_ms) {
            /* Debounce period elapsed, accept new value */
            state->stable_value = input;
            state->pending_time_ms = 0;
        }
    } else {
        /* New pending value */
        state->pending_value = input;
        state->pending_time_ms = dt_ms;
    }

    return state->stable_value;
}

int32_t Debounce_GetValue(const Debounce_State_t* state)
{
    return state ? state->stable_value : 0;
}

void Debounce_Reset(Debounce_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(Debounce_State_t));
}

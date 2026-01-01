/**
 * @file filter.h
 * @brief Logic Engine - Signal Filters (Pure Functions)
 *
 * Various signal filtering algorithms with external state management.
 * All state is passed as parameters, no global variables.
 *
 * Supported filters:
 * - Moving Average (SMA)
 * - Exponential Moving Average (EMA)
 * - Low-Pass Filter (1st order IIR)
 * - Median Filter
 * - Rate Limiter (Slew Rate)
 * - Debounce Filter
 *
 * @note Part of the Logic Engine abstraction layer.
 *       Can run on embedded systems or desktop without hardware.
 */

#ifndef LOGIC_ENGINE_FILTER_H
#define LOGIC_ENGINE_FILTER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Constants
 *============================================================================*/

/** Maximum samples for moving average/median */
#define FILTER_MAX_SAMPLES      16

/** Scale factor for alpha values (8-bit: 0-255 maps to 0.0-1.0) */
#define FILTER_ALPHA_SCALE      256

/*============================================================================
 * Filter Types
 *============================================================================*/

typedef enum {
    FILTER_TYPE_NONE = 0,       /**< No filtering (pass-through) */
    FILTER_TYPE_SMA,            /**< Simple Moving Average */
    FILTER_TYPE_EMA,            /**< Exponential Moving Average */
    FILTER_TYPE_LOWPASS,        /**< Low-Pass (1st order IIR) */
    FILTER_TYPE_MEDIAN,         /**< Median filter */
    FILTER_TYPE_RATE_LIMIT,     /**< Rate/Slew rate limiter */
    FILTER_TYPE_DEBOUNCE,       /**< Debounce filter */
} FilterType_t;

/*============================================================================
 * Moving Average State
 *============================================================================*/

/**
 * Simple Moving Average state.
 */
typedef struct {
    int32_t samples[FILTER_MAX_SAMPLES];  /**< Sample buffer (circular) */
    uint8_t index;              /**< Current write index */
    uint8_t count;              /**< Number of valid samples */
    int32_t sum;                /**< Running sum (for efficiency) */
} SMA_State_t;

/**
 * Simple Moving Average configuration.
 */
typedef struct {
    uint8_t window_size;        /**< Number of samples (1-16) */
} SMA_Config_t;

/*============================================================================
 * Exponential Moving Average State
 *============================================================================*/

/**
 * Exponential Moving Average state.
 */
typedef struct {
    int32_t value;              /**< Current filtered value (scaled) */
    uint8_t initialized;        /**< First sample received */
} EMA_State_t;

/**
 * Exponential Moving Average configuration.
 * Output = alpha * input + (1-alpha) * prev_output
 * alpha is scaled: actual_alpha = alpha / FILTER_ALPHA_SCALE
 */
typedef struct {
    uint8_t alpha;              /**< Smoothing factor (0-255, higher = more responsive) */
} EMA_Config_t;

/*============================================================================
 * Low-Pass Filter State
 *============================================================================*/

/**
 * Low-Pass filter state (1st order IIR).
 * Same as EMA but with time-constant based configuration.
 */
typedef struct {
    int64_t value;              /**< Current filtered value (scaled for precision) */
    uint8_t initialized;        /**< First sample received */
} LPF_State_t;

/**
 * Low-Pass filter configuration.
 * Cutoff frequency determines smoothing.
 * Lower cutoff = more smoothing.
 */
typedef struct {
    uint16_t time_constant_ms;  /**< Time constant in milliseconds */
    uint16_t scale;             /**< Output scale (default 1000) */
} LPF_Config_t;

/*============================================================================
 * Median Filter State
 *============================================================================*/

/**
 * Median filter state.
 */
typedef struct {
    int32_t samples[FILTER_MAX_SAMPLES];  /**< Sample buffer */
    uint8_t index;              /**< Current write index */
    uint8_t count;              /**< Number of valid samples */
} Median_State_t;

/**
 * Median filter configuration.
 */
typedef struct {
    uint8_t window_size;        /**< Number of samples (3, 5, 7, ...) */
} Median_Config_t;

/*============================================================================
 * Rate Limiter State
 *============================================================================*/

/**
 * Rate limiter state.
 */
typedef struct {
    int32_t value;              /**< Current output value */
    uint8_t initialized;        /**< First sample received */
} RateLimiter_State_t;

/**
 * Rate limiter configuration.
 */
typedef struct {
    int32_t rise_rate;          /**< Maximum rise rate per second */
    int32_t fall_rate;          /**< Maximum fall rate per second */
} RateLimiter_Config_t;

/*============================================================================
 * Debounce Filter State
 *============================================================================*/

/**
 * Debounce filter state.
 */
typedef struct {
    int32_t stable_value;       /**< Last stable output */
    int32_t pending_value;      /**< Value being debounced */
    uint32_t pending_time_ms;   /**< Time pending value has been stable */
    uint8_t initialized;        /**< First sample received */
} Debounce_State_t;

/**
 * Debounce filter configuration.
 */
typedef struct {
    uint16_t debounce_ms;       /**< Time value must be stable (ms) */
    int32_t hysteresis;         /**< Hysteresis threshold (optional) */
} Debounce_Config_t;

/*============================================================================
 * Simple Moving Average Functions
 *============================================================================*/

/**
 * Initialize SMA state.
 */
void SMA_Init(SMA_State_t* state);

/**
 * Update SMA with new sample.
 *
 * @param state     SMA state (modified)
 * @param config    SMA configuration
 * @param input     New input value
 * @return Filtered output
 */
int32_t SMA_Update(SMA_State_t* state, const SMA_Config_t* config, int32_t input);

/**
 * Get current SMA value without adding sample.
 */
int32_t SMA_GetValue(const SMA_State_t* state, const SMA_Config_t* config);

/**
 * Reset SMA state.
 */
void SMA_Reset(SMA_State_t* state);

/*============================================================================
 * Exponential Moving Average Functions
 *============================================================================*/

/**
 * Initialize EMA state.
 */
void EMA_Init(EMA_State_t* state);

/**
 * Update EMA with new sample.
 *
 * @param state     EMA state (modified)
 * @param config    EMA configuration
 * @param input     New input value
 * @return Filtered output
 */
int32_t EMA_Update(EMA_State_t* state, const EMA_Config_t* config, int32_t input);

/**
 * Get current EMA value.
 */
int32_t EMA_GetValue(const EMA_State_t* state);

/**
 * Reset EMA state.
 */
void EMA_Reset(EMA_State_t* state);

/*============================================================================
 * Low-Pass Filter Functions
 *============================================================================*/

/**
 * Initialize low-pass filter state.
 */
void LPF_Init(LPF_State_t* state);

/**
 * Update low-pass filter with new sample.
 *
 * @param state     Filter state (modified)
 * @param config    Filter configuration
 * @param input     New input value
 * @param dt_ms     Time delta in milliseconds
 * @return Filtered output
 */
int32_t LPF_Update(LPF_State_t* state, const LPF_Config_t* config,
                   int32_t input, uint32_t dt_ms);

/**
 * Get current filter value.
 */
int32_t LPF_GetValue(const LPF_State_t* state, const LPF_Config_t* config);

/**
 * Reset low-pass filter state.
 */
void LPF_Reset(LPF_State_t* state);

/*============================================================================
 * Median Filter Functions
 *============================================================================*/

/**
 * Initialize median filter state.
 */
void Median_Init(Median_State_t* state);

/**
 * Update median filter with new sample.
 *
 * @param state     Filter state (modified)
 * @param config    Filter configuration
 * @param input     New input value
 * @return Filtered output (median of window)
 */
int32_t Median_Update(Median_State_t* state, const Median_Config_t* config,
                      int32_t input);

/**
 * Get current median value.
 */
int32_t Median_GetValue(const Median_State_t* state, const Median_Config_t* config);

/**
 * Reset median filter state.
 */
void Median_Reset(Median_State_t* state);

/*============================================================================
 * Rate Limiter Functions
 *============================================================================*/

/**
 * Initialize rate limiter state.
 */
void RateLimiter_Init(RateLimiter_State_t* state);

/**
 * Update rate limiter with new target.
 *
 * @param state     Limiter state (modified)
 * @param config    Limiter configuration
 * @param target    Target value
 * @param dt_ms     Time delta in milliseconds
 * @return Rate-limited output
 */
int32_t RateLimiter_Update(RateLimiter_State_t* state,
                           const RateLimiter_Config_t* config,
                           int32_t target, uint32_t dt_ms);

/**
 * Get current rate limiter value.
 */
int32_t RateLimiter_GetValue(const RateLimiter_State_t* state);

/**
 * Reset rate limiter to specific value.
 */
void RateLimiter_Reset(RateLimiter_State_t* state, int32_t value);

/*============================================================================
 * Debounce Filter Functions
 *============================================================================*/

/**
 * Initialize debounce filter state.
 */
void Debounce_Init(Debounce_State_t* state);

/**
 * Update debounce filter with new input.
 *
 * @param state     Filter state (modified)
 * @param config    Filter configuration
 * @param input     New input value
 * @param dt_ms     Time delta in milliseconds
 * @return Debounced output
 */
int32_t Debounce_Update(Debounce_State_t* state, const Debounce_Config_t* config,
                        int32_t input, uint32_t dt_ms);

/**
 * Get current debounced value.
 */
int32_t Debounce_GetValue(const Debounce_State_t* state);

/**
 * Reset debounce filter.
 */
void Debounce_Reset(Debounce_State_t* state);

#ifdef __cplusplus
}
#endif

#endif /* LOGIC_ENGINE_FILTER_H */

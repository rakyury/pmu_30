/**
 * @file hysteresis.h
 * @brief Logic Engine - Hysteresis Comparator (Pure Functions)
 *
 * Schmitt trigger and hysteresis comparator implementations.
 * All state is passed as parameters, no global variables.
 *
 * Supported modes:
 * - Basic hysteresis comparator
 * - Dual-threshold (window) comparator
 * - Multi-level hysteresis
 *
 * @note Part of the Logic Engine abstraction layer.
 *       Can run on embedded systems or desktop without hardware.
 */

#ifndef LOGIC_ENGINE_HYSTERESIS_H
#define LOGIC_ENGINE_HYSTERESIS_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Constants
 *============================================================================*/

/** Maximum levels for multi-level hysteresis */
#define HYST_MAX_LEVELS     8

/*============================================================================
 * Hysteresis Types
 *============================================================================*/

typedef enum {
    HYST_TYPE_SIMPLE = 0,       /**< Simple high/low with hysteresis */
    HYST_TYPE_WINDOW,           /**< Window comparator (in-range) */
    HYST_TYPE_MULTILEVEL,       /**< Multi-level (stepped) */
} HysteresisType_t;

/*============================================================================
 * Simple Hysteresis State & Config
 *============================================================================*/

/**
 * Simple hysteresis state.
 */
typedef struct {
    uint8_t output;             /**< Current output (0 or 1) */
    uint8_t initialized;        /**< State initialized */
} Hysteresis_State_t;

/**
 * Simple hysteresis configuration.
 *
 * Output goes HIGH when input >= threshold_high
 * Output goes LOW when input <= threshold_low
 * Hysteresis band = threshold_high - threshold_low
 */
typedef struct {
    int32_t threshold_high;     /**< Upper threshold (turn on) */
    int32_t threshold_low;      /**< Lower threshold (turn off) */
    uint8_t invert;             /**< Invert output */
} Hysteresis_Config_t;

/*============================================================================
 * Window Comparator State & Config
 *============================================================================*/

/**
 * Window comparator state.
 */
typedef struct {
    uint8_t output;             /**< Current output (0 or 1) */
    uint8_t initialized;        /**< State initialized */
} Window_State_t;

/**
 * Window comparator configuration.
 *
 * Output is HIGH when value is within window:
 *   (low_threshold - hysteresis) < value < (high_threshold + hysteresis)
 *
 * With hysteresis, once inside window, must exit beyond threshold +/- hysteresis
 * to change state.
 */
typedef struct {
    int32_t low_threshold;      /**< Window lower bound */
    int32_t high_threshold;     /**< Window upper bound */
    int32_t hysteresis;         /**< Hysteresis amount */
    uint8_t invert;             /**< Invert output (outside window = HIGH) */
} Window_Config_t;

/*============================================================================
 * Multi-Level Hysteresis State & Config
 *============================================================================*/

/**
 * Multi-level hysteresis state.
 */
typedef struct {
    uint8_t current_level;      /**< Current level (0 to level_count-1) */
    uint8_t initialized;        /**< State initialized */
} MultiLevel_State_t;

/**
 * Level threshold definition.
 */
typedef struct {
    int32_t threshold_up;       /**< Threshold to move up to this level */
    int32_t threshold_down;     /**< Threshold to move down from this level */
} LevelThreshold_t;

/**
 * Multi-level hysteresis configuration.
 *
 * Levels are numbered 0 to (level_count - 1).
 * thresholds[i] defines transitions to/from level i.
 */
typedef struct {
    LevelThreshold_t thresholds[HYST_MAX_LEVELS];
    uint8_t level_count;        /**< Number of levels (2-8) */
} MultiLevel_Config_t;

/*============================================================================
 * Simple Hysteresis Functions
 *============================================================================*/

/**
 * Initialize hysteresis state.
 */
void Hysteresis_Init(Hysteresis_State_t* state);

/**
 * Update hysteresis comparator.
 *
 * @param state     Hysteresis state (modified)
 * @param config    Comparator configuration
 * @param input     Input value
 * @return Output (0 or 1)
 */
int32_t Hysteresis_Update(Hysteresis_State_t* state,
                          const Hysteresis_Config_t* config,
                          int32_t input);

/**
 * Get current output.
 */
int32_t Hysteresis_GetOutput(const Hysteresis_State_t* state);

/**
 * Reset hysteresis state to specific output.
 */
void Hysteresis_Reset(Hysteresis_State_t* state, uint8_t output);

/**
 * Create hysteresis config from center and band.
 *
 * @param center    Center threshold
 * @param band      Hysteresis band (total, not +/-)
 * @return Configuration
 */
Hysteresis_Config_t Hysteresis_ConfigFromBand(int32_t center, int32_t band);

/*============================================================================
 * Window Comparator Functions
 *============================================================================*/

/**
 * Initialize window comparator state.
 */
void Window_Init(Window_State_t* state);

/**
 * Update window comparator.
 *
 * @param state     Window state (modified)
 * @param config    Window configuration
 * @param input     Input value
 * @return Output (1 = in window, 0 = outside)
 */
int32_t Window_Update(Window_State_t* state,
                      const Window_Config_t* config,
                      int32_t input);

/**
 * Get current output.
 */
int32_t Window_GetOutput(const Window_State_t* state);

/**
 * Reset window state.
 */
void Window_Reset(Window_State_t* state);

/*============================================================================
 * Multi-Level Functions
 *============================================================================*/

/**
 * Initialize multi-level state.
 */
void MultiLevel_Init(MultiLevel_State_t* state);

/**
 * Update multi-level hysteresis.
 *
 * @param state     Multi-level state (modified)
 * @param config    Multi-level configuration
 * @param input     Input value
 * @return Current level (0 to level_count-1)
 */
int32_t MultiLevel_Update(MultiLevel_State_t* state,
                          const MultiLevel_Config_t* config,
                          int32_t input);

/**
 * Get current level.
 */
int32_t MultiLevel_GetLevel(const MultiLevel_State_t* state);

/**
 * Reset multi-level state to specific level.
 */
void MultiLevel_Reset(MultiLevel_State_t* state, uint8_t level);

/*============================================================================
 * Pure Comparator Functions (Stateless)
 *============================================================================*/

/**
 * Simple threshold compare (no hysteresis).
 *
 * @param input     Input value
 * @param threshold Threshold value
 * @return 1 if input >= threshold, 0 otherwise
 */
int32_t Compare_GE(int32_t input, int32_t threshold);

/**
 * Simple threshold compare (no hysteresis).
 *
 * @param input     Input value
 * @param threshold Threshold value
 * @return 1 if input > threshold, 0 otherwise
 */
int32_t Compare_GT(int32_t input, int32_t threshold);

/**
 * Range check (no hysteresis).
 *
 * @param input     Input value
 * @param low       Lower bound
 * @param high      Upper bound
 * @return 1 if low <= input <= high, 0 otherwise
 */
int32_t Compare_InRange(int32_t input, int32_t low, int32_t high);

/**
 * Deadband function.
 * Returns 0 if input is within deadband of center.
 *
 * @param input     Input value
 * @param center    Center value
 * @param deadband  Deadband radius
 * @return 0 if in deadband, else (input - center) adjusted for deadband
 */
int32_t Deadband(int32_t input, int32_t center, int32_t deadband);

#ifdef __cplusplus
}
#endif

#endif /* LOGIC_ENGINE_HYSTERESIS_H */

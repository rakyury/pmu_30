/**
 * @file pid.h
 * @brief Logic Engine - PID Controller (Pure Functions)
 *
 * PID controller with external state management.
 * All state is passed as parameters, no global variables.
 *
 * Uses fixed-point arithmetic with configurable scale factor.
 * Default scale: 1000 (3 decimal places precision)
 *
 * @note Part of the Logic Engine abstraction layer.
 *       Can run on embedded systems or desktop without hardware.
 */

#ifndef LOGIC_ENGINE_PID_H
#define LOGIC_ENGINE_PID_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Constants
 *============================================================================*/

/** Default scale factor for fixed-point (1000 = 3 decimal places) */
#define PID_DEFAULT_SCALE       1000

/** Maximum integral accumulator value (prevents overflow) */
#define PID_MAX_INTEGRAL        (INT32_MAX / 2)

/*============================================================================
 * PID Configuration
 *============================================================================*/

/**
 * PID configuration structure.
 * All gain values are scaled by 'scale' factor.
 * E.g., Kp=1500 with scale=1000 means actual Kp=1.5
 */
typedef struct {
    int32_t kp;             /**< Proportional gain (scaled) */
    int32_t ki;             /**< Integral gain (scaled) */
    int32_t kd;             /**< Derivative gain (scaled) */

    int32_t scale;          /**< Scale factor (default 1000) */

    int32_t output_min;     /**< Minimum output value */
    int32_t output_max;     /**< Maximum output value */

    int32_t integral_min;   /**< Minimum integral accumulator */
    int32_t integral_max;   /**< Maximum integral accumulator (anti-windup) */

    int32_t deadband;       /**< Error deadband (error < deadband = 0) */

    uint8_t d_on_measurement; /**< Calculate D term on measurement (not error) */
    uint8_t reset_integral_on_setpoint; /**< Reset integral when setpoint changes */
} PID_Config_t;

/*============================================================================
 * PID State
 *============================================================================*/

/**
 * PID state structure (externally managed).
 * Must be initialized before first use.
 */
typedef struct {
    int64_t integral;       /**< Integral accumulator (64-bit for precision) */
    int32_t prev_error;     /**< Previous error (for derivative) */
    int32_t prev_measurement; /**< Previous measurement (for D on measurement) */
    int32_t prev_setpoint;  /**< Previous setpoint (for reset detection) */
    int32_t output;         /**< Last output value */
    uint8_t initialized;    /**< State has been initialized */
} PID_State_t;

/*============================================================================
 * PID Functions
 *============================================================================*/

/**
 * Initialize PID state.
 *
 * @param state     PID state to initialize
 */
void PID_Init(PID_State_t* state);

/**
 * Reset PID state (clear integral, etc.).
 *
 * @param state     PID state to reset
 */
void PID_Reset(PID_State_t* state);

/**
 * Compute PID output.
 *
 * @param state       PID state (modified)
 * @param config      PID configuration
 * @param setpoint    Desired value
 * @param measurement Current measured value
 * @param dt_ms       Time delta in milliseconds
 *
 * @return PID output (clamped to output_min/max)
 */
int32_t PID_Update(PID_State_t* state, const PID_Config_t* config,
                   int32_t setpoint, int32_t measurement, uint32_t dt_ms);

/**
 * Get current PID output without updating.
 *
 * @param state     PID state
 * @return Last computed output
 */
int32_t PID_GetOutput(const PID_State_t* state);

/**
 * Get current integral value.
 *
 * @param state     PID state
 * @return Current integral accumulator (scaled)
 */
int32_t PID_GetIntegral(const PID_State_t* state);

/**
 * Set integral value (for bumpless transfer).
 *
 * @param state     PID state
 * @param config    PID configuration
 * @param value     New integral value (scaled)
 */
void PID_SetIntegral(PID_State_t* state, const PID_Config_t* config,
                     int32_t value);

/**
 * Compute P term only.
 *
 * @param config    PID configuration
 * @param error     Current error (setpoint - measurement)
 * @return Proportional term (scaled)
 */
int32_t PID_ComputeP(const PID_Config_t* config, int32_t error);

/**
 * Compute I term only.
 *
 * @param state     PID state (modified)
 * @param config    PID configuration
 * @param error     Current error
 * @param dt_ms     Time delta in milliseconds
 * @return Integral term (scaled)
 */
int32_t PID_ComputeI(PID_State_t* state, const PID_Config_t* config,
                     int32_t error, uint32_t dt_ms);

/**
 * Compute D term only.
 *
 * @param state     PID state (modified)
 * @param config    PID configuration
 * @param error     Current error
 * @param measurement Current measurement (for D on measurement mode)
 * @param dt_ms     Time delta in milliseconds
 * @return Derivative term (scaled)
 */
int32_t PID_ComputeD(PID_State_t* state, const PID_Config_t* config,
                     int32_t error, int32_t measurement, uint32_t dt_ms);

/**
 * Create default PID configuration.
 *
 * @param kp        Proportional gain (scaled by 1000)
 * @param ki        Integral gain (scaled by 1000)
 * @param kd        Derivative gain (scaled by 1000)
 * @param out_min   Minimum output
 * @param out_max   Maximum output
 * @return Configuration structure
 */
PID_Config_t PID_DefaultConfig(int32_t kp, int32_t ki, int32_t kd,
                                int32_t out_min, int32_t out_max);

#ifdef __cplusplus
}
#endif

#endif /* LOGIC_ENGINE_PID_H */

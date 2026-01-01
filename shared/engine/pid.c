/**
 * @file pid.c
 * @brief Logic Engine - PID Controller Implementation
 */

#include "pid.h"
#include <string.h>

/*============================================================================
 * Helper Functions
 *============================================================================*/

static int64_t clamp_i64(int64_t value, int64_t min_val, int64_t max_val)
{
    if (value < min_val) return min_val;
    if (value > max_val) return max_val;
    return value;
}

static int32_t clamp_i32(int32_t value, int32_t min_val, int32_t max_val)
{
    if (value < min_val) return min_val;
    if (value > max_val) return max_val;
    return value;
}

static int32_t apply_deadband(int32_t error, int32_t deadband)
{
    if (deadband <= 0) return error;

    if (error > 0) {
        if (error <= deadband) return 0;
        return error - deadband;
    } else {
        if (error >= -deadband) return 0;
        return error + deadband;
    }
}

/*============================================================================
 * PID Functions
 *============================================================================*/

void PID_Init(PID_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(PID_State_t));
}

void PID_Reset(PID_State_t* state)
{
    if (!state) return;

    state->integral = 0;
    state->prev_error = 0;
    state->prev_measurement = 0;
    /* Keep prev_setpoint for change detection */
    state->output = 0;
    state->initialized = 0;
}

int32_t PID_Update(PID_State_t* state, const PID_Config_t* config,
                   int32_t setpoint, int32_t measurement, uint32_t dt_ms)
{
    if (!state || !config) return 0;
    if (dt_ms == 0) return state->output;

    int32_t scale = config->scale > 0 ? config->scale : PID_DEFAULT_SCALE;

    /* Check for setpoint change (for integral reset) */
    if (config->reset_integral_on_setpoint && state->initialized) {
        if (setpoint != state->prev_setpoint) {
            state->integral = 0;
        }
    }
    state->prev_setpoint = setpoint;

    /* Calculate error with deadband */
    int32_t raw_error = setpoint - measurement;
    int32_t error = apply_deadband(raw_error, config->deadband);

    /* Initialize on first run */
    if (!state->initialized) {
        state->prev_error = error;
        state->prev_measurement = measurement;
        state->initialized = 1;
    }

    /*
     * Calculate P term
     * P = Kp * error / scale
     */
    int64_t p_term = ((int64_t)config->kp * error) / scale;

    /*
     * Calculate I term with anti-windup
     * I += Ki * error * dt / scale / 1000
     * Using 64-bit to prevent overflow
     */
    int64_t i_delta = ((int64_t)config->ki * error * dt_ms) / scale / 1000;
    state->integral += i_delta;

    /* Anti-windup: clamp integral */
    int64_t i_min = (int64_t)config->integral_min * scale;
    int64_t i_max = (int64_t)config->integral_max * scale;
    if (i_min == 0 && i_max == 0) {
        /* Use default limits */
        i_min = -PID_MAX_INTEGRAL;
        i_max = PID_MAX_INTEGRAL;
    }
    state->integral = clamp_i64(state->integral, i_min, i_max);

    int64_t i_term = state->integral / scale;

    /*
     * Calculate D term
     * Standard: D = Kd * (error - prev_error) / dt * 1000 / scale
     * On measurement: D = -Kd * (measurement - prev_measurement) / dt * 1000 / scale
     *
     * D on measurement prevents derivative kick when setpoint changes
     */
    int64_t d_term;
    if (config->d_on_measurement) {
        int32_t d_input = measurement - state->prev_measurement;
        /* Negative because we want to resist measurement change */
        d_term = -((int64_t)config->kd * d_input * 1000) / (scale * dt_ms);
    } else {
        int32_t d_input = error - state->prev_error;
        d_term = ((int64_t)config->kd * d_input * 1000) / (scale * dt_ms);
    }

    /* Store for next iteration */
    state->prev_error = error;
    state->prev_measurement = measurement;

    /* Sum and clamp output */
    int64_t output = p_term + i_term + d_term;
    state->output = (int32_t)clamp_i64(output, config->output_min, config->output_max);

    return state->output;
}

int32_t PID_GetOutput(const PID_State_t* state)
{
    return state ? state->output : 0;
}

int32_t PID_GetIntegral(const PID_State_t* state)
{
    if (!state) return 0;
    /* Return integral scaled back to user units */
    return (int32_t)(state->integral / PID_DEFAULT_SCALE);
}

void PID_SetIntegral(PID_State_t* state, const PID_Config_t* config,
                     int32_t value)
{
    if (!state) return;

    int32_t scale = config && config->scale > 0 ? config->scale : PID_DEFAULT_SCALE;
    state->integral = (int64_t)value * scale;

    /* Apply limits if config provided */
    if (config) {
        int64_t i_min = (int64_t)config->integral_min * scale;
        int64_t i_max = (int64_t)config->integral_max * scale;
        if (i_min != 0 || i_max != 0) {
            state->integral = clamp_i64(state->integral, i_min, i_max);
        }
    }
}

int32_t PID_ComputeP(const PID_Config_t* config, int32_t error)
{
    if (!config) return 0;

    int32_t scale = config->scale > 0 ? config->scale : PID_DEFAULT_SCALE;
    int32_t adjusted_error = apply_deadband(error, config->deadband);

    return (int32_t)(((int64_t)config->kp * adjusted_error) / scale);
}

int32_t PID_ComputeI(PID_State_t* state, const PID_Config_t* config,
                     int32_t error, uint32_t dt_ms)
{
    if (!state || !config || dt_ms == 0) return 0;

    int32_t scale = config->scale > 0 ? config->scale : PID_DEFAULT_SCALE;
    int32_t adjusted_error = apply_deadband(error, config->deadband);

    /* Update integral */
    int64_t i_delta = ((int64_t)config->ki * adjusted_error * dt_ms) / scale / 1000;
    state->integral += i_delta;

    /* Apply anti-windup */
    int64_t i_min = (int64_t)config->integral_min * scale;
    int64_t i_max = (int64_t)config->integral_max * scale;
    if (i_min == 0 && i_max == 0) {
        i_min = -PID_MAX_INTEGRAL;
        i_max = PID_MAX_INTEGRAL;
    }
    state->integral = clamp_i64(state->integral, i_min, i_max);

    return (int32_t)(state->integral / scale);
}

int32_t PID_ComputeD(PID_State_t* state, const PID_Config_t* config,
                     int32_t error, int32_t measurement, uint32_t dt_ms)
{
    if (!state || !config || dt_ms == 0) return 0;

    int32_t scale = config->scale > 0 ? config->scale : PID_DEFAULT_SCALE;
    int64_t d_term;

    if (config->d_on_measurement) {
        int32_t d_input = measurement - state->prev_measurement;
        d_term = -((int64_t)config->kd * d_input * 1000) / (scale * dt_ms);
        state->prev_measurement = measurement;
    } else {
        int32_t adjusted_error = apply_deadband(error, config->deadband);
        int32_t d_input = adjusted_error - state->prev_error;
        d_term = ((int64_t)config->kd * d_input * 1000) / (scale * dt_ms);
        state->prev_error = adjusted_error;
    }

    return (int32_t)d_term;
}

PID_Config_t PID_DefaultConfig(int32_t kp, int32_t ki, int32_t kd,
                                int32_t out_min, int32_t out_max)
{
    PID_Config_t config = {0};

    config.kp = kp;
    config.ki = ki;
    config.kd = kd;
    config.scale = PID_DEFAULT_SCALE;
    config.output_min = out_min;
    config.output_max = out_max;
    config.integral_min = out_min;  /* Match output limits by default */
    config.integral_max = out_max;
    config.deadband = 0;
    config.d_on_measurement = 1;    /* Safer default */
    config.reset_integral_on_setpoint = 0;

    return config;
}

/**
 ******************************************************************************
 * @file           : pmu_pid.c
 * @brief          : PID Controller Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_pid.h"
#include "pmu_channel.h"
#include <string.h>
#include <stdio.h>

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

#define CLAMP(x, min, max) ((x) < (min) ? (min) : ((x) > (max) ? (max) : (x)))

/* Private variables ---------------------------------------------------------*/

static PMU_PIDState_t pid_controllers[PMU_PID_MAX_CONTROLLERS];
static PMU_PIDStats_t pid_stats = {0};
static bool pid_initialized = false;

/* Private function prototypes -----------------------------------------------*/

static PMU_PIDState_t* FindController(const char* id);
static PMU_PIDState_t* FindFreeSlot(void);
static uint16_t ResolveChannel(const char* channel_name);
static void UpdateSinglePID(PMU_PIDState_t* pid, uint32_t now_ms);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize PID controller subsystem
 */
HAL_StatusTypeDef PMU_PID_Init(void)
{
    memset(pid_controllers, 0, sizeof(pid_controllers));
    memset(&pid_stats, 0, sizeof(pid_stats));
    pid_initialized = true;

    printf("[PID] Subsystem initialized, max %d controllers\n", PMU_PID_MAX_CONTROLLERS);
    return HAL_OK;
}

/**
 * @brief Add or update a PID controller configuration
 */
HAL_StatusTypeDef PMU_PID_AddController(const PMU_PIDConfig_t* config)
{
    if (!config || strlen(config->id) == 0) {
        return HAL_ERROR;
    }

    /* Check if controller already exists */
    PMU_PIDState_t* pid = FindController(config->id);

    if (!pid) {
        /* Find free slot */
        pid = FindFreeSlot();
        if (!pid) {
            printf("[PID] Error: No free slots for controller '%s'\n", config->id);
            return HAL_ERROR;
        }
        pid_stats.total_controllers++;
    }

    /* Copy configuration */
    memcpy(&pid->config, config, sizeof(PMU_PIDConfig_t));

    /* Resolve channel IDs */
    pid->setpoint_channel_id = ResolveChannel(config->setpoint_channel);
    pid->process_channel_id = ResolveChannel(config->process_channel);
    pid->output_channel_id = ResolveChannel(config->output_channel);

    /* Initialize state */
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->prev_derivative = 0.0f;
    pid->output = 0.0f;
    pid->last_update_ms = HAL_GetTick();
    pid->active = true;
    pid->saturated = false;

    /* Update active count */
    pid_stats.active_controllers = 0;
    for (int i = 0; i < PMU_PID_MAX_CONTROLLERS; i++) {
        if (pid_controllers[i].active && pid_controllers[i].config.enabled) {
            pid_stats.active_controllers++;
        }
    }

    printf("[PID] Added controller '%s': Kp=%.2f Ki=%.2f Kd=%.2f [%.1f - %.1f]\n",
           config->id, config->kp, config->ki, config->kd,
           config->output_min, config->output_max);

    return HAL_OK;
}

/**
 * @brief Remove a PID controller by ID
 */
HAL_StatusTypeDef PMU_PID_RemoveController(const char* id)
{
    PMU_PIDState_t* pid = FindController(id);
    if (!pid) {
        return HAL_ERROR;
    }

    memset(pid, 0, sizeof(PMU_PIDState_t));
    pid_stats.total_controllers--;

    printf("[PID] Removed controller '%s'\n", id);
    return HAL_OK;
}

/**
 * @brief Clear all PID controllers
 */
HAL_StatusTypeDef PMU_PID_ClearAll(void)
{
    memset(pid_controllers, 0, sizeof(pid_controllers));
    pid_stats.total_controllers = 0;
    pid_stats.active_controllers = 0;

    printf("[PID] All controllers cleared\n");
    return HAL_OK;
}

/**
 * @brief Update all PID controllers
 */
void PMU_PID_Update(void)
{
    if (!pid_initialized) return;

    uint32_t now_ms = HAL_GetTick();

    for (int i = 0; i < PMU_PID_MAX_CONTROLLERS; i++) {
        PMU_PIDState_t* pid = &pid_controllers[i];

        if (!pid->active || !pid->config.enabled) {
            continue;
        }

        /* Check if it's time to update */
        uint32_t elapsed = now_ms - pid->last_update_ms;
        if (elapsed >= pid->config.sample_time_ms) {
            UpdateSinglePID(pid, now_ms);
            pid_stats.total_updates++;
        }
    }
}

/**
 * @brief Get PID controller output value
 */
float PMU_PID_GetOutput(const char* id)
{
    PMU_PIDState_t* pid = FindController(id);
    return pid ? pid->output : 0.0f;
}

/**
 * @brief Set PID controller setpoint
 */
HAL_StatusTypeDef PMU_PID_SetSetpoint(const char* id, float setpoint)
{
    PMU_PIDState_t* pid = FindController(id);
    if (!pid) return HAL_ERROR;

    pid->config.setpoint_value = setpoint;
    return HAL_OK;
}

/**
 * @brief Enable or disable a PID controller
 */
HAL_StatusTypeDef PMU_PID_SetEnabled(const char* id, bool enabled)
{
    PMU_PIDState_t* pid = FindController(id);
    if (!pid) return HAL_ERROR;

    pid->config.enabled = enabled;

    /* Update active count */
    pid_stats.active_controllers = 0;
    for (int i = 0; i < PMU_PID_MAX_CONTROLLERS; i++) {
        if (pid_controllers[i].active && pid_controllers[i].config.enabled) {
            pid_stats.active_controllers++;
        }
    }

    return HAL_OK;
}

/**
 * @brief Reset PID controller state
 */
HAL_StatusTypeDef PMU_PID_Reset(const char* id)
{
    PMU_PIDState_t* pid = FindController(id);
    if (!pid) return HAL_ERROR;

    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->prev_derivative = 0.0f;
    pid->output = 0.0f;
    pid->saturated = false;

    return HAL_OK;
}

/**
 * @brief Get PID system statistics
 */
const PMU_PIDStats_t* PMU_PID_GetStats(void)
{
    return &pid_stats;
}

/**
 * @brief Get PID controller state
 */
const PMU_PIDState_t* PMU_PID_GetState(const char* id)
{
    return FindController(id);
}

/**
 * @brief List all PID controllers
 */
uint8_t PMU_PID_ListControllers(PMU_PIDConfig_t* configs, uint8_t max_count)
{
    uint8_t count = 0;

    for (int i = 0; i < PMU_PID_MAX_CONTROLLERS && count < max_count; i++) {
        if (pid_controllers[i].active) {
            memcpy(&configs[count], &pid_controllers[i].config, sizeof(PMU_PIDConfig_t));
            count++;
        }
    }

    return count;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Find controller by ID
 */
static PMU_PIDState_t* FindController(const char* id)
{
    if (!id || strlen(id) == 0) return NULL;

    for (int i = 0; i < PMU_PID_MAX_CONTROLLERS; i++) {
        if (pid_controllers[i].active &&
            strcmp(pid_controllers[i].config.id, id) == 0) {
            return &pid_controllers[i];
        }
    }

    return NULL;
}

/**
 * @brief Find free slot
 */
static PMU_PIDState_t* FindFreeSlot(void)
{
    for (int i = 0; i < PMU_PID_MAX_CONTROLLERS; i++) {
        if (!pid_controllers[i].active) {
            return &pid_controllers[i];
        }
    }
    return NULL;
}

/**
 * @brief Resolve channel name to channel ID
 */
static uint16_t ResolveChannel(const char* channel_name)
{
    if (!channel_name || strlen(channel_name) == 0) {
        return 0xFFFF; /* Invalid */
    }

    const PMU_Channel_t* channel = PMU_Channel_GetByName(channel_name);
    if (channel) {
        return channel->channel_id;
    }

    return 0xFFFF; /* Not found */
}

/**
 * @brief Update a single PID controller
 */
static void UpdateSinglePID(PMU_PIDState_t* pid, uint32_t now_ms)
{
    PMU_PIDConfig_t* cfg = &pid->config;

    /* Get setpoint */
    float setpoint;
    if (pid->setpoint_channel_id != 0xFFFF) {
        setpoint = (float)PMU_Channel_GetValue(pid->setpoint_channel_id);
    } else {
        setpoint = cfg->setpoint_value;
    }

    /* Get process variable */
    float process_value = 0.0f;
    if (pid->process_channel_id != 0xFFFF) {
        process_value = (float)PMU_Channel_GetValue(pid->process_channel_id);
    }

    /* Calculate error */
    float error = setpoint - process_value;
    if (cfg->reversed) {
        error = -error;
    }

    /* Calculate time delta in seconds */
    float dt = (float)cfg->sample_time_ms / 1000.0f;

    /* Proportional term */
    float p_term = cfg->kp * error;

    /* Integral term with anti-windup */
    float i_term = 0.0f;
    if (cfg->ki != 0.0f) {
        pid->integral += error * dt;

        /* Anti-windup: clamp integral when output is saturated */
        if (cfg->anti_windup && pid->saturated) {
            /* Don't accumulate if saturated and error pushes further */
            if ((pid->output >= cfg->output_max && error > 0) ||
                (pid->output <= cfg->output_min && error < 0)) {
                pid->integral -= error * dt;
            }
        }

        i_term = cfg->ki * pid->integral;
    }

    /* Derivative term */
    float d_term = 0.0f;
    if (cfg->kd != 0.0f && dt > 0.0f) {
        float derivative = (error - pid->prev_error) / dt;

        /* Apply low-pass filter to derivative if enabled */
        if (cfg->derivative_filter) {
            float alpha = cfg->derivative_filter_coeff;
            derivative = alpha * derivative + (1.0f - alpha) * pid->prev_derivative;
            pid->prev_derivative = derivative;
        }

        d_term = cfg->kd * derivative;
    }

    /* Calculate output */
    float output = p_term + i_term + d_term;

    /* Clamp output */
    float clamped_output = CLAMP(output, cfg->output_min, cfg->output_max);
    pid->saturated = (clamped_output != output);
    pid->output = clamped_output;

    /* Update state */
    pid->prev_error = error;
    pid->last_update_ms = now_ms;

    /* Write to output channel if configured */
    if (pid->output_channel_id != 0xFFFF) {
        PMU_Channel_SetValue(pid->output_channel_id, (int32_t)(clamped_output * 1000)); /* Scale for milli-units */
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

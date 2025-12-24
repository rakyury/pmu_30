/**
 ******************************************************************************
 * @file           : pmu_pid.h
 * @brief          : PID Controller Implementation Header
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements PID controllers for the PMU-30.
 * PID controllers can be used for:
 * - Temperature control (fan speed, heater)
 * - Motor position/speed control
 * - Pressure regulation
 * - Any closed-loop control application
 *
 ******************************************************************************
 */

#ifndef PMU_PID_H
#define PMU_PID_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"
#include "pmu_types.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported constants --------------------------------------------------------*/

#define PMU_PID_MAX_CONTROLLERS   16   /**< Maximum number of PID controllers */
#define PMU_PID_DEFAULT_SAMPLE_MS 100  /**< Default sample time in ms */

/* Exported types ------------------------------------------------------------*/

/**
 * @brief PID controller configuration
 */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];       /**< Channel ID */

    /* Input/Output channel references */
    char setpoint_channel[PMU_CHANNEL_ID_LEN];  /**< Channel providing setpoint (optional) */
    char process_channel[PMU_CHANNEL_ID_LEN];   /**< Channel providing process variable */
    char output_channel[PMU_CHANNEL_ID_LEN];    /**< Channel to write output to (optional) */

    /* PID gains */
    float kp;                          /**< Proportional gain */
    float ki;                          /**< Integral gain */
    float kd;                          /**< Derivative gain */

    /* Setpoint (used if setpoint_channel is empty) */
    float setpoint_value;              /**< Fixed setpoint value */

    /* Output limits */
    float output_min;                  /**< Minimum output value */
    float output_max;                  /**< Maximum output value */

    /* Advanced settings */
    uint16_t sample_time_ms;           /**< PID loop execution period */
    bool anti_windup;                  /**< Prevent integral windup */
    bool derivative_filter;            /**< Apply low-pass filter to derivative */
    float derivative_filter_coeff;     /**< Filter coefficient (0-1) */

    /* Control options */
    bool enabled;                      /**< Controller enabled */
    bool reversed;                     /**< Reverse acting controller */

} PMU_PIDConfig_t;

/**
 * @brief PID controller runtime state
 */
typedef struct {
    /* Configuration reference */
    PMU_PIDConfig_t config;

    /* Runtime state */
    float integral;                    /**< Integral accumulator */
    float prev_error;                  /**< Previous error (for derivative) */
    float prev_derivative;             /**< Previous derivative (for filter) */
    float output;                      /**< Current output value */

    /* Timing */
    uint32_t last_update_ms;           /**< Last update timestamp */

    /* Resolved channel IDs */
    uint16_t setpoint_channel_id;      /**< Resolved setpoint channel ID */
    uint16_t process_channel_id;       /**< Resolved process channel ID */
    uint16_t output_channel_id;        /**< Resolved output channel ID */

    /* Status */
    bool active;                       /**< Controller slot is active */
    bool saturated;                    /**< Output is saturated (clamped) */

} PMU_PIDState_t;

/**
 * @brief PID system statistics
 */
typedef struct {
    uint8_t total_controllers;         /**< Total configured controllers */
    uint8_t active_controllers;        /**< Currently active controllers */
    uint32_t total_updates;            /**< Total update cycles */
} PMU_PIDStats_t;

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize PID controller subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PID_Init(void);

/**
 * @brief Add or update a PID controller configuration
 * @param config Pointer to PID configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PID_AddController(const PMU_PIDConfig_t* config);

/**
 * @brief Remove a PID controller by ID
 * @param id Controller ID string
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PID_RemoveController(const char* id);

/**
 * @brief Clear all PID controllers
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PID_ClearAll(void);

/**
 * @brief Update all PID controllers (call from main loop)
 * @retval None
 */
void PMU_PID_Update(void);

/**
 * @brief Get PID controller output value
 * @param id Controller ID string
 * @retval Output value (or 0 if not found)
 */
float PMU_PID_GetOutput(const char* id);

/**
 * @brief Set PID controller setpoint
 * @param id Controller ID string
 * @param setpoint New setpoint value
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PID_SetSetpoint(const char* id, float setpoint);

/**
 * @brief Enable or disable a PID controller
 * @param id Controller ID string
 * @param enabled Enable flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PID_SetEnabled(const char* id, bool enabled);

/**
 * @brief Reset PID controller state (clear integral, etc.)
 * @param id Controller ID string
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PID_Reset(const char* id);

/**
 * @brief Get PID system statistics
 * @retval Pointer to statistics structure
 */
const PMU_PIDStats_t* PMU_PID_GetStats(void);

/**
 * @brief Get PID controller state
 * @param id Controller ID string
 * @retval Pointer to state structure (or NULL if not found)
 */
const PMU_PIDState_t* PMU_PID_GetState(const char* id);

/**
 * @brief List all PID controllers
 * @param configs Array to fill with configurations
 * @param max_count Maximum number to return
 * @retval Number of controllers returned
 */
uint8_t PMU_PID_ListControllers(PMU_PIDConfig_t* configs, uint8_t max_count);

#ifdef __cplusplus
}
#endif

#endif /* PMU_PID_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

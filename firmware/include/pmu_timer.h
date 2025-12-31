/**
 ******************************************************************************
 * @file           : pmu_timer.h
 * @brief          : Timer Channel Implementation Header
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements configurable timer channels for the PMU-30.
 * Each timer provides runtime channels:
 * - r_{id}.value   - Current timer value in seconds
 * - r_{id}.running - Timer running state (0/1)
 * - r_{id}.elapsed - Time elapsed since start
 *
 ******************************************************************************
 */

#ifndef PMU_TIMER_H
#define PMU_TIMER_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "pmu_hal.h"
#include "pmu_config.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported constants --------------------------------------------------------*/

#define PMU_TIMER_MAX_TIMERS      16   /**< Maximum number of timer channels */

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Timer channel runtime state
 */
typedef struct {
    /* Configuration */
    PMU_TimerConfig_t config;

    /* Runtime state */
    bool active;                       /**< Timer slot is active */
    bool running;                      /**< Timer is currently running */
    bool expired;                      /**< Timer has expired/completed */

    /* Timing */
    uint32_t start_time_ms;            /**< Timer start timestamp */
    uint32_t elapsed_ms;               /**< Elapsed time in ms */
    uint32_t limit_ms;                 /**< Timer limit in ms */

    /* Edge detection for triggers */
    int32_t prev_start_value;          /**< Previous start channel value */
    int32_t prev_stop_value;           /**< Previous stop channel value */

    /* Resolved channel IDs */
    uint16_t start_channel_id;         /**< Resolved start channel ID */
    uint16_t stop_channel_id;          /**< Resolved stop channel ID */

    /* Runtime output channel IDs */
    uint16_t value_channel_id;         /**< r_{id}.value channel ID */
    uint16_t running_channel_id;       /**< r_{id}.running channel ID */
    uint16_t elapsed_channel_id;       /**< r_{id}.elapsed channel ID */

} PMU_TimerState_t;

/**
 * @brief Timer system statistics
 */
typedef struct {
    uint8_t total_timers;              /**< Total configured timers */
    uint8_t active_timers;             /**< Currently running timers */
} PMU_TimerStats_t;

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize timer subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Timer_Init(void);

/**
 * @brief Add or update a timer configuration
 * @param config Pointer to timer configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Timer_AddTimer(const PMU_TimerConfig_t* config);

/**
 * @brief Remove a timer by ID
 * @param id Timer ID string
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Timer_RemoveTimer(const char* id);

/**
 * @brief Clear all timers
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Timer_ClearAll(void);

/**
 * @brief Update all timers (call from main loop at 100Hz or higher)
 * @retval None
 */
void PMU_Timer_Update(void);

/**
 * @brief Start a timer manually
 * @param id Timer ID string
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Timer_Start(const char* id);

/**
 * @brief Stop a timer manually
 * @param id Timer ID string
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Timer_Stop(const char* id);

/**
 * @brief Reset a timer
 * @param id Timer ID string
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Timer_Reset(const char* id);

/**
 * @brief Get timer current value in seconds
 * @param id Timer ID string
 * @retval Timer value (or 0 if not found)
 */
float PMU_Timer_GetValue(const char* id);

/**
 * @brief Check if timer is running
 * @param id Timer ID string
 * @retval true if running, false otherwise
 */
bool PMU_Timer_IsRunning(const char* id);

/**
 * @brief Check if timer has expired
 * @param id Timer ID string
 * @retval true if expired, false otherwise
 */
bool PMU_Timer_IsExpired(const char* id);

/**
 * @brief Get timer system statistics
 * @retval Pointer to statistics structure
 */
const PMU_TimerStats_t* PMU_Timer_GetStats(void);

/**
 * @brief Get timer state
 * @param id Timer ID string
 * @retval Pointer to state structure (or NULL if not found)
 */
const PMU_TimerState_t* PMU_Timer_GetState(const char* id);

/**
 * @brief List all timers
 * @param configs Array to fill with configurations
 * @param max_count Maximum number to return
 * @retval Number of timers returned
 */
uint8_t PMU_Timer_ListTimers(PMU_TimerConfig_t* configs, uint8_t max_count);

#ifdef __cplusplus
}
#endif

#endif /* PMU_TIMER_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

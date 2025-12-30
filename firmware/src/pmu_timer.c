/**
 ******************************************************************************
 * @file           : pmu_timer.c
 * @brief          : Timer Channel Implementation
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
#include "pmu_timer.h"
#include "pmu_channel.h"
#include <string.h>
#include <stdio.h>

/* Private defines -----------------------------------------------------------*/

#define TIMER_CHANNEL_BASE_ID       400   /**< Base channel ID for timer runtime channels */
#define TIMER_CHANNELS_PER_TIMER    3     /**< value, running, elapsed */

/* Private variables ---------------------------------------------------------*/

static PMU_TimerState_t timers[PMU_TIMER_MAX_TIMERS];
static PMU_TimerStats_t timer_stats = {0};
static bool timer_initialized = false;

/* Private function prototypes -----------------------------------------------*/

static PMU_TimerState_t* FindTimer(const char* id);
static PMU_TimerState_t* FindFreeSlot(void);
static void UpdateSingleTimer(PMU_TimerState_t* timer, uint32_t now_ms);
static bool CheckEdge(int32_t prev, int32_t curr, PMU_EdgeType_t edge);
static void RegisterTimerChannels(PMU_TimerState_t* timer, uint8_t timer_index);
static void UnregisterTimerChannels(PMU_TimerState_t* timer);
static void UpdateTimerChannelValues(PMU_TimerState_t* timer);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize timer subsystem
 */
HAL_StatusTypeDef PMU_Timer_Init(void)
{
    memset(timers, 0, sizeof(timers));
    memset(&timer_stats, 0, sizeof(timer_stats));
    timer_initialized = true;

    printf("[TIMER] Subsystem initialized, max %d timers\n", PMU_TIMER_MAX_TIMERS);
    return HAL_OK;
}

/**
 * @brief Add or update a timer configuration
 */
HAL_StatusTypeDef PMU_Timer_AddTimer(const PMU_TimerConfig_t* config)
{
    if (!config || strlen(config->id) == 0) {
        return HAL_ERROR;
    }

    /* Check if timer already exists */
    PMU_TimerState_t* timer = FindTimer(config->id);
    bool is_new = false;

    if (!timer) {
        /* Find free slot */
        timer = FindFreeSlot();
        if (!timer) {
            printf("[TIMER] No free slots for timer '%s'\n", config->id);
            return HAL_ERROR;
        }
        is_new = true;
        timer_stats.total_timers++;
    }

    /* Copy configuration */
    memcpy(&timer->config, config, sizeof(PMU_TimerConfig_t));
    timer->active = true;
    timer->running = false;
    timer->expired = false;
    timer->elapsed_ms = 0;
    timer->start_time_ms = 0;

    /* Calculate limit in milliseconds */
    timer->limit_ms = (uint32_t)config->limit_hours * 3600000UL +
                      (uint32_t)config->limit_minutes * 60000UL +
                      (uint32_t)config->limit_seconds * 1000UL;

    /* Use channel IDs directly from config (already resolved during JSON parsing) */
    timer->start_channel_id = config->start_channel_id;
    timer->stop_channel_id = config->stop_channel_id;

    /* Initialize edge detection */
    if (timer->start_channel_id != 0) {
        timer->prev_start_value = PMU_Channel_GetValue(timer->start_channel_id);
    }
    if (timer->stop_channel_id != 0) {
        timer->prev_stop_value = PMU_Channel_GetValue(timer->stop_channel_id);
    }

    /* Register runtime channels if new timer */
    if (is_new) {
        uint8_t timer_index = (uint8_t)(timer - timers);
        RegisterTimerChannels(timer, timer_index);
    }

    printf("[TIMER] Added timer '%s': limit=%u ms, mode=%s\n",
           config->id, (unsigned)timer->limit_ms,
           config->mode == PMU_TIMER_MODE_COUNT_DOWN ? "down" : "up");

    return HAL_OK;
}

/**
 * @brief Remove a timer by ID
 */
HAL_StatusTypeDef PMU_Timer_RemoveTimer(const char* id)
{
    PMU_TimerState_t* timer = FindTimer(id);
    if (!timer) {
        return HAL_ERROR;
    }

    /* Unregister runtime channels */
    UnregisterTimerChannels(timer);

    /* Clear timer state */
    if (timer->running) {
        timer_stats.active_timers--;
    }
    memset(timer, 0, sizeof(PMU_TimerState_t));
    timer_stats.total_timers--;

    printf("[TIMER] Removed timer '%s'\n", id);
    return HAL_OK;
}

/**
 * @brief Clear all timers
 */
HAL_StatusTypeDef PMU_Timer_ClearAll(void)
{
    for (int i = 0; i < PMU_TIMER_MAX_TIMERS; i++) {
        if (timers[i].active) {
            UnregisterTimerChannels(&timers[i]);
        }
    }

    memset(timers, 0, sizeof(timers));
    timer_stats.total_timers = 0;
    timer_stats.active_timers = 0;

    printf("[TIMER] All timers cleared\n");
    return HAL_OK;
}

/**
 * @brief Update all timers
 */
void PMU_Timer_Update(void)
{
    if (!timer_initialized) return;

    uint32_t now_ms = HAL_GetTick();

    for (int i = 0; i < PMU_TIMER_MAX_TIMERS; i++) {
        PMU_TimerState_t* timer = &timers[i];

        if (!timer->active) {
            continue;
        }

        UpdateSingleTimer(timer, now_ms);
        UpdateTimerChannelValues(timer);
    }
}

/**
 * @brief Start a timer manually
 */
HAL_StatusTypeDef PMU_Timer_Start(const char* id)
{
    PMU_TimerState_t* timer = FindTimer(id);
    if (!timer || timer->running) {
        return HAL_ERROR;
    }

    timer->running = true;
    timer->expired = false;
    timer->start_time_ms = HAL_GetTick();

    if (timer->config.mode == PMU_TIMER_MODE_COUNT_DOWN) {
        timer->elapsed_ms = timer->limit_ms;
    } else {
        timer->elapsed_ms = 0;
    }

    timer_stats.active_timers++;

    return HAL_OK;
}

/**
 * @brief Stop a timer manually
 */
HAL_StatusTypeDef PMU_Timer_Stop(const char* id)
{
    PMU_TimerState_t* timer = FindTimer(id);
    if (!timer || !timer->running) {
        return HAL_ERROR;
    }

    timer->running = false;
    timer_stats.active_timers--;

    return HAL_OK;
}

/**
 * @brief Reset a timer
 */
HAL_StatusTypeDef PMU_Timer_Reset(const char* id)
{
    PMU_TimerState_t* timer = FindTimer(id);
    if (!timer) {
        return HAL_ERROR;
    }

    if (timer->running) {
        timer->running = false;
        timer_stats.active_timers--;
    }

    timer->elapsed_ms = 0;
    timer->expired = false;
    timer->start_time_ms = 0;

    return HAL_OK;
}

/**
 * @brief Get timer current value in seconds
 */
float PMU_Timer_GetValue(const char* id)
{
    PMU_TimerState_t* timer = FindTimer(id);
    if (!timer) {
        return 0.0f;
    }

    if (timer->config.mode == PMU_TIMER_MODE_COUNT_DOWN) {
        /* Count down: remaining time */
        return (float)timer->elapsed_ms / 1000.0f;
    } else {
        /* Count up: elapsed time */
        return (float)timer->elapsed_ms / 1000.0f;
    }
}

/**
 * @brief Check if timer is running
 */
bool PMU_Timer_IsRunning(const char* id)
{
    PMU_TimerState_t* timer = FindTimer(id);
    return timer ? timer->running : false;
}

/**
 * @brief Check if timer has expired
 */
bool PMU_Timer_IsExpired(const char* id)
{
    PMU_TimerState_t* timer = FindTimer(id);
    return timer ? timer->expired : false;
}

/**
 * @brief Get timer system statistics
 */
const PMU_TimerStats_t* PMU_Timer_GetStats(void)
{
    return &timer_stats;
}

/**
 * @brief Get timer state
 */
const PMU_TimerState_t* PMU_Timer_GetState(const char* id)
{
    return FindTimer(id);
}

/**
 * @brief List all timers
 */
uint8_t PMU_Timer_ListTimers(PMU_TimerConfig_t* configs, uint8_t max_count)
{
    uint8_t count = 0;

    for (int i = 0; i < PMU_TIMER_MAX_TIMERS && count < max_count; i++) {
        if (timers[i].active) {
            memcpy(&configs[count], &timers[i].config, sizeof(PMU_TimerConfig_t));
            count++;
        }
    }

    return count;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Find timer by ID
 */
static PMU_TimerState_t* FindTimer(const char* id)
{
    if (!id || strlen(id) == 0) return NULL;

    for (int i = 0; i < PMU_TIMER_MAX_TIMERS; i++) {
        if (timers[i].active &&
            strcmp(timers[i].config.id, id) == 0) {
            return &timers[i];
        }
    }

    return NULL;
}

/**
 * @brief Find free timer slot
 */
static PMU_TimerState_t* FindFreeSlot(void)
{
    for (int i = 0; i < PMU_TIMER_MAX_TIMERS; i++) {
        if (!timers[i].active) {
            return &timers[i];
        }
    }
    return NULL;
}

/**
 * @brief Check for edge on a signal
 */
static bool CheckEdge(int32_t prev, int32_t curr, PMU_EdgeType_t edge)
{
    bool prev_high = (prev > 500);  /* >0.5 threshold for digital */
    bool curr_high = (curr > 500);

    switch (edge) {
        case PMU_EDGE_RISING:
            return (!prev_high && curr_high);

        case PMU_EDGE_FALLING:
            return (prev_high && !curr_high);

        case PMU_EDGE_BOTH:
            return (prev_high != curr_high);

        case PMU_EDGE_LEVEL:
            return curr_high;  /* Level trigger - just check if signal is high */

        default:
            return false;
    }
}

/**
 * @brief Update a single timer
 */
static void UpdateSingleTimer(PMU_TimerState_t* timer, uint32_t now_ms)
{
    /* Check start trigger (if not running) */
    if (!timer->running) {
        if (timer->start_channel_id != 0) {
            int32_t curr_value = PMU_Channel_GetValue(timer->start_channel_id);

            if (CheckEdge(timer->prev_start_value, curr_value, timer->config.start_edge)) {
                /* Start edge detected - start timer */
                timer->running = true;
                timer->expired = false;
                timer->start_time_ms = now_ms;

                if (timer->config.mode == PMU_TIMER_MODE_COUNT_DOWN) {
                    timer->elapsed_ms = timer->limit_ms;
                } else {
                    timer->elapsed_ms = 0;
                }

                timer_stats.active_timers++;
            }

            timer->prev_start_value = curr_value;
        }
    }

    /* Update elapsed time if running */
    if (timer->running) {
        uint32_t delta = now_ms - timer->start_time_ms;

        if (timer->config.mode == PMU_TIMER_MODE_COUNT_DOWN) {
            /* Count down mode */
            if (delta >= timer->limit_ms) {
                timer->elapsed_ms = 0;
                timer->expired = true;
                timer->running = false;
                timer_stats.active_timers--;
            } else {
                timer->elapsed_ms = timer->limit_ms - delta;
            }
        } else {
            /* Count up mode */
            if (delta >= timer->limit_ms) {
                timer->elapsed_ms = timer->limit_ms;
                timer->expired = true;
                timer->running = false;
                timer_stats.active_timers--;
            } else {
                timer->elapsed_ms = delta;
            }
        }

        /* Check stop trigger */
        if (timer->running && timer->stop_channel_id != 0) {
            int32_t curr_value = PMU_Channel_GetValue(timer->stop_channel_id);

            if (CheckEdge(timer->prev_stop_value, curr_value, timer->config.stop_edge)) {
                /* Stop edge detected - stop timer */
                timer->running = false;
                timer_stats.active_timers--;
            }

            timer->prev_stop_value = curr_value;
        }
    }
}

/**
 * @brief Register runtime channels for a timer
 */
static void RegisterTimerChannels(PMU_TimerState_t* timer, uint8_t timer_index)
{
    char channel_name[48];
    uint16_t base_id = TIMER_CHANNEL_BASE_ID + timer_index * TIMER_CHANNELS_PER_TIMER;

    /* Register r_{id}.value channel */
    {
        PMU_Channel_t channel = {0};
        snprintf(channel_name, sizeof(channel_name), "r_%s.value", timer->config.id);
        strncpy(channel.name, channel_name, sizeof(channel.name) - 1);
        channel.channel_id = base_id;
        channel.hw_class = PMU_CHANNEL_CLASS_OUTPUT_FUNCTION;
        channel.direction = PMU_CHANNEL_DIR_OUTPUT;
        channel.format = PMU_CHANNEL_FORMAT_SIGNED;
        channel.min_value = 0;
        channel.max_value = 359999;  /* Max ~100 hours in seconds */
        strncpy(channel.unit, "s", sizeof(channel.unit) - 1);
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;

        if (PMU_Channel_Register(&channel) == HAL_OK) {
            timer->value_channel_id = base_id;
        }
    }

    /* Register r_{id}.running channel */
    {
        PMU_Channel_t channel = {0};
        snprintf(channel_name, sizeof(channel_name), "r_%s.running", timer->config.id);
        strncpy(channel.name, channel_name, sizeof(channel.name) - 1);
        channel.channel_id = base_id + 1;
        channel.hw_class = PMU_CHANNEL_CLASS_OUTPUT_FUNCTION;
        channel.direction = PMU_CHANNEL_DIR_OUTPUT;
        channel.format = PMU_CHANNEL_FORMAT_BOOLEAN;
        channel.min_value = 0;
        channel.max_value = 1;
        channel.unit[0] = '\0';
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;

        if (PMU_Channel_Register(&channel) == HAL_OK) {
            timer->running_channel_id = base_id + 1;
        }
    }

    /* Register r_{id}.elapsed channel */
    {
        PMU_Channel_t channel = {0};
        snprintf(channel_name, sizeof(channel_name), "r_%s.elapsed", timer->config.id);
        strncpy(channel.name, channel_name, sizeof(channel.name) - 1);
        channel.channel_id = base_id + 2;
        channel.hw_class = PMU_CHANNEL_CLASS_OUTPUT_FUNCTION;
        channel.direction = PMU_CHANNEL_DIR_OUTPUT;
        channel.format = PMU_CHANNEL_FORMAT_SIGNED;
        channel.min_value = 0;
        channel.max_value = 359999;
        strncpy(channel.unit, "s", sizeof(channel.unit) - 1);
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;

        if (PMU_Channel_Register(&channel) == HAL_OK) {
            timer->elapsed_channel_id = base_id + 2;
        }
    }

    printf("[TIMER] Registered runtime channels for '%s': IDs %d-%d\n",
           timer->config.id, base_id, base_id + 2);
}

/**
 * @brief Unregister runtime channels for a timer
 */
static void UnregisterTimerChannels(PMU_TimerState_t* timer)
{
    if (timer->value_channel_id) {
        PMU_Channel_Unregister(timer->value_channel_id);
    }
    if (timer->running_channel_id) {
        PMU_Channel_Unregister(timer->running_channel_id);
    }
    if (timer->elapsed_channel_id) {
        PMU_Channel_Unregister(timer->elapsed_channel_id);
    }
}

/**
 * @brief Update timer runtime channel values
 */
static void UpdateTimerChannelValues(PMU_TimerState_t* timer)
{
    /* Update value channel (seconds) */
    if (timer->value_channel_id) {
        int32_t value_seconds = (int32_t)(timer->elapsed_ms / 1000);
        PMU_Channel_SetValue(timer->value_channel_id, value_seconds);
    }

    /* Update running channel */
    if (timer->running_channel_id) {
        PMU_Channel_SetValue(timer->running_channel_id, timer->running ? 1 : 0);
    }

    /* Update elapsed channel (milliseconds - raw internal value) */
    if (timer->elapsed_channel_id) {
        PMU_Channel_SetValue(timer->elapsed_channel_id, (int32_t)timer->elapsed_ms);
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

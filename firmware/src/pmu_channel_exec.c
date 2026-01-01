/**
 ******************************************************************************
 * @file           : pmu_channel_exec.c
 * @brief          : Firmware Adapter for Shared Channel Executor
 * @author         : R2 m-sport
 * @date           : 2026-01-01
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2026 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_channel_exec.h"
#include "pmu_channel.h"
#include "pmu_hal.h"

/* Shared library headers - only included here, not in public header */
#include "channel_executor.h"
#include "channel_config.h"

#include <string.h>

/* Private types -------------------------------------------------------------*/

/**
 * @brief Virtual channel configuration entry (internal)
 */
typedef struct {
    uint16_t        channel_id;     /**< Channel ID in firmware registry */
    uint8_t         type;           /**< ChannelType_t */
    uint8_t         enabled;        /**< Processing enabled flag */
    ChannelRuntime_t runtime;       /**< Runtime state and config pointer */
} PMU_ExecChannel_t;

/**
 * @brief Channel executor state (internal)
 */
typedef struct {
    ExecContext_t       context;                        /**< Executor context */
    PMU_ExecChannel_t   channels[PMU_EXEC_MAX_CHANNELS]; /**< Channel array */
    uint16_t            channel_count;                  /**< Number of channels */
    uint32_t            exec_count;                     /**< Execution counter */
    uint32_t            last_exec_us;                   /**< Last execution time (us) */
} PMU_ExecState_t;

/* Private variables ---------------------------------------------------------*/

/** Executor state */
static PMU_ExecState_t exec_state;

/** Config storage (static allocation for embedded) */
static uint8_t config_storage[PMU_EXEC_MAX_CHANNELS * 64];  /* ~8KB for configs */
static uint16_t config_storage_used = 0;

/* Private function prototypes -----------------------------------------------*/

static int32_t ExecGetValue(uint16_t channel_id, void* user_data);
static void ExecSetValue(uint16_t channel_id, int32_t value, void* user_data);
static PMU_ExecChannel_t* FindChannel(uint16_t channel_id);
static void* AllocConfig(uint16_t size);

/* Public functions ----------------------------------------------------------*/

/**
 * @brief Initialize channel executor adapter
 */
HAL_StatusTypeDef PMU_ChannelExec_Init(void)
{
    /* Clear state */
    memset(&exec_state, 0, sizeof(exec_state));
    config_storage_used = 0;

    /* Initialize executor context */
    Exec_Init(
        &exec_state.context,
        ExecGetValue,
        ExecSetValue,
        NULL  /* user_data not needed - we use firmware globals */
    );

    return HAL_OK;
}

/**
 * @brief Add a virtual channel to the executor
 */
HAL_StatusTypeDef PMU_ChannelExec_AddChannel(
    uint16_t channel_id,
    uint8_t type,
    const void* config
)
{
    if (exec_state.channel_count >= PMU_EXEC_MAX_CHANNELS) {
        return HAL_ERROR;
    }

    /* Get config size based on type */
    uint16_t config_size = 0;
    switch (type) {
        case CH_TYPE_LOGIC:
            config_size = sizeof(CfgLogic_t);
            break;
        case CH_TYPE_MATH:
            config_size = sizeof(CfgMath_t);
            break;
        case CH_TYPE_TIMER:
            config_size = sizeof(CfgTimer_t);
            break;
        case CH_TYPE_PID:
            config_size = sizeof(CfgPid_t);
            break;
        case CH_TYPE_FILTER:
            config_size = sizeof(CfgFilter_t);
            break;
        case CH_TYPE_TABLE_2D:
            config_size = sizeof(CfgTable2D_t);
            break;
        case CH_TYPE_SWITCH:
            config_size = sizeof(CfgSwitch_t);
            break;
        case CH_TYPE_COUNTER:
            config_size = sizeof(CfgCounter_t);
            break;
        case CH_TYPE_HYSTERESIS:
            config_size = sizeof(CfgHysteresis_t);
            break;
        case CH_TYPE_FLIPFLOP:
            config_size = sizeof(CfgFlipFlop_t);
            break;
        default:
            return HAL_ERROR;  /* Unknown type */
    }

    /* Allocate and copy config */
    void* config_copy = AllocConfig(config_size);
    if (!config_copy) {
        return HAL_ERROR;  /* Out of config storage */
    }
    memcpy(config_copy, config, config_size);

    /* Add channel entry */
    PMU_ExecChannel_t* ch = &exec_state.channels[exec_state.channel_count];
    ch->channel_id = channel_id;
    ch->type = type;
    ch->enabled = 1;

    /* Initialize runtime */
    ch->runtime.id = channel_id;
    ch->runtime.type = type;
    ch->runtime.flags = 0;
    ch->runtime.value = 0;
    ch->runtime.prev_value = 0;
    ch->runtime.config = config_copy;

    /* Initialize state based on type */
    Exec_InitChannelState(&ch->runtime, (ChannelType_t)type);

    exec_state.channel_count++;
    return HAL_OK;
}

/**
 * @brief Remove a channel from the executor
 */
HAL_StatusTypeDef PMU_ChannelExec_RemoveChannel(uint16_t channel_id)
{
    for (uint16_t i = 0; i < exec_state.channel_count; i++) {
        if (exec_state.channels[i].channel_id == channel_id) {
            /* Shift remaining channels down */
            for (uint16_t j = i; j < exec_state.channel_count - 1; j++) {
                exec_state.channels[j] = exec_state.channels[j + 1];
            }
            exec_state.channel_count--;
            return HAL_OK;
        }
    }
    return HAL_ERROR;  /* Not found */
}

/**
 * @brief Clear all channels from executor
 */
void PMU_ChannelExec_Clear(void)
{
    exec_state.channel_count = 0;
    config_storage_used = 0;
}

/**
 * @brief Execute all virtual channels
 */
void PMU_ChannelExec_Update(void)
{
    uint32_t start_tick = HAL_GetTick();

    /* Update timing */
    Exec_UpdateTime(&exec_state.context, start_tick);

    /* Process all enabled channels */
    for (uint16_t i = 0; i < exec_state.channel_count; i++) {
        PMU_ExecChannel_t* ch = &exec_state.channels[i];

        if (!ch->enabled) {
            continue;
        }

        /* Save previous value for change detection */
        ch->runtime.prev_value = ch->runtime.value;

        /* Execute channel through shared library */
        int32_t result = Exec_ProcessChannel(&exec_state.context, &ch->runtime);

        /* Store result */
        ch->runtime.value = result;

        /* Write result to firmware channel registry */
        PMU_Channel_SetValue(ch->channel_id, result);
    }

    exec_state.exec_count++;
    exec_state.last_exec_us = (HAL_GetTick() - start_tick) * 1000;  /* Approximate */
}

/**
 * @brief Enable/disable a channel
 */
HAL_StatusTypeDef PMU_ChannelExec_SetEnabled(uint16_t channel_id, bool enabled)
{
    PMU_ExecChannel_t* ch = FindChannel(channel_id);
    if (!ch) {
        return HAL_ERROR;
    }
    ch->enabled = enabled ? 1 : 0;
    return HAL_OK;
}

/**
 * @brief Reset a channel's state
 */
HAL_StatusTypeDef PMU_ChannelExec_ResetChannel(uint16_t channel_id)
{
    PMU_ExecChannel_t* ch = FindChannel(channel_id);
    if (!ch) {
        return HAL_ERROR;
    }
    Exec_ResetChannelState(&ch->runtime);
    return HAL_OK;
}

/**
 * @brief Load channels from binary configuration blob
 *
 * Binary format:
 * [2 bytes] channel_count
 * For each channel:
 *   [2 bytes] channel_id
 *   [1 byte]  type (ChannelType_t)
 *   [1 byte]  config_size
 *   [N bytes] config data
 */
int PMU_ChannelExec_LoadConfig(const uint8_t* data, uint16_t size)
{
    if (size < 2) {
        return -1;
    }

    /* Clear existing channels */
    PMU_ChannelExec_Clear();

    /* Read channel count */
    uint16_t count = data[0] | (data[1] << 8);
    uint16_t offset = 2;
    int loaded = 0;

    for (uint16_t i = 0; i < count && offset < size; i++) {
        if (offset + 4 > size) {
            break;  /* Not enough data for header */
        }

        uint16_t channel_id = data[offset] | (data[offset + 1] << 8);
        uint8_t type = data[offset + 2];
        uint8_t config_size = data[offset + 3];
        offset += 4;

        if (offset + config_size > size) {
            break;  /* Not enough data for config */
        }

        /* Add channel */
        if (PMU_ChannelExec_AddChannel(channel_id, (ChannelType_t)type, &data[offset]) == HAL_OK) {
            loaded++;
        }

        offset += config_size;
    }

    return loaded;
}

/**
 * @brief Get channel count
 */
uint16_t PMU_ChannelExec_GetChannelCount(void)
{
    return exec_state.channel_count;
}

/**
 * @brief Get execution statistics
 */
void PMU_ChannelExec_GetStats(uint32_t* exec_count, uint32_t* last_exec_us)
{
    if (exec_count) {
        *exec_count = exec_state.exec_count;
    }
    if (last_exec_us) {
        *last_exec_us = exec_state.last_exec_us;
    }
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Get channel value callback for executor
 */
static int32_t ExecGetValue(uint16_t channel_id, void* user_data)
{
    (void)user_data;
    return PMU_Channel_GetValue(channel_id);
}

/**
 * @brief Set channel value callback for executor
 */
static void ExecSetValue(uint16_t channel_id, int32_t value, void* user_data)
{
    (void)user_data;
    PMU_Channel_SetValue(channel_id, value);
}

/**
 * @brief Find channel by ID
 */
static PMU_ExecChannel_t* FindChannel(uint16_t channel_id)
{
    for (uint16_t i = 0; i < exec_state.channel_count; i++) {
        if (exec_state.channels[i].channel_id == channel_id) {
            return &exec_state.channels[i];
        }
    }
    return NULL;
}

/**
 * @brief Allocate config from static storage
 */
static void* AllocConfig(uint16_t size)
{
    /* Align to 4 bytes */
    size = (size + 3) & ~3;

    if (config_storage_used + size > sizeof(config_storage)) {
        return NULL;
    }

    void* ptr = &config_storage[config_storage_used];
    config_storage_used += size;
    return ptr;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

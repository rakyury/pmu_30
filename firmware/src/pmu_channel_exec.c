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

#ifdef NUCLEO_F446RE
#include "stm32f4xx_hal.h"
extern IWDG_HandleTypeDef hiwdg;
#endif

/* Private types -------------------------------------------------------------*/

/**
 * @brief Virtual channel configuration entry (internal)
 * IMPORTANT: Layout must ensure ChannelRuntime_t is 4-byte aligned
 * for proper ARM struct access.
 */
typedef struct {
    uint16_t        channel_id;     /**< Channel ID in firmware registry */
    uint8_t         type;           /**< ChannelType_t */
    uint8_t         enabled;        /**< Processing enabled flag */
    uint16_t        source_id;      /**< Source channel ID (for outputs) */
    uint8_t         hw_index;       /**< Hardware index (for outputs) */
    uint8_t         reserved;       /**< Padding for 4-byte alignment */
    ChannelRuntime_t runtime;       /**< Runtime state and config pointer */
} PMU_ExecChannel_t;

/**
 * @brief Power output link entry (for auto-update)
 */
typedef struct {
    uint16_t        output_id;      /**< Output channel ID */
    uint16_t        source_id;      /**< Source channel to read from */
    uint8_t         hw_index;       /**< Hardware output index (0-29) */
    uint8_t         enabled;        /**< Link active */
} PMU_OutputLink_t;

#define PMU_MAX_OUTPUT_LINKS    32

/**
 * @brief Channel executor state (internal)
 */
typedef struct {
    ExecContext_t       context;                        /**< Executor context */
    PMU_ExecChannel_t   channels[PMU_EXEC_MAX_CHANNELS]; /**< Channel array */
    uint16_t            channel_count;                  /**< Number of channels */
    PMU_OutputLink_t    output_links[PMU_MAX_OUTPUT_LINKS]; /**< Output links */
    uint16_t            output_link_count;              /**< Number of output links */
    uint32_t            exec_count;                     /**< Execution counter */
    uint32_t            last_exec_us;                   /**< Last execution time (us) */
} PMU_ExecState_t;

/* Private variables ---------------------------------------------------------*/

/** Executor state */
static PMU_ExecState_t exec_state;

/** Config storage (static allocation for embedded)
 * IMPORTANT: Must be 4-byte aligned for ARM struct access.
 * Config structs contain int32_t which require 4-byte alignment. */
static uint8_t config_storage[PMU_EXEC_MAX_CHANNELS * 64] __attribute__((aligned(4)));
static uint16_t config_storage_used = 0;

/* External functions (platform-specific) ------------------------------------*/

/* PROFET API - declared here to avoid include dependency issues */
extern HAL_StatusTypeDef PMU_PROFET_SetState(uint8_t channel, uint8_t state);
extern void NucleoOutput_Reset(void);

/* Private function prototypes -----------------------------------------------*/

static int32_t ExecGetValue(uint16_t channel_id, void* user_data);
static void ExecSetValue(uint16_t channel_id, int32_t value, void* user_data);
static PMU_ExecChannel_t* FindChannel(uint16_t channel_id);
static void* AllocConfig(uint16_t size);
static int32_t GetSourceValue(uint16_t channel_id);

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
        case CH_TYPE_NUMBER:
            config_size = sizeof(CfgNumber_t);
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
 * @brief Clear all channels from executor (full reset for config reload)
 */
void PMU_ChannelExec_Clear(void)
{
#ifdef NUCLEO_F446RE
    /* Refresh watchdog */
    HAL_IWDG_Refresh(&hiwdg);
#endif

    /* Save current counts before clearing */
    uint16_t old_channel_count = exec_state.channel_count;
    uint16_t old_link_count = exec_state.output_link_count;

    /* Reset counters FIRST - this prevents Update() from accessing old data */
    exec_state.channel_count = 0;
    exec_state.output_link_count = 0;
    exec_state.exec_count = 0;
    exec_state.last_exec_us = 0;

    /* Reset context timestamps to avoid large dt_ms after reload */
    exec_state.context.now_ms = 0;
    exec_state.context.last_ms = 0;
    exec_state.context.dt_ms = 0;


    /* Skip all memset operations - just reset counters.
     * This is safe because:
     * 1. Counters are already reset, so Update() won't access old channels
     * 2. New channels are added starting from index 0, overwriting old data
     * 3. Config storage allocations start from offset 0, overwriting old data */
    (void)old_channel_count;
    (void)old_link_count;
    config_storage_used = 0;

#ifdef NUCLEO_F446RE
    /* Refresh watchdog */
    HAL_IWDG_Refresh(&hiwdg);
#endif
}
/**
 * @brief Add a power output link (source channel -> hw output)
 */
HAL_StatusTypeDef PMU_ChannelExec_AddOutputLink(
    uint16_t output_id,
    uint16_t source_id,
    uint8_t hw_index
)
{
    if (exec_state.output_link_count >= PMU_MAX_OUTPUT_LINKS) {
        return HAL_ERROR;
    }

    PMU_OutputLink_t* link = &exec_state.output_links[exec_state.output_link_count];
    link->output_id = output_id;
    link->source_id = source_id;
    link->hw_index = hw_index;
    link->enabled = 1;

    exec_state.output_link_count++;
    return HAL_OK;
}

/**
 * @brief Execute all virtual channels and update output links
 */
void PMU_ChannelExec_Update(void)
{
    /* Safety check: validate state to prevent crashes from corruption */
    if (exec_state.channel_count > PMU_EXEC_MAX_CHANNELS ||
        exec_state.output_link_count > PMU_MAX_OUTPUT_LINKS) {
        return;  /* Corrupted state - skip update */
    }

    uint32_t start_tick = HAL_GetTick();

#ifdef NUCLEO_F446RE
    HAL_IWDG_Refresh(&hiwdg);
#endif

    /* Update timing */
    Exec_UpdateTime(&exec_state.context, start_tick);

    /* Process all enabled virtual channels */
    for (uint16_t i = 0; i < exec_state.channel_count; i++) {
        PMU_ExecChannel_t* ch = &exec_state.channels[i];

        if (!ch->enabled) {
            continue;
        }

        /* Safety: ensure config pointer is valid */
        if (ch->runtime.config == NULL) {
            continue;
        }

        /* Save previous value for change detection */
        ch->runtime.prev_value = ch->runtime.value;

        /* Execute channel based on type */
        int32_t result = ch->runtime.value;

        if (ch->runtime.type == CH_TYPE_LOGIC && ch->runtime.config != NULL) {
            /* Simplified inline Logic evaluation for IS_TRUE */
            CfgLogic_t* logic = (CfgLogic_t*)ch->runtime.config;
            if (logic->input_count > 0 && logic->inputs[0] != 0 && logic->inputs[0] != 0xFFFF) {
                int32_t input_val = PMU_Channel_GetValue(logic->inputs[0]);
                if (logic->operation == 0x06) {  /* IS_TRUE */
                    result = (input_val != 0) ? 1 : 0;
                } else if (logic->operation == 0x07) {  /* IS_FALSE */
                    result = (input_val == 0) ? 1 : 0;
                }
            }
        } else if (ch->runtime.type == CH_TYPE_TIMER && ch->runtime.config != NULL) {
            /* Inline Timer evaluation for PULSE mode */
            CfgTimer_t* timer_cfg = (CfgTimer_t*)ch->runtime.config;
            Timer_State_t* timer_st = &ch->runtime.state.timer;

            /* Get trigger input value */
            int32_t trigger = 0;
            if (timer_cfg->trigger_id != 0 && timer_cfg->trigger_id != 0xFFFF) {
                trigger = GetSourceValue(timer_cfg->trigger_id);
            }

            uint32_t now_ms = HAL_GetTick();

            /* Edge detection (common for all modes) */
            uint8_t trigger_now = (trigger != 0) ? 1 : 0;
            uint8_t rising_edge = (trigger_now && !timer_st->last_trigger);
            timer_st->last_trigger = trigger_now;

            /* Start timer on rising edge (only if idle) */
            if (rising_edge && timer_st->state == TIMER_STATE_IDLE) {
                timer_st->state = TIMER_STATE_RUNNING;
                timer_st->start_time_ms = now_ms;
                timer_st->elapsed_ms = 0;
            }

            /* Update elapsed time when running */
            if (timer_st->state == TIMER_STATE_RUNNING) {
                timer_st->elapsed_ms = now_ms - timer_st->start_time_ms;

                /* Check if timer expired */
                if (timer_st->elapsed_ms >= timer_cfg->delay_ms) {
                    timer_st->state = TIMER_STATE_IDLE;
                    timer_st->elapsed_ms = timer_cfg->delay_ms; /* Cap at max */
                }
            }

            /* Output depends on mode:
             * Mode 0 (COUNT_UP): output = elapsed_ms
             * Mode 1 (COUNT_DOWN): output = remaining_ms
             * Mode 2 (PULSE): output = 1 while running, 0 when idle
             */
            if (timer_cfg->mode == 0) {
                /* COUNT_UP: output is elapsed time */
                result = (int32_t)timer_st->elapsed_ms;
            } else if (timer_cfg->mode == 1) {
                /* COUNT_DOWN: output is remaining time */
                if (timer_st->state == TIMER_STATE_RUNNING) {
                    result = (int32_t)(timer_cfg->delay_ms - timer_st->elapsed_ms);
                } else {
                    result = 0;
                }
            } else {
                /* PULSE and others: output is 1 while running */
                result = (timer_st->state == TIMER_STATE_RUNNING) ? 1 : 0;
            }
        }
        /* Add other types as needed: MATH, FILTER, etc. */

        /* Store result */
        ch->runtime.value = result;
    }

#ifdef NUCLEO_F446RE
    HAL_IWDG_Refresh(&hiwdg);
#endif

    /* Process output links: read source channel -> set hardware output */
    for (uint16_t i = 0; i < exec_state.output_link_count; i++) {
        PMU_OutputLink_t* link = &exec_state.output_links[i];

        if (!link->enabled) {
            continue;
        }

        /* Read source channel value (check executor channels first, then firmware) */
        int32_t source_value = GetSourceValue(link->source_id);

        /* Convert to output state (non-zero = ON) */
        uint8_t state = (source_value != 0) ? 1 : 0;

        /* Set hardware output via PROFET API (updates stub_channels for telemetry) */
        PMU_PROFET_SetState(link->hw_index, state);

        /* Also update the output channel value in registry */
        PMU_Channel_SetValue(link->output_id, state ? 1000 : 0);
    }

    exec_state.exec_count++;
    exec_state.last_exec_us = (HAL_GetTick() - start_tick) * 1000;
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
 * Binary format (full CfgChannelHeader_t, 14 bytes):
 * [2 bytes] channel_count
 * For each channel:
 *   [2 bytes] id
 *   [1 byte]  type (ChannelType_t)
 *   [1 byte]  flags
 *   [1 byte]  hw_device
 *   [1 byte]  hw_index
 *   [2 bytes] source_id
 *   [4 bytes] default_value
 *   [1 byte]  name_len
 *   [1 byte]  config_size
 *   [N bytes] name (name_len bytes)
 *   [M bytes] config data (config_size bytes)
 */
int PMU_ChannelExec_LoadConfig(const uint8_t* data, uint16_t size)
{
    if (size < 2) {
        return -1;
    }

#ifdef NUCLEO_F446RE
    HAL_IWDG_Refresh(&hiwdg);
#endif

    /* Clear existing channels and reset outputs */
    PMU_ChannelExec_Clear();

#ifdef NUCLEO_F446RE
    HAL_IWDG_Refresh(&hiwdg);
#endif

    NucleoOutput_Reset();

#ifdef NUCLEO_F446RE
    HAL_IWDG_Refresh(&hiwdg);
#endif

    /* Read channel count */
    uint16_t count = data[0] | (data[1] << 8);
    uint16_t offset = 2;
    int loaded = 0;

    for (uint16_t i = 0; i < count && offset < size; i++) {
#ifdef NUCLEO_F446RE
        HAL_IWDG_Refresh(&hiwdg);
#endif
        /* Check for minimum header size (14 bytes) */
        if (offset + 14 > size) {
            break;  /* Not enough data for header */
        }

        /* Parse CfgChannelHeader_t */
        uint16_t channel_id = data[offset] | (data[offset + 1] << 8);
        uint8_t type = data[offset + 2];
        /* uint8_t flags = data[offset + 3]; */
        /* uint8_t hw_device = data[offset + 4]; */
        uint8_t hw_index = data[offset + 5];
        uint16_t source_id = data[offset + 6] | (data[offset + 7] << 8);
        /* int32_t default_value = ... (offset + 8..11) */
        uint8_t name_len = data[offset + 12];
        uint8_t config_size = data[offset + 13];
        offset += 14;

        /* Validate channel ID - ID 0 is reserved/invalid (matches Val_IsValidChannelId) */
        if (channel_id == 0) {
            offset += name_len + config_size;  /* Skip this channel */
            continue;
        }

        /* Skip name */
        if (offset + name_len > size) {
            break;
        }
        offset += name_len;

        /* Check for config data */
        if (offset + config_size > size) {
            break;
        }

        /* Handle based on channel type */
        if (type == CH_TYPE_POWER_OUTPUT) {
            /* Power output: create link from source_id to hw_index */
            /* source_id must be valid: not CH_REF_NONE (0xFFFF) and not 0 */
            if (source_id != 0xFFFF && source_id != 0) {
                if (PMU_ChannelExec_AddOutputLink(channel_id, source_id, hw_index) == HAL_OK) {
                    loaded++;
                }
            }
        } else if (type >= CH_TYPE_TIMER && type <= CH_TYPE_FLIPFLOP) {
            /* Virtual channel: add to executor */
            if (PMU_ChannelExec_AddChannel(channel_id, type, &data[offset]) == HAL_OK) {
                loaded++;
            }
        } else if (type == CH_TYPE_CAN_INPUT || type == CH_TYPE_CAN_OUTPUT) {
            /* CAN channels: count as loaded (CAN processing is stubbed on Nucleo)
             * TODO: Implement PMU_CAN_AddSignalMap() integration for real CAN hardware */
            loaded++;
        }
        /* Skip unsupported types (digital inputs, analog inputs, etc.) */

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

/**
 * @brief Get channel data for telemetry
 */
bool PMU_ChannelExec_GetChannelInfo(uint16_t index, uint16_t* channel_id, int32_t* value)
{
    if (index >= exec_state.channel_count) {
        return false;
    }

    PMU_ExecChannel_t* ch = &exec_state.channels[index];
    if (channel_id) {
        *channel_id = ch->channel_id;
    }
    if (value) {
        *value = ch->runtime.value;
    }
    return true;
}

/**
 * @brief Sub-channel ID offsets for Timer properties
 *
 * Sub-channel ID = parent_id | SUB_xxx
 * Example: Timer 201 elapsed = 201 | 0x8000 = 32969
 */
#define SUB_ELAPSED   0x8000  /**< Timer elapsed time (ms) */
#define SUB_REMAINING 0x8001  /**< Timer remaining time (ms) */
#define SUB_STATE     0x8002  /**< Timer state (0=idle,1=running,2=expired) */

/**
 * @brief Get Timer sub-channel data for telemetry
 *
 * @param index Channel index
 * @param sub_index Sub-property (0=elapsed, 1=remaining, 2=state)
 * @param sub_channel_id Output: sub-channel ID
 * @param sub_value Output: sub-channel value
 * @return true if valid
 */
bool PMU_ChannelExec_GetTimerSubChannel(uint16_t index, uint8_t sub_index,
                                         uint16_t* sub_channel_id, int32_t* sub_value)
{
    if (index >= exec_state.channel_count) {
        return false;
    }

    PMU_ExecChannel_t* ch = &exec_state.channels[index];

    if (ch->runtime.type != CH_TYPE_TIMER || ch->runtime.config == NULL) {
        return false;
    }

    CfgTimer_t* cfg = (CfgTimer_t*)ch->runtime.config;
    Timer_State_t* st = &ch->runtime.state.timer;

    switch (sub_index) {
        case 0: /* elapsed */
            if (sub_channel_id) *sub_channel_id = ch->channel_id | SUB_ELAPSED;
            if (sub_value) *sub_value = (int32_t)st->elapsed_ms;
            return true;

        case 1: /* remaining */
            if (sub_channel_id) *sub_channel_id = ch->channel_id | SUB_REMAINING;
            if (sub_value) {
                uint32_t remaining = 0;
                if (st->elapsed_ms < cfg->delay_ms) {
                    remaining = cfg->delay_ms - st->elapsed_ms;
                }
                *sub_value = (int32_t)remaining;
            }
            return true;

        case 2: /* state */
            if (sub_channel_id) *sub_channel_id = ch->channel_id | SUB_STATE;
            if (sub_value) *sub_value = (int32_t)st->state;
            return true;

        default:
            return false;
    }
}

/**
 * @brief Get number of sub-channels for a channel
 */
uint8_t PMU_ChannelExec_GetSubChannelCount(uint16_t index)
{
    if (index >= exec_state.channel_count) {
        return 0;
    }
    PMU_ExecChannel_t* ch = &exec_state.channels[index];
    /* Timer has 3 sub-channels: elapsed, remaining, state */
    return (ch->runtime.type == CH_TYPE_TIMER) ? 3 : 0;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Get channel value callback for executor
 * Uses GetSourceValue to check executor channels first, then firmware.
 */
static int32_t ExecGetValue(uint16_t channel_id, void* user_data)
{
    (void)user_data;
    return GetSourceValue(channel_id);
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

/**
 * @brief Get channel value, checking executor channels first
 *
 * For virtual channels (Logic, Timer, etc.) that exist only in the executor,
 * we read directly from runtime.value. For hardware channels (DIN, ADC, etc.)
 * we fall back to PMU_Channel_GetValue().
 *
 * @param channel_id Channel ID to read
 * @return Channel value
 */
static int32_t GetSourceValue(uint16_t channel_id)
{
    /* First check if this is an executor channel (virtual) */
    PMU_ExecChannel_t* ch = FindChannel(channel_id);
    if (ch) {
        return ch->runtime.value;
    }

    /* Not an executor channel - read from firmware channel registry */
    return PMU_Channel_GetValue(channel_id);
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

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

/* Debug variables for output link tracing */
volatile uint16_t g_dbg_link_count = 0;       /**< Output link count after load */
volatile uint16_t g_dbg_link_source_id = 0;   /**< First link's source_id */
volatile uint8_t g_dbg_link_hw_index = 0;     /**< First link's hw_index */
volatile int32_t g_dbg_source_value = -999;   /**< Last read source value */
volatile uint8_t g_dbg_output_state = 0;      /**< Last calculated output state */
volatile uint32_t g_dbg_link_exec_count = 0;  /**< How many times link was processed */
volatile uint32_t g_dbg_load_count = 0;       /**< How many times LoadConfig called */
volatile uint32_t g_dbg_clear_count = 0;      /**< How many times Clear called */
/* Parsing debug */
volatile uint8_t g_dbg_parsed_type = 0;       /**< Type parsed from config */
volatile uint16_t g_dbg_parsed_source = 0;    /**< Source ID parsed from config */
volatile uint8_t g_dbg_addlink_called = 0;    /**< Was AddOutputLink called? */
volatile int8_t g_dbg_addlink_result = -1;    /**< Result of AddOutputLink (-1=not called) */
volatile uint8_t g_dbg_getsrc_in_exec = 0;    /**< Was source found in executor? */
volatile uint8_t g_dbg_getsrc_ch_found = 0;   /**< Was channel found in registry? */

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
    /* Debug: track how many times Clear is called */
    g_dbg_clear_count++;

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

        /* Execute channel - simplified for now (hold value, skip complex processing) */
        int32_t result = ch->runtime.value;

        /* Store result */
        ch->runtime.value = result;
    }

#ifdef NUCLEO_F446RE
    HAL_IWDG_Refresh(&hiwdg);
#endif

    /* Debug: record link count */
    g_dbg_link_count = exec_state.output_link_count;

    /* Process output links: read source channel -> set hardware output */
    for (uint16_t i = 0; i < exec_state.output_link_count; i++) {
        PMU_OutputLink_t* link = &exec_state.output_links[i];

        /* Debug: record first link info */
        if (i == 0) {
            g_dbg_link_source_id = link->source_id;
            g_dbg_link_hw_index = link->hw_index;
        }

        if (!link->enabled) {
            continue;
        }

        /* Read source channel value (check executor channels first, then firmware) */
        int32_t source_value = GetSourceValue(link->source_id);

        /* Debug: record source value and increment exec count */
        if (i == 0) {
            g_dbg_source_value = source_value;
            g_dbg_link_exec_count++;
        }

        /* Convert to output state (non-zero = ON) */
        uint8_t state = (source_value != 0) ? 1 : 0;

        /* Debug: record calculated state */
        if (i == 0) {
            g_dbg_output_state = state;
        }

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
    /* Debug: track how many times LoadConfig is called */
    g_dbg_load_count++;

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

        /* Debug: record parsed values from first channel */
        if (i == 0) {
            g_dbg_parsed_type = type;
            g_dbg_parsed_source = source_id;
        }

        /* Handle based on channel type */
        if (type == CH_TYPE_POWER_OUTPUT) {
            /* Power output: create link from source_id to hw_index */
            /* source_id must be valid: not CH_REF_NONE (0xFFFF) and not 0 */
            if (source_id != 0xFFFF && source_id != 0) {
                g_dbg_addlink_called = 1;
                HAL_StatusTypeDef res = PMU_ChannelExec_AddOutputLink(channel_id, source_id, hw_index);
                g_dbg_addlink_result = (res == HAL_OK) ? 1 : 0;
                if (res == HAL_OK) {
                    loaded++;
                }
            }
        } else if (type >= CH_TYPE_TIMER && type <= CH_TYPE_FLIPFLOP) {
            /* Virtual channel: add to executor */
            if (PMU_ChannelExec_AddChannel(channel_id, type, &data[offset]) == HAL_OK) {
                loaded++;
            }
        } else if (type == CH_TYPE_DIGITAL_INPUT) {
            /* Digital Input: register in firmware channel registry
             * hw_index maps to g_digital_inputs[] which is updated by DigitalInputs_Read() */
            PMU_Channel_t din_channel;
            memset(&din_channel, 0, sizeof(din_channel));
            din_channel.channel_id = channel_id;
            din_channel.hw_class = PMU_CHANNEL_CLASS_INPUT_SWITCH;
            din_channel.direction = PMU_CHANNEL_DIR_INPUT;
            din_channel.format = PMU_CHANNEL_FORMAT_BOOLEAN;
            din_channel.physical_index = hw_index;
            din_channel.flags = PMU_CHANNEL_FLAG_ENABLED;
            din_channel.min_value = 0;
            din_channel.max_value = 1;
            if (PMU_Channel_Register(&din_channel) == HAL_OK) {
                loaded++;
            }
        } else if (type == CH_TYPE_CAN_INPUT || type == CH_TYPE_CAN_OUTPUT) {
            /* CAN channels: count as loaded (CAN processing is stubbed on Nucleo)
             * TODO: Implement PMU_CAN_AddSignalMap() integration for real CAN hardware */
            loaded++;
        }
        /* Skip unsupported types (analog inputs, etc.) */

        offset += config_size;
    }

    /* Debug: capture link count immediately after loading */
    g_dbg_link_count = exec_state.output_link_count;
    if (exec_state.output_link_count > 0) {
        /* Record first link's details */
        g_dbg_link_source_id = exec_state.output_links[0].source_id;
        g_dbg_link_hw_index = exec_state.output_links[0].hw_index;
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
        g_dbg_getsrc_in_exec = 1;
        return ch->runtime.value;
    }
    g_dbg_getsrc_in_exec = 0;

    /* Not an executor channel - read from firmware channel registry */
    int32_t val = PMU_Channel_GetValue(channel_id);

    /* Debug: check if GetInfo would return NULL */
    const PMU_Channel_t* info = PMU_Channel_GetInfo(channel_id);
    g_dbg_getsrc_ch_found = (info != NULL) ? 1 : 0;

    return val;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

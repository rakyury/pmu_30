/**
 ******************************************************************************
 * @file           : pmu_channel_exec.h
 * @brief          : Firmware Adapter for Shared Channel Executor
 * @author         : R2 m-sport
 * @date           : 2026-01-01
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2026 R2 m-sport.
 * All rights reserved.
 *
 * This adapter connects the shared library Channel Executor to the firmware
 * channel system. It provides:
 * - Value callbacks (get/set) that route to PMU_Channel_*
 * - Runtime storage for virtual channels
 * - Configuration loading from binary format
 *
 * NOTE: This header is intentionally minimal to avoid conflicts between
 * legacy pmu_logic.h and new shared/engine/logic.h enum definitions.
 * Internal types are hidden in the .c file.
 *
 ******************************************************************************
 */

#ifndef PMU_CHANNEL_EXEC_H
#define PMU_CHANNEL_EXEC_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "pmu_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported constants --------------------------------------------------------*/

/** Maximum virtual channels that can be processed */
#define PMU_EXEC_MAX_CHANNELS       128

/* Channel types (mirrors ChannelType_t from shared library) */
#define PMU_EXEC_TYPE_POWER_OUTPUT  0x10  /* Power output with source linking */
#define PMU_EXEC_TYPE_TIMER         0x20
#define PMU_EXEC_TYPE_LOGIC         0x21
#define PMU_EXEC_TYPE_MATH          0x22
#define PMU_EXEC_TYPE_TABLE_2D      0x23
#define PMU_EXEC_TYPE_FILTER        0x25
#define PMU_EXEC_TYPE_PID           0x26
#define PMU_EXEC_TYPE_SWITCH        0x28
#define PMU_EXEC_TYPE_COUNTER       0x2A
#define PMU_EXEC_TYPE_HYSTERESIS    0x2B
#define PMU_EXEC_TYPE_FLIPFLOP      0x2C

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize channel executor adapter
 * @retval HAL_OK on success
 */
HAL_StatusTypeDef PMU_ChannelExec_Init(void);

/**
 * @brief Add a virtual channel to the executor
 * @param channel_id    Channel ID in firmware registry
 * @param type          Channel type (PMU_EXEC_TYPE_*)
 * @param config        Pointer to type-specific config (must remain valid!)
 * @retval HAL_OK on success, HAL_ERROR if full
 */
HAL_StatusTypeDef PMU_ChannelExec_AddChannel(
    uint16_t channel_id,
    uint8_t type,
    const void* config
);

/**
 * @brief Add a power output link (source channel -> hardware output)
 * @param output_id     Output channel ID in firmware registry
 * @param source_id     Source channel ID to read value from
 * @param hw_index      Hardware output index (0-29 for PROFET outputs)
 * @retval HAL_OK on success, HAL_ERROR if full
 *
 * When PMU_ChannelExec_Update() runs, it reads source_id value and
 * sets the hardware output state (non-zero = ON, zero = OFF).
 */
HAL_StatusTypeDef PMU_ChannelExec_AddOutputLink(
    uint16_t output_id,
    uint16_t source_id,
    uint8_t hw_index
);

/**
 * @brief Remove a channel from the executor
 * @param channel_id    Channel ID to remove
 * @retval HAL_OK on success
 */
HAL_StatusTypeDef PMU_ChannelExec_RemoveChannel(uint16_t channel_id);

/**
 * @brief Clear all channels from executor
 */
void PMU_ChannelExec_Clear(void);

/**
 * @brief Execute all virtual channels (call at 500Hz or 1kHz)
 *
 * This is the main processing function. It:
 * 1. Updates timing (dt_ms)
 * 2. Iterates through all enabled channels
 * 3. Calls Exec_ProcessChannel for each
 * 4. Writes results to channel registry
 */
void PMU_ChannelExec_Update(void);

/**
 * @brief Enable/disable a channel
 * @param channel_id    Channel ID
 * @param enabled       Enable flag
 * @retval HAL_OK on success
 */
HAL_StatusTypeDef PMU_ChannelExec_SetEnabled(uint16_t channel_id, bool enabled);

/**
 * @brief Reset a channel's state (timer, counter, etc.)
 * @param channel_id    Channel ID to reset
 * @retval HAL_OK on success
 */
HAL_StatusTypeDef PMU_ChannelExec_ResetChannel(uint16_t channel_id);

/**
 * @brief Load channels from binary configuration blob
 * @param data          Pointer to binary config data
 * @param size          Size of data in bytes
 * @retval Number of channels loaded, or -1 on error
 */
int PMU_ChannelExec_LoadConfig(const uint8_t* data, uint16_t size);

/**
 * @brief Get channel count
 * @retval Number of channels in executor
 */
uint16_t PMU_ChannelExec_GetChannelCount(void);

/**
 * @brief Get execution statistics
 * @param exec_count    Output: number of executions
 * @param last_exec_us  Output: last execution time in microseconds
 */
void PMU_ChannelExec_GetStats(uint32_t* exec_count, uint32_t* last_exec_us);

#ifdef __cplusplus
}
#endif

#endif /* PMU_CHANNEL_EXEC_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

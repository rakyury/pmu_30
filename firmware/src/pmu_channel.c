/**
 ******************************************************************************
 * @file           : pmu_channel.c
 * @brief          : Universal Channel Abstraction Layer Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Unified channel abstraction implementation providing:
 * - Single API for all input/output types
 * - Automatic routing to underlying drivers
 * - Virtual channel support
 * - Name-based channel lookup
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_channel.h"
#include "pmu_adc.h"
#include "pmu_profet.h"
#include "pmu_hbridge.h"
#include "pmu_can.h"
#include "pmu_logic.h"
#include "pmu_protection.h"
#include <string.h>
#include <stdlib.h>

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief Channel registry entry
 */
typedef struct {
    PMU_Channel_t channel;      /**< Channel data */
    bool registered;            /**< Registration flag */
} PMU_ChannelEntry_t;

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_ChannelEntry_t channel_registry[PMU_CHANNEL_MAX_CHANNELS];
static PMU_ChannelStats_t channel_stats;

/* Private function prototypes -----------------------------------------------*/
static int32_t Channel_ReadPhysicalInput(const PMU_Channel_t* channel);
static int32_t Channel_ReadVirtualInput(const PMU_Channel_t* channel);
static HAL_StatusTypeDef Channel_WritePhysicalOutput(const PMU_Channel_t* channel, int32_t value);
static HAL_StatusTypeDef Channel_WriteVirtualOutput(const PMU_Channel_t* channel, int32_t value);
static PMU_ChannelEntry_t* Channel_FindEntry(uint16_t channel_id);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize channel abstraction layer
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_Init(void)
{
    /* Clear registry */
    memset(channel_registry, 0, sizeof(channel_registry));
    memset(&channel_stats, 0, sizeof(channel_stats));

    /* Register system channels */
    PMU_Channel_t sys_channel;

    /* Battery voltage */
    memset(&sys_channel, 0, sizeof(sys_channel));
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_BATTERY_V;
    sys_channel.hw_class = PMU_CHANNEL_CLASS_INPUT_SYSTEM;
    sys_channel.direction = PMU_CHANNEL_DIR_INPUT;
    sys_channel.format = PMU_CHANNEL_FORMAT_VOLTAGE;
    sys_channel.physical_index = 0;
    sys_channel.flags = PMU_CHANNEL_FLAG_ENABLED;
    sys_channel.min_value = 0;
    sys_channel.max_value = 30000;  /* 30V max */
    strncpy(sys_channel.name, "Battery Voltage", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "mV", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* Total current */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_TOTAL_I;
    sys_channel.format = PMU_CHANNEL_FORMAT_CURRENT;
    sys_channel.max_value = 100000;  /* 100A max */
    strncpy(sys_channel.name, "Total Current", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "mA", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* MCU temperature */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_MCU_TEMP;
    sys_channel.format = PMU_CHANNEL_FORMAT_SIGNED;
    sys_channel.min_value = -40;
    sys_channel.max_value = 125;
    strncpy(sys_channel.name, "MCU Temperature", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "°C", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* Board temperature */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_BOARD_TEMP;
    strncpy(sys_channel.name, "Board Temperature", sizeof(sys_channel.name));
    PMU_Channel_Register(&sys_channel);

    /* Uptime */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_UPTIME;
    sys_channel.format = PMU_CHANNEL_FORMAT_RAW;
    sys_channel.min_value = 0;
    sys_channel.max_value = 0x7FFFFFFF;
    strncpy(sys_channel.name, "System Uptime", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "s", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    return HAL_OK;
}

/**
 * @brief Register a new channel
 * @param channel Channel configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_Register(const PMU_Channel_t* channel)
{
    if (!channel) {
        return HAL_ERROR;
    }

    if (channel->channel_id >= PMU_CHANNEL_MAX_CHANNELS) {
        return HAL_ERROR;
    }

    /* Check if already registered */
    if (channel_registry[channel->channel_id].registered) {
        return HAL_ERROR;
    }

    /* Copy channel data */
    memcpy(&channel_registry[channel->channel_id].channel, channel, sizeof(PMU_Channel_t));
    channel_registry[channel->channel_id].registered = true;

    /* Update statistics */
    channel_stats.total_channels++;

    if (PMU_Channel_IsInput(channel->hw_class)) {
        channel_stats.input_channels++;
    } else {
        channel_stats.output_channels++;
    }

    if (PMU_Channel_IsVirtual(channel->hw_class)) {
        channel_stats.virtual_channels++;
    } else {
        channel_stats.physical_channels++;
    }

    return HAL_OK;
}

/**
 * @brief Unregister a channel
 * @param channel_id Channel ID to remove
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_Unregister(uint16_t channel_id)
{
    if (channel_id >= PMU_CHANNEL_MAX_CHANNELS) {
        return HAL_ERROR;
    }

    if (!channel_registry[channel_id].registered) {
        return HAL_ERROR;
    }

    /* Update statistics */
    PMU_Channel_t* ch = &channel_registry[channel_id].channel;

    channel_stats.total_channels--;

    if (PMU_Channel_IsInput(ch->hw_class)) {
        channel_stats.input_channels--;
    } else {
        channel_stats.output_channels--;
    }

    if (PMU_Channel_IsVirtual(ch->hw_class)) {
        channel_stats.virtual_channels--;
    } else {
        channel_stats.physical_channels--;
    }

    /* Clear entry */
    memset(&channel_registry[channel_id], 0, sizeof(PMU_ChannelEntry_t));

    return HAL_OK;
}

/**
 * @brief Get channel value
 * @param channel_id Channel ID
 * @retval Channel value (or 0 if not found)
 */
int32_t PMU_Channel_GetValue(uint16_t channel_id)
{
    PMU_ChannelEntry_t* entry = Channel_FindEntry(channel_id);

    if (!entry) {
        return 0;
    }

    PMU_Channel_t* ch = &entry->channel;

    /* Check if enabled */
    if (!(ch->flags & PMU_CHANNEL_FLAG_ENABLED)) {
        return 0;
    }

    int32_t value = 0;

    /* Read based on channel type */
    if (PMU_Channel_IsInput(ch->hw_class)) {
        if (PMU_Channel_IsPhysical(ch->hw_class)) {
            value = Channel_ReadPhysicalInput(ch);
        } else {
            value = Channel_ReadVirtualInput(ch);
        }
    } else {
        /* For outputs, return cached value */
        value = ch->value;
    }

    /* Apply inversion if needed */
    if (ch->flags & PMU_CHANNEL_FLAG_INVERTED) {
        value = ch->max_value - value;
    }

    /* Update cached value */
    entry->channel.value = value;

    return value;
}

/**
 * @brief Set channel value
 * @param channel_id Channel ID
 * @param value Value to set
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_SetValue(uint16_t channel_id, int32_t value)
{
    PMU_ChannelEntry_t* entry = Channel_FindEntry(channel_id);

    if (!entry) {
        return HAL_ERROR;
    }

    PMU_Channel_t* ch = &entry->channel;

    /* Check if enabled */
    if (!(ch->flags & PMU_CHANNEL_FLAG_ENABLED)) {
        return HAL_ERROR;
    }

    /* Can only set outputs */
    if (PMU_Channel_IsInput(ch->hw_class)) {
        return HAL_ERROR;
    }

    /* Clamp value to range */
    if (value < ch->min_value) value = ch->min_value;
    if (value > ch->max_value) value = ch->max_value;

    /* Apply inversion if needed */
    if (ch->flags & PMU_CHANNEL_FLAG_INVERTED) {
        value = ch->max_value - value;
    }

    /* Update cached value */
    entry->channel.value = value;

    /* Write to physical or virtual output */
    HAL_StatusTypeDef status;

    if (PMU_Channel_IsPhysical(ch->hw_class)) {
        status = Channel_WritePhysicalOutput(ch, value);
    } else {
        status = Channel_WriteVirtualOutput(ch, value);
    }

    return status;
}

/**
 * @brief Get channel information
 * @param channel_id Channel ID
 * @retval Pointer to channel structure (or NULL if not found)
 */
const PMU_Channel_t* PMU_Channel_GetInfo(uint16_t channel_id)
{
    PMU_ChannelEntry_t* entry = Channel_FindEntry(channel_id);

    if (!entry) {
        return NULL;
    }

    return &entry->channel;
}

/**
 * @brief Get channel by name
 * @param name Channel name
 * @retval Pointer to channel structure (or NULL if not found)
 */
const PMU_Channel_t* PMU_Channel_GetByName(const char* name)
{
    if (!name) {
        return NULL;
    }

    for (uint16_t i = 0; i < PMU_CHANNEL_MAX_CHANNELS; i++) {
        if (channel_registry[i].registered) {
            if (strcmp(channel_registry[i].channel.name, name) == 0) {
                return &channel_registry[i].channel;
            }
        }
    }

    return NULL;
}

/**
 * @brief Update all channels (called at 1kHz)
 * @retval None
 */
void PMU_Channel_Update(void)
{
    /* Update system channels */
#if !defined(UNIT_TEST) || defined(PMU_EMULATOR)
    PMU_ChannelEntry_t* entry;

    /* Battery voltage */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_BATTERY_V);
    if (entry) {
        entry->channel.value = PMU_Protection_GetVoltage();
    }

    /* Total current */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_TOTAL_I);
    if (entry) {
        entry->channel.value = PMU_Protection_GetTotalCurrent();
    }

    /* MCU temperature */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    if (entry) {
        entry->channel.value = PMU_Protection_GetTemperature();
    }

    /* Uptime */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_UPTIME);
    if (entry) {
        entry->channel.value = HAL_GetTick() / 1000;
    }
#endif
}

/**
 * @brief Get channel statistics
 * @retval Pointer to statistics structure
 */
const PMU_ChannelStats_t* PMU_Channel_GetStats(void)
{
    return &channel_stats;
}

/**
 * @brief List all channels
 * @param channels Array to fill
 * @param max_count Maximum channels to return
 * @retval Number of channels returned
 */
uint16_t PMU_Channel_List(PMU_Channel_t* channels, uint16_t max_count)
{
    if (!channels || max_count == 0) {
        return 0;
    }

    uint16_t count = 0;

    for (uint16_t i = 0; i < PMU_CHANNEL_MAX_CHANNELS && count < max_count; i++) {
        if (channel_registry[i].registered) {
            memcpy(&channels[count], &channel_registry[i].channel, sizeof(PMU_Channel_t));
            count++;
        }
    }

    return count;
}

/**
 * @brief Enable/disable channel
 * @param channel_id Channel ID
 * @param enabled Enable flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_SetEnabled(uint16_t channel_id, bool enabled)
{
    PMU_ChannelEntry_t* entry = Channel_FindEntry(channel_id);

    if (!entry) {
        return HAL_ERROR;
    }

    if (enabled) {
        entry->channel.flags |= PMU_CHANNEL_FLAG_ENABLED;
    } else {
        entry->channel.flags &= ~PMU_CHANNEL_FLAG_ENABLED;
    }

    return HAL_OK;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Read physical input channel
 * @param channel Channel to read
 * @retval Channel value
 */
static int32_t Channel_ReadPhysicalInput(const PMU_Channel_t* channel)
{
#ifndef UNIT_TEST
    switch (channel->hw_class) {
        case PMU_CHANNEL_INPUT_ANALOG:
        case PMU_CHANNEL_INPUT_DIGITAL:
        case PMU_CHANNEL_INPUT_SWITCH:
        case PMU_CHANNEL_INPUT_ROTARY:
        case PMU_CHANNEL_INPUT_FREQUENCY:
            /* Read from ADC module */
            return PMU_ADC_GetRawValue(channel->physical_index);

        default:
            return 0;
    }
#else
    (void)channel;
    return 512;  /* Mid-scale for unit tests */
#endif
}

/**
 * @brief Read virtual input channel
 * @param channel Channel to read
 * @retval Channel value
 */
static int32_t Channel_ReadVirtualInput(const PMU_Channel_t* channel)
{
#ifndef UNIT_TEST
    switch (channel->hw_class) {
        case PMU_CHANNEL_INPUT_CAN:
            /* Read from CAN module */
            /* TODO: Implement CAN input reading */
            return 0;

        case PMU_CHANNEL_INPUT_CALCULATED:
            /* Read from logic module */
            return PMU_Logic_GetVChannel(channel->physical_index);

        case PMU_CHANNEL_INPUT_SYSTEM:
            /* System values handled in PMU_Channel_Update() */
            return channel->value;

        default:
            return 0;
    }
#else
    (void)channel;
    return 512;
#endif
}

/**
 * @brief Write physical output channel
 * @param channel Channel to write
 * @param value Value to write
 * @retval HAL status
 */
static HAL_StatusTypeDef Channel_WritePhysicalOutput(const PMU_Channel_t* channel, int32_t value)
{
#ifndef UNIT_TEST
    switch (channel->hw_class) {
        case PMU_CHANNEL_OUTPUT_POWER:
        case PMU_CHANNEL_OUTPUT_PWM:
            /* Write to PROFET module */
            if (value > 0) {
                PMU_PROFET_SetState(channel->physical_index, 1);
                PMU_PROFET_SetPWM(channel->physical_index, (uint16_t)value);
            } else {
                PMU_PROFET_SetState(channel->physical_index, 0);
            }
            return HAL_OK;

        case PMU_CHANNEL_OUTPUT_HBRIDGE:
            /* Write to H-bridge module */
            /* value format: direction in sign, magnitude in abs value */
            {
                PMU_HBridge_Mode_t mode = PMU_HBRIDGE_MODE_COAST;
                uint16_t duty = abs(value);

                if (value > 0) {
                    mode = PMU_HBRIDGE_MODE_FORWARD;
                } else if (value < 0) {
                    mode = PMU_HBRIDGE_MODE_REVERSE;
                }

                PMU_HBridge_SetMode(channel->physical_index / 2, mode, duty);
            }
            return HAL_OK;

        case PMU_CHANNEL_OUTPUT_ANALOG:
            /* Write to DAC */
            /* TODO: Implement DAC output */
            return HAL_OK;

        default:
            return HAL_ERROR;
    }
#else
    (void)channel;
    (void)value;
    return HAL_OK;
#endif
}

/**
 * @brief Write virtual output channel
 * @param channel Channel to write
 * @param value Value to write
 * @retval HAL status
 */
static HAL_StatusTypeDef Channel_WriteVirtualOutput(const PMU_Channel_t* channel, int32_t value)
{
#ifndef UNIT_TEST
    switch (channel->hw_class) {
        case PMU_CHANNEL_OUTPUT_FUNCTION:
        case PMU_CHANNEL_OUTPUT_TABLE:
        case PMU_CHANNEL_OUTPUT_ENUM:
        case PMU_CHANNEL_OUTPUT_NUMBER:
            /* Write to logic module */
            PMU_Logic_SetVChannel(channel->physical_index, value);
            return HAL_OK;

        case PMU_CHANNEL_OUTPUT_CAN:
            /* Write to CAN module */
            /* TODO: Implement CAN output writing */
            return HAL_OK;

        case PMU_CHANNEL_OUTPUT_PID:
            /* PID outputs are read-only (controlled by PID loop) */
            return HAL_ERROR;

        default:
            return HAL_ERROR;
    }
#else
    (void)channel;
    (void)value;
    return HAL_OK;
#endif
}

/**
 * @brief Find channel entry by ID
 * @param channel_id Channel ID
 * @retval Pointer to entry (or NULL if not found)
 */
static PMU_ChannelEntry_t* Channel_FindEntry(uint16_t channel_id)
{
    if (channel_id >= PMU_CHANNEL_MAX_CHANNELS) {
        return NULL;
    }

    if (!channel_registry[channel_id].registered) {
        return NULL;
    }

    return &channel_registry[channel_id];
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

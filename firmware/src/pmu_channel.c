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
#include <stdio.h>

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
static uint16_t next_dynamic_id = 500;  /**< Counter for dynamic channel IDs */

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

    /* Board temperature Left (ECUMaster: pmuX.boardTemperatureL) */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_BOARD_TEMP_L;
    strncpy(sys_channel.name, "Board Temp L", sizeof(sys_channel.name));
    PMU_Channel_Register(&sys_channel);

    /* Board temperature Right (ECUMaster: pmuX.boardTemperatureR) */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_BOARD_TEMP_R;
    strncpy(sys_channel.name, "Board Temp R", sizeof(sys_channel.name));
    PMU_Channel_Register(&sys_channel);

    /* Board temperature Max (ECUMaster: pmuX.boardTemperatureMax) */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_BOARD_TEMP_MAX;
    strncpy(sys_channel.name, "Board Temp Max", sizeof(sys_channel.name));
    PMU_Channel_Register(&sys_channel);

    /* Uptime */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_UPTIME;
    sys_channel.format = PMU_CHANNEL_FORMAT_RAW;
    sys_channel.min_value = 0;
    sys_channel.max_value = 0x7FFFFFFF;
    strncpy(sys_channel.name, "System Uptime", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "s", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* System status (ECUMaster: pmuX.status) */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_STATUS;
    sys_channel.format = PMU_CHANNEL_FORMAT_RAW;
    sys_channel.min_value = 0;
    sys_channel.max_value = 0xFFFF;
    strncpy(sys_channel.name, "System Status", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* User error (ECUMaster: pmuX.userError) */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_USER_ERROR;
    sys_channel.format = PMU_CHANNEL_FORMAT_BOOLEAN;
    sys_channel.min_value = 0;
    sys_channel.max_value = 1;
    strncpy(sys_channel.name, "User Error", sizeof(sys_channel.name));
    PMU_Channel_Register(&sys_channel);

    /* 5V output voltage */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_5V_OUTPUT;
    sys_channel.format = PMU_CHANNEL_FORMAT_VOLTAGE;
    sys_channel.min_value = 0;
    sys_channel.max_value = 6000;  /* 6V max */
    strncpy(sys_channel.name, "5V Output", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "mV", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* 3.3V output voltage */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_3V3_OUTPUT;
    sys_channel.format = PMU_CHANNEL_FORMAT_VOLTAGE;
    sys_channel.min_value = 0;
    sys_channel.max_value = 4000;  /* 4V max */
    strncpy(sys_channel.name, "3.3V Output", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "mV", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* Is turning off flag */
    sys_channel.channel_id = PMU_CHANNEL_SYSTEM_IS_TURNING_OFF;
    sys_channel.format = PMU_CHANNEL_FORMAT_BOOLEAN;
    sys_channel.min_value = 0;
    sys_channel.max_value = 1;
    strncpy(sys_channel.name, "Is Turning Off", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* Constant channel: zero (always returns 0) */
    sys_channel.channel_id = PMU_CHANNEL_CONST_ZERO;
    sys_channel.hw_class = PMU_CHANNEL_CLASS_INPUT_SYSTEM;
    sys_channel.direction = PMU_CHANNEL_DIR_INPUT;
    sys_channel.format = PMU_CHANNEL_FORMAT_BOOLEAN;
    sys_channel.physical_index = 0;
    sys_channel.flags = PMU_CHANNEL_FLAG_ENABLED;
    sys_channel.value = 0;
    sys_channel.min_value = 0;
    sys_channel.max_value = 0;
    strncpy(sys_channel.name, "zero", sizeof(sys_channel.name));
    strncpy(sys_channel.unit, "", sizeof(sys_channel.unit));
    PMU_Channel_Register(&sys_channel);

    /* Constant channel: one (always returns 1000 = 1.0 scaled) */
    sys_channel.channel_id = PMU_CHANNEL_CONST_ONE;
    sys_channel.value = 1000;   /* 1000 = 1.0 in scaled format (used by logic functions) */
    sys_channel.min_value = 1000;
    sys_channel.max_value = 1000;
    strncpy(sys_channel.name, "one", sizeof(sys_channel.name));
    PMU_Channel_Register(&sys_channel);

    /* Register output sub-channels (ECUMaster compatible: oY.status, oY.current, oY.voltage, oY.active) */
    PMU_Channel_t out_channel;
    memset(&out_channel, 0, sizeof(out_channel));
    out_channel.hw_class = PMU_CHANNEL_CLASS_OUTPUT_POWER;
    out_channel.direction = PMU_CHANNEL_DIR_OUTPUT;
    out_channel.flags = PMU_CHANNEL_FLAG_ENABLED;

    for (uint8_t i = 0; i < 30; i++) {
        out_channel.physical_index = i;

        /* oY.status - state code (0-7) */
        out_channel.channel_id = PMU_CHANNEL_OUTPUT_STATUS_BASE + i;
        out_channel.format = PMU_CHANNEL_FORMAT_ENUM;
        out_channel.min_value = 0;
        out_channel.max_value = 7;
        snprintf(out_channel.name, sizeof(out_channel.name), "o_%d.status", i + 1);
        strncpy(out_channel.unit, "", sizeof(out_channel.unit));
        PMU_Channel_Register(&out_channel);

        /* oY.current - current in mA */
        out_channel.channel_id = PMU_CHANNEL_OUTPUT_CURRENT_BASE + i;
        out_channel.format = PMU_CHANNEL_FORMAT_CURRENT;
        out_channel.min_value = 0;
        out_channel.max_value = 40000;  /* 40A max */
        snprintf(out_channel.name, sizeof(out_channel.name), "o_%d.current", i + 1);
        strncpy(out_channel.unit, "mA", sizeof(out_channel.unit));
        PMU_Channel_Register(&out_channel);

        /* oY.voltage - output voltage in mV */
        out_channel.channel_id = PMU_CHANNEL_OUTPUT_VOLTAGE_BASE + i;
        out_channel.format = PMU_CHANNEL_FORMAT_VOLTAGE;
        out_channel.min_value = 0;
        out_channel.max_value = 30000;  /* 30V max */
        snprintf(out_channel.name, sizeof(out_channel.name), "o_%d.voltage", i + 1);
        strncpy(out_channel.unit, "mV", sizeof(out_channel.unit));
        PMU_Channel_Register(&out_channel);

        /* oY.active - boolean active state */
        out_channel.channel_id = PMU_CHANNEL_OUTPUT_ACTIVE_BASE + i;
        out_channel.format = PMU_CHANNEL_FORMAT_BOOLEAN;
        out_channel.min_value = 0;
        out_channel.max_value = 1;
        snprintf(out_channel.name, sizeof(out_channel.name), "o_%d.active", i + 1);
        strncpy(out_channel.unit, "", sizeof(out_channel.unit));
        PMU_Channel_Register(&out_channel);

        /* oY.dutyCycle - PWM duty cycle (0-1000 = 0-100.0%) */
        out_channel.channel_id = PMU_CHANNEL_OUTPUT_DUTY_BASE + i;
        out_channel.format = PMU_CHANNEL_FORMAT_PERCENT;
        out_channel.min_value = 0;
        out_channel.max_value = 1000;
        snprintf(out_channel.name, sizeof(out_channel.name), "o_%d.dutyCycle", i + 1);
        strncpy(out_channel.unit, "%", sizeof(out_channel.unit));
        PMU_Channel_Register(&out_channel);
    }

    return HAL_OK;
}

/**
 * @brief Generate unique channel ID for dynamic channels
 * @retval Unique channel ID
 */
uint16_t PMU_Channel_GenerateID(void)
{
    /* Return and increment the next available dynamic ID */
    return next_dynamic_id++;
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
 * @brief Update channel value (for internal hardware/ADC use)
 * @note Unlike SetValue, this can update INPUT channels (used by ADC system)
 * @param channel_id Channel ID
 * @param value New value
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_UpdateValue(uint16_t channel_id, int32_t value)
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

    /* Clamp value to range */
    if (value < ch->min_value) value = ch->min_value;
    if (value > ch->max_value) value = ch->max_value;

    /* Update cached value (no output write for inputs) */
    entry->channel.value = value;

    return HAL_OK;
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
 * @brief Get channel index (ID) by string name
 * @param name Channel name/ID string
 * @retval Channel ID (0-1023) or 0xFFFF if not found
 */
uint16_t PMU_Channel_GetIndexByID(const char* name)
{
    const PMU_Channel_t* ch = PMU_Channel_GetByName(name);
    if (ch) {
        return ch->channel_id;
    }
    return 0xFFFF;
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

    /* Battery voltage (pmuX.battery) */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_BATTERY_V);
    if (entry) {
        entry->channel.value = PMU_Protection_GetVoltage();
    }

    /* Total current (pmuX.totalCurrent) */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_TOTAL_I);
    if (entry) {
        entry->channel.value = PMU_Protection_GetTotalCurrent();
    }

    /* MCU temperature */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    if (entry) {
        entry->channel.value = PMU_Protection_GetTemperature();
    }

    /* Board temperature Left (pmuX.boardTemperatureL) - primary board sensor */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_BOARD_TEMP_L);
    if (entry) {
        entry->channel.value = PMU_Protection_GetBoardTempL();
    }

    /* Board temperature Right (pmuX.boardTemperatureR) - secondary board sensor */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_BOARD_TEMP_R);
    if (entry) {
        entry->channel.value = PMU_Protection_GetBoardTempR();
    }

    /* Board temperature Max (pmuX.boardTemperatureMax) - highest of L/R */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_BOARD_TEMP_MAX);
    if (entry) {
        int32_t temp_l = PMU_Protection_GetBoardTempL();
        int32_t temp_r = PMU_Protection_GetBoardTempR();
        entry->channel.value = (temp_l > temp_r) ? temp_l : temp_r;
    }

    /* Uptime */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_UPTIME);
    if (entry) {
        entry->channel.value = HAL_GetTick() / 1000;
    }

    /* System status (pmuX.status) */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_STATUS);
    if (entry) {
        entry->channel.value = PMU_Protection_GetStatus();
    }

    /* User error (pmuX.userError) */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_USER_ERROR);
    if (entry) {
        entry->channel.value = PMU_Protection_GetUserError();
    }

    /* 5V output voltage */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_5V_OUTPUT);
    if (entry) {
        entry->channel.value = PMU_Protection_Get5VOutput();
    }

    /* 3.3V output voltage */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_3V3_OUTPUT);
    if (entry) {
        entry->channel.value = PMU_Protection_Get3V3Output();
    }

    /* Is turning off flag */
    entry = Channel_FindEntry(PMU_CHANNEL_SYSTEM_IS_TURNING_OFF);
    if (entry) {
        entry->channel.value = PMU_Protection_IsTurningOff();
    }

    /* Update output sub-channels (oY.status, oY.current, oY.active, oY.dutyCycle) */
    int32_t battery_mv = PMU_Protection_GetVoltage();
    for (uint8_t i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(i);
        if (!profet) continue;

        /* oY.status - state code (0=OFF, 1=ON, 2=OC, 3=OT, 4=SC, 5=OL, 6=PWM) */
        entry = Channel_FindEntry(PMU_CHANNEL_OUTPUT_STATUS_BASE + i);
        if (entry) {
            entry->channel.value = (int32_t)profet->state;
        }

        /* oY.current - current in mA */
        entry = Channel_FindEntry(PMU_CHANNEL_OUTPUT_CURRENT_BASE + i);
        if (entry) {
            entry->channel.value = (int32_t)profet->current_mA;
        }

        /* oY.voltage - output voltage in mV (approximation: battery_v * duty / 1000) */
        entry = Channel_FindEntry(PMU_CHANNEL_OUTPUT_VOLTAGE_BASE + i);
        if (entry) {
            if (profet->state == PMU_PROFET_STATE_ON) {
                entry->channel.value = battery_mv;
            } else if (profet->state == PMU_PROFET_STATE_PWM) {
                entry->channel.value = (battery_mv * profet->pwm_duty) / 1000;
            } else {
                entry->channel.value = 0;
            }
        }

        /* oY.active - boolean: 1 if ON or PWM with duty > 0 */
        entry = Channel_FindEntry(PMU_CHANNEL_OUTPUT_ACTIVE_BASE + i);
        if (entry) {
            entry->channel.value = (profet->state == PMU_PROFET_STATE_ON ||
                                   (profet->state == PMU_PROFET_STATE_PWM && profet->pwm_duty > 0)) ? 1 : 0;
        }

        /* oY.dutyCycle - PWM duty cycle (0-1000 = 0-100.0%) */
        entry = Channel_FindEntry(PMU_CHANNEL_OUTPUT_DUTY_BASE + i);
        if (entry) {
            if (profet->state == PMU_PROFET_STATE_ON) {
                entry->channel.value = 1000;  /* 100% */
            } else if (profet->state == PMU_PROFET_STATE_PWM) {
                entry->channel.value = (int32_t)profet->pwm_duty;
            } else {
                entry->channel.value = 0;  /* 0% */
            }
        }
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
#if !defined(UNIT_TEST) || defined(PMU_EMULATOR)
    switch (channel->hw_class) {
        case PMU_CHANNEL_CLASS_INPUT_DIGITAL:
        case PMU_CHANNEL_CLASS_INPUT_SWITCH:
            /* Return digital state (0 or 1) for switch inputs */
            return (int32_t)PMU_ADC_GetDigitalState(channel->physical_index);

        case PMU_CHANNEL_CLASS_INPUT_ANALOG:
        case PMU_CHANNEL_CLASS_INPUT_ROTARY:
            /* Return raw ADC value for analog inputs */
            return (int32_t)PMU_ADC_GetRawValue(channel->physical_index);

        case PMU_CHANNEL_CLASS_INPUT_FREQUENCY:
            /* Return frequency in Hz */
            return (int32_t)PMU_ADC_GetFrequency(channel->physical_index);

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

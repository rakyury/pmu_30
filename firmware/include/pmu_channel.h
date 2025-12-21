/**
 ******************************************************************************
 * @file           : pmu_channel.h
 * @brief          : Universal Channel Abstraction Layer
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Unified channel abstraction for all inputs/outputs:
 * - Physical inputs: Analog, Digital
 * - Virtual inputs: CAN bus, Calculated values
 * - Physical outputs: Power (PROFET), PWM, H-bridge
 * - Virtual outputs: Functions, Tables, Enumerations, Numbers
 *
 ******************************************************************************
 */

#ifndef PMU_CHANNEL_H
#define PMU_CHANNEL_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Channel type classification
 */
typedef enum {
    /* Physical Inputs (0x00-0x1F) */
    PMU_CHANNEL_INPUT_ANALOG        = 0x00,  /**< Physical analog input (0-5V) */
    PMU_CHANNEL_INPUT_DIGITAL       = 0x01,  /**< Physical digital input (on/off) */
    PMU_CHANNEL_INPUT_SWITCH        = 0x02,  /**< Physical switch input */
    PMU_CHANNEL_INPUT_ROTARY        = 0x03,  /**< Physical rotary switch */
    PMU_CHANNEL_INPUT_FREQUENCY     = 0x04,  /**< Physical frequency input */

    /* Virtual Inputs (0x20-0x3F) */
    PMU_CHANNEL_INPUT_CAN           = 0x20,  /**< Virtual CAN bus input */
    PMU_CHANNEL_INPUT_CALCULATED    = 0x21,  /**< Virtual calculated value */
    PMU_CHANNEL_INPUT_SYSTEM        = 0x22,  /**< System value (voltage, temp, etc.) */

    /* Physical Outputs (0x40-0x5F) */
    PMU_CHANNEL_OUTPUT_POWER        = 0x40,  /**< Power output (PROFET) */
    PMU_CHANNEL_OUTPUT_PWM          = 0x41,  /**< PWM output */
    PMU_CHANNEL_OUTPUT_HBRIDGE      = 0x42,  /**< H-bridge output */
    PMU_CHANNEL_OUTPUT_ANALOG       = 0x43,  /**< Analog output (DAC) */

    /* Virtual Outputs (0x60-0x7F) */
    PMU_CHANNEL_OUTPUT_FUNCTION     = 0x60,  /**< Logic function output */
    PMU_CHANNEL_OUTPUT_TABLE        = 0x61,  /**< Lookup table output */
    PMU_CHANNEL_OUTPUT_ENUM         = 0x62,  /**< Enumeration output */
    PMU_CHANNEL_OUTPUT_NUMBER       = 0x63,  /**< Constant number output */
    PMU_CHANNEL_OUTPUT_CAN          = 0x64,  /**< Virtual CAN bus output */
    PMU_CHANNEL_OUTPUT_PID          = 0x65,  /**< PID controller output */
} PMU_ChannelType_t;

/**
 * @brief Channel direction
 */
typedef enum {
    PMU_CHANNEL_DIR_INPUT  = 0,  /**< Input channel */
    PMU_CHANNEL_DIR_OUTPUT = 1,  /**< Output channel */
    PMU_CHANNEL_DIR_BIDIR  = 2   /**< Bidirectional channel */
} PMU_ChannelDir_t;

/**
 * @brief Channel value format
 */
typedef enum {
    PMU_CHANNEL_FORMAT_RAW      = 0,  /**< Raw ADC/PWM value (0-1023) */
    PMU_CHANNEL_FORMAT_PERCENT  = 1,  /**< Percentage (0-1000 = 0.0-100.0%) */
    PMU_CHANNEL_FORMAT_VOLTAGE  = 2,  /**< Voltage in mV */
    PMU_CHANNEL_FORMAT_CURRENT  = 3,  /**< Current in mA */
    PMU_CHANNEL_FORMAT_BOOLEAN  = 4,  /**< Boolean (0/1) */
    PMU_CHANNEL_FORMAT_ENUM     = 5,  /**< Enumeration (0-255) */
    PMU_CHANNEL_FORMAT_SIGNED   = 6   /**< Signed value (-32768 to +32767) */
} PMU_ChannelFormat_t;

/**
 * @brief Channel metadata
 */
typedef struct {
    uint16_t channel_id;            /**< Global channel ID (0-1023) */
    PMU_ChannelType_t type;         /**< Channel type */
    PMU_ChannelDir_t direction;     /**< Channel direction */
    PMU_ChannelFormat_t format;     /**< Value format */

    uint8_t physical_index;         /**< Physical index (ADC channel, PROFET channel, etc.) */
    uint8_t flags;                  /**< Status flags */

    int32_t value;                  /**< Current value (signed) */
    int32_t min_value;              /**< Minimum value */
    int32_t max_value;              /**< Maximum value */

    char name[32];                  /**< Channel name */
    char unit[8];                   /**< Unit string ("V", "mA", "%", etc.) */
} PMU_Channel_t;

/**
 * @brief Channel registry statistics
 */
typedef struct {
    uint16_t total_channels;        /**< Total registered channels */
    uint16_t input_channels;        /**< Number of input channels */
    uint16_t output_channels;       /**< Number of output channels */
    uint16_t virtual_channels;      /**< Number of virtual channels */
    uint16_t physical_channels;     /**< Number of physical channels */
} PMU_ChannelStats_t;

/* Exported constants --------------------------------------------------------*/

/* Channel ID ranges */
#define PMU_CHANNEL_ID_INPUT_START      0       /**< Physical inputs: 0-99 */
#define PMU_CHANNEL_ID_INPUT_END        99
#define PMU_CHANNEL_ID_OUTPUT_START     100     /**< Physical outputs: 100-199 */
#define PMU_CHANNEL_ID_OUTPUT_END       199
#define PMU_CHANNEL_ID_VIRTUAL_START    200     /**< Virtual channels: 200-999 */
#define PMU_CHANNEL_ID_VIRTUAL_END      999
#define PMU_CHANNEL_ID_SYSTEM_START     1000    /**< System channels: 1000-1023 */
#define PMU_CHANNEL_ID_SYSTEM_END       1023

#define PMU_CHANNEL_MAX_CHANNELS        1024    /**< Maximum channels */

/* Channel flags */
#define PMU_CHANNEL_FLAG_ENABLED        0x01    /**< Channel enabled */
#define PMU_CHANNEL_FLAG_INVERTED       0x02    /**< Value inverted */
#define PMU_CHANNEL_FLAG_FAULT          0x04    /**< Fault detected */
#define PMU_CHANNEL_FLAG_OVERRIDE       0x08    /**< Manual override active */

/* System channel IDs */
#define PMU_CHANNEL_SYSTEM_BATTERY_V    1000    /**< Battery voltage */
#define PMU_CHANNEL_SYSTEM_TOTAL_I      1001    /**< Total current */
#define PMU_CHANNEL_SYSTEM_MCU_TEMP     1002    /**< MCU temperature */
#define PMU_CHANNEL_SYSTEM_BOARD_TEMP   1003    /**< Board temperature */
#define PMU_CHANNEL_SYSTEM_UPTIME       1004    /**< System uptime (seconds) */

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize channel abstraction layer
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_Init(void);

/**
 * @brief Register a new channel
 * @param channel Channel configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_Register(const PMU_Channel_t* channel);

/**
 * @brief Unregister a channel
 * @param channel_id Channel ID to remove
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_Unregister(uint16_t channel_id);

/**
 * @brief Get channel value
 * @param channel_id Channel ID
 * @retval Channel value (or 0 if not found)
 */
int32_t PMU_Channel_GetValue(uint16_t channel_id);

/**
 * @brief Set channel value
 * @param channel_id Channel ID
 * @param value Value to set
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_SetValue(uint16_t channel_id, int32_t value);

/**
 * @brief Get channel information
 * @param channel_id Channel ID
 * @retval Pointer to channel structure (or NULL if not found)
 */
const PMU_Channel_t* PMU_Channel_GetInfo(uint16_t channel_id);

/**
 * @brief Get channel by name
 * @param name Channel name
 * @retval Pointer to channel structure (or NULL if not found)
 */
const PMU_Channel_t* PMU_Channel_GetByName(const char* name);

/**
 * @brief Update all channels (called at 1kHz)
 * @retval None
 */
void PMU_Channel_Update(void);

/**
 * @brief Get channel statistics
 * @retval Pointer to statistics structure
 */
const PMU_ChannelStats_t* PMU_Channel_GetStats(void);

/**
 * @brief List all channels
 * @param channels Array to fill
 * @param max_count Maximum channels to return
 * @retval Number of channels returned
 */
uint16_t PMU_Channel_List(PMU_Channel_t* channels, uint16_t max_count);

/**
 * @brief Enable/disable channel
 * @param channel_id Channel ID
 * @param enabled Enable flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Channel_SetEnabled(uint16_t channel_id, bool enabled);

/**
 * @brief Check if channel is input
 * @param type Channel type
 * @retval true if input, false otherwise
 */
static inline bool PMU_Channel_IsInput(PMU_ChannelType_t type) {
    return (type < 0x40);
}

/**
 * @brief Check if channel is output
 * @param type Channel type
 * @retval true if output, false otherwise
 */
static inline bool PMU_Channel_IsOutput(PMU_ChannelType_t type) {
    return (type >= 0x40);
}

/**
 * @brief Check if channel is virtual
 * @param type Channel type
 * @retval true if virtual, false otherwise
 */
static inline bool PMU_Channel_IsVirtual(PMU_ChannelType_t type) {
    return ((type >= 0x20 && type < 0x40) || (type >= 0x60));
}

/**
 * @brief Check if channel is physical
 * @param type Channel type
 * @retval true if physical, false otherwise
 */
static inline bool PMU_Channel_IsPhysical(PMU_ChannelType_t type) {
    return !PMU_Channel_IsVirtual(type);
}

#ifdef __cplusplus
}
#endif

#endif /* PMU_CHANNEL_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

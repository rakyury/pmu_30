/**
 ******************************************************************************
 * @file           : pmu_adc.h
 * @brief          : Universal ADC Input Driver Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * 20 Universal Analog/Digital Inputs:
 * - 6 input types: Switch Active Low/High, Rotary Switch, Linear Analog,
 *                  Calibrated Analog, Frequency Input
 * - 10-bit resolution (0-1023)
 * - Input protection: overvoltage, reverse polarity
 * - Configurable pull-up/pull-down
 * - Software filtering (moving average)
 * - Debouncing for digital inputs
 * - Threshold configuration
 *
 ******************************************************************************
 */

#ifndef __PMU_ADC_H
#define __PMU_ADC_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "pmu_config.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief ADC input runtime data
 */
typedef struct {
    uint16_t raw_value;             /* Raw ADC value (0-1023) */
    float scaled_value;             /* Scaled value with calibration */
    uint8_t digital_state;          /* Digital state (0/1) for switches */
    uint32_t frequency_hz;          /* Frequency for frequency inputs */
    uint16_t debounce_counter;      /* Debounce counter */
    uint16_t filter_buffer[8];      /* Moving average filter buffer */
    uint8_t filter_index;           /* Filter buffer index */
    uint32_t last_edge_time;        /* Last edge time for frequency */
    uint8_t edge_count;             /* Edge count for frequency */
    uint16_t channel_id;            /* Channel system ID for PMU_Channel_SetValue */
} PMU_ADC_Input_t;

/* Exported constants --------------------------------------------------------*/

/* ADC resolution */
#define PMU_ADC_RESOLUTION          1024    /* 10-bit */
#define PMU_ADC_VREF_MV             3300    /* 3.3V reference */

/* Default thresholds */
#define PMU_ADC_DEFAULT_HIGH_MV     2500    /* 2.5V high threshold */
#define PMU_ADC_DEFAULT_LOW_MV      800     /* 0.8V low threshold */
#define PMU_ADC_DEFAULT_DEBOUNCE_MS 20      /* 20ms debounce */

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize ADC driver
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_ADC_Init(void);

/**
 * @brief Update all ADC inputs (call at 1kHz)
 * @retval None
 */
void PMU_ADC_Update(void);

/**
 * @brief Get raw ADC value
 * @param channel Input channel (0-19)
 * @retval Raw ADC value (0-1023)
 */
uint16_t PMU_ADC_GetRawValue(uint8_t channel);

/**
 * @brief Get scaled value with calibration applied
 * @param channel Input channel (0-19)
 * @retval Scaled value in configured units
 */
float PMU_ADC_GetScaledValue(uint8_t channel);

/**
 * @brief Get digital state (for switch inputs)
 * @param channel Input channel (0-19)
 * @retval Digital state (0 or 1)
 */
uint8_t PMU_ADC_GetDigitalState(uint8_t channel);

/**
 * @brief Set digital state (for emulator/testing)
 * @param channel Input channel (0-19)
 * @param state Digital state (0 or 1)
 * @note Also syncs to channel system
 */
void PMU_ADC_SetDigitalState(uint8_t channel, uint8_t state);

/**
 * @brief Get input type (for emulator to determine voltage logic)
 * @param channel Input channel (0-19)
 * @retval Input type (PMU_LegacyInputType_t) or -1 if not configured
 */
int PMU_ADC_GetInputType(uint8_t channel);

/**
 * @brief Get frequency (for frequency inputs)
 * @param channel Input channel (0-19)
 * @retval Frequency in Hz
 */
uint32_t PMU_ADC_GetFrequency(uint8_t channel);

/**
 * @brief Get input runtime data
 * @param channel Input channel (0-19)
 * @retval Pointer to input data
 */
PMU_ADC_Input_t* PMU_ADC_GetInputData(uint8_t channel);

/**
 * @brief Set input configuration
 * @param channel Input channel (0-19)
 * @param config Pointer to configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_ADC_SetConfig(uint8_t channel, PMU_InputConfig_t* config);

/**
 * @brief Set channel system ID for input
 * @param channel Input channel (0-19)
 * @param channel_id Channel system ID for PMU_Channel_SetValue
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_ADC_SetChannelId(uint8_t channel, uint16_t channel_id);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_ADC_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

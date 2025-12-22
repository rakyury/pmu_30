/**
 ******************************************************************************
 * @file           : pmu_spi.h
 * @brief          : SPI Driver for PROFET Diagnostics Header
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * SPI Interface for diagnostic readout:
 * - External ADC for high-precision current sensing (ADS8688)
 * - Analog multiplexer control (CD74HC4067)
 * - Future: SPI-capable smart switches
 *
 ******************************************************************************
 */

#ifndef __PMU_SPI_H
#define __PMU_SPI_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <stdint.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief SPI device identifiers
 */
typedef enum {
    PMU_SPI_DEV_ADC_CURRENT = 0,    /* External ADC for current sensing */
    PMU_SPI_DEV_ADC_STATUS,         /* External ADC for status/temp sensing */
    PMU_SPI_DEV_MUX_CTRL,           /* Analog multiplexer control */
    PMU_SPI_DEV_DIAG_IC,            /* Future: SPI diagnostic IC */
    PMU_SPI_DEV_COUNT
} PMU_SPI_Device_t;

/**
 * @brief External ADC channel configuration
 */
typedef struct {
    uint8_t  channel;               /* ADC channel (0-15 for 16ch ADC) */
    uint8_t  gain;                  /* PGA gain setting */
    uint16_t offset_cal;            /* Offset calibration value */
    float    scale_factor;          /* Conversion scale factor */
} PMU_SPI_ADC_Channel_t;

/**
 * @brief Diagnostic data from SPI interface
 */
typedef struct {
    uint16_t current_raw[32];       /* Raw current ADC values */
    uint16_t status_raw[32];        /* Raw status ADC values */
    uint32_t current_mA[32];        /* Calculated current in mA */
    int16_t  temperature_C[32];     /* Calculated temperature in C */
    uint8_t  fault_flags[32];       /* Fault flags per channel */
    uint32_t last_update_tick;      /* Last update timestamp */
    uint8_t  comm_error_count;      /* Communication error counter */
} PMU_SPI_DiagData_t;

/**
 * @brief SPI transaction status
 */
typedef enum {
    PMU_SPI_STATUS_OK = 0,
    PMU_SPI_STATUS_BUSY,
    PMU_SPI_STATUS_ERROR,
    PMU_SPI_STATUS_TIMEOUT
} PMU_SPI_Status_t;

/* Exported constants --------------------------------------------------------*/

/* ADS8688 External ADC constants */
#define PMU_SPI_ADC_RESOLUTION      16          /* 16-bit ADC */
#define PMU_SPI_ADC_CHANNELS        16          /* 16 channels per ADC */
#define PMU_SPI_ADC_VREF_MV         4096        /* 4.096V reference */

/* Current sensing constants (kILIS ratio for BTS7008-2EPA) */
#define PMU_SPI_KILIS_RATIO         4700        /* Current mirror ratio */
#define PMU_SPI_SENSE_RESISTOR_OHM  1000        /* Sense resistor value */

/* Timing constants */
#define PMU_SPI_TIMEOUT_MS          10          /* SPI timeout */
#define PMU_SPI_RETRY_COUNT         3           /* Max retries on error */

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize SPI diagnostic interface
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_Init(void);

/**
 * @brief Deinitialize SPI diagnostic interface
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_DeInit(void);

/**
 * @brief Update all diagnostic channels (call from control task)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_Update(void);

/**
 * @brief Read single ADC channel
 * @param device SPI device (current or status ADC)
 * @param channel ADC channel number
 * @param value Pointer to store result
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_ReadADC(PMU_SPI_Device_t device, uint8_t channel, uint16_t* value);

/**
 * @brief Read all ADC channels in sequence
 * @param device SPI device
 * @param buffer Buffer for results (must be ADC_CHANNELS size)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_ReadAllChannels(PMU_SPI_Device_t device, uint16_t* buffer);

/**
 * @brief Get current measurement for PROFET channel
 * @param channel PROFET channel (0-29)
 * @retval Current in mA
 */
uint32_t PMU_SPI_GetCurrent(uint8_t channel);

/**
 * @brief Get temperature for PROFET channel
 * @param channel PROFET channel (0-29)
 * @retval Temperature in degrees C
 */
int16_t PMU_SPI_GetTemperature(uint8_t channel);

/**
 * @brief Get raw ADC value for channel
 * @param channel PROFET channel (0-29)
 * @param type 0=current, 1=status
 * @retval Raw ADC value
 */
uint16_t PMU_SPI_GetRawValue(uint8_t channel, uint8_t type);

/**
 * @brief Get diagnostic data structure
 * @retval Pointer to diagnostic data
 */
PMU_SPI_DiagData_t* PMU_SPI_GetDiagData(void);

/**
 * @brief Set analog multiplexer channel
 * @param mux_channel Multiplexer channel (0-15)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_SetMuxChannel(uint8_t mux_channel);

/**
 * @brief Configure ADC channel
 * @param device SPI device
 * @param channel Channel number
 * @param config Channel configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_ConfigureChannel(PMU_SPI_Device_t device,
                                            uint8_t channel,
                                            PMU_SPI_ADC_Channel_t* config);

/**
 * @brief Calibrate ADC offset
 * @param device SPI device
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_CalibrateOffset(PMU_SPI_Device_t device);

/**
 * @brief Check SPI communication status
 * @retval PMU_SPI_Status_t
 */
PMU_SPI_Status_t PMU_SPI_GetStatus(void);

/**
 * @brief Reset SPI interface after error
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_Reset(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_SPI_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

/**
 ******************************************************************************
 * @file           : pmu_profet.h
 * @brief          : PROFET 2 Output Driver Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

#ifndef __PMU_PROFET_H
#define __PMU_PROFET_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "pmu_config.h"
#include "pmu_spi.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief PROFET 2 channel state
 */
typedef enum {
    PMU_PROFET_STATE_OFF = 0,
    PMU_PROFET_STATE_ON,
    PMU_PROFET_STATE_PWM,
    PMU_PROFET_STATE_FAULT
} PMU_PROFET_State_t;

/**
 * @brief PROFET 2 fault flags
 */
typedef enum {
    PMU_PROFET_FAULT_NONE = 0x00,
    PMU_PROFET_FAULT_OVERCURRENT = 0x01,
    PMU_PROFET_FAULT_OVERTEMP = 0x02,
    PMU_PROFET_FAULT_SHORT_CIRCUIT = 0x04,
    PMU_PROFET_FAULT_OPEN_LOAD = 0x08,
    PMU_PROFET_FAULT_UNDERVOLTAGE = 0x10
} PMU_PROFET_Fault_t;

/**
 * @brief PROFET 2 channel runtime data
 */
typedef struct {
    PMU_PROFET_State_t state;       /* Current state */
    uint16_t current_mA;            /* Measured current in mA */
    int16_t temperature_C;          /* Measured temperature in °C */
    uint16_t pwm_duty;              /* PWM duty cycle (0-1000 = 0-100%) */
    uint32_t on_time_ms;            /* Total on time in milliseconds */
    uint8_t fault_flags;            /* Current fault flags */
    uint8_t fault_count;            /* Fault counter */
} PMU_PROFET_Channel_t;

/* Exported constants --------------------------------------------------------*/

/* Hardware limits */
#define PMU_PROFET_MAX_CURRENT_MA       40000   /* 40A */
#define PMU_PROFET_MAX_INRUSH_MA        160000  /* 160A */
#define PMU_PROFET_MAX_TEMP_C           150     /* 150°C */
#define PMU_PROFET_PWM_RESOLUTION       1000    /* 0.1% resolution */

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize PROFET 2 driver
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_Init(void);

/**
 * @brief Update all PROFET 2 channels (call at 1kHz)
 * @retval None
 */
void PMU_PROFET_Update(void);

/**
 * @brief Set channel on/off
 * @param channel Channel number (0-29)
 * @param state 0=OFF, 1=ON
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_SetState(uint8_t channel, uint8_t state);

/**
 * @brief Set channel PWM duty cycle
 * @param channel Channel number (0-29)
 * @param duty Duty cycle (0-1000 = 0-100%)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_SetPWM(uint8_t channel, uint16_t duty);

/**
 * @brief Get channel current
 * @param channel Channel number (0-29)
 * @retval Current in mA
 */
uint16_t PMU_PROFET_GetCurrent(uint8_t channel);

/**
 * @brief Get channel temperature
 * @param channel Channel number (0-29)
 * @retval Temperature in °C
 */
int16_t PMU_PROFET_GetTemperature(uint8_t channel);

/**
 * @brief Get channel fault status
 * @param channel Channel number (0-29)
 * @retval Fault flags
 */
uint8_t PMU_PROFET_GetFaults(uint8_t channel);

/**
 * @brief Clear channel faults
 * @param channel Channel number (0-29)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_ClearFaults(uint8_t channel);

/**
 * @brief Get channel runtime data
 * @param channel Channel number (0-29)
 * @retval Pointer to channel data
 */
PMU_PROFET_Channel_t* PMU_PROFET_GetChannelData(uint8_t channel);

/**
 * @brief Enable SPI-based diagnostics (high precision mode)
 * @param enable 1=enable, 0=disable
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_EnableSPIDiag(uint8_t enable);

/**
 * @brief Get SPI diagnostic data for all channels
 * @retval Pointer to SPI diagnostic data
 */
PMU_SPI_DiagData_t* PMU_PROFET_GetSPIDiagData(void);

/**
 * @brief Calibrate current sensing (zero offset)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_CalibrateCurrent(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_PROFET_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

/**
 ******************************************************************************
 * @file           : pmu_protection.h
 * @brief          : Protection Systems Header
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

#ifndef __PMU_PROTECTION_H
#define __PMU_PROTECTION_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Protection system status
 */
typedef enum {
    PMU_PROT_STATUS_OK = 0,
    PMU_PROT_STATUS_WARNING,
    PMU_PROT_STATUS_FAULT,
    PMU_PROT_STATUS_CRITICAL
} PMU_Protection_Status_t;

/**
 * @brief Protection fault flags
 */
typedef enum {
    PMU_PROT_FAULT_NONE = 0x0000,

    /* Voltage faults */
    PMU_PROT_FAULT_UNDERVOLTAGE = 0x0001,
    PMU_PROT_FAULT_OVERVOLTAGE = 0x0002,
    PMU_PROT_FAULT_REVERSE_POLARITY = 0x0004,

    /* Temperature faults */
    PMU_PROT_FAULT_OVERTEMP_WARNING = 0x0010,
    PMU_PROT_FAULT_OVERTEMP_CRITICAL = 0x0020,

    /* Power faults */
    PMU_PROT_FAULT_OVERCURRENT_TOTAL = 0x0100,
    PMU_PROT_FAULT_POWER_LIMIT = 0x0200,

    /* System faults */
    PMU_PROT_FAULT_WATCHDOG = 0x1000,
    PMU_PROT_FAULT_BROWNOUT = 0x2000,
    PMU_PROT_FAULT_FLASH_ERROR = 0x4000
} PMU_Protection_Fault_t;

/**
 * @brief Voltage monitoring data
 */
typedef struct {
    uint16_t voltage_mV;            /* Battery voltage in mV */
    uint16_t voltage_min_mV;        /* Minimum voltage threshold */
    uint16_t voltage_max_mV;        /* Maximum voltage threshold */
    uint16_t voltage_warn_low_mV;   /* Low voltage warning threshold */
    uint16_t voltage_warn_high_mV;  /* High voltage warning threshold */
    uint8_t  undervoltage_count;    /* Consecutive undervoltage detections */
    uint8_t  overvoltage_count;     /* Consecutive overvoltage detections */
} PMU_Voltage_Monitor_t;

/**
 * @brief Temperature monitoring data
 */
typedef struct {
    int16_t board_temp_L_C;         /* Board temperature Left in °C (ECUMaster: boardTemperatureL) */
    int16_t board_temp_R_C;         /* Board temperature Right in °C (ECUMaster: boardTemperatureR) */
    int16_t mcu_temp_C;             /* MCU die temperature in °C */
    int16_t temp_warn_C;            /* Warning threshold */
    int16_t temp_critical_C;        /* Critical threshold */
    uint8_t overtemp_count;         /* Consecutive overtemperature detections */
} PMU_Temperature_Monitor_t;

/**
 * @brief Power monitoring data
 */
typedef struct {
    uint32_t total_current_mA;      /* Total output current in mA */
    uint32_t max_current_mA;        /* Maximum allowed current */
    uint32_t total_power_W;         /* Total power consumption in Watts */
    uint32_t max_power_W;           /* Maximum allowed power */
} PMU_Power_Monitor_t;

/**
 * @brief Complete protection system state
 */
typedef struct {
    PMU_Protection_Status_t status;
    uint16_t fault_flags;
    PMU_Voltage_Monitor_t voltage;
    PMU_Temperature_Monitor_t temperature;
    PMU_Power_Monitor_t power;
    uint32_t uptime_seconds;
    uint32_t fault_count_total;
    uint8_t load_shedding_active;
    uint16_t output_5v_mV;          /* 5V output voltage in mV */
    uint16_t output_3v3_mV;         /* 3.3V output voltage in mV */
    uint8_t user_error;             /* User error flag (ECUMaster: userError) */
    uint8_t is_turning_off;         /* Shutdown in progress flag */
    uint16_t system_status;         /* System status bits (ECUMaster: status) */
} PMU_Protection_State_t;

/* Exported constants --------------------------------------------------------*/

/* Voltage thresholds (mV) */
#define PMU_VOLTAGE_MIN             6000    /* Absolute minimum: 6V */
#define PMU_VOLTAGE_WARN_LOW        10500   /* Warning: 10.5V */
#define PMU_VOLTAGE_NOMINAL         12000   /* Nominal: 12V */
#define PMU_VOLTAGE_WARN_HIGH       15000   /* Warning: 15V */
#define PMU_VOLTAGE_MAX             22000   /* Absolute maximum: 22V */

/* Temperature thresholds (°C) */
#define PMU_TEMP_NORMAL             85      /* Normal operation */
#define PMU_TEMP_WARNING            100     /* Warning threshold */
#define PMU_TEMP_CRITICAL           125     /* Critical - start shutdown */

/* Power limits */
#define PMU_TOTAL_CURRENT_MAX_MA    1200000 /* 1200A total (30ch × 40A) */
#define PMU_TOTAL_POWER_MAX_W       14400   /* 14.4kW @ 12V */

/* Fault detection parameters */
#define PMU_FAULT_THRESHOLD         3       /* Consecutive faults before action */
#define PMU_FAULT_RECOVERY_DELAY_MS 1000    /* Delay before auto-recovery */

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize protection system
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protection_Init(void);

/**
 * @brief Update protection system (call at 1kHz)
 * @retval None
 */
void PMU_Protection_Update(void);

/**
 * @brief Get protection system state
 * @retval Pointer to protection state
 */
PMU_Protection_State_t* PMU_Protection_GetState(void);

/**
 * @brief Check if system is in fault state
 * @retval 1 if fault, 0 if OK
 */
uint8_t PMU_Protection_IsFaulted(void);

/**
 * @brief Clear all recoverable faults
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protection_ClearFaults(void);

/**
 * @brief Enable/disable load shedding
 * @param enable 1 to enable, 0 to disable
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protection_SetLoadShedding(uint8_t enable);

/**
 * @brief Get battery voltage in mV
 * @retval Voltage in millivolts
 */
uint16_t PMU_Protection_GetVoltage(void);

/**
 * @brief Get board temperature in °C
 * @retval Temperature in degrees Celsius
 */
int16_t PMU_Protection_GetTemperature(void);

/**
 * @brief Get total system current in mA
 * @retval Current in milliamperes
 */
uint32_t PMU_Protection_GetTotalCurrent(void);

/**
 * @brief Get board temperature Left (primary sensor)
 * @retval Temperature in degrees Celsius
 */
int16_t PMU_Protection_GetBoardTempL(void);

/**
 * @brief Get board temperature Right (secondary sensor)
 * @retval Temperature in degrees Celsius
 */
int16_t PMU_Protection_GetBoardTempR(void);

/**
 * @brief Get system status bits (ECUMaster compatible)
 * @retval Status bits
 */
uint16_t PMU_Protection_GetStatus(void);

/**
 * @brief Get user error flag
 * @retval 1 if user error, 0 otherwise
 */
uint8_t PMU_Protection_GetUserError(void);

/**
 * @brief Get 5V output voltage
 * @retval Voltage in millivolts
 */
uint16_t PMU_Protection_Get5VOutput(void);

/**
 * @brief Get 3.3V output voltage
 * @retval Voltage in millivolts
 */
uint16_t PMU_Protection_Get3V3Output(void);

/**
 * @brief Check if system is in shutdown sequence
 * @retval 1 if turning off, 0 otherwise
 */
uint8_t PMU_Protection_IsTurningOff(void);

/**
 * @brief Activate load shedding - disable lowest priority outputs
 * @param target_reduction_mA Target current reduction in mA
 * @retval Number of outputs shed
 * @note Outputs with shed_priority=0 are never shed (critical loads)
 */
uint8_t PMU_Protection_ActivateLoadShedding(uint32_t target_reduction_mA);

/**
 * @brief Deactivate load shedding - restore all shed outputs
 * @retval Number of outputs restored
 */
uint8_t PMU_Protection_DeactivateLoadShedding(void);

/**
 * @brief Check if load shedding is active
 * @retval 1 if active, 0 otherwise
 */
uint8_t PMU_Protection_IsLoadSheddingActive(void);

/**
 * @brief Get number of outputs currently shed
 * @retval Count of shed outputs
 */
uint8_t PMU_Protection_GetShedOutputCount(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_PROTECTION_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

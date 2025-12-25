/**
 ******************************************************************************
 * @file           : pmu_protection.c
 * @brief          : Protection Systems Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements critical protection systems:
 * - Battery voltage monitoring (6-22V range)
 * - Board and MCU temperature monitoring
 * - Total current and power monitoring
 * - Load shedding for fault recovery
 * - Fault detection and logging
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_protection.h"
#include "pmu_profet.h"
#include "pmu_hbridge.h"
#include "pmu_adc.h"
#include "pmu_handler.h"
#include "stm32h7xx_hal.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define ADC_VREF_MV                 3300    /* ADC reference voltage */
#define ADC_RESOLUTION              4096    /* 12-bit ADC */

/* Voltage divider for battery monitoring (example: 22V -> 3.3V = 6.67:1) */
#define VOLTAGE_DIVIDER_RATIO       6670    /* 6.67 × 1000 for fixed-point */
#define VOLTAGE_DIVIDER_DIV         1000

/* STM32H7 internal temperature sensor */
#define TEMP_SENSOR_AVG_SLOPE       2500    /* 2.5 mV/°C (STM32H7) */
#define TEMP_SENSOR_V25             760000  /* 760 mV at 25°C */

/* Update rate (1kHz) */
#define UPTIME_UPDATE_RATE_HZ       1000

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_Protection_State_t protection_state;
static ADC_HandleTypeDef* hadc_vbat = NULL;
static ADC_HandleTypeDef* hadc_temp = NULL;
static uint32_t uptime_counter = 0;
static uint32_t fault_recovery_timer = 0;

/* Private function prototypes -----------------------------------------------*/
static void Protection_UpdateVoltage(void);
static void Protection_UpdateTemperature(void);
static void Protection_UpdatePower(void);
static void Protection_CheckFaults(void);
static void Protection_HandleLoadShedding(void);
static uint16_t Protection_ReadVbatADC(void);
static int16_t Protection_ReadMCUTemp(void);
int16_t Protection_ReadBoardTempL(void);
int16_t Protection_ReadBoardTempR(void);
static inline int16_t Protection_GetMaxTemp(void);
static uint16_t Protection_Read5VOutput(void);
static uint16_t Protection_Read3V3Output(void);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief Initialize protection system
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protection_Init(void)
{
    /* Clear protection state */
    memset(&protection_state, 0, sizeof(PMU_Protection_State_t));

    /* Initialize voltage monitoring parameters */
    protection_state.voltage.voltage_min_mV = PMU_VOLTAGE_MIN;
    protection_state.voltage.voltage_max_mV = PMU_VOLTAGE_MAX;
    protection_state.voltage.voltage_warn_low_mV = PMU_VOLTAGE_WARN_LOW;
    protection_state.voltage.voltage_warn_high_mV = PMU_VOLTAGE_WARN_HIGH;

    /* Initialize temperature monitoring parameters */
    protection_state.temperature.temp_warn_C = PMU_TEMP_WARNING;
    protection_state.temperature.temp_critical_C = PMU_TEMP_CRITICAL;

    /* Initialize power monitoring parameters */
    protection_state.power.max_current_mA = PMU_TOTAL_CURRENT_MAX_MA;
    protection_state.power.max_power_W = PMU_TOTAL_POWER_MAX_W;

    /* Set initial status */
    protection_state.status = PMU_PROT_STATUS_OK;
    protection_state.fault_flags = PMU_PROT_FAULT_NONE;

    /* Initialize ADC for battery voltage monitoring
     * Battery voltage is typically connected to a dedicated ADC channel
     * with voltage divider (6.67:1 for 22V max -> 3.3V ADC)
     *
     * Internal temp sensor is on ADC3_INP18 for STM32H7
     */

#ifndef UNIT_TEST
    /* Assign ADC handles - adjust based on actual pinout
     * Example:
     * - ADC1_IN18: Battery voltage (through voltage divider)
     * - ADC3_INP18: Internal temperature sensor
     */
    extern ADC_HandleTypeDef hadc1;  /* For battery voltage */
    extern ADC_HandleTypeDef hadc3;  /* For internal temp sensor */

    hadc_vbat = &hadc1;
    hadc_temp = &hadc3;
#endif

    /* Read initial values */
    Protection_UpdateVoltage();
    Protection_UpdateTemperature();

    return HAL_OK;
}

/**
 * @brief Update protection system (call at 1kHz)
 * @retval None
 */
void PMU_Protection_Update(void)
{
    /* Update uptime counter (1kHz -> seconds) */
    uptime_counter++;
    if (uptime_counter >= UPTIME_UPDATE_RATE_HZ) {
        uptime_counter = 0;
        protection_state.uptime_seconds++;
    }

    /* Update monitoring systems */
    Protection_UpdateVoltage();
    Protection_UpdateTemperature();
    Protection_UpdatePower();

    /* Check for faults */
    Protection_CheckFaults();

    /* Handle load shedding if active */
    if (protection_state.load_shedding_active) {
        Protection_HandleLoadShedding();
    }

    /* Auto-recovery timer */
    if (fault_recovery_timer > 0) {
        fault_recovery_timer--;
    }
}

/**
 * @brief Update voltage monitoring
 */
static void Protection_UpdateVoltage(void)
{
    /* Read battery voltage from ADC */
    protection_state.voltage.voltage_mV = Protection_ReadVbatADC();

    /* Check for undervoltage */
    if (protection_state.voltage.voltage_mV < protection_state.voltage.voltage_min_mV) {
        protection_state.voltage.undervoltage_count++;
    } else {
        protection_state.voltage.undervoltage_count = 0;
    }

    /* Check for overvoltage */
    if (protection_state.voltage.voltage_mV > protection_state.voltage.voltage_max_mV) {
        protection_state.voltage.overvoltage_count++;
    } else {
        protection_state.voltage.overvoltage_count = 0;
    }
}

/**
 * @brief Update temperature monitoring
 */
static void Protection_UpdateTemperature(void)
{
    /* Read MCU internal temperature sensor */
    protection_state.temperature.mcu_temp_C = Protection_ReadMCUTemp();

    /* Read board temperature sensors (Left and Right) */
    protection_state.temperature.board_temp_L_C = Protection_ReadBoardTempL();
    protection_state.temperature.board_temp_R_C = Protection_ReadBoardTempR();

    /* Update voltage outputs monitoring */
    protection_state.output_5v_mV = Protection_Read5VOutput();
    protection_state.output_3v3_mV = Protection_Read3V3Output();

    /* Check for overtemperature using max of all sensors */
    int16_t max_temp = Protection_GetMaxTemp();

    if (max_temp >= protection_state.temperature.temp_critical_C) {
        protection_state.temperature.overtemp_count++;
    } else {
        protection_state.temperature.overtemp_count = 0;
    }
}

/**
 * @brief Update power monitoring
 */
static void Protection_UpdatePower(void)
{
    uint32_t total_current = 0;

    /* Sum current from all PROFET channels - optimized with direct access */
    for (uint8_t i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        if (ch != NULL) {
            total_current += ch->current_mA;
            /* Early exit if over limit to save CPU cycles */
            if (total_current > protection_state.power.max_current_mA) {
                break;
            }
        }
    }

    /* TODO: Add H-bridge current when implemented */

    protection_state.power.total_current_mA = total_current;

    /* Calculate total power: P = V × I (mV × mA / 1000000 = W) */
    protection_state.power.total_power_W =
        ((uint64_t)protection_state.voltage.voltage_mV * total_current) / 1000000;
}

/**
 * @brief Check for faults and update status
 */
static void Protection_CheckFaults(void)
{
    uint16_t new_faults = PMU_PROT_FAULT_NONE;

    /* Check voltage faults */
    if (protection_state.voltage.undervoltage_count >= PMU_FAULT_THRESHOLD) {
        new_faults |= PMU_PROT_FAULT_UNDERVOLTAGE;
    }

    if (protection_state.voltage.overvoltage_count >= PMU_FAULT_THRESHOLD) {
        new_faults |= PMU_PROT_FAULT_OVERVOLTAGE;
    }

    /* Check voltage warnings */
    if (protection_state.voltage.voltage_mV < protection_state.voltage.voltage_warn_low_mV) {
        new_faults |= PMU_PROT_FAULT_BROWNOUT;
    }

    /* High voltage warning - could indicate alternator overvoltage */
    if (protection_state.voltage.voltage_mV > protection_state.voltage.voltage_warn_high_mV) {
        new_faults |= PMU_PROT_FAULT_BROWNOUT;  /* Reuse brownout flag for high voltage */
    }

    /* Get max temperature once for efficiency */
    int16_t max_temp = Protection_GetMaxTemp();

    /* Check temperature faults */
    if (protection_state.temperature.overtemp_count >= PMU_FAULT_THRESHOLD) {
        new_faults |= PMU_PROT_FAULT_OVERTEMP_CRITICAL;
        /* Enable load shedding to reduce heat */
        protection_state.load_shedding_active = 1;
    }

    if (max_temp >= protection_state.temperature.temp_warn_C) {
        new_faults |= PMU_PROT_FAULT_OVERTEMP_WARNING;
    }

    /* Check power faults */
    if (protection_state.power.total_current_mA > protection_state.power.max_current_mA) {
        new_faults |= PMU_PROT_FAULT_OVERCURRENT_TOTAL;
        /* Enable load shedding to reduce current */
        protection_state.load_shedding_active = 1;
    }

    if (protection_state.power.total_power_W > protection_state.power.max_power_W) {
        new_faults |= PMU_PROT_FAULT_POWER_LIMIT;
    }

    /* Update fault flags */
    uint16_t old_faults = protection_state.fault_flags;
    protection_state.fault_flags = new_faults;

    /* Increment fault counter if new faults occurred */
    if (new_faults != PMU_PROT_FAULT_NONE && new_faults != old_faults) {
        protection_state.fault_count_total++;
    }

    /* Push system events for new faults */
    uint16_t newly_set = (new_faults & ~old_faults);
    if (newly_set & PMU_PROT_FAULT_UNDERVOLTAGE) {
        PMU_Handler_PushSystemEvent(PMU_EVENT_SYSTEM_UNDERVOLT);
    }
    if (newly_set & PMU_PROT_FAULT_OVERVOLTAGE) {
        PMU_Handler_PushSystemEvent(PMU_EVENT_SYSTEM_OVERVOLT);
    }
    if (newly_set & PMU_PROT_FAULT_OVERTEMP_CRITICAL) {
        PMU_Handler_PushSystemEvent(PMU_EVENT_SYSTEM_OVERTEMP);
    }

    /* Update status based on faults */
    if (new_faults & (PMU_PROT_FAULT_UNDERVOLTAGE |
                      PMU_PROT_FAULT_OVERVOLTAGE |
                      PMU_PROT_FAULT_OVERTEMP_CRITICAL)) {
        protection_state.status = PMU_PROT_STATUS_CRITICAL;
    } else if (new_faults & (PMU_PROT_FAULT_OVERTEMP_WARNING |
                             PMU_PROT_FAULT_OVERCURRENT_TOTAL |
                             PMU_PROT_FAULT_BROWNOUT)) {
        protection_state.status = PMU_PROT_STATUS_FAULT;
    } else if (new_faults != PMU_PROT_FAULT_NONE) {
        protection_state.status = PMU_PROT_STATUS_WARNING;
    } else {
        protection_state.status = PMU_PROT_STATUS_OK;
        /* Disable load shedding if all OK */
        if (fault_recovery_timer == 0) {
            protection_state.load_shedding_active = 0;
        }
    }
}

/**
 * @brief Handle load shedding - turn off low-priority outputs
 */
static void Protection_HandleLoadShedding(void)
{
    /* TODO: Implement intelligent load shedding based on channel priority */
    /* For now, just a placeholder */

    /* Strategy:
     * 1. Keep critical channels (fuel pump, ECU power, ignition)
     * 2. Turn off comfort features (heated seats, aux lights)
     * 3. Reduce PWM duty on non-critical channels
     * 4. Monitor if fault condition improves
     */
}

/**
 * @brief Read battery voltage from ADC
 * @retval Voltage in mV
 */
static uint16_t Protection_ReadVbatADC(void)
{
#ifdef UNIT_TEST
    /* For unit tests, return nominal voltage */
    return PMU_VOLTAGE_NOMINAL;
#else
    if (hadc_vbat == NULL) {
        return PMU_VOLTAGE_NOMINAL;
    }

    /* With DMA in continuous mode, the ADC value is automatically updated
     * Use polling read for single-shot measurements or read from DMA buffer
     */
    uint16_t adc_value = 0;

    /* Start conversion if not already running */
    HAL_ADC_Start(hadc_vbat);

    /* Wait for conversion to complete (should be quick with continuous mode) */
    if (HAL_ADC_PollForConversion(hadc_vbat, 10) == HAL_OK) {
        adc_value = HAL_ADC_GetValue(hadc_vbat);
    }

    /* Convert to voltage: Vbat = (ADC / 4096) × 3.3V × divider_ratio */
    uint32_t voltage_mV = ((uint32_t)adc_value * ADC_VREF_MV * VOLTAGE_DIVIDER_RATIO) /
                          (ADC_RESOLUTION * VOLTAGE_DIVIDER_DIV);

    return (uint16_t)voltage_mV;
#endif
}

/**
 * @brief Read MCU internal temperature
 * @retval Temperature in °C
 */
static int16_t Protection_ReadMCUTemp(void)
{
#ifdef UNIT_TEST
    /* For unit tests, return nominal temperature */
    return 25;
#else
    if (hadc_temp == NULL) {
        return 25;
    }

    /* Read ADC value from internal temp sensor (ADC3_INP18 on STM32H7)
     * The internal temperature sensor must be enabled in ADC configuration
     */
    uint16_t adc_value = 0;

    /* Start conversion if not already running */
    HAL_ADC_Start(hadc_temp);

    /* Wait for conversion */
    if (HAL_ADC_PollForConversion(hadc_temp, 10) == HAL_OK) {
        adc_value = HAL_ADC_GetValue(hadc_temp);
    }

    /* Convert to voltage (µV) */
    uint32_t voltage_uV = ((uint32_t)adc_value * ADC_VREF_MV * 1000) / ADC_RESOLUTION;

    /* Calculate temperature using STM32H7 formula:
     * Temp(°C) = (V25 - Vsense) / Avg_Slope + 25
     * where:
     * - V25 = 760 mV typical voltage at 25°C
     * - Avg_Slope = 2.5 mV/°C
     */
    int32_t temp_C = ((int32_t)TEMP_SENSOR_V25 - (int32_t)voltage_uV) /
                     TEMP_SENSOR_AVG_SLOPE + 25;

    return (int16_t)temp_C;
#endif
}

/**
 * @brief Read board temperature sensor Left
 * @retval Temperature in °C
 * @note Weak function - can be overridden by emulator
 */
__attribute__((weak))
int16_t Protection_ReadBoardTempL(void)
{
#ifdef UNIT_TEST
    /* For unit tests, return nominal temperature */
    return 25;
#else
    /* External board temperature sensor Left - primary sensor
     * TODO: Implement actual sensor reading
     */
    return 25;  /* Nominal 25°C until sensor is configured */
#endif
}

/**
 * @brief Read board temperature sensor Right
 * @retval Temperature in °C
 * @note Weak function - can be overridden by emulator
 */
__attribute__((weak))
int16_t Protection_ReadBoardTempR(void)
{
#ifdef UNIT_TEST
    /* For unit tests, return nominal temperature */
    return 25;
#else
    /* External board temperature sensor Right - secondary sensor
     * TODO: Implement actual sensor reading
     */
    return 25;  /* Nominal 25°C until sensor is configured */
#endif
}

/**
 * @brief Read 5V output voltage
 * @retval Voltage in mV
 */
static uint16_t Protection_Read5VOutput(void)
{
#ifdef UNIT_TEST
    return 5000;  /* Nominal 5V */
#else
    /* TODO: Read from ADC channel monitoring 5V rail */
    return 5000;  /* Nominal until sensor is configured */
#endif
}

/**
 * @brief Read 3.3V output voltage
 * @retval Voltage in mV
 */
static uint16_t Protection_Read3V3Output(void)
{
#ifdef UNIT_TEST
    return 3300;  /* Nominal 3.3V */
#else
    /* TODO: Read from ADC channel monitoring 3.3V rail */
    return 3300;  /* Nominal until sensor is configured */
#endif
}

/**
 * @brief Get maximum temperature from all sensors
 * @retval Maximum temperature in °C
 */
static inline int16_t Protection_GetMaxTemp(void)
{
    int16_t max_temp = protection_state.temperature.mcu_temp_C;

    if (protection_state.temperature.board_temp_L_C > max_temp) {
        max_temp = protection_state.temperature.board_temp_L_C;
    }
    if (protection_state.temperature.board_temp_R_C > max_temp) {
        max_temp = protection_state.temperature.board_temp_R_C;
    }

    return max_temp;
}

/**
 * @brief Get protection system state
 * @retval Pointer to protection state
 */
PMU_Protection_State_t* PMU_Protection_GetState(void)
{
    return &protection_state;
}

/**
 * @brief Check if system is in fault state
 * @retval 1 if fault, 0 if OK
 */
uint8_t PMU_Protection_IsFaulted(void)
{
    return (protection_state.status >= PMU_PROT_STATUS_FAULT) ? 1 : 0;
}

/**
 * @brief Clear all recoverable faults
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protection_ClearFaults(void)
{
    /* Only clear if not in critical state */
    if (protection_state.status == PMU_PROT_STATUS_CRITICAL) {
        return HAL_ERROR;
    }

    /* Clear fault flags and counters */
    protection_state.fault_flags = PMU_PROT_FAULT_NONE;
    protection_state.voltage.undervoltage_count = 0;
    protection_state.voltage.overvoltage_count = 0;
    protection_state.temperature.overtemp_count = 0;
    protection_state.status = PMU_PROT_STATUS_OK;

    /* Set recovery delay before disabling load shedding */
    fault_recovery_timer = PMU_FAULT_RECOVERY_DELAY_MS;

    return HAL_OK;
}

/**
 * @brief Enable/disable load shedding
 * @param enable 1 to enable, 0 to disable
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protection_SetLoadShedding(uint8_t enable)
{
    protection_state.load_shedding_active = enable ? 1 : 0;
    return HAL_OK;
}

/**
 * @brief Get battery voltage in mV
 * @retval Voltage in millivolts
 */
uint16_t PMU_Protection_GetVoltage(void)
{
    return protection_state.voltage.voltage_mV;
}

/**
 * @brief Get board temperature in °C (returns max of L/R for backward compat)
 * @retval Temperature in degrees Celsius
 */
int16_t PMU_Protection_GetTemperature(void)
{
    /* Return max of L/R for backward compatibility */
    return (protection_state.temperature.board_temp_L_C >
            protection_state.temperature.board_temp_R_C) ?
            protection_state.temperature.board_temp_L_C :
            protection_state.temperature.board_temp_R_C;
}

/**
 * @brief Get total system current in mA
 * @retval Current in milliamperes
 */
uint32_t PMU_Protection_GetTotalCurrent(void)
{
    return protection_state.power.total_current_mA;
}

/**
 * @brief Get board temperature Left (primary sensor)
 * @retval Temperature in degrees Celsius
 */
int16_t PMU_Protection_GetBoardTempL(void)
{
    return protection_state.temperature.board_temp_L_C;
}

/**
 * @brief Get board temperature Right (secondary sensor)
 * @retval Temperature in degrees Celsius
 */
int16_t PMU_Protection_GetBoardTempR(void)
{
    return protection_state.temperature.board_temp_R_C;
}

/**
 * @brief Get system status bits (ECUMaster compatible)
 * @retval Status bits
 */
uint16_t PMU_Protection_GetStatus(void)
{
    return protection_state.system_status;
}

/**
 * @brief Get user error flag
 * @retval 1 if user error, 0 otherwise
 */
uint8_t PMU_Protection_GetUserError(void)
{
    return protection_state.user_error;
}

/**
 * @brief Get 5V output voltage
 * @retval Voltage in millivolts
 */
uint16_t PMU_Protection_Get5VOutput(void)
{
    return protection_state.output_5v_mV;
}

/**
 * @brief Get 3.3V output voltage
 * @retval Voltage in millivolts
 */
uint16_t PMU_Protection_Get3V3Output(void)
{
    return protection_state.output_3v3_mV;
}

/**
 * @brief Check if system is in shutdown sequence
 * @retval 1 if turning off, 0 otherwise
 */
uint8_t PMU_Protection_IsTurningOff(void)
{
    return protection_state.is_turning_off;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

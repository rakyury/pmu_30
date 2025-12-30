/**
 ******************************************************************************
 * @file           : emu_stubs.c
 * @brief          : Stub implementations for firmware dependencies
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This file provides stub implementations for firmware functions that
 * are not fully implemented in the emulator. These are weak symbols
 * that can be overridden by actual implementations.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "stm32_hal_emu.h"
#include "pmu_emulator.h"
#include <stdint.h>
#include <string.h>

/* DMA Buffers ---------------------------------------------------------------*/

/* ADC DMA buffers for PROFET current sensing (30 channels) */
uint16_t profet_current_adc_buffer[30] = {0};

/* ADC DMA buffers for PROFET status sensing (30 channels) */
uint16_t profet_status_adc_buffer[30] = {0};

/* ADC DMA buffers for H-bridge current sensing (4 channels) */
uint16_t hbridge_current_adc_buffer[4] = {0};

/* ADC DMA buffers for H-bridge position sensing (4 channels) */
uint16_t hbridge_position_adc_buffer[4] = {0};

/* HAL Handles ---------------------------------------------------------------*/

SPI_HandleTypeDef hspi1 = {0};
UART_HandleTypeDef huart1 = {0};
TIM_HandleTypeDef htim1 = {0};
TIM_HandleTypeDef htim2 = {0};
TIM_HandleTypeDef htim3 = {0};
TIM_HandleTypeDef htim4 = {0};
TIM_HandleTypeDef htim5 = {0};
TIM_HandleTypeDef htim8 = {0};
TIM_HandleTypeDef htim15 = {0};
ADC_HandleTypeDef hadc1 = {0};
ADC_HandleTypeDef hadc2 = {0};
ADC_HandleTypeDef hadc3 = {0};

/* HAL Helper Functions -----------------------------------------------------*/

/**
 * @brief Get device unique ID word 0 (emulator version)
 */
uint32_t HAL_GetUIDw0(void)
{
    return 0x12345678;  /* Emulator UID */
}

/* Weak Firmware Function Stubs ----------------------------------------------*/

/**
 * These are stub implementations of firmware functions.
 * They can be overridden by linking the actual firmware sources.
 *
 * Note: The following functions are now linked from actual firmware sources:
 * - PMU_Channel_Update() - from pmu_channel.c
 * - PMU_Logic_Execute() - from pmu_logic.c
 * - PMU_CAN_Update() - from pmu_can.c
 *
 * The emulator calls these functions directly in PMU_Emu_Tick().
 */

/* PMU_ADC_Update() - using real implementation from pmu_adc.c
 * The emulator updates adc_dma_buffer in Emu_UpdateADC(),
 * then PMU_ADC_Update() processes the values and updates digital_state. */

/* PMU_PROFET_Update() - using real implementation from pmu_profet.c
 * The stub SPI functions (PMU_SPI_GetCurrent, etc.) return emulator state,
 * so the real PROFET update will read simulated current correctly. */

__attribute__((weak))
void PMU_HBridge_Update(void)
{
    /* Stub - H-Bridge update is handled by emulator */
}

/* PMU_Protection_Update() - using real implementation from pmu_protection.c
 * The emulator provides voltage/temperature values via HAL_ADC_GetValue(),
 * so the real protection module will read simulated values correctly. */

__attribute__((weak))
void PMU_UI_Update(void)
{
    /* Stub - UI not available in emulator */
}

/* SPI Stubs (for PROFET diagnostics) ----------------------------------------*/

/* SPI device type for stub functions */
typedef enum {
    PMU_SPI_DEVICE_CURRENT_ADC = 0,
    PMU_SPI_DEVICE_STATUS_ADC
} PMU_SPI_Device_t;

/* Diagnostic data structure stub */
typedef struct {
    uint16_t current_raw[30];
    uint16_t status_raw[30];
} PMU_SPI_DiagData_t;

static PMU_SPI_DiagData_t spi_diag_data = {0};

HAL_StatusTypeDef PMU_SPI_Init(void)
{
    return HAL_OK;
}

HAL_StatusTypeDef PMU_SPI_DeInit(void)
{
    return HAL_OK;
}

HAL_StatusTypeDef PMU_SPI_Update(void)
{
    return HAL_OK;
}

PMU_SPI_DiagData_t* PMU_SPI_GetDiagData(void)
{
    return &spi_diag_data;
}

HAL_StatusTypeDef PMU_SPI_CalibrateOffset(PMU_SPI_Device_t device)
{
    (void)device;
    return HAL_OK;
}

uint32_t PMU_SPI_GetCurrent(uint8_t channel)
{
    PMU_Emulator_t* emu = PMU_Emu_GetState();
    if (channel < 30 && emu) {
        return emu->profet[channel].current_mA;
    }
    return 0;
}

int16_t PMU_SPI_GetTemperature(uint8_t channel)
{
    PMU_Emulator_t* emu = PMU_Emu_GetState();
    if (channel < 30 && emu) {
        return emu->profet[channel].temperature_C;
    }
    return 25;
}

uint16_t PMU_SPI_GetRawValue(uint8_t channel, uint8_t type)
{
    PMU_Emulator_t* emu = PMU_Emu_GetState();
    if (channel >= 30 || !emu) {
        return 0;
    }
    if (type == 0) {
        /* Current - convert mA to raw ADC (12-bit, 0-20A range) */
        return (uint16_t)((emu->profet[channel].current_mA * 4095) / 20000);
    } else {
        /* Status - return fault flags */
        return emu->profet[channel].fault_flags;
    }
}

uint8_t PMU_SPI_GetFaultFlags(uint8_t channel)
{
    PMU_Emulator_t* emu = PMU_Emu_GetState();
    if (channel < 30 && emu) {
        return emu->profet[channel].fault_flags;
    }
    return 0;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

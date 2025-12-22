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

/* Weak Firmware Function Stubs ----------------------------------------------*/

/**
 * These are stub implementations of firmware functions.
 * They can be overridden by linking the actual firmware sources.
 */

__attribute__((weak))
void PMU_ADC_Update(void)
{
    /* Stub - no operation */
}

__attribute__((weak))
void PMU_CAN_Update(void)
{
    /* Stub - no operation */
}

__attribute__((weak))
void PMU_PROFET_Update(void)
{
    /* Stub - no operation */
}

__attribute__((weak))
void PMU_HBridge_Update(void)
{
    /* Stub - no operation */
}

__attribute__((weak))
void PMU_Protection_Update(void)
{
    /* Stub - no operation */
}

__attribute__((weak))
void PMU_Channel_Update(void)
{
    /* Stub - no operation */
}

__attribute__((weak))
void PMU_Logic_Update(void)
{
    /* Stub - no operation */
}

__attribute__((weak))
void PMU_UI_Update(void)
{
    /* Stub - no operation */
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

/**
 ******************************************************************************
 * @file           : hal_stubs.c
 * @brief          : HAL Peripheral Stubs (temporary until CubeMX generation)
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * This file provides stub definitions for HAL peripheral handles.
 * These will be replaced by actual CubeMX-generated code when the
 * hardware configuration is finalized.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"

/* SPI Handles ---------------------------------------------------------------*/
SPI_HandleTypeDef hspi1;

/* UART Handles --------------------------------------------------------------*/
UART_HandleTypeDef huart1;

/* Timer Handles -------------------------------------------------------------*/
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;
TIM_HandleTypeDef htim4;
TIM_HandleTypeDef htim5;
TIM_HandleTypeDef htim8;
TIM_HandleTypeDef htim15;

/* ADC Handles ---------------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
ADC_HandleTypeDef hadc3;

/* DMA Buffers ---------------------------------------------------------------*/
/* ADC DMA buffers for PROFET current sensing (30 channels) */
__attribute__((aligned(4))) uint16_t profet_current_adc_buffer[30];

/* ADC DMA buffers for PROFET status sensing (30 channels) */
__attribute__((aligned(4))) uint16_t profet_status_adc_buffer[30];

/* ADC DMA buffers for H-bridge current sensing (4 channels) */
__attribute__((aligned(4))) uint16_t hbridge_current_adc_buffer[4];

/* ADC DMA buffers for H-bridge position sensing (4 channels) */
__attribute__((aligned(4))) uint16_t hbridge_position_adc_buffer[4];

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

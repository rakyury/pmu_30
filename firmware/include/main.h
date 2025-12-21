/**
 ******************************************************************************
 * @file           : main.h
 * @brief          : Header for main.c file.
 *                   This file contains the common defines of the application.
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

#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/* Exported types ------------------------------------------------------------*/

/* Exported constants --------------------------------------------------------*/

/* PMU-30 Hardware Configuration */
#define PMU30_NUM_OUTPUTS           30      /* Number of PROFET 2 outputs */
#define PMU30_NUM_HBRIDGES          4       /* Number of dual H-bridges */
#define PMU30_NUM_ADC_INPUTS        20      /* Number of analog inputs */
#define PMU30_NUM_DAC_OUTPUTS       10      /* Number of DAC outputs */
#define PMU30_NUM_CAN_BUSES         4       /* 2x CAN FD + 2x CAN 2.0 */
#define PMU30_NUM_LEDS              30      /* Bicolor LEDs per channel */

/* System Clock */
#define SYSCLK_FREQ                 480000000UL  /* 480 MHz */
#define HCLK_FREQ                   240000000UL  /* 240 MHz */
#define APB1_FREQ                   120000000UL  /* 120 MHz */
#define APB2_FREQ                   120000000UL  /* 120 MHz */

/* Timing Configuration */
#define CONTROL_LOOP_FREQ_HZ        1000    /* 1 kHz control loop */
#define LOGIC_LOOP_FREQ_HZ          500     /* 500 Hz logic update */
#define LOGGING_FREQ_HZ             500     /* 500 Hz data logging */
#define LED_UPDATE_FREQ_HZ          20      /* 20 Hz LED update */

/* Memory Configuration */
#define EXTERNAL_FLASH_SIZE         (512 * 1024 * 1024)  /* 512 MB */
#define LUA_RAM_SIZE                (256 * 1024)          /* 256 KB for Lua */
#define LUA_FLASH_SIZE              (128 * 1024)          /* 128 KB for scripts */

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

/**
 ******************************************************************************
 * @file           : board_config.h
 * @brief          : Board-specific configuration for PMU-30 firmware
 * @author         : R2 m-sport
 * @date           : 2025-12-27
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This header provides board-specific configuration for different targets:
 *   - PMU-30 Rev A (STM32H743VIT6) - Full featured production board
 *   - Nucleo-H743ZI (STM32H743ZI) - Development board for H7 testing
 *   - Nucleo-F446RE (STM32F446RE) - Development board for logic/CAN testing
 *
 ******************************************************************************
 */

#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Nucleo-F446RE Configuration
 * ============================================================================ */
#ifdef NUCLEO_F446RE

/* Board identification */
#define BOARD_NAME              "Nucleo-F446RE"
#define BOARD_MCU               "STM32F446RE"
#define BOARD_CLOCK_MHZ         180

/* Channel configuration (limited by available peripherals) */
#define PMU_CHANNELS            6
#define PMU_ADC_CHANNELS        5
#define PMU_PWM_CHANNELS        6

/* Hardware features */
#define HAS_HIGHSIDE_DRIVERS    0       /* No PROFET hardware */
#define HAS_CURRENT_SENSE       0       /* No current sensing */
#define HAS_HBRIDGE             0       /* No H-Bridge */
#define HAS_CAN_FD              0       /* CAN 2.0 only (not FD) */
#define HAS_EXTERNAL_FLASH      0       /* No SPI flash */
#define HAS_WIFI                0       /* No WiFi module */
#define HAS_BLUETOOTH           0       /* No Bluetooth */

/* Debug configuration */
#define DEBUG_ENABLED           1
#define DEBUG_UART              huart2  /* ST-LINK VCP */
#define DEBUG_BAUDRATE          115200

/* Pin mapping - User LED and Button */
#define USER_LED_PIN            GPIO_PIN_5
#define USER_LED_PORT           GPIOA
#define USER_BTN_PIN            GPIO_PIN_13
#define USER_BTN_PORT           GPIOC

/* Pin mapping - CAN1 */
#define CAN1_RX_PIN             GPIO_PIN_11
#define CAN1_RX_PORT            GPIOA
#define CAN1_TX_PIN             GPIO_PIN_12
#define CAN1_TX_PORT            GPIOA
#define CAN1_AF                 GPIO_AF9_CAN1

/* Pin mapping - Debug UART (USART2) */
#define DEBUG_UART_TX_PIN       GPIO_PIN_2
#define DEBUG_UART_TX_PORT      GPIOA
#define DEBUG_UART_RX_PIN       GPIO_PIN_3
#define DEBUG_UART_RX_PORT      GPIOA
#define DEBUG_UART_AF           GPIO_AF7_USART2

/* Pin mapping - ADC inputs (Arduino connectors) */
#define ADC_CH0_PIN             GPIO_PIN_0      /* A0 - PA0 */
#define ADC_CH0_PORT            GPIOA
#define ADC_CH0_CHANNEL         ADC_CHANNEL_0
#define ADC_CH1_PIN             GPIO_PIN_1      /* A1 - PA1 */
#define ADC_CH1_PORT            GPIOA
#define ADC_CH1_CHANNEL         ADC_CHANNEL_1
#define ADC_CH2_PIN             GPIO_PIN_4      /* A2 - PA4 */
#define ADC_CH2_PORT            GPIOA
#define ADC_CH2_CHANNEL         ADC_CHANNEL_4
#define ADC_CH3_PIN             GPIO_PIN_0      /* A3 - PB0 */
#define ADC_CH3_PORT            GPIOB
#define ADC_CH3_CHANNEL         ADC_CHANNEL_8
#define ADC_CH4_PIN             GPIO_PIN_1      /* A4 - PC1 */
#define ADC_CH4_PORT            GPIOC
#define ADC_CH4_CHANNEL         ADC_CHANNEL_11

/* Pin mapping - Digital inputs (directly usable pins) */
#define PMU_DIGITAL_INPUTS      8
#define DIN_CH0_PIN             GPIO_PIN_13     /* PC13 - User Button */
#define DIN_CH0_PORT            GPIOC
#define DIN_CH1_PIN             GPIO_PIN_10     /* PC10 - D2 */
#define DIN_CH1_PORT            GPIOC
#define DIN_CH2_PIN             GPIO_PIN_12     /* PC12 - D3 (directly near Morpho) */
#define DIN_CH2_PORT            GPIOC
#define DIN_CH3_PIN             GPIO_PIN_2      /* PB2 - D4 (Arduino D4) */
#define DIN_CH3_PORT            GPIOB
#define DIN_CH4_PIN             GPIO_PIN_15     /* PB15 - D5 */
#define DIN_CH4_PORT            GPIOB
#define DIN_CH5_PIN             GPIO_PIN_14     /* PB14 - D6 */
#define DIN_CH5_PORT            GPIOB
#define DIN_CH6_PIN             GPIO_PIN_13     /* PB13 - D7 */
#define DIN_CH6_PORT            GPIOB
#define DIN_CH7_PIN             GPIO_PIN_12     /* PB12 - D8 */
#define DIN_CH7_PORT            GPIOB

/* Pin mapping - PWM outputs (simulated power channels) */
#define PWM_CH0_PIN             GPIO_PIN_8      /* TIM1_CH1 - PA8 */
#define PWM_CH0_PORT            GPIOA
#define PWM_CH0_TIM             htim1
#define PWM_CH0_CHANNEL         TIM_CHANNEL_1
#define PWM_CH1_PIN             GPIO_PIN_9      /* TIM1_CH2 - PA9 */
#define PWM_CH1_PORT            GPIOA
#define PWM_CH1_TIM             htim1
#define PWM_CH1_CHANNEL         TIM_CHANNEL_2
#define PWM_CH2_PIN             GPIO_PIN_0      /* TIM2_CH1 - PA0 (shared with ADC) */
#define PWM_CH2_PORT            GPIOA
#define PWM_CH2_TIM             htim2
#define PWM_CH2_CHANNEL         TIM_CHANNEL_1
#define PWM_CH3_PIN             GPIO_PIN_1      /* TIM2_CH2 - PA1 (shared with ADC) */
#define PWM_CH3_PORT            GPIOA
#define PWM_CH3_TIM             htim2
#define PWM_CH3_CHANNEL         TIM_CHANNEL_2
#define PWM_CH4_PIN             GPIO_PIN_6      /* TIM3_CH1 - PB4 */
#define PWM_CH4_PORT            GPIOB
#define PWM_CH4_TIM             htim3
#define PWM_CH4_CHANNEL         TIM_CHANNEL_1
#define PWM_CH5_PIN             GPIO_PIN_7      /* TIM3_CH2 - PB5 */
#define PWM_CH5_PORT            GPIOB
#define PWM_CH5_TIM             htim3
#define PWM_CH5_CHANNEL         TIM_CHANNEL_2

/* HAL include for F4 series */
#include "stm32f4xx_hal.h"

/* ============================================================================
 * Nucleo-H743ZI Configuration
 * ============================================================================ */
#elif defined(PMU_NUCLEO_BOARD) && !defined(NUCLEO_F446RE)

/* Board identification */
#define BOARD_NAME              "Nucleo-H743ZI"
#define BOARD_MCU               "STM32H743ZI"
#define BOARD_CLOCK_MHZ         480

/* Channel configuration */
#define PMU_CHANNELS            30
#define PMU_ADC_CHANNELS        20
#define PMU_PWM_CHANNELS        30

/* Hardware features (stubbed) */
#define HAS_HIGHSIDE_DRIVERS    0
#define HAS_CURRENT_SENSE       0
#define HAS_HBRIDGE             0
#define HAS_CAN_FD              1       /* FDCAN available */
#define HAS_EXTERNAL_FLASH      0
#define HAS_WIFI                0
#define HAS_BLUETOOTH           0

/* Debug configuration */
#define DEBUG_ENABLED           1
#define DEBUG_UART              huart3  /* ST-LINK VCP on PD8/PD9 */
#define DEBUG_BAUDRATE          115200

/* Pin mapping - User LEDs */
#define LED_GREEN_PIN           GPIO_PIN_0
#define LED_GREEN_PORT          GPIOB
#define LED_YELLOW_PIN          GPIO_PIN_1
#define LED_YELLOW_PORT         GPIOE
#define LED_RED_PIN             GPIO_PIN_14
#define LED_RED_PORT            GPIOB

/* User button */
#define USER_BTN_PIN            GPIO_PIN_13
#define USER_BTN_PORT           GPIOC

/* HAL include for H7 series */
#include "stm32h7xx_hal.h"

/* ============================================================================
 * PMU-30 Production Board Configuration
 * ============================================================================ */
#else

/* Board identification */
#define BOARD_NAME              "PMU-30 Rev A"
#define BOARD_MCU               "STM32H743VIT6"
#define BOARD_CLOCK_MHZ         480

/* Channel configuration */
#ifndef PMU_CHANNELS
#define PMU_CHANNELS            30
#endif
#ifndef PMU_ADC_CHANNELS
#define PMU_ADC_CHANNELS        20
#endif
#ifndef PMU_PWM_CHANNELS
#define PMU_PWM_CHANNELS        30
#endif

/* Hardware features */
#define HAS_HIGHSIDE_DRIVERS    1       /* PROFET 2 drivers */
#define HAS_CURRENT_SENSE       1       /* Current sensing per channel */
#define HAS_HBRIDGE             1       /* 4x H-Bridge */
#define HAS_CAN_FD              1       /* 2x CAN FD + 2x CAN 2.0 */
#define HAS_EXTERNAL_FLASH      1       /* W25Q512JV SPI Flash */
#define HAS_WIFI                1       /* ESP32-C3 module */
#define HAS_BLUETOOTH           1       /* ESP32-C3 module */

/* Debug configuration */
#define DEBUG_ENABLED           1
#define DEBUG_UART              huart1  /* Debug UART */
#define DEBUG_BAUDRATE          115200

/* HAL include for H7 series */
#include "stm32h7xx_hal.h"

#endif /* Board selection */

/* ============================================================================
 * Common Configuration
 * ============================================================================ */

/* Default values if not defined */
#ifndef PMU_MAX_OUTPUTS
#define PMU_MAX_OUTPUTS         PMU_CHANNELS
#endif

#ifndef PMU_MAX_INPUTS
#define PMU_MAX_INPUTS          PMU_ADC_CHANNELS
#endif

#ifndef PMU_MAX_HBRIDGES
#if HAS_HBRIDGE
#define PMU_MAX_HBRIDGES        4
#else
#define PMU_MAX_HBRIDGES        0
#endif
#endif

/* Number of outputs for array sizing */
#ifndef PMU30_NUM_OUTPUTS
#define PMU30_NUM_OUTPUTS       PMU_MAX_OUTPUTS
#endif

/* FreeRTOS task priorities */
#define TASK_PRIORITY_CONTROL   (configMAX_PRIORITIES - 1)
#define TASK_PRIORITY_PROTECT   (configMAX_PRIORITIES - 2)
#define TASK_PRIORITY_CAN       (configMAX_PRIORITIES - 3)
#define TASK_PRIORITY_UI        (tskIDLE_PRIORITY + 2)
#define TASK_PRIORITY_LOGGING   (tskIDLE_PRIORITY + 1)

/* Debug macros */
#if DEBUG_ENABLED
    #define DEBUG_PRINT(fmt, ...) do { \
        char _dbg_buf[256]; \
        snprintf(_dbg_buf, sizeof(_dbg_buf), fmt, ##__VA_ARGS__); \
        HAL_UART_Transmit(&DEBUG_UART, (uint8_t*)_dbg_buf, strlen(_dbg_buf), 100); \
    } while(0)
#else
    #define DEBUG_PRINT(fmt, ...) ((void)0)
#endif

#ifdef __cplusplus
}
#endif

#endif /* BOARD_CONFIG_H */

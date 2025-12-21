/**
 ******************************************************************************
 * @file           : stm32h7xx_hal.h
 * @brief          : HAL stub header for unit testing
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * This is a minimal stub for STM32 HAL to allow unit tests to compile
 */

#ifndef __STM32H7xx_HAL_H
#define __STM32H7xx_HAL_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>

/* HAL Status structures */
typedef enum {
    HAL_OK       = 0x00U,
    HAL_ERROR    = 0x01U,
    HAL_BUSY     = 0x02U,
    HAL_TIMEOUT  = 0x03U
} HAL_StatusTypeDef;

/* GPIO definitions */
typedef enum {
    GPIO_PIN_RESET = 0,
    GPIO_PIN_SET
} GPIO_PinState;

/* Handle typedefs (empty stubs) */
typedef struct { int dummy; } ADC_HandleTypeDef;
typedef struct { int dummy; } SPI_HandleTypeDef;
typedef struct { int dummy; } I2C_HandleTypeDef;
typedef struct { int dummy; } TIM_HandleTypeDef;
typedef struct { int dummy; } UART_HandleTypeDef;
typedef struct { int dummy; } IWDG_HandleTypeDef;

/* CAN FD Handle */
typedef struct {
    int Instance;
    int State;
} FDCAN_HandleTypeDef;

/* Stub functions */
static inline HAL_StatusTypeDef HAL_Init(void) { return HAL_OK; }
static inline uint32_t HAL_GetTick(void) { return 0; }
static inline void HAL_Delay(uint32_t Delay) { (void)Delay; }

#ifdef __cplusplus
}
#endif

#endif /* __STM32H7xx_HAL_H */

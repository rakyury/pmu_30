/**
 ******************************************************************************
 * @file           : pmu_hal.h
 * @brief          : HAL include wrapper for multi-platform support
 * @author         : R2 m-sport
 * @date           : 2025-12-30
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This header provides a single include point for HAL headers across
 * different STM32 platforms (H7, F4) and emulator builds.
 *
 ******************************************************************************
 */

#ifndef PMU_HAL_H
#define PMU_HAL_H

#ifdef __cplusplus
extern "C" {
#endif

/* Platform-specific HAL includes */
#if defined(NUCLEO_F446RE)
    /* STM32F446RE - Nucleo development board */
    #include "stm32f4xx_hal.h"
#elif defined(PMU_EMULATOR) || defined(UNIT_TEST)
    /* Emulator/test build - no real HAL */
    #include <stdint.h>
    #include <stdbool.h>
    /* Define HAL types for compatibility */
    typedef enum {
        HAL_OK       = 0x00U,
        HAL_ERROR    = 0x01U,
        HAL_BUSY     = 0x02U,
        HAL_TIMEOUT  = 0x03U
    } HAL_StatusTypeDef;
    #define HAL_MAX_DELAY      0xFFFFFFFFU
#else
    /* Default: STM32H7 (PMU-30 production hardware) */
    #include "stm32h7xx_hal.h"
#endif

#ifdef __cplusplus
}
#endif

#endif /* PMU_HAL_H */

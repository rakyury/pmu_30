/**
 ******************************************************************************
 * @file           : stm32h7xx_hal.h
 * @brief          : STM32H7 HAL Wrapper for Emulator
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This file acts as a drop-in replacement for the real STM32H7 HAL header
 * when building for the emulator. It includes the emulation layer instead
 * of the real HAL drivers.
 *
 ******************************************************************************
 */

#ifndef __STM32H7xx_HAL_H
#define __STM32H7xx_HAL_H

#ifdef __cplusplus
extern "C" {
#endif

/* When building for emulator, use emulation layer */
#if defined(PMU_EMULATOR) || defined(UNIT_TEST) || defined(NATIVE_BUILD)

#include "stm32_hal_emu.h"

#else

/* For real hardware, include the actual HAL */
#error "This header should only be used for emulator builds. Use the real HAL for hardware builds."

#endif /* PMU_EMULATOR */

#ifdef __cplusplus
}
#endif

#endif /* __STM32H7xx_HAL_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

/**
 ******************************************************************************
 * @file           : pmu_stubs.c
 * @brief          : Stub implementations for disabled hardware modules
 * @author         : R2 m-sport
 * @date           : 2025-12-27
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This file provides stub implementations for hardware modules that are
 * disabled via compile-time flags. Used for Nucleo board testing.
 *
 ******************************************************************************
 */

#include <stdint.h>
#include <stddef.h>
#include "stm32h7xx_hal.h"

/* ============================================================================
 * PROFET Stubs (when PMU_DISABLE_PROFET is defined)
 * ============================================================================ */

#ifdef PMU_DISABLE_PROFET

#include "pmu_profet.h"

/* Stub channel data */
static PMU_PROFET_Channel_t stub_channels[PMU30_NUM_OUTPUTS];

HAL_StatusTypeDef PMU_PROFET_Init(void)
{
    /* Initialize stub data */
    for (uint8_t i = 0; i < PMU30_NUM_OUTPUTS; i++) {
        stub_channels[i].state = PMU_PROFET_STATE_OFF;
        stub_channels[i].fault_flags = PMU_PROFET_FAULT_NONE;
        stub_channels[i].current_mA = 0;
        stub_channels[i].temperature_C = 25;
        stub_channels[i].pwm_duty = 0;
    }
    return HAL_OK;
}

void PMU_PROFET_Update(void)
{
    /* No hardware - nothing to do */
}

HAL_StatusTypeDef PMU_PROFET_SetState(uint8_t channel, uint8_t state)
{
    if (channel >= PMU30_NUM_OUTPUTS) return HAL_ERROR;
    stub_channels[channel].state = state ? PMU_PROFET_STATE_ON : PMU_PROFET_STATE_OFF;
    return HAL_OK;
}

HAL_StatusTypeDef PMU_PROFET_SetPWM(uint8_t channel, uint16_t duty)
{
    if (channel >= PMU30_NUM_OUTPUTS) return HAL_ERROR;
    stub_channels[channel].pwm_duty = duty;
    if (duty > 0) {
        stub_channels[channel].state = PMU_PROFET_STATE_PWM;
    }
    return HAL_OK;
}

PMU_PROFET_State_t PMU_PROFET_GetState(uint8_t channel)
{
    if (channel >= PMU30_NUM_OUTPUTS) return PMU_PROFET_STATE_OFF;
    return stub_channels[channel].state;
}

uint16_t PMU_PROFET_GetCurrent(uint8_t channel)
{
    if (channel >= PMU30_NUM_OUTPUTS) return 0;
    return stub_channels[channel].current_mA;
}

int16_t PMU_PROFET_GetTemperature(uint8_t channel)
{
    if (channel >= PMU30_NUM_OUTPUTS) return 25;
    return stub_channels[channel].temperature_C;
}

uint8_t PMU_PROFET_GetFaultFlags(uint8_t channel)
{
    if (channel >= PMU30_NUM_OUTPUTS) return 0;
    return stub_channels[channel].fault_flags;
}

PMU_PROFET_Channel_t* PMU_PROFET_GetChannelData(uint8_t channel)
{
    if (channel >= PMU30_NUM_OUTPUTS) return NULL;
    return &stub_channels[channel];
}

HAL_StatusTypeDef PMU_PROFET_ClearFault(uint8_t channel)
{
    if (channel >= PMU30_NUM_OUTPUTS) return HAL_ERROR;
    stub_channels[channel].fault_flags = PMU_PROFET_FAULT_NONE;
    return HAL_OK;
}

void PMU_PROFET_SetConfig(uint8_t channel, PMU_OutputConfig_t* config)
{
    (void)channel;
    (void)config;
}

#endif /* PMU_DISABLE_PROFET */

/* ============================================================================
 * H-Bridge Stubs (when PMU_DISABLE_HBRIDGE is defined)
 * ============================================================================ */

#ifdef PMU_DISABLE_HBRIDGE

#include "pmu_hbridge.h"

static PMU_HBridge_Channel_t stub_hbridges[4];

HAL_StatusTypeDef PMU_HBridge_Init(void)
{
    for (uint8_t i = 0; i < 4; i++) {
        stub_hbridges[i].state = PMU_HBRIDGE_STATE_OFF;
        stub_hbridges[i].position = 500;  /* Mid position */
        stub_hbridges[i].target_position = 500;
        stub_hbridges[i].duty_cycle = 0;
        stub_hbridges[i].fault_flags = 0;
    }
    return HAL_OK;
}

void PMU_HBridge_Update(void)
{
    /* No hardware - nothing to do */
}

HAL_StatusTypeDef PMU_HBridge_SetPosition(uint8_t bridge, uint16_t position)
{
    if (bridge >= 4) return HAL_ERROR;
    stub_hbridges[bridge].target_position = position;
    stub_hbridges[bridge].position = position;  /* Instant move in stub */
    return HAL_OK;
}

HAL_StatusTypeDef PMU_HBridge_SetDuty(uint8_t bridge, int16_t duty)
{
    if (bridge >= 4) return HAL_ERROR;
    stub_hbridges[bridge].duty_cycle = duty;
    return HAL_OK;
}

HAL_StatusTypeDef PMU_HBridge_Stop(uint8_t bridge)
{
    if (bridge >= 4) return HAL_ERROR;
    stub_hbridges[bridge].state = PMU_HBRIDGE_STATE_OFF;
    stub_hbridges[bridge].duty_cycle = 0;
    return HAL_OK;
}

PMU_HBridge_State_t PMU_HBridge_GetState(uint8_t bridge)
{
    if (bridge >= 4) return PMU_HBRIDGE_STATE_OFF;
    return stub_hbridges[bridge].state;
}

uint16_t PMU_HBridge_GetPosition(uint8_t bridge)
{
    if (bridge >= 4) return 500;
    return stub_hbridges[bridge].position;
}

uint16_t PMU_HBridge_GetCurrent(uint8_t bridge)
{
    (void)bridge;
    return 0;
}

PMU_HBridge_Channel_t* PMU_HBridge_GetChannelData(uint8_t bridge)
{
    if (bridge >= 4) return NULL;
    return &stub_hbridges[bridge];
}

#endif /* PMU_DISABLE_HBRIDGE */

/* ============================================================================
 * Flash Stubs (when PMU_DISABLE_SPI_FLASH is defined)
 * ============================================================================ */

#ifdef PMU_DISABLE_SPI_FLASH

#include "pmu_flash.h"

HAL_StatusTypeDef PMU_Flash_Init(void)
{
    return HAL_OK;
}

HAL_StatusTypeDef PMU_Flash_Read(uint32_t address, uint8_t* data, uint32_t size)
{
    (void)address;
    /* Return zeros */
    for (uint32_t i = 0; i < size; i++) {
        data[i] = 0xFF;
    }
    return HAL_OK;
}

HAL_StatusTypeDef PMU_Flash_Write(uint32_t address, const uint8_t* data, uint32_t size)
{
    (void)address;
    (void)data;
    (void)size;
    return HAL_OK;
}

HAL_StatusTypeDef PMU_Flash_Erase(uint32_t address, uint32_t size)
{
    (void)address;
    (void)size;
    return HAL_OK;
}

#endif /* PMU_DISABLE_SPI_FLASH */

/* ============================================================================
 * Bootloader Stubs (when PMU_DISABLE_BOOTLOADER is defined)
 * ============================================================================ */

#ifdef PMU_DISABLE_BOOTLOADER

#include "pmu_bootloader.h"

static PMU_Boot_SharedData_t stub_boot_data = {0};

PMU_Boot_SharedData_t* PMU_Bootloader_GetSharedData(void)
{
    return &stub_boot_data;
}

void PMU_Bootloader_JumpToApp(void)
{
    /* No-op in stub */
}

void PMU_Bootloader_JumpToBootloader(void)
{
    /* No-op in stub */
}

#endif /* PMU_DISABLE_BOOTLOADER */

/* ============================================================================
 * UI Stubs (when PMU_NUCLEO_BOARD is defined - Nucleo uses simple LED UI)
 * ============================================================================ */

#ifdef PMU_NUCLEO_BOARD

#include "pmu_ui.h"

HAL_StatusTypeDef PMU_UI_Init(void)
{
    /* Nucleo uses main_nucleo.c LED control instead */
    return HAL_OK;
}

void PMU_UI_Update(void)
{
    /* LED update handled in vUITask */
}

void PMU_UI_SetStatusLED(PMU_Status_LED_t status)
{
    (void)status;
}

HAL_StatusTypeDef PMU_UI_SetChannelLED(uint8_t channel, PMU_LED_Color_t color,
                                        PMU_LED_Pattern_t pattern)
{
    (void)channel;
    (void)color;
    (void)pattern;
    return HAL_OK;
}

void PMU_UI_SetAllChannelLEDs(PMU_LED_Color_t color, PMU_LED_Pattern_t pattern)
{
    (void)color;
    (void)pattern;
}

void PMU_UI_UpdateChannelStatus(void)
{
    /* No-op */
}

void PMU_UI_PlayBuzzer(PMU_Buzzer_Pattern_t pattern)
{
    (void)pattern;
}

void PMU_UI_StopBuzzer(void)
{
    /* No-op */
}

PMU_Button_State_t PMU_UI_GetButtonState(uint8_t button)
{
    (void)button;
    return PMU_BUTTON_RELEASED;
}

uint8_t PMU_UI_ButtonPressed(uint8_t button)
{
    (void)button;
    return 0;
}

uint8_t PMU_UI_ButtonReleased(uint8_t button)
{
    (void)button;
    return 0;
}

void PMU_UI_StartupAnimation(void)
{
    /* No-op */
}

#endif /* PMU_NUCLEO_BOARD */

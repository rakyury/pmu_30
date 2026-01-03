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
#include "board_config.h"

/* Nucleo-F446RE hardware output control */
#ifdef NUCLEO_F446RE
extern void NucleoOutput_SetState(uint8_t channel, uint8_t state);
extern void NucleoOutput_SetPWM(uint8_t channel, uint16_t duty);
#endif

/* ============================================================================
 * PROFET Stubs (when PMU_DISABLE_PROFET is defined)
 * ============================================================================ */

#ifdef PMU_DISABLE_PROFET

#include "pmu_profet.h"

/* Stub channel data */
static PMU_PROFET_Channel_t stub_channels[PMU30_NUM_OUTPUTS] = {0};

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
#ifdef NUCLEO_F446RE
    NucleoOutput_SetState(channel, state);
#endif
    return HAL_OK;
}

HAL_StatusTypeDef PMU_PROFET_SetPWM(uint8_t channel, uint16_t duty)
{
    if (channel >= PMU30_NUM_OUTPUTS) return HAL_ERROR;
    stub_channels[channel].pwm_duty = duty;
    if (duty > 0) {
        stub_channels[channel].state = PMU_PROFET_STATE_PWM;
    }
#ifdef NUCLEO_F446RE
    NucleoOutput_SetPWM(channel, duty);
#endif
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

uint8_t PMU_PROFET_HasManualOverride(uint8_t channel)
{
    (void)channel;
    return 0;  /* No manual override in stub */
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
        stub_hbridges[i].state = PMU_HBRIDGE_STATE_IDLE;
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
    stub_hbridges[bridge].state = PMU_HBRIDGE_STATE_IDLE;
    stub_hbridges[bridge].duty_cycle = 0;
    return HAL_OK;
}

PMU_HBridge_State_t PMU_HBridge_GetState(uint8_t bridge)
{
    if (bridge >= 4) return PMU_HBRIDGE_STATE_IDLE;
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

HAL_StatusTypeDef PMU_HBridge_SetMode(uint8_t bridge, PMU_HBridge_Mode_t mode, uint16_t duty)
{
    if (bridge >= 4) return HAL_ERROR;
    stub_hbridges[bridge].mode = mode;
    stub_hbridges[bridge].duty_cycle = duty;
    return HAL_OK;
}

#endif /* PMU_DISABLE_HBRIDGE */

/* ============================================================================
 * Flash Stubs (when PMU_DISABLE_SPI_FLASH is defined)
 * ============================================================================ */

#ifdef PMU_DISABLE_SPI_FLASH

#include "pmu_flash.h"

PMU_Flash_Status_t PMU_Flash_Init(void)
{
    return PMU_FLASH_OK;
}

PMU_Flash_Status_t PMU_Flash_Read(uint32_t address, uint8_t* data, uint32_t length)
{
    (void)address;
    /* Return zeros */
    for (uint32_t i = 0; i < length; i++) {
        data[i] = 0xFF;
    }
    return PMU_FLASH_OK;
}

PMU_Flash_Status_t PMU_Flash_Write(uint32_t address, const uint8_t* data, uint32_t length)
{
    (void)address;
    (void)data;
    (void)length;
    return PMU_FLASH_OK;
}

PMU_Flash_Status_t PMU_Flash_EraseSector(uint32_t address)
{
    (void)address;
    return PMU_FLASH_OK;
}

PMU_Flash_Status_t PMU_Flash_EraseBlock64K(uint32_t address)
{
    (void)address;
    return PMU_FLASH_OK;
}

PMU_Flash_Status_t PMU_Flash_EraseChip(void)
{
    return PMU_FLASH_OK;
}

PMU_Flash_Status_t PMU_Flash_GetInfo(PMU_Flash_Info_t* info)
{
    if (info) {
        info->manufacturer_id = 0;
        info->memory_type = 0;
        info->capacity = 0;
        info->jedec_id = 0;
        info->unique_id = 0;
        info->total_size = 0;
    }
    return PMU_FLASH_OK;
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

void PMU_Bootloader_JumpToApp(uint32_t app_address)
{
    (void)app_address;
    /* No-op in stub - infinite loop to satisfy noreturn */
    while (1) { }
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

/* ============================================================================
 * CAN Stubs (when NUCLEO_F446RE is defined - bxCAN vs FDCAN)
 * F446RE has bxCAN (classic CAN), H7 has FDCAN. The pmu_can.c uses FDCAN types.
 * ============================================================================ */

#ifdef NUCLEO_F446RE

#include "pmu_can.h"

HAL_StatusTypeDef PMU_CAN_Init(void)
{
    /* CAN initialization is done in main_nucleo_f446.c using bxCAN HAL */
    return HAL_OK;
}

void PMU_CAN_Update(void)
{
    /* No-op - CAN polling not implemented for bxCAN yet */
}

HAL_StatusTypeDef PMU_CAN_SendMessage(PMU_CAN_Bus_t bus, PMU_CAN_Message_t* msg)
{
    (void)bus;
    (void)msg;
    /* TODO: Implement bxCAN transmit */
    return HAL_OK;
}

HAL_StatusTypeDef PMU_CAN_SetFilter(PMU_CAN_Bus_t bus, uint32_t filter_id,
                                     uint32_t filter_mask, PMU_CAN_IDType_t id_type)
{
    (void)bus;
    (void)filter_id;
    (void)filter_mask;
    (void)id_type;
    return HAL_OK;
}

uint16_t PMU_CAN_GetRxQueueCount(PMU_CAN_Bus_t bus)
{
    (void)bus;
    return 0;
}

PMU_CAN_Message_t* PMU_CAN_GetNextMessage(PMU_CAN_Bus_t bus)
{
    (void)bus;
    return NULL;
}

/* ============================================================================
 * ADC Stubs (F446RE uses different ADC peripheral)
 * ============================================================================ */

#include "pmu_adc.h"

/* Simulated ADC values (use 20 as fallback if PMU_MAX_INPUTS not defined) */
#ifndef PMU_MAX_INPUTS
#define PMU_MAX_INPUTS 20
#endif
static uint16_t g_simulated_adc[PMU_MAX_INPUTS] = {0};

HAL_StatusTypeDef PMU_ADC_Init(void)
{
    /* ADC initialization is done in main_nucleo_f446.c */
    return HAL_OK;
}

void PMU_ADC_Update(void)
{
    /* ADC reading should be implemented here if needed */
}

uint16_t PMU_ADC_GetRawValue(uint8_t channel)
{
    if (channel >= PMU_MAX_INPUTS) return 0;
    return g_simulated_adc[channel];
}

uint16_t PMU_ADC_GetValue(uint8_t channel)
{
    if (channel >= PMU_MAX_INPUTS) return 0;
    return g_simulated_adc[channel];
}

float PMU_ADC_GetVoltage(uint8_t channel)
{
    if (channel >= PMU_MAX_INPUTS) return 0.0f;
    /* Convert 12-bit ADC to voltage (3.3V reference) */
    return (float)g_simulated_adc[channel] * 3.3f / 4095.0f;
}

float PMU_ADC_GetScaledValue(uint8_t channel)
{
    return PMU_ADC_GetVoltage(channel);
}

void PMU_ADC_SetSimulatedValue(uint8_t channel, uint16_t value)
{
    if (channel < PMU_MAX_INPUTS) {
        g_simulated_adc[channel] = value;
    }
}

/* ============================================================================
 * CAN Stream Stubs (F446RE - simplified CAN streaming)
 * ============================================================================ */

#include "pmu_can_stream.h"

int PMU_CanStream_Init(const PMU_CanStreamConfig_t* config)
{
    (void)config;
    return 0;
}

void PMU_CanStream_Update(void)
{
    /* No-op */
}

#endif /* NUCLEO_F446RE */

/* ============================================================================
 * Additional Hardware Module Stubs (for NUCLEO_F446RE)
 * These modules are disabled on F446RE but pmu_config_json.c references them
 * ============================================================================ */

#ifdef NUCLEO_F446RE

/* ADC extended functions */
#include "pmu_adc.h"

HAL_StatusTypeDef PMU_ADC_SetConfig(uint8_t channel, PMU_InputConfig_t* config)
{
    (void)channel;
    (void)config;
    return HAL_OK;
}

HAL_StatusTypeDef PMU_ADC_SetChannelId(uint8_t channel, uint16_t channel_id)
{
    (void)channel;
    (void)channel_id;
    return HAL_OK;
}

uint8_t PMU_ADC_GetDigitalState(uint8_t channel)
{
    (void)channel;
    return 0;
}

uint32_t PMU_ADC_GetFrequency(uint8_t channel)
{
    (void)channel;
    return 0;
}

/* LIN stubs - forward declare types to avoid including headers */
typedef struct PMU_LIN_InputConfig_s PMU_LIN_InputConfig_t;
typedef struct PMU_LIN_OutputConfig_s PMU_LIN_OutputConfig_t;
typedef struct PMU_LIN_FrameObjectConfig_s PMU_LIN_FrameObjectConfig_t;

int PMU_LIN_AddInput(const PMU_LIN_InputConfig_t* config)
{
    (void)config;
    return 0;
}

int PMU_LIN_AddOutput(const PMU_LIN_OutputConfig_t* config)
{
    (void)config;
    return 0;
}

int PMU_LIN_AddFrameObject(const PMU_LIN_FrameObjectConfig_t* config)
{
    (void)config;
    return 0;
}

/* PID controller stubs */
typedef struct PMU_PID_Config_s PMU_PID_Config_t;

int PMU_PID_AddController(const PMU_PID_Config_t* config)
{
    (void)config;
    return 0;
}

/* BlinkMarine keypad stubs */
typedef struct PMU_BlinkMarine_KeypadConfig_s PMU_BlinkMarine_KeypadConfig_t;

int PMU_BlinkMarine_AddKeypad(const PMU_BlinkMarine_KeypadConfig_t* config)
{
    (void)config;
    return 0;
}

/* CAN stream extended stubs */
#include "pmu_can_stream.h"

int PMU_CanStream_Configure(const PMU_CanStreamConfig_t* config)
{
    (void)config;
    return 0;
}

void PMU_CanStream_SetEnabled(bool enabled)
{
    (void)enabled;
}

/* CAN bus configuration stub */
#include "pmu_can.h"

HAL_StatusTypeDef PMU_CAN_ConfigureBus(PMU_CAN_Bus_t bus, PMU_CAN_BusConfig_t* config)
{
    (void)bus;
    (void)config;
    return HAL_OK;
}

/* WiFi stubs */
void PMU_WiFi_SetDefaultAPConfig(void* config)
{
    (void)config;
}

void PMU_WiFi_ApplyConfig(void)
{
    /* No-op */
}

/* Bluetooth stubs */
void PMU_BT_SetDefaultConfig(void* config)
{
    (void)config;
}

void PMU_BT_ApplyConfig(void)
{
    /* No-op */
}

/* Handler stubs */
void PMU_Handler_PushSystemEvent(uint8_t event_type, uint8_t severity, const char* message)
{
    (void)event_type;
    (void)severity;
    (void)message;
}

/* Fake ADC3 handle for pmu_protection.c */
/* On F446RE, ADC3 is not used - pmu_protection.c references it for MCU temp */
#include "stm32f4xx_hal.h"
ADC_HandleTypeDef hadc3 = {0};

#endif /* NUCLEO_F446RE */

/* ============================================================================
 * Lua Stubs (when PMU_DISABLE_LUA is defined)
 * ============================================================================ */

#ifdef PMU_DISABLE_LUA

#include "pmu_lua.h"

static PMU_Lua_Stats_t g_lua_stats = {0};

HAL_StatusTypeDef PMU_Lua_Init(void)
{
    return HAL_OK;
}

void PMU_Lua_Deinit(void)
{
    /* No-op */
}

HAL_StatusTypeDef PMU_Lua_LoadScript(const char* name, const char* script, uint32_t length)
{
    (void)name;
    (void)script;
    (void)length;
    return HAL_ERROR;  /* Lua disabled */
}

HAL_StatusTypeDef PMU_Lua_LoadScriptFromFile(const char* filename)
{
    (void)filename;
    return HAL_ERROR;
}

HAL_StatusTypeDef PMU_Lua_UnloadScript(const char* name)
{
    (void)name;
    return HAL_ERROR;
}

PMU_Lua_Status_t PMU_Lua_ExecuteScript(const char* name)
{
    (void)name;
    return PMU_LUA_STATUS_ERROR;
}

PMU_Lua_Status_t PMU_Lua_ExecuteCode(const char* code)
{
    (void)code;
    return PMU_LUA_STATUS_ERROR;
}

void PMU_Lua_Update(void)
{
    /* No-op */
}

HAL_StatusTypeDef PMU_Lua_SetScriptEnabled(const char* name, uint8_t enabled)
{
    (void)name;
    (void)enabled;
    return HAL_ERROR;
}

HAL_StatusTypeDef PMU_Lua_SetScriptAutoRun(const char* name, uint8_t auto_run)
{
    (void)name;
    (void)auto_run;
    return HAL_ERROR;
}

PMU_Lua_ScriptInfo_t* PMU_Lua_GetScriptInfo(const char* name)
{
    (void)name;
    return NULL;
}

PMU_Lua_Stats_t* PMU_Lua_GetStats(void)
{
    return &g_lua_stats;
}

uint8_t PMU_Lua_ListScripts(PMU_Lua_ScriptInfo_t* scripts, uint8_t max_count)
{
    (void)scripts;
    (void)max_count;
    return 0;
}

void PMU_Lua_ClearErrors(void)
{
    /* No-op */
}

const char* PMU_Lua_GetLastError(void)
{
    return "Lua disabled";
}

HAL_StatusTypeDef PMU_Lua_RegisterFunction(const char* name, void* func)
{
    (void)name;
    (void)func;
    return HAL_ERROR;
}

#endif /* PMU_DISABLE_LUA */

/* ============================================================================
 * Logic Functions Stubs (when pmu_logic_functions.c is excluded from build)
 * DEPRECATED: Replaced by shared/channel_executor.c
 * These stubs allow pmu_config_json.c and pmu_lua_api.c to compile
 * NOTE: We don't include pmu_logic_functions.h here to avoid type conflicts
 * ============================================================================ */

/* Forward declarations from pmu_logic_functions.h */
typedef struct PMU_LogicFunction_s PMU_LogicFunction_t;
/* Note: PMU_FunctionType_t replaced with int in stub functions - enums can't be forward-declared in C */

HAL_StatusTypeDef PMU_LogicFunctions_Init(void)
{
    return HAL_OK;  /* Channel Executor handles this now */
}

void PMU_LogicFunctions_Update(void)
{
    /* No-op: Channel Executor handles logic execution */
}

HAL_StatusTypeDef PMU_LogicFunctions_Register(PMU_LogicFunction_t* func)
{
    (void)func;
    return HAL_OK;  /* Silently accept - Channel Executor handles this */
}

HAL_StatusTypeDef PMU_LogicFunctions_Unregister(uint16_t function_id)
{
    (void)function_id;
    return HAL_OK;
}

PMU_LogicFunction_t* PMU_LogicFunctions_GetByID(uint16_t function_id)
{
    (void)function_id;
    return NULL;
}

HAL_StatusTypeDef PMU_LogicFunctions_SetEnabled(uint16_t function_id, bool enabled)
{
    (void)function_id;
    (void)enabled;
    return HAL_OK;
}

uint16_t PMU_LogicFunctions_CreateMath(int type,
                                        uint16_t output_ch,
                                        uint16_t input_a,
                                        uint16_t input_b)
{
    (void)type;
    (void)output_ch;
    (void)input_a;
    (void)input_b;
    return 0;  /* Return 0 as function ID */
}

uint16_t PMU_LogicFunctions_CreateComparison(int type,
                                              uint16_t output_ch,
                                              uint16_t input_a,
                                              uint16_t input_b)
{
    (void)type;
    (void)output_ch;
    (void)input_a;
    (void)input_b;
    return 0;
}

uint16_t PMU_LogicFunctions_CreatePID(uint16_t output_ch,
                                       uint16_t input_ch,
                                       float setpoint,
                                       float kp,
                                       float ki,
                                       float kd)
{
    (void)output_ch;
    (void)input_ch;
    (void)setpoint;
    (void)kp;
    (void)ki;
    (void)kd;
    return 0;
}

uint16_t PMU_LogicFunctions_CreateHysteresis(uint16_t output_ch,
                                              uint16_t input_ch,
                                              int32_t threshold_on,
                                              int32_t threshold_off)
{
    (void)output_ch;
    (void)input_ch;
    (void)threshold_on;
    (void)threshold_off;
    return 0;
}

/* pmu_config_json.c stubs removed - all JSON code deleted from protocol */

/**
 ******************************************************************************
 * @file           : pmu_emulator.c
 * @brief          : PMU-30 Hardware Emulator Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_emulator.h"
#include "stm32_hal_emu.h"
#include "pmu_channel.h"
#include "pmu_logic.h"
#include "pmu_can.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#include <sys/time.h>
#endif

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define EMU_LOG_ENABLED     1
#define EMU_LOG(fmt, ...)   do { if (emu_logging && EMU_LOG_ENABLED) printf("[EMU] " fmt "\n", ##__VA_ARGS__); } while(0)

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/

/* Global emulator state */
static PMU_Emulator_t emulator;
static bool emu_initialized = false;
static bool emu_logging = false;

/* HAL peripheral instances */
GPIO_TypeDef GPIOA_inst, GPIOB_inst, GPIOC_inst, GPIOD_inst;
GPIO_TypeDef GPIOE_inst, GPIOF_inst, GPIOG_inst, GPIOH_inst;
ADC_TypeDef ADC1_inst, ADC2_inst, ADC3_inst;
TIM_TypeDef TIM1_inst, TIM2_inst, TIM3_inst, TIM4_inst;
TIM_TypeDef TIM5_inst, TIM6_inst, TIM7_inst, TIM8_inst;
TIM_TypeDef TIM15_inst, TIM16_inst, TIM17_inst;
SPI_TypeDef SPI1_inst, SPI2_inst, SPI3_inst;
USART_TypeDef USART1_inst, USART2_inst, USART3_inst;
USART_TypeDef UART4_inst, UART5_inst;
FDCAN_GlobalTypeDef FDCAN1_inst, FDCAN2_inst, FDCAN3_inst;
IWDG_TypeDef IWDG_inst;

/* HAL tick counter */
static volatile uint32_t hal_tick = 0;

/* GPIO state storage */
static uint16_t gpio_state[8] = {0}; /* For GPIOA-GPIOH */

/* ADC DMA buffers (shared with firmware) */
extern uint16_t profet_current_adc_buffer[30];
extern uint16_t profet_status_adc_buffer[30];
extern uint16_t hbridge_current_adc_buffer[4];
extern uint16_t hbridge_position_adc_buffer[4];

/* Private function prototypes -----------------------------------------------*/
static void Emu_UpdateADC(uint32_t delta_ms);
static void Emu_UpdateCAN(uint32_t delta_ms);
static void Emu_UpdatePROFET(uint32_t delta_ms);
static void Emu_UpdateHBridge(uint32_t delta_ms);
static void Emu_UpdateProtection(uint32_t delta_ms);
static uint16_t Emu_AddNoise(uint16_t value, uint16_t amplitude);
static uint64_t Emu_GetTimeMs(void);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize the emulator
 */
int PMU_Emu_Init(void)
{
    if (emu_initialized) {
        return 0;
    }

    /* Clear state */
    memset(&emulator, 0, sizeof(emulator));

    /* Set defaults */
    emulator.time_scale = 1.0f;
    emulator.running = true;
    emulator.paused = false;

    /* Initialize ADC channels */
    for (int i = 0; i < PMU_EMU_ADC_CHANNELS; i++) {
        emulator.adc[i].raw_value = 512;  /* Mid-scale */
        emulator.adc[i].voltage_v = 1.65f;
        emulator.adc[i].enabled = true;
        emulator.adc[i].use_noise = false;
        emulator.adc[i].noise_amplitude = 10;
    }

    /* Initialize CAN buses */
    for (int i = 0; i < PMU_EMU_CAN_BUSES; i++) {
        emulator.can_bus_online[i] = true;
    }

    /* Initialize PROFET channels */
    for (int i = 0; i < PMU_EMU_PROFET_CHANNELS; i++) {
        emulator.profet[i].state = 0;  /* OFF */
        emulator.profet[i].pwm_duty = 0;
        emulator.profet[i].current_mA = 0;
        emulator.profet[i].temperature_C = 25;
        emulator.profet[i].fault_flags = 0;
        emulator.profet[i].load_resistance_ohm = 12.0f;  /* 1A @ 12V default */
    }

    /* Initialize H-Bridge channels */
    for (int i = 0; i < PMU_EMU_HBRIDGE_CHANNELS; i++) {
        emulator.hbridge[i].mode = 0;  /* COAST */
        emulator.hbridge[i].state = 0;  /* IDLE */
        emulator.hbridge[i].duty_cycle = 0;
        emulator.hbridge[i].current_mA = 0;
        emulator.hbridge[i].position = 0;
        emulator.hbridge[i].target_position = 0;
        emulator.hbridge[i].motor_speed = 100.0f;  /* Units/sec */
        emulator.hbridge[i].load_inertia = 1.0f;
        emulator.hbridge[i].fault_flags = 0;
    }

    /* Initialize protection */
    emulator.protection.battery_voltage_mV = PMU_EMU_DEFAULT_VOLTAGE_MV;
    emulator.protection.board_temp_C = PMU_EMU_DEFAULT_TEMP_C;
    emulator.protection.mcu_temp_C = PMU_EMU_DEFAULT_TEMP_C;
    emulator.protection.total_current_mA = 0;
    emulator.protection.fault_flags = 0;
    emulator.protection.enable_auto_faults = true;

    /* Seed random for noise */
    srand((unsigned int)time(NULL));

    emu_initialized = true;
    EMU_LOG("Emulator initialized");

    return 0;
}

/**
 * @brief Deinitialize the emulator
 */
void PMU_Emu_Deinit(void)
{
    if (!emu_initialized) {
        return;
    }

    emulator.running = false;
    emu_initialized = false;
    EMU_LOG("Emulator deinitialized");
}

/**
 * @brief Reset emulator to defaults
 */
void PMU_Emu_Reset(void)
{
    PMU_Emu_Deinit();
    PMU_Emu_Init();
    EMU_LOG("Emulator reset");
}

/**
 * @brief Get emulator state
 */
PMU_Emulator_t* PMU_Emu_GetState(void)
{
    return &emulator;
}

/**
 * @brief Run emulator tick
 */
void PMU_Emu_Tick(uint32_t delta_ms)
{
    if (!emu_initialized || emulator.paused) {
        return;
    }

    /* Scale time */
    uint32_t scaled_delta = (uint32_t)(delta_ms * emulator.time_scale);

    /* Update tick counter */
    emulator.tick_ms += scaled_delta;
    hal_tick += scaled_delta;

    /* Update uptime */
    static uint32_t uptime_accum = 0;
    uptime_accum += scaled_delta;
    if (uptime_accum >= 1000) {
        emulator.uptime_seconds += uptime_accum / 1000;
        uptime_accum %= 1000;
    }

    /* Update emulator subsystems (hardware simulation) */
    Emu_UpdateADC(scaled_delta);
    Emu_UpdateCAN(scaled_delta);
    Emu_UpdatePROFET(scaled_delta);
    Emu_UpdateHBridge(scaled_delta);
    Emu_UpdateProtection(scaled_delta);

    /* Update firmware logic (runs at 1kHz in real firmware) */
    static uint32_t channel_update_accum = 0;
    static uint32_t logic_update_accum = 0;

    channel_update_accum += scaled_delta;
    logic_update_accum += scaled_delta;

    /* Channel update at 1kHz */
    if (channel_update_accum >= 1) {
        PMU_Channel_Update();
        channel_update_accum = 0;
    }

    /* Logic update at 500Hz (every 2ms) */
    if (logic_update_accum >= 2) {
        PMU_Logic_Execute();
        logic_update_accum = 0;
    }

    /* CAN update */
    PMU_CAN_Update();
}

/**
 * @brief Pause/resume emulator
 */
void PMU_Emu_SetPaused(bool paused)
{
    emulator.paused = paused;
    EMU_LOG("Emulator %s", paused ? "paused" : "resumed");
}

/**
 * @brief Set time scale
 */
void PMU_Emu_SetTimeScale(float scale)
{
    if (scale > 0.0f && scale <= 100.0f) {
        emulator.time_scale = scale;
        EMU_LOG("Time scale set to %.1fx", scale);
    }
}

/* ============================================================================
 * ADC Input Injection
 * ============================================================================ */

int PMU_Emu_ADC_SetRaw(uint8_t channel, uint16_t value)
{
    if (channel >= PMU_EMU_ADC_CHANNELS) {
        return -1;
    }

    if (value > 1023) value = 1023;

    emulator.adc[channel].raw_value = value;
    emulator.adc[channel].voltage_v = (value * 3.3f) / 1024.0f;

    EMU_LOG("ADC[%d] = %d (%.3fV)", channel, value, emulator.adc[channel].voltage_v);
    return 0;
}

int PMU_Emu_ADC_SetVoltage(uint8_t channel, float voltage_v)
{
    if (channel >= PMU_EMU_ADC_CHANNELS) {
        return -1;
    }

    if (voltage_v < 0.0f) voltage_v = 0.0f;
    if (voltage_v > 3.3f) voltage_v = 3.3f;

    emulator.adc[channel].voltage_v = voltage_v;
    emulator.adc[channel].raw_value = (uint16_t)((voltage_v * 1024.0f) / 3.3f);

    EMU_LOG("ADC[%d] = %.3fV (%d)", channel, voltage_v, emulator.adc[channel].raw_value);
    return 0;
}

int PMU_Emu_ADC_SetFrequency(uint8_t channel, uint32_t frequency_hz)
{
    if (channel >= PMU_EMU_ADC_CHANNELS) {
        return -1;
    }

    emulator.adc[channel].frequency_hz = frequency_hz;
    EMU_LOG("ADC[%d] frequency = %u Hz", channel, frequency_hz);
    return 0;
}

int PMU_Emu_ADC_SetNoise(uint8_t channel, bool enable, uint16_t amplitude)
{
    if (channel >= PMU_EMU_ADC_CHANNELS) {
        return -1;
    }

    emulator.adc[channel].use_noise = enable;
    emulator.adc[channel].noise_amplitude = amplitude;
    return 0;
}

void PMU_Emu_ADC_SetAll(const uint16_t* values)
{
    if (values == NULL) return;

    for (int i = 0; i < PMU_EMU_ADC_CHANNELS; i++) {
        PMU_Emu_ADC_SetRaw(i, values[i]);
    }
}

/* ============================================================================
 * CAN Bus Injection
 * ============================================================================ */

int PMU_Emu_CAN_InjectMessage(uint8_t bus, uint32_t id, const uint8_t* data, uint8_t len)
{
    return PMU_Emu_CAN_InjectFD(bus, id, data, len, false);
}

int PMU_Emu_CAN_InjectFD(uint8_t bus, uint32_t id, const uint8_t* data, uint8_t len, bool is_extended)
{
    if (bus >= PMU_EMU_CAN_BUSES || data == NULL || len > 64) {
        return -1;
    }

    if (!emulator.can_bus_online[bus]) {
        EMU_LOG("CAN[%d] offline, message dropped", bus);
        return -1;
    }

    /* Find empty slot in RX queue */
    int slot = -1;
    for (int i = 0; i < PMU_EMU_CAN_RX_QUEUE_SIZE; i++) {
        if (!emulator.can_rx_queue[i].active || emulator.can_rx_queue[i].interval_ms == 0) {
            slot = i;
            break;
        }
    }

    if (slot < 0) {
        EMU_LOG("CAN RX queue full");
        return -1;
    }

    /* Store message */
    emulator.can_rx_queue[slot].bus = bus;
    emulator.can_rx_queue[slot].id = id;
    memcpy(emulator.can_rx_queue[slot].data, data, len);
    emulator.can_rx_queue[slot].dlc = len;
    emulator.can_rx_queue[slot].is_extended = is_extended;
    emulator.can_rx_queue[slot].is_fd = (len > 8);
    emulator.can_rx_queue[slot].interval_ms = 0;  /* One-shot */
    emulator.can_rx_queue[slot].active = true;

    emulator.can_rx_count++;

    EMU_LOG("CAN[%d] RX: ID=0x%X, DLC=%d", bus, id, len);
    return 0;
}

int PMU_Emu_CAN_AddPeriodicMessage(uint8_t bus, uint32_t id, const uint8_t* data, uint8_t len, uint32_t interval_ms)
{
    if (bus >= PMU_EMU_CAN_BUSES || data == NULL || len > 64 || interval_ms == 0) {
        return -1;
    }

    /* Find empty slot */
    int slot = -1;
    for (int i = 0; i < PMU_EMU_CAN_RX_QUEUE_SIZE; i++) {
        if (!emulator.can_rx_queue[i].active) {
            slot = i;
            break;
        }
    }

    if (slot < 0) {
        return -1;
    }

    emulator.can_rx_queue[slot].bus = bus;
    emulator.can_rx_queue[slot].id = id;
    memcpy(emulator.can_rx_queue[slot].data, data, len);
    emulator.can_rx_queue[slot].dlc = len;
    emulator.can_rx_queue[slot].is_extended = false;
    emulator.can_rx_queue[slot].is_fd = (len > 8);
    emulator.can_rx_queue[slot].interval_ms = interval_ms;
    emulator.can_rx_queue[slot].last_tx_tick = emulator.tick_ms;
    emulator.can_rx_queue[slot].active = true;

    EMU_LOG("CAN[%d] periodic: ID=0x%X, interval=%dms", bus, id, interval_ms);
    return slot;
}

int PMU_Emu_CAN_RemovePeriodicMessage(int index)
{
    if (index < 0 || index >= PMU_EMU_CAN_RX_QUEUE_SIZE) {
        return -1;
    }

    emulator.can_rx_queue[index].active = false;
    return 0;
}

void PMU_Emu_CAN_SetBusOnline(uint8_t bus, bool online)
{
    if (bus < PMU_EMU_CAN_BUSES) {
        emulator.can_bus_online[bus] = online;
        EMU_LOG("CAN[%d] %s", bus, online ? "online" : "offline");
    }
}

void PMU_Emu_CAN_SimulateError(uint8_t bus, uint8_t error_type)
{
    if (bus < PMU_EMU_CAN_BUSES) {
        EMU_LOG("CAN[%d] error: type=%d", bus, error_type);
        /* Error would be reported via CAN statistics */
    }
}

void PMU_Emu_CAN_SetTxCallback(PMU_Emu_CanTxCallback_t callback)
{
    emulator.on_can_tx = callback;
}

/* ============================================================================
 * PROFET Output Monitoring
 * ============================================================================ */

const PMU_Emu_PROFET_Channel_t* PMU_Emu_PROFET_GetState(uint8_t channel)
{
    if (channel >= PMU_EMU_PROFET_CHANNELS) {
        return NULL;
    }
    return &emulator.profet[channel];
}

int PMU_Emu_PROFET_SetLoad(uint8_t channel, float resistance_ohm)
{
    if (channel >= PMU_EMU_PROFET_CHANNELS || resistance_ohm <= 0.0f) {
        return -1;
    }

    emulator.profet[channel].load_resistance_ohm = resistance_ohm;
    EMU_LOG("PROFET[%d] load = %.1f ohm", channel, resistance_ohm);
    return 0;
}

int PMU_Emu_PROFET_InjectFault(uint8_t channel, uint8_t fault_flags)
{
    if (channel >= PMU_EMU_PROFET_CHANNELS) {
        return -1;
    }

    emulator.profet[channel].fault_flags |= fault_flags;
    emulator.profet[channel].state = 3;  /* FAULT */
    EMU_LOG("PROFET[%d] fault injected: 0x%02X", channel, fault_flags);
    return 0;
}

int PMU_Emu_PROFET_ClearFault(uint8_t channel)
{
    if (channel >= PMU_EMU_PROFET_CHANNELS) {
        return -1;
    }

    emulator.profet[channel].fault_flags = 0;
    if (emulator.profet[channel].state == 3) {
        emulator.profet[channel].state = 0;  /* OFF */
    }
    EMU_LOG("PROFET[%d] fault cleared", channel);
    return 0;
}

void PMU_Emu_PROFET_SetCallback(PMU_Emu_OutputCallback_t callback)
{
    emulator.on_profet_change = callback;
}

/* ============================================================================
 * H-Bridge Output Monitoring
 * ============================================================================ */

const PMU_Emu_HBridge_Channel_t* PMU_Emu_HBridge_GetState(uint8_t bridge)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS) {
        return NULL;
    }
    return &emulator.hbridge[bridge];
}

int PMU_Emu_HBridge_SetMotorParams(uint8_t bridge, float speed, float inertia)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS) {
        return -1;
    }

    emulator.hbridge[bridge].motor_speed = speed;
    emulator.hbridge[bridge].load_inertia = inertia;
    EMU_LOG("HBridge[%d] motor: speed=%.1f, inertia=%.1f", bridge, speed, inertia);
    return 0;
}

int PMU_Emu_HBridge_SetPosition(uint8_t bridge, uint16_t position)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS || position > 1000) {
        return -1;
    }

    emulator.hbridge[bridge].position = position;
    EMU_LOG("HBridge[%d] position = %d", bridge, position);
    return 0;
}

int PMU_Emu_HBridge_InjectFault(uint8_t bridge, uint8_t fault_flags)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS) {
        return -1;
    }

    emulator.hbridge[bridge].fault_flags |= fault_flags;
    emulator.hbridge[bridge].state = 4;  /* FAULT */
    EMU_LOG("HBridge[%d] fault injected: 0x%02X", bridge, fault_flags);
    return 0;
}

void PMU_Emu_HBridge_SetCallback(PMU_Emu_OutputCallback_t callback)
{
    emulator.on_hbridge_change = callback;
}

/* ============================================================================
 * Protection System Emulation
 * ============================================================================ */

void PMU_Emu_Protection_SetVoltage(uint16_t voltage_mV)
{
    emulator.protection.battery_voltage_mV = voltage_mV;
    EMU_LOG("Protection: voltage = %d mV", voltage_mV);
}

void PMU_Emu_Protection_SetTemperature(int16_t temp_C)
{
    emulator.protection.board_temp_C = temp_C;
    EMU_LOG("Protection: board temp = %d C", temp_C);
}

void PMU_Emu_Protection_SetMCUTemperature(int16_t temp_C)
{
    emulator.protection.mcu_temp_C = temp_C;
    EMU_LOG("Protection: MCU temp = %d C", temp_C);
}

void PMU_Emu_Protection_InjectFault(uint16_t fault_flags)
{
    emulator.protection.fault_flags |= fault_flags;
    EMU_LOG("Protection: fault injected 0x%04X", fault_flags);
}

void PMU_Emu_Protection_ClearFaults(void)
{
    emulator.protection.fault_flags = 0;
    EMU_LOG("Protection: faults cleared");
}

void PMU_Emu_Protection_SetAutoFaults(bool enable)
{
    emulator.protection.enable_auto_faults = enable;
}

/* ============================================================================
 * Scenario Loading
 * ============================================================================ */

int PMU_Emu_LoadScenario(const char* filename)
{
    FILE* f = fopen(filename, "r");
    if (!f) {
        EMU_LOG("Failed to open scenario file: %s", filename);
        return -1;
    }

    /* Read file content */
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    char* json = (char*)malloc(size + 1);
    if (!json) {
        fclose(f);
        return -1;
    }

    fread(json, 1, size, f);
    json[size] = '\0';
    fclose(f);

    int result = PMU_Emu_LoadScenarioFromString(json);
    free(json);

    return result;
}

int PMU_Emu_LoadScenarioFromString(const char* json)
{
    /* Simple JSON parser for scenario files */
    /* Format:
     * {
     *   "adc": [512, 1023, 0, ...],
     *   "can_messages": [
     *     {"bus": 0, "id": 0x100, "data": [1,2,3,4,5,6,7,8], "interval": 100}
     *   ],
     *   "voltage_mV": 12000,
     *   "temperature_C": 25
     * }
     */

    if (!json) return -1;

    EMU_LOG("Loading scenario from JSON...");

    /* Parse ADC values */
    const char* adc_start = strstr(json, "\"adc\"");
    if (adc_start) {
        const char* arr_start = strchr(adc_start, '[');
        if (arr_start) {
            arr_start++;
            for (int i = 0; i < PMU_EMU_ADC_CHANNELS; i++) {
                int value = atoi(arr_start);
                PMU_Emu_ADC_SetRaw(i, (uint16_t)value);

                const char* comma = strchr(arr_start, ',');
                if (comma) {
                    arr_start = comma + 1;
                } else {
                    break;
                }
            }
        }
    }

    /* Parse voltage */
    const char* voltage_start = strstr(json, "\"voltage_mV\"");
    if (voltage_start) {
        const char* colon = strchr(voltage_start, ':');
        if (colon) {
            int voltage = atoi(colon + 1);
            PMU_Emu_Protection_SetVoltage((uint16_t)voltage);
        }
    }

    /* Parse temperature */
    const char* temp_start = strstr(json, "\"temperature_C\"");
    if (temp_start) {
        const char* colon = strchr(temp_start, ':');
        if (colon) {
            int temp = atoi(colon + 1);
            PMU_Emu_Protection_SetTemperature((int16_t)temp);
        }
    }

    EMU_LOG("Scenario loaded");
    return 0;
}

int PMU_Emu_SaveScenario(const char* filename)
{
    FILE* f = fopen(filename, "w");
    if (!f) {
        return -1;
    }

    fprintf(f, "{\n");

    /* Save ADC values */
    fprintf(f, "  \"adc\": [");
    for (int i = 0; i < PMU_EMU_ADC_CHANNELS; i++) {
        fprintf(f, "%d", emulator.adc[i].raw_value);
        if (i < PMU_EMU_ADC_CHANNELS - 1) fprintf(f, ", ");
    }
    fprintf(f, "],\n");

    /* Save protection values */
    fprintf(f, "  \"voltage_mV\": %d,\n", emulator.protection.battery_voltage_mV);
    fprintf(f, "  \"temperature_C\": %d\n", emulator.protection.board_temp_C);

    fprintf(f, "}\n");
    fclose(f);

    EMU_LOG("Scenario saved to %s", filename);
    return 0;
}

/* ============================================================================
 * Logging & Debug
 * ============================================================================ */

void PMU_Emu_SetLogging(bool enable)
{
    emu_logging = enable;
}

void PMU_Emu_PrintState(void)
{
    printf("\n=== PMU-30 Emulator State ===\n");
    printf("Uptime: %u seconds\n", emulator.uptime_seconds);
    printf("Time scale: %.1fx\n", emulator.time_scale);
    printf("Status: %s\n", emulator.paused ? "PAUSED" : "RUNNING");

    printf("\n--- Protection ---\n");
    printf("Voltage: %d mV\n", emulator.protection.battery_voltage_mV);
    printf("Board Temp: %d C\n", emulator.protection.board_temp_C);
    printf("MCU Temp: %d C\n", emulator.protection.mcu_temp_C);
    printf("Total Current: %u mA\n", emulator.protection.total_current_mA);
    printf("Faults: 0x%04X\n", emulator.protection.fault_flags);

    printf("\n--- ADC Channels ---\n");
    for (int i = 0; i < PMU_EMU_ADC_CHANNELS; i++) {
        printf("ADC[%02d]: %4d (%.3fV)\n", i,
               emulator.adc[i].raw_value, emulator.adc[i].voltage_v);
    }

    printf("\n--- PROFET Outputs ---\n");
    int active_count = 0;
    for (int i = 0; i < PMU_EMU_PROFET_CHANNELS; i++) {
        if (emulator.profet[i].state != 0 || emulator.profet[i].pwm_duty != 0) {
            printf("PROFET[%02d]: state=%d, duty=%d%%, current=%dmA\n", i,
                   emulator.profet[i].state,
                   emulator.profet[i].pwm_duty / 10,
                   emulator.profet[i].current_mA);
            active_count++;
        }
    }
    if (active_count == 0) {
        printf("(All %d channels OFF)\n", PMU_EMU_PROFET_CHANNELS);
    }

    printf("\n--- H-Bridge Outputs ---\n");
    for (int i = 0; i < PMU_EMU_HBRIDGE_CHANNELS; i++) {
        printf("HBridge[%d]: mode=%d, state=%d, duty=%d%%, pos=%d\n", i,
               emulator.hbridge[i].mode,
               emulator.hbridge[i].state,
               emulator.hbridge[i].duty_cycle / 10,
               emulator.hbridge[i].position);
    }

    printf("\n--- CAN Buses ---\n");
    for (int i = 0; i < PMU_EMU_CAN_BUSES; i++) {
        printf("CAN[%d]: %s\n", i, emulator.can_bus_online[i] ? "ONLINE" : "OFFLINE");
    }

    printf("=============================\n\n");
}

void PMU_Emu_GetStatsString(char* buffer, size_t size)
{
    snprintf(buffer, size,
             "EMU: up=%us, V=%dmV, T=%dC, I=%umA",
             emulator.uptime_seconds,
             emulator.protection.battery_voltage_mV,
             emulator.protection.board_temp_C,
             emulator.protection.total_current_mA);
}

/* ============================================================================
 * Private Functions - Subsystem Updates
 * ============================================================================ */

static void Emu_UpdateADC(uint32_t delta_ms)
{
    (void)delta_ms;

    /* Update ADC DMA buffer with emulated values */
    /* The firmware reads from this buffer */
}

static void Emu_UpdateCAN(uint32_t delta_ms)
{
    (void)delta_ms;

    /* Process periodic CAN messages */
    for (int i = 0; i < PMU_EMU_CAN_RX_QUEUE_SIZE; i++) {
        if (!emulator.can_rx_queue[i].active) continue;
        if (emulator.can_rx_queue[i].interval_ms == 0) continue;  /* One-shot */

        uint32_t elapsed = emulator.tick_ms - emulator.can_rx_queue[i].last_tx_tick;
        if (elapsed >= emulator.can_rx_queue[i].interval_ms) {
            /* Time to send */
            emulator.can_rx_queue[i].last_tx_tick = emulator.tick_ms;

            /* This would trigger the CAN RX interrupt in the firmware */
            /* For now, the message is available in the queue */
        }
    }
}

static void Emu_UpdatePROFET(uint32_t delta_ms)
{
    (void)delta_ms;

    uint32_t total_current = 0;

    for (int i = 0; i < PMU_EMU_PROFET_CHANNELS; i++) {
        if (emulator.profet[i].fault_flags != 0) {
            emulator.profet[i].state = 3;  /* FAULT */
            emulator.profet[i].current_mA = 0;
            continue;
        }

        /* Calculate current based on state and duty */
        float voltage = emulator.protection.battery_voltage_mV / 1000.0f;
        float resistance = emulator.profet[i].load_resistance_ohm;

        if (resistance <= 0) resistance = 12.0f;

        float duty_factor = 1.0f;
        if (emulator.profet[i].state == 2) {  /* PWM */
            duty_factor = emulator.profet[i].pwm_duty / 1000.0f;
        } else if (emulator.profet[i].state != 1) {  /* Not ON */
            duty_factor = 0.0f;
        }

        float current_A = (voltage / resistance) * duty_factor;
        emulator.profet[i].current_mA = (uint16_t)(current_A * 1000.0f);

        /* Temperature simulation (simplified) */
        if (emulator.profet[i].current_mA > 0) {
            /* Heating */
            int16_t heat = (int16_t)(emulator.profet[i].current_mA / 5000);
            if (emulator.profet[i].temperature_C < 100 + heat) {
                emulator.profet[i].temperature_C++;
            }
        } else {
            /* Cooling */
            if (emulator.profet[i].temperature_C > 25) {
                emulator.profet[i].temperature_C--;
            }
        }

        total_current += emulator.profet[i].current_mA;
    }

    emulator.protection.total_current_mA = total_current;
}

static void Emu_UpdateHBridge(uint32_t delta_ms)
{
    for (int i = 0; i < PMU_EMU_HBRIDGE_CHANNELS; i++) {
        if (emulator.hbridge[i].fault_flags != 0) {
            emulator.hbridge[i].state = 4;  /* FAULT */
            continue;
        }

        /* Simulate motor movement */
        if (emulator.hbridge[i].mode == 1 || emulator.hbridge[i].mode == 2) {
            /* FORWARD or REVERSE */
            float speed = emulator.hbridge[i].motor_speed;
            float duty_factor = emulator.hbridge[i].duty_cycle / 1000.0f;
            float delta_pos = (speed * duty_factor * delta_ms) / (1000.0f * emulator.hbridge[i].load_inertia);

            int16_t new_pos = (int16_t)emulator.hbridge[i].position;
            if (emulator.hbridge[i].mode == 1) {
                new_pos += (int16_t)delta_pos;
            } else {
                new_pos -= (int16_t)delta_pos;
            }

            /* Clamp position */
            if (new_pos < 0) new_pos = 0;
            if (new_pos > 1000) new_pos = 1000;

            emulator.hbridge[i].position = (uint16_t)new_pos;
            emulator.hbridge[i].state = 1;  /* RUNNING */
        } else if (emulator.hbridge[i].mode == 0 || emulator.hbridge[i].mode == 3) {
            /* COAST or BRAKE */
            emulator.hbridge[i].state = 0;  /* IDLE */
        }

        /* Current simulation */
        if (emulator.hbridge[i].mode == 1 || emulator.hbridge[i].mode == 2) {
            float duty_factor = emulator.hbridge[i].duty_cycle / 1000.0f;
            emulator.hbridge[i].current_mA = (uint16_t)(5000 * duty_factor);  /* 5A max */
        } else {
            emulator.hbridge[i].current_mA = 0;
        }
    }
}

static void Emu_UpdateProtection(uint32_t delta_ms)
{
    (void)delta_ms;

    if (!emulator.protection.enable_auto_faults) {
        return;
    }

    /* Check voltage limits */
    if (emulator.protection.battery_voltage_mV < 6000) {
        emulator.protection.fault_flags |= 0x0001;  /* UNDERVOLTAGE */
    }
    if (emulator.protection.battery_voltage_mV > 22000) {
        emulator.protection.fault_flags |= 0x0002;  /* OVERVOLTAGE */
    }

    /* Check temperature limits */
    if (emulator.protection.board_temp_C > 100) {
        emulator.protection.fault_flags |= 0x0010;  /* OVERTEMP_WARNING */
    }
    if (emulator.protection.board_temp_C > 125) {
        emulator.protection.fault_flags |= 0x0020;  /* OVERTEMP_CRITICAL */
    }
}

static uint16_t Emu_AddNoise(uint16_t value, uint16_t amplitude)
{
    if (amplitude == 0) return value;

    int noise = (rand() % (amplitude * 2 + 1)) - amplitude;
    int result = (int)value + noise;

    if (result < 0) result = 0;
    if (result > 1023) result = 1023;

    return (uint16_t)result;
}

static uint64_t Emu_GetTimeMs(void)
{
#ifdef _WIN32
    return GetTickCount64();
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)(tv.tv_sec) * 1000 + tv.tv_usec / 1000;
#endif
}

/* ============================================================================
 * HAL Function Implementations
 * ============================================================================ */

uint32_t HAL_GetTick(void)
{
    return hal_tick;
}

void HAL_Delay(uint32_t Delay)
{
#ifdef _WIN32
    Sleep(Delay);
#else
    usleep(Delay * 1000);
#endif
    hal_tick += Delay;
}

void HAL_IncTick(void)
{
    hal_tick++;
}

HAL_StatusTypeDef HAL_Init(void)
{
    return HAL_OK;
}

HAL_StatusTypeDef HAL_DeInit(void)
{
    return HAL_OK;
}

/* GPIO Functions */
HAL_StatusTypeDef HAL_GPIO_Init(GPIO_TypeDef* GPIOx, GPIO_InitTypeDef* GPIO_Init)
{
    (void)GPIOx;
    (void)GPIO_Init;
    return HAL_OK;
}

void HAL_GPIO_DeInit(GPIO_TypeDef* GPIOx, uint32_t GPIO_Pin)
{
    (void)GPIOx;
    (void)GPIO_Pin;
}

int HAL_GPIO_ReadPin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin)
{
    int port = 0;
    if (GPIOx == GPIOA) port = 0;
    else if (GPIOx == GPIOB) port = 1;
    else if (GPIOx == GPIOC) port = 2;
    else if (GPIOx == GPIOD) port = 3;
    else if (GPIOx == GPIOE) port = 4;
    else if (GPIOx == GPIOF) port = 5;
    else if (GPIOx == GPIOG) port = 6;
    else if (GPIOx == GPIOH) port = 7;

    return (gpio_state[port] & GPIO_Pin) ? GPIO_PIN_SET : GPIO_PIN_RESET;
}

void HAL_GPIO_WritePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin, int PinState)
{
    int port = 0;
    if (GPIOx == GPIOA) port = 0;
    else if (GPIOx == GPIOB) port = 1;
    else if (GPIOx == GPIOC) port = 2;
    else if (GPIOx == GPIOD) port = 3;
    else if (GPIOx == GPIOE) port = 4;
    else if (GPIOx == GPIOF) port = 5;
    else if (GPIOx == GPIOG) port = 6;
    else if (GPIOx == GPIOH) port = 7;

    if (PinState == GPIO_PIN_SET) {
        gpio_state[port] |= GPIO_Pin;
    } else {
        gpio_state[port] &= ~GPIO_Pin;
    }
}

void HAL_GPIO_TogglePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin)
{
    int state = HAL_GPIO_ReadPin(GPIOx, GPIO_Pin);
    HAL_GPIO_WritePin(GPIOx, GPIO_Pin, state ? GPIO_PIN_RESET : GPIO_PIN_SET);
}

__attribute__((weak)) void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    (void)GPIO_Pin;
}

/* ADC Functions */
HAL_StatusTypeDef HAL_ADC_Init(ADC_HandleTypeDef* hadc)
{
    (void)hadc;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_ADC_DeInit(ADC_HandleTypeDef* hadc)
{
    (void)hadc;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_ADC_Start(ADC_HandleTypeDef* hadc)
{
    (void)hadc;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_ADC_Stop(ADC_HandleTypeDef* hadc)
{
    (void)hadc;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_ADC_Start_DMA(ADC_HandleTypeDef* hadc, uint32_t* pData, uint32_t Length)
{
    (void)hadc;

    /* Fill DMA buffer with emulated ADC values */
    uint16_t* buf = (uint16_t*)pData;
    for (uint32_t i = 0; i < Length && i < PMU_EMU_ADC_CHANNELS; i++) {
        uint16_t value = emulator.adc[i].raw_value;

        /* Add noise if enabled */
        if (emulator.adc[i].use_noise) {
            value = Emu_AddNoise(value, emulator.adc[i].noise_amplitude);
        }

        /* Scale to 12-bit (firmware expects 12-bit ADC) */
        buf[i] = value << 2;
    }

    return HAL_OK;
}

HAL_StatusTypeDef HAL_ADC_Stop_DMA(ADC_HandleTypeDef* hadc)
{
    (void)hadc;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_ADC_ConfigChannel(ADC_HandleTypeDef* hadc, ADC_ChannelConfTypeDef* sConfig)
{
    (void)hadc;
    (void)sConfig;
    return HAL_OK;
}

uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef* hadc)
{
    (void)hadc;
    return emulator.adc[0].raw_value << 2;  /* 12-bit */
}

__attribute__((weak)) void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc)
{
    (void)hadc;
}

/* Timer Functions */
HAL_StatusTypeDef HAL_TIM_Base_Init(TIM_HandleTypeDef* htim)
{
    (void)htim;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_TIM_Base_DeInit(TIM_HandleTypeDef* htim)
{
    (void)htim;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_TIM_Base_Start(TIM_HandleTypeDef* htim)
{
    (void)htim;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_TIM_Base_Stop(TIM_HandleTypeDef* htim)
{
    (void)htim;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_TIM_PWM_Init(TIM_HandleTypeDef* htim)
{
    (void)htim;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_TIM_PWM_Start(TIM_HandleTypeDef* htim, uint32_t Channel)
{
    (void)htim;
    (void)Channel;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_TIM_PWM_Stop(TIM_HandleTypeDef* htim, uint32_t Channel)
{
    (void)htim;
    (void)Channel;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_TIM_PWM_ConfigChannel(TIM_HandleTypeDef* htim, TIM_OC_InitTypeDef* sConfig, uint32_t Channel)
{
    (void)htim;
    (void)sConfig;
    (void)Channel;
    return HAL_OK;
}

__attribute__((weak)) void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef* htim)
{
    (void)htim;
}

/* SPI Functions */
HAL_StatusTypeDef HAL_SPI_Init(SPI_HandleTypeDef* hspi)
{
    (void)hspi;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_SPI_DeInit(SPI_HandleTypeDef* hspi)
{
    (void)hspi;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_SPI_Transmit(SPI_HandleTypeDef* hspi, uint8_t* pData, uint16_t Size, uint32_t Timeout)
{
    (void)hspi;
    (void)pData;
    (void)Size;
    (void)Timeout;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_SPI_Receive(SPI_HandleTypeDef* hspi, uint8_t* pData, uint16_t Size, uint32_t Timeout)
{
    (void)hspi;
    (void)Timeout;

    /* Return emulated SPI diagnostic data */
    memset(pData, 0, Size);
    return HAL_OK;
}

HAL_StatusTypeDef HAL_SPI_TransmitReceive(SPI_HandleTypeDef* hspi, uint8_t* pTxData, uint8_t* pRxData, uint16_t Size, uint32_t Timeout)
{
    (void)hspi;
    (void)pTxData;
    (void)Timeout;

    memset(pRxData, 0, Size);
    return HAL_OK;
}

/* UART Functions */
HAL_StatusTypeDef HAL_UART_Init(UART_HandleTypeDef* huart)
{
    (void)huart;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_UART_DeInit(UART_HandleTypeDef* huart)
{
    (void)huart;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef* huart, uint8_t* pData, uint16_t Size, uint32_t Timeout)
{
    (void)huart;
    (void)Timeout;

    /* Print to stdout for debug */
    fwrite(pData, 1, Size, stdout);
    fflush(stdout);
    return HAL_OK;
}

HAL_StatusTypeDef HAL_UART_Receive(UART_HandleTypeDef* huart, uint8_t* pData, uint16_t Size, uint32_t Timeout)
{
    (void)huart;
    (void)pData;
    (void)Size;
    (void)Timeout;
    return HAL_TIMEOUT;  /* No data available */
}

/* FDCAN Functions */
HAL_StatusTypeDef HAL_FDCAN_Init(FDCAN_HandleTypeDef* hfdcan)
{
    (void)hfdcan;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_FDCAN_DeInit(FDCAN_HandleTypeDef* hfdcan)
{
    (void)hfdcan;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_FDCAN_Start(FDCAN_HandleTypeDef* hfdcan)
{
    (void)hfdcan;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_FDCAN_Stop(FDCAN_HandleTypeDef* hfdcan)
{
    (void)hfdcan;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_FDCAN_ConfigFilter(FDCAN_HandleTypeDef* hfdcan, FDCAN_FilterTypeDef* sFilterConfig)
{
    (void)hfdcan;
    (void)sFilterConfig;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_FDCAN_AddMessageToTxFifoQ(FDCAN_HandleTypeDef* hfdcan, FDCAN_TxHeaderTypeDef* pTxHeader, uint8_t* pTxData)
{
    /* Determine bus from handle */
    uint8_t bus = 0;
    if (hfdcan->Instance == FDCAN1) bus = 0;
    else if (hfdcan->Instance == FDCAN2) bus = 1;
    else if (hfdcan->Instance == FDCAN3) bus = 2;

    /* Call TX callback if registered */
    if (emulator.on_can_tx) {
        uint8_t dlc = (pTxHeader->DataLength >> 16) & 0x0F;
        if (dlc > 8) {
            /* Map CAN FD DLC */
            static const uint8_t fd_dlc_map[] = {12, 16, 20, 24, 32, 48, 64};
            if (dlc <= 15 && dlc >= 9) {
                dlc = fd_dlc_map[dlc - 9];
            }
        }
        emulator.on_can_tx(bus, pTxHeader->Identifier, pTxData, dlc);
    }

    return HAL_OK;
}

HAL_StatusTypeDef HAL_FDCAN_GetRxMessage(FDCAN_HandleTypeDef* hfdcan, uint32_t RxLocation, FDCAN_RxHeaderTypeDef* pRxHeader, uint8_t* pRxData)
{
    (void)RxLocation;

    /* Determine bus from handle */
    uint8_t bus = 0;
    if (hfdcan->Instance == FDCAN1) bus = 0;
    else if (hfdcan->Instance == FDCAN2) bus = 1;
    else if (hfdcan->Instance == FDCAN3) bus = 2;

    /* Find pending message for this bus */
    for (int i = 0; i < PMU_EMU_CAN_RX_QUEUE_SIZE; i++) {
        if (emulator.can_rx_queue[i].active && emulator.can_rx_queue[i].bus == bus) {
            /* Copy message */
            pRxHeader->Identifier = emulator.can_rx_queue[i].id;
            pRxHeader->IdType = emulator.can_rx_queue[i].is_extended ? FDCAN_EXTENDED_ID : FDCAN_STANDARD_ID;
            pRxHeader->DataLength = emulator.can_rx_queue[i].dlc << 16;

            memcpy(pRxData, emulator.can_rx_queue[i].data, emulator.can_rx_queue[i].dlc);

            /* Mark as processed if one-shot */
            if (emulator.can_rx_queue[i].interval_ms == 0) {
                emulator.can_rx_queue[i].active = false;
                emulator.can_rx_count--;
            }

            return HAL_OK;
        }
    }

    return HAL_ERROR;  /* No message available */
}

uint32_t HAL_FDCAN_GetRxFifoFillLevel(FDCAN_HandleTypeDef* hfdcan, uint32_t RxFifo)
{
    (void)RxFifo;

    /* Determine bus from handle */
    uint8_t bus = 0;
    if (hfdcan->Instance == FDCAN1) bus = 0;
    else if (hfdcan->Instance == FDCAN2) bus = 1;
    else if (hfdcan->Instance == FDCAN3) bus = 2;

    /* Count messages for this bus */
    uint32_t count = 0;
    for (int i = 0; i < PMU_EMU_CAN_RX_QUEUE_SIZE; i++) {
        if (emulator.can_rx_queue[i].active && emulator.can_rx_queue[i].bus == bus) {
            count++;
        }
    }

    return count;
}

HAL_StatusTypeDef HAL_FDCAN_ActivateNotification(FDCAN_HandleTypeDef* hfdcan, uint32_t ActiveITs, uint32_t BufferIndexes)
{
    (void)hfdcan;
    (void)ActiveITs;
    (void)BufferIndexes;
    return HAL_OK;
}

__attribute__((weak)) void HAL_FDCAN_RxFifo0Callback(FDCAN_HandleTypeDef* hfdcan, uint32_t RxFifo0ITs)
{
    (void)hfdcan;
    (void)RxFifo0ITs;
}

/* IWDG Functions */
HAL_StatusTypeDef HAL_IWDG_Init(IWDG_HandleTypeDef* hiwdg)
{
    (void)hiwdg;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_IWDG_Refresh(IWDG_HandleTypeDef* hiwdg)
{
    (void)hiwdg;
    return HAL_OK;
}

/* NVIC Functions */
void HAL_NVIC_SetPriority(IRQn_Type IRQn, uint32_t PreemptPriority, uint32_t SubPriority)
{
    (void)IRQn;
    (void)PreemptPriority;
    (void)SubPriority;
}

void HAL_NVIC_EnableIRQ(IRQn_Type IRQn)
{
    (void)IRQn;
}

void HAL_NVIC_DisableIRQ(IRQn_Type IRQn)
{
    (void)IRQn;
}

/* System Functions */
void SystemClock_Config(void)
{
    /* No clock configuration needed in emulation */
}

__attribute__((weak)) void Error_Handler(void)
{
    fprintf(stderr, "Error_Handler called!\n");
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

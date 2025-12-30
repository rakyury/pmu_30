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

/* Feature test macros for POSIX functions (Linux) ---------------------------*/
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE
#endif

/* Includes ------------------------------------------------------------------*/
#include "pmu_emulator.h"
#include "stm32_hal_emu.h"
#include "pmu_channel.h"
#include "pmu_logic.h"
#include "pmu_can.h"
#include "pmu_lin.h"
#include "pmu_profet.h"
#include "pmu_protection.h"
#include "pmu_pid.h"
#include "pmu_timer.h"
#include "pmu_blinkmarine.h"
#include "pmu_config_json.h"
#include "pmu_adc.h"
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
static void Emu_UpdateDigitalInputs(uint32_t delta_ms);
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

    /* Initialize channel abstraction layer (registers system channels like "one", "zero") */
    PMU_Channel_Init();

    /* Set defaults */
    emulator.time_scale = 1.0f;
    emulator.running = true;
    emulator.paused = false;

    /* Initialize ADC channels to 0V
     * NOTE: enabled=false means digital inputs will sync to ADC.
     * Set enabled=true when manually injecting voltage values. */
    for (int i = 0; i < PMU_EMU_ADC_CHANNELS; i++) {
        emulator.adc[i].raw_value = 0;
        emulator.adc[i].voltage_v = 0.0f;
        emulator.adc[i].enabled = false;  /* Allow digital input sync by default */
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
        emulator.profet[i].prev_state = 0;
        emulator.profet[i].pwm_duty = 0;
        emulator.profet[i].current_mA = 0;
        emulator.profet[i].temperature_C = 25;
        emulator.profet[i].fault_flags = 0;
        emulator.profet[i].load_resistance_ohm = 12.0f;  /* 1A @ 12V default */
        /* Realistic simulation defaults */
        emulator.profet[i].inrush_remaining_ms = 0;
        emulator.profet[i].inrush_multiplier = 5.0f;  /* 5x inrush for lamps/motors */
        emulator.profet[i].thermal_energy_J = 0.0f;
        emulator.profet[i].soft_start_ms = 0;  /* 0 = no soft-start */
        emulator.profet[i].soft_start_elapsed = 0;
    }

    /* Initialize H-Bridge channels with realistic motor parameters */
    for (int i = 0; i < PMU_EMU_HBRIDGE_CHANNELS; i++) {
        PMU_Emu_HBridge_Channel_t* hb = &emulator.hbridge[i];

        hb->mode = 0;  /* COAST */
        hb->state = 0;  /* IDLE */
        hb->duty_cycle = 0;
        hb->current_mA = 0;
        hb->position = 500;  /* Mid-position */
        hb->target_position = 500;
        hb->motor_speed = 100.0f;  /* Legacy: units/sec */
        hb->load_inertia = 1.0f;   /* Legacy */
        hb->fault_flags = 0;

        /* Default motor parameters - typical 12V automotive wiper motor */
        PMU_Emu_MotorParams_t* mp = &hb->motor_params;
        mp->Kt = 0.05f;              /* Torque constant: 0.05 Nm/A */
        mp->Ke = 0.05f;              /* Back-EMF constant (V/(rad/s)) = Kt for DC motors */
        mp->Rm = 0.5f;               /* Motor resistance: 0.5 Ohm */
        mp->Lm = 0.001f;             /* Motor inductance: 1 mH */
        mp->Jm = 0.0001f;            /* Motor inertia: 100 g·cm² */
        mp->Jl = 0.001f;             /* Load inertia: 1000 g·cm² (wiper arm + blade) */
        mp->gear_ratio = 50.0f;      /* Typical worm gear ratio */
        mp->Bf = 0.0001f;            /* Viscous friction */
        mp->Tf = 0.01f;              /* Coulomb friction: 10 mNm */
        mp->Ts = 0.02f;              /* Stiction: 20 mNm */
        mp->stiction_velocity = 0.1f; /* 0.1 rad/s threshold */
        mp->pos_min_rad = 0.0f;      /* Min position: 0 rad */
        mp->pos_max_rad = 3.14159f;  /* Max position: π rad (180°) */
        mp->end_stop_stiffness = 10.0f; /* End-stop spring: 10 Nm/rad */
        mp->thermal_resistance = 5.0f;  /* 5 K/W */
        mp->thermal_capacitance = 50.0f; /* 50 J/K */

        /* Initial motor state */
        PMU_Emu_MotorState_t* ms = &hb->motor_state;
        ms->current_A = 0.0f;
        ms->voltage_V = 0.0f;
        ms->back_emf_V = 0.0f;
        ms->omega = 0.0f;
        ms->omega_prev = 0.0f;
        ms->theta = 1.5708f;  /* Start at π/2 rad (90°, mid-position) */
        ms->torque_motor = 0.0f;
        ms->torque_friction = 0.0f;
        ms->torque_load = 0.0f;
        ms->acceleration = 0.0f;
        ms->temperature_C = 25.0f;
        ms->power_dissipated_W = 0.0f;
        ms->at_end_stop = 0;
        ms->stalled = 0;
        ms->stall_time_ms = 0;
    }

    /* Initialize protection */
    emulator.protection.battery_voltage_mV = PMU_EMU_DEFAULT_VOLTAGE_MV;
    emulator.protection.board_temp_L_C = PMU_EMU_DEFAULT_TEMP_C;
    emulator.protection.board_temp_R_C = PMU_EMU_DEFAULT_TEMP_C;
    emulator.protection.mcu_temp_C = PMU_EMU_DEFAULT_TEMP_C;
    emulator.protection.total_current_mA = 0;
    emulator.protection.fault_flags = 0;
    emulator.protection.enable_auto_faults = true;
    emulator.protection.output_5v_mV = 5000;
    emulator.protection.output_3v3_mV = 3300;
    emulator.protection.system_status = 0;
    emulator.protection.user_error = 0;
    emulator.protection.is_turning_off = 0;

    /* Initialize WiFi module */
    emulator.wifi.state = PMU_EMU_WIFI_STATE_OFF;
    emulator.wifi.enabled = false;
    emulator.wifi.ap_mode = false;
    strcpy(emulator.wifi.ssid, "");
    strcpy(emulator.wifi.ip_addr, "0.0.0.0");
    emulator.wifi.rssi = -100;
    emulator.wifi.channel = 0;
    emulator.wifi.tx_bytes = 0;
    emulator.wifi.rx_bytes = 0;
    emulator.wifi.clients_connected = 0;
    emulator.wifi.uptime_s = 0;

    /* Initialize Bluetooth module */
    emulator.bluetooth.state = PMU_EMU_BT_STATE_OFF;
    emulator.bluetooth.enabled = false;
    emulator.bluetooth.ble_mode = true;
    strcpy(emulator.bluetooth.device_name, "PMU-30");
    strcpy(emulator.bluetooth.peer_address, "");
    emulator.bluetooth.rssi = -100;
    emulator.bluetooth.tx_bytes = 0;
    emulator.bluetooth.rx_bytes = 0;
    emulator.bluetooth.authenticated = false;
    emulator.bluetooth.uptime_s = 0;

    /* Initialize flash simulation */
    emulator.flash_temp_C = 25;
    emulator.flash_file_count = 0;

    /* Initialize digital inputs to ON state by default.
     * Low-side switches (active_low) are normally connected to ground,
     * so default state should be ON (pressed/active). */
    for (int i = 0; i < PMU_EMU_DIGITAL_INPUTS; i++) {
        emulator.digital_inputs[i].state = true;
        emulator.digital_inputs[i].debounced_state = true;
        emulator.digital_inputs[i].inverted = false;
        emulator.digital_inputs[i].debounce_ms = 50;
        emulator.digital_inputs[i].last_change_ms = 0;
    }

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
    static uint32_t tick_debug = 0;
    tick_debug++;
    if (tick_debug % 5000 == 1) {
        printf("[TICK] init=%d, paused=%d, delta=%d, scale=%.1f\n",
               emu_initialized, emulator.paused, delta_ms, emulator.time_scale);
        fflush(stdout);
    }

    if (!emu_initialized || emulator.paused) {
        return;
    }

    /* Scale time */
    uint32_t scaled_delta = (uint32_t)(delta_ms * emulator.time_scale);

    /* Update tick counter */
    emulator.tick_ms += scaled_delta;
    hal_tick += scaled_delta;

    /* Update uptime */
    emulator.uptime_accum_ms += scaled_delta;
    if (emulator.uptime_accum_ms >= 1000) {
        emulator.uptime_seconds += emulator.uptime_accum_ms / 1000;
        emulator.uptime_accum_ms %= 1000;
    }

    /* Update emulator subsystems (hardware simulation)
     * IMPORTANT: Digital inputs must update BEFORE ADC so that
     * switch state changes are reflected in ADC values before
     * they are copied to the DMA buffer */
    Emu_UpdateDigitalInputs(scaled_delta);
    Emu_UpdateADC(scaled_delta);
    Emu_UpdateCAN(scaled_delta);
    Emu_UpdatePROFET(scaled_delta);
    Emu_UpdateHBridge(scaled_delta);
    Emu_UpdateProtection(scaled_delta);

    /* Update firmware ADC module (processes analog inputs, updates digital_state) */
    extern void PMU_ADC_Update(void);
    PMU_ADC_Update();

    /* Update firmware PROFET module (reads current from emulator via SPI stubs) */
    PMU_PROFET_Update();

    /* Update firmware protection module (reads voltage/temp from emulator via ADC stubs) */
    PMU_Protection_Update();

    /* Update firmware logic (runs at 1kHz in real firmware) */
    static uint32_t channel_update_accum = 0;
    static uint32_t logic_update_accum = 0;
    static uint32_t debug_accum = 0;

    channel_update_accum += scaled_delta;
    logic_update_accum += scaled_delta;
    debug_accum += scaled_delta;

    /* Channel update at 1kHz */
    if (channel_update_accum >= 1) {
        PMU_Channel_Update();
        channel_update_accum = 0;
    }

    /* Logic update at 500Hz (every 2ms) */
    if (logic_update_accum >= 2) {
        PMU_Logic_Execute();
        PMU_LogicChannel_Update();  /* JSON-config logic channels */
        PMU_NumberChannel_Update(); /* JSON-config math channels */
        PMU_SwitchChannel_Update(); /* JSON-config switch channels */
        PMU_FilterChannel_Update(); /* JSON-config filter channels */
        PMU_TimerChannel_Update();  /* JSON-config timer channels */
        PMU_PID_Update();
        PMU_Timer_Update();
        PMU_PowerOutput_Update();  /* Update outputs based on control channels */
        logic_update_accum = 0;
    }

    /* Debug output disabled - was too spammy */
    (void)debug_accum;

    /* CAN update */
    PMU_CAN_Update();

    /* BlinkMarine keypad update */
    PMU_BlinkMarine_Update();
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
 * Digital Input Emulation
 * ============================================================================ */

int PMU_Emu_DI_SetState(uint8_t channel, bool state)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return -1;
    }

    PMU_Emu_Digital_Input_t* di = &emulator.digital_inputs[channel];
    bool old_state = di->state;
    di->state = state;

    /* Detect edges */
    if (state && !old_state) {
        di->edge_rising = true;
        di->pulse_count++;
    } else if (!state && old_state) {
        di->edge_falling = true;
    }

    /* Update timestamp for debounce */
    if (state != old_state) {
        di->last_change_ms = emulator.tick_ms;
    }

    /* Immediate debounced state update if no debounce configured */
    if (di->debounce_ms == 0) {
        di->debounced_state = di->inverted ? !state : state;
    }

    /* NOTE: Do NOT call PMU_ADC_SetDigitalState() directly here!
     * The digital_state must be computed by PMU_ADC_Update() which applies
     * the correct subtype logic (switch_active_low vs switch_active_high).
     * The flow is:
     * 1. DI state change updates emulator.digital_inputs[]
     * 2. Emu_UpdateDigitalInputs() sets emulator.adc[].raw_value based on input type
     * 3. Emu_UpdateADC() syncs to adc_dma_buffer[]
     * 4. PMU_ADC_Update() processes and sets correct digital_state via type handlers */

    EMU_LOG("DI[%d] = %d", channel, state);
    return 0;
}

bool PMU_Emu_DI_GetState(uint8_t channel)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return false;
    }
    return emulator.digital_inputs[channel].debounced_state;
}

int PMU_Emu_DI_Configure(uint8_t channel, bool inverted, bool pull_up, uint32_t debounce_ms)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return -1;
    }

    PMU_Emu_Digital_Input_t* di = &emulator.digital_inputs[channel];
    di->inverted = inverted;
    di->pull_up = pull_up;
    di->pull_down = !pull_up;
    di->debounce_ms = debounce_ms;

    /* Set initial state based on pull-up/down */
    if (pull_up) {
        di->state = true;
        di->debounced_state = inverted ? false : true;
    } else {
        di->state = false;
        di->debounced_state = inverted ? true : false;
    }

    return 0;
}

int PMU_Emu_DI_Pulse(uint8_t channel, uint32_t duration_ms)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return -1;
    }

    /* Toggle on, then schedule toggle off (simple implementation) */
    PMU_Emu_DI_SetState(channel, true);
    /* Note: In a real implementation, this would use a timer to turn off after duration_ms */
    /* For now, just log the pulse request */
    EMU_LOG("DI[%d] pulse %dms requested (simplified)", channel, duration_ms);
    return 0;
}

int PMU_Emu_DI_Toggle(uint8_t channel)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return -1;
    }

    return PMU_Emu_DI_SetState(channel, !emulator.digital_inputs[channel].state);
}

void PMU_Emu_DI_SetAll(uint16_t states)
{
    for (int i = 0; i < PMU_EMU_DIGITAL_INPUTS; i++) {
        PMU_Emu_DI_SetState(i, (states >> i) & 1);
    }
}

uint16_t PMU_Emu_DI_GetAll(void)
{
    uint16_t result = 0;
    for (int i = 0; i < PMU_EMU_DIGITAL_INPUTS; i++) {
        if (emulator.digital_inputs[i].debounced_state) {
            result |= (1 << i);
        }
    }
    return result;
}

bool PMU_Emu_DI_GetRisingEdge(uint8_t channel)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return false;
    }

    bool edge = emulator.digital_inputs[channel].edge_rising;
    emulator.digital_inputs[channel].edge_rising = false;
    return edge;
}

bool PMU_Emu_DI_GetFallingEdge(uint8_t channel)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return false;
    }

    bool edge = emulator.digital_inputs[channel].edge_falling;
    emulator.digital_inputs[channel].edge_falling = false;
    return edge;
}

uint32_t PMU_Emu_DI_GetPulseCount(uint8_t channel, bool reset)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return 0;
    }

    uint32_t count = emulator.digital_inputs[channel].pulse_count;
    if (reset) {
        emulator.digital_inputs[channel].pulse_count = 0;
    }
    return count;
}

const PMU_Emu_Digital_Input_t* PMU_Emu_DI_GetChannel(uint8_t channel)
{
    if (channel >= PMU_EMU_DIGITAL_INPUTS) {
        return NULL;
    }
    return &emulator.digital_inputs[channel];
}

/**
 * @brief Update digital input debouncing (called from tick)
 */
static void Emu_UpdateDigitalInputs(uint32_t delta_ms)
{
    (void)delta_ms;

    for (int i = 0; i < PMU_EMU_DIGITAL_INPUTS; i++) {
        PMU_Emu_Digital_Input_t* di = &emulator.digital_inputs[i];

        if (di->debounce_ms > 0) {
            /* Check if debounce time has elapsed */
            uint32_t elapsed = emulator.tick_ms - di->last_change_ms;
            if (elapsed >= di->debounce_ms) {
                bool new_state = di->inverted ? !di->state : di->state;
                di->debounced_state = new_state;
            }
        }

        /* Sync digital input state to ADC for firmware processing.
         * Digital inputs are configured via JSON as "digital_input" channels,
         * which sets up the ADC system to process them as switch inputs.
         * The firmware's PMU_ADC_Update() reads from adc_dma_buffer which
         * gets filled from emulator.adc[].raw_value by Emu_UpdateADC().
         *
         * Only sync if ADC channel is not manually overridden (enabled=false).
         * Physical voltage mapping:
         * - di->state = true (HIGH voltage, ~5V) -> raw_value = 1023 (10-bit max)
         * - di->state = false (LOW voltage, ~0V) -> raw_value = 0
         */
        if (i < PMU_EMU_ADC_CHANNELS && !emulator.adc[i].enabled) {
            emulator.adc[i].raw_value = di->state ? 1023 : 0;
            emulator.adc[i].voltage_v = di->state ? 5.0f : 0.0f;
        }
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

    /* Update emulator state - map fault to state */
    emulator.profet[channel].fault_flags |= fault_flags;

    /* Map fault type to specific state:
     * 2=OC (overcurrent), 3=OT (overtemp), 4=SC (short circuit), 5=OL (open load) */
    if (fault_flags & 0x04) {        /* Short circuit */
        emulator.profet[channel].state = 4;  /* SC */
    } else if (fault_flags & 0x02) { /* Over temperature */
        emulator.profet[channel].state = 3;  /* OT */
    } else if (fault_flags & 0x08) { /* Open load */
        emulator.profet[channel].state = 5;  /* OL */
    } else {                         /* Default: overcurrent */
        emulator.profet[channel].state = 2;  /* OC */
    }

    /* Also inject into firmware PROFET module */
    PMU_PROFET_InjectFault(channel, fault_flags);

    EMU_LOG("PROFET[%d] fault injected: 0x%02X", channel, fault_flags);
    return 0;
}

int PMU_Emu_PROFET_ClearFault(uint8_t channel)
{
    if (channel >= PMU_EMU_PROFET_CHANNELS) {
        return -1;
    }

    /* Clear emulator state */
    emulator.profet[channel].fault_flags = 0;

    /* Check if in any fault state (2=OC, 3=OT, 4=SC, 5=OL) */
    uint8_t state = emulator.profet[channel].state;
    if (state >= 2 && state <= 5) {
        emulator.profet[channel].state = 0;  /* OFF */
    }

    /* Also clear in firmware PROFET module */
    PMU_PROFET_ClearFaults(channel);

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

/**
 * @brief Set H-Bridge mode and PWM duty cycle
 */
int PMU_Emu_HBridge_SetMode(uint8_t bridge, uint8_t mode, uint16_t duty)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS) {
        return -1;
    }

    PMU_Emu_HBridge_Channel_t* hb = &emulator.hbridge[bridge];

    /* Limit duty cycle */
    if (duty > 1000) duty = 1000;

    /* Set mode */
    uint8_t old_mode = hb->mode;
    hb->mode = mode;
    hb->duty_cycle = duty;

    /* Update state based on mode */
    if (mode == 0) { /* COAST */
        hb->state = 0; /* IDLE */
    } else if (mode == 1 || mode == 2) { /* FORWARD or REVERSE */
        hb->state = 1; /* RUNNING */
    } else if (mode == 3) { /* BRAKE */
        hb->state = 0; /* IDLE */
    }

    EMU_LOG("HBridge[%d] mode=%d duty=%d (%.1f%%)", bridge, mode, duty, duty / 10.0f);

    /* Notify callback - encode mode in high nibble, keep duty in low 12 bits */
    if (emulator.on_hbridge_change && old_mode != mode) {
        uint16_t encoded_value = ((uint16_t)mode << 12) | (duty & 0x0FFF);
        emulator.on_hbridge_change(bridge, encoded_value);
    }

    return 0;
}

/**
 * @brief Set H-Bridge target position for PID control
 */
int PMU_Emu_HBridge_SetTarget(uint8_t bridge, uint16_t target)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS) {
        return -1;
    }

    if (target > 1000) target = 1000;

    emulator.hbridge[bridge].target_position = target;
    EMU_LOG("HBridge[%d] target position=%d", bridge, target);
    return 0;
}

/**
 * @brief Set detailed motor physics parameters
 */
int PMU_Emu_HBridge_SetMotorPhysics(uint8_t bridge, const PMU_Emu_MotorParams_t* params)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS || params == NULL) {
        return -1;
    }

    memcpy(&emulator.hbridge[bridge].motor_params, params, sizeof(PMU_Emu_MotorParams_t));
    EMU_LOG("HBridge[%d] motor physics updated: Kt=%.3f, Ke=%.3f, Rm=%.2f",
            bridge, params->Kt, params->Ke, params->Rm);
    return 0;
}

/**
 * @brief Set motor preset configuration
 * Presets: "wiper", "valve", "window", "seat", "pump"
 */
int PMU_Emu_HBridge_SetMotorPreset(uint8_t bridge, const char* preset)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS || preset == NULL) {
        return -1;
    }

    PMU_Emu_MotorParams_t* mp = &emulator.hbridge[bridge].motor_params;

    if (strcmp(preset, "wiper") == 0) {
        /* Windshield wiper motor - high torque, moderate speed */
        mp->Kt = 0.05f;    mp->Ke = 0.05f;
        mp->Rm = 0.5f;     mp->Lm = 0.001f;
        mp->Jm = 0.0001f;  mp->Jl = 0.001f;
        mp->gear_ratio = 50.0f;
        mp->Bf = 0.0001f;  mp->Tf = 0.01f;   mp->Ts = 0.02f;
        mp->stiction_velocity = 0.1f;
        mp->pos_min_rad = 0.0f;  mp->pos_max_rad = 3.14159f;
        mp->end_stop_stiffness = 10.0f;
        mp->thermal_resistance = 5.0f;  mp->thermal_capacitance = 50.0f;
    }
    else if (strcmp(preset, "valve") == 0) {
        /* Valve actuator - slow, precise positioning */
        mp->Kt = 0.03f;    mp->Ke = 0.03f;
        mp->Rm = 2.0f;     mp->Lm = 0.002f;
        mp->Jm = 0.00005f; mp->Jl = 0.0005f;
        mp->gear_ratio = 100.0f;
        mp->Bf = 0.0005f;  mp->Tf = 0.005f;  mp->Ts = 0.01f;
        mp->stiction_velocity = 0.05f;
        mp->pos_min_rad = 0.0f;  mp->pos_max_rad = 1.5708f;  /* 90° */
        mp->end_stop_stiffness = 20.0f;
        mp->thermal_resistance = 8.0f;  mp->thermal_capacitance = 30.0f;
    }
    else if (strcmp(preset, "window") == 0) {
        /* Power window motor - moderate speed, high load */
        mp->Kt = 0.08f;    mp->Ke = 0.08f;
        mp->Rm = 0.3f;     mp->Lm = 0.0008f;
        mp->Jm = 0.0002f;  mp->Jl = 0.002f;
        mp->gear_ratio = 80.0f;
        mp->Bf = 0.0002f;  mp->Tf = 0.02f;   mp->Ts = 0.03f;
        mp->stiction_velocity = 0.1f;
        mp->pos_min_rad = 0.0f;  mp->pos_max_rad = 6.28318f;  /* 360° */
        mp->end_stop_stiffness = 15.0f;
        mp->thermal_resistance = 4.0f;  mp->thermal_capacitance = 60.0f;
    }
    else if (strcmp(preset, "seat") == 0) {
        /* Seat motor - very slow, very high torque */
        mp->Kt = 0.1f;     mp->Ke = 0.1f;
        mp->Rm = 0.2f;     mp->Lm = 0.0005f;
        mp->Jm = 0.0003f;  mp->Jl = 0.005f;
        mp->gear_ratio = 200.0f;
        mp->Bf = 0.0003f;  mp->Tf = 0.05f;   mp->Ts = 0.08f;
        mp->stiction_velocity = 0.05f;
        mp->pos_min_rad = 0.0f;  mp->pos_max_rad = 1.0472f;  /* 60° */
        mp->end_stop_stiffness = 25.0f;
        mp->thermal_resistance = 3.0f;  mp->thermal_capacitance = 80.0f;
    }
    else if (strcmp(preset, "pump") == 0) {
        /* Fluid pump motor - continuous rotation, no position limits */
        mp->Kt = 0.04f;    mp->Ke = 0.04f;
        mp->Rm = 0.8f;     mp->Lm = 0.001f;
        mp->Jm = 0.00015f; mp->Jl = 0.0008f;
        mp->gear_ratio = 1.0f;  /* Direct drive */
        mp->Bf = 0.0001f;  mp->Tf = 0.008f;  mp->Ts = 0.012f;
        mp->stiction_velocity = 0.1f;
        mp->pos_min_rad = -1e6f;  mp->pos_max_rad = 1e6f;  /* No limits */
        mp->end_stop_stiffness = 0.0f;
        mp->thermal_resistance = 6.0f;  mp->thermal_capacitance = 40.0f;
    }
    else {
        EMU_LOG("HBridge[%d] unknown preset: %s", bridge, preset);
        return -1;
    }

    EMU_LOG("HBridge[%d] preset '%s' applied", bridge, preset);
    return 0;
}

/**
 * @brief Apply external load torque to motor
 */
int PMU_Emu_HBridge_SetLoadTorque(uint8_t bridge, float torque_Nm)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS) {
        return -1;
    }

    emulator.hbridge[bridge].motor_state.torque_load = torque_Nm;
    EMU_LOG("HBridge[%d] load torque = %.3f Nm", bridge, torque_Nm);
    return 0;
}

/**
 * @brief Get motor dynamic state
 */
const PMU_Emu_MotorState_t* PMU_Emu_HBridge_GetMotorState(uint8_t bridge)
{
    if (bridge >= PMU_EMU_HBRIDGE_CHANNELS) {
        return NULL;
    }
    return &emulator.hbridge[bridge].motor_state;
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
    /* Sets both L and R to same value (use individual setters for different values) */
    emulator.protection.board_temp_L_C = temp_C;
    emulator.protection.board_temp_R_C = temp_C;
    EMU_LOG("Protection: board temp L/R = %d C", temp_C);
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
 * WiFi Module Emulation
 * ============================================================================ */

const PMU_Emu_WiFi_t* PMU_Emu_WiFi_GetState(void)
{
    return &emulator.wifi;
}

void PMU_Emu_WiFi_SetEnabled(bool enabled)
{
    emulator.wifi.enabled = enabled;
    if (enabled) {
        if (emulator.wifi.state == PMU_EMU_WIFI_STATE_OFF) {
            emulator.wifi.state = PMU_EMU_WIFI_STATE_INIT;
        }
    } else {
        emulator.wifi.state = PMU_EMU_WIFI_STATE_OFF;
        emulator.wifi.uptime_s = 0;
    }
    EMU_LOG("WiFi: %s", enabled ? "enabled" : "disabled");
}

void PMU_Emu_WiFi_SetState(PMU_Emu_WiFi_State_t state)
{
    emulator.wifi.state = state;
    if (state == PMU_EMU_WIFI_STATE_CONNECTED || state == PMU_EMU_WIFI_STATE_AP_MODE) {
        emulator.wifi.enabled = true;
    }
}

void PMU_Emu_WiFi_SetConnection(const char* ssid, int8_t rssi, uint8_t channel)
{
    if (ssid) {
        strncpy(emulator.wifi.ssid, ssid, sizeof(emulator.wifi.ssid) - 1);
        emulator.wifi.ssid[sizeof(emulator.wifi.ssid) - 1] = '\0';
    }
    emulator.wifi.rssi = rssi;
    emulator.wifi.channel = channel;
    EMU_LOG("WiFi: connected to %s (ch%d, %ddBm)", emulator.wifi.ssid, channel, rssi);
}

void PMU_Emu_WiFi_SetIP(const char* ip)
{
    if (ip) {
        strncpy(emulator.wifi.ip_addr, ip, sizeof(emulator.wifi.ip_addr) - 1);
        emulator.wifi.ip_addr[sizeof(emulator.wifi.ip_addr) - 1] = '\0';
    }
}

void PMU_Emu_WiFi_AddTraffic(uint32_t tx_bytes, uint32_t rx_bytes)
{
    emulator.wifi.tx_bytes += tx_bytes;
    emulator.wifi.rx_bytes += rx_bytes;
}

/* ============================================================================
 * Bluetooth Module Emulation
 * ============================================================================ */

const PMU_Emu_Bluetooth_t* PMU_Emu_BT_GetState(void)
{
    return &emulator.bluetooth;
}

void PMU_Emu_BT_SetEnabled(bool enabled)
{
    emulator.bluetooth.enabled = enabled;
    if (enabled) {
        if (emulator.bluetooth.state == PMU_EMU_BT_STATE_OFF) {
            emulator.bluetooth.state = PMU_EMU_BT_STATE_ADVERTISING;
        }
    } else {
        emulator.bluetooth.state = PMU_EMU_BT_STATE_OFF;
        emulator.bluetooth.uptime_s = 0;
    }
    EMU_LOG("Bluetooth: %s", enabled ? "enabled" : "disabled");
}

void PMU_Emu_BT_SetState(PMU_Emu_BT_State_t state)
{
    emulator.bluetooth.state = state;
    if (state == PMU_EMU_BT_STATE_CONNECTED) {
        emulator.bluetooth.enabled = true;
    }
}

void PMU_Emu_BT_SetConnection(const char* peer_address, int8_t rssi)
{
    if (peer_address) {
        strncpy(emulator.bluetooth.peer_address, peer_address, sizeof(emulator.bluetooth.peer_address) - 1);
        emulator.bluetooth.peer_address[sizeof(emulator.bluetooth.peer_address) - 1] = '\0';
    }
    emulator.bluetooth.rssi = rssi;
    EMU_LOG("Bluetooth: connected to %s (%ddBm)", emulator.bluetooth.peer_address, rssi);
}

void PMU_Emu_BT_AddTraffic(uint32_t tx_bytes, uint32_t rx_bytes)
{
    emulator.bluetooth.tx_bytes += tx_bytes;
    emulator.bluetooth.rx_bytes += rx_bytes;
}

void PMU_Emu_WiFi_SetAPMode(bool ap_mode)
{
    emulator.wifi.ap_mode = ap_mode;
    if (emulator.wifi.enabled) {
        emulator.wifi.state = ap_mode ? PMU_EMU_WIFI_STATE_AP_MODE : PMU_EMU_WIFI_STATE_CONNECTED;
    }
    EMU_LOG("WiFi: AP mode %s", ap_mode ? "enabled" : "disabled");
}

void PMU_Emu_WiFi_Connect(const char* ssid)
{
    if (!emulator.wifi.enabled) {
        emulator.wifi.enabled = true;
    }
    emulator.wifi.state = PMU_EMU_WIFI_STATE_CONNECTING;
    if (ssid && ssid[0]) {
        strncpy(emulator.wifi.ssid, ssid, sizeof(emulator.wifi.ssid) - 1);
        emulator.wifi.ssid[sizeof(emulator.wifi.ssid) - 1] = '\0';
    }
    /* Simulate successful connection after a short delay (in next tick) */
    emulator.wifi.state = PMU_EMU_WIFI_STATE_CONNECTED;
    emulator.wifi.rssi = -55;
    emulator.wifi.channel = 6;
    snprintf(emulator.wifi.ip_addr, sizeof(emulator.wifi.ip_addr), "192.168.1.%d", 100 + (rand() % 50));
    EMU_LOG("WiFi: connected to '%s'", ssid ? ssid : "(default)");
}

void PMU_Emu_WiFi_Disconnect(void)
{
    emulator.wifi.state = PMU_EMU_WIFI_STATE_INIT;
    emulator.wifi.rssi = 0;
    emulator.wifi.clients_connected = 0;
    snprintf(emulator.wifi.ip_addr, sizeof(emulator.wifi.ip_addr), "0.0.0.0");
    EMU_LOG("WiFi: disconnected");
}

void PMU_Emu_BT_SetBLEMode(bool ble_mode)
{
    emulator.bluetooth.ble_mode = ble_mode;
    EMU_LOG("Bluetooth: BLE mode %s", ble_mode ? "enabled" : "disabled");
}

void PMU_Emu_BT_SetAdvertising(bool advertising)
{
    if (!emulator.bluetooth.enabled) {
        emulator.bluetooth.enabled = true;
        emulator.bluetooth.state = PMU_EMU_BT_STATE_INIT;
    }
    if (advertising) {
        emulator.bluetooth.state = PMU_EMU_BT_STATE_ADVERTISING;
    } else if (emulator.bluetooth.state == PMU_EMU_BT_STATE_ADVERTISING) {
        emulator.bluetooth.state = PMU_EMU_BT_STATE_INIT;
    }
    EMU_LOG("Bluetooth: advertising %s", advertising ? "started" : "stopped");
}

/* ============================================================================
 * LIN Bus Emulation
 * ============================================================================ */

const PMU_Emu_LIN_Bus_t* PMU_Emu_LIN_GetBus(uint8_t bus)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT) {
        return NULL;
    }
    return &emulator.lin[bus];
}

void PMU_Emu_LIN_SetEnabled(uint8_t bus, bool enabled)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT) return;

    emulator.lin[bus].enabled = enabled;
    emulator.lin[bus].state = enabled ? PMU_EMU_LIN_STATE_IDLE : PMU_EMU_LIN_STATE_OFF;
    EMU_LOG("LIN%d: %s", bus, enabled ? "enabled" : "disabled");
}

void PMU_Emu_LIN_SetMasterMode(uint8_t bus, bool is_master)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT) return;

    emulator.lin[bus].is_master = is_master;
    EMU_LOG("LIN%d: %s mode", bus, is_master ? "master" : "slave");
}

void PMU_Emu_LIN_InjectFrame(uint8_t bus, uint8_t frame_id,
                             const uint8_t* data, uint8_t length)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT || !data || length > 8) return;
    if (frame_id > 63) return;

    /* Store in frame data buffer */
    if (frame_id < PMU_EMU_LIN_FRAME_COUNT) {
        memcpy(emulator.lin[bus].frame_data[frame_id], data, length);
    }

    /* Add to RX queue */
    PMU_Emu_LIN_Bus_t* lin = &emulator.lin[bus];
    if (lin->rx_queue_count < PMU_EMU_LIN_RX_QUEUE_SIZE) {
        uint8_t idx = (lin->rx_queue_head + lin->rx_queue_count) % PMU_EMU_LIN_RX_QUEUE_SIZE;
        lin->rx_queue[idx].frame_id = frame_id;
        memcpy(lin->rx_queue[idx].data, data, length);
        lin->rx_queue[idx].length = length;
        lin->rx_queue[idx].timestamp = emulator.tick_ms;
        lin->rx_queue_count++;
    }

    lin->frames_rx++;
    lin->state = PMU_EMU_LIN_STATE_ACTIVE;

    /* Forward to LIN protocol handler */
    PMU_LIN_HandleRxFrame(bus, frame_id, data, length);

    EMU_LOG("LIN%d: injected frame 0x%02X (%d bytes)", bus, frame_id, length);
}

void PMU_Emu_LIN_Transmit(uint8_t bus, uint8_t frame_id,
                          const uint8_t* data, uint8_t length)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT || !data || length > 8) return;
    if (frame_id > 63) return;

    /* Store in frame data buffer */
    if (frame_id < PMU_EMU_LIN_FRAME_COUNT) {
        memcpy(emulator.lin[bus].frame_data[frame_id], data, length);
    }

    emulator.lin[bus].frames_tx++;
    emulator.lin[bus].state = PMU_EMU_LIN_STATE_ACTIVE;

    EMU_LOG("LIN%d: TX frame 0x%02X (%d bytes)", bus, frame_id, length);
}

void PMU_Emu_LIN_RequestFrame(uint8_t bus, uint8_t frame_id)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT) return;
    if (frame_id > 63) return;

    /* In emulator, immediately respond with stored frame data */
    if (frame_id < PMU_EMU_LIN_FRAME_COUNT) {
        PMU_LIN_HandleRxFrame(bus, frame_id,
                              emulator.lin[bus].frame_data[frame_id], 8);
    }

    EMU_LOG("LIN%d: request frame 0x%02X", bus, frame_id);
}

void PMU_Emu_LIN_HandleRx(uint8_t bus, uint8_t frame_id,
                          const uint8_t* data, uint8_t length)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT) return;

    /* Store frame data */
    if (frame_id < PMU_EMU_LIN_FRAME_COUNT) {
        memcpy(emulator.lin[bus].frame_data[frame_id], data, length);
    }

    emulator.lin[bus].frames_rx++;
}

void PMU_Emu_LIN_SendWakeup(uint8_t bus)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT) return;

    emulator.lin[bus].state = PMU_EMU_LIN_STATE_IDLE;
    EMU_LOG("LIN%d: wakeup sent", bus);
}

void PMU_Emu_LIN_SetSleep(uint8_t bus)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT) return;

    emulator.lin[bus].state = PMU_EMU_LIN_STATE_SLEEP;
    EMU_LOG("LIN%d: sleep mode", bus);
}

int PMU_Emu_LIN_GetFrameData(uint8_t bus, uint8_t frame_id, uint8_t* data)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT || !data) return -1;
    if (frame_id >= PMU_EMU_LIN_FRAME_COUNT) return -1;

    memcpy(data, emulator.lin[bus].frame_data[frame_id], 8);
    return 0;
}

void PMU_Emu_LIN_SetFrameData(uint8_t bus, uint8_t frame_id, const uint8_t* data)
{
    if (bus >= PMU_EMU_LIN_BUS_COUNT || !data) return;
    if (frame_id >= PMU_EMU_LIN_FRAME_COUNT) return;

    memcpy(emulator.lin[bus].frame_data[frame_id], data, 8);
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
    fprintf(f, "  \"temperature_C\": %d\n", emulator.protection.board_temp_L_C);

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
    printf("Board Temp L: %d C\n", emulator.protection.board_temp_L_C);
    printf("Board Temp R: %d C\n", emulator.protection.board_temp_R_C);
    printf("MCU Temp: %d C\n", emulator.protection.mcu_temp_C);
    printf("5V Output: %d mV\n", emulator.protection.output_5v_mV);
    printf("3.3V Output: %d mV\n", emulator.protection.output_3v3_mV);
    printf("Total Current: %u mA\n", emulator.protection.total_current_mA);
    printf("Faults: 0x%04X\n", emulator.protection.fault_flags);
    printf("Status: 0x%04X\n", emulator.protection.system_status);

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
    int16_t max_temp = emulator.protection.board_temp_L_C;
    if (emulator.protection.board_temp_R_C > max_temp) {
        max_temp = emulator.protection.board_temp_R_C;
    }

    snprintf(buffer, size,
             "EMU: up=%us, V=%dmV, T=%dC, I=%umA",
             emulator.uptime_seconds,
             emulator.protection.battery_voltage_mV,
             max_temp,
             emulator.protection.total_current_mA);
}

/* ============================================================================
 * Private Functions - Subsystem Updates
 * ============================================================================ */

/* External ADC DMA buffer from pmu_adc.c */
extern uint16_t adc_dma_buffer[20];

static void Emu_UpdateADC(uint32_t delta_ms)
{
    (void)delta_ms;

    /* Update ADC DMA buffer with emulated values
     * The firmware reads from this buffer via ADC_ReadChannel()
     * Buffer values are 12-bit (0-4095) */
    for (int i = 0; i < 20 && i < PMU_EMU_ADC_CHANNELS; i++) {
        uint16_t raw = emulator.adc[i].raw_value;  /* 10-bit (0-1023) */

        /* Add noise if enabled */
        if (emulator.adc[i].use_noise && emulator.adc[i].noise_amplitude > 0) {
            raw = Emu_AddNoise(raw, emulator.adc[i].noise_amplitude);
        }

        /* Convert 10-bit to 12-bit for buffer */
        adc_dma_buffer[i] = raw << 2;
    }
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
    uint32_t total_current = 0;
    const float AMBIENT_TEMP = 25.0f;
    const float THERMAL_RESISTANCE = 5.0f;  /* K/W - junction to ambient */
    const float THERMAL_MASS = 0.5f;        /* J/K - thermal capacitance */
    const uint16_t INRUSH_DURATION_MS = 50; /* Inrush current duration */

    for (int i = 0; i < PMU_EMU_PROFET_CHANNELS; i++) {
        PMU_Emu_PROFET_Channel_t* ch = &emulator.profet[i];

        /* Sync state from firmware PROFET module */
        PMU_PROFET_Channel_t* fw_profet = PMU_PROFET_GetChannelData(i);
        if (fw_profet && ch->fault_flags == 0) {
            ch->state = fw_profet->state;
            ch->pwm_duty = fw_profet->pwm_duty;
        }

        /* Handle fault injection */
        if (ch->fault_flags != 0) {
            uint8_t ff = ch->fault_flags;
            if (ff & 0x04) {
                ch->state = 4;  /* SC - Short Circuit */
            } else if (ff & 0x02) {
                ch->state = 3;  /* OT - Over Temperature */
            } else if (ff & 0x08) {
                ch->state = 5;  /* OL - Open Load */
            } else {
                ch->state = 2;  /* OC - Over Current */
            }
            ch->current_mA = 0;
            ch->inrush_remaining_ms = 0;
            ch->soft_start_elapsed = 0;
            if (fw_profet) {
                fw_profet->fault_flags = ch->fault_flags;
            }
            ch->prev_state = ch->state;
            continue;
        }

        /* Detect state change (OFF->ON or OFF->PWM) for inrush */
        bool just_turned_on = (ch->prev_state == 0 && (ch->state == 1 || ch->state == 6));
        if (just_turned_on) {
            ch->inrush_remaining_ms = INRUSH_DURATION_MS;
            ch->soft_start_elapsed = 0;
        }
        ch->prev_state = ch->state;

        /* Calculate base current */
        float voltage = emulator.protection.battery_voltage_mV / 1000.0f;
        float resistance = ch->load_resistance_ohm;
        if (resistance <= 0.1f) resistance = 12.0f;

        float duty_factor = 0.0f;
        if (ch->state == 1) {       /* ON */
            duty_factor = 1.0f;
        } else if (ch->state == 6) { /* PWM */
            duty_factor = ch->pwm_duty / 1000.0f;
        }

        /* Apply soft-start ramp if configured */
        if (ch->soft_start_ms > 0 && ch->soft_start_elapsed < ch->soft_start_ms) {
            float ramp = (float)ch->soft_start_elapsed / (float)ch->soft_start_ms;
            duty_factor *= ramp;
            ch->soft_start_elapsed += delta_ms;
        }

        /* Calculate steady-state current */
        float current_A = (voltage / resistance) * duty_factor;

        /* Apply inrush current multiplier (exponential decay) */
        if (ch->inrush_remaining_ms > 0) {
            float inrush_factor = 1.0f + (ch->inrush_multiplier - 1.0f) *
                                  ((float)ch->inrush_remaining_ms / INRUSH_DURATION_MS);
            current_A *= inrush_factor;
            ch->inrush_remaining_ms = (delta_ms >= ch->inrush_remaining_ms) ?
                                      0 : ch->inrush_remaining_ms - delta_ms;
        }

        /* Cap current at reasonable maximum (20A) */
        if (current_A > 20.0f) current_A = 20.0f;
        ch->current_mA = (uint16_t)(current_A * 1000.0f);

        /* Update ADC DMA buffer with simulated current
         * ADC = (current_mA × 4095) / (kILIS × 3.3)
         * kILIS = 4700, so divisor = 15510 */
        uint32_t adc_val = (ch->current_mA * 4095UL) / 15510;
        if (adc_val > 4095) adc_val = 4095;
        profet_current_adc_buffer[i] = (uint16_t)adc_val;

        /* Realistic temperature simulation using thermal model:
         * P = I²R (power dissipated in PROFET ~0.1 * load power)
         * dT/dt = (P - (T-Ta)/Rth) / Cth */
        float power_W = current_A * current_A * 0.05f;  /* ~5% of load power in PROFET */
        float temp_diff = ch->temperature_C - AMBIENT_TEMP;
        float heat_loss_W = temp_diff / THERMAL_RESISTANCE;
        float dT = (power_W - heat_loss_W) * (delta_ms / 1000.0f) / THERMAL_MASS;

        ch->thermal_energy_J += power_W * (delta_ms / 1000.0f);
        ch->temperature_C += (int16_t)(dT * 10);  /* Scale for int16 */

        /* Clamp temperature */
        if (ch->temperature_C < (int16_t)AMBIENT_TEMP) ch->temperature_C = (int16_t)AMBIENT_TEMP;
        if (ch->temperature_C > 150) ch->temperature_C = 150;

        /* Update status ADC buffer with temperature
         * V_ST = 1.0V + (Temp - 25) × 0.006V */
        float v_st = 1.0f + (ch->temperature_C - 25) * 0.006f;
        if (v_st < 0) v_st = 0;
        if (v_st > 3.3f) v_st = 3.3f;
        profet_status_adc_buffer[i] = (uint16_t)((v_st * 4095.0f) / 3.3f);

        /* Sync simulated current back to firmware */
        if (fw_profet) {
            fw_profet->current_mA = ch->current_mA;
            fw_profet->temperature_C = ch->temperature_C;
        }

        /* Auto-fault detection if enabled */
        if (emulator.protection.enable_auto_faults) {
            if (ch->temperature_C > 140) {
                ch->fault_flags |= 0x02;  /* OT */
            }
            if (ch->current_mA > 15000) {
                ch->fault_flags |= 0x01;  /* OC */
            }
        }

        total_current += ch->current_mA;
    }

    emulator.protection.total_current_mA = total_current;
}

/**
 * @brief Sign function for friction calculation
 */
static float Emu_Signf(float x)
{
    if (x > 0.0f) return 1.0f;
    if (x < 0.0f) return -1.0f;
    return 0.0f;
}

/**
 * @brief Update H-Bridge with realistic motor physics simulation
 *
 * Physics model:
 * 1. Electrical: V = i*R + Ke*ω (voltage equation)
 *    Motor current: i = (V - Ke*ω) / R
 * 2. Mechanical: J*dω/dt = Kt*i - Bf*ω - Tf*sign(ω) - τ_load - τ_endstop
 * 3. Position: dθ/dt = ω
 * 4. Thermal: C*dT/dt = i²*R - (T-Ta)/Rth
 */
static void Emu_UpdateHBridge(uint32_t delta_ms)
{
    const float AMBIENT_TEMP = 25.0f;
    const float dt = delta_ms / 1000.0f;  /* Time step in seconds */

    if (dt <= 0.0f) return;

    for (int i = 0; i < PMU_EMU_HBRIDGE_CHANNELS; i++) {
        PMU_Emu_HBridge_Channel_t* hb = &emulator.hbridge[i];
        PMU_Emu_MotorParams_t* mp = &hb->motor_params;
        PMU_Emu_MotorState_t* ms = &hb->motor_state;

        /* Handle fault state */
        if (hb->fault_flags != 0) {
            hb->state = 4;  /* FAULT */
            ms->voltage_V = 0.0f;
            ms->current_A = 0.0f;
            /* Let motor coast to stop with friction */
        }

        /* Calculate supply voltage based on mode and duty cycle */
        float Vbus = emulator.protection.battery_voltage_mV / 1000.0f;
        float duty = hb->duty_cycle / 1000.0f;  /* 0.0 to 1.0 */

        switch (hb->mode) {
            case 0:  /* COAST - both switches open, motor coasts */
                ms->voltage_V = 0.0f;
                /* In coast, current decays through freewheeling diodes */
                ms->current_A *= 0.9f;  /* Exponential decay */
                break;

            case 1:  /* FORWARD */
                ms->voltage_V = Vbus * duty;
                hb->state = 1;  /* RUNNING */
                break;

            case 2:  /* REVERSE */
                ms->voltage_V = -Vbus * duty;
                hb->state = 1;  /* RUNNING */
                break;

            case 3:  /* BRAKE - both switches closed, motor brakes */
                ms->voltage_V = 0.0f;
                /* In brake mode, motor acts as generator into short circuit */
                break;

            default:
                ms->voltage_V = 0.0f;
                break;
        }

        /* =====================================================
         * ELECTRICAL MODEL: V = i*R + Ke*ω  =>  i = (V - Ke*ω) / R
         * ===================================================== */

        /* Calculate back-EMF (voltage induced by rotating motor) */
        ms->back_emf_V = mp->Ke * ms->omega;

        /* Calculate motor current */
        if (hb->mode == 3) {
            /* BRAKE mode: motor is shorted, back-EMF drives current */
            ms->current_A = -ms->back_emf_V / mp->Rm;
        } else if (hb->mode == 0) {
            /* COAST: current decays (already handled above) */
        } else {
            /* FORWARD/REVERSE: normal motor operation */
            float net_voltage = ms->voltage_V - ms->back_emf_V;
            ms->current_A = net_voltage / mp->Rm;
        }

        /* Clamp current to realistic limits */
        const float MAX_CURRENT = 30.0f;  /* 30A limit */
        if (ms->current_A > MAX_CURRENT) ms->current_A = MAX_CURRENT;
        if (ms->current_A < -MAX_CURRENT) ms->current_A = -MAX_CURRENT;

        /* =====================================================
         * MECHANICAL MODEL: J*dω/dt = τ_motor - τ_friction - τ_load
         * ===================================================== */

        /* Motor torque: τ = Kt * i */
        ms->torque_motor = mp->Kt * ms->current_A;

        /* Total inertia (motor + load referred to motor shaft) */
        float J_total = mp->Jm + mp->Jl / (mp->gear_ratio * mp->gear_ratio);
        if (J_total < 0.00001f) J_total = 0.00001f;

        /* Friction torque model (Coulomb + viscous + Stribeck) */
        float omega_abs = (ms->omega > 0) ? ms->omega : -ms->omega;
        if (omega_abs < mp->stiction_velocity) {
            /* Stiction regime */
            float stiction_factor = 1.0f + (mp->Ts - mp->Tf) *
                                    (1.0f - omega_abs / mp->stiction_velocity);
            ms->torque_friction = stiction_factor * mp->Tf * Emu_Signf(ms->omega) +
                                  mp->Bf * ms->omega;
        } else {
            /* Dynamic friction: Coulomb + viscous */
            ms->torque_friction = mp->Tf * Emu_Signf(ms->omega) + mp->Bf * ms->omega;
        }

        /* End-stop torque (elastic bounce at limits) */
        float torque_endstop = 0.0f;
        ms->at_end_stop = 0;

        if (ms->theta < mp->pos_min_rad) {
            float penetration = mp->pos_min_rad - ms->theta;
            torque_endstop = mp->end_stop_stiffness * penetration;
            ms->at_end_stop = 1;
            if (ms->omega < 0) torque_endstop += -ms->omega * 0.1f;
        } else if (ms->theta > mp->pos_max_rad) {
            float penetration = ms->theta - mp->pos_max_rad;
            torque_endstop = -mp->end_stop_stiffness * penetration;
            ms->at_end_stop = 2;
            if (ms->omega > 0) torque_endstop += -ms->omega * 0.1f;
        }

        /* Net torque */
        float torque_net = ms->torque_motor - ms->torque_friction -
                           ms->torque_load + torque_endstop;

        /* Handle stall condition */
        if (omega_abs < 0.01f && (hb->mode == 1 || hb->mode == 2) && hb->duty_cycle > 100) {
            float torque_abs = (ms->torque_motor > 0) ? ms->torque_motor : -ms->torque_motor;
            if (torque_abs < mp->Ts) {
                torque_net = 0.0f;
                ms->stall_time_ms += delta_ms;
                if (ms->stall_time_ms > 500) ms->stalled = 1;
            } else {
                ms->stall_time_ms = 0;
                ms->stalled = 0;
            }
        } else {
            ms->stall_time_ms = 0;
            ms->stalled = 0;
        }

        /* Angular acceleration: α = τ / J */
        ms->acceleration = torque_net / J_total;
        ms->omega_prev = ms->omega;

        /* Integrate velocity: ω = ω + α * dt */
        ms->omega += ms->acceleration * dt;

        /* Additional damping in BRAKE mode */
        if (hb->mode == 3) {
            ms->omega *= 0.95f;
        }

        /* Integrate position: θ = θ + ω * dt */
        ms->theta += ms->omega * dt;

        /* Clamp position to end stops */
        if (ms->theta < mp->pos_min_rad - 0.1f) {
            ms->theta = mp->pos_min_rad;
            ms->omega = 0.0f;
        }
        if (ms->theta > mp->pos_max_rad + 0.1f) {
            ms->theta = mp->pos_max_rad;
            ms->omega = 0.0f;
        }

        /* =====================================================
         * THERMAL MODEL: C*dT/dt = P - (T-Ta)/Rth
         * ===================================================== */

        ms->power_dissipated_W = ms->current_A * ms->current_A * mp->Rm;
        float heat_loss = (ms->temperature_C - AMBIENT_TEMP) / mp->thermal_resistance;
        float dT = (ms->power_dissipated_W - heat_loss) * dt / mp->thermal_capacitance;
        ms->temperature_C += dT;

        if (ms->temperature_C < AMBIENT_TEMP) ms->temperature_C = AMBIENT_TEMP;
        if (ms->temperature_C > 150.0f) ms->temperature_C = 150.0f;

        /* =====================================================
         * UPDATE OUTPUT VALUES
         * ===================================================== */

        /* Current in mA for display */
        float current_abs = (ms->current_A > 0) ? ms->current_A : -ms->current_A;
        hb->current_mA = (uint16_t)(current_abs * 1000.0f);

        /* Position in 0-1000 range */
        float pos_range = mp->pos_max_rad - mp->pos_min_rad;
        if (pos_range < 0.001f) pos_range = 3.14159f;
        float pos_normalized = (ms->theta - mp->pos_min_rad) / pos_range;
        if (pos_normalized < 0.0f) pos_normalized = 0.0f;
        if (pos_normalized > 1.0f) pos_normalized = 1.0f;
        hb->position = (uint16_t)(pos_normalized * 1000.0f);

        /* Legacy motor_speed (for backward compatibility) */
        hb->motor_speed = omega_abs * 57.2958f;  /* rad/s to deg/s */

        /* Update ADC buffers */
        hbridge_position_adc_buffer[i] = (uint16_t)(pos_normalized * 4095.0f);
        uint16_t current_adc = (uint16_t)((current_abs / 30.0f) * 4095.0f);
        if (current_adc > 4095) current_adc = 4095;
        hbridge_current_adc_buffer[i] = current_adc;

        /* Update state based on motion */
        if (hb->mode == 0 || hb->mode == 3) {
            hb->state = 0;  /* IDLE */
        } else if (hb->fault_flags != 0) {
            hb->state = 4;  /* FAULT */
        } else if (omega_abs < 0.01f) {
            int16_t pos_error = (int16_t)hb->position - (int16_t)hb->target_position;
            if (pos_error < 0) pos_error = -pos_error;
            hb->state = (pos_error < 20) ? 3 : 1;  /* PARKED or RUNNING */
        } else {
            hb->state = 1;  /* RUNNING */
        }

        /* Auto-fault detection */
        if (emulator.protection.enable_auto_faults) {
            if (ms->temperature_C > 125.0f) hb->fault_flags |= 0x04;
            if (ms->stall_time_ms > 2000) hb->fault_flags |= 0x08;
            if (current_abs > 25.0f) hb->fault_flags |= 0x01;
        }
    }
}

static void Emu_UpdateProtection(uint32_t delta_ms)
{
    (void)delta_ms;

    /* Get max board temperature */
    int16_t max_board_temp = emulator.protection.board_temp_L_C;
    if (emulator.protection.board_temp_R_C > max_board_temp) {
        max_board_temp = emulator.protection.board_temp_R_C;
    }

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

    /* Check temperature limits using max of L/R */
    if (max_board_temp > 100) {
        emulator.protection.fault_flags |= 0x0010;  /* OVERTEMP_WARNING */
    }
    if (max_board_temp > 125) {
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

HAL_StatusTypeDef HAL_ADC_PollForConversion(ADC_HandleTypeDef* hadc, uint32_t Timeout)
{
    (void)hadc;
    (void)Timeout;
    /* Emulator ADC is always ready */
    return HAL_OK;
}

uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef* hadc)
{
    /*
     * Return appropriate emulator values based on ADC handle:
     * - ADC1: Battery voltage (used by hadc_vbat in pmu_protection.c)
     * - ADC3: MCU temperature sensor (used by hadc_temp in pmu_protection.c)
     *
     * Battery voltage conversion (reverse of Protection_ReadVbatADC formula):
     *   voltage_mV = (adc * 3300 * 6670) / (4096 * 1000)
     *   adc = (voltage_mV * 4096 * 1000) / (3300 * 6670)
     *   adc = (voltage_mV * 4096) / 22011
     *
     * MCU temperature conversion (reverse of Protection_ReadMCUTemp formula):
     *   temp_C = (760000 - voltage_uV) / 2500 + 25
     *   voltage_uV = 760000 - (temp_C - 25) * 2500
     *   adc = (voltage_uV * 4096) / 3300000
     */

    if (hadc->Instance == ADC1) {
        /* Battery voltage - convert from mV to ADC value */
        uint32_t voltage_mV = emulator.protection.battery_voltage_mV;
        uint32_t adc_value = (voltage_mV * 4096) / 22011;
        if (adc_value > 4095) adc_value = 4095;
        return adc_value;
    }
    else if (hadc->Instance == ADC3) {
        /* MCU temperature sensor - convert from °C to ADC value */
        int16_t temp_C = emulator.protection.mcu_temp_C;
        int32_t voltage_uV = 760000 - (temp_C - 25) * 2500;
        if (voltage_uV < 0) voltage_uV = 0;
        uint32_t adc_value = (voltage_uV * 4096) / 3300000;
        if (adc_value > 4095) adc_value = 4095;
        return adc_value;
    }

    /* Default - return generic ADC value */
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

HAL_StatusTypeDef HAL_FDCAN_ConfigGlobalFilter(FDCAN_HandleTypeDef* hfdcan, uint32_t NonMatchingStd, uint32_t NonMatchingExt, uint32_t RejectRemoteStd, uint32_t RejectRemoteExt)
{
    (void)hfdcan;
    (void)NonMatchingStd;
    (void)NonMatchingExt;
    (void)RejectRemoteStd;
    (void)RejectRemoteExt;
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

/* Protection Temperature Functions - Override weak implementations in pmu_protection.c */

/**
 * @brief Read board temperature sensor Left (emulator override)
 * @retval Temperature in °C from emulator state
 */
int16_t Protection_ReadBoardTempL(void)
{
    return emulator.protection.board_temp_L_C;
}

/**
 * @brief Read board temperature sensor Right (emulator override)
 * @retval Temperature in °C from emulator state
 */
int16_t Protection_ReadBoardTempR(void)
{
    return emulator.protection.board_temp_R_C;
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

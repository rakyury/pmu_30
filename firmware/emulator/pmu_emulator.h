/**
 ******************************************************************************
 * @file           : pmu_emulator.h
 * @brief          : PMU-30 Hardware Emulator API
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides a complete hardware emulation layer for PMU-30,
 * allowing firmware to run on a PC without real hardware.
 *
 * Features:
 * - ADC input emulation with programmable values
 * - CAN bus emulation with frame injection
 * - PROFET output state tracking
 * - H-Bridge motor simulation
 * - Protection system emulation with fault injection
 * - JSON scenario loading for automated testing
 * - Real-time data injection API
 *
 ******************************************************************************
 */

#ifndef PMU_EMULATOR_H
#define PMU_EMULATOR_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Emulator callback type for output state changes
 */
typedef void (*PMU_Emu_OutputCallback_t)(uint8_t channel, uint16_t value);

/**
 * @brief Emulator callback for CAN TX messages
 */
typedef void (*PMU_Emu_CanTxCallback_t)(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len);

/**
 * @brief ADC channel emulation data
 */
typedef struct {
    uint16_t raw_value;         /**< Raw ADC value (0-1023) */
    float voltage_v;            /**< Voltage in volts (auto-calculated) */
    uint32_t frequency_hz;      /**< Frequency for freq inputs */
    bool enabled;               /**< Channel enabled */
    bool use_noise;             /**< Add random noise */
    uint16_t noise_amplitude;   /**< Noise amplitude (0-100) */
} PMU_Emu_ADC_Channel_t;

/**
 * @brief CAN message injection structure
 */
typedef struct {
    uint8_t bus;                /**< CAN bus (0-3) */
    uint32_t id;                /**< CAN ID */
    uint8_t data[64];           /**< Data bytes (up to 64 for CAN FD) */
    uint8_t dlc;                /**< Data length */
    bool is_extended;           /**< Extended ID flag */
    bool is_fd;                 /**< CAN FD flag */
    uint32_t interval_ms;       /**< Auto-repeat interval (0 = one-shot) */
    uint32_t last_tx_tick;      /**< Last TX timestamp */
    bool active;                /**< Message active flag */
} PMU_Emu_CAN_Message_t;

/**
 * @brief PROFET output emulation state
 */
typedef struct {
    uint8_t state;              /**< 0=OFF, 1=ON, 2=PWM, 3=FAULT */
    uint16_t pwm_duty;          /**< PWM duty (0-1000) */
    uint16_t current_mA;        /**< Simulated current */
    int16_t temperature_C;      /**< Simulated temperature */
    uint8_t fault_flags;        /**< Fault flags */
    float load_resistance_ohm;  /**< Load resistance for current calc */
} PMU_Emu_PROFET_Channel_t;

/**
 * @brief H-Bridge output emulation state
 */
typedef struct {
    uint8_t mode;               /**< Operating mode */
    uint8_t state;              /**< State (IDLE, RUNNING, etc.) */
    uint16_t duty_cycle;        /**< PWM duty (0-1000) */
    uint16_t current_mA;        /**< Simulated current */
    uint16_t position;          /**< Position feedback (0-1000) */
    uint16_t target_position;   /**< Target position */
    float motor_speed;          /**< Motor speed (units/sec) */
    float load_inertia;         /**< Load inertia factor */
    uint8_t fault_flags;        /**< Fault flags */
} PMU_Emu_HBridge_Channel_t;

/**
 * @brief Protection system emulation state
 */
typedef struct {
    uint16_t battery_voltage_mV;    /**< Battery voltage */
    int16_t board_temp_C;           /**< Board temperature */
    int16_t mcu_temp_C;             /**< MCU temperature */
    uint32_t total_current_mA;      /**< Total current */
    uint16_t fault_flags;           /**< Injected fault flags */
    bool enable_auto_faults;        /**< Auto-generate faults on limits */
} PMU_Emu_Protection_t;

/**
 * @brief Complete emulator state
 */
typedef struct {
    /* ADC Channels */
    PMU_Emu_ADC_Channel_t adc[20];

    /* CAN Bus */
    PMU_Emu_CAN_Message_t can_rx_queue[64];
    uint8_t can_rx_count;
    bool can_bus_online[4];

    /* PROFET Outputs */
    PMU_Emu_PROFET_Channel_t profet[30];

    /* H-Bridge Outputs */
    PMU_Emu_HBridge_Channel_t hbridge[4];

    /* Protection System */
    PMU_Emu_Protection_t protection;

    /* Timing */
    uint32_t tick_ms;
    uint32_t uptime_seconds;
    float time_scale;           /**< Time scaling factor (1.0 = real-time) */

    /* Callbacks */
    PMU_Emu_OutputCallback_t on_profet_change;
    PMU_Emu_OutputCallback_t on_hbridge_change;
    PMU_Emu_CanTxCallback_t on_can_tx;

    /* State */
    bool running;
    bool paused;
} PMU_Emulator_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_EMU_ADC_CHANNELS        20
#define PMU_EMU_PROFET_CHANNELS     30
#define PMU_EMU_HBRIDGE_CHANNELS    4
#define PMU_EMU_CAN_BUSES           4
#define PMU_EMU_CAN_RX_QUEUE_SIZE   64

/* Default values */
#define PMU_EMU_DEFAULT_VOLTAGE_MV  12000
#define PMU_EMU_DEFAULT_TEMP_C      25
#define PMU_EMU_VREF_MV             3300

/* Exported macro ------------------------------------------------------------*/

/* Convert voltage to ADC value */
#define PMU_EMU_V_TO_ADC(v)     ((uint16_t)(((v) * 1024.0f) / 3.3f))
#define PMU_EMU_MV_TO_ADC(mv)   ((uint16_t)(((mv) * 1024) / 3300))

/* Exported functions --------------------------------------------------------*/

/* ============================================================================
 * Initialization & Control
 * ============================================================================ */

/**
 * @brief Initialize the emulator
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_Init(void);

/**
 * @brief Deinitialize the emulator and free resources
 */
void PMU_Emu_Deinit(void);

/**
 * @brief Reset emulator to default state
 */
void PMU_Emu_Reset(void);

/**
 * @brief Get emulator state structure
 * @retval Pointer to emulator state
 */
PMU_Emulator_t* PMU_Emu_GetState(void);

/**
 * @brief Run emulator tick (call at 1kHz for real-time)
 * @param delta_ms Time delta in milliseconds
 */
void PMU_Emu_Tick(uint32_t delta_ms);

/**
 * @brief Pause/resume emulator
 * @param paused Pause flag
 */
void PMU_Emu_SetPaused(bool paused);

/**
 * @brief Set time scale factor
 * @param scale Scale factor (1.0 = real-time, 2.0 = 2x speed)
 */
void PMU_Emu_SetTimeScale(float scale);

/* ============================================================================
 * ADC Input Injection
 * ============================================================================ */

/**
 * @brief Set ADC channel raw value
 * @param channel Channel number (0-19)
 * @param value Raw ADC value (0-1023)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_ADC_SetRaw(uint8_t channel, uint16_t value);

/**
 * @brief Set ADC channel voltage
 * @param channel Channel number (0-19)
 * @param voltage_v Voltage in volts (0.0-3.3V)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_ADC_SetVoltage(uint8_t channel, float voltage_v);

/**
 * @brief Set frequency input
 * @param channel Channel number (0-19)
 * @param frequency_hz Frequency in Hz
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_ADC_SetFrequency(uint8_t channel, uint32_t frequency_hz);

/**
 * @brief Enable/disable noise on ADC channel
 * @param channel Channel number (0-19)
 * @param enable Enable flag
 * @param amplitude Noise amplitude (0-100)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_ADC_SetNoise(uint8_t channel, bool enable, uint16_t amplitude);

/**
 * @brief Set all ADC channels at once
 * @param values Array of 20 raw values
 */
void PMU_Emu_ADC_SetAll(const uint16_t* values);

/* ============================================================================
 * CAN Bus Injection
 * ============================================================================ */

/**
 * @brief Inject a CAN message (simulates RX)
 * @param bus CAN bus (0-3)
 * @param id CAN ID
 * @param data Data bytes
 * @param len Data length
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_CAN_InjectMessage(uint8_t bus, uint32_t id, const uint8_t* data, uint8_t len);

/**
 * @brief Inject a CAN FD message
 * @param bus CAN bus (0-3)
 * @param id CAN ID
 * @param data Data bytes (up to 64)
 * @param len Data length
 * @param is_extended Extended ID flag
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_CAN_InjectFD(uint8_t bus, uint32_t id, const uint8_t* data, uint8_t len, bool is_extended);

/**
 * @brief Add periodic CAN message injection
 * @param bus CAN bus (0-3)
 * @param id CAN ID
 * @param data Data bytes
 * @param len Data length
 * @param interval_ms Repeat interval in ms
 * @retval Message index on success, -1 on error
 */
int PMU_Emu_CAN_AddPeriodicMessage(uint8_t bus, uint32_t id, const uint8_t* data, uint8_t len, uint32_t interval_ms);

/**
 * @brief Remove periodic CAN message
 * @param index Message index
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_CAN_RemovePeriodicMessage(int index);

/**
 * @brief Set CAN bus online/offline state
 * @param bus CAN bus (0-3)
 * @param online Online flag
 */
void PMU_Emu_CAN_SetBusOnline(uint8_t bus, bool online);

/**
 * @brief Simulate CAN bus error
 * @param bus CAN bus (0-3)
 * @param error_type Error type (0=none, 1=warning, 2=passive, 3=bus-off)
 */
void PMU_Emu_CAN_SimulateError(uint8_t bus, uint8_t error_type);

/**
 * @brief Register CAN TX callback (to capture outgoing messages)
 * @param callback Callback function
 */
void PMU_Emu_CAN_SetTxCallback(PMU_Emu_CanTxCallback_t callback);

/* ============================================================================
 * PROFET Output Monitoring
 * ============================================================================ */

/**
 * @brief Get PROFET channel state
 * @param channel Channel number (0-29)
 * @retval Pointer to channel state
 */
const PMU_Emu_PROFET_Channel_t* PMU_Emu_PROFET_GetState(uint8_t channel);

/**
 * @brief Set PROFET load resistance (for current simulation)
 * @param channel Channel number (0-29)
 * @param resistance_ohm Load resistance in ohms
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_PROFET_SetLoad(uint8_t channel, float resistance_ohm);

/**
 * @brief Inject PROFET fault
 * @param channel Channel number (0-29)
 * @param fault_flags Fault flags to set
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_PROFET_InjectFault(uint8_t channel, uint8_t fault_flags);

/**
 * @brief Clear PROFET fault
 * @param channel Channel number (0-29)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_PROFET_ClearFault(uint8_t channel);

/**
 * @brief Set PROFET change callback
 * @param callback Callback function
 */
void PMU_Emu_PROFET_SetCallback(PMU_Emu_OutputCallback_t callback);

/* ============================================================================
 * H-Bridge Output Monitoring
 * ============================================================================ */

/**
 * @brief Get H-Bridge channel state
 * @param bridge Bridge number (0-3)
 * @retval Pointer to channel state
 */
const PMU_Emu_HBridge_Channel_t* PMU_Emu_HBridge_GetState(uint8_t bridge);

/**
 * @brief Set H-Bridge motor parameters
 * @param bridge Bridge number (0-3)
 * @param speed Motor speed in units/sec
 * @param inertia Load inertia factor
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_SetMotorParams(uint8_t bridge, float speed, float inertia);

/**
 * @brief Set H-Bridge position feedback directly
 * @param bridge Bridge number (0-3)
 * @param position Position (0-1000)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_SetPosition(uint8_t bridge, uint16_t position);

/**
 * @brief Inject H-Bridge fault
 * @param bridge Bridge number (0-3)
 * @param fault_flags Fault flags to set
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_InjectFault(uint8_t bridge, uint8_t fault_flags);

/**
 * @brief Set H-Bridge change callback
 * @param callback Callback function
 */
void PMU_Emu_HBridge_SetCallback(PMU_Emu_OutputCallback_t callback);

/* ============================================================================
 * Protection System Emulation
 * ============================================================================ */

/**
 * @brief Set battery voltage
 * @param voltage_mV Voltage in millivolts
 */
void PMU_Emu_Protection_SetVoltage(uint16_t voltage_mV);

/**
 * @brief Set board temperature
 * @param temp_C Temperature in Celsius
 */
void PMU_Emu_Protection_SetTemperature(int16_t temp_C);

/**
 * @brief Set MCU temperature
 * @param temp_C Temperature in Celsius
 */
void PMU_Emu_Protection_SetMCUTemperature(int16_t temp_C);

/**
 * @brief Inject protection fault
 * @param fault_flags Fault flags to set
 */
void PMU_Emu_Protection_InjectFault(uint16_t fault_flags);

/**
 * @brief Clear protection faults
 */
void PMU_Emu_Protection_ClearFaults(void);

/**
 * @brief Enable auto-fault generation
 * @param enable Enable flag
 */
void PMU_Emu_Protection_SetAutoFaults(bool enable);

/* ============================================================================
 * Scenario Loading (JSON)
 * ============================================================================ */

/**
 * @brief Load scenario from JSON file
 * @param filename Path to JSON file
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_LoadScenario(const char* filename);

/**
 * @brief Load scenario from JSON string
 * @param json JSON string
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_LoadScenarioFromString(const char* json);

/**
 * @brief Save current state as scenario
 * @param filename Path to JSON file
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_SaveScenario(const char* filename);

/* ============================================================================
 * Logging & Debug
 * ============================================================================ */

/**
 * @brief Enable/disable emulator logging
 * @param enable Enable flag
 */
void PMU_Emu_SetLogging(bool enable);

/**
 * @brief Print emulator state summary
 */
void PMU_Emu_PrintState(void);

/**
 * @brief Get emulator statistics string
 * @param buffer Output buffer
 * @param size Buffer size
 */
void PMU_Emu_GetStatsString(char* buffer, size_t size);

#ifdef __cplusplus
}
#endif

#endif /* PMU_EMULATOR_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

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
 * @brief Digital input emulation data
 */
typedef struct {
    bool state;                 /**< Current input state (true=HIGH, false=LOW) */
    bool inverted;              /**< Invert logic (true=active low) */
    bool pull_up;               /**< Internal pull-up enabled */
    bool pull_down;             /**< Internal pull-down enabled */
    uint32_t debounce_ms;       /**< Debounce time in ms */
    uint32_t last_change_ms;    /**< Timestamp of last state change */
    bool debounced_state;       /**< State after debounce */
    bool edge_rising;           /**< Rising edge detected flag */
    bool edge_falling;          /**< Falling edge detected flag */
    uint32_t pulse_count;       /**< Rising edge counter */
    uint32_t frequency_hz;      /**< Measured frequency (if applicable) */
} PMU_Emu_Digital_Input_t;

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
 *
 * State values match ECUMaster convention:
 * 0=OFF, 1=ON, 2=OC, 3=OT, 4=SC, 5=OL, 6=PWM, 7=DIS
 */
typedef struct {
    uint8_t state;              /**< ECUMaster state (0=OFF,1=ON,2=OC,3=OT,4=SC,5=OL,6=PWM,7=DIS) */
    uint8_t prev_state;         /**< Previous state for edge detection */
    uint16_t pwm_duty;          /**< PWM duty (0-1000) */
    uint16_t current_mA;        /**< Simulated current */
    int16_t temperature_C;      /**< Simulated temperature */
    uint8_t fault_flags;        /**< Fault flags */
    float load_resistance_ohm;  /**< Load resistance for current calc */
    /* Realistic simulation fields */
    uint16_t inrush_remaining_ms;  /**< Inrush current period countdown */
    float inrush_multiplier;       /**< Inrush current multiplier (1.0-10.0) */
    float thermal_energy_J;        /**< Accumulated thermal energy for temp calc */
    uint16_t soft_start_ms;        /**< Soft-start ramp time */
    uint16_t soft_start_elapsed;   /**< Elapsed soft-start time */
} PMU_Emu_PROFET_Channel_t;

/**
 * @brief Motor physics parameters for realistic simulation
 */
typedef struct {
    /* Motor electrical parameters */
    float Kt;                   /**< Torque constant (Nm/A) - typical 0.01-0.1 for small motors */
    float Ke;                   /**< Back-EMF constant (V/(rad/s)) - usually equal to Kt */
    float Rm;                   /**< Motor resistance (Ohm) - winding resistance */
    float Lm;                   /**< Motor inductance (H) - winding inductance */

    /* Motor mechanical parameters */
    float Jm;                   /**< Motor rotor inertia (kg·m²) */
    float Jl;                   /**< Load inertia (kg·m²) */
    float gear_ratio;           /**< Gear ratio (output/input) - 1.0 for direct drive */

    /* Friction parameters */
    float Bf;                   /**< Viscous friction coefficient (Nm/(rad/s)) */
    float Tf;                   /**< Coulomb (static) friction torque (Nm) */
    float Ts;                   /**< Stiction torque (Nm) - breakaway torque */
    float stiction_velocity;    /**< Velocity threshold for stiction (rad/s) */

    /* Position limits */
    float pos_min_rad;          /**< Minimum position (rad) */
    float pos_max_rad;          /**< Maximum position (rad) */
    float end_stop_stiffness;   /**< End-stop spring constant (Nm/rad) */

    /* Thermal parameters */
    float thermal_resistance;   /**< Thermal resistance junction-ambient (K/W) */
    float thermal_capacitance;  /**< Thermal mass (J/K) */
} PMU_Emu_MotorParams_t;

/**
 * @brief Motor dynamic state for simulation
 */
typedef struct {
    /* Electrical state */
    float current_A;            /**< Actual motor current (A) */
    float voltage_V;            /**< Applied voltage (V) */
    float back_emf_V;           /**< Back-EMF voltage (V) */

    /* Mechanical state */
    float omega;                /**< Angular velocity (rad/s) */
    float omega_prev;           /**< Previous angular velocity for accel calc */
    float theta;                /**< Angular position (rad) */
    float torque_motor;         /**< Motor torque (Nm) */
    float torque_friction;      /**< Friction torque (Nm) */
    float torque_load;          /**< External load torque (Nm) */
    float acceleration;         /**< Angular acceleration (rad/s²) */

    /* Thermal state */
    float temperature_C;        /**< Motor temperature (°C) */
    float power_dissipated_W;   /**< Power dissipation (W) */

    /* State flags */
    uint8_t at_end_stop;        /**< At end stop (1=min, 2=max, 0=free) */
    uint8_t stalled;            /**< Motor stalled flag */
    uint32_t stall_time_ms;     /**< Time in stall condition */
} PMU_Emu_MotorState_t;

/**
 * @brief H-Bridge output emulation state
 */
typedef struct {
    uint8_t mode;               /**< Operating mode (0=COAST,1=FWD,2=REV,3=BRAKE) */
    uint8_t state;              /**< State (IDLE, RUNNING, PARKING, PARKED, FAULT) */
    uint16_t duty_cycle;        /**< PWM duty (0-1000) */
    uint16_t current_mA;        /**< Simulated current (mA) */
    uint16_t position;          /**< Position feedback (0-1000) */
    uint16_t target_position;   /**< Target position */
    float motor_speed;          /**< Motor speed (deprecated - use motor_state.omega) */
    float load_inertia;         /**< Load inertia factor (deprecated) */
    uint8_t fault_flags;        /**< Fault flags */

    /* Realistic motor simulation */
    PMU_Emu_MotorParams_t motor_params;  /**< Motor physics parameters */
    PMU_Emu_MotorState_t motor_state;    /**< Motor dynamic state */
} PMU_Emu_HBridge_Channel_t;

/**
 * @brief WiFi module emulation state
 */
typedef enum {
    PMU_EMU_WIFI_STATE_OFF = 0,
    PMU_EMU_WIFI_STATE_INIT,
    PMU_EMU_WIFI_STATE_SCANNING,
    PMU_EMU_WIFI_STATE_CONNECTING,
    PMU_EMU_WIFI_STATE_CONNECTED,
    PMU_EMU_WIFI_STATE_AP_MODE,
    PMU_EMU_WIFI_STATE_ERROR
} PMU_Emu_WiFi_State_t;

typedef struct {
    PMU_Emu_WiFi_State_t state;     /**< Current WiFi state */
    bool enabled;                    /**< WiFi enabled */
    bool ap_mode;                    /**< Access Point mode active */
    char ssid[33];                   /**< Connected/configured SSID */
    char ip_addr[16];                /**< IP address */
    int8_t rssi;                     /**< Signal strength dBm (-100 to 0) */
    uint8_t channel;                 /**< WiFi channel (1-13) */
    uint32_t tx_bytes;               /**< Transmitted bytes */
    uint32_t rx_bytes;               /**< Received bytes */
    uint8_t clients_connected;       /**< Number of clients (AP mode) */
    uint32_t uptime_s;               /**< Connection uptime seconds */
} PMU_Emu_WiFi_t;

/**
 * @brief Bluetooth module emulation state
 */
typedef enum {
    PMU_EMU_BT_STATE_OFF = 0,
    PMU_EMU_BT_STATE_INIT,
    PMU_EMU_BT_STATE_ADVERTISING,
    PMU_EMU_BT_STATE_CONNECTED,
    PMU_EMU_BT_STATE_PAIRING,
    PMU_EMU_BT_STATE_ERROR
} PMU_Emu_BT_State_t;

typedef struct {
    PMU_Emu_BT_State_t state;       /**< Current Bluetooth state */
    bool enabled;                    /**< Bluetooth enabled */
    bool ble_mode;                   /**< BLE mode (vs Classic) */
    char device_name[33];            /**< Device name */
    char peer_address[18];           /**< Connected peer MAC address */
    int8_t rssi;                     /**< Signal strength dBm */
    uint32_t tx_bytes;               /**< Transmitted bytes */
    uint32_t rx_bytes;               /**< Received bytes */
    bool authenticated;              /**< Peer authenticated */
    uint32_t uptime_s;               /**< Connection uptime seconds */
} PMU_Emu_Bluetooth_t;

/**
 * @brief LIN bus emulation state
 */
typedef enum {
    PMU_EMU_LIN_STATE_OFF = 0,
    PMU_EMU_LIN_STATE_IDLE,
    PMU_EMU_LIN_STATE_ACTIVE,
    PMU_EMU_LIN_STATE_SLEEP,
    PMU_EMU_LIN_STATE_ERROR
} PMU_Emu_LIN_State_t;

#define PMU_EMU_LIN_BUS_COUNT       2
#define PMU_EMU_LIN_FRAME_COUNT     32
#define PMU_EMU_LIN_RX_QUEUE_SIZE   16

typedef struct {
    uint8_t frame_id;               /**< LIN frame ID (0-63) */
    uint8_t data[8];                /**< Frame data */
    uint8_t length;                 /**< Data length */
    uint32_t timestamp;             /**< Reception timestamp */
} PMU_Emu_LIN_Frame_t;

typedef struct {
    PMU_Emu_LIN_State_t state;      /**< Bus state */
    bool enabled;                    /**< Bus enabled */
    bool is_master;                  /**< Master mode */
    uint32_t baudrate;               /**< Baud rate */
    uint32_t frames_rx;              /**< Received frames count */
    uint32_t frames_tx;              /**< Transmitted frames count */
    uint32_t errors;                 /**< Error count */
    PMU_Emu_LIN_Frame_t rx_queue[PMU_EMU_LIN_RX_QUEUE_SIZE];
    uint8_t rx_queue_head;           /**< RX queue head index */
    uint8_t rx_queue_count;          /**< RX queue count */
    uint8_t frame_data[PMU_EMU_LIN_FRAME_COUNT][8]; /**< Frame data buffers */
} PMU_Emu_LIN_Bus_t;

/**
 * @brief Protection system emulation state
 */
typedef struct {
    uint16_t battery_voltage_mV;    /**< Battery voltage */
    int16_t board_temp_L_C;         /**< Board temperature Left (ECUMaster: boardTemperatureL) */
    int16_t board_temp_R_C;         /**< Board temperature Right (ECUMaster: boardTemperatureR) */
    int16_t mcu_temp_C;             /**< MCU temperature */
    uint32_t total_current_mA;      /**< Total current */
    uint16_t fault_flags;           /**< Injected fault flags */
    bool enable_auto_faults;        /**< Auto-generate faults on limits */
    uint16_t output_5v_mV;          /**< 5V output voltage */
    uint16_t output_3v3_mV;         /**< 3.3V output voltage */
    uint16_t system_status;         /**< System status bits (ECUMaster: status) */
    uint8_t user_error;             /**< User error flag (ECUMaster: userError) */
    uint8_t is_turning_off;         /**< Shutdown in progress flag */
} PMU_Emu_Protection_t;

/**
 * @brief Complete emulator state
 */
typedef struct {
    /* ADC Channels */
    PMU_Emu_ADC_Channel_t adc[20];

    /* Digital Inputs */
    PMU_Emu_Digital_Input_t digital_inputs[16];

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

    /* Communication Modules */
    PMU_Emu_WiFi_t wifi;
    PMU_Emu_Bluetooth_t bluetooth;
    PMU_Emu_LIN_Bus_t lin[PMU_EMU_LIN_BUS_COUNT];

    /* Timing */
    uint32_t tick_ms;
    uint32_t uptime_seconds;
    uint32_t uptime_accum_ms;   /**< Millisecond accumulator for uptime */
    float time_scale;           /**< Time scaling factor (1.0 = real-time) */

    /* Flash Storage */
    int16_t flash_temp_C;       /**< Simulated flash temperature */
    uint16_t flash_file_count;  /**< Number of files in flash */

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
#define PMU_EMU_DIGITAL_INPUTS      16
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
 * Digital Input Emulation
 * ============================================================================ */

/**
 * @brief Set digital input state
 * @param channel Channel number (0-15)
 * @param state Input state (true=HIGH, false=LOW)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_DI_SetState(uint8_t channel, bool state);

/**
 * @brief Get digital input state (after debounce)
 * @param channel Channel number (0-15)
 * @retval Current debounced state, or false on error
 */
bool PMU_Emu_DI_GetState(uint8_t channel);

/**
 * @brief Set digital input configuration
 * @param channel Channel number (0-15)
 * @param inverted Invert logic
 * @param pull_up Enable pull-up
 * @param debounce_ms Debounce time in ms
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_DI_Configure(uint8_t channel, bool inverted, bool pull_up, uint32_t debounce_ms);

/**
 * @brief Generate pulse on digital input
 * @param channel Channel number (0-15)
 * @param duration_ms Pulse duration in milliseconds
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_DI_Pulse(uint8_t channel, uint32_t duration_ms);

/**
 * @brief Toggle digital input state
 * @param channel Channel number (0-15)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_DI_Toggle(uint8_t channel);

/**
 * @brief Set all digital inputs at once
 * @param states Bitmask of states (bit 0 = channel 0, etc.)
 */
void PMU_Emu_DI_SetAll(uint16_t states);

/**
 * @brief Get all digital inputs as bitmask
 * @retval Bitmask of debounced states
 */
uint16_t PMU_Emu_DI_GetAll(void);

/**
 * @brief Get rising edge flag and clear it
 * @param channel Channel number (0-15)
 * @retval true if rising edge detected since last call
 */
bool PMU_Emu_DI_GetRisingEdge(uint8_t channel);

/**
 * @brief Get falling edge flag and clear it
 * @param channel Channel number (0-15)
 * @retval true if falling edge detected since last call
 */
bool PMU_Emu_DI_GetFallingEdge(uint8_t channel);

/**
 * @brief Get pulse count and optionally reset
 * @param channel Channel number (0-15)
 * @param reset Reset counter after reading
 * @retval Pulse count
 */
uint32_t PMU_Emu_DI_GetPulseCount(uint8_t channel, bool reset);

/**
 * @brief Get digital input structure pointer
 * @param channel Channel number (0-15)
 * @retval Pointer to digital input state, or NULL on error
 */
const PMU_Emu_Digital_Input_t* PMU_Emu_DI_GetChannel(uint8_t channel);

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
 * @brief Set H-Bridge motor parameters (legacy API)
 * @param bridge Bridge number (0-3)
 * @param speed Motor speed in units/sec
 * @param inertia Load inertia factor
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_SetMotorParams(uint8_t bridge, float speed, float inertia);

/**
 * @brief Set detailed motor physics parameters
 * @param bridge Bridge number (0-3)
 * @param params Motor parameters structure
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_SetMotorPhysics(uint8_t bridge, const PMU_Emu_MotorParams_t* params);

/**
 * @brief Set motor preset configuration
 * @param bridge Bridge number (0-3)
 * @param preset Preset name: "wiper", "valve", "window", "seat", "custom"
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_SetMotorPreset(uint8_t bridge, const char* preset);

/**
 * @brief Apply external load torque to motor
 * @param bridge Bridge number (0-3)
 * @param torque_Nm Load torque in Newton-meters (positive opposes motion)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_SetLoadTorque(uint8_t bridge, float torque_Nm);

/**
 * @brief Get motor dynamic state
 * @param bridge Bridge number (0-3)
 * @retval Pointer to motor state, or NULL on error
 */
const PMU_Emu_MotorState_t* PMU_Emu_HBridge_GetMotorState(uint8_t bridge);

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

/**
 * @brief Set H-Bridge mode and PWM duty cycle
 * @param bridge Bridge number (0-3)
 * @param mode Operating mode (0=COAST, 1=FORWARD, 2=REVERSE, 3=BRAKE)
 * @param duty PWM duty cycle (0-1000 = 0-100%)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_SetMode(uint8_t bridge, uint8_t mode, uint16_t duty);

/**
 * @brief Set H-Bridge target position for PID control
 * @param bridge Bridge number (0-3)
 * @param target Target position (0-1000)
 * @retval 0 on success, -1 on error
 */
int PMU_Emu_HBridge_SetTarget(uint8_t bridge, uint16_t target);

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

/* ============================================================================
 * WiFi Module Emulation
 * ============================================================================ */

/**
 * @brief Get WiFi module state
 * @retval Pointer to WiFi state
 */
const PMU_Emu_WiFi_t* PMU_Emu_WiFi_GetState(void);

/**
 * @brief Enable/disable WiFi module
 * @param enabled Enable flag
 */
void PMU_Emu_WiFi_SetEnabled(bool enabled);

/**
 * @brief Set WiFi connection state
 * @param state WiFi state
 */
void PMU_Emu_WiFi_SetState(PMU_Emu_WiFi_State_t state);

/**
 * @brief Set WiFi connection info
 * @param ssid SSID name
 * @param rssi Signal strength dBm
 * @param channel WiFi channel
 */
void PMU_Emu_WiFi_SetConnection(const char* ssid, int8_t rssi, uint8_t channel);

/**
 * @brief Set WiFi IP address
 * @param ip IP address string
 */
void PMU_Emu_WiFi_SetIP(const char* ip);

/**
 * @brief Simulate WiFi data transfer
 * @param tx_bytes Bytes transmitted
 * @param rx_bytes Bytes received
 */
void PMU_Emu_WiFi_AddTraffic(uint32_t tx_bytes, uint32_t rx_bytes);

/* ============================================================================
 * Bluetooth Module Emulation
 * ============================================================================ */

/**
 * @brief Get Bluetooth module state
 * @retval Pointer to Bluetooth state
 */
const PMU_Emu_Bluetooth_t* PMU_Emu_BT_GetState(void);

/**
 * @brief Enable/disable Bluetooth module
 * @param enabled Enable flag
 */
void PMU_Emu_BT_SetEnabled(bool enabled);

/**
 * @brief Set Bluetooth state
 * @param state Bluetooth state
 */
void PMU_Emu_BT_SetState(PMU_Emu_BT_State_t state);

/**
 * @brief Set Bluetooth connection info
 * @param peer_address Peer MAC address
 * @param rssi Signal strength dBm
 */
void PMU_Emu_BT_SetConnection(const char* peer_address, int8_t rssi);

/**
 * @brief Simulate Bluetooth data transfer
 * @param tx_bytes Bytes transmitted
 * @param rx_bytes Bytes received
 */
void PMU_Emu_BT_AddTraffic(uint32_t tx_bytes, uint32_t rx_bytes);

/**
 * @brief Set WiFi AP mode
 * @param ap_mode true for AP mode, false for Station mode
 */
void PMU_Emu_WiFi_SetAPMode(bool ap_mode);

/**
 * @brief Connect WiFi to network (simulated)
 * @param ssid Network SSID
 */
void PMU_Emu_WiFi_Connect(const char* ssid);

/**
 * @brief Disconnect WiFi
 */
void PMU_Emu_WiFi_Disconnect(void);

/**
 * @brief Set Bluetooth BLE mode
 * @param ble_mode true for BLE, false for Classic Bluetooth
 */
void PMU_Emu_BT_SetBLEMode(bool ble_mode);

/**
 * @brief Set Bluetooth advertising state
 * @param advertising true to start advertising, false to stop
 */
void PMU_Emu_BT_SetAdvertising(bool advertising);

/* ============================================================================
 * LIN Bus Emulation
 * ============================================================================ */

/**
 * @brief Get LIN bus state
 * @param bus LIN bus number (0 or 1)
 * @retval Pointer to LIN bus state
 */
const PMU_Emu_LIN_Bus_t* PMU_Emu_LIN_GetBus(uint8_t bus);

/**
 * @brief Enable/disable LIN bus
 * @param bus LIN bus number
 * @param enabled Enable flag
 */
void PMU_Emu_LIN_SetEnabled(uint8_t bus, bool enabled);

/**
 * @brief Set LIN bus as master or slave
 * @param bus LIN bus number
 * @param is_master true for master mode
 */
void PMU_Emu_LIN_SetMasterMode(uint8_t bus, bool is_master);

/**
 * @brief Inject LIN frame (simulate reception)
 * @param bus LIN bus number
 * @param frame_id Frame ID (0-63)
 * @param data Frame data
 * @param length Data length
 */
void PMU_Emu_LIN_InjectFrame(uint8_t bus, uint8_t frame_id,
                             const uint8_t* data, uint8_t length);

/**
 * @brief Transmit LIN frame (from emulator as master)
 * @param bus LIN bus number
 * @param frame_id Frame ID
 * @param data Frame data
 * @param length Data length
 */
void PMU_Emu_LIN_Transmit(uint8_t bus, uint8_t frame_id,
                          const uint8_t* data, uint8_t length);

/**
 * @brief Request LIN frame (master sends header only)
 * @param bus LIN bus number
 * @param frame_id Frame ID to request
 */
void PMU_Emu_LIN_RequestFrame(uint8_t bus, uint8_t frame_id);

/**
 * @brief Handle received LIN frame (internal callback)
 * @param bus LIN bus number
 * @param frame_id Frame ID
 * @param data Frame data
 * @param length Data length
 */
void PMU_Emu_LIN_HandleRx(uint8_t bus, uint8_t frame_id,
                          const uint8_t* data, uint8_t length);

/**
 * @brief Send LIN wakeup signal
 * @param bus LIN bus number
 */
void PMU_Emu_LIN_SendWakeup(uint8_t bus);

/**
 * @brief Set LIN bus to sleep mode
 * @param bus LIN bus number
 */
void PMU_Emu_LIN_SetSleep(uint8_t bus);

/**
 * @brief Get LIN frame data
 * @param bus LIN bus number
 * @param frame_id Frame ID
 * @param data Output buffer (8 bytes)
 * @retval 0 on success, -1 if frame not found
 */
int PMU_Emu_LIN_GetFrameData(uint8_t bus, uint8_t frame_id, uint8_t* data);

/**
 * @brief Set LIN frame data (for slave response)
 * @param bus LIN bus number
 * @param frame_id Frame ID
 * @param data Frame data (8 bytes)
 */
void PMU_Emu_LIN_SetFrameData(uint8_t bus, uint8_t frame_id, const uint8_t* data);

#ifdef __cplusplus
}
#endif

#endif /* PMU_EMULATOR_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

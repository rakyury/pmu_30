/**
 ******************************************************************************
 * @file           : pmu_config.h
 * @brief          : PMU-30 Configuration Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

#ifndef __PMU_CONFIG_H
#define __PMU_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "pmu_types.h"
#include "pmu_can_stream.h"

/* Exported types ------------------------------------------------------------*/

/* Channel types are defined in pmu_types.h:
 * - PMU_ChannelType_t (PMU_CHANNEL_TYPE_DIGITAL_INPUT, etc.)
 * - CAN types (PMU_CAN_MessageType_t, etc.)
 */

/* Digital Input Subtypes */
typedef enum {
    PMU_DI_SUBTYPE_SWITCH_ACTIVE_LOW = 0,
    PMU_DI_SUBTYPE_SWITCH_ACTIVE_HIGH,
    PMU_DI_SUBTYPE_FREQUENCY,
    PMU_DI_SUBTYPE_RPM,
    PMU_DI_SUBTYPE_FLEX_FUEL,
    PMU_DI_SUBTYPE_BEACON,
    PMU_DI_SUBTYPE_PULS_OIL_SENSOR
} PMU_DigitalInputSubtype_t;

/* Analog Input Subtypes */
typedef enum {
    PMU_AI_SUBTYPE_SWITCH_ACTIVE_LOW = 0,
    PMU_AI_SUBTYPE_SWITCH_ACTIVE_HIGH,
    PMU_AI_SUBTYPE_ROTARY_SWITCH,
    PMU_AI_SUBTYPE_LINEAR,
    PMU_AI_SUBTYPE_CALIBRATED
} PMU_AnalogInputSubtype_t;

/* Edge Types */
typedef enum {
    PMU_EDGE_RISING = 0,
    PMU_EDGE_FALLING,
    PMU_EDGE_BOTH,
    PMU_EDGE_LEVEL        /**< Level trigger - fires when signal is high (> 0) */
} PMU_EdgeType_t;

/* Timer Modes */
typedef enum {
    PMU_TIMER_MODE_COUNT_UP = 0,
    PMU_TIMER_MODE_COUNT_DOWN
} PMU_TimerMode_t;

/* Filter Types */
typedef enum {
    PMU_FILTER_MOVING_AVG = 0,
    PMU_FILTER_LOW_PASS,
    PMU_FILTER_MIN_WINDOW,
    PMU_FILTER_MAX_WINDOW,
    PMU_FILTER_MEDIAN
} PMU_FilterType_t;

/* Logic Operations */
typedef enum {
    PMU_LOGIC_IS_TRUE = 0,
    PMU_LOGIC_IS_FALSE,
    PMU_LOGIC_EQUAL,
    PMU_LOGIC_NOT_EQUAL,
    PMU_LOGIC_LESS,
    PMU_LOGIC_GREATER,
    PMU_LOGIC_LESS_EQUAL,
    PMU_LOGIC_GREATER_EQUAL,
    PMU_LOGIC_AND,
    PMU_LOGIC_OR,
    PMU_LOGIC_XOR,
    PMU_LOGIC_NOT,
    PMU_LOGIC_NAND,
    PMU_LOGIC_NOR,
    PMU_LOGIC_IN_RANGE,
    PMU_LOGIC_CHANGED,
    PMU_LOGIC_HYSTERESIS,
    PMU_LOGIC_SET_RESET_LATCH,
    PMU_LOGIC_TOGGLE,
    PMU_LOGIC_PULSE,
    PMU_LOGIC_FLASH,
    PMU_LOGIC_EDGE_RISING,
    PMU_LOGIC_EDGE_FALLING
} PMU_LogicOp_t;

/* Math Operations for Number Channel */
typedef enum {
    PMU_MATH_CONSTANT = 0,
    PMU_MATH_CHANNEL,
    PMU_MATH_ADD,
    PMU_MATH_SUBTRACT,
    PMU_MATH_MULTIPLY,
    PMU_MATH_DIVIDE,
    PMU_MATH_MODULO,
    PMU_MATH_MIN,
    PMU_MATH_MAX,
    PMU_MATH_CLAMP,
    PMU_MATH_LOOKUP2,
    PMU_MATH_LOOKUP3,
    PMU_MATH_LOOKUP4,
    PMU_MATH_LOOKUP5
} PMU_MathOp_t;

/* Pullup Options for Analog Inputs */
typedef enum {
    PMU_PULLUP_NONE = 0,
    PMU_PULLUP_1M_DOWN,
    PMU_PULLUP_10K_UP,
    PMU_PULLUP_10K_DOWN,
    PMU_PULLUP_100K_UP,
    PMU_PULLUP_100K_DOWN
} PMU_PullupOption_t;

/* Logic Polarity */
typedef enum {
    PMU_POLARITY_NORMAL = 0,
    PMU_POLARITY_INVERTED
} PMU_Polarity_t;

/* Logic Default State */
typedef enum {
    PMU_DEFAULT_STATE_OFF = 0,
    PMU_DEFAULT_STATE_ON
} PMU_DefaultState_t;

/* ============================================================================
 * Channel Structures (v2.0)
 * ============================================================================ */

/* Maximum calibration points */
#define PMU_MAX_CALIBRATION_POINTS  16
#define PMU_MAX_TABLE_SIZE          16
#define PMU_MAX_CAN_TX_SIGNALS      8
#define PMU_MAX_NUMBER_INPUTS       5
#define PMU_MAX_OUTPUT_PINS         4
/* PMU_CHANNEL_ID_LEN is defined in pmu_types.h (32) */
#define PMU_MAX_CAN_MESSAGES        32  /**< Max CAN message objects (Level 1) */

/* Calibration Point */
typedef struct {
    float voltage;
    float value;
} PMU_CalibrationPoint_t;

/* ============================================================================
 * Digital Input Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    PMU_DigitalInputSubtype_t subtype;
    uint8_t input_pin;              /* D1-D8 -> 0-7 */
    bool enable_pullup;
    bool invert;                    /* Invert input logic */
    uint16_t threshold_mv;          /* Threshold in mV */
    uint16_t debounce_ms;
    /* Frequency/RPM specific */
    PMU_EdgeType_t trigger_edge;
    float multiplier;
    float divider;
    uint16_t timeout_ms;
    uint16_t number_of_teeth;       /* RPM specific */
    /* Button function mode (ECUMaster compatible) */
    PMU_ButtonMode_t button_mode;
    uint16_t long_press_ms;         /* Long press threshold */
    uint16_t long_press_output_id;  /* Separate long press output (channel_id, 0 = none) */
    uint16_t double_click_ms;       /* Double click window */
    uint16_t double_click_output_id; /* Separate double click output (channel_id, 0 = none) */
    uint16_t hold_start_ms;         /* Press and hold start time */
    uint16_t hold_full_ms;          /* Press and hold full time */
    uint16_t reset_channel_id;      /* Reset channel for latch/toggle (channel_id, 0 = none) */
} PMU_DigitalInputConfig_t;

/* ============================================================================
 * Analog Input Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    PMU_AnalogInputSubtype_t subtype;
    uint8_t input_pin;              /* A1-A20 -> 0-19 */
    PMU_PullupOption_t pullup_option;
    uint8_t decimal_places;
    /* Switch mode */
    uint16_t threshold_high_mv;
    uint16_t threshold_high_time_ms;
    uint16_t threshold_low_mv;
    uint16_t threshold_low_time_ms;
    /* Rotary switch mode */
    uint8_t positions;
    uint16_t debounce_ms;
    /* Linear mode */
    uint16_t min_voltage_mv;
    uint16_t max_voltage_mv;
    float min_value;
    float max_value;
    /* Calibrated mode */
    uint8_t calibration_count;
    PMU_CalibrationPoint_t calibration[PMU_MAX_CALIBRATION_POINTS];
} PMU_AnalogInputConfig_t;

/* ============================================================================
 * Power Output Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    uint8_t output_pins[PMU_MAX_OUTPUT_PINS];
    uint8_t output_pin_count;
    bool enabled;                             /* Output enabled for runtime control */
    uint16_t source_channel_id;               /* Source channel (0 = none) */
    /* PWM */
    bool pwm_enabled;
    uint16_t pwm_frequency_hz;
    uint16_t duty_channel_id;                 /* Duty channel (0 = none) */
    float duty_fixed;               /* Fixed duty if no channel (0-100) */
    uint16_t soft_start_ms;
    /* Protection */
    float current_limit_a;
    float inrush_current_a;
    uint16_t inrush_time_ms;
    uint8_t retry_count;
    bool retry_forever;
} PMU_PowerOutputConfig_t;

/* ============================================================================
 * Logic Function Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    PMU_LogicOp_t operation;
    /* Common: channel input (by ID, 0 = none) */
    uint16_t channel_id;
    uint16_t channel_2_id;
    /* Delays */
    float true_delay_s;
    float false_delay_s;
    /* For comparison operations */
    float constant;
    /* For CHANGED operation */
    float threshold;
    float time_on_s;
    /* For HYSTERESIS operation */
    PMU_Polarity_t polarity;
    float upper_value;
    float lower_value;
    /* For SET_RESET_LATCH */
    uint16_t set_channel_id;
    uint16_t reset_channel_id;
    PMU_DefaultState_t default_state;
    /* For TOGGLE/PULSE operation */
    PMU_EdgeType_t edge;
    uint16_t toggle_channel_id;
    uint8_t pulse_count;
    bool retrigger;
    /* For FLASH operation */
    float time_off_s;
} PMU_LogicConfig_t;

/* ============================================================================
 * Number/Math Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    PMU_MathOp_t operation;
    uint16_t input_ids[PMU_MAX_NUMBER_INPUTS];  /* Channel IDs, 0 = none */
    uint8_t input_count;
    float constant_value;
    float clamp_min;
    float clamp_max;
    float lookup_values[PMU_MAX_NUMBER_INPUTS];
    uint8_t decimal_places;
} PMU_NumberConfig_t;

/* ============================================================================
 * Timer Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    uint16_t start_channel_id;  /* Channel ID, 0 = none */
    PMU_EdgeType_t start_edge;
    uint16_t stop_channel_id;   /* Channel ID, 0 = none */
    PMU_EdgeType_t stop_edge;
    PMU_TimerMode_t mode;
    uint16_t limit_hours;
    uint8_t limit_minutes;
    uint8_t limit_seconds;
} PMU_TimerConfig_t;

/* ============================================================================
 * Filter Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    PMU_FilterType_t filter_type;
    uint16_t input_channel_id;  /* Channel ID, 0 = none */
    uint16_t window_size;
    float time_constant;
} PMU_FilterConfig_t;

/* ============================================================================
 * 2D Table Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    uint16_t x_axis_channel_id;  /* Channel ID, 0 = none */
    float x_min;
    float x_max;
    float x_step;
    uint8_t x_count;
    float x_values[PMU_MAX_TABLE_SIZE];
    float output_values[PMU_MAX_TABLE_SIZE];
    uint8_t decimal_places;
} PMU_Table2DConfig_t;

/* ============================================================================
 * 3D Table Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    uint16_t x_axis_channel_id;  /* Channel ID, 0 = none */
    uint16_t y_axis_channel_id;  /* Channel ID, 0 = none */
    float x_min, x_max, x_step;
    float y_min, y_max, y_step;
    uint8_t x_count, y_count;
    float x_values[PMU_MAX_TABLE_SIZE];
    float y_values[PMU_MAX_TABLE_SIZE];
    float data[PMU_MAX_TABLE_SIZE][PMU_MAX_TABLE_SIZE];
    uint8_t decimal_places;
} PMU_Table3DConfig_t;

/* ============================================================================
 * Switch Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    char switch_type[16];           /* "latching", "press_hold" */
    uint16_t input_up_channel_id;   /* Channel ID, 0 = none */
    PMU_EdgeType_t input_up_edge;
    uint16_t input_down_channel_id; /* Channel ID, 0 = none */
    PMU_EdgeType_t input_down_edge;
    int16_t state_first;
    int16_t state_last;
    int16_t state_default;
} PMU_SwitchConfig_t;

/* ============================================================================
 * CAN Message Object (Level 1 - v3.0)
 * ============================================================================ */

/* CAN Message Types are defined in pmu_types.h (PMU_CAN_MessageType_t) */

/** CAN Message Object Configuration */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];       /**< Unique message identifier */
    char name[32];                      /**< Human-readable name */
    uint8_t can_bus;                    /**< CAN bus (1-4) */
    uint32_t base_id;                   /**< Base CAN ID */
    bool is_extended;                   /**< Use 29-bit extended ID */
    PMU_CAN_MessageType_t message_type; /**< Message type */
    uint8_t frame_count;                /**< Number of frames (for compound) */
    uint8_t dlc;                        /**< Data length code */
    uint16_t timeout_ms;                /**< Reception timeout */
    bool enabled;                       /**< Message enabled */
} PMU_CanMessageConfig_t;

/* ============================================================================
 * CAN RX Channel (Level 2 - v3.0)
 * ============================================================================ */

/* CAN Data Types, Formats, and Timeout Behavior are defined in pmu_types.h:
 * - PMU_CAN_DataType_t (PMU_CanDataType_t alias)
 * - PMU_CAN_DataFormat_t (PMU_CanDataFormat_t alias)
 * - PMU_CAN_TimeoutBehavior_t (PMU_CanTimeoutBehavior_t alias)
 */

/** CAN RX Channel Configuration (v3.0) */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    /* Message reference (v3.0 - two-level architecture) */
    char message_ref[PMU_CHANNEL_ID_LEN];  /**< Reference to CAN message object */
    uint8_t frame_offset;                   /**< Frame offset (compound messages) */
    /* Data extraction */
    PMU_CanDataType_t data_type;
    PMU_CanDataFormat_t data_format;
    bool little_endian;                     /**< Byte order */
    uint8_t byte_offset;                    /**< Starting byte (0-7) */
    uint8_t start_bit;                      /**< Start bit (custom format) */
    uint8_t bit_length;                     /**< Bit length (custom format) */
    /* Scaling */
    float multiplier;
    float divider;
    float offset;
    uint8_t decimal_places;
    /* Timeout handling */
    float default_value;
    PMU_CanTimeoutBehavior_t timeout_behavior;
    /* Legacy fields (v2.0 backwards compatibility) */
    uint8_t can_bus;                        /**< Deprecated: use message_ref */
    uint32_t message_id;                    /**< Deprecated: use message_ref */
    bool is_extended;                       /**< Deprecated: use message_ref */
    uint16_t timeout_ms;                    /**< Deprecated: use message timeout */
} PMU_CanRxConfig_t;

/* ============================================================================
 * CAN TX Channel (v3.0)
 * ============================================================================ */

/** CAN TX Transmit Mode */
typedef enum {
    PMU_CAN_TX_MODE_CYCLE = 0,         /**< Periodic transmission */
    PMU_CAN_TX_MODE_TRIGGERED          /**< Edge-triggered transmission */
} PMU_CanTxMode_t;

/** CAN TX Signal Configuration (v3.0) */
typedef struct {
    uint8_t byte_offset;                /**< Starting byte in frame */
    PMU_CanDataType_t data_type;        /**< Data type */
    PMU_CanDataFormat_t data_format;    /**< Data format */
    bool little_endian;                 /**< Byte order */
    uint16_t source_channel_id;              /**< Source channel ID (0 = none) */
    float multiplier;                   /**< Scale multiplier */
} PMU_CanTxSignalV3_t;

/** CAN TX Channel Configuration (v3.0) */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    char name[32];                      /**< Human-readable name */
    uint8_t can_bus;                    /**< CAN bus (1-2) */
    uint32_t message_id;                /**< CAN ID */
    bool is_extended;                   /**< Use 29-bit extended ID */
    uint8_t dlc;                        /**< Data length code */
    /* Transmission mode */
    PMU_CanTxMode_t transmit_mode;      /**< Cycle or Triggered */
    uint16_t cycle_frequency_hz;        /**< Cycle frequency (cycle mode) */
    uint16_t trigger_channel_id;               /**< Trigger channel ID (triggered mode, 0 = none) */
    PMU_EdgeType_t trigger_edge;        /**< Trigger edge */
    /* Signals */
    uint8_t signal_count;
    PMU_CanTxSignalV3_t signals_v3[PMU_MAX_CAN_TX_SIGNALS];
} PMU_CanTxConfig_t;

/* ============================================================================
 * Legacy Structures (for backwards compatibility with v1.0)
 * ============================================================================ */

/**
 * @brief PMU Output Channel Configuration (Legacy v1.0)
 */
typedef struct {
    uint8_t channel;                /* Channel number (1-30) */
    bool enabled;                   /* Channel enabled */
    uint16_t current_limit_mA;      /* Current limit in mA (0-40000) */
    uint16_t inrush_current_mA;     /* Inrush current limit in mA (0-160000) */
    uint16_t pwm_frequency_hz;      /* PWM frequency in Hz (0-20000) */
    uint8_t pwm_duty_cycle;         /* PWM duty cycle (0-100%) */
    uint16_t soft_start_ms;         /* Soft-start ramp time in ms (0-5000) */
    bool overcurrent_enabled;       /* Overcurrent protection enabled */
    bool overtemp_enabled;          /* Overtemperature protection enabled */
    bool open_load_detect_enabled;  /* Open load detection enabled */
    bool short_circuit_enabled;     /* Short circuit protection enabled */
} PMU_OutputConfig_t;

/**
 * @brief H-Bridge PWM source mode
 */
typedef enum {
    PMU_HBRIDGE_PWM_FIXED = 0,      /* Fixed PWM value */
    PMU_HBRIDGE_PWM_CHANNEL,        /* PWM from channel (0-100%) */
    PMU_HBRIDGE_PWM_BIDIRECTIONAL   /* Bidirectional: 0-50%=Rev, 50-100%=Fwd */
} PMU_HBridge_PwmMode_t;

/**
 * @brief H-Bridge failsafe mode
 */
typedef enum {
    PMU_HBRIDGE_FAILSAFE_PARK = 0,  /* Move to park position */
    PMU_HBRIDGE_FAILSAFE_BRAKE,     /* Active brake (hold) */
    PMU_HBRIDGE_FAILSAFE_COAST,     /* Coast (free spin) */
    PMU_HBRIDGE_FAILSAFE_CUSTOM     /* Move to custom position */
} PMU_HBridge_FailsafeMode_t;

/**
 * @brief PMU H-Bridge Configuration (ECUMaster-style)
 */
typedef struct {
    /* Basic settings */
    char name[32];                  /* Channel name */
    uint8_t bridge;                 /* Bridge number (0-3) */
    bool enabled;                   /* Bridge enabled */
    uint8_t mode;                   /* Operating mode (coast/forward/reverse/brake/wiper_park/pid_position) */
    char motor_preset[16];          /* Motor preset (wiper/window/seat/valve/pump/custom) */

    /* Control sources */
    uint16_t source_channel_id;             /* Activation source channel (0 = none) */
    uint16_t direction_source_channel_id;   /* Direction source channel (0 = none) */
    bool invert_direction;          /* Invert direction logic */

    /* PWM control */
    PMU_HBridge_PwmMode_t pwm_mode; /* PWM source mode */
    uint16_t pwm_frequency;         /* PWM frequency in Hz (1000/4000/10000/20000) */
    uint8_t pwm_value;              /* Fixed PWM value (0-255) */
    uint16_t pwm_source_channel_id;         /* PWM source channel (0 = none) */
    uint8_t duty_limit_percent;     /* Max duty cycle (0-100%) */

    /* Position control */
    bool position_feedback_enabled; /* Enable position feedback */
    uint16_t position_source_channel_id;    /* Position feedback source (0 = none) */
    uint16_t target_position;       /* Fixed target position */
    uint16_t target_source_channel_id;      /* Target position source (0 = none) */
    uint16_t position_min;          /* Minimum position value */
    uint16_t position_max;          /* Maximum position value */
    uint16_t position_deadband;     /* Position tolerance */
    float position_park;            /* Park position for wiper mode */

    /* Valid voltage range (ECUMaster feature) */
    float valid_voltage_min;        /* Min valid feedback voltage (V) */
    float valid_voltage_max;        /* Max valid feedback voltage (V) */

    /* Position margins (ECUMaster feature) */
    uint16_t lower_margin;          /* Lower position margin */
    uint16_t upper_margin;          /* Upper position margin */

    /* PID control */
    float pid_kp;                   /* Proportional gain */
    float pid_ki;                   /* Integral gain */
    float pid_kd;                   /* Derivative gain */
    float pid_kd_filter;            /* Derivative filter (0-1) */
    int16_t pid_output_min;         /* PID output min */
    int16_t pid_output_max;         /* PID output max */

    /* Current protection */
    float current_limit_a;          /* Continuous current limit (A) */
    float inrush_current_a;         /* Inrush current limit (A) */
    uint16_t inrush_time_ms;        /* Inrush time period (ms) */
    uint8_t retry_count;            /* Retry count before lockout */
    uint16_t retry_delay_ms;        /* Delay between retries (ms) */

    /* Stall detection */
    bool stall_detection_enabled;   /* Enable stall detection */
    float stall_current_threshold_a; /* Stall current threshold (A) */
    uint16_t stall_time_threshold_ms; /* Stall time threshold (ms) */
    int16_t overtemperature_threshold_c; /* Over-temperature limit (C) */

    /* Signal loss failsafe */
    bool failsafe_enabled;          /* Enable signal loss protection */
    uint16_t signal_timeout_ms;     /* Signal timeout (ms) */
    PMU_HBridge_FailsafeMode_t failsafe_mode; /* Failsafe action */
    uint16_t failsafe_position;     /* Failsafe target position */
    uint8_t failsafe_pwm;           /* Failsafe PWM value */
    bool auto_recovery;             /* Auto-recover on signal return */
} PMU_HBridgeConfig_t;

/**
 * @brief PMU Input Channel Configuration (Legacy v1.0)
 * Note: PMU_InputType_t is defined in pmu_types.h for current use.
 * This legacy enum is renamed to avoid conflict.
 */
typedef enum {
    PMU_LEGACY_INPUT_SWITCH_ACTIVE_LOW = 0,
    PMU_LEGACY_INPUT_SWITCH_ACTIVE_HIGH,
    PMU_LEGACY_INPUT_ROTARY_SWITCH,
    PMU_LEGACY_INPUT_LINEAR_ANALOG,
    PMU_LEGACY_INPUT_CALIBRATED_ANALOG,
    PMU_LEGACY_INPUT_FREQUENCY
} PMU_LegacyInputType_t;

typedef struct {
    uint8_t channel;                /* Channel number (1-20) */
    PMU_LegacyInputType_t type;     /* Input type (legacy) */
    char name[32];                  /* Input name */
    bool pullup_enabled;            /* Internal pull-up enabled */
    bool pulldown_enabled;          /* Internal pull-down enabled */
    uint16_t threshold_high_mv;     /* High threshold in mV */
    uint16_t threshold_low_mv;      /* Low threshold in mV */
    uint16_t debounce_ms;           /* Debounce time in ms */
    float multiplier;               /* Linear scaling multiplier */
    float offset;                   /* Linear scaling offset */
    char unit[16];                  /* Measurement unit */
    uint8_t decimal_places;         /* Display decimal places (0-3) */
    uint8_t filter_samples;         /* Moving average filter samples */
    /* Calibration table for CALIBRATED_ANALOG type */
    uint8_t calibration_count;      /* Number of calibration points (0-16) */
    PMU_CalibrationPoint_t calibration[PMU_MAX_CALIBRATION_POINTS];
} PMU_InputConfig_t;

/**
 * @brief CAN Message Object Configuration
 */
typedef struct {
    char name[32];                  /* Message name */
    uint8_t can_bus;                /* CAN bus number (1-4) */
    uint32_t message_id;            /* CAN message ID */
    bool extended_id;               /* Extended (29-bit) ID */
    uint8_t dlc;                    /* Data length code (0-8 or 0-64 for CAN FD) */
    uint16_t transmission_rate_hz;  /* Transmission rate in Hz (0 = on-demand) */
    uint16_t timeout_ms;            /* Reception timeout in ms */
    bool is_tx;                     /* Transmit message */
    bool is_rx;                     /* Receive message */
    uint8_t data[64];               /* Default data bytes */
} PMU_CANMessageConfig_t;

/**
 * @brief PMU System Configuration
 */
typedef struct {
    uint8_t hw_revision;            /* Hardware revision */
    uint8_t fw_version_major;       /* Firmware version major */
    uint8_t fw_version_minor;       /* Firmware version minor */
    uint8_t fw_version_patch;       /* Firmware version patch */

    uint32_t serial_number;         /* Device serial number */
    char device_name[32];           /* Device name */

    bool logging_enabled;           /* Data logging enabled */
    uint16_t logging_rate_hz;       /* Logging rate in Hz */

    bool wifi_enabled;              /* WiFi AP mode enabled */
    char wifi_ssid[32];             /* WiFi SSID */
    char wifi_password[64];         /* WiFi password */

    bool bluetooth_enabled;         /* Bluetooth enabled */
    char bt_name[32];               /* Bluetooth device name */

    PMU_OutputConfig_t outputs[PMU30_NUM_OUTPUTS];
    PMU_HBridgeConfig_t hbridges[PMU30_NUM_HBRIDGES];
    PMU_InputConfig_t inputs[PMU30_NUM_ADC_INPUTS];

} PMU_SystemConfig_t;

/* Exported constants --------------------------------------------------------*/

/* Default configuration values */
#define PMU_DEFAULT_CURRENT_LIMIT_MA        40000   /* 40A */
#define PMU_DEFAULT_INRUSH_CURRENT_MA       160000  /* 160A */
#define PMU_DEFAULT_PWM_FREQUENCY_HZ        1000    /* 1 kHz */
#define PMU_DEFAULT_SOFT_START_MS           100     /* 100 ms */

#define PMU_HBRIDGE_DEFAULT_CURRENT_MA      30000   /* 30A */
#define PMU_HBRIDGE_DEFAULT_PWM_FREQ_HZ     20000   /* 20 kHz */
#define PMU_HBRIDGE_STALL_CURRENT_MA        25000   /* 25A stall threshold */
#define PMU_HBRIDGE_STALL_TIME_MS           500     /* 500ms stall detection time */

/* Input thresholds */
#define PMU_INPUT_THRESHOLD_HIGH_MV         3500    /* 3.5V */
#define PMU_INPUT_THRESHOLD_LOW_MV          1500    /* 1.5V */
#define PMU_INPUT_DEBOUNCE_MS               10      /* 10 ms */

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/
void PMU_Config_Init(void);
void PMU_Config_LoadDefaults(void);
void PMU_Config_Save(void);
void PMU_Config_Load(void);
PMU_SystemConfig_t* PMU_Config_Get(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_CONFIG_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

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

/* Exported types ------------------------------------------------------------*/

/* ============================================================================
 * Channel Type Enumeration (v2.0)
 * Unified channel architecture
 * ============================================================================ */
typedef enum {
    PMU_CHANNEL_TYPE_DIGITAL_INPUT = 0,
    PMU_CHANNEL_TYPE_ANALOG_INPUT,
    PMU_CHANNEL_TYPE_POWER_OUTPUT,
    PMU_CHANNEL_TYPE_CAN_RX,
    PMU_CHANNEL_TYPE_CAN_TX,
    PMU_CHANNEL_TYPE_LOGIC,
    PMU_CHANNEL_TYPE_NUMBER,
    PMU_CHANNEL_TYPE_TABLE_2D,
    PMU_CHANNEL_TYPE_TABLE_3D,
    PMU_CHANNEL_TYPE_SWITCH,
    PMU_CHANNEL_TYPE_TIMER,
    PMU_CHANNEL_TYPE_FILTER,
    PMU_CHANNEL_TYPE_ENUM,
    PMU_CHANNEL_TYPE_COUNT
} PMU_ChannelType_t;

/* Backwards compatibility alias */
typedef PMU_ChannelType_t PMU_GPIOType_t;
#define PMU_GPIO_TYPE_DIGITAL_INPUT  PMU_CHANNEL_TYPE_DIGITAL_INPUT
#define PMU_GPIO_TYPE_ANALOG_INPUT   PMU_CHANNEL_TYPE_ANALOG_INPUT
#define PMU_GPIO_TYPE_POWER_OUTPUT   PMU_CHANNEL_TYPE_POWER_OUTPUT
#define PMU_GPIO_TYPE_CAN_RX         PMU_CHANNEL_TYPE_CAN_RX
#define PMU_GPIO_TYPE_CAN_TX         PMU_CHANNEL_TYPE_CAN_TX
#define PMU_GPIO_TYPE_LOGIC          PMU_CHANNEL_TYPE_LOGIC
#define PMU_GPIO_TYPE_NUMBER         PMU_CHANNEL_TYPE_NUMBER
#define PMU_GPIO_TYPE_TABLE_2D       PMU_CHANNEL_TYPE_TABLE_2D
#define PMU_GPIO_TYPE_TABLE_3D       PMU_CHANNEL_TYPE_TABLE_3D
#define PMU_GPIO_TYPE_SWITCH         PMU_CHANNEL_TYPE_SWITCH
#define PMU_GPIO_TYPE_TIMER          PMU_CHANNEL_TYPE_TIMER
#define PMU_GPIO_TYPE_FILTER         PMU_CHANNEL_TYPE_FILTER
#define PMU_GPIO_TYPE_ENUM           PMU_CHANNEL_TYPE_ENUM
#define PMU_GPIO_TYPE_COUNT          PMU_CHANNEL_TYPE_COUNT

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
    PMU_EDGE_BOTH
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
    PMU_LOGIC_CHANGED,
    PMU_LOGIC_HYSTERESIS,
    PMU_LOGIC_SET_RESET_LATCH,
    PMU_LOGIC_TOGGLE,
    PMU_LOGIC_PULSE,
    PMU_LOGIC_FLASH
} PMU_LogicOp_t;

/* Math Operations for Number GPIO */
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
#define PMU_MAX_ENUM_ITEMS          16
#define PMU_MAX_CAN_TX_SIGNALS      8
#define PMU_MAX_NUMBER_INPUTS       5
#define PMU_MAX_OUTPUT_PINS         4
#define PMU_CHANNEL_ID_LEN          32

/* Calibration Point */
typedef struct {
    float voltage;
    float value;
} PMU_CalibrationPoint_t;

/* Enum Item */
typedef struct {
    int16_t value;
    char text[16];
    uint32_t color;  /* RGB color */
} PMU_EnumItem_t;

/* CAN TX Signal */
typedef struct {
    char source_channel[PMU_CHANNEL_ID_LEN];
    uint8_t start_bit;
    uint8_t length;
    bool little_endian;
    float factor;
    float offset;
} PMU_CanTxSignal_t;

/* ============================================================================
 * Digital Input Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    PMU_DigitalInputSubtype_t subtype;
    uint8_t input_pin;              /* D1-D8 -> 0-7 */
    bool enable_pullup;
    uint16_t threshold_mv;          /* Threshold in mV */
    uint16_t debounce_ms;
    /* Frequency/RPM specific */
    PMU_EdgeType_t trigger_edge;
    float multiplier;
    float divider;
    uint16_t timeout_ms;
    uint16_t number_of_teeth;       /* RPM specific */
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
    char source_channel[PMU_CHANNEL_ID_LEN];
    /* PWM */
    bool pwm_enabled;
    uint16_t pwm_frequency_hz;
    char duty_channel[PMU_CHANNEL_ID_LEN];
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
    /* Common: channel input */
    char channel[PMU_CHANNEL_ID_LEN];
    char channel_2[PMU_CHANNEL_ID_LEN];
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
    char set_channel[PMU_CHANNEL_ID_LEN];
    char reset_channel[PMU_CHANNEL_ID_LEN];
    PMU_DefaultState_t default_state;
    /* For TOGGLE/PULSE operation */
    PMU_EdgeType_t edge;
    char toggle_channel[PMU_CHANNEL_ID_LEN];
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
    char inputs[PMU_MAX_NUMBER_INPUTS][PMU_CHANNEL_ID_LEN];
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
    char start_channel[PMU_CHANNEL_ID_LEN];
    PMU_EdgeType_t start_edge;
    char stop_channel[PMU_CHANNEL_ID_LEN];
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
    char input_channel[PMU_CHANNEL_ID_LEN];
    uint16_t window_size;
    float time_constant;
} PMU_FilterConfig_t;

/* ============================================================================
 * Enum Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    bool is_bitfield;
    uint8_t item_count;
    PMU_EnumItem_t items[PMU_MAX_ENUM_ITEMS];
} PMU_EnumConfig_t;

/* ============================================================================
 * 2D Table Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    char x_axis_channel[PMU_CHANNEL_ID_LEN];
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
    char x_axis_channel[PMU_CHANNEL_ID_LEN];
    char y_axis_channel[PMU_CHANNEL_ID_LEN];
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
    char input_up_channel[PMU_CHANNEL_ID_LEN];
    PMU_EdgeType_t input_up_edge;
    char input_down_channel[PMU_CHANNEL_ID_LEN];
    PMU_EdgeType_t input_down_edge;
    int16_t state_first;
    int16_t state_last;
    int16_t state_default;
} PMU_SwitchConfig_t;

/* ============================================================================
 * CAN RX Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    uint8_t can_bus;
    uint32_t message_id;
    bool is_extended;
    uint8_t start_bit;
    uint8_t length;
    bool little_endian;
    bool is_signed;
    bool is_float;
    float factor;
    float offset;
    uint16_t timeout_ms;
} PMU_CanRxConfig_t;

/* ============================================================================
 * CAN TX Channel
 * ============================================================================ */
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];
    uint8_t can_bus;
    uint32_t message_id;
    bool is_extended;
    uint16_t cycle_time_ms;
    uint8_t signal_count;
    PMU_CanTxSignal_t signals[PMU_MAX_CAN_TX_SIGNALS];
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
 * @brief PMU H-Bridge Configuration
 */
typedef struct {
    uint8_t bridge;                 /* Bridge number (1-4) */
    bool enabled;                   /* Bridge enabled */
    uint16_t current_limit_mA;      /* Current limit in mA (0-30000) */
    uint16_t pwm_frequency_hz;      /* PWM frequency in Hz (10-20000) */
    bool brake_on_stop;             /* Enable active braking */
    bool wiper_park_enabled;        /* Wiper park function enabled */
    uint8_t park_input_channel;     /* Input channel for park sensor */
} PMU_HBridgeConfig_t;

/**
 * @brief PMU Input Channel Configuration (Legacy v1.0)
 */
typedef enum {
    PMU_INPUT_SWITCH_ACTIVE_LOW = 0,
    PMU_INPUT_SWITCH_ACTIVE_HIGH,
    PMU_INPUT_ROTARY_SWITCH,
    PMU_INPUT_LINEAR_ANALOG,
    PMU_INPUT_CALIBRATED_ANALOG,
    PMU_INPUT_FREQUENCY
} PMU_InputType_t;

typedef struct {
    uint8_t channel;                /* Channel number (1-20) */
    PMU_InputType_t type;           /* Input type */
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

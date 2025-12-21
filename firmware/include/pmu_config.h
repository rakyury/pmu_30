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

/**
 * @brief PMU Output Channel Configuration
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
 * @brief PMU Input Channel Configuration
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

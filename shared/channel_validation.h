/**
 * @file channel_validation.h
 * @brief PMU-30 Shared Channel Configuration Validation
 *
 * This module provides validation logic for channel configurations.
 * Used by:
 * - Firmware: validate received config before applying
 * - Configurator (Python): validate user input in dialogs
 * - Integration tests: verify config correctness
 *
 * Design principles:
 * - Pure functions (no side effects)
 * - Detailed error reporting
 * - Type-specific validation rules
 * - Range/limit enforcement
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef PMU_CHANNEL_VALIDATION_H
#define PMU_CHANNEL_VALIDATION_H

#include <stdint.h>
#include <stdbool.h>
#include "channel_config.h"
#include "channel_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Validation Error Codes
 *============================================================================*/

typedef enum {
    VAL_OK = 0,

    /* General errors (1-99) */
    VAL_ERR_INVALID_TYPE = 1,
    VAL_ERR_INVALID_ID,
    VAL_ERR_NAME_TOO_LONG,
    VAL_ERR_EMPTY_NAME,
    VAL_ERR_INVALID_FLAGS,
    VAL_ERR_INVALID_HW_DEVICE,
    VAL_ERR_INVALID_HW_INDEX,
    VAL_ERR_INVALID_SOURCE_ID,
    VAL_ERR_CONFIG_SIZE_MISMATCH,

    /* Input validation errors (100-199) */
    VAL_ERR_INPUT_INVALID_DEBOUNCE = 100,
    VAL_ERR_INPUT_INVALID_FILTER_MS,
    VAL_ERR_INPUT_INVALID_FILTER_TYPE,
    VAL_ERR_INPUT_INVALID_SAMPLES,
    VAL_ERR_INPUT_INVALID_RANGE,        /* raw_min >= raw_max */
    VAL_ERR_INPUT_INVALID_TIMEOUT,
    VAL_ERR_INPUT_INVALID_EDGE_MODE,
    VAL_ERR_INPUT_ZERO_DIVISOR,         /* scale_den = 0 */

    /* CAN errors (200-249) */
    VAL_ERR_CAN_INVALID_BUS = 200,
    VAL_ERR_CAN_INVALID_ID,
    VAL_ERR_CAN_INVALID_DLC,
    VAL_ERR_CAN_INVALID_BIT_POS,        /* start_bit + bit_length > 64 */
    VAL_ERR_CAN_INVALID_BYTE_ORDER,
    VAL_ERR_CAN_ZERO_DIVISOR,
    VAL_ERR_CAN_INVALID_PERIOD,

    /* Output validation errors (300-399) */
    VAL_ERR_OUTPUT_INVALID_CURRENT_LIMIT = 300,
    VAL_ERR_OUTPUT_INVALID_PWM_FREQ,
    VAL_ERR_OUTPUT_INVALID_RETRY_COUNT,
    VAL_ERR_OUTPUT_INVALID_SOFT_START,
    VAL_ERR_OUTPUT_INVALID_INRUSH,
    VAL_ERR_PWM_INVALID_DUTY_RANGE,     /* min_duty > max_duty */
    VAL_ERR_HBRIDGE_INVALID_DEADBAND,
    VAL_ERR_HBRIDGE_INVALID_RATE,

    /* Logic/Math errors (400-499) */
    VAL_ERR_LOGIC_INVALID_OPERATION = 400,
    VAL_ERR_LOGIC_NO_INPUTS,
    VAL_ERR_LOGIC_TOO_MANY_INPUTS,
    VAL_ERR_LOGIC_INVALID_INPUT_ID,
    VAL_ERR_LOGIC_INSUFFICIENT_INPUTS,  /* e.g., AND with 1 input */
    VAL_ERR_MATH_INVALID_OPERATION,
    VAL_ERR_MATH_NO_INPUTS,
    VAL_ERR_MATH_TOO_MANY_INPUTS,
    VAL_ERR_MATH_INVALID_INPUT_ID,
    VAL_ERR_MATH_ZERO_DIVISOR,
    VAL_ERR_MATH_INVALID_RANGE,         /* min >= max for clamp */

    /* Timer errors (500-549) */
    VAL_ERR_TIMER_INVALID_MODE = 500,
    VAL_ERR_TIMER_INVALID_TRIGGER_MODE,
    VAL_ERR_TIMER_INVALID_TRIGGER_ID,
    VAL_ERR_TIMER_ZERO_DELAY,
    VAL_ERR_TIMER_INVALID_BLINK_TIMES,

    /* Table errors (550-599) */
    VAL_ERR_TABLE_INVALID_INPUT = 550,
    VAL_ERR_TABLE_INSUFFICIENT_POINTS,
    VAL_ERR_TABLE_TOO_MANY_POINTS,
    VAL_ERR_TABLE_X_NOT_MONOTONIC,      /* X values must be ascending */
    VAL_ERR_TABLE_3D_INVALID_Y_INPUT,
    VAL_ERR_TABLE_3D_INSUFFICIENT_X,
    VAL_ERR_TABLE_3D_INSUFFICIENT_Y,

    /* Filter errors (600-649) */
    VAL_ERR_FILTER_INVALID_INPUT = 600,
    VAL_ERR_FILTER_INVALID_TYPE,
    VAL_ERR_FILTER_INVALID_WINDOW,
    VAL_ERR_FILTER_INVALID_ALPHA,
    VAL_ERR_FILTER_ZERO_TIME_CONST,

    /* PID errors (650-699) */
    VAL_ERR_PID_INVALID_SETPOINT = 650,
    VAL_ERR_PID_INVALID_FEEDBACK,
    VAL_ERR_PID_INVALID_OUTPUT_RANGE,
    VAL_ERR_PID_INVALID_INTEGRAL_RANGE,

    /* Counter errors (700-749) */
    VAL_ERR_COUNTER_INVALID_TRIGGER = 700,
    VAL_ERR_COUNTER_INVALID_RANGE,
    VAL_ERR_COUNTER_ZERO_STEP,

    /* FlipFlop errors (750-799) */
    VAL_ERR_FF_INVALID_TYPE = 750,
    VAL_ERR_FF_INVALID_INPUT,

    /* Hysteresis errors (800-849) */
    VAL_ERR_HYST_INVALID_INPUT = 800,
    VAL_ERR_HYST_INVALID_TYPE,
    VAL_ERR_HYST_INVALID_THRESHOLDS,    /* low >= high */

    /* Switch errors (850-899) */
    VAL_ERR_SWITCH_INVALID_SELECTOR = 850,
    VAL_ERR_SWITCH_NO_CASES,
    VAL_ERR_SWITCH_TOO_MANY_CASES,
    VAL_ERR_SWITCH_INVALID_MODE,

    /* Number errors (900-949) */
    VAL_ERR_NUMBER_INVALID_RANGE = 900,
    VAL_ERR_NUMBER_ZERO_STEP,
    VAL_ERR_NUMBER_VALUE_OUT_OF_RANGE,

} ValidationError_t;

/*============================================================================
 * Validation Limits (configurable)
 *============================================================================*/

typedef struct {
    /* General */
    uint16_t max_channel_id;        /**< Maximum valid channel ID */
    uint16_t max_name_length;       /**< Maximum name length */

    /* Digital input */
    uint16_t max_debounce_ms;       /**< Maximum debounce time */

    /* Analog input */
    uint16_t max_filter_ms;         /**< Maximum filter time */
    uint8_t  max_samples;           /**< Maximum averaging samples */

    /* CAN */
    uint8_t  max_can_bus;           /**< Maximum CAN bus number */

    /* Power output */
    uint32_t max_current_ma;        /**< Maximum current limit */
    uint16_t max_pwm_freq;          /**< Maximum PWM frequency */
    uint16_t min_pwm_freq;          /**< Minimum PWM frequency */

    /* Timer */
    uint32_t max_delay_ms;          /**< Maximum timer delay */

    /* Tables */
    uint8_t  min_table_points;      /**< Minimum table points */

    /* Filter */
    uint8_t  max_window_size;       /**< Maximum filter window */

} ValidationLimits_t;

/*============================================================================
 * Validation Result
 *============================================================================*/

typedef struct {
    ValidationError_t error;        /**< Error code (VAL_OK if valid) */
    const char* field;              /**< Field name that failed (NULL if OK) */
    int32_t actual_value;           /**< Actual value that failed */
    int32_t expected_min;           /**< Expected minimum (if range error) */
    int32_t expected_max;           /**< Expected maximum (if range error) */
} ValidationResult_t;

/*============================================================================
 * Default Limits
 *============================================================================*/

/** Get default validation limits for PMU-30 */
const ValidationLimits_t* Val_GetDefaultLimits(void);

/*============================================================================
 * Header Validation
 *============================================================================*/

/**
 * Validate channel header.
 *
 * @param header Channel header to validate
 * @param limits Validation limits (NULL for defaults)
 * @return Validation result
 */
ValidationResult_t Val_ValidateHeader(
    const CfgChannelHeader_t* header,
    const ValidationLimits_t* limits
);

/*============================================================================
 * Type-Specific Validation
 *============================================================================*/

/** Validate digital input config */
ValidationResult_t Val_ValidateDigitalInput(
    const CfgDigitalInput_t* config,
    const ValidationLimits_t* limits
);

/** Validate analog input config */
ValidationResult_t Val_ValidateAnalogInput(
    const CfgAnalogInput_t* config,
    const ValidationLimits_t* limits
);

/** Validate frequency input config */
ValidationResult_t Val_ValidateFrequencyInput(
    const CfgFrequencyInput_t* config,
    const ValidationLimits_t* limits
);

/** Validate CAN input config */
ValidationResult_t Val_ValidateCanInput(
    const CfgCanInput_t* config,
    const ValidationLimits_t* limits
);

/** Validate power output config */
ValidationResult_t Val_ValidatePowerOutput(
    const CfgPowerOutput_t* config,
    const ValidationLimits_t* limits
);

/** Validate PWM output config */
ValidationResult_t Val_ValidatePwmOutput(
    const CfgPwmOutput_t* config,
    const ValidationLimits_t* limits
);

/** Validate H-Bridge config */
ValidationResult_t Val_ValidateHBridge(
    const CfgHBridge_t* config,
    const ValidationLimits_t* limits
);

/** Validate CAN output config */
ValidationResult_t Val_ValidateCanOutput(
    const CfgCanOutput_t* config,
    const ValidationLimits_t* limits
);

/** Validate timer config */
ValidationResult_t Val_ValidateTimer(
    const CfgTimer_t* config,
    const ValidationLimits_t* limits
);

/** Validate logic config */
ValidationResult_t Val_ValidateLogic(
    const CfgLogic_t* config,
    const ValidationLimits_t* limits
);

/** Validate math config */
ValidationResult_t Val_ValidateMath(
    const CfgMath_t* config,
    const ValidationLimits_t* limits
);

/** Validate 2D table config */
ValidationResult_t Val_ValidateTable2D(
    const CfgTable2D_t* config,
    const ValidationLimits_t* limits
);

/** Validate 3D table config */
ValidationResult_t Val_ValidateTable3D(
    const CfgTable3D_t* config,
    const ValidationLimits_t* limits
);

/** Validate filter config */
ValidationResult_t Val_ValidateFilter(
    const CfgFilter_t* config,
    const ValidationLimits_t* limits
);

/** Validate PID config */
ValidationResult_t Val_ValidatePid(
    const CfgPid_t* config,
    const ValidationLimits_t* limits
);

/** Validate counter config */
ValidationResult_t Val_ValidateCounter(
    const CfgCounter_t* config,
    const ValidationLimits_t* limits
);

/** Validate flipflop config */
ValidationResult_t Val_ValidateFlipFlop(
    const CfgFlipFlop_t* config,
    const ValidationLimits_t* limits
);

/** Validate hysteresis config */
ValidationResult_t Val_ValidateHysteresis(
    const CfgHysteresis_t* config,
    const ValidationLimits_t* limits
);

/** Validate switch config */
ValidationResult_t Val_ValidateSwitch(
    const CfgSwitch_t* config,
    const ValidationLimits_t* limits
);

/** Validate number config */
ValidationResult_t Val_ValidateNumber(
    const CfgNumber_t* config,
    const ValidationLimits_t* limits
);

/*============================================================================
 * Full Channel Validation
 *============================================================================*/

/**
 * Validate complete channel (header + type-specific config).
 *
 * @param header Channel header
 * @param config Type-specific config (cast to appropriate type)
 * @param name Channel name (NULL-terminated)
 * @param limits Validation limits (NULL for defaults)
 * @return Validation result
 */
ValidationResult_t Val_ValidateChannel(
    const CfgChannelHeader_t* header,
    const void* config,
    const char* name,
    const ValidationLimits_t* limits
);

/*============================================================================
 * Utility Functions
 *============================================================================*/

/**
 * Get error message for validation error.
 *
 * @param error Error code
 * @return Human-readable error message
 */
const char* Val_GetErrorMessage(ValidationError_t error);

/**
 * Check if channel ID is valid.
 *
 * @param id Channel ID
 * @param max_id Maximum valid ID
 * @return true if valid
 */
bool Val_IsValidChannelId(uint16_t id, uint16_t max_id);

/**
 * Check if channel ID reference is valid.
 * Allows CH_REF_NONE as a special case.
 *
 * @param id Channel ID reference
 * @param max_id Maximum valid ID
 * @return true if valid
 */
bool Val_IsValidChannelRef(uint16_t id, uint16_t max_id);

/**
 * Create a success result.
 */
ValidationResult_t Val_Success(void);

/**
 * Create an error result.
 */
ValidationResult_t Val_Error(
    ValidationError_t error,
    const char* field,
    int32_t actual,
    int32_t min,
    int32_t max
);

#ifdef __cplusplus
}
#endif

#endif /* PMU_CHANNEL_VALIDATION_H */

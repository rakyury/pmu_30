/**
 * @file channel_validation.c
 * @brief PMU-30 Shared Channel Configuration Validation Implementation
 *
 * @version 1.0
 * @date January 2026
 */

#include "channel_validation.h"
#include <string.h>

/*============================================================================
 * Default Limits
 *============================================================================*/

static const ValidationLimits_t default_limits = {
    .max_channel_id = 4095,         /* 12-bit channel IDs */
    .max_name_length = CFG_MAX_NAME_LEN,

    .max_debounce_ms = 1000,        /* 1 second max debounce */

    .max_filter_ms = 10000,         /* 10 second max filter */
    .max_samples = 64,              /* 64 sample average max */

    .max_can_bus = 3,               /* CAN0-CAN3 */

    .max_current_ma = 40000,        /* 40A max per channel */
    .max_pwm_freq = 25000,          /* 25kHz max PWM */
    .min_pwm_freq = 100,            /* 100Hz min PWM */

    .max_delay_ms = 3600000,        /* 1 hour max timer */

    .min_table_points = 2,          /* At least 2 points for interpolation */

    .max_window_size = 32,          /* 32 sample max window */
};

/*============================================================================
 * Utility Functions
 *============================================================================*/

const ValidationLimits_t* Val_GetDefaultLimits(void)
{
    return &default_limits;
}

ValidationResult_t Val_Success(void)
{
    ValidationResult_t result = {
        .error = VAL_OK,
        .field = NULL,
        .actual_value = 0,
        .expected_min = 0,
        .expected_max = 0
    };
    return result;
}

ValidationResult_t Val_Error(
    ValidationError_t error,
    const char* field,
    int32_t actual,
    int32_t min,
    int32_t max)
{
    ValidationResult_t result = {
        .error = error,
        .field = field,
        .actual_value = actual,
        .expected_min = min,
        .expected_max = max
    };
    return result;
}

bool Val_IsValidChannelId(uint16_t id, uint16_t max_id)
{
    return id > 0 && id <= max_id;
}

bool Val_IsValidChannelRef(uint16_t id, uint16_t max_id)
{
    return id == CH_REF_NONE || (id > 0 && id <= max_id);
}

static const ValidationLimits_t* get_limits(const ValidationLimits_t* limits)
{
    return limits ? limits : &default_limits;
}

/*============================================================================
 * Header Validation
 *============================================================================*/

ValidationResult_t Val_ValidateHeader(
    const CfgChannelHeader_t* header,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!header) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "header", 0, 0, 0);
    }

    /* Validate channel ID */
    if (!Val_IsValidChannelId(header->id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_INVALID_ID, "id",
            header->id, 1, lim->max_channel_id);
    }

    /* Validate channel type */
    if (header->type == 0 || header->type > CH_TYPE_NUMBER) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "type",
            header->type, 1, CH_TYPE_NUMBER);
    }

    /* Validate name length */
    if (header->name_len > lim->max_name_length) {
        return Val_Error(VAL_ERR_NAME_TOO_LONG, "name_len",
            header->name_len, 0, lim->max_name_length);
    }

    /* Validate source reference */
    if (!Val_IsValidChannelRef(header->source_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_INVALID_SOURCE_ID, "source_id",
            header->source_id, 0, lim->max_channel_id);
    }

    return Val_Success();
}

/*============================================================================
 * Digital Input Validation
 *============================================================================*/

ValidationResult_t Val_ValidateDigitalInput(
    const CfgDigitalInput_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Debounce range */
    if (config->debounce_ms > lim->max_debounce_ms) {
        return Val_Error(VAL_ERR_INPUT_INVALID_DEBOUNCE, "debounce_ms",
            config->debounce_ms, 0, lim->max_debounce_ms);
    }

    /* active_high is boolean (0 or 1) */
    if (config->active_high > 1) {
        return Val_Error(VAL_ERR_INVALID_FLAGS, "active_high",
            config->active_high, 0, 1);
    }

    /* use_pullup is boolean */
    if (config->use_pullup > 1) {
        return Val_Error(VAL_ERR_INVALID_FLAGS, "use_pullup",
            config->use_pullup, 0, 1);
    }

    return Val_Success();
}

/*============================================================================
 * Analog Input Validation
 *============================================================================*/

ValidationResult_t Val_ValidateAnalogInput(
    const CfgAnalogInput_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Raw range must be valid (can be inverted for negative slope) */
    if (config->raw_min == config->raw_max) {
        return Val_Error(VAL_ERR_INPUT_INVALID_RANGE, "raw_min/raw_max",
            config->raw_min, 0, 0);
    }

    /* Filter time */
    if (config->filter_ms > lim->max_filter_ms) {
        return Val_Error(VAL_ERR_INPUT_INVALID_FILTER_MS, "filter_ms",
            config->filter_ms, 0, lim->max_filter_ms);
    }

    /* Samples for averaging */
    if (config->samples > 0 && config->samples > lim->max_samples) {
        return Val_Error(VAL_ERR_INPUT_INVALID_SAMPLES, "samples",
            config->samples, 1, lim->max_samples);
    }

    return Val_Success();
}

/*============================================================================
 * Frequency Input Validation
 *============================================================================*/

ValidationResult_t Val_ValidateFrequencyInput(
    const CfgFrequencyInput_t* config,
    const ValidationLimits_t* limits)
{
    (void)limits;

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Frequency range */
    if (config->min_freq_hz >= config->max_freq_hz) {
        return Val_Error(VAL_ERR_INPUT_INVALID_RANGE, "min_freq_hz",
            config->min_freq_hz, 0, config->max_freq_hz);
    }

    /* Edge mode */
    if (config->edge_mode > 2) {
        return Val_Error(VAL_ERR_INPUT_INVALID_EDGE_MODE, "edge_mode",
            config->edge_mode, 0, 2);
    }

    /* Scale denominator cannot be zero */
    if (config->scale_den == 0) {
        return Val_Error(VAL_ERR_INPUT_ZERO_DIVISOR, "scale_den",
            0, 1, INT32_MAX);
    }

    return Val_Success();
}

/*============================================================================
 * CAN Input Validation
 *============================================================================*/

ValidationResult_t Val_ValidateCanInput(
    const CfgCanInput_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* CAN bus number */
    if (config->bus > lim->max_can_bus) {
        return Val_Error(VAL_ERR_CAN_INVALID_BUS, "bus",
            config->bus, 0, lim->max_can_bus);
    }

    /* CAN ID validation */
    if (config->is_extended) {
        if (config->can_id > 0x1FFFFFFF) {
            return Val_Error(VAL_ERR_CAN_INVALID_ID, "can_id",
                config->can_id, 0, 0x1FFFFFFF);
        }
    } else {
        if (config->can_id > 0x7FF) {
            return Val_Error(VAL_ERR_CAN_INVALID_ID, "can_id",
                config->can_id, 0, 0x7FF);
        }
    }

    /* Bit position validation */
    if (config->start_bit + config->bit_length > 64) {
        return Val_Error(VAL_ERR_CAN_INVALID_BIT_POS, "start_bit+bit_length",
            config->start_bit + config->bit_length, 0, 64);
    }

    /* Bit length must be > 0 */
    if (config->bit_length == 0 || config->bit_length > 32) {
        return Val_Error(VAL_ERR_CAN_INVALID_BIT_POS, "bit_length",
            config->bit_length, 1, 32);
    }

    /* Byte order */
    if (config->byte_order > 1) {
        return Val_Error(VAL_ERR_CAN_INVALID_BYTE_ORDER, "byte_order",
            config->byte_order, 0, 1);
    }

    /* Scale denominator */
    if (config->scale_den == 0) {
        return Val_Error(VAL_ERR_CAN_ZERO_DIVISOR, "scale_den",
            0, 1, INT16_MAX);
    }

    return Val_Success();
}

/*============================================================================
 * Power Output Validation
 *============================================================================*/

ValidationResult_t Val_ValidatePowerOutput(
    const CfgPowerOutput_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Current limit */
    if (config->current_limit_ma > lim->max_current_ma) {
        return Val_Error(VAL_ERR_OUTPUT_INVALID_CURRENT_LIMIT, "current_limit_ma",
            config->current_limit_ma, 0, lim->max_current_ma);
    }

    /* Inrush limit must be >= normal limit */
    if (config->inrush_limit_ma < config->current_limit_ma) {
        return Val_Error(VAL_ERR_OUTPUT_INVALID_INRUSH, "inrush_limit_ma",
            config->inrush_limit_ma, config->current_limit_ma, lim->max_current_ma);
    }

    /* PWM frequency (0 = DC, otherwise must be in range) */
    if (config->pwm_frequency > 0) {
        if (config->pwm_frequency < lim->min_pwm_freq ||
            config->pwm_frequency > lim->max_pwm_freq) {
            return Val_Error(VAL_ERR_OUTPUT_INVALID_PWM_FREQ, "pwm_frequency",
                config->pwm_frequency, lim->min_pwm_freq, lim->max_pwm_freq);
        }
    }

    /* Retry count */
    if (config->retry_count > 10) {
        return Val_Error(VAL_ERR_OUTPUT_INVALID_RETRY_COUNT, "retry_count",
            config->retry_count, 0, 10);
    }

    return Val_Success();
}

/*============================================================================
 * PWM Output Validation
 *============================================================================*/

ValidationResult_t Val_ValidatePwmOutput(
    const CfgPwmOutput_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* PWM frequency */
    if (config->frequency_hz < lim->min_pwm_freq ||
        config->frequency_hz > lim->max_pwm_freq) {
        return Val_Error(VAL_ERR_OUTPUT_INVALID_PWM_FREQ, "frequency_hz",
            config->frequency_hz, lim->min_pwm_freq, lim->max_pwm_freq);
    }

    /* Duty cycle range (0-10000 = 0-100%) */
    if (config->min_duty > config->max_duty) {
        return Val_Error(VAL_ERR_PWM_INVALID_DUTY_RANGE, "min_duty",
            config->min_duty, 0, config->max_duty);
    }

    if (config->max_duty > 10000) {
        return Val_Error(VAL_ERR_PWM_INVALID_DUTY_RANGE, "max_duty",
            config->max_duty, 0, 10000);
    }

    /* Default must be within range */
    if (config->default_duty < config->min_duty ||
        config->default_duty > config->max_duty) {
        return Val_Error(VAL_ERR_PWM_INVALID_DUTY_RANGE, "default_duty",
            config->default_duty, config->min_duty, config->max_duty);
    }

    return Val_Success();
}

/*============================================================================
 * H-Bridge Validation
 *============================================================================*/

ValidationResult_t Val_ValidateHBridge(
    const CfgHBridge_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* PWM frequency */
    if (config->frequency_hz < lim->min_pwm_freq ||
        config->frequency_hz > lim->max_pwm_freq) {
        return Val_Error(VAL_ERR_OUTPUT_INVALID_PWM_FREQ, "frequency_hz",
            config->frequency_hz, lim->min_pwm_freq, lim->max_pwm_freq);
    }

    /* Current limit */
    if (config->current_limit_ma > lim->max_current_ma) {
        return Val_Error(VAL_ERR_OUTPUT_INVALID_CURRENT_LIMIT, "current_limit_ma",
            config->current_limit_ma, 0, lim->max_current_ma);
    }

    /* Deadband (can be negative?) */
    if (config->deadband < 0 || config->deadband > 1000) {
        return Val_Error(VAL_ERR_HBRIDGE_INVALID_DEADBAND, "deadband",
            config->deadband, 0, 1000);
    }

    /* Accel/decel rates */
    if (config->accel_rate == 0) {
        return Val_Error(VAL_ERR_HBRIDGE_INVALID_RATE, "accel_rate",
            config->accel_rate, 1, 10000);
    }
    if (config->decel_rate == 0) {
        return Val_Error(VAL_ERR_HBRIDGE_INVALID_RATE, "decel_rate",
            config->decel_rate, 1, 10000);
    }

    return Val_Success();
}

/*============================================================================
 * CAN Output Validation
 *============================================================================*/

ValidationResult_t Val_ValidateCanOutput(
    const CfgCanOutput_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* CAN bus */
    if (config->bus > lim->max_can_bus) {
        return Val_Error(VAL_ERR_CAN_INVALID_BUS, "bus",
            config->bus, 0, lim->max_can_bus);
    }

    /* CAN ID */
    if (config->is_extended) {
        if (config->can_id > 0x1FFFFFFF) {
            return Val_Error(VAL_ERR_CAN_INVALID_ID, "can_id",
                config->can_id, 0, 0x1FFFFFFF);
        }
    } else {
        if (config->can_id > 0x7FF) {
            return Val_Error(VAL_ERR_CAN_INVALID_ID, "can_id",
                config->can_id, 0, 0x7FF);
        }
    }

    /* DLC */
    if (config->dlc == 0 || config->dlc > 8) {
        return Val_Error(VAL_ERR_CAN_INVALID_DLC, "dlc",
            config->dlc, 1, 8);
    }

    /* Bit position */
    if (config->start_bit + config->bit_length > config->dlc * 8) {
        return Val_Error(VAL_ERR_CAN_INVALID_BIT_POS, "start_bit+bit_length",
            config->start_bit + config->bit_length, 0, config->dlc * 8);
    }

    /* Scale denominator */
    if (config->scale_den == 0) {
        return Val_Error(VAL_ERR_CAN_ZERO_DIVISOR, "scale_den",
            0, 1, INT16_MAX);
    }

    return Val_Success();
}

/*============================================================================
 * Timer Validation
 *============================================================================*/

ValidationResult_t Val_ValidateTimer(
    const CfgTimer_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Timer mode */
    if (config->mode > TIMER_MODE_MONOSTABLE) {
        return Val_Error(VAL_ERR_TIMER_INVALID_MODE, "mode",
            config->mode, 0, TIMER_MODE_MONOSTABLE);
    }

    /* Trigger mode (0=level, 1=rising, 2=falling, 3=both) */
    if (config->trigger_mode > 3) {
        return Val_Error(VAL_ERR_TIMER_INVALID_TRIGGER_MODE, "trigger_mode",
            config->trigger_mode, 0, 3);
    }

    /* Trigger ID */
    if (!Val_IsValidChannelRef(config->trigger_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_TIMER_INVALID_TRIGGER_ID, "trigger_id",
            config->trigger_id, 0, lim->max_channel_id);
    }

    /* Delay */
    if (config->delay_ms == 0 && config->mode != TIMER_MODE_BLINK) {
        return Val_Error(VAL_ERR_TIMER_ZERO_DELAY, "delay_ms",
            0, 1, lim->max_delay_ms);
    }
    if (config->delay_ms > lim->max_delay_ms) {
        return Val_Error(VAL_ERR_TIMER_ZERO_DELAY, "delay_ms",
            config->delay_ms, 0, lim->max_delay_ms);
    }

    /* Blink times */
    if (config->mode == TIMER_MODE_BLINK) {
        if (config->on_time_ms == 0 || config->off_time_ms == 0) {
            return Val_Error(VAL_ERR_TIMER_INVALID_BLINK_TIMES, "on_time_ms/off_time_ms",
                0, 1, 60000);
        }
    }

    return Val_Success();
}

/*============================================================================
 * Logic Validation
 *============================================================================*/

ValidationResult_t Val_ValidateLogic(
    const CfgLogic_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Operation */
    if (config->operation > LOGIC_OP_OUTSIDE) {
        return Val_Error(VAL_ERR_LOGIC_INVALID_OPERATION, "operation",
            config->operation, 0, LOGIC_OP_OUTSIDE);
    }

    /* Input count */
    if (config->input_count == 0) {
        return Val_Error(VAL_ERR_LOGIC_NO_INPUTS, "input_count",
            0, 1, CFG_MAX_INPUTS);
    }
    if (config->input_count > CFG_MAX_INPUTS) {
        return Val_Error(VAL_ERR_LOGIC_TOO_MANY_INPUTS, "input_count",
            config->input_count, 1, CFG_MAX_INPUTS);
    }

    /* Multi-input operations need at least 2 inputs */
    if ((config->operation == LOGIC_OP_AND ||
         config->operation == LOGIC_OP_OR ||
         config->operation == LOGIC_OP_XOR) &&
        config->input_count < 2) {
        return Val_Error(VAL_ERR_LOGIC_INSUFFICIENT_INPUTS, "input_count",
            config->input_count, 2, CFG_MAX_INPUTS);
    }

    /* Validate input IDs */
    for (uint8_t i = 0; i < config->input_count; i++) {
        if (!Val_IsValidChannelRef(config->inputs[i], lim->max_channel_id)) {
            return Val_Error(VAL_ERR_LOGIC_INVALID_INPUT_ID, "inputs[]",
                config->inputs[i], 0, lim->max_channel_id);
        }
    }

    return Val_Success();
}

/*============================================================================
 * Math Validation
 *============================================================================*/

ValidationResult_t Val_ValidateMath(
    const CfgMath_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Operation */
    if (config->operation > MATH_OP_CLAMP) {
        return Val_Error(VAL_ERR_MATH_INVALID_OPERATION, "operation",
            config->operation, 0, MATH_OP_CLAMP);
    }

    /* Input count */
    if (config->input_count == 0) {
        return Val_Error(VAL_ERR_MATH_NO_INPUTS, "input_count",
            0, 1, CFG_MAX_INPUTS);
    }
    if (config->input_count > CFG_MAX_INPUTS) {
        return Val_Error(VAL_ERR_MATH_TOO_MANY_INPUTS, "input_count",
            config->input_count, 1, CFG_MAX_INPUTS);
    }

    /* Validate input IDs */
    for (uint8_t i = 0; i < config->input_count; i++) {
        if (!Val_IsValidChannelRef(config->inputs[i], lim->max_channel_id)) {
            return Val_Error(VAL_ERR_MATH_INVALID_INPUT_ID, "inputs[]",
                config->inputs[i], 0, lim->max_channel_id);
        }
    }

    /* Division check */
    if (config->operation == MATH_OP_DIV && config->constant == 0) {
        return Val_Error(VAL_ERR_MATH_ZERO_DIVISOR, "constant",
            0, 1, INT32_MAX);
    }

    /* Scale denominator */
    if (config->scale_den == 0) {
        return Val_Error(VAL_ERR_MATH_ZERO_DIVISOR, "scale_den",
            0, 1, INT16_MAX);
    }

    /* Clamp range */
    if (config->operation == MATH_OP_CLAMP && config->min_value >= config->max_value) {
        return Val_Error(VAL_ERR_MATH_INVALID_RANGE, "min_value",
            config->min_value, INT32_MIN, config->max_value - 1);
    }

    return Val_Success();
}

/*============================================================================
 * Table 2D Validation
 *============================================================================*/

ValidationResult_t Val_ValidateTable2D(
    const CfgTable2D_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Input ID */
    if (!Val_IsValidChannelRef(config->input_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_TABLE_INVALID_INPUT, "input_id",
            config->input_id, 0, lim->max_channel_id);
    }

    /* Point count */
    if (config->point_count < lim->min_table_points) {
        return Val_Error(VAL_ERR_TABLE_INSUFFICIENT_POINTS, "point_count",
            config->point_count, lim->min_table_points, CFG_MAX_TABLE_2D_SIZE);
    }
    if (config->point_count > CFG_MAX_TABLE_2D_SIZE) {
        return Val_Error(VAL_ERR_TABLE_TOO_MANY_POINTS, "point_count",
            config->point_count, lim->min_table_points, CFG_MAX_TABLE_2D_SIZE);
    }

    /* X values must be monotonically increasing */
    for (uint8_t i = 1; i < config->point_count; i++) {
        if (config->x_values[i] <= config->x_values[i-1]) {
            return Val_Error(VAL_ERR_TABLE_X_NOT_MONOTONIC, "x_values[]",
                i, 0, 0);
        }
    }

    return Val_Success();
}

/*============================================================================
 * Table 3D Validation
 *============================================================================*/

ValidationResult_t Val_ValidateTable3D(
    const CfgTable3D_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Input IDs */
    if (!Val_IsValidChannelRef(config->input_x_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_TABLE_INVALID_INPUT, "input_x_id",
            config->input_x_id, 0, lim->max_channel_id);
    }
    if (!Val_IsValidChannelRef(config->input_y_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_TABLE_3D_INVALID_Y_INPUT, "input_y_id",
            config->input_y_id, 0, lim->max_channel_id);
    }

    /* Axis sizes */
    if (config->x_count < lim->min_table_points) {
        return Val_Error(VAL_ERR_TABLE_3D_INSUFFICIENT_X, "x_count",
            config->x_count, lim->min_table_points, CFG_MAX_TABLE_3D_X);
    }
    if (config->y_count < lim->min_table_points) {
        return Val_Error(VAL_ERR_TABLE_3D_INSUFFICIENT_Y, "y_count",
            config->y_count, lim->min_table_points, CFG_MAX_TABLE_3D_Y);
    }
    if (config->x_count > CFG_MAX_TABLE_3D_X) {
        return Val_Error(VAL_ERR_TABLE_TOO_MANY_POINTS, "x_count",
            config->x_count, lim->min_table_points, CFG_MAX_TABLE_3D_X);
    }
    if (config->y_count > CFG_MAX_TABLE_3D_Y) {
        return Val_Error(VAL_ERR_TABLE_TOO_MANY_POINTS, "y_count",
            config->y_count, lim->min_table_points, CFG_MAX_TABLE_3D_Y);
    }

    /* X axis monotonic */
    for (uint8_t i = 1; i < config->x_count; i++) {
        if (config->x_values[i] <= config->x_values[i-1]) {
            return Val_Error(VAL_ERR_TABLE_X_NOT_MONOTONIC, "x_values[]",
                i, 0, 0);
        }
    }

    /* Y axis monotonic */
    for (uint8_t i = 1; i < config->y_count; i++) {
        if (config->y_values[i] <= config->y_values[i-1]) {
            return Val_Error(VAL_ERR_TABLE_X_NOT_MONOTONIC, "y_values[]",
                i, 0, 0);
        }
    }

    return Val_Success();
}

/*============================================================================
 * Filter Validation
 *============================================================================*/

ValidationResult_t Val_ValidateFilter(
    const CfgFilter_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Input ID */
    if (!Val_IsValidChannelRef(config->input_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_FILTER_INVALID_INPUT, "input_id",
            config->input_id, 0, lim->max_channel_id);
    }

    /* Filter type */
    if (config->filter_type > FILTER_TYPE_MEDIAN) {
        return Val_Error(VAL_ERR_FILTER_INVALID_TYPE, "filter_type",
            config->filter_type, 0, FILTER_TYPE_MEDIAN);
    }

    /* Window size for SMA/Median */
    if ((config->filter_type == FILTER_TYPE_SMA ||
         config->filter_type == FILTER_TYPE_MEDIAN) &&
        (config->window_size < 2 || config->window_size > lim->max_window_size)) {
        return Val_Error(VAL_ERR_FILTER_INVALID_WINDOW, "window_size",
            config->window_size, 2, lim->max_window_size);
    }

    /* Time constant for LPF */
    if (config->filter_type == FILTER_TYPE_LOWPASS &&
        config->time_constant_ms == 0) {
        return Val_Error(VAL_ERR_FILTER_ZERO_TIME_CONST, "time_constant_ms",
            0, 1, 60000);
    }

    return Val_Success();
}

/*============================================================================
 * PID Validation
 *============================================================================*/

ValidationResult_t Val_ValidatePid(
    const CfgPid_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Setpoint ID */
    if (!Val_IsValidChannelRef(config->setpoint_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_PID_INVALID_SETPOINT, "setpoint_id",
            config->setpoint_id, 0, lim->max_channel_id);
    }

    /* Feedback ID */
    if (!Val_IsValidChannelRef(config->feedback_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_PID_INVALID_FEEDBACK, "feedback_id",
            config->feedback_id, 0, lim->max_channel_id);
    }

    /* Output range */
    if (config->output_min >= config->output_max) {
        return Val_Error(VAL_ERR_PID_INVALID_OUTPUT_RANGE, "output_min",
            config->output_min, INT16_MIN, config->output_max - 1);
    }

    /* Integral range */
    if (config->integral_min >= config->integral_max) {
        return Val_Error(VAL_ERR_PID_INVALID_INTEGRAL_RANGE, "integral_min",
            config->integral_min, INT16_MIN, config->integral_max - 1);
    }

    return Val_Success();
}

/*============================================================================
 * Counter Validation
 *============================================================================*/

ValidationResult_t Val_ValidateCounter(
    const CfgCounter_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* At least one trigger must be valid */
    bool has_inc = Val_IsValidChannelRef(config->inc_trigger_id, lim->max_channel_id);
    bool has_dec = Val_IsValidChannelRef(config->dec_trigger_id, lim->max_channel_id);
    bool has_reset = Val_IsValidChannelRef(config->reset_trigger_id, lim->max_channel_id);

    if (!has_inc && !has_dec && !has_reset) {
        return Val_Error(VAL_ERR_COUNTER_INVALID_TRIGGER, "triggers",
            0, 0, 0);
    }

    /* Value range */
    if (config->min_value >= config->max_value) {
        return Val_Error(VAL_ERR_COUNTER_INVALID_RANGE, "min_value",
            config->min_value, INT16_MIN, config->max_value - 1);
    }

    /* Step */
    if (config->step == 0) {
        return Val_Error(VAL_ERR_COUNTER_ZERO_STEP, "step",
            0, 1, INT16_MAX);
    }

    /* Initial value in range */
    if (config->initial_value < config->min_value ||
        config->initial_value > config->max_value) {
        return Val_Error(VAL_ERR_COUNTER_INVALID_RANGE, "initial_value",
            config->initial_value, config->min_value, config->max_value);
    }

    return Val_Success();
}

/*============================================================================
 * FlipFlop Validation
 *============================================================================*/

ValidationResult_t Val_ValidateFlipFlop(
    const CfgFlipFlop_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* FlipFlop type */
    if (config->ff_type > FF_TYPE_D_LATCH) {
        return Val_Error(VAL_ERR_FF_INVALID_TYPE, "ff_type",
            config->ff_type, 0, FF_TYPE_D_LATCH);
    }

    /* Input validation depends on type */
    switch (config->ff_type) {
        case FF_TYPE_SR:
        case FF_TYPE_SR_LATCH:
            /* Need S and R inputs */
            if (!Val_IsValidChannelRef(config->set_input_id, lim->max_channel_id) ||
                !Val_IsValidChannelRef(config->reset_input_id, lim->max_channel_id)) {
                return Val_Error(VAL_ERR_FF_INVALID_INPUT, "set/reset_input_id",
                    0, 0, 0);
            }
            break;

        case FF_TYPE_D:
        case FF_TYPE_D_LATCH:
            /* Need D and clock/enable */
            if (!Val_IsValidChannelRef(config->set_input_id, lim->max_channel_id) ||
                !Val_IsValidChannelRef(config->clock_input_id, lim->max_channel_id)) {
                return Val_Error(VAL_ERR_FF_INVALID_INPUT, "set/clock_input_id",
                    0, 0, 0);
            }
            break;

        case FF_TYPE_T:
            /* Need toggle input */
            if (!Val_IsValidChannelRef(config->set_input_id, lim->max_channel_id)) {
                return Val_Error(VAL_ERR_FF_INVALID_INPUT, "set_input_id",
                    0, 0, 0);
            }
            break;

        case FF_TYPE_JK:
            /* Need J, K, and clock */
            if (!Val_IsValidChannelRef(config->set_input_id, lim->max_channel_id) ||
                !Val_IsValidChannelRef(config->reset_input_id, lim->max_channel_id) ||
                !Val_IsValidChannelRef(config->clock_input_id, lim->max_channel_id)) {
                return Val_Error(VAL_ERR_FF_INVALID_INPUT, "set/reset/clock_input_id",
                    0, 0, 0);
            }
            break;

        default:
            break;
    }

    return Val_Success();
}

/*============================================================================
 * Hysteresis Validation
 *============================================================================*/

ValidationResult_t Val_ValidateHysteresis(
    const CfgHysteresis_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Input ID */
    if (!Val_IsValidChannelRef(config->input_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_HYST_INVALID_INPUT, "input_id",
            config->input_id, 0, lim->max_channel_id);
    }

    /* Hysteresis type */
    if (config->hyst_type > HYST_TYPE_MULTILEVEL) {
        return Val_Error(VAL_ERR_HYST_INVALID_TYPE, "hyst_type",
            config->hyst_type, 0, HYST_TYPE_MULTILEVEL);
    }

    /* Thresholds */
    if (config->threshold_low >= config->threshold_high) {
        return Val_Error(VAL_ERR_HYST_INVALID_THRESHOLDS, "threshold_low",
            config->threshold_low, INT32_MIN, config->threshold_high - 1);
    }

    return Val_Success();
}

/*============================================================================
 * Switch Validation
 *============================================================================*/

ValidationResult_t Val_ValidateSwitch(
    const CfgSwitch_t* config,
    const ValidationLimits_t* limits)
{
    const ValidationLimits_t* lim = get_limits(limits);

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Selector ID */
    if (!Val_IsValidChannelRef(config->selector_id, lim->max_channel_id)) {
        return Val_Error(VAL_ERR_SWITCH_INVALID_SELECTOR, "selector_id",
            config->selector_id, 0, lim->max_channel_id);
    }

    /* Case count */
    if (config->case_count == 0) {
        return Val_Error(VAL_ERR_SWITCH_NO_CASES, "case_count",
            0, 1, CFG_MAX_SWITCH_CASES);
    }
    if (config->case_count > CFG_MAX_SWITCH_CASES) {
        return Val_Error(VAL_ERR_SWITCH_TOO_MANY_CASES, "case_count",
            config->case_count, 1, CFG_MAX_SWITCH_CASES);
    }

    /* Mode */
    if (config->mode > 2) {
        return Val_Error(VAL_ERR_SWITCH_INVALID_MODE, "mode",
            config->mode, 0, 2);
    }

    return Val_Success();
}

/*============================================================================
 * Number Validation
 *============================================================================*/

ValidationResult_t Val_ValidateNumber(
    const CfgNumber_t* config,
    const ValidationLimits_t* limits)
{
    (void)limits;

    if (!config) {
        return Val_Error(VAL_ERR_INVALID_TYPE, "config", 0, 0, 0);
    }

    /* Range */
    if (config->min_value >= config->max_value) {
        return Val_Error(VAL_ERR_NUMBER_INVALID_RANGE, "min_value",
            config->min_value, INT32_MIN, config->max_value - 1);
    }

    /* Step (0 means not adjustable by user) */
    if (!config->readonly && config->step == 0) {
        return Val_Error(VAL_ERR_NUMBER_ZERO_STEP, "step",
            0, 1, INT32_MAX);
    }

    /* Value in range */
    if (config->value < config->min_value || config->value > config->max_value) {
        return Val_Error(VAL_ERR_NUMBER_VALUE_OUT_OF_RANGE, "value",
            config->value, config->min_value, config->max_value);
    }

    return Val_Success();
}

/*============================================================================
 * Full Channel Validation
 *============================================================================*/

ValidationResult_t Val_ValidateChannel(
    const CfgChannelHeader_t* header,
    const void* config,
    const char* name,
    const ValidationLimits_t* limits)
{
    ValidationResult_t result;

    /* Validate header first */
    result = Val_ValidateHeader(header, limits);
    if (result.error != VAL_OK) {
        return result;
    }

    /* Validate name if provided */
    if (name && header->name_len > 0) {
        size_t actual_len = strlen(name);
        if (actual_len != header->name_len) {
            return Val_Error(VAL_ERR_NAME_TOO_LONG, "name",
                actual_len, header->name_len, header->name_len);
        }
    }

    /* Type-specific validation */
    if (config == NULL) {
        return Val_Success();  /* No config to validate */
    }

    switch ((ChannelType_t)header->type) {
        case CH_TYPE_DIGITAL_INPUT:
            return Val_ValidateDigitalInput((const CfgDigitalInput_t*)config, limits);

        case CH_TYPE_ANALOG_INPUT:
            return Val_ValidateAnalogInput((const CfgAnalogInput_t*)config, limits);

        case CH_TYPE_FREQUENCY_INPUT:
            return Val_ValidateFrequencyInput((const CfgFrequencyInput_t*)config, limits);

        case CH_TYPE_CAN_INPUT:
            return Val_ValidateCanInput((const CfgCanInput_t*)config, limits);

        case CH_TYPE_POWER_OUTPUT:
            return Val_ValidatePowerOutput((const CfgPowerOutput_t*)config, limits);

        case CH_TYPE_PWM_OUTPUT:
            return Val_ValidatePwmOutput((const CfgPwmOutput_t*)config, limits);

        case CH_TYPE_HBRIDGE:
            return Val_ValidateHBridge((const CfgHBridge_t*)config, limits);

        case CH_TYPE_CAN_OUTPUT:
            return Val_ValidateCanOutput((const CfgCanOutput_t*)config, limits);

        case CH_TYPE_TIMER:
            return Val_ValidateTimer((const CfgTimer_t*)config, limits);

        case CH_TYPE_LOGIC:
            return Val_ValidateLogic((const CfgLogic_t*)config, limits);

        case CH_TYPE_MATH:
            return Val_ValidateMath((const CfgMath_t*)config, limits);

        case CH_TYPE_TABLE_2D:
            return Val_ValidateTable2D((const CfgTable2D_t*)config, limits);

        case CH_TYPE_TABLE_3D:
            return Val_ValidateTable3D((const CfgTable3D_t*)config, limits);

        case CH_TYPE_FILTER:
            return Val_ValidateFilter((const CfgFilter_t*)config, limits);

        case CH_TYPE_PID:
            return Val_ValidatePid((const CfgPid_t*)config, limits);

        case CH_TYPE_COUNTER:
            return Val_ValidateCounter((const CfgCounter_t*)config, limits);

        case CH_TYPE_FLIPFLOP:
            return Val_ValidateFlipFlop((const CfgFlipFlop_t*)config, limits);

        case CH_TYPE_HYSTERESIS:
            return Val_ValidateHysteresis((const CfgHysteresis_t*)config, limits);

        case CH_TYPE_SWITCH:
            return Val_ValidateSwitch((const CfgSwitch_t*)config, limits);

        case CH_TYPE_NUMBER:
            return Val_ValidateNumber((const CfgNumber_t*)config, limits);

        default:
            return Val_Error(VAL_ERR_INVALID_TYPE, "type",
                header->type, 0, CH_TYPE_NUMBER);
    }
}

/*============================================================================
 * Error Messages
 *============================================================================*/

const char* Val_GetErrorMessage(ValidationError_t error)
{
    switch (error) {
        case VAL_OK: return "OK";
        case VAL_ERR_INVALID_TYPE: return "Invalid channel type";
        case VAL_ERR_INVALID_ID: return "Invalid channel ID";
        case VAL_ERR_NAME_TOO_LONG: return "Name too long";
        case VAL_ERR_EMPTY_NAME: return "Name cannot be empty";
        case VAL_ERR_INVALID_FLAGS: return "Invalid flags";
        case VAL_ERR_INVALID_HW_DEVICE: return "Invalid hardware device";
        case VAL_ERR_INVALID_HW_INDEX: return "Invalid hardware index";
        case VAL_ERR_INVALID_SOURCE_ID: return "Invalid source channel ID";
        case VAL_ERR_CONFIG_SIZE_MISMATCH: return "Config size mismatch";

        case VAL_ERR_INPUT_INVALID_DEBOUNCE: return "Invalid debounce time";
        case VAL_ERR_INPUT_INVALID_FILTER_MS: return "Invalid filter time";
        case VAL_ERR_INPUT_INVALID_FILTER_TYPE: return "Invalid filter type";
        case VAL_ERR_INPUT_INVALID_SAMPLES: return "Invalid sample count";
        case VAL_ERR_INPUT_INVALID_RANGE: return "Invalid input range";
        case VAL_ERR_INPUT_INVALID_TIMEOUT: return "Invalid timeout";
        case VAL_ERR_INPUT_INVALID_EDGE_MODE: return "Invalid edge mode";
        case VAL_ERR_INPUT_ZERO_DIVISOR: return "Scale divisor cannot be zero";

        case VAL_ERR_CAN_INVALID_BUS: return "Invalid CAN bus number";
        case VAL_ERR_CAN_INVALID_ID: return "Invalid CAN message ID";
        case VAL_ERR_CAN_INVALID_DLC: return "Invalid CAN DLC";
        case VAL_ERR_CAN_INVALID_BIT_POS: return "Invalid bit position";
        case VAL_ERR_CAN_INVALID_BYTE_ORDER: return "Invalid byte order";
        case VAL_ERR_CAN_ZERO_DIVISOR: return "Scale divisor cannot be zero";
        case VAL_ERR_CAN_INVALID_PERIOD: return "Invalid transmit period";

        case VAL_ERR_OUTPUT_INVALID_CURRENT_LIMIT: return "Invalid current limit";
        case VAL_ERR_OUTPUT_INVALID_PWM_FREQ: return "Invalid PWM frequency";
        case VAL_ERR_OUTPUT_INVALID_RETRY_COUNT: return "Invalid retry count";
        case VAL_ERR_OUTPUT_INVALID_SOFT_START: return "Invalid soft start time";
        case VAL_ERR_OUTPUT_INVALID_INRUSH: return "Invalid inrush limit";
        case VAL_ERR_PWM_INVALID_DUTY_RANGE: return "Invalid duty cycle range";
        case VAL_ERR_HBRIDGE_INVALID_DEADBAND: return "Invalid deadband";
        case VAL_ERR_HBRIDGE_INVALID_RATE: return "Invalid accel/decel rate";

        case VAL_ERR_LOGIC_INVALID_OPERATION: return "Invalid logic operation";
        case VAL_ERR_LOGIC_NO_INPUTS: return "Logic channel needs inputs";
        case VAL_ERR_LOGIC_TOO_MANY_INPUTS: return "Too many inputs";
        case VAL_ERR_LOGIC_INVALID_INPUT_ID: return "Invalid input channel ID";
        case VAL_ERR_LOGIC_INSUFFICIENT_INPUTS: return "Insufficient inputs for operation";
        case VAL_ERR_MATH_INVALID_OPERATION: return "Invalid math operation";
        case VAL_ERR_MATH_NO_INPUTS: return "Math channel needs inputs";
        case VAL_ERR_MATH_TOO_MANY_INPUTS: return "Too many inputs";
        case VAL_ERR_MATH_INVALID_INPUT_ID: return "Invalid input channel ID";
        case VAL_ERR_MATH_ZERO_DIVISOR: return "Division by zero";
        case VAL_ERR_MATH_INVALID_RANGE: return "Invalid min/max range";

        case VAL_ERR_TIMER_INVALID_MODE: return "Invalid timer mode";
        case VAL_ERR_TIMER_INVALID_TRIGGER_MODE: return "Invalid trigger mode";
        case VAL_ERR_TIMER_INVALID_TRIGGER_ID: return "Invalid trigger channel";
        case VAL_ERR_TIMER_ZERO_DELAY: return "Timer delay must be > 0";
        case VAL_ERR_TIMER_INVALID_BLINK_TIMES: return "Blink times must be > 0";

        case VAL_ERR_TABLE_INVALID_INPUT: return "Invalid table input";
        case VAL_ERR_TABLE_INSUFFICIENT_POINTS: return "Need at least 2 table points";
        case VAL_ERR_TABLE_TOO_MANY_POINTS: return "Too many table points";
        case VAL_ERR_TABLE_X_NOT_MONOTONIC: return "X values must be ascending";
        case VAL_ERR_TABLE_3D_INVALID_Y_INPUT: return "Invalid Y input";
        case VAL_ERR_TABLE_3D_INSUFFICIENT_X: return "Need at least 2 X points";
        case VAL_ERR_TABLE_3D_INSUFFICIENT_Y: return "Need at least 2 Y points";

        case VAL_ERR_FILTER_INVALID_INPUT: return "Invalid filter input";
        case VAL_ERR_FILTER_INVALID_TYPE: return "Invalid filter type";
        case VAL_ERR_FILTER_INVALID_WINDOW: return "Invalid window size";
        case VAL_ERR_FILTER_INVALID_ALPHA: return "Invalid alpha value";
        case VAL_ERR_FILTER_ZERO_TIME_CONST: return "Time constant must be > 0";

        case VAL_ERR_PID_INVALID_SETPOINT: return "Invalid setpoint channel";
        case VAL_ERR_PID_INVALID_FEEDBACK: return "Invalid feedback channel";
        case VAL_ERR_PID_INVALID_OUTPUT_RANGE: return "Invalid output range";
        case VAL_ERR_PID_INVALID_INTEGRAL_RANGE: return "Invalid integral range";

        case VAL_ERR_COUNTER_INVALID_TRIGGER: return "Counter needs at least one trigger";
        case VAL_ERR_COUNTER_INVALID_RANGE: return "Invalid counter range";
        case VAL_ERR_COUNTER_ZERO_STEP: return "Counter step must be > 0";

        case VAL_ERR_FF_INVALID_TYPE: return "Invalid flipflop type";
        case VAL_ERR_FF_INVALID_INPUT: return "Invalid flipflop input";

        case VAL_ERR_HYST_INVALID_INPUT: return "Invalid hysteresis input";
        case VAL_ERR_HYST_INVALID_TYPE: return "Invalid hysteresis type";
        case VAL_ERR_HYST_INVALID_THRESHOLDS: return "Low threshold must be < high";

        case VAL_ERR_SWITCH_INVALID_SELECTOR: return "Invalid selector channel";
        case VAL_ERR_SWITCH_NO_CASES: return "Switch needs at least one case";
        case VAL_ERR_SWITCH_TOO_MANY_CASES: return "Too many switch cases";
        case VAL_ERR_SWITCH_INVALID_MODE: return "Invalid switch mode";

        case VAL_ERR_NUMBER_INVALID_RANGE: return "Invalid number range";
        case VAL_ERR_NUMBER_ZERO_STEP: return "Step must be > 0 for adjustable numbers";
        case VAL_ERR_NUMBER_VALUE_OUT_OF_RANGE: return "Value out of range";

        default: return "Unknown validation error";
    }
}

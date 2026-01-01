/**
 * @file channel_config.h
 * @brief PMU-30 Binary Channel Configuration Format
 *
 * Defines binary configuration structures for all channel types.
 * These structures are serialized to/from binary format for storage
 * and transmission.
 *
 * Design principles:
 * - Packed structures for minimal size
 * - Fixed sizes where possible
 * - No pointers (can be directly serialized)
 * - Compatible with Logic Engine structures
 *
 * @version 2.0
 * @date January 2026
 */

#ifndef PMU_CHANNEL_CONFIG_H
#define PMU_CHANNEL_CONFIG_H

#include <stdint.h>
#include <stdbool.h>
#include "channel_types.h"
#include "engine/engine.h"

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Configuration Version & Magic
 *============================================================================*/

#define CFG_MAGIC           0x43464733  /* "CFG3" */
#define CFG_VERSION         2

/*============================================================================
 * Maximum Limits
 *============================================================================*/

#define CFG_MAX_INPUTS          8       /**< Max inputs for logic/math */
#define CFG_MAX_NAME_LEN        31      /**< Max channel name (+ null) */
#define CFG_MAX_UNIT_LEN        7       /**< Max unit string (+ null) */
#define CFG_MAX_TABLE_2D_SIZE   16      /**< Max 2D table points */
#define CFG_MAX_TABLE_3D_X      8       /**< Max 3D table X axis */
#define CFG_MAX_TABLE_3D_Y      8       /**< Max 3D table Y axis */
#define CFG_MAX_SWITCH_CASES    8       /**< Max switch cases */
#define CFG_MAX_ENUM_VALUES     16      /**< Max enum values */

/*============================================================================
 * Channel Header (common for all types)
 *============================================================================*/

/**
 * Binary channel header (14 bytes)
 * Followed by type-specific config data
 */
typedef struct __attribute__((packed)) {
    uint16_t id;                /**< Channel ID (unique) */
    uint8_t  type;              /**< ChannelType_t */
    uint8_t  flags;             /**< ChannelFlags_t bitmask */
    uint8_t  hw_device;         /**< HwDevice_t */
    uint8_t  hw_index;          /**< Hardware index/pin */
    uint16_t source_id;         /**< Primary source channel (CH_REF_NONE if none) */
    int32_t  default_value;     /**< Default/initial value */
    uint8_t  name_len;          /**< Name length (0-31) */
    uint8_t  config_size;       /**< Type-specific config size */
} CfgChannelHeader_t;

_Static_assert(sizeof(CfgChannelHeader_t) == 14, "CfgChannelHeader_t must be 14 bytes");

/*============================================================================
 * Digital Input Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint8_t  active_high;       /**< 1 = active high, 0 = active low */
    uint8_t  use_pullup;        /**< Enable internal pull-up */
    uint16_t debounce_ms;       /**< Debounce time (ms) */
} CfgDigitalInput_t;

_Static_assert(sizeof(CfgDigitalInput_t) == 4, "CfgDigitalInput_t size check");

/*============================================================================
 * Analog Input Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    int32_t  raw_min;           /**< Raw ADC min value */
    int32_t  raw_max;           /**< Raw ADC max value */
    int32_t  scaled_min;        /**< Scaled output min */
    int32_t  scaled_max;        /**< Scaled output max */
    uint16_t filter_ms;         /**< Filter time constant (ms) */
    uint8_t  filter_type;       /**< Filter type (EMA, SMA, etc.) */
    uint8_t  samples;           /**< Averaging samples (for SMA) */
} CfgAnalogInput_t;

_Static_assert(sizeof(CfgAnalogInput_t) == 20, "CfgAnalogInput_t size check");

/*============================================================================
 * Frequency Input Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint32_t min_freq_hz;       /**< Minimum measurable frequency */
    uint32_t max_freq_hz;       /**< Maximum measurable frequency */
    uint16_t timeout_ms;        /**< Zero-detect timeout */
    uint8_t  edge_mode;         /**< 0=rising, 1=falling, 2=both */
    uint8_t  pulses_per_rev;    /**< Pulses per revolution (for RPM) */
    int32_t  scale_num;         /**< Scale numerator */
    int32_t  scale_den;         /**< Scale denominator */
} CfgFrequencyInput_t;

_Static_assert(sizeof(CfgFrequencyInput_t) == 20, "CfgFrequencyInput_t size check");

/*============================================================================
 * CAN Input Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint32_t can_id;            /**< CAN message ID */
    uint8_t  bus;               /**< CAN bus number (0-3) */
    uint8_t  start_bit;         /**< Start bit position */
    uint8_t  bit_length;        /**< Bit length */
    uint8_t  byte_order;        /**< 0=little-endian, 1=big-endian */
    uint8_t  is_signed;         /**< Signed value */
    uint8_t  is_extended;       /**< Extended CAN ID */
    int16_t  scale_num;         /**< Scale factor numerator */
    int16_t  scale_den;         /**< Scale factor denominator */
    int16_t  offset;            /**< Value offset */
    uint16_t timeout_ms;        /**< Timeout for signal loss */
} CfgCanInput_t;

_Static_assert(sizeof(CfgCanInput_t) == 18, "CfgCanInput_t size check");

/*============================================================================
 * Power Output Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t current_limit_ma;  /**< Current limit (mA) */
    uint16_t inrush_time_ms;    /**< Inrush current time (ms) */
    uint16_t inrush_limit_ma;   /**< Inrush current limit (mA) */
    uint8_t  retry_count;       /**< Auto-retry count on fault */
    uint8_t  retry_delay_s;     /**< Delay between retries (seconds) */
    uint16_t pwm_frequency;     /**< PWM frequency (Hz, 0=DC) */
    uint8_t  soft_start_ms;     /**< Soft start ramp time (ms) */
    uint8_t  flags;             /**< Output flags */
} CfgPowerOutput_t;

_Static_assert(sizeof(CfgPowerOutput_t) == 12, "CfgPowerOutput_t size check");

/*============================================================================
 * PWM Output Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t frequency_hz;      /**< PWM frequency */
    uint16_t min_duty;          /**< Minimum duty cycle (0-10000 = 0-100%) */
    uint16_t max_duty;          /**< Maximum duty cycle */
    uint16_t default_duty;      /**< Default duty cycle */
    uint8_t  invert;            /**< Invert output */
    uint8_t  reserved;
} CfgPwmOutput_t;

_Static_assert(sizeof(CfgPwmOutput_t) == 10, "CfgPwmOutput_t size check");

/*============================================================================
 * H-Bridge Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t frequency_hz;      /**< PWM frequency */
    uint16_t current_limit_ma;  /**< Current limit (mA) */
    uint16_t accel_rate;        /**< Acceleration rate (%/s) */
    uint16_t decel_rate;        /**< Deceleration rate (%/s) */
    int16_t  deadband;          /**< Deadband around zero */
    uint8_t  brake_mode;        /**< Brake mode (coast/brake) */
    uint8_t  flags;
} CfgHBridge_t;

_Static_assert(sizeof(CfgHBridge_t) == 12, "CfgHBridge_t size check");

/*============================================================================
 * CAN Output Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint32_t can_id;            /**< CAN message ID */
    uint8_t  bus;               /**< CAN bus number */
    uint8_t  dlc;               /**< Data length code */
    uint8_t  start_bit;         /**< Start bit for value */
    uint8_t  bit_length;        /**< Bit length for value */
    uint8_t  byte_order;        /**< 0=little-endian, 1=big-endian */
    uint8_t  is_extended;       /**< Extended CAN ID */
    uint16_t period_ms;         /**< Transmit period (0=on-change) */
    int16_t  scale_num;         /**< Scale factor numerator */
    int16_t  scale_den;         /**< Scale factor denominator */
    int16_t  offset;            /**< Value offset */
} CfgCanOutput_t;

_Static_assert(sizeof(CfgCanOutput_t) == 18, "CfgCanOutput_t size check");

/*============================================================================
 * Timer Configuration (matches Timer_Config_t)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint8_t  mode;              /**< TimerMode_t */
    uint8_t  trigger_mode;      /**< TimerTrigger_t */
    uint16_t trigger_id;        /**< Trigger source channel */
    uint32_t delay_ms;          /**< Delay/pulse time */
    uint16_t on_time_ms;        /**< On time for BLINK mode */
    uint16_t off_time_ms;       /**< Off time for BLINK mode */
    uint8_t  auto_reset;        /**< Auto-reset after expire */
    uint8_t  reserved[3];
} CfgTimer_t;

_Static_assert(sizeof(CfgTimer_t) == 16, "CfgTimer_t size check");

/*============================================================================
 * Logic Configuration (matches Logic Engine)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint8_t  operation;         /**< LogicOp_t */
    uint8_t  input_count;       /**< Number of inputs (1-8) */
    uint16_t inputs[CFG_MAX_INPUTS]; /**< Input channel IDs */
    int32_t  compare_value;     /**< For comparison ops */
    uint8_t  invert_output;     /**< Invert result */
    uint8_t  reserved[3];
} CfgLogic_t;

_Static_assert(sizeof(CfgLogic_t) == 24, "CfgLogic_t size check");

/*============================================================================
 * Math Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint8_t  operation;         /**< MathOp_t */
    uint8_t  input_count;       /**< Number of inputs */
    uint16_t inputs[CFG_MAX_INPUTS]; /**< Input channel IDs */
    int32_t  constant;          /**< Constant operand (if needed) */
    int32_t  min_value;         /**< Clamp minimum */
    int32_t  max_value;         /**< Clamp maximum */
    int16_t  scale_num;         /**< Output scale numerator */
    int16_t  scale_den;         /**< Output scale denominator */
} CfgMath_t;

_Static_assert(sizeof(CfgMath_t) == 32, "CfgMath_t size check");

/*============================================================================
 * 2D Table Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t input_id;          /**< Input channel ID */
    uint8_t  point_count;       /**< Number of points (2-16) */
    uint8_t  reserved;
    int16_t  x_values[CFG_MAX_TABLE_2D_SIZE];  /**< X axis values */
    int16_t  y_values[CFG_MAX_TABLE_2D_SIZE];  /**< Y axis values */
} CfgTable2D_t;

_Static_assert(sizeof(CfgTable2D_t) == 68, "CfgTable2D_t size check");

/*============================================================================
 * 3D Table Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t input_x_id;        /**< X input channel ID */
    uint16_t input_y_id;        /**< Y input channel ID */
    uint8_t  x_count;           /**< X axis size (2-8) */
    uint8_t  y_count;           /**< Y axis size (2-8) */
    uint8_t  reserved[2];
    int16_t  x_values[CFG_MAX_TABLE_3D_X];     /**< X axis values */
    int16_t  y_values[CFG_MAX_TABLE_3D_Y];     /**< Y axis values */
    int16_t  z_values[CFG_MAX_TABLE_3D_Y][CFG_MAX_TABLE_3D_X]; /**< Z values */
} CfgTable3D_t;

_Static_assert(sizeof(CfgTable3D_t) == 168, "CfgTable3D_t size check");

/*============================================================================
 * Filter Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t input_id;          /**< Input channel ID */
    uint8_t  filter_type;       /**< FilterType_t */
    uint8_t  window_size;       /**< Window size (for SMA/Median) */
    uint16_t time_constant_ms;  /**< Time constant (for LPF) */
    uint8_t  alpha;             /**< Alpha (for EMA, 0-255) */
    uint8_t  reserved;
} CfgFilter_t;

_Static_assert(sizeof(CfgFilter_t) == 8, "CfgFilter_t size check");

/*============================================================================
 * PID Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t setpoint_id;       /**< Setpoint channel ID */
    uint16_t feedback_id;       /**< Feedback/measurement channel ID */
    int16_t  kp;                /**< Proportional gain (scaled by 1000) */
    int16_t  ki;                /**< Integral gain (scaled by 1000) */
    int16_t  kd;                /**< Derivative gain (scaled by 1000) */
    int16_t  output_min;        /**< Output minimum */
    int16_t  output_max;        /**< Output maximum */
    int16_t  integral_min;      /**< Integral min (anti-windup) */
    int16_t  integral_max;      /**< Integral max (anti-windup) */
    int16_t  deadband;          /**< Error deadband */
    uint8_t  d_on_measurement;  /**< D term on measurement */
    uint8_t  reserved;
} CfgPid_t;

_Static_assert(sizeof(CfgPid_t) == 22, "CfgPid_t size check");

/*============================================================================
 * Number (Constant) Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    int32_t  value;             /**< Constant value */
    int32_t  min_value;         /**< Minimum (for user adjustment) */
    int32_t  max_value;         /**< Maximum (for user adjustment) */
    int32_t  step;              /**< Adjustment step */
    uint8_t  readonly;          /**< Not adjustable by user */
    uint8_t  save_to_flash;     /**< Persist value changes */
    uint8_t  reserved[2];
} CfgNumber_t;

_Static_assert(sizeof(CfgNumber_t) == 20, "CfgNumber_t size check");

/*============================================================================
 * Switch/Selector Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t selector_id;       /**< Selector input channel ID */
    uint8_t  case_count;        /**< Number of cases */
    uint8_t  mode;              /**< 0=value match, 1=range match, 2=index */
    struct __attribute__((packed)) {
        int32_t  match_value;   /**< Value to match (or min for range) */
        int32_t  max_value;     /**< Max for range mode */
        int32_t  result;        /**< Output value */
    } cases[CFG_MAX_SWITCH_CASES];
    int32_t  default_value;     /**< Default output */
} CfgSwitch_t;

_Static_assert(sizeof(CfgSwitch_t) == 104, "CfgSwitch_t size check");

/*============================================================================
 * Counter Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t inc_trigger_id;    /**< Increment trigger channel */
    uint16_t dec_trigger_id;    /**< Decrement trigger channel */
    uint16_t reset_trigger_id;  /**< Reset trigger channel */
    int16_t  initial_value;     /**< Initial value */
    int16_t  min_value;         /**< Minimum value */
    int16_t  max_value;         /**< Maximum value */
    int16_t  step;              /**< Step size */
    uint8_t  wrap;              /**< Wrap around at limits */
    uint8_t  edge_mode;         /**< Trigger on edge (vs level) */
} CfgCounter_t;

_Static_assert(sizeof(CfgCounter_t) == 18, "CfgCounter_t size check");

/*============================================================================
 * FlipFlop Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint8_t  ff_type;           /**< FlipFlopType_t */
    uint8_t  reserved;
    uint16_t set_input_id;      /**< S/D/J input channel */
    uint16_t reset_input_id;    /**< R/K input channel */
    uint16_t clock_input_id;    /**< Clock/Enable input channel */
    uint8_t  initial_state;     /**< Initial Q state */
    uint8_t  reserved2[3];
} CfgFlipFlop_t;

_Static_assert(sizeof(CfgFlipFlop_t) == 12, "CfgFlipFlop_t size check");

/*============================================================================
 * Hysteresis Configuration
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t input_id;          /**< Input channel ID */
    uint8_t  hyst_type;         /**< HysteresisType_t */
    uint8_t  invert;            /**< Invert output */
    int32_t  threshold_high;    /**< Upper threshold */
    int32_t  threshold_low;     /**< Lower threshold */
} CfgHysteresis_t;

_Static_assert(sizeof(CfgHysteresis_t) == 12, "CfgHysteresis_t size check");

/*============================================================================
 * Display Settings (for any channel)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    char     unit[CFG_MAX_UNIT_LEN + 1];  /**< Unit string */
    uint8_t  decimal_places;    /**< Decimal places for display */
    int32_t  display_min;       /**< Minimum display value */
    int32_t  display_max;       /**< Maximum display value */
    uint8_t  color_index;       /**< Color scheme index */
    uint8_t  reserved[3];
} CfgDisplay_t;

_Static_assert(sizeof(CfgDisplay_t) == 20, "CfgDisplay_t size check");

/*============================================================================
 * Complete Configuration File Header
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint32_t magic;             /**< CFG_MAGIC */
    uint16_t version;           /**< CFG_VERSION */
    uint16_t device_type;       /**< Target device type */
    uint32_t total_size;        /**< Total file size (bytes) */
    uint32_t crc32;             /**< CRC-32 of everything after header */
    uint16_t channel_count;     /**< Number of channel entries */
    uint16_t flags;             /**< Configuration flags */
    uint32_t timestamp;         /**< Unix timestamp of creation */
    uint8_t  reserved[8];       /**< Reserved for future use */
} CfgFileHeader_t;

_Static_assert(sizeof(CfgFileHeader_t) == 32, "CfgFileHeader_t must be 32 bytes");

/*============================================================================
 * Configuration Flags
 *============================================================================*/

typedef enum {
    CFG_FLAG_COMPRESSED     = 0x0001,   /**< Payload is compressed */
    CFG_FLAG_ENCRYPTED      = 0x0002,   /**< Payload is encrypted */
    CFG_FLAG_PARTIAL        = 0x0004,   /**< Partial config (update only) */
    CFG_FLAG_DEFAULTS       = 0x0008,   /**< Contains only defaults */
} CfgFlags_t;

/*============================================================================
 * API Functions - Serialization
 *============================================================================*/

/**
 * Get size of type-specific config.
 *
 * @param type Channel type
 * @return Config size in bytes, or 0 if no config
 */
uint16_t Cfg_GetTypeConfigSize(ChannelType_t type);

/**
 * Serialize a single channel to buffer.
 *
 * @param buffer Output buffer
 * @param max_size Buffer size
 * @param channel Channel to serialize
 * @return Bytes written, or negative on error
 */
int32_t Cfg_SerializeChannel(
    uint8_t* buffer,
    uint16_t max_size,
    const Channel_t* channel
);

/**
 * Deserialize a single channel from buffer.
 *
 * @param buffer Input buffer
 * @param size Buffer size
 * @param channel Output channel
 * @return Bytes consumed, or negative on error
 */
int32_t Cfg_DeserializeChannel(
    const uint8_t* buffer,
    uint16_t size,
    Channel_t* channel
);

/**
 * Calculate CRC-32 of config data.
 */
uint32_t Cfg_CalcCRC32(const uint8_t* data, uint32_t length);

/**
 * Validate configuration header.
 *
 * @param header Header to validate
 * @return true if valid
 */
bool Cfg_ValidateHeader(const CfgFileHeader_t* header);

#ifdef __cplusplus
}
#endif

#endif /* PMU_CHANNEL_CONFIG_H */

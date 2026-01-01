/**
 * @file channel_types.h
 * @brief PMU-30 Unified Channel System - Core Type Definitions
 *
 * This is the canonical source for all channel-related types.
 * Used by: Firmware, Emulator, Configurator (via bindings)
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef PMU_CHANNEL_TYPES_H
#define PMU_CHANNEL_TYPES_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Platform Detection
 *============================================================================*/

#if defined(PLATFORM_FIRMWARE) || defined(STM32H7) || defined(STM32F4)
    #define PMU_PLATFORM_EMBEDDED   1
#elif defined(PLATFORM_EMULATOR) || defined(_WIN32) || defined(__linux__)
    #define PMU_PLATFORM_DESKTOP    1
#endif

/*============================================================================
 * Channel Types (unified - all channels are "virtual")
 *============================================================================*/

/**
 * @brief Channel type enumeration
 *
 * All channels are virtual. Some have hardware bindings, some don't.
 * The type determines behavior, not whether it's "physical" or "virtual".
 */
typedef enum {
    /* Inputs (may have hw_binding) */
    CH_TYPE_NONE             = 0x00,  /**< Invalid/uninitialized */
    CH_TYPE_DIGITAL_INPUT    = 0x01,  /**< Digital switch/button */
    CH_TYPE_ANALOG_INPUT     = 0x02,  /**< Analog 0-5V sensor */
    CH_TYPE_FREQUENCY_INPUT  = 0x03,  /**< Frequency/RPM measurement */
    CH_TYPE_CAN_INPUT        = 0x04,  /**< CAN bus receive signal */

    /* Outputs (may have hw_binding) */
    CH_TYPE_POWER_OUTPUT     = 0x10,  /**< PROFET high-side output */
    CH_TYPE_PWM_OUTPUT       = 0x11,  /**< PWM output */
    CH_TYPE_HBRIDGE          = 0x12,  /**< H-Bridge motor controller */
    CH_TYPE_CAN_OUTPUT       = 0x13,  /**< CAN bus transmit message */

    /* Virtual (no hw_binding) */
    CH_TYPE_TIMER            = 0x20,  /**< Timer/delay channel */
    CH_TYPE_LOGIC            = 0x21,  /**< Logic function (AND, OR, etc.) */
    CH_TYPE_MATH             = 0x22,  /**< Math operations */
    CH_TYPE_TABLE_2D         = 0x23,  /**< 2D lookup table */
    CH_TYPE_TABLE_3D         = 0x24,  /**< 3D lookup table */
    CH_TYPE_FILTER           = 0x25,  /**< Signal filter */
    CH_TYPE_PID              = 0x26,  /**< PID controller */
    CH_TYPE_NUMBER           = 0x27,  /**< Constant number */
    CH_TYPE_SWITCH           = 0x28,  /**< Multi-state switch */
    CH_TYPE_ENUM             = 0x29,  /**< Enumeration */

    /* System (builtin, readonly) */
    CH_TYPE_SYSTEM           = 0xF0,  /**< System value (battery, temp, etc.) */
} ChannelType_t;

/*============================================================================
 * Hardware Device Types
 *============================================================================*/

/**
 * @brief Hardware device type for hw_binding
 */
typedef enum {
    HW_DEVICE_NONE           = 0x00,  /**< No hardware binding */
    HW_DEVICE_GPIO           = 0x01,  /**< Digital GPIO pin */
    HW_DEVICE_ADC            = 0x02,  /**< ADC channel */
    HW_DEVICE_PWM            = 0x03,  /**< PWM timer output */
    HW_DEVICE_DAC            = 0x04,  /**< DAC output */
    HW_DEVICE_PROFET         = 0x05,  /**< PROFET high-side driver */
    HW_DEVICE_HBRIDGE        = 0x06,  /**< H-Bridge driver */
    HW_DEVICE_CAN            = 0x07,  /**< CAN bus */
    HW_DEVICE_FREQ           = 0x08,  /**< Frequency input capture */
} HwDevice_t;

/*============================================================================
 * Data Types
 *============================================================================*/

/**
 * @brief Data type for value representation
 */
typedef enum {
    DATA_TYPE_BOOL           = 0x00,  /**< Boolean (0/1) */
    DATA_TYPE_UINT8          = 0x01,  /**< Unsigned 8-bit */
    DATA_TYPE_INT8           = 0x02,  /**< Signed 8-bit */
    DATA_TYPE_UINT16         = 0x03,  /**< Unsigned 16-bit */
    DATA_TYPE_INT16          = 0x04,  /**< Signed 16-bit */
    DATA_TYPE_UINT32         = 0x05,  /**< Unsigned 32-bit */
    DATA_TYPE_INT32          = 0x06,  /**< Signed 32-bit */
    DATA_TYPE_FLOAT32        = 0x07,  /**< 32-bit float */
} DataType_t;

/*============================================================================
 * Channel Flags
 *============================================================================*/

/**
 * @brief Channel flags bitmask
 */
typedef enum {
    CH_FLAG_ENABLED          = 0x01,  /**< Channel is active */
    CH_FLAG_INVERTED         = 0x02,  /**< Value is inverted */
    CH_FLAG_BUILTIN          = 0x04,  /**< System-defined (not user) */
    CH_FLAG_READONLY         = 0x08,  /**< Cannot be modified */
    CH_FLAG_HIDDEN           = 0x10,  /**< Hidden from UI */
    CH_FLAG_FAULT            = 0x20,  /**< Channel in fault state */
} ChannelFlags_t;

/*============================================================================
 * Hardware Binding
 *============================================================================*/

/**
 * @brief Hardware binding for channels with physical I/O
 */
typedef struct __attribute__((packed)) {
    int8_t   pin;            /**< Pin number (-1 = no binding) */
    uint8_t  device;         /**< HwDevice_t */
} HwBinding_t;

/*============================================================================
 * Display Settings
 *============================================================================*/

/**
 * @brief Display settings for UI representation
 */
typedef struct __attribute__((packed)) {
    char     unit[8];        /**< Unit string (e.g., "°C", "RPM") */
    uint8_t  decimal_places; /**< 0-6 decimal places */
    uint8_t  data_type;      /**< DataType_t for display conversion */
    int32_t  min_value;      /**< Minimum display value */
    int32_t  max_value;      /**< Maximum display value */
} DisplaySettings_t;

/*============================================================================
 * Channel Reference (for dependencies)
 *============================================================================*/

#define CH_REF_NONE          0xFFFF  /**< No channel reference */

/**
 * @brief Reference to another channel (for source_channel)
 */
typedef uint16_t ChannelRef_t;

/**
 * @brief List of channel references (for multi-source operations)
 */
typedef struct __attribute__((packed)) {
    uint8_t     count;       /**< Number of references (0-8) */
    uint16_t    ids[8];      /**< Channel IDs */
} ChannelRefList_t;

/*============================================================================
 * Core Channel Structure
 *============================================================================*/

#define CH_NAME_MAX_LEN      32

/**
 * @brief Core channel structure (runtime representation)
 */
typedef struct {
    uint16_t         id;             /**< Unique channel ID */
    uint8_t          type;           /**< ChannelType_t */
    uint8_t          flags;          /**< ChannelFlags_t bitmask */
    char             name[CH_NAME_MAX_LEN]; /**< Human-readable name */
    int32_t          value;          /**< Current value */
    HwBinding_t      hw_binding;     /**< Hardware binding (optional) */
    DisplaySettings_t display;       /**< Display settings */
    void*            config;         /**< Type-specific config (pointer) */
} Channel_t;

/*============================================================================
 * Result Codes
 *============================================================================*/

typedef enum {
    PMU_OK                   = 0,
    PMU_ERR_INVALID_PARAM    = -1,
    PMU_ERR_NOT_FOUND        = -2,
    PMU_ERR_NO_MEMORY        = -3,
    PMU_ERR_BUFFER_TOO_SMALL = -4,
    PMU_ERR_CRC_MISMATCH     = -5,
    PMU_ERR_INVALID_FORMAT   = -6,
    PMU_ERR_VERSION_MISMATCH = -7,
} PmuResult_t;

/*============================================================================
 * Magic Numbers and Version
 *============================================================================*/

#define PMU_CONFIG_MAGIC     0x504D5533  /* "PMU3" */
#define PMU_CONFIG_VERSION   1
#define PMU_TELEM_MAGIC      0x544C4D33  /* "TLM3" */
#define PMU_TELEM_VERSION    1

#ifdef __cplusplus
}
#endif

#endif /* PMU_CHANNEL_TYPES_H */

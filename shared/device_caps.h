/**
 * @file device_caps.h
 * @brief PMU-30 Device Capabilities Structure
 *
 * Defines hardware capabilities that the device reports to the configurator
 * at connection time. This allows the configurator to adapt its UI and
 * functionality based on what features are actually available on the hardware.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef PMU_DEVICE_CAPS_H
#define PMU_DEVICE_CAPS_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Capability Flags (32-bit bitmask)
 *============================================================================*/

/** Hardware feature flags */
typedef enum {
    CAPS_HAS_PROFET        = (1 << 0),   /**< Has PROFET power outputs */
    CAPS_HAS_HBRIDGE       = (1 << 1),   /**< Has H-Bridge motor drivers */
    CAPS_HAS_ADC           = (1 << 2),   /**< Has analog inputs */
    CAPS_HAS_DAC           = (1 << 3),   /**< Has analog outputs (DAC) */
    CAPS_HAS_DIN           = (1 << 4),   /**< Has digital inputs */
    CAPS_HAS_DOUT          = (1 << 5),   /**< Has digital outputs */
    CAPS_HAS_FREQ          = (1 << 6),   /**< Has frequency inputs */
    CAPS_HAS_PWM           = (1 << 7),   /**< Has PWM outputs */

    CAPS_HAS_CAN1          = (1 << 8),   /**< Has CAN bus 1 */
    CAPS_HAS_CAN2          = (1 << 9),   /**< Has CAN bus 2 */
    CAPS_HAS_CAN3          = (1 << 10),  /**< Has CAN bus 3 */
    CAPS_HAS_CAN4          = (1 << 11),  /**< Has CAN bus 4 */
    CAPS_HAS_LIN           = (1 << 12),  /**< Has LIN bus */

    CAPS_HAS_WIFI          = (1 << 16),  /**< Has WiFi module */
    CAPS_HAS_BLUETOOTH     = (1 << 17),  /**< Has Bluetooth module */
    CAPS_HAS_GPS           = (1 << 18),  /**< Has GPS receiver */
    CAPS_HAS_GSM           = (1 << 19),  /**< Has GSM/LTE modem */

    CAPS_HAS_SDCARD        = (1 << 20),  /**< Has SD card slot */
    CAPS_HAS_USB           = (1 << 21),  /**< Has USB interface */
    CAPS_HAS_ETHERNET      = (1 << 22),  /**< Has Ethernet */

    CAPS_HAS_RTC           = (1 << 24),  /**< Has RTC with battery backup */
    CAPS_HAS_EEPROM        = (1 << 25),  /**< Has EEPROM storage */
    CAPS_HAS_FLASH_EXT     = (1 << 26),  /**< Has external flash */
} DeviceCapsFlags_t;

/** Software feature flags */
typedef enum {
    CAPS_SW_PID            = (1 << 0),   /**< Supports PID controllers */
    CAPS_SW_TABLES_2D      = (1 << 1),   /**< Supports 2D lookup tables */
    CAPS_SW_TABLES_3D      = (1 << 2),   /**< Supports 3D lookup tables */
    CAPS_SW_LOGIC          = (1 << 3),   /**< Supports logic channels */
    CAPS_SW_TIMERS         = (1 << 4),   /**< Supports timer channels */
    CAPS_SW_FILTERS        = (1 << 5),   /**< Supports filter channels */
    CAPS_SW_MATH           = (1 << 6),   /**< Supports math channels */
    CAPS_SW_LUA            = (1 << 7),   /**< Supports Lua scripting */
    CAPS_SW_DATALOG        = (1 << 8),   /**< Supports data logging */
    CAPS_SW_BLINKMARINE    = (1 << 9),   /**< Supports BlinkMarine keypads */
    CAPS_SW_WIPER_PARK     = (1 << 10),  /**< Supports wiper park mode */
    CAPS_SW_CAN_STREAM     = (1 << 11),  /**< Supports CAN streaming output */
} DeviceCapsSwFlags_t;

/*============================================================================
 * Device Capabilities Structure (64 bytes)
 *============================================================================*/

/**
 * Device capabilities - sent to configurator at connection time.
 *
 * The configurator uses this information to:
 * 1. Hide UI elements for unsupported features
 * 2. Show disabled/locked UI for optional features
 * 3. Adapt channel limits and ranges
 * 4. Enable/disable protocol commands
 */
typedef struct __attribute__((packed)) {
    /* Magic and version (4 bytes) */
    uint16_t magic;              /**< Magic number: 0x4350 = "CP" (Caps) */
    uint8_t  version;            /**< Structure version (1) */
    uint8_t  reserved0;          /**< Reserved, must be 0 */

    /* Device identification (16 bytes) */
    uint8_t  device_type;        /**< Device type (see DeviceType_t) */
    uint8_t  hw_revision;        /**< Hardware revision */
    uint16_t fw_version_major;   /**< Firmware version major */
    uint16_t fw_version_minor;   /**< Firmware version minor */
    uint16_t fw_version_patch;   /**< Firmware version patch */
    uint32_t serial_number;      /**< Device serial number */
    uint32_t reserved1;          /**< Reserved */

    /* Hardware capabilities (8 bytes) */
    uint32_t hw_flags;           /**< Hardware capability flags */
    uint32_t sw_flags;           /**< Software capability flags */

    /* Channel counts (12 bytes) */
    uint8_t  profet_count;       /**< Number of PROFET outputs (0-30) */
    uint8_t  hbridge_count;      /**< Number of H-Bridge channels (0-4) */
    uint8_t  adc_count;          /**< Number of ADC inputs (0-20) */
    uint8_t  din_count;          /**< Number of digital inputs (0-20) */
    uint8_t  freq_count;         /**< Number of frequency inputs (0-4) */
    uint8_t  pwm_count;          /**< Number of PWM outputs (0-8) */
    uint8_t  can_count;          /**< Number of CAN buses (0-4) */
    uint8_t  lin_count;          /**< Number of LIN buses (0-2) */
    uint8_t  dac_count;          /**< Number of DAC outputs (0-4) */
    uint8_t  dout_count;         /**< Number of digital outputs (0-8) */
    uint16_t reserved2;          /**< Reserved */

    /* Channel limits (8 bytes) */
    uint16_t max_channels;       /**< Maximum total channels */
    uint16_t max_logic;          /**< Maximum logic channels */
    uint16_t max_timers;         /**< Maximum timer channels */
    uint16_t max_tables;         /**< Maximum table channels */

    /* Memory info (8 bytes) */
    uint32_t flash_size_kb;      /**< Flash size in KB */
    uint32_t ram_size_kb;        /**< RAM size in KB */

    /* Current limits (8 bytes) */
    uint16_t max_current_ma;     /**< Maximum total current (mA) */
    uint16_t per_channel_ma;     /**< Maximum per-channel current (mA) */
    uint16_t hbridge_current_ma; /**< Maximum H-Bridge current (mA) */
    uint16_t reserved3;          /**< Reserved */

} DeviceCaps_t;

/* Verify structure size */
_Static_assert(sizeof(DeviceCaps_t) == 64, "DeviceCaps_t must be 64 bytes");

/*============================================================================
 * Device Types
 *============================================================================*/

typedef enum {
    DEVICE_TYPE_UNKNOWN    = 0,
    DEVICE_TYPE_PMU30      = 1,    /**< Full PMU-30 device */
    DEVICE_TYPE_NUCLEO_F446 = 2,   /**< Nucleo-F446RE dev board */
    DEVICE_TYPE_NUCLEO_H7  = 3,    /**< Nucleo-H723ZG dev board */
    DEVICE_TYPE_PMU30_LITE = 4,    /**< PMU-30 Lite (reduced channels) */
    DEVICE_TYPE_EMULATOR   = 0xFF, /**< Software emulator */
} DeviceType_t;

/*============================================================================
 * Capability Constants
 *============================================================================*/

#define CAPS_MAGIC          0x4350  /* "CP" */
#define CAPS_VERSION        1

/*============================================================================
 * API Functions
 *============================================================================*/

/**
 * Initialize device capabilities with defaults for device type.
 *
 * @param caps Pointer to capabilities structure
 * @param device_type Device type
 */
void Caps_Init(DeviceCaps_t* caps, DeviceType_t device_type);

/**
 * Check if a hardware capability is present.
 *
 * @param caps Pointer to capabilities
 * @param flag Capability flag to check
 * @return true if capability is present
 */
static inline bool Caps_HasHw(const DeviceCaps_t* caps, DeviceCapsFlags_t flag) {
    return caps && (caps->hw_flags & flag);
}

/**
 * Check if a software capability is present.
 *
 * @param caps Pointer to capabilities
 * @param flag Capability flag to check
 * @return true if capability is present
 */
static inline bool Caps_HasSw(const DeviceCaps_t* caps, DeviceCapsSwFlags_t flag) {
    return caps && (caps->sw_flags & flag);
}

/**
 * Get number of CAN buses.
 */
static inline uint8_t Caps_GetCanCount(const DeviceCaps_t* caps) {
    if (!caps) return 0;
    uint8_t count = 0;
    if (caps->hw_flags & CAPS_HAS_CAN1) count++;
    if (caps->hw_flags & CAPS_HAS_CAN2) count++;
    if (caps->hw_flags & CAPS_HAS_CAN3) count++;
    if (caps->hw_flags & CAPS_HAS_CAN4) count++;
    return count;
}

#ifdef __cplusplus
}
#endif

#endif /* PMU_DEVICE_CAPS_H */

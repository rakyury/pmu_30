/**
 * @file pmu_can_stream.h
 * @brief Standard CAN Stream - Predefined PMU parameter broadcast
 *
 * Implements Standard CAN Stream for real-time monitoring of
 * PMU parameters over CAN bus.
 *
 * Frame Structure:
 *   BaseID+0: System Status & Temperatures (20 Hz)
 *   BaseID+1: Output States (20 Hz)
 *   BaseID+2: Analog Inputs a1-a8 (62.5 Hz)
 *   BaseID+3: Analog Inputs a9-a16 (62.5 Hz)
 *   BaseID+4: Output Currents o1-o8 (20 Hz)
 *   BaseID+5: Output Currents o9-o16 (20 Hz)
 *   BaseID+6: Output Voltages o1-o8 (20 Hz)
 *   BaseID+7: Output Voltages o9-o16 (20 Hz)
 *
 * PMU-30 Extended Frames (optional):
 *   BaseID+8:  Output States o17-o30 (20 Hz)
 *   BaseID+9:  Output Currents o17-o24 (20 Hz)
 *   BaseID+10: Output Currents o25-o30 + reserved (20 Hz)
 *   BaseID+11: Output Voltages o17-o24 (20 Hz)
 *   BaseID+12: Output Voltages o25-o30 + reserved (20 Hz)
 *   BaseID+13: Analog Inputs a17-a20 (62.5 Hz)
 *   BaseID+14: Digital Inputs (20 Hz)
 *   BaseID+15: H-Bridge Status (20 Hz)
 *
 * @author R2 m-sport
 * @date 2025-12-22
 */

#ifndef PMU_CAN_STREAM_H
#define PMU_CAN_STREAM_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Constants
 * ============================================================================ */

/** Number of standard frames */
#define PMU_CAN_STREAM_STD_FRAME_COUNT      8

/** Number of extended frames (PMU-30 specific) */
#define PMU_CAN_STREAM_EXT_FRAME_COUNT      8

/** Total frames when extended mode enabled */
#define PMU_CAN_STREAM_TOTAL_FRAME_COUNT    16

/** Default base CAN ID */
#define PMU_CAN_STREAM_DEFAULT_BASE_ID      0x600

/** Frame transmission rates */
#define PMU_CAN_STREAM_RATE_20HZ            50      /**< 50ms period */
#define PMU_CAN_STREAM_RATE_62HZ            16      /**< 16ms period */

/* ============================================================================
 * Scaling Factors
 * ============================================================================ */

/** Battery voltage: 0.1088 V/bit, range 0-27.75V */
#define PMU_STREAM_SCALE_VBAT               0.1088f
#define PMU_STREAM_VBAT_TO_RAW(v)           ((uint8_t)((v) / PMU_STREAM_SCALE_VBAT))
#define PMU_STREAM_RAW_TO_VBAT(r)           ((float)(r) * PMU_STREAM_SCALE_VBAT)

/** Analog input voltage: 0.0196 V/bit, range 0-5V */
#define PMU_STREAM_SCALE_AIN                0.0196f
#define PMU_STREAM_AIN_TO_RAW(v)            ((uint8_t)((v) / PMU_STREAM_SCALE_AIN))
#define PMU_STREAM_RAW_TO_AIN(r)            ((float)(r) * PMU_STREAM_SCALE_AIN)

/** Output current: 0.25 A/bit, range 0-63.75A */
#define PMU_STREAM_SCALE_CURRENT            0.25f
#define PMU_STREAM_CURRENT_TO_RAW(a)        ((uint8_t)((a) / PMU_STREAM_SCALE_CURRENT))
#define PMU_STREAM_RAW_TO_CURRENT(r)        ((float)(r) * PMU_STREAM_SCALE_CURRENT)

/** Output voltage: 0.0635 V/bit, range 0-16.19V */
#define PMU_STREAM_SCALE_VOUT               0.0635f
#define PMU_STREAM_VOUT_TO_RAW(v)           ((uint8_t)((v) / PMU_STREAM_SCALE_VOUT))
#define PMU_STREAM_RAW_TO_VOUT(r)           ((float)(r) * PMU_STREAM_SCALE_VOUT)

/** Total current: 1 A/bit, range 0-255A */
#define PMU_STREAM_SCALE_TOTAL_CURRENT      1.0f

/** Temperature: 1 °C/bit, range 0-255°C */
#define PMU_STREAM_SCALE_TEMP               1.0f

/* ============================================================================
 * Frame 0: System Status Bit Definitions
 * ============================================================================ */

/** PMU Status (bits 0-2 of byte 0) */
typedef enum {
    PMU_STATUS_OK               = 0,    /**< All outputs normal */
    PMU_STATUS_WARNING          = 1,    /**< Minor issue detected */
    PMU_STATUS_UNDERCURRENT     = 2,    /**< Undercurrent on output(s) */
    PMU_STATUS_OVERCURRENT      = 3,    /**< Overcurrent on output(s) */
    PMU_STATUS_SHORT_CIRCUIT    = 4,    /**< Short circuit detected */
    PMU_STATUS_OVERTEMP         = 5,    /**< Temperature warning */
    PMU_STATUS_CRITICAL         = 6,    /**< Critical fault */
    PMU_STATUS_THERMAL_SHUTDOWN = 7     /**< Thermal shutdown active */
} PMU_StreamStatus_t;

/** Byte 0 masks */
#define PMU_STREAM_STATUS_MASK              0x07
#define PMU_STREAM_USER_ERROR_MASK          0x08
#define PMU_STREAM_USER_ERROR_BIT           3

/** Low-side active/error masks (bytes 6-7) */
#define PMU_STREAM_LOWSIDE_L1_MASK          0x01
#define PMU_STREAM_LOWSIDE_L2_MASK          0x02
#define PMU_STREAM_LOWSIDE_L3_MASK          0x04
#define PMU_STREAM_LOWSIDE_L4_MASK          0x08
#define PMU_STREAM_LOWSIDE_L5_MASK          0x10
#define PMU_STREAM_LOWSIDE_L6_MASK          0x20

/* ============================================================================
 * Frame 1: Output State Bit Definitions
 * ============================================================================ */

/** Output Status Codes */
typedef enum {
    PMU_OUTPUT_STATUS_OFF               = 0,    /**< Output is off */
    PMU_OUTPUT_STATUS_ACTIVE            = 1,    /**< Output on, normal */
    PMU_OUTPUT_STATUS_UNDERCURRENT      = 2,    /**< Undercurrent detected */
    PMU_OUTPUT_STATUS_OVERCURRENT       = 3,    /**< Overcurrent detected */
    PMU_OUTPUT_STATUS_SHORT_GND         = 4,    /**< Short to ground */
    PMU_OUTPUT_STATUS_SHORT_VBAT        = 5,    /**< Short to battery */
    PMU_OUTPUT_STATUS_OPEN_LOAD         = 6,    /**< Open load detected */
    PMU_OUTPUT_STATUS_THERMAL_SHUTDOWN  = 7     /**< Thermal shutdown */
} PMU_OutputStatus_t;

/** H-Bridge Status Codes (Frame 15) */
typedef enum {
    PMU_HBRIDGE_STATUS_IDLE             = 0,    /**< Motor stopped */
    PMU_HBRIDGE_STATUS_FORWARD          = 1,    /**< Running forward */
    PMU_HBRIDGE_STATUS_REVERSE          = 2,    /**< Running reverse */
    PMU_HBRIDGE_STATUS_BRAKE            = 3,    /**< Active braking */
    PMU_HBRIDGE_STATUS_COAST            = 4,    /**< Coasting (free-wheel) */
    PMU_HBRIDGE_STATUS_OVERCURRENT      = 5,    /**< Overcurrent fault */
    PMU_HBRIDGE_STATUS_STALL            = 6,    /**< Stall detected */
    PMU_HBRIDGE_STATUS_THERMAL          = 7     /**< Thermal shutdown */
} PMU_HBridgeStreamStatus_t;

/** Odd output (high nibble) masks */
#define PMU_STREAM_ODD_STATUS_MASK          0xE0
#define PMU_STREAM_ODD_STATUS_SHIFT         5
#define PMU_STREAM_ODD_ACTIVE_MASK          0x10
#define PMU_STREAM_ODD_ACTIVE_BIT           4

/** Even output (low nibble) masks */
#define PMU_STREAM_EVEN_STATUS_MASK         0x0E
#define PMU_STREAM_EVEN_STATUS_SHIFT        1
#define PMU_STREAM_EVEN_ACTIVE_MASK         0x01
#define PMU_STREAM_EVEN_ACTIVE_BIT          0

/* ============================================================================
 * Configuration Structure
 * ============================================================================ */

/**
 * @brief Standard CAN Stream configuration
 */
typedef struct {
    bool        enabled;            /**< Stream enabled */
    uint8_t     can_bus;            /**< CAN bus (1 = CAN A, 2 = CAN B) */
    uint32_t    base_id;            /**< Base CAN ID (frames use base_id + 0..7) */
    bool        is_extended;        /**< Use 29-bit extended CAN IDs */
    bool        include_extended;   /**< Include PMU-30 extended frames (8-15) */
} PMU_CanStreamConfig_t;

/* ============================================================================
 * Frame Data Structures
 * ============================================================================ */

/**
 * @brief Frame 0: System Status (packed)
 */
typedef struct __attribute__((packed)) {
    uint8_t status_flags;       /**< bits 0-2: status, bit 3: user_error */
    uint8_t total_current;      /**< Total current (1 A/bit) */
    uint8_t battery_voltage;    /**< Battery voltage (0.1088 V/bit) */
    uint8_t board_temp_left;    /**< Left board temp (1 °C/bit) */
    uint8_t board_temp_right;   /**< Right board temp (1 °C/bit) */
    uint8_t mcu_temperature;    /**< MCU temperature (1 °C/bit) */
    uint8_t lowside_active;     /**< Low-side active flags (bits 0-5) */
    uint8_t lowside_error;      /**< Low-side error flags (bits 0-5) */
} PMU_StreamFrame0_t;

/**
 * @brief Frame 1: Output States (packed)
 * Each byte contains 2 outputs (odd in high nibble, even in low nibble)
 */
typedef struct __attribute__((packed)) {
    uint8_t outputs[8];         /**< o1/o2, o3/o4, ... o15/o16 */
} PMU_StreamFrame1_t;

/**
 * @brief Frame 2/3: Analog Inputs (packed)
 */
typedef struct __attribute__((packed)) {
    uint8_t voltages[8];        /**< 8 analog input voltages (0.0196 V/bit) */
} PMU_StreamFrameAnalog_t;

/**
 * @brief Frame 4/5: Output Currents (packed)
 */
typedef struct __attribute__((packed)) {
    uint8_t currents[8];        /**< 8 output currents (0.25 A/bit) */
} PMU_StreamFrameCurrent_t;

/**
 * @brief Frame 6/7: Output Voltages (packed)
 */
typedef struct __attribute__((packed)) {
    uint8_t voltages[8];        /**< 8 output voltages (0.0635 V/bit) */
} PMU_StreamFrameVoltage_t;

/**
 * @brief Frame 14: Digital Inputs (PMU-30 extended)
 */
typedef struct __attribute__((packed)) {
    uint8_t states;             /**< Digital input states (bits 0-7) */
    uint8_t counters[4];        /**< Frequency/pulse counters (optional) */
    uint8_t reserved[3];
} PMU_StreamFrameDigital_t;

/**
 * @brief Frame 15: H-Bridge Status (PMU-30 extended)
 */
typedef struct __attribute__((packed)) {
    uint8_t hb1_status;         /**< H-Bridge 1 status */
    uint8_t hb1_current;        /**< H-Bridge 1 current (0.25 A/bit) */
    uint8_t hb2_status;         /**< H-Bridge 2 status */
    uint8_t hb2_current;        /**< H-Bridge 2 current */
    uint8_t hb3_status;         /**< H-Bridge 3 status */
    uint8_t hb3_current;        /**< H-Bridge 3 current */
    uint8_t hb4_status;         /**< H-Bridge 4 status */
    uint8_t hb4_current;        /**< H-Bridge 4 current */
} PMU_StreamFrameHBridge_t;

/* ============================================================================
 * Runtime State
 * ============================================================================ */

/**
 * @brief CAN Stream runtime state
 */
typedef struct {
    PMU_CanStreamConfig_t config;

    uint32_t    timer_20hz;         /**< Timer for 20 Hz frames */
    uint32_t    timer_62hz;         /**< Timer for 62.5 Hz frames */
    uint8_t     frame_sequence;     /**< Current frame in sequence */
    bool        initialized;        /**< Initialization flag */

    /* Statistics */
    uint32_t    frames_sent;        /**< Total frames transmitted */
    uint32_t    errors;             /**< Transmission errors */
} PMU_CanStreamState_t;

/* ============================================================================
 * Public API
 * ============================================================================ */

/**
 * @brief Initialize Standard CAN Stream
 * @param config Configuration structure
 * @return 0 on success, error code on failure
 */
int PMU_CanStream_Init(const PMU_CanStreamConfig_t *config);

/**
 * @brief Deinitialize Standard CAN Stream
 */
void PMU_CanStream_Deinit(void);

/**
 * @brief Enable/disable the stream
 * @param enabled true to enable, false to disable
 */
void PMU_CanStream_SetEnabled(bool enabled);

/**
 * @brief Check if stream is enabled
 * @return true if enabled
 */
bool PMU_CanStream_IsEnabled(void);

/**
 * @brief Process stream (call from main loop or timer)
 *
 * This function handles frame timing and transmission.
 * Should be called frequently (at least every 1ms).
 */
void PMU_CanStream_Process(void);

/**
 * @brief Update configuration
 * @param config New configuration
 * @return 0 on success, error code on failure
 */
int PMU_CanStream_Configure(const PMU_CanStreamConfig_t *config);

/**
 * @brief Get current configuration
 * @param config Output configuration structure
 */
void PMU_CanStream_GetConfig(PMU_CanStreamConfig_t *config);

/**
 * @brief Get stream statistics
 * @param frames_sent Output: total frames sent
 * @param errors Output: transmission errors
 */
void PMU_CanStream_GetStats(uint32_t *frames_sent, uint32_t *errors);

/**
 * @brief Reset statistics counters
 */
void PMU_CanStream_ResetStats(void);

/* ============================================================================
 * Helper Functions
 * ============================================================================ */

/**
 * @brief Pack output state into byte (2 outputs per byte)
 * @param odd_status Status of odd output (1, 3, 5, ...)
 * @param odd_active Active flag of odd output
 * @param even_status Status of even output (2, 4, 6, ...)
 * @param even_active Active flag of even output
 * @return Packed byte
 */
static inline uint8_t PMU_CanStream_PackOutputState(
    PMU_OutputStatus_t odd_status, bool odd_active,
    PMU_OutputStatus_t even_status, bool even_active)
{
    return ((odd_status << PMU_STREAM_ODD_STATUS_SHIFT) & PMU_STREAM_ODD_STATUS_MASK) |
           ((odd_active ? 1 : 0) << PMU_STREAM_ODD_ACTIVE_BIT) |
           ((even_status << PMU_STREAM_EVEN_STATUS_SHIFT) & PMU_STREAM_EVEN_STATUS_MASK) |
           ((even_active ? 1 : 0) << PMU_STREAM_EVEN_ACTIVE_BIT);
}

/**
 * @brief Unpack output state from byte
 * @param packed Packed byte
 * @param odd_status Output: status of odd output
 * @param odd_active Output: active flag of odd output
 * @param even_status Output: status of even output
 * @param even_active Output: active flag of even output
 */
static inline void PMU_CanStream_UnpackOutputState(
    uint8_t packed,
    PMU_OutputStatus_t *odd_status, bool *odd_active,
    PMU_OutputStatus_t *even_status, bool *even_active)
{
    *odd_status = (PMU_OutputStatus_t)((packed & PMU_STREAM_ODD_STATUS_MASK) >> PMU_STREAM_ODD_STATUS_SHIFT);
    *odd_active = (packed & PMU_STREAM_ODD_ACTIVE_MASK) != 0;
    *even_status = (PMU_OutputStatus_t)((packed & PMU_STREAM_EVEN_STATUS_MASK) >> PMU_STREAM_EVEN_STATUS_SHIFT);
    *even_active = (packed & PMU_STREAM_EVEN_ACTIVE_MASK) != 0;
}

#ifdef __cplusplus
}
#endif

#endif /* PMU_CAN_STREAM_H */

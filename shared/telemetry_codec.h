/**
 * @file telemetry_codec.h
 * @brief PMU-30 Telemetry Codec - Build and Parse telemetry packets
 *
 * Shared between Firmware (build) and Configurator (parse).
 * Unified format for all platforms.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef PMU_TELEMETRY_CODEC_H
#define PMU_TELEMETRY_CODEC_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "channel_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Telemetry Section Flags
 *============================================================================*/

#define TELEM_HAS_ADC           0x0001  /**< ADC values section present */
#define TELEM_HAS_OUTPUTS       0x0002  /**< Output states section present */
#define TELEM_HAS_HBRIDGE       0x0004  /**< H-Bridge section present */
#define TELEM_HAS_DIN           0x0008  /**< Digital inputs section present */
#define TELEM_HAS_VIRTUALS      0x0010  /**< Virtual channels section present */
#define TELEM_HAS_FAULTS        0x0020  /**< Fault status section present */
#define TELEM_HAS_CURRENTS      0x0040  /**< Per-output currents section */
#define TELEM_HAS_EXTENDED      0x0080  /**< Extended data section */

/*============================================================================
 * Telemetry Header (always present, 20 bytes)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint32_t stream_counter;     /**< Packet sequence number */
    uint32_t timestamp_ms;       /**< System timestamp (ms) */
    uint16_t input_voltage_mv;   /**< Battery voltage (mV) */
    int16_t  mcu_temp_c10;       /**< MCU temperature (0.1°C) */
    int16_t  board_temp_c10;     /**< Board temperature (0.1°C) */
    uint32_t total_current_ma;   /**< Total system current (mA) */
    uint16_t flags;              /**< Section flags (TELEM_HAS_*) */
} TelemetryHeader_t;

/*============================================================================
 * Section: ADC Values (40 bytes for 20 channels)
 *============================================================================*/

#define TELEM_ADC_COUNT         20

typedef struct __attribute__((packed)) {
    uint16_t values[TELEM_ADC_COUNT];  /**< Raw ADC values (0-4095) */
} TelemetryADC_t;

/*============================================================================
 * Section: Output States (30 bytes for 30 outputs)
 *============================================================================*/

#define TELEM_OUTPUT_COUNT      30

typedef struct __attribute__((packed)) {
    uint8_t states[TELEM_OUTPUT_COUNT];  /**< Output states (0=off, 1=on, etc.) */
} TelemetryOutputs_t;

/*============================================================================
 * Section: Digital Inputs (4 bytes for 20 inputs as bitmask)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint32_t bitmask;  /**< Bit N = input N state (20 bits used) */
} TelemetryDIN_t;

/*============================================================================
 * Section: Virtual Channels (variable length)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t channel_id;  /**< Channel ID */
    int32_t  value;       /**< Current value */
} VirtualChannelEntry_t;

#define TELEM_VIRTUAL_MAX       32  /**< Max virtual channels in one packet */

typedef struct {
    uint16_t count;                                 /**< Number of entries */
    VirtualChannelEntry_t entries[TELEM_VIRTUAL_MAX]; /**< Channel entries */
} TelemetryVirtuals_t;

/*============================================================================
 * Section: Faults (4 bytes)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint8_t  status;        /**< System status byte */
    uint8_t  fault_flags;   /**< Fault flags */
    uint16_t reserved;      /**< Reserved for future use */
} TelemetryFaults_t;

/*============================================================================
 * Section: Per-Output Currents (60 bytes for 30 outputs)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t currents[TELEM_OUTPUT_COUNT];  /**< Current per output (mA) */
} TelemetryCurrents_t;

/*============================================================================
 * Section: H-Bridge (16 bytes for 4 H-bridges)
 *============================================================================*/

#define TELEM_HBRIDGE_COUNT     4

typedef struct __attribute__((packed)) {
    int16_t  position[TELEM_HBRIDGE_COUNT];  /**< Position (-1000 to +1000) */
    uint16_t current[TELEM_HBRIDGE_COUNT];   /**< Current (mA) */
} TelemetryHBridge_t;

/*============================================================================
 * Complete Telemetry Packet (parsed result)
 *============================================================================*/

typedef struct {
    /* Always present */
    TelemetryHeader_t header;

    /* Optional sections (valid if corresponding flag is set) */
    TelemetryADC_t      adc;
    TelemetryOutputs_t  outputs;
    TelemetryDIN_t      din;
    TelemetryVirtuals_t virtuals;
    TelemetryFaults_t   faults;
    TelemetryCurrents_t currents;
    TelemetryHBridge_t  hbridge;
} TelemetryPacket_t;

/*============================================================================
 * Build Configuration
 *============================================================================*/

typedef struct {
    bool include_adc;
    bool include_outputs;
    bool include_hbridge;
    bool include_din;
    bool include_virtuals;
    bool include_faults;
    bool include_currents;
} TelemetryBuildConfig_t;

/*============================================================================
 * Result Codes
 *============================================================================*/

typedef enum {
    TELEM_OK = 0,
    TELEM_ERR_NULL_PARAM,
    TELEM_ERR_BUFFER_TOO_SMALL,
    TELEM_ERR_TOO_SHORT,
    TELEM_ERR_BAD_FLAGS,
    TELEM_ERR_TRUNCATED,
} TelemetryResult_t;

/*============================================================================
 * API Functions
 *============================================================================*/

/**
 * @brief Parse telemetry packet from raw bytes
 *
 * @param data Raw packet data (after protocol framing removed)
 * @param size Size of data in bytes
 * @param out Output packet structure (filled on success)
 * @return TELEM_OK on success, error code otherwise
 */
TelemetryResult_t Telemetry_Parse(
    const uint8_t* data,
    size_t size,
    TelemetryPacket_t* out
);

/**
 * @brief Get minimum packet size for given flags
 *
 * @param flags Section flags (TELEM_HAS_*)
 * @return Minimum packet size in bytes
 */
size_t Telemetry_GetMinSize(uint16_t flags);

/**
 * @brief Check if a section is present in packet
 *
 * @param packet Parsed packet
 * @param flag Section flag (e.g., TELEM_HAS_VIRTUALS)
 * @return true if section is present
 */
static inline bool Telemetry_HasSection(const TelemetryPacket_t* packet, uint16_t flag) {
    return (packet->header.flags & flag) != 0;
}

/**
 * @brief Get virtual channel value by ID
 *
 * @param packet Parsed packet
 * @param channel_id Channel ID to find
 * @param value Output value (valid if found)
 * @return true if channel found, false otherwise
 */
bool Telemetry_GetVirtualValue(
    const TelemetryPacket_t* packet,
    uint16_t channel_id,
    int32_t* value
);

/*============================================================================
 * Build API (firmware-side)
 *============================================================================*/

#ifdef PMU_PLATFORM_EMBEDDED

/**
 * @brief Build telemetry packet into buffer
 *
 * @param buffer Output buffer
 * @param max_size Maximum buffer size
 * @param config What sections to include
 * @return Number of bytes written, or 0 on error
 */
size_t Telemetry_Build(
    uint8_t* buffer,
    size_t max_size,
    const TelemetryBuildConfig_t* config
);

/**
 * @brief Set virtual channels to include in next build
 *
 * @param ids Array of channel IDs
 * @param values Array of channel values
 * @param count Number of channels
 */
void Telemetry_SetVirtuals(
    const uint16_t* ids,
    const int32_t* values,
    uint16_t count
);

#endif /* PMU_PLATFORM_EMBEDDED */

#ifdef __cplusplus
}
#endif

#endif /* PMU_TELEMETRY_CODEC_H */

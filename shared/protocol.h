/**
 * @file protocol.h
 * @brief PMU-30 Unified Binary Protocol
 *
 * Zero-copy, capability-aware protocol for all PMU devices.
 * No board-specific code - everything is driven by DeviceCaps.
 *
 * Design goals:
 * - Minimal memory footprint
 * - Zero dynamic allocation
 * - Maximum performance
 * - Works on any hardware
 *
 * @version 2.0
 * @date January 2026
 */

#ifndef PMU_PROTOCOL_H
#define PMU_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "device_caps.h"

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Frame Format
 *============================================================================
 *
 * All frames use this format:
 *
 * +--------+--------+--------+--------+--------+--- ... ---+--------+--------+
 * | SYNC_H | SYNC_L |  CMD   | LEN_L  | LEN_H  |  PAYLOAD  | CRC_L  | CRC_H  |
 * +--------+--------+--------+--------+--------+--- ... ---+--------+--------+
 *    0xAA     0x55     1B       2B (little endian)   0-1024B     CRC-16
 *
 * - SYNC: 0xAA 0x55 (magic bytes)
 * - CMD: Command code (see ProtocolCmd_t)
 * - LEN: Payload length (0-1024 bytes)
 * - PAYLOAD: Command-specific data
 * - CRC: CRC-16-CCITT of CMD + LEN + PAYLOAD
 *
 * Total overhead: 7 bytes per frame
 *============================================================================*/

#define PROTO_SYNC_H        0xAA
#define PROTO_SYNC_L        0x55
#define PROTO_HEADER_SIZE   5       /* SYNC(2) + CMD(1) + LEN(2) */
#define PROTO_CRC_SIZE      2
#define PROTO_OVERHEAD      (PROTO_HEADER_SIZE + PROTO_CRC_SIZE)
#define PROTO_MAX_PAYLOAD   1024
#define PROTO_MAX_FRAME     (PROTO_OVERHEAD + PROTO_MAX_PAYLOAD)

/*============================================================================
 * Command Codes
 *============================================================================*/

typedef enum {
    /*--- System Commands (0x00-0x0F) ---*/
    CMD_NOP             = 0x00,     /**< No operation (keepalive) */
    CMD_PING            = 0x01,     /**< Ping request */
    CMD_PONG            = 0x02,     /**< Ping response */
    CMD_GET_CAPS        = 0x03,     /**< Get device capabilities */
    CMD_CAPS_RESP       = 0x04,     /**< Capabilities response */
    CMD_RESET           = 0x05,     /**< Reset device */
    CMD_BOOTLOADER      = 0x06,     /**< Enter bootloader */

    /*--- Configuration Commands (0x10-0x1F) ---*/
    CMD_GET_CONFIG      = 0x10,     /**< Get configuration */
    CMD_CONFIG_DATA     = 0x11,     /**< Configuration data (chunked) */
    CMD_SET_CONFIG      = 0x12,     /**< Set configuration (chunked) */
    CMD_CONFIG_ACK      = 0x13,     /**< Configuration acknowledged */
    CMD_SAVE_CONFIG     = 0x14,     /**< Save config to flash */
    CMD_LOAD_CONFIG     = 0x15,     /**< Load config from flash */
    CMD_CLEAR_CONFIG    = 0x16,     /**< Clear config (factory reset) */

    /*--- Telemetry Commands (0x20-0x2F) ---*/
    CMD_TELEM_START     = 0x20,     /**< Start telemetry stream */
    CMD_TELEM_STOP      = 0x21,     /**< Stop telemetry stream */
    CMD_TELEM_DATA      = 0x22,     /**< Telemetry data packet */
    CMD_TELEM_CONFIG    = 0x23,     /**< Configure telemetry (rate, sections) */

    /*--- Channel Commands (0x30-0x3F) ---*/
    CMD_CH_GET_VALUE    = 0x30,     /**< Get channel value */
    CMD_CH_SET_VALUE    = 0x31,     /**< Set channel value */
    CMD_CH_VALUE_RESP   = 0x32,     /**< Channel value response */
    CMD_CH_GET_INFO     = 0x33,     /**< Get channel info */
    CMD_CH_INFO_RESP    = 0x34,     /**< Channel info response */
    CMD_CH_GET_LIST     = 0x35,     /**< Get channel list */
    CMD_CH_LIST_RESP    = 0x36,     /**< Channel list response */

    /*--- Debug Commands (0x40-0x4F) ---*/
    CMD_DEBUG_CONFIG    = 0x40,     /**< Configure debug output */
    CMD_DEBUG_MSG       = 0x41,     /**< Debug message from device */
    CMD_DEBUG_VAR_GET   = 0x42,     /**< Get debug variable */
    CMD_DEBUG_VAR_SET   = 0x43,     /**< Set debug variable */
    CMD_DEBUG_VAR_RESP  = 0x44,     /**< Debug variable response */

    /*--- CAN Commands (0x50-0x5F) ---*/
    CMD_CAN_SEND        = 0x50,     /**< Send CAN frame */
    CMD_CAN_RECV        = 0x51,     /**< Received CAN frame */
    CMD_CAN_CONFIG      = 0x52,     /**< Configure CAN bus */
    CMD_CAN_STATUS      = 0x53,     /**< CAN bus status */

    /*--- Firmware Update (0x60-0x6F) ---*/
    CMD_FW_BEGIN        = 0x60,     /**< Begin firmware update */
    CMD_FW_DATA         = 0x61,     /**< Firmware data chunk */
    CMD_FW_END          = 0x62,     /**< End firmware update */
    CMD_FW_VERIFY       = 0x63,     /**< Verify firmware */
    CMD_FW_STATUS       = 0x64,     /**< Firmware update status */

    /*--- Datalog Commands (0x70-0x7F) ---*/
    CMD_LOG_START       = 0x70,     /**< Start data logging */
    CMD_LOG_STOP        = 0x71,     /**< Stop data logging */
    CMD_LOG_STATUS      = 0x72,     /**< Logging status */
    CMD_LOG_GET_DATA    = 0x73,     /**< Get logged data */
    CMD_LOG_DATA        = 0x74,     /**< Logged data chunk */
    CMD_LOG_CLEAR       = 0x75,     /**< Clear log storage */

    /*--- Error/Status (0xF0-0xFF) ---*/
    CMD_ERROR           = 0xF0,     /**< Error response */
    CMD_STATUS          = 0xF1,     /**< Status response */

} ProtocolCmd_t;

/*============================================================================
 * Error Codes
 *============================================================================*/

typedef enum {
    ERR_OK              = 0x00,     /**< No error */
    ERR_UNKNOWN_CMD     = 0x01,     /**< Unknown command */
    ERR_INVALID_PARAM   = 0x02,     /**< Invalid parameter */
    ERR_INVALID_LENGTH  = 0x03,     /**< Invalid payload length */
    ERR_CRC_MISMATCH    = 0x04,     /**< CRC check failed */
    ERR_BUFFER_FULL     = 0x05,     /**< Buffer overflow */
    ERR_NOT_SUPPORTED   = 0x06,     /**< Feature not supported */
    ERR_BUSY            = 0x07,     /**< Device busy */
    ERR_TIMEOUT         = 0x08,     /**< Operation timeout */
    ERR_FLASH_ERROR     = 0x09,     /**< Flash operation failed */
    ERR_CHANNEL_INVALID = 0x0A,     /**< Invalid channel ID */
    ERR_CONFIG_INVALID  = 0x0B,     /**< Invalid configuration */
    ERR_NOT_CONNECTED   = 0x0C,     /**< Not connected */
} ProtocolError_t;

/*============================================================================
 * Telemetry Section Flags (what data to include)
 *============================================================================*/

typedef enum {
    TELEM_SEC_HEADER    = 0x0001,   /**< Always present: timestamp, voltage, temp */
    TELEM_SEC_OUTPUTS   = 0x0002,   /**< Output states (profet_count bytes) */
    TELEM_SEC_CURRENTS  = 0x0004,   /**< Output currents (profet_count * 2 bytes) */
    TELEM_SEC_ADC       = 0x0008,   /**< ADC values (adc_count * 2 bytes) */
    TELEM_SEC_DIN       = 0x0010,   /**< Digital inputs (bitmask, 4 bytes) */
    TELEM_SEC_HBRIDGE   = 0x0020,   /**< H-Bridge data (hbridge_count * 8 bytes) */
    TELEM_SEC_VIRTUALS  = 0x0040,   /**< Virtual channels (count + id:value pairs) */
    TELEM_SEC_FAULTS    = 0x0080,   /**< Fault status */
    TELEM_SEC_EXTENDED  = 0x0100,   /**< Extended system data */
    TELEM_SEC_DEBUG     = 0x8000,   /**< Debug data (if enabled) */
} TelemSectionFlags_t;

/*============================================================================
 * Telemetry Header (always present, 16 bytes)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint32_t seq;               /**< Packet sequence number */
    uint32_t timestamp_ms;      /**< Milliseconds since boot */
    uint16_t voltage_mv;        /**< Input voltage (mV) */
    int16_t  mcu_temp_c10;      /**< MCU temperature (0.1°C) */
    uint16_t sections;          /**< Section flags present in this packet */
    uint16_t reserved;          /**< Reserved (alignment) */
} TelemHeader_t;

_Static_assert(sizeof(TelemHeader_t) == 16, "TelemHeader_t must be 16 bytes");

/*============================================================================
 * Configuration Header (binary config format)
 *============================================================================*/

#define CONFIG_MAGIC        0x50434647  /* "PCFG" */
#define CONFIG_VERSION      2

typedef struct __attribute__((packed)) {
    uint32_t magic;             /**< Magic: 0x50434647 "PCFG" */
    uint16_t version;           /**< Config format version */
    uint16_t device_type;       /**< Target device type */
    uint32_t total_size;        /**< Total config size (bytes) */
    uint32_t crc32;             /**< CRC-32 of data after header */
    uint16_t channel_count;     /**< Number of channels */
    uint16_t flags;             /**< Config flags */
} ConfigHeader_t;

_Static_assert(sizeof(ConfigHeader_t) == 20, "ConfigHeader_t must be 20 bytes");

/*============================================================================
 * Channel Entry (binary config format, variable size)
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint16_t id;                /**< Channel ID (unique) */
    uint8_t  type;              /**< Channel type (ChannelType_t) */
    uint8_t  flags;             /**< Channel flags */
    uint8_t  hw_device;         /**< Hardware device type (HwDevice_t) */
    uint8_t  hw_index;          /**< Hardware index/pin */
    uint16_t source_id;         /**< Source channel ID (CH_REF_NONE if none) */
    int32_t  default_value;     /**< Default/initial value */
    uint8_t  name_len;          /**< Name length (0-31) */
    /* Followed by: name[name_len], then type-specific data */
} ChannelEntry_t;

/*============================================================================
 * Protocol Parser State Machine
 *============================================================================*/

typedef enum {
    PARSE_STATE_SYNC1,          /**< Waiting for 0xAA */
    PARSE_STATE_SYNC2,          /**< Waiting for 0x55 */
    PARSE_STATE_CMD,            /**< Reading command byte */
    PARSE_STATE_LEN_L,          /**< Reading length low byte */
    PARSE_STATE_LEN_H,          /**< Reading length high byte */
    PARSE_STATE_PAYLOAD,        /**< Reading payload bytes */
    PARSE_STATE_CRC_L,          /**< Reading CRC low byte */
    PARSE_STATE_CRC_H,          /**< Reading CRC high byte */
} ParseState_t;

typedef struct {
    ParseState_t state;         /**< Current parser state */
    uint8_t cmd;                /**< Command byte */
    uint16_t length;            /**< Payload length */
    uint16_t index;             /**< Current index in payload */
    uint16_t crc;               /**< Accumulated CRC */
    uint8_t* buffer;            /**< Payload buffer */
    uint16_t buffer_size;       /**< Buffer size */
} ProtocolParser_t;

/*============================================================================
 * API Types
 *============================================================================*/

/** Frame received callback */
typedef void (*Proto_FrameCallback)(
    uint8_t cmd,
    const uint8_t* payload,
    uint16_t length,
    void* user_data
);

/** Send function (platform-specific) */
typedef bool (*Proto_SendFunc)(
    const uint8_t* data,
    uint16_t length,
    void* user_data
);

/*============================================================================
 * API Functions
 *============================================================================*/

/**
 * Initialize protocol parser.
 *
 * @param parser Parser instance
 * @param buffer Receive buffer
 * @param buffer_size Buffer size
 */
void Proto_Init(
    ProtocolParser_t* parser,
    uint8_t* buffer,
    uint16_t buffer_size
);

/**
 * Feed byte to parser (call for each received byte).
 *
 * @param parser Parser instance
 * @param byte Received byte
 * @param callback Callback when frame complete
 * @param user_data User data for callback
 * @return true if frame was completed
 */
bool Proto_ParseByte(
    ProtocolParser_t* parser,
    uint8_t byte,
    Proto_FrameCallback callback,
    void* user_data
);

/**
 * Build and send a frame.
 *
 * @param cmd Command code
 * @param payload Payload data (can be NULL if length is 0)
 * @param length Payload length
 * @param send_func Platform send function
 * @param user_data User data for send function
 * @return true if sent successfully
 */
bool Proto_SendFrame(
    uint8_t cmd,
    const uint8_t* payload,
    uint16_t length,
    Proto_SendFunc send_func,
    void* user_data
);

/**
 * Build frame into buffer (no send).
 *
 * @param buffer Output buffer (must be length + PROTO_OVERHEAD bytes)
 * @param cmd Command code
 * @param payload Payload data
 * @param length Payload length
 * @return Total frame size
 */
uint16_t Proto_BuildFrame(
    uint8_t* buffer,
    uint8_t cmd,
    const uint8_t* payload,
    uint16_t length
);

/**
 * Calculate CRC-16-CCITT.
 */
uint16_t Proto_CalcCRC(const uint8_t* data, uint16_t length);

/*============================================================================
 * Telemetry Builder (firmware side)
 *============================================================================*/

/**
 * Build telemetry packet based on device capabilities.
 *
 * The builder reads actual hardware values and packs them according to
 * the requested sections and device capabilities.
 *
 * @param buffer Output buffer
 * @param max_size Maximum buffer size
 * @param caps Device capabilities
 * @param sections Requested sections (bitmask)
 * @return Packet size, or 0 on error
 */
uint16_t Telem_Build(
    uint8_t* buffer,
    uint16_t max_size,
    const DeviceCaps_t* caps,
    uint16_t sections
);

/**
 * Calculate telemetry packet size for given caps and sections.
 */
uint16_t Telem_CalcSize(
    const DeviceCaps_t* caps,
    uint16_t sections
);

#ifdef __cplusplus
}
#endif

#endif /* PMU_PROTOCOL_H */

/**
 ******************************************************************************
 * @file           : pmu_serial_transfer.h
 * @brief          : SerialTransfer Protocol for STM32 (bare-metal)
 ******************************************************************************
 *
 * Simple, reliable serial protocol using COBS encoding and CRC8.
 * Compatible with pySerialTransfer Python library.
 *
 * Packet Format:
 * [START=0x7E] [ID] [COBS overhead] [LEN] [payload...] [CRC8] [STOP=0x81]
 *
 ******************************************************************************
 */

#ifndef PMU_SERIAL_TRANSFER_H
#define PMU_SERIAL_TRANSFER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Protocol constants */
#define ST_START_BYTE       0x7E
#define ST_STOP_BYTE        0x81
#define ST_MAX_PAYLOAD      254
#define ST_PREAMBLE_SIZE    4
#define ST_POSTAMBLE_SIZE   2

/* Status codes */
typedef enum {
    ST_STATUS_CONTINUE        =  3,
    ST_STATUS_NEW_DATA        =  2,
    ST_STATUS_NO_DATA         =  1,
    ST_STATUS_CRC_ERROR       =  0,
    ST_STATUS_PAYLOAD_ERROR   = -1,
    ST_STATUS_STOP_BYTE_ERROR = -2,
    ST_STATUS_STALE_PACKET    = -3
} ST_Status;

/* Command IDs */
typedef enum {
    /* Basic commands */
    ST_CMD_PING             = 0x01,
    ST_CMD_PONG             = 0x02,
    ST_CMD_RESET            = 0x05,

    /* Configuration */
    ST_CMD_GET_CONFIG       = 0x10,
    ST_CMD_CONFIG_DATA      = 0x11,
    ST_CMD_SAVE_CONFIG      = 0x14,
    ST_CMD_FLASH_ACK        = 0x15,
    ST_CMD_CLEAR_CONFIG     = 0x16,
    ST_CMD_CLEAR_CONFIG_ACK = 0x17,
    ST_CMD_LOAD_BINARY      = 0x18,
    ST_CMD_BINARY_ACK       = 0x19,

    /* Telemetry */
    ST_CMD_START_STREAM     = 0x20,
    ST_CMD_STOP_STREAM      = 0x21,
    ST_CMD_DATA             = 0x22,

    /* Channel control */
    ST_CMD_SET_OUTPUT       = 0x28,
    ST_CMD_OUTPUT_ACK       = 0x29,

    /* Device info */
    ST_CMD_GET_CAPABILITIES = 0x30,
    ST_CMD_CAPABILITIES     = 0x31,

    /* CAN testing */
    ST_CMD_CAN_INJECT       = 0x40,
    ST_CMD_CAN_INJECT_ACK   = 0x41,

    /* Generic responses */
    ST_CMD_ACK              = 0x3E,
    ST_CMD_NACK             = 0x3F
} ST_Command;

/* Serial Transfer context */
typedef struct {
    /* TX buffer */
    uint8_t tx_buff[ST_MAX_PAYLOAD];

    /* RX buffer */
    uint8_t rx_buff[ST_MAX_PAYLOAD];

    /* State */
    uint8_t bytes_read;
    int8_t  status;
    uint8_t current_packet_id;

    /* Private state machine */
    uint8_t state;
    uint8_t bytes_to_rec;
    uint8_t payload_index;
    uint8_t id_byte;
    uint8_t overhead_byte;
    uint8_t rec_overhead_byte;

    /* Timeout tracking */
    uint32_t packet_start_ms;
    uint32_t timeout_ms;

    /* Callbacks */
    void (*on_packet)(uint8_t cmd, const uint8_t* payload, uint8_t len);
} ST_Context;

/**
 * Initialize SerialTransfer context
 * @param ctx Context to initialize
 * @param timeout_ms Packet timeout in milliseconds (default 50)
 */
void ST_Init(ST_Context* ctx, uint32_t timeout_ms);

/**
 * Reset context state
 * @param ctx Context to reset
 */
void ST_Reset(ST_Context* ctx);

/**
 * Process received byte
 * @param ctx Context
 * @param byte Received byte
 * @param current_ms Current timestamp in milliseconds
 * @return Status code (ST_STATUS_NEW_DATA when complete packet received)
 */
int8_t ST_ProcessByte(ST_Context* ctx, uint8_t byte, uint32_t current_ms);

/**
 * Get current packet ID (after ST_STATUS_NEW_DATA)
 * @param ctx Context
 * @return Packet ID (command)
 */
uint8_t ST_GetPacketID(ST_Context* ctx);

/**
 * Construct packet for transmission
 * @param ctx Context (data should be in ctx->tx_buff)
 * @param payload_len Number of payload bytes
 * @param packet_id Packet ID (command)
 * @param out_buffer Output buffer for complete frame
 * @param out_max_size Maximum size of output buffer
 * @return Number of bytes in output buffer (0 on error)
 */
uint16_t ST_BuildPacket(ST_Context* ctx, uint8_t payload_len, uint8_t packet_id,
                        uint8_t* out_buffer, uint16_t out_max_size);

/**
 * Calculate CRC8 (polynomial 0x9B)
 * @param data Data to checksum
 * @param len Length of data
 * @return CRC8 value
 */
uint8_t ST_CRC8(const uint8_t* data, uint8_t len);

#ifdef __cplusplus
}
#endif

#endif /* PMU_SERIAL_TRANSFER_H */

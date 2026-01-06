/**
 ******************************************************************************
 * @file           : pmu_serial_transfer.c
 * @brief          : SerialTransfer Protocol Implementation for STM32
 ******************************************************************************
 */

#include "pmu_serial_transfer.h"
#include <string.h>

/* CRC8 lookup table (polynomial 0x9B) */
static const uint8_t crc8_table[256] = {
    0x00, 0x9b, 0xad, 0x36, 0xc1, 0x5a, 0x6c, 0xf7,
    0x19, 0x82, 0xb4, 0x2f, 0xd8, 0x43, 0x75, 0xee,
    0x32, 0xa9, 0x9f, 0x04, 0xf3, 0x68, 0x5e, 0xc5,
    0x2b, 0xb0, 0x86, 0x1d, 0xea, 0x71, 0x47, 0xdc,
    0x64, 0xff, 0xc9, 0x52, 0xa5, 0x3e, 0x08, 0x93,
    0x7d, 0xe6, 0xd0, 0x4b, 0xbc, 0x27, 0x11, 0x8a,
    0x56, 0xcd, 0xfb, 0x60, 0x97, 0x0c, 0x3a, 0xa1,
    0x4f, 0xd4, 0xe2, 0x79, 0x8e, 0x15, 0x23, 0xb8,
    0xc8, 0x53, 0x65, 0xfe, 0x09, 0x92, 0xa4, 0x3f,
    0xd1, 0x4a, 0x7c, 0xe7, 0x10, 0x8b, 0xbd, 0x26,
    0xfa, 0x61, 0x57, 0xcc, 0x3b, 0xa0, 0x96, 0x0d,
    0xe3, 0x78, 0x4e, 0xd5, 0x22, 0xb9, 0x8f, 0x14,
    0xac, 0x37, 0x01, 0x9a, 0x6d, 0xf6, 0xc0, 0x5b,
    0xb5, 0x2e, 0x18, 0x83, 0x74, 0xef, 0xd9, 0x42,
    0x9e, 0x05, 0x33, 0xa8, 0x5f, 0xc4, 0xf2, 0x69,
    0x87, 0x1c, 0x2a, 0xb1, 0x46, 0xdd, 0xeb, 0x70,
    0x0b, 0x90, 0xa6, 0x3d, 0xca, 0x51, 0x67, 0xfc,
    0x12, 0x89, 0xbf, 0x24, 0xd3, 0x48, 0x7e, 0xe5,
    0x39, 0xa2, 0x94, 0x0f, 0xf8, 0x63, 0x55, 0xce,
    0x20, 0xbb, 0x8d, 0x16, 0xe1, 0x7a, 0x4c, 0xd7,
    0x6f, 0xf4, 0xc2, 0x59, 0xae, 0x35, 0x03, 0x98,
    0x76, 0xed, 0xdb, 0x40, 0xb7, 0x2c, 0x1a, 0x81,
    0x5d, 0xc6, 0xf0, 0x6b, 0x9c, 0x07, 0x31, 0xaa,
    0x44, 0xdf, 0xe9, 0x72, 0x85, 0x1e, 0x28, 0xb3,
    0xc3, 0x58, 0x6e, 0xf5, 0x02, 0x99, 0xaf, 0x34,
    0xda, 0x41, 0x77, 0xec, 0x1b, 0x80, 0xb6, 0x2d,
    0xf1, 0x6a, 0x5c, 0xc7, 0x30, 0xab, 0x9d, 0x06,
    0xe8, 0x73, 0x45, 0xde, 0x29, 0xb2, 0x84, 0x1f,
    0xa7, 0x3c, 0x0a, 0x91, 0x66, 0xfd, 0xcb, 0x50,
    0xbe, 0x25, 0x13, 0x88, 0x7f, 0xe4, 0xd2, 0x49,
    0x95, 0x0e, 0x38, 0xa3, 0x54, 0xcf, 0xf9, 0x62,
    0x8c, 0x17, 0x21, 0xba, 0x4d, 0xd6, 0xe0, 0x7b
};

/* Parser states */
enum {
    STATE_FIND_START = 0,
    STATE_FIND_ID,
    STATE_FIND_OVERHEAD,
    STATE_FIND_LEN,
    STATE_FIND_PAYLOAD,
    STATE_FIND_CRC,
    STATE_FIND_STOP
};

/* Calculate CRC8 */
uint8_t ST_CRC8(const uint8_t* data, uint8_t len)
{
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        crc = crc8_table[crc ^ data[i]];
    }
    return crc;
}

/* Initialize context */
void ST_Init(ST_Context* ctx, uint32_t timeout_ms)
{
    memset(ctx, 0, sizeof(ST_Context));
    ctx->timeout_ms = timeout_ms ? timeout_ms : 50;
    ctx->status = ST_STATUS_NO_DATA;
}

/* Reset context */
void ST_Reset(ST_Context* ctx)
{
    memset(ctx->tx_buff, 0, sizeof(ctx->tx_buff));
    memset(ctx->rx_buff, 0, sizeof(ctx->rx_buff));
    ctx->bytes_read = 0;
    ctx->packet_start_ms = 0;
    ctx->state = STATE_FIND_START;
    ctx->status = ST_STATUS_NO_DATA;
}

/* Find last occurrence of START_BYTE in buffer */
static int16_t find_last_start(const uint8_t* arr, uint8_t len)
{
    for (int16_t i = len - 1; i >= 0; i--) {
        if (arr[i] == ST_START_BYTE) {
            return i;
        }
    }
    return -1;
}

/* COBS unstuff packet */
static void cobs_unstuff(uint8_t* arr, uint8_t overhead_byte)
{
    uint8_t test_index = overhead_byte;
    uint8_t delta = 0;

    if (test_index <= ST_MAX_PAYLOAD) {
        while (arr[test_index]) {
            delta = arr[test_index];
            arr[test_index] = ST_START_BYTE;
            test_index += delta;
            if (test_index > ST_MAX_PAYLOAD) break;
        }
        if (test_index <= ST_MAX_PAYLOAD) {
            arr[test_index] = ST_START_BYTE;
        }
    }
}

/* Process received byte */
int8_t ST_ProcessByte(ST_Context* ctx, uint8_t byte, uint32_t current_ms)
{
    /* Check for stale packet */
    if (ctx->packet_start_ms != 0 &&
        (current_ms - ctx->packet_start_ms) >= ctx->timeout_ms) {
        ctx->bytes_read = 0;
        ctx->state = STATE_FIND_START;
        ctx->status = ST_STATUS_STALE_PACKET;
        ctx->packet_start_ms = 0;
        return ctx->status;
    }

    switch (ctx->state) {
        case STATE_FIND_START:
            if (byte == ST_START_BYTE) {
                ctx->state = STATE_FIND_ID;
                ctx->packet_start_ms = current_ms;
            }
            break;

        case STATE_FIND_ID:
            ctx->id_byte = byte;
            ctx->state = STATE_FIND_OVERHEAD;
            break;

        case STATE_FIND_OVERHEAD:
            ctx->rec_overhead_byte = byte;
            ctx->state = STATE_FIND_LEN;
            break;

        case STATE_FIND_LEN:
            if (byte > 0 && byte <= ST_MAX_PAYLOAD) {
                ctx->bytes_to_rec = byte;
                ctx->payload_index = 0;
                ctx->state = STATE_FIND_PAYLOAD;
            } else {
                ctx->bytes_read = 0;
                ctx->state = STATE_FIND_START;
                ctx->status = ST_STATUS_PAYLOAD_ERROR;
                ctx->packet_start_ms = 0;
                return ctx->status;
            }
            break;

        case STATE_FIND_PAYLOAD:
            if (ctx->payload_index < ctx->bytes_to_rec) {
                ctx->rx_buff[ctx->payload_index++] = byte;
                if (ctx->payload_index >= ctx->bytes_to_rec) {
                    ctx->state = STATE_FIND_CRC;
                }
            }
            break;

        case STATE_FIND_CRC:
            {
                uint8_t calc_crc = ST_CRC8(ctx->rx_buff, ctx->bytes_to_rec);
                if (calc_crc == byte) {
                    ctx->state = STATE_FIND_STOP;
                } else {
                    ctx->bytes_read = 0;
                    ctx->state = STATE_FIND_START;
                    ctx->status = ST_STATUS_CRC_ERROR;
                    ctx->packet_start_ms = 0;
                    return ctx->status;
                }
            }
            break;

        case STATE_FIND_STOP:
            ctx->state = STATE_FIND_START;
            ctx->packet_start_ms = 0;

            if (byte == ST_STOP_BYTE) {
                /* Valid packet received - unstuff COBS */
                cobs_unstuff(ctx->rx_buff, ctx->rec_overhead_byte);
                ctx->bytes_read = ctx->bytes_to_rec;
                ctx->current_packet_id = ctx->id_byte;
                ctx->status = ST_STATUS_NEW_DATA;

                /* Call callback if set */
                if (ctx->on_packet) {
                    ctx->on_packet(ctx->id_byte, ctx->rx_buff, ctx->bytes_read);
                }

                return ctx->status;
            } else {
                ctx->bytes_read = 0;
                ctx->status = ST_STATUS_STOP_BYTE_ERROR;
                return ctx->status;
            }

        default:
            ctx->state = STATE_FIND_START;
            ctx->bytes_read = 0;
            break;
    }

    ctx->bytes_read = 0;
    ctx->status = ST_STATUS_CONTINUE;
    return ctx->status;
}

/* Get packet ID */
uint8_t ST_GetPacketID(ST_Context* ctx)
{
    return ctx->current_packet_id;
}

/* Calculate COBS overhead byte */
static uint8_t calc_overhead(const uint8_t* arr, uint8_t len)
{
    for (uint8_t i = 0; i < len; i++) {
        if (arr[i] == ST_START_BYTE) {
            return i;
        }
    }
    return 0xFF;  /* No START_BYTE found */
}

/* COBS stuff packet */
static void cobs_stuff(uint8_t* arr, uint8_t len)
{
    int16_t ref_byte = find_last_start(arr, len);

    if (ref_byte != -1) {
        for (int16_t i = len - 1; i >= 0; i--) {
            if (arr[i] == ST_START_BYTE) {
                arr[i] = ref_byte - i;
                ref_byte = i;
            }
        }
    }
}

/* Build packet for transmission */
uint16_t ST_BuildPacket(ST_Context* ctx, uint8_t payload_len, uint8_t packet_id,
                        uint8_t* out_buffer, uint16_t out_max_size)
{
    if (payload_len > ST_MAX_PAYLOAD) {
        payload_len = ST_MAX_PAYLOAD;
    }

    /* Need: 1 start + 1 id + 1 overhead + 1 len + payload + 1 crc + 1 stop */
    uint16_t total_size = 6 + payload_len;
    if (total_size > out_max_size) {
        return 0;
    }

    /* Calculate overhead before stuffing */
    uint8_t overhead = calc_overhead(ctx->tx_buff, payload_len);

    /* Apply COBS stuffing */
    cobs_stuff(ctx->tx_buff, payload_len);

    /* Calculate CRC after stuffing */
    uint8_t crc = ST_CRC8(ctx->tx_buff, payload_len);

    /* Build frame */
    uint16_t idx = 0;
    out_buffer[idx++] = ST_START_BYTE;
    out_buffer[idx++] = packet_id;
    out_buffer[idx++] = overhead;
    out_buffer[idx++] = payload_len;

    /* Copy payload */
    memcpy(&out_buffer[idx], ctx->tx_buff, payload_len);
    idx += payload_len;

    out_buffer[idx++] = crc;
    out_buffer[idx++] = ST_STOP_BYTE;

    return idx;
}

/**
 * @file protocol.c
 * @brief PMU-30 Unified Binary Protocol Implementation
 */

#include "protocol.h"
#include <string.h>

/*============================================================================
 * CRC-16-CCITT Implementation
 *============================================================================*/

static const uint16_t crc16_table[256] = {
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0,
};

uint16_t Proto_CalcCRC(const uint8_t* data, uint16_t length)
{
    uint16_t crc = 0xFFFF;

    for (uint16_t i = 0; i < length; i++) {
        crc = (crc << 8) ^ crc16_table[(crc >> 8) ^ data[i]];
    }

    return crc;
}

/*============================================================================
 * Protocol Parser
 *============================================================================*/

void Proto_Init(
    ProtocolParser_t* parser,
    uint8_t* buffer,
    uint16_t buffer_size
)
{
    if (!parser) return;

    memset(parser, 0, sizeof(ProtocolParser_t));
    parser->state = PARSE_STATE_SYNC1;
    parser->buffer = buffer;
    parser->buffer_size = buffer_size;
}

void Proto_Reset(ProtocolParser_t* parser)
{
    if (!parser) return;

    parser->state = PARSE_STATE_SYNC1;
    parser->cmd = 0;
    parser->length = 0;
    parser->index = 0;
    parser->crc = 0;
}

bool Proto_ParseByte(
    ProtocolParser_t* parser,
    uint8_t byte,
    Proto_FrameCallback callback,
    void* user_data
)
{
    if (!parser) return false;

    switch (parser->state) {
        case PARSE_STATE_SYNC1:
            if (byte == PROTO_SYNC_H) {
                parser->state = PARSE_STATE_SYNC2;
            }
            break;

        case PARSE_STATE_SYNC2:
            if (byte == PROTO_SYNC_L) {
                parser->state = PARSE_STATE_CMD;
            } else if (byte == PROTO_SYNC_H) {
                /* Stay in SYNC2 - might be double sync */
            } else {
                parser->state = PARSE_STATE_SYNC1;
            }
            break;

        case PARSE_STATE_CMD:
            parser->cmd = byte;
            parser->state = PARSE_STATE_LEN_L;
            break;

        case PARSE_STATE_LEN_L:
            parser->length = byte;
            parser->state = PARSE_STATE_LEN_H;
            break;

        case PARSE_STATE_LEN_H:
            parser->length |= ((uint16_t)byte << 8);

            if (parser->length > PROTO_MAX_PAYLOAD) {
                /* Invalid length - reset */
                Proto_Reset(parser);
                return false;
            }

            if (parser->length > parser->buffer_size) {
                /* Buffer too small - reset */
                Proto_Reset(parser);
                return false;
            }

            parser->index = 0;

            if (parser->length == 0) {
                parser->state = PARSE_STATE_CRC_L;
            } else {
                parser->state = PARSE_STATE_PAYLOAD;
            }
            break;

        case PARSE_STATE_PAYLOAD:
            if (parser->buffer && parser->index < parser->buffer_size) {
                parser->buffer[parser->index] = byte;
            }
            parser->index++;

            if (parser->index >= parser->length) {
                parser->state = PARSE_STATE_CRC_L;
            }
            break;

        case PARSE_STATE_CRC_L:
            parser->crc = byte;
            parser->state = PARSE_STATE_CRC_H;
            break;

        case PARSE_STATE_CRC_H:
            parser->crc |= ((uint16_t)byte << 8);

            /* Verify CRC */
            {
                /* CRC is over CMD + LEN + PAYLOAD */
                uint8_t header[3];
                header[0] = parser->cmd;
                header[1] = parser->length & 0xFF;
                header[2] = (parser->length >> 8) & 0xFF;

                uint16_t calc_crc = Proto_CalcCRC(header, 3);
                if (parser->length > 0 && parser->buffer) {
                    calc_crc = 0xFFFF;
                    /* Recalculate over all data */
                    for (int i = 0; i < 3; i++) {
                        calc_crc = (calc_crc << 8) ^ crc16_table[(calc_crc >> 8) ^ header[i]];
                    }
                    for (uint16_t i = 0; i < parser->length; i++) {
                        calc_crc = (calc_crc << 8) ^ crc16_table[(calc_crc >> 8) ^ parser->buffer[i]];
                    }
                }

                if (calc_crc == parser->crc) {
                    /* Valid frame - call callback */
                    if (callback) {
                        callback(parser->cmd, parser->buffer, parser->length, user_data);
                    }
                    Proto_Reset(parser);
                    return true;
                }
            }

            /* CRC mismatch - reset */
            Proto_Reset(parser);
            break;
    }

    return false;
}

/*============================================================================
 * Frame Building
 *============================================================================*/

uint16_t Proto_BuildFrame(
    uint8_t* buffer,
    uint8_t cmd,
    const uint8_t* payload,
    uint16_t length
)
{
    if (!buffer) return 0;
    if (length > PROTO_MAX_PAYLOAD) return 0;

    uint16_t offset = 0;

    /* Sync bytes */
    buffer[offset++] = PROTO_SYNC_H;
    buffer[offset++] = PROTO_SYNC_L;

    /* Command */
    buffer[offset++] = cmd;

    /* Length (little-endian) */
    buffer[offset++] = length & 0xFF;
    buffer[offset++] = (length >> 8) & 0xFF;

    /* Payload */
    if (length > 0 && payload) {
        memcpy(&buffer[offset], payload, length);
        offset += length;
    }

    /* Calculate CRC over CMD + LEN + PAYLOAD */
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 2; i < offset; i++) {
        crc = (crc << 8) ^ crc16_table[(crc >> 8) ^ buffer[i]];
    }

    /* CRC (little-endian) */
    buffer[offset++] = crc & 0xFF;
    buffer[offset++] = (crc >> 8) & 0xFF;

    return offset;
}

bool Proto_SendFrame(
    uint8_t cmd,
    const uint8_t* payload,
    uint16_t length,
    Proto_SendFunc send_func,
    void* user_data
)
{
    if (!send_func) return false;
    if (length > PROTO_MAX_PAYLOAD) return false;

    uint8_t frame[PROTO_MAX_FRAME];
    uint16_t frame_len = Proto_BuildFrame(frame, cmd, payload, length);

    if (frame_len == 0) return false;

    return send_func(frame, frame_len, user_data);
}

/*============================================================================
 * Convenience Functions
 *============================================================================*/

bool Proto_SendPing(Proto_SendFunc send_func, void* user_data)
{
    return Proto_SendFrame(CMD_PING, NULL, 0, send_func, user_data);
}

bool Proto_SendPong(Proto_SendFunc send_func, void* user_data)
{
    return Proto_SendFrame(CMD_PONG, NULL, 0, send_func, user_data);
}

bool Proto_SendError(
    ProtocolError_t error,
    uint8_t original_cmd,
    Proto_SendFunc send_func,
    void* user_data
)
{
    uint8_t payload[2] = { (uint8_t)error, original_cmd };
    return Proto_SendFrame(CMD_ERROR, payload, 2, send_func, user_data);
}

bool Proto_SendCaps(
    const DeviceCaps_t* caps,
    Proto_SendFunc send_func,
    void* user_data
)
{
    if (!caps) return false;
    return Proto_SendFrame(CMD_CAPS_RESP, (const uint8_t*)caps, sizeof(DeviceCaps_t), send_func, user_data);
}

/*============================================================================
 * Telemetry Size Calculation
 *============================================================================*/

uint16_t Telem_CalcSize(
    const DeviceCaps_t* caps,
    uint16_t sections
)
{
    if (!caps) return 0;

    uint16_t size = 0;

    /* Header is always present */
    if (sections & TELEM_SEC_HEADER) {
        size += sizeof(TelemHeader_t);
    }

    /* Output states (1 byte per output) */
    if (sections & TELEM_SEC_OUTPUTS) {
        size += caps->profet_count;
    }

    /* Output currents (2 bytes per output) */
    if (sections & TELEM_SEC_CURRENTS) {
        size += caps->profet_count * 2;
    }

    /* ADC values (2 bytes per channel) */
    if (sections & TELEM_SEC_ADC) {
        size += caps->adc_count * 2;
    }

    /* Digital inputs (4 bytes bitmask) */
    if (sections & TELEM_SEC_DIN) {
        size += 4;
    }

    /* H-Bridge (8 bytes per bridge) */
    if (sections & TELEM_SEC_HBRIDGE) {
        size += caps->hbridge_count * 8;
    }

    /* Faults (4 bytes bitmask + 4 bytes details) */
    if (sections & TELEM_SEC_FAULTS) {
        size += 8;
    }

    return size;
}

/*============================================================================
 * Channel Value Commands
 *============================================================================*/

bool Proto_SendChannelValue(
    uint16_t channel_id,
    int32_t value,
    Proto_SendFunc send_func,
    void* user_data
)
{
    uint8_t payload[6];
    payload[0] = channel_id & 0xFF;
    payload[1] = (channel_id >> 8) & 0xFF;
    payload[2] = value & 0xFF;
    payload[3] = (value >> 8) & 0xFF;
    payload[4] = (value >> 16) & 0xFF;
    payload[5] = (value >> 24) & 0xFF;

    return Proto_SendFrame(CMD_CH_VALUE_RESP, payload, 6, send_func, user_data);
}

bool Proto_ParseChannelValue(
    const uint8_t* payload,
    uint16_t length,
    uint16_t* channel_id,
    int32_t* value
)
{
    if (!payload || length < 6) return false;

    if (channel_id) {
        *channel_id = payload[0] | ((uint16_t)payload[1] << 8);
    }

    if (value) {
        *value = payload[2] |
                 ((int32_t)payload[3] << 8) |
                 ((int32_t)payload[4] << 16) |
                 ((int32_t)payload[5] << 24);
    }

    return true;
}

/*============================================================================
 * Telemetry Configuration
 *============================================================================*/

bool Proto_SendTelemConfig(
    uint16_t sections,
    uint16_t rate_ms,
    Proto_SendFunc send_func,
    void* user_data
)
{
    uint8_t payload[4];
    payload[0] = sections & 0xFF;
    payload[1] = (sections >> 8) & 0xFF;
    payload[2] = rate_ms & 0xFF;
    payload[3] = (rate_ms >> 8) & 0xFF;

    return Proto_SendFrame(CMD_TELEM_CONFIG, payload, 4, send_func, user_data);
}

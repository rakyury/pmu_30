/**
 ******************************************************************************
 * @file           : pmu_min_port.h
 * @brief          : MIN Protocol Port Adapter Header
 ******************************************************************************
 */

#ifndef PMU_MIN_PORT_H
#define PMU_MIN_PORT_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* MIN Command IDs (0-63 range for MIN protocol) */
#define MIN_CMD_PING              0x01
#define MIN_CMD_PONG              0x02
#define MIN_CMD_GET_CONFIG        0x10
#define MIN_CMD_CONFIG_DATA       0x11
#define MIN_CMD_LOAD_CONFIG       0x12
#define MIN_CMD_CONFIG_ACK        0x13
#define MIN_CMD_SAVE_CONFIG       0x14
#define MIN_CMD_FLASH_ACK         0x15
#define MIN_CMD_CLEAR_CONFIG      0x16
#define MIN_CMD_CLEAR_CONFIG_ACK  0x17
#define MIN_CMD_LOAD_BINARY       0x18
#define MIN_CMD_BINARY_ACK        0x19
#define MIN_CMD_START_STREAM      0x20
#define MIN_CMD_STOP_STREAM       0x21
#define MIN_CMD_DATA              0x22
#define MIN_CMD_SET_OUTPUT        0x28
#define MIN_CMD_OUTPUT_ACK        0x29
#define MIN_CMD_ACK               0x3E
#define MIN_CMD_NACK              0x3F

/**
 * @brief Initialize MIN protocol
 */
void PMU_MIN_Init(void);

/**
 * @brief Process received byte through MIN
 * @param byte Received byte
 */
void PMU_MIN_ProcessByte(uint8_t byte);

/**
 * @brief Periodic MIN update - call every 1ms
 */
void PMU_MIN_Update(void);

/**
 * @brief Send telemetry data packet
 */
void PMU_MIN_SendTelemetry(void);

/**
 * @brief Check if MIN stream is active
 * @return true if streaming
 */
bool PMU_MIN_IsStreamActive(void);

#ifdef __cplusplus
}
#endif

#endif /* PMU_MIN_PORT_H */

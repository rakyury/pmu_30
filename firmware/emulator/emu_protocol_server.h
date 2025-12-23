/**
 ******************************************************************************
 * @file           : emu_protocol_server.h
 * @brief          : TCP Server for Configurator Connection
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements a TCP server that allows the PMU-30 Configurator
 * to connect to the emulator and communicate using the standard protocol.
 *
 ******************************************************************************
 */

#ifndef EMU_PROTOCOL_SERVER_H
#define EMU_PROTOCOL_SERVER_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Server configuration
 */
typedef struct {
    uint16_t port;              /**< TCP port to listen on */
    uint32_t timeout_ms;        /**< Connection timeout */
    bool verbose;               /**< Enable verbose logging */
} EMU_ServerConfig_t;

/**
 * @brief Server statistics
 */
typedef struct {
    uint32_t connections_total;     /**< Total connections received */
    uint32_t connections_active;    /**< Currently active connections */
    uint32_t messages_rx;           /**< Messages received */
    uint32_t messages_tx;           /**< Messages sent */
    uint32_t errors;                /**< Protocol errors */
} EMU_ServerStats_t;

/* Exported constants --------------------------------------------------------*/

#define EMU_SERVER_DEFAULT_PORT     9876
#define EMU_SERVER_MAX_CLIENTS      4
#define EMU_SERVER_BUFFER_SIZE      8192

/* Protocol constants */
#define EMU_PROTO_START_BYTE        0xAA
#define EMU_PROTO_HEADER_SIZE       4
#define EMU_PROTO_CRC_SIZE          2
#define EMU_PROTO_MAX_PAYLOAD       4096

/* Message types (matching configurator protocol) */
#define EMU_MSG_PING                0x01
#define EMU_MSG_PONG                0x02
#define EMU_MSG_GET_INFO            0x10
#define EMU_MSG_INFO_RESP           0x11
#define EMU_MSG_GET_CONFIG          0x20
#define EMU_MSG_CONFIG_DATA         0x21
#define EMU_MSG_SET_CONFIG          0x22
#define EMU_MSG_CONFIG_ACK          0x23
#define EMU_MSG_SAVE_TO_FLASH       0x24
#define EMU_MSG_FLASH_ACK           0x25
#define EMU_MSG_SUBSCRIBE_TELEM     0x30
#define EMU_MSG_UNSUBSCRIBE_TELEM   0x31
#define EMU_MSG_TELEMETRY_DATA      0x32
#define EMU_MSG_SET_CHANNEL         0x40
#define EMU_MSG_CHANNEL_ACK         0x41
#define EMU_MSG_GET_CHANNEL         0x42
#define EMU_MSG_CHANNEL_DATA        0x43
#define EMU_MSG_ERROR               0x50
#define EMU_MSG_LOG                 0x55
#define EMU_MSG_RESTART             0x70
#define EMU_MSG_RESTART_ACK         0x71

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize the protocol server
 * @param config Server configuration (NULL for defaults)
 * @retval 0 on success, -1 on error
 */
int EMU_Server_Init(const EMU_ServerConfig_t* config);

/**
 * @brief Start the server (non-blocking)
 * @retval 0 on success, -1 on error
 */
int EMU_Server_Start(void);

/**
 * @brief Stop the server
 */
void EMU_Server_Stop(void);

/**
 * @brief Process server events (call periodically)
 * @param timeout_ms Maximum time to wait for events
 */
void EMU_Server_Process(uint32_t timeout_ms);

/**
 * @brief Check if server is running
 * @retval true if running
 */
bool EMU_Server_IsRunning(void);

/**
 * @brief Check if any client is connected
 * @retval true if at least one client connected
 */
bool EMU_Server_HasClients(void);

/**
 * @brief Get server statistics
 * @retval Pointer to statistics structure
 */
const EMU_ServerStats_t* EMU_Server_GetStats(void);

/**
 * @brief Send telemetry update to all connected clients
 */
void EMU_Server_SendTelemetry(void);

/**
 * @brief Send log message to all connected clients
 * @param level Log level (0=debug, 1=info, 2=warning, 3=error)
 * @param source Source identifier (e.g., "lua", "system")
 * @param message Log message text
 */
void EMU_Server_SendLog(uint8_t level, const char* source, const char* message);

/**
 * @brief Broadcast message to all clients
 * @param msg_type Message type
 * @param payload Payload data
 * @param len Payload length
 * @retval Number of clients message was sent to
 */
int EMU_Server_Broadcast(uint8_t msg_type, const uint8_t* payload, uint16_t len);

/**
 * @brief Load last configuration from file
 * @param filename Config file path (NULL for default "last_config.json")
 * @retval 0 on success, -1 on error or file not found
 */
int EMU_Server_LoadConfig(const char* filename);

#ifdef __cplusplus
}
#endif

#endif /* EMU_PROTOCOL_SERVER_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

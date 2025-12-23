/**
 ******************************************************************************
 * @file           : emu_webui.h
 * @brief          : Web UI Server for Browser Monitoring
 * @author         : R2 m-sport
 * @date           : 2025-12-23
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides a simple HTTP server with WebSocket support for
 * real-time monitoring of the PMU-30 emulator in a web browser.
 *
 ******************************************************************************
 */

#ifndef EMU_WEBUI_H
#define EMU_WEBUI_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Web UI configuration
 */
typedef struct {
    uint16_t http_port;         /**< HTTP server port (default 8080) */
    bool auto_open_browser;     /**< Open browser on start */
    bool verbose;               /**< Enable verbose logging */
} EMU_WebUI_Config_t;

/**
 * @brief Web UI statistics
 */
typedef struct {
    uint32_t http_requests;         /**< Total HTTP requests */
    uint32_t ws_connections;        /**< WebSocket connections */
    uint32_t ws_messages_sent;      /**< WebSocket messages sent */
    uint32_t ws_messages_recv;      /**< WebSocket messages received */
    uint32_t active_ws_clients;     /**< Currently connected WebSocket clients */
} EMU_WebUI_Stats_t;

/* Exported constants --------------------------------------------------------*/

#define EMU_WEBUI_DEFAULT_PORT      8080
#define EMU_WEBUI_MAX_WS_CLIENTS    8
#define EMU_WEBUI_BUFFER_SIZE       16384

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize Web UI server
 * @param config Configuration (NULL for defaults)
 * @retval 0 on success, -1 on error
 */
int EMU_WebUI_Init(const EMU_WebUI_Config_t* config);

/**
 * @brief Start Web UI server
 * @retval 0 on success, -1 on error
 */
int EMU_WebUI_Start(void);

/**
 * @brief Stop Web UI server
 */
void EMU_WebUI_Stop(void);

/**
 * @brief Process Web UI events (call periodically)
 * @param timeout_ms Maximum time to wait for events
 */
void EMU_WebUI_Process(uint32_t timeout_ms);

/**
 * @brief Check if server is running
 * @retval true if running
 */
bool EMU_WebUI_IsRunning(void);

/**
 * @brief Send telemetry update to all WebSocket clients
 */
void EMU_WebUI_SendTelemetry(void);

/**
 * @brief Send log message to WebSocket clients
 * @param level Log level
 * @param source Source identifier
 * @param message Log message
 */
void EMU_WebUI_SendLog(uint8_t level, const char* source, const char* message);

/**
 * @brief Get Web UI statistics
 * @retval Pointer to statistics structure
 */
const EMU_WebUI_Stats_t* EMU_WebUI_GetStats(void);

/**
 * @brief Open browser with Web UI URL
 */
void EMU_WebUI_OpenBrowser(void);

/**
 * @brief Add command log entry (for logging configurator commands)
 * @param level Log level (0=debug, 1=info, 2=warning, 3=error)
 * @param format Printf-style format string
 * @param ... Variable arguments
 */
void EMU_WebUI_AddCmdLog(uint8_t level, const char* format, ...);

/**
 * @brief Send CAN TX notification to WebSocket clients
 * @param bus CAN bus number
 * @param id CAN message ID
 * @param data Data bytes
 * @param len Data length
 */
void EMU_WebUI_SendCanTx(uint8_t bus, uint32_t id, const uint8_t* data, uint8_t len);

#ifdef __cplusplus
}
#endif

#endif /* EMU_WEBUI_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

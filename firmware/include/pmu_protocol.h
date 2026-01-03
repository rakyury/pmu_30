/**
 ******************************************************************************
 * @file           : pmu_protocol.h
 * @brief          : Real-Time Control Protocol Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements a real-time control protocol
 * for monitoring and controlling the PMU-30 via UART, WiFi (ESP32), or CAN.
 *
 * Protocol Features:
 * - Binary protocol for efficiency
 * - Request/response pattern
 * - Streaming telemetry data
 * - Configuration upload/download
 * - Real-time parameter adjustment
 * - Firmware update support
 *
 * Transport: UART (115200 baud), WiFi (ESP32-C3), CAN (1Mbps)
 *
 ******************************************************************************
 */

#ifndef PMU_PROTOCOL_H
#define PMU_PROTOCOL_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#ifdef NUCLEO_F446RE
#include "stm32f4xx_hal.h"
#else
#include "stm32h7xx_hal.h"
#endif
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Protocol command types
 */
typedef enum {
    /* Basic commands (0x00-0x1F) - matches configurator protocol */
    PMU_CMD_PING                = 0x01,  /**< Ping device */
    PMU_CMD_PONG                = 0x02,  /**< Pong response */
    PMU_CMD_GET_VERSION         = 0x10,  /**< Get firmware version (GET_INFO) */
    PMU_CMD_GET_SERIAL          = 0x03,  /**< Get serial number */
    PMU_CMD_INFO_RESP           = 0x11,  /**< Info response */

    /* Configuration commands (0x20-0x2F) - matches configurator protocol */
    PMU_CMD_GET_CONFIG          = 0x20,  /**< Get current configuration */
    PMU_CMD_CONFIG_DATA         = 0x21,  /**< Configuration data response */
    PMU_CMD_LOAD_CONFIG         = 0x22,  /**< Load/set configuration (SET_CONFIG) */
    PMU_CMD_CONFIG_ACK          = 0x23,  /**< Configuration acknowledgment */
    PMU_CMD_SAVE_CONFIG         = 0x24,  /**< Save configuration to flash */
    PMU_CMD_FLASH_ACK           = 0x25,  /**< Flash save acknowledgment */
    PMU_CMD_CLEAR_CONFIG        = 0x26,  /**< Clear config from memory and flash */
    PMU_CMD_CLEAR_CONFIG_ACK    = 0x27,  /**< Clear config acknowledgment */

    /* Telemetry commands (0x30-0x3F) - matches configurator protocol */
    PMU_CMD_START_STREAM        = 0x30,  /**< Subscribe to telemetry */
    PMU_CMD_STOP_STREAM         = 0x31,  /**< Unsubscribe from telemetry */
    PMU_CMD_DATA                = 0x32,  /**< Telemetry data */

    /* Control commands (0x40-0x4F) - matches configurator protocol */
    PMU_CMD_SET_OUTPUT          = 0x40,  /**< Set channel value */
    PMU_CMD_OUTPUT_ACK          = 0x41,  /**< Channel set acknowledgment */
    PMU_CMD_SET_HBRIDGE         = 0x42,  /**< Set H-bridge mode */
    PMU_CMD_GET_CHANNEL         = 0x43,  /**< Get channel value */
    PMU_CMD_CHANNEL_DATA        = 0x44,  /**< Channel data response */
    PMU_CMD_SET_PWM             = 0x45,  /**< Set PWM duty cycle */
    PMU_CMD_GET_OUTPUTS         = 0x46,  /**< Get all output states */
    PMU_CMD_GET_INPUTS          = 0x47,  /**< Get all input states */

    /* Error/Log (0x50-0x5F) */
    PMU_CMD_ERROR               = 0x50,  /**< Error message */
    PMU_CMD_LOG                 = 0x55,  /**< Log message */

    /* Device control (0x60-0x6F) */
    PMU_CMD_SET_CHANNEL_CONFIG  = 0x66,  /**< Set single channel config (atomic update) */
    PMU_CMD_CHANNEL_CONFIG_ACK  = 0x67,  /**< Channel config update response */
    PMU_CMD_LOAD_BINARY_CONFIG  = 0x68,  /**< Load binary configuration (chunked) */
    PMU_CMD_BINARY_CONFIG_ACK   = 0x69,  /**< Binary config acknowledgment */

    /* Device restart (0x70-0x7F) */
    PMU_CMD_RESET               = 0x70,  /**< Reset/restart device */
    PMU_CMD_RESET_ACK           = 0x71,  /**< Reset acknowledgment */
    PMU_CMD_BOOT_COMPLETE       = 0x72,  /**< Boot complete notification */

    /* Logging commands (0x80-0x9F) */
    PMU_CMD_START_LOGGING       = 0x80,  /**< Start data logging */
    PMU_CMD_STOP_LOGGING        = 0x81,  /**< Stop data logging */
    PMU_CMD_GET_LOG_INFO        = 0x82,  /**< Get log information */
    PMU_CMD_DOWNLOAD_LOG        = 0x83,  /**< Download log data */
    PMU_CMD_ERASE_LOGS          = 0x84,  /**< Erase all logs */

    /* Diagnostic commands (0xA0-0xAF) */
    PMU_CMD_GET_STATS           = 0xA0,  /**< Get system statistics */
    PMU_CMD_GET_UPTIME          = 0xA1,  /**< Get system uptime */
    PMU_CMD_GET_CAN_STATS       = 0xA2,  /**< Get CAN bus statistics */
    PMU_CMD_SELF_TEST           = 0xA3,  /**< Run self-test */

    /* Lua scripting commands (0xB0-0xBF) */
    PMU_CMD_LUA_EXECUTE         = 0xB0,  /**< Execute Lua code directly */
    PMU_CMD_LUA_LOAD_SCRIPT     = 0xB1,  /**< Load/update Lua script */
    PMU_CMD_LUA_UNLOAD_SCRIPT   = 0xB2,  /**< Unload Lua script */
    PMU_CMD_LUA_RUN_SCRIPT      = 0xB3,  /**< Run loaded script by name */
    PMU_CMD_LUA_STOP_SCRIPT     = 0xB4,  /**< Stop running script */
    PMU_CMD_LUA_GET_SCRIPTS     = 0xB5,  /**< List loaded scripts */
    PMU_CMD_LUA_GET_STATUS      = 0xB6,  /**< Get Lua engine status */
    PMU_CMD_LUA_GET_OUTPUT      = 0xB7,  /**< Get script output/result */
    PMU_CMD_LUA_SET_ENABLED     = 0xB8,  /**< Enable/disable script */

    /* Firmware update (0xC0-0xDF) */
    PMU_CMD_FW_UPDATE_START     = 0xC0,  /**< Start firmware update */
    PMU_CMD_FW_UPDATE_DATA      = 0xC1,  /**< Send firmware data chunk */
    PMU_CMD_FW_UPDATE_FINISH    = 0xC2,  /**< Finish firmware update */
    PMU_CMD_FW_UPDATE_ABORT     = 0xC3,  /**< Abort firmware update */

    /* Response codes (0xE0-0xFF) */
    PMU_CMD_ACK                 = 0xE0,  /**< Command acknowledged */
    PMU_CMD_NACK                = 0xE1   /**< Command not acknowledged */
    /* Note: PMU_CMD_ERROR = 0x50, PMU_CMD_DATA = 0x32 defined above */
} PMU_CMD_Type_t;

/**
 * @brief Protocol packet structure
 *
 * Frame format v2 with sequence ID for request-response correlation:
 * ┌──────┬────────┬───────┬───────┬─────────────┬───────┐
 * │ 0xAA │ Length │ SeqID │ MsgID │   Payload   │ CRC16 │
 * │ 1B   │ 2B LE  │ 2B LE │ 1B    │ Variable    │ 2B LE │
 * └──────┴────────┴───────┴───────┴─────────────┴───────┘
 *
 * - SeqID: Sequence number echoed in responses for correlation
 *   - 0x0000: Broadcast/unsolicited (no response expected)
 *   - 0x0001-0xFFFE: Normal requests (response includes same SeqID)
 *   - 0xFFFF: Reserved
 * - Length: Payload length only (excludes SeqID, MsgID, CRC)
 * - CRC16: Calculated over Length+SeqID+MsgID+Payload (excludes 0xAA)
 */
typedef struct __attribute__((packed)) {
    uint8_t  start_marker;      /**< Start marker (0xAA) */
    uint16_t length;            /**< Payload length (little-endian) */
    uint16_t seq_id;            /**< Sequence ID for request-response matching */
    uint8_t  command;           /**< Command/message type */
    uint8_t  data[2048];        /**< Payload data */
    uint16_t crc16;             /**< CRC16 checksum (little-endian) */
} PMU_Protocol_Packet_t;

/** Sequence ID values */
#define PMU_SEQ_BROADCAST       0x0000  /**< Broadcast - no response expected */
#define PMU_SEQ_RESERVED        0xFFFF  /**< Reserved */

/**
 * @brief Telemetry stream configuration
 */
typedef struct {
    bool outputs_enabled;       /**< Stream output states */
    bool inputs_enabled;        /**< Stream input values */
    bool can_enabled;           /**< Stream CAN data */
    bool temps_enabled;         /**< Stream temperatures */
    bool voltages_enabled;      /**< Stream voltages */
    bool faults_enabled;        /**< Stream faults */
    bool channels_enabled;      /**< Stream virtual channel values */
    uint16_t rate_hz;           /**< Stream rate in Hz (1-1000) */
} PMU_TelemetryConfig_t;

/**
 * @brief Protocol statistics
 */
typedef struct {
    uint32_t rx_packets;        /**< Received packets */
    uint32_t tx_packets;        /**< Transmitted packets */
    uint32_t rx_errors;         /**< RX errors (CRC, format) */
    uint32_t tx_errors;         /**< TX errors */
    uint32_t last_rx_time_ms;   /**< Last RX timestamp */
    uint32_t last_tx_time_ms;   /**< Last TX timestamp */
} PMU_Protocol_Stats_t;

/**
 * @brief Protocol transport interface
 */
typedef enum {
    PMU_TRANSPORT_UART,         /**< UART transport */
    PMU_TRANSPORT_WIFI,         /**< WiFi transport (ESP32) */
    PMU_TRANSPORT_CAN           /**< CAN transport */
} PMU_Transport_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_PROTOCOL_START_MARKER     0xAA   /**< Packet start marker */
#define PMU_PROTOCOL_VERSION          0x01   /**< Protocol version */
#define PMU_PROTOCOL_MAX_PAYLOAD      2048    /**< Maximum payload size */
#define PMU_PROTOCOL_UART_BAUD        115200 /**< UART baud rate */
#define PMU_PROTOCOL_CAN_ID_BASE      0x600  /**< CAN base ID */

/* Telemetry stream rates */
#define PMU_STREAM_RATE_1HZ           1
#define PMU_STREAM_RATE_10HZ          10
#define PMU_STREAM_RATE_50HZ          50
#define PMU_STREAM_RATE_100HZ         100
#define PMU_STREAM_RATE_500HZ         500
#define PMU_STREAM_RATE_1000HZ        1000

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize protocol handler
 * @param transport Transport interface to use
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_Init(PMU_Transport_t transport);

/**
 * @brief Process received data (call from UART/CAN RX callback)
 * @param data Pointer to received data
 * @param length Length of received data
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_ProcessData(const uint8_t* data, uint16_t length);

/**
 * @brief Update protocol handler (call at 1kHz)
 * @retval None
 */
void PMU_Protocol_Update(void);

/**
 * @brief Send telemetry packet
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_SendTelemetry(void);

/**
 * @brief Send response packet with sequence ID
 * @param command Command type
 * @param seq_id Sequence ID from request (echoed back for correlation)
 * @param data Payload data
 * @param length Payload length
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_SendResponse(PMU_CMD_Type_t command,
                                             uint16_t seq_id,
                                             const uint8_t* data,
                                             uint16_t length);

/**
 * @brief Send broadcast packet (no response expected)
 * @param command Command type
 * @param data Payload data
 * @param length Payload length
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_SendBroadcast(PMU_CMD_Type_t command,
                                              const uint8_t* data,
                                              uint16_t length);

/**
 * @brief Configure telemetry streaming
 * @param config Telemetry configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_ConfigureStream(PMU_TelemetryConfig_t* config);

/**
 * @brief Start telemetry streaming
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_StartStream(void);

/**
 * @brief Stop telemetry streaming
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_StopStream(void);

/**
 * @brief Check if telemetry stream is active
 * @retval true if streaming, false otherwise
 */
bool PMU_Protocol_IsStreamActive(void);

/**
 * @brief Get protocol statistics
 * @retval Pointer to statistics structure
 */
PMU_Protocol_Stats_t* PMU_Protocol_GetStats(void);

/**
 * @brief Calculate CRC16 checksum
 * @param data Data buffer
 * @param length Data length
 * @retval CRC16 checksum
 */
uint16_t PMU_Protocol_CRC16(const uint8_t* data, uint16_t length);

/**
 * @brief Load saved binary config from flash at startup
 * @retval true if config was loaded successfully
 */
bool PMU_Protocol_LoadSavedConfig(void);

#ifdef NUCLEO_F446RE
/**
 * @brief Process any pending RX bytes buffered during TX
 * Call this after TX completes to handle bytes received during transmission.
 */
void PMU_Protocol_ProcessPendingRx(void);

/**
 * @brief Check if TX is in progress (for main loop synchronization)
 * @retval true if TX is in progress, false otherwise
 *
 * Main loop should NOT read RX directly while TX is in progress.
 * During TX, incoming bytes are buffered internally and processed
 * by PMU_Protocol_ProcessPendingRx() after TX completes.
 */
bool PMU_Protocol_IsTxInProgress(void);
#endif

#ifdef __cplusplus
}
#endif

#endif /* PMU_PROTOCOL_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

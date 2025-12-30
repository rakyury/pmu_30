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
    /* Basic commands (0x00-0x1F) */
    PMU_CMD_PING                = 0x01,  /**< Ping device */
    PMU_CMD_GET_VERSION         = 0x02,  /**< Get firmware version */
    PMU_CMD_GET_SERIAL          = 0x03,  /**< Get serial number */
    PMU_CMD_RESET               = 0x04,  /**< Reset device */
    PMU_CMD_BOOTLOADER          = 0x05,  /**< Enter bootloader */

    /* Telemetry commands (0x20-0x3F) */
    PMU_CMD_START_STREAM        = 0x20,  /**< Start telemetry streaming */
    PMU_CMD_STOP_STREAM         = 0x21,  /**< Stop telemetry streaming */
    PMU_CMD_GET_OUTPUTS         = 0x22,  /**< Get output states */
    PMU_CMD_GET_INPUTS          = 0x23,  /**< Get input values */
    PMU_CMD_GET_CAN             = 0x24,  /**< Get CAN data */
    PMU_CMD_GET_TEMPS           = 0x25,  /**< Get temperatures */
    PMU_CMD_GET_VOLTAGES        = 0x26,  /**< Get voltages */
    PMU_CMD_GET_FAULTS          = 0x27,  /**< Get fault status */

    /* Control commands (0x40-0x5F) */
    PMU_CMD_SET_OUTPUT          = 0x40,  /**< Set output state */
    PMU_CMD_SET_PWM             = 0x41,  /**< Set PWM duty cycle */
    PMU_CMD_SET_HBRIDGE         = 0x42,  /**< Set H-bridge mode */
    PMU_CMD_CLEAR_FAULTS        = 0x43,  /**< Clear all faults */
    PMU_CMD_SET_VIRTUAL         = 0x44,  /**< Set virtual channel value */

    /* Configuration commands (0x60-0x7F) */
    PMU_CMD_LOAD_CONFIG         = 0x60,  /**< Load configuration */
    PMU_CMD_SAVE_CONFIG         = 0x61,  /**< Save configuration to flash */
    PMU_CMD_GET_CONFIG          = 0x62,  /**< Get current configuration */
    PMU_CMD_UPLOAD_CONFIG       = 0x63,  /**< Upload configuration (chunked) */
    PMU_CMD_DOWNLOAD_CONFIG     = 0x64,  /**< Download configuration (chunked) */
    PMU_CMD_VALIDATE_CONFIG     = 0x65,  /**< Validate configuration */
    PMU_CMD_SET_CHANNEL_CONFIG  = 0x66,  /**< Set single channel config (atomic update) */
    PMU_CMD_CHANNEL_CONFIG_ACK  = 0x67,  /**< Channel config update response */

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
    PMU_CMD_NACK                = 0xE1,  /**< Command not acknowledged */
    PMU_CMD_ERROR               = 0xE2,  /**< Error response */
    PMU_CMD_DATA                = 0xE3   /**< Data response */
} PMU_CMD_Type_t;

/**
 * @brief Protocol packet structure
 */
typedef struct __attribute__((packed)) {
    uint8_t  start_marker;      /**< Start marker (0xAA) */
    uint8_t  command;           /**< Command type */
    uint16_t length;            /**< Payload length */
    uint8_t  data[256];         /**< Payload data */
    uint16_t crc16;             /**< CRC16 checksum */
} PMU_Protocol_Packet_t;

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
#define PMU_PROTOCOL_MAX_PAYLOAD      256    /**< Maximum payload size */
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
 * @brief Send response packet
 * @param command Command type
 * @param data Payload data
 * @param length Payload length
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Protocol_SendResponse(PMU_CMD_Type_t command,
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

#ifdef __cplusplus
}
#endif

#endif /* PMU_PROTOCOL_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

/**
 ******************************************************************************
 * @file           : pmu_esp32.h
 * @brief          : ESP32-C3 Communication Bridge
 * @author         : R2 m-sport
 * @date           : 2025-12-30
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides low-level UART communication with the ESP32-C3 module
 * that handles WiFi and Bluetooth connectivity. It uses AT commands to
 * control the ESP32 and parse responses.
 *
 * Hardware connections:
 * - UART3_TX (PC10) -> ESP32 RX
 * - UART3_RX (PC11) -> ESP32 TX
 * - GPIO ESP_RST    -> ESP32 EN (reset)
 * - GPIO ESP_BOOT   -> ESP32 IO0 (boot mode)
 *
 ******************************************************************************
 */

#ifndef __PMU_ESP32_H
#define __PMU_ESP32_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief ESP32 module state
 */
typedef enum {
    PMU_ESP32_STATE_OFF = 0,        /**< Module powered off or not responding */
    PMU_ESP32_STATE_BOOTING,        /**< Module is booting up */
    PMU_ESP32_STATE_READY,          /**< Module ready, AT commands accepted */
    PMU_ESP32_STATE_BUSY,           /**< Module busy processing command */
    PMU_ESP32_STATE_ERROR           /**< Module in error state */
} PMU_ESP32_State_t;

/**
 * @brief AT command response status
 */
typedef enum {
    PMU_ESP32_RESP_OK = 0,          /**< OK response received */
    PMU_ESP32_RESP_ERROR,           /**< ERROR response received */
    PMU_ESP32_RESP_FAIL,            /**< FAIL response received */
    PMU_ESP32_RESP_TIMEOUT,         /**< No response within timeout */
    PMU_ESP32_RESP_BUSY,            /**< busy p... or busy s... received */
    PMU_ESP32_RESP_PENDING          /**< Still waiting for response */
} PMU_ESP32_Response_t;

/**
 * @brief ESP32 module information
 */
typedef struct {
    char at_version[32];            /**< AT firmware version */
    char sdk_version[32];           /**< SDK version */
    char mac_sta[18];               /**< Station MAC address (xx:xx:xx:xx:xx:xx) */
    char mac_ap[18];                /**< AP MAC address */
} PMU_ESP32_Info_t;

/**
 * @brief ESP32 statistics
 */
typedef struct {
    uint32_t commands_sent;         /**< Total AT commands sent */
    uint32_t responses_ok;          /**< OK responses received */
    uint32_t responses_error;       /**< ERROR responses received */
    uint32_t timeouts;              /**< Command timeouts */
    uint32_t rx_bytes;              /**< Total bytes received */
    uint32_t tx_bytes;              /**< Total bytes transmitted */
    uint32_t last_response_time_ms; /**< Time of last response */
} PMU_ESP32_Stats_t;

/* Exported constants --------------------------------------------------------*/

/* UART configuration */
#define PMU_ESP32_UART_BAUD         115200
#define PMU_ESP32_UART_TIMEOUT_MS   100

/* Ring buffer sizes */
#define PMU_ESP32_RX_BUFFER_SIZE    512
#define PMU_ESP32_TX_BUFFER_SIZE    256
#define PMU_ESP32_RESP_BUFFER_SIZE  256

/* Command timeouts (ms) */
#define PMU_ESP32_CMD_TIMEOUT_MS    1000    /**< Default command timeout */
#define PMU_ESP32_WIFI_TIMEOUT_MS   10000   /**< WiFi connect/scan timeout */
#define PMU_ESP32_RESET_TIMEOUT_MS  3000    /**< Reset sequence timeout */

/* Response markers */
#define PMU_ESP32_RESP_OK_STR       "OK"
#define PMU_ESP32_RESP_ERROR_STR    "ERROR"
#define PMU_ESP32_RESP_FAIL_STR     "FAIL"
#define PMU_ESP32_RESP_READY_STR    "ready"
#define PMU_ESP32_RESP_BUSY_P_STR   "busy p..."
#define PMU_ESP32_RESP_BUSY_S_STR   "busy s..."

/* AT command strings */
#define PMU_ESP32_CMD_AT            "AT"
#define PMU_ESP32_CMD_RST           "AT+RST"
#define PMU_ESP32_CMD_GMR           "AT+GMR"
#define PMU_ESP32_CMD_CIFSR         "AT+CIFSR"
#define PMU_ESP32_CMD_CWMODE        "AT+CWMODE"
#define PMU_ESP32_CMD_CWSAP         "AT+CWSAP"
#define PMU_ESP32_CMD_CWJAP         "AT+CWJAP"
#define PMU_ESP32_CMD_CWQAP         "AT+CWQAP"
#define PMU_ESP32_CMD_CWLAP         "AT+CWLAP"
#define PMU_ESP32_CMD_CIPSERVER     "AT+CIPSERVER"
#define PMU_ESP32_CMD_CIPSEND       "AT+CIPSEND"
#define PMU_ESP32_CMD_CIPCLOSE      "AT+CIPCLOSE"
#define PMU_ESP32_CMD_CWSTATE       "AT+CWSTATE?"
#define PMU_ESP32_CMD_CIPMUX        "AT+CIPMUX"

/* BLE AT commands */
#define PMU_ESP32_CMD_BLEINIT       "AT+BLEINIT"
#define PMU_ESP32_CMD_BLEADDR       "AT+BLEADDR"
#define PMU_ESP32_CMD_BLENAME       "AT+BLENAME"
#define PMU_ESP32_CMD_BLEADVSTART   "AT+BLEADVSTART"
#define PMU_ESP32_CMD_BLEADVSTOP    "AT+BLEADVSTOP"
#define PMU_ESP32_CMD_BLEGATTSSRV   "AT+BLEGATTSSRVCRE"
#define PMU_ESP32_CMD_BLEGATTSNTFY  "AT+BLEGATTSNTFY"

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize ESP32 bridge
 * @retval HAL status
 * @note Initializes UART3 and resets the ESP32 module
 */
HAL_StatusTypeDef PMU_ESP32_Init(void);

/**
 * @brief Deinitialize ESP32 bridge
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_ESP32_DeInit(void);

/**
 * @brief Reset ESP32 module
 * @retval HAL status
 * @note Performs hardware reset via EN pin and waits for "ready"
 */
HAL_StatusTypeDef PMU_ESP32_Reset(void);

/**
 * @brief Check if ESP32 is ready
 * @retval true if ready to accept commands
 */
bool PMU_ESP32_IsReady(void);

/**
 * @brief Get ESP32 module state
 * @retval Current state
 */
PMU_ESP32_State_t PMU_ESP32_GetState(void);

/**
 * @brief Send AT command and wait for response
 * @param cmd AT command string (without CR/LF)
 * @param response Buffer to store response (can be NULL)
 * @param response_size Size of response buffer
 * @param timeout_ms Timeout in milliseconds
 * @retval Response status
 */
PMU_ESP32_Response_t PMU_ESP32_SendCommand(const char* cmd,
                                            char* response,
                                            uint16_t response_size,
                                            uint32_t timeout_ms);

/**
 * @brief Send AT command with formatted parameters
 * @param fmt Format string (printf-style)
 * @param ... Format arguments
 * @retval Response status
 * @note Uses default timeout, no response capture
 */
PMU_ESP32_Response_t PMU_ESP32_SendCommandF(const char* fmt, ...);

/**
 * @brief Send raw data (for CIPSEND)
 * @param data Data buffer
 * @param length Data length
 * @param timeout_ms Timeout in milliseconds
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_ESP32_SendData(const uint8_t* data,
                                      uint16_t length,
                                      uint32_t timeout_ms);

/**
 * @brief Process received UART data (call from ISR or polling)
 * @note Adds received bytes to ring buffer
 */
void PMU_ESP32_ProcessRx(void);

/**
 * @brief Update ESP32 module (call periodically)
 * @note Processes async notifications, updates state
 */
void PMU_ESP32_Update(void);

/**
 * @brief Get module information
 * @param info Buffer to store info
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_ESP32_GetInfo(PMU_ESP32_Info_t* info);

/**
 * @brief Get statistics
 * @retval Pointer to statistics structure
 */
const PMU_ESP32_Stats_t* PMU_ESP32_GetStats(void);

/**
 * @brief Set async notification callback
 * @param callback Function to call when async data received (+IPD, etc.)
 * @param user_data User data passed to callback
 */
typedef void (*PMU_ESP32_Callback_t)(const char* notification, void* user_data);
void PMU_ESP32_SetCallback(PMU_ESP32_Callback_t callback, void* user_data);

/**
 * @brief Test connection with AT command
 * @retval true if ESP32 responds with OK
 */
bool PMU_ESP32_Test(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_ESP32_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

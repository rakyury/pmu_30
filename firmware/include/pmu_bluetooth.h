/**
 ******************************************************************************
 * @file           : pmu_bluetooth.h
 * @brief          : Bluetooth Configuration and Management Header
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides Bluetooth Classic and BLE connectivity via
 * an external module (e.g., ESP32 or dedicated Bluetooth IC).
 *
 ******************************************************************************
 */

#ifndef __PMU_BLUETOOTH_H
#define __PMU_BLUETOOTH_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Bluetooth operating mode
 */
typedef enum {
    PMU_BT_MODE_DISABLED = 0,   /* Bluetooth disabled */
    PMU_BT_MODE_CLASSIC = 1,    /* Bluetooth Classic (SPP) */
    PMU_BT_MODE_BLE = 2,        /* Bluetooth Low Energy */
    PMU_BT_MODE_DUAL = 3,       /* Both Classic and BLE */
} PMU_BT_Mode_t;

/**
 * @brief Bluetooth connection state
 */
typedef enum {
    PMU_BT_STATE_DISABLED = 0,      /* Bluetooth disabled */
    PMU_BT_STATE_IDLE = 1,          /* Initialized but not advertising/scanning */
    PMU_BT_STATE_ADVERTISING = 2,   /* Advertising (waiting for connection) */
    PMU_BT_STATE_SCANNING = 3,      /* Scanning for devices */
    PMU_BT_STATE_CONNECTING = 4,    /* Connection in progress */
    PMU_BT_STATE_CONNECTED = 5,     /* Connected to a device */
    PMU_BT_STATE_ERROR = 6,         /* Error state */
} PMU_BT_State_t;

/**
 * @brief Bluetooth security level
 */
typedef enum {
    PMU_BT_SEC_NONE = 0,           /* No security */
    PMU_BT_SEC_PAIR_ONLY = 1,      /* Pairing required */
    PMU_BT_SEC_AUTH = 2,           /* Authentication (PIN) required */
    PMU_BT_SEC_SECURE = 3,         /* Secure connection (bonding + encryption) */
} PMU_BT_Security_t;

/**
 * @brief Bluetooth Classic (SPP) configuration
 */
typedef struct {
    char device_name[32];          /* Device name for discovery */
    uint8_t discoverable;          /* Device is discoverable */
    uint8_t connectable;           /* Device accepts connections */
    PMU_BT_Security_t security;    /* Security level */
    char pin[17];                  /* PIN code for pairing (if used) */
    uint8_t max_connections;       /* Max simultaneous connections (1-7) */
} PMU_BT_Classic_Config_t;

/**
 * @brief BLE configuration
 */
typedef struct {
    char device_name[32];          /* Device name for advertising */
    uint8_t advertising_enabled;   /* Enable advertising */
    uint16_t adv_interval_ms;      /* Advertising interval in ms */
    uint16_t conn_interval_min;    /* Min connection interval (1.25ms units) */
    uint16_t conn_interval_max;    /* Max connection interval (1.25ms units) */
    uint16_t slave_latency;        /* Slave latency (number of events) */
    uint16_t supervision_timeout;  /* Supervision timeout (10ms units) */
    PMU_BT_Security_t security;    /* Security level */
    uint8_t require_bonding;       /* Require device to be bonded */
} PMU_BT_BLE_Config_t;

/**
 * @brief Bluetooth telemetry service configuration
 */
typedef struct {
    uint8_t enabled;               /* Telemetry service enabled */
    uint16_t update_rate_ms;       /* Telemetry update rate */
    uint8_t notify_changes;        /* Notify on value changes only */
} PMU_BT_Telemetry_Config_t;

/**
 * @brief Complete Bluetooth configuration
 */
typedef struct {
    uint8_t enabled;               /* Bluetooth enabled */
    PMU_BT_Mode_t mode;            /* Operating mode */
    PMU_BT_Classic_Config_t classic; /* Bluetooth Classic settings */
    PMU_BT_BLE_Config_t ble;       /* BLE settings */
    PMU_BT_Telemetry_Config_t telemetry; /* Telemetry service settings */
} PMU_BT_Config_t;

/**
 * @brief Bluetooth connection information
 */
typedef struct {
    char name[32];                 /* Connected device name */
    uint8_t address[6];            /* Device MAC address */
    int8_t rssi;                   /* Signal strength */
    uint8_t is_classic;            /* 1 = Classic, 0 = BLE */
    uint8_t is_authenticated;      /* Device is authenticated */
    uint8_t is_encrypted;          /* Connection is encrypted */
    uint32_t connected_since;      /* Connection timestamp */
} PMU_BT_Connection_t;

/**
 * @brief Bluetooth status
 */
typedef struct {
    PMU_BT_State_t state;          /* Current state */
    PMU_BT_Mode_t active_mode;     /* Active operating mode */
    uint8_t num_connections;       /* Number of active connections */
    PMU_BT_Connection_t connections[4]; /* Connection info (up to 4) */
    uint8_t mac_address[6];        /* Local MAC address */
    int8_t tx_power;               /* Current TX power in dBm */
    uint32_t uptime_seconds;       /* Time since BT enabled */
} PMU_BT_Status_t;

/* Exported constants --------------------------------------------------------*/

/* Default configuration values */
#define PMU_BT_DEFAULT_DEVICE_NAME      "PMU30"
#define PMU_BT_DEFAULT_PIN              "1234"
#define PMU_BT_DEFAULT_ADV_INTERVAL     100    /* 100ms */
#define PMU_BT_DEFAULT_CONN_INTERVAL    20     /* 25ms (20 * 1.25) */
#define PMU_BT_DEFAULT_SUPERVISION      400    /* 4000ms (400 * 10) */
#define PMU_BT_DEFAULT_TELEM_RATE       100    /* 100ms (10 Hz) */

/* MAC address length */
#define PMU_BT_MAC_ADDR_LEN             6

/* Maximum connections */
#define PMU_BT_MAX_CONNECTIONS          4

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize Bluetooth subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_Init(void);

/**
 * @brief Deinitialize Bluetooth subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_DeInit(void);

/**
 * @brief Update Bluetooth processing (call periodically)
 */
void PMU_BT_Update(void);

/**
 * @brief Apply Bluetooth configuration
 * @param config Configuration to apply
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_ApplyConfig(const PMU_BT_Config_t* config);

/**
 * @brief Get current Bluetooth configuration
 * @param config Buffer to receive configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_GetConfig(PMU_BT_Config_t* config);

/**
 * @brief Get Bluetooth status
 * @param status Buffer to receive status
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_GetStatus(PMU_BT_Status_t* status);

/**
 * @brief Start Bluetooth
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_Start(void);

/**
 * @brief Stop Bluetooth
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_Stop(void);

/**
 * @brief Start advertising (BLE)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_StartAdvertising(void);

/**
 * @brief Stop advertising (BLE)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_StopAdvertising(void);

/**
 * @brief Make device discoverable (Classic)
 * @param enable Enable/disable discoverable mode
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_SetDiscoverable(uint8_t enable);

/**
 * @brief Disconnect from a device
 * @param index Connection index (0-3)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_Disconnect(uint8_t index);

/**
 * @brief Disconnect all devices
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_DisconnectAll(void);

/**
 * @brief Check if Bluetooth is connected
 * @retval Number of active connections
 */
uint8_t PMU_BT_IsConnected(void);

/**
 * @brief Send data over Bluetooth
 * @param data Data to send
 * @param len Data length
 * @param connection_index Connection to send to (0xFF for all)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BT_SendData(const uint8_t* data, size_t len, uint8_t connection_index);

/**
 * @brief Set default configuration
 * @param config Configuration structure to fill with defaults
 */
void PMU_BT_SetDefaultConfig(PMU_BT_Config_t* config);

/**
 * @brief Convert MAC address to string
 * @param mac MAC address bytes
 * @param buffer Output buffer (at least 18 bytes)
 * @return Pointer to buffer
 */
char* PMU_BT_MACtoString(const uint8_t* mac, char* buffer);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_BLUETOOTH_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

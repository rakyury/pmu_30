/**
 ******************************************************************************
 * @file           : pmu_bluetooth.c
 * @brief          : Bluetooth Configuration and Management Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements Bluetooth functionality using an external module
 * (e.g., ESP32 or dedicated Bluetooth IC) connected via UART or SPI.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_bluetooth.h"
#include <string.h>
#include <stdio.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_BT_Config_t s_bt_config;
static PMU_BT_Status_t s_bt_status;
static uint8_t s_bt_initialized = 0;

/* Private function prototypes -----------------------------------------------*/

/* Exported functions --------------------------------------------------------*/

HAL_StatusTypeDef PMU_BT_Init(void)
{
    if (s_bt_initialized) {
        return HAL_OK;
    }

    /* Initialize with defaults */
    memset(&s_bt_config, 0, sizeof(s_bt_config));
    memset(&s_bt_status, 0, sizeof(s_bt_status));

    /* Set default configuration */
    PMU_BT_SetDefaultConfig(&s_bt_config);

    s_bt_status.state = PMU_BT_STATE_DISABLED;
    s_bt_initialized = 1;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_DeInit(void)
{
    if (!s_bt_initialized) {
        return HAL_OK;
    }

    PMU_BT_Stop();
    s_bt_initialized = 0;

    return HAL_OK;
}

void PMU_BT_Update(void)
{
    if (!s_bt_initialized || !s_bt_config.enabled) {
        return;
    }

    /* Update uptime */
    if (s_bt_status.state != PMU_BT_STATE_DISABLED) {
        /* Uptime updated elsewhere via tick */
    }

    /* TODO: Check connection status, handle reconnection, etc. */
}

HAL_StatusTypeDef PMU_BT_ApplyConfig(const PMU_BT_Config_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    /* Copy configuration */
    memcpy(&s_bt_config, config, sizeof(PMU_BT_Config_t));

    /* If Bluetooth is enabled, restart with new config */
    if (s_bt_config.enabled) {
        PMU_BT_Stop();
        return PMU_BT_Start();
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_GetConfig(PMU_BT_Config_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    memcpy(config, &s_bt_config, sizeof(PMU_BT_Config_t));
    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_GetStatus(PMU_BT_Status_t* status)
{
    if (!status) {
        return HAL_ERROR;
    }

    memcpy(status, &s_bt_status, sizeof(PMU_BT_Status_t));
    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_Start(void)
{
    if (!s_bt_initialized) {
        return HAL_ERROR;
    }

    if (!s_bt_config.enabled) {
        s_bt_status.state = PMU_BT_STATE_DISABLED;
        return HAL_OK;
    }

    /* TODO: Initialize Bluetooth hardware based on mode */
    switch (s_bt_config.mode) {
        case PMU_BT_MODE_CLASSIC:
            /* Start Bluetooth Classic (SPP) */
            s_bt_status.state = PMU_BT_STATE_ADVERTISING;
            s_bt_status.active_mode = PMU_BT_MODE_CLASSIC;
            break;

        case PMU_BT_MODE_BLE:
            /* Start BLE */
            if (s_bt_config.ble.advertising_enabled) {
                s_bt_status.state = PMU_BT_STATE_ADVERTISING;
            } else {
                s_bt_status.state = PMU_BT_STATE_IDLE;
            }
            s_bt_status.active_mode = PMU_BT_MODE_BLE;
            break;

        case PMU_BT_MODE_DUAL:
            /* Start both modes */
            s_bt_status.state = PMU_BT_STATE_ADVERTISING;
            s_bt_status.active_mode = PMU_BT_MODE_DUAL;
            break;

        default:
            s_bt_status.state = PMU_BT_STATE_DISABLED;
            break;
    }

    /* Set a fake MAC address for emulator */
    s_bt_status.mac_address[0] = 0xAA;
    s_bt_status.mac_address[1] = 0xBB;
    s_bt_status.mac_address[2] = 0xCC;
    s_bt_status.mac_address[3] = 0xDD;
    s_bt_status.mac_address[4] = 0xEE;
    s_bt_status.mac_address[5] = 0xFF;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_Stop(void)
{
    s_bt_status.state = PMU_BT_STATE_DISABLED;
    s_bt_status.num_connections = 0;
    memset(s_bt_status.connections, 0, sizeof(s_bt_status.connections));

    /* TODO: Shutdown Bluetooth hardware */

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_StartAdvertising(void)
{
    if (!s_bt_initialized || !s_bt_config.enabled) {
        return HAL_ERROR;
    }

    if (s_bt_config.mode == PMU_BT_MODE_BLE || s_bt_config.mode == PMU_BT_MODE_DUAL) {
        s_bt_status.state = PMU_BT_STATE_ADVERTISING;
        /* TODO: Start BLE advertising */
        return HAL_OK;
    }

    return HAL_ERROR;
}

HAL_StatusTypeDef PMU_BT_StopAdvertising(void)
{
    if (!s_bt_initialized) {
        return HAL_ERROR;
    }

    if (s_bt_status.state == PMU_BT_STATE_ADVERTISING) {
        s_bt_status.state = PMU_BT_STATE_IDLE;
        /* TODO: Stop BLE advertising */
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_SetDiscoverable(uint8_t enable)
{
    if (!s_bt_initialized || !s_bt_config.enabled) {
        return HAL_ERROR;
    }

    s_bt_config.classic.discoverable = enable;

    if (enable && s_bt_status.state == PMU_BT_STATE_IDLE) {
        s_bt_status.state = PMU_BT_STATE_ADVERTISING;
    } else if (!enable && s_bt_status.state == PMU_BT_STATE_ADVERTISING &&
               s_bt_status.num_connections == 0) {
        s_bt_status.state = PMU_BT_STATE_IDLE;
    }

    /* TODO: Set discoverable mode on hardware */

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_Disconnect(uint8_t index)
{
    if (!s_bt_initialized || index >= PMU_BT_MAX_CONNECTIONS) {
        return HAL_ERROR;
    }

    if (s_bt_status.connections[index].name[0] != '\0') {
        /* Clear connection info */
        memset(&s_bt_status.connections[index], 0, sizeof(PMU_BT_Connection_t));

        /* Update connection count */
        s_bt_status.num_connections = 0;
        for (int i = 0; i < PMU_BT_MAX_CONNECTIONS; i++) {
            if (s_bt_status.connections[i].name[0] != '\0') {
                s_bt_status.num_connections++;
            }
        }

        /* Update state if no more connections */
        if (s_bt_status.num_connections == 0) {
            if (s_bt_config.ble.advertising_enabled || s_bt_config.classic.discoverable) {
                s_bt_status.state = PMU_BT_STATE_ADVERTISING;
            } else {
                s_bt_status.state = PMU_BT_STATE_IDLE;
            }
        }

        /* TODO: Disconnect on hardware */
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_DisconnectAll(void)
{
    for (int i = 0; i < PMU_BT_MAX_CONNECTIONS; i++) {
        PMU_BT_Disconnect(i);
    }

    return HAL_OK;
}

uint8_t PMU_BT_IsConnected(void)
{
    return s_bt_status.num_connections;
}

HAL_StatusTypeDef PMU_BT_SendData(const uint8_t* data, size_t len, uint8_t connection_index)
{
    if (!s_bt_initialized || !data || len == 0) {
        return HAL_ERROR;
    }

    if (s_bt_status.num_connections == 0) {
        return HAL_ERROR;  /* No connections */
    }

    /* TODO: Send data over Bluetooth */
    (void)connection_index;

    return HAL_OK;
}

void PMU_BT_SetDefaultConfig(PMU_BT_Config_t* config)
{
    if (!config) {
        return;
    }

    memset(config, 0, sizeof(PMU_BT_Config_t));

    /* Disabled by default, user must enable */
    config->enabled = 0;
    config->mode = PMU_BT_MODE_BLE;  /* BLE is most common for IoT */

    /* Classic configuration */
    strncpy(config->classic.device_name, PMU_BT_DEFAULT_DEVICE_NAME, sizeof(config->classic.device_name) - 1);
    config->classic.discoverable = 1;
    config->classic.connectable = 1;
    config->classic.security = PMU_BT_SEC_AUTH;
    strncpy(config->classic.pin, PMU_BT_DEFAULT_PIN, sizeof(config->classic.pin) - 1);
    config->classic.max_connections = 1;

    /* BLE configuration */
    strncpy(config->ble.device_name, PMU_BT_DEFAULT_DEVICE_NAME, sizeof(config->ble.device_name) - 1);
    config->ble.advertising_enabled = 1;
    config->ble.adv_interval_ms = PMU_BT_DEFAULT_ADV_INTERVAL;
    config->ble.conn_interval_min = PMU_BT_DEFAULT_CONN_INTERVAL;
    config->ble.conn_interval_max = PMU_BT_DEFAULT_CONN_INTERVAL * 2;
    config->ble.slave_latency = 0;
    config->ble.supervision_timeout = PMU_BT_DEFAULT_SUPERVISION;
    config->ble.security = PMU_BT_SEC_PAIR_ONLY;
    config->ble.require_bonding = 0;

    /* Telemetry service */
    config->telemetry.enabled = 1;
    config->telemetry.update_rate_ms = PMU_BT_DEFAULT_TELEM_RATE;
    config->telemetry.notify_changes = 0;
}

char* PMU_BT_MACtoString(const uint8_t* mac, char* buffer)
{
    if (!mac || !buffer) {
        return NULL;
    }

    snprintf(buffer, 18, "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    return buffer;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

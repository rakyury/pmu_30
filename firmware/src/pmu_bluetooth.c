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
#include "pmu_esp32.h"
#include <string.h>
#include <stdio.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* BLE service and characteristic UUIDs for PMU telemetry */
#define PMU_BLE_SERVICE_UUID        "0000FFE0-0000-1000-8000-00805F9B34FB"
#define PMU_BLE_CHAR_TX_UUID        "0000FFE1-0000-1000-8000-00805F9B34FB"
#define PMU_BLE_CHAR_RX_UUID        "0000FFE2-0000-1000-8000-00805F9B34FB"

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_BT_Config_t s_bt_config;
static PMU_BT_Status_t s_bt_status;
static uint8_t s_bt_initialized = 0;
static uint8_t s_ble_server_created = 0;

/* Private function prototypes -----------------------------------------------*/
static void BT_AsyncCallback(const char* notification, void* user_data);
static HAL_StatusTypeDef BT_InitBLE(void);
static HAL_StatusTypeDef BT_CreateGATTServer(void);
static void BT_ParseMACAddress(const char* response);

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
    s_ble_server_created = 0;

    /* ESP32 should already be initialized by WiFi */
    if (!PMU_ESP32_IsReady()) {
        /* Try to init ESP32 if not already done */
        HAL_StatusTypeDef status = PMU_ESP32_Init();
        if (status != HAL_OK) {
            return status;
        }
    }

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
        s_bt_status.uptime_seconds++;
    }

    /* ESP32 Update is handled by WiFi module */

    /* Periodic connection check */
    static uint32_t last_check = 0;
    uint32_t now = HAL_GetTick();

    if (now - last_check >= 10000) {  /* Every 10 seconds */
        last_check = now;

        if (PMU_ESP32_IsReady()) {
            char response[128];
            if (PMU_ESP32_SendCommand("AT+BLECONN?", response,
                                       sizeof(response), 1000) == PMU_ESP32_RESP_OK) {
                /* Parse: +BLECONN:<conn_index>,<remote_address> */
                int conn_count = 0;
                char* line = response;
                while ((line = strstr(line, "+BLECONN:")) != NULL) {
                    conn_count++;
                    line++;
                }

                if (conn_count != s_bt_status.num_connections) {
                    s_bt_status.num_connections = conn_count;
                    if (conn_count > 0) {
                        s_bt_status.state = PMU_BT_STATE_CONNECTED;
                    } else if (s_bt_config.ble.advertising_enabled) {
                        s_bt_status.state = PMU_BT_STATE_ADVERTISING;
                    } else {
                        s_bt_status.state = PMU_BT_STATE_IDLE;
                    }
                }
            }
        }
    }
}

HAL_StatusTypeDef PMU_BT_ApplyConfig(const PMU_BT_Config_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    /* Copy configuration */
    memcpy(&s_bt_config, config, sizeof(PMU_BT_Config_t));

    /* Apply the configuration immediately */
    if (s_bt_config.enabled) {
        /* Bluetooth enabled - restart with new config */
        PMU_BT_Stop();
        return PMU_BT_Start();
    } else {
        /* Bluetooth disabled - stop and update status */
        return PMU_BT_Stop();
    }
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

    /* Check if ESP32 is ready */
    if (!PMU_ESP32_IsReady()) {
        s_bt_status.state = PMU_BT_STATE_ERROR;
        return HAL_ERROR;
    }

    HAL_StatusTypeDef status = HAL_OK;

    /* Initialize BLE based on mode */
    switch (s_bt_config.mode) {
        case PMU_BT_MODE_CLASSIC:
            /* Bluetooth Classic not supported by ESP32-C3 */
            s_bt_status.state = PMU_BT_STATE_ERROR;
            return HAL_ERROR;

        case PMU_BT_MODE_BLE:
            /* Initialize BLE */
            status = BT_InitBLE();
            if (status != HAL_OK) {
                s_bt_status.state = PMU_BT_STATE_ERROR;
                return status;
            }
            s_bt_status.active_mode = PMU_BT_MODE_BLE;

            /* Create GATT server if not already done */
            if (!s_ble_server_created) {
                status = BT_CreateGATTServer();
                if (status == HAL_OK) {
                    s_ble_server_created = 1;
                }
            }

            /* Start advertising if enabled */
            if (s_bt_config.ble.advertising_enabled) {
                status = PMU_BT_StartAdvertising();
            } else {
                s_bt_status.state = PMU_BT_STATE_IDLE;
            }
            break;

        case PMU_BT_MODE_DUAL:
            /* ESP32-C3 only supports BLE, treat as BLE mode */
            s_bt_config.mode = PMU_BT_MODE_BLE;
            return PMU_BT_Start();

        default:
            s_bt_status.state = PMU_BT_STATE_DISABLED;
            break;
    }

    /* Get real MAC address from ESP32 */
    BT_ParseMACAddress(NULL);

    return status;
}

HAL_StatusTypeDef PMU_BT_Stop(void)
{
    s_bt_status.state = PMU_BT_STATE_DISABLED;
    s_bt_status.num_connections = 0;
    s_bt_status.uptime_seconds = 0;
    memset(s_bt_status.connections, 0, sizeof(s_bt_status.connections));

    if (!s_bt_initialized || !PMU_ESP32_IsReady()) {
        return HAL_OK;
    }

    /* Stop advertising */
    PMU_ESP32_SendCommand(PMU_ESP32_CMD_BLEADVSTOP, NULL, 0, 1000);

    /* Deinit BLE */
    PMU_ESP32_SendCommandF("AT+BLEINIT=0");

    s_ble_server_created = 0;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_StartAdvertising(void)
{
    if (!s_bt_initialized || !s_bt_config.enabled) {
        return HAL_ERROR;
    }

    if (!PMU_ESP32_IsReady()) {
        return HAL_ERROR;
    }

    if (s_bt_config.mode == PMU_BT_MODE_BLE || s_bt_config.mode == PMU_BT_MODE_DUAL) {
        /* Set advertising parameters */
        /* AT+BLEADVPARAM=<adv_int_min>,<adv_int_max>,<adv_type>,... */
        uint16_t adv_int = s_bt_config.ble.adv_interval_ms * 16 / 10;  /* Convert ms to 0.625ms units */
        PMU_ESP32_SendCommandF("AT+BLEADVPARAM=%d,%d,0,0,7", adv_int, adv_int);

        /* Set advertising data with device name */
        /* Manually construct advertising data: flags + complete local name */
        PMU_ESP32_SendCommandF("AT+BLEADVDATA=\"0201060908%s\"",
                                s_bt_config.ble.device_name);

        /* Start advertising */
        PMU_ESP32_Response_t result = PMU_ESP32_SendCommand(
            PMU_ESP32_CMD_BLEADVSTART, NULL, 0, 1000);

        if (result == PMU_ESP32_RESP_OK) {
            s_bt_status.state = PMU_BT_STATE_ADVERTISING;
            return HAL_OK;
        }

        s_bt_status.state = PMU_BT_STATE_ERROR;
        return HAL_ERROR;
    }

    return HAL_ERROR;
}

HAL_StatusTypeDef PMU_BT_StopAdvertising(void)
{
    if (!s_bt_initialized) {
        return HAL_ERROR;
    }

    if (s_bt_status.state == PMU_BT_STATE_ADVERTISING) {
        if (PMU_ESP32_IsReady()) {
            PMU_ESP32_SendCommand(PMU_ESP32_CMD_BLEADVSTOP, NULL, 0, 1000);
        }
        s_bt_status.state = PMU_BT_STATE_IDLE;
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_SetDiscoverable(uint8_t enable)
{
    if (!s_bt_initialized || !s_bt_config.enabled) {
        return HAL_ERROR;
    }

    s_bt_config.classic.discoverable = enable;
    s_bt_config.ble.advertising_enabled = enable;

    if (enable && s_bt_status.state == PMU_BT_STATE_IDLE) {
        return PMU_BT_StartAdvertising();
    } else if (!enable && s_bt_status.state == PMU_BT_STATE_ADVERTISING &&
               s_bt_status.num_connections == 0) {
        return PMU_BT_StopAdvertising();
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BT_Disconnect(uint8_t index)
{
    if (!s_bt_initialized || index >= PMU_BT_MAX_CONNECTIONS) {
        return HAL_ERROR;
    }

    if (s_bt_status.connections[index].name[0] != '\0') {
        /* Disconnect on ESP32 */
        if (PMU_ESP32_IsReady()) {
            PMU_ESP32_SendCommandF("AT+BLEDISCONN=%d", index);
        }

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

    if (!PMU_ESP32_IsReady()) {
        return HAL_ERROR;
    }

    /* Send notification via GATT characteristic */
    /* AT+BLEGATTSNTFY=<conn_index>,<srv_index>,<char_index>,<length> */
    /* Then send the actual data */

    PMU_ESP32_Response_t result = PMU_ESP32_SendCommandF(
        "AT+BLEGATTSNTFY=%d,1,1,%d", connection_index, (int)len);

    if (result != PMU_ESP32_RESP_OK) {
        return HAL_ERROR;
    }

    /* Send the data */
    HAL_StatusTypeDef status = PMU_ESP32_SendData(data, len, 1000);

    if (status == HAL_OK) {
        s_bt_status.bytes_sent += len;
    }

    return status;
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

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Handle async notifications from ESP32 for BLE events
 */
static void BT_AsyncCallback(const char* notification, void* user_data)
{
    (void)user_data;

    if (strncmp(notification, "+BLECONN:", 9) == 0) {
        /* New BLE connection: +BLECONN:<conn_index>,<remote_address> */
        int conn_idx;
        char mac[18];
        if (sscanf(notification, "+BLECONN:%d,\"%17[^\"]\"", &conn_idx, mac) == 2) {
            if (conn_idx < PMU_BT_MAX_CONNECTIONS) {
                strncpy(s_bt_status.connections[conn_idx].name, mac,
                        sizeof(s_bt_status.connections[conn_idx].name) - 1);
                s_bt_status.num_connections++;
                s_bt_status.state = PMU_BT_STATE_CONNECTED;
            }
        }
    }
    else if (strncmp(notification, "+BLEDISCONN:", 12) == 0) {
        /* BLE disconnection: +BLEDISCONN:<conn_index> */
        int conn_idx;
        if (sscanf(notification, "+BLEDISCONN:%d", &conn_idx) == 1) {
            if (conn_idx < PMU_BT_MAX_CONNECTIONS) {
                memset(&s_bt_status.connections[conn_idx], 0, sizeof(PMU_BT_Connection_t));

                /* Recount connections */
                s_bt_status.num_connections = 0;
                for (int i = 0; i < PMU_BT_MAX_CONNECTIONS; i++) {
                    if (s_bt_status.connections[i].name[0] != '\0') {
                        s_bt_status.num_connections++;
                    }
                }

                if (s_bt_status.num_connections == 0) {
                    if (s_bt_config.ble.advertising_enabled) {
                        s_bt_status.state = PMU_BT_STATE_ADVERTISING;
                    } else {
                        s_bt_status.state = PMU_BT_STATE_IDLE;
                    }
                }
            }
        }
    }
    else if (strncmp(notification, "+WRITE:", 7) == 0) {
        /* BLE write received - data available */
        s_bt_status.bytes_received++;  /* Will be updated with actual size */
    }
}

/**
 * @brief Initialize BLE on ESP32
 */
static HAL_StatusTypeDef BT_InitBLE(void)
{
    /* Initialize BLE as server: AT+BLEINIT=2 */
    PMU_ESP32_Response_t result = PMU_ESP32_SendCommandF("AT+BLEINIT=2");
    if (result != PMU_ESP32_RESP_OK) {
        return HAL_ERROR;
    }

    /* Set BLE device name */
    result = PMU_ESP32_SendCommandF("AT+BLENAME=\"%s\"", s_bt_config.ble.device_name);
    if (result != PMU_ESP32_RESP_OK) {
        return HAL_ERROR;
    }

    return HAL_OK;
}

/**
 * @brief Create GATT server with PMU service
 */
static HAL_StatusTypeDef BT_CreateGATTServer(void)
{
    /* Create GATT service */
    /* For simplicity, use a pre-configured service profile */
    /* AT+BLEGATTSSRVCRE creates a GATT server from the stored config */

    PMU_ESP32_Response_t result = PMU_ESP32_SendCommand(
        "AT+BLEGATTSSRVCRE", NULL, 0, 2000);

    if (result != PMU_ESP32_RESP_OK) {
        /* Service may already exist, try to start it anyway */
    }

    /* Start the GATT server */
    result = PMU_ESP32_SendCommand("AT+BLEGATTSSRVSTART", NULL, 0, 1000);
    if (result != PMU_ESP32_RESP_OK) {
        return HAL_ERROR;
    }

    return HAL_OK;
}

/**
 * @brief Parse and store BLE MAC address from ESP32
 */
static void BT_ParseMACAddress(const char* response)
{
    char resp_buf[128];

    if (response == NULL) {
        /* Query MAC from ESP32 */
        if (PMU_ESP32_SendCommand("AT+BLEADDR?", resp_buf,
                                   sizeof(resp_buf), 1000) != PMU_ESP32_RESP_OK) {
            return;
        }
        response = resp_buf;
    }

    /* Parse: +BLEADDR:<addr_type>,"xx:xx:xx:xx:xx:xx" */
    const char* mac_start = strchr(response, '"');
    if (mac_start) {
        mac_start++;
        sscanf(mac_start, "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
               &s_bt_status.mac_address[0], &s_bt_status.mac_address[1],
               &s_bt_status.mac_address[2], &s_bt_status.mac_address[3],
               &s_bt_status.mac_address[4], &s_bt_status.mac_address[5]);
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

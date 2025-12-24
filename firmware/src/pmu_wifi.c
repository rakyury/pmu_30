/**
 ******************************************************************************
 * @file           : pmu_wifi.c
 * @brief          : WiFi Configuration and Management Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements WiFi functionality using an external WiFi module
 * (ESP32-WROOM or similar) connected via UART.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_wifi.h"
#include <string.h>
#include <stdio.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_WiFi_Config_t s_wifi_config;
static PMU_WiFi_Status_t s_wifi_status;
static uint8_t s_wifi_initialized = 0;

/* Private function prototypes -----------------------------------------------*/

/* Exported functions --------------------------------------------------------*/

HAL_StatusTypeDef PMU_WiFi_Init(void)
{
    if (s_wifi_initialized) {
        return HAL_OK;
    }

    /* Initialize with defaults */
    memset(&s_wifi_config, 0, sizeof(s_wifi_config));
    memset(&s_wifi_status, 0, sizeof(s_wifi_status));

    /* Set default configuration */
    PMU_WiFi_SetDefaultAPConfig(&s_wifi_config);

    s_wifi_status.state = PMU_WIFI_STATE_DISABLED;
    s_wifi_initialized = 1;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_WiFi_DeInit(void)
{
    if (!s_wifi_initialized) {
        return HAL_OK;
    }

    PMU_WiFi_Stop();
    s_wifi_initialized = 0;

    return HAL_OK;
}

void PMU_WiFi_Update(void)
{
    if (!s_wifi_initialized || !s_wifi_config.enabled) {
        return;
    }

    /* Update uptime */
    if (s_wifi_status.state == PMU_WIFI_STATE_CONNECTED) {
        /* Uptime updated elsewhere via tick */
    }

    /* TODO: Check connection status, handle reconnection, etc. */
}

HAL_StatusTypeDef PMU_WiFi_ApplyConfig(const PMU_WiFi_Config_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    /* Copy configuration */
    memcpy(&s_wifi_config, config, sizeof(PMU_WiFi_Config_t));

    /* Apply the configuration immediately */
    if (s_wifi_config.enabled) {
        /* WiFi enabled - restart with new config */
        PMU_WiFi_Stop();
        return PMU_WiFi_Start();
    } else {
        /* WiFi disabled - stop and update status */
        return PMU_WiFi_Stop();
    }
}

HAL_StatusTypeDef PMU_WiFi_GetConfig(PMU_WiFi_Config_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    memcpy(config, &s_wifi_config, sizeof(PMU_WiFi_Config_t));
    return HAL_OK;
}

HAL_StatusTypeDef PMU_WiFi_GetStatus(PMU_WiFi_Status_t* status)
{
    if (!status) {
        return HAL_ERROR;
    }

    memcpy(status, &s_wifi_status, sizeof(PMU_WiFi_Status_t));
    return HAL_OK;
}

HAL_StatusTypeDef PMU_WiFi_Start(void)
{
    if (!s_wifi_initialized) {
        return HAL_ERROR;
    }

    if (!s_wifi_config.enabled) {
        s_wifi_status.state = PMU_WIFI_STATE_DISABLED;
        return HAL_OK;
    }

    /* TODO: Initialize WiFi hardware based on mode */
    switch (s_wifi_config.mode) {
        case PMU_WIFI_MODE_AP:
            /* Start Access Point */
            s_wifi_status.state = PMU_WIFI_STATE_CONNECTED;
            s_wifi_status.active_mode = PMU_WIFI_MODE_AP;
            /* Default AP IP is usually 192.168.4.1 */
            s_wifi_status.ip_address = PMU_WiFi_IP(192, 168, 4, 1);
            s_wifi_status.gateway = PMU_WiFi_IP(192, 168, 4, 1);
            break;

        case PMU_WIFI_MODE_STA:
            /* Connect to configured network */
            s_wifi_status.state = PMU_WIFI_STATE_CONNECTING;
            s_wifi_status.active_mode = PMU_WIFI_MODE_STA;
            /* Actual connection happens asynchronously */
            break;

        case PMU_WIFI_MODE_AP_STA:
            /* Start AP and connect to network */
            s_wifi_status.state = PMU_WIFI_STATE_CONNECTING;
            s_wifi_status.active_mode = PMU_WIFI_MODE_AP_STA;
            break;

        default:
            s_wifi_status.state = PMU_WIFI_STATE_DISABLED;
            break;
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_WiFi_Stop(void)
{
    s_wifi_status.state = PMU_WIFI_STATE_DISABLED;
    s_wifi_status.ip_address = 0;
    s_wifi_status.gateway = 0;
    s_wifi_status.rssi = 0;
    s_wifi_status.connected_clients = 0;

    /* TODO: Shutdown WiFi hardware */

    return HAL_OK;
}

HAL_StatusTypeDef PMU_WiFi_Connect(const char* ssid, const char* password)
{
    if (!ssid) {
        return HAL_ERROR;
    }

    /* Update STA config */
    strncpy(s_wifi_config.sta.ssid, ssid, PMU_WIFI_SSID_MAX_LEN);
    s_wifi_config.sta.ssid[PMU_WIFI_SSID_MAX_LEN] = '\0';

    if (password) {
        strncpy(s_wifi_config.sta.password, password, PMU_WIFI_PASS_MAX_LEN);
        s_wifi_config.sta.password[PMU_WIFI_PASS_MAX_LEN] = '\0';
    } else {
        s_wifi_config.sta.password[0] = '\0';
    }

    s_wifi_status.state = PMU_WIFI_STATE_CONNECTING;

    /* TODO: Initiate connection to WiFi network */

    return HAL_OK;
}

HAL_StatusTypeDef PMU_WiFi_Disconnect(void)
{
    if (s_wifi_status.state == PMU_WIFI_STATE_CONNECTED ||
        s_wifi_status.state == PMU_WIFI_STATE_CONNECTING) {

        s_wifi_status.state = PMU_WIFI_STATE_DISCONNECTED;
        s_wifi_status.ip_address = 0;
        s_wifi_status.rssi = 0;
        s_wifi_status.connected_ssid[0] = '\0';

        /* TODO: Disconnect from WiFi network */
    }

    return HAL_OK;
}

uint8_t PMU_WiFi_Scan(char networks[][33], uint8_t max_networks, int8_t* rssi)
{
    /* TODO: Implement WiFi scanning */
    (void)networks;
    (void)max_networks;
    (void)rssi;

    return 0;
}

uint8_t PMU_WiFi_IsConnected(void)
{
    return (s_wifi_status.state == PMU_WIFI_STATE_CONNECTED) ? 1 : 0;
}

char* PMU_WiFi_GetIPString(char* buffer)
{
    if (!buffer) {
        return NULL;
    }

    return PMU_WiFi_IPtoString(s_wifi_status.ip_address, buffer);
}

void PMU_WiFi_SetDefaultAPConfig(PMU_WiFi_Config_t* config)
{
    if (!config) {
        return;
    }

    memset(config, 0, sizeof(PMU_WiFi_Config_t));

    /* Enable WiFi in AP mode by default */
    config->enabled = 0;  /* Disabled by default, user must enable */
    config->mode = PMU_WIFI_MODE_AP;

    /* AP configuration */
    strncpy(config->ap.ssid, PMU_WIFI_DEFAULT_AP_SSID, PMU_WIFI_SSID_MAX_LEN);
    strncpy(config->ap.password, PMU_WIFI_DEFAULT_AP_PASS, PMU_WIFI_PASS_MAX_LEN);
    config->ap.security = PMU_WIFI_SEC_WPA2;
    config->ap.channel = PMU_WIFI_DEFAULT_AP_CHANNEL;
    config->ap.hidden = 0;
    config->ap.max_clients = 4;

    /* STA configuration (empty by default) */
    config->sta.auto_reconnect = 1;
    config->sta.dhcp = 1;

    /* Web server configuration */
    config->web.enabled = 1;
    config->web.http_port = PMU_WIFI_DEFAULT_HTTP_PORT;
    config->web.ws_port = PMU_WIFI_DEFAULT_WS_PORT;
    config->web.auth_enabled = 0;

    /* Hostname */
    strncpy(config->hostname, "pmu30", PMU_WIFI_HOSTNAME_MAX_LEN);
}

char* PMU_WiFi_IPtoString(uint32_t ip, char* buffer)
{
    if (!buffer) {
        return NULL;
    }

    snprintf(buffer, 16, "%d.%d.%d.%d",
             (int)(ip & 0xFF),
             (int)((ip >> 8) & 0xFF),
             (int)((ip >> 16) & 0xFF),
             (int)((ip >> 24) & 0xFF));

    return buffer;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

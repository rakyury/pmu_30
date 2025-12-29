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
#include "pmu_esp32.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_WiFi_Config_t s_wifi_config;
static PMU_WiFi_Status_t s_wifi_status;
static uint8_t s_wifi_initialized = 0;

/* Private function prototypes -----------------------------------------------*/
static void WiFi_AsyncCallback(const char* notification, void* user_data);
static HAL_StatusTypeDef WiFi_SetMode(PMU_WiFi_Mode_t mode);
static HAL_StatusTypeDef WiFi_StartAP(void);
static HAL_StatusTypeDef WiFi_ConnectSTA(void);
static HAL_StatusTypeDef WiFi_StartServer(void);
static void WiFi_ParseIP(const char* response);

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

    /* Initialize ESP32 bridge */
    HAL_StatusTypeDef status = PMU_ESP32_Init();
    if (status != HAL_OK) {
        return status;
    }

    /* Register callback for async notifications */
    PMU_ESP32_SetCallback(WiFi_AsyncCallback, NULL);

    /* Get MAC addresses from ESP32 */
    PMU_ESP32_Info_t info;
    if (PMU_ESP32_GetInfo(&info) == HAL_OK) {
        /* Parse MAC address string "xx:xx:xx:xx:xx:xx" to bytes */
        sscanf(info.mac_sta, "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
               &s_wifi_status.mac_address[0], &s_wifi_status.mac_address[1],
               &s_wifi_status.mac_address[2], &s_wifi_status.mac_address[3],
               &s_wifi_status.mac_address[4], &s_wifi_status.mac_address[5]);
    }

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

    /* Update ESP32 (process async notifications) */
    PMU_ESP32_Update();

    /* Update uptime */
    if (s_wifi_status.state == PMU_WIFI_STATE_CONNECTED) {
        s_wifi_status.uptime_seconds++;
    }

    /* Check connection status in STA mode */
    if (s_wifi_config.mode == PMU_WIFI_MODE_STA ||
        s_wifi_config.mode == PMU_WIFI_MODE_AP_STA) {

        static uint32_t last_check = 0;
        uint32_t now = HAL_GetTick();

        /* Check every 5 seconds */
        if (now - last_check >= 5000) {
            last_check = now;

            char response[128];
            if (PMU_ESP32_SendCommand(PMU_ESP32_CMD_CWSTATE, response,
                                       sizeof(response), 1000) == PMU_ESP32_RESP_OK) {
                /* Parse: +CWSTATE:<state>,<ssid> */
                int state = 0;
                if (sscanf(response, "+CWSTATE:%d", &state) == 1) {
                    if (state == 2) {  /* Connected */
                        if (s_wifi_status.state != PMU_WIFI_STATE_CONNECTED) {
                            s_wifi_status.state = PMU_WIFI_STATE_CONNECTED;
                            WiFi_ParseIP(NULL);  /* Get IP address */
                        }
                    } else if (state == 0 || state == 1) {  /* Disconnected/Idle */
                        s_wifi_status.state = PMU_WIFI_STATE_DISCONNECTED;
                        s_wifi_status.ip_address = 0;

                        /* Auto-reconnect if configured */
                        if (s_wifi_config.sta.auto_reconnect &&
                            s_wifi_config.sta.ssid[0] != '\0') {
                            WiFi_ConnectSTA();
                        }
                    }
                }
            }
        }
    }
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

    /* Check if ESP32 is ready */
    if (!PMU_ESP32_IsReady()) {
        s_wifi_status.state = PMU_WIFI_STATE_ERROR;
        return HAL_ERROR;
    }

    /* Set WiFi mode on ESP32 */
    HAL_StatusTypeDef status = WiFi_SetMode(s_wifi_config.mode);
    if (status != HAL_OK) {
        s_wifi_status.state = PMU_WIFI_STATE_ERROR;
        return status;
    }

    /* Configure based on mode */
    switch (s_wifi_config.mode) {
        case PMU_WIFI_MODE_AP:
            /* Start Access Point */
            s_wifi_status.active_mode = PMU_WIFI_MODE_AP;
            status = WiFi_StartAP();
            if (status == HAL_OK) {
                s_wifi_status.state = PMU_WIFI_STATE_CONNECTED;
                s_wifi_status.ip_address = PMU_WiFi_IP(192, 168, 4, 1);
                s_wifi_status.gateway = PMU_WiFi_IP(192, 168, 4, 1);
            } else {
                s_wifi_status.state = PMU_WIFI_STATE_ERROR;
            }
            break;

        case PMU_WIFI_MODE_STA:
            /* Connect to configured network */
            s_wifi_status.active_mode = PMU_WIFI_MODE_STA;
            s_wifi_status.state = PMU_WIFI_STATE_CONNECTING;
            if (s_wifi_config.sta.ssid[0] != '\0') {
                status = WiFi_ConnectSTA();
            }
            break;

        case PMU_WIFI_MODE_AP_STA:
            /* Start AP and connect to network */
            s_wifi_status.active_mode = PMU_WIFI_MODE_AP_STA;
            status = WiFi_StartAP();
            if (status == HAL_OK && s_wifi_config.sta.ssid[0] != '\0') {
                s_wifi_status.state = PMU_WIFI_STATE_CONNECTING;
                WiFi_ConnectSTA();
            } else if (status == HAL_OK) {
                s_wifi_status.state = PMU_WIFI_STATE_CONNECTED;
                s_wifi_status.ip_address = PMU_WiFi_IP(192, 168, 4, 1);
            }
            break;

        default:
            s_wifi_status.state = PMU_WIFI_STATE_DISABLED;
            break;
    }

    /* Start TCP server if web server is enabled */
    if (status == HAL_OK && s_wifi_config.web.enabled) {
        WiFi_StartServer();
    }

    return status;
}

HAL_StatusTypeDef PMU_WiFi_Stop(void)
{
    s_wifi_status.state = PMU_WIFI_STATE_DISABLED;
    s_wifi_status.ip_address = 0;
    s_wifi_status.gateway = 0;
    s_wifi_status.rssi = 0;
    s_wifi_status.connected_clients = 0;
    s_wifi_status.uptime_seconds = 0;

    if (!s_wifi_initialized || !PMU_ESP32_IsReady()) {
        return HAL_OK;
    }

    /* Close TCP server */
    PMU_ESP32_SendCommandF("AT+CIPSERVER=0");

    /* Disconnect from AP if in STA mode */
    PMU_ESP32_SendCommand(PMU_ESP32_CMD_CWQAP, NULL, 0, 1000);

    /* Set WiFi mode to disabled */
    PMU_ESP32_SendCommandF("AT+CWMODE=0");

    return HAL_OK;
}

HAL_StatusTypeDef PMU_WiFi_Connect(const char* ssid, const char* password)
{
    if (!ssid || !s_wifi_initialized) {
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

    /* Initiate connection */
    return WiFi_ConnectSTA();
}

HAL_StatusTypeDef PMU_WiFi_Disconnect(void)
{
    if (s_wifi_status.state == PMU_WIFI_STATE_CONNECTED ||
        s_wifi_status.state == PMU_WIFI_STATE_CONNECTING) {

        s_wifi_status.state = PMU_WIFI_STATE_DISCONNECTED;
        s_wifi_status.ip_address = 0;
        s_wifi_status.rssi = 0;
        s_wifi_status.connected_ssid[0] = '\0';

        if (s_wifi_initialized && PMU_ESP32_IsReady()) {
            PMU_ESP32_SendCommand(PMU_ESP32_CMD_CWQAP, NULL, 0, 1000);
        }
    }

    return HAL_OK;
}

uint8_t PMU_WiFi_Scan(char networks[][33], uint8_t max_networks, int8_t* rssi)
{
    if (!s_wifi_initialized || !PMU_ESP32_IsReady() || !networks || max_networks == 0) {
        return 0;
    }

    /* Start WiFi scan - AT+CWLAP */
    char response[1024];
    PMU_ESP32_Response_t result = PMU_ESP32_SendCommand(
        PMU_ESP32_CMD_CWLAP, response, sizeof(response), PMU_ESP32_WIFI_TIMEOUT_MS);

    if (result != PMU_ESP32_RESP_OK) {
        return 0;
    }

    /* Parse response: +CWLAP:(<ecn>,<ssid>,<rssi>,<mac>,<channel>) */
    uint8_t count = 0;
    char* line = response;
    char* next_line;

    while (line && count < max_networks) {
        next_line = strchr(line, '\n');
        if (next_line) {
            *next_line = '\0';
            next_line++;
        }

        if (strncmp(line, "+CWLAP:", 7) == 0) {
            /* Parse: +CWLAP:(<ecn>,"<ssid>",<rssi>,...) */
            char* ssid_start = strchr(line, '"');
            if (ssid_start) {
                ssid_start++;
                char* ssid_end = strchr(ssid_start, '"');
                if (ssid_end) {
                    int len = ssid_end - ssid_start;
                    if (len > 32) len = 32;
                    memcpy(networks[count], ssid_start, len);
                    networks[count][len] = '\0';

                    /* Parse RSSI if requested */
                    if (rssi) {
                        char* rssi_start = ssid_end + 2;  /* Skip "," */
                        rssi[count] = (int8_t)atoi(rssi_start);
                    }
                    count++;
                }
            }
        }

        line = next_line;
    }

    return count;
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

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Handle async notifications from ESP32
 */
static void WiFi_AsyncCallback(const char* notification, void* user_data)
{
    (void)user_data;

    if (strncmp(notification, "WIFI CONNECTED", 14) == 0) {
        /* WiFi connected to AP */
        s_wifi_status.state = PMU_WIFI_STATE_CONNECTED;
        WiFi_ParseIP(NULL);
    }
    else if (strncmp(notification, "WIFI DISCONNECT", 15) == 0) {
        /* WiFi disconnected */
        s_wifi_status.state = PMU_WIFI_STATE_DISCONNECTED;
        s_wifi_status.ip_address = 0;
    }
    else if (strncmp(notification, "WIFI GOT IP", 11) == 0) {
        /* Got IP address */
        WiFi_ParseIP(NULL);
    }
    else if (strncmp(notification, "+STA_CONNECTED:", 15) == 0) {
        /* Client connected to our AP */
        s_wifi_status.connected_clients++;
    }
    else if (strncmp(notification, "+STA_DISCONNECTED:", 18) == 0) {
        /* Client disconnected from our AP */
        if (s_wifi_status.connected_clients > 0) {
            s_wifi_status.connected_clients--;
        }
    }
    else if (strncmp(notification, "+IPD", 4) == 0) {
        /* Incoming data - handled elsewhere */
    }
}

/**
 * @brief Set WiFi mode on ESP32
 */
static HAL_StatusTypeDef WiFi_SetMode(PMU_WiFi_Mode_t mode)
{
    int esp_mode;

    switch (mode) {
        case PMU_WIFI_MODE_DISABLED:
            esp_mode = 0;
            break;
        case PMU_WIFI_MODE_STA:
            esp_mode = 1;
            break;
        case PMU_WIFI_MODE_AP:
            esp_mode = 2;
            break;
        case PMU_WIFI_MODE_AP_STA:
            esp_mode = 3;
            break;
        default:
            return HAL_ERROR;
    }

    /* AT+CWMODE=<mode> */
    PMU_ESP32_Response_t result = PMU_ESP32_SendCommandF("AT+CWMODE=%d", esp_mode);
    return (result == PMU_ESP32_RESP_OK) ? HAL_OK : HAL_ERROR;
}

/**
 * @brief Start WiFi Access Point
 */
static HAL_StatusTypeDef WiFi_StartAP(void)
{
    /* Enable multiple connections for server mode */
    if (PMU_ESP32_SendCommandF("AT+CIPMUX=1") != PMU_ESP32_RESP_OK) {
        return HAL_ERROR;
    }

    /* Configure AP: AT+CWSAP="ssid","password",channel,encryption,max_conn */
    int ecn;
    switch (s_wifi_config.ap.security) {
        case PMU_WIFI_SEC_OPEN:
            ecn = 0;
            break;
        case PMU_WIFI_SEC_WPA:
            ecn = 2;
            break;
        case PMU_WIFI_SEC_WPA2:
        default:
            ecn = 3;
            break;
        case PMU_WIFI_SEC_WPA3:
        case PMU_WIFI_SEC_WPA2_WPA3:
            ecn = 4;
            break;
    }

    PMU_ESP32_Response_t result = PMU_ESP32_SendCommandF(
        "AT+CWSAP=\"%s\",\"%s\",%d,%d,%d,%d",
        s_wifi_config.ap.ssid,
        s_wifi_config.ap.password,
        s_wifi_config.ap.channel,
        ecn,
        s_wifi_config.ap.max_clients,
        s_wifi_config.ap.hidden ? 1 : 0);

    return (result == PMU_ESP32_RESP_OK) ? HAL_OK : HAL_ERROR;
}

/**
 * @brief Connect to WiFi network as station
 */
static HAL_StatusTypeDef WiFi_ConnectSTA(void)
{
    if (!PMU_ESP32_IsReady()) {
        return HAL_ERROR;
    }

    /* AT+CWJAP="ssid","password" */
    PMU_ESP32_Response_t result = PMU_ESP32_SendCommandF(
        "AT+CWJAP=\"%s\",\"%s\"",
        s_wifi_config.sta.ssid,
        s_wifi_config.sta.password);

    if (result == PMU_ESP32_RESP_OK) {
        strncpy(s_wifi_status.connected_ssid, s_wifi_config.sta.ssid,
                sizeof(s_wifi_status.connected_ssid) - 1);
        s_wifi_status.state = PMU_WIFI_STATE_CONNECTED;
        WiFi_ParseIP(NULL);
        return HAL_OK;
    }

    s_wifi_status.state = PMU_WIFI_STATE_DISCONNECTED;
    return HAL_ERROR;
}

/**
 * @brief Start TCP server
 */
static HAL_StatusTypeDef WiFi_StartServer(void)
{
    /* Enable multiple connections */
    if (PMU_ESP32_SendCommandF("AT+CIPMUX=1") != PMU_ESP32_RESP_OK) {
        return HAL_ERROR;
    }

    /* Start TCP server on HTTP port */
    PMU_ESP32_Response_t result = PMU_ESP32_SendCommandF(
        "AT+CIPSERVER=1,%d",
        s_wifi_config.web.http_port);

    return (result == PMU_ESP32_RESP_OK) ? HAL_OK : HAL_ERROR;
}

/**
 * @brief Parse and store IP address from ESP32
 */
static void WiFi_ParseIP(const char* response)
{
    char resp_buf[128];

    if (response == NULL) {
        /* Query IP from ESP32 */
        if (PMU_ESP32_SendCommand(PMU_ESP32_CMD_CIFSR, resp_buf,
                                   sizeof(resp_buf), 1000) != PMU_ESP32_RESP_OK) {
            return;
        }
        response = resp_buf;
    }

    /* Parse: +CIFSR:STAIP,"x.x.x.x" or +CIFSR:APIP,"x.x.x.x" */
    const char* ip_start = strstr(response, "IP,\"");
    if (ip_start) {
        ip_start += 4;  /* Skip 'IP,"' */
        int ip1, ip2, ip3, ip4;
        if (sscanf(ip_start, "%d.%d.%d.%d", &ip1, &ip2, &ip3, &ip4) == 4) {
            s_wifi_status.ip_address = PMU_WiFi_IP(ip1, ip2, ip3, ip4);
        }
    }

    /* Parse gateway if available */
    const char* gw_start = strstr(response, "GATEWAY,\"");
    if (gw_start) {
        gw_start += 9;
        int gw1, gw2, gw3, gw4;
        if (sscanf(gw_start, "%d.%d.%d.%d", &gw1, &gw2, &gw3, &gw4) == 4) {
            s_wifi_status.gateway = PMU_WiFi_IP(gw1, gw2, gw3, gw4);
        }
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

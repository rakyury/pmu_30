/**
 ******************************************************************************
 * @file           : pmu_wifi.h
 * @brief          : WiFi Configuration and Management
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Supports WiFi connectivity for:
 * - Configuration over WiFi (web interface)
 * - Telemetry streaming via WiFi
 * - OTA firmware updates
 *
 ******************************************************************************
 */

#ifndef __PMU_WIFI_H
#define __PMU_WIFI_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "pmu_types.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief WiFi operating mode
 */
typedef enum {
    PMU_WIFI_MODE_DISABLED = 0,     /* WiFi disabled */
    PMU_WIFI_MODE_AP = 1,           /* Access Point mode */
    PMU_WIFI_MODE_STA = 2,          /* Station mode (connect to router) */
    PMU_WIFI_MODE_AP_STA = 3,       /* AP + Station mode */
} PMU_WiFi_Mode_t;

/**
 * @brief WiFi security type
 */
typedef enum {
    PMU_WIFI_SEC_OPEN = 0,          /* Open (no security) */
    PMU_WIFI_SEC_WPA = 1,           /* WPA */
    PMU_WIFI_SEC_WPA2 = 2,          /* WPA2 */
    PMU_WIFI_SEC_WPA3 = 3,          /* WPA3 */
    PMU_WIFI_SEC_WPA2_WPA3 = 4,     /* WPA2/WPA3 mixed */
} PMU_WiFi_Security_t;

/**
 * @brief WiFi connection state
 */
typedef enum {
    PMU_WIFI_STATE_DISABLED = 0,
    PMU_WIFI_STATE_DISCONNECTED = 1,
    PMU_WIFI_STATE_CONNECTING = 2,
    PMU_WIFI_STATE_CONNECTED = 3,
    PMU_WIFI_STATE_ERROR = 4,
} PMU_WiFi_State_t;

/**
 * @brief WiFi Access Point configuration
 */
typedef struct {
    char ssid[33];                  /* AP SSID (max 32 chars + null) */
    char password[65];              /* AP password (max 64 chars + null) */
    PMU_WiFi_Security_t security;   /* Security type */
    uint8_t channel;                /* WiFi channel (1-14, 0=auto) */
    uint8_t hidden;                 /* Hidden SSID (1=hidden) */
    uint8_t max_clients;            /* Maximum connected clients (1-8) */
} PMU_WiFi_AP_Config_t;

/**
 * @brief WiFi Station configuration
 */
typedef struct {
    char ssid[33];                  /* Target SSID to connect to */
    char password[65];              /* Password */
    uint8_t auto_reconnect;         /* Auto-reconnect on disconnect */
    uint8_t dhcp;                   /* Use DHCP (1) or static IP (0) */
    /* Static IP configuration (if dhcp=0) */
    uint32_t static_ip;             /* Static IP address */
    uint32_t gateway;               /* Gateway address */
    uint32_t netmask;               /* Subnet mask */
    uint32_t dns1;                  /* Primary DNS */
    uint32_t dns2;                  /* Secondary DNS */
} PMU_WiFi_STA_Config_t;

/**
 * @brief WiFi web server configuration
 */
typedef struct {
    uint8_t enabled;                /* Web server enabled */
    uint16_t http_port;             /* HTTP port (default 80) */
    uint16_t ws_port;               /* WebSocket port (default 81) */
    uint8_t auth_enabled;           /* Authentication required */
    char username[32];              /* Web interface username */
    char password[32];              /* Web interface password */
} PMU_WiFi_WebServer_Config_t;

/**
 * @brief Complete WiFi configuration
 */
typedef struct {
    PMU_WiFi_Mode_t mode;           /* Operating mode */
    PMU_WiFi_AP_Config_t ap;        /* Access Point config */
    PMU_WiFi_STA_Config_t sta;      /* Station config */
    PMU_WiFi_WebServer_Config_t web; /* Web server config */
    uint8_t enabled;                /* WiFi enabled */
    char hostname[32];              /* Device hostname */
} PMU_WiFi_Config_t;

/**
 * @brief WiFi status information
 */
typedef struct {
    PMU_WiFi_State_t state;         /* Current state */
    PMU_WiFi_Mode_t active_mode;    /* Active mode */
    int8_t rssi;                    /* Signal strength (dBm) for STA mode */
    uint8_t connected_clients;      /* Number of connected clients (AP mode) */
    uint32_t ip_address;            /* Current IP address */
    uint32_t gateway;               /* Current gateway */
    uint8_t mac_address[6];         /* MAC address */
    char connected_ssid[33];        /* Connected SSID (STA mode) */
    uint32_t uptime_seconds;        /* WiFi uptime */
    uint32_t bytes_sent;            /* Total bytes sent */
    uint32_t bytes_received;        /* Total bytes received */
} PMU_WiFi_Status_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_WIFI_SSID_MAX_LEN       32
#define PMU_WIFI_PASS_MAX_LEN       64
#define PMU_WIFI_HOSTNAME_MAX_LEN   31

/* Default AP configuration */
#define PMU_WIFI_DEFAULT_AP_SSID    "PMU30-Config"
#define PMU_WIFI_DEFAULT_AP_PASS    "pmu30setup"
#define PMU_WIFI_DEFAULT_AP_CHANNEL 6

/* Default ports */
#define PMU_WIFI_DEFAULT_HTTP_PORT  80
#define PMU_WIFI_DEFAULT_WS_PORT    81

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize WiFi subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_Init(void);

/**
 * @brief Deinitialize WiFi subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_DeInit(void);

/**
 * @brief Update WiFi (call periodically)
 */
void PMU_WiFi_Update(void);

/**
 * @brief Apply WiFi configuration
 * @param config Configuration to apply
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_ApplyConfig(const PMU_WiFi_Config_t* config);

/**
 * @brief Get current WiFi configuration
 * @param config Buffer to store configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_GetConfig(PMU_WiFi_Config_t* config);

/**
 * @brief Get WiFi status
 * @param status Buffer to store status
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_GetStatus(PMU_WiFi_Status_t* status);

/**
 * @brief Start WiFi
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_Start(void);

/**
 * @brief Stop WiFi
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_Stop(void);

/**
 * @brief Connect to WiFi network (STA mode)
 * @param ssid Network SSID
 * @param password Network password
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_Connect(const char* ssid, const char* password);

/**
 * @brief Disconnect from WiFi network
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_WiFi_Disconnect(void);

/**
 * @brief Scan for available WiFi networks
 * @param networks Buffer to store found networks (array of SSIDs)
 * @param max_networks Maximum networks to return
 * @param rssi Buffer to store RSSI values (optional, can be NULL)
 * @retval Number of networks found
 */
uint8_t PMU_WiFi_Scan(char networks[][33], uint8_t max_networks, int8_t* rssi);

/**
 * @brief Check if WiFi is connected
 * @retval 1 if connected, 0 otherwise
 */
uint8_t PMU_WiFi_IsConnected(void);

/**
 * @brief Get IP address as string
 * @param buffer Buffer to store IP string (min 16 bytes)
 * @retval Pointer to buffer
 */
char* PMU_WiFi_GetIPString(char* buffer);

/**
 * @brief Set default AP configuration
 * @param config Configuration to initialize with defaults
 */
void PMU_WiFi_SetDefaultAPConfig(PMU_WiFi_Config_t* config);

/**
 * @brief Convert IP address to uint32_t
 * @param ip1 First octet
 * @param ip2 Second octet
 * @param ip3 Third octet
 * @param ip4 Fourth octet
 * @retval IP address as uint32_t
 */
static inline uint32_t PMU_WiFi_IP(uint8_t ip1, uint8_t ip2, uint8_t ip3, uint8_t ip4) {
    return ((uint32_t)ip4 << 24) | ((uint32_t)ip3 << 16) | ((uint32_t)ip2 << 8) | ip1;
}

/**
 * @brief Convert uint32_t IP to string
 * @param ip IP address
 * @param buffer Output buffer (min 16 bytes)
 * @retval Pointer to buffer
 */
char* PMU_WiFi_IPtoString(uint32_t ip, char* buffer);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_WIFI_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

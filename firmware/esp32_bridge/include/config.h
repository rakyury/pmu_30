/**
 * @file config.h
 * @brief Configuration for PMU-30 WiFi Bridge
 */
#pragma once

// =============================================================================
// UART Configuration (connection to Nucleo-F446RE)
// =============================================================================
#define NUCLEO_UART_RX    27   // ESP32 RX ← Nucleo TX (PC10)
#define NUCLEO_UART_TX    26   // ESP32 TX → Nucleo RX (PC11)
#define NUCLEO_UART_BAUD  115200

// =============================================================================
// WiFi Configuration
// =============================================================================
#ifndef WIFI_AP_SSID
#define WIFI_AP_SSID      "PMU30-BRIDGE"
#endif

#ifndef WIFI_AP_PASS
#define WIFI_AP_PASS      "pmu30wifi"
#endif

// Station mode (connect to existing network)
// Set empty strings to disable STA mode
#define WIFI_STA_SSID     ""
#define WIFI_STA_PASS     ""

// mDNS hostname (http://pmu30.local)
#define MDNS_HOSTNAME     "pmu30"

// =============================================================================
// TCP Server Configuration
// =============================================================================
#ifndef TCP_PORT
#define TCP_PORT          8266   // SerialTransfer protocol port
#endif

#define HTTP_PORT         80     // Web dashboard port
#define MAX_TCP_CLIENTS   2      // Max simultaneous TCP connections

// =============================================================================
// Display Configuration
// =============================================================================
#define TFT_BACKLIGHT_PIN   4
#define TFT_BUTTON_1       35   // Left button (active low)
#define TFT_BUTTON_2        0   // Right button (active low)

// Display update rate (ms)
#define DISPLAY_UPDATE_MS   100

// =============================================================================
// SerialTransfer Protocol
// =============================================================================
// Command IDs (same as firmware)
#define ST_CMD_PING          0x01
#define ST_CMD_PONG          0x02
#define ST_CMD_GET_CONFIG    0x10
#define ST_CMD_CONFIG_DATA   0x11
#define ST_CMD_SAVE_CONFIG   0x14
#define ST_CMD_FLASH_ACK     0x15
#define ST_CMD_CLEAR_CONFIG  0x16
#define ST_CMD_CLEAR_ACK     0x17
#define ST_CMD_LOAD_BINARY   0x18
#define ST_CMD_BINARY_ACK    0x19
#define ST_CMD_START_STREAM  0x20
#define ST_CMD_STOP_STREAM   0x21
#define ST_CMD_DATA          0x22   // Telemetry packet
#define ST_CMD_SET_OUTPUT    0x28
#define ST_CMD_OUTPUT_ACK    0x29
#define ST_CMD_GET_CAPS      0x30
#define ST_CMD_CAPABILITIES  0x31
#define ST_CMD_ACK           0x3E
#define ST_CMD_NACK          0x3F

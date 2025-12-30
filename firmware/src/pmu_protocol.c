/**
 ******************************************************************************
 * @file           : pmu_protocol.c
 * @brief          : Real-Time Control Protocol Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * Real-time control protocol implementation for PMU-30
 * Supports UART, WiFi (ESP32-C3), and CAN transports
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_protocol.h"
#include "pmu_profet.h"
#include "pmu_hbridge.h"
#include "pmu_adc.h"
#include "pmu_can.h"
#include "pmu_protection.h"
#include "pmu_logic.h"
#include "pmu_logging.h"
#include "pmu_config_json.h"
#include "board_config.h"
#include <string.h>
#include <stdio.h>

/* Private typedef -----------------------------------------------------------*/

typedef struct {
    uint8_t rx_buffer[512];         /**< RX buffer */
    uint16_t rx_index;              /**< RX buffer index */
    uint8_t tx_buffer[512];         /**< TX buffer */
    uint16_t tx_index;              /**< TX buffer index */
    bool packet_in_progress;        /**< Packet reception in progress */
    uint32_t last_byte_time;        /**< Last byte received timestamp */
} PMU_Protocol_Buffer_t;

/* Private define ------------------------------------------------------------*/
#define PROTOCOL_TIMEOUT_MS     1000    /**< Packet timeout */
#define TELEMETRY_BUFFER_SIZE   512     /**< Telemetry buffer size (increased for virtual channels) */

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_Transport_t active_transport = PMU_TRANSPORT_UART;
static PMU_TelemetryConfig_t telemetry_config = {0};
static PMU_Protocol_Stats_t protocol_stats = {0};
static PMU_Protocol_Buffer_t protocol_buffer = {0};
static bool stream_active = false;
static uint32_t stream_counter = 0;
static uint32_t stream_period_ms = 0;
static uint32_t last_stream_time = 0;

/* Config storage buffer - stores received config for GET_CONFIG response */
#define CONFIG_BUFFER_SIZE 512
static char config_buffer[CONFIG_BUFFER_SIZE];
static uint16_t config_buffer_len = 0;
static bool config_received = false;

#ifndef UNIT_TEST
  #ifdef NUCLEO_F446RE
    /* Nucleo-F446RE uses USART2 via ST-LINK VCP for protocol */
    extern UART_HandleTypeDef huart2;
    #define PROTOCOL_UART huart2
  #else
    /* PMU-30 and H7 Nucleo use USART1 for WiFi/protocol */
    extern UART_HandleTypeDef huart1;
    extern UART_HandleTypeDef huart2;  /* UART for USB/debug */
    #define PROTOCOL_UART huart1
  #endif
#endif

/* Private function prototypes -----------------------------------------------*/
static void Protocol_HandleCommand(const PMU_Protocol_Packet_t* packet);
static void Protocol_SendPacket(const PMU_Protocol_Packet_t* packet);
static void Protocol_SendACK(uint8_t command);
static void Protocol_SendNACK(uint8_t command, const char* reason);
static void Protocol_SendData(uint8_t command, const uint8_t* data, uint16_t length);
static void Protocol_HandlePing(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleGetVersion(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleGetSerial(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleStartStream(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleStopStream(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleSetOutput(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleSetPWM(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleSetHBridge(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleGetOutputs(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleGetInputs(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLoadConfig(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleGetConfig(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleSaveConfig(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleStartLogging(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleStopLogging(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleGetLogInfo(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleDownloadLog(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleEraseLogs(const PMU_Protocol_Packet_t* packet);
static bool Protocol_ValidatePacket(const PMU_Protocol_Packet_t* packet);
#ifndef PMU_DISABLE_LUA
static void Protocol_HandleLuaExecute(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLuaLoadScript(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLuaUnloadScript(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLuaRunScript(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLuaStopScript(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLuaGetScripts(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLuaGetStatus(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLuaGetOutput(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLuaSetEnabled(const PMU_Protocol_Packet_t* packet);
#endif
static void Protocol_HandleSetChannelConfig(const PMU_Protocol_Packet_t* packet);
static void Protocol_SendChannelConfigACK(uint16_t channel_id, bool success, uint16_t error_code, const char* error_msg);

/* Payload pack/unpack helpers -----------------------------------------------*/

/**
 * @brief Pack 32-bit value into buffer (little-endian)
 */
static inline void Protocol_PackU32(uint8_t* buffer, uint16_t* index, uint32_t value)
{
    memcpy(&buffer[*index], &value, 4);
    *index += 4;
}

/**
 * @brief Pack 16-bit value into buffer (little-endian)
 */
static inline void Protocol_PackU16(uint8_t* buffer, uint16_t* index, uint16_t value)
{
    memcpy(&buffer[*index], &value, 2);
    *index += 2;
}

/**
 * @brief Pack 8-bit value into buffer
 */
static inline void Protocol_PackU8(uint8_t* buffer, uint16_t* index, uint8_t value)
{
    buffer[*index] = value;
    *index += 1;
}

/**
 * @brief Extract 32-bit value from packet data (little-endian)
 */
static inline uint32_t Protocol_GetU32(const uint8_t* data, uint16_t offset)
{
    uint32_t value;
    memcpy(&value, &data[offset], 4);
    return value;
}

/**
 * @brief Extract 16-bit value from packet data (little-endian)
 */
static inline uint16_t Protocol_GetU16(const uint8_t* data, uint16_t offset)
{
    uint16_t value;
    memcpy(&value, &data[offset], 2);
    return value;
}

/**
 * @brief Extract string from packet into buffer (with length limit)
 */
static inline uint8_t Protocol_ExtractString(const uint8_t* data, uint16_t data_len,
                                              uint16_t offset, char* out_str, uint8_t max_len)
{
    if (offset >= data_len) {
        out_str[0] = '\0';
        return 0;
    }
    uint8_t len = (data_len - offset < max_len) ? (data_len - offset) : max_len;
    memcpy(out_str, &data[offset], len);
    out_str[len] = '\0';
    return len;
}

/* Command handler dispatch table --------------------------------------------*/
typedef void (*Protocol_CommandHandler_t)(const PMU_Protocol_Packet_t* packet);

typedef struct {
    uint8_t command;
    Protocol_CommandHandler_t handler;
} Protocol_CommandEntry_t;

static const Protocol_CommandEntry_t command_dispatch_table[] = {
    /* System commands */
    {PMU_CMD_PING,              Protocol_HandlePing},
    {PMU_CMD_GET_VERSION,       Protocol_HandleGetVersion},
    {PMU_CMD_GET_SERIAL,        Protocol_HandleGetSerial},
    /* Streaming commands */
    {PMU_CMD_START_STREAM,      Protocol_HandleStartStream},
    {PMU_CMD_STOP_STREAM,       Protocol_HandleStopStream},
    /* Output control commands */
    {PMU_CMD_SET_OUTPUT,        Protocol_HandleSetOutput},
    {PMU_CMD_SET_PWM,           Protocol_HandleSetPWM},
    {PMU_CMD_SET_HBRIDGE,       Protocol_HandleSetHBridge},
    /* Query commands */
    {PMU_CMD_GET_OUTPUTS,       Protocol_HandleGetOutputs},
    {PMU_CMD_GET_INPUTS,        Protocol_HandleGetInputs},
    /* Configuration commands */
    {PMU_CMD_GET_CONFIG,        Protocol_HandleGetConfig},
    {PMU_CMD_LOAD_CONFIG,       Protocol_HandleLoadConfig},
    {PMU_CMD_SAVE_CONFIG,       Protocol_HandleSaveConfig},
    /* Logging commands */
    {PMU_CMD_START_LOGGING,     Protocol_HandleStartLogging},
    {PMU_CMD_STOP_LOGGING,      Protocol_HandleStopLogging},
    {PMU_CMD_GET_LOG_INFO,      Protocol_HandleGetLogInfo},
    {PMU_CMD_DOWNLOAD_LOG,      Protocol_HandleDownloadLog},
    {PMU_CMD_ERASE_LOGS,        Protocol_HandleEraseLogs},
#ifndef PMU_DISABLE_LUA
    /* Lua scripting commands */
    {PMU_CMD_LUA_EXECUTE,       Protocol_HandleLuaExecute},
    {PMU_CMD_LUA_LOAD_SCRIPT,   Protocol_HandleLuaLoadScript},
    {PMU_CMD_LUA_UNLOAD_SCRIPT, Protocol_HandleLuaUnloadScript},
    {PMU_CMD_LUA_RUN_SCRIPT,    Protocol_HandleLuaRunScript},
    {PMU_CMD_LUA_STOP_SCRIPT,   Protocol_HandleLuaStopScript},
    {PMU_CMD_LUA_GET_SCRIPTS,   Protocol_HandleLuaGetScripts},
    {PMU_CMD_LUA_GET_STATUS,    Protocol_HandleLuaGetStatus},
    {PMU_CMD_LUA_GET_OUTPUT,    Protocol_HandleLuaGetOutput},
    {PMU_CMD_LUA_SET_ENABLED,   Protocol_HandleLuaSetEnabled},
#endif
    /* Atomic channel config update */
    {PMU_CMD_SET_CHANNEL_CONFIG, Protocol_HandleSetChannelConfig},
};

#define COMMAND_DISPATCH_COUNT (sizeof(command_dispatch_table) / sizeof(command_dispatch_table[0]))

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize protocol handler
 */
HAL_StatusTypeDef PMU_Protocol_Init(PMU_Transport_t transport)
{
    active_transport = transport;

    /* Clear buffers */
    memset(&protocol_buffer, 0, sizeof(protocol_buffer));
    memset(&protocol_stats, 0, sizeof(protocol_stats));

    /* Initialize telemetry config */
    telemetry_config.outputs_enabled = true;
    telemetry_config.inputs_enabled = true;
    telemetry_config.can_enabled = true;
    telemetry_config.temps_enabled = true;
    telemetry_config.voltages_enabled = true;
    telemetry_config.faults_enabled = true;
    telemetry_config.rate_hz = PMU_STREAM_RATE_10HZ;

    /* Calculate stream period */
    stream_period_ms = 1000 / telemetry_config.rate_hz;

#ifndef UNIT_TEST
    /* Initialize UART for protocol communication */
    if (transport == PMU_TRANSPORT_UART || transport == PMU_TRANSPORT_WIFI) {
  #ifdef NUCLEO_F446RE
        /* USART2 is already initialized in main_nucleo_f446.c */
        /* Just enable RX interrupt for protocol */
        HAL_UART_Receive_IT(&PROTOCOL_UART, protocol_buffer.rx_buffer, 1);
  #else
        /* Initialize USART1 for WiFi module (ESP32-C3) on PMU-30/H7 */
        huart1.Instance = USART1;
        huart1.Init.BaudRate = PMU_PROTOCOL_UART_BAUD;
        huart1.Init.WordLength = UART_WORDLENGTH_8B;
        huart1.Init.StopBits = UART_STOPBITS_1;
        huart1.Init.Parity = UART_PARITY_NONE;
        huart1.Init.Mode = UART_MODE_TX_RX;
        huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
        huart1.Init.OverSampling = UART_OVERSAMPLING_16;

        if (HAL_UART_Init(&huart1) != HAL_OK) {
            return HAL_ERROR;
        }

        /* Enable UART RX interrupt */
        HAL_UART_Receive_IT(&huart1, protocol_buffer.rx_buffer, 1);
  #endif
    }
#endif

    return HAL_OK;
}

/**
 * @brief Process received data
 */
HAL_StatusTypeDef PMU_Protocol_ProcessData(const uint8_t* data, uint16_t length)
{
    if (!data || length == 0) {
        return HAL_ERROR;
    }

    protocol_stats.last_rx_time_ms = HAL_GetTick();

    /* Process each byte */
    for (uint16_t i = 0; i < length; i++) {
        uint8_t byte = data[i];

        /* Check for start marker */
        if (byte == PMU_PROTOCOL_START_MARKER && !protocol_buffer.packet_in_progress) {
            protocol_buffer.rx_index = 0;
            protocol_buffer.packet_in_progress = true;
            protocol_buffer.last_byte_time = HAL_GetTick();
        }

        /* Add to buffer */
        if (protocol_buffer.packet_in_progress) {
            if (protocol_buffer.rx_index < sizeof(protocol_buffer.rx_buffer)) {
                protocol_buffer.rx_buffer[protocol_buffer.rx_index++] = byte;
            } else {
                /* Buffer overflow - reset */
                protocol_buffer.packet_in_progress = false;
                protocol_buffer.rx_index = 0;
                protocol_stats.rx_errors++;
            }

            /* Check if we have enough for header */
            if (protocol_buffer.rx_index >= 4) {
                /* header: marker(1) + command(1) + length(2) */
                uint16_t payload_len = protocol_buffer.rx_buffer[2] |
                                      (protocol_buffer.rx_buffer[3] << 8);

                /* Check if full packet received */
                uint16_t total_len = 4 + payload_len + 2;  /* header + payload + CRC */
                if (protocol_buffer.rx_index >= total_len) {
                    /* Full packet received - process it */
                    PMU_Protocol_Packet_t* packet = (PMU_Protocol_Packet_t*)protocol_buffer.rx_buffer;

                    if (Protocol_ValidatePacket(packet)) {
                        Protocol_HandleCommand(packet);
                        protocol_stats.rx_packets++;
                    } else {
                        protocol_stats.rx_errors++;
                    }

                    /* Reset for next packet */
                    protocol_buffer.packet_in_progress = false;
                    protocol_buffer.rx_index = 0;
                }
            }
        }
    }

    return HAL_OK;
}

/**
 * @brief Update protocol handler (call at 1kHz)
 */
void PMU_Protocol_Update(void)
{
    /* Check for packet timeout */
    if (protocol_buffer.packet_in_progress) {
        if ((HAL_GetTick() - protocol_buffer.last_byte_time) > PROTOCOL_TIMEOUT_MS) {
            protocol_buffer.packet_in_progress = false;
            protocol_buffer.rx_index = 0;
            protocol_stats.rx_errors++;
        }
    }

    /* Send telemetry stream if active */
    if (stream_active) {
        uint32_t now = HAL_GetTick();
        if ((now - last_stream_time) >= stream_period_ms) {
            PMU_Protocol_SendTelemetry();
            last_stream_time = now;
        }
    }
}

/**
 * @brief Send telemetry packet
 */
HAL_StatusTypeDef PMU_Protocol_SendTelemetry(void)
{
    uint8_t telemetry_data[TELEMETRY_BUFFER_SIZE];
    uint16_t index = 0;

    /* Add stream counter */
    memcpy(&telemetry_data[index], &stream_counter, sizeof(stream_counter));
    index += sizeof(stream_counter);
    stream_counter++;

    /* Add timestamp */
    uint32_t timestamp = HAL_GetTick();
    memcpy(&telemetry_data[index], &timestamp, sizeof(timestamp));
    index += sizeof(timestamp);

    /* Add outputs data */
    if (telemetry_config.outputs_enabled && index < TELEMETRY_BUFFER_SIZE - 32) {
        /* Pack 30 output states into 30 bytes */
        for (uint8_t i = 0; i < 30 && index < TELEMETRY_BUFFER_SIZE; i++) {
            PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
            if (ch) {
                telemetry_data[index++] = ch->state;
            }
        }
    }

    /* Add inputs data */
    if (telemetry_config.inputs_enabled && index < TELEMETRY_BUFFER_SIZE - 40) {
        /* Pack 20 input values (2 bytes each = 40 bytes) */
        for (uint8_t i = 0; i < 20 && index < TELEMETRY_BUFFER_SIZE - 1; i++) {
            uint16_t val = PMU_ADC_GetRawValue(i);
            telemetry_data[index++] = (uint8_t)(val & 0xFF);
            telemetry_data[index++] = (uint8_t)(val >> 8);
        }
    }

    /* Add voltages */
    if (telemetry_config.voltages_enabled && index < TELEMETRY_BUFFER_SIZE - 4) {
        PMU_Protection_State_t* prot = PMU_Protection_GetState();
        uint16_t voltage_mv = prot->voltage.voltage_mV;
        memcpy(&telemetry_data[index], &voltage_mv, sizeof(voltage_mv));
        index += sizeof(voltage_mv);

        uint16_t current_mA = prot->power.total_current_mA;
        memcpy(&telemetry_data[index], &current_mA, sizeof(current_mA));
        index += sizeof(current_mA);
    }

    /* Add temperatures */
    if (telemetry_config.temps_enabled && index < TELEMETRY_BUFFER_SIZE - 4) {
        PMU_Protection_State_t* prot = PMU_Protection_GetState();
        int16_t mcu_temp = prot->temperature.mcu_temp_C;
        /* Use max of L/R board temps for backward compatibility */
        int16_t board_temp = (prot->temperature.board_temp_L_C > prot->temperature.board_temp_R_C) ?
                              prot->temperature.board_temp_L_C : prot->temperature.board_temp_R_C;
        memcpy(&telemetry_data[index], &mcu_temp, sizeof(mcu_temp));
        index += sizeof(mcu_temp);
        memcpy(&telemetry_data[index], &board_temp, sizeof(board_temp));
        index += sizeof(board_temp);
    }

    /* Add faults */
    if (telemetry_config.faults_enabled && index < TELEMETRY_BUFFER_SIZE - 2) {
        PMU_Protection_State_t* prot = PMU_Protection_GetState();
        telemetry_data[index++] = prot->status;
        telemetry_data[index++] = prot->fault_flags;
    }

#ifndef NUCLEO_F446RE
    /* Add virtual channels (Logic, Timer, Number, Switch, Filter, etc.) */
    /* Format: count (2 bytes) + [channel_id (2 bytes) + value (4 bytes)] * count */
    uint16_t virtual_count_offset = index;  /* Save offset for count */
    uint16_t virtual_count = 0;
    index += 2;  /* Reserve space for count */

    for (uint16_t ch_id = PMU_CHANNEL_ID_VIRTUAL_START;
         ch_id <= PMU_CHANNEL_ID_VIRTUAL_END && index < TELEMETRY_BUFFER_SIZE - 6;
         ch_id++) {
        const PMU_Channel_t* ch = PMU_Channel_GetInfo(ch_id);
        if (ch && (ch->flags & PMU_CHANNEL_FLAG_ENABLED)) {
            /* Add channel ID */
            memcpy(&telemetry_data[index], &ch_id, sizeof(ch_id));
            index += sizeof(ch_id);

            /* Add channel value (4 bytes signed) */
            int32_t value = ch->value;
            memcpy(&telemetry_data[index], &value, sizeof(value));
            index += sizeof(value);

            virtual_count++;
        }
    }

    /* Write virtual channel count at saved offset */
    memcpy(&telemetry_data[virtual_count_offset], &virtual_count, sizeof(virtual_count));
#endif

    /* Send data packet */
    Protocol_SendData(PMU_CMD_DATA, telemetry_data, index);

    return HAL_OK;
}

/**
 * @brief Send response packet
 */
HAL_StatusTypeDef PMU_Protocol_SendResponse(PMU_CMD_Type_t command,
                                             const uint8_t* data,
                                             uint16_t length)
{
    PMU_Protocol_Packet_t packet;

    packet.start_marker = PMU_PROTOCOL_START_MARKER;
    packet.command = command;
    packet.length = length;

    if (data && length > 0 && length <= PMU_PROTOCOL_MAX_PAYLOAD) {
        memcpy(packet.data, data, length);
    }

    /* Calculate CRC */
    packet.crc16 = PMU_Protocol_CRC16((uint8_t*)&packet, 4 + length);

    Protocol_SendPacket(&packet);

    return HAL_OK;
}

/**
 * @brief Configure telemetry streaming
 */
HAL_StatusTypeDef PMU_Protocol_ConfigureStream(PMU_TelemetryConfig_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    memcpy(&telemetry_config, config, sizeof(PMU_TelemetryConfig_t));

    /* Update stream period */
    if (telemetry_config.rate_hz > 0 && telemetry_config.rate_hz <= 1000) {
        stream_period_ms = 1000 / telemetry_config.rate_hz;
    } else {
        stream_period_ms = 100;  /* Default 10Hz */
    }

    return HAL_OK;
}

/**
 * @brief Start telemetry streaming
 */
HAL_StatusTypeDef PMU_Protocol_StartStream(void)
{
    stream_active = true;
    stream_counter = 0;
    last_stream_time = HAL_GetTick();
    return HAL_OK;
}

/**
 * @brief Stop telemetry streaming
 */
HAL_StatusTypeDef PMU_Protocol_StopStream(void)
{
    stream_active = false;
    return HAL_OK;
}

/**
 * @brief Get protocol statistics
 */
PMU_Protocol_Stats_t* PMU_Protocol_GetStats(void)
{
    return &protocol_stats;
}

/**
 * @brief Calculate CRC16 checksum (CCITT)
 */
uint16_t PMU_Protocol_CRC16(const uint8_t* data, uint16_t length)
{
    uint16_t crc = 0xFFFF;

    for (uint16_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc = crc << 1;
            }
        }
    }

    return crc;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Validate packet CRC and structure
 */
static bool Protocol_ValidatePacket(const PMU_Protocol_Packet_t* packet)
{
    if (!packet) {
        return false;
    }

    /* Check start marker */
    if (packet->start_marker != PMU_PROTOCOL_START_MARKER) {
        return false;
    }

    /* Check length */
    if (packet->length > PMU_PROTOCOL_MAX_PAYLOAD) {
        return false;
    }

    /* Verify CRC */
    uint16_t calculated_crc = PMU_Protocol_CRC16((const uint8_t*)packet, 4 + packet->length);
    if (calculated_crc != packet->crc16) {
        return false;
    }

    return true;
}

/**
 * @brief Handle incoming command
 */
static void Protocol_HandleCommand(const PMU_Protocol_Packet_t* packet)
{
    if (!packet) {
        return;
    }

    /* Look up handler in dispatch table */
    for (uint16_t i = 0; i < COMMAND_DISPATCH_COUNT; i++) {
        if (command_dispatch_table[i].command == packet->command) {
            command_dispatch_table[i].handler(packet);
            return;
        }
    }

    /* Command not found in dispatch table */
    Protocol_SendNACK(packet->command, "Unknown command");
}

/**
 * @brief Send packet via active transport
 */
static void Protocol_SendPacket(const PMU_Protocol_Packet_t* packet)
{
    if (!packet) {
        return;
    }

#ifndef UNIT_TEST
    uint16_t total_len = 4 + packet->length + 2;  /* header + payload + CRC */

    if (active_transport == PMU_TRANSPORT_UART || active_transport == PMU_TRANSPORT_WIFI) {
        /* Send via UART */
        HAL_UART_Transmit(&PROTOCOL_UART, (uint8_t*)packet, total_len, 100);
        protocol_stats.tx_packets++;
        protocol_stats.last_tx_time_ms = HAL_GetTick();
    } else if (active_transport == PMU_TRANSPORT_CAN) {
        /* Send via CAN (chunked if needed) */
        PMU_CAN_Message_t can_msg;
        can_msg.id = PMU_PROTOCOL_CAN_ID_BASE;
        can_msg.id_type = PMU_CAN_ID_STANDARD;
        can_msg.frame_type = PMU_CAN_FRAME_FD;
        can_msg.rtr = 0;

        uint16_t offset = 0;
        while (offset < total_len) {
            uint8_t chunk_len = (total_len - offset > 8) ? 8 : (total_len - offset);
            memcpy(can_msg.data, (uint8_t*)packet + offset, chunk_len);
            can_msg.dlc = chunk_len;

            PMU_CAN_SendMessage(PMU_CAN_BUS_1, &can_msg);

            offset += chunk_len;
        }

        protocol_stats.tx_packets++;
        protocol_stats.last_tx_time_ms = HAL_GetTick();
    }
#else
    (void)packet;
    protocol_stats.tx_packets++;
#endif
}

/**
 * @brief Send ACK response
 */
static void Protocol_SendACK(uint8_t command)
{
    uint8_t data[1] = {command};
    PMU_Protocol_SendResponse(PMU_CMD_ACK, data, 1);
}

/**
 * @brief Send NACK response
 */
static void Protocol_SendNACK(uint8_t command, const char* reason)
{
    uint8_t data[64];
    data[0] = command;
    if (reason) {
        strncpy((char*)&data[1], reason, sizeof(data) - 1);
    }
    PMU_Protocol_SendResponse(PMU_CMD_NACK, data, strlen(reason) + 1);
}

/**
 * @brief Send data response
 */
static void Protocol_SendData(uint8_t command, const uint8_t* data, uint16_t length)
{
    PMU_Protocol_SendResponse(command, data, length);
}

/* Command handlers ----------------------------------------------------------*/

static void Protocol_HandlePing(const PMU_Protocol_Packet_t* packet)
{
    /* Echo back ping data */
    Protocol_SendData(PMU_CMD_PING, packet->data, packet->length);
}

static void Protocol_HandleGetVersion(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;
    uint8_t version[64];
    snprintf((char*)version, sizeof(version), "PMU-30 v%d.%d.%d", 1, 0, 0);
    Protocol_SendData(PMU_CMD_GET_VERSION, version, strlen((char*)version));
}

static void Protocol_HandleGetSerial(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;
    uint8_t serial[32];
    snprintf((char*)serial, sizeof(serial), "PMU30-%08X", (unsigned int)HAL_GetUIDw0());
    Protocol_SendData(PMU_CMD_GET_SERIAL, serial, strlen((char*)serial));
}

static void Protocol_HandleStartStream(const PMU_Protocol_Packet_t* packet)
{
    /* Parse stream configuration from packet data */
    if (packet->length >= sizeof(PMU_TelemetryConfig_t)) {
        PMU_TelemetryConfig_t config;
        memcpy(&config, packet->data, sizeof(config));
        PMU_Protocol_ConfigureStream(&config);
    }

    PMU_Protocol_StartStream();
    Protocol_SendACK(PMU_CMD_START_STREAM);
}

static void Protocol_HandleStopStream(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;
    PMU_Protocol_StopStream();
    Protocol_SendACK(PMU_CMD_STOP_STREAM);
}

static void Protocol_HandleSetOutput(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length >= 2) {
        uint8_t channel = packet->data[0];
        uint8_t state = packet->data[1];

        if (channel < 30) {
            PMU_PROFET_SetState(channel, state);
            Protocol_SendACK(PMU_CMD_SET_OUTPUT);
        } else {
            Protocol_SendNACK(PMU_CMD_SET_OUTPUT, "Invalid channel");
        }
    } else {
        Protocol_SendNACK(PMU_CMD_SET_OUTPUT, "Invalid data");
    }
}

static void Protocol_HandleSetPWM(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length >= 3) {
        uint8_t channel = packet->data[0];
        uint16_t duty = packet->data[1] | (packet->data[2] << 8);

        if (channel < 30) {
            PMU_PROFET_SetState(channel, 1);
            PMU_PROFET_SetPWM(channel, duty);
            Protocol_SendACK(PMU_CMD_SET_PWM);
        } else {
            Protocol_SendNACK(PMU_CMD_SET_PWM, "Invalid channel");
        }
    } else {
        Protocol_SendNACK(PMU_CMD_SET_PWM, "Invalid data");
    }
}

/**
 * @brief Handle SET_HBRIDGE command
 * Packet data format:
 *   data[0] = bridge number (0-3)
 *   data[1] = mode (0=COAST, 1=FORWARD, 2=REVERSE, 3=BRAKE, 4=WIPER_PARK, 5=PID)
 *   data[2..3] = duty cycle (0-1000) - little endian
 *   Optional: data[4..5] = target position (0-1000) for PID mode
 */
static void Protocol_HandleSetHBridge(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length >= 4) {
        uint8_t bridge = packet->data[0];
        uint8_t mode = packet->data[1];
        uint16_t duty = packet->data[2] | (packet->data[3] << 8);

        if (bridge < 4) {
            /* Convert mode enum */
            PMU_HBridge_Mode_t hb_mode;
            switch (mode) {
                case 0: hb_mode = PMU_HBRIDGE_MODE_COAST; break;
                case 1: hb_mode = PMU_HBRIDGE_MODE_FORWARD; break;
                case 2: hb_mode = PMU_HBRIDGE_MODE_REVERSE; break;
                case 3: hb_mode = PMU_HBRIDGE_MODE_BRAKE; break;
                case 4: hb_mode = PMU_HBRIDGE_MODE_WIPER_PARK; break;
                case 5: hb_mode = PMU_HBRIDGE_MODE_PID; break;
                default: hb_mode = PMU_HBRIDGE_MODE_COAST; break;
            }

            /* Set mode and duty */
            PMU_HBridge_SetMode(bridge, hb_mode, duty);

            /* If PID mode and target position provided */
            if (mode == 5 && packet->length >= 6) {
                uint16_t target = packet->data[4] | (packet->data[5] << 8);
                PMU_HBridge_SetPosition(bridge, target);
            }

            Protocol_SendACK(PMU_CMD_SET_HBRIDGE);
        } else {
            Protocol_SendNACK(PMU_CMD_SET_HBRIDGE, "Invalid bridge");
        }
    } else {
        Protocol_SendNACK(PMU_CMD_SET_HBRIDGE, "Invalid data");
    }
}

static void Protocol_HandleGetOutputs(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;
    uint8_t data[60];  /* 30 channels × 2 bytes */
    uint16_t index = 0;

    for (uint8_t i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        if (ch) {
            data[index++] = ch->state;
            data[index++] = (uint8_t)(ch->pwm_duty / 4);  /* Scale to 0-255 */
        }
    }

    Protocol_SendData(PMU_CMD_GET_OUTPUTS, data, index);
}

static void Protocol_HandleGetInputs(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;
    uint8_t data[40];  /* 20 inputs × 2 bytes */
    uint16_t index = 0;

    for (uint8_t i = 0; i < 20; i++) {
        uint16_t val = PMU_ADC_GetRawValue(i);
        data[index++] = (uint8_t)(val & 0xFF);
        data[index++] = (uint8_t)(val >> 8);
    }

    Protocol_SendData(PMU_CMD_GET_INPUTS, data, index);
}

static void Protocol_HandleLoadConfig(const PMU_Protocol_Packet_t* packet)
{
    /* Store received config for later GET_CONFIG response */
    if (packet->length > 0 && packet->length < CONFIG_BUFFER_SIZE) {
        memcpy(config_buffer, packet->data, packet->length);
        config_buffer[packet->length] = '\0';
        config_buffer_len = packet->length;
        config_received = true;
    }

    /* Load JSON configuration from packet data */
    PMU_JSON_LoadStats_t stats;
    PMU_JSON_Status_t status = PMU_JSON_LoadFromString((const char*)packet->data,
                                                        packet->length,
                                                        &stats);

    if (status == PMU_JSON_OK) {
        /* Send CONFIG_ACK with success=1, error_code=0 */
        uint8_t response[3] = {1, 0, 0};  /* success, error_code low, error_code high */
        Protocol_SendData(PMU_CMD_CONFIG_ACK, response, 3);
    } else {
        /* Send CONFIG_ACK with success=0, error_code=1 */
        uint8_t response[3] = {0, 1, 0};
        Protocol_SendData(PMU_CMD_CONFIG_ACK, response, 3);
    }
}

/**
 * @brief Handle GET_CONFIG command - send current configuration as JSON
 */
static void Protocol_HandleGetConfig(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    const char* config_to_send;
    uint16_t config_len;

    /* Use stored config if available, otherwise minimal default */
    if (config_received && config_buffer_len > 0) {
        config_to_send = config_buffer;
        config_len = config_buffer_len;
    } else {
        /* Minimal valid JSON config as fallback */
        static const char* minimal_config =
            "{"
            "\"version\":\"1.0\","
            "\"device\":{\"name\":\"PMU-30\",\"serial\":\"PMU30-NUCLEO-001\"},"
            "\"outputs\":[],"
            "\"inputs\":[],"
            "\"hbridges\":[],"
            "\"logic\":[]"
            "}";
        config_to_send = minimal_config;
        config_len = strlen(minimal_config);
    }

    /* Build response with chunk header:
     * [chunk_index:2B LE][total_chunks:2B LE][config_data]
     * Use static buffer to avoid stack overflow on F446RE
     */
    static uint8_t response[4 + 512];  /* Max 512 bytes per chunk */
    uint16_t send_len = (config_len > 508) ? 508 : config_len;

    response[0] = 0;  /* chunk_index low */
    response[1] = 0;  /* chunk_index high */
    response[2] = 1;  /* total_chunks low */
    response[3] = 0;  /* total_chunks high */
    memcpy(&response[4], config_to_send, send_len);

    Protocol_SendData(PMU_CMD_CONFIG_DATA, response, 4 + send_len);
}

/**
 * @brief Handle SAVE_CONFIG command - save configuration to flash
 */
static void Protocol_HandleSaveConfig(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;
    /* For Nucleo, just acknowledge - config is kept in RAM buffer */
    /* TODO: For PMU-30, implement actual flash storage */
    uint8_t response[3] = {1, 0, 0};  /* success=1, error_code=0 */
    Protocol_SendData(PMU_CMD_FLASH_ACK, response, 3);
}

/**
 * @brief Handle start logging command
 */
static void Protocol_HandleStartLogging(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    /* Start logging session */
    if (PMU_Logging_Start() == HAL_OK) {
        Protocol_SendACK(PMU_CMD_START_LOGGING);
    } else {
        Protocol_SendNACK(PMU_CMD_START_LOGGING, "Failed to start logging");
    }
}

/**
 * @brief Handle stop logging command
 */
static void Protocol_HandleStopLogging(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    /* Stop logging session */
    if (PMU_Logging_Stop() == HAL_OK) {
        Protocol_SendACK(PMU_CMD_STOP_LOGGING);
    } else {
        Protocol_SendNACK(PMU_CMD_STOP_LOGGING, "Failed to stop logging");
    }
}

/**
 * @brief Handle get log info command
 */
static void Protocol_HandleGetLogInfo(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    /* Get session list */
    PMU_LogSession_t sessions[10];
    uint16_t session_count = PMU_Logging_GetSessionList(sessions, 10);

    /* Pack session info into response */
    uint8_t response[256];
    uint16_t index = 0;

    Protocol_PackU16(response, &index, session_count);

    /* Pack each session using helpers */
    for (uint16_t i = 0; i < session_count && index < sizeof(response) - 21; i++) {
        Protocol_PackU32(response, &index, sessions[i].session_id);
        Protocol_PackU32(response, &index, sessions[i].start_time);
        Protocol_PackU32(response, &index, sessions[i].duration_ms);
        Protocol_PackU32(response, &index, sessions[i].bytes_used);
        Protocol_PackU32(response, &index, sessions[i].sample_count);
        Protocol_PackU8(response, &index, sessions[i].status);
    }

    Protocol_SendData(PMU_CMD_GET_LOG_INFO, response, index);
}

/**
 * @brief Handle download log command
 */
static void Protocol_HandleDownloadLog(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length < 12) {
        Protocol_SendNACK(PMU_CMD_DOWNLOAD_LOG, "Invalid request");
        return;
    }

    /* Parse request using helpers: session_id (4B), offset (4B), length (4B) */
    uint32_t session_id = Protocol_GetU32(packet->data, 0);
    uint32_t offset = Protocol_GetU32(packet->data, 4);
    uint32_t length = Protocol_GetU32(packet->data, 8);

    /* Limit length to max payload size */
    if (length > PMU_PROTOCOL_MAX_PAYLOAD - 12) {
        length = PMU_PROTOCOL_MAX_PAYLOAD - 12;
    }

    /* Download session data */
    uint8_t response[PMU_PROTOCOL_MAX_PAYLOAD];
    uint16_t index = 0;

    /* Pack request parameters in response header */
    memcpy(&response[index], &session_id, 4);
    index += 4;
    memcpy(&response[index], &offset, 4);
    index += 4;

    /* Download data */
    uint32_t bytes_read = PMU_Logging_DownloadSession(session_id,
                                                       &response[index],
                                                       offset,
                                                       length);

    /* Pack bytes read */
    memcpy(&response[8], &bytes_read, 4);
    index += bytes_read;

    if (bytes_read > 0) {
        Protocol_SendData(PMU_CMD_DOWNLOAD_LOG, response, index);
    } else {
        Protocol_SendNACK(PMU_CMD_DOWNLOAD_LOG, "Session not found or invalid offset");
    }
}

/**
 * @brief Handle erase logs command
 */
static void Protocol_HandleEraseLogs(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    /* Erase all logs */
    if (PMU_Logging_EraseAll() == HAL_OK) {
        Protocol_SendACK(PMU_CMD_ERASE_LOGS);
    } else {
        Protocol_SendNACK(PMU_CMD_ERASE_LOGS, "Failed to erase logs");
    }
}

#ifndef PMU_DISABLE_LUA
/* ============================================================================
 * Lua Scripting Command Handlers
 * ============================================================================ */

/**
 * @brief Handle Lua execute command - execute code directly
 * Payload: null-terminated Lua code string
 */
static void Protocol_HandleLuaExecute(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length == 0) {
        Protocol_SendNACK(PMU_CMD_LUA_EXECUTE, "Empty code");
        return;
    }

    /* Ensure null termination */
    char code[PMU_PROTOCOL_MAX_PAYLOAD + 1];
    uint16_t len = (packet->length < PMU_PROTOCOL_MAX_PAYLOAD) ? packet->length : PMU_PROTOCOL_MAX_PAYLOAD;
    memcpy(code, packet->data, len);
    code[len] = '\0';

    /* Execute the code */
    PMU_Lua_Status_t status = PMU_Lua_ExecuteCode(code);

    if (status == PMU_LUA_STATUS_OK) {
        Protocol_SendACK(PMU_CMD_LUA_EXECUTE);
    } else {
        const char* error_msg = PMU_Lua_GetLastError();
        Protocol_SendNACK(PMU_CMD_LUA_EXECUTE, error_msg ? error_msg : "Execution failed");
    }
}

/**
 * @brief Handle Lua load script command
 * Payload: [name_len:1][name:name_len][code:remaining]
 */
static void Protocol_HandleLuaLoadScript(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length < 2) {
        Protocol_SendNACK(PMU_CMD_LUA_LOAD_SCRIPT, "Invalid payload");
        return;
    }

    uint8_t name_len = packet->data[0];
    if (name_len == 0 || name_len > 31 || (1 + name_len) >= packet->length) {
        Protocol_SendNACK(PMU_CMD_LUA_LOAD_SCRIPT, "Invalid script name");
        return;
    }

    /* Extract script name */
    char name[32];
    memcpy(name, &packet->data[1], name_len);
    name[name_len] = '\0';

    /* Extract script code */
    const char* code = (const char*)&packet->data[1 + name_len];
    uint32_t code_len = packet->length - 1 - name_len;

    /* Load the script */
    if (PMU_Lua_LoadScript(name, code, code_len) == HAL_OK) {
        Protocol_SendACK(PMU_CMD_LUA_LOAD_SCRIPT);
    } else {
        Protocol_SendNACK(PMU_CMD_LUA_LOAD_SCRIPT, "Failed to load script");
    }
}

/**
 * @brief Handle Lua unload script command
 * Payload: null-terminated script name
 */
static void Protocol_HandleLuaUnloadScript(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length == 0) {
        Protocol_SendNACK(PMU_CMD_LUA_UNLOAD_SCRIPT, "No script name");
        return;
    }

    char name[32];
    Protocol_ExtractString(packet->data, packet->length, 0, name, 31);

    if (PMU_Lua_UnloadScript(name) == HAL_OK) {
        Protocol_SendACK(PMU_CMD_LUA_UNLOAD_SCRIPT);
    } else {
        Protocol_SendNACK(PMU_CMD_LUA_UNLOAD_SCRIPT, "Script not found");
    }
}

/**
 * @brief Handle Lua run script command
 * Payload: null-terminated script name
 */
static void Protocol_HandleLuaRunScript(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length == 0) {
        Protocol_SendNACK(PMU_CMD_LUA_RUN_SCRIPT, "No script name");
        return;
    }

    char name[32];
    Protocol_ExtractString(packet->data, packet->length, 0, name, 31);

    PMU_Lua_Status_t status = PMU_Lua_ExecuteScript(name);

    if (status == PMU_LUA_STATUS_OK) {
        Protocol_SendACK(PMU_CMD_LUA_RUN_SCRIPT);
    } else {
        const char* error_msg = PMU_Lua_GetLastError();
        Protocol_SendNACK(PMU_CMD_LUA_RUN_SCRIPT, error_msg ? error_msg : "Execution failed");
    }
}

/**
 * @brief Handle Lua stop script command
 * Payload: null-terminated script name
 */
static void Protocol_HandleLuaStopScript(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length == 0) {
        Protocol_SendNACK(PMU_CMD_LUA_STOP_SCRIPT, "No script name");
        return;
    }

    char name[32];
    Protocol_ExtractString(packet->data, packet->length, 0, name, 31);

    /* Disable the script to stop it */
    if (PMU_Lua_SetScriptEnabled(name, 0) == HAL_OK) {
        Protocol_SendACK(PMU_CMD_LUA_STOP_SCRIPT);
    } else {
        Protocol_SendNACK(PMU_CMD_LUA_STOP_SCRIPT, "Script not found");
    }
}

/**
 * @brief Handle Lua get scripts command
 * Response: [count:1][scripts: count * PMU_Lua_ScriptInfo_t]
 */
static void Protocol_HandleLuaGetScripts(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    uint8_t response[PMU_PROTOCOL_MAX_PAYLOAD];
    PMU_Lua_ScriptInfo_t scripts[PMU_LUA_MAX_SCRIPTS];

    uint8_t count = PMU_Lua_ListScripts(scripts, PMU_LUA_MAX_SCRIPTS);

    response[0] = count;
    uint16_t index = 1;

    /* Pack script info */
    for (uint8_t i = 0; i < count && index < PMU_PROTOCOL_MAX_PAYLOAD - 48; i++) {
        /* Name (32 bytes) */
        memcpy(&response[index], scripts[i].name, 32);
        index += 32;
        /* Enabled (1 byte) */
        response[index++] = scripts[i].enabled;
        /* Auto-run (1 byte) */
        response[index++] = scripts[i].auto_run;
        /* Last status (1 byte) */
        response[index++] = (uint8_t)scripts[i].last_status;
        /* Execution count (4 bytes) */
        memcpy(&response[index], &scripts[i].execution_count, 4);
        index += 4;
    }

    Protocol_SendData(PMU_CMD_LUA_GET_SCRIPTS, response, index);
}

/**
 * @brief Handle Lua get status command
 * Response: PMU_Lua_Stats_t
 */
static void Protocol_HandleLuaGetStatus(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    PMU_Lua_Stats_t* stats = PMU_Lua_GetStats();

    if (stats) {
        Protocol_SendData(PMU_CMD_LUA_GET_STATUS, (uint8_t*)stats, sizeof(PMU_Lua_Stats_t));
    } else {
        Protocol_SendNACK(PMU_CMD_LUA_GET_STATUS, "Lua not initialized");
    }
}

/**
 * @brief Handle Lua get output command
 * Response: last error message string
 */
static void Protocol_HandleLuaGetOutput(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    const char* error = PMU_Lua_GetLastError();

    if (error && error[0]) {
        Protocol_SendData(PMU_CMD_LUA_GET_OUTPUT, (const uint8_t*)error, strlen(error) + 1);
    } else {
        Protocol_SendData(PMU_CMD_LUA_GET_OUTPUT, (const uint8_t*)"", 1);
    }
}

/**
 * @brief Handle Lua set enabled command
 * Payload: [name_len:1][name:name_len][enabled:1]
 */
static void Protocol_HandleLuaSetEnabled(const PMU_Protocol_Packet_t* packet)
{
    if (packet->length < 3) {
        Protocol_SendNACK(PMU_CMD_LUA_SET_ENABLED, "Invalid payload");
        return;
    }

    uint8_t name_len = packet->data[0];
    if (name_len == 0 || name_len > 31 || (1 + name_len + 1) > packet->length) {
        Protocol_SendNACK(PMU_CMD_LUA_SET_ENABLED, "Invalid script name");
        return;
    }

    char name[32];
    memcpy(name, &packet->data[1], name_len);
    name[name_len] = '\0';

    uint8_t enabled = packet->data[1 + name_len];

    if (PMU_Lua_SetScriptEnabled(name, enabled) == HAL_OK) {
        Protocol_SendACK(PMU_CMD_LUA_SET_ENABLED);
    } else {
        Protocol_SendNACK(PMU_CMD_LUA_SET_ENABLED, "Script not found");
    }
}
#endif /* PMU_DISABLE_LUA */

/* ============================================================================
 * Atomic Channel Configuration Update Handler
 * ============================================================================ */

/**
 * @brief Send channel config update acknowledgment
 * Response format: [channel_id:2B][success:1B][error_code:2B][error_msg:NB]
 */
static void Protocol_SendChannelConfigACK(uint16_t channel_id, bool success, uint16_t error_code, const char* error_msg)
{
    uint8_t response[64];
    uint16_t index = 0;

    Protocol_PackU16(response, &index, channel_id);
    Protocol_PackU8(response, &index, success ? 1 : 0);
    Protocol_PackU16(response, &index, error_code);

    if (error_msg && !success) {
        uint8_t msg_len = strlen(error_msg);
        if (msg_len > sizeof(response) - index) {
            msg_len = sizeof(response) - index;
        }
        memcpy(&response[index], error_msg, msg_len);
        index += msg_len;
    }

    PMU_Protocol_SendResponse(PMU_CMD_CHANNEL_CONFIG_ACK, response, index);
}

/**
 * @brief Handle SET_CHANNEL_CONFIG command - atomic update of single channel
 * Payload format: [channel_type:1B][channel_id:2B LE][json_len:2B LE][json_config:NB]
 *
 * Channel type values:
 *   0x01 = power_output, 0x02 = hbridge, 0x03 = digital_input, 0x04 = analog_input,
 *   0x05 = logic, 0x06 = number, 0x07 = timer, 0x08 = filter, 0x09 = switch,
 *   0x0A = table_2d, 0x0B = table_3d, 0x0C = can_rx, 0x0D = can_tx, 0x0E = pid
 */
static void Protocol_HandleSetChannelConfig(const PMU_Protocol_Packet_t* packet)
{
    /* Minimum payload: type(1) + channel_id(2) + json_len(2) = 5 bytes */
    if (packet->length < 5) {
        Protocol_SendChannelConfigACK(0, false, 1, "Payload too short");
        return;
    }

    /* Parse header */
    uint8_t channel_type = packet->data[0];
    uint16_t channel_id = Protocol_GetU16(packet->data, 1);
    uint16_t json_len = Protocol_GetU16(packet->data, 3);

    /* Validate JSON length */
    if (5 + json_len > packet->length) {
        Protocol_SendChannelConfigACK(channel_id, false, 2, "JSON truncated");
        return;
    }

    /* Copy JSON to null-terminated buffer */
    char json_buf[PMU_PROTOCOL_MAX_PAYLOAD + 1];
    uint16_t copy_len = (json_len < PMU_PROTOCOL_MAX_PAYLOAD) ? json_len : PMU_PROTOCOL_MAX_PAYLOAD;
    memcpy(json_buf, &packet->data[5], copy_len);
    json_buf[copy_len] = '\0';

    /* Call JSON update function */
    bool success = PMU_JSON_UpdateChannel(channel_type, channel_id, json_buf);

    if (success) {
        Protocol_SendChannelConfigACK(channel_id, true, 0, NULL);
    } else {
        Protocol_SendChannelConfigACK(channel_id, false, 3, PMU_JSON_GetLastError());
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

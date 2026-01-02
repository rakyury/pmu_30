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
/* pmu_config_json.h removed - binary config only */
#include "pmu_channel.h"
#include "pmu_channel_exec.h"
#include "pmu_lua.h"
#include "board_config.h"
#include <string.h>
#include <stdio.h>

/* External functions from main_nucleo_f446.c */
#ifdef NUCLEO_F446RE
extern uint8_t DigitalInput_Get(uint8_t channel);
#endif

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

/* RX buffer for bytes received during TX (to prevent data loss) */
#define RX_PENDING_BUFFER_SIZE 64
static uint8_t rx_pending_buffer[RX_PENDING_BUFFER_SIZE];
static volatile uint8_t rx_pending_head = 0;
static volatile uint8_t rx_pending_tail = 0;

/* Binary config buffer - reduced size for Channel Executor only */
#define CONFIG_BUFFER_SIZE 2048
static uint8_t binary_config_buffer[CONFIG_BUFFER_SIZE];

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
/* Binary config persistence */
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
/* Protocol_HandleSetChannelConfig removed - binary config only */
static void Protocol_HandleLoadBinaryConfig(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleClearConfig(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleReset(const PMU_Protocol_Packet_t* packet);
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
    /* Configuration commands (binary only) */
    {PMU_CMD_GET_CONFIG,        Protocol_HandleGetConfig},
    {PMU_CMD_SAVE_CONFIG,       Protocol_HandleSaveConfig},
    {PMU_CMD_CLEAR_CONFIG,      Protocol_HandleClearConfig},
    {PMU_CMD_LOAD_BINARY_CONFIG, Protocol_HandleLoadBinaryConfig},
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
    /* Device control */
    {PMU_CMD_RESET,             Protocol_HandleReset},
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
        /* RX interrupt is started by Protocol_StartUartReception() in main */
        /* which uses uart_rx_byte buffer defined in main_nucleo_f446.c */
        extern void Protocol_StartUartReception(void);
        Protocol_StartUartReception();
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
                /* Frame format: [0xAA][Length:2B LE][MsgID:1B][Payload][CRC16:2B LE] */
                uint16_t payload_len = protocol_buffer.rx_buffer[1] |
                                      (protocol_buffer.rx_buffer[2] << 8);

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

    /* Add analog inputs data */
    if (telemetry_config.inputs_enabled && index < TELEMETRY_BUFFER_SIZE - 40) {
        /* Pack 20 analog input values (2 bytes each = 40 bytes) */
        for (uint8_t i = 0; i < 20 && index < TELEMETRY_BUFFER_SIZE - 1; i++) {
            uint16_t val = PMU_ADC_GetRawValue(i);
            telemetry_data[index++] = (uint8_t)(val & 0xFF);
            telemetry_data[index++] = (uint8_t)(val >> 8);
        }

        /* Pack 8 digital inputs as 1 byte (bit 0 = DIN0, bit 7 = DIN7) */
#ifdef NUCLEO_F446RE
        uint8_t din_byte = 0;
        for (uint8_t i = 0; i < 8; i++) {
            if (DigitalInput_Get(i)) {
                din_byte |= (1 << i);
            }
        }
        telemetry_data[index++] = din_byte;

        /* System info (15 bytes total): uptime, RAM, Flash, channels */
        {
            /* Uptime in seconds (4 bytes) */
            uint32_t uptime_sec = HAL_GetTick() / 1000;
            memcpy(&telemetry_data[index], &uptime_sec, 4);
            index += 4;

            /* RAM usage: stack used bytes (4 bytes) */
            extern uint32_t _estack;  /* Top of stack from linker */
            uint32_t sp;
            __asm volatile ("mov %0, sp" : "=r" (sp));
            uint32_t stack_used = (uint32_t)&_estack - sp;
            memcpy(&telemetry_data[index], &stack_used, 4);
            index += 4;

            /* Flash usage: program size in bytes (4 bytes) */
            extern uint32_t _sidata;  /* Start of initialized data in flash (end of code) */
            /* Flash starts at 0x08000000, program size = _sidata - 0x08000000 */
            uint32_t flash_used = (uint32_t)&_sidata - 0x08000000U;
            memcpy(&telemetry_data[index], &flash_used, 4);
            index += 4;

            /* Channel count in runtime (2 bytes) */
            uint16_t ch_count = PMU_ChannelExec_GetChannelCount();
            memcpy(&telemetry_data[index], &ch_count, 2);
            index += 2;

            /* Reserved (1 byte) */
            telemetry_data[index++] = 0;
        }
#else
        telemetry_data[index++] = 0;  /* Placeholder for non-Nucleo */
#endif
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

    /* Add virtual channels (Logic, Timer, Number, Switch, Filter, etc.) */
    /* Format: count (2 bytes) + [channel_id (2 bytes) + value (4 bytes)] * count */
    uint16_t virtual_count_offset = index;  /* Save offset for count */
    uint16_t virtual_count = 0;
    index += 2;  /* Reserve space for count */

#ifdef NUCLEO_F446RE
    /* Nucleo: use Channel Executor for virtual channels */
    {
        uint16_t exec_count = PMU_ChannelExec_GetChannelCount();
        for (uint16_t i = 0; i < exec_count && index < TELEMETRY_BUFFER_SIZE - 6; i++) {
            uint16_t ch_id;
            int32_t value;
            if (PMU_ChannelExec_GetChannelInfo(i, &ch_id, &value)) {
                /* Add channel ID */
                memcpy(&telemetry_data[index], &ch_id, sizeof(ch_id));
                index += sizeof(ch_id);

                /* Add channel value (4 bytes signed) */
                memcpy(&telemetry_data[index], &value, sizeof(value));
                index += sizeof(value);

                virtual_count++;
            }
        }
    }
#else
    /* Full PMU-30: scan dedicated virtual channel range 200-999 */
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
#endif

    /* Write virtual channel count at saved offset */
    memcpy(&telemetry_data[virtual_count_offset], &virtual_count, sizeof(virtual_count));

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

    /* Calculate CRC over length(2) + command(1) + payload - excludes start marker */
    packet.crc16 = PMU_Protocol_CRC16(((uint8_t*)&packet) + 1, 3 + length);

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

    /* Send first telemetry packet immediately (don't wait for period) */
    PMU_Protocol_SendTelemetry();

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
 * @brief Check if telemetry stream is active
 */
bool PMU_Protocol_IsStreamActive(void)
{
    return stream_active;
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

    /* Verify CRC
     * Frame format: [0xAA][Length:2B LE][MsgID:1B][Payload][CRC16:2B LE]
     * CRC is calculated over Length+MsgID+Payload (excludes start marker)
     * CRC position in buffer: byte offset (4 + payload_length)
     */
    const uint8_t* raw_bytes = (const uint8_t*)packet;

    /* CRC calculated over bytes 1 to (3 + length): length(2) + command(1) + payload */
    uint16_t calculated_crc = PMU_Protocol_CRC16(&raw_bytes[1], 3 + packet->length);

    /* Read received CRC from correct position (after payload) */
    uint16_t received_crc = raw_bytes[4 + packet->length] |
                           (raw_bytes[5 + packet->length] << 8);

    if (calculated_crc != received_crc) {
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

#ifdef NUCLEO_F446RE
/**
 * @brief Check for RX data and buffer it (called during TX waits)
 * This prevents data loss when the main loop is blocked during TX
 */
static inline void Protocol_CheckRxDuringTx(void)
{
    if (PROTOCOL_UART.Instance->SR & USART_SR_RXNE) {
        uint8_t rx_byte = (uint8_t)(PROTOCOL_UART.Instance->DR & 0xFF);
        uint8_t next_head = (rx_pending_head + 1) % RX_PENDING_BUFFER_SIZE;
        if (next_head != rx_pending_tail) {
            rx_pending_buffer[rx_pending_head] = rx_byte;
            rx_pending_head = next_head;
        }
        /* If buffer full, byte is lost - but this is still better than no buffering */
    }
}

/**
 * @brief Process any pending RX bytes buffered during TX
 */
void PMU_Protocol_ProcessPendingRx(void)
{
    while (rx_pending_tail != rx_pending_head) {
        uint8_t byte = rx_pending_buffer[rx_pending_tail];
        rx_pending_tail = (rx_pending_tail + 1) % RX_PENDING_BUFFER_SIZE;
        PMU_Protocol_ProcessData(&byte, 1);
    }
}
#endif

/**
 * @brief Send packet via active transport
 */
static void Protocol_SendPacket(const PMU_Protocol_Packet_t* packet)
{
    if (!packet) {
        return;
    }

#ifndef UNIT_TEST
    /* Frame format: [0xAA][Length:2B LE][MsgID:1B][Payload][CRC16:2B LE]
     * CRC is stored in packet->crc16 at fixed struct offset,
     * but must be transmitted at position (4 + length)
     */
    uint16_t header_len = 4;  /* marker(1) + length(2) + command(1) */
    uint16_t payload_len = packet->length;
    const uint8_t* header_ptr = (const uint8_t*)packet;  /* first 4 bytes */
    const uint8_t* payload_ptr = packet->data;
    uint8_t crc_bytes[2] = {
        (uint8_t)(packet->crc16 & 0xFF),
        (uint8_t)(packet->crc16 >> 8)
    };

    if (active_transport == PMU_TRANSPORT_UART || active_transport == PMU_TRANSPORT_WIFI) {
        /* Send via UART */
#ifdef NUCLEO_F446RE
        /* Bare-metal TX with RX buffering - prevents command loss during telemetry TX
         * At 115200 baud, ~80 byte telemetry packet takes ~7ms to send.
         * Without RX check, incoming STOP_STREAM command would be lost!
         */
        /* Send header (4 bytes) */
        for (uint16_t i = 0; i < header_len; i++) {
            while (!(PROTOCOL_UART.Instance->SR & USART_SR_TXE)) {
                Protocol_CheckRxDuringTx();  /* Buffer any incoming bytes */
            }
            PROTOCOL_UART.Instance->DR = header_ptr[i];
        }
        /* Send payload */
        for (uint16_t i = 0; i < payload_len; i++) {
            while (!(PROTOCOL_UART.Instance->SR & USART_SR_TXE)) {
                Protocol_CheckRxDuringTx();  /* Buffer any incoming bytes */
            }
            PROTOCOL_UART.Instance->DR = payload_ptr[i];
        }
        /* Send CRC (2 bytes) */
        for (uint16_t i = 0; i < 2; i++) {
            while (!(PROTOCOL_UART.Instance->SR & USART_SR_TXE)) {
                Protocol_CheckRxDuringTx();  /* Buffer any incoming bytes */
            }
            PROTOCOL_UART.Instance->DR = crc_bytes[i];
        }
        while (!(PROTOCOL_UART.Instance->SR & USART_SR_TC)) {
            Protocol_CheckRxDuringTx();  /* Buffer any incoming bytes */
        }
#else
        /* Build linear TX buffer for HAL */
        static uint8_t tx_buffer[4 + 256 + 2];  /* max frame size */
        memcpy(tx_buffer, header_ptr, header_len);
        memcpy(tx_buffer + header_len, payload_ptr, payload_len);
        memcpy(tx_buffer + header_len + payload_len, crc_bytes, 2);
        HAL_UART_Transmit(&PROTOCOL_UART, tx_buffer, header_len + payload_len + 2, 100);
#endif
        protocol_stats.tx_packets++;
        protocol_stats.last_tx_time_ms = 0;  /* HAL_GetTick disabled */
    } else if (active_transport == PMU_TRANSPORT_CAN) {
        /* Send via CAN (chunked if needed) */
        /* Build linear TX buffer first */
        static uint8_t can_tx_buffer[4 + 256 + 2];
        uint16_t total_len = header_len + payload_len + 2;
        memcpy(can_tx_buffer, header_ptr, header_len);
        memcpy(can_tx_buffer + header_len, payload_ptr, payload_len);
        memcpy(can_tx_buffer + header_len + payload_len, crc_bytes, 2);

        PMU_CAN_Message_t can_msg;
        can_msg.id = PMU_PROTOCOL_CAN_ID_BASE;
        can_msg.id_type = PMU_CAN_ID_STANDARD;
        can_msg.frame_type = PMU_CAN_FRAME_FD;
        can_msg.rtr = 0;

        uint16_t offset = 0;
        while (offset < total_len) {
            uint8_t chunk_len = (total_len - offset > 8) ? 8 : (total_len - offset);
            memcpy(can_msg.data, can_tx_buffer + offset, chunk_len);
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
    Protocol_SendData(PMU_CMD_PONG, packet->data, packet->length);
}

static void Protocol_HandleGetVersion(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;
    uint8_t version[64];
    snprintf((char*)version, sizeof(version), "PMU-30 v%d.%d.%d", 1, 0, 0);
    Protocol_SendData(PMU_CMD_INFO_RESP, version, strlen((char*)version));
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

/* Binary config state */
static uint16_t binary_config_len = 0;

/* ============================================================================
 * Binary Config Flash Storage (Nucleo-F446RE)
 * ============================================================================
 * STM32F446RE has 512KB flash with sectors:
 *   Sector 0-3: 16KB each (0x08000000-0x0800FFFF)
 *   Sector 4: 64KB (0x08010000-0x0801FFFF)
 *   Sectors 5-7: 128KB each (0x08020000-0x0807FFFF)
 *
 * We use Sector 7 (last 128KB at 0x08060000) for config storage.
 * Header: [magic:4B][size:2B][crc16:2B] = 8 bytes
 * Data: binary_config_buffer (up to CONFIG_BUFFER_SIZE bytes)
 */
#ifdef NUCLEO_F446RE
#define CONFIG_FLASH_SECTOR      7
#define CONFIG_FLASH_ADDR        0x08060000UL
#define CONFIG_FLASH_MAGIC       0x434F4E46UL  /* "CONF" */

typedef struct __attribute__((packed)) {
    uint32_t magic;      /* CONFIG_FLASH_MAGIC */
    uint16_t size;       /* Size of config data */
    uint16_t crc16;      /* CRC16 of config data */
} BinaryConfigHeader_t;

/**
 * @brief Calculate CRC16 for binary config verification
 */
static uint16_t BinaryConfig_CRC16(const uint8_t* data, uint16_t length)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

/**
 * @brief Save binary config to flash
 */
static bool BinaryConfig_SaveToFlash(void)
{
    if (binary_config_len == 0 || binary_config_len > CONFIG_BUFFER_SIZE) {
        return false;
    }

    /* Prepare header */
    BinaryConfigHeader_t header;
    header.magic = CONFIG_FLASH_MAGIC;
    header.size = binary_config_len;
    header.crc16 = BinaryConfig_CRC16(binary_config_buffer, binary_config_len);

    /* Unlock flash */
    HAL_FLASH_Unlock();

    /* Erase Sector 7 */
    FLASH_EraseInitTypeDef erase_init;
    uint32_t sector_error = 0;
    erase_init.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase_init.Sector = CONFIG_FLASH_SECTOR;
    erase_init.NbSectors = 1;
    erase_init.VoltageRange = FLASH_VOLTAGE_RANGE_3;  /* 2.7V-3.6V */

    if (HAL_FLASHEx_Erase(&erase_init, &sector_error) != HAL_OK) {
        HAL_FLASH_Lock();
        return false;
    }

    /* Write header (8 bytes = 2 words) */
    uint32_t addr = CONFIG_FLASH_ADDR;
    uint32_t* header_ptr = (uint32_t*)&header;
    for (int i = 0; i < 2; i++) {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr, header_ptr[i]) != HAL_OK) {
            HAL_FLASH_Lock();
            return false;
        }
        addr += 4;
    }

    /* Write config data (word-aligned) */
    uint32_t words = (binary_config_len + 3) / 4;
    uint32_t* data_ptr = (uint32_t*)binary_config_buffer;
    for (uint32_t i = 0; i < words; i++) {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr, data_ptr[i]) != HAL_OK) {
            HAL_FLASH_Lock();
            return false;
        }
        addr += 4;
    }

    HAL_FLASH_Lock();
    return true;
}

/**
 * @brief Load binary config from flash at startup
 */
bool PMU_Protocol_LoadSavedConfig(void)
{
    BinaryConfigHeader_t* header = (BinaryConfigHeader_t*)CONFIG_FLASH_ADDR;

    /* Check magic */
    if (header->magic != CONFIG_FLASH_MAGIC) {
        return false;  /* No saved config */
    }

    /* Check size */
    if (header->size == 0 || header->size > CONFIG_BUFFER_SIZE) {
        return false;
    }

    /* Read config data */
    uint8_t* flash_data = (uint8_t*)(CONFIG_FLASH_ADDR + sizeof(BinaryConfigHeader_t));
    memcpy(binary_config_buffer, flash_data, header->size);
    binary_config_len = header->size;

    /* Verify CRC */
    uint16_t calc_crc = BinaryConfig_CRC16(binary_config_buffer, binary_config_len);
    if (calc_crc != header->crc16) {
        binary_config_len = 0;
        return false;
    }

    /* Load into Channel Executor */
    int loaded = PMU_ChannelExec_LoadConfig(binary_config_buffer, binary_config_len);
    return (loaded >= 0);
}

#else
/* Non-Nucleo platforms - stub implementation */
static bool BinaryConfig_SaveToFlash(void) { return false; }
bool PMU_Protocol_LoadSavedConfig(void) { return false; }
#endif

/**
 * @brief Handle GET_CONFIG command - return current binary configuration
 *
 * Response format (chunked if needed):
 * [chunk_idx:2B LE][total_chunks:2B LE][data]
 *
 * Always uses chunked format (even for single chunk) for consistency.
 */
static void Protocol_HandleGetConfig(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    if (binary_config_len == 0) {
        /* No config loaded - send single chunk with channel_count=0 */
        uint8_t response[6] = {0, 0, 1, 0, 0, 0};  /* chunk_idx=0, total_chunks=1, channel_count=0 */
        Protocol_SendData(PMU_CMD_CONFIG_DATA, response, 6);
        return;
    }

    /* Always use chunked format for consistency */
    uint16_t chunk_size = 256;
    uint16_t total_chunks = (binary_config_len + chunk_size - 1) / chunk_size;
    if (total_chunks == 0) total_chunks = 1;

    for (uint16_t chunk_idx = 0; chunk_idx < total_chunks; chunk_idx++) {
        uint16_t offset = chunk_idx * chunk_size;
        uint16_t len = binary_config_len - offset;
        if (len > chunk_size) len = chunk_size;

        /* Response: [chunk_idx:2B][total_chunks:2B][data:N bytes] */
        uint8_t response[4 + 256];
        response[0] = (uint8_t)(chunk_idx & 0xFF);
        response[1] = (uint8_t)((chunk_idx >> 8) & 0xFF);
        response[2] = (uint8_t)(total_chunks & 0xFF);
        response[3] = (uint8_t)((total_chunks >> 8) & 0xFF);
        memcpy(response + 4, binary_config_buffer + offset, len);
        Protocol_SendData(PMU_CMD_CONFIG_DATA, response, 4 + len);
    }
}

/**
 * @brief Handle SAVE_CONFIG command - save configuration to flash
 */
static void Protocol_HandleSaveConfig(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    if (binary_config_len == 0) {
        /* No config to save */
        uint8_t response[3] = {0, 1, 0};  /* success=0, error_code=1 */
        Protocol_SendData(PMU_CMD_FLASH_ACK, response, 3);
        return;
    }

    bool success = BinaryConfig_SaveToFlash();
    uint8_t response[3] = {success ? 1 : 0, success ? 0 : 2, 0};
    Protocol_SendData(PMU_CMD_FLASH_ACK, response, 3);
}

/**
 * @brief Handle CLEAR_CONFIG command - clear config from memory and flash
 *
 * This resets the device to a clean state with no user configuration.
 * Telemetry continues to work with system channels (physical pins, uptime, etc.)
 */
static void Protocol_HandleClearConfig(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    /* Clear in-memory config */
    binary_config_len = 0;
    memset(binary_config_buffer, 0, sizeof(binary_config_buffer));

    /* Clear channel executor */
    PMU_ChannelExec_Clear();

    /* Erase flash sector (if we're on Nucleo) */
#ifdef NUCLEO_F446RE
    HAL_FLASH_Unlock();

    /* Erase Sector 7 */
    FLASH_EraseInitTypeDef erase;
    erase.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase.Sector = CONFIG_FLASH_SECTOR;
    erase.NbSectors = 1;
    erase.VoltageRange = FLASH_VOLTAGE_RANGE_3;

    uint32_t error = 0;
    HAL_StatusTypeDef status = HAL_FLASHEx_Erase(&erase, &error);

    HAL_FLASH_Lock();

    uint8_t response[2] = {(status == HAL_OK) ? 1 : 0, (status == HAL_OK) ? 0 : 1};
#else
    uint8_t response[2] = {1, 0};  /* Always success on non-Nucleo */
#endif

    Protocol_SendData(PMU_CMD_CLEAR_CONFIG_ACK, response, 2);
}

/* Binary config chunked upload state */
static uint16_t binary_total_chunks = 0;
static uint16_t binary_received_chunks = 0;

/**
 * @brief Handle LOAD_BINARY_CONFIG command - load binary channel configuration
 *
 * Binary config format (chunked):
 * Chunk header: [chunk_idx:2B LE][total_chunks:2B LE][data]
 *
 * Complete payload format (after reassembly):
 * [channel_count:2B LE]
 * For each channel:
 *   [channel_id:2B LE]
 *   [type:1B]
 *   [config_size:1B]
 *   [config_data:N bytes]
 */
static void Protocol_HandleLoadBinaryConfig(const PMU_Protocol_Packet_t* packet)
{
    /* Always use chunked format: [chunk_idx:2B LE][total_chunks:2B LE][data] */
    if (packet->length < 4) {
        uint8_t response[4] = {0, 2, 0, 0};  /* success=0, error=2 (invalid format) */
        Protocol_SendData(PMU_CMD_BINARY_CONFIG_ACK, response, 4);
        return;
    }

    uint16_t chunk_idx = packet->data[0] | (packet->data[1] << 8);
    uint16_t total_chunks = packet->data[2] | (packet->data[3] << 8);
    const uint8_t* chunk_data = packet->data + 4;
    uint16_t chunk_len = packet->length - 4;

    /* Validate chunk header */
    if (total_chunks == 0 || total_chunks > 64 || chunk_idx >= total_chunks) {
        uint8_t response[4] = {0, 3, 0, 0};  /* success=0, error=3 (invalid chunk header) */
        Protocol_SendData(PMU_CMD_BINARY_CONFIG_ACK, response, 4);
        return;
    }

    /* First chunk - reset buffer and stop telemetry */
    if (chunk_idx == 0) {
        PMU_Protocol_StopStream();  /* Stop telemetry during config load */
        binary_config_len = 0;
        binary_total_chunks = total_chunks;
        binary_received_chunks = 0;
    }

    /* Accumulate chunk data */
    if (binary_config_len + chunk_len >= CONFIG_BUFFER_SIZE) {
        uint8_t response[4] = {0, 1, 0, 0};  /* success=0, error=1 (overflow) */
        Protocol_SendData(PMU_CMD_BINARY_CONFIG_ACK, response, 4);
        return;
    }

    memcpy(binary_config_buffer + binary_config_len, chunk_data, chunk_len);
    binary_config_len += chunk_len;
    binary_received_chunks++;

    /* All chunks received - process binary config */
    if (binary_received_chunks >= binary_total_chunks) {
        /* Load into Channel Executor */
        int loaded = PMU_ChannelExec_LoadConfig(binary_config_buffer, binary_config_len);

        /* Send final status (only one ACK for complete config) */
        uint8_t final_response[6] = {0};
        final_response[0] = (loaded >= 0) ? 1 : 0;  /* success */
        final_response[1] = (loaded >= 0) ? 0 : 1;  /* error_code */
        final_response[2] = (uint8_t)(loaded & 0xFF);        /* channels loaded (low) */
        final_response[3] = (uint8_t)((loaded >> 8) & 0xFF); /* channels loaded (high) */
        final_response[4] = (uint8_t)PMU_ChannelExec_GetChannelCount();  /* total channels */
        final_response[5] = 0;  /* reserved */
        Protocol_SendData(PMU_CMD_BINARY_CONFIG_ACK, final_response, 6);
    } else {
        /* Send intermediate ACK for multi-chunk upload */
        uint8_t response[4] = {1, 0, (uint8_t)chunk_idx, (uint8_t)(chunk_idx >> 8)};
        Protocol_SendData(PMU_CMD_BINARY_CONFIG_ACK, response, 4);
    }
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

/* Protocol_HandleSetChannelConfig removed - use LOAD_BINARY_CONFIG for config updates */

/**
 * @brief Handle RESET command - software reset the device
 */
static void Protocol_HandleReset(const PMU_Protocol_Packet_t* packet)
{
    (void)packet;

    /* Send ACK before reset */
    Protocol_SendACK(PMU_CMD_RESET);

    /* Small delay to ensure ACK is transmitted */
    for (volatile int i = 0; i < 100000; i++) { }

    /* Perform software reset */
    NVIC_SystemReset();
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

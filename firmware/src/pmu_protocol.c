/**
 ******************************************************************************
 * @file           : pmu_protocol.c
 * @brief          : Real-Time Control Protocol Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * ECUMaster-style real-time control protocol implementation
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
#define TELEMETRY_BUFFER_SIZE   256     /**< Telemetry buffer size */

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

#ifndef UNIT_TEST
extern UART_HandleTypeDef huart1;  /* UART for WiFi module (ESP32-C3) */
extern UART_HandleTypeDef huart2;  /* UART for USB/debug */
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
static void Protocol_HandleGetOutputs(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleGetInputs(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleLoadConfig(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleStartLogging(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleStopLogging(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleGetLogInfo(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleDownloadLog(const PMU_Protocol_Packet_t* packet);
static void Protocol_HandleEraseLogs(const PMU_Protocol_Packet_t* packet);
static bool Protocol_ValidatePacket(const PMU_Protocol_Packet_t* packet);

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
    /* Initialize UART for WiFi module (ESP32-C3) */
    if (transport == PMU_TRANSPORT_UART || transport == PMU_TRANSPORT_WIFI) {
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
        for (uint8_t i = 0; i < 20 && index < TELEMETRY_BUFFER_SIZE - 1) {
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
        int16_t board_temp = prot->temperature.board_temp_C;
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

    switch (packet->command) {
        case PMU_CMD_PING:
            Protocol_HandlePing(packet);
            break;

        case PMU_CMD_GET_VERSION:
            Protocol_HandleGetVersion(packet);
            break;

        case PMU_CMD_GET_SERIAL:
            Protocol_HandleGetSerial(packet);
            break;

        case PMU_CMD_START_STREAM:
            Protocol_HandleStartStream(packet);
            break;

        case PMU_CMD_STOP_STREAM:
            Protocol_HandleStopStream(packet);
            break;

        case PMU_CMD_SET_OUTPUT:
            Protocol_HandleSetOutput(packet);
            break;

        case PMU_CMD_SET_PWM:
            Protocol_HandleSetPWM(packet);
            break;

        case PMU_CMD_GET_OUTPUTS:
            Protocol_HandleGetOutputs(packet);
            break;

        case PMU_CMD_GET_INPUTS:
            Protocol_HandleGetInputs(packet);
            break;

        case PMU_CMD_LOAD_CONFIG:
            Protocol_HandleLoadConfig(packet);
            break;

        case PMU_CMD_START_LOGGING:
            Protocol_HandleStartLogging(packet);
            break;

        case PMU_CMD_STOP_LOGGING:
            Protocol_HandleStopLogging(packet);
            break;

        case PMU_CMD_GET_LOG_INFO:
            Protocol_HandleGetLogInfo(packet);
            break;

        case PMU_CMD_DOWNLOAD_LOG:
            Protocol_HandleDownloadLog(packet);
            break;

        case PMU_CMD_ERASE_LOGS:
            Protocol_HandleEraseLogs(packet);
            break;

        default:
            Protocol_SendNACK(packet->command, "Unknown command");
            break;
    }
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
        HAL_UART_Transmit(&huart1, (uint8_t*)packet, total_len, 100);
        protocol_stats.tx_packets++;
        protocol_stats.last_tx_time_ms = HAL_GetTick();
    } else if (active_transport == PMU_TRANSPORT_CAN) {
        /* Send via CAN (chunked if needed) */
        PMU_CAN_Message_t can_msg;
        can_msg.id = PMU_PROTOCOL_CAN_ID_BASE;
        can_msg.is_extended = false;
        can_msg.is_fd = true;

        uint16_t offset = 0;
        while (offset < total_len) {
            uint8_t chunk_len = (total_len - offset > 8) ? 8 : (total_len - offset);
            memcpy(can_msg.data, (uint8_t*)packet + offset, chunk_len);
            can_msg.length = chunk_len;

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
    snprintf((char*)serial, sizeof(serial), "PMU30-%08lX", HAL_GetUIDw0());
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
            PMU_PROFET_SetChannel(channel, 1, duty);
            Protocol_SendACK(PMU_CMD_SET_PWM);
        } else {
            Protocol_SendNACK(PMU_CMD_SET_PWM, "Invalid channel");
        }
    } else {
        Protocol_SendNACK(PMU_CMD_SET_PWM, "Invalid data");
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
    /* Load JSON configuration from packet data */
    PMU_JSON_LoadStats_t stats;
    PMU_JSON_Status_t status = PMU_JSON_LoadFromString((const char*)packet->data,
                                                        packet->length,
                                                        &stats);

    if (status == PMU_JSON_OK) {
        uint8_t response[32];
        snprintf((char*)response, sizeof(response),
                 "Loaded: %lu inputs, %lu outputs",
                 stats.inputs_loaded, stats.outputs_loaded);
        Protocol_SendData(PMU_CMD_LOAD_CONFIG, response, strlen((char*)response));
    } else {
        Protocol_SendNACK(PMU_CMD_LOAD_CONFIG, PMU_JSON_GetLastError());
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

    /* Pack session count */
    response[index++] = session_count & 0xFF;
    response[index++] = (session_count >> 8) & 0xFF;

    /* Pack each session */
    for (uint16_t i = 0; i < session_count && index < sizeof(response) - 20; i++) {
        /* Session ID (4 bytes) */
        memcpy(&response[index], &sessions[i].session_id, 4);
        index += 4;

        /* Start time (4 bytes) */
        memcpy(&response[index], &sessions[i].start_time, 4);
        index += 4;

        /* Duration (4 bytes) */
        memcpy(&response[index], &sessions[i].duration_ms, 4);
        index += 4;

        /* Bytes used (4 bytes) */
        memcpy(&response[index], &sessions[i].bytes_used, 4);
        index += 4;

        /* Sample count (4 bytes) */
        memcpy(&response[index], &sessions[i].sample_count, 4);
        index += 4;

        /* Status (1 byte) */
        response[index++] = sessions[i].status;
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

    /* Parse request: session_id (4B), offset (4B), length (4B) */
    uint32_t session_id;
    uint32_t offset;
    uint32_t length;

    memcpy(&session_id, &packet->data[0], 4);
    memcpy(&offset, &packet->data[4], 4);
    memcpy(&length, &packet->data[8], 4);

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

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

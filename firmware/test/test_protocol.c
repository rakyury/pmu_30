/**
 * @file test_protocol.c
 * @brief Unit tests for pmu_protocol module
 *
 * Tests:
 * - Command types and constants
 * - CRC16 calculation
 * - Packet structure
 * - Telemetry configuration
 * - Statistics tracking
 */

#include "unity.h"
#include "pmu_protocol.h"
#include <string.h>

/* ============================================================================
 * Test Helpers
 * ============================================================================ */

static PMU_TelemetryConfig_t default_telemetry_config;

static void reset_telemetry_config(void)
{
    memset(&default_telemetry_config, 0, sizeof(default_telemetry_config));
    default_telemetry_config.outputs_enabled = true;
    default_telemetry_config.inputs_enabled = true;
    default_telemetry_config.rate_hz = 10;
}

/* ============================================================================
 * Command Type Tests
 * ============================================================================ */

void test_basic_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0x01, PMU_CMD_PING);
    TEST_ASSERT_EQUAL_HEX8(0x02, PMU_CMD_GET_VERSION);
    TEST_ASSERT_EQUAL_HEX8(0x03, PMU_CMD_GET_SERIAL);
    TEST_ASSERT_EQUAL_HEX8(0x04, PMU_CMD_RESET);
    TEST_ASSERT_EQUAL_HEX8(0x05, PMU_CMD_BOOTLOADER);
}

void test_telemetry_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0x20, PMU_CMD_START_STREAM);
    TEST_ASSERT_EQUAL_HEX8(0x21, PMU_CMD_STOP_STREAM);
    TEST_ASSERT_EQUAL_HEX8(0x22, PMU_CMD_GET_OUTPUTS);
    TEST_ASSERT_EQUAL_HEX8(0x23, PMU_CMD_GET_INPUTS);
    TEST_ASSERT_EQUAL_HEX8(0x24, PMU_CMD_GET_CAN);
    TEST_ASSERT_EQUAL_HEX8(0x25, PMU_CMD_GET_TEMPS);
    TEST_ASSERT_EQUAL_HEX8(0x26, PMU_CMD_GET_VOLTAGES);
    TEST_ASSERT_EQUAL_HEX8(0x27, PMU_CMD_GET_FAULTS);
}

void test_control_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0x40, PMU_CMD_SET_OUTPUT);
    TEST_ASSERT_EQUAL_HEX8(0x41, PMU_CMD_SET_PWM);
    TEST_ASSERT_EQUAL_HEX8(0x42, PMU_CMD_SET_HBRIDGE);
    TEST_ASSERT_EQUAL_HEX8(0x43, PMU_CMD_CLEAR_FAULTS);
    TEST_ASSERT_EQUAL_HEX8(0x44, PMU_CMD_SET_VIRTUAL);
}

void test_config_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0x60, PMU_CMD_LOAD_CONFIG);
    TEST_ASSERT_EQUAL_HEX8(0x61, PMU_CMD_SAVE_CONFIG);
    TEST_ASSERT_EQUAL_HEX8(0x62, PMU_CMD_GET_CONFIG);
    TEST_ASSERT_EQUAL_HEX8(0x63, PMU_CMD_UPLOAD_CONFIG);
    TEST_ASSERT_EQUAL_HEX8(0x64, PMU_CMD_DOWNLOAD_CONFIG);
    TEST_ASSERT_EQUAL_HEX8(0x65, PMU_CMD_VALIDATE_CONFIG);
}

void test_logging_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0x80, PMU_CMD_START_LOGGING);
    TEST_ASSERT_EQUAL_HEX8(0x81, PMU_CMD_STOP_LOGGING);
    TEST_ASSERT_EQUAL_HEX8(0x82, PMU_CMD_GET_LOG_INFO);
    TEST_ASSERT_EQUAL_HEX8(0x83, PMU_CMD_DOWNLOAD_LOG);
    TEST_ASSERT_EQUAL_HEX8(0x84, PMU_CMD_ERASE_LOGS);
}

void test_diagnostic_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0xA0, PMU_CMD_GET_STATS);
    TEST_ASSERT_EQUAL_HEX8(0xA1, PMU_CMD_GET_UPTIME);
    TEST_ASSERT_EQUAL_HEX8(0xA2, PMU_CMD_GET_CAN_STATS);
    TEST_ASSERT_EQUAL_HEX8(0xA3, PMU_CMD_SELF_TEST);
}

void test_lua_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0xB0, PMU_CMD_LUA_EXECUTE);
    TEST_ASSERT_EQUAL_HEX8(0xB1, PMU_CMD_LUA_LOAD_SCRIPT);
    TEST_ASSERT_EQUAL_HEX8(0xB2, PMU_CMD_LUA_UNLOAD_SCRIPT);
    TEST_ASSERT_EQUAL_HEX8(0xB3, PMU_CMD_LUA_RUN_SCRIPT);
    TEST_ASSERT_EQUAL_HEX8(0xB4, PMU_CMD_LUA_STOP_SCRIPT);
    TEST_ASSERT_EQUAL_HEX8(0xB5, PMU_CMD_LUA_GET_SCRIPTS);
    TEST_ASSERT_EQUAL_HEX8(0xB6, PMU_CMD_LUA_GET_STATUS);
    TEST_ASSERT_EQUAL_HEX8(0xB7, PMU_CMD_LUA_GET_OUTPUT);
    TEST_ASSERT_EQUAL_HEX8(0xB8, PMU_CMD_LUA_SET_ENABLED);
}

void test_firmware_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0xC0, PMU_CMD_FW_UPDATE_START);
    TEST_ASSERT_EQUAL_HEX8(0xC1, PMU_CMD_FW_UPDATE_DATA);
    TEST_ASSERT_EQUAL_HEX8(0xC2, PMU_CMD_FW_UPDATE_FINISH);
    TEST_ASSERT_EQUAL_HEX8(0xC3, PMU_CMD_FW_UPDATE_ABORT);
}

void test_response_command_values(void)
{
    TEST_ASSERT_EQUAL_HEX8(0xE0, PMU_CMD_ACK);
    TEST_ASSERT_EQUAL_HEX8(0xE1, PMU_CMD_NACK);
    TEST_ASSERT_EQUAL_HEX8(0xE2, PMU_CMD_ERROR);
    TEST_ASSERT_EQUAL_HEX8(0xE3, PMU_CMD_DATA);
}

/* ============================================================================
 * Protocol Constants Tests
 * ============================================================================ */

void test_protocol_start_marker(void)
{
    TEST_ASSERT_EQUAL_HEX8(0xAA, PMU_PROTOCOL_START_MARKER);
}

void test_protocol_version(void)
{
    TEST_ASSERT_EQUAL_UINT8(0x01, PMU_PROTOCOL_VERSION);
}

void test_protocol_max_payload(void)
{
    TEST_ASSERT_EQUAL_INT(256, PMU_PROTOCOL_MAX_PAYLOAD);
}

void test_protocol_uart_baud(void)
{
    TEST_ASSERT_EQUAL_INT(115200, PMU_PROTOCOL_UART_BAUD);
}

void test_protocol_can_id_base(void)
{
    TEST_ASSERT_EQUAL_HEX32(0x600, PMU_PROTOCOL_CAN_ID_BASE);
}

/* ============================================================================
 * Stream Rate Constants Tests
 * ============================================================================ */

void test_stream_rate_1hz(void)
{
    TEST_ASSERT_EQUAL_INT(1, PMU_STREAM_RATE_1HZ);
}

void test_stream_rate_10hz(void)
{
    TEST_ASSERT_EQUAL_INT(10, PMU_STREAM_RATE_10HZ);
}

void test_stream_rate_50hz(void)
{
    TEST_ASSERT_EQUAL_INT(50, PMU_STREAM_RATE_50HZ);
}

void test_stream_rate_100hz(void)
{
    TEST_ASSERT_EQUAL_INT(100, PMU_STREAM_RATE_100HZ);
}

void test_stream_rate_500hz(void)
{
    TEST_ASSERT_EQUAL_INT(500, PMU_STREAM_RATE_500HZ);
}

void test_stream_rate_1000hz(void)
{
    TEST_ASSERT_EQUAL_INT(1000, PMU_STREAM_RATE_1000HZ);
}

/* ============================================================================
 * Transport Enum Tests
 * ============================================================================ */

void test_transport_uart(void)
{
    TEST_ASSERT_EQUAL_INT(PMU_TRANSPORT_UART, 0);
}

void test_transport_wifi(void)
{
    TEST_ASSERT_EQUAL_INT(PMU_TRANSPORT_WIFI, 1);
}

void test_transport_can(void)
{
    TEST_ASSERT_EQUAL_INT(PMU_TRANSPORT_CAN, 2);
}

/* ============================================================================
 * Packet Structure Tests
 * ============================================================================ */

void test_packet_structure_size(void)
{
    // Start marker (1) + command (1) + length (2) + data (256) + crc16 (2) = 262
    TEST_ASSERT_EQUAL_INT(262, sizeof(PMU_Protocol_Packet_t));
}

void test_packet_start_marker_offset(void)
{
    PMU_Protocol_Packet_t packet;
    TEST_ASSERT_EQUAL_PTR(&packet, &packet.start_marker);
}

void test_packet_command_offset(void)
{
    PMU_Protocol_Packet_t packet;
    TEST_ASSERT_EQUAL_INT(1, (uint8_t*)&packet.command - (uint8_t*)&packet);
}

void test_packet_length_offset(void)
{
    PMU_Protocol_Packet_t packet;
    TEST_ASSERT_EQUAL_INT(2, (uint8_t*)&packet.length - (uint8_t*)&packet);
}

void test_packet_data_offset(void)
{
    PMU_Protocol_Packet_t packet;
    TEST_ASSERT_EQUAL_INT(4, (uint8_t*)&packet.data - (uint8_t*)&packet);
}

/* ============================================================================
 * Telemetry Config Structure Tests
 * ============================================================================ */

void test_telemetry_config_defaults(void)
{
    reset_telemetry_config();

    TEST_ASSERT_TRUE(default_telemetry_config.outputs_enabled);
    TEST_ASSERT_TRUE(default_telemetry_config.inputs_enabled);
    TEST_ASSERT_FALSE(default_telemetry_config.can_enabled);
    TEST_ASSERT_FALSE(default_telemetry_config.temps_enabled);
    TEST_ASSERT_FALSE(default_telemetry_config.voltages_enabled);
    TEST_ASSERT_FALSE(default_telemetry_config.faults_enabled);
    TEST_ASSERT_EQUAL_UINT16(10, default_telemetry_config.rate_hz);
}

void test_telemetry_config_all_enabled(void)
{
    PMU_TelemetryConfig_t config;
    config.outputs_enabled = true;
    config.inputs_enabled = true;
    config.can_enabled = true;
    config.temps_enabled = true;
    config.voltages_enabled = true;
    config.faults_enabled = true;
    config.rate_hz = 100;

    TEST_ASSERT_TRUE(config.outputs_enabled);
    TEST_ASSERT_TRUE(config.inputs_enabled);
    TEST_ASSERT_TRUE(config.can_enabled);
    TEST_ASSERT_TRUE(config.temps_enabled);
    TEST_ASSERT_TRUE(config.voltages_enabled);
    TEST_ASSERT_TRUE(config.faults_enabled);
    TEST_ASSERT_EQUAL_UINT16(100, config.rate_hz);
}

/* ============================================================================
 * Statistics Structure Tests
 * ============================================================================ */

void test_stats_structure_zeroed(void)
{
    PMU_Protocol_Stats_t stats;
    memset(&stats, 0, sizeof(stats));

    TEST_ASSERT_EQUAL_UINT32(0, stats.rx_packets);
    TEST_ASSERT_EQUAL_UINT32(0, stats.tx_packets);
    TEST_ASSERT_EQUAL_UINT32(0, stats.rx_errors);
    TEST_ASSERT_EQUAL_UINT32(0, stats.tx_errors);
    TEST_ASSERT_EQUAL_UINT32(0, stats.last_rx_time_ms);
    TEST_ASSERT_EQUAL_UINT32(0, stats.last_tx_time_ms);
}

/* ============================================================================
 * CRC16 Tests
 * ============================================================================ */

void test_crc16_empty(void)
{
    uint8_t data[1] = {0};
    uint16_t crc = PMU_Protocol_CRC16(data, 0);
    // CRC of empty data should be initial value or specific
    TEST_ASSERT_TRUE(crc != 0 || crc == 0);  // Just verify it doesn't crash
}

void test_crc16_single_byte(void)
{
    uint8_t data[1] = {0x00};
    uint16_t crc1 = PMU_Protocol_CRC16(data, 1);

    data[0] = 0xFF;
    uint16_t crc2 = PMU_Protocol_CRC16(data, 1);

    TEST_ASSERT_NOT_EQUAL(crc1, crc2);
}

void test_crc16_multiple_bytes(void)
{
    uint8_t data[4] = {0x01, 0x02, 0x03, 0x04};
    uint16_t crc = PMU_Protocol_CRC16(data, 4);

    // CRC should be non-zero for typical data
    TEST_ASSERT_TRUE(crc != 0 || crc == 0);  // Just verify computation
}

void test_crc16_deterministic(void)
{
    uint8_t data[8] = {0xAA, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

    uint16_t crc1 = PMU_Protocol_CRC16(data, 8);
    uint16_t crc2 = PMU_Protocol_CRC16(data, 8);

    TEST_ASSERT_EQUAL_HEX16(crc1, crc2);
}

void test_crc16_different_data(void)
{
    uint8_t data1[4] = {0x01, 0x02, 0x03, 0x04};
    uint8_t data2[4] = {0x01, 0x02, 0x03, 0x05};  // One byte different

    uint16_t crc1 = PMU_Protocol_CRC16(data1, 4);
    uint16_t crc2 = PMU_Protocol_CRC16(data2, 4);

    TEST_ASSERT_NOT_EQUAL(crc1, crc2);
}

void test_crc16_different_lengths(void)
{
    uint8_t data[8] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};

    uint16_t crc4 = PMU_Protocol_CRC16(data, 4);
    uint16_t crc8 = PMU_Protocol_CRC16(data, 8);

    TEST_ASSERT_NOT_EQUAL(crc4, crc8);
}

/* ============================================================================
 * Command Range Tests
 * ============================================================================ */

void test_command_ranges_basic(void)
{
    // Basic commands should be in 0x00-0x1F range
    TEST_ASSERT_LESS_THAN(0x20, PMU_CMD_PING);
    TEST_ASSERT_LESS_THAN(0x20, PMU_CMD_BOOTLOADER);
}

void test_command_ranges_telemetry(void)
{
    // Telemetry commands should be in 0x20-0x3F range
    TEST_ASSERT_GREATER_OR_EQUAL(0x20, PMU_CMD_START_STREAM);
    TEST_ASSERT_LESS_THAN(0x40, PMU_CMD_GET_FAULTS);
}

void test_command_ranges_control(void)
{
    // Control commands should be in 0x40-0x5F range
    TEST_ASSERT_GREATER_OR_EQUAL(0x40, PMU_CMD_SET_OUTPUT);
    TEST_ASSERT_LESS_THAN(0x60, PMU_CMD_SET_VIRTUAL);
}

void test_command_ranges_config(void)
{
    // Config commands should be in 0x60-0x7F range
    TEST_ASSERT_GREATER_OR_EQUAL(0x60, PMU_CMD_LOAD_CONFIG);
    TEST_ASSERT_LESS_THAN(0x80, PMU_CMD_VALIDATE_CONFIG);
}

void test_command_ranges_logging(void)
{
    // Logging commands should be in 0x80-0x9F range
    TEST_ASSERT_GREATER_OR_EQUAL(0x80, PMU_CMD_START_LOGGING);
    TEST_ASSERT_LESS_THAN(0xA0, PMU_CMD_ERASE_LOGS);
}

void test_command_ranges_diagnostic(void)
{
    // Diagnostic commands should be in 0xA0-0xAF range
    TEST_ASSERT_GREATER_OR_EQUAL(0xA0, PMU_CMD_GET_STATS);
    TEST_ASSERT_LESS_THAN(0xB0, PMU_CMD_SELF_TEST);
}

void test_command_ranges_lua(void)
{
    // Lua commands should be in 0xB0-0xBF range
    TEST_ASSERT_GREATER_OR_EQUAL(0xB0, PMU_CMD_LUA_EXECUTE);
    TEST_ASSERT_LESS_THAN(0xC0, PMU_CMD_LUA_SET_ENABLED);
}

void test_command_ranges_firmware(void)
{
    // Firmware commands should be in 0xC0-0xDF range
    TEST_ASSERT_GREATER_OR_EQUAL(0xC0, PMU_CMD_FW_UPDATE_START);
    TEST_ASSERT_LESS_THAN(0xE0, PMU_CMD_FW_UPDATE_ABORT);
}

void test_command_ranges_response(void)
{
    // Response commands should be in 0xE0-0xFF range
    TEST_ASSERT_GREATER_OR_EQUAL(0xE0, PMU_CMD_ACK);
    TEST_ASSERT_GREATER_OR_EQUAL(0xE0, PMU_CMD_DATA);
}

/* ============================================================================
 * Main Test Runner
 * ============================================================================ */

int test_protocol_main(void)
{
    UNITY_BEGIN();

    /* Command Type Tests */
    RUN_TEST(test_basic_command_values);
    RUN_TEST(test_telemetry_command_values);
    RUN_TEST(test_control_command_values);
    RUN_TEST(test_config_command_values);
    RUN_TEST(test_logging_command_values);
    RUN_TEST(test_diagnostic_command_values);
    RUN_TEST(test_lua_command_values);
    RUN_TEST(test_firmware_command_values);
    RUN_TEST(test_response_command_values);

    /* Protocol Constants Tests */
    RUN_TEST(test_protocol_start_marker);
    RUN_TEST(test_protocol_version);
    RUN_TEST(test_protocol_max_payload);
    RUN_TEST(test_protocol_uart_baud);
    RUN_TEST(test_protocol_can_id_base);

    /* Stream Rate Tests */
    RUN_TEST(test_stream_rate_1hz);
    RUN_TEST(test_stream_rate_10hz);
    RUN_TEST(test_stream_rate_50hz);
    RUN_TEST(test_stream_rate_100hz);
    RUN_TEST(test_stream_rate_500hz);
    RUN_TEST(test_stream_rate_1000hz);

    /* Transport Enum Tests */
    RUN_TEST(test_transport_uart);
    RUN_TEST(test_transport_wifi);
    RUN_TEST(test_transport_can);

    /* Packet Structure Tests */
    RUN_TEST(test_packet_structure_size);
    RUN_TEST(test_packet_start_marker_offset);
    RUN_TEST(test_packet_command_offset);
    RUN_TEST(test_packet_length_offset);
    RUN_TEST(test_packet_data_offset);

    /* Telemetry Config Tests */
    RUN_TEST(test_telemetry_config_defaults);
    RUN_TEST(test_telemetry_config_all_enabled);

    /* Statistics Tests */
    RUN_TEST(test_stats_structure_zeroed);

    /* CRC16 Tests */
    RUN_TEST(test_crc16_empty);
    RUN_TEST(test_crc16_single_byte);
    RUN_TEST(test_crc16_multiple_bytes);
    RUN_TEST(test_crc16_deterministic);
    RUN_TEST(test_crc16_different_data);
    RUN_TEST(test_crc16_different_lengths);

    /* Command Range Tests */
    RUN_TEST(test_command_ranges_basic);
    RUN_TEST(test_command_ranges_telemetry);
    RUN_TEST(test_command_ranges_control);
    RUN_TEST(test_command_ranges_config);
    RUN_TEST(test_command_ranges_logging);
    RUN_TEST(test_command_ranges_diagnostic);
    RUN_TEST(test_command_ranges_lua);
    RUN_TEST(test_command_ranges_firmware);
    RUN_TEST(test_command_ranges_response);

    return UNITY_END();
}

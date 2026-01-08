/**
 * @file telemetry.h
 * @brief Telemetry data structures for PMU-30
 *
 * Matches firmware telemetry format from pmu_serial_transfer_port.c
 */
#pragma once

#include <stdint.h>

// =============================================================================
// Telemetry Packet Structure
// =============================================================================

#pragma pack(push, 1)

/**
 * @brief PMU-30 Telemetry packet (fixed portion: 104 bytes)
 */
typedef struct {
    // Stream info (8 bytes)
    uint32_t stream_counter;    // Offset 0
    uint32_t timestamp_ms;      // Offset 4

    // Output states (30 bytes)
    uint8_t output_states[30];  // Offset 8: 0=off, 1=on, 2=fault

    // ADC values (40 bytes)
    uint16_t adc_values[20];    // Offset 38: Raw ADC readings

    // Digital inputs (1 byte)
    uint8_t digital_inputs;     // Offset 78: Bit mask (8 inputs)

    // System info (15 bytes)
    uint32_t uptime_sec;        // Offset 79
    uint8_t debug_rx_count;     // Offset 83
    uint8_t debug_last_cmd;     // Offset 84
    uint8_t reserved1[6];       // Offset 85
    uint16_t channel_count;     // Offset 91
    uint8_t reserved2;          // Offset 93

    // GPIO debug (10 bytes)
    uint16_t gpioc_idr;         // Offset 94
    uint8_t din0_state;         // Offset 96
    uint8_t gpio_pin13;         // Offset 97
    uint8_t reserved3[6];       // Offset 98

    // Virtual channels count (2 bytes)
    uint16_t virtual_count;     // Offset 104

    // Variable-length virtual channels follow:
    // [channel_id (2) + value (4)] × virtual_count
} TelemetryPacket_t;

/**
 * @brief Virtual channel entry
 */
typedef struct {
    uint16_t channel_id;
    int32_t value;
} VirtualChannel_t;

#pragma pack(pop)

// =============================================================================
// Display Data (processed for UI)
// =============================================================================

/**
 * @brief Processed telemetry for display
 */
typedef struct {
    // Connection status
    bool connected;
    uint32_t last_packet_time;

    // Stream info
    uint32_t stream_counter;
    uint32_t uptime_sec;

    // Output states (boolean)
    bool outputs[30];
    uint8_t output_faults;  // Bitmask of faulted outputs

    // Digital inputs (boolean)
    bool inputs[8];

    // Analog values (converted)
    float voltage_v;        // System voltage
    float current_a;        // System current
    float mcu_temp_c;       // MCU temperature
    float board_temp_c;     // Board temperature

    // Faults
    uint8_t fault_status;
    uint8_t fault_flags;

    // Virtual channels (for advanced display)
    uint16_t virtual_count;
    VirtualChannel_t virtuals[16];  // Max displayed virtuals
} DisplayData_t;

// =============================================================================
// Functions
// =============================================================================

/**
 * @brief Parse raw telemetry packet into display data
 * @param raw Raw packet payload (after SerialTransfer decode)
 * @param len Payload length
 * @param out Output display data structure
 * @return true if parsing successful
 */
bool Telemetry_Parse(const uint8_t* raw, uint16_t len, DisplayData_t* out);

/**
 * @brief Get output state color for display
 * @param state Output state (0=off, 1=on, 2=fault)
 * @return Color in RGB565 format
 */
uint16_t Telemetry_GetOutputColor(uint8_t state);

/**
 * @brief Get input state color for display
 * @param state Input state (0=low, 1=high)
 * @return Color in RGB565 format
 */
uint16_t Telemetry_GetInputColor(bool state);

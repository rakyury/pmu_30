/**
 * @file telemetry.cpp
 * @brief Telemetry parsing implementation
 */

#include "telemetry.h"
#include <string.h>

// RGB565 colors
#define COLOR_RED     0xF800
#define COLOR_GREEN   0x07E0
#define COLOR_YELLOW  0xFFE0
#define COLOR_CYAN    0x07FF
#define COLOR_GREY    0x4208

bool Telemetry_Parse(const uint8_t* raw, uint16_t len, DisplayData_t* out)
{
    if (len < 106 || !raw || !out) return false;

    // Cast to packet structure for easy access
    const TelemetryPacket_t* pkt = (const TelemetryPacket_t*)raw;

    // Stream info
    out->stream_counter = pkt->stream_counter;
    out->uptime_sec = pkt->uptime_sec;

    // Output states
    for (int i = 0; i < 30; i++) {
        out->outputs[i] = (pkt->output_states[i] == 1);
    }
    out->output_faults = 0;
    for (int i = 0; i < 8; i++) {
        if (pkt->output_states[i] == 2) {
            out->output_faults |= (1 << i);
        }
    }

    // Digital inputs (bitmask)
    for (int i = 0; i < 8; i++) {
        out->inputs[i] = (pkt->digital_inputs & (1 << i)) != 0;
    }

    // ADC values (placeholder conversions)
    // In real PMU-30, these would be calibrated values
    out->voltage_v = pkt->adc_values[0] * 0.01f;     // Placeholder
    out->current_a = pkt->adc_values[1] * 0.001f;   // Placeholder
    out->mcu_temp_c = 25.0f;                        // Placeholder
    out->board_temp_c = 25.0f;                      // Placeholder

    // Virtual channels
    out->virtual_count = pkt->virtual_count;
    if (out->virtual_count > 16) out->virtual_count = 16;

    // Parse virtual channel data (follows fixed portion at offset 106)
    if (len > 106 && out->virtual_count > 0) {
        const uint8_t* vch_data = raw + 106;
        uint16_t remaining = len - 106;

        for (int i = 0; i < out->virtual_count && remaining >= 6; i++) {
            out->virtuals[i].channel_id = vch_data[0] | (vch_data[1] << 8);
            out->virtuals[i].value = vch_data[2] | (vch_data[3] << 8) |
                                     (vch_data[4] << 16) | (vch_data[5] << 24);
            vch_data += 6;
            remaining -= 6;
        }
    }

    return true;
}

uint16_t Telemetry_GetOutputColor(uint8_t state)
{
    switch (state) {
        case 0: return COLOR_GREY;   // Off
        case 1: return COLOR_GREEN;  // On
        case 2: return COLOR_RED;    // Fault
        default: return COLOR_YELLOW;
    }
}

uint16_t Telemetry_GetInputColor(bool state)
{
    return state ? COLOR_CYAN : COLOR_GREY;
}

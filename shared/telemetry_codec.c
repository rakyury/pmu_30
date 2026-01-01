/**
 * @file telemetry_codec.c
 * @brief PMU-30 Telemetry Codec Implementation
 *
 * @version 1.0
 * @date January 2026
 */

#include "telemetry_codec.h"
#include <string.h>

/*============================================================================
 * Section Size Constants
 *============================================================================*/

#define HEADER_SIZE         sizeof(TelemetryHeader_t)       /* 20 bytes */
#define ADC_SIZE            sizeof(TelemetryADC_t)          /* 40 bytes */
#define OUTPUTS_SIZE        sizeof(TelemetryOutputs_t)      /* 30 bytes */
#define DIN_SIZE            sizeof(TelemetryDIN_t)          /* 4 bytes */
#define FAULTS_SIZE         sizeof(TelemetryFaults_t)       /* 4 bytes */
#define CURRENTS_SIZE       sizeof(TelemetryCurrents_t)     /* 60 bytes */
#define HBRIDGE_SIZE        sizeof(TelemetryHBridge_t)      /* 16 bytes */
#define VIRTUAL_ENTRY_SIZE  sizeof(VirtualChannelEntry_t)   /* 6 bytes */

/*============================================================================
 * Helper: Read values from buffer (handles alignment)
 *============================================================================*/

static inline uint16_t read_u16(const uint8_t* p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static inline uint32_t read_u32(const uint8_t* p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static inline int16_t read_i16(const uint8_t* p) {
    return (int16_t)read_u16(p);
}

static inline int32_t read_i32(const uint8_t* p) {
    return (int32_t)read_u32(p);
}

/*============================================================================
 * Telemetry_GetMinSize
 *============================================================================*/

size_t Telemetry_GetMinSize(uint16_t flags)
{
    size_t size = HEADER_SIZE;

    if (flags & TELEM_HAS_ADC)      size += ADC_SIZE;
    if (flags & TELEM_HAS_OUTPUTS)  size += OUTPUTS_SIZE;
    if (flags & TELEM_HAS_HBRIDGE)  size += HBRIDGE_SIZE;
    if (flags & TELEM_HAS_DIN)      size += DIN_SIZE;
    if (flags & TELEM_HAS_VIRTUALS) size += 2;  /* At least count field */
    if (flags & TELEM_HAS_FAULTS)   size += FAULTS_SIZE;
    if (flags & TELEM_HAS_CURRENTS) size += CURRENTS_SIZE;

    return size;
}

/*============================================================================
 * Telemetry_Parse
 *============================================================================*/

TelemetryResult_t Telemetry_Parse(
    const uint8_t* data,
    size_t size,
    TelemetryPacket_t* out)
{
    if (!data || !out) {
        return TELEM_ERR_NULL_PARAM;
    }

    /* Clear output */
    memset(out, 0, sizeof(TelemetryPacket_t));

    /* Check minimum size for header */
    if (size < HEADER_SIZE) {
        return TELEM_ERR_TOO_SHORT;
    }

    /* Parse header */
    size_t idx = 0;
    out->header.stream_counter = read_u32(&data[idx]); idx += 4;
    out->header.timestamp_ms   = read_u32(&data[idx]); idx += 4;
    out->header.input_voltage_mv = read_u16(&data[idx]); idx += 2;
    out->header.mcu_temp_c10   = read_i16(&data[idx]); idx += 2;
    out->header.board_temp_c10 = read_i16(&data[idx]); idx += 2;
    out->header.total_current_ma = read_u32(&data[idx]); idx += 4;
    out->header.flags          = read_u16(&data[idx]); idx += 2;

    uint16_t flags = out->header.flags;

    /* Check we have enough data for all sections */
    if (size < Telemetry_GetMinSize(flags)) {
        return TELEM_ERR_TOO_SHORT;
    }

    /* Parse ADC section */
    if (flags & TELEM_HAS_ADC) {
        if (idx + ADC_SIZE > size) return TELEM_ERR_TRUNCATED;
        for (int i = 0; i < TELEM_ADC_COUNT; i++) {
            out->adc.values[i] = read_u16(&data[idx]);
            idx += 2;
        }
    }

    /* Parse Outputs section */
    if (flags & TELEM_HAS_OUTPUTS) {
        if (idx + OUTPUTS_SIZE > size) return TELEM_ERR_TRUNCATED;
        memcpy(out->outputs.states, &data[idx], OUTPUTS_SIZE);
        idx += OUTPUTS_SIZE;
    }

    /* Parse H-Bridge section */
    if (flags & TELEM_HAS_HBRIDGE) {
        if (idx + HBRIDGE_SIZE > size) return TELEM_ERR_TRUNCATED;
        for (int i = 0; i < TELEM_HBRIDGE_COUNT; i++) {
            out->hbridge.position[i] = read_i16(&data[idx]);
            idx += 2;
        }
        for (int i = 0; i < TELEM_HBRIDGE_COUNT; i++) {
            out->hbridge.current[i] = read_u16(&data[idx]);
            idx += 2;
        }
    }

    /* Parse Digital Inputs section */
    if (flags & TELEM_HAS_DIN) {
        if (idx + DIN_SIZE > size) return TELEM_ERR_TRUNCATED;
        out->din.bitmask = read_u32(&data[idx]);
        idx += DIN_SIZE;
    }

    /* Parse Virtual Channels section */
    if (flags & TELEM_HAS_VIRTUALS) {
        if (idx + 2 > size) return TELEM_ERR_TRUNCATED;
        uint16_t count = read_u16(&data[idx]);
        idx += 2;

        if (count > TELEM_VIRTUAL_MAX) {
            count = TELEM_VIRTUAL_MAX;  /* Truncate to max */
        }

        out->virtuals.count = count;

        for (uint16_t i = 0; i < count; i++) {
            if (idx + VIRTUAL_ENTRY_SIZE > size) return TELEM_ERR_TRUNCATED;
            out->virtuals.entries[i].channel_id = read_u16(&data[idx]);
            idx += 2;
            out->virtuals.entries[i].value = read_i32(&data[idx]);
            idx += 4;
        }
    }

    /* Parse Faults section */
    if (flags & TELEM_HAS_FAULTS) {
        if (idx + FAULTS_SIZE > size) return TELEM_ERR_TRUNCATED;
        out->faults.status = data[idx++];
        out->faults.fault_flags = data[idx++];
        out->faults.reserved = read_u16(&data[idx]);
        idx += 2;
    }

    /* Parse Currents section */
    if (flags & TELEM_HAS_CURRENTS) {
        if (idx + CURRENTS_SIZE > size) return TELEM_ERR_TRUNCATED;
        for (int i = 0; i < TELEM_OUTPUT_COUNT; i++) {
            out->currents.currents[i] = read_u16(&data[idx]);
            idx += 2;
        }
    }

    return TELEM_OK;
}

/*============================================================================
 * Telemetry_GetVirtualValue
 *============================================================================*/

bool Telemetry_GetVirtualValue(
    const TelemetryPacket_t* packet,
    uint16_t channel_id,
    int32_t* value)
{
    if (!packet || !value) {
        return false;
    }

    if (!(packet->header.flags & TELEM_HAS_VIRTUALS)) {
        return false;
    }

    for (uint16_t i = 0; i < packet->virtuals.count; i++) {
        if (packet->virtuals.entries[i].channel_id == channel_id) {
            *value = packet->virtuals.entries[i].value;
            return true;
        }
    }

    return false;
}

/*============================================================================
 * Build Functions (firmware-side only)
 *============================================================================*/

#ifdef PMU_PLATFORM_EMBEDDED

/* Storage for virtual channel data to include in next build */
static uint16_t g_virtual_ids[TELEM_VIRTUAL_MAX];
static int32_t g_virtual_values[TELEM_VIRTUAL_MAX];
static uint16_t g_virtual_count = 0;

void Telemetry_SetVirtuals(
    const uint16_t* ids,
    const int32_t* values,
    uint16_t count)
{
    if (count > TELEM_VIRTUAL_MAX) {
        count = TELEM_VIRTUAL_MAX;
    }

    g_virtual_count = count;
    if (ids && values && count > 0) {
        memcpy(g_virtual_ids, ids, count * sizeof(uint16_t));
        memcpy(g_virtual_values, values, count * sizeof(int32_t));
    }
}

/* Helper: Write values to buffer */
static inline void write_u16(uint8_t* p, uint16_t v) {
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
}

static inline void write_u32(uint8_t* p, uint32_t v) {
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
    p[2] = (uint8_t)((v >> 16) & 0xFF);
    p[3] = (uint8_t)((v >> 24) & 0xFF);
}

static inline void write_i16(uint8_t* p, int16_t v) {
    write_u16(p, (uint16_t)v);
}

static inline void write_i32(uint8_t* p, int32_t v) {
    write_u32(p, (uint32_t)v);
}

size_t Telemetry_Build(
    uint8_t* buffer,
    size_t max_size,
    const TelemetryBuildConfig_t* config)
{
    if (!buffer || !config) {
        return 0;
    }

    /* Calculate flags based on config */
    uint16_t flags = 0;
    if (config->include_adc)      flags |= TELEM_HAS_ADC;
    if (config->include_outputs)  flags |= TELEM_HAS_OUTPUTS;
    if (config->include_hbridge)  flags |= TELEM_HAS_HBRIDGE;
    if (config->include_din)      flags |= TELEM_HAS_DIN;
    if (config->include_virtuals && g_virtual_count > 0) flags |= TELEM_HAS_VIRTUALS;
    if (config->include_faults)   flags |= TELEM_HAS_FAULTS;
    if (config->include_currents) flags |= TELEM_HAS_CURRENTS;

    /* Calculate required size */
    size_t required = Telemetry_GetMinSize(flags);
    if (flags & TELEM_HAS_VIRTUALS) {
        required += g_virtual_count * VIRTUAL_ENTRY_SIZE;
    }

    if (max_size < required) {
        return 0;
    }

    size_t idx = 0;

    /* Write header - placeholder values, caller should fill in */
    write_u32(&buffer[idx], 0);  idx += 4;  /* stream_counter */
    write_u32(&buffer[idx], 0);  idx += 4;  /* timestamp_ms */
    write_u16(&buffer[idx], 0);  idx += 2;  /* input_voltage_mv */
    write_i16(&buffer[idx], 0);  idx += 2;  /* mcu_temp_c10 */
    write_i16(&buffer[idx], 0);  idx += 2;  /* board_temp_c10 */
    write_u32(&buffer[idx], 0);  idx += 4;  /* total_current_ma */
    write_u16(&buffer[idx], flags); idx += 2;  /* flags */

    /* ADC section - placeholder */
    if (flags & TELEM_HAS_ADC) {
        memset(&buffer[idx], 0, ADC_SIZE);
        idx += ADC_SIZE;
    }

    /* Outputs section - placeholder */
    if (flags & TELEM_HAS_OUTPUTS) {
        memset(&buffer[idx], 0, OUTPUTS_SIZE);
        idx += OUTPUTS_SIZE;
    }

    /* H-Bridge section - placeholder */
    if (flags & TELEM_HAS_HBRIDGE) {
        memset(&buffer[idx], 0, HBRIDGE_SIZE);
        idx += HBRIDGE_SIZE;
    }

    /* Digital inputs section - placeholder */
    if (flags & TELEM_HAS_DIN) {
        write_u32(&buffer[idx], 0);
        idx += DIN_SIZE;
    }

    /* Virtual channels section */
    if (flags & TELEM_HAS_VIRTUALS) {
        write_u16(&buffer[idx], g_virtual_count);
        idx += 2;

        for (uint16_t i = 0; i < g_virtual_count; i++) {
            write_u16(&buffer[idx], g_virtual_ids[i]);
            idx += 2;
            write_i32(&buffer[idx], g_virtual_values[i]);
            idx += 4;
        }
    }

    /* Faults section - placeholder */
    if (flags & TELEM_HAS_FAULTS) {
        memset(&buffer[idx], 0, FAULTS_SIZE);
        idx += FAULTS_SIZE;
    }

    /* Currents section - placeholder */
    if (flags & TELEM_HAS_CURRENTS) {
        memset(&buffer[idx], 0, CURRENTS_SIZE);
        idx += CURRENTS_SIZE;
    }

    return idx;
}

#endif /* PMU_PLATFORM_EMBEDDED */

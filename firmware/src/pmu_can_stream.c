/**
 ******************************************************************************
 * @file           : pmu_can_stream.c
 * @brief          : Standard CAN Stream Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Implements Ecumaster-compatible Standard CAN Stream for real-time
 * monitoring of PMU parameters over CAN bus.
 *
 * Frame Structure (8 standard + 8 extended):
 *   BaseID+0:  System Status & Temperatures (20 Hz)
 *   BaseID+1:  Output States o1-o16 (20 Hz)
 *   BaseID+2:  Analog Inputs a1-a8 (62.5 Hz)
 *   BaseID+3:  Analog Inputs a9-a16 (62.5 Hz)
 *   BaseID+4:  Output Currents o1-o8 (20 Hz)
 *   BaseID+5:  Output Currents o9-o16 (20 Hz)
 *   BaseID+6:  Output Voltages o1-o8 (20 Hz)
 *   BaseID+7:  Output Voltages o9-o16 (20 Hz)
 *   BaseID+8:  Output States o17-o30 (20 Hz) [Extended]
 *   BaseID+9:  Output Currents o17-o24 (20 Hz) [Extended]
 *   BaseID+10: Output Currents o25-o30 + reserved (20 Hz) [Extended]
 *   BaseID+11: Output Voltages o17-o24 (20 Hz) [Extended]
 *   BaseID+12: Output Voltages o25-o30 + reserved (20 Hz) [Extended]
 *   BaseID+13: Analog Inputs a17-a20 (62.5 Hz) [Extended]
 *   BaseID+14: Digital Inputs (20 Hz) [Extended]
 *   BaseID+15: H-Bridge Status (20 Hz) [Extended]
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_can_stream.h"
#include "pmu_can.h"
#include "pmu_profet.h"
#include "pmu_adc.h"
#include "pmu_hbridge.h"
#include "pmu_protection.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/** System tick period in ms (assumed 1ms SysTick) */
#define STREAM_TICK_PERIOD_MS       1

/** Number of low-side outputs */
#define LOWSIDE_COUNT               6

/** Number of digital inputs */
#define DIGITAL_INPUT_COUNT         8

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/

/** Stream runtime state */
static PMU_CanStreamState_t stream_state;

/** Last system tick value */
static uint32_t last_tick_ms = 0;

/* Private function prototypes -----------------------------------------------*/
static void BuildFrame0_SystemStatus(uint8_t *data);
static void BuildFrame1_OutputStates(uint8_t *data);
static void BuildFrame2_AnalogInputs1(uint8_t *data);
static void BuildFrame3_AnalogInputs2(uint8_t *data);
static void BuildFrame4_OutputCurrents1(uint8_t *data);
static void BuildFrame5_OutputCurrents2(uint8_t *data);
static void BuildFrame6_OutputVoltages1(uint8_t *data);
static void BuildFrame7_OutputVoltages2(uint8_t *data);
static void BuildFrame8_OutputStatesExt(uint8_t *data);
static void BuildFrame9_OutputCurrents3(uint8_t *data);
static void BuildFrame10_OutputCurrents4(uint8_t *data);
static void BuildFrame11_OutputVoltages3(uint8_t *data);
static void BuildFrame12_OutputVoltages4(uint8_t *data);
static void BuildFrame13_AnalogInputs3(uint8_t *data);
static void BuildFrame14_DigitalInputs(uint8_t *data);
static void BuildFrame15_HBridgeStatus(uint8_t *data);

static HAL_StatusTypeDef SendStreamFrame(uint8_t frame_offset, uint8_t *data);
static PMU_OutputStatus_t GetOutputStatus(uint8_t channel);
static PMU_StreamStatus_t GetSystemStatus(void);
static uint8_t GetTotalCurrent(void);
static uint8_t GetBatteryVoltageRaw(void);
static uint8_t GetBoardTempLeft(void);
static uint8_t GetBoardTempRight(void);
static uint8_t GetMcuTemperature(void);
static uint8_t GetOutputVoltageRaw(uint8_t channel);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief Initialize Standard CAN Stream
 * @param config Configuration structure
 * @return 0 on success, error code on failure
 */
int PMU_CanStream_Init(const PMU_CanStreamConfig_t *config)
{
    if (config == NULL) {
        return -1;
    }

    /* Clear state */
    memset(&stream_state, 0, sizeof(PMU_CanStreamState_t));

    /* Copy configuration */
    memcpy(&stream_state.config, config, sizeof(PMU_CanStreamConfig_t));

    /* Initialize timers */
    stream_state.timer_20hz = 0;
    stream_state.timer_62hz = 0;
    stream_state.frame_sequence = 0;
    stream_state.frames_sent = 0;
    stream_state.errors = 0;
    stream_state.initialized = true;

    return 0;
}

/**
 * @brief Deinitialize Standard CAN Stream
 */
void PMU_CanStream_Deinit(void)
{
    stream_state.initialized = false;
    stream_state.config.enabled = false;
}

/**
 * @brief Enable/disable the stream
 * @param enabled true to enable, false to disable
 */
void PMU_CanStream_SetEnabled(bool enabled)
{
    stream_state.config.enabled = enabled;

    /* Reset timers when enabling */
    if (enabled) {
        stream_state.timer_20hz = 0;
        stream_state.timer_62hz = 0;
        stream_state.frame_sequence = 0;
    }
}

/**
 * @brief Check if stream is enabled
 * @return true if enabled
 */
bool PMU_CanStream_IsEnabled(void)
{
    return stream_state.config.enabled && stream_state.initialized;
}

/**
 * @brief Process stream (call from main loop or timer)
 *
 * This function handles frame timing and transmission.
 * Should be called frequently (at least every 1ms).
 */
void PMU_CanStream_Process(void)
{
    if (!stream_state.initialized || !stream_state.config.enabled) {
        return;
    }

    /* Get current tick (assuming HAL_GetTick() returns ms) */
    uint32_t current_tick = HAL_GetTick();
    uint32_t elapsed = current_tick - last_tick_ms;
    last_tick_ms = current_tick;

    /* Update timers */
    stream_state.timer_20hz += elapsed;
    stream_state.timer_62hz += elapsed;

    uint8_t frame_data[8];

    /* ========================================================================
     * 62.5 Hz Frames (16ms period) - Analog Inputs
     * ======================================================================== */
    if (stream_state.timer_62hz >= PMU_CAN_STREAM_RATE_62HZ) {
        stream_state.timer_62hz = 0;

        /* Frame 2: Analog Inputs a1-a8 */
        BuildFrame2_AnalogInputs1(frame_data);
        SendStreamFrame(2, frame_data);

        /* Frame 3: Analog Inputs a9-a16 */
        BuildFrame3_AnalogInputs2(frame_data);
        SendStreamFrame(3, frame_data);

        /* Extended: Frame 13: Analog Inputs a17-a20 */
        if (stream_state.config.include_extended) {
            BuildFrame13_AnalogInputs3(frame_data);
            SendStreamFrame(13, frame_data);
        }
    }

    /* ========================================================================
     * 20 Hz Frames (50ms period) - Status, States, Currents, Voltages
     * ======================================================================== */
    if (stream_state.timer_20hz >= PMU_CAN_STREAM_RATE_20HZ) {
        stream_state.timer_20hz = 0;

        /* Frame 0: System Status */
        BuildFrame0_SystemStatus(frame_data);
        SendStreamFrame(0, frame_data);

        /* Frame 1: Output States o1-o16 */
        BuildFrame1_OutputStates(frame_data);
        SendStreamFrame(1, frame_data);

        /* Frame 4: Output Currents o1-o8 */
        BuildFrame4_OutputCurrents1(frame_data);
        SendStreamFrame(4, frame_data);

        /* Frame 5: Output Currents o9-o16 */
        BuildFrame5_OutputCurrents2(frame_data);
        SendStreamFrame(5, frame_data);

        /* Frame 6: Output Voltages o1-o8 */
        BuildFrame6_OutputVoltages1(frame_data);
        SendStreamFrame(6, frame_data);

        /* Frame 7: Output Voltages o9-o16 */
        BuildFrame7_OutputVoltages2(frame_data);
        SendStreamFrame(7, frame_data);

        /* Extended frames (8-15) */
        if (stream_state.config.include_extended) {
            /* Frame 8: Output States o17-o30 */
            BuildFrame8_OutputStatesExt(frame_data);
            SendStreamFrame(8, frame_data);

            /* Frame 9: Output Currents o17-o24 */
            BuildFrame9_OutputCurrents3(frame_data);
            SendStreamFrame(9, frame_data);

            /* Frame 10: Output Currents o25-o30 */
            BuildFrame10_OutputCurrents4(frame_data);
            SendStreamFrame(10, frame_data);

            /* Frame 11: Output Voltages o17-o24 */
            BuildFrame11_OutputVoltages3(frame_data);
            SendStreamFrame(11, frame_data);

            /* Frame 12: Output Voltages o25-o30 */
            BuildFrame12_OutputVoltages4(frame_data);
            SendStreamFrame(12, frame_data);

            /* Frame 14: Digital Inputs */
            BuildFrame14_DigitalInputs(frame_data);
            SendStreamFrame(14, frame_data);

            /* Frame 15: H-Bridge Status */
            BuildFrame15_HBridgeStatus(frame_data);
            SendStreamFrame(15, frame_data);
        }
    }
}

/**
 * @brief Update configuration
 * @param config New configuration
 * @return 0 on success, error code on failure
 */
int PMU_CanStream_Configure(const PMU_CanStreamConfig_t *config)
{
    if (config == NULL) {
        return -1;
    }

    memcpy(&stream_state.config, config, sizeof(PMU_CanStreamConfig_t));
    return 0;
}

/**
 * @brief Get current configuration
 * @param config Output configuration structure
 */
void PMU_CanStream_GetConfig(PMU_CanStreamConfig_t *config)
{
    if (config != NULL) {
        memcpy(config, &stream_state.config, sizeof(PMU_CanStreamConfig_t));
    }
}

/**
 * @brief Get stream statistics
 * @param frames_sent Output: total frames sent
 * @param errors Output: transmission errors
 */
void PMU_CanStream_GetStats(uint32_t *frames_sent, uint32_t *errors)
{
    if (frames_sent != NULL) {
        *frames_sent = stream_state.frames_sent;
    }
    if (errors != NULL) {
        *errors = stream_state.errors;
    }
}

/**
 * @brief Reset statistics counters
 */
void PMU_CanStream_ResetStats(void)
{
    stream_state.frames_sent = 0;
    stream_state.errors = 0;
}

/* ============================================================================
 * Frame Building Functions
 * ============================================================================ */

/**
 * @brief Build Frame 0: System Status & Temperatures
 *
 * Byte 0: Status flags (bits 0-2: status, bit 3: user_error)
 * Byte 1: Total current (1 A/bit)
 * Byte 2: Battery voltage (0.1088 V/bit)
 * Byte 3: Left board temperature (1 °C/bit)
 * Byte 4: Right board temperature (1 °C/bit)
 * Byte 5: MCU temperature (1 °C/bit)
 * Byte 6: Low-side active flags (bits 0-5)
 * Byte 7: Low-side error flags (bits 0-5)
 */
static void BuildFrame0_SystemStatus(uint8_t *data)
{
    memset(data, 0, 8);

    /* Byte 0: Status */
    PMU_StreamStatus_t status = GetSystemStatus();
    data[0] = (uint8_t)status & PMU_STREAM_STATUS_MASK;
    /* TODO: Add user error flag if needed */

    /* Byte 1: Total current (1 A/bit) */
    data[1] = GetTotalCurrent();

    /* Byte 2: Battery voltage (0.1088 V/bit) */
    data[2] = GetBatteryVoltageRaw();

    /* Byte 3: Left board temperature */
    data[3] = GetBoardTempLeft();

    /* Byte 4: Right board temperature */
    data[4] = GetBoardTempRight();

    /* Byte 5: MCU temperature */
    data[5] = GetMcuTemperature();

    /* Byte 6-7: Low-side active/error flags */
    uint8_t lowside_active = 0;
    uint8_t lowside_error = 0;

    for (uint8_t i = 0; i < LOWSIDE_COUNT; i++) {
        PMU_PROFET_Channel_t *ch = PMU_PROFET_GetChannelData(24 + i); /* Low-side outputs 25-30 */
        if (ch != NULL) {
            if (ch->state == PMU_PROFET_STATE_ON || ch->state == PMU_PROFET_STATE_PWM) {
                lowside_active |= (1 << i);
            }
            if (ch->fault_flags != PMU_PROFET_FAULT_NONE) {
                lowside_error |= (1 << i);
            }
        }
    }

    data[6] = lowside_active;
    data[7] = lowside_error;
}

/**
 * @brief Build Frame 1: Output States o1-o16
 *
 * Each byte contains 2 outputs:
 * High nibble: odd output (bits 5-7: status, bit 4: active)
 * Low nibble: even output (bits 1-3: status, bit 0: active)
 */
static void BuildFrame1_OutputStates(uint8_t *data)
{
    memset(data, 0, 8);

    for (uint8_t i = 0; i < 8; i++) {
        uint8_t odd_ch = i * 2;       /* o1, o3, o5, ... */
        uint8_t even_ch = i * 2 + 1;  /* o2, o4, o6, ... */

        PMU_OutputStatus_t odd_status = GetOutputStatus(odd_ch);
        PMU_OutputStatus_t even_status = GetOutputStatus(even_ch);

        PMU_PROFET_Channel_t *odd_data = PMU_PROFET_GetChannelData(odd_ch);
        PMU_PROFET_Channel_t *even_data = PMU_PROFET_GetChannelData(even_ch);

        bool odd_active = (odd_data != NULL &&
                          (odd_data->state == PMU_PROFET_STATE_ON ||
                           odd_data->state == PMU_PROFET_STATE_PWM));
        bool even_active = (even_data != NULL &&
                           (even_data->state == PMU_PROFET_STATE_ON ||
                            even_data->state == PMU_PROFET_STATE_PWM));

        data[i] = PMU_CanStream_PackOutputState(odd_status, odd_active,
                                                  even_status, even_active);
    }
}

/**
 * @brief Build Frame 2: Analog Inputs a1-a8
 *
 * 8 bytes: analog input voltages (0.0196 V/bit)
 */
static void BuildFrame2_AnalogInputs1(uint8_t *data)
{
    for (uint8_t i = 0; i < 8; i++) {
        float voltage = PMU_ADC_GetScaledValue(i);
        /* Clamp to 0-5V range */
        if (voltage < 0.0f) voltage = 0.0f;
        if (voltage > 5.0f) voltage = 5.0f;
        data[i] = PMU_STREAM_AIN_TO_RAW(voltage);
    }
}

/**
 * @brief Build Frame 3: Analog Inputs a9-a16
 */
static void BuildFrame3_AnalogInputs2(uint8_t *data)
{
    for (uint8_t i = 0; i < 8; i++) {
        float voltage = PMU_ADC_GetScaledValue(8 + i);
        if (voltage < 0.0f) voltage = 0.0f;
        if (voltage > 5.0f) voltage = 5.0f;
        data[i] = PMU_STREAM_AIN_TO_RAW(voltage);
    }
}

/**
 * @brief Build Frame 4: Output Currents o1-o8
 *
 * 8 bytes: output currents (0.25 A/bit)
 */
static void BuildFrame4_OutputCurrents1(uint8_t *data)
{
    for (uint8_t i = 0; i < 8; i++) {
        uint16_t current_mA = PMU_PROFET_GetCurrent(i);
        float current_A = (float)current_mA / 1000.0f;
        data[i] = PMU_STREAM_CURRENT_TO_RAW(current_A);
    }
}

/**
 * @brief Build Frame 5: Output Currents o9-o16
 */
static void BuildFrame5_OutputCurrents2(uint8_t *data)
{
    for (uint8_t i = 0; i < 8; i++) {
        uint16_t current_mA = PMU_PROFET_GetCurrent(8 + i);
        float current_A = (float)current_mA / 1000.0f;
        data[i] = PMU_STREAM_CURRENT_TO_RAW(current_A);
    }
}

/**
 * @brief Build Frame 6: Output Voltages o1-o8
 *
 * 8 bytes: output voltages (0.0635 V/bit)
 */
static void BuildFrame6_OutputVoltages1(uint8_t *data)
{
    for (uint8_t i = 0; i < 8; i++) {
        data[i] = GetOutputVoltageRaw(i);
    }
}

/**
 * @brief Build Frame 7: Output Voltages o9-o16
 */
static void BuildFrame7_OutputVoltages2(uint8_t *data)
{
    for (uint8_t i = 0; i < 8; i++) {
        data[i] = GetOutputVoltageRaw(8 + i);
    }
}

/**
 * @brief Build Frame 8: Output States o17-o30 (Extended)
 *
 * 7 bytes used for 14 outputs, byte 7 reserved
 */
static void BuildFrame8_OutputStatesExt(uint8_t *data)
{
    memset(data, 0, 8);

    for (uint8_t i = 0; i < 7; i++) {
        uint8_t odd_ch = 16 + i * 2;       /* o17, o19, o21, ... */
        uint8_t even_ch = 16 + i * 2 + 1;  /* o18, o20, o22, ... */

        /* Check bounds (we have outputs 17-30 = channels 16-29) */
        if (odd_ch >= 30) {
            data[i] = 0;
            continue;
        }

        PMU_OutputStatus_t odd_status = GetOutputStatus(odd_ch);
        PMU_OutputStatus_t even_status = (even_ch < 30) ? GetOutputStatus(even_ch) : PMU_OUTPUT_STATUS_OFF;

        PMU_PROFET_Channel_t *odd_data = PMU_PROFET_GetChannelData(odd_ch);
        PMU_PROFET_Channel_t *even_data = (even_ch < 30) ? PMU_PROFET_GetChannelData(even_ch) : NULL;

        bool odd_active = (odd_data != NULL &&
                          (odd_data->state == PMU_PROFET_STATE_ON ||
                           odd_data->state == PMU_PROFET_STATE_PWM));
        bool even_active = (even_data != NULL &&
                           (even_data->state == PMU_PROFET_STATE_ON ||
                            even_data->state == PMU_PROFET_STATE_PWM));

        data[i] = PMU_CanStream_PackOutputState(odd_status, odd_active,
                                                  even_status, even_active);
    }

    data[7] = 0; /* Reserved */
}

/**
 * @brief Build Frame 9: Output Currents o17-o24 (Extended)
 */
static void BuildFrame9_OutputCurrents3(uint8_t *data)
{
    for (uint8_t i = 0; i < 8; i++) {
        uint16_t current_mA = PMU_PROFET_GetCurrent(16 + i);
        float current_A = (float)current_mA / 1000.0f;
        data[i] = PMU_STREAM_CURRENT_TO_RAW(current_A);
    }
}

/**
 * @brief Build Frame 10: Output Currents o25-o30 + reserved (Extended)
 */
static void BuildFrame10_OutputCurrents4(uint8_t *data)
{
    memset(data, 0, 8);

    for (uint8_t i = 0; i < 6; i++) { /* Only 6 outputs: o25-o30 */
        uint16_t current_mA = PMU_PROFET_GetCurrent(24 + i);
        float current_A = (float)current_mA / 1000.0f;
        data[i] = PMU_STREAM_CURRENT_TO_RAW(current_A);
    }

    data[6] = 0; /* Reserved */
    data[7] = 0; /* Reserved */
}

/**
 * @brief Build Frame 11: Output Voltages o17-o24 (Extended)
 */
static void BuildFrame11_OutputVoltages3(uint8_t *data)
{
    for (uint8_t i = 0; i < 8; i++) {
        data[i] = GetOutputVoltageRaw(16 + i);
    }
}

/**
 * @brief Build Frame 12: Output Voltages o25-o30 + reserved (Extended)
 */
static void BuildFrame12_OutputVoltages4(uint8_t *data)
{
    memset(data, 0, 8);

    for (uint8_t i = 0; i < 6; i++) { /* Only 6 outputs: o25-o30 */
        data[i] = GetOutputVoltageRaw(24 + i);
    }

    data[6] = 0; /* Reserved */
    data[7] = 0; /* Reserved */
}

/**
 * @brief Build Frame 13: Analog Inputs a17-a20 (Extended)
 */
static void BuildFrame13_AnalogInputs3(uint8_t *data)
{
    memset(data, 0, 8);

    for (uint8_t i = 0; i < 4; i++) { /* Only 4 inputs: a17-a20 */
        float voltage = PMU_ADC_GetScaledValue(16 + i);
        if (voltage < 0.0f) voltage = 0.0f;
        if (voltage > 5.0f) voltage = 5.0f;
        data[i] = PMU_STREAM_AIN_TO_RAW(voltage);
    }

    /* Bytes 4-7: Reserved */
}

/**
 * @brief Build Frame 14: Digital Inputs (Extended)
 *
 * Byte 0: Digital input states (bits 0-7 for d1-d8)
 * Bytes 1-4: Frequency/pulse counters (optional)
 * Bytes 5-7: Reserved
 */
static void BuildFrame14_DigitalInputs(uint8_t *data)
{
    memset(data, 0, 8);

    /* Byte 0: Digital input states */
    uint8_t states = 0;
    for (uint8_t i = 0; i < DIGITAL_INPUT_COUNT; i++) {
        if (PMU_ADC_GetDigitalState(i)) {
            states |= (1 << i);
        }
    }
    data[0] = states;

    /* Bytes 1-4: Frequency counters for first 4 inputs (optional) */
    /* TODO: Implement frequency counter reporting if needed */

    /* Bytes 5-7: Reserved */
}

/**
 * @brief Build Frame 15: H-Bridge Status (Extended)
 *
 * For each H-Bridge (2 bytes each):
 * Byte 0: Status code (PMU_HBridgeStreamStatus_t)
 * Byte 1: Current (0.25 A/bit)
 */
static void BuildFrame15_HBridgeStatus(uint8_t *data)
{
    memset(data, 0, 8);

    for (uint8_t i = 0; i < 4; i++) {
        PMU_HBridge_Channel_t *hb = PMU_HBridge_GetChannelData(i);

        if (hb == NULL) {
            data[i * 2] = PMU_HBRIDGE_STATUS_IDLE;
            data[i * 2 + 1] = 0;
            continue;
        }

        /* Convert H-Bridge state to stream status */
        PMU_HBridgeStreamStatus_t status;

        if (hb->fault_flags & PMU_HBRIDGE_FAULT_OVERTEMP) {
            status = PMU_HBRIDGE_STATUS_THERMAL;
        } else if (hb->fault_flags & (PMU_HBRIDGE_FAULT_OVERCURRENT_FWD | PMU_HBRIDGE_FAULT_OVERCURRENT_REV)) {
            status = PMU_HBRIDGE_STATUS_OVERCURRENT;
        } else if (hb->fault_flags & PMU_HBRIDGE_FAULT_STALL) {
            status = PMU_HBRIDGE_STATUS_STALL;
        } else {
            switch (hb->mode) {
                case PMU_HBRIDGE_MODE_FORWARD:
                    status = PMU_HBRIDGE_STATUS_FORWARD;
                    break;
                case PMU_HBRIDGE_MODE_REVERSE:
                    status = PMU_HBRIDGE_STATUS_REVERSE;
                    break;
                case PMU_HBRIDGE_MODE_BRAKE:
                    status = PMU_HBRIDGE_STATUS_BRAKE;
                    break;
                case PMU_HBRIDGE_MODE_COAST:
                    status = PMU_HBRIDGE_STATUS_COAST;
                    break;
                default:
                    status = PMU_HBRIDGE_STATUS_IDLE;
                    break;
            }
        }

        data[i * 2] = (uint8_t)status;

        /* Current (0.25 A/bit) */
        float current_A = (float)hb->current_mA / 1000.0f;
        data[i * 2 + 1] = PMU_STREAM_CURRENT_TO_RAW(current_A);
    }
}

/* ============================================================================
 * Helper Functions
 * ============================================================================ */

/**
 * @brief Send a stream frame
 * @param frame_offset Offset from base ID (0-15)
 * @param data 8-byte frame data
 * @return HAL status
 */
static HAL_StatusTypeDef SendStreamFrame(uint8_t frame_offset, uint8_t *data)
{
    uint32_t can_id = stream_state.config.base_id + frame_offset;

    /* Convert bus number (1=CAN_A, 2=CAN_B) to enum */
    PMU_CAN_Bus_t bus = (stream_state.config.can_bus == 2) ? PMU_CAN_BUS_2 : PMU_CAN_BUS_1;

    PMU_CAN_Message_t msg;
    msg.id = can_id;
    msg.dlc = 8;
    msg.id_type = stream_state.config.is_extended ? PMU_CAN_ID_EXTENDED : PMU_CAN_ID_STANDARD;
    msg.frame_type = PMU_CAN_FRAME_CLASSIC;
    msg.rtr = 0;
    memcpy(msg.data, data, 8);

    HAL_StatusTypeDef result = PMU_CAN_SendMessage(bus, &msg);

    if (result == HAL_OK) {
        stream_state.frames_sent++;
    } else {
        stream_state.errors++;
    }

    return result;
}

/**
 * @brief Get output status for stream
 * @param channel Output channel (0-29)
 * @return Output status code
 */
static PMU_OutputStatus_t GetOutputStatus(uint8_t channel)
{
    PMU_PROFET_Channel_t *ch = PMU_PROFET_GetChannelData(channel);

    if (ch == NULL) {
        return PMU_OUTPUT_STATUS_OFF;
    }

    /* Check faults first */
    if (ch->fault_flags & PMU_PROFET_FAULT_OVERTEMP) {
        return PMU_OUTPUT_STATUS_THERMAL_SHUTDOWN;
    }
    if (ch->fault_flags & PMU_PROFET_FAULT_SHORT_CIRCUIT) {
        return PMU_OUTPUT_STATUS_SHORT_GND;
    }
    if (ch->fault_flags & PMU_PROFET_FAULT_OVERCURRENT) {
        return PMU_OUTPUT_STATUS_OVERCURRENT;
    }
    if (ch->fault_flags & PMU_PROFET_FAULT_OPEN_LOAD) {
        return PMU_OUTPUT_STATUS_OPEN_LOAD;
    }

    /* Check state */
    switch (ch->state) {
        case PMU_PROFET_STATE_ON:
        case PMU_PROFET_STATE_PWM:
            return PMU_OUTPUT_STATUS_ACTIVE;
        case PMU_PROFET_STATE_FAULT:
            return PMU_OUTPUT_STATUS_OVERCURRENT;
        default:
            return PMU_OUTPUT_STATUS_OFF;
    }
}

/**
 * @brief Get overall system status
 * @return System status code
 */
static PMU_StreamStatus_t GetSystemStatus(void)
{
    /* Check for thermal issues first (most critical) */
    uint8_t mcu_temp = GetMcuTemperature();
    if (mcu_temp > 100) {
        return PMU_STATUS_THERMAL_SHUTDOWN;
    }
    if (mcu_temp > 85) {
        return PMU_STATUS_OVERTEMP;
    }

    /* Check all outputs for faults */
    bool has_overcurrent = false;
    bool has_short = false;
    bool has_undercurrent = false;
    bool has_warning = false;

    for (uint8_t i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t *ch = PMU_PROFET_GetChannelData(i);
        if (ch == NULL) continue;

        if (ch->fault_flags & PMU_PROFET_FAULT_SHORT_CIRCUIT) {
            has_short = true;
        }
        if (ch->fault_flags & PMU_PROFET_FAULT_OVERCURRENT) {
            has_overcurrent = true;
        }
        if (ch->fault_flags & PMU_PROFET_FAULT_OPEN_LOAD) {
            has_undercurrent = true;
        }
        if (ch->fault_flags != PMU_PROFET_FAULT_NONE) {
            has_warning = true;
        }
    }

    /* Priority order */
    if (has_short) {
        return PMU_STATUS_SHORT_CIRCUIT;
    }
    if (has_overcurrent) {
        return PMU_STATUS_OVERCURRENT;
    }
    if (has_undercurrent) {
        return PMU_STATUS_UNDERCURRENT;
    }
    if (has_warning) {
        return PMU_STATUS_WARNING;
    }

    return PMU_STATUS_OK;
}

/**
 * @brief Get total current consumption
 * @return Total current in Amps (1 A/bit)
 */
static uint8_t GetTotalCurrent(void)
{
    uint32_t total_mA = 0;

    for (uint8_t i = 0; i < 30; i++) {
        total_mA += PMU_PROFET_GetCurrent(i);
    }

    /* Add H-Bridge currents */
    for (uint8_t i = 0; i < 4; i++) {
        total_mA += PMU_HBridge_GetCurrent(i);
    }

    /* Convert to Amps, clamp to 255 */
    uint32_t total_A = total_mA / 1000;
    if (total_A > 255) total_A = 255;

    return (uint8_t)total_A;
}

/**
 * @brief Get battery voltage in raw format
 * @return Battery voltage (0.1088 V/bit)
 */
static uint8_t GetBatteryVoltageRaw(void)
{
    /* TODO: Read actual battery voltage from ADC or SPI diagnostics */
    /* For now, assume 12V nominal */
    float vbat = 12.0f;

    /* Check if we can get it from protection module */
    /* vbat = PMU_Protection_GetBatteryVoltage(); */

    return PMU_STREAM_VBAT_TO_RAW(vbat);
}

/**
 * @brief Get left board temperature
 * @return Temperature in °C
 */
static uint8_t GetBoardTempLeft(void)
{
    /* TODO: Read from NTC sensor */
    /* For now, estimate from output temperatures */
    int16_t max_temp = 25;

    for (uint8_t i = 0; i < 15; i++) {
        int16_t temp = PMU_PROFET_GetTemperature(i);
        if (temp > max_temp) max_temp = temp;
    }

    return (max_temp > 255) ? 255 : (uint8_t)max_temp;
}

/**
 * @brief Get right board temperature
 * @return Temperature in °C
 */
static uint8_t GetBoardTempRight(void)
{
    /* TODO: Read from NTC sensor */
    int16_t max_temp = 25;

    for (uint8_t i = 15; i < 30; i++) {
        int16_t temp = PMU_PROFET_GetTemperature(i);
        if (temp > max_temp) max_temp = temp;
    }

    return (max_temp > 255) ? 255 : (uint8_t)max_temp;
}

/**
 * @brief Get MCU internal temperature
 * @return Temperature in °C
 */
static uint8_t GetMcuTemperature(void)
{
    /* TODO: Read from STM32 internal temperature sensor */
    /* ADC reading of VTEMPSENSOR */
    return 45; /* Placeholder */
}

/**
 * @brief Get output voltage in raw format
 * @param channel Output channel (0-29)
 * @return Voltage (0.0635 V/bit)
 */
static uint8_t GetOutputVoltageRaw(uint8_t channel)
{
    PMU_PROFET_Channel_t *ch = PMU_PROFET_GetChannelData(channel);

    if (ch == NULL || ch->state == PMU_PROFET_STATE_OFF) {
        return 0;
    }

    /* When output is on, voltage should be close to battery voltage */
    /* minus some drop. For PWM, scale by duty cycle. */
    float vbat = 12.0f; /* TODO: Get actual battery voltage */
    float vout = 0.0f;

    if (ch->state == PMU_PROFET_STATE_ON) {
        vout = vbat - 0.3f; /* ~300mV drop typical */
    } else if (ch->state == PMU_PROFET_STATE_PWM) {
        /* Average voltage based on duty cycle */
        vout = (vbat - 0.3f) * (float)ch->pwm_duty / 1000.0f;
    }

    /* Clamp to range */
    if (vout < 0.0f) vout = 0.0f;
    if (vout > 16.19f) vout = 16.19f;

    return PMU_STREAM_VOUT_TO_RAW(vout);
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

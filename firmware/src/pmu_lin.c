/**
 ******************************************************************************
 * @file           : pmu_lin.c
 * @brief          : LIN Bus Protocol Handler Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_lin.h"
#include "pmu_channel.h"
#include <string.h>
#include <stdio.h>

#ifdef USE_EMULATOR
#include "pmu_emulator.h"
#endif

/* Private defines -----------------------------------------------------------*/

#define LIN_LOG(fmt, ...) printf("[LIN] " fmt "\n", ##__VA_ARGS__)

/* Private variables ---------------------------------------------------------*/

static bool s_initialized = false;
static PMU_LIN_Mode_t s_mode = PMU_LIN_MODE_SLAVE;

/* Frame Objects (Level 1) */
static PMU_LIN_FrameObject_t s_frames[PMU_LIN_MAX_FRAME_OBJECTS];
static uint16_t s_frame_count = 0;

/* Input Signals (Level 2) */
static PMU_LIN_Input_t s_inputs[PMU_LIN_MAX_INPUTS];
static uint16_t s_input_count = 0;

/* Output Signals */
static PMU_LIN_Output_t s_outputs[PMU_LIN_MAX_OUTPUTS];
static uint16_t s_output_count = 0;

/* Schedule Table */
static PMU_LIN_Schedule_t s_schedule;

/* Bus State */
static PMU_LIN_State_t s_bus_state[PMU_LIN_BUS_COUNT];
static PMU_LIN_Stats_t s_bus_stats[PMU_LIN_BUS_COUNT];
static uint32_t s_baudrate[PMU_LIN_BUS_COUNT] = {19200, 19200};

/* Callbacks */
static PMU_LIN_RxCallback_t s_rx_callback = NULL;
static PMU_LIN_ErrorCallback_t s_error_callback = NULL;

/* Current tick (updated externally) */
extern uint32_t HAL_GetTick(void);

/* Private function prototypes -----------------------------------------------*/

static PMU_LIN_FrameObject_t* find_frame_by_id(const char* id);
static PMU_LIN_FrameObject_t* find_frame_by_number(PMU_LIN_Bus_t bus, uint8_t frame_id);

/* Public functions ----------------------------------------------------------*/

/* ============================================================================
 * Initialization
 * ============================================================================ */

int PMU_LIN_Init(PMU_LIN_Mode_t mode)
{
    if (s_initialized) {
        return 0;  /* Already initialized */
    }

    s_mode = mode;

    /* Clear all data */
    memset(s_frames, 0, sizeof(s_frames));
    memset(s_inputs, 0, sizeof(s_inputs));
    memset(s_outputs, 0, sizeof(s_outputs));
    memset(&s_schedule, 0, sizeof(s_schedule));
    memset(s_bus_state, 0, sizeof(s_bus_state));
    memset(s_bus_stats, 0, sizeof(s_bus_stats));

    s_frame_count = 0;
    s_input_count = 0;
    s_output_count = 0;

    /* Set initial bus state */
    for (int i = 0; i < PMU_LIN_BUS_COUNT; i++) {
        s_bus_state[i] = PMU_LIN_STATE_IDLE;
    }

    s_initialized = true;
    LIN_LOG("Initialized in %s mode", mode == PMU_LIN_MODE_MASTER ? "MASTER" : "SLAVE");

    return 0;
}

void PMU_LIN_DeInit(void)
{
    if (!s_initialized) {
        return;
    }

    PMU_LIN_StopSchedule();

    for (int i = 0; i < PMU_LIN_BUS_COUNT; i++) {
        s_bus_state[i] = PMU_LIN_STATE_UNINIT;
    }

    s_initialized = false;
    LIN_LOG("Deinitialized");
}

void PMU_LIN_Reset(void)
{
    /* Clear frames */
    memset(s_frames, 0, sizeof(s_frames));
    s_frame_count = 0;

    /* Clear inputs */
    memset(s_inputs, 0, sizeof(s_inputs));
    s_input_count = 0;

    /* Clear outputs */
    memset(s_outputs, 0, sizeof(s_outputs));
    s_output_count = 0;

    /* Clear schedule */
    memset(&s_schedule, 0, sizeof(s_schedule));

    LIN_LOG("Reset complete");
}

int PMU_LIN_ConfigureBus(PMU_LIN_Bus_t bus, uint32_t baudrate)
{
    if (bus >= PMU_LIN_BUS_COUNT) {
        return -1;
    }

    s_baudrate[bus] = baudrate;

    /* TODO: Configure hardware UART for LIN */
    /* For now, just store the baudrate */

    LIN_LOG("Bus %d configured at %lu baud", bus, (unsigned long)baudrate);
    return 0;
}

/* ============================================================================
 * Frame Object Management (Level 1)
 * ============================================================================ */

int PMU_LIN_AddFrameObject(const PMU_LIN_FrameObject_t* frame)
{
    if (!frame || s_frame_count >= PMU_LIN_MAX_FRAME_OBJECTS) {
        return -1;
    }

    if (frame->frame_id > PMU_LIN_MAX_FRAME_ID) {
        LIN_LOG("Invalid frame ID: %d (max %d)", frame->frame_id, PMU_LIN_MAX_FRAME_ID);
        return -1;
    }

    /* Check for duplicate ID */
    if (find_frame_by_id(frame->id) != NULL) {
        LIN_LOG("Duplicate frame ID: %s", frame->id);
        return -1;
    }

    /* Copy frame object */
    PMU_LIN_FrameObject_t* new_frame = &s_frames[s_frame_count];
    memcpy(new_frame, frame, sizeof(PMU_LIN_FrameObject_t));

    /* Initialize runtime state */
    new_frame->last_rx_tick = 0;
    new_frame->last_tx_tick = 0;
    new_frame->timeout_flag = 0;
    new_frame->error_flags = 0;
    new_frame->rx_count = 0;
    new_frame->tx_count = 0;
    new_frame->error_count = 0;
    memset(new_frame->data, 0, sizeof(new_frame->data));

    int index = s_frame_count;
    s_frame_count++;

    LIN_LOG("Added frame '%s' (ID=%d, bus=%d)", frame->id, frame->frame_id, frame->bus);
    return index;
}

PMU_LIN_FrameObject_t* PMU_LIN_GetFrameObject(const char* id)
{
    return find_frame_by_id(id);
}

PMU_LIN_FrameObject_t* PMU_LIN_GetFrameByID(PMU_LIN_Bus_t bus, uint8_t frame_id)
{
    return find_frame_by_number(bus, frame_id);
}

uint16_t PMU_LIN_GetFrameCount(void)
{
    return s_frame_count;
}

/* ============================================================================
 * Input Signal Management (Level 2)
 * ============================================================================ */

int PMU_LIN_AddInput(const PMU_LIN_Input_t* input)
{
    if (!input || s_input_count >= PMU_LIN_MAX_INPUTS) {
        return -1;
    }

    /* Copy input */
    PMU_LIN_Input_t* new_input = &s_inputs[s_input_count];
    memcpy(new_input, input, sizeof(PMU_LIN_Input_t));

    /* Initialize runtime state */
    new_input->frame_ptr = NULL;
    new_input->current_value = input->default_value;
    new_input->timeout_flag = 0;

    /* Set default scaling if not specified */
    if (new_input->divider == 0.0f) {
        new_input->divider = 1.0f;
    }
    if (new_input->multiplier == 0.0f) {
        new_input->multiplier = 1.0f;
    }

    int index = s_input_count;
    s_input_count++;

    LIN_LOG("Added input '%s' -> frame '%s'", input->id, input->frame_ref);
    return index;
}

PMU_LIN_Input_t* PMU_LIN_GetInput(const char* id)
{
    for (uint16_t i = 0; i < s_input_count; i++) {
        if (strcmp(s_inputs[i].id, id) == 0) {
            return &s_inputs[i];
        }
    }
    return NULL;
}

int PMU_LIN_LinkInputsToFrames(void)
{
    int linked = 0;

    for (uint16_t i = 0; i < s_input_count; i++) {
        PMU_LIN_Input_t* input = &s_inputs[i];

        /* Find referenced frame */
        input->frame_ptr = find_frame_by_id(input->frame_ref);

        if (input->frame_ptr) {
            linked++;
        } else {
            LIN_LOG("Warning: Input '%s' could not find frame '%s'",
                    input->id, input->frame_ref);
        }
    }

    LIN_LOG("Linked %d/%d inputs to frames", linked, s_input_count);
    return linked;
}

uint16_t PMU_LIN_GetInputCount(void)
{
    return s_input_count;
}

/* ============================================================================
 * Output Signal Management
 * ============================================================================ */

int PMU_LIN_AddOutput(const PMU_LIN_Output_t* output)
{
    if (!output || s_output_count >= PMU_LIN_MAX_OUTPUTS) {
        return -1;
    }

    /* Copy output */
    PMU_LIN_Output_t* new_output = &s_outputs[s_output_count];
    memcpy(new_output, output, sizeof(PMU_LIN_Output_t));

    /* Initialize runtime state */
    new_output->frame_ptr = NULL;
    new_output->current_value = 0.0f;

    /* Set default scaling if not specified */
    if (new_output->divider == 0.0f) {
        new_output->divider = 1.0f;
    }
    if (new_output->multiplier == 0.0f) {
        new_output->multiplier = 1.0f;
    }

    int index = s_output_count;
    s_output_count++;

    LIN_LOG("Added output '%s' -> frame '%s'", output->id, output->frame_ref);
    return index;
}

PMU_LIN_Output_t* PMU_LIN_GetOutput(const char* id)
{
    for (uint16_t i = 0; i < s_output_count; i++) {
        if (strcmp(s_outputs[i].id, id) == 0) {
            return &s_outputs[i];
        }
    }
    return NULL;
}

int PMU_LIN_LinkOutputsToFrames(void)
{
    int linked = 0;

    for (uint16_t i = 0; i < s_output_count; i++) {
        PMU_LIN_Output_t* output = &s_outputs[i];

        /* Find referenced frame */
        output->frame_ptr = find_frame_by_id(output->frame_ref);

        if (output->frame_ptr) {
            linked++;
        } else {
            LIN_LOG("Warning: Output '%s' could not find frame '%s'",
                    output->id, output->frame_ref);
        }

        /* Resolve source channel */
        if (output->source_channel[0]) {
            uint16_t idx = PMU_Channel_GetIndexByID(output->source_channel);
            if (idx > 0) {
                output->source_channel_idx = idx;
            }
        }
    }

    LIN_LOG("Linked %d/%d outputs to frames", linked, s_output_count);
    return linked;
}

uint16_t PMU_LIN_GetOutputCount(void)
{
    return s_output_count;
}

/* ============================================================================
 * Frame Processing
 * ============================================================================ */

void PMU_LIN_HandleRxFrame(PMU_LIN_Bus_t bus, uint8_t frame_id,
                           const uint8_t* data, uint8_t length)
{
    if (bus >= PMU_LIN_BUS_COUNT || !data || length > PMU_LIN_FRAME_DATA_LEN) {
        return;
    }

    /* Find matching frame object */
    PMU_LIN_FrameObject_t* frame = find_frame_by_number(bus, frame_id);

    if (frame && frame->enabled) {
        /* Copy data to frame buffer */
        memcpy(frame->data, data, length);
        frame->last_rx_tick = HAL_GetTick();
        frame->timeout_flag = 0;
        frame->rx_count++;

        /* Update bus stats */
        s_bus_stats[bus].frames_rx++;

        /* Call RX callback if registered */
        if (s_rx_callback) {
            s_rx_callback(bus, frame_id, data, length);
        }
    }

#ifdef USE_EMULATOR
    /* Notify emulator */
    PMU_Emu_LIN_HandleRx(bus, frame_id, data, length);
#endif
}

void PMU_LIN_ProcessInputs(void)
{
    for (uint16_t i = 0; i < s_input_count; i++) {
        PMU_LIN_Input_t* input = &s_inputs[i];
        PMU_LIN_FrameObject_t* frame = input->frame_ptr;

        if (!frame || !frame->enabled) {
            continue;
        }

        /* Check for timeout */
        if (frame->timeout_flag) {
            input->timeout_flag = 1;

            switch (input->timeout_behavior) {
                case PMU_LIN_TIMEOUT_USE_DEFAULT:
                    input->current_value = input->default_value;
                    break;
                case PMU_LIN_TIMEOUT_SET_ZERO:
                    input->current_value = 0.0f;
                    break;
                case PMU_LIN_TIMEOUT_HOLD_LAST:
                    /* Keep current value */
                    break;
            }
        } else {
            input->timeout_flag = 0;

            /* Extract raw value from frame data */
            int32_t raw = PMU_LIN_ExtractSignal(
                frame->data,
                input->start_bit,
                input->bit_length,
                input->byte_order,
                input->data_type == PMU_LIN_DATA_TYPE_SIGNED
            );

            /* Apply scaling */
            float scaled = ((float)raw * input->multiplier / input->divider) + input->offset;
            input->current_value = scaled;
        }

        /* Update virtual channel if configured */
        if (input->virtual_channel > 0) {
            PMU_Channel_SetValue(input->virtual_channel, input->current_value);
        }
    }
}

void PMU_LIN_ProcessOutputs(void)
{
    for (uint16_t i = 0; i < s_output_count; i++) {
        PMU_LIN_Output_t* output = &s_outputs[i];
        PMU_LIN_FrameObject_t* frame = output->frame_ptr;

        if (!frame || !frame->enabled || frame->direction != PMU_LIN_DIR_PUBLISH) {
            continue;
        }

        /* Get source value */
        float value = 0.0f;
        if (output->source_channel_idx > 0) {
            value = PMU_Channel_GetValue(output->source_channel_idx);
        }
        output->current_value = value;

        /* Inverse scaling: raw = (value - offset) * divider / multiplier */
        float raw_f = (value - output->offset) * output->divider / output->multiplier;
        int32_t raw = (int32_t)raw_f;

        /* Pack into frame data */
        PMU_LIN_PackSignal(
            frame->data,
            output->start_bit,
            output->bit_length,
            output->byte_order,
            raw
        );
    }
}

void PMU_LIN_ProcessTimeouts(void)
{
    uint32_t now = HAL_GetTick();

    for (uint16_t i = 0; i < s_frame_count; i++) {
        PMU_LIN_FrameObject_t* frame = &s_frames[i];

        if (!frame->enabled || frame->timeout_ms == 0) {
            continue;
        }

        /* Only check timeouts for subscribe frames */
        if (frame->direction != PMU_LIN_DIR_SUBSCRIBE) {
            continue;
        }

        uint32_t elapsed = now - frame->last_rx_tick;
        if (elapsed > frame->timeout_ms && !frame->timeout_flag) {
            frame->timeout_flag = 1;
            frame->error_count++;
            s_bus_stats[frame->bus].errors_timeout++;

            LIN_LOG("Frame '%s' timeout", frame->id);
        }
    }
}

int PMU_LIN_TransmitFrame(PMU_LIN_Bus_t bus, uint8_t frame_id,
                          const uint8_t* data, uint8_t length)
{
    if (bus >= PMU_LIN_BUS_COUNT || !data || length > PMU_LIN_FRAME_DATA_LEN) {
        return -1;
    }

    if (s_mode != PMU_LIN_MODE_MASTER) {
        return -1;  /* Only master can initiate transmission */
    }

    PMU_LIN_FrameObject_t* frame = find_frame_by_number(bus, frame_id);
    if (frame) {
        frame->last_tx_tick = HAL_GetTick();
        frame->tx_count++;
    }

    s_bus_stats[bus].frames_tx++;

#ifdef USE_EMULATOR
    /* Send via emulator */
    PMU_Emu_LIN_Transmit(bus, frame_id, data, length);
#else
    /* TODO: Actual hardware LIN transmission */
    /* This would involve:
     * 1. Send break field (13+ bit times of dominant)
     * 2. Send sync byte (0x55)
     * 3. Send protected ID (with parity)
     * 4. Send data bytes
     * 5. Send checksum
     */
    (void)bus;
    (void)frame_id;
    (void)data;
    (void)length;
#endif

    return 0;
}

int PMU_LIN_RequestFrame(PMU_LIN_Bus_t bus, uint8_t frame_id)
{
    if (bus >= PMU_LIN_BUS_COUNT) {
        return -1;
    }

    if (s_mode != PMU_LIN_MODE_MASTER) {
        return -1;
    }

#ifdef USE_EMULATOR
    /* Request frame via emulator */
    PMU_Emu_LIN_RequestFrame(bus, frame_id);
#else
    /* TODO: Send header and wait for slave response */
    (void)bus;
    (void)frame_id;
#endif

    return 0;
}

/* ============================================================================
 * Schedule Table
 * ============================================================================ */

int PMU_LIN_AddScheduleSlot(uint8_t frame_id, uint16_t delay_ms)
{
    if (s_schedule.slot_count >= PMU_LIN_MAX_SCHEDULE_SLOTS) {
        return -1;
    }

    PMU_LIN_ScheduleSlot_t* slot = &s_schedule.slots[s_schedule.slot_count];
    slot->frame_id = frame_id;
    slot->delay_ms = delay_ms;
    slot->enabled = 1;

    int index = s_schedule.slot_count;
    s_schedule.slot_count++;

    return index;
}

void PMU_LIN_StartSchedule(void)
{
    if (s_mode != PMU_LIN_MODE_MASTER) {
        return;
    }

    s_schedule.enabled = 1;
    s_schedule.current_slot = 0;
    s_schedule.next_slot_tick = HAL_GetTick();

    LIN_LOG("Schedule started (%d slots)", s_schedule.slot_count);
}

void PMU_LIN_StopSchedule(void)
{
    s_schedule.enabled = 0;
    LIN_LOG("Schedule stopped");
}

void PMU_LIN_ProcessSchedule(void)
{
    if (!s_schedule.enabled || s_schedule.slot_count == 0) {
        return;
    }

    uint32_t now = HAL_GetTick();

    if (now >= s_schedule.next_slot_tick) {
        PMU_LIN_ScheduleSlot_t* slot = &s_schedule.slots[s_schedule.current_slot];

        if (slot->enabled) {
            /* Find the frame and transmit/request */
            PMU_LIN_FrameObject_t* frame = find_frame_by_number(PMU_LIN_BUS_1, slot->frame_id);
            if (frame) {
                if (frame->direction == PMU_LIN_DIR_PUBLISH) {
                    PMU_LIN_TransmitFrame(frame->bus, frame->frame_id,
                                          frame->data, frame->length);
                } else {
                    PMU_LIN_RequestFrame(frame->bus, frame->frame_id);
                }
            }
        }

        /* Move to next slot */
        s_schedule.current_slot++;
        if (s_schedule.current_slot >= s_schedule.slot_count) {
            s_schedule.current_slot = 0;
        }

        /* Schedule next slot */
        s_schedule.next_slot_tick = now + slot->delay_ms;
    }
}

/* ============================================================================
 * Sleep/Wakeup
 * ============================================================================ */

void PMU_LIN_SendSleep(PMU_LIN_Bus_t bus)
{
    if (bus >= PMU_LIN_BUS_COUNT) {
        return;
    }

    /* Sleep frame: ID=0x3C (master request), data=0x00, 0xFF, ... */
    uint8_t sleep_data[8] = {0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    PMU_LIN_TransmitFrame(bus, PMU_LIN_DIAG_MASTER_REQ, sleep_data, 8);

    s_bus_state[bus] = PMU_LIN_STATE_SLEEP;
    s_bus_stats[bus].sleep_count++;

    LIN_LOG("Bus %d entering sleep", bus);
}

void PMU_LIN_SendWakeup(PMU_LIN_Bus_t bus)
{
    if (bus >= PMU_LIN_BUS_COUNT) {
        return;
    }

#ifdef USE_EMULATOR
    PMU_Emu_LIN_SendWakeup(bus);
#else
    /* TODO: Send wakeup signal (dominant for 250us-5ms) */
#endif

    s_bus_state[bus] = PMU_LIN_STATE_IDLE;
    s_bus_stats[bus].wakeup_count++;

    LIN_LOG("Bus %d wakeup sent", bus);
}

bool PMU_LIN_IsSleeping(PMU_LIN_Bus_t bus)
{
    if (bus >= PMU_LIN_BUS_COUNT) {
        return false;
    }
    return s_bus_state[bus] == PMU_LIN_STATE_SLEEP;
}

/* ============================================================================
 * Diagnostics
 * ============================================================================ */

int PMU_LIN_SendDiagRequest(PMU_LIN_Bus_t bus, uint8_t nad, const uint8_t* data)
{
    if (bus >= PMU_LIN_BUS_COUNT || !data) {
        return -1;
    }

    /* Diagnostic frame format: NAD, PCI, SID, D1, D2, D3, D4, D5 */
    uint8_t diag_data[8];
    diag_data[0] = nad;
    memcpy(&diag_data[1], data, 7);

    return PMU_LIN_TransmitFrame(bus, PMU_LIN_DIAG_MASTER_REQ, diag_data, 8);
}

int PMU_LIN_ReadDiagResponse(PMU_LIN_Bus_t bus, uint8_t nad,
                             uint8_t* data, uint32_t timeout_ms)
{
    if (bus >= PMU_LIN_BUS_COUNT || !data) {
        return -1;
    }

    /* Find diagnostic response frame */
    PMU_LIN_FrameObject_t* frame = find_frame_by_number(bus, PMU_LIN_DIAG_SLAVE_RESP);
    if (!frame) {
        return -1;
    }

    uint32_t start = HAL_GetTick();
    while ((HAL_GetTick() - start) < timeout_ms) {
        /* Check if new data received with matching NAD */
        if (frame->data[0] == nad) {
            memcpy(data, &frame->data[1], 7);
            return 0;
        }

        /* Small delay to avoid busy-waiting */
#ifdef USE_EMULATOR
        /* In emulator, just check once */
        break;
#endif
    }

    return -1;  /* Timeout */
}

/* ============================================================================
 * Callbacks
 * ============================================================================ */

void PMU_LIN_SetRxCallback(PMU_LIN_RxCallback_t callback)
{
    s_rx_callback = callback;
}

void PMU_LIN_SetErrorCallback(PMU_LIN_ErrorCallback_t callback)
{
    s_error_callback = callback;
}

/* ============================================================================
 * Statistics
 * ============================================================================ */

const PMU_LIN_Stats_t* PMU_LIN_GetStats(PMU_LIN_Bus_t bus)
{
    if (bus >= PMU_LIN_BUS_COUNT) {
        return NULL;
    }
    return &s_bus_stats[bus];
}

void PMU_LIN_ResetStats(PMU_LIN_Bus_t bus)
{
    if (bus >= PMU_LIN_BUS_COUNT) {
        return;
    }
    memset(&s_bus_stats[bus], 0, sizeof(PMU_LIN_Stats_t));
}

PMU_LIN_State_t PMU_LIN_GetState(PMU_LIN_Bus_t bus)
{
    if (bus >= PMU_LIN_BUS_COUNT) {
        return PMU_LIN_STATE_UNINIT;
    }
    return s_bus_state[bus];
}

/* ============================================================================
 * Utility Functions
 * ============================================================================ */

uint8_t PMU_LIN_CalculateChecksum(PMU_LIN_ChecksumType_t type, uint8_t pid,
                                  const uint8_t* data, uint8_t length)
{
    uint16_t sum = 0;

    /* Enhanced checksum includes PID */
    if (type == PMU_LIN_CHECKSUM_ENHANCED) {
        sum = pid;
    }

    /* Sum all data bytes */
    for (uint8_t i = 0; i < length; i++) {
        sum += data[i];
        /* Handle carry */
        if (sum > 0xFF) {
            sum = (sum & 0xFF) + 1;
        }
    }

    /* Invert result */
    return (uint8_t)(~sum);
}

uint8_t PMU_LIN_CalculatePID(uint8_t id)
{
    /* ID is 6 bits (0-63) */
    id &= 0x3F;

    /* Calculate parity bits */
    uint8_t p0 = (id ^ (id >> 1) ^ (id >> 2) ^ (id >> 4)) & 0x01;
    uint8_t p1 = ~((id >> 1) ^ (id >> 3) ^ (id >> 4) ^ (id >> 5)) & 0x01;

    return id | (p0 << 6) | (p1 << 7);
}

int32_t PMU_LIN_ExtractSignal(const uint8_t* data, uint8_t start_bit,
                              uint8_t bit_length, uint8_t byte_order,
                              bool is_signed)
{
    if (!data || bit_length == 0 || bit_length > 32) {
        return 0;
    }

    int32_t value = 0;
    uint8_t bits_read = 0;

    if (byte_order == 0) {
        /* Little endian (Intel format) - LSB first */
        uint8_t byte_pos = start_bit / 8;
        uint8_t bit_pos = start_bit % 8;

        while (bits_read < bit_length) {
            uint8_t bits_in_byte = 8 - bit_pos;
            if (bits_in_byte > (bit_length - bits_read)) {
                bits_in_byte = bit_length - bits_read;
            }

            uint8_t mask = ((1 << bits_in_byte) - 1) << bit_pos;
            uint8_t extracted = (data[byte_pos] & mask) >> bit_pos;
            value |= ((int32_t)extracted << bits_read);

            bits_read += bits_in_byte;
            byte_pos++;
            bit_pos = 0;
        }
    } else {
        /* Big endian (Motorola format) - MSB first */
        uint8_t byte_pos = start_bit / 8;
        uint8_t bit_pos = start_bit % 8;

        while (bits_read < bit_length) {
            uint8_t bits_in_byte = bit_pos + 1;
            if (bits_in_byte > (bit_length - bits_read)) {
                bits_in_byte = bit_length - bits_read;
            }

            uint8_t shift = bit_pos + 1 - bits_in_byte;
            uint8_t mask = ((1 << bits_in_byte) - 1) << shift;
            uint8_t extracted = (data[byte_pos] & mask) >> shift;

            value = (value << bits_in_byte) | extracted;

            bits_read += bits_in_byte;
            byte_pos++;
            bit_pos = 7;
        }
    }

    /* Sign extend if signed */
    if (is_signed && bit_length < 32) {
        int32_t sign_bit = 1 << (bit_length - 1);
        if (value & sign_bit) {
            value |= ~((1 << bit_length) - 1);
        }
    }

    return value;
}

void PMU_LIN_PackSignal(uint8_t* data, uint8_t start_bit,
                        uint8_t bit_length, uint8_t byte_order,
                        int32_t value)
{
    if (!data || bit_length == 0 || bit_length > 32) {
        return;
    }

    uint8_t bits_written = 0;

    if (byte_order == 0) {
        /* Little endian */
        uint8_t byte_pos = start_bit / 8;
        uint8_t bit_pos = start_bit % 8;

        while (bits_written < bit_length) {
            uint8_t bits_in_byte = 8 - bit_pos;
            if (bits_in_byte > (bit_length - bits_written)) {
                bits_in_byte = bit_length - bits_written;
            }

            uint8_t mask = ((1 << bits_in_byte) - 1);
            uint8_t bits = (value >> bits_written) & mask;

            data[byte_pos] &= ~(mask << bit_pos);
            data[byte_pos] |= (bits << bit_pos);

            bits_written += bits_in_byte;
            byte_pos++;
            bit_pos = 0;
        }
    } else {
        /* Big endian */
        uint8_t byte_pos = start_bit / 8;
        uint8_t bit_pos = start_bit % 8;

        /* For big endian, we write MSB first */
        int32_t remaining_value = value;
        uint8_t remaining_bits = bit_length;

        while (remaining_bits > 0) {
            uint8_t bits_in_byte = bit_pos + 1;
            if (bits_in_byte > remaining_bits) {
                bits_in_byte = remaining_bits;
            }

            uint8_t shift = bit_pos + 1 - bits_in_byte;
            uint8_t mask = ((1 << bits_in_byte) - 1);
            uint8_t bits = (remaining_value >> (remaining_bits - bits_in_byte)) & mask;

            data[byte_pos] &= ~(mask << shift);
            data[byte_pos] |= (bits << shift);

            remaining_bits -= bits_in_byte;
            byte_pos++;
            bit_pos = 7;
        }
    }
}

/* Private functions ---------------------------------------------------------*/

static PMU_LIN_FrameObject_t* find_frame_by_id(const char* id)
{
    if (!id) return NULL;

    for (uint16_t i = 0; i < s_frame_count; i++) {
        if (strcmp(s_frames[i].id, id) == 0) {
            return &s_frames[i];
        }
    }
    return NULL;
}

static PMU_LIN_FrameObject_t* find_frame_by_number(PMU_LIN_Bus_t bus, uint8_t frame_id)
{
    for (uint16_t i = 0; i < s_frame_count; i++) {
        if (s_frames[i].bus == bus && s_frames[i].frame_id == frame_id) {
            return &s_frames[i];
        }
    }
    return NULL;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/

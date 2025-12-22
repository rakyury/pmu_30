# Unified Channel System Architecture

**Version:** 1.0
**Date:** December 2024
**Author:** R2 m-sport

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [Channel Types](#3-channel-types)
4. [Channel ID Allocation](#4-channel-id-allocation)
5. [State Management](#5-state-management)
6. [Thread Safety and Concurrency](#6-thread-safety-and-concurrency)
7. [Performance Characteristics](#7-performance-characteristics)
8. [Integration Points](#8-integration-points)
9. [Memory Layout](#9-memory-layout)
10. [Error Handling](#10-error-handling)

---

## 1. Overview

The Unified Channel System provides a universal abstraction layer for all inputs and outputs in the PMU-30 Power Management Unit. This architecture enables consistent access to physical hardware, virtual calculations, CAN bus signals, and system parameters through a single, unified API.

### 1.1 Design Goals

| Goal | Description |
|------|-------------|
| **Abstraction** | Hide hardware complexity behind consistent interface |
| **Flexibility** | Support physical, virtual, and system channels |
| **Performance** | 1kHz update rate for all channels |
| **Scalability** | Support up to 1024 channels |
| **Type Safety** | Strong typing with format specifications |

### 1.2 Key Features

- **Universal Access**: Single API for all channel types
- **Bidirectional**: Support for input, output, and bidirectional channels
- **Value Formats**: Raw, percentage, voltage, current, boolean, enum, signed
- **Metadata**: Name, unit, min/max values per channel
- **Flags**: Enable, invert, fault, override states

---

## 2. Architecture Principles

### 2.1 Layered Architecture

```
+----------------------------------------------------------+
|                    Application Layer                      |
|           (Configuration, Logic Functions, UI)            |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|              Unified Channel Abstraction                  |
|                   (pmu_channel.h)                         |
|    - PMU_Channel_GetValue()                              |
|    - PMU_Channel_SetValue()                              |
|    - PMU_Channel_Register()                              |
+----------------------------------------------------------+
                            |
            +---------------+---------------+
            |               |               |
            v               v               v
+----------------+  +----------------+  +----------------+
| Physical I/O   |  | Virtual I/O    |  | System I/O     |
| - ADC          |  | - CAN signals  |  | - Battery V    |
| - PROFET       |  | - Calculations |  | - Temperature  |
| - H-bridge     |  | - Functions    |  | - Uptime       |
| - GPIO         |  | - Tables       |  | - Total I      |
+----------------+  +----------------+  +----------------+
```

### 2.2 Channel Classification

Channels are classified by two orthogonal dimensions:

**By Direction:**
- **Input**: Data flows into the system
- **Output**: Data flows out of the system
- **Bidirectional**: Data can flow both ways

**By Nature:**
- **Physical**: Connected to hardware (ADC, PROFET, GPIO)
- **Virtual**: Computed or received (CAN, calculations)
- **System**: Internal system state (voltage, temperature)

---

## 3. Channel Types

### 3.1 Physical Inputs (0x00-0x1F)

| Type Code | Name | Description | Value Range |
|-----------|------|-------------|-------------|
| 0x00 | `PMU_CHANNEL_INPUT_ANALOG` | ADC input (0-5V) | 0-4095 (12-bit) |
| 0x01 | `PMU_CHANNEL_INPUT_DIGITAL` | Digital on/off | 0 or 1 |
| 0x02 | `PMU_CHANNEL_INPUT_SWITCH` | Momentary switch | 0 or 1 |
| 0x03 | `PMU_CHANNEL_INPUT_ROTARY` | Rotary selector | 0-255 positions |
| 0x04 | `PMU_CHANNEL_INPUT_FREQUENCY` | Frequency input | 0-20000 Hz |

**Analog Input Processing:**
```
Raw ADC (0-4095) --> Scaling --> Calibration --> Value
                         |             |
                         v             v
                    min/max      User-defined
                    mapping      curve points
```

### 3.2 Virtual Inputs (0x20-0x3F)

| Type Code | Name | Description | Source |
|-----------|------|-------------|--------|
| 0x20 | `PMU_CHANNEL_INPUT_CAN` | CAN bus signal | CAN frames |
| 0x21 | `PMU_CHANNEL_INPUT_CALCULATED` | Math result | Logic functions |
| 0x22 | `PMU_CHANNEL_INPUT_SYSTEM` | System value | Internal sensors |

**CAN Input Processing:**
```
CAN Frame --> Signal Extraction --> Scaling --> Value
    |               |                   |
    v               v                   v
  ID filter    Start bit,          Factor,
              Length, Endian        Offset
```

### 3.3 Physical Outputs (0x40-0x5F)

| Type Code | Name | Description | Control Range |
|-----------|------|-------------|---------------|
| 0x40 | `PMU_CHANNEL_OUTPUT_POWER` | PROFET high-side switch | 0 (off) or 1 (on) |
| 0x41 | `PMU_CHANNEL_OUTPUT_PWM` | PWM output | 0-1000 (0.0-100.0%) |
| 0x42 | `PMU_CHANNEL_OUTPUT_HBRIDGE` | H-bridge motor | -1000 to +1000 |
| 0x43 | `PMU_CHANNEL_OUTPUT_ANALOG` | DAC output | 0-4095 |

**PROFET Output Flow:**
```
Source Channel --> Condition Eval --> Soft Start --> PWM Gen --> Hardware
       |                |                 |             |
       v                v                 v             v
   Any input      Logic result        Ramp up      10Hz-30kHz
    channel        true/false         0-5000ms
```

### 3.4 Virtual Outputs (0x60-0x7F)

| Type Code | Name | Description | Use Case |
|-----------|------|-------------|----------|
| 0x60 | `PMU_CHANNEL_OUTPUT_FUNCTION` | Logic function result | Calculations |
| 0x61 | `PMU_CHANNEL_OUTPUT_TABLE` | Lookup table result | Calibration |
| 0x62 | `PMU_CHANNEL_OUTPUT_ENUM` | Enumeration/state | State machines |
| 0x63 | `PMU_CHANNEL_OUTPUT_NUMBER` | Constant value | Parameters |
| 0x64 | `PMU_CHANNEL_OUTPUT_CAN` | CAN transmit | ECU communication |
| 0x65 | `PMU_CHANNEL_OUTPUT_PID` | PID controller | Closed-loop control |

---

## 4. Channel ID Allocation

### 4.1 ID Ranges

```
Channel ID Space (0-1023)
+--------+--------+--------+--------+--------+
|  0-99  |100-199 |200-999 |1000-1023|
+--------+--------+--------+--------+
| Physical| Physical| Virtual | System  |
| Inputs  | Outputs | Channels| Channels|
+--------+--------+--------+---------+
```

| Range | Count | Purpose | Examples |
|-------|-------|---------|----------|
| 0-99 | 100 | Physical inputs | ADC0-19, Digital0-7 |
| 100-199 | 100 | Physical outputs | PROFET0-29, HBridge0-3 |
| 200-999 | 800 | Virtual channels | CAN signals, calculations |
| 1000-1023 | 24 | System channels | Battery V, MCU temp |

### 4.2 Reserved System Channels

| ID | Name | Description | Unit |
|----|------|-------------|------|
| 1000 | `PMU_CHANNEL_SYSTEM_BATTERY_V` | Battery voltage | mV |
| 1001 | `PMU_CHANNEL_SYSTEM_TOTAL_I` | Total current | mA |
| 1002 | `PMU_CHANNEL_SYSTEM_MCU_TEMP` | MCU die temperature | 0.1°C |
| 1003 | `PMU_CHANNEL_SYSTEM_BOARD_TEMP` | Board temperature | 0.1°C |
| 1004 | `PMU_CHANNEL_SYSTEM_UPTIME` | System uptime | seconds |

### 4.3 ID Assignment Strategy

```c
// Physical input allocation
#define ADC_INPUT_BASE      0       // ADC inputs: 0-19
#define DIGITAL_INPUT_BASE  20      // Digital inputs: 20-27
#define FREQ_INPUT_BASE     30      // Frequency inputs: 30-37

// Physical output allocation
#define PROFET_OUTPUT_BASE  100     // PROFET outputs: 100-129
#define HBRIDGE_OUTPUT_BASE 130     // H-bridge outputs: 130-137

// Virtual channel allocation (user-configurable)
#define VIRTUAL_BASE        200     // Virtual channels start
```

---

## 5. State Management

### 5.1 Channel State Structure

```c
typedef struct {
    uint16_t channel_id;            // Global channel ID (0-1023)
    PMU_ChannelType_t type;         // Channel type
    PMU_ChannelDir_t direction;     // Input/Output/Bidir
    PMU_ChannelFormat_t format;     // Value format

    uint8_t physical_index;         // Physical hardware index
    uint8_t flags;                  // Status flags

    int32_t value;                  // Current value (signed)
    int32_t min_value;              // Minimum value
    int32_t max_value;              // Maximum value

    char name[32];                  // Channel name
    char unit[8];                   // Unit string
} PMU_Channel_t;
```

### 5.2 Channel Flags

| Flag | Bit | Description |
|------|-----|-------------|
| `PMU_CHANNEL_FLAG_ENABLED` | 0x01 | Channel is active |
| `PMU_CHANNEL_FLAG_INVERTED` | 0x02 | Value is inverted |
| `PMU_CHANNEL_FLAG_FAULT` | 0x04 | Fault condition detected |
| `PMU_CHANNEL_FLAG_OVERRIDE` | 0x08 | Manual override active |

### 5.3 Value Formats

| Format | Code | Description | Range |
|--------|------|-------------|-------|
| RAW | 0 | Raw ADC/PWM value | 0-4095 |
| PERCENT | 1 | Percentage x10 | 0-1000 (0.0-100.0%) |
| VOLTAGE | 2 | Millivolts | 0-65535 mV |
| CURRENT | 3 | Milliamps | 0-65535 mA |
| BOOLEAN | 4 | Boolean | 0 or 1 |
| ENUM | 5 | Enumeration | 0-255 |
| SIGNED | 6 | Signed value | -32768 to +32767 |

---

## 6. Thread Safety and Concurrency

### 6.1 Execution Model

The PMU-30 firmware uses a cooperative multitasking model with FreeRTOS:

```
+------------------+     +------------------+     +------------------+
|   Main Loop      |     |   Logic Task     |     |   CAN Task       |
|   (1kHz)         |     |   (500Hz)        |     |   (Event-driven) |
+------------------+     +------------------+     +------------------+
         |                        |                       |
         v                        v                       v
+------------------------------------------------------------------+
|                    Channel Registry (Shared)                      |
|                    Protected by Mutex                             |
+------------------------------------------------------------------+
```

### 6.2 Concurrency Patterns

**Read-Write Locking:**
```c
// Read operation (multiple readers allowed)
int32_t PMU_Channel_GetValue(uint16_t channel_id) {
    xSemaphoreTake(channel_mutex, portMAX_DELAY);
    int32_t value = channel_registry[channel_id].value;
    xSemaphoreGive(channel_mutex);
    return value;
}

// Write operation (exclusive access)
HAL_StatusTypeDef PMU_Channel_SetValue(uint16_t channel_id, int32_t value) {
    xSemaphoreTake(channel_mutex, portMAX_DELAY);
    channel_registry[channel_id].value = value;
    xSemaphoreGive(channel_mutex);
    return HAL_OK;
}
```

### 6.3 Update Sequence

```
1. ADC DMA Complete Interrupt (1kHz)
   |
   v
2. PMU_Channel_Update() called from main loop
   |
   +-- Update physical inputs from ADC buffer
   +-- Update system channels (voltage, temp)
   |
   v
3. PMU_Logic_Execute() called from logic task (500Hz)
   |
   +-- Read input channels
   +-- Execute logic functions
   +-- Write output channels
   |
   v
4. PMU_Logic_ApplyOutputs()
   |
   +-- Update PROFET PWM registers
   +-- Update H-bridge duty cycles
   +-- Queue CAN transmit messages
```

---

## 7. Performance Characteristics

### 7.1 Timing Specifications

| Operation | Typical Time | Maximum Time |
|-----------|--------------|--------------|
| Channel read | < 1 us | 5 us |
| Channel write | < 2 us | 10 us |
| Full update cycle | < 500 us | 1000 us |
| Logic function execution | < 5 us | 20 us |

### 7.2 Memory Usage

| Component | Size | Notes |
|-----------|------|-------|
| Channel registry | 64 KB | 1024 channels x 64 bytes |
| Channel name strings | 32 KB | 1024 x 32 bytes |
| Logic function state | 8 KB | 64 functions x 128 bytes |
| **Total** | ~104 KB | |

### 7.3 Throughput

| Metric | Value |
|--------|-------|
| Channel update rate | 1 kHz |
| Logic execution rate | 500 Hz |
| CAN message rate | Up to 10,000 msg/s |
| Maximum channels updated per cycle | 1024 |

---

## 8. Integration Points

### 8.1 With ADC Subsystem

```c
// ADC channels mapped to input channels
static const uint8_t adc_to_channel_map[] = {
    0,   // ADC0 -> Channel 0
    1,   // ADC1 -> Channel 1
    // ... up to 19 ADC channels
};

void PMU_Channel_UpdateFromADC(uint16_t* adc_buffer, uint8_t count) {
    for (uint8_t i = 0; i < count; i++) {
        uint16_t channel_id = adc_to_channel_map[i];
        PMU_Channel_SetValue(channel_id, adc_buffer[i]);
    }
}
```

### 8.2 With PROFET Driver

```c
// Output channels mapped to PROFET channels
void PMU_Channel_ApplyToPROFET(void) {
    for (uint8_t i = 0; i < 30; i++) {
        uint16_t channel_id = PROFET_OUTPUT_BASE + i;
        int32_t value = PMU_Channel_GetValue(channel_id);
        PMU_PROFET_SetDuty(i, (uint16_t)value);
    }
}
```

### 8.3 With CAN Subsystem

```c
// CAN signal mapping
typedef struct {
    uint16_t channel_id;    // Target channel
    uint32_t can_id;        // CAN message ID
    uint8_t start_bit;      // Signal start bit
    uint8_t length;         // Signal length
    float factor;           // Scaling factor
    float offset;           // Offset value
} PMU_CAN_SignalMap_t;

void PMU_Channel_UpdateFromCAN(CAN_RxHeaderTypeDef* header, uint8_t* data) {
    // Extract signal value and update channel
}
```

### 8.4 With Logic Functions

```c
// Logic function reads input channel, writes output channel
void PMU_LogicFunction_Execute(PMU_LogicFunction_t* func) {
    // Read inputs
    int32_t inputs[8];
    for (uint8_t i = 0; i < func->input_count; i++) {
        inputs[i] = PMU_Channel_GetValue(func->input_channels[i]);
    }

    // Execute function
    int32_t result = execute_function(func->type, inputs);

    // Write output
    PMU_Channel_SetValue(func->output_channel, result);
}
```

---

## 9. Memory Layout

### 9.1 Channel Registry Structure

```
Channel Registry (64 KB)
+------------------+
| Channel 0        |  64 bytes
| - id, type       |
| - value          |
| - name[32]       |
+------------------+
| Channel 1        |
| ...              |
+------------------+
| Channel 1023     |
+------------------+

Total: 1024 channels x 64 bytes = 65,536 bytes
```

### 9.2 Optimized Access

```c
// Fast channel access using direct indexing
static PMU_Channel_t channel_registry[PMU_CHANNEL_MAX_CHANNELS];

// O(1) access time
#define PMU_CHANNEL_GET(id) (&channel_registry[id])
```

---

## 10. Error Handling

### 10.1 Error Codes

| Code | Name | Description |
|------|------|-------------|
| HAL_OK | Success | Operation completed |
| HAL_ERROR | General error | Unspecified error |
| HAL_BUSY | Resource busy | Channel locked |
| HAL_TIMEOUT | Timeout | Operation timed out |

### 10.2 Fault Detection

```c
// Automatic fault detection
void PMU_Channel_CheckFaults(void) {
    for (uint16_t i = 0; i < PMU_CHANNEL_MAX_CHANNELS; i++) {
        PMU_Channel_t* ch = &channel_registry[i];

        // Check value bounds
        if (ch->value < ch->min_value || ch->value > ch->max_value) {
            ch->flags |= PMU_CHANNEL_FLAG_FAULT;
        }

        // Check for stuck ADC
        // Check for open load on PROFET
        // etc.
    }
}
```

### 10.3 Recovery Mechanisms

| Fault | Detection | Recovery |
|-------|-----------|----------|
| ADC stuck | No change > 1s | Reset ADC |
| PROFET overcurrent | Current sense | Auto-retry after delay |
| CAN timeout | No message > timeout | Use default value |
| Out of range | Value bounds check | Clamp to limits |

---

## See Also

- [Logic Functions Framework](logic-functions-framework.md)
- [Channel API Reference](../api/channel-api.md)
- [Channel Types Specification](../api/channel-types.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

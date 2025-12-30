# PMU-30 Channel Reference

**Version:** 3.0 | **Last Updated:** December 2025

The complete reference for PMU-30's unified channel system.

---

## Table of Contents

1. [Channel ID Assignment](#1-channel-id-assignment)
2. [Physical Inputs](#2-physical-inputs)
3. [Physical Outputs](#3-physical-outputs)
4. [Virtual Channels](#4-virtual-channels)
5. [System Channels](#5-system-channels)
6. [Output Sub-Channels](#6-output-sub-channels)
7. [C API Reference](#7-c-api-reference)
8. [JSON Configuration](#8-json-configuration)

---

## 1. Channel ID Assignment

### 1.1 Channel ID Ranges (Canonical Reference)

| Range | Type | Count | Description |
|-------|------|-------|-------------|
| **0-49** | Digital Inputs | 50 | Physical switch/button inputs (D0-D19 + reserved) |
| **50-99** | Analog Inputs | 50 | 0-5V sensor inputs, 10-bit (A0-A19 + reserved) |
| **100-129** | Power Outputs | 30 | PROFET high-side outputs (O0-O29) |
| **130-149** | Reserved | 20 | Future expansion |
| **150-157** | H-Bridge | 8 | 4 H-bridges × 2 channels (HB0-HB3) |
| **158-199** | Reserved | 42 | Future expansion |
| **200-999** | Virtual | 800 | Logic, Math, Timers, Tables, Filters, PID |
| **1000-1023** | System | 24 | Battery, temperatures, status, constants |
| **1100-1129** | Output Status | 30 | Per-output status codes |
| **1130-1159** | Output Current | 30 | Per-output current (mA) |
| **1160-1189** | Output Voltage | 30 | Per-output voltage (mV) |
| **1190-1219** | Output Active | 30 | Per-output active state |
| **1220-1249** | Analog Voltage | 30 | Per-analog raw voltage (mV) |
| **1250-1279** | Output Duty | 30 | Per-output duty cycle (0-1000) |

### 1.2 Channel Class Hierarchy

```
PMU_ChannelClass_t (pmu_channel.h)
│
├── Physical Inputs (0x00-0x1F)
│   ├── INPUT_ANALOG (0x00)      → ID: 50-99
│   ├── INPUT_DIGITAL (0x01)     → ID: 0-49
│   ├── INPUT_SWITCH (0x02)      → ID: 0-49
│   ├── INPUT_ROTARY (0x03)      → ID: 50-99
│   └── INPUT_FREQUENCY (0x04)   → ID: 0-49
│
├── Virtual Inputs (0x20-0x3F)
│   ├── INPUT_CAN (0x20)         → ID: 200-999
│   ├── INPUT_CALCULATED (0x21)  → ID: 200-999
│   └── INPUT_SYSTEM (0x22)      → ID: 1000-1023
│
├── Physical Outputs (0x40-0x5F)
│   ├── OUTPUT_POWER (0x40)      → ID: 100-129
│   ├── OUTPUT_PWM (0x41)        → ID: 100-129
│   ├── OUTPUT_HBRIDGE (0x42)    → ID: 150-157
│   └── OUTPUT_ANALOG (0x43)     → Reserved
│
└── Virtual Outputs (0x60-0x7F)
    ├── OUTPUT_FUNCTION (0x60)   → ID: 200-999
    ├── OUTPUT_TABLE (0x61)      → ID: 200-999
    ├── OUTPUT_ENUM (0x62)       → ID: 200-999
    ├── OUTPUT_NUMBER (0x63)     → ID: 200-999
    ├── OUTPUT_CAN (0x64)        → ID: 200-999
    └── OUTPUT_PID (0x65)        → ID: 200-999
```

---

## 2. Physical Inputs

### 2.1 Digital Inputs (ID: 0-49)

**Hardware:** 20 dedicated digital inputs (D0-D19)

| Parameter | Value |
|-----------|-------|
| Channels | 20 (D0-D19) |
| Logic Low | < 1.5V |
| Logic High | > 3.0V |
| Sample Rate | 1 kHz |
| Debounce | 0-10000 ms configurable |
| Value | 0 (low) or 1 (high) |

**Subtypes:**
- `switch_active_low` - Grounded when activated (internal pull-up)
- `switch_active_high` - 5V when activated (internal pull-down)
- `frequency` - Frequency/RPM measurement (0-20kHz)

**JSON Configuration:**
```json
{
  "channel_id": 0,
  "channel_type": "digital_input",
  "channel_name": "Headlight Switch",
  "input_pin": 0,
  "subtype": "switch_active_low",
  "debounce_ms": 50
}
```

### 2.2 Analog Inputs (ID: 50-99)

**Hardware:** 20 analog inputs (A0-A19), STM32H7 ADC

| Parameter | Value |
|-----------|-------|
| Channels | 20 (A0-A19) |
| Resolution | 10-bit (0-1023) |
| Voltage Range | 0-5V |
| Sample Rate | 1 kHz |
| Input Impedance | >100 kOhm |
| Protection | ESD, overvoltage to 36V |

**Subtypes:**
- `linear` - Linear voltage-to-value scaling
- `calibrated` - Multi-point calibration curve
- `rotary_switch` - Resistor ladder position detection

**Pullup Options:** `none`, `1m_down`, `10k_up`, `10k_down`, `100k_up`, `100k_down`

**JSON Configuration:**
```json
{
  "channel_id": 50,
  "channel_type": "analog_input",
  "channel_name": "Coolant Temp",
  "input_pin": 0,
  "subtype": "calibrated",
  "pullup_option": "10k_up",
  "calibration_points": [
    {"voltage": 0.5, "value": -400},
    {"voltage": 4.5, "value": 1200}
  ]
}
```

---

## 3. Physical Outputs

### 3.1 Power Outputs (ID: 100-129)

**Hardware:** 30 PROFET high-side switches (O0-O29)

| Parameter | Value |
|-----------|-------|
| Outputs | 30 (O0-O29) |
| Current Rating | 40A continuous per output |
| Inrush Current | 100-160A (1ms) |
| PWM Frequency | 1 Hz - 20 kHz |
| PWM Resolution | 0.1% (0-1000) |
| Total System Current | 200A max |

**Output Status Codes:**

| Code | Name | Description |
|------|------|-------------|
| 0 | OFF | Output disabled |
| 1 | ON | Output fully on |
| 2 | OC | Overcurrent protection triggered |
| 3 | OT | Over-temperature protection |
| 4 | SC | Short circuit detected |
| 5 | OL | Open load (no current detected) |
| 6 | PWM | PWM mode active |
| 7 | DISABLED | Programmatically disabled |

**JSON Configuration:**
```json
{
  "channel_id": 100,
  "channel_type": "power_output",
  "channel_name": "Headlights",
  "output_pins": [0, 1],
  "source_channel_id": 0,
  "pwm_frequency": 200,
  "soft_start_ms": 500,
  "current_limit": 20000,
  "inrush_current": 80000,
  "retry_count": 3,
  "retry_delay_ms": 1000
}
```

### 3.2 H-Bridge Outputs (ID: 150-157)

**Hardware:** 4 H-bridges (HB0-HB3), bidirectional motor control

| Parameter | Value |
|-----------|-------|
| H-Bridges | 4 (HB0-HB3) |
| Current | 30A continuous |
| Peak Current | 60A (100ms) |
| PWM | 1 Hz - 20 kHz |
| Value Range | -1000 to +1000 |

**Control Modes:**
- Forward: value > 0 (0 to +1000)
- Reverse: value < 0 (-1000 to 0)
- Brake: value = 0 with brake_mode = true
- Coast: value = 0 with brake_mode = false

**JSON Configuration:**
```json
{
  "channel_id": 150,
  "channel_type": "hbridge_output",
  "channel_name": "Wiper Motor",
  "hbridge_index": 0,
  "source_channel_id": 200,
  "pwm_frequency": 1000,
  "current_limit": 25000
}
```

---

## 4. Virtual Channels

Virtual channels (ID: 200-999) process and transform data. See [Logic Functions Reference](logic-functions.md) for complete function documentation.

### 4.1 Channel Types Summary

| Type | JSON `channel_type` | Description |
|------|---------------------|-------------|
| Logic | `logic` | Boolean operations, comparisons, state machines |
| Number | `number` | Math operations, constants |
| Timer | `timer` | Count up/down, delays |
| Filter | `filter` | Low-pass, moving average, median |
| Table 2D | `table_2d` | 1D interpolation lookup |
| Table 3D | `table_3d` | 2D interpolation lookup |
| PID | `pid` | PID controller |
| CAN RX | `can_rx` | CAN signal extraction |
| Switch | `switch` | Multi-position selector |

### 4.2 Quick Examples

**Logic (Hysteresis):**
```json
{
  "channel_id": 200,
  "channel_type": "logic",
  "channel_name": "Fan Enable",
  "operation": "hysteresis",
  "source_channel_id": 50,
  "upper_value": 850,
  "lower_value": 750
}
```

**Number (Math):**
```json
{
  "channel_id": 210,
  "channel_type": "number",
  "channel_name": "Average",
  "operation": "average",
  "source_channel_ids": [50, 51, 52]
}
```

**Timer:**
```json
{
  "channel_id": 220,
  "channel_type": "timer",
  "channel_name": "Run Time",
  "mode": "count_up",
  "trigger_channel_id": 0,
  "scale_ms": 1000
}
```

**PID:**
```json
{
  "channel_id": 230,
  "channel_type": "pid",
  "channel_name": "Idle Control",
  "input_channel_id": 300,
  "setpoint_channel_id": 231,
  "kp": 2.0, "ki": 0.1, "kd": 0.5,
  "output_min": 0, "output_max": 1000
}
```

---

## 5. System Channels

### 5.1 System Channel IDs (1000-1023)

| ID | Constant | Description | Unit |
|----|----------|-------------|------|
| 1000 | `PMU_CHANNEL_SYSTEM_BATTERY_V` | Battery voltage | mV |
| 1001 | `PMU_CHANNEL_SYSTEM_TOTAL_I` | Total current draw | mA |
| 1002 | `PMU_CHANNEL_SYSTEM_MCU_TEMP` | MCU die temperature | °C×10 |
| 1003 | `PMU_CHANNEL_SYSTEM_BOARD_TEMP_L` | Board temperature Left | °C×10 |
| 1004 | `PMU_CHANNEL_SYSTEM_BOARD_TEMP_R` | Board temperature Right | °C×10 |
| 1005 | `PMU_CHANNEL_SYSTEM_BOARD_TEMP_MAX` | Board temperature Max | °C×10 |
| 1006 | `PMU_CHANNEL_SYSTEM_UPTIME` | System uptime | seconds |
| 1007 | `PMU_CHANNEL_SYSTEM_STATUS` | System status flags | bitfield |
| 1008 | `PMU_CHANNEL_SYSTEM_USER_ERROR` | User error code | code |
| 1009 | `PMU_CHANNEL_SYSTEM_5V_OUTPUT` | 5V output voltage | mV |
| 1010 | `PMU_CHANNEL_SYSTEM_3V3_OUTPUT` | 3.3V output voltage | mV |
| 1011 | `PMU_CHANNEL_SYSTEM_IS_TURNING_OFF` | Shutdown in progress | bool |
| 1012 | `PMU_CHANNEL_CONST_ZERO` | Constant 0 | - |
| 1013 | `PMU_CHANNEL_CONST_ONE` | Constant 1 | - |

**Properties:**
- Read-only (updated by hardware drivers at 1kHz)
- Always enabled, no configuration required
- Can be used as `source_channel_id` for outputs

---

## 6. Output Sub-Channels

Real-time telemetry for each of the 30 outputs:

| Base ID | Range | Constant | Description | Unit |
|---------|-------|----------|-------------|------|
| 1100 | 1100-1129 | `PMU_CHANNEL_OUTPUT_STATUS_BASE` | Status code | enum |
| 1130 | 1130-1159 | `PMU_CHANNEL_OUTPUT_CURRENT_BASE` | Current | mA |
| 1160 | 1160-1189 | `PMU_CHANNEL_OUTPUT_VOLTAGE_BASE` | Voltage | mV |
| 1190 | 1190-1219 | `PMU_CHANNEL_OUTPUT_ACTIVE_BASE` | Active state | bool |
| 1220 | 1220-1249 | `PMU_CHANNEL_ANALOG_VOLTAGE_BASE` | Analog voltage | mV |
| 1250 | 1250-1279 | `PMU_CHANNEL_OUTPUT_DUTY_BASE` | Duty cycle | 0-1000 |

**Usage:** Add output index (0-29) to base ID:
```c
// Monitor output 5
int32_t status  = PMU_Channel_GetValue(1100 + 5);  // 1105
int32_t current = PMU_Channel_GetValue(1130 + 5);  // 1135
int32_t duty    = PMU_Channel_GetValue(1250 + 5);  // 1255
```

---

## 7. C API Reference

### 7.1 Core Functions

```c
#include "pmu_channel.h"

// Initialize channel system (call once at startup)
HAL_StatusTypeDef PMU_Channel_Init(void);

// Read any channel value
int32_t PMU_Channel_GetValue(uint16_t channel_id);

// Write to output/virtual channels
HAL_StatusTypeDef PMU_Channel_SetValue(uint16_t channel_id, int32_t value);

// Update input channels (for hardware drivers)
HAL_StatusTypeDef PMU_Channel_UpdateValue(uint16_t channel_id, int32_t value);

// Get channel metadata
const PMU_Channel_t* PMU_Channel_GetInfo(uint16_t channel_id);

// Find channel by name
const PMU_Channel_t* PMU_Channel_GetByName(const char* name);

// Enable/disable channel
HAL_StatusTypeDef PMU_Channel_SetEnabled(uint16_t channel_id, bool enabled);

// Generate unique ID for dynamic channels
uint16_t PMU_Channel_GenerateID(void);
```

### 7.2 Type Checking

```c
// Check channel classification
bool PMU_Channel_IsInput(PMU_ChannelClass_t hw_class);   // hw_class < 0x40
bool PMU_Channel_IsOutput(PMU_ChannelClass_t hw_class);  // hw_class >= 0x40
bool PMU_Channel_IsVirtual(PMU_ChannelClass_t hw_class); // 0x20-0x3F or 0x60+
bool PMU_Channel_IsPhysical(PMU_ChannelClass_t hw_class);
```

### 7.3 Data Structures

```c
typedef struct {
    uint16_t channel_id;            // Global ID (0-1279)
    PMU_ChannelClass_t hw_class;    // Hardware classification
    PMU_ChannelDir_t direction;     // INPUT/OUTPUT/BIDIR/VIRTUAL
    PMU_ChannelFormat_t format;     // RAW/PERCENT/VOLTAGE/CURRENT/BOOLEAN/etc.
    uint8_t physical_index;         // Hardware index
    uint8_t flags;                  // ENABLED/INVERTED/FAULT/OVERRIDE
    int32_t value;                  // Current value
    int32_t min_value, max_value;   // Value range
    char name[32];                  // Channel name
    char unit[8];                   // Unit string
} PMU_Channel_t;
```

---

## 8. JSON Configuration

### 8.1 Configuration File Structure (v3.0)

```json
{
  "version": "3.0",
  "device_name": "PMU-30",
  "channels": [
    { /* channel configs */ }
  ],
  "can_messages": [
    { /* CAN TX message configs */ }
  ]
}
```

### 8.2 Common Channel Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `channel_id` | int | Yes | Unique ID (see ranges above) |
| `channel_type` | string | Yes | Type identifier |
| `channel_name` | string | Yes | Display name (max 31 chars) |
| `source_channel_id` | int | Varies | Input source for outputs |

### 8.3 Channel Type Reference

| `channel_type` | ID Range | Description |
|----------------|----------|-------------|
| `digital_input` | 0-49 | Digital switch input |
| `analog_input` | 50-99 | Analog sensor input |
| `power_output` | 100-129 | PROFET power output |
| `hbridge_output` | 150-157 | H-bridge motor output |
| `logic` | 200-999 | Logic function |
| `number` | 200-999 | Math operation |
| `timer` | 200-999 | Timer channel |
| `filter` | 200-999 | Signal filter |
| `table_2d` | 200-999 | 1D lookup table |
| `table_3d` | 200-999 | 2D lookup table |
| `pid` | 200-999 | PID controller |
| `can_rx` | 200-999 | CAN signal input |
| `switch` | 200-999 | Multi-position switch |

---

## See Also

- [Logic Functions Reference](logic-functions.md) - Complete logic function documentation
- [Protocol Reference](protocol.md) - Communication protocol
- [Configuration Reference](configuration.md) - Full JSON schema
- [Getting Started Guide](../guides/getting-started.md) - Tutorial

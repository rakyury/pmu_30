# Channel Types Specification

**Version:** 1.0
**Date:** December 2024

---

## Table of Contents

1. [Overview](#1-overview)
2. [Physical Input Channels](#2-physical-input-channels)
3. [Virtual Input Channels](#3-virtual-input-channels)
4. [Physical Output Channels](#4-physical-output-channels)
5. [Virtual Output Channels](#5-virtual-output-channels)
6. [System Channels](#6-system-channels)
7. [Custom Channel Implementation](#7-custom-channel-implementation)

---

## 1. Overview

### 1.1 Channel Type Hierarchy

```
Channel Types
|
+-- Physical Inputs (0x00-0x1F)
|   +-- ANALOG (0x00)
|   +-- DIGITAL (0x01)
|   +-- SWITCH (0x02)
|   +-- ROTARY (0x03)
|   +-- FREQUENCY (0x04)
|
+-- Virtual Inputs (0x20-0x3F)
|   +-- CAN (0x20)
|   +-- CALCULATED (0x21)
|   +-- SYSTEM (0x22)
|
+-- Physical Outputs (0x40-0x5F)
|   +-- POWER (0x40)
|   +-- PWM (0x41)
|   +-- HBRIDGE (0x42)
|   +-- ANALOG (0x43)
|
+-- Virtual Outputs (0x60-0x7F)
    +-- FUNCTION (0x60)
    +-- TABLE (0x61)
    +-- ENUM (0x62)
    +-- NUMBER (0x63)
    +-- CAN (0x64)
    +-- PID (0x65)
```

---

## 2. Physical Input Channels

### 2.1 Analog Input (0x00)

**Type Code:** `PMU_CHANNEL_INPUT_ANALOG`

**Description:** 12-bit ADC input for voltage measurement (0-5V range)

**Hardware:** STM32H7 ADC with oversampling

| Parameter | Value |
|-----------|-------|
| Resolution | 12-bit (0-4095) |
| Voltage Range | 0-5V |
| Sample Rate | 1 kHz |
| Input Impedance | >100 kOhm |
| Protection | ESD, overvoltage to 36V |

**Value Formats:**

| Format | Range | Unit |
|--------|-------|------|
| RAW | 0-4095 | ADC counts |
| VOLTAGE | 0-5000 | mV |
| PERCENT | 0-1000 | 0.1% |

**Configuration Parameters:**

```json
{
  "channel_type": "analog_input",
  "input_pin": 0,
  "pullup_option": "10k_up",
  "subtype": "linear",
  "voltage_min": 0.5,
  "voltage_max": 4.5,
  "value_min": 0,
  "value_max": 100
}
```

**Pullup Options:**
- `none` - No pullup/pulldown
- `1m_down` - 1M to ground
- `10k_up` - 10K to 5V
- `10k_down` - 10K to ground
- `100k_up` - 100K to 5V
- `100k_down` - 100K to ground

---

### 2.2 Digital Input (0x01)

**Type Code:** `PMU_CHANNEL_INPUT_DIGITAL`

**Description:** Digital on/off input with configurable threshold

| Parameter | Value |
|-----------|-------|
| Logic Low | < 1.5V |
| Logic High | > 3.0V |
| Sample Rate | 1 kHz |
| Debounce | 0-10000 ms |

**Value:** 0 (low) or 1 (high)

**Configuration:**

```json
{
  "channel_type": "digital_input",
  "input_pin": 0,
  "subtype": "switch_active_low",
  "threshold_voltage": 2.5,
  "debounce_ms": 50
}
```

---

### 2.3 Switch Input (0x02)

**Type Code:** `PMU_CHANNEL_INPUT_SWITCH`

**Description:** Momentary switch with active high/low configuration

| Parameter | Value |
|-----------|-------|
| Debounce | 10-100 ms typical |
| Pull resistor | 10K internal |

**Subtypes:**
- `switch_active_low` - Grounded when pressed
- `switch_active_high` - 5V when pressed

---

### 2.4 Rotary Input (0x03)

**Type Code:** `PMU_CHANNEL_INPUT_ROTARY`

**Description:** Multi-position rotary switch

| Parameter | Value |
|-----------|-------|
| Positions | 2-12 typical |
| Encoding | Resistor ladder |

**Value:** Position number (0 to N-1)

**Configuration:**

```json
{
  "channel_type": "analog_input",
  "subtype": "rotary_switch",
  "input_pin": 5,
  "positions": [
    {"voltage": 0.0, "position": 0},
    {"voltage": 1.0, "position": 1},
    {"voltage": 2.0, "position": 2},
    {"voltage": 3.0, "position": 3}
  ]
}
```

---

### 2.5 Frequency Input (0x04)

**Type Code:** `PMU_CHANNEL_INPUT_FREQUENCY`

**Description:** Frequency/RPM measurement

| Parameter | Value |
|-----------|-------|
| Frequency Range | 0-20,000 Hz |
| Resolution | 1 Hz |
| Input Type | Hall effect, VR sensor |

**Configuration:**

```json
{
  "channel_type": "digital_input",
  "subtype": "frequency",
  "input_pin": 2,
  "threshold_voltage": 2.5,
  "trigger_edge": "rising",
  "number_of_teeth": 60,
  "timeout_ms": 1000
}
```

**RPM Calculation:**
```
RPM = (Frequency * 60) / number_of_teeth
```

---

## 3. Virtual Input Channels

### 3.1 CAN Input (0x20)

**Type Code:** `PMU_CHANNEL_INPUT_CAN`

**Description:** Signal extracted from CAN bus message

| Parameter | Value |
|-----------|-------|
| CAN Buses | 4 (2x CAN FD, 2x CAN 2.0) |
| Message ID | 11-bit or 29-bit |
| Signal Length | 1-64 bits |
| Byte Order | Little/Big endian |

**Configuration:**

```json
{
  "channel_type": "can_rx",
  "can_bus": 1,
  "message_id": 256,
  "is_extended": false,
  "start_bit": 0,
  "length": 16,
  "byte_order": "little_endian",
  "is_signed": false,
  "factor": 0.1,
  "offset": 0,
  "timeout_ms": 500
}
```

**Signal Extraction:**
```
raw_value = extract_bits(data, start_bit, length, byte_order)
value = (raw_value * factor) + offset
```

---

### 3.2 Calculated Input (0x21)

**Type Code:** `PMU_CHANNEL_INPUT_CALCULATED`

**Description:** Result from logic function

**Source:** Logic function output

**Value:** Any int32_t value

---

### 3.3 System Input (0x22)

**Type Code:** `PMU_CHANNEL_INPUT_SYSTEM`

**Description:** Internal system measurement

**Reserved IDs:** 1000-1023

---

## 4. Physical Output Channels

### 4.1 Power Output (0x40)

**Type Code:** `PMU_CHANNEL_OUTPUT_POWER`

**Description:** PROFET high-side switch output

| Parameter | Value |
|-----------|-------|
| Current Rating | 25-40A continuous |
| Inrush Current | 100-160A (1ms) |
| PWM Capable | Yes |
| PWM Frequency | 10 Hz - 30 kHz |

**Value Formats:**
- Boolean: 0 (off), 1 (on)
- PWM: 0-1000 (0.0-100.0%)

**Configuration:**

```json
{
  "channel_type": "power_output",
  "output_pins": [0],
  "source_channel": "logic_fan_control",
  "pwm_enabled": true,
  "pwm_frequency_hz": 100,
  "duty_channel": "table_fan_duty",
  "soft_start_ms": 500,
  "current_limit_a": 20.0,
  "inrush_current_a": 80.0,
  "retry_count": 3,
  "retry_delay_ms": 1000
}
```

**Protection Features:**
- Overcurrent detection
- Short circuit protection
- Thermal shutdown
- Open load detection

---

### 4.2 PWM Output (0x41)

**Type Code:** `PMU_CHANNEL_OUTPUT_PWM`

**Description:** Variable duty cycle output

| Parameter | Value |
|-----------|-------|
| Resolution | 12-bit (0.025%) |
| Frequency | 10 Hz - 30 kHz |

**Value:** 0-1000 (0.0-100.0%)

---

### 4.3 H-Bridge Output (0x42)

**Type Code:** `PMU_CHANNEL_OUTPUT_HBRIDGE`

**Description:** Bidirectional motor driver

| Parameter | Value |
|-----------|-------|
| Current | 30A continuous |
| Peak Current | 60A (100ms) |
| PWM | 10 Hz - 20 kHz |

**Value:** -1000 to +1000 (direction + speed)

**Configuration:**

```json
{
  "channel_type": "hbridge_output",
  "hbridge_index": 0,
  "source_channel": "logic_wiper_control",
  "duty_channel": "num_wiper_speed",
  "pwm_frequency_hz": 1000,
  "dead_time_us": 2,
  "current_limit_a": 25.0,
  "stall_timeout_ms": 500
}
```

**Control Modes:**
- Forward: value > 0
- Reverse: value < 0
- Brake: value = 0, brake_mode = true
- Coast: value = 0, brake_mode = false

---

### 4.4 Analog Output (0x43)

**Type Code:** `PMU_CHANNEL_OUTPUT_ANALOG`

**Description:** DAC output for analog signals

| Parameter | Value |
|-----------|-------|
| Resolution | 12-bit |
| Range | 0-3.3V or 0-5V |

**Value:** 0-4095

---

## 5. Virtual Output Channels

### 5.1 Function Output (0x60)

**Type Code:** `PMU_CHANNEL_OUTPUT_FUNCTION`

**Description:** Logic function result

**Source:** PMU_LogicFunction_t

---

### 5.2 Table Output (0x61)

**Type Code:** `PMU_CHANNEL_OUTPUT_TABLE`

**Description:** Lookup table result

**Configuration:**

```json
{
  "channel_type": "table_2d",
  "x_axis_channel": "crx_rpm",
  "x_values": [0, 1000, 2000, 3000, 4000],
  "output_values": [0, 250, 500, 750, 1000]
}
```

---

### 5.3 Enum Output (0x62)

**Type Code:** `PMU_CHANNEL_OUTPUT_ENUM`

**Description:** Enumerated state

**Configuration:**

```json
{
  "channel_type": "enum",
  "items": [
    {"value": 0, "text": "Off", "color": "#808080"},
    {"value": 1, "text": "Running", "color": "#00FF00"},
    {"value": 2, "text": "Fault", "color": "#FF0000"}
  ]
}
```

---

### 5.4 Number Output (0x63)

**Type Code:** `PMU_CHANNEL_OUTPUT_NUMBER`

**Description:** Constant or calculated number

**Configuration:**

```json
{
  "channel_type": "number",
  "operation": "constant",
  "constant_value": 500
}
```

**Operations:**
- `constant` - Fixed value
- `channel` - Copy from another channel
- `add`, `subtract`, `multiply`, `divide` - Math
- `min`, `max`, `clamp` - Range functions

---

### 5.5 CAN Output (0x64)

**Type Code:** `PMU_CHANNEL_OUTPUT_CAN`

**Description:** CAN message transmitter

**Configuration:**

```json
{
  "channel_type": "can_tx",
  "can_bus": 1,
  "message_id": 768,
  "is_extended": false,
  "cycle_time_ms": 100,
  "signals": [
    {
      "source_channel": "ai_throttle",
      "start_bit": 0,
      "length": 8,
      "byte_order": "little_endian",
      "factor": 1.0,
      "offset": 0
    }
  ]
}
```

---

### 5.6 PID Output (0x65)

**Type Code:** `PMU_CHANNEL_OUTPUT_PID`

**Description:** PID controller output

**Configuration:**

```json
{
  "channel_type": "pid",
  "input_channel": "ai_temperature",
  "setpoint_channel": "num_target_temp",
  "output_min": 0,
  "output_max": 1000,
  "kp": 2.0,
  "ki": 0.1,
  "kd": 0.5
}
```

---

## 6. System Channels

### 6.1 Reserved System Channel IDs

| ID | Name | Description | Unit |
|----|------|-------------|------|
| 1000 | BATTERY_V | Battery voltage | mV |
| 1001 | TOTAL_I | Total current draw | mA |
| 1002 | MCU_TEMP | MCU die temperature | 0.1°C |
| 1003 | BOARD_TEMP | Board temperature | 0.1°C |
| 1004 | UPTIME | System uptime | seconds |
| 1005-1019 | Reserved | Future use | - |
| 1020-1023 | User | User-defined | - |

### 6.2 System Channel Properties

- Read-only (cannot be set by user)
- Updated by hardware drivers
- Always enabled
- No configuration required

---

## 7. Custom Channel Implementation

### 7.1 Creating Custom Channel Type

```c
// Define custom channel handler
typedef struct {
    PMU_ChannelType_t type;
    HAL_StatusTypeDef (*init)(PMU_Channel_t* ch);
    int32_t (*read)(PMU_Channel_t* ch);
    HAL_StatusTypeDef (*write)(PMU_Channel_t* ch, int32_t value);
} PMU_ChannelHandler_t;

// Register handler
HAL_StatusTypeDef PMU_Channel_RegisterHandler(
    PMU_ChannelType_t type,
    PMU_ChannelHandler_t* handler
);
```

### 7.2 Example: Custom Sensor

```c
// Custom NTC temperature sensor handler
int32_t read_ntc_temp(PMU_Channel_t* ch) {
    // Read ADC
    uint16_t adc = PMU_ADC_Read(ch->physical_index);

    // Convert to resistance
    float resistance = 10000.0f * adc / (4095 - adc);

    // Steinhart-Hart equation
    float temp = calculate_ntc_temp(resistance);

    return (int32_t)(temp * 10);  // Return in 0.1°C
}

PMU_ChannelHandler_t ntc_handler = {
    .type = PMU_CHANNEL_INPUT_ANALOG,
    .init = NULL,
    .read = read_ntc_temp,
    .write = NULL
};
```

---

## See Also

- [Channel API Reference](channel-api.md)
- [Unified Channel System](../architecture/unified-channel-system.md)
- [Getting Started with Channels](../guides/getting-started-channels.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

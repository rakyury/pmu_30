# Configuration Reference

**Version:** 3.0
**Date:** December 2025

---

## 1. Configuration Overview

PMU-30 configuration is stored in JSON format and manages all aspects of device operation.

### JSON Schema Version 3.0

```json
{
  "version": "3.0",
  "device": { ... },
  "can_messages": [ ... ],
  "channels": [ ... ],
  "settings": {
    "device": { ... },
    "can_a": { ... },
    "can_b": { ... },
    "standard_can_stream": { ... },
    "power": { ... },
    "system": { ... },
    "safety": { ... }
  }
}
```

---

## 2. Device Configuration

```json
{
  "device": {
    "name": "PMU-30",
    "serial_number": "R2M-2025-00001",
    "firmware_version": "3.0.0",
    "hardware_revision": "B",
    "created": "2025-12-22T10:00:00",
    "modified": "2025-12-22T12:30:00"
  }
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| name | string | Device identifier |
| serial_number | string | Serial number |
| firmware_version | string | Read from device |
| hardware_revision | string | Read from device |
| created | string | ISO 8601 creation date |
| modified | string | ISO 8601 modification date |

---

## 3. CAN Messages (Level 1)

Two-level CAN architecture: CAN Messages define frame properties, CAN Inputs extract signals.

```json
{
  "can_messages": [
    {
      "id": "msg_ecu_base",
      "name": "ECU Base Data",
      "can_bus": 1,
      "base_id": 256,
      "is_extended": false,
      "message_type": "normal",
      "frame_count": 1,
      "dlc": 8,
      "timeout_ms": 500,
      "enabled": true,
      "description": "ECU broadcast data"
    }
  ]
}
```

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| id | string | ^[a-zA-Z][a-zA-Z0-9_]*$ | Unique message identifier |
| name | string | - | Human-readable name |
| can_bus | integer | 1-4 | CAN bus number |
| base_id | integer | 0-0x1FFFFFFF | Base CAN ID |
| is_extended | boolean | - | Use 29-bit extended ID |
| message_type | string | normal, compound, pmu1_rx, pmu2_rx, pmu3_rx | Message type |
| frame_count | integer | 1-8 | Number of frames (compound) |
| dlc | integer | 0-64 | Data length code |
| timeout_ms | integer | 0-65535 | Reception timeout |
| enabled | boolean | - | Message enabled |

### Message Types

| Type | Description |
|------|-------------|
| normal | Standard single-frame message |
| compound | Multi-frame message (frame_count > 1) |
| pmu1_rx | Ecumaster PMU 1 RX protocol |
| pmu2_rx | Ecumaster PMU 2 RX protocol |
| pmu3_rx | Ecumaster PMU 3 RX protocol |

---

## 4. Channels Configuration

Channels are stored in a unified array with `channel_type` discriminator.

### 4.1 Digital Input

```json
{
  "id": "di_ignition",
  "channel_type": "digital_input",
  "enabled": true,
  "subtype": "switch_active_high",
  "input_pin": 0,
  "enable_pullup": true,
  "threshold_voltage": 2.5,
  "debounce_ms": 50,
  "description": "Ignition switch"
}
```

#### Digital Input Subtypes

| Subtype | Description |
|---------|-------------|
| switch_active_low | Switch, active when low |
| switch_active_high | Switch, active when high |
| frequency | Frequency measurement |
| rpm | RPM measurement (with number_of_teeth) |
| flex_fuel | Flex fuel sensor |
| beacon | Beacon/strobe input |
| puls_oil_sensor | Pulsed oil sensor |

### 4.2 Analog Input

```json
{
  "id": "ai_coolant_temp",
  "channel_type": "analog_input",
  "enabled": true,
  "subtype": "calibrated",
  "input_pin": 0,
  "pullup_option": "10k_up",
  "decimal_places": 1,
  "calibration_points": [
    { "voltage": 0.5, "value": 120.0 },
    { "voltage": 2.5, "value": 80.0 },
    { "voltage": 4.5, "value": -40.0 }
  ]
}
```

#### Analog Input Subtypes

| Subtype | Description |
|---------|-------------|
| switch_active_low | Switch with voltage threshold |
| switch_active_high | Switch with voltage threshold |
| rotary_switch | Multi-position rotary switch |
| linear | Linear voltage to value mapping |
| calibrated | Calibration curve lookup |

#### Pullup Options

| Option | Description |
|--------|-------------|
| none | No pullup/pulldown |
| 1m_down | 1M pulldown |
| 10k_up | 10K pullup |
| 10k_down | 10K pulldown |
| 100k_up | 100K pullup |
| 100k_down | 100K pulldown |

### 4.3 Power Output

```json
{
  "id": "out_fuel_pump",
  "channel_type": "power_output",
  "enabled": true,
  "output_pins": [0, 1],
  "source_channel": "logic_fuel_pump",
  "pwm_enabled": false,
  "pwm_frequency_hz": 1000,
  "duty_channel": "",
  "duty_fixed": 100.0,
  "soft_start_ms": 100,
  "current_limit_a": 15.0,
  "inrush_current_a": 40.0,
  "inrush_time_ms": 50,
  "retry_count": 3,
  "retry_forever": false
}
```

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| output_pins | array | 0-29 | Output pin numbers (max 3) |
| source_channel | string | - | Boolean control channel |
| pwm_enabled | boolean | - | Enable PWM mode |
| pwm_frequency_hz | integer | 1-20000 | PWM frequency |
| duty_channel | string | - | Duty cycle source channel |
| duty_fixed | number | 0-100 | Fixed duty cycle % |
| soft_start_ms | integer | 0-5000 | Soft start duration |
| current_limit_a | number | 0.1-40.0 | Current limit |
| inrush_current_a | number | 0.1-160.0 | Inrush current limit |
| inrush_time_ms | integer | 0-1000 | Inrush time window |
| retry_count | integer | 0-10 | Retry on fault |
| retry_forever | boolean | - | Retry indefinitely |

### 4.4 CAN RX (CAN Input - Level 2)

```json
{
  "id": "crx_rpm",
  "channel_type": "can_rx",
  "enabled": true,
  "message_ref": "msg_ecu_base",
  "frame_offset": 0,
  "data_type": "unsigned",
  "data_format": "16bit",
  "byte_order": "little_endian",
  "byte_offset": 0,
  "start_bit": 0,
  "bit_length": 16,
  "multiplier": 1.0,
  "divider": 1.0,
  "offset": 0.0,
  "decimal_places": 0,
  "default_value": 0.0,
  "timeout_behavior": "set_zero"
}
```

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| message_ref | string | - | Reference to can_messages[].id |
| frame_offset | integer | 0-7 | Frame offset (compound messages) |
| data_type | string | unsigned, signed, float | Data type |
| data_format | string | 8bit, 16bit, 32bit, custom | Data format |
| byte_order | string | little_endian, big_endian | Byte order |
| byte_offset | integer | 0-7 | Starting byte |
| start_bit | integer | 0-63 | Start bit (custom format) |
| bit_length | integer | 1-64 | Bit length (custom format) |
| multiplier | number | - | Scale multiplier |
| divider | number | != 0 | Scale divider |
| offset | number | - | Value offset |
| decimal_places | integer | 0-6 | Display precision |
| default_value | number | - | Default on timeout |
| timeout_behavior | string | use_default, hold_last, set_zero | Timeout action |

### 4.5 CAN TX (CAN Output)

```json
{
  "id": "ctx_pmu_status",
  "channel_type": "can_tx",
  "enabled": true,
  "name": "PMU Status",
  "can_bus": 1,
  "message_id": 1536,
  "is_extended": false,
  "dlc": 8,
  "transmit_mode": "cycle",
  "cycle_frequency_hz": 20,
  "trigger_channel": "",
  "trigger_edge": "rising",
  "signals": [
    {
      "byte_offset": 0,
      "data_type": "unsigned",
      "data_format": "16bit",
      "byte_order": "little_endian",
      "source_channel": "ai_battery_voltage",
      "multiplier": 100.0
    }
  ]
}
```

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| can_bus | integer | 1-2 | CAN bus |
| message_id | integer | 0-0x1FFFFFFF | CAN ID |
| is_extended | boolean | - | 29-bit extended ID |
| dlc | integer | 0-8 | Data length |
| transmit_mode | string | cycle, triggered | Transmission mode |
| cycle_frequency_hz | integer | 1-1000 | Cycle frequency |
| trigger_channel | string | - | Trigger source channel |
| trigger_edge | string | rising, falling, both | Trigger edge |
| signals | array | - | Signal mappings (max 8) |

### 4.6 Logic Channel

```json
{
  "id": "logic_fan_control",
  "channel_type": "logic",
  "enabled": true,
  "operation": "greater",
  "channel": "ai_coolant_temp",
  "constant": 95.0,
  "true_delay_s": 0.0,
  "false_delay_s": 5.0
}
```

#### Logic Operations

| Operation | Description | Parameters |
|-----------|-------------|------------|
| is_true | Input is true | channel |
| is_false | Input is false | channel |
| equal | A == constant | channel, constant |
| not_equal | A != constant | channel, constant |
| less | A < constant | channel, constant |
| greater | A > constant | channel, constant |
| less_equal | A <= constant | channel, constant |
| greater_equal | A >= constant | channel, constant |
| in_range | lower <= A <= upper | channel, lower_value, upper_value |
| and | A AND B | channel, channel_2 |
| or | A OR B | channel, channel_2 |
| xor | A XOR B | channel, channel_2 |
| not | NOT A | channel |
| nand | NOT(A AND B) | channel, channel_2 |
| nor | NOT(A OR B) | channel, channel_2 |
| edge_rising | Rising edge detect | channel |
| edge_falling | Falling edge detect | channel |
| changed | Value changed | channel, threshold, time_on_s |
| hysteresis | Hysteresis comparator | channel, upper_value, lower_value, polarity |
| set_reset_latch | SR latch | set_channel, reset_channel, default_state |
| toggle | Toggle on edge | toggle_channel, edge |
| pulse | Pulse generator | channel, pulse_count, time_on_s, retrigger |
| flash | Oscillator | channel, time_on_s, time_off_s |

### 4.7 Number Channel

```json
{
  "id": "num_total_current",
  "channel_type": "number",
  "enabled": true,
  "operation": "add",
  "inputs": ["out_current_1", "out_current_2", "out_current_3"],
  "constant_value": 0.0,
  "clamp_min": 0.0,
  "clamp_max": 200.0
}
```

| Operation | Description |
|-----------|-------------|
| constant | Fixed value |
| add | Sum of inputs |
| subtract | A - B |
| multiply | A * B |
| divide | A / B |
| min | Minimum of inputs |
| max | Maximum of inputs |
| average | Average of inputs |
| abs | Absolute value |
| scale | multiplier * input + offset |
| clamp | Clamp to min/max |
| conditional | If condition then A else B |

### 4.8 Timer Channel

```json
{
  "id": "timer_engine_runtime",
  "channel_type": "timer",
  "enabled": true,
  "start_channel": "di_ignition",
  "start_edge": "rising",
  "stop_channel": "",
  "stop_edge": "falling",
  "mode": "count_up",
  "limit_hours": 999,
  "limit_minutes": 59,
  "limit_seconds": 59
}
```

### 4.9 Filter Channel

```json
{
  "id": "filter_oil_pressure",
  "channel_type": "filter",
  "enabled": true,
  "filter_type": "moving_avg",
  "input_channel": "ai_oil_pressure",
  "window_size": 10,
  "time_constant": 0.1
}
```

| Filter Type | Description |
|-------------|-------------|
| moving_avg | Moving average |
| low_pass | Low-pass IIR filter |
| min_window | Minimum over window |
| max_window | Maximum over window |
| median | Median filter |

### 4.10 Table 2D Channel

```json
{
  "id": "table_fan_speed",
  "channel_type": "table_2d",
  "enabled": true,
  "x_axis_channel": "ai_coolant_temp",
  "x_axis_type": "channel",
  "interpolation": "linear",
  "clamp_output": true,
  "data": [
    { "x": 70.0, "y": 0.0 },
    { "x": 85.0, "y": 50.0 },
    { "x": 95.0, "y": 80.0 },
    { "x": 105.0, "y": 100.0 }
  ]
}
```

### 4.11 Table 3D Channel

```json
{
  "id": "table_boost_target",
  "channel_type": "table_3d",
  "enabled": true,
  "x_axis_channel": "crx_rpm",
  "y_axis_channel": "crx_tps",
  "interpolation": "linear",
  "x_values": [1000, 2000, 3000, 4000, 5000],
  "y_values": [0, 25, 50, 75, 100],
  "data": [
    [0.0, 0.2, 0.4, 0.6, 0.8],
    [0.0, 0.3, 0.6, 0.9, 1.0],
    [0.0, 0.4, 0.8, 1.0, 1.2],
    [0.0, 0.5, 0.9, 1.1, 1.3],
    [0.0, 0.6, 1.0, 1.2, 1.4]
  ]
}
```

### 4.12 Switch Channel

```json
{
  "id": "switch_lights_mode",
  "channel_type": "switch",
  "enabled": true,
  "switch_type": "latching",
  "input_up_channel": "di_button_up",
  "input_up_edge": "rising",
  "input_down_channel": "di_button_down",
  "input_down_edge": "rising",
  "state_first": 0,
  "state_last": 3,
  "state_default": 0
}
```

### 4.13 Enum Channel

```json
{
  "id": "enum_gear",
  "channel_type": "enum",
  "enabled": true,
  "is_bitfield": false,
  "items": [
    { "value": 0, "text": "Neutral", "color": "#808080" },
    { "value": 1, "text": "1st", "color": "#00FF00" },
    { "value": 2, "text": "2nd", "color": "#00FF00" },
    { "value": 3, "text": "3rd", "color": "#00FF00" },
    { "value": 4, "text": "4th", "color": "#00FF00" },
    { "value": 5, "text": "5th", "color": "#00FF00" },
    { "value": 6, "text": "6th", "color": "#00FF00" },
    { "value": -1, "text": "Reverse", "color": "#FF0000" }
  ]
}
```

---

## 5. Settings Configuration

### 5.1 CAN Bus Settings

```json
{
  "settings": {
    "can_a": {
      "enabled": true,
      "bitrate": "500 kbps",
      "fd_enabled": false,
      "fd_bitrate": "2 Mbps",
      "terminator": false,
      "listen_only": false
    },
    "can_b": {
      "enabled": false,
      "bitrate": "500 kbps",
      "fd_enabled": false,
      "fd_bitrate": "2 Mbps",
      "terminator": false,
      "listen_only": false
    },
    "can": {
      "node_id": 1,
      "auto_retransmit": true
    }
  }
}
```

#### Bitrate Options

| Classic CAN | CAN FD Data Rate |
|-------------|------------------|
| 125 kbps | 1 Mbps |
| 250 kbps | 2 Mbps |
| 500 kbps | 4 Mbps |
| 1000 kbps | 5 Mbps |
| - | 8 Mbps |

### 5.2 Standard CAN Stream

Ecumaster-compatible PMU parameter broadcast.

```json
{
  "settings": {
    "standard_can_stream": {
      "enabled": true,
      "can_bus": 1,
      "base_id": 1536,
      "is_extended": false,
      "include_extended_frames": false
    }
  }
}
```

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| enabled | boolean | - | Enable stream |
| can_bus | integer | 1-2 | CAN bus (1=CAN A, 2=CAN B) |
| base_id | integer | 0-2047 | Base CAN ID (uses 8 consecutive) |
| is_extended | boolean | - | Use 29-bit extended IDs |
| include_extended_frames | boolean | - | Include frames 8-15 (PMU-30 specific) |

#### PMU-30 Hardware

| Resource | Count |
|----------|-------|
| Power Outputs | 30 (o1-o30) |
| Analog Inputs | 20 (a1-a20) |
| Digital Inputs | 8 (d1-d8) |
| H-Bridges | 4 (hb1-hb4) |
| Low-Side Outputs | 6 (l1-l6) |

#### Standard Stream Frames (8 frames at 20/62.5 Hz)

| Frame | CAN ID | Rate | Content |
|-------|--------|------|---------|
| 0 | BaseID+0 | 20 Hz | System Status & Temperatures |
| 1 | BaseID+1 | 20 Hz | Output States o1-o16 |
| 2 | BaseID+2 | 62.5 Hz | Analog Inputs a1-a8 |
| 3 | BaseID+3 | 62.5 Hz | Analog Inputs a9-a16 |
| 4 | BaseID+4 | 20 Hz | Output Currents o1-o8 |
| 5 | BaseID+5 | 20 Hz | Output Currents o9-o16 |
| 6 | BaseID+6 | 20 Hz | Output Voltages o1-o8 |
| 7 | BaseID+7 | 20 Hz | Output Voltages o9-o16 |

#### Extended Frames (PMU-30 specific, covers all 30 outputs)

| Frame | CAN ID | Rate | Content |
|-------|--------|------|---------|
| 8 | BaseID+8 | 20 Hz | Output States o17-o30 |
| 9 | BaseID+9 | 20 Hz | Output Currents o17-o24 |
| 10 | BaseID+10 | 20 Hz | Output Currents o25-o30 |
| 11 | BaseID+11 | 20 Hz | Output Voltages o17-o24 |
| 12 | BaseID+12 | 20 Hz | Output Voltages o25-o30 |
| 13 | BaseID+13 | 62.5 Hz | Analog Inputs a17-a20 |
| 14 | BaseID+14 | 20 Hz | Digital Inputs d1-d8 |
| 15 | BaseID+15 | 20 Hz | H-Bridge Status hb1-hb4 |

### 5.3 Power Settings

```json
{
  "settings": {
    "power": {
      "nominal_voltage": 12.0,
      "low_voltage_warning": 10.5,
      "low_voltage_cutoff": 9.0,
      "high_voltage_cutoff": 16.0
    }
  }
}
```

### 5.4 System Settings

```json
{
  "settings": {
    "system": {
      "units": "Metric (C, km/h)",
      "log_level": "Warning",
      "watchdog_timeout_ms": 1000,
      "heartbeat_interval_ms": 1000
    }
  }
}
```

### 5.5 Safety Settings

```json
{
  "settings": {
    "safety": {
      "safe_state": "All Outputs Off",
      "startup_delay_ms": 500,
      "max_total_current_a": 100.0
    }
  }
}
```

| Safe State Options |
|-------------------|
| All Outputs Off |
| Maintain Last State |
| Custom Profile |

---

## 6. Migration from v2.0 to v3.0

### Automatic Migration

The configurator automatically migrates v2.0 configurations:

1. **CAN RX channels**: Legacy fields (`can_bus`, `message_id`, `is_extended`) are converted to `message_ref`
2. **CAN Messages**: Unique message objects are created from CAN RX channels
3. **Scaling**: `factor` is converted to `multiplier`/`divider`
4. **Settings**: New sections are added with defaults

### Breaking Changes

| v2.0 | v3.0 |
|------|------|
| `factor` (can_rx) | `multiplier`, `divider` |
| `value_type` (can_rx) | `data_type` |
| inline CAN bus/ID | `message_ref` reference |

---

## 7. Firmware API

### Load Configuration

```c
PMU_JSON_Status_t PMU_JSON_LoadFromString(const char* json, uint32_t len, PMU_JSON_LoadStats_t* stats);
PMU_JSON_Status_t PMU_JSON_LoadFromFlash(uint32_t addr, PMU_JSON_LoadStats_t* stats);
```

### Validate Configuration

```c
bool PMU_JSON_Validate(const char* json, uint32_t len, char* error, uint32_t error_len);
```

### Get Channel Value

```c
float PMU_Channel_GetValue(const char* channel_id);
bool PMU_Channel_GetBool(const char* channel_id);
```

---

## 8. Default Values

| Category | Parameter | Default |
|----------|-----------|---------|
| Device | startup_delay_ms | 500 |
| Device | watchdog_timeout_ms | 1000 |
| CAN | bitrate | 500 kbps |
| CAN | timeout_ms | 500 |
| Output | pwm_frequency_hz | 1000 |
| Output | soft_start_ms | 100 |
| Output | retry_count | 3 |
| Output | current_limit_a | 15.0 |
| Power | nominal_voltage | 12.0 |
| Power | low_voltage_cutoff | 9.0 |
| Stream | base_id | 0x600 |

---

## See Also

- [Standard CAN Stream](../standard_can_stream.md)
- [Channel Types](../api/channel-types.md)
- [Troubleshooting Guide](troubleshooting-guide.md)

---

**Document Version:** 3.0
**Last Updated:** December 2025

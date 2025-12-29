# PMU-30 Configuration Reference

**Version:** 3.0 | **Last Updated:** December 2025

Complete JSON configuration schema and parameters reference.

---

## Table of Contents

1. [Configuration Structure](#1-configuration-structure)
2. [Device Settings](#2-device-settings)
3. [Channel Configuration](#3-channel-configuration)
4. [CAN Messages](#4-can-messages)
5. [Complete Example](#5-complete-example)

---

## 1. Configuration Structure

### 1.1 Root Schema (v3.0)

```json
{
  "version": "3.0",
  "device_name": "PMU-30",
  "device_settings": { },
  "channels": [ ],
  "can_messages": [ ]
}
```

### 1.2 Schema Changes from v2.0

| v2.0 | v3.0 | Change |
|------|------|--------|
| `id: "100"` | `channel_id: 100` | String → Integer |
| `name:` | `channel_name:` | Renamed |
| CAN signals in channels | `can_messages:` array | Separated |

---

## 2. Device Settings

```json
{
  "device_settings": {
    "can1_baudrate": 500000,
    "can2_baudrate": 500000,
    "can1_termination": true,
    "can2_termination": false,
    "wifi_enabled": true,
    "wifi_ssid": "PMU30_XXXX",
    "wifi_password": "",
    "bluetooth_enabled": true,
    "telemetry_rate_hz": 50
  }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `can1_baudrate` | int | 500000 | CAN1 bit rate (125k-1M, or 5M for FD) |
| `can2_baudrate` | int | 500000 | CAN2 bit rate |
| `can1_termination` | bool | true | Enable 120Ω termination on CAN1 |
| `can2_termination` | bool | false | Enable 120Ω termination on CAN2 |
| `wifi_enabled` | bool | true | Enable WiFi AP mode |
| `wifi_ssid` | string | auto | WiFi network name |
| `wifi_password` | string | "" | WiFi password (empty = open) |
| `bluetooth_enabled` | bool | true | Enable Bluetooth |
| `telemetry_rate_hz` | int | 50 | Telemetry update rate (10-500) |

---

## 3. Channel Configuration

### 3.1 Digital Input

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

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | int | Yes | 0-49 |
| `channel_type` | string | Yes | `"digital_input"` |
| `channel_name` | string | Yes | Display name (max 31 chars) |
| `input_pin` | int | Yes | Hardware pin 0-19 |
| `subtype` | string | No | `switch_active_low`, `switch_active_high`, `frequency` |
| `debounce_ms` | int | No | Debounce time 0-10000ms (default: 50) |
| `threshold_voltage` | float | No | Threshold voltage for frequency mode |

### 3.2 Analog Input

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

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | int | Yes | 50-99 |
| `channel_type` | string | Yes | `"analog_input"` |
| `channel_name` | string | Yes | Display name |
| `input_pin` | int | Yes | Hardware pin 0-19 |
| `subtype` | string | No | `linear`, `calibrated`, `rotary_switch` |
| `pullup_option` | string | No | `none`, `1m_down`, `10k_up`, `10k_down`, `100k_up`, `100k_down` |
| `voltage_min` | float | Linear | Min voltage for scaling |
| `voltage_max` | float | Linear | Max voltage for scaling |
| `value_min` | int | Linear | Output at voltage_min |
| `value_max` | int | Linear | Output at voltage_max |
| `calibration_points` | array | Calibrated | Voltage-to-value pairs |

### 3.3 Power Output

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
  "retry_delay_ms": 1000,
  "shed_priority": 2
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | int | Yes | 100-129 |
| `channel_type` | string | Yes | `"power_output"` |
| `channel_name` | string | Yes | Display name |
| `output_pins` | array | Yes | Pin indices [0-29], multiple for merging |
| `source_channel_id` | int | Yes | Input source channel |
| `duty_channel_id` | int | No | PWM duty source (0-1000) |
| `pwm_frequency` | int | No | PWM frequency 1-20000 Hz |
| `soft_start_ms` | int | No | Soft start ramp time 0-5000ms |
| `current_limit` | int | No | Current limit in mA |
| `inrush_current` | int | No | Inrush current limit in mA |
| `retry_count` | int | No | Fault retry attempts (0-10) |
| `retry_delay_ms` | int | No | Delay between retries |
| `shed_priority` | int | No | Load shedding priority (0-10, see below) |

**Load Shedding Priority:**

The `shed_priority` field controls which outputs are disabled first during fault conditions (overcurrent, overtemperature, low voltage):

| Priority | Behavior | Example Use Case |
|----------|----------|------------------|
| **0** | Never shed (critical) | ECU power, fuel pump, ignition |
| **1-3** | Shed last (important) | Headlights, brake lights |
| **4-6** | Shed middle (normal) | Interior lights, accessories |
| **7-10** | Shed first (low priority) | Heated seats, auxiliary loads |

When load shedding activates, outputs with the highest `shed_priority` number are disabled first until the fault condition clears.

### 3.4 H-Bridge Output

```json
{
  "channel_id": 150,
  "channel_type": "hbridge_output",
  "channel_name": "Wiper Motor",
  "hbridge_index": 0,
  "source_channel_id": 200,
  "duty_channel_id": 250,
  "pwm_frequency": 1000,
  "current_limit": 25000
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | int | Yes | 150-157 |
| `channel_type` | string | Yes | `"hbridge_output"` |
| `channel_name` | string | Yes | Display name |
| `hbridge_index` | int | Yes | H-bridge index 0-3 |
| `source_channel_id` | int | Yes | Direction control (-1000 to +1000) |
| `duty_channel_id` | int | No | Optional separate duty source |
| `pwm_frequency` | int | No | PWM frequency 1-20000 Hz |
| `current_limit` | int | No | Current limit in mA |
| `brake_mode` | bool | No | Brake on zero (vs coast) |

### 3.5 Logic Channel

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

See [Logic Functions Reference](logic-functions.md) for all operations.

### 3.6 Number Channel

```json
{
  "channel_id": 210,
  "channel_type": "number",
  "channel_name": "Average",
  "operation": "average",
  "source_channel_ids": [50, 51, 52]
}
```

| Operation | Parameters |
|-----------|------------|
| `constant` | `constant_value` |
| `add`, `multiply` | `source_channel_ids` (array) |
| `subtract`, `divide`, `modulo` | `source_channel_ids` (2 elements) |
| `min`, `max`, `average` | `source_channel_ids` (2-8 elements) |
| `abs` | `source_channel_id` |
| `scale` | `source_channel_id`, `factor`, `offset` |
| `clamp` | `source_channel_id`, `min_value`, `max_value` |

### 3.7 Timer Channel

```json
{
  "channel_id": 220,
  "channel_type": "timer",
  "channel_name": "Run Time",
  "mode": "count_up",
  "trigger_channel_id": 0,
  "reset_channel_id": 1,
  "scale_ms": 1000
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `mode` | string | `count_up`, `count_down`, `retriggerable`, `stopwatch` |
| `trigger_channel_id` | int | Start/run trigger |
| `reset_channel_id` | int | Reset trigger |
| `max_value` | int | Maximum count value |
| `initial_value` | int | Starting value (count_down) |
| `scale_ms` | int | Time per increment (ms) |
| `delay_ms` | int | Delay time (retriggerable) |

### 3.8 Filter Channel

```json
{
  "channel_id": 230,
  "channel_type": "filter",
  "channel_name": "Filtered",
  "source_channel_id": 50,
  "filter_type": "low_pass",
  "time_constant_ms": 500
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter_type` | string | `low_pass`, `moving_average`, `median`, `min_window`, `max_window` |
| `time_constant_ms` | int | Low-pass time constant |
| `window_size` | int | Moving average/median samples |

### 3.9 Table 2D Channel

```json
{
  "channel_id": 240,
  "channel_type": "table_2d",
  "channel_name": "PWM Curve",
  "x_axis_channel_id": 50,
  "x_values": [0, 250, 500, 750, 1000],
  "output_values": [0, 100, 300, 700, 1000]
}
```

### 3.10 Table 3D Channel

```json
{
  "channel_id": 241,
  "channel_type": "table_3d",
  "channel_name": "Map",
  "x_axis_channel_id": 300,
  "y_axis_channel_id": 301,
  "x_values": [1000, 2000, 3000],
  "y_values": [0, 50, 100],
  "z_values": [[100, 200, 300], [150, 250, 350], [200, 300, 400]]
}
```

### 3.11 PID Channel

PID controllers for closed-loop control. See [Logic Functions Reference](logic-functions.md#9-pid-controller) for comprehensive documentation, tuning guide, and examples.

```json
{
  "channel_id": 250,
  "channel_type": "pid",
  "channel_name": "Fan Control",
  "input_channel_id": 50,
  "setpoint_channel_id": 251,
  "setpoint_value": 85.0,
  "kp": 2.0,
  "ki": 0.1,
  "kd": 0.5,
  "output_min": 0,
  "output_max": 1000,
  "sample_time_ms": 100,
  "anti_windup": true,
  "derivative_filter": true,
  "derivative_filter_coeff": 0.1,
  "reversed": false,
  "enabled": true
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_channel_id` | int | Required | Process variable source |
| `setpoint_channel_id` | int | Optional | Dynamic setpoint source |
| `setpoint_value` | float | 0 | Fixed setpoint (if no channel) |
| `kp`, `ki`, `kd` | float | 1, 0, 0 | PID gains |
| `output_min`, `output_max` | float | 0, 1000 | Output limits |
| `sample_time_ms` | int | 100 | Loop period (ms) |
| `anti_windup` | bool | true | Prevent integral windup |
| `derivative_filter` | bool | false | Filter derivative term |
| `derivative_filter_coeff` | float | 0.1 | Filter coefficient (0-1) |
| `reversed` | bool | false | Reverse-acting (for cooling) |
| `enabled` | bool | true | Controller enabled |

### 3.12 CAN RX Channel

```json
{
  "channel_id": 300,
  "channel_type": "can_rx",
  "channel_name": "Engine RPM",
  "can_bus": 1,
  "message_id": 256,
  "is_extended": false,
  "start_bit": 0,
  "length": 16,
  "byte_order": "little_endian",
  "is_signed": false,
  "factor": 1.0,
  "offset": 0,
  "timeout_ms": 500
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `can_bus` | int | CAN bus 1-4 |
| `message_id` | int | CAN message ID |
| `is_extended` | bool | 29-bit extended ID |
| `start_bit` | int | Signal start bit |
| `length` | int | Signal bit length |
| `byte_order` | string | `little_endian` or `big_endian` |
| `is_signed` | bool | Signed value |
| `factor` | float | Scale factor |
| `offset` | float | Offset |
| `timeout_ms` | int | Signal timeout |

### 3.13 Switch Channel

```json
{
  "channel_id": 260,
  "channel_type": "switch",
  "channel_name": "Mode Select",
  "source_channel_id": 55,
  "positions": [
    {"min": 0, "max": 100, "output": 0},
    {"min": 200, "max": 300, "output": 1},
    {"min": 400, "max": 500, "output": 2}
  ]
}
```

---

## 4. CAN Messages

### 4.1 CAN TX Configuration

CAN transmit messages are defined in a separate `can_messages` array:

```json
{
  "can_messages": [
    {
      "message_id": 1792,
      "can_bus": 1,
      "is_extended": false,
      "cycle_time_ms": 100,
      "signals": [
        {
          "source_channel_id": 1000,
          "start_bit": 0,
          "length": 16,
          "byte_order": "little_endian",
          "factor": 1.0,
          "offset": 0
        },
        {
          "source_channel_id": 1001,
          "start_bit": 16,
          "length": 16
        }
      ]
    }
  ]
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `message_id` | int | CAN message ID |
| `can_bus` | int | CAN bus 1-4 |
| `is_extended` | bool | 29-bit extended ID |
| `cycle_time_ms` | int | Transmit interval |
| `signals` | array | Signals to pack |

### 4.2 Signal Definition

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `source_channel_id` | int | Yes | - |
| `start_bit` | int | Yes | - |
| `length` | int | Yes | - |
| `byte_order` | string | No | `little_endian` |
| `factor` | float | No | 1.0 |
| `offset` | float | No | 0 |

---

## 5. Complete Example

```json
{
  "version": "3.0",
  "device_name": "Race Car PMU",
  "device_settings": {
    "can1_baudrate": 500000,
    "can1_termination": true,
    "telemetry_rate_hz": 50
  },
  "channels": [
    {
      "channel_id": 0,
      "channel_type": "digital_input",
      "channel_name": "Headlight Switch",
      "input_pin": 0,
      "subtype": "switch_active_low",
      "debounce_ms": 50
    },
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
    },
    {
      "channel_id": 200,
      "channel_type": "logic",
      "channel_name": "Fan Enable",
      "operation": "hysteresis",
      "source_channel_id": 50,
      "upper_value": 850,
      "lower_value": 750
    },
    {
      "channel_id": 100,
      "channel_type": "power_output",
      "channel_name": "Headlights",
      "output_pins": [0, 1],
      "source_channel_id": 0,
      "current_limit": 15000
    },
    {
      "channel_id": 101,
      "channel_type": "power_output",
      "channel_name": "Cooling Fan",
      "output_pins": [2],
      "source_channel_id": 200,
      "current_limit": 25000,
      "soft_start_ms": 500
    }
  ],
  "can_messages": [
    {
      "message_id": 1792,
      "can_bus": 1,
      "cycle_time_ms": 100,
      "signals": [
        {"source_channel_id": 1000, "start_bit": 0, "length": 16},
        {"source_channel_id": 1001, "start_bit": 16, "length": 16},
        {"source_channel_id": 50, "start_bit": 32, "length": 16}
      ]
    }
  ]
}
```

---

## See Also

- [Channels Reference](channels.md) - Channel ID ranges and types
- [Logic Functions Reference](logic-functions.md) - All operations
- [Protocol Reference](protocol.md) - Communication protocol

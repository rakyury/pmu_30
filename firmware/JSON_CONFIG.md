# PMU-30 JSON Configuration

**Version**: 3.0
**Date**: 2025-12-29

## Overview

PMU-30 supports complete device configuration via JSON files. All I/O channels, logic functions, and system settings can be configured through JSON, enabling:

- Configure device without reflashing firmware
- Use graphical configurator application
- Save and load different configurations
- Create complex control logic without programming
- Real-time parameter updates via atomic protocol commands

## JSON Configuration Structure v3.0

PMU-30 uses a **unified channel architecture** where all elements are represented in a single `channels` array, with separate `can_messages` for CAN message definitions:

```json
{
  "version": "3.0",
  "device": {
    "name": "PMU-30 Racing Controller",
    "serial_number": "PMU30-001",
    "firmware_version": "2.0.0"
  },
  "can_messages": [
    { "name": "msg_ecu_status", "can_bus": 1, "base_id": 256, ... }
  ],
  "channels": [
    { "channel_id": 1, "channel_type": "digital_input", "channel_name": "Ignition", ... },
    { "channel_id": 2, "channel_type": "analog_input", "channel_name": "Throttle", ... },
    { "channel_id": 200, "channel_type": "logic", "channel_name": "FanEnable", ... },
    { "channel_id": 201, "channel_type": "can_rx", "message_ref": "msg_ecu_status", ... },
    { "channel_id": 100, "channel_type": "power_output", "channel_name": "FuelPump", ... }
  ],
  "settings": {
    "can_a": { ... },
    "can_b": { ... },
    "standard_can_stream": { ... },
    "power": { ... },
    "system": { ... }
  }
}
```

## Unified Channel Structure

All channels share common base fields:

```json
{
  "channel_id": 42,
  "channel_type": "logic",
  "channel_name": "BrakeLight",
  "enabled": true,
  "description": "Controls brake lights based on brake pedal"
}
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `channel_id` | Yes | integer | Unique numeric ID (0-999 for user channels) |
| `channel_type` | Yes | string | Channel type (see below) |
| `channel_name` | No | string | Human-readable display name |
| `enabled` | No | boolean | Active state (default: true) |
| `description` | No | string | User notes |

### Channel ID Ranges

| Range | Type | Description |
|-------|------|-------------|
| 0-99 | Physical Inputs | Digital/analog inputs |
| 100-199 | Physical Outputs | Power outputs, H-bridges |
| 200-999 | Virtual Channels | Logic, CAN, tables, etc. |
| 1000-1023 | System Channels | Battery, temp, etc. (read-only) |

## Channel Types

### Input Channels

#### Digital Input (`digital_input`)
```json
{
  "channel_id": 1,
  "channel_type": "digital_input",
  "channel_name": "Ignition",
  "input_pin": 0,
  "subtype": "switch_active_low",
  "enable_pullup": true,
  "debounce_ms": 50,
  "threshold_voltage": 2.5
}
```

**Subtypes:** `switch_active_low`, `switch_active_high`, `frequency`, `rpm`, `flex_fuel`, `beacon`, `keypad_button`

#### Analog Input (`analog_input`)
```json
{
  "channel_id": 2,
  "channel_type": "analog_input",
  "channel_name": "Throttle",
  "input_pin": 0,
  "subtype": "linear",
  "pullup_option": "1m_down",
  "min_voltage": 0.5,
  "max_voltage": 4.5,
  "min_value": 0,
  "max_value": 100,
  "decimal_places": 1
}
```

**Subtypes:** `switch_active_low`, `switch_active_high`, `rotary_switch`, `linear`, `calibrated`

### Logic Channels (`logic`)

Boolean operations with optional delays:

```json
{
  "channel_id": 200,
  "channel_type": "logic",
  "channel_name": "EngineRunning",
  "operator": "greater_than",
  "input_a_channel_id": 201,
  "threshold": 500,
  "true_delay_s": 0.5,
  "false_delay_s": 2.0,
  "hysteresis": 100
}
```

**Available Operations:**

| Operation | Description | Parameters |
|-----------|-------------|------------|
| `and` | All inputs true | `input_channel_ids` (array) |
| `or` | Any input true | `input_channel_ids` (array) |
| `not` | Invert input | `input_a_channel_id` |
| `xor` | Exclusive OR | `input_a_channel_id`, `input_b_channel_id` |
| `nand` | NOT AND | `input_channel_ids` (array) |
| `nor` | NOT OR | `input_channel_ids` (array) |
| `greater_than` | A > threshold | `input_a_channel_id`, `threshold` |
| `less_than` | A < threshold | `input_a_channel_id`, `threshold` |
| `equal_to` | A == threshold | `input_a_channel_id`, `threshold` |
| `not_equal` | A != threshold | `input_a_channel_id`, `threshold` |
| `greater_equal` | A >= threshold | `input_a_channel_id`, `threshold` |
| `less_equal` | A <= threshold | `input_a_channel_id`, `threshold` |
| `in_range` | min <= A <= max | `input_a_channel_id`, `range_min`, `range_max` |
| `hysteresis` | Schmitt trigger | `input_a_channel_id`, `on_threshold`, `off_threshold` |
| `flash` | Blinking output | `time_on_ms`, `time_off_ms` |
| `pulse` | One-shot pulse | `pulse_duration_ms`, `trigger_edge` |
| `toggle` | Toggle on edge | `input_a_channel_id`, `trigger_edge` |
| `set_reset_latch` | SR latch | `set_channel_id`, `reset_channel_id` |

### Number Channels (`number`)

Mathematical operations:

```json
{
  "channel_id": 210,
  "channel_type": "number",
  "channel_name": "MaxTemp",
  "operator": "max",
  "input_channel_ids": [2, 3, 4],
  "decimal_places": 1
}
```

**Available Operations:**

| Operation | Description | Parameters |
|-----------|-------------|------------|
| `constant` | Fixed value | `constant_value` |
| `add` | Sum inputs | `input_channel_ids` |
| `subtract` | A - B | `input_a_channel_id`, `input_b_channel_id` |
| `multiply` | A * B | `input_a_channel_id`, `input_b_channel_id` |
| `divide` | A / B | `input_a_channel_id`, `input_b_channel_id` |
| `min` | Minimum | `input_channel_ids` |
| `max` | Maximum | `input_channel_ids` |
| `average` | Average | `input_channel_ids` |
| `abs` | Absolute value | `input_a_channel_id` |
| `scale` | Linear scaling | `input_a_channel_id`, `multiplier`, `offset` |
| `clamp` | Limit range | `input_a_channel_id`, `clamp_min`, `clamp_max` |
| `conditional` | If-then-else | `condition_channel_id`, `true_channel_id`, `false_channel_id` |

### Filter Channels (`filter`)

Signal smoothing:

```json
{
  "channel_id": 220,
  "channel_type": "filter",
  "channel_name": "ThrottleFiltered",
  "filter_type": "moving_avg",
  "input_channel_id": 2,
  "window_size": 10
}
```

**Filter Types:**
- `moving_avg` - Moving average (`window_size`: 2-100)
- `low_pass` - Low-pass RC filter (`time_constant` in seconds)
- `min_window` - Minimum over window
- `max_window` - Maximum over window
- `median` - Median filter

### Timer Channels (`timer`)

Time measurement:

```json
{
  "channel_id": 230,
  "channel_type": "timer",
  "channel_name": "EngineRuntime",
  "start_channel_id": 200,
  "start_edge": "rising",
  "mode": "count_up",
  "limit_hours": 999,
  "limit_minutes": 59,
  "limit_seconds": 59
}
```

### Table Channels

#### 2D Table (`table_2d`)
```json
{
  "channel_id": 240,
  "channel_type": "table_2d",
  "channel_name": "FanPWM",
  "x_axis_channel_id": 2,
  "x_values": [70, 80, 90, 100, 110],
  "output_values": [0, 0, 50, 80, 100],
  "decimal_places": 0
}
```

#### 3D Table (`table_3d`)
```json
{
  "channel_id": 250,
  "channel_type": "table_3d",
  "channel_name": "BoostMap",
  "x_axis_channel_id": 2,
  "y_axis_channel_id": 201,
  "x_values": [0, 25, 50, 75, 100],
  "y_values": [1000, 3000, 5000, 7000],
  "data": [
    [100, 110, 120, 130],
    [110, 120, 135, 145],
    [120, 135, 150, 160],
    [130, 145, 160, 175],
    [140, 155, 175, 190]
  ]
}
```

### Switch Channels (`switch`)

State machine channels:

```json
{
  "channel_id": 260,
  "channel_type": "switch",
  "channel_name": "DrivingMode",
  "switch_type": "latching",
  "input_up_channel_id": 5,
  "input_up_edge": "rising",
  "state_first": 0,
  "state_last": 3,
  "state_default": 0
}
```

### PID Controller (`pid`)

Closed-loop control:

```json
{
  "channel_id": 270,
  "channel_type": "pid",
  "channel_name": "IdleControl",
  "input_channel_id": 201,
  "setpoint_channel_id": 220,
  "output_channel_id": 108,
  "kp": 1500,
  "ki": 200,
  "kd": 50,
  "output_min": 0,
  "output_max": 1000,
  "sample_time_ms": 20
}
```

### Output Channels

#### Power Output (`power_output`)
```json
{
  "channel_id": 100,
  "channel_type": "power_output",
  "channel_name": "FuelPump",
  "pins": [0],
  "source_channel_id": 200,
  "pwm_enabled": false,
  "pwm_frequency": 100,
  "default_duty": 1000,
  "current_limit_a": 15.0,
  "inrush_current_a": 30.0,
  "inrush_time_ms": 200,
  "retry_count": 3,
  "retry_delay_ms": 100
}
```

#### H-Bridge (`hbridge`)
```json
{
  "channel_id": 130,
  "channel_type": "hbridge",
  "channel_name": "Window",
  "bridge_number": 0,
  "source_channel_id": 260,
  "direction_channel_id": 261,
  "pwm_frequency": 1000,
  "current_limit_a": 10.0
}
```

### CAN Channels

#### CAN Messages (Level 1)
Define message structure in `can_messages` array:

```json
{
  "can_messages": [
    {
      "name": "msg_ecu_status",
      "can_bus": 1,
      "base_id": 256,
      "is_extended": false,
      "dlc": 8,
      "signals": [
        { "name": "rpm", "start_bit": 0, "length": 16, "byte_order": "little_endian", "factor": 1.0, "offset": 0.0 },
        { "name": "map", "start_bit": 16, "length": 16, "byte_order": "little_endian", "factor": 0.1, "offset": 0.0 }
      ]
    }
  ]
}
```

#### CAN RX (`can_rx`)
Reference signals from CAN messages:

```json
{
  "channel_id": 280,
  "channel_type": "can_rx",
  "channel_name": "EngineRPM",
  "message_ref": "msg_ecu_status",
  "signal_name": "rpm",
  "timeout_ms": 500,
  "default_value": 0
}
```

#### CAN TX (`can_tx`)
Transmit messages:

```json
{
  "channel_id": 290,
  "channel_type": "can_tx",
  "channel_name": "PMU_Status",
  "can_bus": 1,
  "message_id": 768,
  "is_extended": false,
  "cycle_time_ms": 100,
  "signals": [
    { "source_channel_id": 2, "start_bit": 0, "length": 8, "factor": 1.0, "offset": 0.0 },
    { "source_channel_id": 1000, "start_bit": 8, "length": 16, "factor": 0.1, "offset": 0.0 }
  ]
}
```

### Lua Script (`lua_script`)

Custom logic via Lua:

```json
{
  "channel_id": 300,
  "channel_type": "lua_script",
  "channel_name": "CustomLogic",
  "script": "function update()\n  local rpm = ch.get(280)\n  if rpm > 7000 then\n    ch.set(100, 0)\n  end\nend",
  "enabled": true,
  "run_interval_ms": 10
}
```

### Event Handler (`handler`)

React to events:

```json
{
  "channel_id": 310,
  "channel_type": "handler",
  "channel_name": "OverheatHandler",
  "trigger_channel_id": 200,
  "trigger_edge": "rising",
  "action": "set_channel",
  "target_channel_id": 105,
  "target_value": 0
}
```

### BlinkMarine Keypad (`blinkmarine_keypad`)

CAN keypad integration:

```json
{
  "channel_id": 320,
  "channel_type": "blinkmarine_keypad",
  "channel_name": "DashKeypad",
  "keypad_type": 0,
  "can_bus": 1,
  "base_id": 512,
  "buttons": [
    { "name": "Button 1", "press_action": "Toggle", "led_mode": "follow" },
    { "name": "Button 2", "press_action": "Momentary", "led_mode": "off" }
  ]
}
```

**Keypad Types:** `0` = PKP2600SI (12 buttons), `1` = PKP2800SI (16 buttons)

## System Channels (Read-Only)

| ID | Name | Description | Units |
|----|------|-------------|-------|
| 1000 | `pmu.batteryVoltage` | Battery voltage | mV |
| 1001 | `pmu.totalCurrent` | Total current | mA |
| 1002 | `pmu.mcuTemperature` | MCU temperature | °C |
| 1003 | `pmu.boardTemperatureL` | Left board temp | °C |
| 1004 | `pmu.boardTemperatureR` | Right board temp | °C |
| 1005 | `pmu.boardTemperatureMax` | Max board temp | °C |
| 1006 | `pmu.uptime` | System uptime | seconds |
| 1007 | `pmu.status` | Status bitmask | flags |
| 1008 | `pmu.userError` | User error code | code |
| 1009 | `pmu.5VOutput` | 5V rail voltage | mV |
| 1010 | `pmu.3V3Output` | 3.3V rail voltage | mV |
| 1011 | `pmu.isTurningOff` | Shutdown flag | 0/1 |
| 1012 | `zero` | Constant 0 | - |
| 1013 | `one` | Constant 1 | - |

## Atomic Channel Updates

Individual channels can be updated at runtime via protocol command 0x66 (`SET_CHANNEL_CONFIG`) without full configuration reload:

```
Request:  [0xAA][0x66][N][TYPE][CHANNEL_ID:2B][JSON_LEN:2B][JSON_CONFIG][CRC]
Response: [0xAA][0x67][N][CHANNEL_ID:2B][SUCCESS][ERROR_CODE:2B][ERROR_MSG][CRC]
```

See `PROTOCOL_DOCUMENTATION.md` for full details.

## Loading Configuration

### From String (C API):
```c
const char* json_config = "{ ... }";
PMU_JSON_LoadStats_t stats;
PMU_JSON_Status_t result = PMU_JSON_LoadFromString(json_config, strlen(json_config), &stats);

if (result == PMU_JSON_OK) {
    printf("Loaded %d channels, %d CAN messages\n",
           stats.total_channels, stats.can_messages);
}
```

### From Flash Memory:
```c
PMU_JSON_LoadStats_t stats;
PMU_JSON_Status_t result = PMU_JSON_LoadFromFlash(0x08100000, &stats);
```

### Load Statistics (v3.0)
```c
typedef struct {
    uint32_t total_channels;
    uint32_t can_messages;      // CAN message objects
    uint32_t digital_inputs;
    uint32_t analog_inputs;
    uint32_t power_outputs;
    uint32_t logic_functions;
    uint32_t numbers;
    uint32_t filters;
    uint32_t timers;
    uint32_t tables_2d;
    uint32_t tables_3d;
    uint32_t switches;
    uint32_t can_rx;
    uint32_t can_tx;
    uint32_t lua_scripts;
    uint32_t pid_controllers;
    uint32_t blinkmarine_keypads;
    uint32_t handlers;
    uint32_t parse_time_ms;
    bool stream_enabled;
} PMU_JSON_LoadStats_t;
```

## Version Compatibility

| Version | Status | Features |
|---------|--------|----------|
| 3.0 | **Current** | Two-level CAN, unified channels, PID, Lua, Handlers, Keypads |
| 2.0 | Legacy | Unified channel array, single-level CAN |
| 1.0 | Legacy | Separate arrays for inputs/outputs/logic |

Legacy v1.0 and v2.0 configurations are auto-migrated when loaded.

## Practical Examples

### Example 1: Launch Control

```json
{
  "version": "3.0",
  "can_messages": [
    { "name": "msg_ecu", "can_bus": 1, "base_id": 256, "signals": [
      { "name": "rpm", "start_bit": 0, "length": 16 },
      { "name": "speed", "start_bit": 16, "length": 16 }
    ]}
  ],
  "channels": [
    { "channel_id": 280, "channel_type": "can_rx", "channel_name": "RPM", "message_ref": "msg_ecu", "signal_name": "rpm" },
    { "channel_id": 281, "channel_type": "can_rx", "channel_name": "Speed", "message_ref": "msg_ecu", "signal_name": "speed" },
    { "channel_id": 200, "channel_type": "logic", "channel_name": "RPM_OK", "operator": "greater_than", "input_a_channel_id": 280, "threshold": 4000 },
    { "channel_id": 201, "channel_type": "logic", "channel_name": "Speed_OK", "operator": "less_than", "input_a_channel_id": 281, "threshold": 5 },
    { "channel_id": 202, "channel_type": "logic", "channel_name": "LaunchActive", "operator": "and", "input_channel_ids": [1, 200, 201] },
    { "channel_id": 100, "channel_type": "power_output", "channel_name": "IgnitionCut", "pins": [1], "source_channel_id": 202 }
  ]
}
```

### Example 2: Fan Control with PWM Table

```json
{
  "version": "3.0",
  "channels": [
    { "channel_id": 2, "channel_type": "analog_input", "channel_name": "CoolantTemp", "input_pin": 4, "min_voltage": 0.5, "max_voltage": 4.5, "min_value": -40, "max_value": 150 },
    { "channel_id": 3, "channel_type": "analog_input", "channel_name": "OilTemp", "input_pin": 5, "min_voltage": 0.5, "max_voltage": 4.5, "min_value": -40, "max_value": 150 },
    { "channel_id": 210, "channel_type": "number", "channel_name": "MaxTemp", "operator": "max", "input_channel_ids": [2, 3] },
    { "channel_id": 240, "channel_type": "table_2d", "channel_name": "FanDuty", "x_axis_channel_id": 210, "x_values": [70, 80, 90, 100, 110], "output_values": [0, 0, 50, 80, 100] },
    { "channel_id": 200, "channel_type": "logic", "channel_name": "FanEnable", "operator": "hysteresis", "input_a_channel_id": 210, "on_threshold": 80, "off_threshold": 75 },
    { "channel_id": 102, "channel_type": "power_output", "channel_name": "Fan", "pins": [2], "source_channel_id": 200, "pwm_enabled": true, "pwm_frequency": 100, "duty_channel_id": 240 }
  ]
}
```

### Example 3: PID Idle Control

```json
{
  "version": "3.0",
  "channels": [
    { "channel_id": 280, "channel_type": "can_rx", "channel_name": "RPM", "message_ref": "msg_ecu", "signal_name": "rpm" },
    { "channel_id": 220, "channel_type": "number", "channel_name": "TargetRPM", "operator": "constant", "constant_value": 850 },
    { "channel_id": 270, "channel_type": "pid", "channel_name": "IdlePID", "input_channel_id": 280, "setpoint_channel_id": 220, "kp": 1500, "ki": 200, "kd": 50, "output_min": 0, "output_max": 1000, "sample_time_ms": 20 },
    { "channel_id": 108, "channel_type": "power_output", "channel_name": "IdleValve", "pins": [8], "pwm_enabled": true, "pwm_frequency": 1000, "duty_channel_id": 270 }
  ]
}
```

## ID Naming Conventions

Recommended prefixes for `channel_name`:

| Type | Example Names |
|------|---------------|
| Digital Input | `Ignition`, `LaunchBtn`, `DoorSwitch` |
| Analog Input | `Throttle`, `OilPressure`, `CoolantTemp` |
| Logic | `EngineRunning`, `FanEnable`, `OverheatWarn` |
| Number | `MaxTemp`, `BoostError`, `TotalPower` |
| Filter | `ThrottleFiltered`, `BoostSmooth` |
| Timer | `EngineRuntime`, `LapTimer` |
| Table 2D | `FanPWM`, `ThrottleCurve` |
| Table 3D | `BoostMap`, `FuelMap` |
| Switch | `DrivingMode`, `TractionLevel` |
| PID | `IdleControl`, `BoostPID` |
| CAN RX | `EngineRPM`, `VehicleSpeed` |
| CAN TX | `PMU_Status`, `PMU_Telemetry` |
| Output | `FuelPump`, `Fan`, `IgnitionCut` |

## Tips and Best Practices

1. **Use numeric `channel_id`**: All channel references use numeric IDs (not strings)
2. **Unique IDs**: Each `channel_id` must be unique within the configuration
3. **Source references**: Use `source_channel_id`, `input_channel_id`, etc. for channel references
4. **Two-level CAN**: Define CAN messages first, then reference signals in `can_rx` channels
5. **Execution order**: Channels are evaluated in dependency order automatically
6. **Performance**: Up to 100 logic functions at 500Hz without performance impact
7. **Debugging**: Set `"enabled": false` to temporarily disable channels
8. **Atomic updates**: Use protocol 0x66 for real-time parameter changes

## Changelog

### Version 3.0 (2025-12-29)
- Two-level CAN architecture (`can_messages` + `can_rx`/`can_tx`)
- Added PID controller channel type
- Added Lua script channel type
- Added event handler channel type
- Added BlinkMarine keypad channel type
- Changed channel references to use numeric `channel_id`
- Added `channel_name` field for display names
- Added atomic channel update protocol (0x66/0x67)
- Added system channels with ECUMaster-compatible aliases
- Expanded load statistics for all channel types

### Version 2.0 (2025-12-21)
- Unified channel architecture
- Single `channels` array for all types
- String-based channel references

### Version 1.0 (Initial)
- Separate arrays for inputs, outputs, logic
- Basic channel types only

## See Also

- [CHANNEL_ABSTRACTION.md](CHANNEL_ABSTRACTION.md) - Channel system API
- [PROTOCOL_DOCUMENTATION.md](PROTOCOL_DOCUMENTATION.md) - Communication protocol
- [LOGIC_FUNCTIONS.md](LOGIC_FUNCTIONS.md) - Detailed logic function documentation

---

**Copyright 2025 R2 m-sport | PMU-30 Racing Controller**

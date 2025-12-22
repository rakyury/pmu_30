# PMU-30 JSON Configuration

## Overview

PMU-30 supports complete device configuration via JSON files. All I/O channels, logic functions, and system settings can be configured through JSON, enabling:

- Configure device without reflashing firmware
- Use graphical configurator application
- Save and load different configurations
- Create complex control logic without programming

## JSON Configuration Structure v2.0

PMU-30 uses a **unified channel architecture** where all elements are represented in a single `channels` array:

```json
{
  "version": "2.0",
  "device": {
    "name": "PMU-30 Racing Controller",
    "serial_number": "PMU30-001",
    "firmware_version": "2.0.0"
  },
  "channels": [
    { "id": "...", "channel_type": "digital_input", ... },
    { "id": "...", "channel_type": "analog_input", ... },
    { "id": "...", "channel_type": "logic", ... },
    { "id": "...", "channel_type": "number", ... },
    { "id": "...", "channel_type": "power_output", ... }
  ],
  "can_buses": [ ... ],
  "system": { ... }
}
```

## Channel Types

### Input Channels

#### Digital Input
```json
{
  "id": "di_ignition",
  "channel_type": "digital_input",
  "subtype": "switch_active_low",
  "input_pin": 0,
  "enable_pullup": true,
  "threshold_voltage": 2.5,
  "debounce_ms": 50
}
```

**Subtypes:** `switch_active_low`, `switch_active_high`, `frequency`, `rpm`, `flex_fuel`, `beacon`, `puls_oil_sensor`

#### Analog Input
```json
{
  "id": "ai_throttle",
  "channel_type": "analog_input",
  "subtype": "linear",
  "input_pin": 0,
  "pullup_option": "1m_down",
  "min_voltage": 0.5,
  "max_voltage": 4.5,
  "min_value": 0.0,
  "max_value": 100.0
}
```

**Subtypes:** `switch_active_low`, `switch_active_high`, `rotary_switch`, `linear`, `calibrated`

### Logic Channels

Logic channels perform boolean operations with optional delays:

```json
{
  "id": "l_engine_running",
  "channel_type": "logic",
  "operation": "greater",
  "channel": "di_engine_rpm",
  "constant": 500,
  "true_delay_s": 0.5,
  "false_delay_s": 2.0
}
```

**Available Operations:**

| Operation | Description | Example |
|-----------|-------------|---------|
| `and` | All inputs true | AND gate |
| `or` | Any input true | OR gate |
| `not` | Invert input | NOT gate |
| `xor` | Exclusive OR | XOR gate |
| `nand` | NOT AND | NAND gate |
| `nor` | NOT OR | NOR gate |
| `greater` | A > B | Comparison |
| `less` | A < B | Comparison |
| `equal` | A == B | Comparison |
| `not_equal` | A != B | Comparison |
| `greater_equal` | A >= B | Comparison |
| `less_equal` | A <= B | Comparison |
| `in_range` | min <= A <= max | Range check |
| `hysteresis` | Schmitt trigger | On/Off thresholds |
| `flash` | Blinking output | time_on, time_off |
| `pulse` | One-shot pulse | pulse_duration |
| `toggle` | Toggle on edge | Flip-flop |
| `set_reset_latch` | SR latch | set/reset channels |

### Number Channels

Number channels perform mathematical operations:

```json
{
  "id": "n_max_temp",
  "channel_type": "number",
  "operation": "max",
  "inputs": ["ai_coolant_temp", "ai_oil_temp"],
  "decimal_places": 1
}
```

**Available Operations:**

| Operation | Description | Parameters |
|-----------|-------------|------------|
| `constant` | Fixed value | `constant_value` |
| `add` | Sum inputs | - |
| `subtract` | A - B | - |
| `multiply` | A * B | - |
| `divide` | A / B | - |
| `min` | Minimum value | - |
| `max` | Maximum value | - |
| `average` | Average of inputs | - |
| `abs` | Absolute value | - |
| `scale` | Linear scaling | `multiplier`, `offset` |
| `clamp` | Limit range | `clamp_min`, `clamp_max` |
| `conditional` | If-then-else | condition, true_val, false_val |
| `lookup3` | 3-position lookup | `lookup_values` |

### Filter Channels

Filter channels smooth input signals:

```json
{
  "id": "flt_throttle",
  "channel_type": "filter",
  "filter_type": "moving_avg",
  "input_channel": "ai_throttle",
  "window_size": 10
}
```

**Filter Types:**
- `moving_avg` - Moving average (window_size: 2-100)
- `low_pass` - Low-pass RC filter (time_constant in seconds)
- `min_window` - Minimum over window
- `max_window` - Maximum over window
- `median` - Median filter

### Timer Channels

Timer channels count time:

```json
{
  "id": "tm_engine_runtime",
  "channel_type": "timer",
  "start_channel": "l_engine_running",
  "start_edge": "rising",
  "mode": "count_up",
  "limit_hours": 999,
  "limit_minutes": 59,
  "limit_seconds": 59
}
```

### Table Channels

#### 2D Table (1D Lookup)
```json
{
  "id": "t2d_fan_pwm",
  "channel_type": "table_2d",
  "x_axis_channel": "ai_coolant_temp",
  "x_values": [70, 80, 90, 100, 110],
  "output_values": [0, 0, 50, 80, 100],
  "decimal_places": 0
}
```

#### 3D Table (2D Map)
```json
{
  "id": "t3d_boost_map",
  "channel_type": "table_3d",
  "x_axis_channel": "ai_throttle",
  "y_axis_channel": "di_engine_rpm",
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

### Switch Channels

State machine channels:

```json
{
  "id": "sw_driving_mode",
  "channel_type": "switch",
  "switch_type": "latching",
  "input_up_channel": "di_mode_btn",
  "input_up_edge": "rising",
  "state_first": 0,
  "state_last": 3,
  "state_default": 0
}
```

### Output Channels

#### Power Output
```json
{
  "id": "out_fuel_pump",
  "channel_type": "power_output",
  "output_pins": [0],
  "source_channel": "l_fuel_pump_latch",
  "pwm_enabled": false,
  "current_limit_a": 15.0,
  "inrush_current_a": 30.0,
  "inrush_time_ms": 200,
  "retry_count": 3
}
```

### CAN Channels

#### CAN RX (Receive Signal)
```json
{
  "id": "crx_ecu_rpm",
  "channel_type": "can_rx",
  "can_bus": 1,
  "message_id": 256,
  "is_extended": false,
  "start_bit": 0,
  "length": 16,
  "byte_order": "little_endian",
  "value_type": "unsigned",
  "factor": 1.0,
  "offset": 0.0,
  "timeout_ms": 500
}
```

#### CAN TX (Transmit Message)
```json
{
  "id": "ctx_pmu_status",
  "channel_type": "can_tx",
  "can_bus": 1,
  "message_id": 768,
  "cycle_time_ms": 100,
  "signals": [
    {
      "source_channel": "ai_throttle",
      "start_bit": 0,
      "length": 8,
      "byte_order": "little_endian",
      "factor": 1.0,
      "offset": 0.0
    }
  ]
}
```

## Practical Examples

### Example 1: Launch Control

```json
{
  "version": "2.0",
  "channels": [
    {
      "id": "l_rpm_check",
      "channel_type": "logic",
      "operation": "greater",
      "channel": "crx_ecu_rpm",
      "constant": 4000
    },
    {
      "id": "l_speed_check",
      "channel_type": "logic",
      "operation": "less",
      "channel": "crx_vehicle_speed",
      "constant": 5
    },
    {
      "id": "l_launch_active",
      "channel_type": "logic",
      "operation": "and",
      "channel": "di_launch_btn",
      "channel_2": "l_rpm_check",
      "channel_3": "l_speed_check"
    },
    {
      "id": "out_ignition_cut",
      "channel_type": "power_output",
      "output_pins": [1],
      "source_channel": "l_launch_active"
    }
  ]
}
```

**Logic:**
1. Check RPM > 4000
2. Check speed < 5 km/h
3. Check launch button pressed
4. If all conditions TRUE - activate ignition cut

### Example 2: Fan Control with PWM Table

```json
{
  "version": "2.0",
  "channels": [
    {
      "id": "n_max_temp",
      "channel_type": "number",
      "operation": "max",
      "inputs": ["ai_coolant_temp", "ai_oil_temp"]
    },
    {
      "id": "t2d_fan_duty",
      "channel_type": "table_2d",
      "x_axis_channel": "n_max_temp",
      "x_values": [70, 80, 90, 100, 110],
      "output_values": [0, 0, 50, 80, 100]
    },
    {
      "id": "l_fan_enable",
      "channel_type": "logic",
      "operation": "hysteresis",
      "channel": "n_max_temp",
      "polarity": "normal",
      "upper_value": 80,
      "lower_value": 75
    },
    {
      "id": "out_fan",
      "channel_type": "power_output",
      "output_pins": [2],
      "source_channel": "l_fan_enable",
      "pwm_enabled": true,
      "pwm_frequency_hz": 100,
      "duty_channel": "t2d_fan_duty",
      "current_limit_a": 20.0
    }
  ]
}
```

### Example 3: Boost Control with PID

```json
{
  "version": "2.0",
  "channels": [
    {
      "id": "flt_boost",
      "channel_type": "filter",
      "filter_type": "low_pass",
      "input_channel": "ai_boost_pressure",
      "time_constant": 0.05
    },
    {
      "id": "n_boost_error",
      "channel_type": "number",
      "operation": "subtract",
      "inputs": ["n_boost_target", "flt_boost"]
    },
    {
      "id": "n_wastegate_duty",
      "channel_type": "number",
      "operation": "scale",
      "inputs": ["n_boost_error"],
      "input_multipliers": ["*3.0"],
      "clamp_min": 0,
      "clamp_max": 100
    },
    {
      "id": "out_wastegate",
      "channel_type": "power_output",
      "output_pins": [5],
      "source_channel": "l_engine_running",
      "pwm_enabled": true,
      "pwm_frequency_hz": 50,
      "duty_channel": "n_wastegate_duty"
    }
  ]
}
```

## Loading Configuration

### From String (C API):
```c
const char* json_config = "{ ... }";
PMU_JSON_LoadStats_t stats;
PMU_JSON_Status_t result = PMU_JSON_LoadFromString(json_config, strlen(json_config), &stats);

if (result == PMU_JSON_OK) {
    printf("Loaded %d channels\n", stats.total_channels);
}
```

### From Flash Memory:
```c
PMU_JSON_LoadStats_t stats;
PMU_JSON_Status_t result = PMU_JSON_LoadFromFlash(0x08100000, &stats);
```

## Validation

Validate JSON before loading:

```c
char error_msg[256];
bool valid = PMU_JSON_Validate(json_string, length, error_msg, sizeof(error_msg));

if (!valid) {
    printf("Validation error: %s\n", error_msg);
}
```

## Supported Functions Summary

### Logic Operations
- `and`, `or`, `not`, `xor`, `nand`, `nor`
- `greater`, `less`, `equal`, `not_equal`, `greater_equal`, `less_equal`
- `in_range`, `hysteresis`
- `flash`, `pulse`, `toggle`, `set_reset_latch`

### Math Operations
- `add`, `subtract`, `multiply`, `divide`
- `min`, `max`, `average`, `abs`
- `scale`, `clamp`, `conditional`
- `lookup3` (3-position lookup)

### Filters
- `moving_avg`, `low_pass`
- `min_window`, `max_window`, `median`

### Tables
- `table_2d` (1D lookup with interpolation)
- `table_3d` (2D map with interpolation)

## ID Naming Conventions

Recommended prefixes for channel IDs:

| Prefix | Type | Example |
|--------|------|---------|
| `di_` | Digital Input | `di_ignition`, `di_launch_btn` |
| `ai_` | Analog Input | `ai_throttle`, `ai_coolant_temp` |
| `l_` | Logic | `l_engine_running`, `l_fan_enable` |
| `n_` | Number | `n_max_temp`, `n_boost_error` |
| `flt_` | Filter | `flt_throttle`, `flt_boost` |
| `tm_` | Timer | `tm_engine_runtime` |
| `t2d_` | Table 2D | `t2d_fan_pwm` |
| `t3d_` | Table 3D | `t3d_boost_map` |
| `sw_` | Switch | `sw_driving_mode` |
| `e_` | Enum | `e_gear`, `e_mode` |
| `crx_` | CAN RX | `crx_ecu_rpm` |
| `ctx_` | CAN TX | `ctx_pmu_status` |
| `out_` | Output | `out_fuel_pump`, `out_fan` |

## Tips and Recommendations

1. **Channel IDs**: Must start with a letter, use only letters, numbers, underscores
2. **References**: Channels can reference other channels by ID string
3. **Execution Order**: Channels are evaluated in dependency order automatically
4. **Performance**: Up to 100 logic functions at 500Hz without performance loss
5. **Debugging**: Use `"enabled": false` to temporarily disable channels

## See Also

- [LOGIC_FUNCTIONS.md](LOGIC_FUNCTIONS.md) - Detailed C API documentation
- [examples/lua_examples.lua](examples/lua_examples.lua) - Lua script examples
- [examples/config_examples.json](examples/config_examples.json) - Complete configuration examples

---

**Copyright 2025 R2 m-sport | PMU-30 Racing Controller**

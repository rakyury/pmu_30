# Logic Function Examples

**Version:** 2.0
**Date:** December 2025

Practical examples for using logic functions in the PMU-30 with JSON configuration v3.0 format.

---

## Table of Contents

1. [Simple Function Execution](#1-simple-function-execution)
2. [Function Chaining](#2-function-chaining)
3. [Conditional Logic](#3-conditional-logic)
4. [Loop and Timer Patterns](#4-loop-and-timer-patterns)
5. [Filter Applications](#5-filter-applications)
6. [Control Systems](#6-control-systems)
7. [Error Handling](#7-error-handling)
8. [Performance Optimization](#8-performance-optimization)

---

## Channel ID Reference

| Range | Type | Description |
|-------|------|-------------|
| 0-49 | Digital Inputs | d1-d20 physical digital inputs |
| 50-99 | Analog Inputs | a1-a20 physical analog inputs |
| 100-199 | Physical Outputs | o1-o30 power outputs, hb1-hb4 H-bridges |
| 200-999 | Virtual Channels | Logic, numbers, tables, CAN RX/TX, timers |
| 1000-1023 | System Channels | Battery voltage, temperatures, status |

---

## 1. Simple Function Execution

### Basic Math: Add Two Channels

**C Code:**
```c
// Result = Channel 50 + Channel 51 (two analog inputs)
void example_add(void) {
    uint16_t func_id = PMU_LogicFunctions_CreateMath(
        PMU_FUNC_ADD,
        200,    // Output channel (virtual)
        50,     // Input A (analog 1)
        51      // Input B (analog 2)
    );

    printf("Created ADD function ID: %d\n", func_id);
}
```

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 200,
      "channel_name": "SumAnalog",
      "operator": "add",
      "input_a_channel_id": 50,
      "input_b_channel_id": 51
    }
  ]
}
```

### Scale and Offset

**C Code:**
```c
// Convert ADC (0-4095) to Temperature (-40 to 120 C)
// Formula: temp = adc * 0.039 - 40
void example_scale(void) {
    PMU_LogicFunction_t scale = {
        .function_id = 0,
        .type = PMU_FUNC_SCALE,
        .output_channel = 200,
        .input_channels = {50},
        .input_count = 1,
        .enabled = 1,
        .params.scale = {
            .scale = 39,     // 0.039 * 1000
            .offset = -400   // -40 * 10 (0.1 C units)
        }
    };
    PMU_LogicFunctions_Register(&scale);
}
```

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "analog_input",
      "channel_id": 50,
      "channel_name": "CoolantTemp",
      "pin": 1,
      "sensor_type": "ntc_10k",
      "scaling": {
        "factor": 39,
        "offset": -400
      }
    }
  ]
}
```

### Clamp Value to Range

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "filter",
      "channel_id": 201,
      "channel_name": "ThrottleClamped",
      "filter_type": "clamp",
      "source_channel_id": 200,
      "min_value": 0,
      "max_value": 1000
    }
  ]
}
```

---

## 2. Function Chaining

### Sensor Processing Pipeline

Pipeline: ADC -> Scale -> Filter -> Clamp -> Output

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "analog_input",
      "channel_id": 50,
      "channel_name": "TempRaw",
      "pin": 1,
      "sensor_type": "voltage"
    },
    {
      "type": "logic",
      "channel_id": 200,
      "channel_name": "TempScaled",
      "operator": "scale",
      "input_a_channel_id": 50,
      "scale_factor": 244,
      "scale_offset": -400
    },
    {
      "type": "filter",
      "channel_id": 201,
      "channel_name": "TempFiltered",
      "filter_type": "moving_average",
      "source_channel_id": 200,
      "window_size": 8
    },
    {
      "type": "filter",
      "channel_id": 202,
      "channel_name": "TempFinal",
      "filter_type": "clamp",
      "source_channel_id": 201,
      "min_value": -400,
      "max_value": 1200
    }
  ]
}
```

### Multi-Sensor Maximum

Take maximum of 4 temperature sensors:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 210,
      "channel_name": "MaxTemp",
      "operator": "max",
      "input_a_channel_id": 50,
      "input_b_channel_id": 51,
      "input_c_channel_id": 52,
      "input_d_channel_id": 53
    }
  ]
}
```

---

## 3. Conditional Logic

### Simple Comparison

Output = 1 if temperature > 85 C:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "number",
      "channel_id": 250,
      "channel_name": "TempThreshold",
      "value": 850
    },
    {
      "type": "logic",
      "channel_id": 201,
      "channel_name": "OverheatFlag",
      "operator": "greater_than",
      "input_a_channel_id": 200,
      "input_b_channel_id": 250
    }
  ]
}
```

### AND Gate: Multiple Conditions

Fuel pump ON if: ignition AND (running OR priming) AND safety:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 220,
      "channel_name": "EngineRunning",
      "operator": "greater_than",
      "input_a_channel_id": 300,
      "threshold": 300
    },
    {
      "type": "timer",
      "channel_id": 221,
      "channel_name": "PrimePulse",
      "timer_mode": "pulse",
      "trigger_channel_id": 0,
      "duration_ms": 3000
    },
    {
      "type": "logic",
      "channel_id": 222,
      "channel_name": "RunOrPrime",
      "operator": "or",
      "input_a_channel_id": 220,
      "input_b_channel_id": 221
    },
    {
      "type": "logic",
      "channel_id": 223,
      "channel_name": "FuelPumpEnable",
      "operator": "and",
      "input_a_channel_id": 0,
      "input_b_channel_id": 222,
      "input_c_channel_id": 1,
      "input_d_channel_id": 2
    },
    {
      "type": "power_output",
      "channel_id": 104,
      "channel_name": "FuelPump",
      "pins": [5],
      "source_channel_id": 223
    }
  ]
}
```

### OR Gate: Any Condition

Warning light if: overheat OR low oil OR low fuel:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 230,
      "channel_name": "WarningAny",
      "operator": "or",
      "input_a_channel_id": 210,
      "input_b_channel_id": 211,
      "input_c_channel_id": 212
    },
    {
      "type": "power_output",
      "channel_id": 101,
      "channel_name": "WarningLight",
      "pins": [2],
      "source_channel_id": 230
    }
  ]
}
```

### Ternary/Conditional

Speed = (gear == reverse) ? -speed : speed:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 220,
      "channel_name": "SignedSpeed",
      "operator": "conditional",
      "condition_channel_id": 215,
      "true_channel_id": 216,
      "false_channel_id": 217
    }
  ]
}
```

### In-Range Check

Valid = 1 if 500 <= RPM <= 7000:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 225,
      "channel_name": "RPMValid",
      "operator": "in_range",
      "input_a_channel_id": 300,
      "min_value": 500,
      "max_value": 7000
    }
  ]
}
```

---

## 4. Loop and Timer Patterns

### Hysteresis (On/Off with Dead Band)

Fan: ON above 85 C, OFF below 75 C:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 230,
      "channel_name": "FanControl",
      "operator": "hysteresis",
      "input_a_channel_id": 200,
      "threshold_on": 850,
      "threshold_off": 750
    },
    {
      "type": "power_output",
      "channel_id": 105,
      "channel_name": "RadiatorFan",
      "pins": [6],
      "source_channel_id": 230,
      "current_limit_a": 25
    }
  ]
}
```

### Debounce Filter

Debounce switch for 50ms:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "digital_input",
      "channel_id": 0,
      "channel_name": "StartButton",
      "pin": 1,
      "debounce_ms": 50
    }
  ]
}
```

### Rate Limiter

Limit throttle change rate to 500/second:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "filter",
      "channel_id": 231,
      "channel_name": "ThrottleRateLimited",
      "filter_type": "rate_limit",
      "source_channel_id": 200,
      "max_rate": 500
    }
  ]
}
```

### Timer: Delayed On

Turn on after 500ms:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "timer",
      "channel_id": 240,
      "channel_name": "DelayedStart",
      "timer_mode": "delay_on",
      "trigger_channel_id": 0,
      "delay_ms": 500
    }
  ]
}
```

### Timer: Pulse Generator

Generate 2-second pulse:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "timer",
      "channel_id": 241,
      "channel_name": "PrimePulse",
      "timer_mode": "pulse",
      "trigger_channel_id": 0,
      "duration_ms": 2000
    }
  ]
}
```

---

## 5. Filter Applications

### Moving Average (Noise Reduction)

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "filter",
      "channel_id": 240,
      "channel_name": "TempSmoothed",
      "filter_type": "moving_average",
      "source_channel_id": 50,
      "window_size": 16
    }
  ]
}
```

### Low-Pass Filter (RC)

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "filter",
      "channel_id": 241,
      "channel_name": "PressureFiltered",
      "filter_type": "low_pass",
      "source_channel_id": 51,
      "time_constant_ms": 100
    }
  ]
}
```

### Peak Hold (Max over Window)

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "filter",
      "channel_id": 242,
      "channel_name": "RPMPeak",
      "filter_type": "peak_hold",
      "source_channel_id": 300,
      "hold_time_ms": 5000
    }
  ]
}
```

---

## 6. Control Systems

### PID Controller

Temperature control with PID for heater:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "number",
      "channel_id": 260,
      "channel_name": "TempSetpoint",
      "value": 750
    },
    {
      "type": "pid",
      "channel_id": 261,
      "channel_name": "HeaterPID",
      "input_channel_id": 200,
      "setpoint_channel_id": 260,
      "output_channel_id": 100,
      "kp": 2000,
      "ki": 100,
      "kd": 500,
      "output_min": 0,
      "output_max": 1000,
      "sample_time_ms": 50
    }
  ]
}
```

### 2D Lookup Table

Fan speed from temperature lookup table:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "table_2d",
      "channel_id": 262,
      "channel_name": "FanSpeedTable",
      "input_channel_id": 200,
      "x_axis": [500, 600, 700, 800, 900, 1000],
      "values": [0, 100, 300, 600, 850, 1000]
    },
    {
      "type": "power_output",
      "channel_id": 105,
      "channel_name": "RadiatorFan",
      "pins": [6],
      "source_channel_id": 262,
      "pwm_enabled": true,
      "pwm_frequency": 100
    }
  ]
}
```

### 3D Lookup Table

Fuel enrichment from RPM and TPS:

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "table_3d",
      "channel_id": 263,
      "channel_name": "FuelEnrichment",
      "input_x_channel_id": 300,
      "input_y_channel_id": 301,
      "x_axis": [1000, 2000, 3000, 4000, 5000, 6000, 7000],
      "y_axis": [0, 250, 500, 750, 1000],
      "values": [
        [100, 100, 100, 100, 100],
        [100, 105, 110, 115, 120],
        [100, 108, 116, 124, 130],
        [100, 110, 120, 130, 140],
        [100, 112, 124, 136, 150],
        [100, 115, 130, 145, 160],
        [100, 118, 136, 154, 170]
      ]
    }
  ]
}
```

### Closed-Loop Idle Control

**JSON Configuration (v3.0):**
```json
{
  "channels": [
    {
      "type": "number",
      "channel_id": 260,
      "channel_name": "TargetRPM",
      "value": 800
    },
    {
      "type": "pid",
      "channel_id": 261,
      "channel_name": "IdlePID",
      "input_channel_id": 300,
      "setpoint_channel_id": 260,
      "output_channel_id": 101,
      "kp": 500,
      "ki": 20,
      "kd": 100,
      "output_min": 0,
      "output_max": 1000,
      "sample_time_ms": 20
    },
    {
      "type": "power_output",
      "channel_id": 101,
      "channel_name": "IdleValve",
      "pins": [2],
      "pwm_enabled": true,
      "pwm_frequency": 500
    }
  ]
}
```

---

## 7. Error Handling

### Safe Function Creation (C Code)

```c
void safe_create_function(PMU_LogicFunction_t* func) {
    // Validate before registration
    if (func->function_id >= PMU_MAX_LOGIC_FUNCTIONS) {
        printf("Error: Invalid function ID %d\n", func->function_id);
        return;
    }

    if (func->output_channel >= PMU_CHANNEL_MAX_CHANNELS) {
        printf("Error: Invalid output channel %d\n", func->output_channel);
        return;
    }

    for (int i = 0; i < func->input_count; i++) {
        if (func->input_channels[i] >= PMU_CHANNEL_MAX_CHANNELS) {
            printf("Error: Invalid input channel %d\n", func->input_channels[i]);
            return;
        }
    }

    HAL_StatusTypeDef status = PMU_LogicFunctions_Register(func);
    if (status != HAL_OK) {
        printf("Error: Registration failed\n");
    }
}
```

### Function Status Check (C Code)

```c
void check_function_health(uint16_t func_id) {
    PMU_LogicFunction_t* func = PMU_LogicFunctions_GetByID(func_id);

    if (func == NULL) {
        printf("Function %d: NOT FOUND\n", func_id);
        return;
    }

    printf("Function %d:\n", func_id);
    printf("  Type: 0x%02X\n", func->type);
    printf("  Enabled: %s\n", func->enabled ? "YES" : "NO");
    printf("  Output: %d\n", func->output_channel);

    // Check output channel
    const PMU_Channel_t* out = PMU_Channel_GetInfo(func->output_channel);
    if (out) {
        printf("  Output value: %ld\n", out->value);
        if (out->flags & PMU_CHANNEL_FLAG_FAULT) {
            printf("  WARNING: Output channel in fault!\n");
        }
    }
}
```

---

## 8. Performance Optimization

### Minimal Function Count

**BAD: 4 separate functions**
```json
{
  "channels": [
    {"type": "logic", "channel_id": 200, "operator": "add", "input_a_channel_id": 50, "input_b_channel_id": 51},
    {"type": "logic", "channel_id": 201, "operator": "add", "input_a_channel_id": 200, "input_b_channel_id": 52},
    {"type": "logic", "channel_id": 202, "operator": "add", "input_a_channel_id": 201, "input_b_channel_id": 53},
    {"type": "logic", "channel_id": 203, "operator": "divide", "input_a_channel_id": 202, "input_b_channel_id": 254}
  ]
}
```

**GOOD: Single average function**
```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 200,
      "channel_name": "AverageTemp",
      "operator": "average",
      "input_a_channel_id": 50,
      "input_b_channel_id": 51,
      "input_c_channel_id": 52,
      "input_d_channel_id": 53
    }
  ]
}
```

### Appropriate Filter Size

```json
{
  "channels": [
    {
      "type": "filter",
      "channel_id": 240,
      "channel_name": "ThrottleFiltered",
      "filter_type": "moving_average",
      "source_channel_id": 54,
      "window_size": 4
    },
    {
      "type": "filter",
      "channel_id": 241,
      "channel_name": "TempFiltered",
      "filter_type": "moving_average",
      "source_channel_id": 50,
      "window_size": 32
    }
  ]
}
```

Notes:
- Small filter (4) = fast response, more noise (for throttle)
- Large filter (32) = slow response, less noise (for temperature)

### Disable Unused Channels

Logic channels can be enabled/disabled via JSON:

```json
{
  "channels": [
    {
      "type": "logic",
      "channel_id": 230,
      "channel_name": "IdleControl",
      "operator": "pid",
      "enabled": false
    }
  ]
}
```

---

## See Also

- [Channel Examples](channel-examples.md)
- [Real-World Scenarios](real-world-scenarios.md)
- [JSON Configuration](../../firmware/JSON_CONFIG.md) - Configuration format v3.0

---

**Document Version:** 2.0
**Last Updated:** December 2025

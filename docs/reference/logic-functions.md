# PMU-30 Logic Functions Reference

**Version:** 3.0 | **Last Updated:** December 2025

Complete reference for all virtual channel operations: math, logic, comparison, filters, tables, timers, and PID controllers.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Math Operations](#2-math-operations)
3. [Comparison Operations](#3-comparison-operations)
4. [Logic Operations](#4-logic-operations)
5. [State Operations](#5-state-operations)
6. [Timer Operations](#6-timer-operations)
7. [Filter Operations](#7-filter-operations)
8. [Table Lookups](#8-table-lookups)
9. [PID Controller](#9-pid-controller)
10. [C API Reference](#10-c-api-reference)

---

## 1. Overview

### 1.1 System Limits

| Parameter | Value |
|-----------|-------|
| Max Functions | 100 (channel IDs 200-999) |
| Update Rate | 500 Hz |
| Max Inputs per Function | 8 |
| Channel ID Range | 200-999 |

### 1.2 Function Type Codes

```c
typedef enum {
    // Math (0x00-0x0F)
    PMU_FUNC_ADD = 0x00, PMU_FUNC_SUBTRACT, PMU_FUNC_MULTIPLY, PMU_FUNC_DIVIDE,
    PMU_FUNC_MIN, PMU_FUNC_MAX, PMU_FUNC_AVERAGE, PMU_FUNC_ABS,
    PMU_FUNC_SCALE, PMU_FUNC_CLAMP, PMU_FUNC_MODULO,

    // Comparison (0x20-0x2F)
    PMU_FUNC_GREATER = 0x20, PMU_FUNC_LESS, PMU_FUNC_EQUAL, PMU_FUNC_NOT_EQUAL,
    PMU_FUNC_GREATER_EQUAL, PMU_FUNC_LESS_EQUAL, PMU_FUNC_IN_RANGE,

    // Logic (0x40-0x4F)
    PMU_FUNC_AND = 0x40, PMU_FUNC_OR, PMU_FUNC_NOT, PMU_FUNC_XOR,
    PMU_FUNC_NAND, PMU_FUNC_NOR,

    // Tables (0x60-0x6F)
    PMU_FUNC_TABLE_1D = 0x60, PMU_FUNC_TABLE_2D,

    // Filters (0x80-0x8F)
    PMU_FUNC_MOVING_AVG = 0x80, PMU_FUNC_MIN_WINDOW, PMU_FUNC_MAX_WINDOW,
    PMU_FUNC_MEDIAN, PMU_FUNC_LOW_PASS,

    // Control (0xA0-0xAF)
    PMU_FUNC_PID = 0xA0, PMU_FUNC_HYSTERESIS, PMU_FUNC_RATE_LIMIT, PMU_FUNC_DEBOUNCE,

    // Special (0xC0-0xCF)
    PMU_FUNC_MUX = 0xC0, PMU_FUNC_DEMUX, PMU_FUNC_CONDITIONAL, PMU_FUNC_CUSTOM_LUA,
} PMU_FunctionType_t;
```

---

## 2. Math Operations

### 2.1 Operation Reference

| Operation | JSON `operation` | Inputs | Formula |
|-----------|------------------|--------|---------|
| Add | `add` | 2-8 | `A + B + C + ...` |
| Subtract | `subtract` | 2 | `A - B` |
| Multiply | `multiply` | 2-8 | `A × B × C × ...` |
| Divide | `divide` | 2 | `A / B` |
| Modulo | `modulo` | 2 | `A % B` |
| Min | `min` | 2-8 | `min(A, B, C, ...)` |
| Max | `max` | 2-8 | `max(A, B, C, ...)` |
| Average | `average` | 2-8 | `(A + B + ...) / N` |
| Absolute | `abs` | 1 | `|A|` |
| Scale | `scale` | 1 | `A × factor + offset` |
| Clamp | `clamp` | 1 | `min(max(A, min_val), max_val)` |
| Constant | `constant` | 0 | `value` |
| Bitwise AND | `bitand` | 2 | `A & B` |
| Bitwise OR | `bitor` | 2 | `A | B` |

### 2.2 JSON Examples

**Add:**
```json
{
  "channel_id": 200,
  "channel_type": "number",
  "channel_name": "Total Current",
  "operation": "add",
  "source_channel_ids": [1130, 1131, 1132, 1133]
}
```

**Scale:**
```json
{
  "channel_id": 201,
  "channel_type": "number",
  "channel_name": "Voltage Scaled",
  "operation": "scale",
  "source_channel_id": 1000,
  "factor": 0.001,
  "offset": 0
}
```

**Clamp:**
```json
{
  "channel_id": 202,
  "channel_type": "number",
  "channel_name": "Clamped Value",
  "operation": "clamp",
  "source_channel_id": 50,
  "min_value": 0,
  "max_value": 1000
}
```

**Constant:**
```json
{
  "channel_id": 203,
  "channel_type": "number",
  "channel_name": "Setpoint",
  "operation": "constant",
  "constant_value": 800
}
```

---

## 3. Comparison Operations

### 3.1 Operation Reference

| Operation | JSON `operation` | Inputs | Output |
|-----------|------------------|--------|--------|
| Greater | `gt` | 2 | `1` if A > B, else `0` |
| Less | `lt` | 2 | `1` if A < B, else `0` |
| Equal | `eq` | 2 | `1` if A == B, else `0` |
| Not Equal | `ne` | 2 | `1` if A != B, else `0` |
| Greater/Equal | `ge` | 2 | `1` if A >= B, else `0` |
| Less/Equal | `le` | 2 | `1` if A <= B, else `0` |
| In Range | `in_range` | 1 | `1` if min <= A <= max, else `0` |

### 3.2 JSON Examples

**Greater Than:**
```json
{
  "channel_id": 210,
  "channel_type": "logic",
  "channel_name": "Over Temp",
  "operation": "gt",
  "source_channel_id": 50,
  "compare_value": 900
}
```

**In Range:**
```json
{
  "channel_id": 211,
  "channel_type": "logic",
  "channel_name": "Normal Range",
  "operation": "in_range",
  "source_channel_id": 50,
  "lower_value": 200,
  "upper_value": 800
}
```

---

## 4. Logic Operations

### 4.1 Operation Reference

| Operation | JSON `operation` | Inputs | Formula |
|-----------|------------------|--------|---------|
| AND | `and` | 2-8 | `A && B && C && ...` |
| OR | `or` | 2-8 | `A || B || C || ...` |
| NOT | `not` | 1 | `!A` |
| XOR | `xor` | 2-8 | `A ^ B ^ C ^ ...` |
| NAND | `nand` | 2-8 | `!(A && B && ...)` |
| NOR | `nor` | 2-8 | `!(A || B || ...)` |

### 4.2 JSON Examples

**AND:**
```json
{
  "channel_id": 220,
  "channel_type": "logic",
  "channel_name": "Both Active",
  "operation": "and",
  "source_channel_ids": [0, 1]
}
```

**OR:**
```json
{
  "channel_id": 221,
  "channel_type": "logic",
  "channel_name": "Any Active",
  "operation": "or",
  "source_channel_ids": [0, 1, 2, 3]
}
```

**NOT:**
```json
{
  "channel_id": 222,
  "channel_type": "logic",
  "channel_name": "Inverted",
  "operation": "not",
  "source_channel_id": 0
}
```

---

## 5. State Operations

### 5.1 Operation Reference

| Operation | JSON `operation` | Description |
|-----------|------------------|-------------|
| Hysteresis | `hysteresis` | Schmitt trigger with upper/lower thresholds |
| Toggle | `toggle` | Flip-flop on rising edge |
| Latch | `latch` | Set/Reset latch (SR flip-flop) |
| Rising Edge | `rising` | Pulse on 0→1 transition |
| Falling Edge | `falling` | Pulse on 1→0 transition |
| Changed | `changed` | Pulse on any value change |
| Pulse | `pulse` | One-shot pulse generator |
| Flash | `flash` | Periodic on/off oscillator |

### 5.2 JSON Examples

**Hysteresis:**
```json
{
  "channel_id": 230,
  "channel_type": "logic",
  "channel_name": "Fan Control",
  "operation": "hysteresis",
  "source_channel_id": 50,
  "upper_value": 850,
  "lower_value": 750,
  "polarity": "normal"
}
```

**Toggle:**
```json
{
  "channel_id": 231,
  "channel_type": "logic",
  "channel_name": "Toggle State",
  "operation": "toggle",
  "source_channel_id": 0
}
```

**Latch:**
```json
{
  "channel_id": 232,
  "channel_type": "logic",
  "channel_name": "Latched",
  "operation": "latch",
  "set_channel_id": 0,
  "reset_channel_id": 1
}
```

**Flash:**
```json
{
  "channel_id": 233,
  "channel_type": "logic",
  "channel_name": "Blinker",
  "operation": "flash",
  "source_channel_id": 0,
  "on_time_ms": 500,
  "off_time_ms": 500
}
```

**Pulse:**
```json
{
  "channel_id": 234,
  "channel_type": "logic",
  "channel_name": "One Shot",
  "operation": "pulse",
  "source_channel_id": 0,
  "pulse_time_ms": 1000,
  "retriggerable": true
}
```

---

## 6. Timer Operations

### 6.1 Timer Modes

| Mode | JSON `mode` | Description |
|------|-------------|-------------|
| Count Up | `count_up` | Counts up while trigger active |
| Count Down | `count_down` | Counts down from max value |
| Retriggerable | `retriggerable` | Resets on each trigger edge |
| Stopwatch | `stopwatch` | Counts total time trigger was active |

### 6.2 JSON Examples

**Count Up Timer:**
```json
{
  "channel_id": 240,
  "channel_type": "timer",
  "channel_name": "Engine Run Time",
  "mode": "count_up",
  "trigger_channel_id": 0,
  "reset_channel_id": 1,
  "max_value": 36000000,
  "scale_ms": 100
}
```

**Count Down Timer:**
```json
{
  "channel_id": 241,
  "channel_type": "timer",
  "channel_name": "Countdown",
  "mode": "count_down",
  "trigger_channel_id": 0,
  "initial_value": 300000,
  "scale_ms": 1000
}
```

**Retriggerable Delay:**
```json
{
  "channel_id": 242,
  "channel_type": "timer",
  "channel_name": "Delayed Off",
  "mode": "retriggerable",
  "trigger_channel_id": 0,
  "delay_ms": 5000
}
```

---

## 7. Filter Operations

### 7.1 Filter Types

| Filter | JSON `filter_type` | Description |
|--------|---------------------|-------------|
| Low Pass | `low_pass` | First-order IIR filter |
| Moving Average | `moving_average` | Rolling average over N samples |
| Median | `median` | Median of last N samples |
| Min Window | `min_window` | Minimum over time window |
| Max Window | `max_window` | Maximum over time window |

### 7.2 JSON Examples

**Low Pass Filter:**
```json
{
  "channel_id": 250,
  "channel_type": "filter",
  "channel_name": "Filtered Temp",
  "source_channel_id": 50,
  "filter_type": "low_pass",
  "time_constant_ms": 500
}
```

**Moving Average:**
```json
{
  "channel_id": 251,
  "channel_type": "filter",
  "channel_name": "Averaged Voltage",
  "source_channel_id": 1000,
  "filter_type": "moving_average",
  "window_size": 10
}
```

**Median Filter:**
```json
{
  "channel_id": 252,
  "channel_type": "filter",
  "channel_name": "Noise Reject",
  "source_channel_id": 50,
  "filter_type": "median",
  "window_size": 5
}
```

---

## 8. Table Lookups

### 8.1 2D Table (1D Interpolation)

Linear interpolation with up to 16 breakpoints:

```json
{
  "channel_id": 260,
  "channel_type": "table_2d",
  "channel_name": "PWM Curve",
  "x_axis_channel_id": 50,
  "x_values": [0, 250, 500, 750, 1000],
  "output_values": [0, 100, 300, 700, 1000]
}
```

### 8.2 3D Table (2D Interpolation)

Bilinear interpolation with up to 16×16 grid:

```json
{
  "channel_id": 261,
  "channel_type": "table_3d",
  "channel_name": "Fuel Map",
  "x_axis_channel_id": 300,
  "y_axis_channel_id": 301,
  "x_values": [1000, 2000, 3000, 4000],
  "y_values": [0, 25, 50, 75, 100],
  "z_values": [
    [100, 150, 200, 250],
    [120, 180, 250, 320],
    [140, 220, 310, 400],
    [160, 260, 370, 480],
    [180, 300, 430, 560]
  ]
}
```

---

## 9. PID Controller

PMU-30 supports up to **16 independent PID controllers** for closed-loop control applications such as temperature regulation, motor speed control, idle valve management, and boost pressure control.

### 9.1 Features

- **Proportional, Integral, Derivative** control with configurable gains
- **Anti-windup** with automatic integral clamping during saturation
- **Derivative filter** (low-pass) for noise reduction
- **Configurable output limits** with saturation detection
- **Reverse-acting mode** for cooling applications (higher output = lower process value)
- **Variable sample rate** (default 100ms, configurable per controller)
- **Dynamic setpoint** from channel or fixed value
- **Runtime monitoring** of integral accumulator and saturation state

### 9.2 JSON Configuration

#### Basic Example
```json
{
  "channel_id": 270,
  "channel_type": "pid",
  "channel_name": "Cooling Fan",
  "input_channel_id": 50,
  "setpoint_channel_id": 271,
  "kp": 2.0,
  "ki": 0.1,
  "kd": 0.5,
  "output_min": 0,
  "output_max": 1000,
  "anti_windup": true
}
```

#### Full Configuration (All Parameters)
```json
{
  "channel_id": 270,
  "channel_type": "pid",
  "channel_name": "Idle Control",
  "input_channel_id": 300,
  "setpoint_channel_id": 271,
  "setpoint_value": 850,
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

### 9.3 Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `channel_id` | int | Required | Channel ID (200-999) |
| `channel_type` | string | Required | Must be `"pid"` |
| `channel_name` | string | Required | Display name (max 31 chars) |
| `input_channel_id` | int | Required | Process variable source channel |
| `setpoint_channel_id` | int | Optional | Dynamic setpoint source channel |
| `setpoint_value` | float | 0 | Fixed setpoint (used if no setpoint_channel_id) |
| `kp` | float | 1.0 | Proportional gain |
| `ki` | float | 0.0 | Integral gain |
| `kd` | float | 0.0 | Derivative gain |
| `output_min` | float | 0 | Minimum output value |
| `output_max` | float | 1000 | Maximum output value |
| `sample_time_ms` | int | 100 | PID loop execution period (ms) |
| `anti_windup` | bool | true | Prevent integral windup when saturated |
| `derivative_filter` | bool | false | Apply low-pass filter to derivative |
| `derivative_filter_coeff` | float | 0.1 | Filter coefficient (0-1, lower = more filtering) |
| `reversed` | bool | false | Reverse-acting controller (for cooling) |
| `enabled` | bool | true | Controller enabled |

### 9.4 How It Works

The PID algorithm calculates output based on the error between setpoint and process variable:

```
error = setpoint - process_value  (or negative if reversed)

P_term = Kp × error
I_term = Ki × ∫error dt           (with anti-windup)
D_term = Kd × d(error)/dt         (with optional filtering)

output = clamp(P_term + I_term + D_term, output_min, output_max)
```

**Anti-Windup Behavior:**
When output is saturated (clamped), the integral term stops accumulating in the direction that would increase saturation. This prevents integral windup during large setpoint changes or startup.

**Derivative Filter:**
The derivative term can be noisy with real sensors. Enable `derivative_filter` and set `derivative_filter_coeff` (0.1 = heavy filtering, 0.9 = light filtering) to smooth the derivative response.

### 9.5 Tuning Guide

| Parameter | Effect of Increase | Typical Range |
|-----------|-------------------|---------------|
| **Kp** | Faster response, may cause overshoot | 0.5 - 10.0 |
| **Ki** | Eliminates steady-state error, may cause oscillation | 0.01 - 1.0 |
| **Kd** | Reduces overshoot, sensitive to noise | 0.0 - 2.0 |

**Recommended Starting Values by Application:**

| Application | Kp | Ki | Kd | Sample (ms) | Notes |
|-------------|----|----|----|----|------|
| Temperature control | 2.0 | 0.1 | 0.5 | 500-1000 | Slow process, use derivative filter |
| Fan speed | 1.5 | 0.3 | 0.1 | 100-200 | Medium response |
| Idle valve | 3.0 | 0.5 | 0.2 | 50-100 | Fast response needed |
| Boost control | 2.0 | 0.2 | 0.3 | 20-50 | Fast process, tune carefully |
| Motor position | 5.0 | 0.0 | 2.0 | 10-20 | Often PD only (no integral) |

**Tuning Procedure:**
1. Set Ki=0, Kd=0, start with low Kp
2. Increase Kp until response is fast but stable
3. Add Ki to eliminate steady-state error
4. Add Kd if overshoot is a problem
5. Enable derivative filter if output is noisy

### 9.6 Practical Examples

#### Example 1: Radiator Fan Control
Control fan PWM based on coolant temperature with hysteresis-like behavior.

```json
{
  "channel_id": 270,
  "channel_type": "pid",
  "channel_name": "Radiator Fan",
  "input_channel_id": 50,
  "setpoint_value": 85.0,
  "kp": 20.0,
  "ki": 0.5,
  "kd": 1.0,
  "output_min": 0,
  "output_max": 1000,
  "sample_time_ms": 500,
  "anti_windup": true,
  "reversed": true
}
```
*Note: `reversed: true` because higher fan speed should reduce temperature.*

#### Example 2: Idle Speed Control
Maintain target RPM using idle air control valve.

```json
{
  "channel_id": 271,
  "channel_type": "pid",
  "channel_name": "Idle Control",
  "input_channel_id": 300,
  "setpoint_channel_id": 272,
  "kp": 0.5,
  "ki": 0.1,
  "kd": 0.05,
  "output_min": 100,
  "output_max": 800,
  "sample_time_ms": 50,
  "anti_windup": true,
  "derivative_filter": true,
  "derivative_filter_coeff": 0.2
}
```

#### Example 3: Boost Pressure Control
Control wastegate duty cycle to maintain target boost.

```json
{
  "channel_id": 273,
  "channel_type": "pid",
  "channel_name": "Boost Control",
  "input_channel_id": 51,
  "setpoint_channel_id": 274,
  "kp": 3.0,
  "ki": 0.3,
  "kd": 0.5,
  "output_min": 0,
  "output_max": 1000,
  "sample_time_ms": 20,
  "anti_windup": true
}
```

### 9.7 C API Reference

```c
#include "pmu_pid.h"

/* Constants */
#define PMU_PID_MAX_CONTROLLERS   16   /* Maximum PID controllers */
#define PMU_PID_DEFAULT_SAMPLE_MS 100  /* Default sample time */
```

#### Initialization
```c
HAL_StatusTypeDef PMU_PID_Init(void);
```

#### Controller Management
```c
/* Add or update a PID controller */
HAL_StatusTypeDef PMU_PID_AddController(const PMU_PIDConfig_t* config);

/* Remove a PID controller by ID */
HAL_StatusTypeDef PMU_PID_RemoveController(const char* id);

/* Clear all PID controllers */
HAL_StatusTypeDef PMU_PID_ClearAll(void);

/* Enable or disable a controller */
HAL_StatusTypeDef PMU_PID_SetEnabled(const char* id, bool enabled);

/* Reset controller state (clears integral, previous error) */
HAL_StatusTypeDef PMU_PID_Reset(const char* id);
```

#### Runtime Control
```c
/* Update all PID controllers (call from main loop) */
void PMU_PID_Update(void);

/* Get controller output value */
float PMU_PID_GetOutput(const char* id);

/* Set controller setpoint programmatically */
HAL_StatusTypeDef PMU_PID_SetSetpoint(const char* id, float setpoint);
```

#### Status and Monitoring
```c
/* Get controller state (integral, saturation, etc.) */
const PMU_PIDState_t* PMU_PID_GetState(const char* id);

/* Get system statistics */
const PMU_PIDStats_t* PMU_PID_GetStats(void);

/* List all configured controllers */
uint8_t PMU_PID_ListControllers(PMU_PIDConfig_t* configs, uint8_t max_count);
```

### 9.8 Data Structures

```c
typedef struct {
    char id[PMU_CHANNEL_ID_LEN];       /* Channel ID */

    /* Input/Output channel references */
    char setpoint_channel[PMU_CHANNEL_ID_LEN];  /* Setpoint source (optional) */
    char process_channel[PMU_CHANNEL_ID_LEN];   /* Process variable source */
    char output_channel[PMU_CHANNEL_ID_LEN];    /* Output destination (optional) */

    /* PID gains */
    float kp;                          /* Proportional gain */
    float ki;                          /* Integral gain */
    float kd;                          /* Derivative gain */

    /* Setpoint */
    float setpoint_value;              /* Fixed setpoint (if no channel) */

    /* Output limits */
    float output_min;                  /* Minimum output value */
    float output_max;                  /* Maximum output value */

    /* Advanced settings */
    uint16_t sample_time_ms;           /* PID loop execution period */
    bool anti_windup;                  /* Prevent integral windup */
    bool derivative_filter;            /* Apply low-pass filter to derivative */
    float derivative_filter_coeff;     /* Filter coefficient (0-1) */

    /* Control options */
    bool enabled;                      /* Controller enabled */
    bool reversed;                     /* Reverse acting controller */
} PMU_PIDConfig_t;

typedef struct {
    PMU_PIDConfig_t config;            /* Configuration */

    /* Runtime state */
    float integral;                    /* Integral accumulator */
    float prev_error;                  /* Previous error */
    float prev_derivative;             /* Previous derivative (for filter) */
    float output;                      /* Current output value */

    /* Status */
    bool active;                       /* Controller slot is active */
    bool saturated;                    /* Output is saturated (clamped) */
    uint32_t last_update_ms;           /* Last update timestamp */
} PMU_PIDState_t;

typedef struct {
    uint8_t total_controllers;         /* Total configured */
    uint8_t active_controllers;        /* Currently enabled */
    uint32_t total_updates;            /* Total update cycles */
} PMU_PIDStats_t;
```

### 9.9 Troubleshooting

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| Output oscillates | Ki too high or Kd too low | Reduce Ki, increase Kd |
| Slow to reach setpoint | Kp too low or Ki=0 | Increase Kp or add Ki |
| Large overshoot | Kp too high, Ki too high, or Kd=0 | Reduce Kp/Ki, add Kd |
| Output jumps erratically | Noisy input signal | Enable derivative_filter |
| Never reaches setpoint | Wrong sign (cooling vs heating) | Set `reversed: true` |
| Output stuck at min/max | Integral windup | Ensure `anti_windup: true` |
| No output change | Controller disabled | Check `enabled: true` |

---

## 10. C API Reference

### 10.1 Initialization

```c
#include "pmu_logic_functions.h"

HAL_StatusTypeDef PMU_LogicFunctions_Init(void);
```

### 10.2 Function Registration

```c
// Register configured function
HAL_StatusTypeDef PMU_LogicFunctions_Register(PMU_LogicFunction_t* func);

// Remove function
HAL_StatusTypeDef PMU_LogicFunctions_Unregister(uint16_t function_id);

// Get function by ID
PMU_LogicFunction_t* PMU_LogicFunctions_GetByID(uint16_t function_id);
```

### 10.3 Helper Functions

```c
// Create math function
uint16_t PMU_LogicFunctions_CreateMath(
    PMU_FunctionType_t type, uint16_t output_ch,
    uint16_t input_a, uint16_t input_b);

// Create comparison
uint16_t PMU_LogicFunctions_CreateComparison(
    PMU_FunctionType_t type, uint16_t output_ch,
    uint16_t input_a, uint16_t input_b);

// Create PID controller
uint16_t PMU_LogicFunctions_CreatePID(
    uint16_t output_ch, uint16_t input_ch,
    float setpoint, float kp, float ki, float kd);

// Create hysteresis
uint16_t PMU_LogicFunctions_CreateHysteresis(
    uint16_t output_ch, uint16_t input_ch,
    int32_t threshold_on, int32_t threshold_off);
```

### 10.4 Execution

```c
// Execute all functions (called at 500Hz)
void PMU_LogicFunctions_Update(void);

// Enable/disable function
HAL_StatusTypeDef PMU_LogicFunctions_SetEnabled(uint16_t function_id, bool enabled);
```

### 10.5 Data Structures

```c
typedef struct {
    uint16_t function_id;          // Unique ID (0-63)
    PMU_FunctionType_t type;       // Function type
    uint16_t output_channel;       // Output channel ID
    uint16_t input_channels[8];    // Input channel IDs
    uint8_t input_count;           // Number of inputs
    uint8_t enabled;               // Enable flag
    union { /* type-specific params */ } params;
} PMU_LogicFunction_t;

typedef struct {
    float kp, ki, kd;              // PID gains
    float setpoint;                // Target value
    int32_t output_min, output_max;// Output limits
    float integral;                // Internal state
    int32_t last_error;
} PMU_PID_Config_t;
```

---

## See Also

- [Channels Reference](channels.md) - Channel system overview
- [Configuration Reference](configuration.md) - Full JSON schema
- [Examples](../examples/logic-examples.md) - Practical examples

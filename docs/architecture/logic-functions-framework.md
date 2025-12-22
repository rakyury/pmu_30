# Logic Functions Framework Architecture

**Version:** 1.0
**Date:** December 2024
**Author:** R2 m-sport

---

## Table of Contents

1. [Overview](#1-overview)
2. [Function Categories](#2-function-categories)
3. [Function Signatures](#3-function-signatures)
4. [Execution Model](#4-execution-model)
5. [Parameter Validation](#5-parameter-validation)
6. [Error Handling](#6-error-handling)
7. [Extension Points](#7-extension-points)
8. [Performance Considerations](#8-performance-considerations)

---

## 1. Overview

The Logic Functions Framework provides a comprehensive set of 64 built-in functions for real-time signal processing, control, and automation in the PMU-30. Functions operate on the Unified Channel System, reading from input channels and writing to output channels.

### 1.1 Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Deterministic** | Fixed execution time, predictable behavior |
| **Composable** | Functions can chain together |
| **Real-time** | 500Hz update rate guaranteed |
| **Type-safe** | Strict input/output validation |
| **Extensible** | Custom Lua functions supported |

### 1.2 System Limits

| Parameter | Value | Description |
|-----------|-------|-------------|
| Maximum Functions | 64 | Registered logic functions |
| Maximum Inputs | 8 | Inputs per function |
| Update Rate | 500 Hz | Function execution frequency |
| Execution Budget | 2 ms | Maximum per cycle |

---

## 2. Function Categories

### 2.1 Category Overview

```
Logic Functions (64 total)
|
+-- Mathematical Operations (0x00-0x0F) -------- 10 functions
|   ADD, SUBTRACT, MULTIPLY, DIVIDE, MIN,
|   MAX, AVERAGE, ABS, SCALE, CLAMP
|
+-- Comparison Operations (0x20-0x2F) ---------- 7 functions
|   GREATER, LESS, EQUAL, NOT_EQUAL,
|   GREATER_EQUAL, LESS_EQUAL, IN_RANGE
|
+-- Logic Operations (0x40-0x4F) --------------- 6 functions
|   AND, OR, NOT, XOR, NAND, NOR
|
+-- Lookup Tables (0x60-0x6F) ------------------ 2 functions
|   TABLE_1D, TABLE_2D
|
+-- Filters (0x80-0x8F) ------------------------ 5 functions
|   MOVING_AVG, MIN_WINDOW, MAX_WINDOW,
|   MEDIAN, LOW_PASS
|
+-- Control (0xA0-0xAF) ------------------------ 4 functions
|   PID, HYSTERESIS, RATE_LIMIT, DEBOUNCE
|
+-- Special (0xC0-0xCF) ------------------------ 4 functions
    MUX, DEMUX, CONDITIONAL, CUSTOM_LUA
```

### 2.2 Mathematical Operations (0x00-0x0F)

| Code | Function | Formula | Inputs | Output |
|------|----------|---------|--------|--------|
| 0x00 | ADD | A + B | 2 | Sum |
| 0x01 | SUBTRACT | A - B | 2 | Difference |
| 0x02 | MULTIPLY | A * B | 2 | Product |
| 0x03 | DIVIDE | A / B | 2 | Quotient |
| 0x04 | MIN | min(A, B, ...) | 2-8 | Minimum |
| 0x05 | MAX | max(A, B, ...) | 2-8 | Maximum |
| 0x06 | AVERAGE | sum / count | 2-8 | Average |
| 0x07 | ABS | |A| | 1 | Absolute |
| 0x08 | SCALE | A * scale + offset | 1 | Scaled |
| 0x09 | CLAMP | clamp(A, min, max) | 1 | Clamped |

**Example: Temperature Scaling**
```
Input: Raw ADC (0-4095)
Function: SCALE
Parameters: scale = 0.0122, offset = -40
Output: Temperature in °C (-40 to +125)
```

### 2.3 Comparison Operations (0x20-0x2F)

| Code | Function | Condition | Output |
|------|----------|-----------|--------|
| 0x20 | GREATER | A > B | 1 if true |
| 0x21 | LESS | A < B | 1 if true |
| 0x22 | EQUAL | A == B | 1 if true |
| 0x23 | NOT_EQUAL | A != B | 1 if true |
| 0x24 | GREATER_EQUAL | A >= B | 1 if true |
| 0x25 | LESS_EQUAL | A <= B | 1 if true |
| 0x26 | IN_RANGE | min <= A <= max | 1 if true |

**Example: Overheat Detection**
```
Input A: Coolant Temperature (channel)
Input B: Threshold (constant 100°C)
Function: GREATER
Output: 1 when overheating
```

### 2.4 Logic Operations (0x40-0x4F)

| Code | Function | Truth Table | Inputs |
|------|----------|-------------|--------|
| 0x40 | AND | All inputs true | 2-8 |
| 0x41 | OR | Any input true | 2-8 |
| 0x42 | NOT | Invert input | 1 |
| 0x43 | XOR | Odd number true | 2 |
| 0x44 | NAND | NOT(AND) | 2-8 |
| 0x45 | NOR | NOT(OR) | 2-8 |

**Example: Safety Interlock**
```
Input A: Engine Running
Input B: Door Closed
Input C: Seatbelt Fastened
Function: AND
Output: System Ready (all conditions met)
```

### 2.5 Lookup Tables (0x60-0x6F)

| Code | Function | Description | Parameters |
|------|----------|-------------|------------|
| 0x60 | TABLE_1D | 1D interpolation | X values, Y values |
| 0x61 | TABLE_2D | 2D map interpolation | X, Y, Z values |

**1D Table Structure:**
```
Y
^
|     *---*
|   *
| *
+-----------> X

Points: [(x0,y0), (x1,y1), ..., (xn,yn)]
Interpolation: Linear between points
```

**2D Table Structure:**
```
      Y0    Y1    Y2    Y3
X0  [ z00   z01   z02   z03 ]
X1  [ z10   z11   z12   z13 ]
X2  [ z20   z21   z22   z23 ]

Interpolation: Bilinear
```

### 2.6 Filters (0x80-0x8F)

| Code | Function | Description | Parameters |
|------|----------|-------------|------------|
| 0x80 | MOVING_AVG | Running average | window_size |
| 0x81 | MIN_WINDOW | Minimum over window | window_size |
| 0x82 | MAX_WINDOW | Maximum over window | window_size |
| 0x83 | MEDIAN | Median filter | window_size |
| 0x84 | LOW_PASS | RC low-pass filter | time_constant |

**Moving Average:**
```
output = (sample[n] + sample[n-1] + ... + sample[n-w+1]) / w

Where w = window_size (typically 4-32 samples)
```

**Low-Pass Filter (RC):**
```
alpha = dt / (tau + dt)
output = alpha * input + (1 - alpha) * previous_output

Where:
  dt = sample period (2ms at 500Hz)
  tau = time constant (user-defined)
```

### 2.7 Control Functions (0xA0-0xAF)

| Code | Function | Description | Parameters |
|------|----------|-------------|------------|
| 0xA0 | PID | PID controller | Kp, Ki, Kd, setpoint |
| 0xA1 | HYSTERESIS | Schmitt trigger | threshold_on, threshold_off |
| 0xA2 | RATE_LIMIT | Slew rate limiter | max_rate |
| 0xA3 | DEBOUNCE | Digital debounce | debounce_ms |

**PID Controller:**
```
error = setpoint - input
P = Kp * error
I = Ki * integral(error)
D = Kd * derivative(error)
output = clamp(P + I + D, min, max)
```

**Hysteresis (Schmitt Trigger):**
```
         ON threshold
            |
State: -----+--------> ON
            |
        ----+--------> OFF
            |
         OFF threshold

Prevents oscillation around threshold
```

### 2.8 Special Functions (0xC0-0xCF)

| Code | Function | Description | Parameters |
|------|----------|-------------|------------|
| 0xC0 | MUX | Multiplexer | selector, inputs[] |
| 0xC1 | DEMUX | Demultiplexer | selector, input |
| 0xC2 | CONDITIONAL | Ternary operator | condition, true_val, false_val |
| 0xC3 | CUSTOM_LUA | Lua script | script_id |

**Multiplexer:**
```
selector = 0 -> output = input[0]
selector = 1 -> output = input[1]
selector = N -> output = input[N]
```

**Conditional:**
```
output = condition ? true_value : false_value
```

---

## 3. Function Signatures

### 3.1 Function Configuration Structure

```c
typedef struct {
    uint16_t function_id;          // Unique function ID
    PMU_FunctionType_t type;       // Function type
    uint16_t output_channel;       // Output channel ID
    uint16_t input_channels[8];    // Input channel IDs
    uint8_t input_count;           // Number of inputs
    uint8_t enabled;               // Enable flag

    union {
        // Type-specific parameters
        struct { int32_t scale; int32_t offset; } scale;
        struct { int32_t min; int32_t max; } clamp;
        PMU_PID_Config_t pid;
        PMU_Table1D_t table_1d;
        PMU_Table2D_t table_2d;
        // ... other types
    } params;
} PMU_LogicFunction_t;
```

### 3.2 Return Values

All functions return `int32_t` values:

| Return Type | Range | Description |
|-------------|-------|-------------|
| Boolean | 0 or 1 | Comparison/Logic results |
| Percentage | 0-1000 | 0.0% to 100.0% |
| Signed | -2^31 to 2^31-1 | Full range |
| Fixed-point | varies | x1000 scaling typical |

### 3.3 Input Specifications

| Input Type | Valid Range | Default |
|------------|-------------|---------|
| Channel ID | 0-1023 | Required |
| Constant | -2^31 to 2^31-1 | 0 |
| Boolean | 0 or 1 | 0 |
| Percentage | 0-1000 | 0 |

---

## 4. Execution Model

### 4.1 Execution Pipeline

```
                    500 Hz Timer Interrupt
                            |
                            v
+----------------------------------------------------------------+
|                    PMU_LogicFunctions_Update()                 |
+----------------------------------------------------------------+
            |
            v
+------------------------+
| For each enabled       |
| function (0-63):       |
+------------------------+
            |
            v
+------------------------+
| 1. Read Input Channels |
|    - Fetch values      |
|    - Check validity    |
+------------------------+
            |
            v
+------------------------+
| 2. Execute Function    |
|    - Apply algorithm   |
|    - Compute result    |
+------------------------+
            |
            v
+------------------------+
| 3. Write Output        |
|    - Update channel    |
|    - Set flags         |
+------------------------+
            |
            v
     Next Function
```

### 4.2 Execution Order

Functions execute in ID order (0 to 63). This allows chaining:

```
Function 0: Read ADC -> Scale -> Output to Virtual Channel 200
Function 1: Read Channel 200 -> Compare -> Output to Channel 201
Function 2: Read Channel 201 -> AND with other -> Output to PROFET
```

### 4.3 Timing Guarantees

| Metric | Value |
|--------|-------|
| Update period | 2 ms (500 Hz) |
| Max execution time | 2 ms total |
| Per-function budget | ~30 us average |
| Jitter | < 100 us |

---

## 5. Parameter Validation

### 5.1 Validation Rules

| Parameter | Validation | Action on Failure |
|-----------|------------|-------------------|
| function_id | 0-63 | Reject registration |
| type | Valid enum | Reject registration |
| output_channel | 0-1023 | Reject registration |
| input_channels | 0-1023 | Use default (0) |
| input_count | 1-8 | Clamp to range |

### 5.2 Runtime Checks

```c
HAL_StatusTypeDef PMU_LogicFunctions_Register(PMU_LogicFunction_t* func) {
    // Validate function ID
    if (func->function_id >= PMU_MAX_LOGIC_FUNCTIONS) {
        return HAL_ERROR;
    }

    // Validate function type
    if (!is_valid_function_type(func->type)) {
        return HAL_ERROR;
    }

    // Validate channel IDs
    if (func->output_channel >= PMU_CHANNEL_MAX_CHANNELS) {
        return HAL_ERROR;
    }

    for (uint8_t i = 0; i < func->input_count; i++) {
        if (func->input_channels[i] >= PMU_CHANNEL_MAX_CHANNELS) {
            return HAL_ERROR;
        }
    }

    // Type-specific validation
    switch (func->type) {
        case PMU_FUNC_PID:
            if (func->params.pid.kp < 0 || func->params.pid.ki < 0) {
                return HAL_ERROR;
            }
            break;
        // ... other types
    }

    return HAL_OK;
}
```

---

## 6. Error Handling

### 6.1 Error Conditions

| Error | Detection | Response |
|-------|-----------|----------|
| Division by zero | B == 0 | Return 0 or max |
| Overflow | Result > INT32_MAX | Clamp to max |
| Invalid input | Channel not found | Use default value |
| Timeout | Channel stale | Use last value |

### 6.2 Error Propagation

```c
int32_t execute_divide(int32_t a, int32_t b) {
    if (b == 0) {
        // Log error
        PMU_Error_Log(ERR_DIVIDE_BY_ZERO);
        // Return safe value
        return (a >= 0) ? INT32_MAX : INT32_MIN;
    }
    return a / b;
}
```

### 6.3 Fault Flags

Each function can set fault flags in output channel:

```c
// Set fault flag on output channel
if (error_detected) {
    PMU_Channel_t* ch = PMU_Channel_GetInfo(func->output_channel);
    ch->flags |= PMU_CHANNEL_FLAG_FAULT;
}
```

---

## 7. Extension Points

### 7.1 Custom Lua Functions

The framework supports custom functions written in Lua:

```lua
-- Custom function example: weighted average
function weighted_average(inputs, weights)
    local sum = 0
    local weight_sum = 0
    for i, v in ipairs(inputs) do
        sum = sum + v * weights[i]
        weight_sum = weight_sum + weights[i]
    end
    return sum / weight_sum
end
```

### 7.2 Registration API

```c
// Register custom Lua function
uint16_t PMU_LogicFunctions_RegisterLua(
    const char* script,
    uint16_t output_channel,
    uint16_t* input_channels,
    uint8_t input_count
);
```

### 7.3 Custom C Functions

For high-performance requirements:

```c
// Custom function prototype
typedef int32_t (*PMU_CustomFunc_t)(int32_t* inputs, uint8_t count, void* params);

// Registration
HAL_StatusTypeDef PMU_LogicFunctions_RegisterCustom(
    uint16_t function_id,
    PMU_CustomFunc_t func,
    void* params
);
```

---

## 8. Performance Considerations

### 8.1 Optimization Guidelines

| Guideline | Benefit |
|-----------|---------|
| Minimize function count | Reduce execution time |
| Use appropriate filter size | Balance response vs stability |
| Avoid unnecessary calculations | Save CPU cycles |
| Chain related functions | Share intermediate results |

### 8.2 Function Complexity

| Function | Typical Time | Notes |
|----------|--------------|-------|
| ADD/SUBTRACT | < 1 us | Simple arithmetic |
| MULTIPLY/DIVIDE | 1-2 us | Hardware multiply |
| AND/OR/NOT | < 1 us | Bitwise operations |
| TABLE_1D | 2-5 us | Linear search + interpolation |
| TABLE_2D | 5-10 us | 2D interpolation |
| PID | 3-5 us | Multiple operations |
| MOVING_AVG | 2-3 us | Array access |
| MEDIAN | 5-10 us | Sorting required |
| CUSTOM_LUA | 50-500 us | Interpreted |

### 8.3 Memory Usage

| Component | Size per Function |
|-----------|-------------------|
| Base structure | 64 bytes |
| PID state | 32 bytes |
| 1D table (16 points) | 128 bytes |
| 2D table (8x8) | 256 bytes |
| Moving average buffer | window_size * 4 bytes |

---

## See Also

- [Unified Channel System](unified-channel-system.md)
- [Logic Functions API Reference](../api/logic-functions-reference.md)
- [Logic Functions Integration Guide](../guides/logic-functions-integration.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

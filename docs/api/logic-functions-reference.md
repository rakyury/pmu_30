# Logic Functions API Reference

**Version:** 1.0
**Date:** December 2024
**Module:** pmu_logic_functions.h

---

## Table of Contents

1. [Overview](#1-overview)
2. [Initialization](#2-initialization)
3. [Function Registration](#3-function-registration)
4. [Function Control](#4-function-control)
5. [Helper Functions](#5-helper-functions)
6. [Data Types](#6-data-types)
7. [Function Types Reference](#7-function-types-reference)
8. [Examples](#8-examples)

---

## 1. Overview

The Logic Functions API provides programmatic access to the 64-function logic engine. Functions read from input channels, perform computations, and write to output channels at 500Hz.

### 1.1 Include Header

```c
#include "pmu_logic_functions.h"
```

### 1.2 API Summary

| Function | Description |
|----------|-------------|
| `PMU_LogicFunctions_Init()` | Initialize module |
| `PMU_LogicFunctions_Register()` | Register new function |
| `PMU_LogicFunctions_Unregister()` | Remove function |
| `PMU_LogicFunctions_Update()` | Execute all functions |
| `PMU_LogicFunctions_GetByID()` | Get function by ID |
| `PMU_LogicFunctions_SetEnabled()` | Enable/disable function |
| `PMU_LogicFunctions_CreateMath()` | Create math function |
| `PMU_LogicFunctions_CreateComparison()` | Create comparison |
| `PMU_LogicFunctions_CreatePID()` | Create PID controller |
| `PMU_LogicFunctions_CreateHysteresis()` | Create hysteresis |

---

## 2. Initialization

### PMU_LogicFunctions_Init

Initialize the logic functions module.

```c
HAL_StatusTypeDef PMU_LogicFunctions_Init(void);
```

**Parameters:** None

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | Initialization successful |
| `HAL_ERROR` | Initialization failed |

**Example:**
```c
void system_init(void) {
    PMU_Channel_Init();  // Initialize channels first
    if (PMU_LogicFunctions_Init() != HAL_OK) {
        Error_Handler();
    }
}
```

---

## 3. Function Registration

### PMU_LogicFunctions_Register

Register a fully configured logic function.

```c
HAL_StatusTypeDef PMU_LogicFunctions_Register(PMU_LogicFunction_t* func);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| func | `PMU_LogicFunction_t*` | Pointer to function config |

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | Registration successful |
| `HAL_ERROR` | Invalid config or ID collision |

**Example:**
```c
PMU_LogicFunction_t add_func = {
    .function_id = 0,
    .type = PMU_FUNC_ADD,
    .output_channel = 200,
    .input_channels = {0, 1},
    .input_count = 2,
    .enabled = 1
};

PMU_LogicFunctions_Register(&add_func);
```

---

### PMU_LogicFunctions_Unregister

Remove a logic function.

```c
HAL_StatusTypeDef PMU_LogicFunctions_Unregister(uint16_t function_id);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| function_id | `uint16_t` | Function ID (0-63) |

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | Unregistration successful |
| `HAL_ERROR` | Function not found |

---

## 4. Function Control

### PMU_LogicFunctions_Update

Execute all enabled logic functions. Called at 500Hz.

```c
void PMU_LogicFunctions_Update(void);
```

**Parameters:** None

**Returns:** None

**Notes:**
- Executes functions in ID order (0-63)
- Respects enabled flag
- Thread-safe operation

---

### PMU_LogicFunctions_GetByID

Get function configuration by ID.

```c
PMU_LogicFunction_t* PMU_LogicFunctions_GetByID(uint16_t function_id);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| function_id | `uint16_t` | Function ID (0-63) |

**Returns:**
| Value | Description |
|-------|-------------|
| `PMU_LogicFunction_t*` | Pointer to function |
| `NULL` | Function not found |

---

### PMU_LogicFunctions_SetEnabled

Enable or disable a function.

```c
HAL_StatusTypeDef PMU_LogicFunctions_SetEnabled(uint16_t function_id, bool enabled);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| function_id | `uint16_t` | Function ID (0-63) |
| enabled | `bool` | Enable state |

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | State changed |
| `HAL_ERROR` | Function not found |

---

## 5. Helper Functions

### PMU_LogicFunctions_CreateMath

Create a simple math function (add, subtract, multiply, divide).

```c
uint16_t PMU_LogicFunctions_CreateMath(
    PMU_FunctionType_t type,
    uint16_t output_ch,
    uint16_t input_a,
    uint16_t input_b
);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| type | `PMU_FunctionType_t` | Math type (ADD, SUBTRACT, etc.) |
| output_ch | `uint16_t` | Output channel ID |
| input_a | `uint16_t` | First input channel |
| input_b | `uint16_t` | Second input channel |

**Returns:** Function ID (0-63) or 0 on error

**Example:**
```c
// Create: channel[200] = channel[0] + channel[1]
uint16_t func_id = PMU_LogicFunctions_CreateMath(
    PMU_FUNC_ADD, 200, 0, 1
);
```

---

### PMU_LogicFunctions_CreateComparison

Create a comparison function.

```c
uint16_t PMU_LogicFunctions_CreateComparison(
    PMU_FunctionType_t type,
    uint16_t output_ch,
    uint16_t input_a,
    uint16_t input_b
);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| type | `PMU_FunctionType_t` | Comparison type |
| output_ch | `uint16_t` | Output channel (0 or 1) |
| input_a | `uint16_t` | First input channel |
| input_b | `uint16_t` | Second input channel |

**Returns:** Function ID or 0 on error

**Example:**
```c
// Create: channel[201] = (channel[0] > channel[1]) ? 1 : 0
uint16_t func_id = PMU_LogicFunctions_CreateComparison(
    PMU_FUNC_GREATER, 201, 0, 1
);
```

---

### PMU_LogicFunctions_CreatePID

Create a PID controller function.

```c
uint16_t PMU_LogicFunctions_CreatePID(
    uint16_t output_ch,
    uint16_t input_ch,
    float setpoint,
    float kp,
    float ki,
    float kd
);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| output_ch | `uint16_t` | Output channel (control signal) |
| input_ch | `uint16_t` | Input channel (process variable) |
| setpoint | `float` | Target value |
| kp | `float` | Proportional gain |
| ki | `float` | Integral gain |
| kd | `float` | Derivative gain |

**Returns:** Function ID or 0 on error

**Example:**
```c
// Temperature control: maintain 80C
uint16_t pid_id = PMU_LogicFunctions_CreatePID(
    100,    // PWM output for heater
    0,      // Temperature sensor input
    800,    // 80.0 C (x10 format)
    2.0f,   // Kp
    0.1f,   // Ki
    0.5f    // Kd
);
```

---

### PMU_LogicFunctions_CreateHysteresis

Create a hysteresis (Schmitt trigger) function.

```c
uint16_t PMU_LogicFunctions_CreateHysteresis(
    uint16_t output_ch,
    uint16_t input_ch,
    int32_t threshold_on,
    int32_t threshold_off
);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| output_ch | `uint16_t` | Output channel (0 or 1) |
| input_ch | `uint16_t` | Input channel |
| threshold_on | `int32_t` | Turn ON threshold |
| threshold_off | `int32_t` | Turn OFF threshold |

**Returns:** Function ID or 0 on error

**Example:**
```c
// Fan control with hysteresis
// ON above 90C, OFF below 80C
uint16_t hyst_id = PMU_LogicFunctions_CreateHysteresis(
    100,    // Fan output
    0,      // Temperature input
    900,    // 90.0 C ON threshold
    800     // 80.0 C OFF threshold
);
```

---

## 6. Data Types

### PMU_FunctionType_t

```c
typedef enum {
    // Mathematical (0x00-0x0F)
    PMU_FUNC_ADD = 0x00,
    PMU_FUNC_SUBTRACT,
    PMU_FUNC_MULTIPLY,
    PMU_FUNC_DIVIDE,
    PMU_FUNC_MIN,
    PMU_FUNC_MAX,
    PMU_FUNC_AVERAGE,
    PMU_FUNC_ABS,
    PMU_FUNC_SCALE,
    PMU_FUNC_CLAMP,

    // Comparison (0x20-0x2F)
    PMU_FUNC_GREATER = 0x20,
    PMU_FUNC_LESS,
    PMU_FUNC_EQUAL,
    PMU_FUNC_NOT_EQUAL,
    PMU_FUNC_GREATER_EQUAL,
    PMU_FUNC_LESS_EQUAL,
    PMU_FUNC_IN_RANGE,

    // Logic (0x40-0x4F)
    PMU_FUNC_AND = 0x40,
    PMU_FUNC_OR,
    PMU_FUNC_NOT,
    PMU_FUNC_XOR,
    PMU_FUNC_NAND,
    PMU_FUNC_NOR,

    // Tables (0x60-0x6F)
    PMU_FUNC_TABLE_1D = 0x60,
    PMU_FUNC_TABLE_2D,

    // Filters (0x80-0x8F)
    PMU_FUNC_MOVING_AVG = 0x80,
    PMU_FUNC_MIN_WINDOW,
    PMU_FUNC_MAX_WINDOW,
    PMU_FUNC_MEDIAN,
    PMU_FUNC_LOW_PASS,

    // Control (0xA0-0xAF)
    PMU_FUNC_PID = 0xA0,
    PMU_FUNC_HYSTERESIS,
    PMU_FUNC_RATE_LIMIT,
    PMU_FUNC_DEBOUNCE,

    // Special (0xC0-0xCF)
    PMU_FUNC_MUX = 0xC0,
    PMU_FUNC_DEMUX,
    PMU_FUNC_CONDITIONAL,
    PMU_FUNC_CUSTOM_LUA,
} PMU_FunctionType_t;
```

---

### PMU_LogicFunction_t

```c
typedef struct {
    uint16_t function_id;          // Unique ID (0-63)
    PMU_FunctionType_t type;       // Function type
    uint16_t output_channel;       // Output channel ID
    uint16_t input_channels[8];    // Input channel IDs
    uint8_t input_count;           // Number of inputs
    uint8_t enabled;               // Enable flag

    union {
        struct {
            int32_t scale;         // Scale factor (x1000)
            int32_t offset;        // Offset value
        } scale;

        struct {
            int32_t min;           // Minimum value
            int32_t max;           // Maximum value
        } clamp;

        PMU_PID_Config_t pid;
        PMU_Table1D_t table_1d;
        PMU_Table2D_t table_2d;
        PMU_MovingAvg_t moving_avg;

        struct {
            int32_t threshold_on;
            int32_t threshold_off;
            uint8_t state;
        } hysteresis;

        struct {
            int32_t max_rate;
            int32_t last_value;
            uint32_t last_update_ms;
        } rate_limit;

        struct {
            uint32_t debounce_ms;
            uint8_t state;
            uint32_t last_change_ms;
        } debounce;

        uint8_t custom_params[64];
    } params;
} PMU_LogicFunction_t;
```

---

### PMU_PID_Config_t

```c
typedef struct {
    float kp;                      // Proportional gain
    float ki;                      // Integral gain
    float kd;                      // Derivative gain
    float setpoint;                // Target value
    int32_t output_min;            // Min output
    int32_t output_max;            // Max output
    float integral;                // Internal state
    int32_t last_error;            // Internal state
    uint32_t last_update_ms;       // Internal state
} PMU_PID_Config_t;
```

---

### PMU_Table1D_t

```c
typedef struct {
    uint16_t size;                 // Number of points
    int32_t* x_values;             // X axis values
    int32_t* y_values;             // Y axis values
} PMU_Table1D_t;
```

---

### PMU_Table2D_t

```c
typedef struct {
    uint16_t x_size;               // X axis size
    uint16_t y_size;               // Y axis size
    int32_t* x_values;             // X axis values
    int32_t* y_values;             // Y axis values
    int32_t* z_values;             // Z values (x_size * y_size)
} PMU_Table2D_t;
```

---

## 7. Function Types Reference

### 7.1 Mathematical Functions

| Type | Inputs | Formula | Notes |
|------|--------|---------|-------|
| ADD | 2 | A + B | Overflow saturates |
| SUBTRACT | 2 | A - B | |
| MULTIPLY | 2 | A * B | Result / 1000 for fixed-point |
| DIVIDE | 2 | A / B | B=0 returns MAX |
| MIN | 2-8 | min(inputs) | |
| MAX | 2-8 | max(inputs) | |
| AVERAGE | 2-8 | sum / count | |
| ABS | 1 | |A| | |
| SCALE | 1 | A * scale / 1000 + offset | |
| CLAMP | 1 | clamp(A, min, max) | |

### 7.2 Comparison Functions

| Type | Inputs | Result | Notes |
|------|--------|--------|-------|
| GREATER | 2 | A > B ? 1 : 0 | |
| LESS | 2 | A < B ? 1 : 0 | |
| EQUAL | 2 | A == B ? 1 : 0 | |
| NOT_EQUAL | 2 | A != B ? 1 : 0 | |
| GREATER_EQUAL | 2 | A >= B ? 1 : 0 | |
| LESS_EQUAL | 2 | A <= B ? 1 : 0 | |
| IN_RANGE | 3 | min <= A <= max ? 1 : 0 | inputs: value, min, max |

### 7.3 Logic Functions

| Type | Inputs | Result | Notes |
|------|--------|--------|-------|
| AND | 2-8 | All non-zero | |
| OR | 2-8 | Any non-zero | |
| NOT | 1 | !A | |
| XOR | 2 | A ^ B | |
| NAND | 2-8 | !(AND) | |
| NOR | 2-8 | !(OR) | |

### 7.4 Filter Functions

| Type | Parameters | Description |
|------|------------|-------------|
| MOVING_AVG | window_size | Running average |
| MIN_WINDOW | window_size | Minimum over time |
| MAX_WINDOW | window_size | Maximum over time |
| MEDIAN | window_size | Median filter |
| LOW_PASS | time_constant | RC filter |

### 7.5 Control Functions

| Type | Parameters | Description |
|------|------------|-------------|
| PID | Kp, Ki, Kd, setpoint | PID controller |
| HYSTERESIS | on_thresh, off_thresh | Schmitt trigger |
| RATE_LIMIT | max_rate | Slew limiter |
| DEBOUNCE | debounce_ms | Digital filter |

### 7.6 Special Functions

| Type | Parameters | Description |
|------|------------|-------------|
| MUX | selector | Select input by index |
| DEMUX | selector | Route to output |
| CONDITIONAL | condition | Ternary: cond ? A : B |
| CUSTOM_LUA | script_id | Lua function |

---

## 8. Examples

### 8.1 Temperature-Controlled Fan

```c
void setup_fan_control(void) {
    // Read temperature from ADC channel 0
    // Control fan on output channel 100

    // Create hysteresis: ON > 85C, OFF < 75C
    uint16_t func_id = PMU_LogicFunctions_CreateHysteresis(
        100,    // Fan output (PROFET)
        0,      // Temperature sensor (ADC)
        850,    // 85.0 C ON
        750     // 75.0 C OFF
    );

    if (func_id == 0) {
        // Error handling
    }
}
```

### 8.2 Fuel Pump Safety

```c
void setup_fuel_pump_safety(void) {
    // Fuel pump runs only when:
    // - Engine running (RPM > 500)
    // - Oil pressure OK (> 20 PSI)
    // - No fault conditions

    // Function 0: RPM > 500
    PMU_LogicFunctions_CreateComparison(
        PMU_FUNC_GREATER, 200, 0, 201  // ch200 = ch0 > ch201(500)
    );

    // Function 1: Oil > 20 PSI
    PMU_LogicFunctions_CreateComparison(
        PMU_FUNC_GREATER, 202, 1, 203  // ch202 = ch1 > ch203(20)
    );

    // Function 2: AND all conditions
    PMU_LogicFunction_t and_func = {
        .function_id = 2,
        .type = PMU_FUNC_AND,
        .output_channel = 100,  // Fuel pump output
        .input_channels = {200, 202},
        .input_count = 2,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&and_func);
}
```

### 8.3 PWM from Table

```c
void setup_pwm_table(void) {
    // 1D lookup table for fan speed based on temperature
    static int32_t temp_values[] = {500, 600, 700, 800, 900, 1000};  // 50-100 C
    static int32_t pwm_values[]  = {0, 200, 400, 600, 800, 1000};    // 0-100%

    PMU_LogicFunction_t table_func = {
        .function_id = 0,
        .type = PMU_FUNC_TABLE_1D,
        .output_channel = 100,
        .input_channels = {0},  // Temperature input
        .input_count = 1,
        .enabled = 1,
        .params.table_1d = {
            .size = 6,
            .x_values = temp_values,
            .y_values = pwm_values
        }
    };

    PMU_LogicFunctions_Register(&table_func);
}
```

### 8.4 Moving Average Filter

```c
void setup_filtered_input(void) {
    static int32_t filter_buffer[16];

    PMU_LogicFunction_t filter_func = {
        .function_id = 0,
        .type = PMU_FUNC_MOVING_AVG,
        .output_channel = 200,  // Filtered output
        .input_channels = {0},  // Raw ADC input
        .input_count = 1,
        .enabled = 1,
        .params.moving_avg = {
            .window_size = 16,
            .index = 0,
            .buffer = filter_buffer,
            .sum = 0
        }
    };

    PMU_LogicFunctions_Register(&filter_func);
}
```

---

## See Also

- [Logic Functions Framework](../architecture/logic-functions-framework.md)
- [Logic Functions Integration Guide](../guides/logic-functions-integration.md)
- [Logic Function Examples](../examples/logic-function-examples.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

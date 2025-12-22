# Logic Functions Integration Guide

**Version:** 1.0
**Date:** December 2024

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Integration Overview](#2-integration-overview)
3. [Function Chaining](#3-function-chaining)
4. [State Management](#4-state-management)
5. [Performance Optimization](#5-performance-optimization)
6. [Memory Management](#6-memory-management)
7. [Real-World Examples](#7-real-world-examples)

---

## 1. Introduction

Logic functions process data from input channels and produce results on output channels. This guide explains how to integrate logic functions into your PMU-30 application effectively.

### 1.1 Prerequisites

Before using logic functions:
1. Initialize channel system (`PMU_Channel_Init()`)
2. Register required channels
3. Initialize logic functions (`PMU_LogicFunctions_Init()`)

### 1.2 Execution Flow

```
1 kHz                           500 Hz
+----------------+             +---------------------+
| Channel Update | ---------> | Logic Function Exec |
| - Read ADC     |             | - Read channels     |
| - Update CAN   |             | - Execute functions |
| - System vals  |             | - Write outputs     |
+----------------+             +---------------------+
                                        |
                                        v
                               +-----------------+
                               | Apply to HW     |
                               | - PROFET PWM    |
                               | - H-bridge      |
                               | - CAN TX        |
                               +-----------------+
```

---

## 2. Integration Overview

### 2.1 Basic Setup

```c
#include "pmu_channel.h"
#include "pmu_logic_functions.h"

void setup_logic_system(void) {
    // 1. Initialize subsystems
    PMU_Channel_Init();
    PMU_LogicFunctions_Init();

    // 2. Register channels
    register_input_channels();
    register_output_channels();
    register_virtual_channels();

    // 3. Create logic functions
    create_logic_functions();
}

void main_loop(void) {
    while (1) {
        // Channels updated automatically at 1 kHz by timer interrupt
        // Logic functions executed at 500 Hz by logic task

        // Application logic here...
        HAL_Delay(10);
    }
}
```

### 2.2 Function Registration Pattern

```c
void create_logic_functions(void) {
    // Simple functions using helpers
    PMU_LogicFunctions_CreateMath(PMU_FUNC_ADD, 200, 0, 1);
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_GREATER, 201, 0, 202);
    PMU_LogicFunctions_CreateHysteresis(100, 0, 900, 800);

    // Complex functions using full structure
    PMU_LogicFunction_t complex_func = {
        .function_id = 10,
        .type = PMU_FUNC_AND,
        .output_channel = 205,
        .input_channels = {200, 201, 202, 203},
        .input_count = 4,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&complex_func);
}
```

---

## 3. Function Chaining

### 3.1 Execution Order

Functions execute in ID order (0, 1, 2, ... 63). Use this to chain operations:

```
Function 0 (ID=0): Scale ADC input -> Virtual Channel 200
Function 1 (ID=1): Compare Channel 200 to threshold -> Virtual Channel 201
Function 2 (ID=2): AND Channel 201 with other conditions -> Output 100
```

### 3.2 Chain Example: Sensor to Output

```c
void setup_sensor_chain(void) {
    // Step 1: Scale raw ADC (0-4095) to temperature (0-1000 = 0-100 C)
    PMU_LogicFunction_t scale = {
        .function_id = 0,
        .type = PMU_FUNC_SCALE,
        .output_channel = 200,
        .input_channels = {0},  // Raw ADC
        .input_count = 1,
        .enabled = 1,
        .params.scale = {
            .scale = 244,   // 1000/4095 * 1000
            .offset = 0
        }
    };
    PMU_LogicFunctions_Register(&scale);

    // Step 2: Compare to overheat threshold (85 C)
    PMU_LogicFunctions_CreateComparison(
        PMU_FUNC_GREATER, 201, 200, 850
    );

    // Step 3: Control warning light
    // Output 100 = 1 when temperature > 85 C
    PMU_LogicFunction_t output = {
        .function_id = 2,
        .type = PMU_FUNC_AND,  // Pass through (single input)
        .output_channel = 100,
        .input_channels = {201},
        .input_count = 1,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&output);
}
```

### 3.3 Parallel Chains

```
       +-> [Scale] -> [Compare] -> [AND] -> Output A
Input -+
       +-> [Filter] -> [PID] -------------> Output B
```

```c
void setup_parallel_chains(void) {
    // Chain A: Temperature warning
    PMU_LogicFunctions_CreateMath(PMU_FUNC_SCALE, 200, 0, 0);  // ID=0
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_GREATER, 201, 200, 850);  // ID=1

    // Chain B: Fan PID control
    // ID=2: Moving average filter
    PMU_LogicFunction_t filter = {
        .function_id = 2,
        .type = PMU_FUNC_MOVING_AVG,
        .output_channel = 210,
        .input_channels = {0},
        .input_count = 1,
        .enabled = 1,
        .params.moving_avg.window_size = 8
    };
    PMU_LogicFunctions_Register(&filter);

    // ID=3: PID controller
    PMU_LogicFunctions_CreatePID(101, 210, 750, 2.0f, 0.1f, 0.5f);

    // Chain A continues: ID=4
    PMU_LogicFunction_t warning = {
        .function_id = 4,
        .type = PMU_FUNC_CONDITIONAL,
        .output_channel = 100,
        .input_channels = {201, 202, 203},  // condition, true_val, false_val
        .input_count = 3,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&warning);
}
```

---

## 4. State Management

### 4.1 Stateful Functions

Some functions maintain internal state between executions:

| Function | State | Persistence |
|----------|-------|-------------|
| PID | Integral, last_error | Volatile |
| Moving Average | Sample buffer | Volatile |
| Hysteresis | Current state | Volatile |
| Debounce | Stable state, timer | Volatile |
| Rate Limit | Last value, timestamp | Volatile |

### 4.2 Initializing State

```c
void reset_pid_state(uint16_t function_id) {
    PMU_LogicFunction_t* func = PMU_LogicFunctions_GetByID(function_id);
    if (func && func->type == PMU_FUNC_PID) {
        func->params.pid.integral = 0;
        func->params.pid.last_error = 0;
        func->params.pid.last_update_ms = HAL_GetTick();
    }
}
```

### 4.3 State Across Power Cycles

For non-volatile state, save to flash:

```c
typedef struct {
    uint32_t uptime;
    int32_t counters[8];
    uint8_t states[16];
} PMU_PersistentState_t;

void save_state_to_flash(void) {
    PMU_PersistentState_t state;

    // Copy volatile state to structure
    state.uptime = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_UPTIME);
    // ... other state

    // Write to flash
    PMU_Flash_Write(FLASH_STATE_ADDR, &state, sizeof(state));
}

void restore_state_from_flash(void) {
    PMU_PersistentState_t state;
    PMU_Flash_Read(FLASH_STATE_ADDR, &state, sizeof(state));

    // Apply restored state
    // ...
}
```

---

## 5. Performance Optimization

### 5.1 Function Count

**Guideline:** Use minimum functions necessary

| Functions | CPU Load | Notes |
|-----------|----------|-------|
| 0-16 | < 5% | Minimal impact |
| 17-32 | 5-15% | Normal operation |
| 33-48 | 15-30% | Heavy usage |
| 49-64 | 30-50% | Maximum load |

### 5.2 Optimization Techniques

**1. Combine simple operations:**
```c
// Instead of 3 functions:
// ADD(A, B) -> C
// MULTIPLY(C, 2) -> D
// ADD(D, 100) -> E

// Use single SCALE:
// SCALE(A+B, 2, 100) -> E
```

**2. Use appropriate filter size:**
```c
// Small window = faster response, more noise
// Large window = slower response, smoother
.params.moving_avg.window_size = 8;  // Good balance
```

**3. Avoid Lua for simple operations:**
```c
// Use built-in functions when possible
// Lua is 10-100x slower than native C
```

### 5.3 Profiling

```c
void profile_logic_execution(void) {
    uint32_t start = DWT->CYCCNT;

    PMU_LogicFunctions_Update();

    uint32_t cycles = DWT->CYCCNT - start;
    float us = cycles / (SystemCoreClock / 1000000.0f);

    printf("Logic execution: %.1f us\n", us);
}
```

---

## 6. Memory Management

### 6.1 Static Allocation

All logic function memory is statically allocated:

```c
// In pmu_logic_functions.c
static PMU_LogicFunction_t functions[PMU_MAX_LOGIC_FUNCTIONS];
static int32_t table_data[MAX_TABLE_POINTS];
static int32_t filter_buffers[MAX_FILTER_SIZE * MAX_FILTERS];
```

### 6.2 Table Memory

For lookup tables, allocate data separately:

```c
// Static allocation for 1D table
static int32_t temp_x[16] = {0, 100, 200, ...};
static int32_t temp_y[16] = {0, 50, 150, ...};

PMU_LogicFunction_t table = {
    .type = PMU_FUNC_TABLE_1D,
    .params.table_1d = {
        .size = 16,
        .x_values = temp_x,
        .y_values = temp_y
    }
};
```

### 6.3 Memory Usage

| Component | Size |
|-----------|------|
| Function registry | 64 * 128 = 8 KB |
| Filter buffers | 32 * 64 = 2 KB |
| Table storage | 4 KB typical |
| **Total** | ~14 KB |

---

## 7. Real-World Examples

### 7.1 Complete Fan Control System

```c
/*
 * Fan Control System
 *
 * Inputs:
 *   - Channel 0: Coolant temperature (ADC)
 *   - Channel 1: Oil temperature (ADC)
 *
 * Outputs:
 *   - Channel 100: Fan relay (on/off)
 *   - Channel 101: Fan PWM (variable speed)
 *
 * Logic:
 *   1. Scale temperatures to C
 *   2. Take maximum of both
 *   3. Apply hysteresis for relay
 *   4. Apply lookup table for PWM
 */

static int32_t fan_curve_x[] = {600, 700, 800, 900, 1000};  // 60-100 C
static int32_t fan_curve_y[] = {0, 250, 500, 750, 1000};    // 0-100%

void setup_fan_control(void) {
    // Function 0: Scale coolant temp (ADC to 0.1 C)
    PMU_LogicFunction_t scale_coolant = {
        .function_id = 0,
        .type = PMU_FUNC_SCALE,
        .output_channel = 200,
        .input_channels = {0},
        .input_count = 1,
        .enabled = 1,
        .params.scale = {.scale = 244, .offset = -400}  // -40 to 100 C
    };
    PMU_LogicFunctions_Register(&scale_coolant);

    // Function 1: Scale oil temp
    PMU_LogicFunction_t scale_oil = {
        .function_id = 1,
        .type = PMU_FUNC_SCALE,
        .output_channel = 201,
        .input_channels = {1},
        .input_count = 1,
        .enabled = 1,
        .params.scale = {.scale = 244, .offset = -400}
    };
    PMU_LogicFunctions_Register(&scale_oil);

    // Function 2: Maximum temperature
    PMU_LogicFunction_t max_temp = {
        .function_id = 2,
        .type = PMU_FUNC_MAX,
        .output_channel = 202,
        .input_channels = {200, 201},
        .input_count = 2,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&max_temp);

    // Function 3: Hysteresis for relay (ON > 85 C, OFF < 75 C)
    PMU_LogicFunctions_CreateHysteresis(100, 202, 850, 750);

    // Function 4: PWM from lookup table
    PMU_LogicFunction_t pwm_table = {
        .function_id = 4,
        .type = PMU_FUNC_TABLE_1D,
        .output_channel = 101,
        .input_channels = {202},
        .input_count = 1,
        .enabled = 1,
        .params.table_1d = {
            .size = 5,
            .x_values = fan_curve_x,
            .y_values = fan_curve_y
        }
    };
    PMU_LogicFunctions_Register(&pwm_table);
}
```

### 7.2 Fuel Pump Safety System

```c
/*
 * Fuel Pump Safety
 *
 * Pump runs only when:
 *   - Ignition ON
 *   - Engine running (RPM > 500) OR priming (first 3 seconds)
 *   - No crash detected (inertia switch)
 *   - Oil pressure OK
 */

void setup_fuel_pump_safety(void) {
    // Virtual channels for thresholds
    PMU_Channel_t rpm_threshold = {
        .channel_id = 250,
        .type = PMU_CHANNEL_OUTPUT_NUMBER,
        .value = 500  // 500 RPM
    };
    PMU_Channel_Register(&rpm_threshold);

    // Function 0: RPM > 500
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_GREATER, 260, 200, 250);

    // Function 1: Priming timer (3 seconds after ignition)
    PMU_LogicFunction_t primer = {
        .function_id = 1,
        .type = PMU_FUNC_DEBOUNCE,
        .output_channel = 261,
        .input_channels = {10},  // Ignition input
        .input_count = 1,
        .enabled = 1,
        .params.debounce.debounce_ms = 3000
    };
    PMU_LogicFunctions_Register(&primer);

    // Function 2: Engine running OR priming
    PMU_LogicFunction_t run_or_prime = {
        .function_id = 2,
        .type = PMU_FUNC_OR,
        .output_channel = 262,
        .input_channels = {260, 261},
        .input_count = 2,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&run_or_prime);

    // Function 3: All safety conditions
    PMU_LogicFunction_t safety = {
        .function_id = 3,
        .type = PMU_FUNC_AND,
        .output_channel = 100,  // Fuel pump output
        .input_channels = {
            10,   // Ignition ON
            262,  // Engine running or priming
            11,   // Inertia switch OK
            12    // Oil pressure OK
        },
        .input_count = 4,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&safety);
}
```

### 7.3 Wiper Controller with Intermittent

```c
/*
 * Wiper Controller
 *
 * Inputs:
 *   - Channel 20: Wiper switch (0=OFF, 1=INT, 2=LOW, 3=HIGH)
 *   - Channel 21: Intermittent delay pot (0-1000)
 *
 * Outputs:
 *   - Channel 130: Wiper motor (H-bridge)
 *
 * Features:
 *   - Park position detection
 *   - Variable intermittent delay
 *   - Two speed operation
 */

void setup_wiper_controller(void) {
    // This requires custom state machine in application code
    // Logic functions handle speed selection

    // Function 0: Switch == HIGH (3)
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_EQUAL, 270, 20, 3);

    // Function 1: Switch == LOW (2)
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_EQUAL, 271, 20, 2);

    // Function 2: High speed value (1000)
    // Function 3: Low speed value (600)
    // Function 4: MUX to select speed
    PMU_LogicFunction_t speed_select = {
        .function_id = 4,
        .type = PMU_FUNC_CONDITIONAL,
        .output_channel = 272,
        .input_channels = {270, 273, 274},  // high?, high_speed, low_speed
        .input_count = 3,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&speed_select);

    // Intermittent timer handled in application code
}
```

---

## Next Steps

- [Advanced Channel Configuration](advanced-channel-configuration.md)
- [Custom Logic Function Development](custom-logic-functions.md)
- [Logic Function Examples](../examples/logic-function-examples.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

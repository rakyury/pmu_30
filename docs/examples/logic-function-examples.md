# Logic Function Examples

**Version:** 1.0
**Date:** December 2024

Practical examples for using logic functions in the PMU-30.

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

## 1. Simple Function Execution

### Basic Math: Add Two Channels

```c
// Result = Channel 0 + Channel 1
void example_add(void) {
    uint16_t func_id = PMU_LogicFunctions_CreateMath(
        PMU_FUNC_ADD,
        200,    // Output channel
        0,      // Input A
        1       // Input B
    );

    printf("Created ADD function ID: %d\n", func_id);
}
```

### Scale and Offset

```c
// Convert ADC (0-4095) to Temperature (-40 to 120 C)
// Formula: temp = adc * 0.039 - 40
void example_scale(void) {
    PMU_LogicFunction_t scale = {
        .function_id = 0,
        .type = PMU_FUNC_SCALE,
        .output_channel = 200,
        .input_channels = {0},
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

### Clamp Value to Range

```c
// Clamp throttle to 0-100%
void example_clamp(void) {
    PMU_LogicFunction_t clamp = {
        .function_id = 1,
        .type = PMU_FUNC_CLAMP,
        .output_channel = 201,
        .input_channels = {200},
        .input_count = 1,
        .enabled = 1,
        .params.clamp = {
            .min = 0,
            .max = 1000
        }
    };
    PMU_LogicFunctions_Register(&clamp);
}
```

---

## 2. Function Chaining

### Sensor Processing Pipeline

```c
/*
 * Pipeline: ADC -> Scale -> Filter -> Clamp -> Output
 *
 * Function 0: Scale ADC to engineering units
 * Function 1: Apply moving average filter
 * Function 2: Clamp to valid range
 */
void example_pipeline(void) {
    // Function 0: Scale
    PMU_LogicFunction_t f0 = {
        .function_id = 0,
        .type = PMU_FUNC_SCALE,
        .output_channel = 200,
        .input_channels = {0},
        .input_count = 1,
        .enabled = 1,
        .params.scale = {.scale = 244, .offset = -400}
    };
    PMU_LogicFunctions_Register(&f0);

    // Function 1: Moving average (8 samples)
    static int32_t filter_buffer[8];
    PMU_LogicFunction_t f1 = {
        .function_id = 1,
        .type = PMU_FUNC_MOVING_AVG,
        .output_channel = 201,
        .input_channels = {200},
        .input_count = 1,
        .enabled = 1,
        .params.moving_avg = {
            .window_size = 8,
            .buffer = filter_buffer
        }
    };
    PMU_LogicFunctions_Register(&f1);

    // Function 2: Clamp
    PMU_LogicFunction_t f2 = {
        .function_id = 2,
        .type = PMU_FUNC_CLAMP,
        .output_channel = 202,
        .input_channels = {201},
        .input_count = 1,
        .enabled = 1,
        .params.clamp = {.min = -400, .max = 1200}
    };
    PMU_LogicFunctions_Register(&f2);
}
```

### Multi-Sensor Maximum

```c
// Take maximum of 4 temperature sensors
void example_max_sensors(void) {
    PMU_LogicFunction_t max_func = {
        .function_id = 0,
        .type = PMU_FUNC_MAX,
        .output_channel = 210,
        .input_channels = {0, 1, 2, 3},  // 4 temp sensors
        .input_count = 4,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&max_func);
}
```

---

## 3. Conditional Logic

### Simple Comparison

```c
// Output = 1 if temperature > 85 C
void example_compare(void) {
    // First create threshold constant channel
    PMU_Channel_t threshold = {
        .channel_id = 250,
        .type = PMU_CHANNEL_OUTPUT_NUMBER,
        .value = 850  // 85.0 C
    };
    PMU_Channel_Register(&threshold);

    // Then create comparison
    PMU_LogicFunctions_CreateComparison(
        PMU_FUNC_GREATER,
        201,    // Output
        200,    // Temperature channel
        250     // Threshold channel
    );
}
```

### AND Gate: Multiple Conditions

```c
// Fuel pump ON if: ignition AND (running OR priming) AND safety
void example_and_gate(void) {
    PMU_LogicFunction_t and_func = {
        .function_id = 10,
        .type = PMU_FUNC_AND,
        .output_channel = 100,  // Fuel pump
        .input_channels = {
            20,   // Ignition switch
            201,  // Engine running OR priming
            22,   // Safety switch OK
            23    // Oil pressure OK
        },
        .input_count = 4,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&and_func);
}
```

### OR Gate: Any Condition

```c
// Warning light if: overheat OR low oil OR low fuel
void example_or_gate(void) {
    PMU_LogicFunction_t or_func = {
        .function_id = 11,
        .type = PMU_FUNC_OR,
        .output_channel = 101,  // Warning light
        .input_channels = {
            210,  // Overheat flag
            211,  // Low oil flag
            212   // Low fuel flag
        },
        .input_count = 3,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&or_func);
}
```

### Ternary/Conditional

```c
// Speed = (gear == reverse) ? -speed : speed
void example_conditional(void) {
    PMU_LogicFunction_t cond = {
        .function_id = 12,
        .type = PMU_FUNC_CONDITIONAL,
        .output_channel = 220,
        .input_channels = {
            215,  // Condition: reverse gear active
            216,  // True value: negative speed
            217   // False value: positive speed
        },
        .input_count = 3,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&cond);
}
```

### In-Range Check

```c
// Valid = 1 if 500 <= RPM <= 7000
void example_in_range(void) {
    PMU_LogicFunction_t range = {
        .function_id = 13,
        .type = PMU_FUNC_IN_RANGE,
        .output_channel = 225,
        .input_channels = {
            200,  // RPM value
            251,  // Min (500)
            252   // Max (7000)
        },
        .input_count = 3,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&range);
}
```

---

## 4. Loop and Timer Patterns

### Hysteresis (On/Off with Dead Band)

```c
// Fan: ON above 85 C, OFF below 75 C
void example_hysteresis(void) {
    PMU_LogicFunctions_CreateHysteresis(
        100,    // Fan output
        200,    // Temperature input
        850,    // ON threshold (85 C)
        750     // OFF threshold (75 C)
    );
}
```

### Debounce Filter

```c
// Debounce switch for 50ms
void example_debounce(void) {
    PMU_LogicFunction_t debounce = {
        .function_id = 20,
        .type = PMU_FUNC_DEBOUNCE,
        .output_channel = 230,
        .input_channels = {20},
        .input_count = 1,
        .enabled = 1,
        .params.debounce = {
            .debounce_ms = 50
        }
    };
    PMU_LogicFunctions_Register(&debounce);
}
```

### Rate Limiter

```c
// Limit throttle change rate to 500/second
void example_rate_limit(void) {
    PMU_LogicFunction_t rate = {
        .function_id = 21,
        .type = PMU_FUNC_RATE_LIMIT,
        .output_channel = 231,
        .input_channels = {200},
        .input_count = 1,
        .enabled = 1,
        .params.rate_limit = {
            .max_rate = 500  // units per second
        }
    };
    PMU_LogicFunctions_Register(&rate);
}
```

---

## 5. Filter Applications

### Moving Average (Noise Reduction)

```c
static int32_t avg_buffer[16];

void example_moving_avg(void) {
    PMU_LogicFunction_t avg = {
        .function_id = 30,
        .type = PMU_FUNC_MOVING_AVG,
        .output_channel = 240,
        .input_channels = {0},
        .input_count = 1,
        .enabled = 1,
        .params.moving_avg = {
            .window_size = 16,
            .buffer = avg_buffer
        }
    };
    PMU_LogicFunctions_Register(&avg);
}
```

### Low-Pass Filter (RC)

```c
void example_lowpass(void) {
    PMU_LogicFunction_t lpf = {
        .function_id = 31,
        .type = PMU_FUNC_LOW_PASS,
        .output_channel = 241,
        .input_channels = {0},
        .input_count = 1,
        .enabled = 1,
        // Time constant set via params
    };
    PMU_LogicFunctions_Register(&lpf);
}
```

### Peak Hold (Max Window)

```c
static int32_t max_buffer[32];

void example_peak_hold(void) {
    PMU_LogicFunction_t peak = {
        .function_id = 32,
        .type = PMU_FUNC_MAX_WINDOW,
        .output_channel = 242,
        .input_channels = {0},
        .input_count = 1,
        .enabled = 1,
        .params.moving_avg = {  // Same structure
            .window_size = 32,
            .buffer = max_buffer
        }
    };
    PMU_LogicFunctions_Register(&peak);
}
```

---

## 6. Control Systems

### PID Controller

```c
// Temperature control with PID
void example_pid(void) {
    uint16_t pid_id = PMU_LogicFunctions_CreatePID(
        100,        // Heater PWM output
        200,        // Temperature input
        750.0f,     // Setpoint: 75.0 C
        2.0f,       // Kp
        0.1f,       // Ki
        0.5f        // Kd
    );

    // Set output limits after creation
    PMU_LogicFunction_t* pid = PMU_LogicFunctions_GetByID(pid_id);
    if (pid) {
        pid->params.pid.output_min = 0;
        pid->params.pid.output_max = 1000;
    }
}
```

### Lookup Table Control

```c
// Fan speed from temperature lookup table
static int32_t temp_points[] = {500, 600, 700, 800, 900, 1000};
static int32_t speed_points[] = {0, 100, 300, 600, 850, 1000};

void example_lookup(void) {
    PMU_LogicFunction_t table = {
        .function_id = 40,
        .type = PMU_FUNC_TABLE_1D,
        .output_channel = 100,  // Fan PWM
        .input_channels = {200},  // Temperature
        .input_count = 1,
        .enabled = 1,
        .params.table_1d = {
            .size = 6,
            .x_values = temp_points,
            .y_values = speed_points
        }
    };
    PMU_LogicFunctions_Register(&table);
}
```

### Closed-Loop Idle Control

```c
/*
 * Idle RPM Control:
 * - Target: 800 RPM
 * - Actuator: Idle air valve (PWM)
 * - Feedback: RPM from CAN
 */
void example_idle_control(void) {
    // Constant for target RPM
    PMU_Channel_t target = {
        .channel_id = 260,
        .type = PMU_CHANNEL_OUTPUT_NUMBER,
        .value = 800
    };
    PMU_Channel_Register(&target);

    // Error = Target - Actual
    PMU_LogicFunction_t error = {
        .function_id = 50,
        .type = PMU_FUNC_SUBTRACT,
        .output_channel = 261,
        .input_channels = {260, 200},  // target - actual
        .input_count = 2,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&error);

    // PID on error
    PMU_LogicFunctions_CreatePID(
        101,        // IAC valve output
        200,        // RPM input
        800.0f,     // Target RPM
        0.5f,       // Kp (gentle)
        0.02f,      // Ki
        0.1f        // Kd
    );
}
```

---

## 7. Error Handling

### Safe Function Creation

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

### Function Status Check

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
    printf("  Inputs: ");
    for (int i = 0; i < func->input_count; i++) {
        printf("%d ", func->input_channels[i]);
    }
    printf("\n");

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

```c
// BAD: 4 separate functions
void bad_example(void) {
    PMU_LogicFunctions_CreateMath(PMU_FUNC_ADD, 200, 0, 1);
    PMU_LogicFunctions_CreateMath(PMU_FUNC_ADD, 201, 200, 2);
    PMU_LogicFunctions_CreateMath(PMU_FUNC_ADD, 202, 201, 3);
    PMU_LogicFunctions_CreateMath(PMU_FUNC_DIVIDE, 203, 202, 254);  // /4
}

// GOOD: Single average function
void good_example(void) {
    PMU_LogicFunction_t avg = {
        .function_id = 0,
        .type = PMU_FUNC_AVERAGE,
        .output_channel = 200,
        .input_channels = {0, 1, 2, 3},
        .input_count = 4,
        .enabled = 1
    };
    PMU_LogicFunctions_Register(&avg);
}
```

### Appropriate Filter Size

```c
// Small filter = fast response, more noise
// Large filter = slow response, less noise

// For fast-changing signals (throttle):
.params.moving_avg.window_size = 4;

// For slow-changing signals (temperature):
.params.moving_avg.window_size = 32;
```

### Disable Unused Functions

```c
void optimization_example(void) {
    // Disable functions when not needed
    if (engine_off) {
        PMU_LogicFunctions_SetEnabled(10, false);  // Disable idle control
        PMU_LogicFunctions_SetEnabled(11, false);  // Disable fuel calc
    } else {
        PMU_LogicFunctions_SetEnabled(10, true);
        PMU_LogicFunctions_SetEnabled(11, true);
    }
}
```

---

## See Also

- [Logic Functions API Reference](../api/logic-functions-reference.md)
- [Channel Examples](channel-examples.md)
- [Real-World Scenarios](real-world-scenarios.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

# Channel Operations Functions

**Category:** Multi-Channel Operations
**Function IDs:** 0xD0-0xDF

---

## Overview

Channel operations functions work with multiple channels simultaneously for aggregation, monitoring, and coordination.

---

## Functions

### 1. CHANNEL_SUM (0xD0)

Sums multiple channel values.

```c
{
    "type": "channel_sum",
    "inputs": [100, 101, 102, 103],   // Up to 8 channels
    "output": 210
}
// Output = sum of all input channel values
```

**Use Case:** Total current calculation.

---

### 2. CHANNEL_MIN (0xD1)

Returns minimum of multiple channels.

```c
{
    "type": "channel_min",
    "inputs": [0, 1, 2, 3],
    "output": 200
}
// Output = lowest value among inputs
```

**Use Case:** Lowest temperature sensor.

---

### 3. CHANNEL_MAX (0xD2)

Returns maximum of multiple channels.

```c
{
    "type": "channel_max",
    "inputs": [0, 1, 2, 3],
    "output": 200
}
// Output = highest value among inputs
```

**Use Case:** Hottest temperature sensor.

---

### 4. CHANNEL_AVG (0xD3)

Returns average of multiple channels.

```c
{
    "type": "channel_avg",
    "inputs": [0, 1, 2, 3],
    "output": 200
}
// Output = average of all input values
```

---

### 5. CHANNEL_DIFF (0xD4)

Returns difference between two channels.

```c
{
    "type": "channel_diff",
    "inputs": [200, 201],
    "output": 210,
    "parameters": {
        "absolute": true    // Return absolute difference
    }
}
// Output = |Input[0] - Input[1]|
```

**Use Case:** Differential sensor, imbalance detection.

---

### 6. REDUNDANCY_CHECK (0xD5)

Validates redundant sensors.

```c
{
    "type": "redundancy_check",
    "inputs": [0, 1],           // Two redundant sensors
    "output": 200,              // Validated value
    "parameters": {
        "max_deviation": 100,   // Max allowed difference
        "fault_channel": 210    // Fault indicator output
    }
}
// If |Input[0] - Input[1]| > max_deviation: Fault = 1
// Otherwise: Output = average of inputs
```

**Use Case:** Dual TPS validation.

---

### 7. SENSOR_SELECT (0xD6)

Selects best sensor from group.

```c
{
    "type": "sensor_select",
    "inputs": [0, 1, 2],
    "output": 200,
    "parameters": {
        "mode": "median",       // or "average_exclude_outlier"
        "outlier_threshold": 200
    }
}
```

---

### 8. CHANNEL_SYNC (0xD7)

Synchronizes multiple outputs.

```c
{
    "type": "channel_sync",
    "input": 200,               // Source value
    "outputs": [100, 101, 102], // Multiple outputs
    "parameters": {
        "delay_ms": [0, 10, 20] // Staggered timing
    }
}
// All outputs receive same value with optional delay
```

**Use Case:** Staggered relay activation.

---

### 9. GANG_CONTROL (0xD8)

Controls multiple outputs as group.

```c
{
    "type": "gang_control",
    "input": 210,               // Enable
    "outputs": [100, 101, 102],
    "parameters": {
        "values": [1000, 800, 600],  // PWM values when enabled
        "master": 100           // Master channel for feedback
    }
}
```

**Use Case:** Multi-stage cooling fans.

---

### 10. LOAD_BALANCE (0xD9)

Distributes load across outputs.

```c
{
    "type": "load_balance",
    "input": 200,               // Total requested current
    "outputs": [100, 101, 102, 103],
    "parameters": {
        "max_per_channel": 300, // 30A each
        "mode": "round_robin"   // or "sequential", "proportional"
    }
}
// Distributes load evenly across available outputs
```

---

### 11. FAULT_AGGREGATE (0xDA)

Combines fault status from multiple channels.

```c
{
    "type": "fault_aggregate",
    "inputs": [100, 101, 102],  // Channels to monitor
    "output": 210,
    "parameters": {
        "mode": "any",          // or "all", "count"
        "threshold": 1          // For count mode
    }
}
// Output = 1 if any input channel has fault
```

---

### 12. CURRENT_LIMIT_MANAGER (0xDB)

Manages total current budget.

```c
{
    "type": "current_limit_manager",
    "inputs": [100, 101, 102, 103],  // Output channels
    "output": 210,                    // Budget remaining
    "parameters": {
        "total_budget_a": 150,
        "priority": [1, 2, 3, 4],    // Shedding priority
        "action": "derate"           // or "shed"
    }
}
// Automatically derates or sheds low-priority loads when over budget
```

---

## Implementation

```c
int32_t execute_channel_sum(PMU_LogicFunction_t* func, int32_t* inputs) {
    int32_t sum = 0;
    for (int i = 0; i < func->input_count; i++) {
        sum += inputs[i];
    }
    return sum;
}

int32_t execute_redundancy_check(PMU_LogicFunction_t* func, int32_t* inputs) {
    int32_t diff = inputs[0] - inputs[1];
    if (diff < 0) diff = -diff;

    if (diff > func->params.max_deviation) {
        // Set fault indicator
        PMU_Channel_SetValue(func->params.fault_channel, 1);
        // Return average anyway (degraded mode)
        return (inputs[0] + inputs[1]) / 2;
    }

    PMU_Channel_SetValue(func->params.fault_channel, 0);
    return (inputs[0] + inputs[1]) / 2;
}

void execute_channel_sync(PMU_LogicFunction_t* func, int32_t input) {
    for (int i = 0; i < func->output_count; i++) {
        // Apply with staggered delay if configured
        if (func->params.delays[i] == 0) {
            PMU_Channel_SetValue(func->outputs[i], input);
        } else {
            // Queue delayed write
            schedule_delayed_write(func->outputs[i], input,
                                   func->params.delays[i]);
        }
    }
}
```

---

## Practical Examples

### Total Current Monitoring

```c
{
    "functions": [
        // Sum currents from all 30 outputs
        {"id": 0, "type": "channel_sum",
         "inputs": [140, 141, 142, 143, 144, 145, 146, 147],  // Currents 1-8
         "output": 210
        },
        // ... more sums for channels 9-30 ...
        {"id": 4, "type": "channel_sum",
         "inputs": [210, 211, 212, 213],  // Partial sums
         "output": 1001                    // Total current
        }
    ]
}
```

### Dual TPS Validation

```c
{
    "functions": [
        {"id": 0, "type": "redundancy_check",
         "inputs": [4, 5],          // TPS1, TPS2
         "output": 200,             // Validated TPS
         "parameters": {
             "max_deviation": 100,  // 10% tolerance
             "fault_channel": 210
         }
        },
        // Use fault for limp mode
        {"id": 1, "type": "if_then_else",
         "inputs": [210, 500, 200], // Fault, LimpValue, ValidValue
         "output": 201
        }
    ]
}
```

### Staggered Relay Startup

```c
{
    "type": "channel_sync",
    "input": 210,                   // Master enable
    "outputs": [100, 101, 102, 103, 104],
    "parameters": {
        "delay_ms": [0, 50, 100, 150, 200]  // 50ms between each
    }
}
// Prevents inrush current spike from simultaneous relay activation
```

---

## See Also

- [I/O Functions](io-functions.md)
- [State Management Functions](state-management-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

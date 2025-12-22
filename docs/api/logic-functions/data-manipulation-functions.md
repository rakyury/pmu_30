# Data Manipulation Functions

**Category:** Lookup Tables and Signal Processing
**Function IDs:** 0x60-0x7F

---

## 1. Lookup Table Functions (0x60-0x6F)

### TABLE_1D (0x60)

1-dimensional lookup table with interpolation.

```c
{
    "type": "table_1d",
    "input": 0,             // Input channel (X axis)
    "output": 200,
    "parameters": {
        "x_values": [0, 250, 500, 750, 1000],
        "y_values": [0, 100, 400, 800, 1000],
        "interpolation": "linear"   // or "step"
    }
}
```

**Use Case:** Temperature to fan speed mapping.

---

### TABLE_2D (0x61)

2-dimensional lookup table.

```c
{
    "type": "table_2d",
    "inputs": [200, 201],   // X and Y axes
    "output": 210,
    "parameters": {
        "x_axis": [0, 2000, 4000, 6000, 8000],      // RPM
        "y_axis": [0, 250, 500, 750, 1000],         // Load
        "values": [
            [0,   0,   0,   0,   0],
            [100, 150, 200, 250, 300],
            [200, 300, 400, 500, 600],
            [300, 450, 600, 750, 900],
            [400, 600, 800, 1000, 1000]
        ],
        "interpolation": "bilinear"
    }
}
```

**Use Case:** Boost control map based on RPM and throttle.

---

### CURVE_FIT (0x62)

Polynomial curve fitting.

```c
{
    "type": "curve_fit",
    "input": 0,
    "output": 200,
    "parameters": {
        "coefficients": [100, 0.5, -0.001],  // a + bx + cx²
        "order": 2
    }
}
// Output = 100 + 0.5*x - 0.001*x²
```

**Use Case:** NTC temperature linearization.

---

## 2. Filter Functions (0x70-0x7F)

### MOVING_AVERAGE (0x80)

Moving average filter.

```c
{
    "type": "moving_avg",
    "input": 0,
    "output": 200,
    "parameters": {
        "window_size": 8
    }
}
```

---

### EXPONENTIAL_FILTER (0x81)

Exponential moving average (EMA).

```c
{
    "type": "exp_filter",
    "input": 0,
    "output": 200,
    "parameters": {
        "alpha": 100        // 0-1000 (100 = 0.1)
    }
}
// Output = alpha * Input + (1-alpha) * PreviousOutput
```

---

### RATE_LIMIT (0x82)

Limits rate of change.

```c
{
    "type": "rate_limit",
    "input": 200,
    "output": 100,
    "parameters": {
        "max_rate_up": 100,     // Max increase per cycle
        "max_rate_down": 50     // Max decrease per cycle
    }
}
```

**Use Case:** Soft ramp for motors.

---

### DEADBAND_FILTER (0x83)

Filters noise within deadband.

```c
{
    "type": "deadband_filter",
    "input": 200,
    "output": 201,
    "parameters": {
        "deadband": 10
    }
}
// Output only changes if input changes by more than deadband
```

---

### MEDIAN_FILTER (0x84)

Median of last N samples.

```c
{
    "type": "median_filter",
    "input": 0,
    "output": 200,
    "parameters": {
        "window_size": 5
    }
}
```

**Use Case:** Spike removal from noisy sensors.

---

### HYSTERESIS_FILTER (0x85)

Prevents oscillation at thresholds.

```c
{
    "type": "hysteresis",
    "input": 0,
    "output": 100,
    "parameters": {
        "threshold_on": 850,
        "threshold_off": 800
    }
}
// Turns ON at 85°C, OFF at 80°C
```

---

### DERIVATIVE (0x86)

Rate of change (dV/dt).

```c
{
    "type": "derivative",
    "input": 200,
    "output": 201,
    "parameters": {
        "sample_time_ms": 2     // 500Hz
    }
}
// Output = (current - previous) / sample_time
```

---

### INTEGRAL (0x87)

Accumulated sum over time.

```c
{
    "type": "integral",
    "input": 200,
    "output": 201,
    "parameters": {
        "sample_time_ms": 2,
        "min": -10000,
        "max": 10000,
        "reset_channel": 210    // Optional: reset trigger
    }
}
```

---

## Implementation

```c
// Moving average state
typedef struct {
    int32_t buffer[32];
    uint8_t index;
    int32_t sum;
} MovingAvgState_t;

int32_t execute_moving_avg(PMU_LogicFunction_t* func, int32_t input) {
    MovingAvgState_t* state = &func->state.moving_avg;
    uint8_t size = func->params.window_size;

    // Remove oldest value
    state->sum -= state->buffer[state->index];

    // Add new value
    state->buffer[state->index] = input;
    state->sum += input;

    // Advance index
    state->index = (state->index + 1) % size;

    return state->sum / size;
}

// Lookup table with interpolation
int32_t execute_table_1d(PMU_LogicFunction_t* func, int32_t input) {
    int32_t* x = func->params.x_values;
    int32_t* y = func->params.y_values;
    uint8_t count = func->params.table_size;

    // Clamp to range
    if (input <= x[0]) return y[0];
    if (input >= x[count-1]) return y[count-1];

    // Find segment
    for (int i = 0; i < count - 1; i++) {
        if (input >= x[i] && input < x[i+1]) {
            // Linear interpolation
            int32_t dx = x[i+1] - x[i];
            int32_t dy = y[i+1] - y[i];
            return y[i] + (input - x[i]) * dy / dx;
        }
    }

    return y[count-1];
}
```

---

## Practical Examples

### Temperature-Compensated Sensor

```c
// NTC lookup table
{
    "type": "table_1d",
    "input": 0,
    "parameters": {
        "x_values": [100, 300, 600, 1000, 1500, 2000, 2500, 3000, 3500, 4000],
        "y_values": [1500, 1200, 1000, 800, 600, 450, 300, 200, 100, -100],
        "interpolation": "linear"
    }
}
// Maps ADC value to temperature in 0.1°C
```

### Smoothed Throttle

```c
// Smooth throttle position
{
    "functions": [
        {"type": "moving_avg", "input": 4, "output": 200, "parameters": {"window_size": 4}},
        {"type": "rate_limit", "input": 200, "output": 201, "parameters": {"max_rate_up": 50, "max_rate_down": 100}}
    ]
}
```

---

## See Also

- [Arithmetic Functions](arithmetic-functions.md)
- [Control Functions](control-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

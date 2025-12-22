# Control Functions

**Category:** Advanced Control Systems
**Function IDs:** 0xA0-0xBF

---

## Overview

Control functions implement advanced control algorithms including PID, PWM generation, and specialized motor control.

---

## 1. PID Controller (0xA0)

Full PID controller with anti-windup.

```c
{
    "type": "pid",
    "inputs": [200, 201],       // Process Variable, Setpoint
    "output": 100,
    "parameters": {
        "kp": 100,              // Proportional gain (x100)
        "ki": 50,               // Integral gain (x100)
        "kd": 10,               // Derivative gain (x100)
        "output_min": 0,
        "output_max": 1000,
        "sample_time_ms": 10,
        "deadband": 5,
        "anti_windup": true
    }
}
```

### PID Tuning Guide

| Application | Kp | Ki | Kd |
|-------------|----|----|-----|
| Temperature | 50-100 | 10-30 | 5-20 |
| Pressure | 100-200 | 30-50 | 10-30 |
| Speed | 80-150 | 20-40 | 10-25 |
| Position | 150-300 | 50-100 | 20-50 |

---

## 2. PI Controller (0xA1)

Simplified PI controller.

```c
{
    "type": "pi",
    "inputs": [200, 201],
    "output": 100,
    "parameters": {
        "kp": 100,
        "ki": 50,
        "output_min": 0,
        "output_max": 1000
    }
}
```

---

## 3. P Controller (0xA2)

Proportional-only controller.

```c
{
    "type": "p_only",
    "inputs": [200, 201],
    "output": 100,
    "parameters": {
        "kp": 100,
        "bias": 500             // Output when error = 0
    }
}
// Output = bias + kp * error
```

---

## 4. Bang-Bang Controller (0xA3)

On-off control with hysteresis.

```c
{
    "type": "bang_bang",
    "inputs": [200, 201],       // PV, Setpoint
    "output": 100,
    "parameters": {
        "hysteresis": 20,       // +/- 20 around setpoint
        "invert": false
    }
}
// ON when PV < Setpoint - hysteresis
// OFF when PV > Setpoint + hysteresis
```

---

## 5. PWM Duty Controller (0xA4)

Maps input to PWM duty cycle.

```c
{
    "type": "pwm_duty",
    "input": 200,
    "output": 100,
    "parameters": {
        "input_min": 600,       // Start at 60°C
        "input_max": 1000,      // Full at 100°C
        "duty_min": 0,
        "duty_max": 1000,
        "curve": "linear"       // or "exponential", "scurve"
    }
}
```

---

## 6. Soft Start/Stop (0xA5)

Ramped output control.

```c
{
    "type": "soft_start",
    "input": 210,               // Target value
    "output": 100,
    "parameters": {
        "ramp_up_ms": 1000,
        "ramp_down_ms": 500,
        "start_delay_ms": 0
    }
}
```

---

## 7. Current Limiter (0xA6)

Limits output based on current feedback.

```c
{
    "type": "current_limiter",
    "inputs": [200, 140],       // Requested duty, Current feedback
    "output": 100,
    "parameters": {
        "current_limit_ma": 15000,
        "kp": 50                // Proportional gain for limiting
    }
}
// Reduces duty when current exceeds limit
```

---

## 8. H-Bridge Controller (0xA7)

Bidirectional motor control.

```c
{
    "type": "hbridge_control",
    "inputs": [200, 201],       // Speed command, Direction
    "output": 130,
    "parameters": {
        "deadband": 50,
        "acceleration": 100,    // Max change per cycle
        "brake_threshold": 20
    }
}
// Output: -1000 to +1000 for H-bridge
```

---

## 9. Wiper Controller (0xA8)

Specialized wiper motor control.

```c
{
    "type": "wiper",
    "inputs": [20, 21, 26],     // Off/Int/Lo/Hi, Park switch, Wash
    "output": 130,
    "parameters": {
        "park_position": 0,
        "intermittent_ms": 5000,
        "wash_wipes": 3,
        "wash_delay_ms": 500
    }
}
```

### Wiper States

| Mode | Behavior |
|------|----------|
| OFF | Return to park |
| INT | Wipe every N seconds |
| LOW | Continuous slow |
| HIGH | Continuous fast |
| WASH | Spray + wipe + delay wipes |

---

## 10. Cruise Control (0xA9)

Speed control with throttle output.

```c
{
    "type": "cruise_control",
    "inputs": [200, 201, 20, 21, 22],  // Speed, Target, Enable, Set, Resume
    "output": 210,
    "parameters": {
        "kp": 80,
        "ki": 20,
        "max_output": 800,      // Max throttle
        "coast_threshold": 50
    }
}
```

---

## 11. Boost Controller (0xAA)

Turbo boost pressure control.

```c
{
    "type": "boost_control",
    "inputs": [200, 201, 202],  // MAP, Target, TPS
    "output": 100,              // Wastegate solenoid
    "parameters": {
        "kp": 100,
        "ki": 30,
        "tps_compensation": true,
        "gear_compensation": [100, 95, 90, 85, 80, 75]
    }
}
```

---

## 12. Lambda Controller (0xAB)

Air-fuel ratio control.

```c
{
    "type": "lambda_control",
    "inputs": [200, 201],       // Lambda, Target
    "output": 100,              // Fuel trim output
    "parameters": {
        "kp": 50,
        "ki": 20,
        "lean_limit": 800,      // 0.8 lambda
        "rich_limit": 1200      // 1.2 lambda
    }
}
```

---

## Implementation

```c
typedef struct {
    int32_t integral;
    int32_t prev_error;
    int32_t prev_output;
    uint32_t last_time;
} PIDState_t;

int32_t execute_pid(PMU_LogicFunction_t* func, int32_t* inputs) {
    PIDState_t* state = &func->state.pid;
    int32_t pv = inputs[0];
    int32_t setpoint = inputs[1];

    // Calculate error
    int32_t error = setpoint - pv;

    // Deadband
    if (abs(error) < func->params.deadband) {
        error = 0;
    }

    // Proportional
    int32_t p_term = (func->params.kp * error) / 100;

    // Integral with anti-windup
    state->integral += error;
    if (func->params.anti_windup) {
        int32_t max_integral = func->params.output_max * 100 / func->params.ki;
        if (state->integral > max_integral) state->integral = max_integral;
        if (state->integral < -max_integral) state->integral = -max_integral;
    }
    int32_t i_term = (func->params.ki * state->integral) / 100;

    // Derivative
    int32_t d_term = (func->params.kd * (error - state->prev_error)) / 100;
    state->prev_error = error;

    // Sum and clamp
    int32_t output = p_term + i_term + d_term;
    if (output > func->params.output_max) output = func->params.output_max;
    if (output < func->params.output_min) output = func->params.output_min;

    return output;
}

int32_t execute_soft_start(PMU_LogicFunction_t* func, int32_t* inputs) {
    int32_t target = inputs[0];
    int32_t* current = &func->state.current_value;

    if (target > *current) {
        // Ramping up
        int32_t step = func->params.output_max * 2 / func->params.ramp_up_ms;
        *current += step;
        if (*current > target) *current = target;
    } else if (target < *current) {
        // Ramping down
        int32_t step = func->params.output_max * 2 / func->params.ramp_down_ms;
        *current -= step;
        if (*current < target) *current = target;
    }

    return *current;
}
```

---

## Practical Examples

### PID-Controlled Cooling Fan

```c
{
    "type": "pid",
    "inputs": [0, 850],         // Coolant temp, Target 85°C
    "output": 100,
    "parameters": {
        "kp": 80,
        "ki": 20,
        "kd": 10,
        "output_min": 0,
        "output_max": 1000,
        "anti_windup": true
    }
}
```

### Soft-Start Motor

```c
{
    "functions": [
        // Enable signal
        {"id": 0, "type": "is_true", "input": 20, "output": 210},
        // Target duty when enabled
        {"id": 1, "type": "if_then_else", "inputs": [210, 1000, 0], "output": 211},
        // Soft start/stop
        {"id": 2, "type": "soft_start", "input": 211, "output": 100,
         "parameters": {"ramp_up_ms": 2000, "ramp_down_ms": 500}}
    ]
}
```

### Current-Limited Output

```c
{
    "functions": [
        // Desired duty from logic
        {"id": 0, "type": "channel_copy", "input": 200, "output": 210},
        // Limit based on current
        {"id": 1, "type": "current_limiter",
         "inputs": [210, 140],      // Desired, Actual current
         "output": 100,
         "parameters": {"current_limit_ma": 12000, "kp": 50}}
    ]
}
```

---

## See Also

- [Data Manipulation Functions](data-manipulation-functions.md)
- [State Management Functions](state-management-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

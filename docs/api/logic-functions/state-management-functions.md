# State Management Functions

**Category:** Stateful Logic and Memory
**Function IDs:** 0xC0-0xCF

---

## Overview

State management functions maintain internal state between execution cycles.

---

## Functions

### 1. LATCH_SR (0xC0)

Set-Reset latch (flip-flop).

```c
{
    "type": "latch_sr",
    "inputs": [210, 211],   // Set, Reset
    "output": 220,
    "parameters": {
        "initial_state": 0,
        "priority": "reset"     // or "set"
    }
}
// Set pulse -> Output = 1 (stays)
// Reset pulse -> Output = 0 (stays)
```

**Use Case:** Fault latch, toggle state.

---

### 2. TOGGLE (0xC1)

Toggles output on rising edge.

```c
{
    "type": "toggle",
    "input": 20,            // Button input
    "output": 100,
    "parameters": {
        "initial_state": 0
    }
}
// Each button press toggles output ON/OFF
```

---

### 3. PULSE (0xC2)

Generates fixed-length pulse on trigger.

```c
{
    "type": "pulse",
    "input": 210,           // Trigger
    "output": 100,
    "parameters": {
        "duration_ms": 500,
        "retrigger": false
    }
}
// Rising edge on input -> Output HIGH for 500ms
```

---

### 4. DELAY_ON (0xC3)

Delays turn-on by specified time.

```c
{
    "type": "delay_on",
    "input": 210,
    "output": 100,
    "parameters": {
        "delay_ms": 2000
    }
}
// Input must be HIGH for 2 seconds before output goes HIGH
// Output goes LOW immediately when input goes LOW
```

**Use Case:** Anti-bounce, delayed enable.

---

### 5. DELAY_OFF (0xC4)

Delays turn-off by specified time.

```c
{
    "type": "delay_off",
    "input": 210,
    "output": 100,
    "parameters": {
        "delay_ms": 5000
    }
}
// Output goes HIGH immediately when input goes HIGH
// Output stays HIGH for 5 seconds after input goes LOW
```

**Use Case:** Fan run-on after engine off.

---

### 6. FLASHER (0xC5)

Generates periodic on/off signal.

```c
{
    "type": "flasher",
    "input": 210,           // Enable
    "output": 100,
    "parameters": {
        "on_time_ms": 500,
        "off_time_ms": 500
    }
}
// When enabled: 500ms ON, 500ms OFF, repeat
```

**Use Case:** Turn signals, warning lights.

---

### 7. COUNTER (0xC6)

Counts pulses or edges.

```c
{
    "type": "counter",
    "inputs": [210, 211],   // Count, Reset
    "output": 220,
    "parameters": {
        "edge": "rising",   // or "falling", "both"
        "max": 1000,
        "wrap": true
    }
}
```

---

### 8. TIMER (0xC7)

Elapsed time counter.

```c
{
    "type": "timer",
    "inputs": [210, 211],   // Run, Reset
    "output": 220,          // Elapsed time in ms
    "parameters": {
        "max_ms": 3600000   // 1 hour max
    }
}
```

---

### 9. STATE_MACHINE (0xC8)

Programmable state machine.

```c
{
    "type": "state_machine",
    "inputs": [210, 211, 212],  // Event inputs
    "output": 220,              // Current state
    "parameters": {
        "initial_state": 0,
        "transitions": [
            {"from": 0, "event": 0, "to": 1},
            {"from": 1, "event": 1, "to": 2},
            {"from": 2, "event": 2, "to": 0}
        ]
    }
}
```

---

### 10. MEMORY (0xC9)

Sample and hold.

```c
{
    "type": "memory",
    "inputs": [200, 210],   // Value, Trigger
    "output": 220,
    "parameters": {
        "mode": "rising_edge"   // or "high", "falling_edge"
    }
}
// Captures input value on trigger
```

---

### 11. PEAK_HOLD (0xCA)

Holds maximum value.

```c
{
    "type": "peak_hold",
    "inputs": [200, 210],   // Value, Reset
    "output": 220,
    "parameters": {
        "decay_rate": 0     // 0 = hold forever, >0 = decay per second
    }
}
```

**Use Case:** Max RPM, max speed recording.

---

### 12. MIN_HOLD (0xCB)

Holds minimum value.

```c
{
    "type": "min_hold",
    "inputs": [200, 210],   // Value, Reset
    "output": 220
}
```

**Use Case:** Minimum oil pressure recording.

---

## Implementation

```c
typedef struct {
    uint8_t state;
    uint32_t timer;
    int32_t held_value;
} StateMemory_t;

int32_t execute_toggle(PMU_LogicFunction_t* func, int32_t* inputs) {
    StateMemory_t* mem = &func->state.memory;
    static int32_t prev_input = 0;

    // Rising edge detection
    if (inputs[0] != 0 && prev_input == 0) {
        mem->state = !mem->state;
    }
    prev_input = inputs[0];

    return mem->state;
}

int32_t execute_flasher(PMU_LogicFunction_t* func, int32_t* inputs) {
    StateMemory_t* mem = &func->state.memory;

    if (inputs[0] == 0) {
        mem->timer = 0;
        return 0;
    }

    uint32_t period = func->params.on_time + func->params.off_time;
    mem->timer = (mem->timer + 2) % period;  // 500Hz = 2ms per cycle

    return (mem->timer < func->params.on_time) ? 1 : 0;
}

int32_t execute_delay_off(PMU_LogicFunction_t* func, int32_t* inputs) {
    StateMemory_t* mem = &func->state.memory;

    if (inputs[0] != 0) {
        // Input is HIGH
        mem->timer = HAL_GetTick();
        return 1;
    } else {
        // Input is LOW, check delay
        if (HAL_GetTick() - mem->timer < func->params.delay_ms) {
            return 1;  // Still in delay period
        }
        return 0;
    }
}
```

---

## Practical Examples

### Turn Signal Flasher

```c
{
    "functions": [
        {"id": 0, "type": "flasher",
         "input": 20,           // Left signal switch
         "output": 100,         // Left signal output
         "parameters": {"on_time_ms": 500, "off_time_ms": 500}
        },
        {"id": 1, "type": "flasher",
         "input": 21,           // Right signal switch
         "output": 101,
         "parameters": {"on_time_ms": 500, "off_time_ms": 500}
        }
    ]
}
```

### Push-On/Push-Off Button

```c
{
    "type": "toggle",
    "input": 20,        // Momentary button
    "output": 100,      // Light output
    "parameters": {"initial_state": 0}
}
```

### Fan Run-On

```c
{
    "functions": [
        // Immediate on when temp high
        {"id": 0, "type": "greater", "inputs": [0, 850], "output": 210},
        // Delay off by 60 seconds
        {"id": 1, "type": "delay_off", "input": 210, "output": 100,
         "parameters": {"delay_ms": 60000}}
    ]
}
```

---

## See Also

- [Control Flow Functions](control-flow-functions.md)
- [Utility Functions](utility-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

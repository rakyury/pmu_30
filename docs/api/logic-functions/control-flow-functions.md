# Control Flow Functions

**Category:** Conditional Execution and Selection
**Function IDs:** 0x50-0x5F

---

## Overview

Control flow functions enable conditional logic and value selection based on input conditions.

---

## Functions

### 1. IF_THEN_ELSE (0x50)

Selects between two values based on condition.

```c
{
    "type": "if_then_else",
    "inputs": [210, 200, 201],  // Condition, TrueValue, FalseValue
    "output": 100
}
// Output = Condition ? TrueValue : FalseValue
```

**Example:** Select fan speed based on temperature threshold.

---

### 2. SELECT (0x51)

Selects one of multiple values based on index.

```c
{
    "type": "select",
    "inputs": [220, 200, 201, 202, 203],  // Index, Value0, Value1, ...
    "output": 100
}
// Output = Values[Index] (clamped to valid range)
```

**Use Case:** Rotary switch mode selection.

---

### 3. MULTIPLEXER (0x52)

Routes one of N inputs to output.

```c
{
    "type": "multiplexer",
    "inputs": [200, 201, 202, 203],
    "output": 210,
    "parameters": {
        "selector_channel": 20,     // Digital inputs for selection
        "mode": "binary"            // or "one_hot"
    }
}
```

**Modes:**
- `binary`: Selector is binary value (0-3 selects input 0-3)
- `one_hot`: Each selector bit selects corresponding input

---

### 4. PRIORITY_ENCODER (0x53)

Returns index of highest priority active input.

```c
{
    "type": "priority_encoder",
    "inputs": [210, 211, 212, 213],  // Priority high to low
    "output": 220
}
// Output = index of first non-zero input (0-3), or -1 if all zero
```

---

### 5. SWITCH_CASE (0x54)

Multi-way switch based on input value.

```c
{
    "type": "switch_case",
    "input": 220,
    "output": 100,
    "parameters": {
        "cases": [
            {"value": 0, "result": 0},
            {"value": 1, "result": 500},
            {"value": 2, "result": 750},
            {"value": 3, "result": 1000}
        ],
        "default": 0
    }
}
```

---

### 6. THRESHOLD_SELECT (0x55)

Selects output based on threshold levels.

```c
{
    "type": "threshold_select",
    "input": 0,         // Temperature input
    "output": 100,
    "parameters": {
        "thresholds": [600, 700, 800, 900],
        "outputs": [0, 250, 500, 750, 1000]
    }
}
// Input < 600: Output = 0
// 600-699: Output = 250
// 700-799: Output = 500
// 800-899: Output = 750
// >= 900: Output = 1000
```

**Use Case:** Stepped fan control.

---

### 7. CONDITIONAL_ENABLE (0x56)

Enables/disables another function.

```c
{
    "type": "conditional_enable",
    "input": 210,           // Condition
    "output": 0,            // Not used
    "parameters": {
        "target_function": 5,
        "invert": false
    }
}
// Enables function 5 when input is true
```

---

### 8. SEQUENCE (0x57)

Executes functions in sequence with delays.

```c
{
    "type": "sequence",
    "input": 210,           // Trigger
    "output": 220,          // Current step
    "parameters": {
        "steps": [
            {"channel": 100, "value": 1, "delay_ms": 0},
            {"channel": 101, "value": 1, "delay_ms": 100},
            {"channel": 102, "value": 1, "delay_ms": 200}
        ],
        "mode": "trigger"   // or "hold"
    }
}
```

**Modes:**
- `trigger`: Single execution on rising edge
- `hold`: Runs while input is true, reverses when false

---

## Implementation

```c
int32_t execute_control_flow(PMU_LogicFunction_t* func, int32_t* inputs) {
    switch (func->type) {
        case PMU_FUNC_IF_THEN_ELSE:
            return (inputs[0] != 0) ? inputs[1] : inputs[2];

        case PMU_FUNC_SELECT: {
            int32_t index = inputs[0];
            if (index < 0) index = 0;
            if (index >= func->input_count - 1) index = func->input_count - 2;
            return inputs[index + 1];
        }

        case PMU_FUNC_PRIORITY_ENCODER:
            for (int i = 0; i < func->input_count; i++) {
                if (inputs[i] != 0) return i;
            }
            return -1;

        case PMU_FUNC_SWITCH_CASE:
            for (int i = 0; i < func->params.case_count; i++) {
                if (inputs[0] == func->params.cases[i].value) {
                    return func->params.cases[i].result;
                }
            }
            return func->params.default_value;

        case PMU_FUNC_THRESHOLD_SELECT: {
            for (int i = 0; i < func->params.threshold_count; i++) {
                if (inputs[0] < func->params.thresholds[i]) {
                    return func->params.outputs[i];
                }
            }
            return func->params.outputs[func->params.threshold_count];
        }

        default:
            return 0;
    }
}
```

---

## Practical Examples

### Mode-Based Fan Control

```c
// Rotary switch selects fan mode
{
    "functions": [
        // Mode 0=Off, 1=Low, 2=Auto, 3=High
        {"id": 0, "type": "switch_case",
         "input": 20,
         "output": 100,
         "parameters": {
             "cases": [
                 {"value": 0, "result": 0},
                 {"value": 1, "result": 300},
                 {"value": 2, "result": -1},     // Special: use auto
                 {"value": 3, "result": 1000}
             ]
         }
        },
        // Auto mode calculation
        {"id": 1, "type": "threshold_select",
         "input": 0,
         "output": 210
        },
        // Select auto if mode 2
        {"id": 2, "type": "if_then_else",
         "inputs": [211, 210, 100],  // IsAuto, AutoValue, ManualValue
         "output": 100
        }
    ]
}
```

### Startup Sequence

```c
// Fuel system startup sequence
{
    "type": "sequence",
    "input": 210,           // Ignition ON
    "parameters": {
        "steps": [
            {"channel": 100, "value": 1, "delay_ms": 0},      // Main relay
            {"channel": 101, "value": 1, "delay_ms": 500},    // Fuel pump prime
            {"channel": 102, "value": 1, "delay_ms": 2000}    // Injector power
        ]
    }
}
```

---

## See Also

- [Logic Comparison Functions](logic-comparison-functions.md)
- [State Management Functions](state-management-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

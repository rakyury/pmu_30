# Arithmetic Functions

**Category:** Mathematical Operations
**Function IDs:** 0x00-0x0F

---

## Overview

Arithmetic functions perform mathematical calculations on channel values.

---

## Functions

### 1. ADD (0x00)

Adds two values.

```c
{
    "type": "add",
    "inputs": [200, 201],   // Input channels
    "output": 202           // Result channel
}
// Output = Input[0] + Input[1]
```

---

### 2. SUBTRACT (0x01)

Subtracts second value from first.

```c
{
    "type": "subtract",
    "inputs": [200, 201],
    "output": 202
}
// Output = Input[0] - Input[1]
```

---

### 3. MULTIPLY (0x02)

Multiplies two values with scaling.

```c
{
    "type": "multiply",
    "inputs": [200, 201],
    "output": 202,
    "parameters": {
        "scale_factor": 1000    // Divide result by this
    }
}
// Output = (Input[0] * Input[1]) / scale_factor
```

**Note:** Scale factor prevents overflow with large values.

---

### 4. DIVIDE (0x03)

Divides first value by second.

```c
{
    "type": "divide",
    "inputs": [200, 201],
    "output": 202,
    "parameters": {
        "scale_factor": 1000    // Multiply before divide
    }
}
// Output = (Input[0] * scale_factor) / Input[1]
// Returns INT32_MAX if Input[1] = 0
```

---

### 5. MODULO (0x04)

Returns remainder of division.

```c
{
    "type": "modulo",
    "inputs": [200, 201],
    "output": 202
}
// Output = Input[0] % Input[1]
```

---

### 6. MIN (0x05)

Returns minimum of two values.

```c
{
    "type": "min",
    "inputs": [200, 201],
    "output": 202
}
// Output = min(Input[0], Input[1])
```

---

### 7. MAX (0x06)

Returns maximum of two values.

```c
{
    "type": "max",
    "inputs": [200, 201],
    "output": 202
}
// Output = max(Input[0], Input[1])
```

---

### 8. AVERAGE (0x07)

Returns average of up to 8 inputs.

```c
{
    "type": "average",
    "inputs": [200, 201, 202, 203],
    "output": 210
}
// Output = (sum of all inputs) / count
```

---

### 9. WEIGHTED_AVG (0x08)

Weighted average of inputs.

```c
{
    "type": "weighted_avg",
    "inputs": [200, 201],
    "output": 210,
    "parameters": {
        "weights": [70, 30]     // 70% first, 30% second
    }
}
// Output = (Input[0]*70 + Input[1]*30) / 100
```

---

### 10. NEGATE (0x09)

Returns negative of value.

```c
{
    "type": "negate",
    "input": 200,
    "output": 201
}
// Output = -Input
```

---

### 11. INCREMENT (0x0A)

Increments value by step.

```c
{
    "type": "increment",
    "input": 200,
    "output": 201,
    "parameters": {
        "step": 1,
        "max": 1000,
        "wrap": true
    }
}
```

---

### 12. DECREMENT (0x0B)

Decrements value by step.

```c
{
    "type": "decrement",
    "input": 200,
    "output": 201,
    "parameters": {
        "step": 1,
        "min": 0,
        "wrap": true
    }
}
```

---

## Implementation

```c
int32_t execute_arithmetic(PMU_LogicFunction_t* func, int32_t* inputs) {
    switch (func->type) {
        case PMU_FUNC_ADD:
            return inputs[0] + inputs[1];

        case PMU_FUNC_SUBTRACT:
            return inputs[0] - inputs[1];

        case PMU_FUNC_MULTIPLY:
            return (inputs[0] * inputs[1]) / func->params.scale_factor;

        case PMU_FUNC_DIVIDE:
            if (inputs[1] == 0) return INT32_MAX;
            return (inputs[0] * func->params.scale_factor) / inputs[1];

        case PMU_FUNC_MIN:
            return (inputs[0] < inputs[1]) ? inputs[0] : inputs[1];

        case PMU_FUNC_MAX:
            return (inputs[0] > inputs[1]) ? inputs[0] : inputs[1];

        case PMU_FUNC_AVERAGE: {
            int32_t sum = 0;
            for (int i = 0; i < func->input_count; i++) {
                sum += inputs[i];
            }
            return sum / func->input_count;
        }

        default:
            return 0;
    }
}
```

---

## Practical Examples

### Calculate Fuel Consumption

```c
// Liters per hour from injector duty and flow rate
{
    "functions": [
        {
            "id": 0,
            "type": "multiply",
            "inputs": [200, 201],    // Duty * FlowRate
            "output": 210,
            "parameters": {"scale_factor": 1000}
        }
    ]
}
```

### Average Temperature

```c
// Average of 4 temperature sensors
{
    "type": "average",
    "inputs": [0, 1, 2, 3],     // 4 NTC inputs
    "output": 200
}
```

---

## See Also

- [Logic Comparison Functions](logic-comparison-functions.md)
- [Data Manipulation Functions](data-manipulation-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

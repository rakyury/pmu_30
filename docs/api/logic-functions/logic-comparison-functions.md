# Logic & Comparison Functions

**Category:** Boolean Logic and Value Comparison
**Function IDs:** 0x20-0x4F

---

## 1. Comparison Functions (0x20-0x2F)

### GREATER (0x20)

Returns 1 if first input is greater than second.

```c
{
    "type": "greater",
    "inputs": [200, 201],
    "output": 210
}
// Output = (Input[0] > Input[1]) ? 1 : 0
```

---

### GREATER_EQUAL (0x21)

Returns 1 if first input is greater than or equal to second.

```c
{
    "type": "greater_equal",
    "inputs": [200, 201],
    "output": 210
}
// Output = (Input[0] >= Input[1]) ? 1 : 0
```

---

### LESS (0x22)

Returns 1 if first input is less than second.

```c
{
    "type": "less",
    "inputs": [200, 201],
    "output": 210
}
// Output = (Input[0] < Input[1]) ? 1 : 0
```

---

### LESS_EQUAL (0x23)

Returns 1 if first input is less than or equal to second.

```c
{
    "type": "less_equal",
    "inputs": [200, 201],
    "output": 210
}
// Output = (Input[0] <= Input[1]) ? 1 : 0
```

---

### EQUAL (0x24)

Returns 1 if inputs are equal (within tolerance).

```c
{
    "type": "equal",
    "inputs": [200, 201],
    "output": 210,
    "parameters": {
        "tolerance": 10     // Optional: +/- tolerance
    }
}
// Output = (|Input[0] - Input[1]| <= tolerance) ? 1 : 0
```

---

### NOT_EQUAL (0x25)

Returns 1 if inputs are not equal.

```c
{
    "type": "not_equal",
    "inputs": [200, 201],
    "output": 210,
    "parameters": {
        "tolerance": 10
    }
}
// Output = (|Input[0] - Input[1]| > tolerance) ? 1 : 0
```

---

### IN_RANGE (0x26)

Returns 1 if value is within range.

```c
{
    "type": "in_range",
    "input": 200,
    "output": 210,
    "parameters": {
        "min": 800,
        "max": 900
    }
}
// Output = (Input >= min && Input <= max) ? 1 : 0
```

---

### OUT_OF_RANGE (0x27)

Returns 1 if value is outside range.

```c
{
    "type": "out_of_range",
    "input": 200,
    "output": 210,
    "parameters": {
        "min": 800,
        "max": 900
    }
}
// Output = (Input < min || Input > max) ? 1 : 0
```

---

## 2. Boolean Logic Functions (0x40-0x4F)

### AND (0x40)

Logical AND of 2-8 inputs.

```c
{
    "type": "and",
    "inputs": [210, 211, 212],
    "output": 220
}
// Output = 1 if ALL inputs are non-zero
```

---

### OR (0x41)

Logical OR of 2-8 inputs.

```c
{
    "type": "or",
    "inputs": [210, 211, 212],
    "output": 220
}
// Output = 1 if ANY input is non-zero
```

---

### NOT (0x42)

Logical NOT (inversion).

```c
{
    "type": "not",
    "input": 210,
    "output": 220
}
// Output = (Input == 0) ? 1 : 0
```

---

### XOR (0x43)

Exclusive OR of 2 inputs.

```c
{
    "type": "xor",
    "inputs": [210, 211],
    "output": 220
}
// Output = 1 if inputs differ
```

---

### NAND (0x44)

NOT AND of 2-8 inputs.

```c
{
    "type": "nand",
    "inputs": [210, 211],
    "output": 220
}
// Output = NOT(AND(inputs))
```

---

### NOR (0x45)

NOT OR of 2-8 inputs.

```c
{
    "type": "nor",
    "inputs": [210, 211],
    "output": 220
}
// Output = NOT(OR(inputs))
```

---

### IS_TRUE (0x46)

Returns 1 if input is non-zero.

```c
{
    "type": "is_true",
    "input": 200,
    "output": 210
}
// Output = (Input != 0) ? 1 : 0
```

---

### IS_FALSE (0x47)

Returns 1 if input is zero.

```c
{
    "type": "is_false",
    "input": 200,
    "output": 210
}
// Output = (Input == 0) ? 1 : 0
```

---

## Implementation

```c
int32_t execute_comparison(PMU_LogicFunction_t* func, int32_t* inputs) {
    switch (func->type) {
        case PMU_FUNC_GREATER:
            return (inputs[0] > inputs[1]) ? 1 : 0;

        case PMU_FUNC_LESS:
            return (inputs[0] < inputs[1]) ? 1 : 0;

        case PMU_FUNC_EQUAL: {
            int32_t diff = inputs[0] - inputs[1];
            if (diff < 0) diff = -diff;
            return (diff <= func->params.tolerance) ? 1 : 0;
        }

        case PMU_FUNC_IN_RANGE:
            return (inputs[0] >= func->params.min &&
                    inputs[0] <= func->params.max) ? 1 : 0;

        case PMU_FUNC_AND: {
            for (int i = 0; i < func->input_count; i++) {
                if (inputs[i] == 0) return 0;
            }
            return 1;
        }

        case PMU_FUNC_OR: {
            for (int i = 0; i < func->input_count; i++) {
                if (inputs[i] != 0) return 1;
            }
            return 0;
        }

        case PMU_FUNC_NOT:
            return (inputs[0] == 0) ? 1 : 0;

        case PMU_FUNC_XOR:
            return ((inputs[0] != 0) ^ (inputs[1] != 0)) ? 1 : 0;

        default:
            return 0;
    }
}
```

---

## Practical Examples

### Temperature Warning

```c
// Warning if temp > 90C or oil pressure < 2 bar
{
    "functions": [
        {"id": 0, "type": "greater", "inputs": [0, 900], "output": 210},
        {"id": 1, "type": "less", "inputs": [1, 200], "output": 211},
        {"id": 2, "type": "or", "inputs": [210, 211], "output": 100}
    ]
}
```

### Multi-Condition Enable

```c
// Enable output if: engine running AND temp OK AND switch ON
{
    "functions": [
        {"id": 0, "type": "greater", "inputs": [200, 500], "output": 210},  // RPM > 500
        {"id": 1, "type": "less", "inputs": [0, 950], "output": 211},        // Temp < 95
        {"id": 2, "type": "is_true", "input": 20, "output": 212},            // Switch ON
        {"id": 3, "type": "and", "inputs": [210, 211, 212], "output": 100}
    ]
}
```

---

## See Also

- [Arithmetic Functions](arithmetic-functions.md)
- [Control Flow Functions](control-flow-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

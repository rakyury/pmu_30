# I/O Functions

**Category:** Input/Output Operations
**Function IDs:** 0xE0-0xEF

---

## Overview

I/O functions provide direct manipulation of channel values with enhanced control.

---

## Functions

### 1. CHANNEL_COPY (0xE0)

Copies value from one channel to another.

```c
// Configuration
{
    "type": "channel_copy",
    "input": 200,       // Source channel
    "output": 100       // Destination channel
}
```

**Use Case:** Route CAN signal directly to output.

---

### 2. CHANNEL_SCALE (0xE1)

Scales and offsets a channel value.

```c
// Output = (Input * factor) + offset
{
    "type": "channel_scale",
    "input": 0,
    "output": 200,
    "parameters": {
        "factor": 0.0122,   // 5V / 4095 * 10
        "offset": -25       // Offset in tenths
    }
}
```

---

### 3. CHANNEL_LIMIT (0xE2)

Clamps value between min and max.

```c
{
    "type": "channel_limit",
    "input": 200,
    "output": 201,
    "parameters": {
        "min": 0,
        "max": 1000
    }
}
```

---

### 4. CHANNEL_INVERT (0xE3)

Inverts digital or analog value.

```c
// Digital: 0->1, 1->0
// Analog: max - value
{
    "type": "channel_invert",
    "input": 20,
    "output": 100,
    "parameters": {
        "max_value": 1000   // For analog inversion
    }
}
```

---

### 5. CHANNEL_DEADBAND (0xE4)

Creates a deadband zone around center.

```c
{
    "type": "channel_deadband",
    "input": 200,
    "output": 130,
    "parameters": {
        "center": 500,
        "width": 50         // +/- 50 from center = 0
    }
}
```

**Use Case:** Joystick/throttle with center deadzone.

---

### 6. CHANNEL_MAP (0xE5)

Maps input range to output range.

```c
// Map 0-4095 ADC to 0-100 percentage
{
    "type": "channel_map",
    "input": 0,
    "output": 200,
    "parameters": {
        "in_min": 0,
        "in_max": 4095,
        "out_min": 0,
        "out_max": 1000
    }
}
```

---

### 7. CHANNEL_ABS (0xE6)

Returns absolute value.

```c
{
    "type": "channel_abs",
    "input": 130,       // H-bridge value (-1000 to 1000)
    "output": 201       // Always positive
}
```

---

### 8. CHANNEL_SIGN (0xE7)

Returns sign of value (-1, 0, +1).

```c
{
    "type": "channel_sign",
    "input": 130,
    "output": 202
}
// Returns: -1 if negative, 0 if zero, 1 if positive
```

---

## Implementation Example

```c
int32_t execute_io_function(PMU_LogicFunction_t* func, int32_t* inputs) {
    switch (func->type) {
        case PMU_FUNC_CHANNEL_COPY:
            return inputs[0];

        case PMU_FUNC_CHANNEL_SCALE:
            return (inputs[0] * func->params.factor) + func->params.offset;

        case PMU_FUNC_CHANNEL_LIMIT:
            if (inputs[0] < func->params.min) return func->params.min;
            if (inputs[0] > func->params.max) return func->params.max;
            return inputs[0];

        case PMU_FUNC_CHANNEL_INVERT:
            return func->params.max_value - inputs[0];

        case PMU_FUNC_CHANNEL_MAP: {
            int32_t range_in = func->params.in_max - func->params.in_min;
            int32_t range_out = func->params.out_max - func->params.out_min;
            return ((inputs[0] - func->params.in_min) * range_out / range_in)
                   + func->params.out_min;
        }

        default:
            return 0;
    }
}
```

---

## See Also

- [Arithmetic Functions](arithmetic-functions.md)
- [Data Manipulation](data-manipulation-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

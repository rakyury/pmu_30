# Utility Functions

**Category:** System Utilities and Helpers
**Function IDs:** 0xF0-0xFF

---

## Overview

Utility functions provide system-level operations, debugging aids, and special-purpose functionality.

---

## Functions

### 1. CONSTANT (0xF0)

Outputs a constant value.

```c
{
    "type": "constant",
    "output": 200,
    "parameters": {
        "value": 1000
    }
}
// Output always = 1000
```

**Use Case:** Threshold values, reference constants.

---

### 2. SYSTEM_TIME (0xF1)

Outputs system timestamp.

```c
{
    "type": "system_time",
    "output": 200,
    "parameters": {
        "unit": "seconds"   // or "ms", "minutes", "hours"
    }
}
// Output = time since boot
```

---

### 3. RTC_TIME (0xF2)

Outputs real-time clock value.

```c
{
    "type": "rtc_time",
    "output": 200,
    "parameters": {
        "format": "hhmm"    // or "seconds_since_midnight"
    }
}
// Output = 1430 for 14:30
```

---

### 4. RANDOM (0xF3)

Generates pseudo-random value.

```c
{
    "type": "random",
    "output": 200,
    "parameters": {
        "min": 0,
        "max": 1000,
        "seed_channel": 0   // Optional: seed from channel
    }
}
```

---

### 5. DEBUG_PRINT (0xF4)

Outputs value to debug log (no runtime effect).

```c
{
    "type": "debug_print",
    "input": 200,
    "parameters": {
        "label": "Temperature",
        "interval_ms": 1000     // Print every second
    }
}
// Logs: [DEBUG] Temperature = 875
```

---

### 6. WATCHDOG (0xF5)

Monitors channel for activity.

```c
{
    "type": "watchdog",
    "input": 200,               // Channel to monitor
    "output": 210,              // Fault indicator
    "parameters": {
        "timeout_ms": 5000,
        "min_change": 10        // Must change by at least 10
    }
}
// Output = 1 if input hasn't changed for timeout period
```

**Use Case:** Sensor stuck detection.

---

### 7. HEARTBEAT (0xF6)

Generates periodic pulse.

```c
{
    "type": "heartbeat",
    "output": 200,
    "parameters": {
        "period_ms": 1000,
        "pulse_width_ms": 100
    }
}
// 100ms pulse every 1 second
```

---

### 8. BIT_EXTRACT (0xF7)

Extracts bits from value.

```c
{
    "type": "bit_extract",
    "input": 200,
    "output": 210,
    "parameters": {
        "start_bit": 4,
        "bit_count": 4
    }
}
// Output = (Input >> 4) & 0x0F
```

**Use Case:** Decode CAN status bytes.

---

### 9. BIT_PACK (0xF8)

Packs multiple channels into bits.

```c
{
    "type": "bit_pack",
    "inputs": [100, 101, 102, 103, 104, 105, 106, 107],
    "output": 200
}
// Output = bit0*1 + bit1*2 + bit2*4 + ...
// Non-zero inputs become 1, zero inputs become 0
```

**Use Case:** Create status byte from multiple flags.

---

### 10. CONDITION_COUNT (0xF9)

Counts how many inputs are true.

```c
{
    "type": "condition_count",
    "inputs": [210, 211, 212, 213],
    "output": 220
}
// Output = number of non-zero inputs (0-4)
```

---

### 11. RAMP_GENERATOR (0xFA)

Generates ramp signal.

```c
{
    "type": "ramp_generator",
    "inputs": [210, 211],       // Start, Stop
    "output": 200,
    "parameters": {
        "start_value": 0,
        "end_value": 1000,
        "duration_ms": 5000,
        "mode": "once"          // or "continuous", "pingpong"
    }
}
```

---

### 12. PWM_GENERATOR (0xFB)

Generates PWM signal in software.

```c
{
    "type": "pwm_generator",
    "input": 200,               // Duty cycle (0-1000)
    "output": 210,              // PWM state (0 or 1)
    "parameters": {
        "frequency_hz": 10      // Software PWM at 10Hz
    }
}
```

**Use Case:** Slow PWM for indicators.

---

### 13. FAULT_INJECT (0xFC)

Injects test faults (debug only).

```c
{
    "type": "fault_inject",
    "input": 220,               // Trigger
    "parameters": {
        "channel": 100,
        "fault_type": "overcurrent"
    }
}
// When trigger active, simulates fault on channel
```

---

### 14. VERSION_INFO (0xFD)

Returns firmware/config version.

```c
{
    "type": "version_info",
    "output": 200,
    "parameters": {
        "info": "firmware_major"    // or "minor", "patch", "config"
    }
}
```

---

### 15. CHANNEL_STATUS (0xFE)

Returns channel status flags.

```c
{
    "type": "channel_status",
    "input": 100,               // Channel to check
    "output": 200,
    "parameters": {
        "flag": "fault"         // or "enabled", "timeout"
    }
}
// Output = 1 if channel has fault flag
```

---

### 16. NOP (0xFF)

No operation (placeholder).

```c
{
    "type": "nop",
    "input": 0,
    "output": 0
}
// Does nothing, used for spacing/alignment
```

---

## Implementation

```c
int32_t execute_utility(PMU_LogicFunction_t* func, int32_t* inputs) {
    switch (func->type) {
        case PMU_FUNC_CONSTANT:
            return func->params.value;

        case PMU_FUNC_SYSTEM_TIME:
            switch (func->params.unit) {
                case UNIT_MS:      return HAL_GetTick();
                case UNIT_SECONDS: return HAL_GetTick() / 1000;
                case UNIT_MINUTES: return HAL_GetTick() / 60000;
                case UNIT_HOURS:   return HAL_GetTick() / 3600000;
            }
            break;

        case PMU_FUNC_BIT_EXTRACT: {
            uint32_t mask = (1 << func->params.bit_count) - 1;
            return (inputs[0] >> func->params.start_bit) & mask;
        }

        case PMU_FUNC_BIT_PACK: {
            int32_t result = 0;
            for (int i = 0; i < func->input_count; i++) {
                if (inputs[i] != 0) {
                    result |= (1 << i);
                }
            }
            return result;
        }

        case PMU_FUNC_CONDITION_COUNT: {
            int32_t count = 0;
            for (int i = 0; i < func->input_count; i++) {
                if (inputs[i] != 0) count++;
            }
            return count;
        }

        case PMU_FUNC_CHANNEL_STATUS: {
            const PMU_Channel_t* ch = PMU_Channel_GetInfo(inputs[0]);
            if (ch == NULL) return -1;
            return (ch->flags & func->params.flag_mask) ? 1 : 0;
        }

        case PMU_FUNC_NOP:
        default:
            return 0;
    }
    return 0;
}
```

---

## Practical Examples

### Status Byte for CAN

```c
{
    "functions": [
        // Check each output for fault
        {"id": 0, "type": "channel_status", "input": 100, "output": 210,
         "parameters": {"flag": "fault"}},
        {"id": 1, "type": "channel_status", "input": 101, "output": 211,
         "parameters": {"flag": "fault"}},
        // ... more channels ...
        // Pack into status byte
        {"id": 8, "type": "bit_pack",
         "inputs": [210, 211, 212, 213, 214, 215, 216, 217],
         "output": 250}
    ]
}
// Channel 250 contains fault status bitmap for CAN transmission
```

### Sensor Health Monitor

```c
{
    "type": "watchdog",
    "input": 200,           // RPM signal
    "output": 210,
    "parameters": {
        "timeout_ms": 2000,
        "min_change": 50
    }
}
// Detects if RPM signal is stuck (sensor failure)
```

### System Uptime

```c
{
    "functions": [
        {"type": "system_time", "output": 1003, "parameters": {"unit": "seconds"}},
        // Convert to minutes for CAN
        {"type": "divide", "inputs": [1003, 60], "output": 1004}
    ]
}
```

---

## See Also

- [State Management Functions](state-management-functions.md)
- [Channel Operations Functions](channel-operations-functions.md)
- [Logic Functions Reference](../logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

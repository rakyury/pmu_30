# Getting Started with Unified Channels

**Version:** 1.0
**Date:** December 2024

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Quick Start Tutorial](#2-quick-start-tutorial)
3. [Basic Channel Operations](#3-basic-channel-operations)
4. [Common Use Cases](#4-common-use-cases)
5. [Configuration Best Practices](#5-configuration-best-practices)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Introduction

The Unified Channel System provides a single interface for all inputs and outputs in the PMU-30. Whether you're reading an analog sensor, controlling a PROFET output, or processing CAN bus data, the API is consistent and simple.

### 1.1 What is a Channel?

A channel is an abstraction that represents:
- **Physical inputs**: ADC, digital pins, frequency counters
- **Physical outputs**: PROFET switches, H-bridges, PWM
- **Virtual data**: CAN signals, calculations, system values

### 1.2 Why Use Channels?

| Benefit | Description |
|---------|-------------|
| **Simplicity** | One API for everything |
| **Flexibility** | Mix physical and virtual freely |
| **Portability** | Logic independent of hardware |
| **Debugging** | All values accessible by name |

---

## 2. Quick Start Tutorial

### 2.1 Initialize the System

```c
#include "pmu_channel.h"

int main(void) {
    // Initialize HAL
    HAL_Init();
    SystemClock_Config();

    // Initialize channel system
    if (PMU_Channel_Init() != HAL_OK) {
        Error_Handler();
    }

    // Your application code...
}
```

### 2.2 Read an Input

```c
// Read analog input (channel 0)
int32_t throttle = PMU_Channel_GetValue(0);

// Read battery voltage (system channel)
int32_t battery_mv = PMU_Channel_GetValue(1000);
float battery_v = battery_mv / 1000.0f;

printf("Throttle: %ld, Battery: %.2f V\n", throttle, battery_v);
```

### 2.3 Control an Output

```c
// Turn on headlights (output channel 100)
PMU_Channel_SetValue(100, 1);  // ON

// Set fan speed to 75% (PWM output)
PMU_Channel_SetValue(101, 750);  // 75.0%

// Control H-bridge motor (forward 50%)
PMU_Channel_SetValue(130, 500);  // +50%
```

### 2.4 Create a Virtual Channel

```c
PMU_Channel_t fuel_level = {
    .channel_id = 200,
    .type = PMU_CHANNEL_INPUT_CALCULATED,
    .direction = PMU_CHANNEL_DIR_INPUT,
    .format = PMU_CHANNEL_FORMAT_PERCENT,
    .flags = PMU_CHANNEL_FLAG_ENABLED,
    .min_value = 0,
    .max_value = 1000,
    .name = "Fuel Level",
    .unit = "%"
};

PMU_Channel_Register(&fuel_level);

// Now you can read/write channel 200
PMU_Channel_SetValue(200, 750);  // 75%
```

---

## 3. Basic Channel Operations

### 3.1 Reading Values

```c
// By ID (fastest)
int32_t value = PMU_Channel_GetValue(channel_id);

// By name (convenient for debugging)
const PMU_Channel_t* ch = PMU_Channel_GetByName("Coolant Temp");
if (ch != NULL) {
    printf("%s = %ld %s\n", ch->name, ch->value, ch->unit);
}

// Get full info
const PMU_Channel_t* info = PMU_Channel_GetInfo(0);
printf("Range: %ld to %ld\n", info->min_value, info->max_value);
```

### 3.2 Writing Values

```c
// Simple write
PMU_Channel_SetValue(100, 1);

// With error checking
HAL_StatusTypeDef status = PMU_Channel_SetValue(100, value);
if (status != HAL_OK) {
    // Handle error - channel not found or read-only
}
```

### 3.3 Checking Channel State

```c
const PMU_Channel_t* ch = PMU_Channel_GetInfo(100);

// Check if enabled
if (ch->flags & PMU_CHANNEL_FLAG_ENABLED) {
    // Channel is active
}

// Check for fault
if (ch->flags & PMU_CHANNEL_FLAG_FAULT) {
    // Handle fault condition
}

// Check type
if (PMU_Channel_IsInput(ch->type)) {
    // It's an input
}

if (PMU_Channel_IsVirtual(ch->type)) {
    // It's virtual (CAN, calculated, etc.)
}
```

### 3.4 Enabling/Disabling

```c
// Disable a channel (stops updates, outputs go to safe state)
PMU_Channel_SetEnabled(100, false);

// Re-enable
PMU_Channel_SetEnabled(100, true);
```

---

## 4. Common Use Cases

### 4.1 Reading Analog Sensor

```c
// Temperature sensor on ADC channel 2
// Raw ADC: 0-4095
// Voltage: 0-5V
// Temperature: -40 to +125 C

int32_t raw = PMU_Channel_GetValue(2);

// Convert using calibration
float voltage = raw * 5.0f / 4095.0f;
float temp_c = (voltage - 0.5f) * 100.0f;  // For LM35

printf("Temperature: %.1f C\n", temp_c);
```

### 4.2 Simple Output Control

```c
// Headlight control based on light sensor
int32_t light_level = PMU_Channel_GetValue(0);  // Light sensor

if (light_level < 200) {  // Dark
    PMU_Channel_SetValue(100, 1);  // Headlights ON
} else {
    PMU_Channel_SetValue(100, 0);  // Headlights OFF
}
```

### 4.3 PWM Fan Control

```c
// Fan speed based on temperature
int32_t temp = PMU_Channel_GetValue(1);  // Temperature in 0.1 C

int32_t duty = 0;
if (temp > 800) {         // > 80 C
    duty = 1000;          // 100%
} else if (temp > 600) {  // > 60 C
    duty = (temp - 600) * 5;  // 0-100% between 60-80 C
}

PMU_Channel_SetValue(101, duty);  // PWM output
```

### 4.4 H-Bridge Motor Control

```c
// Window motor control
// Channel 10: UP button
// Channel 11: DOWN button
// Channel 130: H-bridge output

int32_t up = PMU_Channel_GetValue(10);
int32_t down = PMU_Channel_GetValue(11);

if (up && !down) {
    PMU_Channel_SetValue(130, 800);   // Forward 80%
} else if (down && !up) {
    PMU_Channel_SetValue(130, -800);  // Reverse 80%
} else {
    PMU_Channel_SetValue(130, 0);     // Stop
}
```

### 4.5 Using CAN Data

```c
// ECU RPM from CAN bus (configured as channel 200)
int32_t rpm = PMU_Channel_GetValue(200);

// Rev limiter at 7000 RPM
if (rpm > 7000) {
    PMU_Channel_SetValue(100, 0);  // Cut fuel pump
} else {
    PMU_Channel_SetValue(100, 1);  // Fuel pump ON
}
```

---

## 5. Configuration Best Practices

### 5.1 Channel Naming Conventions

```c
// Good names - descriptive and consistent
"Coolant Temp"
"Oil Pressure"
"Headlight L"
"Fan PWM"
"ECU RPM"

// Bad names - ambiguous
"Input 1"
"ADC0"
"Out"
```

### 5.2 Channel ID Organization

| Range | Purpose | Example |
|-------|---------|---------|
| 0-19 | Analog inputs | Sensors |
| 20-39 | Digital inputs | Switches |
| 100-129 | PROFET outputs | Lights, pumps |
| 130-139 | H-bridge outputs | Motors |
| 200-299 | CAN inputs | ECU data |
| 300-399 | Calculations | Logic results |

### 5.3 Value Scaling

```c
// Use consistent scaling throughout
// Temperatures: 0.1 C (25.0 C = 250)
// Pressures: 0.01 bar (3.5 bar = 350)
// Percentages: 0.1% (100% = 1000)
// Voltages: mV (12.5V = 12500)
```

### 5.4 Error Handling Pattern

```c
void safe_output_control(uint16_t output_ch, uint16_t input_ch) {
    // Check input channel exists
    const PMU_Channel_t* in = PMU_Channel_GetInfo(input_ch);
    if (in == NULL) {
        // Log error, use default
        PMU_Channel_SetValue(output_ch, 0);
        return;
    }

    // Check for input fault
    if (in->flags & PMU_CHANNEL_FLAG_FAULT) {
        // Safe state on fault
        PMU_Channel_SetValue(output_ch, 0);
        return;
    }

    // Normal operation
    PMU_Channel_SetValue(output_ch, in->value > 500 ? 1 : 0);
}
```

---

## 6. Troubleshooting

### 6.1 Channel Not Found

**Symptom:** `PMU_Channel_GetInfo()` returns NULL

**Solutions:**
- Verify channel ID is within range (0-1023)
- Check if channel was registered
- System channels (1000+) are always available

```c
const PMU_Channel_t* ch = PMU_Channel_GetInfo(100);
if (ch == NULL) {
    printf("Channel 100 not registered!\n");
}
```

### 6.2 Value Not Updating

**Symptom:** Channel value stays constant

**Possible causes:**
1. Channel disabled
2. ADC not initialized
3. CAN timeout
4. Physical connection issue

```c
const PMU_Channel_t* ch = PMU_Channel_GetInfo(0);

// Check if enabled
if (!(ch->flags & PMU_CHANNEL_FLAG_ENABLED)) {
    printf("Channel disabled\n");
}

// Check for fault
if (ch->flags & PMU_CHANNEL_FLAG_FAULT) {
    printf("Channel in fault state\n");
}
```

### 6.3 Output Not Working

**Symptom:** Output doesn't respond to SetValue

**Solutions:**
1. Check channel is output type
2. Verify physical connection
3. Check for overcurrent/fault
4. Ensure soft-start has completed

```c
// Check output status via PROFET diagnostics
if (PMU_PROFET_IsFault(0)) {
    printf("PROFET 0 in fault!\n");
    PMU_PROFET_ClearFault(0);
}
```

### 6.4 Incorrect Scaling

**Symptom:** Values seem wrong

**Debug steps:**
1. Read raw ADC value
2. Check min/max configuration
3. Verify calibration points

```c
// Read raw and scaled
int32_t raw = PMU_Channel_GetValue(0);
const PMU_Channel_t* ch = PMU_Channel_GetInfo(0);

printf("Raw: %ld, Range: %ld-%ld, Format: %d\n",
       raw, ch->min_value, ch->max_value, ch->format);
```

### 6.5 CAN Channel Timeout

**Symptom:** CAN input shows old/default value

**Solutions:**
1. Check CAN bus connection
2. Verify message ID and signal mapping
3. Extend timeout value
4. Check termination resistors

```c
// CAN diagnostic
extern uint32_t can_rx_count;
extern uint32_t can_error_count;

printf("CAN RX: %lu, Errors: %lu\n", can_rx_count, can_error_count);
```

---

## Next Steps

- [Logic Functions Integration](logic-functions-integration.md) - Use channels with logic functions
- [Channel API Reference](../api/channel-api.md) - Complete API documentation
- [Channel Examples](../examples/channel-examples.md) - More code examples

---

**Document Version:** 1.0
**Last Updated:** December 2024

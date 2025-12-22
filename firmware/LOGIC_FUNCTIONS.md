# PMU-30 Logic Functions & Lua Scripting

**Version**: 2.0
**Author**: R2 m-sport
**Date**: 2025-12-22

---

## Overview

The PMU-30 Logic Functions system provides powerful tools for creating complex control logic without recompiling firmware. Two approaches are supported:

1. **C API** - Register logic functions in firmware code
2. **Lua Scripting** - Dynamically create logic through scripts

Both systems work through the **Universal Channel Abstraction**, providing uniform access to all inputs and outputs.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Physical Layer                          │
│  ADC    PROFET    H-Bridge    CAN    Flash    Sensors       │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────────┐
│            Universal Channel Abstraction                     │
│  PMU_Channel_GetValue() / PMU_Channel_SetValue()            │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────┴─────────┐  ┌────────┴──────────┐
│ Logic Functions │  │   Lua Scripting    │
│   (C API)       │  │   (Dynamic)        │
└─────────────────┘  └───────────────────┘
```

---

## Logic Function Types

### Mathematical Operations (0x00-0x1F)

| Function | Description | Example |
|----------|-------------|---------|
| **ADD** | Sum of two inputs | `output = A + B` |
| **SUBTRACT** | Subtraction | `output = A - B` |
| **MULTIPLY** | Multiplication (fixed-point) | `output = (A * B) / 1000` |
| **DIVIDE** | Division | `output = (A * 1000) / B` |
| **MIN** | Minimum of N inputs | `output = min(A, B, C, ...)` |
| **MAX** | Maximum of N inputs | `output = max(A, B, C, ...)` |
| **AVERAGE** | Average value | `output = (A + B + ...) / N` |
| **ABS** | Absolute value | `output = |A|` |
| **SCALE** | Linear scaling | `output = (A * scale) + offset` |
| **CLAMP** | Range limiting | `output = clamp(A, min, max)` |

### Comparison Operations (0x20-0x3F)

| Function | Description | Result |
|----------|-------------|--------|
| **GREATER** | A > B | 1 or 0 |
| **LESS** | A < B | 1 or 0 |
| **EQUAL** | A == B | 1 or 0 |
| **NOT_EQUAL** | A != B | 1 or 0 |
| **GREATER_EQUAL** | A >= B | 1 or 0 |
| **LESS_EQUAL** | A <= B | 1 or 0 |
| **IN_RANGE** | min <= A <= max | 1 or 0 |

### Logical Operations (0x40-0x5F)

| Function | Description | Example |
|----------|-------------|---------|
| **AND** | Logical AND | All inputs != 0 |
| **OR** | Logical OR | At least one input != 0 |
| **NOT** | Logical NOT | Input inversion |
| **XOR** | Exclusive OR | Odd number of non-zero inputs |
| **NAND** | NOT-AND | Inversion of AND |
| **NOR** | NOT-OR | Inversion of OR |

### Special Logic Operations

| Function | Description | Parameters |
|----------|-------------|------------|
| **HYSTERESIS** | Schmitt trigger | upper_value, lower_value |
| **FLASH** | Blinking output | time_on_s, time_off_s |
| **PULSE** | One-shot pulse | pulse_duration_s |
| **TOGGLE** | Toggle on edge | trigger_channel |
| **SET_RESET_LATCH** | SR latch | set_channel, reset_channel |

### Tables (0x60-0x7F)

| Function | Description | Application |
|----------|-------------|-------------|
| **TABLE_1D** | 1D lookup with linear interpolation | Throttle curve, temperature compensation |
| **TABLE_2D** | 2D lookup (map) | Calibration maps, VE tables |

### Filters (0x80-0x9F)

| Function | Description | Application |
|----------|-------------|-------------|
| **MOVING_AVG** | Moving average | Noise suppression |
| **MIN_WINDOW** | Minimum over time window | Dip detection |
| **MAX_WINDOW** | Maximum over time window | Peak detection |
| **MEDIAN** | Median filter | Outlier removal |
| **LOW_PASS** | Low-pass filter (RC) | Signal smoothing |

### Control (0xA0-0xBF)

| Function | Description | Parameters |
|----------|-------------|------------|
| **PID** | PID controller | Kp, Ki, Kd, setpoint |
| **HYSTERESIS** | Hysteresis (Schmitt trigger) | threshold_on, threshold_off |
| **RATE_LIMIT** | Rate of change limiter | max_rate |
| **DEBOUNCE** | Debounce filter | debounce_ms |

---

## C API

### Initialization

```c
#include "pmu_logic_functions.h"
#include "pmu_channel.h"

// Initialize module
PMU_LogicFunctions_Init();
```

### Creating Functions

#### Simple Mathematical Operations

```c
// Example: Sum two pressure sensors
uint16_t brake_front = 0;   // Front brake channel
uint16_t brake_rear = 1;    // Rear brake channel
uint16_t brake_total = 200; // Virtual channel for sum

uint16_t func_id = PMU_LogicFunctions_CreateMath(
    PMU_FUNC_ADD,       // Operation type
    brake_total,        // Output channel
    brake_front,        // Input A
    brake_rear          // Input B
);
```

#### PID Controller

```c
// Example: Boost control via PID
uint16_t boost_sensor = 5;    // Pressure sensor
uint16_t wastegate = 105;     // Wastegate PWM output

uint16_t pid_id = PMU_LogicFunctions_CreatePID(
    wastegate,          // Output channel
    boost_sensor,       // Process variable (PV)
    1500,               // Setpoint (1.5 bar = 1500 mbar)
    2.0f,               // Kp (proportional gain)
    0.5f,               // Ki (integral gain)
    0.1f                // Kd (derivative gain)
);
```

#### Hysteresis (Cooling Fan)

```c
// Example: Fan with hysteresis
uint16_t temp_sensor = 10;    // Temperature sensor
uint16_t fan = 110;           // Fan relay

uint16_t hyst_id = PMU_LogicFunctions_CreateHysteresis(
    fan,                // Output channel
    temp_sensor,        // Input channel (temperature)
    85,                 // Turn ON at 85C
    75                  // Turn OFF at 75C
);
```

### Manual Registration

```c
// Create complex function manually
PMU_LogicFunction_t func = {0};
func.type = PMU_FUNC_TABLE_1D;
func.output_channel = 300;
func.input_channels[0] = 5;
func.input_count = 1;
func.enabled = 1;

// Configure table (e.g., throttle curve)
static int32_t throttle_x[] = {0, 250, 500, 750, 1000};
static int32_t throttle_y[] = {0, 100, 300, 600, 1000};

func.params.table_1d.size = 5;
func.params.table_1d.x_values = throttle_x;
func.params.table_1d.y_values = throttle_y;

PMU_LogicFunctions_Register(&func);
```

### Updating Functions

```c
// Call periodically (e.g., in main loop at 1 kHz)
void Control_Task(void) {
    PMU_LogicFunctions_Update();
}
```

---

## Lua API

### Script Initialization

```lua
-- Lua scripts automatically have access to PMU API
print("PMU-30 Lua Script Started")
```

### Channel Access

```lua
-- Read channel value
local rpm = channel.get(250)  -- Channel 250 = Engine RPM

-- Write value
channel.set(100, 1000)  -- Set channel 100 to 100%

-- Find channel by name
local brake_ch = channel.find("Brake_Pressure")
if brake_ch then
    local pressure = channel.get(brake_ch)
    print("Brake pressure: " .. pressure)
end

-- Get channel information
local info = channel.info(250)
if info then
    print("Name: " .. info.name)
    print("Min: " .. info.min .. ", Max: " .. info.max)
    print("Unit: " .. info.unit)
end
```

### Creating Logic Functions

```lua
-- Math operations
local power_ch = 200
local voltage_ch = 1000
local current_ch = 1001

-- P = V * I
local func_id = logic.multiply(power_ch, voltage_ch, current_ch)

-- Comparison
local oil_pressure = channel.find("Oil_Pressure")
local warning_led = channel.find("Oil_Warning")

-- Turn on LED if pressure < 20
logic.compare(warning_led, oil_pressure, 20, "<")

-- PID controller
local boost_sensor = channel.find("Boost_Pressure")
local wastegate = channel.find("Wastegate_PWM")

logic.pid(
    wastegate,      -- Output
    boost_sensor,   -- Input
    1500,           -- Setpoint (1.5 bar)
    2.0,            -- Kp
    0.5,            -- Ki
    0.1             -- Kd
)

-- Hysteresis
local temp = channel.find("Engine_Temp")
local fan = channel.find("Cooling_Fan")

logic.hysteresis(fan, temp, 85, 75)  -- ON=85C, OFF=75C
```

### System Functions

```lua
-- Get battery voltage
local voltage = system.voltage()
print("Battery: " .. voltage .. " mV")

-- Current consumption
local current = system.current()
print("Current: " .. current .. " mA")

-- MCU temperature
local temp = system.temperature()
print("MCU Temp: " .. temp .. " C")

-- Uptime
local uptime = system.uptime()
print("Uptime: " .. (uptime / 1000) .. " seconds")
```

### Utilities

```lua
-- Print to log
print("Hello from Lua!")

-- Get time in ms
local now = millis()

-- Delay
sleep(100)  -- 100 ms
```

---

## Practical Examples

### 1. Launch Control

```c
// C API version
void Setup_LaunchControl(void) {
    // Condition: RPM > 4000 AND speed < 5 km/h AND button pressed
    uint16_t rpm_ch = PMU_Channel_GetByName("Engine_RPM")->channel_id;
    uint16_t speed_ch = PMU_Channel_GetByName("Vehicle_Speed")->channel_id;
    uint16_t button_ch = PMU_Channel_GetByName("Launch_Button")->channel_id;
    uint16_t cut_ch = PMU_Channel_GetByName("Ignition_Cut")->channel_id;

    // RPM > 4000
    uint16_t rpm_high_ch = 301;
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_GREATER, rpm_high_ch, rpm_ch, 4000);

    // Speed < 5
    uint16_t speed_low_ch = 302;
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_LESS, speed_low_ch, speed_ch, 5);

    // AND all conditions
    PMU_LogicFunction_t and_func = {0};
    and_func.type = PMU_FUNC_AND;
    and_func.output_channel = cut_ch;
    and_func.input_channels[0] = rpm_high_ch;
    and_func.input_channels[1] = speed_low_ch;
    and_func.input_channels[2] = button_ch;
    and_func.input_count = 3;
    and_func.enabled = 1;

    PMU_LogicFunctions_Register(&and_func);
}
```

```lua
-- Lua version
function launch_control()
    local rpm = channel.get(channel.find("Engine_RPM"))
    local speed = channel.get(channel.find("Vehicle_Speed"))
    local button = channel.get(channel.find("Launch_Button"))
    local cut_ch = channel.find("Ignition_Cut")

    if button == 1 and speed < 5 and rpm > 4000 then
        channel.set(cut_ch, 1)  -- Cut ignition
    else
        channel.set(cut_ch, 0)
    end
end
```

### 2. Traction Control

```lua
function traction_control()
    -- Compare front and rear wheel speeds
    local fl = channel.get(channel.find("Wheel_FL"))
    local fr = channel.get(channel.find("Wheel_FR"))
    local rl = channel.get(channel.find("Wheel_RL"))
    local rr = channel.get(channel.find("Wheel_RR"))

    local front_avg = (fl + fr) / 2
    local rear_avg = (rl + rr) / 2

    -- If rear wheels are spinning (10% faster than front)
    if rear_avg > front_avg * 1.1 then
        -- Reduce power by 20%
        local throttle = channel.get(channel.find("Throttle"))
        channel.set(channel.find("Throttle_Output"), throttle * 0.8)

        -- Turn on indicator
        channel.set(channel.find("TC_Light"), 1)
    else
        -- No intervention
        local throttle = channel.get(channel.find("Throttle"))
        channel.set(channel.find("Throttle_Output"), throttle)
        channel.set(channel.find("TC_Light"), 0)
    end
end
```

### 3. Boost Control

```c
// PID controller for wastegate
void Setup_BoostControl(void) {
    uint16_t boost_sensor = 5;
    uint16_t wastegate = 105;

    // Target: 1.5 bar (1500 mbar)
    // Tuning: Kp=2.0, Ki=0.5, Kd=0.1
    uint16_t pid_id = PMU_LogicFunctions_CreatePID(
        wastegate, boost_sensor,
        1500,  // Setpoint
        2.0f,  // Kp
        0.5f,  // Ki
        0.1f   // Kd
    );
}
```

### 4. Cooling Fan Control

```c
// Hysteresis: ON=85C, OFF=75C
void Setup_FanControl(void) {
    uint16_t temp = 10;
    uint16_t fan = 110;

    PMU_LogicFunctions_CreateHysteresis(fan, temp, 85, 75);
}
```

---

## Best Practices

### 1. Channel Naming
Use meaningful names for easy Lua integration:

```c
// Good
PMU_Channel_t ch = {
    .channel_id = 0,
    .name = "Brake_Pressure_Front",
    ...
};

// Bad
PMU_Channel_t ch = {
    .channel_id = 0,
    .name = "CH0",
    ...
};
```

### 2. Virtual Channels for Intermediate Results

```lua
-- Use virtual channels (200-999) for intermediate calculations
local rpm_limit_ch = 300
logic.compare(rpm_limit_ch, rpm_ch, 9000, ">")

local speed_ok_ch = 301
logic.compare(speed_ok_ch, speed_ch, 5, "<")

-- Then combine results
logic.and(cut_ch, rpm_limit_ch, speed_ok_ch, button_ch)
```

### 3. Error Handling in Lua

```lua
function safe_channel_access()
    local ch = channel.find("Some_Channel")
    if ch then
        local value = channel.get(ch)
        -- Use value
    else
        print("ERROR: Channel not found")
    end
end
```

### 4. Performance Optimization

- Use C API for time-critical functions
- Use Lua scripts for configurable logic
- Avoid heavy computations in every cycle

---

## Performance Considerations

- **C API**: Execution ~2-5 us per function
- **Lua API**: Execution ~50-200 us per call
- **Recommended update rate**: 100-1000 Hz (500 Hz typical)
- **Maximum functions**: 100 simultaneous

---

## Troubleshooting

### Function Not Executing
- Check `func->enabled == 1`
- Ensure `PMU_LogicFunctions_Update()` is called periodically
- Verify channel IDs are correct

### Lua Script Not Working
- Check syntax via `PMU_Lua_LoadScript()`
- Ensure script is registered and enabled
- Check error log via `PMU_Lua_GetStats()`

### Incorrect Values
- Check channel formats (RAW, PERCENT, VOLTAGE, etc.)
- Verify scaling is correct
- Check min/max ranges

---

## See Also

- [JSON_CONFIG.md](JSON_CONFIG.md) - JSON configuration format
- [examples/lua_examples.lua](examples/lua_examples.lua) - Lua script examples
- [examples/config_examples.json](examples/config_examples.json) - Configuration examples

---

**Copyright 2025 R2 m-sport. All rights reserved.**

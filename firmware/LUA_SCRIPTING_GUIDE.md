# PMU-30 Lua Scripting Guide

**Version**: 1.0
**Date**: 2025-12-21
**Author**: R2 m-sport

## Overview

The PMU-30 firmware includes an embedded Lua 5.4 scripting engine that allows you to create custom logic without recompiling the firmware. This provides ultimate flexibility for race applications, prototyping, and custom integrations.

---

## Features

- **Embedded Lua 5.4** - Full scripting capabilities
- **Real-time execution** - Scripts run at 100Hz-500Hz
- **PMU API access** - Control all PMU functions from Lua
- **Multiple scripts** - Up to 8 concurrent scripts
- **Sandboxing** - Safe execution with timeout protection
- **Persistent storage** - Scripts stored in flash/SD card
- **Hot reload** - Update scripts without reboot

---

## Getting Started

### 1. Basic Script Structure

```lua
-- Simple LED blink script

function main()
    -- Read input
    local button = getInput(0)

    -- Control output
    if button > 2048 then
        setOutput(5, 1, 0)  -- Turn ON channel 5
    else
        setOutput(5, 0, 0)  -- Turn OFF channel 5
    end
end

-- Auto-execute
main()
```

### 2. Loading Scripts

**Method 1: Via Configuration Tool**
```
1. Open PMU Configurator
2. Go to Scripts tab
3. Click "Load Script"
4. Select .lua file
5. Click "Upload to PMU"
```

**Method 2: Via SD Card** (if enabled)
```
1. Copy .lua files to SD card /scripts/ folder
2. Insert SD card
3. Scripts auto-load on boot
```

**Method 3: Programmatically** (C API)
```c
const char* script = "setOutput(0, 1, 0)";
PMU_Lua_LoadScript("my_script", script, strlen(script));
PMU_Lua_ExecuteScript("my_script");
```

---

## PMU Lua API Reference

### Input/Output Functions

#### `getInput(channel)`
Read analog input value (ADC).

**Parameters:**
- `channel` (number): ADC channel (0-19)

**Returns:**
- `value` (number): 12-bit ADC value (0-4095)

**Example:**
```lua
local pot_value = getInput(0)  -- Read potentiometer
if pot_value > 2048 then
    log("Pot above 50%")
end
```

---

#### `setOutput(channel, state, pwm)`
Control output channel.

**Parameters:**
- `channel` (number): Output channel (0-29)
- `state` (number): 0=OFF, 1=ON
- `pwm` (number): PWM duty cycle 0-100% (optional)

**Example:**
```lua
setOutput(5, 1, 0)     -- Turn on channel 5
setOutput(10, 1, 75)   -- Channel 10 at 75% PWM
setOutput(15, 0, 0)    -- Turn off channel 15
```

---

#### `getVirtual(channel)`
Read virtual channel value.

**Parameters:**
- `channel` (number): Virtual channel (0-255)

**Returns:**
- `value` (number): 32-bit signed integer

**Example:**
```lua
local counter = getVirtual(0)
local can_rpm = getVirtual(100)  -- CAN signal mapped to virtual channel
```

---

#### `setVirtual(channel, value)`
Write virtual channel value.

**Parameters:**
- `channel` (number): Virtual channel (0-255)
- `value` (number): Value to write

**Example:**
```lua
-- Use virtual channels as variables
setVirtual(0, counter + 1)
setVirtual(50, rpm / 100)  -- Store calculated value
```

---

### System Functions

#### `getVoltage()`
Get battery voltage.

**Returns:**
- `voltage` (number): Voltage in millivolts

**Example:**
```lua
local voltage = getVoltage()
if voltage < 11000 then
    log("Low battery: " .. voltage .. "mV")
end
```

---

#### `getTemperature()`
Get board temperature.

**Returns:**
- `temp` (number): Temperature in °C

**Example:**
```lua
local temp = getTemperature()
if temp > 70 then
    setOutput(FAN_OUTPUT, 1, 100)  -- Full fan speed
end
```

---

#### `log(message)`
Send log message to console.

**Parameters:**
- `message` (string): Message to log

**Example:**
```lua
log("Script started")
log("Value: " .. tostring(value))
```

---

#### `delay(milliseconds)`
Delay execution (use sparingly!).

**Parameters:**
- `milliseconds` (number): Delay time

**Warning:** Long delays will block execution. Use virtual channels for timing instead.

**Example:**
```lua
-- BAD - blocks system
delay(1000)

-- GOOD - use counter
local count = getVirtual(TIMER_CH)
if count >= 100 then  -- 1 second at 100Hz
    -- Do something
    setVirtual(TIMER_CH, 0)
else
    setVirtual(TIMER_CH, count + 1)
end
```

---

### CAN Functions

#### `sendCAN(bus, id, data)`
Send CAN message.

**Parameters:**
- `bus` (number): CAN bus (1-4)
- `id` (number): CAN ID (11-bit or 29-bit)
- `data` (string): Data bytes (max 64 for CAN FD)

**Example:**
```lua
-- Send 8-byte CAN message
local data = string.char(0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08)
sendCAN(1, 0x123, data)
```

---

## Example Scripts

### Example 1: Button Counter

```lua
-- Count button presses

local IN_BUTTON = 0
local OUT_LED = 5
local VIRT_COUNT = 0
local VIRT_LAST_STATE = 1

function main()
    local button = getInput(IN_BUTTON)
    local last_state = getVirtual(VIRT_LAST_STATE)

    -- Detect rising edge
    if button > 2048 and last_state == 0 then
        -- Button just pressed
        local count = getVirtual(VIRT_COUNT)
        count = count + 1
        setVirtual(VIRT_COUNT, count)

        log("Button pressed " .. count .. " times")

        -- Blink LED
        setOutput(OUT_LED, 1, 0)
    elseif button < 2048 then
        setOutput(OUT_LED, 0, 0)
    end

    -- Store state
    setVirtual(VIRT_LAST_STATE, button > 2048 and 1 or 0)
end

main()
```

### Example 2: Temperature-Based Fan Control

```lua
-- Automatic fan control based on temperature

local OUT_FAN = 10
local TEMP_THRESHOLD_LOW = 60   -- °C
local TEMP_THRESHOLD_HIGH = 80  -- °C

function control_fan()
    local temp = getTemperature()

    local pwm = 0

    if temp > TEMP_THRESHOLD_HIGH then
        pwm = 100  -- Full speed
    elseif temp > TEMP_THRESHOLD_LOW then
        -- Linear ramp
        pwm = ((temp - TEMP_THRESHOLD_LOW) * 100) /
              (TEMP_THRESHOLD_HIGH - TEMP_THRESHOLD_LOW)
    end

    setOutput(OUT_FAN, pwm > 0 and 1 or 0, pwm)
end

control_fan()
```

### Example 3: Sequential Start-up

```lua
-- Sequential power-up of components

local VIRT_STATE = 0
local VIRT_TIMER = 1

local STATE_IDLE = 0
local STATE_FUEL_PUMP = 1
local STATE_IGNITION = 2
local STATE_RUNNING = 3

function startup_sequence()
    local state = getVirtual(VIRT_STATE)
    local timer = getVirtual(VIRT_TIMER)

    if state == STATE_IDLE then
        -- Check start button
        if getInput(0) > 2048 then
            setVirtual(VIRT_STATE, STATE_FUEL_PUMP)
            setVirtual(VIRT_TIMER, 0)
        end

    elseif state == STATE_FUEL_PUMP then
        -- Turn on fuel pump
        setOutput(0, 1, 0)

        timer = timer + 1
        setVirtual(VIRT_TIMER, timer)

        if timer > 50 then  -- 500ms at 100Hz
            setVirtual(VIRT_STATE, STATE_IGNITION)
            setVirtual(VIRT_TIMER, 0)
        end

    elseif state == STATE_IGNITION then
        -- Turn on ignition
        setOutput(1, 1, 0)

        timer = timer + 1
        setVirtual(VIRT_TIMER, timer)

        if timer > 20 then  -- 200ms
            setVirtual(VIRT_STATE, STATE_RUNNING)
        end

    elseif state == STATE_RUNNING then
        -- Normal operation
        -- Both fuel pump and ignition stay on
    end
end

startup_sequence()
```

---

## Best Practices

### 1. Use Virtual Channels for State

❌ **Don't use global variables:**
```lua
-- BAD - global state lost between calls
counter = counter + 1
```

✅ **Use virtual channels:**
```lua
-- GOOD - persistent state
local counter = getVirtual(VIRT_COUNTER)
setVirtual(VIRT_COUNTER, counter + 1)
```

### 2. Avoid Long Delays

❌ **Don't block execution:**
```lua
-- BAD - blocks for 1 second
delay(1000)
```

✅ **Use counter-based timing:**
```lua
-- GOOD - non-blocking
local ticks = getVirtual(TIMER)
if ticks >= 100 then  -- 1 second at 100Hz
    -- Do periodic task
    setVirtual(TIMER, 0)
else
    setVirtual(TIMER, ticks + 1)
end
```

### 3. Minimize Execution Time

- Keep scripts under 10ms execution time
- Avoid complex calculations in tight loops
- Use lookup tables instead of math functions
- Profile with execution statistics

### 4. Error Handling

```lua
-- Check return values
local value = getInput(channel)
if value == nil then
    log("Error reading input")
    return
end

-- Validate ranges
if channel < 0 or channel > 29 then
    log("Invalid channel: " .. channel)
    return
end
```

### 5. Debugging

```lua
-- Add debug logging
log("State: " .. state .. ", Timer: " .. timer)

-- Use virtual channels to expose internal state
setVirtual(DEBUG_STATE, state)
setVirtual(DEBUG_VALUE, calculated_value)
```

---

## Performance Considerations

### Execution Timing

- Scripts execute at **100Hz-500Hz** (10ms-2ms period)
- Maximum execution time: **10ms per cycle**
- Timeout after 10ms prevents system lockup
- Use `PMU_Lua_GetStats()` to monitor performance

### Memory Usage

- Total Lua memory: **128KB**
- Max script size: **32KB**
- Max scripts: **8 concurrent**
- Automatic garbage collection

### Optimization Tips

1. **Cache function results:**
```lua
-- BAD - called 3 times
if getInput(0) > 1000 and getInput(0) < 3000 then
    setOutput(5, getInput(0) / 100, 0)
end

-- GOOD - called once
local input = getInput(0)
if input > 1000 and input < 3000 then
    setOutput(5, input / 100, 0)
end
```

2. **Use local variables:**
```lua
-- GOOD - faster access
local temp = getTemperature()
local voltage = getVoltage()
```

3. **Avoid string concatenation in loops:**
```lua
-- BAD
for i = 1, 100 do
    msg = msg .. tostring(i)
end

-- GOOD
local parts = {}
for i = 1, 100 do
    parts[#parts + 1] = tostring(i)
end
msg = table.concat(parts)
```

---

## Safety and Sandboxing

### Restricted Functions

For safety, some Lua standard library functions are disabled:
- `io.*` - File I/O (use PMU API instead)
- `os.execute` - System commands
- `load`, `loadfile` - Dynamic code loading
- `dofile` - File execution

### Timeout Protection

Scripts are automatically terminated after 10ms to prevent:
- Infinite loops
- System lockup
- Missed real-time deadlines

### Fault Isolation

- Each script runs in isolated environment
- Script errors don't crash the system
- Failed scripts can be disabled automatically

---

## Integration with Configuration Tool

### Script Management UI

The PMU Configurator provides:
- **Script editor** with syntax highlighting
- **Live testing** - execute scripts in real-time
- **Variable watch** - monitor virtual channels
- **Performance profiler** - execution time graph
- **Error console** - see script errors

### Auto-Run Configuration

Scripts can be configured to:
- **Auto-load** on boot
- **Auto-execute** periodically
- **Manual trigger** only
- **Conditional execution** based on system state

---

## Troubleshooting

### Common Errors

**1. "Script too large"**
- Reduce script size below 32KB
- Split into multiple scripts
- Remove unused code

**2. "Execution timeout"**
- Reduce loop iterations
- Remove delay() calls
- Optimize calculations

**3. "Memory error"**
- Reduce number of scripts
- Clear unused variables
- Avoid large string operations

**4. "Syntax error"**
- Check Lua syntax
- Use online Lua validator
- Check for missing `end` statements

### Debug Checklist

1. ✅ Check script syntax with Lua validator
2. ✅ Verify channel numbers are in range
3. ✅ Monitor execution time statistics
4. ✅ Add log() statements for debugging
5. ✅ Test in simulator before deploying

---

## Advanced Topics

### Custom Functions

You can register custom C functions from firmware:

```c
// In firmware
static int my_custom_function(lua_State* L) {
    int arg = luaL_checkinteger(L, 1);
    // Do something
    lua_pushinteger(L, result);
    return 1;
}

PMU_Lua_RegisterFunction("myFunction", my_custom_function);
```

```lua
-- In Lua script
local result = myFunction(42)
```

### Integrating with Logic Functions

Lua scripts can work alongside C logic functions:

```c
// C logic function
PMU_LogicFunc_t my_logic = {
    .type = PMU_LOGIC_TYPE_CUSTOM,
    .enabled = 1,
    // Call Lua script
    .custom_func = execute_lua_logic
};
```

---

## Examples Repository

Full examples available in:
- `firmware/scripts/example_basic.lua`
- `firmware/scripts/example_pwm_control.lua`
- `firmware/scripts/example_state_machine.lua`
- `firmware/scripts/example_can_processing.lua`

---

## API Summary

| Function | Description | Returns |
|----------|-------------|---------|
| `getInput(ch)` | Read ADC input | 0-4095 |
| `setOutput(ch, state, pwm)` | Control output | - |
| `getVirtual(ch)` | Read virtual channel | number |
| `setVirtual(ch, val)` | Write virtual channel | - |
| `getVoltage()` | Battery voltage | mV |
| `getTemperature()` | Board temperature | °C |
| `log(msg)` | Log message | - |
| `delay(ms)` | Delay (avoid!) | - |
| `sendCAN(bus, id, data)` | Send CAN message | - |

---

## Support

For questions and support:
- GitHub Issues: https://github.com/r2-msport/pmu30
- Documentation: https://docs.pmu30.com
- Forum: https://forum.pmu30.com

---

**Happy Scripting!** 🚀

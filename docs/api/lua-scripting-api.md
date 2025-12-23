# Lua Scripting API Reference

PMU-30 supports Lua 5.4 scripting for custom logic, automation, and advanced control scenarios.

## Table of Contents

- [Overview](#overview)
- [Channel API](#channel-api)
- [Logic API](#logic-api)
- [System API](#system-api)
- [Utility Functions](#utility-functions)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Limitations](#limitations)

---

## Overview

Lua scripts in PMU-30 have access to the universal channel system, allowing them to:
- Read any channel value (inputs, outputs, logic results)
- Write to output channels
- Create dynamic logic functions
- Access system information (voltage, temperature, uptime)
- Send CAN messages

### Script Lifecycle

1. **Loading** - Script is parsed and compiled
2. **Execution** - Script runs when triggered (auto-run or manual)
3. **Update** - Auto-run scripts execute periodically in the main loop

---

## Channel API

The `channel` table provides access to the universal channel system.

### channel.get(channel_id)

Get the current value of a channel.

```lua
-- By channel ID
local value = channel.get(0)

-- Get input voltage (scaled)
local voltage = channel.get(10)
```

**Parameters:**
- `channel_id` (number) - Channel ID (0-based)

**Returns:** Channel value (integer)

---

### channel.set(channel_id, value)

Set a channel value. Only works for writable channels (outputs, logic).

```lua
-- Turn on output
channel.set(0, 1)

-- Set PWM duty (0-1000 = 0-100%)
channel.set(5, 750)  -- 75% duty
```

**Parameters:**
- `channel_id` (number) - Channel ID
- `value` (number) - Value to set

**Returns:** `true` on success, `false` on failure

---

### channel.find(name)

Find a channel by its name.

```lua
local ch_id = channel.find("Headlights")
if ch_id then
    channel.set(ch_id, 1)
end
```

**Parameters:**
- `name` (string) - Channel name

**Returns:** Channel ID or `nil` if not found

---

### channel.info(channel_id)

Get detailed information about a channel.

```lua
local info = channel.info(0)
print("Name: " .. info.name)
print("Type: " .. info.type)
print("Value: " .. info.value)
print("Min: " .. info.min)
print("Max: " .. info.max)
```

**Returns:** Table with fields:
- `id` - Channel ID
- `name` - Channel name
- `type` - Channel type (number)
- `value` - Current value
- `min` - Minimum value
- `max` - Maximum value
- `unit` - Unit string

---

### channel.list()

Get a list of all channels.

```lua
local channels = channel.list()
for i, ch in ipairs(channels) do
    print(ch.name .. " = " .. ch.value)
end
```

**Returns:** Array of channel info tables

---

## Shorthand Functions

For convenience, global functions are available:

### getChannel(id_or_name)

```lua
-- By ID
local val = getChannel(0)

-- By name
local val = getChannel("Headlights")
```

### setChannel(id_or_name, value)

```lua
-- By ID
setChannel(0, 1)

-- By name
setChannel("Headlights", 1)
```

### getInput(channel)

Get raw ADC input value.

```lua
local adc_value = getInput(0)  -- 0-4095
```

### setOutput(channel, state)

Set output on/off state.

```lua
setOutput(0, 1)  -- Turn on
setOutput(0, 0)  -- Turn off
```

---

## Logic API

The `logic` table allows creating dynamic logic functions at runtime.

### logic.add(output, input_a, input_b)

Create an addition function: `output = input_a + input_b`

```lua
local func_id = logic.add(10, 0, 1)
```

### logic.subtract(output, input_a, input_b)

Create a subtraction function: `output = input_a - input_b`

### logic.multiply(output, input_a, input_b)

Create a multiplication function: `output = input_a * input_b`

### logic.divide(output, input_a, input_b)

Create a division function: `output = input_a / input_b`

### logic.compare(output, input_a, input_b, operator)

Create a comparison function.

```lua
-- output = 1 if input_a > input_b, else 0
local func_id = logic.compare(10, 0, 1, ">")
```

**Operators:** `>`, `<`, `==`, `!=`, `>=`, `<=`

### logic.pid(output, input, setpoint, kp, ki, kd)

Create a PID controller.

```lua
-- Temperature control
local pid = logic.pid(
    5,      -- Output channel (heater PWM)
    2,      -- Input channel (temperature sensor)
    50.0,   -- Setpoint (50 degrees)
    1.0,    -- Kp
    0.1,    -- Ki
    0.05    -- Kd
)
```

### logic.hysteresis(output, input, on_threshold, off_threshold)

Create a hysteresis function (on/off with deadband).

```lua
-- Fan control: on when temp > 60, off when temp < 50
local hyst = logic.hysteresis(5, 2, 60, 50)
```

### logic.enable(func_id, enabled)

Enable or disable a logic function.

```lua
logic.enable(func_id, false)  -- Disable
logic.enable(func_id, true)   -- Enable
```

---

## System API

The `system` table provides access to system information.

### system.voltage()

Get battery voltage in millivolts.

```lua
local voltage_mv = system.voltage()
print("Battery: " .. (voltage_mv / 1000) .. "V")
```

### system.current()

Get total system current in milliamps.

```lua
local current_ma = system.current()
```

### system.temperature()

Get MCU temperature in degrees Celsius.

```lua
local temp = system.temperature()
if temp > 80 then
    log("Warning: High temperature!")
end
```

### system.uptime()

Get system uptime in milliseconds.

```lua
local uptime = system.uptime()
```

---

## Utility Functions

### log(message)

Output a log message.

```lua
log("Script started")
log("Value: " .. value)
```

### print(message)

Alias for `log()`.

### millis()

Get current tick count in milliseconds.

```lua
local start = millis()
-- ... do something ...
local elapsed = millis() - start
log("Took " .. elapsed .. " ms")
```

### delay(ms) / sleep(ms)

Pause script execution.

```lua
delay(100)  -- Wait 100ms
sleep(500)  -- Wait 500ms
```

**Warning:** Blocking delays should be used sparingly as they pause the entire control loop.

---

## CAN Functions

### sendCAN(bus, id, data)

Send a CAN message.

```lua
-- Send 4 bytes on bus 0
sendCAN(0, 0x100, string.char(0x01, 0x02, 0x03, 0x04))

-- Using table (Lua 5.4)
local data = {0x01, 0x02, 0x03, 0x04}
sendCAN(0, 0x200, string.char(table.unpack(data)))
```

**Parameters:**
- `bus` (number) - CAN bus index (0-3)
- `id` (number) - CAN message ID
- `data` (string) - Data bytes (max 8 for CAN 2.0, 64 for CAN FD)

---

## Examples

### Basic Output Control

```lua
-- Turn on headlights when ignition is on
function update()
    local ignition = channel.get(0)  -- Digital input
    channel.set(10, ignition)        -- Headlight output
end
```

### Temperature-Based Fan Control

```lua
local FAN_ON_TEMP = 60
local FAN_OFF_TEMP = 50

function update()
    local temp = channel.get(2)  -- Temperature sensor
    local fan = channel.get(5)   -- Current fan state

    if temp > FAN_ON_TEMP then
        channel.set(5, 1)
    elseif temp < FAN_OFF_TEMP then
        channel.set(5, 0)
    end
end
```

### PWM Dimming

```lua
-- Smooth PWM ramp
function dimmer(channel_id, target, step)
    local current = channel.get(channel_id)

    if current < target then
        channel.set(channel_id, math.min(current + step, target))
    elseif current > target then
        channel.set(channel_id, math.max(current - step, target))
    end
end

function update()
    local switch = channel.get(0)
    local target = switch == 1 and 1000 or 0
    dimmer(5, target, 10)
end
```

### CAN Message Response

```lua
-- Send status when requested
function update()
    local voltage = system.voltage()
    local temp = system.temperature()

    -- Pack into CAN message
    local data = string.char(
        voltage % 256,
        math.floor(voltage / 256),
        temp % 256,
        math.floor(temp / 256)
    )

    sendCAN(0, 0x100, data)
end
```

---

## Best Practices

1. **Keep scripts short** - Long-running scripts block the control loop
2. **Avoid blocking delays** - Use state machines instead of `delay()`
3. **Cache channel lookups** - Use `channel.find()` once at startup
4. **Handle errors** - Check for `nil` returns from `channel.find()`
5. **Use meaningful names** - Name your channels descriptively

### State Machine Pattern

```lua
local state = "idle"
local timer = 0

function update()
    local now = millis()

    if state == "idle" then
        if channel.get(0) == 1 then
            state = "active"
            timer = now
            channel.set(5, 1)
        end
    elseif state == "active" then
        if now - timer > 5000 then  -- 5 second timeout
            state = "idle"
            channel.set(5, 0)
        end
    end
end
```

---

## Limitations

- **Memory**: Scripts share a limited memory pool (configurable, default 64KB)
- **Execution time**: Maximum execution time per call (default 100ms)
- **No file I/O**: Scripts cannot access the filesystem
- **No network**: No direct network access (use CAN for communication)
- **Single-threaded**: Scripts run in the main control loop

---

## Migration from Legacy API

If you have scripts using the old `setVirtual`/`getVirtual` functions, update them:

| Old API | New API |
|---------|---------|
| `pmu.getVirtual(ch)` | `channel.get(ch)` or `getChannel(ch)` |
| `pmu.setVirtual(ch, val)` | `channel.set(ch, val)` or `setChannel(ch, val)` |
| `pmu.getInput(ch)` | `getInput(ch)` or `channel.get(ch)` |
| `pmu.setOutput(ch, val)` | `setOutput(ch, val)` or `channel.set(ch, val)` |

The new unified channel system treats all channels (inputs, outputs, logic) uniformly.

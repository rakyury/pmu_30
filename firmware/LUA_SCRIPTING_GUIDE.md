# Lua Scripting Guide for PMU 30

## Overview

This guide provides documentation for scripting the PMU 30 using Lua. The scripting interface allows you to automate measurements, control device operation, and process data in real-time.

## Channel System

The PMU 30 uses a unified channel system where all measurement channels are treated uniformly. Channels are identified by a channel number and can be accessed through the scripting interface.

### Channel Identification

All channels in the system are accessed using a consistent interface:

```lua
-- Access channel by number
local channel = pmu.channel(1)
```

### Channel Types

The unified channel system supports various measurement types:

- **Voltage Channels**: Measure voltage across components
- **Current Channels**: Measure current through components
- **Temperature Channels**: Measure temperature sensors
- **Custom Channels**: User-defined measurement channels

All channels follow the same access patterns and methods regardless of their measurement type.

## Core API Reference

### Channel Operations

#### Getting a Channel

```lua
local channel = pmu.channel(channel_number)
```

Returns a channel object for the specified channel number.

#### Channel Methods

**Enable/Disable Channel**
```lua
channel:enable()
channel:disable()
```

**Set Range**
```lua
channel:set_range(range_value)
```

**Read Value**
```lua
channel:read()
```

Returns the current measured value from the channel.

**Get Channel Information**
```lua
channel:get_info()
```

Returns a table containing channel metadata including name, type, and range.

### Measurement Configuration

All channels support the same configuration methods:

```lua
-- Configure measurement for all channel types
channel:set_range(10)      -- Set measurement range
channel:set_rate(1000)     -- Set sampling rate in Hz
channel:enable()           -- Enable the channel
```

## Common Usage Patterns

### Basic Measurement Loop

```lua
-- Initialize a channel
local ch1 = pmu.channel(1)
ch1:enable()
ch1:set_range(10)

-- Read measurements in a loop
for i = 1, 100 do
    local value = ch1:read()
    print("Channel 1 value: " .. value)
end

-- Disable when done
ch1:disable()
```

### Multiple Channel Monitoring

```lua
-- Initialize multiple channels
local channels = {}
for i = 1, 4 do
    channels[i] = pmu.channel(i)
    channels[i]:enable()
end

-- Read all channels
for i = 1, 4 do
    local value = channels[i]:read()
    print("Channel " .. i .. ": " .. value)
end

-- Cleanup
for i = 1, 4 do
    channels[i]:disable()
end
```

### Conditional Measurement

```lua
local ch1 = pmu.channel(1)
ch1:enable()

if ch1:get_info().enabled then
    local value = ch1:read()
    if value > 5.0 then
        print("Warning: High value detected")
    end
end
```

## Error Handling

The scripting interface provides error feedback for invalid operations:

```lua
local status, result = pcall(function()
    local ch = pmu.channel(1)
    ch:read()
    return result
end)

if not status then
    print("Error: " .. result)
end
```

## Advanced Topics

### Channel Synchronization

Synchronize measurements across multiple channels:

```lua
local channels = {}
for i = 1, 4 do
    channels[i] = pmu.channel(i)
    channels[i]:enable()
    channels[i]:set_rate(1000)
end

-- All channels now sample at the same rate
```

### Data Logging

Log channel data to memory:

```lua
local ch1 = pmu.channel(1)
local data = {}

ch1:enable()
for i = 1, 1000 do
    table.insert(data, ch1:read())
end
ch1:disable()

-- Process logged data
local sum = 0
for _, value in ipairs(data) do
    sum = sum + value
end
local average = sum / #data
print("Average: " .. average)
```

## Limitations and Constraints

- Maximum number of active channels is limited by hardware
- Sampling rates are constrained by the device's ADC capabilities
- Channel ranges must be selected from available hardware ranges
- Lua script execution has a maximum timeout to prevent device lockup

## Troubleshooting

### Channel Not Responding

Ensure the channel is enabled:
```lua
local ch = pmu.channel(1)
if not ch:get_info().enabled then
    ch:enable()
end
```

### Invalid Range Error

Use only supported ranges for your measurement type:
```lua
local ch = pmu.channel(1)
ch:set_range(10)  -- Adjust to match your measurement requirements
```

### Script Timeout

Reduce the complexity of your script or add periodic delays:
```lua
for i = 1, 10000 do
    pmu.delay(1)  -- Add 1ms delay
    -- Do measurement work
end
```

## Best Practices

1. Always disable channels when measurements are complete
2. Use appropriate ranges for your measurements to maximize accuracy
3. Enable error handling for robust scripts
4. Test scripts with small datasets before running long operations
5. Use synchronization for correlated measurements
6. Document complex measurement sequences with comments

## Support and Additional Resources

For additional information about the PMU 30 device, refer to the main hardware documentation or contact support.

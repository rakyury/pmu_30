# PMU-30 Universal Channel Abstraction

**Version**: 1.0
**Author**: R2 m-sport
**Date**: 2025-12-21

---

## Overview

The Universal Channel Abstraction provides a unified API for working with all types of PMU-30 inputs and outputs, regardless of their physical or virtual nature.

### Key Benefits

- **Unified Interface**: `PMU_Channel_GetValue()` and `PMU_Channel_SetValue()` for all channel types
- **Automatic Routing**: The system automatically determines which driver to use
- **Virtual Channels**: Support for calculated values, CAN, functions, tables
- **Name Lookup**: Access channels by symbolic name
- **Metadata**: Each channel contains information about type, range, units

---

## Channel Types

### Physical Inputs (0x00-0x1F)

| Type | Code | Description | Example |
|------|------|-------------|---------|
| `PMU_CHANNEL_INPUT_ANALOG` | 0x00 | Analog input (0-5V) | Pressure sensor |
| `PMU_CHANNEL_INPUT_DIGITAL` | 0x01 | Digital input (on/off) | Door switch |
| `PMU_CHANNEL_INPUT_SWITCH` | 0x02 | Switch | Steering wheel toggle |
| `PMU_CHANNEL_INPUT_ROTARY` | 0x03 | Rotary switch | Multi-position selector |
| `PMU_CHANNEL_INPUT_FREQUENCY` | 0x04 | Frequency input | Speed sensor |

### Virtual Inputs (0x20-0x3F)

| Type | Code | Description | Example |
|------|------|-------------|---------|
| `PMU_CHANNEL_INPUT_CAN` | 0x20 | CAN bus input | Engine RPM from ECU |
| `PMU_CHANNEL_INPUT_CALCULATED` | 0x21 | Calculated value | Power (V × I) |
| `PMU_CHANNEL_INPUT_SYSTEM` | 0x22 | System value | Battery voltage |

### Physical Outputs (0x40-0x5F)

| Type | Code | Description | Example |
|------|------|-------------|---------|
| `PMU_CHANNEL_OUTPUT_POWER` | 0x40 | Power output (PROFET) | Fuel pump relay |
| `PMU_CHANNEL_OUTPUT_PWM` | 0x41 | PWM output | Fan control |
| `PMU_CHANNEL_OUTPUT_HBRIDGE` | 0x42 | H-bridge | Power window |
| `PMU_CHANNEL_OUTPUT_ANALOG` | 0x43 | Analog output (DAC) | 0-10V control |

### Virtual Outputs (0x60-0x7F)

| Type | Code | Description | Example |
|------|------|-------------|---------|
| `PMU_CHANNEL_OUTPUT_FUNCTION` | 0x60 | Logic function | AND/OR/NOT |
| `PMU_CHANNEL_OUTPUT_TABLE` | 0x61 | Lookup table | Throttle curve |
| `PMU_CHANNEL_OUTPUT_ENUM` | 0x62 | Enumeration | Operating mode (1=OFF, 2=ON, 3=AUTO) |
| `PMU_CHANNEL_OUTPUT_NUMBER` | 0x63 | Constant | Regulator setpoint |
| `PMU_CHANNEL_OUTPUT_CAN` | 0x64 | CAN output | Send temperature to display |
| `PMU_CHANNEL_OUTPUT_PID` | 0x65 | PID controller | Temperature controller |

---

## Channel ID Ranges

```
0-99:      Physical inputs (ADC 0-19)
100-199:   Physical outputs (PROFET 0-29, H-bridge 0-3)
200-999:   Virtual channels (CAN, functions, tables)
1000-1023: System channels (voltage, temperature, uptime)
```

### Predefined System Channels

| ID | Name | Description | Units |
|----|------|-------------|-------|
| 1000 | Battery Voltage | Battery voltage | mV |
| 1001 | Total Current | Total current consumption | mA |
| 1002 | MCU Temperature | MCU temperature | °C |
| 1003 | Board Temperature | Board temperature | °C |
| 1004 | System Uptime | Operating time | seconds |

---

## Value Formats

| Format | Description | Range |
|--------|-------------|-------|
| `PMU_CHANNEL_FORMAT_RAW` | Raw ADC/PWM value | 0-1023 |
| `PMU_CHANNEL_FORMAT_PERCENT` | Percentage | 0-1000 (0.0-100.0%) |
| `PMU_CHANNEL_FORMAT_VOLTAGE` | Voltage | mV |
| `PMU_CHANNEL_FORMAT_CURRENT` | Current | mA |
| `PMU_CHANNEL_FORMAT_BOOLEAN` | Boolean | 0/1 |
| `PMU_CHANNEL_FORMAT_ENUM` | Enumeration | 0-255 |
| `PMU_CHANNEL_FORMAT_SIGNED` | Signed | -32768 to +32767 |

---

## API Reference

### Initialization

```c
// Initialize channel system
HAL_StatusTypeDef PMU_Channel_Init(void);

// Register a new channel
PMU_Channel_t channel = {
    .channel_id = 0,
    .type = PMU_CHANNEL_INPUT_ANALOG,
    .direction = PMU_CHANNEL_DIR_INPUT,
    .format = PMU_CHANNEL_FORMAT_RAW,
    .physical_index = 0,  // ADC channel 0
    .flags = PMU_CHANNEL_FLAG_ENABLED,
    .min_value = 0,
    .max_value = 1023,
    .name = "Brake Pressure",
    .unit = "bar"
};
PMU_Channel_Register(&channel);
```

### Reading Values

```c
// Read by ID
int32_t value = PMU_Channel_GetValue(0);  // Read channel 0

// Read by name
const PMU_Channel_t* ch = PMU_Channel_GetByName("Brake Pressure");
if (ch) {
    int32_t pressure = PMU_Channel_GetValue(ch->channel_id);
}

// Read system value
int32_t battery_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
```

### Writing Values

```c
// Set power output to 50%
PMU_Channel_SetValue(100, 500);  // Channel 100, 50.0%

// Set H-bridge to forward motion at 70% power
PMU_Channel_SetValue(150, 700);  // Positive = forward

// Set H-bridge to reverse motion
PMU_Channel_SetValue(150, -700);  // Negative = reverse
```

### Channel Information

```c
// Get metadata
const PMU_Channel_t* info = PMU_Channel_GetInfo(0);
if (info) {
    printf("Channel: %s\n", info->name);
    printf("Type: 0x%02X\n", info->type);
    printf("Value: %ld %s\n", info->value, info->unit);
    printf("Range: %ld - %ld\n", info->min_value, info->max_value);
}

// Check type
if (PMU_Channel_IsInput(info->type)) {
    // This is an input
}
if (PMU_Channel_IsVirtual(info->type)) {
    // This is a virtual channel
}
```

### Channel Management

```c
// Enable/disable channel
PMU_Channel_SetEnabled(0, true);   // Enable
PMU_Channel_SetEnabled(0, false);  // Disable

// Get list of all channels
PMU_Channel_t channels[100];
uint16_t count = PMU_Channel_List(channels, 100);

for (uint16_t i = 0; i < count; i++) {
    printf("%d: %s = %ld %s\n",
           channels[i].channel_id,
           channels[i].name,
           channels[i].value,
           channels[i].unit);
}

// Statistics
const PMU_ChannelStats_t* stats = PMU_Channel_GetStats();
printf("Total: %d, Inputs: %d, Outputs: %d, Virtual: %d\n",
       stats->total_channels,
       stats->input_channels,
       stats->output_channels,
       stats->virtual_channels);
```

---

## Usage Examples

### Example 1: Registering Physical Channels from Configuration

```c
// When loading configuration from JSON
void RegisterPhysicalChannels(void)
{
    PMU_Channel_t channel;

    // Register all physical inputs (ADC 0-19)
    for (uint8_t i = 0; i < 20; i++) {
        memset(&channel, 0, sizeof(channel));
        channel.channel_id = i;  // ID 0-19
        channel.type = PMU_CHANNEL_INPUT_ANALOG;
        channel.direction = PMU_CHANNEL_DIR_INPUT;
        channel.format = PMU_CHANNEL_FORMAT_RAW;
        channel.physical_index = i;
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;
        channel.min_value = 0;
        channel.max_value = 1023;

        snprintf(channel.name, sizeof(channel.name), "Input %d", i);
        strncpy(channel.unit, "raw", sizeof(channel.unit));

        PMU_Channel_Register(&channel);
    }

    // Register all power outputs (PROFET 0-29)
    for (uint8_t i = 0; i < 30; i++) {
        memset(&channel, 0, sizeof(channel));
        channel.channel_id = 100 + i;  // ID 100-129
        channel.type = PMU_CHANNEL_OUTPUT_POWER;
        channel.direction = PMU_CHANNEL_DIR_OUTPUT;
        channel.format = PMU_CHANNEL_FORMAT_PERCENT;
        channel.physical_index = i;
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;
        channel.min_value = 0;
        channel.max_value = 1000;

        snprintf(channel.name, sizeof(channel.name), "Output %d", i);
        strncpy(channel.unit, "%", sizeof(channel.unit));

        PMU_Channel_Register(&channel);
    }
}
```

### Example 2: Logic Function Using Channels

```c
// Turn on fan if temperature > 80°C OR pressure > 3 bar
void UpdateCoolingFan(void)
{
    int32_t temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    int32_t pressure = PMU_Channel_GetValue(5);  // Pressure sensor on input 5

    bool fan_on = (temp > 80) || (pressure > 3000);

    // Channel 105 = fan (PROFET output 5)
    PMU_Channel_SetValue(105, fan_on ? 1000 : 0);  // 100% or 0%
}
```

### Example 3: Virtual Channel with Calculation

```c
// Register virtual channel for power (P = V × I)
void RegisterPowerChannel(void)
{
    PMU_Channel_t channel = {
        .channel_id = 200,
        .type = PMU_CHANNEL_INPUT_CALCULATED,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_RAW,
        .physical_index = 0,  // Logic function index
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .min_value = 0,
        .max_value = 100000,  // 100 kW max
        .name = "Total Power",
        .unit = "W"
    };
    strncpy(channel.unit, "W", sizeof(channel.unit));

    PMU_Channel_Register(&channel);
}

// Update calculated value (called periodically)
void UpdatePowerCalculation(void)
{
    int32_t voltage = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t current = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);

    // P = V × I (in mW, then convert to W)
    int32_t power_w = (voltage * current) / 1000000;

    // Save to virtual channel through logic module
    PMU_Logic_SetVirtualChannel(0, power_w);
}
```

### Example 4: CAN Virtual Input

```c
// Register CAN input for engine RPM
void RegisterEngineRPM(void)
{
    PMU_Channel_t channel = {
        .channel_id = 250,
        .type = PMU_CHANNEL_INPUT_CAN,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_RAW,
        .physical_index = 0,  // CAN message index
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .min_value = 0,
        .max_value = 9000,
        .name = "Engine RPM",
        .unit = "rpm"
    };

    PMU_Channel_Register(&channel);
}

// Read RPM from anywhere in the code
void DisplayEngineRPM(void)
{
    int32_t rpm = PMU_Channel_GetValue(250);
    printf("Engine RPM: %ld\n", rpm);
}
```

---

## Integration with Existing Modules

### Updating pmu_logging.c

```c
static uint16_t Logging_GetChannelValue(PMU_LogChannel_t* channel)
{
    // Old way - multiple case statements
    // New way - single call:
    return (uint16_t)PMU_Channel_GetValue(channel->channel_id);
}
```

### Updating pmu_logic.c

```c
// Instead of direct calls to PMU_ADC_GetValue(), PMU_PROFET_GetState():
int32_t input_value = PMU_Channel_GetValue(input_channel_id);
PMU_Channel_SetValue(output_channel_id, result);
```

### Updating pmu_protocol.c

```c
// Command to get channel value by name
static void Protocol_HandleGetChannelByName(const PMU_Protocol_Packet_t* packet)
{
    const char* name = (const char*)packet->data;
    const PMU_Channel_t* ch = PMU_Channel_GetByName(name);

    if (ch) {
        int32_t value = PMU_Channel_GetValue(ch->channel_id);
        uint8_t response[8];
        memcpy(&response[0], &ch->channel_id, 2);
        memcpy(&response[2], &value, 4);
        Protocol_SendData(PMU_CMD_GET_CHANNEL, response, 6);
    } else {
        Protocol_SendNACK(PMU_CMD_GET_CHANNEL, "Channel not found");
    }
}
```

---

## Performance

- **Lookup time**: O(1) for ID access (direct array indexing)
- **Memory overhead**: ~80 bytes per channel
- **Maximum channels**: 1024
- **Total memory**: ~80 KB for full registration

---

## Best Practices

1. **Use meaningful channel names**: `"Brake_Pressure"` instead of `"Input_5"`
2. **Set correct ranges**: Helps detect errors
3. **Specify units**: Simplifies debugging and logging
4. **Register channels at initialization**: Don't create dynamically during operation
5. **Use system channels**: Instead of direct calls to `PMU_Protection_GetVoltage()`

---

## Future Enhancements

- Callback functions on value change
- Value filtering (debounce, averaging)
- Channel aliases
- Channel groups
- Save/load channel registry from flash

---

**© 2025 R2 m-sport. All rights reserved.**

# PMU-30 Universal Channel Abstraction

**Version**: 2.0
**Author**: R2 m-sport
**Date**: 2025-12-29

---

## Overview

The Universal Channel Abstraction provides a unified API for working with all types of PMU-30 inputs and outputs, regardless of their physical or virtual nature. This layer enables consistent access to hardware I/O, calculated values, and system parameters through a single interface.

### Key Benefits

- **Unified Interface**: `PMU_Channel_GetValue()` and `PMU_Channel_SetValue()` for all channel types
- **Automatic Routing**: The system automatically determines which driver to use
- **Virtual Channels**: Support for calculated values, CAN, functions, tables
- **Name Lookup**: Access channels by symbolic name or ID
- **ECUMaster Compatible**: System channel naming follows ECUMaster `pmuX.*` conventions
- **Sub-Channels**: Per-output sub-channels for status, current, voltage, duty cycle
- **Atomic Updates**: Real-time channel config updates via protocol (0x66/0x67)

---

## Channel Classification (PMU_ChannelClass_t)

### Physical Inputs (0x00-0x1F)

| Class | Code | Description | Example |
|-------|------|-------------|---------|
| `PMU_CHANNEL_CLASS_INPUT_ANALOG` | 0x00 | Analog input (0-5V) | Pressure sensor |
| `PMU_CHANNEL_CLASS_INPUT_DIGITAL` | 0x01 | Digital input (on/off) | Door switch |
| `PMU_CHANNEL_CLASS_INPUT_SWITCH` | 0x02 | Switch input | Steering wheel toggle |
| `PMU_CHANNEL_CLASS_INPUT_ROTARY` | 0x03 | Rotary switch | Multi-position selector |
| `PMU_CHANNEL_CLASS_INPUT_FREQUENCY` | 0x04 | Frequency input | Speed sensor |

### Virtual Inputs (0x20-0x3F)

| Class | Code | Description | Example |
|-------|------|-------------|---------|
| `PMU_CHANNEL_CLASS_INPUT_CAN` | 0x20 | CAN bus input | Engine RPM from ECU |
| `PMU_CHANNEL_CLASS_INPUT_CALCULATED` | 0x21 | Calculated value | Power (V × I) |
| `PMU_CHANNEL_CLASS_INPUT_SYSTEM` | 0x22 | System value | Battery voltage |

### Physical Outputs (0x40-0x5F)

| Class | Code | Description | Example |
|-------|------|-------------|---------|
| `PMU_CHANNEL_CLASS_OUTPUT_POWER` | 0x40 | Power output (PROFET) | Fuel pump relay |
| `PMU_CHANNEL_CLASS_OUTPUT_PWM` | 0x41 | PWM output | Fan control |
| `PMU_CHANNEL_CLASS_OUTPUT_HBRIDGE` | 0x42 | H-bridge | Power window |
| `PMU_CHANNEL_CLASS_OUTPUT_ANALOG` | 0x43 | Analog output (DAC) | 0-10V control |

### Virtual Outputs (0x60-0x7F)

| Class | Code | Description | Example |
|-------|------|-------------|---------|
| `PMU_CHANNEL_CLASS_OUTPUT_FUNCTION` | 0x60 | Logic function | AND/OR/NOT |
| `PMU_CHANNEL_CLASS_OUTPUT_TABLE` | 0x61 | Lookup table | Throttle curve |
| `PMU_CHANNEL_CLASS_OUTPUT_ENUM` | 0x62 | Enumeration | Mode (OFF/ON/AUTO) |
| `PMU_CHANNEL_CLASS_OUTPUT_NUMBER` | 0x63 | Constant | Regulator setpoint |
| `PMU_CHANNEL_CLASS_OUTPUT_CAN` | 0x64 | CAN output | Send temp to display |
| `PMU_CHANNEL_CLASS_OUTPUT_PID` | 0x65 | PID controller | Temperature controller |

---

## Channel ID Ranges

```
0-99:       Physical inputs (Analog 0-11, Digital 0-7)
100-199:    Physical outputs (PROFET 0-29, H-bridge 0-3)
200-999:    Virtual channels (Logic, CAN RX/TX, Tables, Numbers, etc.)
1000-1023:  System channels (voltage, temperature, uptime, constants)
1100-1279:  Output sub-channels (status, current, voltage, active, duty)
```

### System Channels (1000-1023)

| ID | Name | ECUMaster Alias | Description | Units |
|----|------|-----------------|-------------|-------|
| 1000 | Battery Voltage | `pmu.batteryVoltage` | Main battery voltage | mV |
| 1001 | Total Current | `pmu.totalCurrent` | Total current draw | mA |
| 1002 | MCU Temperature | `pmu.mcuTemperature` | MCU die temperature | °C |
| 1003 | Board Temp L | `pmu.boardTemperatureL` | Left board sensor | °C |
| 1004 | Board Temp R | `pmu.boardTemperatureR` | Right board sensor | °C |
| 1005 | Board Temp Max | `pmu.boardTemperatureMax` | Maximum board temp | °C |
| 1006 | System Uptime | `pmu.uptime` | Operating time | seconds |
| 1007 | System Status | `pmu.status` | Status bitmask | bitmask |
| 1008 | User Error | `pmu.userError` | User-defined error code | code |
| 1009 | 5V Output | `pmu.5VOutput` | 5V rail voltage | mV |
| 1010 | 3.3V Output | `pmu.3V3Output` | 3.3V rail voltage | mV |
| 1011 | Is Turning Off | `pmu.isTurningOff` | Shutdown in progress | 0/1 |
| 1012 | Constant Zero | `zero` | Always returns 0 | - |
| 1013 | Constant One | `one` | Always returns 1 | - |

### Output Sub-Channels (ECUMaster Compatible)

Each of the 30 PROFET outputs has associated sub-channels for monitoring:

| Base | Range | ECUMaster Alias | Description | Units |
|------|-------|-----------------|-------------|-------|
| 1100 | 1100-1129 | `pmu.oY.status` | Output state (0-7) | enum |
| 1130 | 1130-1159 | `pmu.oY.current` | Measured current | mA |
| 1160 | 1160-1189 | `pmu.oY.voltage` | Output voltage | mV |
| 1190 | 1190-1219 | `pmu.oY.active` | Output active flag | bool |
| 1250 | 1250-1279 | `pmu.oY.dutyCycle` | PWM duty cycle | 0-1000 |

**Usage**: `channel_id = BASE + output_index` (e.g., Output 5 current = 1130 + 5 = 1135)

### Analog Input Sub-Channels

| Base | Range | ECUMaster Alias | Description | Units |
|------|-------|-----------------|-------------|-------|
| 1220 | 1220-1231 | `pmu.aY.voltage` | Raw ADC voltage | mV |

---

## Value Formats (PMU_ChannelFormat_t)

| Format | Code | Description | Range |
|--------|------|-------------|-------|
| `PMU_CHANNEL_FORMAT_RAW` | 0 | Raw ADC/PWM value | 0-1023 |
| `PMU_CHANNEL_FORMAT_PERCENT` | 1 | Percentage (scaled) | 0-1000 (0.0-100.0%) |
| `PMU_CHANNEL_FORMAT_VOLTAGE` | 2 | Voltage | mV |
| `PMU_CHANNEL_FORMAT_CURRENT` | 3 | Current | mA |
| `PMU_CHANNEL_FORMAT_BOOLEAN` | 4 | Boolean | 0/1 |
| `PMU_CHANNEL_FORMAT_ENUM` | 5 | Enumeration | 0-255 |
| `PMU_CHANNEL_FORMAT_SIGNED` | 6 | Signed integer | -32768 to +32767 |
| `PMU_CHANNEL_FORMAT_INT` | 7 | General integer | int32_t range |

---

## Channel Flags

```c
#define PMU_CHANNEL_FLAG_ENABLED   0x01  /* Channel enabled */
#define PMU_CHANNEL_FLAG_INVERTED  0x02  /* Value inverted */
#define PMU_CHANNEL_FLAG_FAULT     0x04  /* Fault detected */
#define PMU_CHANNEL_FLAG_OVERRIDE  0x08  /* Manual override active */
```

---

## API Reference

### Initialization

```c
// Initialize channel system (call once at startup)
HAL_StatusTypeDef PMU_Channel_Init(void);

// Register a new channel
PMU_Channel_t channel = {
    .channel_id = 200,                          // Virtual channel range
    .hw_class = PMU_CHANNEL_CLASS_INPUT_CALCULATED,
    .direction = PMU_CHANNEL_DIR_VIRTUAL,
    .format = PMU_CHANNEL_FORMAT_INT,
    .physical_index = 0,
    .flags = PMU_CHANNEL_FLAG_ENABLED,
    .min_value = 0,
    .max_value = 100000,
    .name = "TotalPower",
    .unit = "W"
};
PMU_Channel_Register(&channel);

// Generate unique ID for dynamic channels
uint16_t new_id = PMU_Channel_GenerateID();
```

### Reading Values

```c
// Read by channel ID
int32_t value = PMU_Channel_GetValue(0);  // Physical input 0

// Read system channels
int32_t battery_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
int32_t mcu_temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);

// Read output sub-channels
int32_t out5_current = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_CURRENT_BASE + 5);
int32_t out5_status = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_STATUS_BASE + 5);

// Read by name
const PMU_Channel_t* ch = PMU_Channel_GetByName("BrakePressure");
if (ch) {
    int32_t pressure = PMU_Channel_GetValue(ch->channel_id);
}

// Get channel ID by name/ID string
uint16_t id = PMU_Channel_GetIndexByID("FuelPump");  // Returns 0xFFFF if not found
```

### Writing Values

```c
// Set power output to 50%
PMU_Channel_SetValue(100, 500);  // Channel 100 (output 0), 50.0%

// Set H-bridge forward at 70%
PMU_Channel_SetValue(150, 700);  // Positive = forward

// Set H-bridge reverse at 70%
PMU_Channel_SetValue(150, -700);  // Negative = reverse

// Update input value (for syncing hardware state)
PMU_Channel_UpdateValue(5, raw_adc_value);  // Allows setting INPUT channels
```

### Channel Information

```c
// Get metadata
const PMU_Channel_t* info = PMU_Channel_GetInfo(105);
if (info) {
    printf("Channel: %s\n", info->name);
    printf("Class: 0x%02X\n", info->hw_class);
    printf("Value: %ld %s\n", info->value, info->unit);
    printf("Range: %ld - %ld\n", info->min_value, info->max_value);
    printf("Flags: 0x%02X\n", info->flags);
}

// Type checking helpers
if (PMU_Channel_IsInput(info->hw_class)) {
    // This is an input channel
}
if (PMU_Channel_IsOutput(info->hw_class)) {
    // This is an output channel
}
if (PMU_Channel_IsVirtual(info->hw_class)) {
    // This is a virtual (calculated/CAN/logic) channel
}
if (PMU_Channel_IsPhysical(info->hw_class)) {
    // This is a physical (ADC/PROFET/H-bridge) channel
}
```

### Channel Management

```c
// Enable/disable channel
PMU_Channel_SetEnabled(105, true);   // Enable
PMU_Channel_SetEnabled(105, false);  // Disable

// List all registered channels
PMU_Channel_t channels[100];
uint16_t count = PMU_Channel_List(channels, 100);

for (uint16_t i = 0; i < count; i++) {
    printf("%d: %s = %ld %s\n",
           channels[i].channel_id,
           channels[i].name,
           channels[i].value,
           channels[i].unit);
}

// Get statistics
const PMU_ChannelStats_t* stats = PMU_Channel_GetStats();
printf("Total: %d, Inputs: %d, Outputs: %d, Virtual: %d, Physical: %d\n",
       stats->total_channels,
       stats->input_channels,
       stats->output_channels,
       stats->virtual_channels,
       stats->physical_channels);

// Update all channels (call at 1kHz in main loop)
PMU_Channel_Update();
```

---

## Usage Examples

### Example 1: Reading Output Status and Current

```c
void MonitorOutputHealth(uint8_t output_index)
{
    // Read output sub-channels
    int32_t status = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_STATUS_BASE + output_index);
    int32_t current_ma = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_CURRENT_BASE + output_index);
    int32_t duty = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_DUTY_BASE + output_index);

    printf("Output %d: status=%ld, current=%ldmA, duty=%ld.%ld%%\n",
           output_index, status, current_ma, duty / 10, duty % 10);

    // Check for faults (status >= 2 indicates fault)
    if (status >= 2) {
        printf("WARNING: Output %d has fault state %ld\n", output_index, status);
    }
}
```

### Example 2: Cooling Fan Logic with Hysteresis

```c
void UpdateCoolingFan(void)
{
    // Read system temperatures
    int32_t mcu_temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    int32_t board_temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BOARD_TEMP_MAX);
    int32_t pressure = PMU_Channel_GetValue(5);  // Pressure sensor on input 5

    // Fan threshold with hysteresis
    static bool fan_on = false;
    int32_t max_temp = (mcu_temp > board_temp) ? mcu_temp : board_temp;

    if (max_temp > 80 || pressure > 3000) {
        fan_on = true;
    } else if (max_temp < 70 && pressure < 2500) {
        fan_on = false;
    }

    // Channel 105 = fan (PROFET output 5)
    PMU_Channel_SetValue(105, fan_on ? 1000 : 0);
}
```

### Example 3: Virtual Power Calculation Channel

```c
void RegisterPowerChannel(void)
{
    PMU_Channel_t channel = {
        .channel_id = 200,
        .hw_class = PMU_CHANNEL_CLASS_INPUT_CALCULATED,
        .direction = PMU_CHANNEL_DIR_VIRTUAL,
        .format = PMU_CHANNEL_FORMAT_INT,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .min_value = 0,
        .max_value = 100000,
    };
    strncpy(channel.name, "TotalPower", sizeof(channel.name));
    strncpy(channel.unit, "W", sizeof(channel.unit));

    PMU_Channel_Register(&channel);
}

// Called at 100Hz to update calculated value
void UpdatePowerCalculation(void)
{
    int32_t voltage_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t current_ma = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);

    // P = V × I (convert from mV*mA to W)
    int32_t power_w = (voltage_mv * current_ma) / 1000000;

    PMU_Channel_UpdateValue(200, power_w);
}
```

### Example 4: CAN Input for Engine RPM

```c
void RegisterEngineRPM(void)
{
    PMU_Channel_t channel = {
        .channel_id = 250,
        .hw_class = PMU_CHANNEL_CLASS_INPUT_CAN,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_INT,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .min_value = 0,
        .max_value = 9000,
    };
    strncpy(channel.name, "EngineRPM", sizeof(channel.name));
    strncpy(channel.unit, "rpm", sizeof(channel.unit));

    PMU_Channel_Register(&channel);
}

// CAN RX callback updates the channel
void OnCANMessage_EngineRPM(uint16_t rpm)
{
    PMU_Channel_UpdateValue(250, rpm);
}

// Read from anywhere
void DisplayDashboard(void)
{
    int32_t rpm = PMU_Channel_GetValue(250);
    int32_t battery = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t uptime = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_UPTIME);

    printf("RPM: %ld | Battery: %ld.%02ldV | Uptime: %lds\n",
           rpm, battery / 1000, (battery % 1000) / 10, uptime);
}
```

---

## Atomic Channel Configuration Updates

Channels can be reconfigured at runtime via the protocol command 0x66 (`SET_CHANNEL_CONFIG`):

```
Request:  [0xAA][0x66][N][TYPE][CHANNEL_ID:2B][JSON_LEN:2B][JSON_CONFIG][CRC]
Response: [0xAA][0x67][N][CHANNEL_ID:2B][SUCCESS][ERROR_CODE:2B][ERROR_MSG][CRC]
```

This enables real-time tuning from the configurator UI without full config reload.

See `PROTOCOL_DOCUMENTATION.md` for full details.

---

## Integration with Existing Modules

### Updating pmu_logic.c

```c
// Use channel abstraction instead of direct driver calls
int32_t input_value = PMU_Channel_GetValue(input_channel_id);
PMU_Channel_SetValue(output_channel_id, result);
```

### Updating pmu_protocol.c

```c
// Command handler using channel abstraction
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

### Updating pmu_config_json.c

```c
// When loading configuration, register channels
void JSON_RegisterChannelFromConfig(cJSON* channel_obj)
{
    PMU_Channel_t channel;
    memset(&channel, 0, sizeof(channel));

    channel.channel_id = cJSON_GetObjectItem(channel_obj, "channel_id")->valueint;
    // ... parse other fields ...

    PMU_Channel_Register(&channel);
}
```

---

## Performance

| Metric | Value |
|--------|-------|
| Lookup time (by ID) | O(1) - direct array indexing |
| Lookup time (by name) | O(n) - linear search |
| Memory per channel | ~80 bytes |
| Maximum channels | 1024 |
| Total memory (full) | ~80 KB |
| Update rate | 1 kHz (every 1ms) |

---

## Best Practices

1. **Use meaningful channel names**: `"BrakePressure"` instead of `"Input5"`
2. **Set correct ranges**: Helps detect out-of-bound errors
3. **Specify units**: Simplifies debugging and logging
4. **Register at initialization**: Don't create channels dynamically during operation
5. **Use system channels**: Instead of direct calls like `PMU_Protection_GetVoltage()`
6. **Use sub-channels for monitoring**: Access output current/status via sub-channels
7. **Leverage constants**: Use `PMU_CHANNEL_CONST_ZERO` and `PMU_CHANNEL_CONST_ONE` for fixed values

---

## Changelog

### Version 2.0 (2025-12-29)
- Updated to match actual firmware implementation (`pmu_channel.h`)
- Added ECUMaster-compatible system channel aliases
- Added output sub-channels (status, current, voltage, active, duty)
- Added analog input sub-channels (voltage)
- Added constant channels (zero, one)
- Added `PMU_Channel_UpdateValue()` for input synchronization
- Added `PMU_Channel_GenerateID()` for dynamic channel creation
- Added `PMU_Channel_GetIndexByID()` for name-to-ID lookup
- Added `PMU_CHANNEL_FORMAT_INT` value format
- Renamed type enum from `PMU_CHANNEL_INPUT_*` to `PMU_ChannelClass_t`
- Added atomic update protocol reference (0x66/0x67)

### Version 1.0 (2025-12-21)
- Initial implementation

---

**© 2025 R2 m-sport. All rights reserved.**

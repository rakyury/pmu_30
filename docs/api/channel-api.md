# Channel API Reference

**Version:** 1.0
**Date:** December 2024
**Module:** pmu_channel.h

---

## Table of Contents

1. [Overview](#1-overview)
2. [Initialization](#2-initialization)
3. [Channel Registration](#3-channel-registration)
4. [Read/Write Operations](#4-readwrite-operations)
5. [Channel Information](#5-channel-information)
6. [Channel Control](#6-channel-control)
7. [Utility Functions](#7-utility-functions)
8. [Data Types](#8-data-types)
9. [Constants](#9-constants)
10. [Examples](#10-examples)

---

## 1. Overview

The Channel API provides a unified interface for accessing all inputs and outputs in the PMU-30 system. All channel operations are thread-safe and designed for real-time execution.

### 1.1 Include Header

```c
#include "pmu_channel.h"
```

### 1.2 API Summary

| Function | Description |
|----------|-------------|
| `PMU_Channel_Init()` | Initialize channel subsystem |
| `PMU_Channel_Register()` | Register a new channel |
| `PMU_Channel_Unregister()` | Remove a channel |
| `PMU_Channel_GetValue()` | Read channel value |
| `PMU_Channel_SetValue()` | Write channel value |
| `PMU_Channel_GetInfo()` | Get channel metadata |
| `PMU_Channel_GetByName()` | Find channel by name |
| `PMU_Channel_Update()` | Update all channels |
| `PMU_Channel_GetStats()` | Get registry statistics |
| `PMU_Channel_List()` | List all channels |
| `PMU_Channel_SetEnabled()` | Enable/disable channel |

---

## 2. Initialization

### PMU_Channel_Init

Initialize the channel abstraction layer. Must be called before any other channel functions.

```c
HAL_StatusTypeDef PMU_Channel_Init(void);
```

**Parameters:** None

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | Initialization successful |
| `HAL_ERROR` | Initialization failed |

**Example:**
```c
void system_init(void) {
    if (PMU_Channel_Init() != HAL_OK) {
        Error_Handler();
    }
}
```

**Notes:**
- Call once during system startup
- Initializes channel registry to empty state
- Creates synchronization primitives

---

## 3. Channel Registration

### PMU_Channel_Register

Register a new channel in the system.

```c
HAL_StatusTypeDef PMU_Channel_Register(const PMU_Channel_t* channel);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| channel | `const PMU_Channel_t*` | Pointer to channel configuration |

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | Registration successful |
| `HAL_ERROR` | Invalid configuration or ID collision |

**Example:**
```c
PMU_Channel_t adc_channel = {
    .channel_id = 0,
    .type = PMU_CHANNEL_INPUT_ANALOG,
    .direction = PMU_CHANNEL_DIR_INPUT,
    .format = PMU_CHANNEL_FORMAT_VOLTAGE,
    .physical_index = 0,
    .flags = PMU_CHANNEL_FLAG_ENABLED,
    .value = 0,
    .min_value = 0,
    .max_value = 5000,  // 5000 mV
    .name = "Throttle Position",
    .unit = "mV"
};

if (PMU_Channel_Register(&adc_channel) != HAL_OK) {
    // Handle error
}
```

---

### PMU_Channel_Unregister

Remove a channel from the registry.

```c
HAL_StatusTypeDef PMU_Channel_Unregister(uint16_t channel_id);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| channel_id | `uint16_t` | Channel ID to remove (0-1023) |

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | Unregistration successful |
| `HAL_ERROR` | Channel not found |

**Example:**
```c
// Remove virtual channel
PMU_Channel_Unregister(200);
```

---

## 4. Read/Write Operations

### PMU_Channel_GetValue

Read the current value of a channel.

```c
int32_t PMU_Channel_GetValue(uint16_t channel_id);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| channel_id | `uint16_t` | Channel ID (0-1023) |

**Returns:**
| Value | Description |
|-------|-------------|
| `int32_t` | Current channel value |
| `0` | If channel not found |

**Example:**
```c
// Read battery voltage (channel 1000)
int32_t battery_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
float battery_v = battery_mv / 1000.0f;

// Read analog input
int32_t throttle = PMU_Channel_GetValue(0);
```

**Performance:** < 1 us typical

---

### PMU_Channel_SetValue

Write a value to a channel.

```c
HAL_StatusTypeDef PMU_Channel_SetValue(uint16_t channel_id, int32_t value);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| channel_id | `uint16_t` | Channel ID (0-1023) |
| value | `int32_t` | Value to set |

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | Value set successfully |
| `HAL_ERROR` | Channel not found or read-only |

**Example:**
```c
// Set output duty cycle (0-1000 = 0-100%)
PMU_Channel_SetValue(100, 500);  // Set PROFET 0 to 50%

// Set virtual channel
PMU_Channel_SetValue(200, 1234);
```

**Notes:**
- Value is not automatically clamped to min/max
- For output channels, value is applied on next update cycle
- Thread-safe operation

---

## 5. Channel Information

### PMU_Channel_GetInfo

Get full channel information structure.

```c
const PMU_Channel_t* PMU_Channel_GetInfo(uint16_t channel_id);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| channel_id | `uint16_t` | Channel ID (0-1023) |

**Returns:**
| Value | Description |
|-------|-------------|
| `PMU_Channel_t*` | Pointer to channel structure |
| `NULL` | If channel not found |

**Example:**
```c
const PMU_Channel_t* ch = PMU_Channel_GetInfo(0);
if (ch != NULL) {
    printf("Channel: %s\n", ch->name);
    printf("Value: %ld %s\n", ch->value, ch->unit);
    printf("Range: %ld - %ld\n", ch->min_value, ch->max_value);
}
```

---

### PMU_Channel_GetByName

Find a channel by its name.

```c
const PMU_Channel_t* PMU_Channel_GetByName(const char* name);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| name | `const char*` | Channel name string |

**Returns:**
| Value | Description |
|-------|-------------|
| `PMU_Channel_t*` | Pointer to channel structure |
| `NULL` | If channel not found |

**Example:**
```c
const PMU_Channel_t* ch = PMU_Channel_GetByName("Coolant Temp");
if (ch != NULL) {
    int32_t temp = ch->value;
}
```

**Notes:**
- Case-sensitive comparison
- O(n) search complexity
- Use channel ID for performance-critical code

---

### PMU_Channel_GetStats

Get channel registry statistics.

```c
const PMU_ChannelStats_t* PMU_Channel_GetStats(void);
```

**Parameters:** None

**Returns:** Pointer to statistics structure

**Example:**
```c
const PMU_ChannelStats_t* stats = PMU_Channel_GetStats();
printf("Total channels: %d\n", stats->total_channels);
printf("Input channels: %d\n", stats->input_channels);
printf("Output channels: %d\n", stats->output_channels);
printf("Virtual channels: %d\n", stats->virtual_channels);
printf("Physical channels: %d\n", stats->physical_channels);
```

---

### PMU_Channel_List

List all registered channels.

```c
uint16_t PMU_Channel_List(PMU_Channel_t* channels, uint16_t max_count);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| channels | `PMU_Channel_t*` | Array to fill |
| max_count | `uint16_t` | Maximum channels to return |

**Returns:** Number of channels copied

**Example:**
```c
PMU_Channel_t channel_list[100];
uint16_t count = PMU_Channel_List(channel_list, 100);

for (uint16_t i = 0; i < count; i++) {
    printf("[%d] %s = %ld\n",
           channel_list[i].channel_id,
           channel_list[i].name,
           channel_list[i].value);
}
```

---

## 6. Channel Control

### PMU_Channel_Update

Update all channels from hardware. Called automatically at 1kHz.

```c
void PMU_Channel_Update(void);
```

**Parameters:** None

**Returns:** None

**Notes:**
- Reads ADC values for analog inputs
- Updates system channels (voltage, temperature)
- Typically called from main loop or timer ISR

---

### PMU_Channel_SetEnabled

Enable or disable a channel.

```c
HAL_StatusTypeDef PMU_Channel_SetEnabled(uint16_t channel_id, bool enabled);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| channel_id | `uint16_t` | Channel ID (0-1023) |
| enabled | `bool` | Enable state |

**Returns:**
| Value | Description |
|-------|-------------|
| `HAL_OK` | State changed successfully |
| `HAL_ERROR` | Channel not found |

**Example:**
```c
// Disable output channel
PMU_Channel_SetEnabled(100, false);

// Re-enable
PMU_Channel_SetEnabled(100, true);
```

---

## 7. Utility Functions

### PMU_Channel_IsInput

Check if channel type is an input.

```c
static inline bool PMU_Channel_IsInput(PMU_ChannelType_t type);
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| type | `PMU_ChannelType_t` | Channel type |

**Returns:** `true` if input type, `false` otherwise

**Example:**
```c
const PMU_Channel_t* ch = PMU_Channel_GetInfo(0);
if (PMU_Channel_IsInput(ch->type)) {
    // Handle as input
}
```

---

### PMU_Channel_IsOutput

Check if channel type is an output.

```c
static inline bool PMU_Channel_IsOutput(PMU_ChannelType_t type);
```

---

### PMU_Channel_IsVirtual

Check if channel type is virtual.

```c
static inline bool PMU_Channel_IsVirtual(PMU_ChannelType_t type);
```

---

### PMU_Channel_IsPhysical

Check if channel type is physical.

```c
static inline bool PMU_Channel_IsPhysical(PMU_ChannelType_t type);
```

---

## 8. Data Types

### PMU_ChannelType_t

```c
typedef enum {
    // Physical Inputs (0x00-0x1F)
    PMU_CHANNEL_INPUT_ANALOG        = 0x00,
    PMU_CHANNEL_INPUT_DIGITAL       = 0x01,
    PMU_CHANNEL_INPUT_SWITCH        = 0x02,
    PMU_CHANNEL_INPUT_ROTARY        = 0x03,
    PMU_CHANNEL_INPUT_FREQUENCY     = 0x04,

    // Virtual Inputs (0x20-0x3F)
    PMU_CHANNEL_INPUT_CAN           = 0x20,
    PMU_CHANNEL_INPUT_CALCULATED    = 0x21,
    PMU_CHANNEL_INPUT_SYSTEM        = 0x22,

    // Physical Outputs (0x40-0x5F)
    PMU_CHANNEL_OUTPUT_POWER        = 0x40,
    PMU_CHANNEL_OUTPUT_PWM          = 0x41,
    PMU_CHANNEL_OUTPUT_HBRIDGE      = 0x42,
    PMU_CHANNEL_OUTPUT_ANALOG       = 0x43,

    // Virtual Outputs (0x60-0x7F)
    PMU_CHANNEL_OUTPUT_FUNCTION     = 0x60,
    PMU_CHANNEL_OUTPUT_TABLE        = 0x61,
    PMU_CHANNEL_OUTPUT_ENUM         = 0x62,
    PMU_CHANNEL_OUTPUT_NUMBER       = 0x63,
    PMU_CHANNEL_OUTPUT_CAN          = 0x64,
    PMU_CHANNEL_OUTPUT_PID          = 0x65,
} PMU_ChannelType_t;
```

---

### PMU_ChannelDir_t

```c
typedef enum {
    PMU_CHANNEL_DIR_INPUT  = 0,
    PMU_CHANNEL_DIR_OUTPUT = 1,
    PMU_CHANNEL_DIR_BIDIR  = 2
} PMU_ChannelDir_t;
```

---

### PMU_ChannelFormat_t

```c
typedef enum {
    PMU_CHANNEL_FORMAT_RAW      = 0,  // Raw value (0-4095)
    PMU_CHANNEL_FORMAT_PERCENT  = 1,  // Percentage (0-1000)
    PMU_CHANNEL_FORMAT_VOLTAGE  = 2,  // Millivolts
    PMU_CHANNEL_FORMAT_CURRENT  = 3,  // Milliamps
    PMU_CHANNEL_FORMAT_BOOLEAN  = 4,  // Boolean (0/1)
    PMU_CHANNEL_FORMAT_ENUM     = 5,  // Enumeration (0-255)
    PMU_CHANNEL_FORMAT_SIGNED   = 6   // Signed value
} PMU_ChannelFormat_t;
```

---

### PMU_Channel_t

```c
typedef struct {
    uint16_t channel_id;            // Global channel ID (0-1023)
    PMU_ChannelType_t type;         // Channel type
    PMU_ChannelDir_t direction;     // Channel direction
    PMU_ChannelFormat_t format;     // Value format

    uint8_t physical_index;         // Physical hardware index
    uint8_t flags;                  // Status flags

    int32_t value;                  // Current value (signed)
    int32_t min_value;              // Minimum value
    int32_t max_value;              // Maximum value

    char name[32];                  // Channel name
    char unit[8];                   // Unit string
} PMU_Channel_t;
```

---

### PMU_ChannelStats_t

```c
typedef struct {
    uint16_t total_channels;        // Total registered channels
    uint16_t input_channels;        // Number of input channels
    uint16_t output_channels;       // Number of output channels
    uint16_t virtual_channels;      // Number of virtual channels
    uint16_t physical_channels;     // Number of physical channels
} PMU_ChannelStats_t;
```

---

## 9. Constants

### Channel ID Ranges

```c
#define PMU_CHANNEL_ID_INPUT_START      0
#define PMU_CHANNEL_ID_INPUT_END        99
#define PMU_CHANNEL_ID_OUTPUT_START     100
#define PMU_CHANNEL_ID_OUTPUT_END       199
#define PMU_CHANNEL_ID_VIRTUAL_START    200
#define PMU_CHANNEL_ID_VIRTUAL_END      999
#define PMU_CHANNEL_ID_SYSTEM_START     1000
#define PMU_CHANNEL_ID_SYSTEM_END       1023

#define PMU_CHANNEL_MAX_CHANNELS        1024
```

### Channel Flags

```c
#define PMU_CHANNEL_FLAG_ENABLED        0x01
#define PMU_CHANNEL_FLAG_INVERTED       0x02
#define PMU_CHANNEL_FLAG_FAULT          0x04
#define PMU_CHANNEL_FLAG_OVERRIDE       0x08
```

### System Channel IDs

```c
#define PMU_CHANNEL_SYSTEM_BATTERY_V    1000
#define PMU_CHANNEL_SYSTEM_TOTAL_I      1001
#define PMU_CHANNEL_SYSTEM_MCU_TEMP     1002
#define PMU_CHANNEL_SYSTEM_BOARD_TEMP   1003
#define PMU_CHANNEL_SYSTEM_UPTIME       1004
```

---

## 10. Examples

### 10.1 Basic Channel Read/Write

```c
#include "pmu_channel.h"

void example_basic_usage(void) {
    // Initialize
    PMU_Channel_Init();

    // Read analog input (ADC channel 0)
    int32_t adc_value = PMU_Channel_GetValue(0);

    // Read system battery voltage
    int32_t battery_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);

    // Set output duty cycle (50%)
    PMU_Channel_SetValue(100, 500);

    // Check if channel exists
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(0);
    if (ch != NULL) {
        // Channel exists
    }
}
```

### 10.2 Register Custom Channel

```c
void example_register_channel(void) {
    PMU_Channel_t my_channel = {
        .channel_id = 200,
        .type = PMU_CHANNEL_INPUT_CALCULATED,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_PERCENT,
        .physical_index = 0,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1000,
        .name = "Fuel Level",
        .unit = "%"
    };

    HAL_StatusTypeDef status = PMU_Channel_Register(&my_channel);
    if (status == HAL_OK) {
        // Success
    }
}
```

### 10.3 Iterate All Channels

```c
void example_list_channels(void) {
    PMU_Channel_t channels[256];
    uint16_t count = PMU_Channel_List(channels, 256);

    for (uint16_t i = 0; i < count; i++) {
        PMU_Channel_t* ch = &channels[i];

        const char* type_str = PMU_Channel_IsInput(ch->type) ? "IN" : "OUT";
        const char* nature_str = PMU_Channel_IsVirtual(ch->type) ? "VIRT" : "PHYS";

        printf("[%04d] %-20s %s/%s = %ld %s\n",
               ch->channel_id,
               ch->name,
               type_str,
               nature_str,
               ch->value,
               ch->unit);
    }
}
```

---

## See Also

- [Unified Channel System Architecture](../architecture/unified-channel-system.md)
- [Channel Types Specification](channel-types.md)
- [Getting Started with Channels](../guides/getting-started-channels.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024

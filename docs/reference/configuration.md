# PMU-30 Configuration Reference

**Version:** 4.0 | **Last Updated:** January 2026

Binary configuration format specification for PMU-30 firmware and configurator.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Binary Format](#2-binary-format)
3. [File Header](#3-file-header)
4. [Channel Header](#4-channel-header)
5. [Channel Types](#5-channel-types)
6. [Type-Specific Configurations](#6-type-specific-configurations)
7. [Usage Examples](#7-usage-examples)

---

## 1. Overview

### 1.1 Architecture

The PMU-30 system uses a **single binary format** for all configuration:

```
┌─────────────────────┐
│   Configurator      │ ◄──── Creates/edits config
│   (Python/Qt)       │
└──────────┬──────────┘
           │
           │ .pmu30 binary file
           ▼
┌─────────────────────┐
│   Binary Config     │ ◄──── One format for entire system
│   (.pmu30 file)     │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│ Firmware│ │ Config- │
│ (C)     │ │ urator  │
│         │ │ (Python)│
└─────────┘ └─────────┘
```

### 1.2 Design Principles

| Principle | Description |
|-----------|-------------|
| **No JSON** | Binary format only, no JSON conversion |
| **One Format** | Same binary format for firmware and configurator |
| **Shared Library** | C and Python implementations share identical structures |
| **CRC-32 Verified** | All configurations protected by CRC-32 checksum |
| **Compact** | Minimal overhead, efficient for embedded systems |

### 1.3 File Extension

Configuration files use the `.pmu30` extension.

---

## 2. Binary Format

### 2.1 File Structure

```
┌──────────────────────────────────────┐
│           File Header (32 bytes)      │
├──────────────────────────────────────┤
│           Channel 0                   │
│  ├─ Channel Header (14 bytes)        │
│  ├─ Name (variable, 0-31 bytes)      │
│  └─ Config (type-specific)           │
├──────────────────────────────────────┤
│           Channel 1                   │
│  └─ ...                              │
├──────────────────────────────────────┤
│           ...                         │
├──────────────────────────────────────┤
│           Channel N                   │
└──────────────────────────────────────┘
```

### 2.2 Byte Order

All multi-byte values are stored in **little-endian** format.

### 2.3 Constants

```c
#define CFG_MAGIC           0x43464733  // "CFG3"
#define CFG_VERSION         2
#define CFG_MAX_NAME_LEN    31
#define CFG_MAX_INPUTS      8
#define CH_REF_NONE         0xFFFF      // No channel reference
```

---

## 3. File Header

### 3.1 Structure (32 bytes)

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | magic | uint32 | Magic number: 0x43464733 ("CFG3") |
| 4 | 2 | version | uint16 | Format version (currently 2) |
| 6 | 2 | device_type | uint16 | Device type (0x0030 = PMU-30) |
| 8 | 4 | total_size | uint32 | Total file size in bytes |
| 12 | 4 | crc32 | uint32 | CRC-32 of all channel data |
| 16 | 2 | channel_count | uint16 | Number of channels |
| 18 | 2 | flags | uint16 | Configuration flags |
| 20 | 4 | timestamp | uint32 | Unix timestamp (seconds) |
| 24 | 8 | reserved | bytes | Reserved for future use |

### 3.2 C Structure

```c
typedef struct __attribute__((packed)) {
    uint32_t magic;          // 0x43464733
    uint16_t version;        // 2
    uint16_t device_type;    // 0x0030
    uint32_t total_size;
    uint32_t crc32;
    uint16_t channel_count;
    uint16_t flags;
    uint32_t timestamp;
    uint8_t  reserved[8];
} CfgFileHeader_t;
```

### 3.3 Python Structure

```python
@dataclass
class CfgFileHeader:
    FORMAT = "<IHHIIHHI8s"  # 32 bytes
    SIZE = 32

    magic: int = 0x43464733
    version: int = 2
    device_type: int = 0
    total_size: int = 32
    crc32: int = 0
    channel_count: int = 0
    flags: int = 0
    timestamp: int = 0
    reserved: bytes = bytes(8)
```

### 3.4 Flags

| Bit | Flag | Description |
|-----|------|-------------|
| 0 | COMPRESSED | Channel data is compressed |
| 1 | ENCRYPTED | Channel data is encrypted |
| 2 | PARTIAL | Partial configuration (delta update) |
| 3 | DEFAULTS | Contains default values |

---

## 4. Channel Header

### 4.1 Structure (14 bytes)

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 2 | id | uint16 | Channel ID (0-65535) |
| 2 | 1 | type | uint8 | Channel type (ChannelType enum) |
| 3 | 1 | flags | uint8 | Channel flags |
| 4 | 1 | hw_device | uint8 | Hardware device type |
| 5 | 1 | hw_index | uint8 | Hardware device index |
| 6 | 2 | source_id | uint16 | Source channel ID (0xFFFF = none) |
| 8 | 4 | default_value | int32 | Default value |
| 12 | 1 | name_len | uint8 | Length of name string |
| 13 | 1 | config_size | uint8 | Size of type-specific config |

### 4.2 C Structure

```c
typedef struct __attribute__((packed)) {
    uint16_t id;
    uint8_t  type;
    uint8_t  flags;
    uint8_t  hw_device;
    uint8_t  hw_index;
    uint16_t source_id;
    int32_t  default_value;
    uint8_t  name_len;
    uint8_t  config_size;
} CfgChannelHeader_t;
```

### 4.3 Channel Flags

| Bit | Flag | Description |
|-----|------|-------------|
| 0 | ENABLED | Channel is enabled |
| 1 | INVERTED | Output value is inverted |
| 2 | BUILTIN | Built-in system channel |
| 3 | READONLY | Read-only channel |
| 4 | HIDDEN | Hidden from UI |
| 5 | FAULT | Channel in fault state |

---

## 5. Channel Types

### 5.1 Type Enumeration

```c
typedef enum {
    // Inputs (0x01-0x0F)
    CH_TYPE_DIGITAL_INPUT   = 0x01,
    CH_TYPE_ANALOG_INPUT    = 0x02,
    CH_TYPE_FREQUENCY_INPUT = 0x03,
    CH_TYPE_CAN_INPUT       = 0x04,

    // Outputs (0x10-0x1F)
    CH_TYPE_POWER_OUTPUT    = 0x10,
    CH_TYPE_PWM_OUTPUT      = 0x11,
    CH_TYPE_HBRIDGE         = 0x12,
    CH_TYPE_CAN_OUTPUT      = 0x13,

    // Virtual (0x20-0x2F)
    CH_TYPE_TIMER           = 0x20,
    CH_TYPE_LOGIC           = 0x21,
    CH_TYPE_MATH            = 0x22,
    CH_TYPE_TABLE_2D        = 0x23,
    CH_TYPE_TABLE_3D        = 0x24,
    CH_TYPE_FILTER          = 0x25,
    CH_TYPE_PID             = 0x26,
    CH_TYPE_NUMBER          = 0x27,
    CH_TYPE_SWITCH          = 0x28,
    CH_TYPE_ENUM            = 0x29,
    CH_TYPE_COUNTER         = 0x2A,
    CH_TYPE_HYSTERESIS      = 0x2B,
    CH_TYPE_FLIPFLOP        = 0x2C,

    // System (0xF0-0xFF)
    CH_TYPE_SYSTEM          = 0xF0,
} ChannelType_t;
```

### 5.2 Hardware Device Types

```c
typedef enum {
    HW_DEVICE_NONE    = 0x00,
    HW_DEVICE_GPIO    = 0x01,
    HW_DEVICE_ADC     = 0x02,
    HW_DEVICE_PWM     = 0x03,
    HW_DEVICE_DAC     = 0x04,
    HW_DEVICE_PROFET  = 0x05,
    HW_DEVICE_HBRIDGE = 0x06,
    HW_DEVICE_CAN     = 0x07,
    HW_DEVICE_FREQ    = 0x08,
} HwDevice_t;
```

### 5.3 Channel ID Ranges

| Range | Purpose | Examples |
|-------|---------|----------|
| 0-99 | Physical inputs | Digital inputs, analog inputs |
| 100-199 | Physical outputs | Power outputs, H-bridges |
| 200-999 | Virtual channels | Logic, timers, tables |
| 1000-1023 | System channels | Battery voltage, temperature |

---

## 6. Type-Specific Configurations

### 6.1 Digital Input (4 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | active_high | 1 = active high, 0 = active low |
| 1 | 1 | use_pullup | Enable internal pull-up |
| 2 | 2 | debounce_ms | Debounce time in milliseconds |

### 6.2 Analog Input (20 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | raw_min | Minimum raw ADC value |
| 4 | 4 | raw_max | Maximum raw ADC value |
| 8 | 4 | scaled_min | Minimum scaled output |
| 12 | 4 | scaled_max | Maximum scaled output |
| 16 | 2 | filter_ms | Filter time constant |
| 18 | 1 | filter_type | Filter type (0=none, 1=LP, 2=avg) |
| 19 | 1 | samples | Number of samples to average |

### 6.3 Power Output (12 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | current_limit_ma | Current limit in milliamps |
| 2 | 2 | inrush_time_ms | Inrush time window |
| 4 | 2 | inrush_limit_ma | Inrush current limit |
| 6 | 1 | retry_count | Fault retry attempts |
| 7 | 1 | retry_delay_s | Delay between retries |
| 8 | 2 | pwm_frequency | PWM frequency (0 = DC) |
| 10 | 1 | soft_start_ms | Soft start ramp time |
| 11 | 1 | flags | Output flags |

### 6.4 Logic (24 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | operation | Logic operation code |
| 1 | 1 | input_count | Number of inputs used |
| 2 | 16 | inputs[8] | Input channel IDs (8 x uint16) |
| 18 | 4 | compare_value | Comparison value |
| 22 | 1 | invert_output | Invert result |
| 23 | 1 | reserved | Reserved |

**Logic Operations:**

| Code | Operation | Description |
|------|-----------|-------------|
| 0 | AND | All inputs true |
| 1 | OR | Any input true |
| 2 | XOR | Odd number of inputs true |
| 3 | NOT | Invert single input |
| 4 | NAND | NOT AND |
| 5 | NOR | NOT OR |
| 6 | GT | Input > compare_value |
| 7 | LT | Input < compare_value |
| 8 | EQ | Input == compare_value |
| 9 | NE | Input != compare_value |
| 10 | GE | Input >= compare_value |
| 11 | LE | Input <= compare_value |

### 6.5 Math (32 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | operation | Math operation code |
| 1 | 1 | input_count | Number of inputs used |
| 2 | 16 | inputs[8] | Input channel IDs |
| 18 | 4 | constant | Constant value for operations |
| 22 | 4 | min_value | Output minimum clamp |
| 26 | 4 | max_value | Output maximum clamp |
| 30 | 2 | scale_num | Scale numerator |
| 32 | 2 | scale_den | Scale denominator |

**Math Operations:**

| Code | Operation | Description |
|------|-----------|-------------|
| 0 | ADD | Sum of all inputs |
| 1 | SUB | input[0] - input[1] |
| 2 | MUL | Product of all inputs |
| 3 | DIV | input[0] / input[1] |
| 4 | MOD | input[0] % input[1] |
| 5 | MIN | Minimum of inputs |
| 6 | MAX | Maximum of inputs |
| 7 | AVG | Average of inputs |
| 8 | ABS | Absolute value |
| 9 | NEG | Negate value |
| 10 | SCALE | (input * scale_num) / scale_den |
| 11 | CLAMP | Clamp to min/max |
| 12 | MAP | Linear interpolation |

### 6.6 Timer (16 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | mode | Timer mode |
| 1 | 1 | trigger_mode | Trigger edge mode |
| 2 | 2 | trigger_id | Trigger channel ID |
| 4 | 4 | delay_ms | Delay time in milliseconds |
| 8 | 2 | on_time_ms | On time for flasher |
| 10 | 2 | off_time_ms | Off time for flasher |
| 12 | 1 | auto_reset | Auto-reset on completion |
| 13 | 3 | reserved | Reserved |

**Timer Modes:**

| Code | Mode | Description |
|------|------|-------------|
| 0 | DELAY_ON | Delay before turning on |
| 1 | DELAY_OFF | Delay before turning off |
| 2 | PULSE | Single pulse of delay_ms |
| 3 | FLASHER | Alternating on/off |
| 4 | STOPWATCH | Count up while trigger active |

### 6.7 Table 2D (68 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | input_id | X-axis input channel |
| 2 | 1 | point_count | Number of table points |
| 3 | 1 | reserved | Reserved |
| 4 | 32 | x_values[16] | X-axis values (16 x int16) |
| 36 | 32 | y_values[16] | Y-axis values (16 x int16) |

### 6.8 Filter (8 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | input_id | Input channel ID |
| 2 | 1 | filter_type | Filter type |
| 3 | 1 | window_size | Moving average window |
| 4 | 2 | time_constant_ms | Low-pass time constant |
| 6 | 1 | alpha | EMA alpha (0-255) |
| 7 | 1 | reserved | Reserved |

**Filter Types:**

| Code | Type | Description |
|------|------|-------------|
| 0 | LOW_PASS | First-order low-pass |
| 1 | MOVING_AVG | Moving average |
| 2 | MEDIAN | Median filter |
| 3 | EMA | Exponential moving average |

### 6.9 PID (22 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | setpoint_id | Setpoint channel ID |
| 2 | 2 | feedback_id | Feedback channel ID |
| 4 | 2 | kp | Proportional gain (x1000) |
| 6 | 2 | ki | Integral gain (x1000) |
| 8 | 2 | kd | Derivative gain (x1000) |
| 10 | 2 | output_min | Minimum output |
| 12 | 2 | output_max | Maximum output |
| 14 | 2 | integral_min | Integral windup min |
| 16 | 2 | integral_max | Integral windup max |
| 18 | 2 | deadband | Deadband zone |
| 20 | 1 | d_on_measurement | D on measurement vs error |
| 21 | 1 | reserved | Reserved |

### 6.10 Counter (16 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | trigger_id | Trigger channel ID |
| 2 | 2 | reset_id | Reset channel ID |
| 4 | 4 | min_value | Minimum count value |
| 8 | 4 | max_value | Maximum count value |
| 12 | 1 | direction | Count direction (0=up, 1=down) |
| 13 | 1 | wrap | Wrap around on overflow |
| 14 | 2 | step | Count step size |

### 6.11 Hysteresis (12 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | input_id | Input channel ID |
| 2 | 2 | reserved | Reserved |
| 4 | 4 | threshold_high | Upper threshold |
| 8 | 4 | threshold_low | Lower threshold |

### 6.12 FlipFlop (8 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | set_id | Set input channel ID |
| 2 | 2 | reset_id | Reset input channel ID |
| 4 | 1 | mode | FlipFlop mode |
| 5 | 1 | default_state | Initial state |
| 6 | 2 | reserved | Reserved |

**FlipFlop Modes:**

| Code | Mode | Description |
|------|------|-------------|
| 0 | SR | Set-Reset latch |
| 1 | D | D-type (set follows input) |
| 2 | T | Toggle on rising edge |
| 3 | JK | JK flip-flop |

---

## 7. Usage Examples

### 7.1 Python: Load Configuration

```python
from shared.python.channel_config import ConfigFile

# Load from file
config = ConfigFile.load("my_config.pmu30")

print(f"Channels: {len(config.channels)}")
for ch in config.channels:
    print(f"  [{ch.id}] {ch.name} ({ch.type.name})")
```

### 7.2 Python: Create Configuration

```python
from shared.python.channel_config import (
    ConfigFile, Channel, ChannelType, ChannelFlags,
    HwDevice, CfgLogic, CfgPowerOutput
)

# Create new config
config = ConfigFile(device_type=0x0030)

# Add logic channel
logic = Channel(
    id=200,
    type=ChannelType.LOGIC,
    flags=ChannelFlags.ENABLED,
    name="FanEnable",
    config=CfgLogic(
        operation=6,  # GT
        input_count=1,
        inputs=[50],  # Coolant temp channel
        compare_value=850  # 85.0 degrees
    )
)
config.channels.append(logic)

# Add power output
output = Channel(
    id=100,
    type=ChannelType.POWER_OUTPUT,
    flags=ChannelFlags.ENABLED,
    hw_device=HwDevice.PROFET,
    hw_index=0,
    source_id=200,  # Connected to logic channel
    name="FanRelay",
    config=CfgPowerOutput(
        current_limit_ma=25000
    )
)
config.channels.append(output)

# Save to file
config.save("fan_control.pmu30")
```

### 7.3 Python: Send to Device

```python
from configurator.src.models.binary_config import BinaryConfigManager

manager = BinaryConfigManager()
manager.load_from_file("my_config.pmu30")

# Serialize for transmission
binary_data = manager.to_bytes()

# Send via protocol
protocol.upload_config(binary_data)
```

### 7.4 C: Load Configuration in Firmware

```c
#include "channel_config.h"

// Binary config received from configurator
const uint8_t* config_data;
uint16_t config_size;

// Validate header
CfgFileHeader_t* header = (CfgFileHeader_t*)config_data;
if (header->magic != CFG_MAGIC) {
    return ERROR_INVALID_MAGIC;
}

// Verify CRC
uint32_t calc_crc = crc32(config_data + sizeof(CfgFileHeader_t),
                          header->total_size - sizeof(CfgFileHeader_t));
if (calc_crc != header->crc32) {
    return ERROR_CRC_MISMATCH;
}

// Parse channels
uint8_t* ptr = config_data + sizeof(CfgFileHeader_t);
for (uint16_t i = 0; i < header->channel_count; i++) {
    CfgChannelHeader_t* ch = (CfgChannelHeader_t*)ptr;
    ptr += sizeof(CfgChannelHeader_t);

    // Read name
    char name[32];
    memcpy(name, ptr, ch->name_len);
    name[ch->name_len] = '\0';
    ptr += ch->name_len;

    // Read type-specific config
    void* config = ptr;
    ptr += ch->config_size;

    // Register channel
    PMU_ChannelExec_AddChannel(ch->id, ch->type, config);
}
```

---

## See Also

- [Channels Reference](channels.md) - Channel ID ranges and types
- [Logic Functions Reference](logic-functions.md) - Logic operations
- [Protocol Reference](protocol.md) - Communication protocol
- [Shared Library Documentation](../BINARY_CONFIG_ARCHITECTURE.md) - Shared library architecture

---

**Copyright 2026 R2 m-sport. All rights reserved.**

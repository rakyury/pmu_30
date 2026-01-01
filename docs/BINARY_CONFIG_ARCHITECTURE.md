# Binary Configuration Architecture

**Version:** 1.0 | **Date:** January 2026 | **Author:** R2 m-sport

---

## Overview

The PMU-30 system uses a **unified binary configuration format** across all components. This eliminates format conversion issues and ensures consistency between firmware and configurator.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SHARED LIBRARY                               │
├─────────────────────────────────────────────────────────────────────┤
│  shared/                                                             │
│  ├── channel_config.h       C binary structures                     │
│  ├── channel_config.c       C serialization/deserialization         │
│  ├── channel_executor.h     Channel execution API                   │
│  ├── channel_executor.c     Shared channel processing               │
│  ├── engine/                Logic Engine (pure functions)           │
│  │   ├── logic_engine.h                                             │
│  │   ├── logic.c            AND, OR, comparisons                    │
│  │   ├── math.c             ADD, MUL, scale, clamp                  │
│  │   ├── timer.c            Delay, pulse, flasher                   │
│  │   ├── filter.c           Low-pass, moving average                │
│  │   ├── table.c            2D/3D interpolation                     │
│  │   ├── pid.c              PID controller                          │
│  │   ├── counter.c          Up/down counter                         │
│  │   ├── hysteresis.c       Threshold with hysteresis               │
│  │   └── flipflop.c         SR, D, T, JK latches                    │
│  └── python/                                                         │
│      └── channel_config.py  Python port of binary structures        │
└─────────────────────────────────────────────────────────────────────┘
                    │                           │
                    │                           │
         ┌──────────▼──────────┐     ┌──────────▼──────────┐
         │      FIRMWARE       │     │    CONFIGURATOR     │
         │      (C/STM32)      │     │    (Python/Qt)      │
         ├─────────────────────┤     ├─────────────────────┤
         │ pmu_channel_exec.c  │     │ binary_config.py    │
         │ - Firmware adapter  │     │ - Config manager    │
         │ - HAL integration   │     │ - UI integration    │
         │ - 500Hz execution   │     │ - File I/O          │
         └─────────────────────┘     └─────────────────────┘
                    │                           │
                    └───────────┬───────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    .pmu30 Binary      │
                    │    Configuration      │
                    │    File               │
                    └───────────────────────┘
```

## Key Principles

| Principle | Description |
|-----------|-------------|
| **No JSON** | Binary format only throughout the system |
| **One Format** | Identical binary format for firmware and configurator |
| **Shared Code** | C and Python implementations mirror each other |
| **CRC Verified** | All configs protected by CRC-32 |
| **Pure Functions** | Logic Engine has no side effects |

## File Format

Binary configuration files use the `.pmu30` extension:

```
┌────────────────────────────────┐
│  File Header (32 bytes)        │
│  - Magic: 0x43464733 ("CFG3")  │
│  - Version, device type        │
│  - CRC-32 checksum             │
│  - Channel count               │
├────────────────────────────────┤
│  Channel 0                     │
│  ├─ Header (14 bytes)          │
│  ├─ Name (0-31 bytes)          │
│  └─ Config (type-specific)     │
├────────────────────────────────┤
│  Channel 1...N                 │
└────────────────────────────────┘
```

## Data Flow

### Configurator to Firmware

```
1. User edits configuration in Configurator UI
2. BinaryConfigManager creates Channel objects
3. ConfigFile.serialize() produces binary data
4. Binary sent to firmware via protocol (UPLOAD_CONFIG command)
5. PMU_ChannelExec_LoadConfig() parses binary
6. Channels registered with executor
7. PMU_ChannelExec_Update() runs at 500Hz
```

### Firmware to Configurator

```
1. Firmware calls ConfigFile.serialize()
2. Binary sent via protocol (DOWNLOAD_CONFIG command)
3. BinaryConfigManager.load_from_bytes() parses
4. ConfigManager populates UI with channel data
```

### File Save/Load

```
# Save
config = ConfigFile(device_type=0x0030)
config.channels = [...channels...]
config.save("project.pmu30")

# Load
config = ConfigFile.load("project.pmu30")
for ch in config.channels:
    print(ch.name, ch.type)
```

## Channel Execution

The Channel Executor processes virtual channels:

```
PMU_ChannelExec_Update()
    │
    ├─► Update timing (delta_ms calculation)
    │
    ├─► For each enabled channel:
    │       │
    │       ├─► Read input channel values
    │       │       ↓
    │       ├─► Execute via Logic Engine
    │       │   (Logic_Evaluate, Math_Evaluate, Timer_Update, etc.)
    │       │       ↓
    │       └─► Write result to output channel
    │
    └─► Execution complete
```

## Shared Library Components

### channel_config.h/c

Binary structure definitions and serialization:

```c
// File header
typedef struct {
    uint32_t magic;         // 0x43464733
    uint16_t version;       // 2
    uint16_t device_type;
    uint32_t total_size;
    uint32_t crc32;
    uint16_t channel_count;
    uint16_t flags;
    uint32_t timestamp;
    uint8_t  reserved[8];
} CfgFileHeader_t;

// Channel header
typedef struct {
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

### channel_executor.h/c

Channel processing and runtime state:

```c
// Initialize executor
void Exec_Init(ExecContext_t* ctx,
               Exec_GetValueFunc get_value,
               Exec_SetValueFunc set_value,
               void* user_data);

// Process single channel
int32_t Exec_ProcessChannel(ExecContext_t* ctx,
                            ChannelRuntime_t* runtime);

// Update timing
void Exec_UpdateTime(ExecContext_t* ctx, uint32_t now_ms);
```

### Logic Engine (shared/engine/)

Pure calculation functions with no side effects:

```c
// Logic operations
int32_t Logic_Evaluate(const CfgLogic_t* cfg,
                       const int32_t* inputs);

// Math operations
int32_t Math_Evaluate(const CfgMath_t* cfg,
                      const int32_t* inputs);

// Timer processing
int32_t Timer_Update(TimerState_t* state,
                     const CfgTimer_t* cfg,
                     int32_t trigger,
                     uint32_t delta_ms);

// Filter processing
int32_t Filter_Update(FilterState_t* state,
                      const CfgFilter_t* cfg,
                      int32_t input);
```

## Firmware Integration

The firmware adapter (`pmu_channel_exec.c`) bridges shared library to HAL:

```c
// Callbacks to firmware channel registry
static int32_t ExecGetValue(uint16_t channel_id, void* user_data) {
    return PMU_Channel_GetValue(channel_id);
}

static void ExecSetValue(uint16_t channel_id, int32_t value, void* user_data) {
    PMU_Channel_SetValue(channel_id, value);
}

// Main loop integration
void vControlTask(void* params) {
    while (1) {
        vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(2));  // 500Hz

        PMU_ADC_Update();           // Read physical inputs
        PMU_Channel_Update();       // Sync to registry
        PMU_ChannelExec_Update();   // Execute virtual channels
        PMU_PROFET_Update();        // Update outputs
    }
}
```

## Configurator Integration

The configurator uses `BinaryConfigManager` for all config operations:

```python
from configurator.src.models.binary_config import BinaryConfigManager

# Create new config
manager = BinaryConfigManager()
manager.new_config()

# Add channels
channel = manager.create_logic_channel(
    name="FanEnable",
    operation=6,  # GT
    inputs=[50],
    compare_value=850
)
manager.add_channel(channel)

# Save to file
manager.save_to_file("project.pmu30")

# Send to device
binary_data = manager.to_bytes()
protocol.upload_config(binary_data)
```

## Channel Types

| Type | Code | Config Size | Description |
|------|------|-------------|-------------|
| DIGITAL_INPUT | 0x01 | 4 bytes | Digital input with debounce |
| ANALOG_INPUT | 0x02 | 20 bytes | ADC with scaling |
| FREQUENCY_INPUT | 0x03 | 20 bytes | Frequency counter |
| CAN_INPUT | 0x04 | 18 bytes | CAN signal extraction |
| POWER_OUTPUT | 0x10 | 12 bytes | PROFET high-side switch |
| TIMER | 0x20 | 16 bytes | Delay, pulse, flasher |
| LOGIC | 0x21 | 24 bytes | Boolean operations |
| MATH | 0x22 | 32 bytes | Arithmetic operations |
| TABLE_2D | 0x23 | 68 bytes | 1D lookup table |
| FILTER | 0x25 | 8 bytes | Signal filtering |
| PID | 0x26 | 22 bytes | PID controller |
| COUNTER | 0x2A | 16 bytes | Up/down counter |
| HYSTERESIS | 0x2B | 12 bytes | Threshold with hysteresis |
| FLIPFLOP | 0x2C | 8 bytes | SR/D/T/JK latch |

## Testing

Both C and Python implementations are tested against the same test vectors:

```python
# tests/test_binary_config.py
def test_roundtrip():
    """Config survives serialize/deserialize cycle"""
    config = ConfigFile(device_type=0x0030)
    config.channels.append(create_test_channel())

    binary = config.serialize()
    loaded = ConfigFile.deserialize(binary)

    assert len(loaded.channels) == 1
    assert loaded.channels[0].name == "Test"
```

```c
// tests/test_channel_config.c
void test_roundtrip(void) {
    CfgFileHeader_t header = {.magic = CFG_MAGIC, ...};
    uint8_t buffer[256];

    serialize_header(&header, buffer);
    CfgFileHeader_t loaded;
    deserialize_header(buffer, &loaded);

    TEST_ASSERT_EQUAL(header.magic, loaded.magic);
}
```

## Migration from JSON

Legacy JSON configurations can be converted to binary format using the configurator:

1. Open JSON config in configurator (legacy import)
2. Save as `.pmu30` binary file
3. Update firmware to receive binary config

Note: The firmware no longer supports JSON parsing. All new configurations must use binary format.

---

## See Also

- [Configuration Reference](reference/configuration.md) - Binary format specification
- [Channels Reference](reference/channels.md) - Channel ID ranges
- [Logic Functions Reference](reference/logic-functions.md) - Logic operations
- [Firmware Architecture](firmware_architecture.md) - System architecture

---

**Copyright 2026 R2 m-sport. All rights reserved.**

# Shared Protocol Library Proposal

## Problem Statement

Current architecture has **two separate implementations** of critical logic:

| Component | Firmware (C) | Configurator (Python) |
|-----------|--------------|----------------------|
| Protocol framing | `pmu_protocol.c` | `protocol.py` |
| CRC-CCITT | `PMU_Protocol_CRC16()` | `calc_crc()` |
| JSON parsing | `pmu_config_json.c` | `config_schema.py` |
| Telemetry format | `Protocol_SendTelemetry()` | `telemetry.py` |

**Issues encountered:**
1. CRC algorithm mismatch (Modbus vs CRC-CCITT)
2. Length field interpretation (payload only vs payload+cmd)
3. Telemetry format differences between platforms
4. JSON schema drift between implementations

**Time lost:** 4+ hours debugging protocol mismatches

---

## Proposed Solution: Shared C Library

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    pmu_protocol_shared                       │
│  (Pure C library - no HAL/OS dependencies)                   │
├─────────────────────────────────────────────────────────────┤
│  protocol.h / protocol.c                                     │
│  ├── PMU_Protocol_BuildFrame()                               │
│  ├── PMU_Protocol_ParseFrame()                               │
│  ├── PMU_Protocol_CRC16()                                    │
│  └── PMU_Protocol_ValidateFrame()                            │
├─────────────────────────────────────────────────────────────┤
│  telemetry.h / telemetry.c                                   │
│  ├── PMU_Telemetry_Pack()                                    │
│  ├── PMU_Telemetry_Unpack()                                  │
│  └── PMU_Telemetry_Format (struct definition)                │
├─────────────────────────────────────────────────────────────┤
│  config_json.h / config_json.c                               │
│  ├── PMU_Config_ParseJSON()                                  │
│  ├── PMU_Config_SerializeJSON()                              │
│  └── PMU_Config_Validate()                                   │
└─────────────────────────────────────────────────────────────┘
          │                           │
          ▼                           ▼
┌─────────────────────┐    ┌─────────────────────────┐
│   STM32 Firmware    │    │   Python Configurator   │
│                     │    │                         │
│  #include "proto.h" │    │  from ctypes import *   │
│  Uses directly as   │    │  lib = CDLL("pmu.dll")  │
│  static library     │    │  lib.PMU_Protocol_*     │
└─────────────────────┘    └─────────────────────────┘
```

### Build Targets

```
shared/
├── CMakeLists.txt
├── include/
│   ├── pmu_protocol.h
│   ├── pmu_telemetry.h
│   └── pmu_config.h
├── src/
│   ├── pmu_protocol.c
│   ├── pmu_telemetry.c
│   └── pmu_config.c
├── bindings/
│   └── python/
│       └── pmu_protocol.py   # ctypes wrapper
└── tests/
    ├── test_protocol.c
    └── test_protocol.py      # Same tests, both languages
```

### Build Commands

```bash
# Build for desktop (Windows DLL)
cmake -B build_desktop -DBUILD_SHARED=ON
cmake --build build_desktop

# Build for embedded (static library)
cmake -B build_stm32 -DCMAKE_TOOLCHAIN_FILE=arm-gcc.cmake
cmake --build build_stm32

# Run tests on desktop
ctest --test-dir build_desktop
python -m pytest tests/
```

---

## Implementation Plan

### Phase 1: Extract Protocol Core (2-3 hours)

1. Create `shared/` directory
2. Extract CRC, frame building, frame parsing from `pmu_protocol.c`
3. Create minimal C API without HAL dependencies
4. Build as static library for STM32

### Phase 2: Python Bindings (1-2 hours)

1. Build shared library as DLL/SO for desktop
2. Create ctypes wrapper in Python
3. Replace Python protocol implementation with C calls

### Phase 3: Telemetry Format (2-3 hours)

1. Define telemetry struct in C header
2. Pack/unpack functions in C
3. Python uses same C functions via bindings

### Phase 4: JSON Config (3-4 hours)

1. Extract JSON parsing logic
2. Use cJSON for both platforms
3. Schema validation in C

---

## Benefits

| Metric | Before | After |
|--------|--------|-------|
| Protocol bugs | Common | Impossible (same code) |
| Debug time | Hours | Minutes |
| Test coverage | Separate tests | Unified tests |
| Feature parity | Manual sync | Automatic |

---

## Alternative: Code Generation

If C library approach is complex, consider:

1. **Protocol Buffers** - Define protocol in .proto, generate C and Python
2. **FlatBuffers** - Zero-copy, efficient for embedded
3. **Custom DSL** - Define protocol in YAML, generate both implementations

### Proto Example

```protobuf
message TelemetryPacket {
  uint32 timestamp_ms = 1;
  uint32 voltage_mv = 2;
  int32 temperature_c = 3;
  repeated uint32 adc_values = 4;
  repeated OutputState outputs = 5;
}
```

---

## Recommendation

**Start with Phase 1: Extract Protocol Core**

This gives immediate benefits:
- CRC guaranteed identical
- Frame format guaranteed identical  
- Can test protocol on desktop before deploying

The cJSON library already exists in firmware - reusing it for Python (via ctypes) ensures JSON parsing is identical.

---

## Quick Win: Shared Test Suite

Even without shared library, create **unified test cases**:

```python
# tests/protocol_test_vectors.py
TEST_VECTORS = [
    {
        "name": "PING command",
        "frame": bytes([0xAA, 0x00, 0x00, 0x01, 0xE1, 0x1A]),
        "cmd": 0x01,
        "payload": b"",
    },
    {
        "name": "START_STREAM",
        "frame": bytes([0xAA, 0x02, 0x00, 0x30, 0x64, 0x00, 0xAB, 0xCD]),
        "cmd": 0x30,
        "payload": bytes([0x64, 0x00]),  # 100Hz
    },
]
```

Run same vectors against both C and Python implementations to catch drift.

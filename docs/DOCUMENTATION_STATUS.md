# Documentation Status Report

This document tracks the accuracy of documentation compared to the actual implementation.

**Last Updated:** 2024-12-29

## Summary

| Status | Count | Description |
|--------|-------|-------------|
| 🔴 Critical | 3 | Documentation completely wrong |
| 🟠 High | 3 | Significant discrepancies |
| 🟡 Medium | 2 | Minor issues or missing docs |
| ✅ OK | 7 | Documentation matches implementation |

---

## Critical Issues 🔴

### 1. Protocol Message IDs — Complete Mismatch

**File:** [docs/protocol_specification.md](protocol_specification.md) (Lines 50-67)

| Documented ID | Documented Name | Actual ID | Actual Name |
|---------------|-----------------|-----------|-------------|
| 0x02 | PONG | 0x02 | PMU_CMD_GET_VERSION |
| 0x10 | GET_INFO | 0x10 | (not used) |
| 0x20 | GET_CONFIG | 0x20 | PMU_CMD_START_STREAM |
| 0x21 | CONFIG_DATA | 0x21 | PMU_CMD_STOP_STREAM |
| 0x22 | SET_CONFIG | 0x22 | PMU_CMD_GET_OUTPUTS |
| 0x40 | SUBSCRIBE_TELEMETRY | 0x40 | PMU_CMD_SET_OUTPUT |
| 0x41 | UNSUBSCRIBE_TELEMETRY | 0x41 | PMU_CMD_SET_PWM |
| 0x42 | TELEMETRY_DATA | 0x42 | PMU_CMD_SET_HBRIDGE |

**Actual Implementation:** [firmware/include/pmu_protocol.h](../firmware/include/pmu_protocol.h) (Lines 46-114)

**Impact:** Critical — Any client using documented message IDs will fail to communicate with firmware.

**Action Required:** Regenerate protocol documentation from firmware source.

---

### 2. Telemetry Message Codes — Wrong Codes

**File:** [docs/telemetry.md](telemetry.md) (Lines 34-55)

| Documented | Actual |
|------------|--------|
| 0x30 = Subscribe to Telemetry | 0x20 = PMU_CMD_START_STREAM |
| 0x31 = Unsubscribe Telemetry | 0x21 = PMU_CMD_STOP_STREAM |
| 0x32 = Telemetry Data Packet | 0xE3 = Response DATA |

**Impact:** Critical — Telemetry subscription will not work with documented codes.

---

### 3. Telemetry Packet Size — Internal Contradiction

**Contradiction within documentation itself:**

| File | Claimed Size |
|------|--------------|
| [protocol_specification.md](protocol_specification.md) (Line 141) | 119 bytes |
| [telemetry.md](telemetry.md) (Line 55) | 174 bytes |

**Impact:** Critical — Developers will implement wrong packet parsing.

---

## High Priority Issues 🟠

### 4. System Channel ID Range

**File:** [docs/channels.md](channels.md) (Line 50)

| Documented | Actual |
|------------|--------|
| 1000-1099 | 1000-1023 |

**Source:** [firmware/include/pmu_channel.h](../firmware/include/pmu_channel.h) (Line 136)

```c
#define PMU_CHANNEL_SYSTEM_MAX      1023  // NOT 1099
```

---

### 5. Configurator Launch Path

**File:** [docs/configurator/README.md](configurator/README.md) (Line 32)

| Documented | Actual |
|------------|--------|
| `main.py` from configurator directory | `configurator/src/main.py` |

**Fix:** Update README to show correct path.

---

### 6. Missing Protocol Documentation

The following protocol command groups are implemented but NOT documented:

| Command Group | ID Range | Implementation |
|---------------|----------|----------------|
| Lua Scripting | 0xB0-0xB8 | pmu_protocol.h |
| Firmware Update | 0xC0-0xC3 | pmu_protocol.h |
| Data Logging | 0x80-0x84 | pmu_protocol.h |
| Diagnostics | 0xA0-0xA3 | pmu_protocol.h |
| Response Codes | 0xE0-0xE3 | pmu_protocol.h |

---

## Medium Priority Issues 🟡

### 7. Undocumented System Channels

**File:** [docs/firmware_architecture.md](firmware_architecture.md) (Lines 247-259)

These system channels exist in firmware but are NOT in documentation:

```c
#define PMU_CHANNEL_SYSTEM_USER_ERROR       1008
#define PMU_CHANNEL_SYSTEM_5V_OUTPUT        1009
#define PMU_CHANNEL_SYSTEM_3V3_OUTPUT       1010
#define PMU_CHANNEL_SYSTEM_IS_TURNING_OFF   1011
```

**Source:** [firmware/include/pmu_channel.h](../firmware/include/pmu_channel.h) (Lines 158-162)

---

### 8. Output Count Mismatch

**File:** [docs/configurator/ui-overview.md](configurator/ui-overview.md)

| Documented | Actual |
|------------|--------|
| "40 power outputs" in LED bar | 30 PROFET + 4 H-Bridge = 34 channels |

---

## Documentation Matches Implementation ✅

| Component | Documentation | Implementation | Status |
|-----------|---------------|----------------|--------|
| Channel Architecture | channels.md | pmu_channel.h | ✅ |
| PROFET States | firmware_architecture.md | pmu_profet.h | ✅ |
| Logic Functions | api/logic-functions/ | pmu_logic.h | ✅ |
| H-Bridge Modes | firmware_architecture.md | pmu_hbridge.h | ✅ |
| Analog Inputs (20 pins, 12-bit) | configurator/analog-inputs.md | pmu_adc.h | ✅ |
| Digital Inputs (20 pins) | configurator/digital-inputs.md | pmu_gpio.h | ✅ |
| Frame Structure | protocol_specification.md | pmu_protocol.h | ✅ |

---

## Recommended Actions

### Immediate (Critical)

1. **Regenerate protocol_specification.md** from actual firmware headers
2. **Fix telemetry.md** with correct message codes (0x20/0x21)
3. **Resolve packet size contradiction** — verify actual size in firmware

### Short-term (High)

4. **Update channels.md** — change range to 1000-1023
5. **Fix configurator README** — correct launch path
6. **Document missing protocols** — Lua, FW update, logging, diagnostics

### Medium-term

7. **Add system channels 1008-1011** to firmware_architecture.md
8. **Fix output count** in ui-overview.md (34 not 40)

---

## Version History

| Date | Author | Changes |
|------|--------|---------|
| 2024-12-29 | Claude Code | Initial analysis report |

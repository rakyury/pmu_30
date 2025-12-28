# PMU-30 Configuration Synchronization

## Overview

This document explains how configuration changes made in the Configurator application are applied to the PMU-30 firmware, including the difference between full configuration uploads and real-time parameter updates.

## Configuration Update Methods

The PMU-30 supports two main approaches for applying configuration changes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Configuration Update Methods                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────────────────┐     ┌───────────────────────────────────┐  │
│   │  FULL CONFIG UPLOAD       │     │  REAL-TIME PARAMETER UPDATE       │  │
│   │                           │     │                                   │  │
│   │  SET_CONFIG (0x22)        │     │  SET_CHANNEL (0x40)               │  │
│   │                           │     │  SET_HBRIDGE (0x42)               │  │
│   │  • Uploads entire JSON    │     │                                   │  │
│   │  • ~32KB max              │     │  • Single value change            │  │
│   │  • Chunked transfer       │     │  • Immediate effect               │  │
│   │  • Device parses & applies│     │  • No config reload               │  │
│   │  • Use for structural     │     │  • Use for live tuning            │  │
│   │    changes                │     │                                   │  │
│   └───────────────────────────┘     └───────────────────────────────────┘  │
│                                                                              │
│   Use Cases:                        Use Cases:                              │
│   • Adding/removing channels        • Adjusting thresholds                  │
│   • Changing channel references     • Tuning PID parameters                 │
│   • Modifying channel structure     • Testing output states                 │
│   • First-time configuration        • Live calibration                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Full Configuration Upload

When you make structural changes (adding channels, modifying channel types, changing references), the Configurator uploads the entire configuration:

### Protocol Flow

```
Configurator                         PMU-30 Device
     │                                     │
     │  SET_CONFIG (0x22)                  │
     │  [chunk 0/N] [4000 bytes JSON]      │
     │────────────────────────────────────►│
     │                                     │
     │  SET_CONFIG (0x22)                  │
     │  [chunk 1/N] [4000 bytes JSON]      │
     │────────────────────────────────────►│
     │              ...                    │
     │  SET_CONFIG (0x22)                  │
     │  [chunk N/N] [remaining bytes]      │
     │────────────────────────────────────►│
     │                                     │ Parse JSON
     │                                     │ Validate config
     │                                     │ Apply to RAM
     │  CONFIG_ACK (0x23)                  │
     │  [success=1, error_code=0]          │
     │◄────────────────────────────────────│
     │                                     │
```

### SET_CONFIG Payload (0x22)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | chunk_index | Current chunk number (0-based) |
| 2 | 2 | total_chunks | Total number of chunks |
| 4 | N | json_data | JSON configuration fragment |

### CONFIG_ACK Payload (0x23)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | success | 1 = success, 0 = failure |
| 1 | 2 | error_code | Error code if failed |

### Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0x00 | OK | Configuration applied successfully |
| 0x01 | PARSE_ERROR | JSON parsing failed |
| 0x02 | VALIDATION_ERROR | Configuration validation failed |
| 0x03 | MEMORY_ERROR | Insufficient memory |
| 0x04 | TIMEOUT | Transfer timeout |
| 0x05 | CRC_ERROR | Checksum mismatch |

### Example: Upload Configuration

```python
from controllers.device_controller import DeviceController

controller = DeviceController()
controller.connect({"type": "Emulator", "host": "localhost", "port": 5555})

# Build configuration
config = {
    "version": "3.0",
    "device": {"name": "My PMU"},
    "channels": [
        {"id": "ignition", "channel_type": "digital_input", "input_pin": 0},
        {"id": "fuel_pump", "channel_type": "power_output", "output_pins": [0],
         "source_channel": "ignition"}
    ]
}

# Upload to device (RAM only)
success = controller.write_configuration(config)

if success:
    print("Configuration uploaded to device RAM")

    # Optionally persist to flash
    if controller.save_to_flash():
        print("Configuration saved to flash")
```

## Real-Time Parameter Updates

For immediate value changes without full config reload, use real-time control commands:

### SET_CHANNEL (0x40)

Set a virtual channel's value directly. This is useful for:
- Testing logic functions
- Tuning PID setpoints
- Manual override of calculated values
- Live calibration

**Payload:**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | channel_id | Target channel ID (numeric) |
| 2 | 4 | value | New value (float, little-endian) |

**Response:** CHANNEL_ACK (0x41)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | channel_id | Channel that was updated |
| 2 | 1 | success | 1 = success, 0 = failure |
| 3 | 2 | error_code | Error code if failed |

### SET_HBRIDGE (0x42)

Control H-Bridge motor outputs in real-time.

**Payload:**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | bridge_id | H-Bridge number (0-3) |
| 1 | 1 | mode | Mode: 0=coast, 1=forward, 2=reverse, 3=brake |
| 2 | 2 | pwm | PWM duty cycle (0-1000 = 0-100%) |

### When to Use Each Method

| Scenario | Method | Reason |
|----------|--------|--------|
| Add new channel | Full upload | Structural change |
| Change channel type | Full upload | Structural change |
| Modify channel references | Full upload | Dependency changes |
| Adjust current limit | Full upload | Channel property |
| Test output manually | SET_CHANNEL | Immediate effect |
| Tune PID gains | SET_CHANNEL | Live tuning |
| Manual motor control | SET_HBRIDGE | Direct control |
| Calibrate sensor | Full upload | Multi-point data |

## Configuration Lifecycle

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Configurator│    │  Protocol   │    │  Device     │    │   Flash     │
│    (UI)     │    │  (USB/WiFi) │    │    (RAM)    │    │  Storage    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       │ Edit channel     │                  │                  │
       │─────────►        │                  │                  │
       │                  │                  │                  │
       │ [User saves]     │                  │                  │
       │                  │                  │                  │
       │ SET_CONFIG       │                  │                  │
       │─────────────────►│                  │                  │
       │                  │ JSON chunks      │                  │
       │                  │─────────────────►│                  │
       │                  │                  │ Parse & Apply    │
       │                  │                  │────────┐         │
       │                  │                  │        │         │
       │                  │                  │◄───────┘         │
       │                  │ CONFIG_ACK       │                  │
       │◄─────────────────│◄─────────────────│                  │
       │                  │                  │                  │
       │ [Optional: persist]                 │                  │
       │                  │                  │                  │
       │ SAVE_TO_FLASH    │                  │                  │
       │─────────────────►│─────────────────►│                  │
       │                  │                  │ Write JSON       │
       │                  │                  │─────────────────►│
       │                  │                  │                  │
       │                  │ FLASH_ACK        │                  │
       │◄─────────────────│◄─────────────────│                  │
       │                  │                  │                  │
```

## RAM vs Flash Configuration

| Aspect | RAM (Active) | Flash (Persistent) |
|--------|--------------|-------------------|
| Modified by | SET_CONFIG | SAVE_TO_FLASH |
| Survives restart | No | Yes |
| Apply time | Immediate | After reboot |
| Size limit | ~48KB | ~32KB |
| Use case | Development, testing | Production deployment |

### Important Notes

1. **SET_CONFIG updates RAM only** - Changes take effect immediately but are lost on restart
2. **SAVE_TO_FLASH persists** - Must explicitly save to make changes permanent
3. **Restart loads from flash** - Device always boots from flash configuration
4. **No auto-save** - Configurator never auto-saves to flash without user action

## Atomic Updates (Future)

For individual parameter updates without full config upload, the protocol supports atomic channel updates:

### UPDATE_CHANNEL (Planned)

This command will allow updating a single channel's properties:

```json
{
    "channel_id": "fuel_pump",
    "updates": {
        "current_limit_a": 15.0,
        "inrush_time_ms": 150
    }
}
```

Benefits:
- Faster than full upload for single-parameter changes
- Maintains channel structure
- Immediate application
- Automatic RAM update

## Emulator-Specific Commands

When connected to the emulator, additional commands allow direct hardware simulation:

| Command | ID | Description |
|---------|-----|-------------|
| EMU_SET_DIGITAL_INPUT | 0x84 | Set digital input state |
| EMU_SET_ANALOG_INPUT | 0x86 | Set analog input voltage |
| EMU_SET_OUTPUT | 0x85 | Set output state/PWM |
| EMU_SET_VOLTAGE | 0x82 | Set battery voltage |
| EMU_SET_TEMPERATURE | 0x83 | Set board temperature |
| EMU_INJECT_CAN | 0x88 | Inject CAN message |
| EMU_INJECT_FAULT | 0x80 | Simulate fault condition |

These commands bypass the normal channel logic and directly set hardware states, useful for:
- Testing protection functions
- Simulating sensor inputs
- Verifying CAN message parsing
- Fault injection testing

## Best Practices

1. **Use full upload sparingly** - Only when structure changes
2. **Prefer real-time commands for tuning** - Faster, less overhead
3. **Always save to flash before deployment** - Ensure persistence
4. **Test in emulator first** - Use EMU commands for simulation
5. **Validate before upload** - Use ConfigValidator locally

```python
from models.config_schema import ConfigValidator

# Validate before uploading
is_valid, errors = ConfigValidator.validate_config(config)
if not is_valid:
    print("Validation errors:")
    print(ConfigValidator.format_validation_errors(errors))
else:
    controller.write_configuration(config)
```

## See Also

- [Device Reboot](device_reboot.md) - Restart and config reload
- [Configuration Schema](configuration_schema.md) - JSON configuration format
- [Protocol Specification](protocol_specification.md) - Full protocol details
- [Telemetry](telemetry.md) - Real-time data streaming

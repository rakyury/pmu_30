# PMU-30 Communication Protocol Specification

## Overview

The PMU-30 uses a binary protocol for communication over USB CDC (virtual serial port), WiFi (ESP32-C3), or CAN bus. The protocol supports device configuration, real-time telemetry streaming, control commands, Lua scripting, and firmware updates.

## Physical Layer

| Transport | Details |
|-----------|---------|
| **USB CDC** | Virtual COM Port, 115200 baud (configurable up to 921600), 8N1 |
| **WiFi** | ESP32-C3 module, TCP socket |
| **CAN** | 1Mbps, base ID 0x600 |

## Frame Format

All messages use the following frame structure:

```
+--------+--------+---------+---------+--------+
| START  |  CMD   | LENGTH  | PAYLOAD |  CRC   |
| 1 byte | 1 byte | 2 bytes | N bytes | 2 bytes|
+--------+--------+---------+---------+--------+
```

| Field    | Size    | Description                           |
|----------|---------|---------------------------------------|
| START    | 1 byte  | Frame start marker (0xAA)             |
| CMD      | 1 byte  | Command type identifier               |
| LENGTH   | 2 bytes | Payload length (little-endian)        |
| PAYLOAD  | N bytes | Command-specific data (max 256 bytes) |
| CRC      | 2 bytes | CRC-16 (little-endian)                |

### CRC Calculation

CRC-16 checksum calculated over CMD, LENGTH, and PAYLOAD bytes.

```python
def crc16(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc
```

## Command Reference

### Basic Commands (0x00-0x1F)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0x01 | PING          | Host→Device | Connection test          |
| 0x02 | GET_VERSION   | Host→Device | Get firmware version     |
| 0x03 | GET_SERIAL    | Host→Device | Get serial number        |
| 0x04 | RESET         | Host→Device | Reset device             |
| 0x05 | BOOTLOADER    | Host→Device | Enter bootloader mode    |

### Telemetry Commands (0x20-0x3F)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0x20 | START_STREAM  | Host→Device | Start telemetry streaming|
| 0x21 | STOP_STREAM   | Host→Device | Stop telemetry streaming |
| 0x22 | GET_OUTPUTS   | Host→Device | Get output states        |
| 0x23 | GET_INPUTS    | Host→Device | Get input values         |
| 0x24 | GET_CAN       | Host→Device | Get CAN data             |
| 0x25 | GET_TEMPS     | Host→Device | Get temperatures         |
| 0x26 | GET_VOLTAGES  | Host→Device | Get voltages             |
| 0x27 | GET_FAULTS    | Host→Device | Get fault status         |

### Control Commands (0x40-0x5F)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0x40 | SET_OUTPUT    | Host→Device | Set output ON/OFF state  |
| 0x41 | SET_PWM       | Host→Device | Set PWM duty cycle       |
| 0x42 | SET_HBRIDGE   | Host→Device | Set H-bridge mode        |
| 0x43 | CLEAR_FAULTS  | Host→Device | Clear all faults         |
| 0x44 | SET_VIRTUAL   | Host→Device | Set virtual channel value|

### Configuration Commands (0x60-0x7F)

| ID   | Name            | Direction   | Description                |
|------|-----------------|-------------|----------------------------|
| 0x60 | LOAD_CONFIG     | Host→Device | Load configuration from flash |
| 0x61 | SAVE_CONFIG     | Host→Device | Save configuration to flash |
| 0x62 | GET_CONFIG      | Host→Device | Get current configuration  |
| 0x63 | UPLOAD_CONFIG   | Host→Device | Upload configuration (chunked) |
| 0x64 | DOWNLOAD_CONFIG | Device→Host | Download configuration (chunked) |
| 0x65 | VALIDATE_CONFIG | Host→Device | Validate configuration     |

### Logging Commands (0x80-0x9F)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0x80 | START_LOGGING | Host→Device | Start data logging       |
| 0x81 | STOP_LOGGING  | Host→Device | Stop data logging        |
| 0x82 | GET_LOG_INFO  | Host→Device | Get log information      |
| 0x83 | DOWNLOAD_LOG  | Device→Host | Download log data        |
| 0x84 | ERASE_LOGS    | Host→Device | Erase all logs           |

### Diagnostic Commands (0xA0-0xAF)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0xA0 | GET_STATS     | Host→Device | Get system statistics    |
| 0xA1 | GET_UPTIME    | Host→Device | Get system uptime        |
| 0xA2 | GET_CAN_STATS | Host→Device | Get CAN bus statistics   |
| 0xA3 | SELF_TEST     | Host→Device | Run self-test            |

### Lua Scripting Commands (0xB0-0xBF)

| ID   | Name            | Direction   | Description              |
|------|-----------------|-------------|--------------------------|
| 0xB0 | LUA_EXECUTE     | Host→Device | Execute Lua code directly|
| 0xB1 | LUA_LOAD_SCRIPT | Host→Device | Load/update Lua script   |
| 0xB2 | LUA_UNLOAD_SCRIPT| Host→Device| Unload Lua script        |
| 0xB3 | LUA_RUN_SCRIPT  | Host→Device | Run loaded script by name|
| 0xB4 | LUA_STOP_SCRIPT | Host→Device | Stop running script      |
| 0xB5 | LUA_GET_SCRIPTS | Host→Device | List loaded scripts      |
| 0xB6 | LUA_GET_STATUS  | Host→Device | Get Lua engine status    |
| 0xB7 | LUA_GET_OUTPUT  | Host→Device | Get script output/result |
| 0xB8 | LUA_SET_ENABLED | Host→Device | Enable/disable script    |

### Firmware Update Commands (0xC0-0xDF)

| ID   | Name             | Direction   | Description              |
|------|------------------|-------------|--------------------------|
| 0xC0 | FW_UPDATE_START  | Host→Device | Start firmware update    |
| 0xC1 | FW_UPDATE_DATA   | Host→Device | Send firmware data chunk |
| 0xC2 | FW_UPDATE_FINISH | Host→Device | Finish firmware update   |
| 0xC3 | FW_UPDATE_ABORT  | Host→Device | Abort firmware update    |

### Response Codes (0xE0-0xFF)

| ID   | Name  | Direction   | Description              |
|------|-------|-------------|--------------------------|
| 0xE0 | ACK   | Device→Host | Command acknowledged     |
| 0xE1 | NACK  | Device→Host | Command not acknowledged |
| 0xE2 | ERROR | Device→Host | Error response           |
| 0xE3 | DATA  | Device→Host | Data response            |

## Message Payloads

### PING (0x01)
Empty payload. Used to verify connection. Device responds with ACK (0xE0).

### GET_VERSION (0x02)
Empty payload. Device responds with DATA (0xE3):

| Offset | Size     | Field            | Description                |
|--------|----------|------------------|----------------------------|
| 0      | 1 byte   | major            | Major version              |
| 1      | 1 byte   | minor            | Minor version              |
| 2      | 1 byte   | patch            | Patch version              |
| 3      | 1 byte   | hw_revision      | Hardware revision          |

### GET_SERIAL (0x03)
Empty payload. Device responds with DATA (0xE3):

| Offset | Size     | Field         | Description                |
|--------|----------|---------------|----------------------------|
| 0      | 16 bytes | serial_number | Null-terminated string     |

### START_STREAM (0x20)

| Offset | Size    | Field   | Description              |
|--------|---------|---------|--------------------------|
| 0      | 1 byte  | flags   | Data type flags (bitmask)|
| 1      | 2 bytes | rate_hz | Stream rate (1-1000 Hz)  |

**Data Type Flags:**

| Bit | Flag            | Description          |
|-----|-----------------|----------------------|
| 0   | outputs_enabled | Include output states|
| 1   | inputs_enabled  | Include input values |
| 2   | can_enabled     | Include CAN data     |
| 3   | temps_enabled   | Include temperatures |
| 4   | voltages_enabled| Include voltages     |
| 5   | faults_enabled  | Include faults       |

### STOP_STREAM (0x21)
Empty payload. Stops telemetry streaming.

### SET_OUTPUT (0x40)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 1 byte  | output_id  | Output index (0-29)      |
| 1      | 1 byte  | state      | 0=OFF, 1=ON              |

### SET_PWM (0x41)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 1 byte  | output_id  | Output index (0-29)      |
| 1      | 2 bytes | duty       | Duty cycle (0-1000 = 0-100%) |

### SET_HBRIDGE (0x42)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 1 byte  | bridge_id  | H-Bridge index (0-3)     |
| 1      | 1 byte  | mode       | 0=Coast, 1=Fwd, 2=Rev, 3=Brake |
| 2      | 1 byte  | pwm        | PWM level (0-255)        |

### SET_VIRTUAL (0x44)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 2 bytes | channel_id | Virtual channel ID       |
| 1      | 4 bytes | value      | Value (int32)            |

### UPLOAD_CONFIG (0x63)
Uploads configuration in chunks.

| Offset | Size     | Field        | Description              |
|--------|----------|--------------|--------------------------|
| 0      | 2 bytes  | chunk_index  | Current chunk (0-based)  |
| 2      | 2 bytes  | total_chunks | Total number of chunks   |
| 4      | N bytes  | data         | JSON configuration chunk |

### LUA_EXECUTE (0xB0)

| Offset | Size    | Field   | Description              |
|--------|---------|---------|--------------------------|
| 0      | N bytes | code    | Lua code (null-terminated)|

### LUA_LOAD_SCRIPT (0xB1)

| Offset | Size    | Field   | Description              |
|--------|---------|---------|--------------------------|
| 0      | 32 bytes| name    | Script name              |
| 32     | N bytes | code    | Lua script code          |

### FW_UPDATE_START (0xC0)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 4 bytes | total_size | Total firmware size      |
| 4      | 4 bytes | crc32      | Expected CRC32           |

### FW_UPDATE_DATA (0xC1)

| Offset | Size     | Field        | Description              |
|--------|----------|--------------|--------------------------|
| 0      | 4 bytes  | offset       | Data offset in firmware  |
| 4      | N bytes  | data         | Firmware data chunk      |

### ACK (0xE0)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 1 byte  | cmd_id     | Command being acknowledged|

### ERROR (0xE2)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 1 byte  | cmd_id     | Failed command           |
| 1      | 2 bytes | error_code | Error code               |
| 3      | N bytes | message    | Error message (optional) |

## Error Codes

| Code | Description                    |
|------|--------------------------------|
| 0x01 | Invalid frame format           |
| 0x02 | CRC mismatch                   |
| 0x03 | Unknown command                |
| 0x04 | Invalid payload                |
| 0x10 | Output index out of range      |
| 0x11 | Invalid output value           |
| 0x12 | Output disabled/faulted        |
| 0x20 | Config parse error             |
| 0x21 | Config validation error        |
| 0x22 | Config write error (flash)     |
| 0x30 | Device busy                    |
| 0x31 | Operation timeout              |
| 0x40 | Lua script error               |
| 0x41 | Lua memory limit               |
| 0x50 | Firmware update error          |
| 0x51 | Invalid firmware               |
| 0xFF | Internal error                 |

## Telemetry Packet Structure

When streaming is active, the device sends telemetry at the configured rate:

| Offset | Size     | Field           | Description                    |
|--------|----------|-----------------|--------------------------------|
| 0      | 4 bytes  | timestamp_ms    | Device uptime in milliseconds  |
| 4      | 4 bytes  | status_flags    | System status bitmask          |
| 8      | 2 bytes  | battery_mv      | Battery voltage in mV          |
| 10     | 2 bytes  | temp_left       | Left board temp (0.1°C units)  |
| 12     | 2 bytes  | temp_right      | Right board temp (0.1°C units) |
| 14     | 60 bytes | output_currents | 30 × uint16 current in mA      |
| 74     | 40 bytes | analog_values   | 20 × uint16 ADC values         |
| 114    | 20 bytes | digital_states  | 20 × uint8 digital states      |
| 134    | 30 bytes | output_states   | 30 × uint8 output states       |
| 164    | 8 bytes  | hbridge_currents| 4 × uint16 H-bridge currents   |
| 172    | 2 bytes  | reserved        | Reserved for future use        |

**Total packet size: 174 bytes**

### Output States (1 byte each)

| Value | State              |
|-------|--------------------|
| 0     | OFF                |
| 1     | ON                 |
| 2     | FAULT_OVERCURRENT  |
| 3     | FAULT_OVERHEAT     |
| 4     | FAULT_SHORT        |
| 5     | FAULT_OPEN         |
| 6     | PWM_ACTIVE         |
| 7     | DISABLED           |

### Status Flags (32-bit bitmask)

| Bit | Flag               |
|-----|--------------------|
| 0   | CONFIG_LOADED      |
| 1   | TELEMETRY_ACTIVE   |
| 2   | LUA_RUNNING        |
| 3   | LOGGING_ACTIVE     |
| 4   | OVERVOLTAGE        |
| 5   | UNDERVOLTAGE       |
| 6   | OVERTEMPERATURE    |
| 7   | CAN1_ERROR         |
| 8   | CAN2_ERROR         |
| 9   | FLASH_ERROR        |
| 10  | CONFIG_ERROR       |
| 11  | WATCHDOG_RESET     |
| 12  | LUA_ERROR          |

## Typical Communication Flows

### Connection Sequence

```
Host                          Device
  |                              |
  |-------- PING (0x01) -------->|
  |<------- ACK (0xE0) ----------|
  |                              |
  |---- GET_VERSION (0x02) ----->|
  |<------- DATA (0xE3) ---------|
  |                              |
```

### Configuration Upload

```
Host                          Device
  |                              |
  |-- UPLOAD_CONFIG chunk 0/3 -->|
  |<------- ACK (0xE0) ----------|
  |-- UPLOAD_CONFIG chunk 1/3 -->|
  |<------- ACK (0xE0) ----------|
  |-- UPLOAD_CONFIG chunk 2/3 -->|
  |<------- ACK (0xE0) ----------|
  |                              |
  |---- SAVE_CONFIG (0x61) ----->|
  |<------- ACK (0xE0) ----------|
  |                              |
```

### Telemetry Streaming

```
Host                          Device
  |                              |
  |-- START_STREAM (50Hz) ------>|
  |<------- ACK (0xE0) ----------|
  |<------- DATA (telemetry) ----|  (every 20ms)
  |<------- DATA (telemetry) ----|
  |<------- DATA (telemetry) ----|
  |         ...                  |
  |-- STOP_STREAM (0x21) ------->|
  |<------- ACK (0xE0) ----------|
  |                              |
```

### Output Control

```
Host                          Device
  |                              |
  |-- SET_OUTPUT (out=5, on) --->|
  |<------- ACK (0xE0) ----------|
  |                              |
  |-- SET_PWM (out=5, 75%) ----->|
  |<------- ACK (0xE0) ----------|
  |                              |
```

### Lua Script Execution

```
Host                          Device
  |                              |
  |-- LUA_EXECUTE("pmu.o1=1") -->|
  |<------- ACK (0xE0) ----------|
  |                              |
  |-- LUA_LOAD_SCRIPT ---------->|
  |<------- ACK (0xE0) ----------|
  |                              |
  |-- LUA_RUN_SCRIPT ----------->|
  |<------- ACK (0xE0) ----------|
  |                              |
```

## Python API Usage

### Connecting to Device

```python
from src.communication.comm_manager import CommunicationManager

manager = CommunicationManager()

# Connect
await manager.connect("COM3")

# Get device version
version = await manager.get_version()
print(f"Firmware: {version.major}.{version.minor}.{version.patch}")

# Disconnect
await manager.disconnect()
```

### Telemetry Streaming

```python
def on_telemetry(packet):
    print(f"Voltage: {packet.battery_mv / 1000}V")
    print(f"Temperature: {packet.temp_left / 10}°C")
    print(f"Output 1 current: {packet.output_currents[0]}mA")

manager.on_telemetry(on_telemetry)
await manager.start_telemetry(rate_hz=50)

# ... later
await manager.stop_telemetry()
```

### Output Control

```python
# Turn on output 5
await manager.set_output(5, True)

# Set output 5 to 75% PWM
await manager.set_pwm(5, 750)  # 750 = 75.0%

# Control H-bridge
await manager.set_hbridge(0, mode=1, pwm=200)  # Forward at ~78%
```

### Configuration Upload

```python
import json

config = {
    "outputs": [...],
    "inputs": [...],
    "logic_functions": [...]
}

await manager.upload_config(json.dumps(config).encode())
await manager.save_config()
```

## Implementation Notes

1. **Timeouts**: All commands should have a 1 second timeout
2. **Retries**: Failed commands should be retried up to 3 times
3. **Chunk Size**: Configuration chunks should not exceed 256 bytes (max payload)
4. **Flow Control**: Wait for ACK before sending next command/chunk
5. **Stream Rates**: Supported rates: 1, 10, 50, 100, 500, 1000 Hz
6. **CRC Validation**: All received packets must be CRC-validated

## Protocol Constants

```c
#define PMU_PROTOCOL_START_MARKER  0xAA
#define PMU_PROTOCOL_VERSION       0x01
#define PMU_PROTOCOL_MAX_PAYLOAD   256
#define PMU_PROTOCOL_CAN_ID_BASE   0x600
```

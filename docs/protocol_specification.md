# PMU-30 Communication Protocol Specification

## Overview

The PMU-30 uses a binary protocol for communication over USB CDC (virtual serial port). The protocol supports device configuration, real-time telemetry streaming, and control commands.

## Physical Layer

- **Interface**: USB CDC (Virtual COM Port)
- **Baud Rate**: 115200 (configurable up to 921600)
- **Data Format**: 8N1 (8 data bits, no parity, 1 stop bit)

## Frame Format

All messages use the following frame structure:

```
+--------+--------+--------+---------+--------+
| START  | LENGTH | MSG_ID | PAYLOAD |  CRC   |
| 1 byte | 2 bytes| 1 byte | N bytes | 2 bytes|
+--------+--------+--------+---------+--------+
```

| Field    | Size    | Description                           |
|----------|---------|---------------------------------------|
| START    | 1 byte  | Frame start marker (0xAA)             |
| LENGTH   | 2 bytes | Payload length (little-endian)        |
| MSG_ID   | 1 byte  | Message type identifier               |
| PAYLOAD  | N bytes | Message-specific data                 |
| CRC      | 2 bytes | CRC-16-CCITT (little-endian)          |

### CRC Calculation

CRC-16-CCITT with polynomial 0x1021, initial value 0xFFFF. The CRC is calculated over the MSG_ID and PAYLOAD bytes.

```python
def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
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

## Message Types

| ID   | Name                | Direction  | Description                    |
|------|---------------------|------------|--------------------------------|
| 0x01 | PING                | Host→Device| Connection test                |
| 0x02 | PONG                | Device→Host| Ping response                  |
| 0x10 | GET_INFO            | Host→Device| Request device information     |
| 0x11 | INFO_RESP           | Device→Host| Device information response    |
| 0x20 | GET_CONFIG          | Host→Device| Request current configuration  |
| 0x21 | CONFIG_DATA         | Both       | Configuration data chunk       |
| 0x22 | SET_CONFIG          | Host→Device| Upload configuration chunk     |
| 0x23 | CONFIG_ACK          | Device→Host| Configuration acknowledgment   |
| 0x30 | SET_CHANNEL         | Host→Device| Set channel output value       |
| 0x31 | CHANNEL_ACK         | Device→Host| Channel command acknowledgment |
| 0x40 | SUBSCRIBE_TELEMETRY | Host→Device| Start telemetry streaming      |
| 0x41 | UNSUBSCRIBE_TELEMETRY| Host→Device| Stop telemetry streaming      |
| 0x42 | TELEMETRY_DATA      | Device→Host| Real-time telemetry packet     |
| 0xF0 | ERROR               | Device→Host| Error response                 |

## Message Payloads

### PING (0x01)
Empty payload. Used to verify connection.

### PONG (0x02)
Empty payload. Response to PING.

### GET_INFO (0x10)
Empty payload. Requests device information.

### INFO_RESP (0x11)

| Offset | Size     | Field            | Description                |
|--------|----------|------------------|----------------------------|
| 0      | 3 bytes  | firmware_version | Major.Minor.Patch          |
| 3      | 1 byte   | hw_revision      | Hardware revision          |
| 4      | 16 bytes | serial_number    | Null-terminated string     |
| 20     | 32 bytes | device_name      | Null-terminated string     |

### GET_CONFIG (0x20)
Empty payload. Requests full configuration.

### CONFIG_DATA (0x21)
Used for both download (device→host) and upload response.

| Offset | Size     | Field       | Description              |
|--------|----------|-------------|--------------------------|
| 0      | 2 bytes  | chunk_index | Current chunk (0-based)  |
| 2      | 2 bytes  | total_chunks| Total number of chunks   |
| 4      | N bytes  | data        | JSON configuration chunk |

### SET_CONFIG (0x22)
Upload configuration chunk to device.

| Offset | Size     | Field       | Description              |
|--------|----------|-------------|--------------------------|
| 0      | 2 bytes  | chunk_index | Current chunk (0-based)  |
| 2      | 2 bytes  | total_chunks| Total number of chunks   |
| 4      | N bytes  | data        | JSON configuration chunk |

### CONFIG_ACK (0x23)

| Offset | Size    | Field      | Description           |
|--------|---------|------------|-----------------------|
| 0      | 1 byte  | success    | 1=success, 0=failure  |
| 1      | 2 bytes | error_code | Error code if failed  |

### SET_CHANNEL (0x30)
Set output channel value.

| Offset | Size    | Field     | Description              |
|--------|---------|-----------|--------------------------|
| 0      | 2 bytes | channel_id| Channel index (0-29)     |
| 2      | 4 bytes | value     | Float value (0.0-100.0)  |

### CHANNEL_ACK (0x31)

| Offset | Size    | Field      | Description           |
|--------|---------|------------|-----------------------|
| 0      | 1 byte  | success    | 1=success, 0=failure  |
| 1      | 2 bytes | channel_id | Channel that was set  |

### SUBSCRIBE_TELEMETRY (0x40)

| Offset | Size    | Field   | Description              |
|--------|---------|---------|--------------------------|
| 0      | 2 bytes | rate_hz | Telemetry rate (1-100 Hz)|

### UNSUBSCRIBE_TELEMETRY (0x41)
Empty payload. Stops telemetry streaming.

### TELEMETRY_DATA (0x42)
119 bytes total, sent at subscribed rate.

| Offset | Size     | Field          | Description                    |
|--------|----------|----------------|--------------------------------|
| 0      | 4 bytes  | timestamp_ms   | Device uptime in milliseconds  |
| 4      | 30 bytes | channel_states | 1 byte per channel (enum)      |
| 34     | 16 bytes | analog_values  | 8 × uint16 ADC values          |
| 50     | 60 bytes | output_currents| 30 × uint16 current in mA      |
| 110    | 2 bytes  | input_voltage  | Input voltage in mV            |
| 112    | 1 byte   | temperature    | Board temperature in °C        |
| 113    | 4 bytes  | fault_flags    | System fault flags (bitmask)   |
| 117    | 2 bytes  | crc            | Packet CRC                     |

#### Channel States (1 byte each)

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

#### Fault Flags (32-bit bitmask)

| Bit | Flag               |
|-----|--------------------|
| 0   | OVERVOLTAGE        |
| 1   | UNDERVOLTAGE       |
| 2   | OVERTEMPERATURE    |
| 3   | CAN1_ERROR         |
| 4   | CAN2_ERROR         |
| 5   | FLASH_ERROR        |
| 6   | CONFIG_ERROR       |
| 7   | WATCHDOG_RESET     |
| 8   | POWER_FAIL         |
| 9   | GROUND_FAULT       |
| 10  | REVERSE_POLARITY   |
| 11  | SENSOR_ERROR       |
| 12  | LUA_ERROR          |
| 13  | LOGIC_ERROR        |
| 16  | CHANNEL_FAULT_1-8  |
| 17  | CHANNEL_FAULT_9-16 |
| 18  | CHANNEL_FAULT_17-24|
| 19  | CHANNEL_FAULT_25-30|

### ERROR (0xF0)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 2 bytes | error_code | Error code               |
| 2      | 1 byte  | msg_length | Error message length     |
| 3      | N bytes | message    | UTF-8 error message      |

## Error Codes

| Code | Description                    |
|------|--------------------------------|
| 0x01 | Invalid frame                  |
| 0x02 | CRC mismatch                   |
| 0x03 | Unknown message type           |
| 0x04 | Invalid payload                |
| 0x10 | Channel out of range           |
| 0x11 | Invalid channel value          |
| 0x12 | Channel disabled               |
| 0x20 | Config parse error             |
| 0x21 | Config validation error        |
| 0x22 | Config write error             |
| 0x30 | Device busy                    |
| 0x31 | Operation timeout              |
| 0xFF | Internal error                 |

## Typical Communication Flow

### Connection Sequence

```
Host                          Device
  |                              |
  |-------- PING --------------->|
  |<------- PONG ----------------|
  |                              |
  |-------- GET_INFO ----------->|
  |<------- INFO_RESP -----------|
  |                              |
```

### Configuration Upload

```
Host                          Device
  |                              |
  |-- SET_CONFIG (chunk 0/3) --->|
  |<------- CONFIG_ACK ----------|
  |-- SET_CONFIG (chunk 1/3) --->|
  |<------- CONFIG_ACK ----------|
  |-- SET_CONFIG (chunk 2/3) --->|
  |<------- CONFIG_ACK ----------|
  |                              |
```

### Telemetry Streaming

```
Host                          Device
  |                              |
  |-- SUBSCRIBE_TELEMETRY(50Hz)->|
  |<------- TELEMETRY_DATA ------|  (every 20ms)
  |<------- TELEMETRY_DATA ------|
  |<------- TELEMETRY_DATA ------|
  |         ...                  |
  |-- UNSUBSCRIBE_TELEMETRY ---->|
  |                              |
```

## Python API Usage

### Connecting to Device

```python
from src.communication.comm_manager import CommunicationManager

manager = CommunicationManager()

# Connect
await manager.connect("COM3")

# Get device info
info = await manager.get_device_info()
print(f"Firmware: {info.firmware_version}")

# Disconnect
await manager.disconnect()
```

### Telemetry Streaming

```python
def on_telemetry(packet):
    print(f"Voltage: {packet.input_voltage}V")
    print(f"Temperature: {packet.temperature_c}°C")
    print(f"Active channels: {packet.active_channels}")

manager.on_telemetry(on_telemetry)
await manager.start_telemetry(rate_hz=50)

# ... later
await manager.stop_telemetry()
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
```

### Channel Control

```python
# Set channel 5 to 75% duty cycle
await manager.set_channel(5, 75.0)

# Turn off channel 10
await manager.set_channel(10, 0.0)
```

## Implementation Notes

1. **Timeouts**: All commands should have a 1 second timeout
2. **Retries**: Failed commands should be retried up to 3 times
3. **Chunk Size**: Configuration chunks should not exceed 512 bytes
4. **Flow Control**: Wait for ACK before sending next chunk
5. **Telemetry Buffer**: Keep last 10 telemetry packets for smoothing

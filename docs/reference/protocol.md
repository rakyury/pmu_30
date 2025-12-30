# PMU-30 Communication Protocol Specification

**Version:** 2.0
**Date:** 2025-12-29
**Author:** R2 m-sport

---

## Overview

The PMU-30 uses a binary protocol for communication over USB CDC (virtual serial port), WiFi (ESP32-C3), or CAN bus. The protocol supports device configuration, real-time telemetry streaming, control commands, Lua scripting, data logging, and firmware updates.

### Key Features

- **Binary Protocol**: Efficient binary format for low latency
- **Multi-Transport**: Supports UART (115200 baud), WiFi (TCP/IP), and CAN (1Mbps)
- **Real-Time Streaming**: Telemetry data at rates from 1Hz to 1000Hz
- **Remote Control**: Set outputs, PWM, H-bridge modes in real-time
- **Atomic Updates**: Push single channel changes without full config reload
- **Configuration**: Upload/download JSON configuration files
- **Diagnostics**: Firmware version, statistics, fault status
- **Data Logging**: High-speed logging to flash memory

---

## Physical Layer

| Transport | Details |
|-----------|---------|
| **USB CDC** | Virtual COM Port, 115200 baud (configurable up to 921600), 8N1 |
| **WiFi** | ESP32-C3 module, TCP socket on port 8080 |
| **CAN** | 1Mbps, base ID 0x600 |

### UART/WiFi (ESP32-C3)

- **Baud Rate**: 115200 bps
- **Format**: 8N1 (8 data bits, no parity, 1 stop bit)
- **Hardware Flow Control**: None
- **Connection**: USART1 (PA9/PA10) -> ESP32-C3

WiFi provides TCP/IP transparent bridge to UART.

### CAN Bus

- **Base CAN ID**: `0x600`
- **Bitrate**: 1 Mbps (CAN FD optional at 5 Mbps data phase)
- **Format**: Standard 11-bit ID
- **Chunking**: Packets > 8 bytes split into multiple frames

---

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

CRC-16 CCITT checksum calculated over START, CMD, LENGTH, and PAYLOAD bytes.

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

```c
uint16_t crc16(uint8_t* data, size_t length) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000)
                crc = (crc << 1) ^ 0x1021;
            else
                crc = crc << 1;
        }
    }
    return crc;
}
```

---

## Command Reference

### Basic Commands (0x00-0x1F)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0x01 | PING          | Host->Device | Connection test          |
| 0x02 | GET_VERSION   | Host->Device | Get firmware version     |
| 0x03 | GET_SERIAL    | Host->Device | Get serial number        |
| 0x04 | RESET         | Host->Device | Reset device             |
| 0x05 | BOOTLOADER    | Host->Device | Enter bootloader mode    |

### Telemetry Commands (0x20-0x3F)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0x20 | START_STREAM  | Host->Device | Start telemetry streaming|
| 0x21 | STOP_STREAM   | Host->Device | Stop telemetry streaming |
| 0x22 | GET_OUTPUTS   | Host->Device | Get output states        |
| 0x23 | GET_INPUTS    | Host->Device | Get input values         |
| 0x24 | GET_CAN       | Host->Device | Get CAN data             |
| 0x25 | GET_TEMPS     | Host->Device | Get temperatures         |
| 0x26 | GET_VOLTAGES  | Host->Device | Get voltages             |
| 0x27 | GET_FAULTS    | Host->Device | Get fault status         |

### Control Commands (0x40-0x5F)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0x40 | SET_OUTPUT    | Host->Device | Set output ON/OFF state  |
| 0x41 | SET_PWM       | Host->Device | Set PWM duty cycle       |
| 0x42 | SET_HBRIDGE   | Host->Device | Set H-bridge mode        |
| 0x43 | CLEAR_FAULTS  | Host->Device | Clear all faults         |
| 0x44 | SET_VIRTUAL   | Host->Device | Set virtual channel value|

### Configuration Commands (0x60-0x7F)

| ID   | Name               | Direction   | Description                |
|------|--------------------|-------------|----------------------------|
| 0x60 | LOAD_CONFIG        | Host->Device | Load configuration from flash |
| 0x61 | SAVE_CONFIG        | Host->Device | Save configuration to flash |
| 0x62 | GET_CONFIG         | Host->Device | Get current configuration  |
| 0x63 | UPLOAD_CONFIG      | Host->Device | Upload configuration (chunked) |
| 0x64 | DOWNLOAD_CONFIG    | Device->Host | Download configuration (chunked) |
| 0x65 | VALIDATE_CONFIG    | Host->Device | Validate configuration     |
| 0x66 | SET_CHANNEL_CONFIG | Host->Device | Update single channel config |
| 0x67 | CHANNEL_CONFIG_ACK | Device->Host | Response to channel config |

### Device Control Commands (0x70-0x7F)

| ID   | Name           | Direction   | Description              |
|------|----------------|-------------|--------------------------|
| 0x70 | RESTART_DEVICE | Host->Device | Soft device restart      |
| 0x71 | RESTART_ACK    | Device->Host | Restart acknowledgment   |
| 0x72 | BOOT_COMPLETE  | Device->Host | Boot complete notification |

### Logging Commands (0x80-0x9F)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0x80 | START_LOGGING | Host->Device | Start data logging       |
| 0x81 | STOP_LOGGING  | Host->Device | Stop data logging        |
| 0x82 | GET_LOG_INFO  | Host->Device | Get log information      |
| 0x83 | DOWNLOAD_LOG  | Device->Host | Download log data        |
| 0x84 | ERASE_LOGS    | Host->Device | Erase all logs           |

### Diagnostic Commands (0xA0-0xAF)

| ID   | Name          | Direction   | Description              |
|------|---------------|-------------|--------------------------|
| 0xA0 | GET_STATS     | Host->Device | Get system statistics    |
| 0xA1 | GET_UPTIME    | Host->Device | Get system uptime        |
| 0xA2 | GET_CAN_STATS | Host->Device | Get CAN bus statistics   |
| 0xA3 | SELF_TEST     | Host->Device | Run self-test            |

### Lua Scripting Commands (0xB0-0xBF)

| ID   | Name             | Direction   | Description              |
|------|------------------|-------------|--------------------------|
| 0xB0 | LUA_EXECUTE      | Host->Device | Execute Lua code directly|
| 0xB1 | LUA_LOAD_SCRIPT  | Host->Device | Load/update Lua script   |
| 0xB2 | LUA_UNLOAD_SCRIPT| Host->Device | Unload Lua script        |
| 0xB3 | LUA_RUN_SCRIPT   | Host->Device | Run loaded script by name|
| 0xB4 | LUA_STOP_SCRIPT  | Host->Device | Stop running script      |
| 0xB5 | LUA_GET_SCRIPTS  | Host->Device | List loaded scripts      |
| 0xB6 | LUA_GET_STATUS   | Host->Device | Get Lua engine status    |
| 0xB7 | LUA_GET_OUTPUT   | Host->Device | Get script output/result |
| 0xB8 | LUA_SET_ENABLED  | Host->Device | Enable/disable script    |

### Firmware Update Commands (0xC0-0xDF)

| ID   | Name             | Direction   | Description              |
|------|------------------|-------------|--------------------------|
| 0xC0 | FW_UPDATE_START  | Host->Device | Start firmware update    |
| 0xC1 | FW_UPDATE_DATA   | Host->Device | Send firmware data chunk |
| 0xC2 | FW_UPDATE_FINISH | Host->Device | Finish firmware update   |
| 0xC3 | FW_UPDATE_ABORT  | Host->Device | Abort firmware update    |

### Response Codes (0xE0-0xFF)

| ID   | Name  | Direction   | Description              |
|------|-------|-------------|--------------------------|
| 0xE0 | ACK   | Device->Host | Command acknowledged     |
| 0xE1 | NACK  | Device->Host | Command not acknowledged |
| 0xE2 | ERROR | Device->Host | Error response           |
| 0xE3 | DATA  | Device->Host | Data response            |

---

## Message Payloads

### Basic Commands

#### PING (0x01)

**Request:**
```
[0xAA][0x01][0x00][0x00][CRC]
```

**Response:**
```
[0xAA][0xE0][0x01][0x01][CRC]  // ACK
```

Echo back to verify connectivity.

---

#### GET_VERSION (0x02)

**Request:**
```
[0xAA][0x02][0x00][0x00][CRC]
```

**Response (DATA):**

| Offset | Size     | Field            | Description                |
|--------|----------|------------------|----------------------------|
| 0      | 1 byte   | major            | Major version              |
| 1      | 1 byte   | minor            | Minor version              |
| 2      | 1 byte   | patch            | Patch version              |
| 3      | 1 byte   | hw_revision      | Hardware revision          |

---

#### GET_SERIAL (0x03)

**Request:**
```
[0xAA][0x03][0x00][0x00][CRC]
```

**Response (DATA):**

| Offset | Size     | Field         | Description                |
|--------|----------|---------------|----------------------------|
| 0      | 16 bytes | serial_number | Null-terminated string     |

---

### Telemetry Commands

#### START_STREAM (0x20)

**Request:**
```
[0xAA][0x20][0x08][CONFIG][CRC]

CONFIG (8 bytes):
  Byte 0: Flags (bit 0: outputs, bit 1: inputs, bit 2: CAN,
                 bit 3: temps, bit 4: voltages, bit 5: faults)
  Byte 1-2: Stream rate (Hz, little-endian, 1-1000)
  Byte 3-7: Reserved
```

**Data Type Flags:**

| Bit | Flag            | Description          |
|-----|-----------------|----------------------|
| 0   | outputs_enabled | Include output states|
| 1   | inputs_enabled  | Include input values |
| 2   | can_enabled     | Include CAN data     |
| 3   | temps_enabled   | Include temperatures |
| 4   | voltages_enabled| Include voltages     |
| 5   | faults_enabled  | Include faults       |

**Response:**
```
[0xAA][0xE0][0x01][0x20][CRC]  // ACK
```

---

#### STOP_STREAM (0x21)

**Request:**
```
[0xAA][0x21][0x00][0x00][CRC]
```

**Response:**
```
[0xAA][0xE0][0x01][0x21][CRC]  // ACK
```

---

#### GET_OUTPUTS (0x22)

**Request:**
```
[0xAA][0x22][0x00][0x00][CRC]
```

**Response (60 bytes for 30 channels):**
```
[0xAA][0x22][0x3C][...60 bytes...][CRC]

For each channel (2 bytes):
  Byte 0: State (0=OFF, 1=ON, 2=PWM, 3=FAULT)
  Byte 1: PWM duty (0-255, scaled from 0-1000)
```

---

#### GET_INPUTS (0x23)

**Request:**
```
[0xAA][0x23][0x00][0x00][CRC]
```

**Response (40 bytes for 20 inputs):**
```
[0xAA][0x23][0x28][...40 bytes...][CRC]

For each input (2 bytes, little-endian):
  Raw ADC value (0-1023)
```

---

### Control Commands

#### SET_OUTPUT (0x40)

**Request:**
```
[0xAA][0x40][0x02][CHANNEL][STATE][CRC]

  CHANNEL: Output channel (0-29)
  STATE: 0=OFF, 1=ON
```

**Response:**
```
[0xAA][0xE0][0x01][0x40][CRC]  // ACK
```

---

#### SET_PWM (0x41)

**Request:**
```
[0xAA][0x41][0x03][CHANNEL][DUTY_L][DUTY_H][CRC]

  CHANNEL: Output channel (0-29)
  DUTY: PWM duty cycle (0-1000 = 0-100%, little-endian)
```

**Response:**
```
[0xAA][0xE0][0x01][0x41][CRC]  // ACK
```

---

#### SET_HBRIDGE (0x42)

**Request:**
```
[0xAA][0x42][0x04][BRIDGE][MODE][DUTY_L][DUTY_H][CRC]

  BRIDGE: H-bridge number (0-3)
  MODE: 0=Coast, 1=Forward, 2=Reverse, 3=Brake
  DUTY: PWM duty cycle (0-1000, little-endian)
```

**Response:**
```
[0xAA][0xE0][0x01][0x42][CRC]  // ACK
```

---

#### SET_VIRTUAL (0x44)

**Request:**

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 2 bytes | channel_id | Virtual channel ID       |
| 2      | 4 bytes | value      | Value (int32, little-endian) |

**Response:**
```
[0xAA][0xE0][0x01][0x44][CRC]  // ACK
```

---

### Configuration Commands

#### LOAD_CONFIG (0x60)

**Request:**
```
[0xAA][0x60][N][...JSON config...][CRC]

  Payload: JSON configuration string (matching configurator format)
```

**Response:**
```
[0xAA][0x60][N]["Loaded: X inputs, Y outputs"][CRC]
```

---

#### UPLOAD_CONFIG (0x63)

Uploads configuration in chunks (max 256 bytes per chunk).

**Request:**

| Offset | Size     | Field        | Description              |
|--------|----------|--------------|--------------------------|
| 0      | 2 bytes  | chunk_index  | Current chunk (0-based)  |
| 2      | 2 bytes  | total_chunks | Total number of chunks   |
| 4      | N bytes  | data         | JSON configuration chunk |

**Response:**
```
[0xAA][0xE0][0x01][0x63][CRC]  // ACK for each chunk
```

---

#### SET_CHANNEL_CONFIG (0x66) - Atomic Update

Push a single channel configuration to the device without full configuration reload.

**Request:**
```
[0xAA][0x66][N][TYPE][CHANNEL_ID_L][CHANNEL_ID_H][JSON_LEN_L][JSON_LEN_H][...JSON config...][CRC]

  TYPE: Channel type discriminator (1 byte)
  CHANNEL_ID: Numeric channel ID (2 bytes, little-endian)
  JSON_LEN: Length of JSON config string (2 bytes, little-endian)
  JSON config: UTF-8 JSON configuration string
```

**Channel Type Codes:**

| Code | Type |
|------|------|
| 0x01 | Power Output |
| 0x02 | H-Bridge |
| 0x03 | Digital Input |
| 0x04 | Analog Input |
| 0x05 | Logic |
| 0x06 | Number |
| 0x07 | Timer |
| 0x08 | Filter |
| 0x09 | Switch |
| 0x0A | Table 2D |
| 0x0B | Table 3D |
| 0x0C | CAN RX |
| 0x0D | CAN TX |
| 0x0E | PID Controller |
| 0x0F | Lua Script |
| 0x10 | Handler |
| 0x11 | BlinkMarine Keypad |

**Response (CHANNEL_CONFIG_ACK 0x67):**
```
[0xAA][0x67][N][CHANNEL_ID_L][CHANNEL_ID_H][SUCCESS][ERROR_CODE_L][ERROR_CODE_H][...error message...][CRC]

  CHANNEL_ID: Echo of requested channel ID (2 bytes, little-endian)
  SUCCESS: 0x01 = success, 0x00 = failure
  ERROR_CODE: Error code if failed (2 bytes, little-endian)
  Error message: Human-readable error string (variable length)
```

**Error Codes:**

| Code | Meaning |
|------|---------|
| 0x0000 | Success |
| 0x0001 | Invalid channel type |
| 0x0002 | Channel not found |
| 0x0003 | JSON parse error |
| 0x0004 | Validation error |

**Use Case:** When the user modifies a power output's PWM frequency or changes a logic channel's condition in the configurator, this command pushes just that channel's config to the firmware instantly, without disrupting other running channels.

---

### Device Control Commands

#### RESTART_DEVICE (0x70)

**Request:**
```
[0xAA][0x70][0x00][0x00][CRC]
```

**Response:**
```
[0xAA][0x71][0x00][0x00][CRC]  // RESTART_ACK
```

Device will:
1. Send RESTART_ACK immediately
2. Perform soft reset
3. Reinitialize all subsystems
4. Load configuration from flash
5. Send BOOT_COMPLETE to all connected clients

---

#### BOOT_COMPLETE (0x72)

**Direction:** Device -> Host (unsolicited)

```
[0xAA][0x72][0x00][0x00][CRC]
```

Sent by the device after successful initialization/restart to signal that:
1. All subsystems are initialized
2. Configuration is loaded
3. Device is ready to accept commands

**Use Case:** When the configurator receives BOOT_COMPLETE, it should re-read the configuration from the device to synchronize state.

---

### Logging Commands

#### START_LOGGING (0x80)

**Request:**
```
[0xAA][0x80][0x00][0x00][CRC]
```

**Response:**
```
[0xAA][0xE0][0x01][0x80][CRC]  // ACK
```

---

#### STOP_LOGGING (0x81)

**Request:**
```
[0xAA][0x81][0x00][0x00][CRC]
```

**Response:**
```
[0xAA][0xE0][0x01][0x81][CRC]  // ACK
```

---

#### GET_LOG_INFO (0x82)

**Request:**
```
[0xAA][0x82][0x00][0x00][CRC]
```

**Response:**
```
[0xAA][0x82][N][SESSION_COUNT_2B][...session data...][CRC]

For each session (21 bytes):
  Session ID (4 bytes, little-endian)
  Start time (4 bytes, seconds since boot)
  Duration (4 bytes, milliseconds)
  Bytes used (4 bytes)
  Sample count (4 bytes)
  Status (1 byte)
```

---

#### DOWNLOAD_LOG (0x83)

**Request:**
```
[0xAA][0x83][0x0C][SESSION_ID_4B][OFFSET_4B][LENGTH_4B][CRC]

  SESSION_ID: Session to download
  OFFSET: Byte offset in session data
  LENGTH: Bytes to download (max 244)
```

**Response:**
```
[0xAA][0x83][N][SESSION_ID_4B][OFFSET_4B][BYTES_READ_4B][...data...][CRC]
```

---

#### ERASE_LOGS (0x84)

**Request:**
```
[0xAA][0x84][0x00][0x00][CRC]
```

**Response:**
```
[0xAA][0xE0][0x01][0x84][CRC]  // ACK
```

> **WARNING:** This operation is irreversible.

---

### Lua Scripting Commands

#### LUA_EXECUTE (0xB0)

**Request:**

| Offset | Size    | Field   | Description              |
|--------|---------|---------|--------------------------|
| 0      | N bytes | code    | Lua code (null-terminated)|

---

#### LUA_LOAD_SCRIPT (0xB1)

**Request:**

| Offset | Size    | Field   | Description              |
|--------|---------|---------|--------------------------|
| 0      | 32 bytes| name    | Script name              |
| 32     | N bytes | code    | Lua script code          |

---

### Firmware Update Commands

#### FW_UPDATE_START (0xC0)

**Request:**

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 4 bytes | total_size | Total firmware size      |
| 4      | 4 bytes | crc32      | Expected CRC32           |

---

#### FW_UPDATE_DATA (0xC1)

**Request:**

| Offset | Size     | Field        | Description              |
|--------|----------|--------------|--------------------------|
| 0      | 4 bytes  | offset       | Data offset in firmware  |
| 4      | N bytes  | data         | Firmware data chunk      |

---

### Response Payloads

#### ACK (0xE0)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 1 byte  | cmd_id     | Command being acknowledged|

---

#### NACK (0xE1)

```
[0xAA][0xE1][N][COMMAND]["Error reason"][CRC]
```

---

#### ERROR (0xE2)

| Offset | Size    | Field      | Description              |
|--------|---------|------------|--------------------------|
| 0      | 1 byte  | cmd_id     | Failed command           |
| 1      | 2 bytes | error_code | Error code               |
| 3      | N bytes | message    | Error message (optional) |

---

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

---

## Telemetry Packet Structure

When streaming is active (0x20), the device sends DATA packets (0xE3) at the configured rate:

```
[0xAA][0xE3][N][COUNTER_4B][TIMESTAMP_4B][...data...][CRC]
```

**Full packet structure (174 bytes):**

| Offset | Size     | Field           | Description                    |
|--------|----------|-----------------|--------------------------------|
| 0      | 4 bytes  | counter         | Stream packet counter          |
| 4      | 4 bytes  | timestamp_ms    | Device uptime in milliseconds  |
| 8      | 4 bytes  | status_flags    | System status bitmask          |
| 12     | 2 bytes  | battery_mv      | Battery voltage in mV          |
| 14     | 2 bytes  | temp_left       | Left board temp (0.1C units)   |
| 16     | 2 bytes  | temp_right      | Right board temp (0.1C units)  |
| 18     | 60 bytes | output_currents | 30 x uint16 current in mA      |
| 78     | 40 bytes | analog_values   | 20 x uint16 ADC values         |
| 118    | 20 bytes | digital_states  | 20 x uint8 digital states      |
| 138    | 30 bytes | output_states   | 30 x uint8 output states       |
| 168    | 8 bytes  | hbridge_currents| 4 x uint16 H-bridge currents   |
| 176    | 2 bytes  | reserved        | Reserved for future use        |

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

---

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

### Atomic Channel Update

```
Host                          Device
  |                              |
  |-- SET_CHANNEL_CONFIG ------->|
  |   (type=0x01, id=105,        |
  |    JSON config)              |
  |<-- CHANNEL_CONFIG_ACK -------|
  |   (id=105, success=1)        |
  |                              |
```

### Device Restart

```
Host                          Device
  |                              |
  |-- RESTART_DEVICE (0x70) ---->|
  |<--- RESTART_ACK (0x71) ------|
  |                              |
  |   ... device reboots ...     |
  |                              |
  |<--- BOOT_COMPLETE (0x72) ----|
  |                              |
  |-- GET_CONFIG (0x62) -------->|
  |<--- DATA (config JSON) ------|
  |                              |
```

---

## Python Client Examples

### Basic Connection

```python
import serial
import struct

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

def calc_crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc

def send_command(cmd, payload=b''):
    packet = bytearray([0xAA, cmd])
    packet += struct.pack('<H', len(payload))
    packet += payload
    crc = calc_crc16(packet)
    packet += struct.pack('<H', crc)
    ser.write(packet)

    # Read response
    response = ser.read(4)
    if len(response) < 4:
        return None

    marker, resp_cmd, length = struct.unpack('<BBH', response)
    if marker != 0xAA:
        return None

    payload = ser.read(length)
    crc_received = struct.unpack('<H', ser.read(2))[0]

    # Verify CRC
    crc_calc = calc_crc16(response + payload)
    if crc_calc != crc_received:
        print("CRC error!")
        return None

    return payload

# Get firmware version
version = send_command(0x02)
print(f"Firmware: {version.decode('utf-8')}")

# Set output 5 ON
send_command(0x40, bytes([5, 1]))

# Set PWM on channel 10 to 50%
duty = 500  # 0-1000 range
send_command(0x41, bytes([10]) + struct.pack('<H', duty))
```

### Telemetry Streaming

```python
# Start streaming at 50Hz
config = struct.pack('<BH5B', 0x3F, 50, 0, 0, 0, 0, 0)  # All flags, 50Hz
send_command(0x20, config)

# Read stream data
while True:
    data = send_command(0xE3)
    if data:
        counter, timestamp = struct.unpack('<II', data[0:8])
        print(f"Stream #{counter}, time={timestamp}ms")

# Stop streaming
send_command(0x21)
```

### Atomic Channel Configuration Update

```python
import json

CHANNEL_TYPES = {
    'power_output': 0x01,
    'hbridge': 0x02,
    'digital_input': 0x03,
    'analog_input': 0x04,
    'logic': 0x05,
    'number': 0x06,
    'timer': 0x07,
    'filter': 0x08,
    'switch': 0x09,
    'table_2d': 0x0A,
    'table_3d': 0x0B,
    'can_rx': 0x0C,
    'can_tx': 0x0D,
    'pid': 0x0E,
    'lua_script': 0x0F,
    'handler': 0x10,
    'blinkmarine_keypad': 0x11,
}

def set_channel_config(channel_type: str, channel_id: int, config: dict):
    """Send atomic channel configuration update."""
    type_code = CHANNEL_TYPES.get(channel_type)
    if type_code is None:
        return False, f"Unknown channel type: {channel_type}"

    config_json = json.dumps(config, separators=(',', ':')).encode('utf-8')
    json_len = len(config_json)

    # Build payload: type(1) + channel_id(2) + json_len(2) + json_data
    payload = struct.pack('<BHH', type_code, channel_id, json_len) + config_json

    response = send_command(0x66, payload)

    if response is None:
        return False, "No response"

    if len(response) < 5:
        return False, "Response too short"

    resp_channel_id, success, error_code = struct.unpack('<HBH', response[0:5])
    error_msg = response[5:].decode('utf-8', errors='replace') if len(response) > 5 else ""

    return bool(success), error_msg


# Example: Update power output PWM settings
output_config = {
    "channel_id": 105,
    "channel_name": "FuelPump",
    "pins": [5],
    "pwm_enabled": True,
    "pwm_frequency": 200,
    "default_duty": 750,
    "source_channel_id": 50,
}

success, error = set_channel_config('power_output', 105, output_config)
if success:
    print("Output 5 config updated - PWM now active at 200Hz/75%")
else:
    print(f"Failed: {error}")
```

### Data Logging

```python
# Start logging
send_command(0x80)
print("Logging started")

# ... collect data ...

# Stop logging
send_command(0x81)
print("Logging stopped")

# Get list of sessions
response = send_command(0x82)
if response and len(response) >= 2:
    session_count = struct.unpack('<H', response[0:2])[0]
    print(f"Found {session_count} logging sessions")

# Download session data
session_id = 1
offset = 0
chunk_size = 244
session_data = bytearray()

while True:
    request = struct.pack('<III', session_id, offset, chunk_size)
    response = send_command(0x83, request)

    if not response or len(response) < 12:
        break

    resp_session, resp_offset, bytes_read = struct.unpack('<III', response[0:12])
    chunk_data = response[12:12+bytes_read]

    session_data.extend(chunk_data)

    if bytes_read < chunk_size:
        break

    offset += bytes_read

# Save to file
with open(f'session_{session_id}.bin', 'wb') as f:
    f.write(session_data)
print(f"Downloaded: {len(session_data)} bytes")
```

---

## WiFi Configuration (ESP32-C3)

### Access Point Mode (Default)

- **SSID**: `PMU-30-XXXXXX` (last 6 digits of serial)
- **Password**: `pmu30racing`
- **IP**: `192.168.4.1`
- **Port**: `8080` (TCP)

### Client Mode

Configure via web interface at http://192.168.4.1 or through configurator.

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Max Stream Rate | 1000 Hz |
| Typical Latency (UART) | < 5ms |
| Typical Latency (WiFi) | < 20ms |
| Typical Latency (CAN) | < 2ms |
| Max Packet Size | 260 bytes (header + 256B payload) |
| CRC Overhead | 2 bytes (0.8% for max packet) |

---

## Implementation Notes

1. **Timeouts**: All commands should have a 1 second timeout
2. **Retries**: Failed commands should be retried up to 3 times
3. **Chunk Size**: Configuration chunks should not exceed 256 bytes (max payload)
4. **Flow Control**: Wait for ACK before sending next command/chunk
5. **Stream Rates**: Supported rates: 1, 10, 50, 100, 500, 1000 Hz
6. **CRC Validation**: All received packets must be CRC-validated

---

## Protocol Constants

```c
#define PMU_PROTOCOL_START_MARKER  0xAA
#define PMU_PROTOCOL_VERSION       0x02
#define PMU_PROTOCOL_MAX_PAYLOAD   256
#define PMU_PROTOCOL_CAN_ID_BASE   0x600
```

---

## Security Considerations

**Current Version**: No authentication or encryption

**Recommendations**:
- Use on isolated vehicle network only
- Do not expose WiFi AP to internet
- Change default WiFi password
- Monitor for unauthorized access

---

## Error Handling

### NACK Responses

Common error messages:

- `"Unknown command"` - Command not recognized
- `"Invalid channel"` - Channel number out of range
- `"Invalid data"` - Malformed payload
- `"CRC error"` - Checksum mismatch
- `"Busy"` - Device busy processing previous command

### Timeout Handling

- **Packet Timeout**: 1000ms - if no bytes received, packet is discarded
- **Response Timeout**: Client should implement 500ms timeout for responses
- **Stream Timeout**: If no DATA packets received for 2x stream period, restart stream

---

## Troubleshooting

### No Response to Commands

1. Check serial/WiFi connection
2. Verify baud rate (115200)
3. Verify CRC calculation
4. Check start marker (0xAA)
5. Review device logs

### Stream Data Corruption

1. Reduce stream rate
2. Check CRC errors
3. Verify WiFi signal strength
4. Use CAN for critical data

### Configuration Load Fails

1. Validate JSON syntax
2. Check configuration version
3. Verify all required fields present
4. Check device memory available

---

## Changelog

### Version 2.0 (2025-12-29)
- Merged protocol_specification.md and PROTOCOL_DOCUMENTATION.md into single document
- Added comprehensive Python client examples
- Added data logging examples
- Added WiFi configuration section
- Added troubleshooting guide

### Version 1.2 (2025-12-29)
- Added Atomic Channel Configuration Commands (0x66-0x67)
- SET_CHANNEL_CONFIG (0x66) for real-time single channel updates
- CHANNEL_CONFIG_ACK (0x67) response with error handling

### Version 1.1 (2025-12-28)
- Added Device Control Commands (0x70-0x72)
- RESTART_DEVICE (0x70) for soft device reset
- BOOT_COMPLETE (0x72) for boot notification

### Version 1.0 (2025-12-21)
- Initial protocol implementation
- UART, WiFi, and CAN transport support
- Basic commands and telemetry streaming
- JSON configuration loading
- Real-time output control

---

## See Also

- [JSON Configuration](../firmware/JSON_CONFIG.md) - Full JSON configuration format v3.0
- [Standard CAN Stream](standard_can_stream.md) - ECUMaster-compatible CAN broadcast
- [Channel Abstraction](../firmware/CHANNEL_ABSTRACTION.md) - Channel types and system channels

---

**Copyright (c) 2025 R2 m-sport. All rights reserved.**

# PMU-30 Real-Time Control Protocol Documentation

**Version**: 1.0
**Author**: R2 m-sport
**Date**: 2025-12-21

---

## Overview

PMU-30 implements a real-time control protocol for remote monitoring, control, and configuration via UART, WiFi (ESP32-C3), or CAN bus.

### Key Features

- **Binary Protocol**: Efficient binary format for low latency
- **Multi-Transport**: Supports UART (115200 baud), WiFi, and CAN (1Mbps)
- **Real-Time Streaming**: Telemetry data at rates from 1Hz to 1000Hz
- **Remote Control**: Set outputs, PWM, H-bridge modes in real-time
- **Configuration**: Upload/download JSON configuration files
- **Diagnostics**: Firmware version, statistics, fault status

---

## Protocol Structure

### Packet Format

All packets follow this structure:

```
| Start Marker | Command | Length  | Payload (0-256 bytes) | CRC16 |
|    1 byte    | 1 byte  | 2 bytes |      N bytes          | 2 bytes|
```

- **Start Marker**: `0xAA` (packet start identifier)
- **Command**: Command type (see Command Reference)
- **Length**: Payload length in bytes (little-endian)
- **Payload**: Command-specific data
- **CRC16**: CCITT CRC16 checksum of (Marker + Command + Length + Payload)

### CRC16 Calculation

```c
uint16_t crc = 0xFFFF;
for (each byte in packet) {
    crc ^= (uint16_t)byte << 8;
    for (j = 0; j < 8; j++) {
        if (crc & 0x8000)
            crc = (crc << 1) ^ 0x1021;
        else
            crc = crc << 1;
    }
}
```

---

## Transport Interfaces

### UART/WiFi (ESP32-C3)

- **Baud Rate**: 115200 bps
- **Format**: 8N1 (8 data bits, no parity, 1 stop bit)
- **Hardware Flow Control**: None
- **Connection**: USART1 (PA9/PA10) → ESP32-C3

WiFi provides TCP/IP transparent bridge to UART.

### CAN Bus

- **Base CAN ID**: `0x600`
- **Bitrate**: 1 Mbps (CAN FD optional at 5 Mbps data phase)
- **Format**: Standard 11-bit ID
- **Chunking**: Packets > 8 bytes split into multiple frames

---

## Command Reference

### Basic Commands (0x00-0x1F)

#### 0x01 - PING
**Request**:
```
[0xAA][0x01][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0x01][N][...echo data...][CRC]
```
Echo back request data to verify connectivity.

---

#### 0x02 - GET_VERSION
**Request**:
```
[0xAA][0x02][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0x02][N]["PMU-30 v1.0.0"][CRC]
```
Returns firmware version string.

---

#### 0x03 - GET_SERIAL
**Request**:
```
[0xAA][0x03][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0x03][N]["PMU30-XXXXXXXX"][CRC]
```
Returns device serial number.

---

### Telemetry Commands (0x20-0x3F)

#### 0x20 - START_STREAM
**Request**:
```
[0xAA][0x20][0x08][CONFIG][CRC]

CONFIG (8 bytes):
  Byte 0: Flags (bit 0: outputs, bit 1: inputs, bit 2: CAN,
                 bit 3: temps, bit 4: voltages, bit 5: faults)
  Byte 1-2: Stream rate (Hz, little-endian)
  Byte 3-7: Reserved
```

**Response**:
```
[0xAA][0xE0][0x01][0x20][CRC]  // ACK
```

Start streaming telemetry data at specified rate.

---

#### 0x21 - STOP_STREAM
**Request**:
```
[0xAA][0x21][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0xE0][0x01][0x21][CRC]  // ACK
```

Stop telemetry streaming.

---

#### 0x22 - GET_OUTPUTS
**Request**:
```
[0xAA][0x22][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0x22][0x3C][...60 bytes...][CRC]

Data (60 bytes for 30 channels):
  For each channel (2 bytes):
    Byte 0: State (0=OFF, 1=ON, 2=PWM, 3=FAULT)
    Byte 1: PWM duty (0-255, scaled from 0-1000)
```

Get all output states.

---

#### 0x23 - GET_INPUTS
**Request**:
```
[0xAA][0x23][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0x23][0x28][...40 bytes...][CRC]

Data (40 bytes for 20 inputs):
  For each input (2 bytes, little-endian):
    Raw ADC value (0-1023)
```

Get all input values.

---

### Control Commands (0x40-0x5F)

#### 0x40 - SET_OUTPUT
**Request**:
```
[0xAA][0x40][0x02][CHANNEL][STATE][CRC]

  CHANNEL: Output channel (0-29)
  STATE: 0=OFF, 1=ON
```

**Response**:
```
[0xAA][0xE0][0x01][0x40][CRC]  // ACK
```

Set output on/off state.

---

#### 0x41 - SET_PWM
**Request**:
```
[0xAA][0x41][0x03][CHANNEL][DUTY_L][DUTY_H][CRC]

  CHANNEL: Output channel (0-29)
  DUTY: PWM duty cycle (0-1000, little-endian)
```

**Response**:
```
[0xAA][0xE0][0x01][0x41][CRC]  // ACK
```

Set PWM duty cycle (also enables output).

---

#### 0x42 - SET_HBRIDGE
**Request**:
```
[0xAA][0x42][0x04][BRIDGE][MODE][DUTY_L][DUTY_H][CRC]

  BRIDGE: H-bridge number (0-3)
  MODE: 0=Coast, 1=Forward, 2=Reverse, 3=Brake
  DUTY: PWM duty cycle (0-1000, little-endian)
```

**Response**:
```
[0xAA][0xE0][0x01][0x42][CRC]  // ACK
```

Set H-bridge mode and duty cycle.

---

### Configuration Commands (0x60-0x7F)

#### 0x60 - LOAD_CONFIG
**Request**:
```
[0xAA][0x60][N][...JSON config...][CRC]

  Payload: JSON configuration string (matching configurator format)
```

**Response**:
```
[0xAA][0x60][N]["Loaded: X inputs, Y outputs"][CRC]
```

Load configuration from JSON string.

---

#### 0x63 - UPLOAD_CONFIG (Chunked Transfer)
**Request** (First chunk):
```
[0xAA][0x63][N][CHUNK_INDEX_L][CHUNK_INDEX_H][TOTAL_SIZE_4B][...data...][CRC]
```

**Response**:
```
[0xAA][0xE0][0x01][0x63][CRC]  // ACK for each chunk
```

Upload large configuration in chunks (256 bytes per chunk).

---

#### 0x66 - SET_CHANNEL_CONFIG (Atomic Update)
**Request**:
```
[0xAA][0x66][N][TYPE][CHANNEL_ID_L][CHANNEL_ID_H][JSON_LEN_L][JSON_LEN_H][...JSON config...][CRC]

  TYPE: Channel type discriminator (1 byte):
    0x01 = Power Output
    0x02 = H-Bridge
    0x03 = Digital Input
    0x04 = Analog Input
    0x05 = Logic
    0x06 = Number
    0x07 = Timer
    0x08 = Filter
    0x09 = Switch
    0x0A = Table 2D
    0x0B = Table 3D
    0x0C = CAN RX
    0x0D = CAN TX
    0x0E = PID Controller
    0x0F = Lua Script
    0x10 = Handler
    0x11 = BlinkMarine Keypad
  CHANNEL_ID: Numeric channel ID (2 bytes, little-endian)
  JSON_LEN: Length of JSON config string (2 bytes, little-endian)
  JSON config: UTF-8 JSON configuration string
```

**Response**:
```
[0xAA][0x67][N][CHANNEL_ID_L][CHANNEL_ID_H][SUCCESS][ERROR_CODE_L][ERROR_CODE_H][...error message...][CRC]

  CHANNEL_ID: Echo of requested channel ID (2 bytes, little-endian)
  SUCCESS: 0x01 = success, 0x00 = failure
  ERROR_CODE: Error code if failed (2 bytes, little-endian)
    0x0000 = No error
    0x0001 = Invalid channel type
    0x0002 = Channel not found
    0x0003 = JSON parse error
    0x0004 = Validation error
  Error message: Human-readable error string (variable length)
```

Push a single channel configuration to the device without full configuration reload. This enables real-time parameter changes from the UI.

**Use Case**: When the user modifies a power output's PWM frequency or changes a logic channel's condition in the configurator, this command pushes just that channel's config to the firmware instantly, without disrupting other running channels.

---

#### 0x67 - CHANNEL_CONFIG_ACK
**Direction**: Device → Host (response to SET_CHANNEL_CONFIG)

See 0x66 response format above.

---

### Logging Commands (0x80-0x9F)

#### 0x80 - START_LOGGING
**Request**:
```
[0xAA][0x80][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0xE0][0x01][0x80][CRC]  // ACK
```

Start data logging session. Logging uses configured channels and sample rate.

---

#### 0x81 - STOP_LOGGING
**Request**:
```
[0xAA][0x81][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0xE0][0x01][0x81][CRC]  // ACK
```

Stop current logging session and flush data to flash.

---

#### 0x82 - GET_LOG_INFO
**Request**:
```
[0xAA][0x82][0x00][0x00][CRC]
```

**Response**:
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

Get list of all logging sessions stored in flash.

---

#### 0x83 - DOWNLOAD_LOG
**Request**:
```
[0xAA][0x83][0x0C][SESSION_ID_4B][OFFSET_4B][LENGTH_4B][CRC]

  SESSION_ID: Session to download
  OFFSET: Byte offset in session data
  LENGTH: Bytes to download (max 244)
```

**Response**:
```
[0xAA][0x83][N][SESSION_ID_4B][OFFSET_4B][BYTES_READ_4B][...data...][CRC]
```

Download session data in chunks. Call multiple times with increasing offset to download complete session.

---

#### 0x84 - ERASE_LOGS
**Request**:
```
[0xAA][0x84][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0xE0][0x01][0x84][CRC]  // ACK
```

Erase all logging data from flash. WARNING: This operation is irreversible.

---

### Response Codes (0xE0-0xFF)

#### 0xE0 - ACK
```
[0xAA][0xE0][0x01][COMMAND][CRC]
```
Command acknowledged successfully.

---

#### 0xE1 - NACK
```
[0xAA][0xE1][N][COMMAND]["Error reason"][CRC]
```
Command failed with error message.

---

#### 0xE3 - DATA
```
[0xAA][0xE3][N][...telemetry data...][CRC]
```
Telemetry data stream packet.

---

## Telemetry Data Format

When streaming is active, DATA packets (0xE3) are sent at configured rate:

```
[0xAA][0xE3][N][COUNTER_4B][TIMESTAMP_4B][...data...][CRC]

Data structure (variable, based on enabled flags):
  - Stream counter (4 bytes)
  - Timestamp ms (4 bytes)
  - Outputs (30 bytes, if enabled): State for each channel
  - Inputs (40 bytes, if enabled): Raw ADC values (2 bytes each)
  - Voltages (4 bytes, if enabled): Battery voltage (2B), Total current (2B)
  - Temperatures (4 bytes, if enabled): MCU temp (2B), Board temp (2B)
  - Faults (2 bytes, if enabled): Status byte, Fault flags byte
```

---

## Example: Python Client

### Connect and Get Version

```python
import serial
import struct

# Open serial port (or network socket for WiFi)
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
    packet += struct.pack('<H', len(payload))  # Length (little-endian)
    packet += payload
    crc = calc_crc16(packet)
    packet += struct.pack('<H', crc)
    ser.write(packet)

    # Read response
    response = ser.read(4)  # Read header
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

# Start streaming at 10Hz
config = struct.pack('<BH5B', 0x3F, 10, 0, 0, 0, 0, 0)  # All flags enabled, 10Hz
send_command(0x20, config)

# Read stream data
while True:
    data = send_command(0xE3)  # Read DATA packet
    if data:
        counter, timestamp = struct.unpack('<II', data[0:8])
        print(f"Stream #{counter}, time={timestamp}ms")
```

---

### Set All Outputs from JSON

```python
import json

# Load configuration from file
with open('pmu30_config.json', 'r') as f:
    config_json = f.read()

# Send to device
response = send_command(0x60, config_json.encode('utf-8'))
print(response.decode('utf-8'))
```

---

### Atomic Channel Configuration Update

Update a single channel's configuration without full config reload.
This is useful for real-time tuning from the configurator UI.

```python
import json

# Channel type discriminators
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
    """
    Send atomic channel configuration update.

    Args:
        channel_type: Type string (e.g., 'power_output', 'logic')
        channel_id: Numeric channel ID
        config: Configuration dictionary

    Returns:
        Tuple of (success, error_message)
    """
    type_code = CHANNEL_TYPES.get(channel_type)
    if type_code is None:
        return False, f"Unknown channel type: {channel_type}"

    # Serialize config to compact JSON
    config_json = json.dumps(config, separators=(',', ':')).encode('utf-8')
    json_len = len(config_json)

    # Build payload: type(1) + channel_id(2) + json_len(2) + json_data
    payload = struct.pack('<BHH', type_code, channel_id, json_len) + config_json

    # Send SET_CHANNEL_CONFIG (0x66)
    response = send_command(0x66, payload)

    if response is None:
        return False, "No response"

    # Parse CHANNEL_CONFIG_ACK (0x67) response
    # Format: channel_id(2) + success(1) + error_code(2) + error_msg(N)
    if len(response) < 5:
        return False, "Response too short"

    resp_channel_id, success, error_code = struct.unpack('<HBH', response[0:5])
    error_msg = response[5:].decode('utf-8', errors='replace') if len(response) > 5 else ""

    return bool(success), error_msg


# Example 1: Update power output PWM settings
output_config = {
    "channel_id": 105,              # Output 5 (100 + index)
    "channel_name": "FuelPump",
    "pins": [5],
    "pwm_enabled": True,
    "pwm_frequency": 200,           # 200 Hz
    "default_duty": 750,            # 75% duty cycle
    "source_channel_id": 50,        # Linked to analog input
    "invert": False,
    "retry_count": 3,
    "retry_delay_ms": 100
}

success, error = set_channel_config('power_output', 105, output_config)
if success:
    print("Output 5 config updated - PWM now active at 200Hz/75%")
else:
    print(f"Failed: {error}")


# Example 2: Update logic channel condition
logic_config = {
    "channel_id": 201,
    "channel_name": "OverheatWarning",
    "operator": "greater_than",
    "input_a_channel_id": 1002,     # MCU temperature (system channel)
    "threshold": 85000,              # 85°C in milli-degrees
    "hysteresis": 5000               # 5°C hysteresis
}

success, error = set_channel_config('logic', 201, logic_config)
if success:
    print("Logic channel updated - overheat threshold set to 85°C")
else:
    print(f"Failed: {error}")


# Example 3: Update PID controller tuning
pid_config = {
    "channel_id": 250,
    "channel_name": "IdleControl",
    "input_channel_id": 10,          # RPM sensor
    "setpoint_channel_id": 220,      # Target RPM number channel
    "output_channel_id": 108,        # Idle valve output
    "kp": 1500,                      # Proportional gain (scaled x1000)
    "ki": 200,                       # Integral gain (scaled x1000)
    "kd": 50,                        # Derivative gain (scaled x1000)
    "output_min": 0,
    "output_max": 1000,
    "sample_time_ms": 20
}

success, error = set_channel_config('pid', 250, pid_config)
if success:
    print("PID tuning updated - Kp=1.5, Ki=0.2, Kd=0.05")
else:
    print(f"Failed: {error}")
```

**Error Codes:**

| Code | Meaning |
|------|---------|
| 0x0000 | Success |
| 0x0001 | Invalid channel type |
| 0x0002 | Channel not found |
| 0x0003 | JSON parse error |
| 0x0004 | Validation error |

---

### Data Logging Example

```python
# Start logging
send_command(0x80)  # START_LOGGING
print("Logging started")

# ... drive the vehicle, collect data ...

# Stop logging
send_command(0x81)  # STOP_LOGGING
print("Logging stopped")

# Get list of sessions
response = send_command(0x82)  # GET_LOG_INFO
if response and len(response) >= 2:
    session_count = struct.unpack('<H', response[0:2])[0]
    print(f"Found {session_count} logging sessions")

    # Parse each session
    offset = 2
    for i in range(session_count):
        if offset + 21 <= len(response):
            session_id, start_time, duration, bytes_used, sample_count, status = \
                struct.unpack('<IIIIIB', response[offset:offset+21])
            print(f"Session {session_id}: {bytes_used} bytes, {sample_count} samples")
            offset += 21

# Download session data
session_id = 1
offset = 0
chunk_size = 244

# Download in chunks
session_data = bytearray()
while True:
    # Request chunk: session_id (4B), offset (4B), length (4B)
    request = struct.pack('<III', session_id, offset, chunk_size)
    response = send_command(0x83, request)  # DOWNLOAD_LOG

    if not response or len(response) < 12:
        break

    # Parse response: session_id (4B), offset (4B), bytes_read (4B), data
    resp_session, resp_offset, bytes_read = struct.unpack('<III', response[0:12])
    chunk_data = response[12:12+bytes_read]

    session_data.extend(chunk_data)
    print(f"Downloaded {len(session_data)} bytes...")

    if bytes_read < chunk_size:
        break  # Last chunk

    offset += bytes_read

# Save to file
with open(f'session_{session_id}.bin', 'wb') as f:
    f.write(session_data)
print(f"Downloaded session {session_id}: {len(session_data)} bytes")

# Erase all logs (use with caution!)
# send_command(0x84)  # ERASE_LOGS
```

---

## WiFi Configuration (ESP32-C3)

ESP32-C3 module creates WiFi AP or connects to existing network:

### Access Point Mode
- **SSID**: `PMU-30-XXXXXX` (last 6 digits of serial)
- **Password**: `pmu30racing`
- **IP**: `192.168.4.1`
- **Port**: `8080` (TCP)

### Client Mode
Configure via web interface at http://192.168.4.1 or through configurator.

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
- **Stream Timeout**: If no DATA packets received for 2× stream period, restart stream

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

## Security Considerations

**Current Version**: No authentication or encryption

**Future Enhancements**:
- Password protection for configuration changes
- TLS/SSL for WiFi connections
- Encrypted firmware updates
- Access control lists

**Recommendations**:
- Use on isolated vehicle network only
- Do not expose WiFi AP to internet
- Change default WiFi password
- Monitor for unauthorized access

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

## Device Control Commands (0x70-0x7F)

### 0x70 - RESTART_DEVICE
**Request**:
```
[0xAA][0x70][0x00][0x00][CRC]
```

**Response**:
```
[0xAA][0x71][0x00][0x00][CRC]  // RESTART_ACK
```

Restart the device. The device will:
1. Send RESTART_ACK immediately
2. Perform soft reset
3. Reinitialize all subsystems
4. Load configuration from flash
5. Send BOOT_COMPLETE to all connected clients

---

### 0x71 - RESTART_ACK
**Direction**: Device → Host (response to RESTART_DEVICE)

Acknowledges that restart command was received and restart is beginning.

---

### 0x72 - BOOT_COMPLETE
**Direction**: Device → Host (unsolicited)
```
[0xAA][0x72][0x00][0x00][CRC]
```

Sent by the device after successful initialization/restart to signal that:
1. All subsystems are initialized
2. Configuration is loaded
3. Device is ready to accept commands

**Use Case**: When the configurator receives BOOT_COMPLETE, it should re-read the configuration from the device to synchronize state. This is important after restart, as the device reloads config from flash which may differ from the configurator's current state.

---

## Changelog

### Version 1.2 (2025-12-29)
- Added Atomic Channel Configuration Commands (0x66-0x67)
- SET_CHANNEL_CONFIG (0x66) for real-time single channel updates
- CHANNEL_CONFIG_ACK (0x67) response with error handling
- Enables UI changes to be pushed to firmware without full config reload

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

**© 2025 R2 m-sport. All rights reserved.**

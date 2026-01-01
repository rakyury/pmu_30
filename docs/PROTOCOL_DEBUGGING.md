# Protocol Communication Debugging Guide

## Lesson Learned: Protocol Mismatch Investigation

This document captures the debugging experience from December 2024 when configurator stopped communicating with Nucleo-F446RE firmware.

---

## Problem Description

**Symptoms:**
- Device shows "initialization OK" in terminal (TX works)
- No response to any commands from configurator
- Telemetry not updating in Variables Inspector

**Root Cause:**
Two critical bugs in Python protocol implementation:

### Bug 1: CRC Algorithm Mismatch

| Implementation | Algorithm | Polynomial | Shift |
|----------------|-----------|------------|-------|
| **Firmware (C)** | CRC-CCITT | 0x1021 | Left |
| **Python (WRONG)** | Modbus CRC | 0xA001 | Right |

**Wrong Python code:**
```python
def calc_crc_modbus(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001  # WRONG!
            else:
                crc >>= 1
    return crc
```

**Correct Python code:**
```python
def calc_crc_ccitt(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8  # XOR into high byte
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF  # Left shift!
            else:
                crc = (crc << 1) & 0xFFFF
    return crc
```

### Bug 2: Length Field Interpretation

**Frame format:**
```
┌────────┬────────┬─────────┬────────────┬───────┐
│ 0xAA   │ Length │ Command │   Payload  │ CRC16 │
│ 1 byte │ 2 bytes│  1 byte │  N bytes   │2 bytes│
└────────┴────────┴─────────┴────────────┴───────┘
```

| Implementation | Length field contains |
|----------------|----------------------|
| **Firmware (C)** | Payload size only |
| **Python (WRONG)** | Payload + Command (1 extra byte) |

**Wrong:**
```python
length = 1 + len(payload)  # WRONG - includes command
```

**Correct:**
```python
length = len(payload)  # Payload only, NOT including command byte
```

---

## Debugging Steps

### 1. Verify TX Works
```
Terminal shows: "initialization OK"
→ Firmware boots correctly, UART TX works
```

### 2. Check RX at Firmware Level
Add debug counters in firmware:
```c
volatile uint32_t g_uart_rx_count = 0;
volatile uint8_t g_last_rx_byte = 0;

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    g_uart_rx_count++;
    g_last_rx_byte = uart_rx_byte;
    // ...
}
```

### 3. Create Minimal Test Script
```python
import serial
import struct

def calc_crc_ccitt(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def build_frame(cmd, payload=b''):
    length = len(payload)  # Payload only!
    crc_data = struct.pack('<H', length) + bytes([cmd]) + payload
    crc = calc_crc_ccitt(crc_data)
    return bytes([0xAA]) + crc_data + struct.pack('<H', crc)

# Test PING
ser = serial.Serial('COM11', 115200, timeout=1)
frame = build_frame(0x01)  # PING
print(f"Sending: {frame.hex()}")
ser.write(frame)
response = ser.read(100)
print(f"Response: {response.hex()}")
```

### 4. Compare CRC Values
```python
# Test vector: PING command
data = bytes([0x00, 0x00, 0x01])  # length=0, cmd=PING
crc_ccitt = calc_crc_ccitt(data)  # Correct: 0x1AE1
crc_modbus = calc_crc_modbus(data)  # Wrong: different value
print(f"CRC-CCITT: {crc_ccitt:04X}")
```

---

## Prevention Measures

### 1. Shared Test Vectors
Create `tests/protocol_vectors.json`:
```json
{
  "vectors": [
    {
      "name": "PING",
      "cmd": 1,
      "payload": "",
      "expected_crc": "1AE1",
      "expected_frame": "AA00000101E11A"
    },
    {
      "name": "START_STREAM_100Hz",
      "cmd": 48,
      "payload": "6400",
      "expected_crc": "ABCD",
      "expected_frame": "AA02003064000BCDAB"
    }
  ]
}
```

### 2. CRC Verification on Both Sides
Firmware logs received CRC and calculated CRC:
```c
uint16_t received_crc = ...;
uint16_t calculated_crc = PMU_Protocol_CRC16(...);
if (received_crc != calculated_crc) {
    DEBUG_PRINT("CRC mismatch: got %04X, expected %04X", 
                received_crc, calculated_crc);
}
```

### 3. Protocol Buffer Size Check
**Issue found:** RX buffer was 512 bytes, LOAD_CONFIG frame was 2010 bytes.

**Fix:** Increase buffer to 2560 bytes:
```c
typedef struct {
    uint8_t rx_buffer[2560];  // Was 512 - too small!
    // ...
} PMU_Protocol_Buffer_t;
```

---

## Key Takeaways

1. **CRC algorithm MUST match exactly** - polynomial, shift direction, initial value
2. **Length field definition MUST be documented** - payload only vs payload+command
3. **Buffer sizes MUST accommodate max frame** - 2048 payload + headers
4. **Create shared test vectors** - run same tests on both implementations
5. **Add debug logging** - byte counters, CRC values, buffer states

---

## Reference: Correct Protocol Implementation

### Frame Building (Python)
```python
def build_frame(cmd: int, payload: bytes = b'') -> bytes:
    """Build PMU-30 protocol frame."""
    length = len(payload)  # Payload size only
    crc_data = struct.pack('<H', length) + bytes([cmd]) + payload
    crc = calc_crc_ccitt(crc_data)
    return bytes([0xAA]) + crc_data + struct.pack('<H', crc)
```

### Frame Parsing (Python)
```python
def parse_frame(data: bytes) -> tuple:
    """Parse PMU-30 protocol frame."""
    if len(data) < 6 or data[0] != 0xAA:
        return None
    
    length = struct.unpack_from('<H', data, 1)[0]
    cmd = data[3]
    payload = data[4:4+length]
    received_crc = struct.unpack_from('<H', data, 4+length)[0]
    
    # Verify CRC
    crc_data = data[1:4+length]
    calculated_crc = calc_crc_ccitt(crc_data)
    
    if received_crc != calculated_crc:
        return None
    
    return (cmd, payload)
```

### CRC-CCITT (C Reference)
```c
uint16_t PMU_Protocol_CRC16(const uint8_t* data, uint16_t length) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc = crc << 1;
            }
        }
    }
    return crc;
}
```

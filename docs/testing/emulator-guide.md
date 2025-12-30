# PMU-30 Emulator Guide

**Version:** 1.0
**Date:** December 2025

---

## 1. Overview

The PMU-30 Emulator is a native Windows/Linux executable that simulates the STM32H7 firmware without requiring actual hardware. It enables development, testing, and debugging of the Configurator application and firmware logic.

### Purpose

- **Development**: Test Configurator features without hardware
- **Integration Testing**: Automated testing via the socket protocol
- **Demonstration**: Show PMU functionality to stakeholders
- **CI/CD**: Run tests in GitHub Actions or similar

---

## 2. Building the Emulator

### Prerequisites

- PlatformIO
- MSYS2/MinGW-w64 (Windows) or GCC (Linux)
- Python 3.8+

### Build Commands

```bash
# From firmware directory
cd firmware

# Build emulator
python -m platformio run -e pmu30_emulator

# Executable location
# Windows: .pio/build/pmu30_emulator/program.exe
# Linux:   .pio/build/pmu30_emulator/program
```

### Build Configuration

The emulator is configured in `platformio.ini`:

```ini
[env:pmu30_emulator]
platform = native
build_flags =
    -DPMU_EMULATOR
    -DUNIT_TEST
    # ... other flags
```

The `PMU_EMULATOR` define enables emulator-specific code paths.

---

## 3. Running the Emulator

### Command Line

```bash
# Start with default settings
./program.exe

# Start with specific port
./program.exe --port 9876

# Start with verbose logging
./program.exe --verbose
```

### Connection

The emulator listens on TCP port `9876` by default. The Configurator connects to this port for communication.

### Web UI (Optional)

The emulator includes a simple web UI at `http://localhost:8080` for monitoring state and injecting test inputs.

---

## 4. What's Emulated (Full Functionality)

These components are **fully functional** in the emulator:

| Component | Description |
|-----------|-------------|
| **Channel System** | All channel types (inputs, outputs, logic, numbers, timers, etc.) |
| **Logic Functions** | All 25+ logic operations (AND, OR, comparisons, hysteresis, etc.) |
| **Configuration Parser** | Full JSON configuration loading and validation |
| **Protocol Handler** | Complete binary protocol with CRC16 |
| **Telemetry Streaming** | Real-time telemetry at configurable rates |
| **Timer Channels** | Accurate timing using system clock |
| **Filter Channels** | Low-pass, moving average filters |
| **Table Lookups** | 2D and 3D interpolation tables |
| **Number Operations** | Math operations (add, multiply, scale, clamp, etc.) |
| **Protection Logic** | Fault detection and retry logic (simulated) |
| **Load Shedding** | Priority-based load shedding algorithm |

---

## 5. What's Stubbed (Limited/No Functionality)

These components are **stubbed** and have limited or no real functionality:

### 5.1 ESP32-C3 WiFi/Bluetooth Module

| Function | Emulator Behavior |
|----------|-------------------|
| `PMU_ESP32_Init()` | Always returns `HAL_OK`, sets state to READY |
| `PMU_ESP32_IsReady()` | Always returns `true` |
| `PMU_ESP32_SendCommand()` | Returns `OK` without sending anything |
| `PMU_ESP32_GetInfo()` | Returns dummy values (MAC: `00:00:00:00:00:00`) |

**Impact**: WiFi AP mode, WiFi STA connections, BLE advertising, and BLE data transfer are not functional. Configuration is accepted but nothing happens.

**Workaround**: Use real hardware for WiFi/Bluetooth testing, or mock the Configurator's network layer for UI testing.

### 5.2 UART/Serial Communication (ESP32)

| Function | Emulator Behavior |
|----------|-------------------|
| UART3 initialization | Skipped |
| UART interrupts | Not used |
| Ring buffer RX | Empty |

**Impact**: No actual AT command communication with ESP32.

### 5.3 Hardware ADC

| Component | Emulator Behavior |
|-----------|-------------------|
| ADC channels | Read from `emu_state.json` or set via protocol |
| DMA transfers | Not used |
| ADC calibration | Skipped |

**Workaround**: Use `EMU_SET_ANALOG_INPUT` protocol command or modify `emu_state.json` to set analog values.

### 5.4 Hardware PWM

| Component | Emulator Behavior |
|-----------|-------------------|
| Timer PWM outputs | State tracked but no hardware |
| PWM frequency | Stored but not generated |
| Duty cycle | Stored and reported in telemetry |

**Impact**: PWM waveforms are not generated. Output state and duty cycle are tracked for logic and telemetry.

### 5.5 PROFET High-Side Switches

| Component | Emulator Behavior |
|-----------|-------------------|
| Current sensing | Simulated based on state |
| Fault detection | Can be injected via protocol |
| Temperature sensing | Fixed/configurable value |

**Workaround**: Use `EMU_INJECT_FAULT` to simulate overcurrent, short circuit, etc.

### 5.6 H-Bridge Motor Drivers

| Component | Emulator Behavior |
|-----------|-------------------|
| Motor control | Direction/duty tracked |
| Position feedback | Simulated ADC value |
| PID control | Functional with simulated feedback |

**Impact**: No actual motor movement. Position can be set via `EMU_SET_ANALOG_INPUT`.

### 5.7 CAN Bus

| Component | Emulator Behavior |
|-----------|-------------------|
| CAN TX | Messages logged, not transmitted |
| CAN RX | Inject via `EMU_INJECT_CAN` protocol command |
| CAN FD | Not supported |

**Workaround**: Use `EMU_INJECT_CAN` to simulate incoming CAN messages.

### 5.8 SPI Flash (External Storage)

| Component | Emulator Behavior |
|-----------|-------------------|
| Flash read/write | Uses local file (`emu_flash.bin`) |
| Configuration save | Saved to file |
| Data logging | Saved to file |

**Impact**: Fully functional but uses file system instead of SPI flash.

### 5.9 LIN Bus

| Component | Emulator Behavior |
|-----------|-------------------|
| LIN master | Stubbed |
| LIN slave | Stubbed |

**Impact**: LIN communication is not functional.

### 5.10 Real-Time Clock

| Component | Emulator Behavior |
|-----------|-------------------|
| RTC time | Uses system time |
| Backup battery | N/A |

**Impact**: Fully functional using host system clock.

---

## 6. Protocol Commands for Testing

The emulator supports special protocol commands for testing:

| Command | Code | Description |
|---------|------|-------------|
| `EMU_INJECT_FAULT` | `0x80` | Inject fault on output channel |
| `EMU_CLEAR_FAULT` | `0x81` | Clear fault on output channel |
| `EMU_SET_VOLTAGE` | `0x82` | Set battery voltage (mV) |
| `EMU_SET_TEMPERATURE` | `0x83` | Set board temperature (°C) |
| `EMU_SET_DIGITAL_INPUT` | `0x84` | Set digital input state |
| `EMU_SET_OUTPUT` | `0x85` | Force output state |
| `EMU_SET_ANALOG_INPUT` | `0x86` | Set analog input voltage (mV) |
| `EMU_INJECT_CAN` | `0x88` | Inject CAN message |

### Example: Inject Overcurrent Fault

```python
# Python example using protocol
frame = FrameBuilder.emu_inject_fault(channel=0, fault_type=0x01)  # OC
await transport.send(encode_frame(frame))
```

### Example: Set Digital Input

```python
# Set digital input 3 to HIGH
frame = FrameBuilder.emu_set_digital_input(channel=3, state=True)
await transport.send(encode_frame(frame))
```

---

## 7. State Persistence

The emulator saves/loads state from `emu_state.json`:

```json
{
  "digital_inputs": [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  "analog_inputs": [2500, 1000, 3300, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  "battery_voltage_mv": 13800,
  "board_temperature_c": 45,
  "ambient_temperature_c": 25
}
```

Edit this file to set initial conditions before starting the emulator.

---

## 8. Known Limitations Summary

| Category | Limitation |
|----------|------------|
| **WiFi** | Stubbed - config accepted but no network |
| **Bluetooth** | Stubbed - config accepted but no BLE |
| **CAN TX** | Logged only, not transmitted |
| **LIN** | Fully stubbed |
| **Hardware PWM** | Duty tracked, no waveform |
| **Real current** | Simulated, not measured |
| **Flash writes** | Uses filesystem |
| **Boot time** | Instant (no hardware init) |

---

## 9. Troubleshooting

### Emulator Won't Start

```
Error: Port 9876 already in use
```

**Solution**: Kill existing emulator instance or use `--port <other>`.

### Configurator Can't Connect

1. Verify emulator is running
2. Check firewall settings
3. Ensure correct port in Configurator settings

### Tests Fail Randomly

- Increase `asyncio.sleep()` delays between operations
- Check for race conditions in state updates
- Verify emulator was reset between tests

### WiFi/BT Tests Always Pass

This is expected! ESP32 functions are stubbed to return success. For actual WiFi/BT testing, use real hardware.

---

## 10. Best Practices

1. **Reset between tests**: Send `RESTART_DEVICE` or restart emulator
2. **Use delays**: Allow 100-500ms for state propagation
3. **Check telemetry**: Verify state via telemetry, not just command ACKs
4. **Document hardware-only tests**: Mark tests that require real hardware
5. **Mock network layer**: For WiFi/BT UI testing, mock at application level

---

## See Also

- [Integration Testing Guide](integration-testing-guide.md) - Hardware-in-loop testing
- [Unit Testing Guide](unit-testing-guide.md) - Module-level testing
- [Protocol Reference](../reference/protocol.md) - Binary protocol details

---

**Document Version:** 1.0
**Last Updated:** December 2025

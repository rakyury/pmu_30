# PMU-30 - Automotive Power Management Unit

Professional 30-channel Power Management Unit for motorsport applications.

## Overview

PMU-30 is a high-performance power distribution module designed for racing and high-performance automotive applications. Built on STM32H7 microcontroller with 30 intelligent PROFET 2-based outputs capable of 40A continuous (160A inrush) per channel.

## Key Features

### Hardware
- **30 Power Outputs**: PROFET 2 based, 40A continuous, 160A inrush per channel
- **4x Dual H-Bridge Outputs**: 30A per bridge for motor control (wipers, fans, actuators)
- **Microcontroller**: STM32H7 series (high-performance ARM Cortex-M7, 480MHz)
- **Connectivity**:
  - 2x CAN FD interfaces (5Mbps)
  - 2x CAN 2.0 A/B interfaces
  - 1x LIN bus (LIN 2.2A)
  - **ESP32-C3 Module** for wireless connectivity:
    - WiFi (AP mode, STA mode, or dual AP+STA)
    - Bluetooth Low Energy (BLE 5.0)
    - Web server for remote monitoring
  - USB-C (configuration & updates)
  - RAD-LOK connector (high-density automotive)
- **Inputs**: 20x ADC channels (10-bit, protected), 10x DAC outputs
- **Sensors**:
  - 3-axis accelerometer + 3-axis gyroscope
  - Board temperature monitoring
  - Per-channel temperature monitoring
- **Memory**: 512MB for data logging (500Hz)
- **Sensor Power**: 5V 500mA monitored output
- **Real-time Clock**: RTC with battery backup
- **LED Indicators**: 30x bicolor LEDs (per-channel) + system status
- **Operating Range**: 6-22V (ISO 7637 transient immunity), -40°C to +125°C (AEC-Q100 Grade 1)

### Output Features
- PWM control with configurable frequency
- Soft-start functionality
- Duty cycle control (fixed value or mapped to input channel)
- **Load Shedding Priority** (0=critical, never shed → 10=lowest, shed first)
- Pin merging for high-current outputs (2x or 3x combined)
- Individual channel protection:
  - Overcurrent protection with configurable retry
  - Overtemperature protection with thermal derating
  - Short circuit detection
  - Open load detection

### Software Features
- **Advanced Logic Engine**:
  - 100 virtual functions, 250 operations
  - Logic operations: isTrue, isFalse, =, !=, <, <=, >, >=, AND, OR, XOR
  - Special functions: Flash, Pulse, Toggle, Set/Reset Latch
  - Update frequency: 500Hz
- **Lua Scripting**: Embedded Lua 5.4 for custom logic (like RaceCapture)
  - 256KB RAM, 128KB flash for scripts
  - Full API access to inputs, outputs, CAN, sensors
  - Example scripts: launch control, progressive nitrous, intelligent cooling
- **CAN Integration**:
  - DBC/CANX import/export support
  - Automatic signal parsing and mapping
  - Compatible with ECU databases (Link, Haltech, MoTeC, etc.)
  - Live CAN signal monitoring with decoded values
- **Look-up Tables**: Custom input/output mapping with interpolation
- **PID Controllers**: Closed-loop control systems
- **Wiper Control**: Dedicated wiper output with park/brake function
- **Blinker Logic**: Built-in turn signal control
- **CAN Keyboard Support**: BlinkMarine PKP keypads via CANopen
- **Data Logging**: 500Hz high-speed logging to 512MB internal memory
- **OTA Updates**: Over-the-air firmware updates
- **Web Interface**: Full monitoring and configuration via WiFi

## Documentation

### Quick Start
- [Quick Start Guide](docs/QUICKSTART.md) - Get running in 5 minutes

### Architecture
- [Firmware Architecture](docs/firmware_architecture.md) - Complete firmware design
- [Unified Channel System](docs/architecture/unified-channel-system.md) - Channel abstraction layer
- [Logic Functions Framework](docs/architecture/logic-functions-framework.md) - 64 logic functions

### Reference
- [Configuration Reference](docs/reference/configuration.md) - Binary config format
- [Protocol Reference](docs/reference/protocol.md) - Binary protocol details
- [Channel Types](docs/api/channel-types.md) - All channel type specifications

### Configuration Guides
- [Power Outputs](docs/configuration/power-outputs.md) - Output configuration
- [Digital Inputs](docs/configuration/digital-inputs.md) - Digital input setup
- [Analog Inputs](docs/configuration/analog-inputs.md) - ADC configuration
- [CAN Messages](docs/configuration/can-messages.md) - CAN RX/TX setup

### Testing
- [Emulator Guide](docs/testing/emulator-guide.md) - Desktop testing without hardware
- [Integration Testing](docs/testing/integration-testing-guide.md) - Hardware-in-loop testing

### Hardware
- [PCB Design Specification](docs/PCB_DESIGN_SPECIFICATION.md) - PCB engineering spec

## Project Structure

```
pmu_30/
├── docs/                           # Documentation
│   ├── architecture/              # System architecture docs
│   ├── configuration/             # Channel configuration guides
│   ├── reference/                 # Protocol & config schema
│   ├── testing/                   # Testing guides (emulator, integration)
│   └── firmware_architecture.md   # Complete firmware design
├── hardware/                      # Hardware design files
│   ├── bom.md                    # Bill of Materials
│   ├── schematic/                # Schematic files
│   └── pcb/                      # PCB layout files
├── firmware/                      # STM32 firmware (C, PlatformIO)
│   ├── platformio.ini            # Build configuration
│   ├── src/                      # Source files (pmu_*.c)
│   ├── include/                  # Headers (pmu_*.h)
│   ├── emulator/                 # Native emulator code
│   └── lib/                      # Libraries
├── configurator/                  # Python+Qt configuration software
│   ├── requirements.txt
│   ├── src/
│   │   ├── main.py              # Application entry point
│   │   ├── ui/                  # UI components
│   │   ├── models/              # Data models
│   │   ├── communication/       # Protocol handler
│   │   └── controllers/         # Device controller
│   └── tests/                   # Unit & integration tests
└── releases/                      # Release builds
```

## Configurator Software

### Quick Start

```bash
cd configurator
pip install -r requirements.txt
python src/main.py
```

### Key Features

- **30 Power Outputs** with full configuration
  - PWM frequency, soft-start, duty cycle
  - Current limits, retry on fault
  - Load shedding priority (0-10)
  - Pin merging for high current
- **20 Input Channels**
  - Digital inputs (active high/low, pull-up/down)
  - Analog inputs with scaling and filtering
  - CAN inputs from any ECU signal
- **4 H-Bridge Motor Outputs** for wipers, fans, actuators
- **Logic Engine**: 64 functions, 25+ operation types
- **PID Controllers** with anti-windup
- **LUA 5.4 Scripting** for custom logic
- **CAN Bus Integration**
  - DBC import/export
  - CAN message TX/RX configuration
  - BlinkMarine PKP keypad support
- **Real-time Monitoring**
  - Output Monitor (states, currents, faults)
  - Analog Monitor (live ADC values)
  - Digital Monitor (input states)
  - Variables Inspector (CAN signals)
- **Emulator Support**: Connect to firmware emulator for development
- **Dark/Light Themes** with multiple Qt styles
- **Configuration Save/Load** (.pmu30 binary format)

### Desktop Emulator

For development without hardware, use the firmware emulator:

```bash
# Build emulator
cd firmware
python -m platformio run -e pmu30_emulator

# Run emulator (Windows)
.pio/build/pmu30_emulator/program.exe
```

## Firmware

### Build Targets

| Target | Platform | Description |
|--------|----------|-------------|
| `pmu30` | STM32H7 | Production firmware for hardware |
| `pmu30_emulator` | Native (Windows/Linux) | Desktop emulator for development |

### Build Commands

```bash
cd firmware

# Build for hardware
python -m platformio run -e pmu30

# Build emulator
python -m platformio run -e pmu30_emulator
```

### ESP32-C3 Communication

The firmware communicates with the ESP32-C3 module via AT commands over UART3:
- **WiFi**: AP mode, STA mode, or dual AP+STA
- **Bluetooth**: BLE server with telemetry characteristics
- **Web Server**: HTTP and WebSocket for remote monitoring

See [Firmware Architecture](docs/firmware_architecture.md) for implementation details.

## Development Status

Project is in active development.

### Current Version: v0.2.0

| Component | Status |
|-----------|--------|
| Core Firmware | ✅ Complete |
| Channel System | ✅ Complete |
| Logic Engine | ✅ Complete |
| Protocol Handler | ✅ Complete |
| ESP32 Bridge | ✅ Implemented |
| WiFi (AT Commands) | ✅ Implemented |
| Bluetooth (AT Commands) | ✅ Implemented |
| Load Shedding | ✅ Implemented |
| Desktop Emulator | ✅ Functional |
| Configurator UI | ✅ Functional |
| Integration Tests | ✅ Added |

### Quick Links
- [Firmware Architecture](docs/firmware_architecture.md) - Complete firmware design
- [Emulator Guide](docs/testing/emulator-guide.md) - Desktop testing
- [Configuration Reference](docs/reference/configuration.md) - Binary config format

## Testing

### Unit Tests (Configurator)

```bash
cd configurator
python -m pytest tests/ -v
```

### Integration Tests

Requires running emulator:

```bash
# Terminal 1: Start emulator
cd firmware
.pio/build/pmu30_emulator/program.exe

# Terminal 2: Run integration tests
cd configurator
python -m pytest tests/integration/ -v
```

### Test Coverage

| Category | Tests |
|----------|-------|
| Channel Configuration | ✅ |
| Logic Functions | ✅ |
| Protocol Handler | ✅ |
| WiFi/Bluetooth Config | ✅ |
| Load Shedding Priority | ✅ |

## References

This project is inspired by industry-leading PDMs from various manufacturers, incorporating best practices in power distribution and motorsport electronics.

- MaxxECU PDM (reliability, integration)
- MoTec PDM32 (professional-grade features)
- Link ECU PDM Razor (wiper/blinker control)
- AIM PDM (professional telemetry)
- RaceCapture from Autosport Labs (Lua scripting, open-source inspiration)

## Owner & Development

**R2 m-sport** - Project Owner and Lead Development

This is a professional motorsport electronics development project by R2 m-sport.

## License

Proprietary - © 2025 R2 m-sport. All rights reserved.

This project and its documentation are the property of R2 m-sport. Unauthorized copying, distribution, or use is prohibited.

## Contact

For inquiries regarding this project, please contact R2 m-sport.
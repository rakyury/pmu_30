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
  - WiFi (Access Point mode)
  - Bluetooth Low Energy
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
- Individual channel protection:
  - Overcurrent protection
  - Overtemperature protection
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
- **CAN Keyboard Support**: Blinkmarine compatible
- **Data Logging**: 500Hz high-speed logging to 512MB internal memory
- **OTA Updates**: Over-the-air firmware updates
- **Web Interface**: Full monitoring and configuration via WiFi

## Documentation

### Quick Start
- [Quick Start Guide](docs/QUICKSTART.md) - Get running in 5 minutes

### Architecture
- [Unified Channel System](docs/architecture/unified-channel-system.md) - Channel abstraction layer
- [Logic Functions Framework](docs/architecture/logic-functions-framework.md) - 64 logic functions

### API Reference
- [Channel API](docs/api/channel-api.md) - Channel read/write operations
- [Logic Functions API](docs/api/logic-functions-reference.md) - Logic function programming
- [Channel Types](docs/api/channel-types.md) - All channel type specifications

### Guides
- [Getting Started with Channels](docs/guides/getting-started-channels.md) - Channel basics
- [Logic Functions Integration](docs/guides/logic-functions-integration.md) - Using logic functions

### Examples
- [Channel Examples](docs/examples/channel-examples.md) - Code examples for channels
- [Logic Function Examples](docs/examples/logic-function-examples.md) - Logic function examples

### Hardware
- [PCB Design Specification](docs/PCB_DESIGN_SPECIFICATION.md) - PCB engineering spec

## Project Structure

```
pmu_30/
├── docs/                           # Documentation
│   ├── architecture/              # System architecture docs
│   ├── api/                       # API reference docs
│   ├── guides/                    # How-to guides
│   ├── examples/                  # Code examples
│   ├── technical_specification.md # Hardware TZ
│   ├── reference_analysis.md      # Reference PDM analysis
│   └── PCB_DESIGN_SPECIFICATION.md # PCB engineering spec
├── hardware/                      # Hardware design files
│   ├── bom.md                    # Bill of Materials
│   ├── schematic/                # Schematic files
│   └── pcb/                      # PCB layout files
├── firmware/                      # STM32 firmware (C, PlatformIO)
│   ├── platformio.ini
│   ├── src/
│   ├── include/
│   └── lib/
└── configurator/                  # Python+Qt configuration software
    ├── requirements.txt
    ├── launch.py                 # UI launcher
    ├── src/
    │   ├── main.py              # Classic UI entry point
    │   ├── main_professional.py # Modern UI entry point
    │   └── ui/
    └── docs/
```

## Configurator Software

### Quick Start

**Option 1: Use Launcher (Recommended)**
```bash
cd configurator
python launch.py
```

Select your preferred interface:
1. **Modern Style** - Dock-based layout ⭐
2. **Classic Style** - Traditional tab-based interface

**Option 2: Direct Launch**

Modern Style:
```bash
cd configurator
python src/main_professional.py
```

Classic Style:
```bash
cd configurator
python src/main.py
```

### UI Styles Comparison

| Feature | Modern Style | Classic Style |
|---------|--------------|---------------|
| Layout | Dock widgets | Tabs |
| Monitoring | Always visible | Separate tab |
| Project tree | Hierarchical | By category |
| Grouping | Yes (folders) | No |
| Drag & Drop | Yes | No |
| Real-time panels | 3 (dockable) | 1 (fixed) |
| Screen space | Efficient | Standard |
| Learning curve | Medium | Easy |

### Key Features

**Both Styles:**
- 30 output channels configuration
- 20 input channels with multiple types
- 4 H-Bridge motor control
- Logic Engine (256 virtual channels, 16 operations)
- PID Controllers with anti-windup
- LUA 5.4 scripting engine
- CAN Bus configuration with DBC import/export
- Settings: CAN, Power, Safety, System
- Dark/Light themes
- Multiple Qt styles (Fluent, Windows11, Fusion, etc.)
- Configuration save/load (JSON)
- 28 unit tests ✅

**Modern Style Only:**
- Project tree with hierarchy
- Output Monitor (real-time)
- Analog Monitor (real-time)
- Variables Inspector (CAN + PMU status)
- Drag & drop panel layout
- Save/restore custom layouts

### Documentation

- [docs/UI_IMPROVEMENTS.md](configurator/docs/UI_IMPROVEMENTS.md) - UI development history
- [docs/QT_STYLES.md](configurator/docs/QT_STYLES.md) - Available Qt styles

## Development Status

Project is in active development. See [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) for current status.

### Quick Links
- [Roadmap](docs/ROADMAP.md) - Version releases
- [Changelog](docs/CHANGELOG.md) - Version history
- [Ecumaster Comparison](docs/ECUMASTER_COMPARISON.md) - Feature comparison
- [Test Plan](docs/REFACTORING_AND_TEST_PLAN.md) - Testing coverage

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
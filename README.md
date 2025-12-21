# PMU-30 - Automotive Power Distribution Module

Professional 30-channel Power Distribution Module for motorsport applications.

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

## Project Structure

```
pmu_30/
├── docs/                           # Documentation
│   ├── technical_specification.md # Hardware TZ
│   ├── reference_analysis.md      # Reference PDM analysis
│   ├── user_manual.md            # User documentation
│   └── api_reference.md          # Software API docs
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
    ├── src/
    └── ui/
```

## Development Status

Project is in active development. See [docs/project_plan.md](docs/project_plan.md) for current status.

## References

This project is inspired by industry-leading PDMs:
- ECUMaster PMU24 DL (logic system, data logging)
- ECUMaster Dual H-Bridge (motor control)
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
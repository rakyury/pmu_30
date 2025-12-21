# PMU-30 Firmware

**Owner:** R2 m-sport
**Target:** STM32H743VIT6 / STM32H753VIT6
**Framework:** STM32 HAL + FreeRTOS
**Language:** C (C11 standard)

---

## Overview

This directory contains the firmware for the PMU-30 Power Management Unit. The firmware is built using PlatformIO and runs on the STM32H7 microcontroller with FreeRTOS for real-time task management.

## Project Structure

```
firmware/
├── platformio.ini          # PlatformIO configuration
├── src/                    # Source files
│   ├── main.c              # Main application entry point
│   ├── pmu_config.c        # Configuration management
│   ├── pmu_profet.c        # PROFET 2 output driver
│   ├── pmu_hbridge.c       # H-Bridge motor control
│   ├── pmu_can.c           # CAN communication
│   ├── pmu_adc.c           # Analog input handling
│   ├── pmu_protection.c    # Protection systems
│   ├── pmu_logic.c         # Logic engine
│   └── pmu_logging.c       # Data logging
├── include/                # Header files
│   ├── main.h
│   ├── pmu_config.h
│   ├── pmu_profet.h
│   ├── pmu_hbridge.h
│   ├── pmu_can.h
│   ├── pmu_adc.h
│   ├── pmu_protection.h
│   ├── pmu_logic.h
│   └── pmu_logging.h
├── lib/                    # External libraries
│   ├── FreeRTOS/           # FreeRTOS kernel
│   ├── Lua/                # Lua 5.4 embedded
│   └── DBC_Parser/         # CAN DBC file parser
└── test/                   # Unit tests

```

## Key Features

### Real-Time Architecture
- **FreeRTOS**: Multi-task real-time operating system
- **Control Task**: 1 kHz deterministic control loop
- **Protection Task**: Fast fault detection and response
- **CAN Task**: CAN bus communication handling
- **Logging Task**: 500 Hz data logging
- **UI Task**: Status LED and UI updates

### Hardware Abstraction
- **PROFET 2 Driver**: 30 intelligent high-side switches
- **H-Bridge Driver**: 4 dual H-bridge motor controllers
- **CAN Interface**: 2x CAN FD + 2x CAN 2.0 support
- **ADC System**: 20 universal analog/digital inputs
- **Protection**: Overcurrent, overtemperature, short circuit

### Software Features
- **Logic Engine**: 100 virtual functions, 250 operations @ 500 Hz
- **Lua Scripting**: Embedded Lua 5.4 for custom logic
- **DBC Support**: CAN database import/export
- **Data Logging**: 500 Hz logging to 512 MB external flash
- **OTA Updates**: Over-the-air firmware updates via WiFi

## Building the Firmware

### Prerequisites

1. **PlatformIO**: Install PlatformIO IDE or CLI
   ```bash
   pip install platformio
   ```

2. **STM32 Tools**: Install ST-Link drivers and tools

### Build Commands

**Debug Build:**
```bash
cd firmware
pio run -e pmu30_debug
```

**Release Build:**
```bash
pio run -e pmu30_release
```

**Upload to Device:**
```bash
pio run -e pmu30_debug -t upload
```

**Clean Build:**
```bash
pio run -t clean
```

### Build Environments

- `pmu30_debug`: Debug build with optimization for debugging (-Og, -g3)
- `pmu30_release`: Release build with full optimization (-O2, LTO)
- `pmu30_test`: Unit testing environment (native platform)

## Flashing

### Using ST-Link

```bash
pio run -e pmu30_debug -t upload
```

### Using USB DFU

```bash
# Enter DFU mode, then:
pio run -e pmu30_debug -t upload --upload-port /dev/ttyUSB0
```

## Debugging

### Serial Monitor

```bash
pio device monitor -e pmu30_debug
```

### GDB Debugging

```bash
pio debug -e pmu30_debug
```

## Testing

### Run Unit Tests

```bash
pio test -e pmu30_test
```

### Run Tests on Hardware

```bash
pio test -e pmu30_debug
```

## Configuration

The firmware can be configured via:

1. **platformio.ini**: Build-time configuration
2. **pmu_config.h**: System constants and defaults
3. **Configuration Tool**: Python+Qt configurator (see ../configurator/)

## Memory Map

### Flash (2 MB)
- 0x08000000: Bootloader (128 KB)
- 0x08020000: Application firmware (1.5 MB)
- 0x081E0000: Configuration storage (64 KB)
- 0x081F0000: Backup configuration (64 KB)

### RAM (1 MB)
- DTCM RAM (128 KB): Critical data, ISR stacks
- AXI SRAM (512 KB): Application data, FreeRTOS heap
- SRAM1 (128 KB): DMA buffers
- SRAM2 (128 KB): Backup SRAM
- SRAM3 (32 KB): Ethernet buffers (future)
- SRAM4 (64 KB): Lua VM heap

### External Flash (512 MB)
- Data logging storage
- Lua scripts storage
- DBC file storage
- Firmware update staging

## Task Architecture

| Task | Priority | Stack | Frequency | Function |
|------|----------|-------|-----------|----------|
| Control | Highest | 512 | 1000 Hz | Main control loop |
| Protection | High | 384 | 1000 Hz | Fault detection |
| CAN | Medium | 512 | Event | CAN communication |
| Logging | Low | 512 | 500 Hz | Data logging |
| UI | Lowest | 256 | 20 Hz | Status LEDs |

## Pin Assignment

See [../docs/technical_specification.md](../docs/technical_specification.md) for complete pin assignment details.

## Contributing

This is a proprietary project owned by R2 m-sport. Internal development only.

## License

Proprietary - © 2025 R2 m-sport. All rights reserved.

---

**For more information, see the main project README and technical documentation.**

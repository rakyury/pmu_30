# PMU-30 Development Plan

**Version:** 1.0
**Date:** December 2024
**Status:** Active Development

---

## Current State Summary

### Completed ✅
- **Documentation**: Full documentation suite (35+ documents)
- **Configurator UI**: Modern + Classic interfaces, basic functionality
- **Architecture**: Unified Channel System, Logic Functions Framework
- **PCB Specification**: Complete engineering spec

### In Progress 🔄
- Firmware core implementation
- Configurator-device communication

### Not Started ⬜
- Hardware prototype
- Production firmware
- Full system integration

---

## Phase 1: Firmware Core (4-6 weeks)

### 1.1 HAL & Drivers
| Task | Priority | Status |
|------|----------|--------|
| STM32H7 HAL configuration | P0 | ⬜ |
| GPIO driver (outputs, inputs) | P0 | ⬜ |
| ADC driver with DMA | P0 | ⬜ |
| PWM/Timer driver | P0 | ⬜ |
| SPI driver (PROFET, sensors) | P0 | ⬜ |
| CAN FD driver | P0 | ⬜ |
| CAN 2.0 driver | P0 | ⬜ |
| UART driver (debug) | P1 | ⬜ |
| USB CDC driver | P1 | ⬜ |
| Flash driver (config storage) | P1 | ⬜ |
| RTC driver | P2 | ⬜ |
| I2C driver (IMU, temp sensors) | P2 | ⬜ |

### 1.2 PROFET Driver
| Task | Priority | Status |
|------|----------|--------|
| Basic on/off control | P0 | ⬜ |
| PWM duty cycle control | P0 | ⬜ |
| Current sensing (IS pin) | P0 | ⬜ |
| Fault detection (DEN pin) | P0 | ⬜ |
| Soft-start implementation | P1 | ⬜ |
| Overcurrent protection | P0 | ⬜ |
| Retry logic | P1 | ⬜ |
| Temperature compensation | P2 | ⬜ |

### 1.3 H-Bridge Driver
| Task | Priority | Status |
|------|----------|--------|
| Forward/Reverse control | P0 | ⬜ |
| PWM speed control | P0 | ⬜ |
| Dead-time management | P0 | ⬜ |
| Brake function | P1 | ⬜ |
| Coast function | P1 | ⬜ |
| Current limiting | P1 | ⬜ |

### 1.4 Channel System
| Task | Priority | Status |
|------|----------|--------|
| Channel registry | P0 | ⬜ |
| Channel read/write API | P0 | ⬜ |
| Channel flags management | P0 | ⬜ |
| System channels | P1 | ⬜ |
| Channel persistence | P2 | ⬜ |

**Deliverables:**
- [ ] All hardware peripherals functional
- [ ] Basic output control working
- [ ] ADC sampling at 1kHz
- [ ] Unit tests passing

---

## Phase 2: Logic Engine (3-4 weeks)

### 2.1 Core Logic System
| Task | Priority | Status |
|------|----------|--------|
| Function registry | P0 | ⬜ |
| Execution scheduler (500Hz) | P0 | ⬜ |
| Input collection | P0 | ⬜ |
| Output distribution | P0 | ⬜ |
| State management | P1 | ⬜ |

### 2.2 Arithmetic Functions
| Function | Priority | Status |
|----------|----------|--------|
| ADD, SUBTRACT | P0 | ⬜ |
| MULTIPLY, DIVIDE | P0 | ⬜ |
| MIN, MAX, AVERAGE | P1 | ⬜ |
| NEGATE, ABS | P2 | ⬜ |

### 2.3 Comparison Functions
| Function | Priority | Status |
|----------|----------|--------|
| GREATER, LESS | P0 | ⬜ |
| EQUAL, NOT_EQUAL | P0 | ⬜ |
| IN_RANGE | P1 | ⬜ |

### 2.4 Boolean Functions
| Function | Priority | Status |
|----------|----------|--------|
| AND, OR, NOT | P0 | ⬜ |
| XOR, NAND, NOR | P1 | ⬜ |

### 2.5 State Functions
| Function | Priority | Status |
|----------|----------|--------|
| TOGGLE | P0 | ⬜ |
| LATCH_SR | P0 | ⬜ |
| PULSE | P1 | ⬜ |
| DELAY_ON, DELAY_OFF | P1 | ⬜ |
| FLASHER | P1 | ⬜ |
| TIMER, COUNTER | P2 | ⬜ |

### 2.6 Data Functions
| Function | Priority | Status |
|----------|----------|--------|
| TABLE_1D | P0 | ⬜ |
| TABLE_2D | P1 | ⬜ |
| MOVING_AVERAGE | P1 | ⬜ |
| HYSTERESIS | P0 | ⬜ |
| RATE_LIMIT | P2 | ⬜ |

### 2.7 Control Functions
| Function | Priority | Status |
|----------|----------|--------|
| PID controller | P1 | ⬜ |
| PI controller | P2 | ⬜ |
| PWM_DUTY mapping | P1 | ⬜ |
| SOFT_START | P1 | ⬜ |

**Deliverables:**
- [ ] 64 logic functions implemented
- [ ] 500Hz execution verified
- [ ] Function chaining working
- [ ] All unit tests passing

---

## Phase 3: CAN Integration (2-3 weeks)

### 3.1 CAN Core
| Task | Priority | Status |
|------|----------|--------|
| CAN FD initialization | P0 | ⬜ |
| CAN 2.0 initialization | P0 | ⬜ |
| Hardware filtering | P0 | ⬜ |
| TX queue management | P0 | ⬜ |
| RX callback handling | P0 | ⬜ |

### 3.2 Signal Processing
| Task | Priority | Status |
|------|----------|--------|
| Signal extraction (RX) | P0 | ⬜ |
| Signal packing (TX) | P0 | ⬜ |
| Endian conversion | P0 | ⬜ |
| Factor/offset scaling | P0 | ⬜ |
| Timeout detection | P1 | ⬜ |

### 3.3 DBC Support
| Task | Priority | Status |
|------|----------|--------|
| DBC parser (configurator) | P1 | ⬜ |
| Signal mapping export | P1 | ⬜ |
| Signal mapping import | P1 | ⬜ |

**Deliverables:**
- [ ] 4 CAN buses operational
- [ ] Signal extraction working
- [ ] Periodic TX working
- [ ] Timeout detection working

---

## Phase 4: Configuration System (2-3 weeks)

### 4.1 JSON Configuration
| Task | Priority | Status |
|------|----------|--------|
| JSON parser (cJSON) | P0 | ⬜ |
| Config schema validation | P0 | ⬜ |
| Config apply functions | P0 | ⬜ |
| Default configuration | P0 | ⬜ |

### 4.2 Storage
| Task | Priority | Status |
|------|----------|--------|
| Flash sector management | P0 | ⬜ |
| Config save to flash | P0 | ⬜ |
| Config load from flash | P0 | ⬜ |
| CRC verification | P0 | ⬜ |
| Backup/restore | P2 | ⬜ |

### 4.3 Communication Protocol
| Task | Priority | Status |
|------|----------|--------|
| USB protocol | P0 | ⬜ |
| Config upload chunked | P0 | ⬜ |
| Config download | P0 | ⬜ |
| Live value monitoring | P1 | ⬜ |
| Command interface | P1 | ⬜ |

**Deliverables:**
- [ ] Configuration save/load working
- [ ] USB configuration upload
- [ ] Configurator connection established

---

## Phase 5: Configurator Enhancement (3-4 weeks)

### 5.1 Device Communication
| Task | Priority | Status |
|------|----------|--------|
| USB serial connection | P0 | ⬜ |
| Protocol implementation | P0 | ⬜ |
| Config upload/download | P0 | ⬜ |
| Live monitoring | P1 | ⬜ |
| Firmware update | P2 | ⬜ |

### 5.2 UI Improvements
| Task | Priority | Status |
|------|----------|--------|
| Connection status indicator | P0 | ⬜ |
| Real-time value display | P1 | ⬜ |
| Output control panel | P1 | ⬜ |
| Diagnostics view | P1 | ⬜ |
| Fault log viewer | P2 | ⬜ |

### 5.3 Advanced Features
| Task | Priority | Status |
|------|----------|--------|
| DBC import wizard | P1 | ⬜ |
| Logic function builder | P2 | ⬜ |
| Simulation mode | P2 | ⬜ |
| Configuration comparison | P3 | ⬜ |

**Deliverables:**
- [ ] Full device communication
- [ ] Real-time monitoring
- [ ] Configuration management

---

## Phase 6: Protection & Safety (2-3 weeks)

### 6.1 Output Protection
| Task | Priority | Status |
|------|----------|--------|
| Overcurrent detection | P0 | ⬜ |
| Short circuit protection | P0 | ⬜ |
| Open load detection | P1 | ⬜ |
| Thermal derating | P1 | ⬜ |

### 6.2 System Protection
| Task | Priority | Status |
|------|----------|--------|
| Undervoltage protection | P0 | ⬜ |
| Overvoltage protection | P0 | ⬜ |
| Total current limiting | P1 | ⬜ |
| Watchdog implementation | P0 | ⬜ |

### 6.3 Safety Features
| Task | Priority | Status |
|------|----------|--------|
| Safe state function | P0 | ⬜ |
| Crash detection (IMU) | P2 | ⬜ |
| Fault logging | P1 | ⬜ |
| Recovery procedures | P1 | ⬜ |

**Deliverables:**
- [ ] All protection active
- [ ] Safe state verified
- [ ] Fault logging working

---

## Phase 7: Additional Features (4-6 weeks)

### 7.1 Wireless Communication
| Task | Priority | Status |
|------|----------|--------|
| WiFi AP mode | P2 | ⬜ |
| Web interface | P2 | ⬜ |
| BLE connectivity | P3 | ⬜ |
| OTA updates | P3 | ⬜ |

### 7.2 Data Logging
| Task | Priority | Status |
|------|----------|--------|
| Log file system | P2 | ⬜ |
| Channel logging | P2 | ⬜ |
| Triggered logging | P2 | ⬜ |
| Log export | P2 | ⬜ |

### 7.3 Advanced Control
| Task | Priority | Status |
|------|----------|--------|
| Wiper controller | P2 | ⬜ |
| Blinker logic | P2 | ⬜ |
| Cruise control | P3 | ⬜ |
| Boost control | P3 | ⬜ |

### 7.4 Lua Scripting
| Task | Priority | Status |
|------|----------|--------|
| Lua 5.4 integration | P3 | ⬜ |
| API bindings | P3 | ⬜ |
| Script storage | P3 | ⬜ |
| Debug interface | P3 | ⬜ |

---

## Phase 8: Hardware Production (Parallel)

### 8.1 PCB Design
| Task | Priority | Status |
|------|----------|--------|
| Schematic capture | P0 | ⬜ |
| Component selection | P0 | ⬜ |
| PCB layout | P0 | ⬜ |
| Design review | P0 | ⬜ |
| Gerber generation | P0 | ⬜ |

### 8.2 Prototype
| Task | Priority | Status |
|------|----------|--------|
| PCB fabrication | P0 | ⬜ |
| Component procurement | P0 | ⬜ |
| Assembly (PCBA) | P0 | ⬜ |
| Initial bring-up | P0 | ⬜ |
| Basic functionality test | P0 | ⬜ |

### 8.3 Enclosure
| Task | Priority | Status |
|------|----------|--------|
| CNC enclosure design | P1 | ⬜ |
| Thermal analysis | P1 | ⬜ |
| Prototype machining | P1 | ⬜ |
| Fit testing | P1 | ⬜ |

---

## Phase 9: Testing & Validation (3-4 weeks)

### 9.1 Unit Testing
| Task | Priority | Status |
|------|----------|--------|
| Channel system tests | P0 | ⬜ |
| Logic function tests | P0 | ⬜ |
| Driver tests | P0 | ⬜ |
| Protection tests | P0 | ⬜ |

### 9.2 Integration Testing
| Task | Priority | Status |
|------|----------|--------|
| End-to-end data flow | P0 | ⬜ |
| CAN communication | P0 | ⬜ |
| Configuration system | P0 | ⬜ |
| Performance benchmarks | P1 | ⬜ |

### 9.3 System Testing
| Task | Priority | Status |
|------|----------|--------|
| Full load testing | P0 | ⬜ |
| Thermal testing | P0 | ⬜ |
| EMC pre-compliance | P1 | ⬜ |
| Environmental testing | P1 | ⬜ |
| Endurance testing | P1 | ⬜ |

---

## Timeline Overview

```
Month 1-2:   Phase 1 (Firmware Core)
Month 2-3:   Phase 2 (Logic Engine)
Month 3:     Phase 3 (CAN Integration)
Month 3-4:   Phase 4 (Configuration)
Month 4-5:   Phase 5 (Configurator)
Month 5-6:   Phase 6 (Protection)
Month 6-8:   Phase 7 (Additional Features)
Month 4-6:   Phase 8 (Hardware - parallel)
Month 7-8:   Phase 9 (Testing)
```

**Total Estimated Time: 6-8 months to v1.0**

---

## Milestones

| Milestone | Target | Description |
|-----------|--------|-------------|
| M1 | Month 2 | Firmware boots, basic I/O |
| M2 | Month 3 | Logic functions working |
| M3 | Month 4 | CAN + Config working |
| M4 | Month 5 | Configurator connected |
| M5 | Month 6 | Hardware prototype |
| M6 | Month 7 | Full integration |
| M7 | Month 8 | v1.0 Release |

---

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Component shortage | Medium | High | Early procurement |
| PROFET driver issues | Low | High | Dev board testing first |
| Performance targets | Medium | Medium | Early profiling |
| EMC compliance | Medium | Medium | Design review |
| Schedule slip | Medium | Medium | Buffer time |

---

## Resource Requirements

### Hardware
- STM32H743 Nucleo board
- PROFET 2 evaluation board
- BTN8982 evaluation board
- CAN FD transceiver board
- Load resistors & test loads
- Oscilloscope, logic analyzer
- Power supply (0-30V, 50A)

### Software
- STM32CubeIDE
- PlatformIO
- Python 3.8+
- Qt 6.x
- Git

---

## Next Immediate Steps

1. **Set up STM32H743 Nucleo development environment**
2. **Create basic HAL configuration (CubeMX)**
3. **Implement GPIO driver for LED test**
4. **Test PROFET control on eval board**
5. **Begin channel system implementation**

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 2024 | Initial plan |

---

**Owner:** R2 m-sport
**Last Updated:** December 2024

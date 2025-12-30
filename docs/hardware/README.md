# PMU-30 Hardware Documentation

**Version:** 3.0 | **Last Updated:** December 2025

Hardware design documentation for the PMU-30 Power Management Unit.

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [Technical Specification](technical_specification.md) | Complete hardware requirements, power stages, I/O, protection |
| [PCB Design Specification](PCB_DESIGN_SPECIFICATION.md) | PCB layout, stack-up, components, thermal, routing guide |
| [BOM Specification](BOM_SPECIFICATION.md) | Bill of materials, part numbers, alternatives |
| [POC PCB Requirements](POC_PCB_REQUIREMENTS.md) | Proof of concept board (10-channel scaled version) |

---

## Hardware Overview

| Feature | Specification |
|---------|---------------|
| **Power Outputs** | 30 × PROFET high-side, 40A each |
| **H-Bridges** | 4 × bidirectional, 30A each |
| **Analog Inputs** | 20 × 0-5V, 12-bit ADC |
| **Digital Inputs** | 20 × configurable pull-up/down |
| **CAN Bus** | 2 × CAN FD + 2 × CAN 2.0 |
| **Connectivity** | USB-C, WiFi, Bluetooth, LIN |
| **Operating Voltage** | 6-22V DC |
| **Max Total Current** | 200A continuous |
| **PCB Size** | 150mm × 120mm, 8-layer |
| **Enclosure** | IP67 aluminum, 156×126×40mm |

---

## Quick Reference

### Channel ID Ranges

| ID Range | Type | Hardware |
|----------|------|----------|
| 0-19 | Digital Inputs | 20 × dedicated pins |
| 50-69 | Analog Inputs | 20 × 0-5V ADC |
| 100-129 | Power Outputs | 30 × PROFET (15 ICs) |
| 150-157 | H-Bridge | 4 × dual (8 half-bridges) |

### Key Components

| Function | Part Number |
|----------|-------------|
| MCU | STM32H743VIT6 (480MHz Cortex-M7) |
| Power Switch | BTS7012-2EPA (40A × 2ch) |
| H-Bridge | BTN8982TA (30A) |
| CAN FD | TJA1463 |
| WiFi/BT | ESP32-C3-MINI-1-N4 |
| Flash | W25Q512JVEIQ (64MB) |
| IMU | LSM6DSO32X |
| GPS | MAX-M10S or NEO-M9N |

### Connector Pinout Summary

| Connector | Pins | Function |
|-----------|------|----------|
| Main A (34-pin) | 1-30 | Power outputs 1-30 |
| | 31-34 | H-Bridge 1-2 |
| Main B (26-pin) | 1-20 | Analog inputs 1-20 |
| | 21-26 | CAN1/CAN2, 5V sensor |
| Main C (26-pin) | 1-20 | Digital inputs 1-20 |
| | 21-26 | LIN, USB, reserved |
| Power (+) | Radlock | 200A main battery |
| Ground (-) | M8 stud | Chassis ground |

---

## Document Relationships

```
┌─────────────────────────────────────────────────────────┐
│              technical_specification.md                  │
│        (System requirements, electrical specs)           │
└───────────────────────────┬─────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            v               v               v
┌───────────────────┐ ┌───────────────┐ ┌─────────────────┐
│ PCB_DESIGN_SPEC   │ │ BOM_SPEC      │ │ POC_PCB_REQ     │
│ (Layout, routing) │ │ (Parts list)  │ │ (10ch prototype)│
└───────────────────┘ └───────────────┘ └─────────────────┘
```

---

## See Also

- [Channels Reference](../reference/channels.md) - Software channel system
- [Configuration Reference](../reference/configuration.md) - JSON configuration
- [Protocol Reference](../reference/protocol.md) - Communication protocol

---

**Copyright © 2025 R2 m-sport. All rights reserved.**

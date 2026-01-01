# PMU-30 Documentation

**Version:** 4.0 | **Last Updated:** January 2026

---

## Single Source of Truth

**This `docs/` folder is the authoritative source for all PMU-30 project documentation.**

All technical decisions, specifications, and architecture information should be documented here. If there is a discrepancy between code comments and documentation, the documentation takes precedence.

---

## Quick Links

| Getting Started | Reference | Architecture |
|-----------------|-----------|--------------|
| [Quick Start](QUICKSTART.md) | [Channels](reference/channels.md) | [Firmware Architecture](firmware_architecture.md) |
| [Configuration](reference/configuration.md) | [Logic Functions](reference/logic-functions.md) | [Binary Config Architecture](BINARY_CONFIG_ARCHITECTURE.md) |
| [Examples](examples/real-world-scenarios.md) | [Protocol](reference/protocol.md) | [Shared Library](SHARED_PROTOCOL_LIBRARY.md) |

---

## Documentation Structure

```
docs/
├── README.md                        ← You are here (Single Source of Truth)
├── QUICKSTART.md                    ← 5-minute setup guide
├── ROADMAP.md                       ← Future plans
│
├── BINARY_CONFIG_ARCHITECTURE.md    ← Binary config system
├── SHARED_PROTOCOL_LIBRARY.md       ← Shared library design
├── firmware_architecture.md         ← Firmware internals
│
├── reference/                       ← SPECIFICATIONS
│   ├── channels.md                  ← Channel ID ranges and types
│   ├── configuration.md             ← Binary config format (.pmu30)
│   ├── logic-functions.md           ← Logic operations
│   └── protocol.md                  ← Communication protocol
│
├── configurator/                    ← UI DOCUMENTATION
│   ├── README.md
│   └── ...
│
├── examples/                        ← PRACTICAL EXAMPLES
│   ├── channel-examples.md
│   └── real-world-scenarios.md
│
├── hardware/                        ← HARDWARE SPECS
│   ├── technical_specification.md
│   └── PCB_DESIGN_SPECIFICATION.md
│
└── testing/                         ← TEST GUIDES
    ├── emulator-guide.md
    └── integration-testing-guide.md
```

---

## Architecture Overview

### Binary Configuration (No JSON)

PMU-30 uses a unified binary format for all configuration:

```
┌─────────────────────┐
│   Configurator      │ Creates/edits configuration
│   (Python/Qt)       │
└──────────┬──────────┘
           │
           │ .pmu30 binary file
           ▼
┌─────────────────────┐
│   Binary Config     │ One format for entire system
│   (.pmu30 file)     │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│ Firmware│ │Configur-│
│ (C)     │ │ator     │
└─────────┘ └─────────┘
```

**Key principles:**
- No JSON anywhere in the system
- One binary format for firmware and configurator
- Shared library for C and Python
- CRC-32 verification

See [Binary Config Architecture](BINARY_CONFIG_ARCHITECTURE.md) for details.

### Shared Library

```
shared/
├── channel_config.h/c      # Binary structures (C)
├── channel_executor.h/c    # Channel processing (C)
├── engine/                 # Logic Engine (pure C)
└── python/
    └── channel_config.py   # Python port
```

See [Shared Library](SHARED_PROTOCOL_LIBRARY.md) for details.

---

## Hardware Specifications

| Feature | Specification |
|---------|---------------|
| **Power Outputs** | 30 × PROFET high-side, 40A each |
| **H-Bridges** | 4 × bidirectional, 30A each |
| **Analog Inputs** | 20 × 0-5V, 12-bit resolution |
| **Digital Inputs** | 20 × configurable pull-up/down |
| **CAN Bus** | 2 × CAN FD + 2 × CAN 2.0 |
| **Connectivity** | USB-C, WiFi, Bluetooth, LIN |
| **Operating Voltage** | 6-22V DC |
| **Max Total Current** | 200A |

---

## Channel System

| ID Range | Type | Description |
|----------|------|-------------|
| 0-99 | Physical Inputs | Digital and analog inputs |
| 100-199 | Physical Outputs | Power outputs, H-bridges |
| 200-999 | Virtual Channels | Logic, Math, Timers, PID |
| 1000-1023 | System Channels | Battery, temperature, status |

See [Channels Reference](reference/channels.md) for details.

---

## Configuration Format

Binary format (`.pmu30` extension):

```
┌────────────────────────────────┐
│  File Header (32 bytes)        │
│  - Magic: 0x43464733           │
│  - CRC-32 checksum             │
│  - Channel count               │
├────────────────────────────────┤
│  Channel 0                     │
│  ├─ Header (14 bytes)          │
│  ├─ Name (0-31 bytes)          │
│  └─ Config (type-specific)     │
├────────────────────────────────┤
│  Channel 1...N                 │
└────────────────────────────────┘
```

See [Configuration Reference](reference/configuration.md) for full specification.

---

## Reference Documents

### Architecture

| Document | Description |
|----------|-------------|
| [firmware_architecture.md](firmware_architecture.md) | Firmware internals, HAL, RTOS |
| [BINARY_CONFIG_ARCHITECTURE.md](BINARY_CONFIG_ARCHITECTURE.md) | Binary config system |
| [SHARED_PROTOCOL_LIBRARY.md](SHARED_PROTOCOL_LIBRARY.md) | Shared library design |

### Specifications

| Document | Description |
|----------|-------------|
| [channels.md](reference/channels.md) | Channel IDs, types, API |
| [configuration.md](reference/configuration.md) | Binary config format |
| [logic-functions.md](reference/logic-functions.md) | Logic operations |
| [protocol.md](reference/protocol.md) | Communication protocol |

### Hardware

| Document | Description |
|----------|-------------|
| [technical_specification.md](hardware/technical_specification.md) | Electrical specs |
| [PCB_DESIGN_SPECIFICATION.md](hardware/PCB_DESIGN_SPECIFICATION.md) | PCB design |

### Testing

| Document | Description |
|----------|-------------|
| [emulator-guide.md](testing/emulator-guide.md) | Emulator usage |
| [integration-testing-guide.md](testing/integration-testing-guide.md) | Integration tests |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 4.0 | January 2026 | Binary-only configuration, shared library |
| 3.0 | December 2025 | JSON v3.0 format (deprecated) |
| 2.0 | November 2025 | Two-level CAN architecture |
| 1.0 | October 2025 | Initial release |

---

**Copyright 2026 R2 m-sport. All rights reserved.**

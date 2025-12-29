# PMU-30 Documentation

**Version:** 3.0 | **Last Updated:** December 2025

Welcome to PMU-30 documentation - a professional power management unit for motorsport and automotive applications.

---

## Quick Links

| Getting Started | Reference | Tools |
|-----------------|-----------|-------|
| [Quick Start](QUICKSTART.md) | [Channels](reference/channels.md) | [Configurator UI](configurator/README.md) |
| [First Configuration](guides/getting-started.md) | [Logic Functions](reference/logic-functions.md) | [CAN Monitor](configurator/can-monitor.md) |
| [Examples](examples/scenarios.md) | [Configuration](reference/configuration.md) | [Output Monitor](configurator/output-monitor.md) |
| | [Protocol](reference/protocol.md) | |

---

## Documentation Structure

```
docs/
├── README.md              ← You are here
├── QUICKSTART.md          ← 5-minute setup guide
├── CHANGELOG.md           ← Release history
├── ROADMAP.md             ← Future plans
│
├── reference/             ← SINGLE SOURCE OF TRUTH
│   ├── channels.md        ← Complete channel reference
│   ├── logic-functions.md ← All logic operations
│   ├── configuration.md   ← JSON schema & config
│   └── protocol.md        ← Communication protocol
│
├── guides/                ← HOW-TO TUTORIALS
│   ├── getting-started.md
│   └── ...
│
├── configurator/          ← UI DOCUMENTATION
│   ├── README.md
│   ├── analog-inputs.md
│   ├── digital-inputs.md
│   ├── power-outputs.md
│   └── monitors/
│
├── examples/              ← PRACTICAL EXAMPLES
│   ├── channel-examples.md
│   ├── logic-examples.md
│   └── scenarios.md
│
├── hardware/              ← HARDWARE SPECS
│   ├── README.md
│   ├── technical_specification.md
│   └── PCB_DESIGN_SPECIFICATION.md
│
└── firmware_architecture.md ← FIRMWARE ARCHITECTURE
```

---

## Hardware Overview

| Feature | Specification |
|---------|---------------|
| **Power Outputs** | 30 × PROFET high-side, 40A each |
| **H-Bridges** | 4 × bidirectional, 30A each |
| **Analog Inputs** | 20 × 0-5V, 10-bit resolution |
| **Digital Inputs** | 20 × configurable pull-up/down |
| **CAN Bus** | 2 × CAN FD + 2 × CAN 2.0 |
| **Connectivity** | USB-C, WiFi, Bluetooth, LIN |
| **Operating Voltage** | 6-22V DC |
| **Max Total Current** | 200A |

---

## Channel System

PMU-30 uses a unified channel abstraction for all I/O:

| ID Range | Type | Description |
|----------|------|-------------|
| 0-49 | Digital Inputs | Physical switch/button inputs |
| 50-99 | Analog Inputs | 0-5V sensor inputs |
| 100-129 | Power Outputs | PROFET outputs |
| 150-157 | H-Bridge | Motor control |
| 200-999 | Virtual | Logic, Math, Timers, PID |
| 1000-1023 | System | Battery, temp, status |
| 1100-1279 | Telemetry | Per-output monitoring |

→ See [Channels Reference](reference/channels.md) for details.

---

## Configuration Format (v3.0)

PMU-30 uses JSON configuration:

```json
{
  "version": "3.0",
  "device_name": "PMU-30",
  "channels": [
    {
      "channel_id": 100,
      "channel_type": "power_output",
      "channel_name": "Headlights",
      "output_pins": [0, 1],
      "source_channel_id": 0,
      "current_limit": 15000
    }
  ],
  "can_messages": [
    {
      "message_id": 1792,
      "can_bus": 1,
      "cycle_time_ms": 100,
      "signals": [...]
    }
  ]
}
```

→ See [Configuration Reference](reference/configuration.md) for full schema.

---

## Reference Documents

### Core Reference (Single Source of Truth)

| Document | Description |
|----------|-------------|
| [channels.md](reference/channels.md) | Channel IDs, types, C API, JSON config |
| [logic-functions.md](reference/logic-functions.md) | Math, logic, timers, filters, PID |
| [configuration.md](reference/configuration.md) | Complete JSON schema |
| [protocol.md](reference/protocol.md) | Serial/WiFi protocol |
| [firmware_architecture.md](firmware_architecture.md) | Firmware architecture, HAL, RTOS, boot sequence |

### Configurator UI

| Document | Description |
|----------|-------------|
| [README.md](configurator/README.md) | UI overview |
| [analog-inputs.md](configurator/analog-inputs.md) | Analog input configuration |
| [digital-inputs.md](configurator/digital-inputs.md) | Digital input configuration |
| [power-outputs.md](configurator/power-outputs.md) | Output configuration |

### Examples

| Document | Description |
|----------|-------------|
| [channel-examples.md](examples/channel-examples.md) | Channel code examples |
| [logic-examples.md](examples/logic-function-examples.md) | Logic function examples |
| [scenarios.md](examples/real-world-scenarios.md) | Complete configurations |

---

## Comparison with Competitors

See [ECUMASTER_COMPARISON.md](ECUMASTER_COMPARISON.md) for detailed feature comparison.

### Key Advantages

- **More Outputs**: 30×40A vs 16×25A
- **H-Bridge**: 4 motor outputs (unique)
- **CAN FD**: Up to 5 Mbps
- **WiFi/Bluetooth**: Wireless connectivity
- **Lua Scripting**: Custom programmable logic
- **PWM Range**: 1Hz-20kHz vs 4-400Hz

---

## Support

- [Troubleshooting Guide](operations/troubleshooting-guide.md)
- [GitHub Issues](https://github.com/...)

---

**Copyright © 2025 R2 m-sport. All rights reserved.**

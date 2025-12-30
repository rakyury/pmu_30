# PMU-30 Desktop Suite v0.2.1

Power Management Unit Configuration and Emulation Suite for desktop development and testing.

## Installation

**IMPORTANT:** This release requires the full PMU-30 project structure.

Extract the ZIP contents to the `releases/` folder of your PMU-30 project:

```
pmu_30/
  ├── releases/           <-- Extract here
  │     ├── PMU30_Desktop_Suite.bat
  │     ├── pmu30_emulator.exe
  │     └── README.md
  ├── configurator/
  │     └── src/
  │           └── main.py
  └── firmware/
```

## Quick Start

### Option 1: Batch Launcher (Recommended)
1. Extract ZIP to `pmu_30/releases/` folder
2. Double-click `PMU30_Desktop_Suite.bat`
3. Both emulator and configurator will start automatically
4. Configurator will auto-connect to the emulator

### Option 2: Manual Launch
1. Run `pmu30_emulator.exe` first
2. Wait for "Server started on port 9876" message
3. Run configurator with: `python configurator/src/main.py --connect`

## Components

### Emulator (`pmu30_emulator.exe`)
Hardware emulator for PMU-30 firmware development. Simulates:
- 20 ADC inputs (analog/digital/frequency)
- 30 PROFET power outputs
- 4 H-Bridge motor outputs
- 4 CAN buses
- Full logic functions engine

**Interfaces:**
- TCP Protocol: `localhost:9876` (for configurator)
- Web UI: `http://localhost:8080` (browser-based control)

**Console Commands:**
```
adc <ch> <value>    - Set ADC raw value (0-1023)
adcv <ch> <voltage> - Set ADC voltage (0.0-3.3V)
volt <mV>           - Set battery voltage
temp <C>            - Set temperature
ui                  - Show channel state grid
help                - Show all commands
quit                - Exit emulator
```

### Configurator
PyQt6-based configuration tool for:
- Channel configuration (inputs, outputs, logic, timers)
- Real-time telemetry monitoring
- Data logging and graphing
- CAN message configuration

**Command Line Options:**
```
python main.py                    # Normal startup with dialog
python main.py --connect          # Auto-connect to localhost:9876
python main.py --connect host:port # Connect to specific address
python main.py -f config.json     # Load configuration file
python main.py --no-startup       # Skip startup dialog
```

## Architecture

```
┌─────────────────────────────────────────────┐
│           PMU-30 Desktop Suite               │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────┐    ┌─────────────────┐  │
│  │   Emulator    │◄──►│  Configurator   │  │
│  │  (C firmware) │    │    (Python)     │  │
│  └───────┬───────┘    └─────────────────┘  │
│          │                                  │
│          ▼                                  │
│  ┌───────────────┐                         │
│  │    Web UI     │                         │
│  │ (Browser)     │                         │
│  └───────────────┘                         │
│                                             │
└─────────────────────────────────────────────┘
```

## Logic Functions

This version includes full implementation of all logic operations:

| Category | Operations |
|----------|------------|
| **Basic** | IS_TRUE, IS_FALSE, AND, OR, XOR, NOT, NAND, NOR |
| **Comparison** | EQUAL, NOT_EQUAL, LESS, GREATER, LESS_EQUAL, GREATER_EQUAL |
| **Range** | IN_RANGE (lower <= value <= upper) |
| **Stateful** | HYSTERESIS, SET_RESET_LATCH, TOGGLE, FLASH, PULSE, CHANGED |
| **Edge** | EDGE_RISING, EDGE_FALLING (one-shot pulse on transitions) |

### Boolean Casting
All logic functions use C-style boolean casting:
- `value > 0` = TRUE (1000)
- `value <= 0` = FALSE (0)

This allows using any channel type as a logic input:
- Timer running (1000) = TRUE
- Analog voltage > 0mV = TRUE
- Output current > 0mA = TRUE

### Comparison Constants
Constants are in the same units as the channel value:
- Timer elapsed: constant in milliseconds
- Analog input: constant in millivolts
- Logic output: constant as 0 or 1000

## System Requirements

- Windows 10/11 (64-bit)
- Python 3.10+ (for configurator)
- PyQt6 (for configurator GUI)

## Troubleshooting

### Configurator won't connect
1. Make sure emulator is running first
2. Check that port 9876 is not blocked by firewall
3. Try running emulator with administrator privileges

### Emulator crashes on startup
1. Check if another instance is already running
2. Verify that ports 8080 and 9876 are available

### Logic functions not working
1. Verify channel references use string IDs (e.g., "Timer_7")
2. Check that constant values are in correct units
3. Enable debug output in emulator to see logic evaluation

## Version History

### v0.2.1 (2025-12-25)
- Full implementation of all logic operations
- Fixed channel references (now use string IDs)
- Fixed timer elapsed output (now in milliseconds)
- Fixed comparison constants (no x1000 scaling)

### v0.2.0
- Desktop emulator with Web UI
- PyQt6 configurator with dark theme
- Real-time telemetry and data logging

## License

Proprietary - R2 m-sport (c) 2025. All rights reserved.

# PMU-30 Hardware Emulator

Hardware emulator for PMU-30 that allows running firmware logic on a PC without physical hardware. Designed for development, testing, and debugging of the PMU-30 configurator and firmware.

## Table of Contents

- [Features](#features)
- [Current Status](#current-status)
- [Build and Run](#build-and-run)
- [Configurator Connection](#configurator-connection)
- [Interactive Mode](#interactive-mode)
- [UI Visualization](#ui-visualization)
- [Test Scenarios](#test-scenarios)
- [API for Programmatic Use](#api-for-programmatic-use)
- [Architecture](#architecture)
- [Limitations](#limitations)
- [TODO / Future Improvements](#todo--future-improvements)

---

## Features

### Implemented Components

| Component | Status | Description |
|-----------|--------|-------------|
| **ADC (20 channels)** | Working | Analog/digital/frequency input injection |
| **CAN Bus (4 buses)** | Working | Message injection, periodic messages, online/offline simulation |
| **PROFET (30 outputs)** | Working | State monitoring, current simulation, fault injection |
| **H-Bridge (4 bridges)** | Working | Position simulation, motor parameters, fault injection |
| **Protection System** | Working | Voltage/temperature/current monitoring, fault injection |
| **TCP Server** | Working | Configurator connection on port 9876 |
| **JSON Config Parsing** | Working | Full v3.0 config format support |
| **Telemetry** | Working | Real-time channel state streaming |
| **Console UI** | Working | Channel state visualization |
| **Lua Scripting** | Optional | Requires Lua 5.4 library (disabled by default on Windows) |

### Key Capabilities

- **Data Injection** - Set values for all ADC inputs via console or API
- **CAN Frame Injection** - Inject CAN messages (one-shot or periodic)
- **Fault Injection** - Inject faults for protection and output testing
- **JSON Scenarios** - Load/save test scenarios from files
- **Real-time Simulation** - Current calculation based on voltage and load resistance
- **Motor Simulation** - H-Bridge position simulation with speed and inertia parameters
- **Configurator Connection** - Full protocol compatibility with PMU-30 Configurator

---

## Current Status

### What Works

1. **Configurator Connection**
   - TCP server accepts connections from configurator
   - PING/PONG for connection check
   - GET_INFO returns device information
   - SET_CONFIG receives and parses JSON configuration
   - Telemetry subscription and streaming

2. **Configuration Parsing**
   - Version detection (v1.0, v2.0, v3.0)
   - Device info (name, serial, firmware version)
   - All channel types: digital_input, analog_input, power_output, logic, timer, filter, table2d, table3d, can_rx, can_tx
   - Protection settings (current limits, inrush, retry)
   - PWM settings (frequency, duty, soft start)
   - CAN messages (Level 1)
   - Lua scripts (parsing only, execution requires Lua library)
   - System settings (frequencies, baudrates)
   - Settings (CAN stream enable, CAN bus configs)

3. **HAL Emulation**
   - GPIO read/write
   - ADC with DMA buffer filling
   - Timer PWM
   - FDCAN TX/RX
   - SPI (stub responses)
   - UART (stdout output)

4. **Interactive Console**
   - All documented commands working
   - Background tick thread for real-time operation
   - Signal handling for graceful shutdown

5. **Firmware Integration**
   - PMU_Channel_Update() called at 1kHz tick rate
   - PMU_Logic_Execute() called at 500Hz for logic functions
   - PMU_CAN_Update() processes CAN RX queue from injected messages
   - Real channel values from firmware used in telemetry

6. **Configuration Persistence**
   - Configuration saved to `last_config.json` on each upload
   - Configuration automatically loaded on emulator startup

### What's Partially Working

1. **Lua Scripting** - Script management infrastructure works, actual Lua execution requires linking Lua 5.4 library

---

## Build and Run

### Requirements

- PlatformIO Core (CLI)
- GCC compiler:
  - **Windows**: MinGW-w64 via MSYS2
  - **Linux/macOS**: Native GCC
- Lua 5.4 (optional, for scripting)

### Installing Dependencies

**Windows (MSYS2):**
```bash
# Install MSYS2 from https://www.msys2.org/
pacman -S mingw-w64-ucrt-x86_64-gcc
# Add C:\msys64\ucrt64\bin to PATH
```

**Linux:**
```bash
sudo apt install build-essential
# Optional: Lua for scripting
sudo apt install liblua5.4-dev
```

### Building

```bash
cd firmware

# Build emulator
pio run -e pmu30_emulator

# Run (Linux/macOS)
.pio/build/pmu30_emulator/program

# Run (Windows)
.pio\build\pmu30_emulator\program.exe
```

### Run Modes

```bash
# Interactive mode (default) - console with commands
./pmu30_emulator

# Headless mode - TCP server only, no console
./pmu30_emulator --headless

# Run scenario file
./pmu30_emulator --scenario scenarios/test.json

# Show help
./pmu30_emulator --help

# Show version
./pmu30_emulator --version
```

---

## Configurator Connection

The emulator starts a TCP server on port **9876** that accepts connections from the PMU-30 Configurator.

### Connection Steps

1. **Start the emulator:**
   ```bash
   .pio\build\pmu30_emulator\program.exe
   ```

   Console output:
   ```
   +===============================================================+
   |               PMU-30 Firmware Emulator v1.0.0                 |
   +===============================================================+
   >>> Configurator can connect to: localhost:9876
   ```

2. **Start Configurator:**
   ```bash
   cd configurator
   python launch.py
   ```

3. **Connect from Configurator:**
   - Click **Connect** or **File -> Connect**
   - Select connection type: **Emulator**
   - Host: `localhost`
   - Port: `9876`
   - Click **Check Emulator** (should show "ONLINE")
   - Click **Connect**

### Configuration Loading

When you send configuration from Configurator (Write to Device):

```
+============================================================+
|          CONFIGURATION LOADED FROM CONFIGURATOR            |
+============================================================+
|  Total Channels:    15                                     |
|    - Digital Inputs: 4                                     |
|    - Analog Inputs:  6                                     |
|    - Power Outputs:  3                                     |
|    - Logic Functions:2                                     |
|    - CAN RX:         0                                     |
|    - CAN TX:         0                                     |
|  CAN Messages:      5                                      |
|  Lua Scripts:       1                                      |
|  CAN Stream:        ON                                     |
|  Parse Time:        3 ms                                   |
|  Config saved to:   last_config.json                       |
+============================================================+
```

Configuration is also saved to `last_config.json` for debugging.

### Remote Connection

The emulator can run on a remote machine:

```bash
# On server
./pmu30_emulator --headless

# In Configurator
Host: 192.168.1.100
Port: 9876
```

---

## Interactive Mode

### Command Reference

```
--- ADC Commands ---
  adc <ch> <value>      Set ADC channel (0-19) raw value (0-1023)
  adcv <ch> <voltage>   Set ADC channel voltage (0.0-3.3V)
  freq <ch> <hz>        Set frequency input (Hz)

--- CAN Commands ---
  can <bus> <id> <d0> [d1-d7]   Inject single CAN message
  canp <bus> <id> <int> <d0-d7> Add periodic CAN message (interval in ms)
  canoff <bus>          Set CAN bus offline
  canon <bus>           Set CAN bus online

--- Protection Commands ---
  volt <mV>             Set battery voltage (mV)
  temp <C>              Set board temperature (C)
  fault <flags>         Inject protection fault (hex)
  clear                 Clear all faults

--- PROFET Commands ---
  load <ch> <ohm>       Set PROFET load resistance
  pfault <ch> <flags>   Inject PROFET fault (hex)

--- H-Bridge Commands ---
  hpos <br> <pos>       Set H-Bridge position (0-1000)
  hmotor <br> <spd> <i> Set motor params (speed, inertia)
  hfault <br> <flags>   Inject H-Bridge fault (hex)

--- Control Commands ---
  pause                 Pause emulator tick
  resume                Resume emulator tick
  speed <x>             Set time scale (1.0 = real-time, 2.0 = 2x speed)
  reset                 Reset emulator to defaults
  status                Print full emulator status
  tick                  Run single tick manually

--- Scenario Commands ---
  load <file>           Load scenario from JSON file
  save <file>           Save current state to JSON

--- UI Commands ---
  ui                    Show channel state grid
  ui <ch>               Show detailed info for channel (0-29)
  ui on                 Enable automatic state updates
  ui off                Disable automatic state updates

--- General ---
  help                  Show command help
  quit / exit           Exit emulator
```

### Usage Examples

```bash
# Set ADC input to mid-scale
EMU> adc 0 512
ADC[0] = 512

# Set ADC voltage directly
EMU> adcv 1 2.5
ADC[1] = 2.500V

# Set battery voltage to 14V
EMU> volt 14000
Voltage = 14000 mV

# Inject CAN message on bus 0
EMU> can 0 0x100 01 02 03 04
CAN[0] TX: ID=0x100, DLC=4

# Set load resistance for current simulation
EMU> load 5 4.7
PROFET[5] load = 4.7 ohm

# Inject overcurrent fault on channel 0
EMU> pfault 0 0x01
PROFET[0] fault: 0x01

# View full status
EMU> status
=== PMU-30 Emulator State ===
Uptime: 45 seconds
Time scale: 1.0x
Status: RUNNING
...
```

---

## UI Visualization

Console-based monitoring of channel states.

### Commands

| Command | Description |
|---------|-------------|
| `ui` | Show state grid for all 30 channels |
| `ui <ch>` | Detailed information for specific channel |
| `ui on` | Enable automatic updates on state change |
| `ui off` | Disable automatic updates |

### Channel Grid

```
EMU> ui

+---------------------------------------------------------+
|                   CHANNEL STATUS                        |
+---------------------------------------------------------+
|  0  1  2  3  4  5  6  7  8  9                          |
|  *  o  o  *  o  ~  o  o  o  *                          |
|                                                         |
| 10 11 12 13 14 15 16 17 18 19                          |
|  o  o  *  o  o  o  o  o  o  o                          |
|                                                         |
| 20 21 22 23 24 25 26 27 28 29                          |
|  o  o  o  o  ~  o  o  o  o  *                          |
+---------------------------------------------------------+
  Legend: o=OFF  *=ON  ~=PWM  !=FAULT
```

### Channel Details

```
EMU> ui 5

=== Channel 5 Details ===
  State:       PWM (75.5%)
  Current:     2340 mA
  Temperature: 42 C
  On time:     15230 ms
  Faults:      0x00 (0 total)
```

---

## Test Scenarios

### JSON Format

```json
{
    "name": "Basic Test",
    "description": "Test scenario with default values",

    "adc": [512, 512, 0, 0, 0, 0, 0, 0, 0, 0,
           0, 0, 0, 0, 0, 0, 0, 0, 0, 0],

    "voltage_mV": 12000,
    "temperature_C": 25,

    "can_messages": [
        {
            "bus": 0,
            "id": "0x100",
            "data": [1, 2, 3, 4, 5, 6, 7, 8],
            "interval_ms": 100
        }
    ],

    "profet_loads": [
        {"channel": 0, "resistance_ohm": 4.7},
        {"channel": 1, "resistance_ohm": 10.0}
    ]
}
```

### Running Scenarios

```bash
# Load at startup
./pmu30_emulator --scenario test_can.json

# Load from interactive mode
EMU> load test_can.json
Scenario loaded: test_can.json
```

---

## API for Programmatic Use

### C API

```c
#include "pmu_emulator.h"

// Initialize
PMU_Emu_Init();

// Main loop
while (running) {
    PMU_Emu_Tick(1);  // 1ms tick
    usleep(1000);
}

// Cleanup
PMU_Emu_Deinit();
```

### Data Injection

```c
// ADC
PMU_Emu_ADC_SetVoltage(0, 2.5f);     // Channel 0, 2.5V
PMU_Emu_ADC_SetRaw(1, 512);           // Channel 1, raw value
PMU_Emu_ADC_SetFrequency(2, 1000);    // Channel 2, 1000 Hz

// CAN
uint8_t data[] = {0x01, 0x02, 0x03, 0x04};
PMU_Emu_CAN_InjectMessage(0, 0x100, data, 4);
PMU_Emu_CAN_AddPeriodicMessage(0, 0x200, data, 8, 100); // 100ms interval

// Protection
PMU_Emu_Protection_SetVoltage(12000);      // 12V
PMU_Emu_Protection_SetTemperature(25);     // 25C

// Fault injection
PMU_Emu_Protection_InjectFault(0x0001);    // Undervoltage
PMU_Emu_PROFET_InjectFault(0, 0x01);       // Channel 0 overcurrent
```

### Callbacks

```c
// CAN TX callback - called when firmware sends CAN message
void OnCanTx(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len) {
    printf("CAN TX: bus=%d, id=0x%X\n", bus, id);
}
PMU_Emu_CAN_SetTxCallback(OnCanTx);

// Get PROFET state
const PMU_Emu_PROFET_Channel_t* ch = PMU_Emu_PROFET_GetState(0);
printf("PROFET[0]: state=%d, current=%d mA\n", ch->state, ch->current_mA);
```

---

## Architecture

```
+-----------------------------------------------------------+
|                   PMU-30 Configurator                      |
|                    (TCP Client)                            |
+-----------------------------+-----------------------------+
                              | TCP:9876
                              v
+-----------------------------------------------------------+
|                  Protocol Server                           |
|         (emu_protocol_server.c)                           |
|  - Handles PING, GET_INFO, SET_CONFIG, TELEMETRY          |
+-----------------------------------------------------------+
|                  Interactive Console                       |
|         (emu_main.c)                                      |
|  - Command parsing, tick thread, signal handling          |
+-----------------------------------------------------------+
|                    Console UI                              |
|         (emu_ui.c)                                        |
|  - Channel state visualization                            |
+-----------------------------------------------------------+
|                  PMU Emulator Core                         |
|         (pmu_emulator.c)                                  |
|  - ADC, CAN, PROFET, H-Bridge, Protection simulation      |
+-----------------------------------------------------------+
|                  HAL Emulation Layer                       |
|         (stm32_hal_emu.h + pmu_emulator.c)               |
|  - GPIO, ADC, TIM, SPI, UART, FDCAN stubs                |
+-----------------------------------------------------------+
|                  Firmware Stubs                            |
|         (emu_stubs.c)                                     |
|  - DMA buffers, weak function stubs                       |
+-----------------------------------------------------------+
|                  Firmware Sources                          |
|  (pmu_config_json.c, pmu_channel.c, pmu_can.c, ...)      |
+-----------------------------------------------------------+
```

### Communication Protocol

| Code | Message | Direction | Description |
|------|---------|-----------|-------------|
| 0x01 | PING | C->E | Connection check |
| 0x02 | PONG | E->C | PING response |
| 0x10 | GET_INFO | C->E | Request device info |
| 0x11 | INFO_RESP | E->C | Device info response |
| 0x20 | GET_CONFIG | C->E | Request current configuration |
| 0x21 | CONFIG_DATA | E->C | Configuration data |
| 0x22 | SET_CONFIG | C->E | Send new configuration (JSON) |
| 0x23 | CONFIG_ACK | E->C | Configuration accepted |
| 0x30 | SUBSCRIBE_TELEM | C->E | Start telemetry streaming |
| 0x31 | UNSUBSCRIBE_TELEM | C->E | Stop telemetry streaming |
| 0x32 | TELEMETRY_DATA | E->C | Telemetry packet |
| 0x40 | SET_CHANNEL | C->E | Set channel output value |
| 0x41 | CHANNEL_ACK | E->C | Channel set acknowledged |
| 0x50 | ERROR | E->C | Error response |

C = Configurator, E = Emulator

---

## Limitations

### Architectural Limitations

- **Single-threaded execution** - No FreeRTOS task scheduling, all firmware runs in main tick loop
- **No real-time guarantees** - Timing depends on host OS scheduler
- **Simplified physics** - Current/temperature simulation is approximate

### Not Emulated

- **Flash memory** - No persistent storage, config is RAM-only
- **SPI diagnostics** - Returns stub/zero values
- **External EEPROM** - Not implemented
- **RTC** - Uses host system time
- **DMA transfers** - Simulated synchronously
- **Interrupts** - Polling-based instead

### Known Issues

1. **PWM output state** - Visual state tracking works, but actual PWM generation is simulated
2. **H-Bridge end stops** - No mechanical limit switch simulation
3. **Lua execution disabled** - Lua library not linked by default; only script management works

---

## TODO / Future Improvements

### Recently Completed ✓

- [x] **Integrate firmware logic execution** - PMU_Channel_Update and PMU_Logic_Execute now called in tick loop
- [x] **CAN RX message processing** - Injected CAN messages are processed by firmware CAN handler
- [x] **Telemetry with real data** - Uses PMU_Channel_GetValue() for actual channel states
- [x] **Output state feedback** - SET_CHANNEL updates both firmware channel and emulator state
- [x] **Lua scripting structure** - Lua files included in build (stub mode without Lua library)
- [x] **Config persistence** - Auto-loads last_config.json on startup

### High Priority

- [ ] **Full Lua support** - Link Lua 5.4 library for actual script execution
- [ ] **Web UI** - Browser-based monitoring interface
- [ ] **Multiple client support** - Allow multiple configurator connections
- [ ] **CAN bus logging** - Save CAN traffic to file for analysis

### Medium Priority

- [ ] **Flash memory emulation** - File-backed persistent storage
- [ ] **SPI diagnostic simulation** - Return realistic PROFET diagnostic data
- [ ] **Automated test framework** - JSON-based test assertions
- [ ] **Performance profiling** - Measure tick execution time
- [ ] **Docker support** - Containerized emulator for CI/CD

### Configurator Integration

- [ ] **Read config from device** - GET_CONFIG should return current parsed config
- [ ] **Error reporting** - Send parsing errors back to configurator
- [ ] **Firmware update simulation** - Accept firmware binary (no-op)

---

## Files Structure

```
firmware/emulator/
├── emu_main.c              # Entry point, CLI parsing, interactive mode
├── emu_protocol_server.c   # TCP server, protocol handling
├── emu_protocol_server.h   # Server API
├── emu_ui.c               # Console UI visualization
├── emu_stubs.c            # DMA buffers, weak function stubs
├── emu_flash.c            # Flash emulation (stub)
├── pmu_emulator.c         # Core emulation: ADC, CAN, PROFET, H-Bridge
├── pmu_emulator.h         # Emulator API
├── stm32_hal_emu.h        # HAL type definitions and stubs
└── README.md              # This file
```

---

## License

Copyright (c) 2025 R2 m-sport. All rights reserved.

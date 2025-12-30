# PMU Monitor

The PMU Monitor provides a comprehensive real-time view of the entire PMU-30 system state, similar to professional ECU diagnostic displays (ECUMaster style).

## Overview

Located in the Monitor panel as the first tab (shortcut: **F9**), this widget displays all system parameters in an expandable tree structure.

## Display Format

```
+-- System (expanded by default)
|     Board Temp L:     45.2 C
|     Board Temp R:     43.8 C
|     Board Temp 2:     41.5 C
|     Battery Voltage:  13.8 V
|     5V Output:        5.02 V
|     3.3V Output:      3.31 V
|     Total Current:    12.5 A
|     Uptime:           01:23:45
|     Status:           0x0000
|     Reset Detector:   0
|     User Error:       0
|     Is Turning Off:   No
|
+-- HW OUT Active Mask
|     o1: ON   o2: OFF  o3: PWM  ...
|
+-- HW LS OUT Active
|     ls1: OFF  ls2: OFF  ...
|
+-- Output Currents
|     O1:  2.5A   O2: 0.0A   O3: 1.2A  ...
|
+-- Output States
|     O1: ON     O2: OFF    O3: PWM   ...
|
+-- Analog Inputs
|     A1: 2.45V  A2: 1.23V  A3: 0.00V ...
|
+-- Digital Inputs
|     D1: HIGH   D2: LOW    D3: HIGH  ...
|
+-- H-Bridges
|   +-- HB1
|   |     State: IDLE
|   |     Current: 0.0A
|   |     Duty: 0%
|   +-- HB2
|         ...
|
+-- CAN Bus
|   +-- CAN1
|   |     Status: OK
|   |     RX Count: 1234
|   |     TX Count: 567
|   |     Errors: 0
|   +-- CAN2
|         ...
|
+-- Faults
|     Overvoltage:  No
|     Undervoltage: No
|     Overtemp:     No
|     CAN1 Error:   No
|     CAN2 Error:   No
|     Config Error: No
|     Watchdog:     No
|
+-- Device Info
      Serial: 12345678
      Firmware: v1.2.3
      Hardware: Rev B
      Uptime: 01:23:45
```

## Categories

### System (Auto-Expanded)

Core system health parameters:

| Parameter | Description | Range |
|-----------|-------------|-------|
| Board Temp L | Left side temperature | -40 to 125 C |
| Board Temp R | Right side temperature | -40 to 125 C |
| Board Temp 2 | Secondary sensor | -40 to 125 C |
| Battery Voltage | Input supply voltage | 0 to 30 V |
| 5V Output | Internal 5V rail | 0 to 6 V |
| 3.3V Output | Internal 3.3V rail | 0 to 4 V |
| Total Current | Sum of all outputs | 0 to 1200 A |
| Uptime | Time since power on | HH:MM:SS |
| Status | Status bit field | Hex |
| Reset Detector | Reset flag | 0/1 |
| User Error | Application error | 0/1 |
| Is Turning Off | Shutdown in progress | Yes/No |

### HW OUT Active Mask

Shows ON/OFF/PWM state for all 30 PROFET outputs in compact format:
```
o1: ON   o2: OFF  o3: PWM  o4: OFF  o5: ON   o6: OFF
o7: OFF  o8: OFF  o9: OFF  o10: ON  ...
```

### Output Currents

Real-time current draw for each output channel:
```
O1:  2.50A   O2:  0.00A   O3:  1.23A   O4:  0.00A
O5:  0.85A   O6:  0.00A   O7:  0.00A   O8:  0.00A
...
```

### Output States

Current state of each output:

| State | Description | Color |
|-------|-------------|-------|
| OFF | Output disabled | White |
| ON | Output active (100%) | Green |
| PWM | Pulse-width modulation | Blue |
| OC | Overcurrent fault | Red |
| OT | Overtemperature fault | Red |
| SC | Short circuit fault | Red |
| OL | Open load detected | Orange |
| DIS | Disabled by protection | Gray |

### Analog Inputs

Raw voltage readings from all 20 analog channels:
```
A1: 2.45V   A2: 1.23V   A3: 0.00V   A4: 3.30V
A5: 1.65V   A6: 0.82V   A7: 2.10V   A8: 0.00V
...
```

### Digital Inputs

Logic state of all 20 digital inputs:
```
D1: HIGH   D2: LOW    D3: HIGH   D4: LOW
D5: LOW    D6: HIGH   D7: LOW    D8: LOW
...
```

### H-Bridges

Each H-Bridge has a sub-section:

| Parameter | Description |
|-----------|-------------|
| State | IDLE, RUN, STALL, FAULT, OC, OT |
| Current | Motor current in Amps |
| Duty | PWM duty cycle 0-100% |

### CAN Bus

Each CAN interface shows:

| Parameter | Description |
|-----------|-------------|
| Status | OK, ERROR, BUS_OFF |
| RX Count | Messages received |
| TX Count | Messages transmitted |
| Errors | Error counter |

### Faults

System fault flags (binary Yes/No):

| Fault | Trigger Condition |
|-------|-------------------|
| Overvoltage | Battery > 18V |
| Undervoltage | Battery < 9V |
| Overtemp | Board > 85C |
| CAN1 Error | CAN1 bus error |
| CAN2 Error | CAN2 bus error |
| Config Error | Invalid configuration |
| Watchdog | Watchdog timeout |

### Device Info

Static device information:

| Field | Description |
|-------|-------------|
| Serial | Unique device serial number |
| Firmware | Firmware version string |
| Hardware | Hardware revision |
| Uptime | Running time since boot |

## Color Coding

Text colors indicate status:

| Color | Hex | Meaning |
|-------|-----|---------|
| Light Gray | #C8C8C8 | Normal value |
| Green | #64FF64 | Active/OK |
| Orange | #FFC864 | Warning |
| Red | #FF6464 | Error/Fault |
| Gray | #808080 | Disabled/Inactive |

## Update Rate

- **Refresh interval**: 100ms (10 Hz)
- **Data source**: Telemetry stream from device
- **Offline behavior**: Shows last known values grayed out

## Interactions

### Expand/Collapse
- Click category name to expand/collapse
- System category auto-expands on connect

### Copy Values
- Right-click any value to copy to clipboard
- Select multiple rows for bulk copy

## Styling

```
Background: Pure Black (#000000)
Text: White (#FFFFFF)
Header: Dark Gray (#2D2D2D)
Border: 1px #333333
Font: Monospace for values, Sans-serif for labels
```

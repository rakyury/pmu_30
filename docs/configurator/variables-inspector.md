# Variables Inspector

The Variables Inspector displays all system variables and virtual channels in real-time. Access via monitor tabs or press **F12**.

## Overview

This widget provides a comprehensive view of every accessible value in the PMU-30 system, including hardware channels, user-created channels, and system parameters.

## Table Layout

| Name | Value | Unit |
|------|-------|------|
| pmu.battery_voltage | 13.82 | V |
| pmu.board_temp_l | 45.2 | °C |
| pmu.o1.current | 2.5 | A |
| Headlight Logic | ON | |
| Fuel Filter | 75.2 | % |

## Column Definitions

| Column | Width | Description |
|--------|-------|-------------|
| **Name** | 200px | Variable/channel name |
| **Value** | 100px | Current value |
| **Unit** | 60px | Unit of measurement |

## Variable Categories

### 1. Constant Channels

System constants always available:

| Name | Value | Description |
|------|-------|-------------|
| zero | 0 | Constant zero |
| one | 1 | Constant one |

### 2. PMU System Channels

Core system parameters (prefix: `pmu.`):

| Name | Description | Unit |
|------|-------------|------|
| pmu.status | System status bits | - |
| pmu.user_error | Application error flag | - |
| pmu.battery_voltage | Input voltage | V |
| pmu.board_temp_l | Left board temperature | °C |
| pmu.board_temp_r | Right board temperature | °C |
| pmu.board_temp_max | Maximum temperature | °C |
| pmu.5v_output | 5V rail voltage | V |
| pmu.3v3_output | 3.3V rail voltage | V |
| pmu.total_current | Sum of all outputs | A |
| pmu.uptime | Time since boot | s |
| pmu.is_turning_off | Shutdown flag | - |

### 3. PMU Hardware Channels

Direct hardware access:

#### Output Channels (pmu.oN.*)
```
pmu.o1.status    - Output state (0=OFF, 1=ON, etc.)
pmu.o1.current   - Current draw in mA
pmu.o1.dc        - Duty cycle (0-1000 = 0-100%)
...through pmu.o40.*
```

#### Analog Inputs (pmu.aN.*)
```
pmu.a1.voltage   - Scaled voltage
pmu.a1.raw       - Raw ADC value (0-4095)
...through pmu.a20.*
```

#### Digital Inputs (pmu.dN.*)
```
pmu.d1.state     - Digital state (0 or 1)
...through pmu.d20.*
```

### 4. User-Created Output Channels

For each configured output:
```
{output_name}.status   - Current state
{output_name}.current  - Current in mA
{output_name}.dc       - Duty cycle
{output_name}.fault    - Fault flags
```

Example:
```
Headlights.status  = 1
Headlights.current = 8500
Headlights.dc      = 1000
Headlights.fault   = 0
```

### 5. User-Created Input Channels

For each configured analog input:
```
{input_name}.voltage  - Processed voltage
{input_name}.raw      - Raw ADC value
```

### 6. CAN RX Channels

From CAN message definitions:
```
Engine_RPM         - Extracted signal value
Coolant_Temp       - Extracted signal value
```

### 7. BlinkMarine Keypad Channels

For configured CAN keypads:
```
bm_{keypad_name}.btn1  - Button 1 state
bm_{keypad_name}.btn2  - Button 2 state
...
```

### 8. Virtual Channels (ID 200+)

User-created logic, math, and state channels:

#### Logic Channels
```
Display: "ON" or "OFF"
Color: Green when ON (value > 0)
```

#### Number/Math Channels
```
Display: Numeric value / 1000 with 2 decimals
Example: 1500 → "1.50"
```

#### Timer Channels
```
{timer_name}          - "ON" or "OFF"
{timer_name}.elapsed  - Time in ms (formatted HH:MM:SS)
{timer_name}.running  - Boolean state
```

#### Filter Channels
```
Display: Filtered value with configured decimals
```

#### Switch Channels
```
Display: "State N" where N is current state
```

## Value Formatting

| Type | Format | Example |
|------|--------|---------|
| Logic | ON / OFF | "ON" |
| Timer State | ON / OFF | "OFF" |
| Timer Elapsed | HH:MM:SS | "01:23:45" |
| Switch | State N | "State 2" |
| Numeric | value/1000 | "1.50" |
| Percentage | with % | "75.2%" |
| Voltage | with V | "13.82V" |
| Current | with A/mA | "2.5A" |
| Temperature | with °C | "45.2°C" |

## Row Colors

| Condition | Background | Description |
|-----------|------------|-------------|
| Normal | #000000 (Black) | Default state |
| Active/ON | #325032 (Green) | Logic true, timer running |
| Error | #503028 (Red) | Fault condition |
| Disabled | #3C3C3C (Gray) | Offline or unavailable |
| Recently Changed | #283C28 (Darker Green) | Value just updated |

### Change Highlighting

When a value changes:
1. Row briefly highlights with darker green background
2. Color decays back to normal over 250ms
3. Helps identify active/changing values

## Filter Feature

Toolbar includes a search filter:

```
[Filter: ______________]
```

- Case-insensitive matching
- Filters by variable name
- Real-time filtering as you type
- Clear button to show all

## Update Performance

Optimized for large variable counts:

| Feature | Implementation |
|---------|----------------|
| Row Lookup | O(1) via index map |
| Batched Updates | Groups telemetry updates |
| Color Decay | 250ms timer, changed rows only |
| Scroll Position | Preserved during updates |

## Double-Click Action

Double-clicking a row opens the edit dialog for editable channel types:

| Type | Dialog |
|------|--------|
| Logic | Logic Dialog |
| Number | Number Dialog |
| Timer | Timer Dialog |
| Filter | Filter Dialog |
| Switch | Switch Dialog |
| Table 2D | Table 2D Dialog |
| Table 3D | Table 3D Dialog |
| Analog Input | Analog Input Dialog |
| Digital Input | Digital Input Dialog |
| Power Output | Output Config Dialog |
| H-Bridge | H-Bridge Dialog |
| CAN RX | CAN Input Dialog |
| CAN TX | CAN Output Dialog |
| PID | PID Controller Dialog |

## Sorting

Default sort order by category:
1. System channels (pmu.*)
2. Hardware channels
3. User outputs
4. User inputs
5. CAN channels
6. Virtual channels (logic, timer, etc.)

Within categories, sorted alphabetically by name.

## Styling

```css
Table {
  background: #000000;
  alternate-row: none;
  gridline-color: #333333;
}

Header {
  background: #2D2D2D;
  font-weight: bold;
}

Scrollbar {
  background: #1a1a1a;
  handle: #404040;
  handle-hover: #505050;
}

Row.active {
  background: #325032;
}

Row.changed {
  background: #283C28;
  transition: background 250ms;
}
```

## Use Cases

### Debugging
- Monitor all values simultaneously
- Identify which channels are changing
- Verify logic function outputs

### Tuning
- Watch PID controller behavior
- Observe filter response
- Check timer operation

### Verification
- Confirm CAN signal decoding
- Validate analog scaling
- Test digital input logic

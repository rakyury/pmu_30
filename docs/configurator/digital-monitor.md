# Digital Monitor

The Digital Monitor displays real-time state of all 20 digital input channels. Access via the monitor tabs.

## Table Layout

| Pin | Name | State | Type |
|-----|------|-------|------|
| D1 | Ignition | ON | Switch High |
| D2 | Door Sensor | OFF | Switch Low |
| D3 | Speed Sensor | 2450 | Frequency |
| D4 | (unconfigured) | - | - |

## Column Definitions

| Column | Width | Description |
|--------|-------|-------------|
| **Pin** | 50px | Digital pin identifier (D1-D20) |
| **Name** | 150px | User-assigned channel name |
| **State** | 80px | Current logical state |
| **Type** | 100px | Input subtype configuration |

## Input Types (Subtypes)

### Switch Active High

Standard digital switch, HIGH = ON:

```
Configuration:
  subtype: "switch_active_high"

Logic:
  Physical HIGH (3.3V) → Logical ON
  Physical LOW (0V)    → Logical OFF

Use Case:
  - Push buttons to 3.3V
  - Active-high sensors
```

### Switch Active Low

Inverted logic switch, LOW = ON:

```
Configuration:
  subtype: "switch_active_low"

Logic:
  Physical HIGH (3.3V) → Logical OFF
  Physical LOW (0V)    → Logical ON

Use Case:
  - Push buttons to ground
  - Open-collector outputs
  - Active-low sensors
```

### Frequency Input

Measures signal frequency:

```
Configuration:
  subtype: "frequency"

Display:
  State shows frequency in Hz

Range: 0-50,000 Hz typical

Use Case:
  - Hall effect wheel sensors
  - Flow meters
  - Tachometer signals
```

### RPM Input

Frequency converted to RPM:

```
Configuration:
  subtype: "rpm"
  pulses_per_rev: 2  (configurable)

Formula:
  RPM = (frequency × 60) / pulses_per_rev

Display:
  State shows RPM value

Use Case:
  - Engine speed sensors
  - Wheel speed sensors
```

### Flex Fuel

Ethanol content sensor:

```
Configuration:
  subtype: "flex_fuel"

Input:
  50-150 Hz signal from flex fuel sensor

Output:
  Ethanol percentage (0-100%)

Formula:
  E% = (frequency - 50)  [clamped 0-100]
```

### Beacon

Emergency beacon/strobe detector:

```
Configuration:
  subtype: "beacon"

Behavior:
  Detects periodic flashing patterns
```

### PULS Oil

Oil consumption pulse counter:

```
Configuration:
  subtype: "puls_oil"

Behavior:
  Counts pulses for oil usage monitoring
```

## State Display

| State | Meaning | Condition |
|-------|---------|-----------|
| **ON** | Logically active | Switch triggered |
| **OFF** | Logically inactive | Switch not triggered |
| **-** | Offline/Unknown | No connection |
| **{number}** | Frequency/RPM value | Frequency-type inputs |

## Row Colors

| Condition | Background | Text |
|-----------|------------|------|
| Logical ON | #325032 (Dark Green) | White |
| Logical OFF | #000000 (Black) | White |
| Unconfigured | #3C3C3C (Gray) | #808080 (Dim) |
| Offline | #3C3C3C (Gray) | #808080 (Dim) |

## Logic Mapping

Important: The State column shows **logical** state, not physical voltage:

```
Switch Active High:
  Physical HIGH → State: ON  (green row)
  Physical LOW  → State: OFF (black row)

Switch Active Low:
  Physical HIGH → State: OFF (black row)
  Physical LOW  → State: ON  (green row)
```

## Hardware Specifications

| Parameter | Value |
|-----------|-------|
| Input Voltage | 0-5V tolerant (3.3V logic) |
| Logic Threshold | ~1.65V (Schmitt trigger) |
| Pull-up/down | Configurable internal |
| Debounce | Software configurable |
| Max Frequency | 50 kHz |

## Wiring Examples

### Push Button to Ground (Active Low)

```
        PMU-30
         ___
Button -|D1 |--- Internal Pull-up
        |   |
GND ----|   |
        |___|

Configuration:
  Type: Switch Low
  Pull: Pull-up enabled
```

### Push Button to 3.3V (Active High)

```
        PMU-30      3.3V
         ___         |
Button -|D1 |--------+
        |   |
GND ----|   |--- Internal Pull-down
        |___|

Configuration:
  Type: Switch High
  Pull: Pull-down enabled
```

### Hall Effect Speed Sensor

```
        PMU-30
         ___
Signal -|D1 |
        |   |
GND ----|GND|
5V -----|5V |
        |___|

Configuration:
  Type: Frequency or RPM
  Pulses per rev: 4 (for wheel with 4 magnets)
```

### Open Collector Output

```
External Device     PMU-30
     ___             ___
    |   |-- OUT ----|D1 |--- Internal Pull-up
    |   |           |   |
    |GND|-----------|GND|
    |___|           |___|

Configuration:
  Type: Switch Low (active when pulled low)
  Pull: Pull-up enabled
```

## Update Behavior

- **Refresh rate**: 100ms (10 Hz)
- **Data source**: Telemetry digital input array
- **Debouncing**: Hardware + software (configurable)
- **Offline**: Shows "-" for state

## Type Display Format

| Subtype | Display |
|---------|---------|
| switch_active_high | "Switch High" |
| switch_active_low | "Switch Low" |
| frequency | "Frequency" |
| rpm | "RPM" |
| flex_fuel | "Flex Fuel" |
| beacon | "Beacon" |
| puls_oil | "PULS Oil" |
| (none) | "-" |

## Double-Click Action

Double-clicking a row opens the Digital Input Configuration dialog.

## Common Applications

| Application | Type | Notes |
|-------------|------|-------|
| Ignition Switch | Switch High/Low | Depends on wiring |
| Door Ajar Sensor | Switch Low | Ground when door open |
| Brake Pedal Switch | Switch High/Low | Safety critical |
| Park/Neutral Switch | Switch Low | Ground when engaged |
| Wheel Speed Sensor | Frequency/RPM | Hall effect |
| Engine Speed | RPM | Pulses per revolution |
| Flex Fuel Sensor | Flex Fuel | GM-type sensor |
| Oil Level Switch | Switch Low | Ground when low |

## Styling

```css
Table {
  background: #000000;
  gridline-color: #333333;
}

Header {
  background: #2D2D2D;
  font-weight: bold;
}

Row.logical-on {
  background: #325032;
}

Row.unconfigured {
  background: #3C3C3C;
  color: #808080;
}
```

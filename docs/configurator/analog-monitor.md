# Analog Monitor

The Analog Monitor displays real-time values from all 20 analog input channels. Access via the monitor tabs or press **F11**.

## Table Layout

| Pin | Name | Value | Vltg | Pu/pd |
|-----|------|-------|------|-------|
| A1 | Fuel Level | 75.2% | 2.48V | Pd |
| A2 | Oil Pressure | 3.2 bar | 1.65V | - |
| A3 | Throttle | 23.5% | 0.78V | Pu |
| A4 | (unconfigured) | ? | 0.00V | - |

## Column Definitions

| Column | Width | Description |
|--------|-------|-------------|
| **Pin** | 50px | Analog pin identifier (A1-A20) |
| **Name** | 150px | User-assigned channel name |
| **Value** | 100px | Scaled/processed value |
| **Vltg** | 70px | Raw ADC voltage (0-3.3V) |
| **Pu/pd** | 50px | Pull-up/Pull-down config |

## ADC Specifications

| Parameter | Value |
|-----------|-------|
| Resolution | 12-bit (0-4095) |
| Reference Voltage | 3.3V |
| LSB Value | 0.000805V |
| Sample Rate | 1 kHz |
| Input Range | 0-3.3V (with scaling up to 5V) |

## Input Types

### Linear Scaling

Converts voltage range to value range:

```
Configuration:
  type: "linear"
  min_voltage: 0.5V
  max_voltage: 4.5V
  min_value: 0
  max_value: 100
  unit: "%"
  decimals: 1

Formula:
  value = min_value + (voltage - min_voltage) *
          (max_value - min_value) / (max_voltage - min_voltage)

Example:
  Voltage: 2.5V
  Value: 0 + (2.5 - 0.5) * (100 - 0) / (4.5 - 0.5) = 50.0%
```

### Switch (Active High)

Binary output with hysteresis:

```
Configuration:
  type: "switch_active_high"
  threshold_high: 2.5V  (turn ON above this)
  threshold_low: 2.0V   (turn OFF below this)

Behavior:
  - Output = 1 when voltage > threshold_high
  - Output = 0 when voltage < threshold_low
  - Hysteresis prevents oscillation
```

**Display**: Row turns green (#325032) when logically ON.

### Switch (Active Low)

Inverted logic:

```
Configuration:
  type: "switch_active_low"
  threshold_high: 2.5V
  threshold_low: 2.0V

Behavior:
  - Output = 0 when voltage > threshold_high
  - Output = 1 when voltage < threshold_low
```

### Calibrated (Lookup Table)

Interpolates from calibration points:

```
Configuration:
  type: "calibrated"
  calibration_points: [
    {voltage: 0.5, value: 0},
    {voltage: 1.5, value: 25},
    {voltage: 2.5, value: 50},
    {voltage: 3.5, value: 100}
  ]

Behavior:
  - Linear interpolation between points
  - Extrapolates to nearest point outside range
```

### Rotary Switch

Discrete position detection:

```
Configuration:
  type: "rotary"
  positions: 12

Display:
  Position 1, Position 2, ... Position 12
```

## Pull-Up/Pull-Down Configuration

| Display | Meaning | Use Case |
|---------|---------|----------|
| **Pu** | Pull-up resistor enabled | Switches to ground |
| **Pd** | Pull-down resistor enabled | Switches to power |
| **-** | No pull resistor | Voltage signals |

Internal pull resistors are typically 10kΩ.

## Value Display Formatting

| Type | Format | Example |
|------|--------|---------|
| Linear | Value with unit | `75.2%`, `3.2 bar` |
| Switch | ON / OFF | `ON`, `OFF` |
| Calibrated | Value with unit | `50.0 C` |
| Rotary | Percentage | `45%` |
| Unconfigured | Question mark | `?` |

Decimal places are configurable per channel (0-3).

## Row Colors

| Condition | Background | Text |
|-----------|------------|------|
| Normal (configured) | #000000 (Black) | White |
| Switch ON | #325032 (Dark Green) | White |
| Switch OFF | #000000 (Black) | White |
| Unconfigured | #3C3C3C (Gray) | #808080 (Dim) |

## Voltage Display

Raw ADC voltage always shown regardless of input type:

```
ADC Value: 2048 (12-bit)
Voltage: 2048 × 3.3V / 4095 = 1.65V
```

## Update Behavior

- **Refresh rate**: 100ms (10 Hz)
- **Data source**: Telemetry ADC array
- **Reference voltage**: From device (typically 3.3V)
- **Offline**: Shows "?" for values, "-.--V" for voltage

## Common Sensor Applications

| Sensor Type | Input Type | Typical Range |
|-------------|------------|---------------|
| Fuel Level Sender | Linear | 0-190Ω → 0-100% |
| Oil Pressure | Calibrated | 0-10 bar |
| Coolant Temp | Calibrated (NTC) | -40 to 150°C |
| Throttle Position | Linear | 0.5-4.5V → 0-100% |
| MAP Sensor | Linear | 0-5V → 0-300 kPa |
| Lambda/O2 | Linear | 0-1V → 0.7-1.3 λ |
| Brake Pressure | Calibrated | 0-200 bar |

## Wiring Examples

### Resistive Sender (Fuel Level)
```
        PMU-30
         ___
Sender -|A1 |--- Pull-up to 5V (internal or external)
        |   |
GND ----|GND|
        |___|

Configuration:
  Pull: Pu (pull-up)
  Type: Linear or Calibrated
```

### Voltage Signal (TPS)
```
        PMU-30
         ___
Signal -|A1 |
        |   |
GND ----|GND|
        |___|

Configuration:
  Pull: - (none)
  Type: Linear (0.5-4.5V → 0-100%)
```

### NTC Temperature Sensor
```
        PMU-30
         ___
NTC ----|A1 |--- Pull-up to 5V
        |   |
GND ----|GND|
        |___|

Configuration:
  Pull: Pu (pull-up)
  Type: Calibrated (with temperature curve)
```

## Double-Click Action

Double-clicking a row opens the Analog Input Configuration dialog.

## Styling

```css
Table {
  background: #000000;
  gridline-color: #333333;
  alternate-row: none;
}

Header {
  background: #2D2D2D;
  font-weight: bold;
}

Cell.unconfigured {
  color: #808080;
  background: #3C3C3C;
}

Cell.switch-on {
  background: #325032;
}
```

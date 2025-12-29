# Output Monitor

The Output Monitor displays real-time status of all power output channels in a professional table format. Access via the second monitor tab or press **F10**.

## Table Layout

| Pin | Name | Status | V | Load | Curr | Peak | Vltg | Trip |
|-----|------|--------|---|------|------|------|------|------|
| O1 | Headlights | ON | 13.8 | 100% | 8.5A | 12.2A | 13.8 | |
| O2 | Tail Lights | PWM | 13.8 | 50% | 1.2A | 2.1A | 6.9 | |
| O3 | Horn | OFF | 13.8 | 0% | 0.0A | 15.0A | 0.0 | |
| O4 | Fuel Pump | OC | 13.8 | 100% | 42.0A | 42.0A | 0.0 | :warning: |

## Column Definitions

| Column | Width | Description |
|--------|-------|-------------|
| **Pin** | 60px | Output pin identifier (O1-O40) |
| **Name** | 150px | User-assigned channel name |
| **Status** | 60px | Current output state |
| **V** | 50px | Battery voltage |
| **Load** | 60px | Duty cycle percentage |
| **Curr** | 70px | Current draw |
| **Peak** | 70px | Peak current since reset |
| **Vltg** | 60px | Output voltage |
| **Trip** | 40px | Warning indicator |

## Pin Display

### Single Pin Outputs
```
O1, O2, O3, ...O40
```

### Merged Multi-Pin Outputs
When multiple pins are combined for higher current:
```
O1-O3    (3 pins merged)
O5,O6    (2 pins merged)
```

Secondary pins are hidden from the table to avoid redundancy.

## Status Values

| Status | Description | Row Color |
|--------|-------------|-----------|
| **OFF** | Output disabled | Black (#000000) |
| **ON** | Active at 100% duty | Dark Green (#325032) |
| **PWM** | Pulse-width modulated | Dark Blue (#003250) |
| **OC** | Overcurrent fault | Dark Red (#503028) |
| **OT** | Overtemperature fault | Dark Red (#503028) |
| **SC** | Short circuit detected | Dark Red (#503028) |
| **OL** | Open load (no load) | Dark Orange (#643C00) |
| **DIS** | Disabled by protection | Gray (#3C3C3C) |
| **-** | Unconfigured channel | Gray (#3C3C3C) |

## Current Display

Current values are displayed intelligently:

| Range | Format | Example |
|-------|--------|---------|
| < 1A | milliamps | 850mA |
| >= 1A | amps with decimals | 8.50A |
| >= 10A | amps with 1 decimal | 12.5A |
| >= 100A | amps integer | 125A |

## Voltage Calculation

Output voltage depends on state:

| State | Output Voltage |
|-------|----------------|
| OFF | 0.0V |
| ON | Battery voltage |
| PWM | Battery voltage x duty cycle |
| Fault | 0.0V |

Example: Battery = 13.8V, Duty = 50%
- Output voltage = 13.8 x 0.50 = 6.9V

## Peak Current Tracking

- **Peak** column shows maximum current since last reset
- Useful for detecting transient overcurrent events
- **Reset Peaks** button clears all peak values

## Trip Warning Indicator

The Trip column shows :warning: when:
- Overcurrent condition detected
- Overtemperature warning
- Short circuit protection activated
- Open load detection (optional)

## Toolbar

| Button | Action |
|--------|--------|
| **Reset Peaks** | Clear all peak current values |

## Row Colors

### Configured Channels

| Condition | Background | Text |
|-----------|------------|------|
| OFF state | #000000 (Black) | White |
| ON state | #325032 (Dark Green) | White |
| PWM state | #003250 (Dark Blue) | White |
| Any fault | #503028 (Dark Red) | White |

### Unconfigured Channels

| Element | Color |
|---------|-------|
| Background | #3C3C3C (Gray) |
| Text | #808080 (Dim Gray) |
| All values | "-" (dash) |

## Update Behavior

- **Refresh rate**: 100ms (10 Hz)
- **Data source**: Telemetry channel states, duties, currents
- **Offline**: Shows last values with gray background

## Current Limits

Each PROFET channel has built-in protection:

| Limit | Threshold | Action |
|-------|-----------|--------|
| Overcurrent | 42A (105% of 40A) | OC state, retry after cooldown |
| Short Circuit | 80A | SC state, immediate shutdown |
| Overtemperature | 145C | OT state, thermal shutdown |
| Open Load | < 50mA when ON | OL state (warning only) |

## Multi-Pin Merging Display

When outputs are merged for higher current capacity:

```
Configuration:
  Output: "High Power Load"
  Pins: [1, 2, 3]  // O1, O2, O3 merged

Display:
  Pin     Name              Curr    Peak
  O1-O3   High Power Load   45.0A   52.3A
  (O2 and O3 rows hidden)
```

Current shown is the sum of all merged pins.

## Double-Click Action

Double-clicking a row opens the Output Configuration dialog for that channel.

## Styling

```css
Table {
  background: #000000;
  gridline-color: #333333;
  font: 11px Sans-serif;
}

Header {
  background: #2D2D2D;
  color: #FFFFFF;
  font-weight: bold;
  padding: 4px;
}

Cell {
  padding: 2px 4px;
  border: none;
}
```

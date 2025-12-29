# PMU-30 Channel System

## Overview

The PMU-30 uses a unified channel architecture where everything is a "channel" - physical inputs, outputs, CAN signals, logic functions, timers, and more. Channels can reference each other, creating a powerful signal routing and processing system.

## Channel Classification

Channels are classified into three main categories based on their relationship to physical hardware:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PMU-30 Channel System                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐  │
│  │  PHYSICAL INPUTS    │  │  PHYSICAL OUTPUTS   │  │ VIRTUAL CHANNELS│  │
│  │                     │  │                     │  │                 │  │
│  │  • Digital Input    │  │  • Power Output     │  │ • Logic         │  │
│  │  • Analog Input     │  │  • H-Bridge         │  │ • Number/Math   │  │
│  │                     │  │                     │  │ • Timer         │  │
│  │  Bound to specific  │  │  Bound to specific  │  │ • Filter        │  │
│  │  input pins (0-19)  │  │  output pins (0-29) │  │ • Switch        │  │
│  │                     │  │                     │  │ • Table 2D/3D   │  │
│  │  Read real-world    │  │  Drive real-world   │  │ • CAN RX/TX     │  │
│  │  signals            │  │  loads              │  │ • PID           │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      SYSTEM CHANNELS (Read-Only)                  │  │
│  │                                                                   │  │
│  │  • pmu.batteryVoltage, pmu.totalCurrent, pmu.mcuTemperature      │  │
│  │  • pmu.o1.current, pmu.o1.status, pmu.a1.voltage                 │  │
│  │  • zero, one (constants)                                          │  │
│  │                                                                   │  │
│  │  Always available, no configuration needed                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Channel ID Ranges

| Range     | Type                | Description                        |
|-----------|---------------------|------------------------------------|
| 0-19      | Digital Inputs      | Hardware digital input states      |
| 0-99      | Physical Inputs     | All physical input channels        |
| 100-199   | Physical Outputs    | Power output channels              |
| 200-999   | User/Virtual        | User-defined virtual channels      |
| 1000-1099 | System Channels     | PMU system values                  |
| 1100-1129 | Output Status       | pmu.o1.status - pmu.o30.status     |
| 1130-1159 | Output Current      | pmu.o1.current - pmu.o30.current   |
| 1160-1189 | Output Voltage      | pmu.o1.voltage - pmu.o30.voltage   |
| 1190-1219 | Output Active       | pmu.o1.active - pmu.o30.active     |
| 1220-1239 | Analog Voltage      | pmu.a1.voltage - pmu.a20.voltage   |
| 1250-1279 | Output Duty Cycle   | pmu.o1.dutyCycle - pmu.o30.dutyCycle|

## Physical Input Channels

Physical input channels read signals from the real world through dedicated hardware pins.

### Digital Input (`digital_input`)

Reads digital HIGH/LOW states from switch inputs, buttons, or digital sensors.

**Hardware Resources:**
- 20 digital input pins (0-19)
- Each pin supports voltage measurement (0-30V range)
- Configurable threshold voltage for HIGH/LOW detection
- Internal pull-up resistors available

**Key Behaviors:**
- **Debouncing**: Filters mechanical switch bounce (configurable 0-10000ms)
- **Polarity**: Active-low or active-high operation
- **Edge Detection**: Can trigger on rising, falling, or both edges
- **Frequency Modes**: Can measure frequency, RPM, or duty cycle

**Example - Ignition Switch:**
```json
{
  "channel_id": 1,
  "channel_name": "Ignition",
  "channel_type": "digital_input",
  "input_pin": 0,
  "subtype": "switch_active_low",
  "enable_pullup": true,
  "debounce_ms": 50,
  "threshold_voltage": 6.0
}
```

**Example - RPM Input:**
```json
{
  "channel_id": 2,
  "channel_name": "Engine RPM",
  "channel_type": "digital_input",
  "input_pin": 3,
  "subtype": "rpm",
  "number_of_teeth": 60,
  "multiplier": 1,
  "divider": 1
}
```

### Analog Input (`analog_input`)

Reads continuous voltage values and converts them to engineering units.

**Hardware Resources:**
- 20 dedicated analog input pins (A1-A20)
- 12-bit ADC resolution (0-4095)
- Voltage range: 0-5V (typical), 0-30V with external divider
- Configurable pull-up/pull-down resistors

---

#### Analog Input Subtypes

| Subtype | Value | Description | Output Type |
|---------|-------|-------------|-------------|
| `switch_active_low` | 0 | Voltage threshold → digital output | Boolean (0/1) |
| `switch_active_high` | 1 | Voltage threshold → digital output | Boolean (0/1) |
| `rotary_switch` | 2 | Multi-position switch detector | Integer (0-N) |
| `linear` | 3 | Linear voltage-to-value scaling | Float |
| `calibrated` | 4 | Multi-point calibration curve | Float |

---

#### Subtype: Switch (Active Low / Active High)

Converts analog voltage to a digital on/off signal using configurable thresholds with hysteresis and debounce.

**How it works:**
- **Active High**: Output = 1 when voltage > high threshold
- **Active Low**: Output = 1 when voltage < low threshold (inverted logic)
- Hysteresis between high/low thresholds prevents oscillation
- Time-based debounce filters noise

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `threshold_high` | float | 2.5 | Upper threshold voltage (V) |
| `threshold_high_time_ms` | int | 50 | Time above threshold before switching ON |
| `threshold_low` | float | 1.5 | Lower threshold voltage (V) |
| `threshold_low_time_ms` | int | 50 | Time below threshold before switching OFF |

**Example - Button on Analog Pin:**
```json
{
  "channel_id": 21,
  "channel_name": "Start Button",
  "channel_type": "analog_input",
  "subtype": "switch_active_high",
  "input_pin": 0,
  "pullup_option": "10k_up",
  "threshold_high": 3.5,
  "threshold_high_time_ms": 20,
  "threshold_low": 1.5,
  "threshold_low_time_ms": 20
}
```

---

#### Subtype: Rotary Switch

Detects multi-position rotary switches using voltage divider networks.

**How it works:**
- Divides voltage range into N equal zones
- Each zone maps to a position number (0 to N-1)
- Debounce prevents false transitions during switching

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `positions` | int | 4 | Number of switch positions (2-12) |
| `debounce_ms` | int | 50 | Debounce time in milliseconds |

**Example - 6-Position Mode Selector:**
```json
{
  "channel_id": 22,
  "channel_name": "Drive Mode",
  "channel_type": "analog_input",
  "subtype": "rotary_switch",
  "input_pin": 3,
  "pullup_option": "10k_up",
  "positions": 6,
  "debounce_ms": 100
}
```

**Voltage Zones (example for 6 positions on 5V):**
| Position | Voltage Range |
|----------|---------------|
| 0 | 0.00V - 0.83V |
| 1 | 0.83V - 1.67V |
| 2 | 1.67V - 2.50V |
| 3 | 2.50V - 3.33V |
| 4 | 3.33V - 4.17V |
| 5 | 4.17V - 5.00V |

---

#### Subtype: Linear

Maps voltage linearly to engineering units. Most common for analog sensors.

**How it works:**
```
                    (voltage - min_voltage)
output = min_value + ────────────────────────── × (max_value - min_value)
                    (max_voltage - min_voltage)
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_voltage` | float | 0.0 | Voltage at minimum value (V) |
| `max_voltage` | float | 5.0 | Voltage at maximum value (V) |
| `min_value` | float | 0 | Output at min_voltage |
| `max_value` | float | 100 | Output at max_voltage |
| `decimal_places` | int | 0 | Display precision (0-6) |

**Example - Oil Pressure Sensor (0.5-4.5V = 0-10 bar):**
```json
{
  "channel_id": 23,
  "channel_name": "Oil Pressure",
  "channel_type": "analog_input",
  "subtype": "linear",
  "input_pin": 4,
  "pullup_option": "none",
  "min_voltage": 0.5,
  "max_voltage": 4.5,
  "min_value": 0,
  "max_value": 100,
  "decimal_places": 1,
  "quantity": "Pressure",
  "unit": "bar"
}
```

**Example - Fuel Level Sender (240Ω empty, 33Ω full with 10K pullup):**
```json
{
  "channel_id": 24,
  "channel_name": "Fuel Level",
  "channel_type": "analog_input",
  "subtype": "linear",
  "input_pin": 5,
  "pullup_option": "10k_up",
  "min_voltage": 0.65,
  "max_voltage": 3.3,
  "min_value": 0,
  "max_value": 100,
  "decimal_places": 0,
  "quantity": "Percentage",
  "unit": "%"
}
```

---

#### Subtype: Calibrated

Uses a multi-point lookup table for non-linear sensors like thermistors.

**How it works:**
- Define up to 16 voltage-value pairs
- Firmware interpolates between points
- Best for NTC thermistors, custom sensors

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `calibration_points` | array | Array of {voltage, value} pairs |
| `decimal_places` | int | Display precision (0-6) |

**Example - NTC Thermistor (Coolant Temperature):**
```json
{
  "channel_id": 25,
  "channel_name": "Coolant Temp",
  "channel_type": "analog_input",
  "subtype": "calibrated",
  "input_pin": 6,
  "pullup_option": "10k_up",
  "decimal_places": 0,
  "quantity": "Temperature",
  "unit": "°C",
  "calibration_points": [
    {"voltage": 0.25, "value": 120},
    {"voltage": 0.50, "value": 100},
    {"voltage": 1.00, "value": 80},
    {"voltage": 1.50, "value": 60},
    {"voltage": 2.00, "value": 40},
    {"voltage": 2.50, "value": 25},
    {"voltage": 3.00, "value": 10},
    {"voltage": 3.50, "value": 0},
    {"voltage": 4.00, "value": -10},
    {"voltage": 4.50, "value": -20}
  ]
}
```

---

#### Pullup/Pulldown Options

Configure internal resistors for proper sensor biasing.

| Option | Value | Description | Use Case |
|--------|-------|-------------|----------|
| `1m_down` | Default | 1MΩ to GND | General purpose, high impedance |
| `none` | - | No internal resistor | Voltage output sensors (0.5-4.5V) |
| `10k_up` | 10kΩ to VCC | Pull-up to 5V | NTC thermistors, variable resistors |
| `10k_down` | 10kΩ to GND | Pull-down | Switches to VCC |
| `100k_up` | 100kΩ to VCC | Weak pull-up | High impedance sensors |
| `100k_down` | 100kΩ to GND | Weak pull-down | High impedance sensors |

**Choosing the right pullup:**
- **Voltage output sensors** (0.5-4.5V): Use `none`
- **NTC thermistors**: Use `10k_up` (matches most automotive thermistors)
- **Resistive fuel senders**: Use `10k_up` or match sender resistance range
- **Switches to ground**: Use `10k_up`
- **Switches to VCC**: Use `10k_down`

---

#### Quantity and Unit System

The PMU-30 uses a comprehensive quantity/unit system for display purposes. Values are stored as integers internally, with `decimal_places` determining precision.

**Available Quantities:**

| Quantity | Default Unit | Available Units |
|----------|--------------|-----------------|
| User | user | user |
| Voltage | V | V, mV, kV |
| Current | A | A, mA, kA |
| Temperature | °C | °C, °F, K |
| Pressure | kPa | kPa, Pa, bar, mbar, psi, atm, mmHg, inHg |
| Percentage | % | %, ‰ |
| Angular velocity | rpm | rpm, krpm, rps, °/s |
| Velocity | km/h | km/h, m/s, mph, kn |
| Frequency | Hz | Hz, kHz, MHz, rpm |
| Time | s | s, ms, µs, min, h |
| Distance | m | m, km, cm, mm, mi, in, ft, yd |
| Mass | kg | kg, g, mg, lb, oz |
| Force | N | N, kN, lbf, kgf |
| Power | W | W, kW, HP, PS |
| Energy | J | J, kJ, Wh, kWh, cal |
| Resistance | Ω | Ω, kΩ, MΩ |
| Angle | ° | °, rad |
| Air fuel ratio | AFR | AFR, λ |
| Lambda | λ | λ, AFR |
| Volume | L | L, mL, m³, gal, qt |
| Volume flow rate | L/min | L/min, L/h, mL/min, gal/h |
| Mass flow rate | kg/h | kg/h, g/s, lb/h |

**Example with Quantity/Unit:**
```json
{
  "channel_id": 26,
  "channel_name": "Boost Pressure",
  "channel_type": "analog_input",
  "subtype": "linear",
  "input_pin": 7,
  "min_voltage": 0.5,
  "max_voltage": 4.5,
  "min_value": 0,
  "max_value": 300,
  "decimal_places": 1,
  "quantity": "Pressure",
  "unit": "kPa"
}
```

## Physical Output Channels

Physical output channels drive real-world loads through power switches.

### Power Output (`power_output`)

Controls high-side PROFET switches with protection features.

**Hardware Resources:**
- 30 output pins (organized in PROFET ICs)
- Current sensing on each output
- Overcurrent/short-circuit protection
- Over-temperature protection

**Key Behaviors:**
- **Source-Controlled**: ON/OFF driven by another channel
- **PWM**: Supports pulse-width modulation (1-20000 Hz)
- **Soft Start**: Gradual ramp-up to reduce inrush current
- **Protection**: Auto-retry on fault with configurable limits

**Example - Headlights with Soft Start (PWM ramp-up):**
```json
{
  "channel_id": 100,
  "channel_name": "Headlights",
  "channel_type": "power_output",
  "output_pins": [0, 1],
  "source_channel_id": 200,
  "pwm_enabled": true,
  "pwm_frequency_hz": 1000,
  "soft_start_ms": 500,
  "current_limit_a": 15.0,
  "inrush_current_a": 25.0,
  "inrush_time_ms": 100,
  "retry_count": 3
}
```

> **Note:** `soft_start_ms` requires `pwm_enabled: true`. It ramps the duty cycle from 0% to 100% over the specified time to reduce inrush current on capacitive/inductive loads.

**Example - LED Bar with PWM Dimming:**
```json
{
  "channel_id": 101,
  "channel_name": "LED Bar",
  "channel_type": "power_output",
  "output_pins": [5],
  "source_channel_id": 200,
  "pwm_enabled": true,
  "pwm_frequency_hz": 500,
  "duty_channel_id": 201,
  "current_limit_a": 10.0
}
```

> **Note:** Channel references use integer IDs (`source_channel_id`, `duty_channel_id`), not string names. Use channel_id 0 for "none".

### H-Bridge (`hbridge`)

Controls DC motors with bidirectional operation.

**Hardware Resources:**
- 4 H-Bridge channels
- Current sensing per bridge
- PWM frequency up to 25kHz
- Stall detection

**Key Behaviors:**
- **Direction Control**: Forward, reverse, brake, coast
- **Speed Control**: PWM duty cycle (0-100%)
- **Position Control**: PID-based positioning
- **Protection**: Overcurrent and stall detection

**Example - Power Window Motor:**
```json
{
  "channel_id": 130,
  "channel_name": "Window Motor",
  "channel_type": "hbridge",
  "bridge_number": 0,
  "source_channel_id": 200,
  "direction_source_channel_id": 201,
  "pwm_source_channel_id": 202,
  "pwm_frequency": 20000,
  "current_limit_a": 20.0
}
```

> **Note:** All channel references use integer IDs (e.g., `source_channel_id`, `direction_source_channel_id`). Use 0 for "none".

## Virtual Channels

Virtual channels exist only in software - they have no direct hardware binding but can reference any other channel as input.

### Logic (`logic`)

Boolean operations on input channels.

**Key Behaviors:**
- **Output**: Always 0 (false) or 1 (true)
- **Delay**: Can delay state transitions
- **Edge Detection**: Can trigger on state changes
- **Latch**: Can remember states (SR latch, toggle)

**Operations:**

| Operation | Inputs | Description |
|-----------|--------|-------------|
| `is_true` | 1 | Output true if input != 0 |
| `is_false` | 1 | Output true if input == 0 |
| `equal` | 1 | Input == Constant |
| `greater` | 1 | Input > Constant |
| `in_range` | 1 | Lower <= Input <= Upper |
| `and` | 2 | Input1 AND Input2 |
| `or` | 2 | Input1 OR Input2 |
| `xor` | 2 | Input1 XOR Input2 |
| `edge_rising` | 1 | Pulse on 0→1 transition |
| `toggle` | 1 | Toggle on rising edge |
| `set_reset_latch` | 2 | SR latch |
| `flash` | 1 | Blink when input true |

**Example - Brake Light Logic:**
```json
{
  "channel_id": 200,
  "channel_name": "Brake Active",
  "channel_type": "logic",
  "operation": "or",
  "input_channel_id": 10,
  "input_channel_2_id": 11,
  "false_delay_s": 0.5
}
```

### Number/Math (`number`)

Mathematical operations on numeric values.

**Key Behaviors:**
- **Output**: Floating-point numeric value
- **Multiple Inputs**: Up to 8 input channels
- **Clamping**: Can limit output range

**Operations:**

| Operation | Inputs | Description |
|-----------|--------|-------------|
| `constant` | 0 | Fixed value output |
| `add` | 2+ | Sum of inputs |
| `subtract` | 2 | Input1 - Input2 |
| `multiply` | 2+ | Product of inputs |
| `divide` | 2 | Input1 / Input2 |
| `min` | 2+ | Minimum of inputs |
| `max` | 2+ | Maximum of inputs |
| `average` | 2+ | Mean of inputs |
| `abs` | 1 | Absolute value |
| `clamp` | 1 | Limit to min/max range |
| `conditional` | 3 | If input1 then input2 else input3 |

**Example - Average Temperature:**
```json
{
  "channel_id": 400,
  "channel_name": "Avg Temp",
  "channel_type": "number",
  "operation": "average",
  "input_ids": [25, 27, 28],
  "decimal_places": 1
}
```

### Timer (`timer`)

Time measurement and countdown functions.

**Key Behaviors:**
- **Count Up**: Measure elapsed time
- **Count Down**: Countdown from limit
- **Start/Stop Control**: Controlled by input channels
- **Limits**: Maximum time in hours:minutes:seconds

**Example - Engine Runtime:**
```json
{
  "channel_id": 401,
  "channel_name": "Engine Runtime",
  "channel_type": "timer",
  "start_channel_id": 201,
  "start_edge": "rising",
  "mode": "count_up"
}
```

### Filter (`filter`)

Signal smoothing and noise reduction.

**Filter Types:**
- `moving_avg` - Moving average filter
- `low_pass` - First-order low-pass filter
- `min_window` - Minimum over window
- `max_window` - Maximum over window
- `median` - Median filter

**Example - Smoothed Oil Pressure:**
```json
{
  "channel_id": 402,
  "channel_name": "Oil Pressure Smooth",
  "channel_type": "filter",
  "filter_type": "moving_avg",
  "input_channel_id": 23,
  "window_size": 10
}
```

### Switch (`switch`)

Multi-state selector controlled by up/down inputs.

**Example - Wiper Speed Selector:**
```json
{
  "channel_id": 403,
  "channel_name": "Wiper Mode",
  "channel_type": "switch",
  "switch_type": "latching",
  "input_up_channel_id": 15,
  "input_down_channel_id": 16,
  "state_first": 0,
  "state_last": 3,
  "state_default": 0
}
```

### Table 2D/3D (`table_2d`, `table_3d`)

Lookup tables for non-linear mappings.

**Example - Boost Target Map:**
```json
{
  "channel_id": 404,
  "channel_name": "Boost Target",
  "channel_type": "table_3d",
  "x_axis_channel_id": 300,
  "y_axis_channel_id": 301,
  "interpolation": "linear",
  "x_values": [1000, 2000, 3000, 4000, 5000],
  "y_values": [0, 25, 50, 75, 100],
  "data": [
    [5, 8, 10, 12, 14],
    [6, 10, 14, 16, 18],
    [8, 14, 18, 20, 22],
    [10, 16, 20, 22, 24],
    [12, 18, 22, 24, 26]
  ]
}
```

### CAN Channels (`can_rx`, `can_tx`)

Interface with CAN bus for data exchange.

**CAN RX** - Receive values from CAN messages:
```json
{
  "channel_id": 300,
  "channel_name": "Vehicle Speed",
  "channel_type": "can_rx",
  "message_ref": "ECU_Data",
  "data_format": "16bit",
  "byte_offset": 0,
  "multiplier": 1,
  "divider": 100
}
```

**CAN TX** - Transmit values on CAN bus:
```json
{
  "channel_id": 500,
  "channel_name": "PMU Status",
  "channel_type": "can_tx",
  "can_bus": 1,
  "message_id": 768,
  "cycle_time_ms": 100,
  "signals": [
    {"source_channel_id": 1000, "start_bit": 0, "bit_length": 16}
  ]
}
```

## System Channels

System channels are predefined, read-only channels that provide access to PMU internal values. They are always available without configuration.

### PMU Core Channels (1000-1019)

| ID   | Name                   | Description                    | Unit   |
|------|------------------------|--------------------------------|--------|
| 1000 | `pmu.batteryVoltage`   | Main battery voltage           | mV     |
| 1001 | `pmu.totalCurrent`     | Total current draw             | mA     |
| 1002 | `pmu.mcuTemperature`   | MCU die temperature            | °C     |
| 1003 | `pmu.boardTemperatureL`| Left board temperature         | °C     |
| 1004 | `pmu.boardTemperatureR`| Right board temperature        | °C     |
| 1005 | `pmu.boardTemperatureMax` | Maximum board temperature   | °C     |
| 1006 | `pmu.uptime`           | Time since power-on            | seconds|
| 1007 | `pmu.status`           | System status flags            | bitmask|
| 1008 | `pmu.userError`        | User error code                | code   |
| 1009 | `pmu.5VOutput`         | 5V regulator output            | mV     |
| 1010 | `pmu.3V3Output`        | 3.3V regulator output          | mV     |
| 1011 | `pmu.isTurningOff`     | Shutdown in progress           | 0/1    |
| 1012 | `zero`                 | Constant value 0               | -      |
| 1013 | `one`                  | Constant value 1               | -      |

### RTC Channels (1020-1027)

| ID   | Name              | Description                    |
|------|-------------------|--------------------------------|
| 1020 | `pmu.rtc.time`    | Time as HHMMSS                 |
| 1021 | `pmu.rtc.date`    | Date as YYYYMMDD               |
| 1022 | `pmu.rtc.hour`    | Current hour (0-23)            |
| 1023 | `pmu.rtc.minute`  | Current minute (0-59)          |
| 1024 | `pmu.rtc.second`  | Current second (0-59)          |
| 1025 | `pmu.rtc.day`     | Day of month (1-31)            |
| 1026 | `pmu.rtc.month`   | Month (1-12)                   |
| 1027 | `pmu.rtc.year`    | Year (4-digit)                 |

### Output Sub-Channels

Each power output (1-30) has sub-channels for monitoring:

| Pattern             | Description                       | Unit   |
|---------------------|-----------------------------------|--------|
| `pmu.o{n}.status`   | Output state (OFF/ON/FAULT)       | enum   |
| `pmu.o{n}.current`  | Measured output current           | mA     |
| `pmu.o{n}.voltage`  | Output voltage                    | mV     |
| `pmu.o{n}.active`   | Output is conducting              | 0/1    |
| `pmu.o{n}.dutyCycle`| PWM duty cycle                    | 0-1000 |

Example: `pmu.o1.current` = current through output 1

### Analog Sub-Channels

Each analog input (1-20) provides a voltage sub-channel:

| Pattern             | Description                       | Unit   |
|---------------------|-----------------------------------|--------|
| `pmu.a{n}.voltage`  | Raw ADC voltage                   | mV     |

Example: `pmu.a5.voltage` = voltage on analog input 5

### Digital Sub-Channels

Each digital input (1-20) provides a state sub-channel:

| Pattern             | Description                       | Value  |
|---------------------|-----------------------------------|--------|
| `pmu.d{n}.state`    | Digital input state               | 0/1    |

Example: `pmu.d3.state` = state of digital input 3

### Using System Channels

System channels can be referenced like any other channel:

```json
{
  "channel_id": 201,
  "channel_name": "Low Voltage Warning",
  "channel_type": "logic",
  "operation": "less",
  "input_channel_id": 1000,
  "constant": 11500
}
```

> **Note:** System channels are referenced by their numeric ID. `pmu.batteryVoltage` = ID 1000.

```json
{
  "channel_id": 405,
  "channel_name": "Output Current Table",
  "channel_type": "table_2d",
  "x_axis_channel_id": 1130,
  "data": [
    {"x": 0, "y": 0},
    {"x": 5000, "y": 50},
    {"x": 10000, "y": 100}
  ]
}
```

## Channel Execution Order

The firmware processes channels in a specific order each control cycle:

1. **Physical Inputs** - Read ADC values and digital states
2. **CAN RX** - Process received CAN messages
3. **Virtual Channels** - Evaluate in dependency order:
   - Logic, Math, Timers, Filters, Switches, Tables
4. **Physical Outputs** - Update output states
5. **CAN TX** - Transmit CAN messages

## Channel ID Assignment

Every channel has the following identifiers:
- **`channel_id`** (integer, required) - Numeric ID used by firmware for fast lookups
- **`channel_name`** (string, optional) - Human-readable name for display in UI

### Channel ID Ranges

The firmware reserves specific numeric ID ranges for different channel types:

| Range | Category | Description |
|-------|----------|-------------|
| 0-19 | Digital Inputs | Hardware digital input pins (pmu.d1...pmu.d20) |
| 0-99 | Physical Inputs | All physical input channels |
| 100-199 | Physical Outputs | Power output channels (PROFET) |
| **200-999** | **User Channels** | User-defined virtual channels |
| 1000-1099 | System Channels | PMU core values (voltage, temp, etc.) |
| 1100-1129 | Output Status | pmu.o1.status ... pmu.o30.status |
| 1130-1159 | Output Current | pmu.o1.current ... pmu.o30.current |
| 1160-1189 | Output Voltage | pmu.o1.voltage ... pmu.o30.voltage |
| 1190-1219 | Output Active | pmu.o1.active ... pmu.o30.active |
| 1220-1239 | Analog Voltage | pmu.a1.voltage ... pmu.a20.voltage |
| 1250-1279 | Output Duty | pmu.o1.dutyCycle ... pmu.o30.dutyCycle |

### Automatic ID Assignment

When you create a new channel in the Configurator, the `channel_id` is automatically assigned:

```python
from models.channel_display_service import ChannelIdGenerator

# Get existing channels
existing = config_manager.get_all_channels()

# Get next available ID (scans for gaps)
next_id = ChannelIdGenerator.get_next_channel_id(existing)
# Returns: 200 (first user channel), or next unused ID
```

The generator:
1. Collects all `channel_id` values from existing channels
2. Scans range 200-999 for the first unused ID
3. Returns the next available ID

### ID Assignment Flow

```
┌─────────────────┐     ┌───────────────────────┐     ┌─────────────────┐
│  User creates   │     │  ChannelIdGenerator   │     │   Config JSON   │
│  new channel    │────►│  finds next free ID   │────►│   saved with    │
│  in dialog      │     │  in range 200-999     │     │   channel_id    │
└─────────────────┘     └───────────────────────┘     └─────────────────┘
                                   │
                                   ▼
                        ┌───────────────────────┐
                        │  Existing channels:   │
                        │  200, 201, 202, 204   │
                        │                       │
                        │  Next free: 203       │
                        └───────────────────────┘
```

### Manual ID Assignment

You can specify `channel_id` manually in the JSON:

```json
{
  "channel_id": 3,
  "channel_name": "Ignition",
  "channel_type": "digital_input",
  "input_pin": 0
}
```

**Note:** Manual IDs must be:
- In the appropriate range for the channel type
- Not already in use
- Unique within the configuration

### Channel ID and Name

| Aspect | `channel_id` (integer) | `channel_name` (string) |
|--------|------------------------|-------------------------|
| Required | Yes | No (optional) |
| Used in | Firmware runtime, JSON config | UI display |
| Format | `250` | `"Ignition Switch"` |
| Lookup speed | O(1) array index | N/A |
| References | All channel references | Display only |

### ID Resolution at Startup

When configuration is loaded, the firmware:

1. Parses all channel definitions
2. Uses numeric `channel_id` directly for lookups
3. Resolves all channel references (e.g., `source_channel_id: 200`)
4. Builds channel lookup table indexed by `channel_id`

```
Config:                              Runtime:
┌─────────────────────────┐         ┌─────────────────────────┐
│ "source_channel_id":    │  ──►    │ source_channel_id: 200  │
│   200                   │         │                         │
│ "channel_id": 100       │         │ channels[100] = {...}   │
└─────────────────────────┘         └─────────────────────────┘
```

## Channel References

Channels reference each other by numeric `channel_id`:

```json
{
  "source_channel_id": 200,
  "channel_id": 10,
  "input_ids": [5, 6, 7]
}
```

**Important:** All channel references in JSON configuration use integer IDs:
- `input_channel_id`, `input_channel_2_id` - Logic inputs
- `source_channel_id` - Output activation source
- `duty_channel_id` - PWM duty source
- `input_ids` - Array of input channel IDs
- Use `0` for "none" (no channel linked)

The configurator UI shows human-readable names, but stores integer IDs in the JSON configuration.

## Units and Quantities

Channels can specify a **quantity** (physical measurement type) and **unit** for proper display formatting.

### Available Quantities

| Quantity | Units | Default |
|----------|-------|---------|
| User | user | user |
| Acceleration | m/s², g, ft/s² | m/s² |
| Angle | °, rad | ° |
| Angular velocity | rpm, krpm, rps, °/s | rpm |
| Current | A, mA, kA | A |
| Distance | m, km, cm, mm, mi, in, ft | m |
| Frequency | Hz, kHz, MHz | Hz |
| Mass | kg, g, mg, lb, oz | kg |
| Mass flow rate | kg/h, g/s, lb/h | kg/h |
| Percentage | %, ‰ | % |
| Power | W, kW, HP, PS | W |
| Pressure | kPa, Pa, bar, mbar, psi, atm | kPa |
| Resistance | Ω, kΩ, MΩ | Ω |
| Temperature | °C, °F, K | °C |
| Time | s, ms, µs, min, h | s |
| Velocity | km/h, m/s, mph, kn | km/h |
| Voltage | V, mV, kV | V |
| Volume | L, mL, m³, gal | L |
| Volume flow rate | L/min, L/h, mL/min | L/min |

### Specifying Units in Configuration

```json
{
  "channel_id": 27,
  "channel_name": "Oil Pressure",
  "channel_type": "analog_input",
  "input_pin": 5,
  "quantity": "Pressure",
  "unit": "psi",
  "decimal_places": 1,
  "min_voltage": 0.5,
  "max_voltage": 4.5,
  "min_value": 0,
  "max_value": 100
}
```

## Decimal Places and Integer Values

### Internal Representation

**All channel values are stored as 32-bit signed integers (`int32_t`) in the firmware**, not floats. The `decimal_places` property specifies how many decimal places of precision are encoded in the integer:

| decimal_places | Stored Value | Display Value | Scale Factor |
|----------------|--------------|---------------|--------------|
| 0 | 1234 | 1234 | 1 |
| 1 | 1234 | 123.4 | 10 |
| 2 | 1234 | 12.34 | 100 |
| 3 | 1234 | 1.234 | 1000 |

### Conversion Formulas

**Float to Integer (Configurator → Firmware):**
```
int_value = round(float_value × 10^decimal_places)
```

**Integer to Float (Firmware → Display):**
```
float_value = int_value / 10^decimal_places
```

### Example

An oil pressure sensor configured with `decimal_places: 1`:

```
User enters:     75.3 psi
Stored as:       753 (integer)
Displayed as:    75.3 psi

Calculation:     75.3 × 10¹ = 753
Reverse:         753 / 10¹ = 75.3
```

### Why Integers?

The firmware uses fixed-point integer arithmetic instead of floating-point for several reasons:

1. **Deterministic timing** - Integer operations have consistent execution time
2. **CAN bus compatibility** - CAN data is natively integer-based
3. **Memory efficiency** - int32_t uses less RAM than double
4. **Precision control** - Known precision prevents rounding surprises
5. **ECUMaster compatibility** - Matches industry standard conventions

### Range Limits

| decimal_places | Min Value | Max Value | Precision |
|----------------|-----------|-----------|-----------|
| 0 | -2,147,483,648 | 2,147,483,647 | 1 |
| 1 | -214,748,364.8 | 214,748,364.7 | 0.1 |
| 2 | -21,474,836.48 | 21,474,836.47 | 0.01 |
| 3 | -2,147,483.648 | 2,147,483.647 | 0.001 |

### Channel Type Defaults

| Channel Type | Default decimal_places | Typical Use |
|--------------|------------------------|-------------|
| digital_input | 0 | Boolean (0/1) |
| analog_input | 1-2 | Sensor readings |
| can_rx | Varies | Depends on source |
| number | 0-2 | Calculations |
| timer | 0 | Seconds elapsed |
| filter | Same as input | Signal smoothing |

### Telemetry Encoding

When telemetry is transmitted, integer values are sent directly. The Configurator applies `decimal_places` to format the display:

```
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│    Firmware       │    │    Protocol       │    │   Configurator    │
│                   │    │                   │    │                   │
│  value = 753      │───►│  [0xF1, 0x02]     │───►│  753 / 10 = 75.3  │
│  (int32)          │    │  (little-endian)  │    │  display: "75.3"  │
└───────────────────┘    └───────────────────┘    └───────────────────┘
```

### CAN TX Encoding

For CAN transmission, values are scaled using `multiplier`:

```json
{
  "channel_id": 501,
  "channel_name": "ECU Pressure Out",
  "channel_type": "can_tx",
  "signals": [{
    "source_channel_id": 5,
    "start_bit": 0,
    "bit_length": 16,
    "multiplier": 10
  }]
}
```

The multiplier converts the channel value to the CAN signal scale:
```
CAN value = channel_value × multiplier
753 × 10 = 7530 (sent as 0x1D6A)
```

### Best Practices for Decimal Places

1. **Match sensor resolution** - Don't use more precision than your sensor provides
2. **Consider CAN compatibility** - Use same scaling as other ECUs on the bus
3. **Keep it simple** - decimal_places of 0-2 covers most use cases
4. **Document units** - Always specify quantity/unit alongside decimal_places

## Best Practices

1. **Use descriptive names**: `Fuel Pump Relay` not `Output 1`
2. **Group related channels**: Use naming conventions like `Wiper *`, `Lights *`
3. **Document with descriptions**: Add `description` field for complex logic
4. **Use filters for noisy signals**: Apply moving average to analog sensors
5. **Protect outputs**: Set appropriate current limits and retry counts
6. **Monitor with system channels**: Use `pmu.o*.current` for diagnostics
7. **Avoid circular dependencies**: Logic channels cannot reference themselves

## See Also

- [Configuration Schema](configuration_schema.md) - JSON configuration format
- [Telemetry](telemetry.md) - Real-time channel monitoring
- [Protocol Specification](protocol_specification.md) - Communication protocol

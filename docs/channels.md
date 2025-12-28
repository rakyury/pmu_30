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
  "id": "ignition",
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
  "id": "engine_rpm",
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
- 20 analog input pins (0-19, shared with digital inputs)
- 12-bit ADC resolution (0-4095)
- Voltage range: 0-5V (typical), 0-30V with divider
- Configurable pull-up/pull-down resistors

**Key Behaviors:**
- **Scaling**: Linear voltage-to-value mapping
- **Calibration**: Multi-point calibration curves
- **Rotary Switch**: Auto-detects multi-position switches
- **Threshold**: Can output digital states based on voltage thresholds

**Example - Oil Pressure Sensor:**
```json
{
  "id": "oil_pressure",
  "channel_type": "analog_input",
  "input_pin": 4,
  "subtype": "linear",
  "min_voltage": 0.5,
  "max_voltage": 4.5,
  "min_value": 0,
  "max_value": 100,
  "decimal_places": 1
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

**Example - Headlights with Soft Start:**
```json
{
  "id": "headlights",
  "channel_type": "power_output",
  "output_pins": [0, 1],
  "source_channel": "lights_switch",
  "pwm_enabled": false,
  "soft_start_ms": 500,
  "current_limit_a": 15.0,
  "inrush_current_a": 25.0,
  "inrush_time_ms": 100,
  "retry_count": 3
}
```

**Example - LED Bar with PWM Dimming:**
```json
{
  "id": "led_bar",
  "channel_type": "power_output",
  "output_pins": [5],
  "source_channel": "lights_on",
  "pwm_enabled": true,
  "pwm_frequency_hz": 500,
  "duty_channel": "dimmer_level",
  "current_limit_a": 10.0
}
```

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
  "id": "window_motor",
  "channel_type": "hbridge",
  "bridge_number": 0,
  "source_channel": "window_enable",
  "direction_channel": "window_direction",
  "duty_channel": "window_speed",
  "pwm_frequency_hz": 20000,
  "current_limit_a": 20.0
}
```

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
  "id": "brake_active",
  "channel_type": "logic",
  "operation": "or",
  "channel": "brake_pedal",
  "channel_2": "ebrake_switch",
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
  "id": "avg_temp",
  "channel_type": "number",
  "operation": "average",
  "inputs": ["temp_1", "temp_2", "temp_3"],
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
  "id": "engine_runtime",
  "channel_type": "timer",
  "start_channel": "engine_running",
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
  "id": "oil_pressure_smooth",
  "channel_type": "filter",
  "filter_type": "moving_avg",
  "input_channel": "oil_pressure_raw",
  "window_size": 10
}
```

### Switch (`switch`)

Multi-state selector controlled by up/down inputs.

**Example - Wiper Speed Selector:**
```json
{
  "id": "wiper_mode",
  "channel_type": "switch",
  "switch_type": "latching",
  "input_up_channel": "wiper_up_btn",
  "input_down_channel": "wiper_down_btn",
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
  "id": "boost_target",
  "channel_type": "table_3d",
  "x_axis_channel": "rpm",
  "y_axis_channel": "tps",
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
  "id": "vehicle_speed",
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
  "id": "pmu_status",
  "channel_type": "can_tx",
  "can_bus": 1,
  "message_id": 768,
  "cycle_time_ms": 100,
  "signals": [
    {"source_channel": "battery_voltage", "start_bit": 0, "bit_length": 16}
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
  "id": "low_voltage_warning",
  "channel_type": "logic",
  "operation": "less",
  "channel": "pmu.batteryVoltage",
  "constant": 11500
}
```

```json
{
  "id": "output_current_table",
  "channel_type": "table_2d",
  "x_axis_channel": "pmu.o1.current",
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

## Channel References

Channels reference each other by their `id` (string) or `channel_id` (numeric):

```json
{
  "source_channel": "ignition_switch",
  "channel": "brake_pedal",
  "inputs": ["temp_1", "temp_2", "temp_3"]
}
```

At runtime, string IDs are resolved to numeric channel IDs for efficient processing.

## Best Practices

1. **Use descriptive IDs**: `fuel_pump_relay` not `output_1`
2. **Group related channels**: Use naming conventions like `wiper_*`, `lights_*`
3. **Document with descriptions**: Add `description` field for complex logic
4. **Use filters for noisy signals**: Apply moving average to analog sensors
5. **Protect outputs**: Set appropriate current limits and retry counts
6. **Monitor with system channels**: Use `pmu.o*.current` for diagnostics
7. **Avoid circular dependencies**: Logic channels cannot reference themselves

## See Also

- [Configuration Schema](configuration_schema.md) - JSON configuration format
- [Telemetry](telemetry.md) - Real-time channel monitoring
- [Protocol Specification](protocol_specification.md) - Communication protocol

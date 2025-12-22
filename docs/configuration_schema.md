# PMU-30 Configuration Schema

## Overview

The PMU-30 configuration is stored as JSON and defines the behavior of all outputs, inputs, logic functions, and communication settings.

## Root Structure

```json
{
  "version": 1,
  "device": {...},
  "outputs": [...],
  "inputs": [...],
  "virtual_inputs": [...],
  "hbridges": [...],
  "logic_functions": [...],
  "can_bus": [...],
  "can_frames": [...],
  "safety": {...}
}
```

## Device Settings

```json
{
  "device": {
    "name": "My PMU-30",
    "undervoltage_threshold": 10.0,
    "overvoltage_threshold": 16.0,
    "overtemp_threshold": 85,
    "startup_delay_ms": 500,
    "watchdog_enabled": true,
    "watchdog_timeout_ms": 1000
  }
}
```

| Field                   | Type    | Range      | Description                    |
|-------------------------|---------|------------|--------------------------------|
| name                    | string  | 1-32 chars | Device display name            |
| undervoltage_threshold  | float   | 6.0-12.0   | Low voltage cutoff (V)         |
| overvoltage_threshold   | float   | 14.0-18.0  | High voltage cutoff (V)        |
| overtemp_threshold      | int     | 60-100     | Temperature limit (°C)         |
| startup_delay_ms        | int     | 0-5000     | Power-on delay (ms)            |
| watchdog_enabled        | bool    | -          | Enable hardware watchdog       |
| watchdog_timeout_ms     | int     | 100-5000   | Watchdog timeout (ms)          |

## Outputs (30 channels)

```json
{
  "outputs": [
    {
      "channel": 0,
      "name": "headlights",
      "enabled": true,
      "type": "switch",
      "profet_type": "BTS7008-2EPA",
      "current_limit": 15.0,
      "inrush_time_ms": 100,
      "retry_count": 3,
      "retry_delay_ms": 1000,
      "soft_start": false,
      "soft_start_time_ms": 0,
      "pwm_frequency": 100,
      "default_state": "off",
      "invert": false,
      "input_source": -1,
      "logic_source": -1,
      "can_source": null
    }
  ]
}
```

| Field             | Type   | Range        | Description                      |
|-------------------|--------|--------------|----------------------------------|
| channel           | int    | 0-29         | Physical channel index           |
| name              | string | 1-32 chars   | Output name (alphanumeric + _)   |
| enabled           | bool   | -            | Channel enabled                  |
| type              | enum   | see below    | Output type                      |
| profet_type       | string | see below    | PROFET IC type                   |
| current_limit     | float  | 0.1-40.0     | Overcurrent threshold (A)        |
| inrush_time_ms    | int    | 0-10000      | Inrush ignore period (ms)        |
| retry_count       | int    | 0-10         | Auto-retry attempts              |
| retry_delay_ms    | int    | 100-60000    | Delay between retries (ms)       |
| soft_start        | bool   | -            | Enable soft start PWM            |
| soft_start_time_ms| int    | 0-5000       | Soft start ramp time (ms)        |
| pwm_frequency     | int    | 50-20000     | PWM frequency (Hz)               |
| default_state     | enum   | off/on/last  | State on power-up                |
| invert            | bool   | -            | Invert output logic              |
| input_source      | int    | -1 to 19     | Direct input binding (-1=none)   |
| logic_source      | int    | -1 to 63     | Logic function binding (-1=none) |
| can_source        | object | null/object  | CAN signal binding               |

### Output Types

| Type      | Description                           |
|-----------|---------------------------------------|
| switch    | Simple on/off output                  |
| pwm       | PWM-controlled output                 |
| flasher   | Flashing output (configurable rate)   |
| strobe    | Strobe pattern output                 |
| momentary | Pulse output (configurable duration)  |

### PROFET Types

| Type           | Max Current | Features                |
|----------------|-------------|-------------------------|
| BTS7002-1EPA   | 21A         | Single channel          |
| BTS7004-1EPA   | 15A         | Single channel          |
| BTS7006-1EPA   | 12.5A       | Single channel          |
| BTS7008-2EPA   | 11A×2       | Dual channel            |
| BTS50015-1TAD  | 5A          | Diagnostic              |

## Inputs (20 channels)

```json
{
  "inputs": [
    {
      "channel": 0,
      "name": "ignition",
      "enabled": true,
      "type": "digital",
      "pull": "none",
      "debounce_ms": 50,
      "threshold_low": 2.0,
      "threshold_high": 3.0,
      "invert": false
    }
  ]
}
```

| Field          | Type   | Range      | Description                    |
|----------------|--------|------------|--------------------------------|
| channel        | int    | 0-19       | Physical input index           |
| name           | string | 1-32 chars | Input name                     |
| enabled        | bool   | -          | Input enabled                  |
| type           | enum   | see below  | Input type                     |
| pull           | enum   | none/up/down| Internal pull resistor        |
| debounce_ms    | int    | 0-1000     | Debounce time (ms)             |
| threshold_low  | float  | 0.0-5.0    | Low threshold for analog (V)   |
| threshold_high | float  | 0.0-5.0    | High threshold for analog (V)  |
| invert         | bool   | -          | Invert input logic             |

### Input Types

| Type     | Description                              |
|----------|------------------------------------------|
| digital  | Digital input (high/low)                 |
| analog   | Analog input (0-5V)                      |
| frequency| Frequency counter input                  |
| pwm_in   | PWM input (duty cycle measurement)       |
| resistive| Resistive sensor input                   |

## Virtual Inputs (32 channels)

Virtual inputs are software-defined signals that can be controlled via CAN or logic functions.

```json
{
  "virtual_inputs": [
    {
      "channel": 0,
      "name": "horn_button",
      "enabled": true,
      "default_state": false,
      "persist": false
    }
  ]
}
```

## H-Bridges (4 channels)

```json
{
  "hbridges": [
    {
      "channel": 0,
      "name": "window_motor",
      "enabled": true,
      "type": "BTN8982TA",
      "current_limit": 25.0,
      "pwm_frequency": 20000,
      "deadtime_ns": 500,
      "auto_reverse_ms": 0,
      "stall_current": 20.0,
      "stall_action": "stop"
    }
  ]
}
```

| Field           | Type   | Range       | Description                    |
|-----------------|--------|-------------|--------------------------------|
| channel         | int    | 0-3         | H-bridge index                 |
| name            | string | 1-32 chars  | H-bridge name                  |
| enabled         | bool   | -           | H-bridge enabled               |
| type            | string | BTN8982TA   | Driver IC type                 |
| current_limit   | float  | 0.1-43.0    | Maximum current (A)            |
| pwm_frequency   | int    | 1000-25000  | PWM frequency (Hz)             |
| deadtime_ns     | int    | 0-5000      | Dead time (ns)                 |
| auto_reverse_ms | int    | 0-60000     | Auto-reverse timeout (0=off)   |
| stall_current   | float  | 0.0-43.0    | Stall detection threshold (A)  |
| stall_action    | enum   | stop/reverse| Action on stall detection      |

## Logic Functions (64 slots)

```json
{
  "logic_functions": [
    {
      "slot": 0,
      "name": "brake_light_logic",
      "enabled": true,
      "function_type": "or",
      "inputs": [
        {"type": "input", "index": 5},
        {"type": "virtual", "index": 10}
      ],
      "parameters": {},
      "output_invert": false
    }
  ]
}
```

### Function Types

| Type           | Description                                    |
|----------------|------------------------------------------------|
| and            | Logical AND of all inputs                      |
| or             | Logical OR of all inputs                       |
| not            | Logical NOT of first input                     |
| xor            | Logical XOR of two inputs                      |
| nand           | Logical NAND                                   |
| nor            | Logical NOR                                    |
| sr_latch       | Set-Reset latch                                |
| d_latch        | D-type latch                                   |
| toggle         | Toggle on rising edge                          |
| one_shot       | Single pulse on trigger                        |
| delay_on       | Delayed turn-on                                |
| delay_off      | Delayed turn-off                               |
| timer          | Periodic timer                                 |
| pwm_gen        | PWM generator                                  |
| flasher        | Flasher with configurable rate                 |
| alternating    | Alternating flasher                            |
| sequencer      | Sequential pattern                             |
| comparator     | Analog comparator                              |
| threshold      | Threshold with hysteresis                      |
| counter        | Up/down counter                                |
| selector       | Input selector/multiplexer                     |
| priority       | Priority encoder                               |
| interlock      | Mutual exclusion                               |
| conditional    | If-then-else logic                             |
| wiper          | Wiper control (park/intermittent/continuous)   |
| turn_signal    | Turn signal with lane change                   |

### Logic Input Sources

```json
{
  "inputs": [
    {"type": "input", "index": 0},
    {"type": "virtual", "index": 5},
    {"type": "logic", "index": 10},
    {"type": "output", "index": 3},
    {"type": "can", "frame_id": "0x100", "signal": "speed"},
    {"type": "constant", "value": true},
    {"type": "analog", "index": 2}
  ]
}
```

## CAN Bus Configuration

```json
{
  "can_bus": [
    {
      "bus": 0,
      "enabled": true,
      "bitrate": 500000,
      "fd_enabled": true,
      "fd_bitrate": 2000000,
      "termination": true,
      "silent": false
    }
  ]
}
```

| Field       | Type  | Range                 | Description              |
|-------------|-------|-----------------------|--------------------------|
| bus         | int   | 0-3                   | CAN bus index            |
| enabled     | bool  | -                     | Bus enabled              |
| bitrate     | int   | 10000-1000000         | Arbitration bitrate      |
| fd_enabled  | bool  | -                     | Enable CAN FD            |
| fd_bitrate  | int   | 500000-8000000        | CAN FD data bitrate      |
| termination | bool  | -                     | Enable 120Ω termination  |
| silent      | bool  | -                     | Listen-only mode         |

## CAN Frames

```json
{
  "can_frames": [
    {
      "id": "tx_status",
      "can_id": "0x300",
      "bus": 0,
      "direction": "tx",
      "dlc": 8,
      "cycle_time_ms": 100,
      "signals": [
        {
          "name": "voltage",
          "start_bit": 0,
          "length": 16,
          "byte_order": "little",
          "value_type": "unsigned",
          "scale": 0.01,
          "offset": 0,
          "source": {"type": "system", "signal": "input_voltage"}
        }
      ]
    }
  ]
}
```

## Safety Settings

```json
{
  "safety": {
    "emergency_stop_input": 0,
    "emergency_stop_action": "all_off",
    "max_total_current": 100.0,
    "overcurrent_action": "limit",
    "thermal_derating_start": 70,
    "thermal_derating_full": 90,
    "fault_log_enabled": true,
    "fault_log_size": 100
  }
}
```

## Validation Rules

1. **Output names**: Must be unique, alphanumeric + underscore, 1-32 chars
2. **Input references**: Must point to valid, enabled inputs
3. **Logic references**: No circular dependencies allowed
4. **Current limits**: Sum of enabled outputs ≤ 100A total
5. **CAN IDs**: Must be unique per bus for TX frames
6. **PWM frequencies**: Must be within PROFET/driver limits

## Example Configuration

```json
{
  "version": 1,
  "device": {
    "name": "Race Car PMU",
    "undervoltage_threshold": 11.0,
    "overvoltage_threshold": 15.5,
    "overtemp_threshold": 80
  },
  "outputs": [
    {
      "channel": 0,
      "name": "fuel_pump",
      "enabled": true,
      "type": "switch",
      "current_limit": 10.0,
      "input_source": 0
    },
    {
      "channel": 1,
      "name": "headlights",
      "enabled": true,
      "type": "switch",
      "current_limit": 15.0,
      "logic_source": 0
    }
  ],
  "inputs": [
    {
      "channel": 0,
      "name": "ignition",
      "enabled": true,
      "type": "digital",
      "debounce_ms": 50
    }
  ],
  "logic_functions": [
    {
      "slot": 0,
      "name": "lights_on",
      "function_type": "and",
      "inputs": [
        {"type": "input", "index": 0},
        {"type": "virtual", "index": 0}
      ]
    }
  ]
}
```

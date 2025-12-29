# PMU-30 Configuration Schema v3.0

## Overview

The PMU-30 configuration is stored as JSON and defines the behavior of all channels - inputs, outputs, CAN, logic functions, and more. Version 3.0 uses a unified channel architecture where all channel types share a common structure.

## Root Structure

```json
{
  "version": "3.0",
  "device": {...},
  "can_messages": [...],
  "channels": [...],
  "system": {...},
  "standard_can_stream": {...}
}
```

| Field              | Required | Type   | Description                         |
|--------------------|----------|--------|-------------------------------------|
| version            | Yes      | string | Schema version (e.g., "3.0")        |
| device             | Yes      | object | Device identification and settings  |
| can_messages       | No       | array  | CAN message definitions (Level 1)   |
| channels           | Yes      | array  | All channel configurations          |
| system             | No       | object | System-wide settings                |
| standard_can_stream| No       | object | Standard CAN stream configuration   |

## Device Settings

```json
{
  "device": {
    "name": "Race Car PMU",
    "serial_number": "PMU30-2024-001",
    "firmware_version": "1.0.0",
    "hardware_revision": "rev3",
    "created": "2024-01-15T10:30:00Z",
    "modified": "2024-12-29T14:45:00Z"
  }
}
```

| Field             | Required | Type   | Description                        |
|-------------------|----------|--------|------------------------------------|
| name              | Yes      | string | Device display name (1-32 chars)   |
| serial_number     | No       | string | Device serial number               |
| firmware_version  | No       | string | Firmware version string            |
| hardware_revision | No       | string | Hardware revision identifier       |
| created           | No       | string | Configuration creation timestamp   |
| modified          | No       | string | Last modification timestamp        |

## Unified Channel Structure

All channels share a common base structure:

```json
{
  "channel_id": 42,
  "channel_type": "logic",
  "channel_name": "Brake Light Logic",
  "enabled": true,
  "description": "Controls brake lights based on brake pedal input"
}
```

| Field        | Required | Type    | Description                            |
|--------------|----------|---------|----------------------------------------|
| channel_id   | Yes      | integer | Unique numeric identifier (0-999)      |
| channel_type | Yes      | string  | Channel type (see below)               |
| channel_name | No       | string  | Human-readable display name            |
| enabled      | No       | boolean | Whether channel is active (default: true)|
| description  | No       | string  | User notes about this channel          |

### Channel ID Rules

- Must be a unique integer within the configuration (0-999)
- Auto-assigned by the Configurator when creating new channels
- Used for all inter-channel references (e.g., `source_channel_id`, `input_channel_id`)

## Channel Types

### Physical Input Channels

These channel types are bound to physical hardware pins.

#### Digital Input (`digital_input`)

```json
{
  "channel_id": 1,
  "channel_type": "digital_input",
  "channel_name": "Ignition Switch",
  "input_pin": 0,
  "subtype": "switch_active_low",
  "enable_pullup": true,
  "debounce_ms": 50,
  "threshold_voltage": 2.5,
  "trigger_edge": "rising"
}
```

| Field             | Type    | Description                              |
|-------------------|---------|------------------------------------------|
| input_pin         | integer | Physical pin number (0-19)               |
| subtype           | string  | Input behavior type                      |
| enable_pullup     | boolean | Enable internal pull-up resistor         |
| debounce_ms       | integer | Debounce time in milliseconds (0-10000)  |
| threshold_voltage | number  | Voltage threshold for high/low (V)       |
| trigger_edge      | string  | Edge detection: rising/falling/both      |

**Subtypes:**
- `switch_active_low` - Switch to ground (default high)
- `switch_active_high` - Switch to voltage (default low)
- `frequency` - Frequency counter input
- `rpm` - RPM measurement with teeth count
- `flex_fuel` - Flex fuel sensor input
- `beacon` - Beacon/strobe input
- `keypad_button` - Virtual button from CAN keypad

#### Analog Input (`analog_input`)

```json
{
  "channel_id": 2,
  "channel_type": "analog_input",
  "channel_name": "Oil Pressure",
  "input_pin": 4,
  "subtype": "linear",
  "pullup_option": "none",
  "min_voltage": 0.5,
  "max_voltage": 4.5,
  "min_value": 0,
  "max_value": 100,
  "decimal_places": 1
}
```

| Field            | Type    | Description                              |
|------------------|---------|------------------------------------------|
| input_pin        | integer | Physical pin number (0-19)               |
| subtype          | string  | Input processing type                    |
| pullup_option    | string  | Pull resistor configuration              |
| min_voltage      | number  | Minimum sensor voltage (V)               |
| max_voltage      | number  | Maximum sensor voltage (V)               |
| min_value        | number  | Output value at min voltage              |
| max_value        | number  | Output value at max voltage              |
| decimal_places   | integer | Display decimal places (0-6)             |
| calibration_points| array  | Multi-point calibration data             |

**Subtypes:**
- `linear` - Linear voltage-to-value mapping
- `calibrated` - Multi-point calibration curve
- `rotary_switch` - Multi-position rotary selector
- `switch_active_low/high` - Analog threshold switching

**Pull Options:** `none`, `1m_down`, `10k_up`, `10k_down`, `100k_up`, `100k_down`

### Physical Output Channels

#### Power Output (`power_output`)

```json
{
  "channel_id": 100,
  "channel_type": "power_output",
  "channel_name": "Headlights",
  "output_pins": [0, 1],
  "source_channel_id": 200,
  "pwm_enabled": false,
  "pwm_frequency_hz": 200,
  "duty_channel_id": 0,
  "duty_fixed": 100,
  "soft_start_ms": 200,
  "current_limit_a": 15.0,
  "inrush_current_a": 25.0,
  "inrush_time_ms": 100,
  "retry_count": 3,
  "retry_forever": false
}
```

| Field            | Type    | Description                              |
|------------------|---------|------------------------------------------|
| output_pins      | array   | Physical output pin(s) (max 3)           |
| source_channel_id| integer | Channel ID that controls ON/OFF state (0=none) |
| pwm_enabled      | boolean | Enable PWM output                        |
| pwm_frequency_hz | integer | PWM frequency (1-20000 Hz)               |
| duty_channel_id  | integer | Channel ID for variable duty cycle (0=none) |
| duty_fixed       | number  | Fixed duty cycle (0-100%)                |
| soft_start_ms    | integer | Soft start ramp time in ms               |
| current_limit_a  | number  | Overcurrent protection threshold (A)     |
| inrush_current_a | number  | Inrush current limit (A)                 |
| inrush_time_ms   | integer | Inrush protection time (ms)              |
| retry_count      | integer | Fault retry attempts                     |
| retry_forever    | boolean | Keep retrying indefinitely               |

#### H-Bridge (`hbridge`)

```json
{
  "channel_id": 101,
  "channel_type": "hbridge",
  "channel_name": "Window Motor",
  "bridge_number": 0,
  "source_channel_id": 200,
  "direction_source_channel_id": 201,
  "pwm_source_channel_id": 202,
  "mode": "direct",
  "pwm_frequency": 20000,
  "current_limit_a": 25.0
}
```

### Virtual Channels (No Physical Pins)

#### Logic (`logic`)

```json
{
  "channel_id": 200,
  "channel_type": "logic",
  "channel_name": "Brake Active",
  "operation": "or",
  "input_channel_id": 10,
  "input_channel_2_id": 11,
  "true_delay_s": 0,
  "false_delay_s": 0.5
}
```

**Operations:**
- **Basic:** `is_true`, `is_false`
- **Comparison:** `equal`, `not_equal`, `less`, `greater`, `less_equal`, `greater_equal`, `in_range`
- **Multi-input:** `and`, `or`, `xor`, `not`, `nand`, `nor`
- **Edge detection:** `edge_rising`, `edge_falling`
- **Advanced:** `changed`, `hysteresis`, `set_reset_latch`, `toggle`, `pulse`, `flash`

#### Number/Math (`number`)

```json
{
  "channel_id": 201,
  "channel_type": "number",
  "channel_name": "Average Temp",
  "operation": "average",
  "input_channel_ids": [3, 4, 5],
  "multiplier": 1.0,
  "offset": 0,
  "clamp_min": 0,
  "clamp_max": 150
}
```

**Operations:** `constant`, `add`, `subtract`, `multiply`, `divide`, `min`, `max`, `average`, `abs`, `scale`, `clamp`, `conditional`

#### Timer (`timer`)

```json
{
  "channel_id": 202,
  "channel_type": "timer",
  "channel_name": "Engine Runtime",
  "start_channel_id": 10,
  "start_edge": "rising",
  "stop_channel_id": 0,
  "stop_edge": "rising",
  "mode": "count_up",
  "limit_hours": 99,
  "limit_minutes": 59,
  "limit_seconds": 59
}
```

#### Filter (`filter`)

```json
{
  "channel_id": 203,
  "channel_type": "filter",
  "channel_name": "Oil Pressure Filtered",
  "filter_type": "moving_avg",
  "input_channel_id": 5,
  "window_size": 10
}
```

**Filter Types:** `moving_avg`, `low_pass`, `min_window`, `max_window`, `median`

#### Switch (`switch`)

```json
{
  "channel_id": 204,
  "channel_type": "switch",
  "channel_name": "Wiper Speed",
  "switch_type": "latching",
  "input_up_channel_id": 20,
  "input_up_edge": "rising",
  "input_down_channel_id": 21,
  "input_down_edge": "rising",
  "state_first": 0,
  "state_last": 3,
  "state_default": 0
}
```

#### 2D Table (`table_2d`)

```json
{
  "channel_id": 205,
  "channel_type": "table_2d",
  "channel_name": "Oil Temp Warning",
  "x_axis_channel_id": 8,
  "interpolation": "linear",
  "clamp_output": true,
  "data": [
    {"x": 80, "y": 0},
    {"x": 100, "y": 50},
    {"x": 120, "y": 100}
  ]
}
```

#### 3D Table (`table_3d`)

```json
{
  "channel_id": 206,
  "channel_type": "table_3d",
  "channel_name": "Boost Target",
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

### CAN Channels

#### CAN RX (`can_rx`)

```json
{
  "channel_id": 300,
  "channel_type": "can_rx",
  "channel_name": "Vehicle Speed",
  "message_ref": "ECU_Data_1",
  "frame_offset": 0,
  "data_type": "unsigned",
  "data_format": "16bit",
  "byte_order": "little_endian",
  "byte_offset": 2,
  "multiplier": 1.0,
  "divider": 100,
  "offset": 0,
  "decimal_places": 1,
  "default_value": 0,
  "timeout_behavior": "use_default"
}
```

| Field            | Type    | Description                              |
|------------------|---------|------------------------------------------|
| message_ref      | string  | Reference to can_messages[].id           |
| frame_offset     | integer | Frame index for compound messages (0-7)  |
| data_type        | string  | unsigned/signed/float                    |
| data_format      | string  | 8bit/16bit/32bit/custom                  |
| byte_order       | string  | little_endian/big_endian                 |
| byte_offset      | integer | Starting byte position (0-7)             |
| start_bit        | integer | For custom: starting bit (0-63)          |
| bit_length       | integer | For custom: number of bits (1-64)        |
| multiplier       | number  | Value multiplier                         |
| divider          | number  | Value divider (non-zero)                 |
| offset           | number  | Value offset                             |
| default_value    | number  | Value when timed out                     |
| timeout_behavior | string  | use_default/hold_last/set_zero           |

#### CAN TX (`can_tx`)

```json
{
  "channel_id": 400,
  "channel_type": "can_tx",
  "channel_name": "PMU Status",
  "can_bus": 1,
  "message_id": 768,
  "is_extended": false,
  "cycle_time_ms": 100,
  "signals": [
    {
      "name": "battery_voltage",
      "source_channel_id": 900,
      "start_bit": 0,
      "bit_length": 16,
      "multiplier": 100,
      "offset": 0
    }
  ]
}
```

## CAN Messages (Level 1)

CAN messages define the frame structure that CAN RX channels reference:

```json
{
  "can_messages": [
    {
      "id": "ECU_Data_1",
      "name": "Engine ECU Data Frame 1",
      "can_bus": 1,
      "base_id": 256,
      "is_extended": false,
      "message_type": "normal",
      "dlc": 8,
      "timeout_ms": 1000,
      "description": "Primary engine data"
    }
  ]
}
```

| Field        | Required | Type    | Description                        |
|--------------|----------|---------|-------------------------------------|
| id           | Yes      | string  | Unique message identifier           |
| name         | No       | string  | Human-readable name                 |
| can_bus      | Yes      | integer | CAN bus number (1-4)                |
| base_id      | Yes      | integer | Base CAN ID                         |
| is_extended  | No       | boolean | Extended (29-bit) ID                |
| message_type | No       | string  | normal/compound/pmu1_rx/pmu2_rx     |
| frame_count  | No       | integer | Number of frames for compound (1-8) |
| dlc          | No       | integer | Data length code (0-64)             |
| timeout_ms   | No       | integer | Message timeout (0-65535)           |

## System Settings

```json
{
  "system": {
    "control_frequency_hz": 1000,
    "logic_frequency_hz": 1000,
    "can1_baudrate": 500000,
    "can2_baudrate": 500000
  }
}
```

## Standard CAN Stream

```json
{
  "standard_can_stream": {
    "enabled": true,
    "can_bus": 1,
    "base_id": 1792,
    "is_extended": false,
    "include_extended_frames": true
  }
}
```

## Validation

The configuration is validated on load and before upload to device.

### Validation Rules

1. **Required Fields**: `version`, `device`, `device.name`, `channels`
2. **Channel IDs**:
   - Must be unique integers (0-999)
   - Auto-assigned by the Configurator
3. **Channel References**: All `*_channel_id` fields must point to existing channel IDs (or 0 for none)
4. **Pin Assignments**: Physical pins can only be used once
5. **CAN Message References**: `message_ref` must exist in `can_messages`
6. **Divider Values**: Cannot be zero
7. **Circular Dependencies**: Not allowed in logic/math chains

### ConfigValidator Usage

```python
from models.config_schema import ConfigValidator

# Validate full configuration
is_valid, errors = ConfigValidator.validate_config(config_dict)

if not is_valid:
    error_text = ConfigValidator.format_validation_errors(errors)
    print(error_text)

# Check for circular dependencies
cycles = ConfigValidator.detect_circular_dependencies(config_dict)
if cycles:
    print(f"Circular dependency found: {' -> '.join(cycles[0])}")
```

### Validation Errors

Common validation errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `Missing required field: 'version'` | No version in config | Add `"version": "3.0"` |
| `channel_id must be integer` | Non-integer channel_id | Use integer (0-999) |
| `references undefined channel_id: 42` | Invalid channel reference | Fix the reference or create the channel |
| `Duplicate channel_id: 5` | Same ID used twice | Make IDs unique |
| `divider cannot be zero` | CAN RX divider = 0 | Set divider to non-zero |

## Migration

### From v2.0 to v3.0

The system automatically migrates v2.0 configurations:
- Separate arrays merged into unified `channels` array
- String `id` fields converted to integer `channel_id`
- `name` field moved to `channel_name`
- `channel_id` auto-assigned if missing

### From v1.x

Migration from v1.x is not supported. Create a new configuration.

## Complete Example

```json
{
  "version": "3.0",
  "device": {
    "name": "Rally Car PMU",
    "serial_number": "RC-001"
  },
  "can_messages": [
    {
      "id": "ECU_Status",
      "can_bus": 1,
      "base_id": 256,
      "timeout_ms": 500
    }
  ],
  "channels": [
    {
      "channel_id": 1,
      "channel_type": "digital_input",
      "channel_name": "Ignition",
      "input_pin": 0,
      "subtype": "switch_active_low",
      "debounce_ms": 50
    },
    {
      "channel_id": 2,
      "channel_type": "can_rx",
      "channel_name": "RPM",
      "message_ref": "ECU_Status",
      "data_format": "16bit",
      "byte_offset": 0,
      "multiplier": 1,
      "divider": 1
    },
    {
      "channel_id": 3,
      "channel_type": "logic",
      "channel_name": "Engine Running",
      "operation": "greater",
      "input_channel_id": 2,
      "input_channel_2_id": 0,
      "constant": 500
    },
    {
      "channel_id": 100,
      "channel_type": "power_output",
      "channel_name": "Fuel Pump",
      "output_pins": [0],
      "source_channel_id": 3,
      "current_limit_a": 10.0
    }
  ],
  "system": {
    "control_frequency_hz": 1000,
    "can1_baudrate": 500000
  }
}
```

## See Also

- [Channel System](channels.md) - Detailed channel documentation
- [Protocol Specification](protocol_specification.md) - Communication protocol
- [Telemetry](telemetry.md) - Real-time data streaming
- [Device Reboot](device_reboot.md) - Restart and config reload

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
  "id": "unique_channel_id",
  "channel_type": "logic",
  "channel_name": "Brake Light Logic",
  "channel_id": 42,
  "enabled": true,
  "description": "Controls brake lights based on brake pedal input"
}
```

| Field        | Required | Type    | Description                            |
|--------------|----------|---------|----------------------------------------|
| id           | Yes      | string  | Unique identifier (letters, numbers, _)|
| channel_type | Yes      | string  | Channel type (see below)               |
| channel_name | No       | string  | Human-readable display name            |
| channel_id   | No       | integer | Numeric ID for protocol (0-999)        |
| enabled      | No       | boolean | Whether channel is active (default: true)|
| description  | No       | string  | User notes about this channel          |

### ID Naming Rules

- Must start with a letter (a-z, A-Z)
- Can contain letters, numbers, and underscores
- Maximum 32 characters
- Must be unique within the configuration
- Examples: `ignition_sw`, `Brake_Light_1`, `RPM_CAN_in`

## Channel Types

### Physical Input Channels

These channel types are bound to physical hardware pins.

#### Digital Input (`digital_input`)

```json
{
  "id": "ignition_switch",
  "channel_type": "digital_input",
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
  "id": "oil_pressure",
  "channel_type": "analog_input",
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
  "id": "headlights",
  "channel_type": "power_output",
  "output_pins": [0, 1],
  "source_channel": "lights_logic",
  "pwm_enabled": false,
  "pwm_frequency_hz": 200,
  "duty_channel": null,
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
| source_channel   | string  | Channel that controls ON/OFF state       |
| pwm_enabled      | boolean | Enable PWM output                        |
| pwm_frequency_hz | integer | PWM frequency (1-20000 Hz)               |
| duty_channel     | string  | Channel for variable duty cycle          |
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
  "id": "window_motor",
  "channel_type": "hbridge",
  "bridge_number": 0,
  "source_channel": "window_up",
  "direction_channel": "window_direction",
  "duty_channel": "window_speed",
  "mode": "direct",
  "pwm_frequency_hz": 20000,
  "current_limit_a": 25.0
}
```

### Virtual Channels (No Physical Pins)

#### Logic (`logic`)

```json
{
  "id": "brake_active",
  "channel_type": "logic",
  "operation": "or",
  "channel": "brake_pedal",
  "channel_2": "ebrake_switch",
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
  "id": "average_temp",
  "channel_type": "number",
  "operation": "average",
  "inputs": ["temp_1", "temp_2", "temp_3"],
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
  "id": "engine_runtime",
  "channel_type": "timer",
  "start_channel": "engine_running",
  "start_edge": "rising",
  "stop_channel": null,
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
  "id": "oil_pressure_filtered",
  "channel_type": "filter",
  "filter_type": "moving_avg",
  "input_channel": "oil_pressure_raw",
  "window_size": 10
}
```

**Filter Types:** `moving_avg`, `low_pass`, `min_window`, `max_window`, `median`

#### Switch (`switch`)

```json
{
  "id": "wiper_speed",
  "channel_type": "switch",
  "switch_type": "latching",
  "input_up_channel": "wiper_up_btn",
  "input_up_edge": "rising",
  "input_down_channel": "wiper_down_btn",
  "input_down_edge": "rising",
  "state_first": 0,
  "state_last": 3,
  "state_default": 0
}
```

#### 2D Table (`table_2d`)

```json
{
  "id": "oil_temp_warning",
  "channel_type": "table_2d",
  "x_axis_channel": "oil_temp",
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

### CAN Channels

#### CAN RX (`can_rx`)

```json
{
  "id": "vehicle_speed",
  "channel_type": "can_rx",
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
  "id": "pmu_status",
  "channel_type": "can_tx",
  "can_bus": 1,
  "message_id": 768,
  "is_extended": false,
  "cycle_time_ms": 100,
  "signals": [
    {
      "name": "battery_voltage",
      "source_channel": "system_voltage",
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
   - Must be unique
   - Must match pattern `^[a-zA-Z][a-zA-Z0-9_]*$`
   - Maximum 32 characters
3. **Channel References**: Must point to existing channel IDs
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
| `channel ID must start with a letter` | ID like `1_input` | Rename to `input_1` |
| `references undefined channel 'xyz'` | Invalid channel reference | Fix the reference or create the channel |
| `Duplicate channel ID: 'abc'` | Same ID used twice | Make IDs unique |
| `divider cannot be zero` | CAN RX divider = 0 | Set divider to non-zero |

## Migration

### From v2.0 to v3.0

The system automatically migrates v2.0 configurations:
- Separate arrays merged into unified `channels` array
- `name` field copied to `id` if missing
- `channel_id` auto-generated if missing

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
      "id": "ignition",
      "channel_type": "digital_input",
      "input_pin": 0,
      "subtype": "switch_active_low",
      "debounce_ms": 50
    },
    {
      "id": "rpm",
      "channel_type": "can_rx",
      "message_ref": "ECU_Status",
      "data_format": "16bit",
      "byte_offset": 0,
      "multiplier": 1,
      "divider": 1
    },
    {
      "id": "engine_running",
      "channel_type": "logic",
      "operation": "and",
      "channel": "ignition",
      "channel_2": "rpm",
      "constant": 500
    },
    {
      "id": "fuel_pump",
      "channel_type": "power_output",
      "output_pins": [0],
      "source_channel": "engine_running",
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

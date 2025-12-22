# JSON Configuration Validation

## Overview

PMU-30 Configurator implements comprehensive JSON configuration validation to ensure data integrity and provide clear error messages when configuration files are malformed or contain invalid data.

## JSON Format Version 2.0

PMU-30 uses a **unified channel architecture** where all I/O and logic elements are represented as channels in a single `channels` array.

### Basic Structure

```json
{
  "version": "2.0",
  "device": {
    "name": "PMU-30 Racing Controller",
    "serial_number": "PMU30-001",
    "firmware_version": "2.0.0"
  },
  "channels": [
    { "id": "...", "channel_type": "digital_input", ... },
    { "id": "...", "channel_type": "analog_input", ... },
    { "id": "...", "channel_type": "logic", ... },
    { "id": "...", "channel_type": "power_output", ... }
  ],
  "can_buses": [ ... ],
  "system": { ... }
}
```

## Features

### 1. Automatic Validation on Load
When loading a JSON configuration file, the system automatically validates:
- JSON syntax correctness
- Required fields presence
- Data types correctness
- Value ranges and constraints
- Duplicate channel ID detection
- Channel reference validation
- Circular dependency detection

### 2. Clear Error Messages
Instead of cryptic error codes, users receive human-readable error messages:

```
Configuration validation failed:

1. channels[0].channel_type: 'invalid_type' is not valid
2. channels[5].input_pin must be between 0 and 19
3. Duplicate channel ID: 'fuel_pump'
4. channels[10].source_channel: references undefined channel 'missing_channel'
```

### 3. JSON Syntax Errors
Invalid JSON syntax is detected and reported with line/column information:

```
Invalid JSON format in configuration file:

Line 15, Column 23:
Expecting ',' delimiter

Please check the file syntax.
```

## Validation Rules

### Required Fields
- `version`: Configuration version (string, format: "x.y", e.g., "2.0")
- `device`: Device information object
  - `name`: Device name (non-empty string)
- `channels`: Array of channel configurations

### Channel ID Requirements
- Must start with a letter (a-z, A-Z)
- Can contain letters, numbers, and underscores
- Must be unique across all channels
- Pattern: `^[a-zA-Z][a-zA-Z0-9_]*$`

### Channel Types
All channels must have a valid `channel_type`:

| Type | Description |
|------|-------------|
| `digital_input` | Digital input pins (switch, frequency, RPM) |
| `analog_input` | Analog input pins (voltage, calibrated sensors) |
| `power_output` | PROFET power outputs (up to 30 channels) |
| `logic` | Logic functions (AND, OR, comparisons, hysteresis) |
| `number` | Math operations (add, multiply, clamp, etc.) |
| `filter` | Signal filters (moving average, low-pass) |
| `timer` | Time counters (count up/down) |
| `table_2d` | 2D lookup tables with interpolation |
| `table_3d` | 3D lookup maps |
| `switch` | State machines (latching, press-hold) |
| `enum` | Enumeration definitions |
| `can_rx` | CAN receive signals |
| `can_tx` | CAN transmit messages |

## Channel Type Schemas

### Digital Input
```json
{
  "id": "di_ignition",
  "channel_type": "digital_input",
  "subtype": "switch_active_low",
  "input_pin": 0,
  "enable_pullup": true,
  "threshold_voltage": 2.5,
  "debounce_ms": 50
}
```

**Subtypes:** `switch_active_low`, `switch_active_high`, `frequency`, `rpm`, `flex_fuel`, `beacon`, `puls_oil_sensor`

**Fields:**
- `input_pin`: 0-7 (digital input pins)
- `enable_pullup`: boolean
- `threshold_voltage`: 0-30V
- `debounce_ms`: 0-10000ms

### Analog Input
```json
{
  "id": "ai_throttle",
  "channel_type": "analog_input",
  "subtype": "linear",
  "input_pin": 0,
  "pullup_option": "1m_down",
  "decimal_places": 1,
  "min_voltage": 0.5,
  "max_voltage": 4.5,
  "min_value": 0.0,
  "max_value": 100.0
}
```

**Subtypes:** `switch_active_low`, `switch_active_high`, `rotary_switch`, `linear`, `calibrated`

**Fields:**
- `input_pin`: 0-19 (analog input pins)
- `pullup_option`: `none`, `1m_down`, `10k_up`, `10k_down`, `100k_up`, `100k_down`
- `decimal_places`: 0-6
- For `calibrated` subtype, use `calibration_points` array

### Power Output
```json
{
  "id": "out_fuel_pump",
  "channel_type": "power_output",
  "output_pins": [0],
  "source_channel": "l_fuel_pump_latch",
  "pwm_enabled": false,
  "current_limit_a": 15.0,
  "inrush_current_a": 30.0,
  "inrush_time_ms": 200,
  "retry_count": 3
}
```

**Fields:**
- `output_pins`: Array of pin numbers (max 3 pins for parallel)
- `source_channel`: Reference to control channel
- `pwm_enabled`: Enable PWM mode
- `pwm_frequency_hz`: 1-20000 Hz
- `duty_channel` or `duty_fixed`: PWM duty source
- `current_limit_a`: Overcurrent protection threshold

### Logic
```json
{
  "id": "l_engine_running",
  "channel_type": "logic",
  "operation": "greater",
  "channel": "di_engine_rpm",
  "constant": 500,
  "true_delay_s": 0.5,
  "false_delay_s": 2.0
}
```

**Operations:**
- **Logical:** `and`, `or`, `not`, `xor`, `nand`, `nor`
- **Comparison:** `greater`, `less`, `equal`, `not_equal`, `greater_equal`, `less_equal`, `in_range`
- **Special:** `hysteresis`, `flash`, `pulse`, `toggle`, `set_reset_latch`

### Number
```json
{
  "id": "n_max_temp",
  "channel_type": "number",
  "operation": "max",
  "inputs": ["ai_coolant_temp", "ai_oil_temp"],
  "input_multipliers": ["*1", "*1"],
  "decimal_places": 1
}
```

**Operations:** `constant`, `add`, `subtract`, `multiply`, `divide`, `min`, `max`, `average`, `abs`, `scale`, `clamp`, `conditional`, `lookup3`

### Filter
```json
{
  "id": "flt_throttle_smooth",
  "channel_type": "filter",
  "filter_type": "moving_avg",
  "input_channel": "ai_throttle",
  "window_size": 10
}
```

**Filter types:** `moving_avg`, `low_pass`, `min_window`, `max_window`, `median`

### Timer
```json
{
  "id": "tm_engine_run_time",
  "channel_type": "timer",
  "start_channel": "l_engine_running",
  "start_edge": "rising",
  "mode": "count_up",
  "limit_hours": 999,
  "limit_minutes": 59,
  "limit_seconds": 59
}
```

### Table 2D
```json
{
  "id": "t2d_fan_pwm",
  "channel_type": "table_2d",
  "x_axis_channel": "ai_coolant_temp",
  "x_values": [70, 80, 90, 100, 110],
  "output_values": [0, 0, 50, 80, 100],
  "decimal_places": 0
}
```

### Switch
```json
{
  "id": "sw_driving_mode",
  "channel_type": "switch",
  "switch_type": "latching",
  "input_up_channel": "di_mode_btn",
  "input_up_edge": "rising",
  "state_first": 0,
  "state_last": 3,
  "state_default": 0
}
```

### Enum
```json
{
  "id": "e_gear",
  "channel_type": "enum",
  "is_bitfield": false,
  "items": [
    {"value": 0, "text": "N", "color": "#FFFFFF"},
    {"value": 1, "text": "1", "color": "#00FF00"},
    {"value": 2, "text": "2", "color": "#00FF00"}
  ]
}
```

### CAN RX
```json
{
  "id": "crx_ecu_rpm",
  "channel_type": "can_rx",
  "can_bus": 1,
  "message_id": 256,
  "is_extended": false,
  "start_bit": 0,
  "length": 16,
  "byte_order": "little_endian",
  "value_type": "unsigned",
  "factor": 1.0,
  "offset": 0.0,
  "timeout_ms": 500
}
```

### CAN TX
```json
{
  "id": "ctx_pmu_status",
  "channel_type": "can_tx",
  "can_bus": 1,
  "message_id": 768,
  "cycle_time_ms": 100,
  "signals": [
    {
      "source_channel": "ai_throttle",
      "start_bit": 0,
      "length": 8,
      "byte_order": "little_endian",
      "factor": 1.0,
      "offset": 0.0
    }
  ]
}
```

## Array Limits
- **Digital Inputs**: Maximum 8
- **Analog Inputs**: Maximum 20
- **Power Outputs**: Maximum 30
- **H-Bridges**: Maximum 4
- **Logic Functions**: Maximum 100
- **Tables**: Maximum 50
- **CAN Buses**: Maximum 4

## Usage in Code

### Loading Configuration with Validation

```python
from models.config_manager import ConfigManager

manager = ConfigManager()

# Load configuration with automatic validation
success, error_msg = manager.load_from_file("config.json")

if not success:
    print(f"Validation failed:\n{error_msg}")
else:
    print("Configuration loaded successfully")
```

### Manual Validation

```python
from models.config_schema import ConfigValidator

# Validate configuration dictionary
is_valid, errors = ConfigValidator.validate_config(config_dict)

if not is_valid:
    error_message = ConfigValidator.format_validation_errors(errors)
    print(error_message)

# Check for circular dependencies
cycles = ConfigValidator.detect_circular_dependencies(config_dict)
if cycles:
    print(f"Circular dependencies found: {cycles}")
```

## Error Handling in GUI

When user opens a configuration file through the GUI:

1. **File Not Found**: Shows error dialog with file path
2. **JSON Syntax Error**: Shows error with line/column information
3. **Validation Errors**: Shows formatted list of all validation issues
4. **Circular Dependencies**: Warns about channels that reference each other
5. **Success**: Loads configuration and displays it in project tree

## Testing

The validation system is covered by comprehensive unit tests:

```bash
# Run validation tests
python -m pytest tests/test_config_validation.py -v

# Run all tests
python -m pytest tests/ -v
```

**Test Coverage:**
- Valid configuration acceptance
- Missing required fields detection
- Invalid data types detection
- Out-of-range values detection
- Duplicate channel ID detection
- Invalid channel references detection
- Circular dependency detection
- JSON syntax error handling
- Data preservation on save/load

## Common Validation Errors

### Error: "Missing required field: 'version'"
**Cause**: Configuration file doesn't have version field
**Fix**: Add `"version": "2.0"` to root object

### Error: "channels[3].channel_type: 'gpio' is not valid"
**Cause**: Invalid channel type specified
**Fix**: Use one of the valid channel types listed above

### Error: "Duplicate channel ID: 'fuel_pump'"
**Cause**: Multiple channels have the same ID
**Fix**: Ensure each channel has a unique ID

### Error: "channels[5].source_channel: references undefined channel 'missing'"
**Cause**: Channel references another channel that doesn't exist
**Fix**: Create the missing channel or fix the reference

### Error: "channels[0].id: channel ID must start with a letter"
**Cause**: Channel ID doesn't follow naming rules
**Fix**: Use format like `di_ignition`, `out_fuel_pump`, `l_engine_running`

## Example Valid Configuration

```json
{
  "version": "2.0",
  "device": {
    "name": "PMU-30 Racing Controller",
    "serial_number": "PMU30-001",
    "firmware_version": "2.0.0"
  },
  "channels": [
    {
      "id": "di_ignition",
      "channel_type": "digital_input",
      "subtype": "switch_active_low",
      "input_pin": 0,
      "enable_pullup": true,
      "debounce_ms": 50
    },
    {
      "id": "ai_coolant_temp",
      "channel_type": "analog_input",
      "subtype": "calibrated",
      "input_pin": 2,
      "pullup_option": "10k_up",
      "calibration_points": [
        {"voltage": 0.5, "value": -40},
        {"voltage": 2.5, "value": 50},
        {"voltage": 4.5, "value": 120}
      ]
    },
    {
      "id": "l_engine_running",
      "channel_type": "logic",
      "operation": "greater",
      "channel": "crx_ecu_rpm",
      "constant": 500,
      "true_delay_s": 0.5
    },
    {
      "id": "l_fan_control",
      "channel_type": "logic",
      "operation": "hysteresis",
      "channel": "ai_coolant_temp",
      "polarity": "normal",
      "upper_value": 90,
      "lower_value": 80
    },
    {
      "id": "out_fuel_pump",
      "channel_type": "power_output",
      "output_pins": [0],
      "source_channel": "l_engine_running",
      "current_limit_a": 15.0,
      "inrush_current_a": 30.0,
      "inrush_time_ms": 200
    },
    {
      "id": "out_fan",
      "channel_type": "power_output",
      "output_pins": [2],
      "source_channel": "l_fan_control",
      "pwm_enabled": true,
      "pwm_frequency_hz": 100,
      "current_limit_a": 20.0
    }
  ],
  "can_buses": [
    {
      "bus": 1,
      "enabled": true,
      "bitrate": 500000,
      "fd_enabled": false
    }
  ],
  "system": {
    "update_rate_hz": 1000,
    "watchdog_timeout_ms": 100
  }
}
```

## Migration from v1.0

If you have v1.0 configuration files, they need to be converted to v2.0 format:

### Changes:
1. `"version": "1.0"` -> `"version": "2.0"`
2. Separate arrays (`inputs`, `outputs`, `logic_functions`, etc.) -> unified `channels` array
3. `channel` field (number) -> `id` field (string)
4. `type` field -> `channel_type` + `subtype` fields
5. `gpio_type` field -> `channel_type` field

### Example Migration:

**v1.0 (old):**
```json
{
  "version": "1.0",
  "inputs": [
    {"channel": 0, "name": "Throttle", "type": "Linear Analog", ...}
  ],
  "outputs": [
    {"channel": 0, "name": "Fuel Pump", ...}
  ]
}
```

**v2.0 (new):**
```json
{
  "version": "2.0",
  "channels": [
    {"id": "ai_throttle", "channel_type": "analog_input", "subtype": "linear", ...},
    {"id": "out_fuel_pump", "channel_type": "power_output", ...}
  ]
}
```

## Performance

Validation is performed efficiently:
- Average validation time: <10ms for typical configurations
- Circular dependency detection: O(n) complexity
- No external dependencies required
- Pure Python implementation
- Minimal memory overhead

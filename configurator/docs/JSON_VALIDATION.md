# JSON Configuration Validation

## Overview

PMU-30 Configurator implements comprehensive JSON configuration validation to ensure data integrity and provide clear error messages when configuration files are malformed or contain invalid data.

## Features

### 1. **Automatic Validation on Load**
When loading a JSON configuration file, the system automatically validates:
- JSON syntax correctness
- Required fields presence
- Data types correctness
- Value ranges and constraints
- Duplicate channel detection
- Array size limits

### 2. **Clear Error Messages**
Instead of cryptic error codes, users receive human-readable error messages:

```
Configuration validation failed:

1. inputs[0].type must be one of ['Switch Active Low', 'Switch Active High', ...]
2. outputs[5].channel must be between 0 and 29
3. Duplicate output channels: {0, 5}
```

### 3. **JSON Syntax Errors**
Invalid JSON syntax is detected and reported with line/column information:

```
Invalid JSON format in configuration file:

Line 15, Column 23:
Expecting ',' delimiter

Please check the file syntax.
```

## Validation Rules

### Required Fields
- `version`: Configuration version (string, format: "x.y")
- `device`: Device information object
  - `name`: Device name (non-empty string)
  - `serial_number`: Serial number (string)
- `inputs`: Array of input configurations (max 20)
- `outputs`: Array of output configurations (max 30)

### Input Configuration
```json
{
  "channel": 0,           // Required: 0-19
  "name": "Brake Pressure", // Required: non-empty string
  "type": "Calibrated Analog", // Required: valid type
  "pull_up": false,       // Optional: boolean
  "pull_down": false,     // Optional: boolean
  "filter_samples": 10,   // Optional: 1-100
  "parameters": {         // Optional: object
    "multiplier": 100.0,
    "offset": -50.0,
    "unit": "bar"
  }
}
```

**Valid Input Types:**
- Switch Active Low
- Switch Active High
- Rotary Switch
- Linear Analog
- Calibrated Analog
- Frequency Input

### Output Configuration
```json
{
  "channel": 5,           // Required: 0-29
  "name": "Fuel Pump",    // Required: non-empty string
  "enabled": true,        // Required: boolean
  "protection": {         // Optional: object
    "current_limit": 15.0,
    "inrush_current": 30.0,
    "inrush_time_ms": 500
  },
  "pwm": {                // Optional: object
    "enabled": true,
    "frequency": 1000,
    "default_duty": 75.0
  },
  "advanced": {}          // Optional: object
}
```

### Array Limits
- **Inputs**: Maximum 20
- **Outputs**: Maximum 30
- **H-Bridges**: Maximum 4
- **Logic Functions**: Maximum 100
- **Virtual Channels**: Maximum 256
- **CAN Buses**: Maximum 4

### Channel Uniqueness
- Input channels must be unique (0-19)
- Output channels must be unique (0-29)
- Duplicate channels will cause validation error

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
    # Format errors for display
    error_message = ConfigValidator.format_validation_errors(errors)
    print(error_message)
```

## Error Handling in GUI

When user opens a configuration file through the GUI:

1. **File Not Found**: Shows error dialog with file path
2. **JSON Syntax Error**: Shows error with line/column information
3. **Validation Errors**: Shows formatted list of all validation issues
4. **Success**: Loads configuration and displays it in tabs

## Testing

The validation system is covered by comprehensive unit tests:

```bash
# Run validation tests
python -m unittest tests.test_config_validation -v

# Run all tests
python -m unittest discover tests -v
```

**Test Coverage:**
- ✅ Valid configuration acceptance
- ✅ Missing required fields detection
- ✅ Invalid data types detection
- ✅ Out-of-range values detection
- ✅ Duplicate channel detection
- ✅ Array size limit enforcement
- ✅ JSON syntax error handling
- ✅ Data preservation on save/load

## Common Validation Errors

### Error: "Missing required field: 'version'"
**Cause**: Configuration file doesn't have version field
**Fix**: Add `"version": "1.0"` to root object

### Error: "Too many inputs: 25 (maximum 20)"
**Cause**: Configuration has more than 20 input channels
**Fix**: Remove excess inputs or split into multiple configurations

### Error: "inputs[3].type must be one of [...]"
**Cause**: Invalid input type specified
**Fix**: Use one of the valid input types listed

### Error: "Duplicate input channels: {0, 5}"
**Cause**: Multiple inputs configured for same channel
**Fix**: Ensure each input has unique channel number (0-19)

### Error: "inputs[0].channel must be between 0 and 19"
**Cause**: Input channel number outside valid range
**Fix**: Use channel number between 0 and 19

## Example Valid Configuration

```json
{
  "version": "1.0",
  "device": {
    "name": "PMU-30",
    "serial_number": "PMU30-001",
    "firmware_version": "1.0.0",
    "hardware_revision": "A",
    "created": "2025-12-21T12:00:00",
    "modified": "2025-12-21T15:30:00"
  },
  "inputs": [
    {
      "channel": 0,
      "name": "Brake Pressure",
      "type": "Calibrated Analog",
      "pull_up": false,
      "pull_down": false,
      "filter_samples": 10,
      "parameters": {
        "multiplier": 100.0,
        "offset": -50.0,
        "unit": "bar"
      }
    }
  ],
  "outputs": [
    {
      "channel": 0,
      "name": "Fuel Pump",
      "enabled": true,
      "protection": {
        "current_limit": 15.0,
        "inrush_current": 30.0,
        "inrush_time_ms": 500,
        "retry_count": 3,
        "retry_delay_ms": 1000
      },
      "pwm": {
        "enabled": true,
        "frequency": 1000,
        "default_duty": 75.0
      },
      "advanced": {
        "diagnostics": true,
        "open_load_detection": true
      }
    }
  ],
  "hbridges": [],
  "logic_functions": [],
  "virtual_channels": [],
  "pid_controllers": [],
  "can_buses": [],
  "wiper_modules": [],
  "turn_signal_modules": [],
  "system": {
    "control_frequency": 1000,
    "protection_frequency": 500,
    "logging_frequency": 500
  }
}
```

## Performance

Validation is performed efficiently:
- Average validation time: <5ms for typical configurations
- No external dependencies required
- Pure Python implementation
- Minimal memory overhead

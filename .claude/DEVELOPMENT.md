# PMU-30 Development Guidelines

## Starting the Development Environment

**ALWAYS use PowerShell to start emulator and configurator!**

### Quick Start (Single Command)
```powershell
powershell -Command "Start-Process -FilePath 'c:\Projects\pmu_30\firmware\.pio\build\pmu30_emulator\program.exe' -WorkingDirectory 'c:\Projects\pmu_30'; Start-Sleep -Seconds 2; Start-Process -FilePath 'python' -ArgumentList 'src/main.py' -WorkingDirectory 'c:\Projects\pmu_30\configurator'"
```

### Start Emulator Only
```powershell
powershell -Command "Start-Process -FilePath 'c:\Projects\pmu_30\firmware\.pio\build\pmu30_emulator\program.exe' -WorkingDirectory 'c:\Projects\pmu_30'"
```

### Start Configurator Only
```powershell
powershell -Command "Start-Process -FilePath 'python' -ArgumentList 'src/main.py' -WorkingDirectory 'c:\Projects\pmu_30\configurator'"
```

### Stop All Processes
```powershell
powershell -Command "Stop-Process -Name program -Force -ErrorAction SilentlyContinue; Stop-Process -Name python -Force -ErrorAction SilentlyContinue"
```

## Important Notes

1. **Working Directory**: Emulator MUST be started from `c:\Projects\pmu_30` to load `last_config.json` correctly
2. **Configurator**: MUST be started from `c:\Projects\pmu_30\configurator` for Python imports to work
3. **Config Files**: Two config files exist:
   - `c:\Projects\pmu_30\last_config.json` - Used by emulator (main)
   - `c:\Projects\pmu_30\firmware\last_config.json` - Backup copy

## Building

### Build Emulator (with MSYS2 toolchain)
```powershell
powershell -Command "$env:PATH = 'C:\msys64\ucrt64\bin;' + $env:PATH; cd c:\Projects\pmu_30\firmware; python -m platformio run -e pmu30_emulator"
```

## Default Configuration

The default config (`create_default_config()` in `config_schema.py`) includes:
- 30 Power Outputs (o_1 to o_30)
- 20 Analog Inputs (a_1 to a_20)
- 20 Digital Inputs (d_1 to d_20) - all enabled
- 4 H-Bridges (hb_1 to hb_4)
- 10 Logic, Timer, Filter, Switch, Number channels each
- 4 PID controllers
- Example 2D and 3D tables

**1:1 Mapping**: First 20 outputs (o_1 to o_20) are linked to digital inputs (d_1 to d_20):
- `o_1.source_channel = "d_1"`
- `o_2.source_channel = "d_2"`
- ...
- `o_20.source_channel = "d_20"`

Outputs o_21 to o_30 have no control function (for CAN, logic, etc.)

## Logic Functions

Logic channels support 21 different operation types organized in categories:

### Basic Logic (single input)
| Operation | Description | Parameters |
|-----------|-------------|------------|
| `is_true` | Output = 1 if Channel != 0 | `channel`, `true_delay_s`, `false_delay_s` |
| `is_false` | Output = 1 if Channel == 0 | `channel`, `true_delay_s`, `false_delay_s` |
| `not` | Inverts input (same as is_false) | `channel`, `true_delay_s`, `false_delay_s` |

### Comparison (channel vs constant)
| Operation | Description | Parameters |
|-----------|-------------|------------|
| `equal` | Output = 1 if Channel == Constant | `channel`, `constant`, `true_delay_s`, `false_delay_s` |
| `not_equal` | Output = 1 if Channel != Constant | `channel`, `constant`, `true_delay_s`, `false_delay_s` |
| `less` | Output = 1 if Channel < Constant | `channel`, `constant`, `true_delay_s`, `false_delay_s` |
| `greater` | Output = 1 if Channel > Constant | `channel`, `constant`, `true_delay_s`, `false_delay_s` |
| `less_equal` | Output = 1 if Channel <= Constant | `channel`, `constant`, `true_delay_s`, `false_delay_s` |
| `greater_equal` | Output = 1 if Channel >= Constant | `channel`, `constant`, `true_delay_s`, `false_delay_s` |
| `in_range` | Output = 1 if lower <= Channel <= upper | `channel`, `lower_value`, `upper_value` |

### Multi-Input Logic (two inputs)
| Operation | Description | Parameters |
|-----------|-------------|------------|
| `and` | Output = 1 if Channel1 AND Channel2 | `channel`, `channel_2`, `true_delay_s`, `false_delay_s` |
| `or` | Output = 1 if Channel1 OR Channel2 | `channel`, `channel_2`, `true_delay_s`, `false_delay_s` |
| `xor` | Output = 1 if one input (not both) | `channel`, `channel_2`, `true_delay_s`, `false_delay_s` |
| `nand` | Output = NOT(Channel1 AND Channel2) | `channel`, `channel_2`, `true_delay_s`, `false_delay_s` |
| `nor` | Output = NOT(Channel1 OR Channel2) | `channel`, `channel_2`, `true_delay_s`, `false_delay_s` |

### Edge Detection
| Operation | Description | Parameters |
|-----------|-------------|------------|
| `edge_rising` | Output pulse on 0->1 transition | `channel` |
| `edge_falling` | Output pulse on 1->0 transition | `channel` |

### Advanced Operations
| Operation | Description | Parameters |
|-----------|-------------|------------|
| `changed` | Output = 1 if value changed by threshold | `channel`, `threshold`, `time_on_s` |
| `hysteresis` | Schmitt trigger with upper/lower thresholds | `channel`, `upper_value`, `lower_value`, `polarity` |
| `set_reset_latch` | SR flip-flop | `set_channel`, `reset_channel`, `default_state` |
| `toggle` | Toggle output on edge | `toggle_channel`, `edge`, `set_channel`, `reset_channel`, `default_state` |
| `pulse` | Generate pulse(s) on edge | `channel`, `edge`, `time_on_s`, `pulse_count`, `retrigger` |
| `flash` | Periodic on/off when active | `channel`, `time_on_s`, `time_off_s` |

### Default Logic Examples (in last_config.json)

| Channel | Operation | Description |
|---------|-----------|-------------|
| `logic_1` | `and` | d_1 AND d_2 - both inputs must be ON |
| `logic_2` | `or` | d_3 OR d_4 - either input activates |
| `logic_3` | `not` | NOT d_5 - inverted digital input |
| `logic_4` | `greater` | a_1 > 2.5V - analog threshold |
| `logic_5` | `hysteresis` | a_2 with 1.5V-3.5V hysteresis |
| `logic_6` | `toggle` | Toggle by d_6 rising edge |
| `logic_7` | `pulse` | 0.5s pulse on d_7 edge |
| `logic_8` | `flash` | Blink 0.5s on/off when d_8 active |
| `logic_9` | `set_reset_latch` | SR latch: set=d_9, reset=d_10 |
| `logic_10` | `xor` | d_11 XOR d_12 - exclusive OR |

### Channel ID References
- Digital Inputs: d_1=250, d_2=251, ..., d_20=269
- Analog Inputs: a_1=230, a_2=231, ..., a_20=249
- Logic Channels: logic_1=274, logic_2=275, ..., logic_10=283

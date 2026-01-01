# Shared Library Architecture

**Version:** 2.0 | **Date:** January 2026 | **Author:** R2 m-sport

---

## Overview

The PMU-30 system uses a shared library architecture for configuration and channel execution. This ensures identical behavior between firmware (C) and configurator (Python).

## Problem Solved

Previous architecture had separate implementations:

| Component | Firmware (C) | Configurator (Python) |
|-----------|--------------|----------------------|
| Config format | JSON parsing | JSON parsing |
| Channel logic | pmu_logic.c | logic_engine.py |
| Protocol | pmu_protocol.c | protocol.py |

**Issues encountered:**
- Format drift between implementations
- Logic behavior differences
- Maintenance burden of two codebases

## Current Architecture

```
shared/
├── channel_config.h          # Binary structure definitions (C)
├── channel_config.c          # Binary serialization (C)
├── channel_executor.h        # Execution API (C)
├── channel_executor.c        # Channel processing (C)
├── channel_types.h           # Type enumerations (C)
├── engine/                   # Logic Engine (C)
│   ├── logic_engine.h
│   ├── logic.c               # Boolean operations
│   ├── math.c                # Arithmetic operations
│   ├── timer.c               # Timing functions
│   ├── filter.c              # Signal filtering
│   ├── table.c               # Lookup tables
│   ├── pid.c                 # PID controller
│   ├── counter.c             # Counters
│   ├── hysteresis.c          # Hysteresis function
│   └── flipflop.c            # Latches
└── python/
    ├── channel_config.py     # Python port of binary structures
    └── engine/               # Python port of Logic Engine
        ├── __init__.py
        └── logic_engine.py
```

## Integration Points

### Firmware

```c
// firmware/src/pmu_channel_exec.c

#include "channel_executor.h"
#include "channel_config.h"

// Initialize with HAL callbacks
Exec_Init(&context,
          ExecGetValue,   // PMU_Channel_GetValue wrapper
          ExecSetValue,   // PMU_Channel_SetValue wrapper
          NULL);

// Add channel from binary config
PMU_ChannelExec_AddChannel(channel_id, type, config);

// Execute at 500Hz
PMU_ChannelExec_Update();
```

### Configurator

```python
# configurator/src/models/binary_config.py

from shared.python.channel_config import (
    ConfigFile, Channel, ChannelType
)

# Load binary config
config = ConfigFile.load("project.pmu30")

# Save binary config
config.save("project.pmu30")

# Send to device
binary_data = config.serialize()
```

## Build Integration

### Firmware (PlatformIO)

```ini
; platformio.ini
[env:pmu30]
build_src_filter =
    +<src/>
    +<../shared/>
    +<../shared/engine/>
```

### Configurator (Python)

```python
# Add shared library to path
import sys
from pathlib import Path

shared_path = Path(__file__).parent.parent.parent / "shared" / "python"
sys.path.insert(0, str(shared_path))

from channel_config import ConfigFile
```

## Binary Format

All configuration uses binary format (no JSON):

| Component | Format | CRC |
|-----------|--------|-----|
| File header | 32 bytes, little-endian | CRC-32 of payload |
| Channel header | 14 bytes | Included in file CRC |
| Channel config | Type-specific size | Included in file CRC |

## Logic Engine

The Logic Engine processes virtual channels using pure functions:

```c
// Pure function - no side effects
int32_t Logic_Evaluate(const CfgLogic_t* cfg,
                       const int32_t* inputs)
{
    switch (cfg->operation) {
        case LOGIC_OP_AND:
            return Logic_And(inputs, cfg->input_count);
        case LOGIC_OP_OR:
            return Logic_Or(inputs, cfg->input_count);
        case LOGIC_OP_GT:
            return inputs[0] > cfg->compare_value ? 1 : 0;
        // ...
    }
}
```

Python implementation mirrors C exactly:

```python
def logic_evaluate(cfg: CfgLogic, inputs: List[int]) -> int:
    if cfg.operation == LogicOp.AND:
        return logic_and(inputs, cfg.input_count)
    elif cfg.operation == LogicOp.OR:
        return logic_or(inputs, cfg.input_count)
    elif cfg.operation == LogicOp.GT:
        return 1 if inputs[0] > cfg.compare_value else 0
    # ...
```

## Benefits

| Metric | Before | After |
|--------|--------|-------|
| Config bugs | Common | Impossible (same format) |
| Logic differences | Frequent | None (same code) |
| Test coverage | Separate | Unified |
| Feature parity | Manual sync | Automatic |

## Testing Strategy

Both implementations tested against same vectors:

```python
# tests/test_vectors.py
TEST_VECTORS = [
    {
        "name": "Logic AND true",
        "type": ChannelType.LOGIC,
        "config": {"operation": 0, "inputs": [1, 1, 1]},
        "expected": 1
    },
    {
        "name": "Logic AND false",
        "type": ChannelType.LOGIC,
        "config": {"operation": 0, "inputs": [1, 0, 1]},
        "expected": 0
    },
]
```

Run tests on both platforms:
- `pytest tests/` for Python
- `pio test` for C firmware

---

## Shared Validation Module

The shared validation module ensures identical validation between Configurator and Firmware.

### Architecture

```
shared/
├── channel_validation.h       # Validation API (C)
├── channel_validation.c       # Validation logic (C)
└── python/
    └── channel_validation.py  # Python port

configurator/
└── src/utils/validation.py    # Config transformer bridge
```

### Config Transformers

The Configurator uses **Config Transformers** to map UI field names to shared validation field names:

```python
# configurator/src/utils/validation.py

CONFIG_TRANSFORMERS = {
    "timer": _transform_timer_config,      # limit_hours/min/sec -> delay_ms
    "logic": _transform_logic_config,      # input_channels -> input_ids
    "filter": _transform_filter_config,    # time_constant -> time_constant_ms
    "pid": _transform_pid_config,          # setpoint_channel -> setpoint_id
    "table_2d": _transform_table_2d_config,# x_axis_channel -> input_id
    "digital_input": _transform_digital_input_config,
    "analog_input": _transform_analog_input_config,
    "power_output": _transform_power_output_config,
    "switch": _transform_switch_config,
    "number": _transform_number_config,
    "can_rx": _transform_can_input_config,
}
```

### Integration in Dialogs

```python
# configurator/src/ui/dialogs/base_channel_dialog.py

def _on_accept(self):
    errors = self._validate_base()
    errors.extend(self._validate_specific())

    # Run shared validation (consistent with firmware)
    if self.channel_type:
        config = self.get_config()
        shared_errors = validate_with_shared(self.channel_type, config)
        errors.extend(shared_errors)

    if errors:
        QMessageBox.warning(self, "Validation Error", ...)
        return
    self.accept()
```

### Benefits

| Aspect | Before | After |
|--------|--------|-------|
| Validation rules | Duplicated | Single source |
| UI/FW consistency | Manual sync | Automatic |
| Error messages | Different | Identical |
| Test coverage | Separate | Unified |

---

## See Also

- [Binary Configuration Architecture](BINARY_CONFIG_ARCHITECTURE.md)
- [Configuration Reference](reference/configuration.md)
- [Firmware Architecture](firmware_architecture.md)

---

**Copyright 2026 R2 m-sport. All rights reserved.**

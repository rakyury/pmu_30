# PMU-30 Configurator Tests

## Test Summary

| Category | Tests | Files |
|----------|-------|-------|
| Unit Tests | 135 | 4 |
| UI Tests | 242 | 10 |
| Integration Tests | 172 | 14 |
| Other Tests | 105 | 5 |
| **Total** | **~654** | **33** |

## Running Tests

---

## 🚨 CRITICAL TESTS - MUST RUN AFTER EVERY CHANGE

These tests verify the fundamental control flow of the PMU-30.
**Run after ANY firmware or configurator modification!**

```bash
# Start emulator first:
start "" "../firmware/.pio/build/pmu30_emulator/program.exe"

# Run critical tests:
python -m pytest tests/integration/test_control_flow_critical.py -v -s --timeout=60
```

### Critical Test Flows

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| `test_low_side_switch_controls_output` | LOW-SIDE DI → Output | DI=ON → OUT=ON, change to HIGH-SIDE → OUT=OFF |
| `test_high_side_switch_controls_output` | HIGH-SIDE DI → Output | DI HIGH=ON → OUT=ON, DI LOW=OFF → OUT=OFF |
| `test_timer_oneshot_controls_output` | Timer → Output | Trigger → OUT=ON, wait → OUT=OFF |
| `test_timer_retriggerable_controls_output` | Retriggerable Timer | Retrigger resets timeout |
| `test_input_type_change_updates_output` | Input type change | Changing DI type updates output immediately |

### Quick Validation Script

```bash
# Run from configurator directory:
python run_critical_tests.py
```

---


### Run all tests with pytest
```bash
cd configurator
python -m pytest tests/ -v
```

### Run UI tests only
```bash
python -m pytest tests/ui -v --timeout=60
```

### Run unit tests only
```bash
python -m pytest tests/unit -v
```

### Run integration tests (requires emulator)
```bash
# Start the emulator first:
# ../firmware/.pio/build/pmu30_emulator/program.exe

python -m pytest tests/integration -v --timeout=120
```

### Run with coverage
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── unit/                       # Unit tests (135 tests)
│   ├── test_channel_model.py   # Channel model tests (46)
│   ├── test_undo_manager.py    # Undo/Redo tests (44)
│   ├── test_constants_conversion.py  # Constants tests (32)
│   └── ...
├── ui/                         # UI tests (242 tests)
│   ├── test_dialogs_inputs.py  # Input dialog tests (30)
│   ├── test_dialogs_outputs.py # Output dialog tests (24)
│   ├── test_dialogs_logic.py   # Logic dialog tests (34)
│   ├── test_dialogs_hbridge.py # H-Bridge dialog tests (23)
│   ├── test_dialogs_misc.py    # Misc dialog tests (29)
│   ├── test_widgets.py         # Widget tests (34)
│   ├── test_widgets_controls.py  # Control widget tests (24)
│   ├── test_widgets_monitors.py  # Monitor widget tests (44)
│   └── test_main_window.py     # Main window tests (29)
├── integration/                # Integration tests (172 tests)
│   ├── conftest.py             # Pytest fixtures
│   ├── helpers.py              # Test utilities
│   ├── test_analog_inputs.py   # Analog input tests (14)
│   ├── test_digital_inputs.py  # Digital input tests (16)
│   ├── test_output_control.py  # Output control tests (8)
│   ├── test_output_pwm.py      # PWM output tests (10)
│   ├── test_output_protection.py  # Protection tests (14)
│   ├── test_can_inputs.py      # CAN input tests (15)
│   ├── test_tables.py          # Table tests (16)
│   ├── test_timer_operations.py  # Timer tests (7)
│   ├── test_hbridge_pid.py     # H-Bridge PID tests (12)
│   ├── test_filter_channels.py # Filter tests (13)
│   ├── test_switch_channels.py # Switch tests (13)
│   ├── test_arithmetic_functions.py  # Arithmetic tests (11)
│   ├── test_atomic_config.py   # Config tests (12)
│   ├── test_flash_autosave.py  # Flash tests (11)
│   └── test_control_flow_critical.py  # CRITICAL: Control flow tests (5)
├── test_config_manager.py      # ConfigManager tests (13)
├── test_config_validation.py   # Validation tests (15)
├── test_protocol.py            # Protocol tests (27)
├── test_telemetry.py           # Telemetry tests (30)
├── test_comm_manager.py        # Communication tests (20)
└── README.md                   # This file
```

## CI Integration

Tests run automatically in GitHub Actions on:
- Every push to `main` and `develop`
- All pull requests to `main`

The CI workflow:
1. Installs Qt dependencies for headless testing
2. Runs UI tests with xvfb (virtual framebuffer)
3. Generates coverage reports
4. Uploads to Codecov

### Skipped in CI
- `test_main_window.py` - Hangs in headless environment due to QTimer widgets

## Writing New Tests

### Unit Test Template
```python
import pytest
from models.my_module import MyClass

class TestMyClass:
    def test_something(self):
        instance = MyClass()
        result = instance.do_something()
        assert result == expected_value
```

### UI Test Template (PyQt6)
```python
import pytest
from PyQt6.QtWidgets import QApplication
from ui.dialogs.my_dialog import MyDialog

@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app

class TestMyDialog:
    def test_dialog_opens(self, qapp):
        dialog = MyDialog()
        assert dialog is not None
        dialog.close()
```

### Integration Test Template
```python
import pytest
import asyncio
from .helpers import BASE_CONFIG

class TestMyFeature:
    async def test_feature(self, emulator_connection):
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        # ... test code
```

---

## 🔧 Test Configuration Templates

### BASE_CONFIG

Empty base configuration for custom test setups:
```python
from .helpers import BASE_CONFIG

config = BASE_CONFIG.copy()
config["channels"] = [
    make_digital_input_config(1, "di_test", "switch_active_low"),
    make_output_config(1, "o_test", "di_test"),
]
```

### COMPREHENSIVE_TEST_CONFIG

**⚠️ CRITICAL: Use this for full integration testing!**

Complete configuration with ALL channel types and REAL logic connections:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPREHENSIVE TEST CONFIG                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DIGITAL INPUTS (5)          ANALOG INPUTS (3)                      │
│  ├── di_ignition (low)       ├── ai_coolant_temp                    │
│  ├── di_start_btn (high)     ├── ai_oil_pressure                    │
│  ├── di_brake (low)          └── ai_throttle                        │
│  ├── di_launch_btn (high)                                           │
│  └── di_pit_limiter (high)                                          │
│         │                           │                               │
│         ▼                           ▼                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    LOGIC CHANNELS (16)                        │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ Boolean Gates:    and, or, not, xor, nand, nor               │  │
│  │ Comparisons:      greater, less, equal, not_equal,           │  │
│  │                   greater_equal, less_equal, in_range        │  │
│  │ Special:          hysteresis, flash, pulse, toggle, latch    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                           │                               │
│         ▼                           ▼                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   NUMBER CHANNELS (11)                        │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ Operations:       constant, add, subtract, multiply, divide  │  │
│  │                   min, max, average, abs, scale, clamp       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   POWER OUTPUTS (6)                           │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ o_fuel_pump      ← di_ignition (direct)                      │  │
│  │ o_starter        ← l_start_ready (AND logic)                 │  │
│  │ o_fan            ← l_fan_control (hysteresis) + PWM          │  │
│  │ o_warning_lamp   ← l_warning_flash (flash logic)             │  │
│  │ o_fuel_relay     ← l_fuel_pump_latch (SR latch)              │  │
│  │ o_boost_solenoid ← l_engine_safe (complex chain)             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      CAN TX (2 messages)                      │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ 0x600: ignition, engine_safe, coolant_temp, throttle         │  │
│  │ 0x601: fuel_pump, fan, starter, warning                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Also includes: Filters (2), Timers (2), Tables (1)                 │
└─────────────────────────────────────────────────────────────────────┘
```

**Usage:**
```python
import json
from .helpers import COMPREHENSIVE_TEST_CONFIG

class TestComprehensiveFlow:
    async def test_full_chain(self, protocol_handler):
        # Send complete config with all channel types
        response = await protocol_handler.send_config(
            json.dumps(COMPREHENSIVE_TEST_CONFIG)
        )
        assert response.success

        # Test: di_ignition (active_low) → o_fuel_pump
        # di_ignition defaults to ON (active_low with no signal = ON)
        await asyncio.sleep(0.5)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.outputs[0] == 1  # o_fuel_pump should be ON
```

### Channel Flow Examples

| Input | Logic/Number | Output | CAN Signal |
|-------|--------------|--------|------------|
| `di_ignition` | direct | `o_fuel_pump` | `ctx_pmu_status.ignition` |
| `di_ignition` + `di_brake` | `l_start_ready` (AND) | `o_starter` | `ctx_outputs.starter` |
| `ai_coolant_temp` | `l_fan_control` (hysteresis 85-95°C) | `o_fan` | `ctx_outputs.fan` |
| `ai_coolant_temp` > 95°C | `l_temp_high` → `l_warning_flash` | `o_warning_lamp` | `ctx_outputs.warning` |
| `ai_oil_pressure` + `ai_coolant_temp` | `l_pressure_ok` + `l_temp_normal` → `l_engine_safe` | `o_boost_solenoid` | `ctx_pmu_status.engine_safe` |

### Helper Functions

```python
from .helpers import (
    make_digital_input_config,  # Digital input with type
    make_analog_input_config,   # Analog input with scaling
    make_output_config,         # Power output with source
    make_logic_config,          # Logic operation
    make_number_config,         # Number operation
    make_timer_config,          # Timer channel
    make_filter_config,         # Filter channel
    make_table_2d_config,       # 2D lookup table
)

# Example: Create logic AND gate
logic = make_logic_config(
    channel_id=400,
    name="l_ready",
    operation="and",
    input1="di_ignition",
    input2="di_brake"
)

# Example: Create number with subtraction
number = make_number_config(
    channel_id=500,
    name="n_temp_diff",
    operation="subtract",
    inputs=["ai_temp1", "ai_temp2"]
)
```

---

## Coverage Goals

| Category | Target | Current |
|----------|--------|---------|
| Models | 90% | ~80% |
| Dialogs | 80% | ~75% |
| Widgets | 70% | ~65% |
| Communication | 85% | ~80% |

## Dependencies

- pytest >= 7.4.0
- pytest-qt >= 4.2.0
- pytest-cov >= 4.1.0
- pytest-timeout >= 2.2.0
- pytest-asyncio >= 0.21.0

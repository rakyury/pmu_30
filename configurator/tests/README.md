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
│   └── test_flash_autosave.py  # Flash tests (11)
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

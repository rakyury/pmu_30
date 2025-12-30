# PMU-30 Configurator UI Tests

Comprehensive UI test suite for the PMU-30 Configurator application.

## Test Structure

```
tests/ui/
├── conftest.py              # Fixtures and test configuration
├── test_dialogs_inputs.py   # Digital/Analog input dialog tests
├── test_dialogs_outputs.py  # Output configuration dialog tests
├── test_dialogs_logic.py    # Logic and Math channel dialog tests
├── test_dialogs_misc.py     # Timer, CAN, and other dialog tests
├── test_main_window.py      # Main window and menu tests
└── test_widgets.py          # Widget component tests
```

## Running Tests

```bash
# Run all UI tests
cd configurator
python -m pytest tests/ui/ -v

# Run specific test file
python -m pytest tests/ui/test_dialogs_inputs.py -v

# Run with coverage
python -m pytest tests/ui/ --cov=src/ui --cov-report=html
```

## Test Coverage

### Dialogs (120+ tests)

| Dialog | Tests | Coverage |
|--------|-------|----------|
| DigitalInputDialog | 17 | All subtypes, validation, config roundtrip |
| AnalogInputDialog | 20 | All subtypes, calibration table, pin filtering |
| OutputConfigDialog | 24 | PWM, protection, multi-pin, validation |
| LogicDialog | 28 | All operations (AND, OR, Hysteresis, Pulse...) |
| NumberDialog | 27 | All math operations (Add, Clamp, Lookup...) |
| TimerDialog | 7 | Triggers, modes, time limits |
| CANMessageDialog | 4 | Templates, message types |
| Other dialogs | 13 | Filter, Enum, Switch, PID, Lua, Connection |

### Main Window (30 tests)

- Window creation and initialization
- Menu bar structure (File, Edit, Device)
- Dock widgets creation
- Monitor tabs (PMU, Outputs, Analog, PID, CAN, DataLogger)
- Action methods existence
- Signal definitions

### Widgets (33 tests)

| Widget | Tests |
|--------|-------|
| ProjectTree | 6 |
| OutputMonitor | 6 |
| AnalogMonitor | 2 |
| VariablesInspector | 2 |
| PMUMonitor | 1 |
| HBridgeMonitor | 2 |
| PIDTuner | 2 |
| CANMonitor | 2 |
| DataLogger | 1 |
| ChannelGraph | 4 |
| LogViewer | 1 |

## Test Fixtures

Defined in `conftest.py`:

- `qapp` - QApplication instance (session scope)
- `qtbot` - Qt interaction helper
- `mock_config_manager` - Mocked ConfigManager
- `sample_channels` - Sample channel configurations
- `available_channels` - Channel dictionary for selectors
- `sample_can_messages` - CAN message samples
- `mock_comm_manager` - Mocked CommunicationManager
- `mock_telemetry_handler` - Mocked TelemetryHandler

## Writing New Tests

```python
class TestMyDialog:
    def test_dialog_creation(self, qapp):
        """Test dialog can be created"""
        dialog = MyDialog()
        assert dialog is not None
        dialog.close()

    def test_config_roundtrip(self, qapp):
        """Test config save/load"""
        config = {"name": "Test", "value": 42}
        dialog = MyDialog(config=config)
        saved = dialog.get_config()
        assert saved["name"] == config["name"]
        dialog.close()
```

## Notes

- Tests use PyQt6 with pytest
- Dialog visibility tests require `dialog.show()` before checking `isHidden()`
- Main window tests mock DeviceController and ConfigManager
- Some tests are skipped if optional components are not available

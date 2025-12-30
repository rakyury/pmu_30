"""
PyQt6 UI Test Configuration and Fixtures
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# Import PyQt6 for testing
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


@pytest.fixture(scope='session')
def qapp():
    """Create QApplication instance for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def qtbot(qapp):
    """Create a simple qtbot-like helper."""
    class QtBot:
        def __init__(self, app):
            self.app = app

        def addWidget(self, widget):
            """Track widget for cleanup."""
            widget.show()
            self.app.processEvents()

        def keyClick(self, widget, key, modifier=Qt.KeyboardModifier.NoModifier):
            """Simulate key click."""
            from PyQt6.QtTest import QTest
            QTest.keyClick(widget, key, modifier)
            self.app.processEvents()

        def keyClicks(self, widget, text):
            """Type text."""
            from PyQt6.QtTest import QTest
            QTest.keyClicks(widget, text)
            self.app.processEvents()

        def mouseClick(self, widget, button=Qt.MouseButton.LeftButton):
            """Simulate mouse click."""
            from PyQt6.QtTest import QTest
            QTest.mouseClick(widget, button)
            self.app.processEvents()

        def wait(self, ms=10):
            """Wait for events to process."""
            import time
            time.sleep(ms / 1000)
            self.app.processEvents()

    return QtBot(qapp)


@pytest.fixture
def mock_config_manager():
    """Create mock ConfigManager."""
    manager = MagicMock()
    manager.config = {
        "version": "1.0",
        "device": {"name": "PMU-30", "model": "PMU-30"},
        "inputs": [],
        "outputs": [],
        "channels": [],
        "can": {"messages": []},
        "lua_scripts": []
    }
    manager.get_config.return_value = manager.config
    manager.is_modified.return_value = False
    manager.current_file = None
    return manager


@pytest.fixture
def sample_channels():
    """Sample channel configurations for testing."""
    return [
        {
            "channel_id": 1,
            "id": "ai_test1",
            "name": "Test Analog 1",
            "channel_type": "analog_input",
            "subtype": "linear",
            "input_pin": 0
        },
        {
            "channel_id": 2,
            "id": "di_test1",
            "name": "Test Digital 1",
            "channel_type": "digital_input",
            "subtype": "switch_active_low",
            "input_pin": 0
        },
        {
            "channel_id": 3,
            "id": "out_test1",
            "name": "Test Output 1",
            "channel_type": "power_output",
            "output_pin": 0,
            "enabled": True
        },
        {
            "channel_id": 4,
            "id": "logic_test1",
            "name": "Test Logic 1",
            "channel_type": "logic",
            "operation": "and"
        },
        {
            "channel_id": 5,
            "id": "num_test1",
            "name": "Test Number 1",
            "channel_type": "number",
            "value": 42.0
        }
    ]


@pytest.fixture
def available_channels(sample_channels):
    """Available channels dictionary for channel selectors."""
    return {
        "Analog Inputs": ["ai_test1"],
        "Digital Inputs": ["di_test1"],
        "Power Outputs": ["out_test1"],
        "Logic": ["logic_test1"],
        "Numbers": ["num_test1"],
        "System": ["sys_voltage", "sys_current", "sys_temperature"]
    }


@pytest.fixture
def sample_can_messages():
    """Sample CAN messages for testing."""
    return [
        {
            "id": "engine_rpm",
            "name": "Engine RPM",
            "can_id": 0x100,
            "dlc": 8,
            "signals": [
                {
                    "name": "rpm",
                    "start_bit": 0,
                    "bit_length": 16,
                    "factor": 1.0,
                    "offset": 0.0
                }
            ]
        },
        {
            "id": "vehicle_speed",
            "name": "Vehicle Speed",
            "can_id": 0x101,
            "dlc": 8,
            "signals": [
                {
                    "name": "speed_kmh",
                    "start_bit": 0,
                    "bit_length": 16,
                    "factor": 0.1,
                    "offset": 0.0
                }
            ]
        }
    ]


@pytest.fixture
def mock_comm_manager():
    """Create mock CommunicationManager."""
    manager = MagicMock()
    manager.is_connected.return_value = False
    manager.connect.return_value = True
    manager.disconnect.return_value = True
    manager.send_config.return_value = True
    return manager


@pytest.fixture
def mock_telemetry_handler():
    """Create mock TelemetryHandler."""
    handler = MagicMock()
    handler.is_running.return_value = False
    handler.channel_values = {}
    return handler


# Channel type enums for test parametrization
CHANNEL_TYPES = [
    "analog_input",
    "digital_input",
    "power_output",
    "logic",
    "number",
    "timer",
    "switch",
    "table_2d",
    "table_3d",
    "filter",
    "enum",
    "can_rx",
    "can_tx",
    "lua_script",
    "pid"
]

DIGITAL_INPUT_SUBTYPES = [
    "switch_active_low",
    "switch_active_high",
    "frequency",
    "rpm",
    "flex_fuel",
    "beacon",
    "puls_oil_sensor"
]

ANALOG_INPUT_SUBTYPES = [
    "switch_active_low",
    "switch_active_high",
    "rotary_switch",
    "linear",
    "calibrated"
]

LOGIC_OPERATIONS = [
    "and", "or", "not", "xor",
    "add", "subtract", "multiply", "divide",
    "compare_gt", "compare_lt", "compare_eq",
    "min", "max", "average"
]

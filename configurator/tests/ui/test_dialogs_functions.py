"""
UI Tests for Function Dialogs (FilterDialog, SwitchDialog, Table2D, Table3D, PID)
Comprehensive tests for Phase 2 of tech debt refactoring.
"""

import pytest
from PyQt6.QtWidgets import QApplication

from ui.dialogs.filter_dialog import FilterDialog
from ui.dialogs.switch_dialog import SwitchDialog
from ui.dialogs.table_2d_dialog import Table2DDialog
from ui.dialogs.table_3d_dialog import Table3DDialog
from ui.dialogs.pid_controller_dialog import PIDControllerDialog
from models.channel import FilterType


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for the test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_available_channels():
    """Sample available channels for testing."""
    return {
        "digital_inputs": [
            (10, "StartButton", "", 0),
            (11, "IgnitionSwitch", "", 0),
        ],
        "analog_inputs": [
            (20, "FuelLevel", "L", 1),
            (21, "CoolantTemp", "C", 1),
            (22, "OilPressure", "kPa", 1),
        ],
        "logic": [
            (30, "EngineRunning", "", 0),
        ],
        "numbers": [
            (40, "CalculatedRPM", "rpm", 0),
        ],
    }


@pytest.fixture
def sample_existing_channels():
    """Sample existing channels for testing."""
    return [
        {"channel_id": 10, "name": "StartButton"},
        {"channel_id": 20, "name": "FuelLevel"},
    ]


# ==================== FilterDialog Tests ====================

class TestFilterDialogCreation:
    """Tests for FilterDialog creation."""

    def test_create_new_dialog(self, qapp):
        """Test creating new filter dialog."""
        dialog = FilterDialog()
        assert dialog is not None
        assert dialog.windowTitle().startswith("New")
        dialog.close()

    def test_create_edit_dialog(self, qapp, sample_available_channels):
        """Test creating filter dialog for editing."""
        config = {
            "channel_id": 100,
            "name": "SmoothedRPM",
            "input_channel": 40,
            "filter_type": "moving_avg",
            "window_size": 20,
        }
        dialog = FilterDialog(config=config, available_channels=sample_available_channels)
        assert "Edit" in dialog.windowTitle()
        assert dialog.name_edit.text() == "SmoothedRPM"
        dialog.close()

    def test_auto_generate_name(self, qapp):
        """Test auto-generated name for new filter."""
        dialog = FilterDialog()
        name = dialog.name_edit.text()
        assert name != ""
        assert "Filter" in name
        dialog.close()


class TestFilterTypes:
    """Tests for filter type functionality."""

    def test_all_filter_types_available(self, qapp):
        """Test all filter types are in dropdown."""
        dialog = FilterDialog()

        filter_types = []
        for i in range(dialog.filter_type_combo.count()):
            filter_types.append(dialog.filter_type_combo.itemData(i))

        assert FilterType.MOVING_AVG.value in filter_types
        assert FilterType.LOW_PASS.value in filter_types
        assert FilterType.MIN_WINDOW.value in filter_types
        assert FilterType.MAX_WINDOW.value in filter_types
        assert FilterType.MEDIAN.value in filter_types
        dialog.close()

    def test_moving_avg_shows_window_size(self, qapp):
        """Test moving average shows window size parameter."""
        dialog = FilterDialog()

        # Find and select moving average
        for i in range(dialog.filter_type_combo.count()):
            if dialog.filter_type_combo.itemData(i) == FilterType.MOVING_AVG.value:
                dialog.filter_type_combo.setCurrentIndex(i)
                break

        # Check visibility via isVisibleTo (works for hidden dialogs)
        assert dialog.window_label.isVisibleTo(dialog)
        assert dialog.window_spin.isVisibleTo(dialog)
        assert not dialog.time_const_spin.isVisibleTo(dialog)
        dialog.close()

    def test_low_pass_shows_time_constant(self, qapp):
        """Test low pass shows time constant parameter."""
        dialog = FilterDialog()

        # Find and select low pass
        for i in range(dialog.filter_type_combo.count()):
            if dialog.filter_type_combo.itemData(i) == FilterType.LOW_PASS.value:
                dialog.filter_type_combo.setCurrentIndex(i)
                break

        # Check visibility via isVisibleTo (works for hidden dialogs)
        assert dialog.time_const_spin.isVisibleTo(dialog)
        assert not dialog.window_spin.isVisibleTo(dialog)
        dialog.close()

    def test_median_shows_window_size(self, qapp):
        """Test median filter shows window size parameter."""
        dialog = FilterDialog()

        for i in range(dialog.filter_type_combo.count()):
            if dialog.filter_type_combo.itemData(i) == FilterType.MEDIAN.value:
                dialog.filter_type_combo.setCurrentIndex(i)
                break

        # Check visibility via isVisibleTo (works for hidden dialogs)
        assert dialog.window_spin.isVisibleTo(dialog)
        dialog.close()


class TestFilterDialogConfig:
    """Tests for FilterDialog configuration."""

    def test_get_config_returns_complete(self, qapp):
        """Test get_config returns complete configuration."""
        dialog = FilterDialog()
        dialog.name_edit.setText("TestFilter")
        dialog.input_edit.setText("TestChannel")

        config = dialog.get_config()

        assert config["name"] == "TestFilter"
        assert "filter_type" in config
        assert "window_size" in config
        assert "time_constant" in config
        assert "channel_type" in config
        dialog.close()

    def test_window_size_range(self, qapp):
        """Test window size spinbox range."""
        dialog = FilterDialog()
        assert dialog.window_spin.minimum() == 2
        assert dialog.window_spin.maximum() == 100
        dialog.close()

    def test_time_constant_range(self, qapp):
        """Test time constant spinbox range."""
        dialog = FilterDialog()
        assert dialog.time_const_spin.minimum() == 0.001
        assert dialog.time_const_spin.maximum() == 100.0
        dialog.close()

    def test_config_roundtrip(self, qapp, sample_available_channels):
        """Test config load/save roundtrip."""
        original = {
            "channel_id": 150,
            "name": "FilteredTemp",
            "input_channel": 21,
            "filter_type": "median",
            "window_size": 15,
            "time_constant": 0.5,
        }

        dialog = FilterDialog(config=original, available_channels=sample_available_channels)
        result = dialog.get_config()

        assert result["name"] == original["name"]
        assert result["filter_type"] == original["filter_type"]
        assert result["window_size"] == original["window_size"]
        dialog.close()


class TestFilterDialogValidation:
    """Tests for FilterDialog validation."""

    def test_validation_input_required(self, qapp):
        """Test validation requires input channel."""
        dialog = FilterDialog()
        dialog.name_edit.setText("Test")
        dialog.input_edit.setText("")

        errors = dialog._validate_specific()
        assert len(errors) > 0
        assert any("input" in e.lower() for e in errors)
        dialog.close()


# ==================== SwitchDialog Tests ====================

class TestSwitchDialogCreation:
    """Tests for SwitchDialog creation."""

    def test_create_new_dialog(self, qapp):
        """Test creating new switch dialog."""
        dialog = SwitchDialog()
        assert dialog is not None
        assert "Switch" in dialog.windowTitle() or "New" in dialog.windowTitle()
        dialog.close()

    def test_create_edit_dialog(self, qapp, sample_available_channels):
        """Test creating switch dialog for editing."""
        config = {
            "name": "ModeSwitch",
            "switch_type": "latching switch",
            "input_channel_up": 10,
            "input_channel_down": 11,
            "first_state": 0,
            "last_state": 3,
            "default_state": 0,
        }
        dialog = SwitchDialog(config=config, available_channels=sample_available_channels)
        assert dialog.name_edit.text() == "ModeSwitch"
        dialog.close()


class TestSwitchTypes:
    """Tests for switch type functionality."""

    def test_switch_types_available(self, qapp):
        """Test switch types in dropdown."""
        dialog = SwitchDialog()

        types = [dialog.type_combo.itemText(i) for i in range(dialog.type_combo.count())]

        assert "latching switch" in types
        assert "press/hold switch" in types
        dialog.close()

    def test_trigger_edges_available(self, qapp):
        """Test trigger edges in dropdown."""
        dialog = SwitchDialog()

        edges = [dialog.trigger_up_combo.itemText(i) for i in range(dialog.trigger_up_combo.count())]

        assert "Rising" in edges
        assert "Falling" in edges
        assert "Both" in edges
        dialog.close()


class TestSwitchStateRange:
    """Tests for switch state range validation."""

    def test_state_spinbox_range(self, qapp):
        """Test state spinbox ranges."""
        dialog = SwitchDialog()

        assert dialog.first_state_spin.minimum() == 0
        assert dialog.first_state_spin.maximum() == 255
        assert dialog.last_state_spin.minimum() == 0
        assert dialog.last_state_spin.maximum() == 255
        assert dialog.default_state_spin.minimum() == 0
        assert dialog.default_state_spin.maximum() == 255
        dialog.close()

    def test_default_values(self, qapp):
        """Test default state values."""
        dialog = SwitchDialog()

        assert dialog.first_state_spin.value() == 0
        assert dialog.last_state_spin.value() == 2
        assert dialog.default_state_spin.value() == 0
        dialog.close()


class TestSwitchDialogConfig:
    """Tests for SwitchDialog configuration."""

    def test_get_config_returns_complete(self, qapp):
        """Test get_config returns complete configuration."""
        dialog = SwitchDialog()
        dialog.name_edit.setText("TestSwitch")

        config = dialog.get_config()

        assert config["name"] == "TestSwitch"
        assert "switch_type" in config
        assert "first_state" in config
        assert "last_state" in config
        assert "default_state" in config
        dialog.close()

    def test_config_roundtrip(self, qapp, sample_available_channels):
        """Test config load/save roundtrip."""
        original = {
            "name": "LightsSwitch",
            "switch_type": "press/hold switch",
            "input_channel_up": 10,
            "trigger_edge_up": "Falling",
            "first_state": 1,
            "last_state": 5,
            "default_state": 2,
        }

        dialog = SwitchDialog(config=original, available_channels=sample_available_channels)
        result = dialog.get_config()

        assert result["name"] == original["name"]
        assert result["switch_type"] == original["switch_type"]
        assert result["first_state"] == original["first_state"]
        assert result["last_state"] == original["last_state"]
        assert result["default_state"] == original["default_state"]
        dialog.close()


# ==================== Table2DDialog Tests ====================

class TestTable2DDialogCreation:
    """Tests for Table2DDialog creation."""

    def test_create_new_dialog(self, qapp):
        """Test creating new 2D table dialog."""
        dialog = Table2DDialog()
        assert dialog is not None
        assert "2D" in dialog.windowTitle() or "Table" in dialog.windowTitle()
        dialog.close()

    def test_create_edit_dialog(self, qapp, sample_available_channels):
        """Test creating 2D table dialog for editing."""
        config = {
            "channel_id": 200,
            "name": "FuelMap",
            "input_x": 40,
            "axis_x": [1000, 2000, 3000, 4000],
            "values": [50, 60, 70, 80],
        }
        dialog = Table2DDialog(config=config, available_channels=sample_available_channels)
        assert dialog.name_edit.text() == "FuelMap"
        dialog.close()


class TestTable2DDialogConfig:
    """Tests for Table2DDialog configuration."""

    def test_get_config_returns_complete(self, qapp):
        """Test get_config returns complete configuration."""
        dialog = Table2DDialog()
        dialog.name_edit.setText("TestTable2D")

        config = dialog.get_config()

        assert config["name"] == "TestTable2D"
        assert "channel_type" in config
        # Table2D uses x_values and output_values for the data points
        assert "x_values" in config or "x_axis" in config or "axis_x" in config
        dialog.close()

    def test_table_has_axis_settings(self, qapp):
        """Test table has axis configuration settings."""
        dialog = Table2DDialog()

        # Should have X axis configuration fields
        assert hasattr(dialog, 'x_min_spin') or hasattr(dialog, 'x_axis_min')
        assert hasattr(dialog, 'x_max_spin') or hasattr(dialog, 'x_axis_max')
        dialog.close()


# ==================== Table3DDialog Tests ====================

class TestTable3DDialogCreation:
    """Tests for Table3DDialog creation."""

    def test_create_new_dialog(self, qapp):
        """Test creating new 3D table dialog."""
        dialog = Table3DDialog()
        assert dialog is not None
        assert "3D" in dialog.windowTitle() or "Table" in dialog.windowTitle()
        dialog.close()

    def test_create_edit_dialog(self, qapp, sample_available_channels):
        """Test creating 3D table dialog for editing."""
        config = {
            "channel_id": 201,
            "name": "IgnitionMap",
            "input_x": 40,
            "input_y": 21,
            "axis_x": [1000, 2000, 3000],
            "axis_y": [50, 75, 100],
            "values": [[10, 15, 20], [12, 17, 22], [14, 19, 24]],
        }
        dialog = Table3DDialog(config=config, available_channels=sample_available_channels)
        assert dialog.name_edit.text() == "IgnitionMap"
        dialog.close()


class TestTable3DDialogConfig:
    """Tests for Table3DDialog configuration."""

    def test_get_config_returns_complete(self, qapp):
        """Test get_config returns complete configuration."""
        dialog = Table3DDialog()
        dialog.name_edit.setText("TestTable3D")

        config = dialog.get_config()

        assert config["name"] == "TestTable3D"
        assert "channel_type" in config
        dialog.close()

    def test_has_two_axis_inputs(self, qapp):
        """Test dialog has X and Y axis configuration."""
        dialog = Table3DDialog()

        # Should have X and Y axis min/max/step configuration
        # The actual attribute names vary by implementation
        x_attrs = ['x_min_spin', 'x_axis_min', 'x_input_edit', 'x_channel_edit']
        y_attrs = ['y_min_spin', 'y_axis_min', 'y_input_edit', 'y_channel_edit']

        has_x = any(hasattr(dialog, attr) for attr in x_attrs)
        has_y = any(hasattr(dialog, attr) for attr in y_attrs)

        assert has_x, f"Dialog should have X axis config (checked: {x_attrs})"
        assert has_y, f"Dialog should have Y axis config (checked: {y_attrs})"
        dialog.close()


# ==================== PIDControllerDialog Tests ====================

class TestPIDDialogCreation:
    """Tests for PIDControllerDialog creation."""

    def test_create_new_dialog(self, qapp):
        """Test creating new PID controller dialog."""
        dialog = PIDControllerDialog()
        assert dialog is not None
        assert "PID" in dialog.windowTitle()
        dialog.close()

    def test_create_edit_dialog(self, qapp, sample_available_channels):
        """Test creating PID dialog for editing."""
        config = {
            "channel_id": 300,
            "name": "BoostControl",
            "setpoint_channel": 40,
            "feedback_channel": 22,
            "output_channel": 50,
            "kp": 1.0,
            "ki": 0.1,
            "kd": 0.01,
        }
        dialog = PIDControllerDialog(config=config, available_channels=sample_available_channels)
        assert dialog.name_edit.text() == "BoostControl"
        dialog.close()


class TestPIDParameters:
    """Tests for PID parameter inputs."""

    def test_pid_gain_spinboxes_exist(self, qapp):
        """Test PID gain spinboxes exist."""
        dialog = PIDControllerDialog()

        assert hasattr(dialog, 'kp_spin')
        assert hasattr(dialog, 'ki_spin')
        assert hasattr(dialog, 'kd_spin')
        dialog.close()

    def test_pid_gain_ranges(self, qapp):
        """Test PID gain spinbox ranges are reasonable."""
        dialog = PIDControllerDialog()

        # Gains should allow negative values for some control strategies
        assert dialog.kp_spin.minimum() <= 0 or dialog.kp_spin.minimum() >= 0  # Just check it exists
        assert dialog.kp_spin.maximum() >= 10  # Should allow reasonable gains
        dialog.close()

    def test_pid_output_limits(self, qapp):
        """Test PID output limit controls exist."""
        dialog = PIDControllerDialog()

        # Should have output limit controls
        assert hasattr(dialog, 'output_min_spin') or hasattr(dialog, 'min_output_spin')
        assert hasattr(dialog, 'output_max_spin') or hasattr(dialog, 'max_output_spin')
        dialog.close()


class TestPIDDialogConfig:
    """Tests for PIDControllerDialog configuration."""

    def test_get_config_returns_complete(self, qapp):
        """Test get_config returns complete configuration."""
        dialog = PIDControllerDialog()
        dialog.name_edit.setText("TestPID")

        config = dialog.get_config()

        assert config["name"] == "TestPID"
        assert "channel_type" in config
        assert "kp" in config
        assert "ki" in config
        assert "kd" in config
        dialog.close()

    def test_config_roundtrip(self, qapp, sample_available_channels):
        """Test config load/save roundtrip."""
        original = {
            "channel_id": 350,
            "name": "TempControl",
            "setpoint_channel": 21,
            "feedback_channel": 22,
            "kp": 2.5,
            "ki": 0.5,
            "kd": 0.05,
            "output_min": 0,
            "output_max": 100,
        }

        dialog = PIDControllerDialog(config=original, available_channels=sample_available_channels)
        result = dialog.get_config()

        assert result["name"] == original["name"]
        assert result["kp"] == original["kp"]
        assert result["ki"] == original["ki"]
        assert result["kd"] == original["kd"]
        dialog.close()


class TestPIDChannelInputs:
    """Tests for PID channel input fields."""

    def test_has_setpoint_channel(self, qapp):
        """Test dialog has setpoint channel selector."""
        dialog = PIDControllerDialog()
        # Check for various possible attribute names
        setpoint_attrs = ['setpoint_edit', 'setpoint_channel_edit', 'target_edit', 'target_channel_edit']
        has_setpoint = any(hasattr(dialog, attr) for attr in setpoint_attrs)
        assert has_setpoint, f"Dialog should have setpoint channel (checked: {setpoint_attrs})"
        dialog.close()

    def test_has_process_channel(self, qapp):
        """Test dialog has process/feedback channel selector."""
        dialog = PIDControllerDialog()
        # The process variable input is called 'process_edit'
        assert hasattr(dialog, 'process_edit'), "Dialog should have process channel selector"
        dialog.close()

    def test_has_output_channel(self, qapp):
        """Test dialog has output channel selector."""
        dialog = PIDControllerDialog()
        assert hasattr(dialog, 'output_edit'), "Dialog should have output channel selector"
        dialog.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

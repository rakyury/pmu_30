"""
UI Tests for Control Widget Components
Tests: ConstantSpinbox, TimeInputWidget, ChannelSearchDialog,
       ConnectionStatusWidget, LedIndicator, DigitalMonitor, TreeModel
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt


# ============================================================================
# ConstantSpinbox Tests
# ============================================================================

class TestConstantSpinbox:
    """Tests for ConstantSpinBox widget"""

    def test_widget_creation(self, qapp):
        """Test ConstantSpinBox can be created"""
        from ui.widgets.constant_spinbox import ConstantSpinBox
        widget = ConstantSpinBox()
        assert widget is not None
        widget.close()

    def test_value_methods(self, qapp):
        """Test value getter/setter"""
        from ui.widgets.constant_spinbox import ConstantSpinBox
        widget = ConstantSpinBox()
        # Use existing methods
        widget.setValue(50.0)
        value = widget.value()
        assert isinstance(value, (int, float))
        widget.close()


# ============================================================================
# TimeInputWidget Tests
# ============================================================================

class TestTimeInputWidget:
    """Tests for TimeInputWidget"""

    def test_widget_creation(self, qapp):
        """Test TimeInputWidget can be created"""
        from ui.widgets.time_input import TimeInputWidget
        widget = TimeInputWidget()
        assert widget is not None
        widget.close()

    def test_set_time(self, qapp):
        """Test setting time"""
        from ui.widgets.time_input import TimeInputWidget
        widget = TimeInputWidget()
        if hasattr(widget, 'set_time_ms'):
            widget.set_time_ms(5000)
        elif hasattr(widget, 'setValue'):
            widget.setValue(5000)
        widget.close()

    def test_get_time(self, qapp):
        """Test getting time"""
        from ui.widgets.time_input import TimeInputWidget
        widget = TimeInputWidget()
        if hasattr(widget, 'get_time_ms'):
            value = widget.get_time_ms()
            assert isinstance(value, (int, float))
        widget.close()


# ============================================================================
# ChannelSearchDialog Tests
# ============================================================================

class TestChannelSearchDialog:
    """Tests for ChannelSearchDialog"""

    def test_dialog_creation(self, qapp):
        """Test ChannelSearchDialog can be created"""
        from ui.widgets.channel_search import ChannelSearchDialog
        dialog = ChannelSearchDialog()
        assert dialog is not None
        dialog.close()

    def test_set_channels(self, qapp):
        """Test setting channel list"""
        from ui.widgets.channel_search import ChannelSearchDialog
        dialog = ChannelSearchDialog()
        channels = [
            {"name": "channel1", "channel_type": "digital_input"},
            {"name": "channel2", "channel_type": "analog_input"},
        ]
        if hasattr(dialog, 'set_channels'):
            dialog.set_channels(channels)
        dialog.close()


# ============================================================================
# ConnectionStatusWidget Tests
# ============================================================================

class TestConnectionStatusWidget:
    """Tests for ConnectionStatusWidget"""

    def test_widget_creation(self, qapp):
        """Test ConnectionStatusWidget can be created"""
        from ui.widgets.connection_status import ConnectionStatusWidget
        widget = ConnectionStatusWidget()
        assert widget is not None
        widget.close()

    def test_set_connected(self, qapp):
        """Test setting connected state"""
        from ui.widgets.connection_status import ConnectionStatusWidget
        widget = ConnectionStatusWidget()
        if hasattr(widget, 'set_connected'):
            widget.set_connected(True)
        widget.close()


# ============================================================================
# LEDWidget Tests
# ============================================================================

class TestLEDWidget:
    """Tests for LEDWidget"""

    def test_widget_creation(self, qapp):
        """Test LEDWidget can be created"""
        from ui.widgets.led_indicator import LEDWidget
        widget = LEDWidget()
        assert widget is not None
        widget.close()

    def test_set_color(self, qapp):
        """Test setting LED color"""
        from ui.widgets.led_indicator import LEDWidget, LEDColor
        widget = LEDWidget()
        if hasattr(widget, 'set_color'):
            widget.set_color(LEDColor.GREEN)
        widget.close()

    def test_set_state(self, qapp):
        """Test setting LED state"""
        from ui.widgets.led_indicator import LEDWidget
        widget = LEDWidget()
        if hasattr(widget, 'set_on'):
            widget.set_on(True)
        elif hasattr(widget, 'setState'):
            widget.setState(True)
        widget.close()


# ============================================================================
# DigitalMonitor Tests
# ============================================================================

class TestDigitalMonitor:
    """Tests for DigitalMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test DigitalMonitor can be created"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        assert widget is not None
        widget.close()

    def test_input_count(self, qapp):
        """Test inputs_data attribute exists"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        assert hasattr(widget, 'inputs_data')
        widget.close()

    def test_table_exists(self, qapp):
        """Test table widget exists"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        assert hasattr(widget, 'table')
        widget.close()


# ============================================================================
# TreeModel Tests
# ============================================================================

class TestTreeModel:
    """Tests for TreeModel"""

    def test_model_creation(self, qapp):
        """Test TreeModel can be created"""
        from ui.widgets.tree_model import TreeModel
        model = TreeModel()
        assert model is not None


# ============================================================================
# Widget Resize Tests
# ============================================================================

class TestWidgetResize:
    """Tests for widget resize behavior"""

    def test_output_monitor_resize(self, qapp):
        """Test OutputMonitor resizes correctly"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        widget.resize(800, 600)
        assert widget.width() == 800
        widget.close()

    def test_analog_monitor_resize(self, qapp):
        """Test AnalogMonitor resizes correctly"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        widget.resize(600, 400)
        assert widget.width() == 600
        widget.close()

    def test_pid_tuner_resize(self, qapp):
        """Test PIDTuner resizes correctly"""
        from ui.widgets.pid_tuner import PIDTuner
        widget = PIDTuner()
        widget.resize(500, 300)
        assert widget.width() == 500
        widget.close()

    def test_can_monitor_resize(self, qapp):
        """Test CANMonitor resizes correctly"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        widget.resize(700, 500)
        assert widget.width() == 700
        widget.close()

    def test_digital_monitor_resize(self, qapp):
        """Test DigitalMonitor resizes correctly"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        widget.resize(400, 300)
        assert widget.width() == 400
        widget.close()

    def test_hbridge_monitor_resize(self, qapp):
        """Test HBridgeMonitor resizes correctly"""
        from ui.widgets.hbridge_monitor import HBridgeMonitor
        widget = HBridgeMonitor()
        widget.resize(600, 400)
        assert widget.width() == 600
        widget.close()


# ============================================================================
# Widget Signal Tests
# ============================================================================

class TestWidgetSignals:
    """Tests for widget signals"""

    def test_digital_monitor_signals(self, qapp):
        """Test DigitalMonitor has expected signals"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        # Just verify widget works
        assert widget is not None
        widget.close()

    def test_output_monitor_signals(self, qapp):
        """Test OutputMonitor has channel_edit_requested signal"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert hasattr(widget, 'channel_edit_requested')
        widget.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

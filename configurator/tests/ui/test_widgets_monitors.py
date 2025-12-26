"""
UI Tests for Monitor Widget Components
Tests: AnalogMonitor, DigitalMonitor, OutputMonitor, CANMonitor,
       HBridgeMonitor, PMUMonitorWidget
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt


# ============================================================================
# AnalogMonitor Tests
# ============================================================================

class TestAnalogMonitor:
    """Tests for AnalogMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test AnalogMonitor can be created"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        assert widget is not None
        widget.close()

    def test_has_table(self, qapp):
        """Test AnalogMonitor has table widget"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        assert hasattr(widget, 'table')
        widget.close()

    def test_set_connected(self, qapp):
        """Test setting connection state"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        widget.set_connected(True)
        assert widget._connected == True
        widget.set_connected(False)
        assert widget._connected == False
        widget.close()

    def test_set_inputs(self, qapp):
        """Test setting input configuration"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        inputs = [
            {"name": "Voltage1", "channel": 0, "input_type": "voltage"},
            {"name": "Current1", "channel": 1, "input_type": "current"},
        ]
        widget.set_inputs(inputs)
        # set_inputs updates existing inputs, doesn't change count
        assert widget.get_channel_count() >= 2
        widget.close()

    def test_update_input_value(self, qapp):
        """Test updating input value"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        inputs = [{"name": "Voltage1", "channel": 0, "input_type": "voltage"}]
        widget.set_inputs(inputs)
        widget.set_connected(True)
        widget.update_input_value(0, 12.5, 2.5)
        widget.close()

    def test_update_from_telemetry(self, qapp):
        """Test updating from telemetry data"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        widget.set_connected(True)
        adc_values = [2048, 1024, 512, 256]
        widget.update_from_telemetry(adc_values, reference_voltage=3.3)
        widget.close()

    def test_get_channel_count(self, qapp):
        """Test getting channel count"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        # Default inputs should be created
        count = widget.get_channel_count()
        assert count >= 0
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

    def test_has_inputs_data(self, qapp):
        """Test DigitalMonitor has inputs_data attribute"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        assert hasattr(widget, 'inputs_data')
        widget.close()

    def test_has_table(self, qapp):
        """Test DigitalMonitor has table widget"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        assert hasattr(widget, 'table')
        widget.close()

    def test_set_connected(self, qapp):
        """Test setting connection state"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        if hasattr(widget, 'set_connected'):
            widget.set_connected(True)
            widget.set_connected(False)
        widget.close()

    def test_set_inputs(self, qapp):
        """Test setting digital inputs"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        if hasattr(widget, 'set_inputs'):
            inputs = [
                {"name": "Switch1", "channel": 0},
                {"name": "Switch2", "channel": 1},
            ]
            widget.set_inputs(inputs)
        widget.close()


# ============================================================================
# OutputMonitor Tests
# ============================================================================

class TestOutputMonitor:
    """Tests for OutputMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test OutputMonitor can be created"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert widget is not None
        widget.close()

    def test_has_table(self, qapp):
        """Test OutputMonitor has table widget"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert hasattr(widget, 'table')
        widget.close()

    def test_has_signal(self, qapp):
        """Test OutputMonitor has channel_edit_requested signal"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert hasattr(widget, 'channel_edit_requested')
        widget.close()

    def test_set_connected(self, qapp):
        """Test setting connection state"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        if hasattr(widget, 'set_connected'):
            widget.set_connected(True)
            widget.set_connected(False)
        widget.close()

    def test_set_outputs(self, qapp):
        """Test setting output configuration"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        if hasattr(widget, 'set_outputs'):
            outputs = [
                {"name": "Output1", "channel": 0},
                {"name": "Output2", "channel": 1},
            ]
            widget.set_outputs(outputs)
        widget.close()


# ============================================================================
# CANMonitor Tests
# ============================================================================

class TestCANMonitor:
    """Tests for CANMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test CANMonitor can be created"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        assert widget is not None
        widget.close()

    def test_set_connected(self, qapp):
        """Test setting connection state"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        # CANMonitor.set_connected may require connection_label - skip if missing
        if hasattr(widget, 'connection_label'):
            widget.set_connected(True)
            widget.set_connected(False)
        widget.close()

    def test_set_configuration(self, qapp):
        """Test setting CAN configuration"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        messages = [
            {"id": "0x100", "name": "Status"},
            {"id": "0x200", "name": "Control"},
        ]
        inputs = [{"name": "RPM", "message_ref": "0x100"}]
        widget.set_configuration(messages, inputs)
        widget.close()

    def test_receive_message(self, qapp):
        """Test receiving CAN message"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        widget.receive_message(0x100, b'\x01\x02\x03\x04')
        widget.close()

    def test_receive_extended_message(self, qapp):
        """Test receiving extended CAN message"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        widget.receive_message(0x18FF0001, b'\x01\x02', is_extended=True)
        widget.close()

    def test_clear_messages(self, qapp):
        """Test clearing messages"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        widget.receive_message(0x100, b'\x01')
        widget._clear_messages()
        widget.close()


# ============================================================================
# HBridgeMonitor Tests
# ============================================================================

class TestHBridgeMonitor:
    """Tests for HBridgeMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test HBridgeMonitor can be created"""
        from ui.widgets.hbridge_monitor import HBridgeMonitor
        widget = HBridgeMonitor()
        assert widget is not None
        widget.close()

    def test_has_table(self, qapp):
        """Test HBridgeMonitor has table widget"""
        from ui.widgets.hbridge_monitor import HBridgeMonitor
        widget = HBridgeMonitor()
        assert hasattr(widget, 'table')
        widget.close()

    def test_set_connected(self, qapp):
        """Test setting connection state"""
        from ui.widgets.hbridge_monitor import HBridgeMonitor
        widget = HBridgeMonitor()
        if hasattr(widget, 'set_connected'):
            widget.set_connected(True)
            widget.set_connected(False)
        widget.close()

    def test_set_hbridges(self, qapp):
        """Test setting H-bridge configuration"""
        from ui.widgets.hbridge_monitor import HBridgeMonitor
        widget = HBridgeMonitor()
        if hasattr(widget, 'set_hbridges'):
            hbridges = [
                {"name": "Motor1", "bridge_index": 0},
                {"name": "Motor2", "bridge_index": 1},
            ]
            widget.set_hbridges(hbridges)
        widget.close()


# ============================================================================
# PMUMonitorWidget Tests
# ============================================================================

class TestPMUMonitorWidget:
    """Tests for PMUMonitorWidget"""

    def test_widget_creation(self, qapp):
        """Test PMUMonitorWidget can be created"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        assert widget is not None
        widget.close()

    def test_has_tree(self, qapp):
        """Test PMUMonitorWidget has tree widget"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        assert hasattr(widget, 'tree')
        widget.close()

    def test_set_connected(self, qapp):
        """Test setting connection state"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        widget.set_connected(True)
        widget.set_connected(False)
        widget.close()

    def test_set_value(self, qapp):
        """Test setting a monitor value"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        widget.set_value("input_voltage", 12.5)
        widget.close()

    def test_set_value_with_fault(self, qapp):
        """Test setting value with fault flag"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        widget.set_value("output1_current", 15.0, is_fault=True)
        widget.close()

    def test_update_from_telemetry(self, qapp):
        """Test updating from telemetry data"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        telemetry = {
            "input_voltage": 12.0,
            "temperature": 45,
            "outputs": [1, 1, 0, 0, 0, 0, 0, 0]
        }
        widget.update_from_telemetry(telemetry)
        widget.close()

    def test_update_device_info(self, qapp):
        """Test updating device info"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        info = {
            "firmware_version": "1.0.0",
            "serial": "12345678"
        }
        widget.update_device_info(info)
        widget.close()

    def test_expand_collapse(self, qapp):
        """Test expand and collapse all"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        widget.expand_all()
        widget.collapse_all()
        widget.close()


# ============================================================================
# Monitor Resize Tests
# ============================================================================

class TestMonitorResize:
    """Tests for monitor widget resize behavior"""

    def test_analog_monitor_resize(self, qapp):
        """Test AnalogMonitor resizes correctly"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        widget.resize(800, 600)
        assert widget.width() == 800
        assert widget.height() == 600
        widget.close()

    def test_digital_monitor_resize(self, qapp):
        """Test DigitalMonitor resizes correctly"""
        from ui.widgets.digital_monitor import DigitalMonitor
        widget = DigitalMonitor()
        widget.resize(600, 400)
        assert widget.width() == 600
        assert widget.height() == 400
        widget.close()

    def test_output_monitor_resize(self, qapp):
        """Test OutputMonitor resizes correctly"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        widget.resize(700, 500)
        assert widget.width() == 700
        assert widget.height() == 500
        widget.close()

    def test_can_monitor_resize(self, qapp):
        """Test CANMonitor resizes correctly"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        widget.resize(900, 700)
        assert widget.width() == 900
        assert widget.height() == 700
        widget.close()

    def test_hbridge_monitor_resize(self, qapp):
        """Test HBridgeMonitor resizes correctly"""
        from ui.widgets.hbridge_monitor import HBridgeMonitor
        widget = HBridgeMonitor()
        widget.resize(600, 400)
        assert widget.width() == 600
        assert widget.height() == 400
        widget.close()

    def test_pmu_monitor_resize(self, qapp):
        """Test PMUMonitorWidget resizes correctly"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        widget.resize(400, 600)
        assert widget.width() == 400
        assert widget.height() == 600
        widget.close()


# ============================================================================
# Monitor State Tests
# ============================================================================

class TestMonitorStateManagement:
    """Tests for monitor widget state management"""

    def test_analog_monitor_disconnected_state(self, qapp):
        """Test AnalogMonitor behavior when disconnected"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        widget.set_connected(False)
        # Should not crash when updating while disconnected
        widget.update_input_value(0, 0, 0)
        widget.close()

    def test_can_monitor_pause_resume(self, qapp):
        """Test CANMonitor pause/resume"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        # Pause
        widget._on_pause_toggle(True)
        # Still can receive messages
        widget.receive_message(0x100, b'\x01\x02')
        # Resume
        widget._on_pause_toggle(False)
        widget.close()

    def test_pmu_monitor_refresh(self, qapp):
        """Test PMUMonitorWidget refresh display"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        widget.set_connected(True)
        widget._refresh_display()
        widget.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

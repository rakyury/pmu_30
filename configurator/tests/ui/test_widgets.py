"""
UI Tests for Widget Components
Tests: ProjectTree, OutputMonitor, AnalogMonitor, VariablesInspector,
       PMUMonitor, ChannelGraph, CANMonitor, DataLogger, etc.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QWidget, QTreeWidget, QTableWidget
from PyQt6.QtCore import Qt


class TestProjectTree:
    """Tests for ProjectTree widget"""

    def test_widget_creation(self, qapp):
        """Test ProjectTree can be created"""
        from ui.widgets.project_tree import ProjectTree
        widget = ProjectTree()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()

    def test_tree_widget_exists(self, qapp):
        """Test tree widget is created"""
        from ui.widgets.project_tree import ProjectTree
        widget = ProjectTree()
        assert hasattr(widget, 'tree')
        assert isinstance(widget.tree, QTreeWidget)
        widget.close()

    def test_folder_structure_created(self, qapp):
        """Test folder structure is created"""
        from ui.widgets.project_tree import ProjectTree
        widget = ProjectTree()

        # Check top level items exist
        top_level_count = widget.tree.topLevelItemCount()
        assert top_level_count > 0

        # Check expected folders
        folder_texts = []
        for i in range(top_level_count):
            folder_texts.append(widget.tree.topLevelItem(i).text(0))

        assert any("Input" in t for t in folder_texts)
        assert any("Output" in t for t in folder_texts)
        assert any("Function" in t for t in folder_texts)
        widget.close()

    def test_signals_defined(self, qapp):
        """Test signals are defined"""
        from ui.widgets.project_tree import ProjectTree
        widget = ProjectTree()

        assert hasattr(widget, 'item_selected')
        assert hasattr(widget, 'item_added')
        assert hasattr(widget, 'item_edited')
        assert hasattr(widget, 'item_deleted')
        assert hasattr(widget, 'configuration_changed')
        widget.close()

    def test_buttons_exist(self, qapp):
        """Test add/edit/delete buttons exist"""
        from ui.widgets.project_tree import ProjectTree
        widget = ProjectTree()

        assert hasattr(widget, 'add_btn')
        assert hasattr(widget, 'edit_btn')
        assert hasattr(widget, 'delete_btn')
        widget.close()

    def test_get_all_channels(self, qapp):
        """Test getting all channels from tree"""
        from ui.widgets.project_tree import ProjectTree
        widget = ProjectTree()

        # get_all_channels should return empty list initially
        channels = widget.get_all_channels()
        assert isinstance(channels, list)
        widget.close()


class TestOutputMonitor:
    """Tests for OutputMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test OutputMonitor can be created"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()

    def test_table_widget_exists(self, qapp):
        """Test table widget is created"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert hasattr(widget, 'table')
        assert isinstance(widget.table, QTableWidget)
        widget.close()

    def test_default_outputs_initialized(self, qapp):
        """Test default 30 outputs are initialized"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert len(widget.outputs_data) == 30
        widget.close()

    def test_columns_count(self, qapp):
        """Test correct number of columns"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert widget.table.columnCount() >= 5  # At least basic columns
        widget.close()

    def test_reset_peaks_button(self, qapp):
        """Test reset peaks button exists"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert hasattr(widget, 'reset_peaks_btn')
        widget.close()

    def test_update_timer_started(self, qapp):
        """Test update timer is started"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()
        assert hasattr(widget, 'update_timer')
        assert widget.update_timer.isActive()
        widget.close()

    def test_set_outputs(self, qapp):
        """Test setting output configurations"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()

        outputs = [
            {"channel": 0, "name": "Fuel Pump", "enabled": True, "pins": [0]},
            {"channel": 1, "name": "Fan", "enabled": True, "pins": [1]},
        ]
        widget.set_outputs(outputs)

        assert len(widget.outputs_data) >= 2
        widget.close()


class TestAnalogMonitor:
    """Tests for AnalogMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test AnalogMonitor can be created"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()

    def test_table_widget_exists(self, qapp):
        """Test table widget is created"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()
        assert hasattr(widget, 'table')
        assert isinstance(widget.table, QTableWidget)
        widget.close()


class TestVariablesInspector:
    """Tests for VariablesInspector widget"""

    def test_widget_creation(self, qapp):
        """Test VariablesInspector can be created"""
        from ui.widgets.variables_inspector import VariablesInspector
        widget = VariablesInspector()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()

    def test_table_widget_exists(self, qapp):
        """Test table widget is created"""
        from ui.widgets.variables_inspector import VariablesInspector
        widget = VariablesInspector()
        assert hasattr(widget, 'table')
        widget.close()


class TestPMUMonitor:
    """Tests for PMUMonitorWidget"""

    def test_widget_creation(self, qapp):
        """Test PMUMonitorWidget can be created"""
        from ui.widgets.pmu_monitor import PMUMonitorWidget
        widget = PMUMonitorWidget()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()


class TestHBridgeMonitor:
    """Tests for HBridgeMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test HBridgeMonitor can be created"""
        from ui.widgets.hbridge_monitor import HBridgeMonitor
        widget = HBridgeMonitor()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()

    def test_signal_defined(self, qapp):
        """Test hbridge_command signal is defined"""
        from ui.widgets.hbridge_monitor import HBridgeMonitor
        widget = HBridgeMonitor()
        assert hasattr(widget, 'hbridge_command')
        widget.close()


class TestPIDTuner:
    """Tests for PIDTuner widget"""

    def test_widget_creation(self, qapp):
        """Test PIDTuner can be created"""
        from ui.widgets.pid_tuner import PIDTuner
        widget = PIDTuner()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()

    def test_signals_defined(self, qapp):
        """Test signals are defined"""
        from ui.widgets.pid_tuner import PIDTuner
        widget = PIDTuner()
        assert hasattr(widget, 'parameters_changed')
        assert hasattr(widget, 'controller_reset')
        widget.close()


class TestCANMonitor:
    """Tests for CANMonitor widget"""

    def test_widget_creation(self, qapp):
        """Test CANMonitor can be created"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()

    def test_send_message_signal_defined(self, qapp):
        """Test send_message signal is defined"""
        from ui.widgets.can_monitor import CANMonitor
        widget = CANMonitor()
        assert hasattr(widget, 'send_message')
        widget.close()


class TestDataLogger:
    """Tests for DataLoggerWidget"""

    def test_widget_creation(self, qapp):
        """Test DataLoggerWidget can be created"""
        from ui.widgets.data_logger import DataLoggerWidget
        widget = DataLoggerWidget()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()


class TestChannelGraph:
    """Tests for ChannelGraphWidget"""

    def test_widget_creation(self, qapp):
        """Test ChannelGraphWidget can be created"""
        from ui.widgets.channel_graph import ChannelGraphWidget
        widget = ChannelGraphWidget()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()

    def test_signals_defined(self, qapp):
        """Test signals are defined"""
        from ui.widgets.channel_graph import ChannelGraphWidget
        widget = ChannelGraphWidget()
        assert hasattr(widget, 'channel_selected')
        assert hasattr(widget, 'channel_edit_requested')
        assert hasattr(widget, 'refresh_requested')
        widget.close()

    def test_set_channels(self, qapp, sample_channels):
        """Test setting channels"""
        from ui.widgets.channel_graph import ChannelGraphWidget
        widget = ChannelGraphWidget()
        widget.set_channels(sample_channels)
        assert widget.channels == sample_channels
        widget.close()

    def test_rebuild_graph(self, qapp, sample_channels):
        """Test rebuilding graph"""
        from ui.widgets.channel_graph import ChannelGraphWidget
        widget = ChannelGraphWidget()
        widget.set_channels(sample_channels)
        widget._rebuild_graph()
        widget.close()


class TestLogViewer:
    """Tests for LogViewerWidget"""

    def test_widget_creation(self, qapp):
        """Test LogViewerWidget can be created"""
        from ui.widgets.log_viewer import LogViewerWidget
        widget = LogViewerWidget()
        assert widget is not None
        assert isinstance(widget, QWidget)
        widget.close()


class TestLuaEditor:
    """Tests for Lua Editor widget"""

    def test_widget_creation(self, qapp):
        """Test LuaEditor can be created"""
        try:
            from ui.widgets.lua_editor import LuaEditor
            widget = LuaEditor()
            assert widget is not None
            widget.close()
        except ImportError:
            pytest.skip("LuaEditor not available")


class TestWidgetUpdates:
    """Tests for widget update functionality"""

    def test_output_monitor_update_status(self, qapp):
        """Test output monitor can receive status updates"""
        from ui.widgets.output_monitor import OutputMonitor
        widget = OutputMonitor()

        # Test update_output_status method
        widget.update_output_status(0, "on", 12.5, 50.0)
        widget.close()

    def test_analog_monitor_update_value(self, qapp):
        """Test analog monitor can receive value updates"""
        from ui.widgets.analog_monitor import AnalogMonitor
        widget = AnalogMonitor()

        # Test update_input_value method
        widget.update_input_value(0, 50.0, 2.5)
        widget.close()


class TestWidgetIntegration:
    """Integration tests for widget interactions"""

    def test_project_tree_channel_types(self, qapp):
        """Test project tree has all channel types"""
        from ui.widgets.project_tree import ProjectTree
        from models.channel import ChannelType

        widget = ProjectTree()

        # Check that channel_type_folders dict is populated
        assert len(widget.channel_type_folders) > 0
        widget.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

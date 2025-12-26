"""
UI Tests for Tab Widgets
Tests: InputsTab, OutputsTab, LogicTab, CANTab, HBridgeTab, PIDTab, SettingsTab
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


class TestBaseTab:
    """Tests for BaseTab base class"""

    def test_base_tab_import(self, qapp):
        """Test BaseTab can be imported"""
        from ui.tabs.base_tab import BaseTab
        assert BaseTab is not None

    def test_base_tab_creation(self, qapp):
        """Test BaseTab creation"""
        from ui.tabs.base_tab import BaseTab
        tab = BaseTab()
        assert tab is not None
        tab.close()

    def test_base_tab_signal_exists(self, qapp):
        """Test configuration_changed signal exists"""
        from ui.tabs.base_tab import BaseTab
        tab = BaseTab()
        assert hasattr(tab, 'configuration_changed')
        tab.close()

    def test_validate_configuration_default(self, qapp):
        """Test default validation returns True"""
        from ui.tabs.base_tab import BaseTab
        tab = BaseTab()
        is_valid, error = tab.validate_configuration()
        assert is_valid is True
        assert error == ""
        tab.close()


class TestInputsTab:
    """Tests for InputsTab"""

    def test_tab_creation(self, qapp):
        """Test InputsTab creation"""
        from ui.tabs.inputs_tab import InputsTab
        tab = InputsTab()
        assert tab is not None
        assert hasattr(tab, 'table')
        assert hasattr(tab, 'inputs')
        tab.close()

    def test_tab_has_buttons(self, qapp):
        """Test InputsTab has CRUD buttons"""
        from ui.tabs.inputs_tab import InputsTab
        tab = InputsTab()
        assert hasattr(tab, 'add_btn')
        assert hasattr(tab, 'edit_btn')
        assert hasattr(tab, 'delete_btn')
        assert hasattr(tab, 'duplicate_btn')
        tab.close()

    def test_table_columns(self, qapp):
        """Test InputsTab table has correct columns"""
        from ui.tabs.inputs_tab import InputsTab
        tab = InputsTab()
        assert tab.table.columnCount() == 6
        tab.close()

    def test_load_empty_configuration(self, qapp):
        """Test loading empty configuration"""
        from ui.tabs.inputs_tab import InputsTab
        tab = InputsTab()
        config = {"channels": []}
        tab.load_configuration(config)
        assert len(tab.inputs) == 0
        tab.close()

    def test_load_configuration_with_inputs(self, qapp):
        """Test loading configuration with inputs"""
        from ui.tabs.inputs_tab import InputsTab
        tab = InputsTab()
        config = {
            "inputs": [
                {
                    "id": "input_1",
                    "channel_type": "analog_input",
                    "name": "Temperature",
                    "subtype": "linear"
                },
                {
                    "id": "input_2",
                    "channel_type": "digital_input",
                    "name": "Switch",
                    "subtype": "switch_active_low"
                }
            ]
        }
        tab.load_configuration(config)
        assert len(tab.inputs) == 2
        tab.close()


class TestOutputsTab:
    """Tests for OutputsTab"""

    def test_tab_creation(self, qapp):
        """Test OutputsTab creation"""
        from ui.tabs.outputs_tab import OutputsTab
        tab = OutputsTab()
        assert tab is not None
        tab.close()

    def test_tab_has_table(self, qapp):
        """Test OutputsTab has output table"""
        from ui.tabs.outputs_tab import OutputsTab
        tab = OutputsTab()
        assert hasattr(tab, 'table')
        tab.close()


class TestLogicTab:
    """Tests for LogicTab"""

    def test_tab_creation(self, qapp):
        """Test LogicTab creation"""
        from ui.tabs.logic_tab import LogicTab
        tab = LogicTab()
        assert tab is not None
        tab.close()

    def test_tab_has_logic_list(self, qapp):
        """Test LogicTab has logic functions list"""
        from ui.tabs.logic_tab import LogicTab
        tab = LogicTab()
        assert hasattr(tab, 'table') or hasattr(tab, 'list_widget') or hasattr(tab, 'logic_functions')
        tab.close()


class TestCANTab:
    """Tests for CANTab"""

    def test_tab_creation(self, qapp):
        """Test CANTab creation"""
        from ui.tabs.can_tab import CANTab
        tab = CANTab()
        assert tab is not None
        tab.close()

    def test_tab_components(self, qapp):
        """Test CANTab has expected components"""
        from ui.tabs.can_tab import CANTab
        tab = CANTab()
        # CAN tab should have message management
        assert hasattr(tab, 'messages_table') or hasattr(tab, 'can_messages')
        tab.close()


class TestHBridgeTab:
    """Tests for HBridgeTab"""

    def test_tab_creation(self, qapp):
        """Test HBridgeTab creation"""
        from ui.tabs.hbridge_tab import HBridgeTab
        tab = HBridgeTab()
        assert tab is not None
        tab.close()

    def test_tab_has_hbridge_widgets(self, qapp):
        """Test HBridgeTab has H-Bridge configuration widgets"""
        from ui.tabs.hbridge_tab import HBridgeTab
        tab = HBridgeTab()
        # Should have table or list for h-bridges
        assert hasattr(tab, 'table') or hasattr(tab, 'hbridges')
        tab.close()


class TestPIDTab:
    """Tests for PIDTab"""

    def test_tab_creation(self, qapp):
        """Test PIDTab creation"""
        from ui.tabs.pid_tab import PIDTab
        tab = PIDTab()
        assert tab is not None
        tab.close()

    def test_tab_has_pid_list(self, qapp):
        """Test PIDTab has PID controllers list"""
        from ui.tabs.pid_tab import PIDTab
        tab = PIDTab()
        assert hasattr(tab, 'table') or hasattr(tab, 'pid_list')
        tab.close()


class TestLuaTab:
    """Tests for LuaTab"""

    def test_tab_creation(self, qapp):
        """Test LuaTab creation"""
        from ui.tabs.lua_tab import LuaTab
        tab = LuaTab()
        assert tab is not None
        tab.close()

    def test_tab_has_editor(self, qapp):
        """Test LuaTab has script management"""
        from ui.tabs.lua_tab import LuaTab
        tab = LuaTab()
        # LuaTab uses table and lua_scripts list for script management
        assert hasattr(tab, 'table') or hasattr(tab, 'lua_scripts')
        tab.close()


class TestSettingsTab:
    """Tests for SettingsTab"""

    def test_tab_creation(self, qapp):
        """Test SettingsTab creation"""
        from ui.tabs.settings_tab import SettingsTab
        tab = SettingsTab()
        assert tab is not None
        tab.close()

    def test_tab_has_system_settings(self, qapp):
        """Test SettingsTab has system settings widgets"""
        from ui.tabs.settings_tab import SettingsTab
        tab = SettingsTab()
        # Should have settings widgets
        assert tab is not None
        tab.close()


class TestMonitoringTab:
    """Tests for MonitoringTab"""

    def test_tab_creation(self, qapp):
        """Test MonitoringTab creation"""
        from ui.tabs.monitoring_tab import MonitoringTab
        tab = MonitoringTab()
        assert tab is not None
        tab.close()


class TestTabsIntegration:
    """Integration tests for tabs"""

    def test_all_tabs_can_be_created(self, qapp):
        """Test all tabs can be instantiated without errors"""
        from ui.tabs.inputs_tab import InputsTab
        from ui.tabs.outputs_tab import OutputsTab
        from ui.tabs.logic_tab import LogicTab
        from ui.tabs.can_tab import CANTab
        from ui.tabs.hbridge_tab import HBridgeTab
        from ui.tabs.pid_tab import PIDTab
        from ui.tabs.lua_tab import LuaTab
        from ui.tabs.settings_tab import SettingsTab
        from ui.tabs.monitoring_tab import MonitoringTab

        tabs = [
            InputsTab(),
            OutputsTab(),
            LogicTab(),
            CANTab(),
            HBridgeTab(),
            PIDTab(),
            LuaTab(),
            SettingsTab(),
            MonitoringTab(),
        ]

        for tab in tabs:
            assert tab is not None
            tab.close()

    def test_tabs_inherit_from_base(self, qapp):
        """Test key tabs inherit from BaseTab"""
        from ui.tabs.base_tab import BaseTab
        from ui.tabs.inputs_tab import InputsTab
        from ui.tabs.outputs_tab import OutputsTab

        # InputsTab and OutputsTab inherit from BaseTab
        assert issubclass(InputsTab, BaseTab)
        assert issubclass(OutputsTab, BaseTab)
        # Note: Some tabs like LogicTab inherit directly from QWidget

    def test_tabs_have_configuration_signal(self, qapp):
        """Test all tabs have configuration_changed signal"""
        from ui.tabs.inputs_tab import InputsTab
        from ui.tabs.outputs_tab import OutputsTab
        from ui.tabs.logic_tab import LogicTab

        tabs = [InputsTab(), OutputsTab(), LogicTab()]

        for tab in tabs:
            assert hasattr(tab, 'configuration_changed')
            tab.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

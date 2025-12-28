"""
UI Tests for Main Window and Menu System
Tests: MainWindowProfessional, menus, docks, actions
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QMenuBar, QDockWidget, QTabWidget
from PyQt6.QtCore import Qt


@contextmanager
def mock_main_window_deps():
    """Context manager to properly mock MainWindow dependencies."""
    mock_config = MagicMock()
    mock_config.is_modified.return_value = False  # Prevent "Unsaved Changes" dialog
    mock_config.get_config.return_value = {"channels": [], "can_messages": [], "device": {}}

    with patch('ui.main_window_professional.DeviceController'), \
         patch('ui.main_window_professional.ConfigManager', return_value=mock_config):
        yield mock_config


class TestMainWindowCreation:
    """Tests for MainWindowProfessional creation and initialization"""

    def test_window_creation(self, qapp):
        """Test main window can be created"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert window is not None
            assert isinstance(window, QMainWindow)
            window.force_close()

    def test_window_title(self, qapp):
        """Test window has correct title"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert "PMU-30" in window.windowTitle()
            assert "Configurator" in window.windowTitle()
            window.force_close()

    def test_dock_widgets_created(self, qapp):
        """Test dock widgets are created"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            # Check main docks exist
            assert hasattr(window, 'project_tree_dock')
            assert hasattr(window, 'monitor_dock')
            assert isinstance(window.project_tree_dock, QDockWidget)
            assert isinstance(window.monitor_dock, QDockWidget)
            window.force_close()

    def test_monitor_tabs_created(self, qapp):
        """Test monitor tabs are created"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'monitor_tabs')
            assert isinstance(window.monitor_tabs, QTabWidget)
            assert window.monitor_tabs.count() > 0
            window.force_close()

    def test_project_tree_created(self, qapp):
        """Test project tree widget is created"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'project_tree')
            window.force_close()


class TestMainWindowMenus:
    """Tests for menu bar and actions"""

    def test_menubar_exists(self, qapp):
        """Test menu bar is created"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            menubar = window.menuBar()
            assert menubar is not None
            assert isinstance(menubar, QMenuBar)
            window.force_close()

    def test_file_menu_exists(self, qapp):
        """Test File menu exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            menubar = window.menuBar()
            actions = [a.text() for a in menubar.actions()]
            assert any("File" in a for a in actions)
            window.force_close()

    def test_edit_menu_exists(self, qapp):
        """Test Edit menu exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            menubar = window.menuBar()
            actions = [a.text() for a in menubar.actions()]
            assert any("Edit" in a for a in actions)
            window.force_close()

    def test_device_menu_exists(self, qapp):
        """Test Device menu exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            menubar = window.menuBar()
            actions = [a.text() for a in menubar.actions()]
            assert any("Device" in a for a in actions)
            window.force_close()

    def test_file_menu_actions(self, qapp):
        """Test File menu has expected actions"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            menubar = window.menuBar()
            file_menu = None
            for action in menubar.actions():
                if "File" in action.text():
                    file_menu = action.menu()
                    break

            assert file_menu is not None

            action_texts = [a.text() for a in file_menu.actions()]
            assert any("New" in t for t in action_texts)
            assert any("Open" in t for t in action_texts)
            assert any("Save" in t for t in action_texts)
            assert any("Exit" in t for t in action_texts)
            window.force_close()

    def test_device_menu_actions(self, qapp):
        """Test Device menu has expected actions"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            menubar = window.menuBar()
            device_menu = None
            for action in menubar.actions():
                if "Device" in action.text():
                    device_menu = action.menu()
                    break

            assert device_menu is not None

            action_texts = [a.text() for a in device_menu.actions()]
            assert any("Connect" in t for t in action_texts)
            assert any("Disconnect" in t for t in action_texts)
            assert any("Flash" in t or "Save" in t for t in action_texts)
            window.force_close()


class TestMainWindowStatusBar:
    """Tests for status bar"""

    def test_statusbar_exists(self, qapp):
        """Test status bar is created"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            statusbar = window.statusBar()
            assert statusbar is not None
            window.force_close()


class TestMainWindowMonitorTabs:
    """Tests for monitor tab widgets"""

    def test_pmu_monitor_tab(self, qapp):
        """Test PMU monitor tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'pmu_monitor')
            window.force_close()

    def test_output_monitor_tab(self, qapp):
        """Test Output monitor tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'output_monitor')
            window.force_close()

    def test_analog_monitor_tab(self, qapp):
        """Test Analog monitor tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'analog_monitor')
            window.force_close()

    def test_hbridge_monitor_tab(self, qapp):
        """Test H-Bridge monitor tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'hbridge_monitor')
            window.force_close()

    def test_variables_inspector_tab(self, qapp):
        """Test Variables inspector tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'variables_inspector')
            window.force_close()

    def test_pid_tuner_tab(self, qapp):
        """Test PID tuner tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'pid_tuner')
            window.force_close()

    def test_can_monitor_tab(self, qapp):
        """Test CAN monitor tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'can_monitor')
            window.force_close()

    def test_data_logger_tab(self, qapp):
        """Test Data logger tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'data_logger')
            window.force_close()

    def test_channel_graph_tab(self, qapp):
        """Test Channel graph tab exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'channel_graph')
            window.force_close()


class TestMainWindowActions:
    """Tests for main window action methods"""

    def test_new_configuration_method_exists(self, qapp):
        """Test new_configuration method exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'new_configuration')
            assert callable(window.new_configuration)
            window.force_close()

    def test_save_configuration_method_exists(self, qapp):
        """Test save_configuration method exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'save_configuration')
            assert callable(window.save_configuration)
            window.force_close()

    def test_open_configuration_method_exists(self, qapp):
        """Test open_configuration method exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'open_configuration')
            assert callable(window.open_configuration)
            window.force_close()

    def test_connect_device_method_exists(self, qapp):
        """Test connect_device method exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'connect_device')
            assert callable(window.connect_device)
            window.force_close()

    def test_disconnect_device_method_exists(self, qapp):
        """Test disconnect_device method exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'disconnect_device')
            assert callable(window.disconnect_device)
            window.force_close()


class TestMainWindowSignals:
    """Tests for main window signals"""

    def test_configuration_changed_signal_exists(self, qapp):
        """Test configuration_changed signal exists"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'configuration_changed')
            window.force_close()


class TestMainWindowConfigManager:
    """Tests for config manager integration"""

    def test_config_manager_initialized(self, qapp):
        """Test config manager is initialized"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'config_manager')
            window.force_close()

    def test_device_controller_initialized(self, qapp):
        """Test device controller is initialized"""
        with mock_main_window_deps():
            from ui.main_window_professional import MainWindowProfessional
            window = MainWindowProfessional()

            assert hasattr(window, 'device_controller')
            window.force_close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

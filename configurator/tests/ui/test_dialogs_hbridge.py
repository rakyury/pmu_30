"""
UI Tests for H-Bridge Related Dialogs
Tests: HBridgeDialog, WiperDialog, BlinkerDialog, BlinkMarineKeypadDialog,
       HandlerDialog, CANInputDialog, CANOutputDialog
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt


# ============================================================================
# HBridgeDialog Tests
# ============================================================================

class TestHBridgeDialog:
    """Tests for HBridgeDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new H-Bridge dialog"""
        from ui.dialogs.hbridge_dialog import HBridgeDialog
        dialog = HBridgeDialog()
        assert dialog is not None
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        from ui.dialogs.hbridge_dialog import HBridgeDialog
        config = {
            "channel_id": 1,
            "channel_name": "Motor1",
            "output_index": 0,
        }
        dialog = HBridgeDialog(hbridge_config=config)
        assert dialog is not None
        dialog.close()

    def test_get_config(self, qapp):
        """Test getting configuration from dialog"""
        from ui.dialogs.hbridge_dialog import HBridgeDialog
        dialog = HBridgeDialog()

        config = dialog.get_config()

        assert isinstance(config, dict)
        dialog.close()

    def test_with_used_bridges(self, qapp):
        """Test dialog with used bridges list"""
        from ui.dialogs.hbridge_dialog import HBridgeDialog
        dialog = HBridgeDialog(used_bridges=[0, 1])
        assert dialog is not None
        dialog.close()


# ============================================================================
# WiperDialog Tests
# ============================================================================

class TestWiperDialog:
    """Tests for WiperDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new Wiper dialog"""
        from ui.dialogs.wiper_dialog import WiperDialog
        dialog = WiperDialog()
        assert dialog is not None
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        from ui.dialogs.wiper_dialog import WiperDialog
        config = {
            "channel_id": 1,
            "channel_name": "FrontWiper",
        }
        dialog = WiperDialog(wiper_config=config)
        assert dialog is not None
        dialog.close()

    def test_get_config(self, qapp):
        """Test getting configuration from dialog"""
        from ui.dialogs.wiper_dialog import WiperDialog
        dialog = WiperDialog()

        config = dialog.get_config()

        assert isinstance(config, dict)
        dialog.close()

    def test_with_used_bridges(self, qapp):
        """Test dialog with used bridges list"""
        from ui.dialogs.wiper_dialog import WiperDialog
        dialog = WiperDialog(used_bridges=[0, 1])
        assert dialog is not None
        dialog.close()


# ============================================================================
# BlinkerDialog Tests
# ============================================================================

class TestBlinkerDialog:
    """Tests for BlinkerDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new Blinker dialog"""
        from ui.dialogs.blinker_dialog import BlinkerDialog
        dialog = BlinkerDialog()
        assert dialog is not None
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        from ui.dialogs.blinker_dialog import BlinkerDialog
        config = {
            "channel_id": 1,
            "channel_name": "TurnSignal",
        }
        dialog = BlinkerDialog(blinker_config=config)
        assert dialog is not None
        dialog.close()

    def test_get_config(self, qapp):
        """Test getting configuration from dialog"""
        from ui.dialogs.blinker_dialog import BlinkerDialog
        dialog = BlinkerDialog()

        config = dialog.get_config()

        assert isinstance(config, dict)
        dialog.close()


# ============================================================================
# BlinkMarineKeypadDialog Tests
# ============================================================================

class TestBlinkMarineKeypadDialog:
    """Tests for BlinkMarineKeypadDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new keypad dialog"""
        from ui.dialogs.blinkmarine_keypad_dialog import BlinkMarineKeypadDialog
        dialog = BlinkMarineKeypadDialog()
        assert dialog is not None
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        from ui.dialogs.blinkmarine_keypad_dialog import BlinkMarineKeypadDialog
        config = {
            "channel_id": 1,
            "channel_name": "MainKeypad",
        }
        dialog = BlinkMarineKeypadDialog(config=config)
        assert dialog is not None
        dialog.close()

    def test_get_config(self, qapp):
        """Test getting configuration from dialog"""
        from ui.dialogs.blinkmarine_keypad_dialog import BlinkMarineKeypadDialog
        dialog = BlinkMarineKeypadDialog()

        config = dialog.get_config()

        assert isinstance(config, dict)
        dialog.close()


# ============================================================================
# HandlerDialog Tests
# ============================================================================

class TestHandlerDialog:
    """Tests for HandlerDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new handler dialog"""
        from ui.dialogs.handler_dialog import HandlerDialog
        dialog = HandlerDialog()
        assert dialog is not None
        dialog.close()

    def test_get_config(self, qapp):
        """Test getting configuration from dialog"""
        from ui.dialogs.handler_dialog import HandlerDialog
        dialog = HandlerDialog()

        config = dialog.get_config()

        assert isinstance(config, dict)
        dialog.close()


# ============================================================================
# CAN Input/Output Dialog Tests
# ============================================================================

class TestCANInputDialog:
    """Tests for CANInputDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new CAN input dialog"""
        from ui.dialogs.can_input_dialog import CANInputDialog
        dialog = CANInputDialog()
        assert dialog is not None
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        from ui.dialogs.can_input_dialog import CANInputDialog
        config = {
            "channel_id": 1,
            "channel_name": "EngineRPM",
            "message_ref": "engine_msg",
        }
        dialog = CANInputDialog(input_config=config)
        assert dialog is not None
        dialog.close()

    def test_get_config(self, qapp):
        """Test getting configuration from dialog"""
        from ui.dialogs.can_input_dialog import CANInputDialog
        dialog = CANInputDialog()

        config = dialog.get_config()

        assert isinstance(config, dict)
        dialog.close()

    def test_with_message_ids(self, qapp):
        """Test dialog with available message IDs"""
        from ui.dialogs.can_input_dialog import CANInputDialog
        dialog = CANInputDialog(message_ids=["msg1", "msg2", "msg3"])
        assert dialog is not None
        dialog.close()


class TestCANOutputDialog:
    """Tests for CANOutputDialog"""

    def test_dialog_creation_new(self, qapp):
        """Test creating new CAN output dialog"""
        from ui.dialogs.can_output_dialog import CANOutputDialog
        dialog = CANOutputDialog()
        assert dialog is not None
        dialog.close()

    def test_dialog_creation_edit(self, qapp):
        """Test creating edit dialog with config"""
        from ui.dialogs.can_output_dialog import CANOutputDialog
        config = {
            "channel_id": 1,
            "channel_name": "StatusOut",
        }
        dialog = CANOutputDialog(output_config=config)
        assert dialog is not None
        dialog.close()

    def test_get_config(self, qapp):
        """Test getting configuration from dialog"""
        from ui.dialogs.can_output_dialog import CANOutputDialog
        dialog = CANOutputDialog()

        config = dialog.get_config()

        assert isinstance(config, dict)
        dialog.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

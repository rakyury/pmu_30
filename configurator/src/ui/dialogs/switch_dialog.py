"""
Switch Configuration Dialog
Allows creation of state switches (latching or press/hold)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QComboBox, QDialogButtonBox, QGroupBox, QPushButton
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional
from .channel_selector_dialog import ChannelSelectorDialog


class SwitchDialog(QDialog):
    """Dialog for configuring state switches."""

    SWITCH_TYPES = [
        "latching switch",
        "press/hold switch"
    ]

    TRIGGER_EDGES = [
        "Rising",
        "Falling",
        "Both"
    ]

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None, available_channels: Optional[Dict] = None):
        super().__init__(parent)
        self.config = config or {}
        self.available_channels = available_channels or {}  # Dict of all available channels/functions
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("New Switch")
        self.setMinimumWidth(550)

        layout = QVBoxLayout(self)

        # Main settings group
        main_group = QGroupBox("eSwitch")
        main_layout = QFormLayout()

        # Channel name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., s_switch1")
        main_layout.addRow("Channel name:", self.name_edit)

        # Switch type
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.SWITCH_TYPES)
        main_layout.addRow("Switch type:", self.type_combo)

        # Input channel up
        channel_up_layout = QHBoxLayout()
        self.channel_up_edit = QLineEdit()
        self.channel_up_edit.setPlaceholderText("Select input channel...")
        self.channel_up_edit.setReadOnly(True)
        channel_up_layout.addWidget(self.channel_up_edit, stretch=1)

        self.channel_up_btn = QPushButton("Browse...")
        self.channel_up_btn.clicked.connect(self._browse_channel_up)
        channel_up_layout.addWidget(self.channel_up_btn)
        main_layout.addRow("Input channel up:", channel_up_layout)

        # Trigger edge up
        self.trigger_up_combo = QComboBox()
        self.trigger_up_combo.addItems(self.TRIGGER_EDGES)
        main_layout.addRow("Trigger edge up:", self.trigger_up_combo)

        # Input channel down
        channel_down_layout = QHBoxLayout()
        self.channel_down_edit = QLineEdit()
        self.channel_down_edit.setPlaceholderText("Select input channel...")
        self.channel_down_edit.setReadOnly(True)
        channel_down_layout.addWidget(self.channel_down_edit, stretch=1)

        self.channel_down_btn = QPushButton("Browse...")
        self.channel_down_btn.clicked.connect(self._browse_channel_down)
        channel_down_layout.addWidget(self.channel_down_btn)
        main_layout.addRow("Input channel down:", channel_down_layout)

        # Trigger edge down
        self.trigger_down_combo = QComboBox()
        self.trigger_down_combo.addItems(self.TRIGGER_EDGES)
        main_layout.addRow("Trigger edge down:", self.trigger_down_combo)

        # First state
        self.first_state_spin = QSpinBox()
        self.first_state_spin.setRange(0, 255)
        self.first_state_spin.setValue(0)
        main_layout.addRow("First state:", self.first_state_spin)

        # Last state
        self.last_state_spin = QSpinBox()
        self.last_state_spin.setRange(0, 255)
        self.last_state_spin.setValue(2)
        main_layout.addRow("Last state:", self.last_state_spin)

        # Default state
        self.default_state_spin = QSpinBox()
        self.default_state_spin.setRange(0, 255)
        self.default_state_spin.setValue(0)
        main_layout.addRow("Default state:", self.default_state_spin)

        main_group.setLayout(main_layout)
        layout.addWidget(main_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Channel name is required!")
            self.name_edit.setFocus()
            return

        # Validate first state <= last state
        if self.first_state_spin.value() > self.last_state_spin.value():
            QMessageBox.warning(self, "Validation Error", "First state must be less than or equal to Last state!")
            self.first_state_spin.setFocus()
            return

        # Validate default state is within range
        default_state = self.default_state_spin.value()
        first_state = self.first_state_spin.value()
        last_state = self.last_state_spin.value()

        if default_state < first_state or default_state > last_state:
            QMessageBox.warning(self, "Validation Error",
                f"Default state ({default_state}) must be between First state ({first_state}) and Last state ({last_state})!")
            self.default_state_spin.setFocus()
            return

        self.accept()

    def _browse_channel_up(self):
        """Browse and select input channel up."""
        current = self.channel_up_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.channel_up_edit.setText(channel if channel else "")

    def _browse_channel_down(self):
        """Browse and select input channel down."""
        current = self.channel_down_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.channel_down_edit.setText(channel if channel else "")

    def _load_config(self):
        """Load configuration into UI."""
        if not self.config:
            return

        self.name_edit.setText(self.config.get("name", ""))

        # Switch type
        switch_type = self.config.get("switch_type", "latching switch")
        idx = self.type_combo.findText(switch_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        # Input channels
        self.channel_up_edit.setText(self.config.get("input_channel_up", ""))
        self.channel_down_edit.setText(self.config.get("input_channel_down", ""))

        # Trigger edges
        trigger_up = self.config.get("trigger_edge_up", "Rising")
        idx = self.trigger_up_combo.findText(trigger_up)
        if idx >= 0:
            self.trigger_up_combo.setCurrentIndex(idx)

        trigger_down = self.config.get("trigger_edge_down", "Rising")
        idx = self.trigger_down_combo.findText(trigger_down)
        if idx >= 0:
            self.trigger_down_combo.setCurrentIndex(idx)

        # States
        self.first_state_spin.setValue(self.config.get("first_state", 0))
        self.last_state_spin.setValue(self.config.get("last_state", 2))
        self.default_state_spin.setValue(self.config.get("default_state", 0))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from UI."""
        return {
            "name": self.name_edit.text(),
            "switch_type": self.type_combo.currentText(),
            "input_channel_up": self.channel_up_edit.text(),
            "trigger_edge_up": self.trigger_up_combo.currentText(),
            "input_channel_down": self.channel_down_edit.text(),
            "trigger_edge_down": self.trigger_down_combo.currentText(),
            "first_state": self.first_state_spin.value(),
            "last_state": self.last_state_spin.value(),
            "default_state": self.default_state_spin.value()
        }

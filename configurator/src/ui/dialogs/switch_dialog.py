"""
Switch Configuration Dialog
Allows creation of state switches (latching or press/hold)
"""

from PyQt6.QtWidgets import (
    QFormLayout, QSpinBox, QComboBox, QGroupBox, QGridLayout, QLabel
)
from typing import Dict, Any, Optional, List
from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType


class SwitchDialog(BaseChannelDialog):
    """Dialog for configuring state switches."""

    SWITCH_TYPES = [
        "latching switch",
        "press/hold switch"
    ]

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        """Initialize SwitchDialog with standard constructor pattern."""
        super().__init__(parent, config, available_channels, ChannelType.SWITCH, existing_channels)

        # Create Switch specific UI
        self._create_switch_ui()

        # Load config if editing
        if config:
            self._load_specific_config(config)

        # Finalize UI sizing
        self._finalize_ui()

    def _create_switch_ui(self):
        """Create Switch specific UI components using base class helpers."""
        # Switch settings group
        switch_group = QGroupBox("Switch Settings")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Switch type
        layout.addWidget(QLabel("Switch type:"), row, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.SWITCH_TYPES)
        layout.addWidget(self.type_combo, row, 1, 1, 3)
        row += 1

        # Input channel up (full width) - using base class helper
        layout.addWidget(QLabel("Channel up:"), row, 0)
        self.channel_up_widget, self.channel_up_edit = self._create_channel_selector(
            "Select channel for incrementing state..."
        )
        layout.addWidget(self.channel_up_widget, row, 1, 1, 3)
        row += 1

        # Trigger edge up
        layout.addWidget(QLabel("Edge up:"), row, 0)
        self.trigger_up_combo = self._create_edge_combo(include_both=True, include_level=False)
        layout.addWidget(self.trigger_up_combo, row, 1)
        row += 1

        # Input channel down (full width) - using base class helper
        layout.addWidget(QLabel("Channel down:"), row, 0)
        self.channel_down_widget, self.channel_down_edit = self._create_channel_selector(
            "Select channel for decrementing state..."
        )
        layout.addWidget(self.channel_down_widget, row, 1, 1, 3)
        row += 1

        # Trigger edge down
        layout.addWidget(QLabel("Edge down:"), row, 0)
        self.trigger_down_combo = self._create_edge_combo(include_both=True, include_level=False)
        layout.addWidget(self.trigger_down_combo, row, 1)

        switch_group.setLayout(layout)
        self.content_layout.addWidget(switch_group)

        # State settings group
        state_group = QGroupBox("State Range")
        state_layout = QFormLayout()

        # First state
        self.first_state_spin = QSpinBox()
        self.first_state_spin.setRange(0, 255)
        self.first_state_spin.setValue(0)
        state_layout.addRow("First state:", self.first_state_spin)

        # Last state
        self.last_state_spin = QSpinBox()
        self.last_state_spin.setRange(0, 255)
        self.last_state_spin.setValue(2)
        state_layout.addRow("Last state:", self.last_state_spin)

        # Default state
        self.default_state_spin = QSpinBox()
        self.default_state_spin.setRange(0, 255)
        self.default_state_spin.setValue(0)
        state_layout.addRow("Default state:", self.default_state_spin)

        state_group.setLayout(state_layout)
        self.content_layout.addWidget(state_group)

    def _validate_specific(self) -> list:
        """Validate Switch specific fields."""
        errors = []

        # Validate first state <= last state
        if self.first_state_spin.value() > self.last_state_spin.value():
            errors.append("First state must be less than or equal to Last state")

        # Validate default state is within range
        default_state = self.default_state_spin.value()
        first_state = self.first_state_spin.value()
        last_state = self.last_state_spin.value()

        if default_state < first_state or default_state > last_state:
            errors.append(f"Default state ({default_state}) must be between First state ({first_state}) and Last state ({last_state})")

        return errors

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load Switch specific configuration."""
        # Switch type
        switch_type = config.get("switch_type", "latching switch")
        idx = self.type_combo.findText(switch_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        # Input channels - using base class helper
        self._set_channel_edit_value(self.channel_up_edit, config.get("input_channel_up"))
        self._set_channel_edit_value(self.channel_down_edit, config.get("input_channel_down"))

        # Trigger edges - using base class helper
        self._set_edge_combo_value(self.trigger_up_combo, config.get("trigger_edge_up", "rising"))
        self._set_edge_combo_value(self.trigger_down_combo, config.get("trigger_edge_down", "rising"))

        # States
        self.first_state_spin.setValue(config.get("first_state", 0))
        self.last_state_spin.setValue(config.get("last_state", 2))
        self.default_state_spin.setValue(config.get("default_state", 0))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        # Get base config (channel_id, name, enabled, channel_type)
        config = self.get_base_config()

        # Add Switch specific fields - using base class helpers for channel IDs
        config.update({
            "switch_type": self.type_combo.currentText(),
            "input_channel_up": self._get_channel_id_from_edit(self.channel_up_edit) or "",
            "trigger_edge_up": self._get_edge_combo_value(self.trigger_up_combo),
            "input_channel_down": self._get_channel_id_from_edit(self.channel_down_edit) or "",
            "trigger_edge_down": self._get_edge_combo_value(self.trigger_down_combo),
            "first_state": self.first_state_spin.value(),
            "last_state": self.last_state_spin.value(),
            "default_state": self.default_state_spin.value()
        })

        return config

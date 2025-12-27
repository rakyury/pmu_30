"""
Switch Configuration Dialog
Allows creation of state switches (latching or press/hold)
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QComboBox, QGroupBox, QPushButton
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List
from .channel_selector_dialog import ChannelSelectorDialog
from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType
from models.channel_display_service import ChannelDisplayService


class SwitchDialog(BaseChannelDialog):
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

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None,
                 **kwargs):
        """Initialize SwitchDialog.

        Args:
            parent: Parent widget
            config: Switch configuration (for editing) or None (for creating)
            available_channels: Dict of available channels for source selection
            existing_channels: List of existing channel configs
            **kwargs: Additional arguments for backwards compatibility
        """
        # Initialize base class (creates Basic Settings with name, channel_id, enabled)
        super().__init__(parent, config, available_channels, ChannelType.SWITCH, existing_channels)

        self.setMinimumWidth(550)

        # Create Switch specific UI
        self._create_switch_ui()

        if config:
            self._load_specific_config(config)

    def _create_switch_ui(self):
        """Create Switch specific UI components."""
        # Switch settings group
        switch_group = QGroupBox("Switch Settings")
        switch_layout = QFormLayout()

        # Switch type
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.SWITCH_TYPES)
        switch_layout.addRow("Switch type:", self.type_combo)

        # Input channel up
        channel_up_layout = QHBoxLayout()
        self.channel_up_edit = QLineEdit()
        self.channel_up_edit.setPlaceholderText("Select input channel...")
        self.channel_up_edit.setReadOnly(True)
        channel_up_layout.addWidget(self.channel_up_edit, stretch=1)

        self.channel_up_btn = QPushButton("Browse...")
        self.channel_up_btn.clicked.connect(self._browse_channel_up)
        channel_up_layout.addWidget(self.channel_up_btn)
        switch_layout.addRow("Input channel up:", channel_up_layout)

        # Trigger edge up
        self.trigger_up_combo = QComboBox()
        self.trigger_up_combo.addItems(self.TRIGGER_EDGES)
        switch_layout.addRow("Trigger edge up:", self.trigger_up_combo)

        # Input channel down
        channel_down_layout = QHBoxLayout()
        self.channel_down_edit = QLineEdit()
        self.channel_down_edit.setPlaceholderText("Select input channel...")
        self.channel_down_edit.setReadOnly(True)
        channel_down_layout.addWidget(self.channel_down_edit, stretch=1)

        self.channel_down_btn = QPushButton("Browse...")
        self.channel_down_btn.clicked.connect(self._browse_channel_down)
        channel_down_layout.addWidget(self.channel_down_btn)
        switch_layout.addRow("Input channel down:", channel_down_layout)

        # Trigger edge down
        self.trigger_down_combo = QComboBox()
        self.trigger_down_combo.addItems(self.TRIGGER_EDGES)
        switch_layout.addRow("Trigger edge down:", self.trigger_down_combo)

        switch_group.setLayout(switch_layout)
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

    # Channel helper method
    def _get_channel_display_name(self, channel_id) -> str:
        """Get display name for a channel using central lookup."""
        return ChannelDisplayService.get_display_name(channel_id, self.available_channels)

    def _browse_channel_up(self):
        """Browse and select input channel up."""
        current = self.channel_up_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.channel_up_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_channel_down(self):
        """Browse and select input channel down."""
        current = self.channel_down_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.channel_down_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load Switch specific configuration."""
        # Switch type
        switch_type = config.get("switch_type", "latching switch")
        idx = self.type_combo.findText(switch_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        # Input channels - convert channel IDs to display names
        self.channel_up_edit.setText(self._get_channel_display_name(config.get("input_channel_up", "")))
        self.channel_down_edit.setText(self._get_channel_display_name(config.get("input_channel_down", "")))

        # Trigger edges
        trigger_up = config.get("trigger_edge_up", "Rising")
        idx = self.trigger_up_combo.findText(trigger_up)
        if idx >= 0:
            self.trigger_up_combo.setCurrentIndex(idx)

        trigger_down = config.get("trigger_edge_down", "Rising")
        idx = self.trigger_down_combo.findText(trigger_down)
        if idx >= 0:
            self.trigger_down_combo.setCurrentIndex(idx)

        # States
        self.first_state_spin.setValue(config.get("first_state", 0))
        self.last_state_spin.setValue(config.get("last_state", 2))
        self.default_state_spin.setValue(config.get("default_state", 0))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        # Get base config (channel_id, name, enabled, channel_type)
        config = self.get_base_config()

        # Add Switch specific fields
        config.update({
            "switch_type": self.type_combo.currentText(),
            "input_channel_up": self.channel_up_edit.text(),
            "trigger_edge_up": self.trigger_up_combo.currentText(),
            "input_channel_down": self.channel_down_edit.text(),
            "trigger_edge_down": self.trigger_down_combo.currentText(),
            "first_state": self.first_state_spin.value(),
            "last_state": self.last_state_spin.value(),
            "default_state": self.default_state_spin.value()
        })

        return config

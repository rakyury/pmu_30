"""
Event Handler Configuration Dialog
Configures event handlers that react to system events and execute actions
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QGridLayout, QLabel, QWidget, QCheckBox, QLineEdit, QStackedWidget,
    QHBoxLayout, QTextEdit
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, EventType, ActionType


class HandlerDialog(BaseChannelDialog):
    """Dialog for configuring event handler channels"""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent, config, available_channels, ChannelType.HANDLER, existing_channels)

        self.setWindowTitle("Event Handler Configuration")
        self.setMinimumHeight(600)
        self.resize(650, 620)

        self._create_event_group()
        self._create_condition_group()
        self._create_action_group()
        self._create_options_group()

        # Load config if editing
        if config:
            self._load_specific_config(config)

    def _create_event_group(self):
        """Create event configuration group"""
        event_group = QGroupBox("Event Trigger")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        row = 0

        # Event type selector
        layout.addWidget(QLabel("Event Type: *"), row, 0)
        self.event_combo = QComboBox()
        self.event_combo.addItem("Channel ON (Rising Edge)", EventType.CHANNEL_ON.value)
        self.event_combo.addItem("Channel OFF (Falling Edge)", EventType.CHANNEL_OFF.value)
        self.event_combo.addItem("Channel Fault", EventType.CHANNEL_FAULT.value)
        self.event_combo.addItem("Channel Fault Cleared", EventType.CHANNEL_CLEARED.value)
        self.event_combo.addItem("Threshold Crossed (High)", EventType.THRESHOLD_HIGH.value)
        self.event_combo.addItem("Threshold Crossed (Low)", EventType.THRESHOLD_LOW.value)
        self.event_combo.addItem("System Undervoltage", EventType.SYSTEM_UNDERVOLT.value)
        self.event_combo.addItem("System Overvoltage", EventType.SYSTEM_OVERVOLT.value)
        self.event_combo.addItem("System Overtemperature", EventType.SYSTEM_OVERTEMP.value)
        self.event_combo.currentIndexChanged.connect(self._on_event_changed)
        layout.addWidget(self.event_combo, row, 1)
        row += 1

        # Source channel selector
        layout.addWidget(QLabel("Source Channel:"), row, 0)
        self.source_channel_widget, self.source_channel_edit = self._create_channel_selector(
            "Channel that triggers the event..."
        )
        layout.addWidget(self.source_channel_widget, row, 1)
        row += 1

        # Threshold value (for threshold events)
        self.threshold_label = QLabel("Threshold Value:")
        layout.addWidget(self.threshold_label, row, 0)
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(-1000000, 1000000)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(0.0)
        layout.addWidget(self.threshold_spin, row, 1)
        row += 1

        # Info label
        self.event_info = QLabel("")
        self.event_info.setStyleSheet("color: #b0b0b0; font-style: italic;")
        self.event_info.setWordWrap(True)
        layout.addWidget(self.event_info, row, 0, 1, 2)

        event_group.setLayout(layout)
        self.content_layout.addWidget(event_group)

        # Initial visibility update
        self._on_event_changed()

    def _create_condition_group(self):
        """Create optional condition group"""
        condition_group = QGroupBox("Condition (Optional)")
        layout = QFormLayout()

        # Condition channel selector
        self.condition_channel_widget, self.condition_channel_edit = self._create_channel_selector(
            "Handler fires only if this channel is TRUE..."
        )
        layout.addRow("Condition Channel:", self.condition_channel_widget)

        info = QLabel("If a condition channel is specified, the handler will only execute\n"
                      "when the event occurs AND the condition channel value is non-zero (TRUE).")
        info.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addRow(info)

        condition_group.setLayout(layout)
        self.content_layout.addWidget(condition_group)

    def _create_action_group(self):
        """Create action configuration group"""
        action_group = QGroupBox("Action")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        row = 0

        # Action type selector
        layout.addWidget(QLabel("Action Type: *"), row, 0)
        self.action_combo = QComboBox()
        self.action_combo.addItem("Write to Virtual Channel", ActionType.WRITE_CHANNEL.value)
        self.action_combo.addItem("Set Output State", ActionType.SET_OUTPUT.value)
        self.action_combo.addItem("Send CAN Message", ActionType.SEND_CAN.value)
        self.action_combo.addItem("Send LIN Message", ActionType.SEND_LIN.value)
        self.action_combo.addItem("Run Lua Function", ActionType.RUN_LUA.value)
        self.action_combo.currentIndexChanged.connect(self._on_action_changed)
        layout.addWidget(self.action_combo, row, 1)
        row += 1

        # Stacked widget for action-specific options
        self.action_stack = QStackedWidget()
        layout.addWidget(self.action_stack, row, 0, 1, 2)

        # Page 0: Write Channel / Set Output
        channel_page = QWidget()
        channel_layout = QFormLayout(channel_page)
        self.target_channel_widget, self.target_channel_edit = self._create_channel_selector(
            "Target channel to write to..."
        )
        channel_layout.addRow("Target Channel: *", self.target_channel_widget)
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1000000, 1000000)
        self.value_spin.setDecimals(2)
        self.value_spin.setValue(1.0)
        channel_layout.addRow("Value to Write:", self.value_spin)
        self.action_stack.addWidget(channel_page)

        # Page 1: CAN/LIN Message
        can_page = QWidget()
        can_layout = QFormLayout(can_page)
        self.can_bus_spin = QSpinBox()
        self.can_bus_spin.setRange(1, 4)
        self.can_bus_spin.setValue(1)
        can_layout.addRow("CAN/LIN Bus:", self.can_bus_spin)
        self.message_id_spin = QSpinBox()
        self.message_id_spin.setRange(0, 0x1FFFFFFF)
        self.message_id_spin.setDisplayIntegerBase(16)
        self.message_id_spin.setPrefix("0x")
        self.message_id_spin.setValue(0x100)
        can_layout.addRow("Message ID:", self.message_id_spin)
        self.message_data_edit = QLineEdit()
        self.message_data_edit.setPlaceholderText("00 00 00 00 00 00 00 00")
        self.message_data_edit.setToolTip("Enter 8 bytes as hex, space-separated (e.g., 01 02 03 04 05 06 07 08)")
        can_layout.addRow("Data (8 bytes):", self.message_data_edit)
        self.action_stack.addWidget(can_page)

        # Page 2: Lua Function
        lua_page = QWidget()
        lua_layout = QFormLayout(lua_page)
        self.lua_function_edit = QLineEdit()
        self.lua_function_edit.setPlaceholderText("on_event_handler")
        self.lua_function_edit.setToolTip("Name of Lua function to call when event occurs")
        lua_layout.addRow("Lua Function: *", self.lua_function_edit)
        lua_info = QLabel("The Lua function will be called with event info as argument.\n"
                          "Example: function on_event_handler(event) ... end")
        lua_info.setStyleSheet("color: #b0b0b0; font-style: italic;")
        lua_layout.addRow(lua_info)
        self.action_stack.addWidget(lua_page)

        action_group.setLayout(layout)
        self.content_layout.addWidget(action_group)

        # Initial action page
        self._on_action_changed()

    def _create_options_group(self):
        """Create handler options group"""
        options_group = QGroupBox("Options")
        layout = QFormLayout()

        # Enabled checkbox
        self.enabled_check = QCheckBox("Handler Enabled")
        self.enabled_check.setChecked(True)
        layout.addRow(self.enabled_check)

        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description of what this handler does...")
        layout.addRow("Description:", self.description_edit)

        options_group.setLayout(layout)
        self.content_layout.addWidget(options_group)

    def _on_event_changed(self):
        """Handle event type change"""
        event = self.event_combo.currentData()

        # Show/hide threshold based on event type
        is_threshold = event in [EventType.THRESHOLD_HIGH.value, EventType.THRESHOLD_LOW.value]
        self.threshold_label.setVisible(is_threshold)
        self.threshold_spin.setVisible(is_threshold)

        # Show/hide source channel based on event type
        is_system = event in [EventType.SYSTEM_UNDERVOLT.value, EventType.SYSTEM_OVERVOLT.value,
                              EventType.SYSTEM_OVERTEMP.value]
        self.source_channel_widget.setEnabled(not is_system)
        if is_system:
            self.source_channel_edit.setPlaceholderText("Not required for system events")
        else:
            self.source_channel_edit.setPlaceholderText("Channel that triggers the event...")

        # Update info text
        event_info_map = {
            EventType.CHANNEL_ON.value: "Triggered when the source channel transitions from 0 to non-zero (rising edge).",
            EventType.CHANNEL_OFF.value: "Triggered when the source channel transitions from non-zero to 0 (falling edge).",
            EventType.CHANNEL_FAULT.value: "Triggered when the source output channel enters a fault state.",
            EventType.CHANNEL_CLEARED.value: "Triggered when the source output channel fault is cleared.",
            EventType.THRESHOLD_HIGH.value: "Triggered when the source channel value rises above the threshold.",
            EventType.THRESHOLD_LOW.value: "Triggered when the source channel value falls below the threshold.",
            EventType.SYSTEM_UNDERVOLT.value: "Triggered when system voltage drops below safe level.",
            EventType.SYSTEM_OVERVOLT.value: "Triggered when system voltage exceeds safe level.",
            EventType.SYSTEM_OVERTEMP.value: "Triggered when system temperature exceeds safe level.",
        }
        self.event_info.setText(event_info_map.get(event, ""))

    def _on_action_changed(self):
        """Handle action type change"""
        action = self.action_combo.currentData()

        if action in [ActionType.WRITE_CHANNEL.value, ActionType.SET_OUTPUT.value]:
            self.action_stack.setCurrentIndex(0)
        elif action in [ActionType.SEND_CAN.value, ActionType.SEND_LIN.value]:
            self.action_stack.setCurrentIndex(1)
        elif action == ActionType.RUN_LUA.value:
            self.action_stack.setCurrentIndex(2)

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        # Event settings
        event = config.get("event", "channel_on")
        for i in range(self.event_combo.count()):
            if self.event_combo.itemData(i) == event:
                self.event_combo.setCurrentIndex(i)
                break

        self._set_channel_edit_value(self.source_channel_edit, config.get("source_channel"))
        self.threshold_spin.setValue(config.get("threshold_value", 0.0))

        # Condition
        self._set_channel_edit_value(self.condition_channel_edit, config.get("condition_channel"))

        # Action settings
        action = config.get("action", "write_channel")
        for i in range(self.action_combo.count()):
            if self.action_combo.itemData(i) == action:
                self.action_combo.setCurrentIndex(i)
                break

        self._set_channel_edit_value(self.target_channel_edit, config.get("target_channel"))
        self.value_spin.setValue(config.get("value", 1.0))
        self.can_bus_spin.setValue(config.get("can_bus", 1))
        self.message_id_spin.setValue(config.get("message_id", 0x100))

        # Parse message data
        message_data = config.get("message_data", [0] * 8)
        if isinstance(message_data, list):
            hex_str = " ".join(f"{b:02X}" for b in message_data[:8])
            self.message_data_edit.setText(hex_str)

        self.lua_function_edit.setText(config.get("lua_function", ""))

        # Options
        self.enabled_check.setChecked(config.get("enabled", True))
        self.description_edit.setText(config.get("description", ""))

        # Update UI
        self._on_event_changed()
        self._on_action_changed()

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []
        event = self.event_combo.currentData()
        action = self.action_combo.currentData()

        # Check source channel for non-system events
        is_system = event in [EventType.SYSTEM_UNDERVOLT.value, EventType.SYSTEM_OVERVOLT.value,
                              EventType.SYSTEM_OVERTEMP.value]
        if not is_system and not self.source_channel_edit.text().strip():
            errors.append("Source channel is required for this event type")

        # Validate action-specific fields
        if action in [ActionType.WRITE_CHANNEL.value, ActionType.SET_OUTPUT.value]:
            if not self.target_channel_edit.text().strip():
                errors.append("Target channel is required for this action")
        elif action == ActionType.RUN_LUA.value:
            if not self.lua_function_edit.text().strip():
                errors.append("Lua function name is required")

        return errors

    def _parse_message_data(self) -> List[int]:
        """Parse message data from hex string"""
        text = self.message_data_edit.text().strip()
        if not text:
            return [0] * 8

        try:
            # Parse space-separated hex bytes
            parts = text.split()
            data = []
            for part in parts[:8]:
                data.append(int(part, 16) & 0xFF)
            # Pad to 8 bytes
            while len(data) < 8:
                data.append(0)
            return data
        except ValueError:
            return [0] * 8

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()

        # Get channel IDs using helper method
        source_channel_id = self._get_channel_id_from_edit(self.source_channel_edit)
        condition_channel_id = self._get_channel_id_from_edit(self.condition_channel_edit)
        target_channel_id = self._get_channel_id_from_edit(self.target_channel_edit)

        config.update({
            "event": self.event_combo.currentData(),
            "source_channel": source_channel_id if source_channel_id else "",
            "threshold_value": self.threshold_spin.value(),
            "condition_channel": condition_channel_id if condition_channel_id else "",
            "action": self.action_combo.currentData(),
            "target_channel": target_channel_id if target_channel_id else "",
            "value": self.value_spin.value(),
            "can_bus": self.can_bus_spin.value(),
            "message_id": self.message_id_spin.value(),
            "message_data": self._parse_message_data(),
            "lua_function": self.lua_function_edit.text().strip(),
            "enabled": self.enabled_check.isChecked(),
            "description": self.description_edit.text().strip(),
        })

        return config

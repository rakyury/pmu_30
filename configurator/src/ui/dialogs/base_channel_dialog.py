"""
Base Channel Dialog
Common base class for all Channel configuration dialogs

Architecture:
- channel_id: Numeric, auto-generated, unique across ALL channels (0-65535), NOT editable
- name: User-defined string, editable
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from models.channel import ChannelBase, ChannelType, get_channel_display_name


# Global channel ID counter - shared across all channel types
# System channels use IDs 1000-1100, user channels use 1-999
_next_user_channel_id = 1


def get_next_channel_id(existing_channels: List[Dict[str, Any]] = None) -> int:
    """Get next available channel ID based on existing channels."""
    global _next_user_channel_id

    used_ids = set()
    if existing_channels:
        for ch in existing_channels:
            ch_id = ch.get("channel_id")
            if ch_id is not None:
                used_ids.add(ch_id)

    # Find next free ID in user range (1-999)
    for candidate in range(1, 1000):
        if candidate not in used_ids:
            return candidate

    # Fallback - use global counter
    while _next_user_channel_id in used_ids and _next_user_channel_id < 1000:
        _next_user_channel_id += 1

    result = _next_user_channel_id
    _next_user_channel_id += 1
    return result


class BaseChannelDialog(QDialog):
    """Base dialog for configuring channels"""

    # Prefixes for auto-generated names by channel type
    NAME_PREFIXES = {
        ChannelType.ANALOG_INPUT: "Analog ",
        ChannelType.DIGITAL_INPUT: "Digital ",
        ChannelType.POWER_OUTPUT: "Output ",
        ChannelType.LOGIC: "Logic ",
        ChannelType.NUMBER: "Number ",
        ChannelType.TIMER: "Timer ",
        ChannelType.SWITCH: "Switch ",
        ChannelType.TABLE_2D: "Table2D ",
        ChannelType.TABLE_3D: "Table3D ",
        ChannelType.FILTER: "Filter ",
        ChannelType.ENUM: "Enum ",
        ChannelType.CAN_RX: "CAN_RX ",
        ChannelType.CAN_TX: "CAN_TX ",
        ChannelType.LUA_SCRIPT: "Script ",
        ChannelType.PID: "PID ",
    }

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 channel_type: ChannelType = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)

        self.config = config or {}
        self.available_channels = available_channels or {}
        self.channel_type = channel_type
        self.existing_channels = existing_channels or []
        self.is_edit_mode = bool(config and config.get("channel_id") is not None)

        # Store or generate channel_id
        if self.is_edit_mode:
            self._channel_id = config.get("channel_id", 0)
        else:
            self._channel_id = get_next_channel_id(existing_channels)

        self._init_base_ui()

        if config:
            self._load_base_config(config)

        if not self.is_edit_mode:
            # Auto-generate name for new channels
            self._auto_generate_name()

    def _init_base_ui(self):
        """Initialize base UI components"""
        title = "Edit" if self.is_edit_mode else "New"
        type_name = get_channel_display_name(self.channel_type) if self.channel_type else "Channel"
        self.setWindowTitle(f"{title} {type_name}")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.resize(650, 550)

        self.main_layout = QVBoxLayout(self)

        # Create scroll area for content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_widget = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_widget)

        # Basic settings group (common for all channel types)
        self._create_basic_group()

        self.scroll.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll)

        # Buttons
        self._create_buttons()

    def _create_basic_group(self):
        """Create basic settings group"""
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        # Channel ID field (read-only, numeric, auto-generated)
        self.channel_id_label = QLabel(str(self._channel_id))
        self.channel_id_label.setStyleSheet("font-weight: bold; color: #b0b0b0;")
        basic_layout.addRow("Channel ID:", self.channel_id_label)

        # Name field (editable by user)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter channel name (e.g., Ignition Switch)")
        basic_layout.addRow("Name: *", self.name_edit)

        basic_group.setLayout(basic_layout)
        self.content_layout.addWidget(basic_group)

    def _create_buttons(self):
        """Create OK/Cancel buttons"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.main_layout.addLayout(button_layout)

    def _load_base_config(self, config: Dict[str, Any]):
        """Load base configuration fields"""
        self.name_edit.setText(config.get("name", ""))

    def _auto_generate_name(self):
        """Auto-generate name for new channel based on type and ID"""
        prefix = self.NAME_PREFIXES.get(self.channel_type, "Channel ")
        # Use channel_id as the number suffix
        self.name_edit.setText(f"{prefix}{self._channel_id}")

    def _validate_base(self) -> List[str]:
        """Validate base fields, return list of errors"""
        errors = []

        name = self.name_edit.text().strip()
        if not name:
            errors.append("Name is required")

        return errors

    def _on_accept(self):
        """Validate and accept dialog"""
        errors = self._validate_base()
        errors.extend(self._validate_specific())

        if errors:
            QMessageBox.warning(
                self,
                "Validation Error",
                "\n".join(f"- {e}" for e in errors)
            )
            return

        self.accept()

    def _validate_specific(self) -> List[str]:
        """Override in subclasses to add specific validation"""
        return []

    def get_base_config(self) -> Dict[str, Any]:
        """Get base configuration fields"""
        name = self.name_edit.text().strip()
        return {
            "channel_id": self._channel_id,
            "id": name,  # String ID for display, firmware uses numeric channel_id
            "name": name,
            "channel_type": self.channel_type.value if self.channel_type else ""
        }

    def get_config(self) -> Dict[str, Any]:
        """Override in subclasses to return full configuration"""
        return self.get_base_config()

    def _create_channel_selector(self, placeholder: str = "Select channel...") -> tuple:
        """
        Create channel selector widget with browse button.

        Returns:
            tuple: (container_widget, line_edit)
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setPlaceholderText(placeholder)
        layout.addWidget(edit, stretch=1)

        btn = QPushButton("...")
        btn.setMaximumWidth(30)
        btn.setToolTip("Browse channels")
        btn.clicked.connect(lambda: self._browse_channel(edit))
        layout.addWidget(btn)

        return container, edit

    def _browse_channel(self, target_edit: QLineEdit):
        """Open channel selector dialog"""
        from .channel_selector_dialog import ChannelSelectorDialog

        current = target_edit.text()
        # Exclude current channel from selection to prevent self-reference
        exclude_id = self._channel_id if hasattr(self, '_channel_id') else None
        accepted, channel_id = ChannelSelectorDialog.select_channel(
            self, current, self.available_channels,
            show_tree=True, exclude_channel=exclude_id
        )
        if accepted:
            if channel_id is not None:
                # Find display name for the channel_id
                display_name = self._get_channel_display_name(channel_id)
                target_edit.setText(display_name)
                # Store numeric ID in property for later use
                target_edit.setProperty("channel_id", channel_id)
            else:
                target_edit.setText("")
                target_edit.setProperty("channel_id", None)

    def _get_channel_display_name(self, channel_id) -> str:
        """Get display name for a channel by its ID (numeric or string)."""
        if not self.available_channels:
            return str(channel_id)

        # Search through all channel categories
        for category, channels in self.available_channels.items():
            for ch in channels:
                if isinstance(ch, tuple) and len(ch) == 2:
                    ch_id, ch_name = ch
                    if ch_id == channel_id:
                        return str(ch_name)
                elif ch == channel_id:
                    return str(ch)

        # Fallback to string representation
        return str(channel_id)

    def _get_channel_id_from_edit(self, edit: QLineEdit):
        """Get channel ID from edit field (from property or text fallback)."""
        channel_id = edit.property("channel_id")
        if channel_id is None:
            # Fallback to text (for backwards compatibility)
            text = edit.text().strip()
            return text if text else None
        return channel_id

    def _set_channel_edit_value(self, edit: QLineEdit, channel_id):
        """Set channel edit field value with display name lookup.

        Args:
            edit: The QLineEdit to set
            channel_id: Channel ID (numeric int or string)
        """
        if channel_id is None or channel_id == "" or channel_id == 0:
            edit.setText("")
            edit.setProperty("channel_id", None)
            return

        # Find display name for the channel_id
        display_name = self._get_channel_display_name(channel_id)
        edit.setText(display_name)
        edit.setProperty("channel_id", channel_id)

    def _create_edge_combo(self, include_both: bool = True, include_level: bool = False) -> QComboBox:
        """Create edge selection combobox"""
        combo = QComboBox()
        combo.addItem("Rising", "rising")
        combo.addItem("Falling", "falling")
        if include_both:
            combo.addItem("Both", "both")
        if include_level:
            combo.addItem("Level (High)", "level")
        return combo

    def _set_edge_combo_value(self, combo: QComboBox, value: str):
        """Set edge combo value by data"""
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                break

    def _get_edge_combo_value(self, combo: QComboBox) -> str:
        """Get edge combo current data value"""
        return combo.currentData() or "rising"


class ChannelListWidget(QWidget):
    """Widget for managing a list of input channels"""

    def __init__(self, parent=None, available_channels: Dict[str, List[str]] = None,
                 max_channels: int = 8):
        super().__init__(parent)
        self.available_channels = available_channels or {}
        self.max_channels = max_channels
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # List display
        from PyQt6.QtWidgets import QListWidget
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(100)
        layout.addWidget(self.list_widget)

        # Add/Remove buttons
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._on_remove)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_add(self):
        """Add new channel"""
        if self.list_widget.count() >= self.max_channels:
            QMessageBox.warning(
                self, "Limit Reached",
                f"Maximum {self.max_channels} channels allowed"
            )
            return

        from .channel_selector_dialog import ChannelSelectorDialog
        accepted, channel = ChannelSelectorDialog.select_channel(
            self, "", self.available_channels
        )
        if accepted and channel:
            # Check for duplicates
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).text() == channel:
                    QMessageBox.warning(
                        self, "Duplicate",
                        f"Channel '{channel}' is already in the list"
                    )
                    return
            self.list_widget.addItem(channel)

    def _on_remove(self):
        """Remove selected channel"""
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            self.list_widget.takeItem(current_row)

    def get_channels(self) -> List[str]:
        """Get list of selected channels"""
        channels = []
        for i in range(self.list_widget.count()):
            channels.append(self.list_widget.item(i).text())
        return channels

    def set_channels(self, channels: List[str]):
        """Set list of channels"""
        self.list_widget.clear()
        for ch in channels:
            self.list_widget.addItem(ch)

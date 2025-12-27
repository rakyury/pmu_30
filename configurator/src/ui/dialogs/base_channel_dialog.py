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
    QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings
from typing import Dict, Any, Optional, List

from models.channel import ChannelBase, ChannelType, get_channel_display_name
from models.channel_display_service import ChannelDisplayService, ChannelIdGenerator


def get_next_channel_id(existing_channels: List[Dict[str, Any]] = None) -> int:
    """Get next available channel ID based on existing channels.

    Delegates to ChannelIdGenerator for centralized, stateless ID generation.
    Kept for backward compatibility with existing code.
    """
    return ChannelIdGenerator.get_next_channel_id(existing_channels)


class BaseChannelDialog(QDialog):
    """Base dialog for configuring channels"""

    # ID prefixes for channel identifiers (used in references)
    ID_PREFIXES = {
        ChannelType.ANALOG_INPUT: "ai_",
        ChannelType.DIGITAL_INPUT: "di_",
        ChannelType.POWER_OUTPUT: "o_",
        ChannelType.HBRIDGE: "hb_",
        ChannelType.LOGIC: "l_",
        ChannelType.NUMBER: "n_",
        ChannelType.TIMER: "t_",
        ChannelType.SWITCH: "sw_",
        ChannelType.TABLE_2D: "t2d_",
        ChannelType.TABLE_3D: "t3d_",
        ChannelType.FILTER: "f_",
        ChannelType.CAN_RX: "can_rx_",
        ChannelType.CAN_TX: "can_tx_",
        ChannelType.LUA_SCRIPT: "lua_",
        ChannelType.PID: "pid_",
        ChannelType.HANDLER: "h_",
        ChannelType.BLINKMARINE_KEYPAD: "bm_",
    }

    # Human-readable name prefixes for display names
    NAME_PREFIXES = {
        ChannelType.ANALOG_INPUT: "Analog ",
        ChannelType.DIGITAL_INPUT: "Digital ",
        ChannelType.POWER_OUTPUT: "Output ",
        ChannelType.HBRIDGE: "H-Bridge ",
        ChannelType.LOGIC: "Logic ",
        ChannelType.NUMBER: "Number ",
        ChannelType.TIMER: "Timer ",
        ChannelType.SWITCH: "Switch ",
        ChannelType.TABLE_2D: "Table2D ",
        ChannelType.TABLE_3D: "Table3D ",
        ChannelType.FILTER: "Filter ",
        ChannelType.CAN_RX: "CAN RX ",
        ChannelType.CAN_TX: "CAN TX ",
        ChannelType.LUA_SCRIPT: "Script ",
        ChannelType.PID: "PID ",
        ChannelType.HANDLER: "Handler ",
        ChannelType.BLINKMARINE_KEYPAD: "BlinkMarine ",
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

        if not self.is_edit_mode and not self.name_edit.text().strip():
            # Auto-generate name for new channels (only if not already set from config)
            self._auto_generate_name()

    def _init_base_ui(self):
        """Initialize base UI components"""
        title = "Edit" if self.is_edit_mode else "New"
        type_name = get_channel_display_name(self.channel_type) if self.channel_type else "Channel"
        self.setWindowTitle(f"{title} {type_name}")
        self.setModal(True)
        self.setSizeGripEnabled(True)  # Allow resize if needed

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)

        # Content layout - directly in dialog, no scroll area
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
        self.main_layout.addLayout(self.content_layout)

        # Basic settings group (common for all channel types)
        self._create_basic_group()

        # Add stretch to push buttons to bottom
        self.main_layout.addStretch()

        # Buttons
        self._create_buttons()

    def _finalize_ui(self):
        """Call after subclass has added all content to adjust size"""
        # Ensure dialog fits its content
        self.adjustSize()

        # Make dialog 50% wider for better readability
        current_size = self.sizeHint()
        new_width = int(current_size.width() * 1.5)
        self.resize(new_width, current_size.height())

        # Set minimum to this new size
        self.setMinimumSize(new_width, current_size.height())

        # Restore saved geometry if available (overrides the above if saved)
        self._restore_geometry()

    def _get_geometry_key(self) -> str:
        """Get settings key for this dialog type's geometry."""
        class_name = self.__class__.__name__
        return f"DialogGeometry/{class_name}"

    def _save_geometry(self):
        """Save dialog geometry to settings."""
        settings = QSettings("R2M-Sport", "PMU-30 Configurator")
        settings.setValue(self._get_geometry_key(), self.saveGeometry())

    def _restore_geometry(self):
        """Restore dialog geometry from settings."""
        settings = QSettings("R2M-Sport", "PMU-30 Configurator")
        geometry = settings.value(self._get_geometry_key())
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        """Save geometry when dialog closes."""
        self._save_geometry()
        super().closeEvent(event)

    def _create_basic_group(self):
        """Create basic settings group"""
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        # Channel ID field (read-only, numeric, auto-generated)
        self.channel_id_label = QLabel(str(self._channel_id))
        self.channel_id_label.setStyleSheet("font-weight: bold; color: #b0b0b0;")
        basic_layout.addRow("Channel ID:", self.channel_id_label)

        # Name field - the ONLY user-editable identifier
        # Must be unique across all channels, used for references in logic
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., CoolantTemp, FanOutput, IgnitionSwitch")
        self.name_edit.setToolTip(
            "Unique channel name.\n"
            "Used in UI and for references in logic.\n"
            "Must be unique across all channels."
        )
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
        # Name is the primary identifier - try 'channel_name' first, then 'name', then 'id'
        name = config.get("channel_name", "") or config.get("name", "") or config.get("id", "")
        self.name_edit.setText(name)

    def _auto_generate_name(self):
        """Auto-generate name for new channel based on type"""
        # Generate human-readable name (e.g., Analog1, Output2, Timer3)
        name_prefix = self.NAME_PREFIXES.get(self.channel_type, "Channel")
        # Remove spaces for cleaner names that work better as identifiers
        clean_prefix = name_prefix.strip().replace(" ", "")
        self.name_edit.setText(f"{clean_prefix}{self._channel_id}")

    def _validate_base(self) -> List[str]:
        """Validate base fields, return list of errors"""
        errors = []

        name = self.name_edit.text().strip()
        if not name:
            errors.append("Name is required")
        # Allow letters, numbers, spaces, underscores, hyphens, parentheses, slashes, dots
        # Only restriction: must start with a letter or underscore
        elif not name[0].isalpha() and name[0] != '_':
            errors.append("Name must start with a letter or underscore")
        # Allow most printable characters for descriptive names
        # Forbidden: only characters that could cause issues in JSON/firmware: " ' \\ ; { } [ ]
        elif any(c in name for c in '"\'\\;{}[]'):
            errors.append("Name cannot contain: \" ' \\ ; { } [ ]")

        # Check for duplicate names (excluding current channel in edit mode)
        if name and self.existing_channels:
            for ch in self.existing_channels:
                # Check both 'name' and 'id' for backwards compatibility
                ch_name = ch.get("name", "") or ch.get("id", "")
                if ch_name == name:
                    # In edit mode, skip self
                    if self.is_edit_mode and ch.get("channel_id") == self._channel_id:
                        continue
                    errors.append(f"Name '{name}' is already used by another channel")
                    break

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
            "channel_name": name,  # Primary identifier - used by firmware
            "name": name,  # Alias for backwards compatibility
            "channel_type": self.channel_type.value if self.channel_type else ""
        }

    def get_config(self) -> Dict[str, Any]:
        """Override in subclasses to return full configuration"""
        return self.get_base_config()

    def _create_channel_selector(self, placeholder: str = "Select channel...") -> tuple:
        """
        Create channel selector widget with browse and clear buttons.

        Returns:
            tuple: (container_widget, line_edit)
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setPlaceholderText(placeholder)
        layout.addWidget(edit, stretch=1)

        # Clear button (hidden when empty)
        clear_btn = QPushButton("×")
        clear_btn.setMaximumWidth(24)
        clear_btn.setToolTip("Clear selection")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #888;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff4444;
            }
        """)
        clear_btn.setVisible(False)

        def update_clear_button_visibility():
            clear_btn.setVisible(bool(edit.text()))

        def clear_selection():
            edit.setText("")
            edit.setProperty("channel_id", None)
            clear_btn.setVisible(False)

        clear_btn.clicked.connect(clear_selection)
        edit.textChanged.connect(update_clear_button_visibility)
        layout.addWidget(clear_btn)

        # Browse button
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
        """Get display name for a channel by its numeric channel_id.

        Delegates to ChannelDisplayService for centralized lookup.

        Returns channel_name (user-friendly) for display in the input field.
        """
        return ChannelDisplayService.get_display_name(channel_id, self.available_channels)

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

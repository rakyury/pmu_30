"""
Base GPIO Dialog
Common base class for all GPIO configuration dialogs
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from models.gpio import GPIOBase, GPIOType, get_gpio_display_name


class BaseGPIODialog(QDialog):
    """Base dialog for configuring GPIO channels"""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 gpio_type: GPIOType = None):
        super().__init__(parent)

        self.config = config or {}
        self.available_channels = available_channels or {}
        self.gpio_type = gpio_type
        self.is_edit_mode = bool(config and config.get("id"))

        self._init_base_ui()

        if config:
            self._load_base_config(config)

    def _init_base_ui(self):
        """Initialize base UI components"""
        title = "Edit" if self.is_edit_mode else "New"
        type_name = get_gpio_display_name(self.gpio_type) if self.gpio_type else "Channel"
        self.setWindowTitle(f"{title} {type_name}")
        self.setModal(True)
        self.setMinimumWidth(550)
        self.setMinimumHeight(350)
        self.resize(600, 400)

        self.main_layout = QVBoxLayout(self)

        # Create scroll area for content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_widget = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_widget)

        # Basic settings group (common for all GPIO types)
        self._create_basic_group()

        self.scroll.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll)

        # Buttons
        self._create_buttons()

    def _create_basic_group(self):
        """Create basic settings group"""
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        # ID field
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("Unique identifier (e.g., ignition_switch)")
        if self.is_edit_mode:
            self.id_edit.setEnabled(False)  # Cannot change ID in edit mode
        basic_layout.addRow("ID: *", self.id_edit)

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
        self.id_edit.setText(config.get("id", ""))

    def _validate_base(self) -> List[str]:
        """Validate base fields, return list of errors"""
        errors = []

        channel_id = self.id_edit.text().strip()
        if not channel_id:
            errors.append("ID is required")
        elif not channel_id[0].isalpha():
            errors.append("ID must start with a letter")
        elif not all(c.isalnum() or c == '_' for c in channel_id):
            errors.append("ID can only contain letters, numbers, and underscores")

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
        return {
            "id": self.id_edit.text().strip(),
            "gpio_type": self.gpio_type.value if self.gpio_type else ""
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
        channel = ChannelSelectorDialog.select_channel(
            self, current, self.available_channels
        )
        if channel:
            target_edit.setText(channel)

    def _create_edge_combo(self, include_both: bool = True) -> QComboBox:
        """Create edge selection combobox"""
        combo = QComboBox()
        combo.addItem("Rising", "rising")
        combo.addItem("Falling", "falling")
        if include_both:
            combo.addItem("Both", "both")
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
        channel = ChannelSelectorDialog.select_channel(
            self, "", self.available_channels
        )
        if channel:
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

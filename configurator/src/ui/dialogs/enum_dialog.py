"""
Enumeration Configuration Dialog
Supports creating enumerations with value/color/text items
Can be used as axis for 2D tables
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QVBoxLayout, QDialog,
    QLabel, QLineEdit, QSpinBox, QColorDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, EnumItem


class EnumItemDialog(QDialog):
    """Dialog for editing a single enum item"""

    def __init__(self, parent=None, item: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.item = item or {}
        self._init_ui()
        if item:
            self._load_item(item)

    def _init_ui(self):
        self.setWindowTitle("Edit Enum Item")
        self.setModal(True)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        # Value
        self.value_spin = QSpinBox()
        self.value_spin.setRange(-2147483648, 2147483647)
        self.value_spin.setValue(0)
        form_layout.addRow("Value:", self.value_spin)

        # Text
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Display text (e.g., 'Neutral', 'Gear 1')")
        form_layout.addRow("Text:", self.text_edit)

        # Color
        color_layout = QHBoxLayout()
        self.color_edit = QLineEdit()
        self.color_edit.setText("#FFFFFF")
        self.color_edit.setMaximumWidth(100)
        color_layout.addWidget(self.color_edit)

        self.color_btn = QPushButton("Pick...")
        self.color_btn.clicked.connect(self._pick_color)
        color_layout.addWidget(self.color_btn)

        self.color_preview = QLabel()
        self.color_preview.setFixedSize(24, 24)
        self._update_color_preview()
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()

        form_layout.addRow("Color:", color_layout)

        layout.addLayout(form_layout)

        # Connect color edit to preview
        self.color_edit.textChanged.connect(self._update_color_preview)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _pick_color(self):
        """Open color picker dialog"""
        current = QColor(self.color_edit.text())
        color = QColorDialog.getColor(current, self, "Select Color")
        if color.isValid():
            self.color_edit.setText(color.name().upper())

    def _update_color_preview(self):
        """Update color preview label"""
        color = self.color_edit.text()
        self.color_preview.setStyleSheet(
            f"background-color: {color}; border: 1px solid #888;"
        )

    def _load_item(self, item: Dict[str, Any]):
        """Load item data"""
        self.value_spin.setValue(item.get("value", 0))
        self.text_edit.setText(item.get("text", ""))
        self.color_edit.setText(item.get("color", "#FFFFFF"))

    def _on_accept(self):
        """Validate and accept"""
        if not self.text_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Text is required")
            return
        self.accept()

    def get_item(self) -> Dict[str, Any]:
        """Get item data"""
        return {
            "value": self.value_spin.value(),
            "text": self.text_edit.text().strip(),
            "color": self.color_edit.text().strip().upper()
        }


class EnumDialog(BaseChannelDialog):
    """Dialog for configuring enumeration channels"""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent, config, available_channels, ChannelType.ENUM, existing_channels)

        self._create_settings_group()
        self._create_items_group()

        # Load config if editing
        if config:
            self._load_specific_config(config)

        # Finalize UI sizing
        self._finalize_ui()

    def _create_settings_group(self):
        """Create settings group"""
        settings_group = QGroupBox("Enumeration Settings")
        settings_layout = QFormLayout()

        # Bitfield checkbox
        self.bitfield_check = QCheckBox("Bitfield mode")
        self.bitfield_check.setToolTip(
            "When enabled, values are treated as bit flags.\n"
            "Multiple items can be active simultaneously."
        )
        settings_layout.addRow("", self.bitfield_check)

        # Info
        info_label = QLabel(
            "Enumerations define discrete named values.\n"
            "Can be used as table axis or for state display."
        )
        info_label.setStyleSheet("color: #b0b0b0; font-style: italic;")
        settings_layout.addRow("", info_label)

        settings_group.setLayout(settings_layout)
        self.content_layout.addWidget(settings_group)

    def _create_items_group(self):
        """Create items table group"""
        items_group = QGroupBox("Items")
        items_layout = QVBoxLayout()

        # Table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3)
        self.items_table.setHorizontalHeaderLabels(["Value", "Color", "Text"])
        self.items_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.items_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.items_table.itemDoubleClicked.connect(self._on_edit_item)
        items_layout.addWidget(self.items_table)

        # Buttons
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._on_add_item)
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._on_edit_item)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._on_delete_item)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        delete_all_btn = QPushButton("Delete All")
        delete_all_btn.clicked.connect(self._on_delete_all)
        btn_layout.addWidget(delete_all_btn)

        items_layout.addLayout(btn_layout)

        items_group.setLayout(items_layout)
        self.content_layout.addWidget(items_group)

        # Add default item
        if not self.config.get("items"):
            self._add_item_to_table({"value": 0, "text": "?", "color": "#FFFFFF"})

    def _add_item_to_table(self, item: Dict[str, Any]):
        """Add item to table"""
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        # Value
        value_item = QTableWidgetItem(str(item.get("value", 0)))
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.items_table.setItem(row, 0, value_item)

        # Color
        color = item.get("color", "#FFFFFF")
        color_item = QTableWidgetItem(color)
        color_item.setBackground(QColor(color))
        color_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.items_table.setItem(row, 1, color_item)

        # Text
        text_item = QTableWidgetItem(item.get("text", ""))
        self.items_table.setItem(row, 2, text_item)

    def _on_add_item(self):
        """Add new item"""
        # Suggest next value
        next_value = 0
        if self.items_table.rowCount() > 0:
            try:
                last_value = int(self.items_table.item(
                    self.items_table.rowCount() - 1, 0
                ).text())
                next_value = last_value + 1
            except (ValueError, AttributeError):
                pass

        dialog = EnumItemDialog(self, {"value": next_value, "text": "", "color": "#FFFFFF"})
        if dialog.exec():
            self._add_item_to_table(dialog.get_item())

    def _on_edit_item(self):
        """Edit selected item"""
        row = self.items_table.currentRow()
        if row < 0:
            return

        item = {
            "value": int(self.items_table.item(row, 0).text()),
            "color": self.items_table.item(row, 1).text(),
            "text": self.items_table.item(row, 2).text()
        }

        dialog = EnumItemDialog(self, item)
        if dialog.exec():
            new_item = dialog.get_item()
            self.items_table.item(row, 0).setText(str(new_item["value"]))
            self.items_table.item(row, 1).setText(new_item["color"])
            self.items_table.item(row, 1).setBackground(QColor(new_item["color"]))
            self.items_table.item(row, 2).setText(new_item["text"])

    def _on_delete_item(self):
        """Delete selected item"""
        row = self.items_table.currentRow()
        if row >= 0:
            self.items_table.removeRow(row)

    def _on_delete_all(self):
        """Delete all items"""
        if self.items_table.rowCount() == 0:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Delete all items?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.items_table.setRowCount(0)

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        self.bitfield_check.setChecked(config.get("is_bitfield", False))

        # Load items
        self.items_table.setRowCount(0)
        items = config.get("items", [])
        for item in items:
            if isinstance(item, dict):
                self._add_item_to_table(item)

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []

        if self.items_table.rowCount() == 0:
            errors.append("At least one item is required")

        # Check for duplicate values
        values = set()
        for row in range(self.items_table.rowCount()):
            try:
                value = int(self.items_table.item(row, 0).text())
                if value in values:
                    errors.append(f"Duplicate value: {value}")
                values.add(value)
            except (ValueError, AttributeError):
                errors.append(f"Invalid value at row {row + 1}")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()

        items = []
        for row in range(self.items_table.rowCount()):
            try:
                items.append({
                    "value": int(self.items_table.item(row, 0).text()),
                    "color": self.items_table.item(row, 1).text(),
                    "text": self.items_table.item(row, 2).text()
                })
            except (ValueError, AttributeError):
                pass

        config.update({
            "is_bitfield": self.bitfield_check.isChecked(),
            "items": items
        })

        return config

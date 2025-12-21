"""
Table Configuration Dialog
Allows creation of interpolation lookup tables
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QPushButton,
    QDialogButtonBox, QGroupBox, QCheckBox, QLabel, QHeaderView
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List


class TableDialog(QDialog):
    """Dialog for configuring lookup tables."""

    INTERPOLATION_TYPES = [
        "Linear",
        "Step (Hold previous)",
        "Step (Hold next)"
    ]

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None, available_channels: Optional[List[str]] = None):
        super().__init__(parent)
        self.config = config or {}
        self.available_channels = available_channels or []
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Table Configuration")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter table name...")
        basic_layout.addRow("Name: *", self.name_edit)

        self.input_channel_combo = QComboBox()
        self.input_channel_combo.setEditable(True)
        self.input_channel_combo.addItems(self.available_channels)
        self.input_channel_combo.setPlaceholderText("Select input channel...")
        basic_layout.addRow("Input Channel:", self.input_channel_combo)

        self.interpolation_combo = QComboBox()
        self.interpolation_combo.addItems(self.INTERPOLATION_TYPES)
        basic_layout.addRow("Interpolation:", self.interpolation_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Table group
        table_group = QGroupBox("Lookup Table")
        table_layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()

        self.add_row_btn = QPushButton("Add Row")
        self.add_row_btn.clicked.connect(self._add_row)
        toolbar.addWidget(self.add_row_btn)

        self.remove_row_btn = QPushButton("Remove Row")
        self.remove_row_btn.clicked.connect(self._remove_row)
        toolbar.addWidget(self.remove_row_btn)

        toolbar.addStretch()

        self.sort_btn = QPushButton("Sort by X")
        self.sort_btn.clicked.connect(self._sort_table)
        toolbar.addWidget(self.sort_btn)

        table_layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Input (X)", "Output (Y)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(250)
        table_layout.addWidget(self.table)

        # Add default rows
        for _ in range(5):
            self._add_row()

        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        # Options
        options_layout = QHBoxLayout()
        self.clamp_check = QCheckBox("Clamp output to table range")
        self.clamp_check.setChecked(True)
        options_layout.addWidget(self.clamp_check)
        options_layout.addStretch()
        layout.addLayout(options_layout)

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
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _add_row(self):
        """Add row to table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Create editable cells
        x_item = QTableWidgetItem("0.0")
        y_item = QTableWidgetItem("0.0")

        self.table.setItem(row, 0, x_item)
        self.table.setItem(row, 1, y_item)

    def _remove_row(self):
        """Remove selected row."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def _sort_table(self):
        """Sort table by X values."""
        # Collect all rows
        rows = []
        for i in range(self.table.rowCount()):
            x_item = self.table.item(i, 0)
            y_item = self.table.item(i, 1)
            if x_item and y_item:
                try:
                    x_val = float(x_item.text())
                    y_val = float(y_item.text())
                    rows.append((x_val, y_val))
                except ValueError:
                    continue

        # Sort by X
        rows.sort(key=lambda r: r[0])

        # Clear table and refill
        self.table.setRowCount(0)
        for x_val, y_val in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(x_val)))
            self.table.setItem(row, 1, QTableWidgetItem(str(y_val)))

    def _load_config(self):
        """Load configuration into UI."""
        if not self.config:
            return

        self.name_edit.setText(self.config.get("name", ""))

        input_channel = self.config.get("input_channel", "")
        if input_channel:
            self.input_channel_combo.setCurrentText(input_channel)

        interpolation = self.config.get("interpolation", "Linear")
        idx = self.interpolation_combo.findText(interpolation)
        if idx >= 0:
            self.interpolation_combo.setCurrentIndex(idx)

        # Load table data
        table_data = self.config.get("table_data", [])
        if table_data:
            self.table.setRowCount(0)
            for x_val, y_val in table_data:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(x_val)))
                self.table.setItem(row, 1, QTableWidgetItem(str(y_val)))

        self.clamp_check.setChecked(self.config.get("clamp_output", True))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from UI."""
        # Collect table data
        table_data = []
        for i in range(self.table.rowCount()):
            x_item = self.table.item(i, 0)
            y_item = self.table.item(i, 1)
            if x_item and y_item:
                try:
                    x_val = float(x_item.text())
                    y_val = float(y_item.text())
                    table_data.append((x_val, y_val))
                except ValueError:
                    continue

        return {
            "name": self.name_edit.text(),
            "input_channel": self.input_channel_combo.currentText(),
            "interpolation": self.interpolation_combo.currentText(),
            "table_data": table_data,
            "clamp_output": self.clamp_check.isChecked()
        }

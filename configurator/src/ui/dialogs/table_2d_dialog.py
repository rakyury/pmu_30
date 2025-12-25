"""
2D Table Configuration Dialog
Lookup table with X axis channel and auto-generated values
"""

from PyQt6.QtWidgets import (
    QGroupBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QVBoxLayout, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType


class Table2DDialog(BaseChannelDialog):
    """Dialog for configuring 2D lookup table channels."""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent, config, available_channels, ChannelType.TABLE_2D, existing_channels)

        # Increase dialog size for table content
        self.resize(650, 500)

        self._create_axis_group()
        self._create_table_group()

        # Connect signals
        self.x_min_spin.valueChanged.connect(self._update_columns_label)
        self.x_max_spin.valueChanged.connect(self._update_columns_label)
        self.x_step_spin.valueChanged.connect(self._update_columns_label)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        self._update_columns_label()

    def _create_axis_group(self):
        """Create axis configuration group"""
        axis_group = QGroupBox("Axis Configuration")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Decimal places
        layout.addWidget(QLabel("Decimal places:"), row, 0)
        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(0, 6)
        self.decimal_spin.setValue(0)
        layout.addWidget(self.decimal_spin, row, 1)
        row += 1

        # X axis channel (full width)
        layout.addWidget(QLabel("Axis X channel: *"), row, 0)
        self.x_channel_widget, self.x_channel_edit = self._create_channel_selector(
            "Select X axis channel..."
        )
        layout.addWidget(self.x_channel_widget, row, 1, 1, 3)
        row += 1

        # X axis: min, max, step
        layout.addWidget(QLabel("min:"), row, 0)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1000000, 1000000)
        self.x_min_spin.setDecimals(2)
        self.x_min_spin.setValue(0)
        layout.addWidget(self.x_min_spin, row, 1)

        layout.addWidget(QLabel("max:"), row, 2)
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1000000, 1000000)
        self.x_max_spin.setDecimals(2)
        self.x_max_spin.setValue(100)
        layout.addWidget(self.x_max_spin, row, 3)
        row += 1

        layout.addWidget(QLabel("step:"), row, 0)
        self.x_step_spin = QDoubleSpinBox()
        self.x_step_spin.setRange(0.001, 100000)
        self.x_step_spin.setDecimals(2)
        self.x_step_spin.setValue(10)
        layout.addWidget(self.x_step_spin, row, 1)

        # Columns label
        self.columns_label = QLabel("columns: 11")
        self.columns_label.setStyleSheet("color: #0078d4;")
        layout.addWidget(self.columns_label, row, 2, 1, 2)
        row += 1

        # Create button
        self.create_btn = QPushButton("Create Table")
        self.create_btn.clicked.connect(self._create_table)
        layout.addWidget(self.create_btn, row, 0, 1, 4)

        axis_group.setLayout(layout)
        self.content_layout.addWidget(axis_group)

    def _create_table_group(self):
        """Create table editor group"""
        table_group = QGroupBox("Table Data")
        layout = QVBoxLayout()

        # X axis label
        self.x_axis_label = QLabel("X: -")
        self.x_axis_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        layout.addWidget(self.x_axis_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.table_widget = QTableWidget()
        self.table_widget.setMinimumHeight(150)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_widget.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.cellChanged.connect(self._update_heat_map)

        layout.addWidget(self.table_widget)

        # Info label
        info = QLabel("Click 'Create Table' to generate axis values, then edit output values.")
        info.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addWidget(info)

        table_group.setLayout(layout)
        self.content_layout.addWidget(table_group)

    def _update_columns_label(self):
        """Update the columns count label"""
        x_values = self._generate_x_values()
        self.columns_label.setText(f"columns: {len(x_values)}")

    def _generate_x_values(self) -> List[float]:
        """Generate X axis values based on min, max, step"""
        x_min = self.x_min_spin.value()
        x_max = self.x_max_spin.value()
        x_step = self.x_step_spin.value()

        if x_step <= 0 or x_min >= x_max:
            return [x_min]

        values = []
        v = x_min
        while v <= x_max + 0.0001:  # Small epsilon for floating point
            values.append(round(v, 2))
            v += x_step
        return values

    def _create_table(self):
        """Generate table based on axis configuration"""
        # Validate axis channel is selected
        x_channel = self.x_channel_edit.text().strip()
        if not x_channel:
            QMessageBox.warning(self, "Validation Error", "Please select X axis channel first")
            return

        x_values = self._generate_x_values()

        self.table_widget.blockSignals(True)
        self.table_widget.setRowCount(1)
        self.table_widget.setColumnCount(len(x_values))

        # Update axis label
        self.x_axis_label.setText(f"X: {x_channel}")

        # Set headers (X values)
        headers = [str(v) for v in x_values]
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setVerticalHeaderLabels(["Output"])

        # Initialize cells with 0
        for col in range(len(x_values)):
            item = QTableWidgetItem("0")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_widget.setItem(0, col, item)

        self.table_widget.blockSignals(False)
        self._update_heat_map()

    def _get_heat_map_color(self, value: float, min_val: float, max_val: float) -> QColor:
        """Calculate heat map color for a value (blue -> green -> yellow -> red)"""
        if max_val == min_val:
            return QColor(255, 255, 255)  # White for uniform values

        # Normalize to 0-1 range
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0.0, min(1.0, normalized))

        # Color gradient: blue (0) -> cyan (0.25) -> green (0.5) -> yellow (0.75) -> red (1)
        if normalized < 0.25:
            t = normalized / 0.25
            r, g, b = 0, int(255 * t), 255
        elif normalized < 0.5:
            t = (normalized - 0.25) / 0.25
            r, g, b = 0, 255, int(255 * (1 - t))
        elif normalized < 0.75:
            t = (normalized - 0.5) / 0.25
            r, g, b = int(255 * t), 255, 0
        else:
            t = (normalized - 0.75) / 0.25
            r, g, b = 255, int(255 * (1 - t)), 0

        return QColor(r, g, b)

    def _update_heat_map(self):
        """Update cell colors based on values"""
        if self.table_widget.columnCount() == 0:
            return

        # Collect all values
        values = []
        for col in range(self.table_widget.columnCount()):
            item = self.table_widget.item(0, col)
            if item:
                try:
                    values.append(float(item.text()))
                except ValueError:
                    values.append(0.0)

        if not values:
            return

        min_val = min(values)
        max_val = max(values)

        # Apply colors
        self.table_widget.blockSignals(True)
        for col in range(self.table_widget.columnCount()):
            item = self.table_widget.item(0, col)
            if item:
                try:
                    val = float(item.text())
                except ValueError:
                    val = 0.0
                color = self._get_heat_map_color(val, min_val, max_val)
                item.setBackground(color)
        self.table_widget.blockSignals(False)

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        # Axis configuration
        x_channel = config.get("x_axis_channel", "")
        self.x_channel_edit.setText(x_channel)
        self.x_min_spin.setValue(config.get("x_min", 0.0))
        self.x_max_spin.setValue(config.get("x_max", 100.0))
        self.x_step_spin.setValue(config.get("x_step", 10.0))
        self.decimal_spin.setValue(config.get("decimal_places", 0))

        # Load existing table data
        x_values = config.get("x_values", [])
        output_values = config.get("output_values", [])

        if x_values and output_values:
            self.table_widget.blockSignals(True)
            self.table_widget.setRowCount(1)
            self.table_widget.setColumnCount(len(x_values))

            # Update axis label
            self.x_axis_label.setText(f"X: {x_channel or '-'}")

            headers = [str(v) for v in x_values]
            self.table_widget.setHorizontalHeaderLabels(headers)
            self.table_widget.setVerticalHeaderLabels(["Output"])

            for col, val in enumerate(output_values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_widget.setItem(0, col, item)

            self.table_widget.blockSignals(False)
            self._update_heat_map()

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []

        if not self.x_channel_edit.text().strip():
            errors.append("X axis channel is required")

        if self.x_min_spin.value() >= self.x_max_spin.value():
            errors.append("X min must be less than X max")

        if self.x_step_spin.value() <= 0:
            errors.append("X step must be greater than 0")

        if self.table_widget.columnCount() == 0:
            errors.append("Please create table first")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()

        # Get X values from headers
        x_values = []
        for col in range(self.table_widget.columnCount()):
            header = self.table_widget.horizontalHeaderItem(col)
            if header:
                try:
                    x_values.append(float(header.text()))
                except ValueError:
                    x_values.append(0.0)

        # Get output values from cells
        output_values = []
        for col in range(self.table_widget.columnCount()):
            item = self.table_widget.item(0, col)
            if item:
                try:
                    output_values.append(float(item.text()))
                except ValueError:
                    output_values.append(0.0)
            else:
                output_values.append(0.0)

        config.update({
            "x_axis_channel": self.x_channel_edit.text().strip(),
            "x_min": self.x_min_spin.value(),
            "x_max": self.x_max_spin.value(),
            "x_step": self.x_step_spin.value(),
            "x_values": x_values,
            "output_values": output_values,
            "decimal_places": self.decimal_spin.value()
        })

        return config

"""
3D Table Configuration Dialog
Lookup table with X and Y axis channels and auto-generated values
Based on ECUMaster ADU Table implementation
"""

from PyQt6.QtWidgets import (
    QGroupBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QVBoxLayout, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter
from typing import Dict, Any, Optional, List

from .base_gpio_dialog import BaseGPIODialog
from models.gpio import GPIOType


class VerticalLabel(QLabel):
    """Label that displays text vertically (rotated 90 degrees counter-clockwise)"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumWidth(20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.translate(0, self.height())
        painter.rotate(-90)
        painter.drawText(0, 0, self.height(), self.width(), Qt.AlignmentFlag.AlignCenter, self.text())

    def minimumSizeHint(self):
        size = super().minimumSizeHint()
        return QSize(size.height(), size.width())

    def sizeHint(self):
        size = super().sizeHint()
        return QSize(size.height(), size.width())


class Table3DDialog(BaseGPIODialog):
    """Dialog for configuring 3D lookup table channels."""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None):
        super().__init__(parent, config, available_channels, GPIOType.TABLE_3D)

        # Increase dialog size for 3D table content
        self.setMinimumHeight(550)
        self.resize(700, 600)

        self._create_axis_group()
        self._create_table_group()

        # Connect signals
        self.x_min_spin.valueChanged.connect(self._update_size_labels)
        self.x_max_spin.valueChanged.connect(self._update_size_labels)
        self.x_step_spin.valueChanged.connect(self._update_size_labels)
        self.y_min_spin.valueChanged.connect(self._update_size_labels)
        self.y_max_spin.valueChanged.connect(self._update_size_labels)
        self.y_step_spin.valueChanged.connect(self._update_size_labels)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        self._update_size_labels()

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

        # X axis: min, max
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

        # X axis: step and columns
        layout.addWidget(QLabel("step:"), row, 0)
        self.x_step_spin = QDoubleSpinBox()
        self.x_step_spin.setRange(0.001, 100000)
        self.x_step_spin.setDecimals(2)
        self.x_step_spin.setValue(10)
        layout.addWidget(self.x_step_spin, row, 1)

        self.columns_label = QLabel("columns: 11")
        self.columns_label.setStyleSheet("color: #0078d4;")
        layout.addWidget(self.columns_label, row, 2, 1, 2)
        row += 1

        # Y axis channel (full width)
        layout.addWidget(QLabel("Axis Y channel: *"), row, 0)
        self.y_channel_widget, self.y_channel_edit = self._create_channel_selector(
            "Select Y axis channel..."
        )
        layout.addWidget(self.y_channel_widget, row, 1, 1, 3)
        row += 1

        # Y axis: min, max
        layout.addWidget(QLabel("min:"), row, 0)
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1000000, 1000000)
        self.y_min_spin.setDecimals(2)
        self.y_min_spin.setValue(0)
        layout.addWidget(self.y_min_spin, row, 1)

        layout.addWidget(QLabel("max:"), row, 2)
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1000000, 1000000)
        self.y_max_spin.setDecimals(2)
        self.y_max_spin.setValue(100)
        layout.addWidget(self.y_max_spin, row, 3)
        row += 1

        # Y axis: step and rows
        layout.addWidget(QLabel("step:"), row, 0)
        self.y_step_spin = QDoubleSpinBox()
        self.y_step_spin.setRange(0.001, 100000)
        self.y_step_spin.setDecimals(2)
        self.y_step_spin.setValue(10)
        layout.addWidget(self.y_step_spin, row, 1)

        self.rows_label = QLabel("rows: 11")
        self.rows_label.setStyleSheet("color: #0078d4;")
        layout.addWidget(self.rows_label, row, 2, 1, 2)
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
        main_layout = QVBoxLayout()

        # X axis label (horizontal, centered above table)
        self.x_axis_label = QLabel("X: -")
        self.x_axis_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        main_layout.addWidget(self.x_axis_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Horizontal layout for Y label + table
        table_row = QHBoxLayout()

        # Y axis label (vertical, on the left of table)
        self.y_axis_label = VerticalLabel("Y: -")
        self.y_axis_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        table_row.addWidget(self.y_axis_label)

        self.table_widget = QTableWidget()
        self.table_widget.setMinimumHeight(200)
        self.table_widget.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.cellChanged.connect(self._update_heat_map)
        table_row.addWidget(self.table_widget)

        main_layout.addLayout(table_row)

        # Info label
        info = QLabel("Click 'Create Table' to generate axis values, then edit output values.")
        info.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(info)

        table_group.setLayout(main_layout)
        self.content_layout.addWidget(table_group)

    def _update_size_labels(self):
        """Update the columns and rows count labels"""
        x_values = self._generate_axis_values(
            self.x_min_spin.value(),
            self.x_max_spin.value(),
            self.x_step_spin.value()
        )
        y_values = self._generate_axis_values(
            self.y_min_spin.value(),
            self.y_max_spin.value(),
            self.y_step_spin.value()
        )
        self.columns_label.setText(f"columns: {len(x_values)}")
        self.rows_label.setText(f"rows: {len(y_values)}")

    def _generate_axis_values(self, min_val: float, max_val: float, step: float) -> List[float]:
        """Generate axis values based on min, max, step"""
        if step <= 0 or min_val >= max_val:
            return [min_val]

        values = []
        v = min_val
        while v <= max_val + 0.0001:  # Small epsilon for floating point
            values.append(round(v, 2))
            v += step
        return values

    def _create_table(self):
        """Generate table based on axis configuration"""
        # Validate axis channels are selected
        x_channel = self.x_channel_edit.text().strip()
        y_channel = self.y_channel_edit.text().strip()
        if not x_channel or not y_channel:
            errors = []
            if not x_channel:
                errors.append("X axis channel")
            if not y_channel:
                errors.append("Y axis channel")
            QMessageBox.warning(
                self, "Validation Error",
                f"Please select: {', '.join(errors)}"
            )
            return

        x_values = self._generate_axis_values(
            self.x_min_spin.value(),
            self.x_max_spin.value(),
            self.x_step_spin.value()
        )
        y_values = self._generate_axis_values(
            self.y_min_spin.value(),
            self.y_max_spin.value(),
            self.y_step_spin.value()
        )

        self.table_widget.blockSignals(True)
        self.table_widget.setRowCount(len(y_values))
        self.table_widget.setColumnCount(len(x_values))

        # Update axis labels
        self.x_axis_label.setText(f"X: {x_channel}")
        self.y_axis_label.setText(f"Y: {y_channel}")

        # Set headers
        x_headers = [str(v) for v in x_values]
        y_headers = [str(v) for v in y_values]
        self.table_widget.setHorizontalHeaderLabels(x_headers)
        self.table_widget.setVerticalHeaderLabels(y_headers)

        # Initialize cells with 0
        for row in range(len(y_values)):
            for col in range(len(x_values)):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_widget.setItem(row, col, item)

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
        if self.table_widget.rowCount() == 0 or self.table_widget.columnCount() == 0:
            return

        # Collect all values
        values = []
        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
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
        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
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
        y_channel = config.get("y_axis_channel", "")
        self.x_channel_edit.setText(x_channel)
        self.y_channel_edit.setText(y_channel)
        self.x_min_spin.setValue(config.get("x_min", 0.0))
        self.x_max_spin.setValue(config.get("x_max", 100.0))
        self.x_step_spin.setValue(config.get("x_step", 10.0))
        self.y_min_spin.setValue(config.get("y_min", 0.0))
        self.y_max_spin.setValue(config.get("y_max", 100.0))
        self.y_step_spin.setValue(config.get("y_step", 10.0))
        self.decimal_spin.setValue(config.get("decimal_places", 0))

        # Load existing table data
        x_values = config.get("x_values", [])
        y_values = config.get("y_values", [])
        data = config.get("data", [])

        if x_values and y_values and data:
            self.table_widget.blockSignals(True)
            self.table_widget.setRowCount(len(y_values))
            self.table_widget.setColumnCount(len(x_values))

            # Update axis labels
            self.x_axis_label.setText(f"X: {x_channel or '-'}")
            self.y_axis_label.setText(f"Y: {y_channel or '-'}")

            x_headers = [str(v) for v in x_values]
            y_headers = [str(v) for v in y_values]
            self.table_widget.setHorizontalHeaderLabels(x_headers)
            self.table_widget.setVerticalHeaderLabels(y_headers)

            for row_idx, row_data in enumerate(data):
                if row_idx < len(y_values):
                    for col_idx, val in enumerate(row_data):
                        if col_idx < len(x_values):
                            item = QTableWidgetItem(str(val))
                            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            self.table_widget.setItem(row_idx, col_idx, item)

            self.table_widget.blockSignals(False)
            self._update_heat_map()

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []

        if not self.x_channel_edit.text().strip():
            errors.append("X axis channel is required")

        if not self.y_channel_edit.text().strip():
            errors.append("Y axis channel is required")

        if self.x_min_spin.value() >= self.x_max_spin.value():
            errors.append("X min must be less than X max")

        if self.x_step_spin.value() <= 0:
            errors.append("X step must be greater than 0")

        if self.y_min_spin.value() >= self.y_max_spin.value():
            errors.append("Y min must be less than Y max")

        if self.y_step_spin.value() <= 0:
            errors.append("Y step must be greater than 0")

        if self.table_widget.rowCount() == 0 or self.table_widget.columnCount() == 0:
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

        # Get Y values from headers
        y_values = []
        for row in range(self.table_widget.rowCount()):
            header = self.table_widget.verticalHeaderItem(row)
            if header:
                try:
                    y_values.append(float(header.text()))
                except ValueError:
                    y_values.append(0.0)

        # Get data from cells (2D matrix)
        data = []
        for row in range(self.table_widget.rowCount()):
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                if item:
                    try:
                        row_data.append(float(item.text()))
                    except ValueError:
                        row_data.append(0.0)
                else:
                    row_data.append(0.0)
            data.append(row_data)

        config.update({
            "x_axis_channel": self.x_channel_edit.text().strip(),
            "y_axis_channel": self.y_channel_edit.text().strip(),
            "x_min": self.x_min_spin.value(),
            "x_max": self.x_max_spin.value(),
            "x_step": self.x_step_spin.value(),
            "x_values": x_values,
            "y_min": self.y_min_spin.value(),
            "y_max": self.y_max_spin.value(),
            "y_step": self.y_step_spin.value(),
            "y_values": y_values,
            "data": data,
            "decimal_places": self.decimal_spin.value()
        })

        return config

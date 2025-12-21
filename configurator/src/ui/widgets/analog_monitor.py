"""
Analog Monitor Widget
Real-time monitoring of analog input channels
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer
from typing import Dict, List


class AnalogMonitor(QWidget):
    """Analog input channels monitor widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs_data = []
        self._init_ui()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_values)
        self.update_timer.start(100)  # Update every 100ms

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Toolbar
        toolbar = QHBoxLayout()

        self.pin_btn = QPushButton("pin")
        self.pin_btn.setMaximumWidth(40)
        self.pin_btn.setCheckable(True)
        toolbar.addWidget(self.pin_btn)

        self.abc_btn = QPushButton("abc")
        self.abc_btn.setMaximumWidth(40)
        toolbar.addWidget(self.abc_btn)

        toolbar.addStretch()

        # Info button
        self.info_btn = QPushButton("?")
        self.info_btn.setMaximumWidth(25)
        toolbar.addWidget(self.info_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Pin", "Name", "Value", "V"])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 40)   # Pin
        self.table.setColumnWidth(2, 80)   # Value
        self.table.setColumnWidth(3, 50)   # V

        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

    def set_inputs(self, inputs: List[Dict]):
        """Set inputs list."""
        self.inputs_data = inputs
        self._populate_table()

    def _populate_table(self):
        """Populate table with inputs."""
        self.table.setRowCount(len(self.inputs_data))

        for row, input_data in enumerate(self.inputs_data):
            # Pin (A1, A2, etc.)
            pin_item = QTableWidgetItem(f"A{input_data.get('channel', 0) + 1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, pin_item)

            # Name
            name = input_data.get('name', '')
            if name:
                name_item = QTableWidgetItem(f"in.{name}")
            else:
                name_item = QTableWidgetItem("")
            self.table.setItem(row, 1, name_item)

            # Value (? when offline)
            value_item = QTableWidgetItem("?")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, value_item)

            # Voltage
            voltage_item = QTableWidgetItem("?")
            voltage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, voltage_item)

            # Highlight disabled inputs
            if not input_data.get('enabled', False):
                for col in range(4):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(Qt.GlobalColor.gray)

    def _update_values(self):
        """Update real-time values (when connected to device)."""
        # TODO: Update from device when connected
        pass

    def update_input_value(self, channel: int, value: float, voltage: float):
        """Update specific input value."""
        for row in range(self.table.rowCount()):
            pin_text = self.table.item(row, 0).text()
            if pin_text == f"A{channel + 1}":
                self.table.item(row, 2).setText(f"{value:.2f}")
                self.table.item(row, 3).setText(f"{voltage:.1f}")
                break

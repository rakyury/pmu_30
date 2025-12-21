"""
Output Monitor Widget
Real-time monitoring of output channels
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer
from typing import Dict, List


class OutputMonitor(QWidget):
    """Output channels monitor widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.outputs_data = []
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Pin", "Name", "Status", "V", "Load"])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 40)   # Pin
        self.table.setColumnWidth(2, 50)   # Status
        self.table.setColumnWidth(3, 50)   # V
        self.table.setColumnWidth(4, 50)   # Load

        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

    def set_outputs(self, outputs: List[Dict]):
        """Set outputs list."""
        self.outputs_data = outputs
        self._populate_table()

    def _populate_table(self):
        """Populate table with outputs."""
        self.table.setRowCount(len(self.outputs_data))

        for row, output in enumerate(self.outputs_data):
            # Pin (O1, O2, etc.)
            pin_item = QTableWidgetItem(f"O{output.get('channel', 0) + 1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, pin_item)

            # Name
            name = output.get('name', '')
            if name:
                name_item = QTableWidgetItem(f"o_{name}")
            else:
                name_item = QTableWidgetItem("")
            self.table.setItem(row, 1, name_item)

            # Status (? when offline)
            status_item = QTableWidgetItem("?")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, status_item)

            # Voltage
            voltage_item = QTableWidgetItem("?")
            voltage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, voltage_item)

            # Load
            load_item = QTableWidgetItem("?")
            load_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, load_item)

            # Highlight enabled outputs
            if not output.get('enabled', False):
                for col in range(5):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(Qt.GlobalColor.gray)

    def _update_values(self):
        """Update real-time values (when connected to device)."""
        # TODO: Update from device when connected
        pass

    def update_output_status(self, channel: int, status: str, voltage: float, load: float):
        """Update specific output status."""
        for row in range(self.table.rowCount()):
            pin_text = self.table.item(row, 0).text()
            if pin_text == f"O{channel + 1}":
                self.table.item(row, 2).setText(status)
                self.table.item(row, 3).setText(f"{voltage:.1f}")
                self.table.item(row, 4).setText(f"{load:.1f}")
                break

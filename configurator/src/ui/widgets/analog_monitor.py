"""
Analog Monitor Widget
Real-time monitoring of analog input channels with ECUMaster-compatible columns

ECUMaster column layout:
Pin | Name | Value | Vltg | Pu/pd

ECUMaster channel naming convention:
- pmuX.aY.voltage - Analog input voltage
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List


class AnalogMonitor(QWidget):
    """Analog input channels monitor widget with real-time telemetry display."""

    # Colors for different states
    COLOR_NORMAL = QColor(255, 255, 255)      # White
    COLOR_ACTIVE = QColor(200, 255, 200)      # Light green (signal present)
    COLOR_DISABLED = QColor(220, 220, 220)    # Light gray

    # Column indices - matching ECUMaster layout
    COL_PIN = 0
    COL_NAME = 1
    COL_VALUE = 2
    COL_VLTG = 3
    COL_PUPD = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs_data = []
        self._connected = False
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

        self.status_label = QLabel("Offline")
        self.status_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self.status_label)

        toolbar.addStretch()

        # Info button
        self.info_btn = QPushButton("?")
        self.info_btn.setMaximumWidth(25)
        toolbar.addWidget(self.info_btn)

        layout.addLayout(toolbar)

        # Table with ECUMaster-compatible columns
        # Pin | Name | Value | Vltg | Pu/pd
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Pin", "Name", "Value", "Vltg", "Pu/pd"])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_PIN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_VALUE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_VLTG, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_PUPD, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(self.COL_PIN, 30)     # Pin
        self.table.setColumnWidth(self.COL_VALUE, 60)   # Value
        self.table.setColumnWidth(self.COL_VLTG, 45)    # Vltg
        self.table.setColumnWidth(self.COL_PUPD, 45)    # Pu/pd

        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

    def set_inputs(self, inputs: List[Dict]):
        """Set inputs list."""
        self.inputs_data = inputs
        self._populate_table()

    def set_connected(self, connected: bool):
        """Set connection state."""
        self._connected = connected
        if connected:
            self.status_label.setText("Online")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("Offline")
            self.status_label.setStyleSheet("color: #888;")
            # Reset all values to "?"
            self._reset_values()

    def _reset_values(self):
        """Reset all telemetry values to '?'."""
        for row in range(self.table.rowCount()):
            for col in [self.COL_VALUE, self.COL_VLTG]:
                item = self.table.item(row, col)
                if item:
                    item.setText("?")
                    item.setBackground(QBrush(self.COLOR_DISABLED))

    def _populate_table(self):
        """Populate table with inputs."""
        self.table.setRowCount(len(self.inputs_data))

        for row, input_data in enumerate(self.inputs_data):
            channel = input_data.get('channel', 0)

            # Pin (A1, A2, etc.)
            pin_item = QTableWidgetItem(f"A{channel + 1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_PIN, pin_item)

            # Name
            name = input_data.get('name', '')
            if name:
                name_item = QTableWidgetItem(name)
            else:
                name_item = QTableWidgetItem("")
            self.table.setItem(row, self.COL_NAME, name_item)

            # Value (? when offline)
            value_item = QTableWidgetItem("?")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_VALUE, value_item)

            # Voltage
            vltg_item = QTableWidgetItem("?")
            vltg_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_VLTG, vltg_item)

            # Pull-up/Pull-down configuration
            pupd = input_data.get('pull_mode', 'none')
            pupd_str = ""
            if pupd == 'pull_up':
                pupd_str = "Pu"
            elif pupd == 'pull_down':
                pupd_str = "Pd"
            pupd_item = QTableWidgetItem(pupd_str)
            pupd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_PUPD, pupd_item)

            # Set initial row color
            self._set_row_color(row, self.COLOR_DISABLED)

            # Highlight disabled inputs
            if not input_data.get('enabled', False):
                for col in range(5):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(Qt.GlobalColor.gray)

    def _set_row_color(self, row: int, color: QColor):
        """Set background color for entire row."""
        for col in range(5):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(color))

    def _update_values(self):
        """Update real-time values (when connected to device)."""
        # Values are updated via update_from_telemetry() called from main window
        pass

    def update_input_value(self, channel: int, value: float, voltage: float):
        """Update specific input value (legacy method for backwards compatibility)."""
        for row in range(self.table.rowCount()):
            pin_item = self.table.item(row, self.COL_PIN)
            if pin_item and pin_item.text() == f"A{channel + 1}":
                self.table.item(row, self.COL_VALUE).setText(f"{value:.1f}")
                self.table.item(row, self.COL_VLTG).setText(f"{voltage:.2f}")

                # Highlight if signal is present (voltage > 0.1V)
                if voltage > 0.1:
                    self._set_row_color(row, self.COLOR_ACTIVE)
                else:
                    self._set_row_color(row, self.COLOR_NORMAL)
                break

    def update_from_telemetry(self, adc_values: List[int], reference_voltage: float = 5.0):
        """
        Update all analog inputs from telemetry data.

        Args:
            adc_values: List of raw ADC values (0-4095 for 12-bit)
            reference_voltage: ADC reference voltage (default 5.0V)
        """
        for row in range(min(self.table.rowCount(), len(self.inputs_data))):
            if row >= len(adc_values):
                break

            adc_raw = adc_values[row]

            # Convert raw ADC to voltage (12-bit ADC, reference voltage)
            voltage = (adc_raw / 4095.0) * reference_voltage

            # Value as percentage (0-100%)
            value_percent = (adc_raw / 4095.0) * 100

            # Update Value column
            value_item = self.table.item(row, self.COL_VALUE)
            if value_item:
                value_item.setText(f"{value_percent:.1f}")

            # Update Voltage column
            vltg_item = self.table.item(row, self.COL_VLTG)
            if vltg_item:
                vltg_item.setText(f"{voltage:.2f}")

            # Set row color based on signal presence
            if voltage > 0.1:
                self._set_row_color(row, self.COLOR_ACTIVE)
            else:
                self._set_row_color(row, self.COLOR_NORMAL)

    def get_channel_count(self) -> int:
        """Get number of configured analog inputs."""
        return len(self.inputs_data)

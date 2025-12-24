"""
Digital Input Monitor Widget
Real-time monitoring of digital input channels

Column layout:
Pin | Name | State | Type
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List


class DigitalMonitor(QWidget):
    """Digital input channels monitor widget with real-time telemetry display."""

    # Colors for different states
    COLOR_NORMAL = QColor(255, 255, 255)      # White
    COLOR_ACTIVE = QColor(200, 255, 200)      # Light green (ON state)
    COLOR_INACTIVE = QColor(255, 220, 220)    # Light red (OFF state)
    COLOR_DISABLED = QColor(220, 220, 220)    # Light gray (unconfigured)

    # Column indices
    COL_PIN = 0
    COL_NAME = 1
    COL_STATE = 2
    COL_TYPE = 3

    # Digital input types
    TYPE_NAMES = {
        'switch_active_low': 'Switch Low',
        'switch_active_high': 'Switch High',
        'frequency': 'Frequency',
        'rpm': 'RPM',
        'flex_fuel': 'Flex Fuel',
        'beacon': 'Beacon',
        'puls_oil_sensor': 'PULS Oil'
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs_data = []
        self._connected = False
        self._telemetry_data = {}
        self._init_ui()

        # Initialize with default 8 digital inputs
        self._init_default_inputs()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_values)
        self.update_timer.start(100)  # Update every 100ms

    def _init_default_inputs(self):
        """Initialize with default 8 digital inputs (unconfigured)."""
        default_inputs = []
        for i in range(8):
            default_inputs.append({
                'input_pin': i,
                'name': '',
                'subtype': '',
                '_is_default': True
            })
        self.inputs_data = default_inputs
        self._populate_table()

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

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Pin", "Name", "State", "Type"])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_PIN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_STATE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_TYPE, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(self.COL_PIN, 35)
        self.table.setColumnWidth(self.COL_STATE, 50)
        self.table.setColumnWidth(self.COL_TYPE, 80)

        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.table)

    def set_inputs(self, inputs: List[Dict]):
        """Set configured inputs - merges with defaults to keep all 8 inputs visible."""
        # Create a mapping of configured inputs by pin number
        configured_by_pin = {}
        for inp in inputs:
            # Only process digital inputs
            if inp.get('channel_type') != 'digital_input':
                continue
            pin = inp.get('input_pin')
            if pin is not None and inp.get('name'):
                configured_by_pin[pin] = inp

        # Build merged list: configured inputs override defaults
        merged_inputs = []
        for i in range(8):
            if i in configured_by_pin:
                inp = configured_by_pin[i].copy()
                inp['_is_default'] = False
                merged_inputs.append(inp)
            else:
                merged_inputs.append({
                    'input_pin': i,
                    'name': '',
                    'subtype': '',
                    '_is_default': True
                })

        self.inputs_data = merged_inputs
        self._populate_table()

    def _populate_table(self):
        """Populate the table with current inputs data."""
        self.table.setRowCount(len(self.inputs_data))

        for row, inp in enumerate(self.inputs_data):
            is_default = inp.get('_is_default', True)
            pin = inp.get('input_pin', row)

            # Pin
            pin_item = QTableWidgetItem(f"D{pin + 1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_PIN, pin_item)

            # Name
            name = inp.get('name', '')
            name_item = QTableWidgetItem(name)
            self.table.setItem(row, self.COL_NAME, name_item)

            # State (will be updated by telemetry)
            state_item = QTableWidgetItem("-")
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_STATE, state_item)

            # Type
            subtype = inp.get('subtype', '')
            type_display = self.TYPE_NAMES.get(subtype, subtype)
            type_item = QTableWidgetItem(type_display)
            self.table.setItem(row, self.COL_TYPE, type_item)

            # Set row color based on configuration state
            if is_default:
                self._set_row_color(row, self.COLOR_DISABLED)
            else:
                self._set_row_color(row, self.COLOR_NORMAL)

    def _set_row_color(self, row: int, color: QColor):
        """Set background color for a row."""
        brush = QBrush(color)
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(brush)

    def update_from_telemetry(self, adc_values: list, reference_voltage: float = 3.3):
        """Update from telemetry ADC values.

        Args:
            adc_values: List of 20 raw ADC values (0-4095 for 12-bit ADC)
            reference_voltage: ADC reference voltage (default 3.3V)
        """
        self._adc_values = adc_values
        self._reference_voltage = reference_voltage
        self._connected = True
        self.status_label.setText("Online")
        self.status_label.setStyleSheet("color: #0a0;")

    def _update_values(self):
        """Update displayed values from telemetry."""
        if not hasattr(self, '_adc_values') or not self._adc_values:
            return

        for row, inp in enumerate(self.inputs_data):
            is_default = inp.get('_is_default', True)
            pin = inp.get('input_pin', row)

            # Get ADC value and convert to voltage
            if pin < len(self._adc_values):
                raw_value = self._adc_values[pin]
                voltage = (raw_value / 4095.0) * self._reference_voltage
            else:
                voltage = 0
                raw_value = 0

            # Get threshold from config
            threshold = inp.get('threshold_voltage', 2.51)

            # Compute digital state based on threshold
            subtype = inp.get('subtype', 'switch_active_low')
            if subtype == 'switch_active_high':
                state = 1 if voltage > threshold else 0
            else:  # switch_active_low (default)
                state = 0 if voltage > threshold else 1

            # Update state column
            state_item = self.table.item(row, self.COL_STATE)
            if state_item:
                state_item.setText("ON" if state else "OFF")

            # Set row color based on state (only for configured inputs)
            if not is_default:
                if state:
                    self._set_row_color(row, self.COLOR_ACTIVE)
                else:
                    self._set_row_color(row, self.COLOR_NORMAL)

    def set_connected(self, connected: bool):
        """Set connection state."""
        self._connected = connected
        if connected:
            self.status_label.setText("Online")
            self.status_label.setStyleSheet("color: #0a0;")
        else:
            self.status_label.setText("Offline")
            self.status_label.setStyleSheet("color: #888;")
            # Clear values
            for row in range(self.table.rowCount()):
                state_item = self.table.item(row, self.COL_STATE)
                if state_item:
                    state_item.setText("-")

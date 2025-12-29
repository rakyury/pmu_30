"""
Digital Input Monitor Widget
Real-time monitoring of digital input channels

Column layout:
Pin | Name | State | Type
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List


class DigitalMonitor(QWidget):
    """Digital input channels monitor widget with real-time telemetry display."""

    # Signal emitted when user double-clicks a channel to edit it
    channel_edit_requested = pyqtSignal(str, dict)  # (channel_type, channel_config)

    # Colors for different states (dark theme - matching Variables Inspector)
    COLOR_NORMAL = QColor(0, 0, 0)            # Pure black (matching Variables Inspector)
    COLOR_ACTIVE = QColor(50, 80, 50)         # Dark green (ON state)
    COLOR_INACTIVE = QColor(80, 40, 40)       # Dark red (OFF state)
    COLOR_DISABLED = QColor(60, 60, 60)       # Dark gray (unconfigured)

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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        """Initialize with default 20 digital inputs (unconfigured)."""
        default_inputs = []
        for i in range(20):
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
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # Dark theme styling (matching Variables Inspector - pure black)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #000000;
                color: #ffffff;
                gridline-color: #333333;
            }
            QTableWidget::item {
                background-color: #000000;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #333333;
            }
        """)

        layout.addWidget(self.table)

    def set_inputs(self, inputs: List[Dict]):
        """Set configured inputs - merges with defaults to keep all 20 inputs visible."""
        # Create a mapping of configured inputs by pin number
        configured_by_pin = {}
        for inp in inputs:
            # Only process digital inputs
            if inp.get('channel_type') != 'digital_input':
                continue
            # Support both 'input_pin' and 'channel' field names for pin number
            pin = inp.get('input_pin') if inp.get('input_pin') is not None else inp.get('channel')
            # Check both 'name' and 'channel_name' for backwards compatibility
            channel_name = inp.get('name') or inp.get('channel_name')
            if pin is not None and channel_name:
                configured_by_pin[pin] = inp

        # Build merged list: configured inputs override defaults
        merged_inputs = []
        for i in range(20):
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
            # Support both 'input_pin' and 'channel' field names
            pin = inp.get('input_pin') if inp.get('input_pin') is not None else inp.get('channel', row)

            # Pin
            pin_item = QTableWidgetItem(f"D{pin + 1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_PIN, pin_item)

            # Name (check both 'name' and 'channel_name' for backwards compatibility)
            name = inp.get('name') or inp.get('channel_name', '')
            name_item = QTableWidgetItem(name)
            self.table.setItem(row, self.COL_NAME, name_item)

            # State (will be updated by telemetry)
            state_item = QTableWidgetItem("-")
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_STATE, state_item)

            # Type - support both 'subtype' and 'input_type' field names
            subtype = inp.get('subtype') or inp.get('input_type', '')
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
        bg_brush = QBrush(color)
        fg_brush = QBrush(QColor(255, 255, 255))  # White text
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(bg_brush)
                item.setForeground(fg_brush)

    def update_from_telemetry(self, digital_inputs: list):
        """Update from telemetry digital input states.

        Args:
            digital_inputs: List of 20 digital input states (0 or 1)
        """
        self._digital_inputs = digital_inputs
        self._connected = True

    def _update_values(self):
        """Update displayed values from telemetry."""
        if not hasattr(self, '_digital_inputs') or not self._digital_inputs:
            return

        for row, inp in enumerate(self.inputs_data):
            is_default = inp.get('_is_default', True)
            # Support both 'input_pin' and 'channel' field names
            pin = inp.get('input_pin') if inp.get('input_pin') is not None else inp.get('channel', row)

            # Get physical state from telemetry
            if pin < len(self._digital_inputs):
                physical_state = self._digital_inputs[pin]
            else:
                physical_state = 0

            # Apply subtype logic to get logical state
            # - switch_active_high: HIGH=ON, LOW=OFF (no inversion)
            # - switch_active_low: HIGH=OFF, LOW=ON (inverted)
            subtype = inp.get('subtype') or inp.get('input_type', '')
            if subtype == 'switch_active_low':
                logical_state = not physical_state
            else:
                logical_state = physical_state

            # Update state column
            state_item = self.table.item(row, self.COL_STATE)
            if state_item:
                state_item.setText("ON" if logical_state else "OFF")

            # Set row color based on logical state (only for configured inputs)
            if not is_default:
                if logical_state:
                    self._set_row_color(row, self.COLOR_ACTIVE)
                else:
                    self._set_row_color(row, self.COLOR_NORMAL)

    def set_connected(self, connected: bool):
        """Set connection state."""
        self._connected = connected
        if not connected:
            # Clear values
            for row in range(self.table.rowCount()):
                state_item = self.table.item(row, self.COL_STATE)
                if state_item:
                    state_item.setText("-")

    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle double-click on table cell - emit signal to edit the channel."""
        if row < 0 or row >= len(self.inputs_data):
            return
        input_data = self.inputs_data[row]
        # Only emit for configured inputs (not default/unconfigured)
        if not input_data.get('_is_default', True):
            self.channel_edit_requested.emit('digital_input', input_data)

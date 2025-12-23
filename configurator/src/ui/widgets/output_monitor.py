"""
Output Monitor Widget
Real-time monitoring of output channels with ECUMaster-compatible columns

ECUMaster column layout:
Pin | Name | Status | V | Load | Curr | Peak | Vltg | Trip

ECUMaster channel naming convention:
- pmuX.oY.status  - Output status
- pmuX.oY.current - Output current (mA)
- pmuX.oY.voltage - Output voltage (V)
- pmuX.oY.active  - Output active flag
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List


class OutputMonitor(QWidget):
    """Output channels monitor widget with real-time telemetry display."""

    # Colors for different states
    COLOR_NORMAL = QColor(255, 255, 255)      # White
    COLOR_ACTIVE = QColor(200, 255, 200)      # Light green
    COLOR_FAULT = QColor(255, 200, 200)       # Light red
    COLOR_PWM = QColor(200, 230, 255)         # Light blue
    COLOR_DISABLED = QColor(220, 220, 220)    # Light gray

    # Column indices - matching ECUMaster layout
    COL_PIN = 0
    COL_NAME = 1
    COL_STATUS = 2
    COL_V = 3        # Battery voltage
    COL_LOAD = 4     # Load/Duty %
    COL_CURR = 5     # Current (mA)
    COL_PEAK = 6     # Peak current
    COL_VLTG = 7     # Output voltage
    COL_TRIP = 8     # Trip/Fault indicator

    def __init__(self, parent=None):
        super().__init__(parent)
        self.outputs_data = []
        self._connected = False
        self._peak_currents = {}  # Track peak currents per channel
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

        # Reset peaks button
        self.reset_peaks_btn = QPushButton("Reset Peaks")
        self.reset_peaks_btn.setMaximumWidth(80)
        self.reset_peaks_btn.clicked.connect(self._reset_peaks)
        toolbar.addWidget(self.reset_peaks_btn)

        # Info button
        self.info_btn = QPushButton("?")
        self.info_btn.setMaximumWidth(25)
        toolbar.addWidget(self.info_btn)

        layout.addLayout(toolbar)

        # Table with ECUMaster-compatible columns
        # Pin | Name | Status | V | Load | Curr | Peak | Vltg | Trip
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Pin", "Name", "Status", "V", "Load", "Curr", "Peak", "Vltg", "Trip"
        ])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_PIN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_V, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_LOAD, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_CURR, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_PEAK, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_VLTG, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_TRIP, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(self.COL_PIN, 30)      # Pin
        self.table.setColumnWidth(self.COL_STATUS, 45)   # Status
        self.table.setColumnWidth(self.COL_V, 35)        # V (battery)
        self.table.setColumnWidth(self.COL_LOAD, 40)     # Load
        self.table.setColumnWidth(self.COL_CURR, 50)     # Curr
        self.table.setColumnWidth(self.COL_PEAK, 50)     # Peak
        self.table.setColumnWidth(self.COL_VLTG, 40)     # Vltg
        self.table.setColumnWidth(self.COL_TRIP, 35)     # Trip

        self.table.setAlternatingRowColors(False)  # We'll use custom row colors
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

    def set_outputs(self, outputs: List[Dict]):
        """Set outputs list."""
        self.outputs_data = outputs
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
            for col in [self.COL_STATUS, self.COL_V, self.COL_LOAD, self.COL_CURR,
                       self.COL_PEAK, self.COL_VLTG, self.COL_TRIP]:
                item = self.table.item(row, col)
                if item:
                    item.setText("?")
                    item.setBackground(QBrush(self.COLOR_DISABLED))

    def _reset_peaks(self):
        """Reset peak current values."""
        self._peak_currents.clear()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.COL_PEAK)
            if item:
                item.setText("0")

    def _populate_table(self):
        """Populate table with outputs."""
        self.table.setRowCount(len(self.outputs_data))

        for row, output in enumerate(self.outputs_data):
            channel = output.get('channel', 0)

            # Pin (O1, O2, etc.)
            pin_item = QTableWidgetItem(f"O{channel + 1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_PIN, pin_item)

            # Name
            name = output.get('name', '')
            if name:
                name_item = QTableWidgetItem(f"o_{name}")
            else:
                name_item = QTableWidgetItem("")
            self.table.setItem(row, self.COL_NAME, name_item)

            # Status
            status_item = QTableWidgetItem("?")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_STATUS, status_item)

            # V (battery voltage - same for all)
            v_item = QTableWidgetItem("?")
            v_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_V, v_item)

            # Load (duty %)
            load_item = QTableWidgetItem("?")
            load_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_LOAD, load_item)

            # Curr (current mA)
            curr_item = QTableWidgetItem("?")
            curr_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_CURR, curr_item)

            # Peak (peak current)
            peak_item = QTableWidgetItem("?")
            peak_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_PEAK, peak_item)

            # Vltg (output voltage)
            vltg_item = QTableWidgetItem("?")
            vltg_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_VLTG, vltg_item)

            # Trip (fault indicator)
            trip_item = QTableWidgetItem("?")
            trip_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_TRIP, trip_item)

            # Set initial row color
            self._set_row_color(row, self.COLOR_DISABLED)

            # Dim disabled outputs
            if not output.get('enabled', False):
                for col in range(9):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(Qt.GlobalColor.gray)

    def _set_row_color(self, row: int, color: QColor):
        """Set background color for entire row."""
        for col in range(9):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(color))

    def _update_values(self):
        """Update real-time values (when connected to device)."""
        # Values are updated via update_from_telemetry() called from main window
        pass

    def update_output_status(self, channel: int, status: str, voltage: float, load: float):
        """Update specific output status (legacy method for backwards compatibility)."""
        # Find the row for this channel
        for row in range(self.table.rowCount()):
            pin_item = self.table.item(row, self.COL_PIN)
            if pin_item and pin_item.text() == f"O{channel + 1}":
                # Update status
                self.table.item(row, self.COL_STATUS).setText(status)

                # Update voltage
                if voltage > 0:
                    self.table.item(row, self.COL_VLTG).setText(f"{voltage:.1f}")

                # Update load (duty)
                self.table.item(row, self.COL_LOAD).setText(f"{load:.0f}%")

                # Set row color based on status
                if status in ["OC", "OT", "SC", "OL"]:
                    self._set_row_color(row, self.COLOR_FAULT)
                elif status == "PWM":
                    self._set_row_color(row, self.COLOR_PWM)
                elif status == "ON":
                    self._set_row_color(row, self.COLOR_ACTIVE)
                else:
                    self._set_row_color(row, self.COLOR_NORMAL)
                break

    def update_from_telemetry(self, profet_states: List[int], profet_duties: List[int],
                               profet_currents: List[int], battery_voltage: float = 0.0):
        """
        Update all outputs from telemetry data.

        Args:
            profet_states: List of channel states (0=OFF, 1=ON, 2=OC, 3=OT, 4=SC, 5=OL, 6=PWM, 7=DIS)
            profet_duties: List of duty cycles (0-1000 = 0-100.0%)
            profet_currents: List of channel currents in mA
            battery_voltage: System battery voltage for output voltage estimation
        """
        state_names = ["OFF", "ON", "OC", "OT", "SC", "OL", "PWM", "DIS"]
        fault_states = [2, 3, 4, 5]  # OC, OT, SC, OL

        for row in range(min(self.table.rowCount(), len(self.outputs_data))):
            output_config = self.outputs_data[row]

            # Get list of physical pins for this output
            pins = output_config.get('pins', [output_config.get('channel', row)])
            if not pins:
                pins = [row]

            # Use first pin as primary channel index for telemetry
            channel_idx = pins[0] if pins else row

            if channel_idx >= len(profet_states):
                continue

            # Aggregate state/duty/current from all pins in this output
            state = profet_states[channel_idx]
            duty = profet_duties[channel_idx] if channel_idx < len(profet_duties) else 0

            # Sum current from all pins in this output channel
            current_ma = 0
            for pin in pins:
                if pin < len(profet_currents):
                    current_ma += profet_currents[pin]

            # Check if output is disabled in config
            is_enabled = output_config.get('enabled', True)

            # Override status if disabled in config
            if not is_enabled:
                status_str = "DIS"
                state = 7  # Treat as disabled for color
            else:
                status_str = state_names[state] if state < len(state_names) else "?"

            status_item = self.table.item(row, self.COL_STATUS)
            if status_item:
                status_item.setText(status_str)

            # V (battery voltage - same for all outputs)
            v_item = self.table.item(row, self.COL_V)
            if v_item:
                v_item.setText(f"{battery_voltage:.1f}")

            # Load (duty cycle 0-1000 -> 0-100.0%)
            load_item = self.table.item(row, self.COL_LOAD)
            if load_item:
                if is_enabled:
                    duty_percent = duty / 10.0
                    load_item.setText(f"{duty_percent:.0f}%")
                else:
                    load_item.setText("-")

            # Current in mA (show 0 or - for disabled)
            curr_item = self.table.item(row, self.COL_CURR)
            if curr_item:
                if is_enabled:
                    if current_ma >= 1000:
                        curr_item.setText(f"{current_ma/1000:.2f}A")
                    else:
                        curr_item.setText(f"{current_ma}")
                else:
                    curr_item.setText("-")

            # Peak current tracking (only when enabled)
            if is_enabled:
                if row not in self._peak_currents:
                    self._peak_currents[row] = 0
                if current_ma > self._peak_currents[row]:
                    self._peak_currents[row] = current_ma

            peak_item = self.table.item(row, self.COL_PEAK)
            if peak_item:
                if is_enabled:
                    peak = self._peak_currents.get(row, 0)
                    if peak >= 1000:
                        peak_item.setText(f"{peak/1000:.2f}A")
                    else:
                        peak_item.setText(f"{peak}")
                else:
                    peak_item.setText("-")

            # Output voltage estimation
            vltg_item = self.table.item(row, self.COL_VLTG)
            if vltg_item:
                if not is_enabled:
                    vltg_item.setText("-")
                elif state == 1:  # ON
                    vltg_item.setText(f"{battery_voltage:.1f}")
                elif state == 6:  # PWM
                    output_voltage = battery_voltage * (duty / 1000.0)
                    vltg_item.setText(f"{output_voltage:.1f}")
                else:
                    vltg_item.setText("0.0")

            # Trip indicator (fault flag)
            trip_item = self.table.item(row, self.COL_TRIP)
            if trip_item:
                if state in fault_states:
                    trip_item.setText("!")
                else:
                    trip_item.setText("")

            # Set row color based on state
            if not is_enabled:
                self._set_row_color(row, self.COLOR_DISABLED)
            elif state in fault_states:
                self._set_row_color(row, self.COLOR_FAULT)
            elif state == 6:  # PWM
                self._set_row_color(row, self.COLOR_PWM)
            elif state == 1:  # ON
                self._set_row_color(row, self.COLOR_ACTIVE)
            else:  # OFF
                self._set_row_color(row, self.COLOR_NORMAL)

    def get_channel_count(self) -> int:
        """Get number of configured outputs."""
        return len(self.outputs_data)

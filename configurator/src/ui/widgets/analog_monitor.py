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

        # Initialize with default 20 analog inputs
        self._init_default_inputs()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_values)
        self.update_timer.start(100)  # Update every 100ms

    def _init_default_inputs(self):
        """Initialize with default 20 analog inputs (unconfigured - no names)."""
        default_inputs = []
        for i in range(20):
            default_inputs.append({
                'channel': i,
                'name': '',  # Empty name for unconfigured pins
                'enabled': True,
                'pull_mode': 'none',
                '_is_default': True  # Flag to indicate this is a default/unconfigured input
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
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_VALUE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_VLTG, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_PUPD, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnWidth(self.COL_PIN, 30)     # Pin
        self.table.setColumnWidth(self.COL_NAME, 80)    # Name (smaller)
        self.table.setColumnWidth(self.COL_VALUE, 50)   # Value
        self.table.setColumnWidth(self.COL_VLTG, 45)    # Vltg
        self.table.setColumnWidth(self.COL_PUPD, 45)    # Pu/pd

        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Read-only
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  # Select full rows

        layout.addWidget(self.table)

    def set_inputs(self, inputs: List[Dict]):
        """
        Set configured inputs - merges with defaults to keep all 20 inputs visible.
        Configured inputs get their names and settings, unconfigured remain gray.
        Only inputs with a valid name/id are considered "configured".
        """
        # Create a mapping of configured inputs by pin number
        # Only include inputs that have a name (id)
        configured_by_pin = {}
        for inp in inputs:
            # Only consider inputs with a name as "configured"
            name = inp.get('id', inp.get('name', ''))
            if not name:
                continue
            pin = inp.get('input_pin', inp.get('channel', -1))
            if pin >= 0:
                configured_by_pin[pin] = inp

        # Reset to defaults first
        self._init_default_inputs()

        # Update configured inputs with their names and settings
        for i, input_data in enumerate(self.inputs_data):
            channel = input_data.get('channel', i)
            if channel in configured_by_pin:
                cfg = configured_by_pin[channel]
                input_data['name'] = cfg.get('id', cfg.get('name', ''))
                input_data['pull_mode'] = cfg.get('pull_mode', 'none')
                input_data['enabled'] = cfg.get('enabled', True)
                input_data['_is_default'] = False
                # Store subtype and thresholds for switch logic
                input_data['subtype'] = cfg.get('subtype', 'linear')
                input_data['threshold_high'] = cfg.get('threshold_high', 2.5)
                input_data['threshold_low'] = cfg.get('threshold_low', 1.5)
                # Store linear mapping values
                input_data['min_voltage'] = cfg.get('min_voltage', 0.0)
                input_data['max_voltage'] = cfg.get('max_voltage', 5.0)
                input_data['min_value'] = cfg.get('min_value', 0.0)
                input_data['max_value'] = cfg.get('max_value', 100.0)
                input_data['decimal_places'] = cfg.get('decimal_places', 0)
                # Store calibration points for calibrated type
                input_data['calibration_points'] = cfg.get('calibration_points', [])
            else:
                input_data['_is_default'] = True

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
            channel = input_data.get('channel', row)
            is_default = input_data.get('_is_default', True)

            # Pin (A1, A2, etc.)
            pin_item = QTableWidgetItem(f"A{channel + 1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_PIN, pin_item)

            # Name - only show for configured inputs
            name = input_data.get('name', '')
            name_item = QTableWidgetItem(name if name else "")
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

            # Set initial row color - gray for unconfigured/default inputs
            if is_default:
                self._set_row_color(row, self.COLOR_DISABLED)
                # Gray text for unconfigured
                for col in range(5):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(Qt.GlobalColor.gray)
            else:
                self._set_row_color(row, self.COLOR_NORMAL)

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
                # Check if this row is configured
                input_data = self.inputs_data[row] if row < len(self.inputs_data) else {}
                name = input_data.get('name', '')
                is_default = input_data.get('_is_default', True) or not name

                # Only update values for configured inputs
                # Unconfigured inputs stay gray with "?" values
                if is_default:
                    # Keep gray color and "?" values for unconfigured inputs
                    self._set_row_color(row, self.COLOR_DISABLED)
                else:
                    # Update values only for configured inputs
                    self.table.item(row, self.COL_VALUE).setText(f"{value:.1f}")
                    self.table.item(row, self.COL_VLTG).setText(f"{voltage:.2f}")

                    # Set row color based on signal state
                    if voltage > 0.1:
                        self._set_row_color(row, self.COLOR_ACTIVE)
                    else:
                        self._set_row_color(row, self.COLOR_NORMAL)
                break

    def update_from_telemetry(self, adc_values: List[int], reference_voltage: float = 3.3):
        """
        Update all analog inputs from telemetry data.

        Args:
            adc_values: List of raw ADC values (0-4095 for 12-bit)
            reference_voltage: ADC reference voltage (default 3.3V)
        """
        for row in range(min(self.table.rowCount(), len(self.inputs_data))):
            if row >= len(adc_values):
                break

            input_data = self.inputs_data[row]
            # Consider unconfigured if _is_default flag is True OR if name is empty
            name = input_data.get('name', '')
            is_default = input_data.get('_is_default', True) or not name

            # Unconfigured inputs stay gray with "?" values - don't update
            if is_default:
                self._set_row_color(row, self.COLOR_DISABLED)
                continue

            adc_raw = adc_values[row]

            # Convert raw ADC to voltage (12-bit ADC, reference voltage)
            voltage = (adc_raw / 4095.0) * reference_voltage

            # Get subtype and thresholds
            subtype = input_data.get('subtype', 'linear')
            threshold_high = input_data.get('threshold_high', 2.5)
            threshold_low = input_data.get('threshold_low', 1.5)

            # Calculate value based on input type
            if subtype in ('switch_active_low', 'switch_active_high'):
                # For switch inputs, calculate digital state (0 or 1)
                # Based on dialog: "1 if voltage >: threshold_high", "0 if voltage <: threshold_low"
                # Get previous state for hysteresis
                prev_state = input_data.get('_digital_state', 0)

                # Same logic for both switch types (based on voltage thresholds from dialog)
                if voltage > threshold_high:
                    digital_state = 1  # "1 if voltage > threshold_high"
                elif voltage < threshold_low:
                    digital_state = 0  # "0 if voltage < threshold_low"
                else:
                    digital_state = prev_state  # Hysteresis zone

                # Store state for next update
                input_data['_digital_state'] = digital_state
                display_value = str(digital_state)
            elif subtype == 'linear':
                # For linear inputs, apply voltage-to-value mapping
                min_voltage = input_data.get('min_voltage', 0.0)
                max_voltage = input_data.get('max_voltage', 5.0)
                min_value = input_data.get('min_value', 0.0)
                max_value = input_data.get('max_value', 100.0)
                decimal_places = input_data.get('decimal_places', 0)

                # Linear interpolation
                if max_voltage != min_voltage:
                    scaled_value = min_value + (voltage - min_voltage) * (max_value - min_value) / (max_voltage - min_voltage)
                else:
                    scaled_value = min_value

                # Format with correct decimal places
                display_value = f"{scaled_value:.{decimal_places}f}"
                digital_state = 1 if voltage > 0.1 else 0
            elif subtype == 'calibrated':
                # For calibrated inputs, use interpolation from calibration table
                calibration_points = input_data.get('calibration_points', [])
                decimal_places = input_data.get('decimal_places', 0)

                if len(calibration_points) >= 2:
                    # Sort by voltage
                    sorted_points = sorted(calibration_points, key=lambda p: p.get('voltage', 0))

                    # Find interpolation range
                    scaled_value = 0.0
                    for i in range(len(sorted_points) - 1):
                        v1 = sorted_points[i].get('voltage', 0)
                        v2 = sorted_points[i + 1].get('voltage', 0)
                        val1 = sorted_points[i].get('value', 0)
                        val2 = sorted_points[i + 1].get('value', 0)

                        if v1 <= voltage <= v2:
                            # Interpolate
                            if v2 != v1:
                                scaled_value = val1 + (voltage - v1) * (val2 - val1) / (v2 - v1)
                            else:
                                scaled_value = val1
                            break
                    else:
                        # Outside range - extrapolate from nearest points
                        if voltage < sorted_points[0].get('voltage', 0):
                            scaled_value = sorted_points[0].get('value', 0)
                        else:
                            scaled_value = sorted_points[-1].get('value', 0)

                    display_value = f"{scaled_value:.{decimal_places}f}"
                else:
                    # Not enough calibration points - show percentage
                    value_percent = (adc_raw / 4095.0) * 100
                    display_value = f"{value_percent:.1f}"

                digital_state = 1 if voltage > 0.1 else 0
            else:
                # For rotary switch or unknown types, show percentage (0-100%)
                value_percent = (adc_raw / 4095.0) * 100
                display_value = f"{value_percent:.1f}"
                digital_state = 1 if voltage > 0.1 else 0

            # Update Value column (only for configured inputs)
            value_item = self.table.item(row, self.COL_VALUE)
            if value_item:
                value_item.setText(display_value)

            # Update Voltage column (only for configured inputs)
            vltg_item = self.table.item(row, self.COL_VLTG)
            if vltg_item:
                vltg_item.setText(f"{voltage:.2f}")

            # Set row color based on state
            if subtype in ('switch_active_low', 'switch_active_high'):
                # For switches: green if ON (1), normal if OFF (0)
                if digital_state == 1:
                    self._set_row_color(row, self.COLOR_ACTIVE)
                else:
                    self._set_row_color(row, self.COLOR_NORMAL)
            else:
                # For analog: color based on voltage level
                if voltage > 0.1:
                    self._set_row_color(row, self.COLOR_ACTIVE)
                else:
                    self._set_row_color(row, self.COLOR_NORMAL)

    def get_channel_count(self) -> int:
        """Get number of configured analog inputs."""
        return len(self.inputs_data)

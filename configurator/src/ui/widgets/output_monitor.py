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
    QHeaderView, QPushButton, QHBoxLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List


class OutputMonitor(QWidget):
    """Output channels monitor widget with real-time telemetry display."""

    # Signal emitted when user double-clicks a channel to edit it
    channel_edit_requested = pyqtSignal(str, dict)  # (channel_type, channel_config)

    # Colors for different states (dark theme - matching Variables Inspector)
    COLOR_NORMAL = QColor(0, 0, 0)            # Pure black (matching Variables Inspector)
    COLOR_ACTIVE = QColor(50, 80, 50)         # Dark green
    COLOR_FAULT = QColor(80, 40, 40)          # Dark red
    COLOR_PWM = QColor(0, 50, 80)             # Dark blue
    COLOR_DISABLED = QColor(60, 60, 60)       # Dark gray

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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.outputs_data = []
        self._connected = False
        self._peak_currents = {}  # Track peak currents per channel
        self._row_to_index = {}   # Mapping from table row to outputs_data index
        self._init_ui()

        # Initialize with default 30 outputs
        self._init_default_outputs()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_values)
        self.update_timer.start(100)  # Update every 100ms

    def _init_default_outputs(self):
        """Initialize with default 30 PROFET outputs (unconfigured - no names)."""
        default_outputs = []
        for i in range(30):
            default_outputs.append({
                'channel': i,
                'name': '',  # Empty name for unconfigured pins
                'enabled': True,
                'pins': [i],
                '_is_default': True  # Flag to indicate this is a default/unconfigured output
            })
        self.outputs_data = default_outputs
        self._populate_table()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Toolbar
        toolbar = QHBoxLayout()

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
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_V, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_LOAD, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_CURR, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_PEAK, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_VLTG, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_TRIP, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnWidth(self.COL_PIN, 80)      # Pin (can show O1, O2, O3)
        self.table.setColumnWidth(self.COL_NAME, 100)    # Name
        self.table.setColumnWidth(self.COL_STATUS, 50)   # Status
        self.table.setColumnWidth(self.COL_V, 40)        # V (battery)
        self.table.setColumnWidth(self.COL_LOAD, 45)     # Load
        self.table.setColumnWidth(self.COL_CURR, 55)     # Curr
        self.table.setColumnWidth(self.COL_PEAK, 55)     # Peak
        self.table.setColumnWidth(self.COL_VLTG, 45)     # Vltg
        self.table.setColumnWidth(self.COL_TRIP, 25)     # Trip (smaller)

        self.table.setAlternatingRowColors(False)  # We'll use custom row colors
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Read-only
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  # Select full rows

        # Double-click to edit channel
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

    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle double-click on a cell to open edit dialog."""
        # Get the output data for this row
        if row not in self._row_to_index:
            return

        idx = self._row_to_index[row]
        if idx < 0 or idx >= len(self.outputs_data):
            return

        output_data = self.outputs_data[idx]

        # Emit signal to open edit dialog
        # channel_type is 'power_output' for PROFET outputs
        self.channel_edit_requested.emit('power_output', output_data)

    def set_outputs(self, outputs: List[Dict]):
        """
        Set configured outputs - merges with defaults to keep all 30 outputs visible.
        Configured outputs get their names and settings, unconfigured remain gray.
        Secondary pins (used by multi-pin outputs) are hidden.
        Only outputs with a valid name/id are considered "configured".
        """
        # Reset to defaults first
        self._init_default_outputs()

        # Track which pins are secondary (used but not as primary)
        secondary_pins = set()

        # Create mapping of configured outputs by primary pin
        # Only include outputs that have a name
        configured_by_pin = {}
        for out in outputs:
            # Only consider outputs with a name as "configured"
            # Priority: name > channel_name > id (for backwards compatibility)
            name = out.get('name') or out.get('channel_name') or out.get('id', '')
            if not name:
                continue
            # Support multiple field names: output_pins, pins, channel
            pins = out.get('output_pins') or out.get('pins') or [out.get('channel', -1)]
            if pins:
                primary_pin = pins[0]
                if primary_pin >= 0:
                    configured_by_pin[primary_pin] = out
                    # Mark all non-primary pins as secondary (to hide)
                    for pin in pins[1:]:
                        if pin >= 0:
                            secondary_pins.add(pin)

        # Update configured outputs with their names and settings
        for i, output_data in enumerate(self.outputs_data):
            channel = output_data.get('channel', i)
            if channel in secondary_pins:
                # This pin is used as secondary by another output - hide it
                output_data['_is_hidden'] = True
                output_data['_is_default'] = True
            elif channel in configured_by_pin:
                cfg = configured_by_pin[channel]
                # Priority: name > channel_name > id (for backwards compatibility)
                output_data['name'] = cfg.get('name') or cfg.get('channel_name') or cfg.get('id', '')
                # Support multiple field names: output_pins, pins, channel
                output_data['pins'] = cfg.get('output_pins') or cfg.get('pins') or [channel]
                output_data['enabled'] = cfg.get('enabled', True)
                output_data['_is_default'] = False
                output_data['_is_hidden'] = False
            else:
                output_data['_is_default'] = True
                output_data['_is_hidden'] = False

        self._populate_table()

    def set_connected(self, connected: bool):
        """Set connection state."""
        self._connected = connected
        if connected:
            pass  # Connection status shown in status bar
        else:
            pass  # Connection status shown in status bar
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
        """Populate table with outputs (hidden secondary pins are skipped)."""
        # Filter out hidden outputs
        visible_outputs = [(i, out) for i, out in enumerate(self.outputs_data)
                          if not out.get('_is_hidden', False)]

        self.table.setRowCount(len(visible_outputs))

        # Store mapping from table row to original index
        self._row_to_index = {}

        for row, (orig_idx, output) in enumerate(visible_outputs):
            self._row_to_index[row] = orig_idx
            is_default = output.get('_is_default', True)

            # Get pins - can be single pin or multiple pins
            pins = output.get('pins', [])
            if not pins:
                # Fallback to legacy 'channel' field
                channel = output.get('channel', orig_idx)
                pins = [channel]

            # Pin (O1, O2, etc. or O1, O2, O3 for multiple)
            pin_str = ", ".join([f"O{p + 1}" for p in pins])
            pin_item = QTableWidgetItem(pin_str)
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_PIN, pin_item)

            # Name - only show if configured (not default)
            name = output.get('name', '')
            name_item = QTableWidgetItem(name if name else "")
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
            trip_item = QTableWidgetItem("")
            trip_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_TRIP, trip_item)

            # Set initial styling based on configured/default
            if is_default:
                self._set_row_color(row, self.COLOR_DISABLED)
                # Gray text for unconfigured outputs
                for col in range(9):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(Qt.GlobalColor.gray)
            else:
                self._set_row_color(row, self.COLOR_NORMAL)

    def _set_row_color(self, row: int, color: QColor):
        """Set background color for entire row."""
        bg_brush = QBrush(color)
        fg_brush = QBrush(QColor(255, 255, 255))  # White text
        for col in range(9):
            item = self.table.item(row, col)
            if item:
                item.setBackground(bg_brush)
                item.setForeground(fg_brush)

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
                    self.table.item(row, self.COL_VLTG).setText(f"{voltage:.2f}")

                # Update load (duty)
                self.table.item(row, self.COL_LOAD).setText(f"{load:.2f}%")

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
            profet_states: List of channel states (0=OFF, 1=ON, 2=OC, 3=OT, 4=SC, 5=OL, 6=PWM)
            profet_duties: List of duty cycles (0-1000 = 0-100.0%)
            profet_currents: List of channel currents in mA
            battery_voltage: System battery voltage for output voltage estimation
        """
        state_names = ["OFF", "ON", "OC", "OT", "SC", "OL", "PWM"]
        fault_states = [2, 3, 4, 5]  # OC, OT, SC, OL

        for row in range(self.table.rowCount()):
            # Get original output index from row mapping
            orig_idx = self._row_to_index.get(row, row)
            if orig_idx >= len(self.outputs_data):
                continue

            output_config = self.outputs_data[orig_idx]
            # Consider unconfigured if _is_default flag is True OR if name is empty
            name = output_config.get('name', '')
            is_default = output_config.get('_is_default', True) or not name

            # Get list of physical pins for this output
            # Support multiple field names: output_pins, pins, channel
            pins = output_config.get('output_pins') or output_config.get('pins') or [output_config.get('channel', orig_idx)]
            if not pins:
                pins = [orig_idx]

            # Use first pin as primary channel index for telemetry
            channel_idx = pins[0] if pins else orig_idx

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

            # Show status based on configuration
            if is_default:
                status_str = "-"  # Show dash for unconfigured
            else:
                # Show actual state from telemetry
                # No more DIS status - outputs are controlled only by Control Function
                status_str = state_names[state] if state < len(state_names) else "?"

            status_item = self.table.item(row, self.COL_STATUS)
            if status_item:
                status_item.setText(status_str)

            # V (battery voltage - same for all outputs)
            v_item = self.table.item(row, self.COL_V)
            if v_item:
                if is_default:
                    v_item.setText("-")
                else:
                    v_item.setText(f"{battery_voltage:.2f}")

            # Load (duty cycle 0-1000 -> 0-100.0%)
            load_item = self.table.item(row, self.COL_LOAD)
            if load_item:
                if is_default:
                    load_item.setText("-")
                else:
                    duty_percent = duty / 10.0
                    load_item.setText(f"{duty_percent:.2f}%")

            # Current in mA (show - for unconfigured)
            curr_item = self.table.item(row, self.COL_CURR)
            if curr_item:
                if is_default:
                    curr_item.setText("-")
                elif current_ma >= 1000:
                    curr_item.setText(f"{current_ma/1000:.2f}A")
                else:
                    curr_item.setText(f"{current_ma}")

            # Peak current tracking (only when configured)
            if not is_default:
                if row not in self._peak_currents:
                    self._peak_currents[row] = 0
                if current_ma > self._peak_currents[row]:
                    self._peak_currents[row] = current_ma

            peak_item = self.table.item(row, self.COL_PEAK)
            if peak_item:
                if is_default:
                    peak_item.setText("-")
                else:
                    peak = self._peak_currents.get(row, 0)
                    if peak >= 1000:
                        peak_item.setText(f"{peak/1000:.2f}A")
                    else:
                        peak_item.setText(f"{peak}")

            # Output voltage estimation
            vltg_item = self.table.item(row, self.COL_VLTG)
            if vltg_item:
                if is_default:
                    vltg_item.setText("-")
                elif state == 1:  # ON
                    vltg_item.setText(f"{battery_voltage:.2f}")
                elif state == 6:  # PWM
                    output_voltage = battery_voltage * (duty / 1000.0)
                    vltg_item.setText(f"{output_voltage:.2f}")
                else:
                    vltg_item.setText("0.00")

            # Trip indicator (fault flag) - show error icon for faults
            trip_item = self.table.item(row, self.COL_TRIP)
            if trip_item:
                if not is_default and state in fault_states:
                    trip_item.setText("\u26a0")  # Warning sign ⚠
                else:
                    trip_item.setText("")

            # Check if PWM is configured for this output
            is_pwm_configured = output_config.get("pwm_enabled", False)
            if not is_pwm_configured:
                pwm_cfg = output_config.get("pwm", {})
                is_pwm_configured = pwm_cfg.get("enabled", False)

            # Determine if output is in PWM mode:
            # - state == 6 (firmware reports PWM)
            # - OR duty is between 1-999 (partial PWM)
            # - OR PWM is configured and output is active with non-100% duty
            is_pwm_active = (state == 6 or
                            (duty > 0 and duty < 1000) or
                            (is_pwm_configured and state == 1 and duty < 1000))

            # Set row color based on state:
            # - Unconfigured (default) outputs stay gray
            # - Configured outputs: colored based on state
            if is_default:
                self._set_row_color(row, self.COLOR_DISABLED)
            elif state in fault_states:
                self._set_row_color(row, self.COLOR_FAULT)
            elif is_pwm_active:  # PWM mode (state=6 or partial duty)
                self._set_row_color(row, self.COLOR_PWM)
            elif state == 1:  # ON (100% duty)
                self._set_row_color(row, self.COLOR_ACTIVE)
            else:  # OFF
                self._set_row_color(row, self.COLOR_NORMAL)

    def get_channel_count(self) -> int:
        """Get number of configured outputs."""
        return len(self.outputs_data)

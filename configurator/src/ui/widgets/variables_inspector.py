"""
Variables Inspector Widget
Real-time monitoring of all system channels with ECUMaster-compatible layout

ECUMaster column layout:
Name | Value | Unit

Channel naming conventions:
- c_xxx - CAN RX channels
- k_xxx - Keypad channels
- kb_X.active - Keypad button active state
- o_xxx - Output channels
- a_xxx - Analog input channels
- t_xxx - Timer channels
- v_xxx - Virtual channels
- pmu1.xxx - PMU system channels
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout, QLabel, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List, Any, Optional


class VariablesInspector(QWidget):
    """Variables inspector widget with real-time telemetry display."""

    # Colors for different states (ECUMaster style)
    COLOR_NORMAL = QColor(255, 255, 255)       # White - normal
    COLOR_ACTIVE = QColor(255, 200, 150)       # Orange - active/triggered
    COLOR_ERROR = QColor(255, 150, 150)        # Red - error/fault
    COLOR_DISABLED = QColor(220, 220, 220)     # Light gray - disabled
    COLOR_CHANGED = QColor(200, 255, 200)      # Light green - recently changed

    # Column indices
    COL_NAME = 0
    COL_VALUE = 1
    COL_UNIT = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._channels: Dict[str, Dict[str, Any]] = {}  # name -> {value, unit, type, active}
        self._previous_values: Dict[str, Any] = {}  # For change detection
        self._init_ui()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
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

        # Filter field
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter...")
        self.filter_edit.setMaximumWidth(150)
        self.filter_edit.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_edit)

        # Info button
        self.info_btn = QPushButton("?")
        self.info_btn.setMaximumWidth(25)
        toolbar.addWidget(self.info_btn)

        layout.addLayout(toolbar)

        # Table with ECUMaster-compatible columns
        # Name | Value | Unit
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "Value", "Unit"])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_VALUE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_UNIT, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(self.COL_VALUE, 80)
        self.table.setColumnWidth(self.COL_UNIT, 60)

        self.table.setAlternatingRowColors(False)  # We use custom row colors
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.table)

        # Status bar
        self.count_label = QLabel("0 channels")
        layout.addWidget(self.count_label)

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
            value_item = self.table.item(row, self.COL_VALUE)
            if value_item:
                value_item.setText("?")
            self._set_row_color(row, self.COLOR_DISABLED)

    def set_channels(self, channels: List[Dict[str, Any]]):
        """
        Set the list of channels to display.

        Args:
            channels: List of channel dicts with keys:
                - id: Channel identifier
                - name: Display name (optional, uses id if not provided)
                - unit: Unit string (optional)
                - channel_type: Type of channel (can_rx, output, analog, etc.)
        """
        self._channels.clear()

        for ch in channels:
            ch_id = ch.get('id', '')
            if not ch_id:
                continue

            self._channels[ch_id] = {
                'name': ch.get('name', ch_id),
                'unit': ch.get('unit', ''),
                'type': ch.get('channel_type', 'unknown'),
                'value': '?',
                'active': False,
                'error': False,
            }

        self._populate_table()

    def add_channel(self, channel_id: str, name: str = "", unit: str = "",
                    channel_type: str = "unknown"):
        """Add a single channel to the inspector."""
        self._channels[channel_id] = {
            'name': name or channel_id,
            'unit': unit,
            'type': channel_type,
            'value': '?',
            'active': False,
            'error': False,
        }
        self._populate_table()

    def remove_channel(self, channel_id: str):
        """Remove a channel from the inspector."""
        if channel_id in self._channels:
            del self._channels[channel_id]
            self._populate_table()

    def clear_channels(self):
        """Clear all channels."""
        self._channels.clear()
        self._populate_table()

    def _populate_table(self):
        """Populate table with channels."""
        # Sort channels by name
        sorted_ids = sorted(self._channels.keys())

        self.table.setRowCount(len(sorted_ids))

        for row, ch_id in enumerate(sorted_ids):
            ch = self._channels[ch_id]

            # Name
            name_item = QTableWidgetItem(ch['name'])
            name_item.setData(Qt.ItemDataRole.UserRole, ch_id)  # Store ID in item
            self.table.setItem(row, self.COL_NAME, name_item)

            # Value
            value_item = QTableWidgetItem(str(ch['value']))
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_VALUE, value_item)

            # Unit
            unit_item = QTableWidgetItem(ch['unit'])
            unit_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_UNIT, unit_item)

            # Initial color
            self._set_row_color(row, self.COLOR_DISABLED if not self._connected else self.COLOR_NORMAL)

        self.count_label.setText(f"{len(sorted_ids)} channels")
        self._apply_filter()

    def _set_row_color(self, row: int, color: QColor):
        """Set background color for entire row."""
        for col in range(3):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(color))

    def _get_row_by_id(self, channel_id: str) -> int:
        """Find row index by channel ID."""
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, self.COL_NAME)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == channel_id:
                return row
        return -1

    def update_value(self, channel_id: str, value: Any, active: bool = False,
                     error: bool = False):
        """
        Update a single channel value.

        Args:
            channel_id: Channel identifier
            value: New value (will be converted to string)
            active: Whether channel is active/triggered (orange highlight)
            error: Whether channel has error (red highlight)
        """
        if channel_id not in self._channels:
            return

        # Store previous value for change detection
        prev_value = self._channels[channel_id].get('value')

        # Update internal state
        self._channels[channel_id]['value'] = value
        self._channels[channel_id]['active'] = active
        self._channels[channel_id]['error'] = error

        # Update table
        row = self._get_row_by_id(channel_id)
        if row < 0:
            return

        # Update value text
        value_item = self.table.item(row, self.COL_VALUE)
        if value_item:
            if isinstance(value, float):
                value_item.setText(f"{value:.2f}")
            else:
                value_item.setText(str(value))

        # Update row color based on state
        if error:
            self._set_row_color(row, self.COLOR_ERROR)
        elif active:
            self._set_row_color(row, self.COLOR_ACTIVE)
        elif prev_value != value and prev_value != '?':
            # Recently changed - show green briefly
            self._set_row_color(row, self.COLOR_CHANGED)
        else:
            self._set_row_color(row, self.COLOR_NORMAL)

    def update_values_batch(self, values: Dict[str, Any]):
        """
        Update multiple channel values at once.

        Args:
            values: Dict mapping channel_id to value (or tuple of (value, active, error))
        """
        for channel_id, val in values.items():
            if isinstance(val, tuple):
                if len(val) >= 3:
                    self.update_value(channel_id, val[0], val[1], val[2])
                elif len(val) >= 2:
                    self.update_value(channel_id, val[0], val[1])
                else:
                    self.update_value(channel_id, val[0])
            else:
                self.update_value(channel_id, val)

    def update_from_telemetry(self, telemetry_data: Dict[str, Any]):
        """
        Update channels from telemetry packet.

        Args:
            telemetry_data: Telemetry data dict with channel values
        """
        # Update PMU system channels
        if 'board_temp_l' in telemetry_data:
            self.update_value('pmu1.boardTemperatureL', telemetry_data['board_temp_l'])
        if 'board_temp_r' in telemetry_data:
            self.update_value('pmu1.boardTemperatureR', telemetry_data['board_temp_r'])
        if 'battery_voltage' in telemetry_data:
            self.update_value('pmu1.batteryVoltage', telemetry_data['battery_voltage'])
        if 'voltage_5v' in telemetry_data:
            self.update_value('pmu1.5VOutput', telemetry_data['voltage_5v'])
        if 'voltage_3v3' in telemetry_data:
            self.update_value('pmu1.3V3Output', telemetry_data['voltage_3v3'])
        if 'pmu_status' in telemetry_data:
            self.update_value('pmu1.status', telemetry_data['pmu_status'])
        if 'user_error' in telemetry_data:
            self.update_value('pmu1.userError', telemetry_data['user_error'],
                            error=telemetry_data['user_error'] != 0)

        # Update output channels
        if 'profet_states' in telemetry_data:
            states = telemetry_data['profet_states']
            state_names = ["OFF", "ON", "OC", "OT", "SC", "OL", "PWM", "DIS"]
            fault_states = [2, 3, 4, 5]  # OC, OT, SC, OL

            for i, state in enumerate(states):
                ch_id = f'o_{i+1}.status'
                status_str = state_names[state] if state < len(state_names) else "?"
                is_active = state == 1 or state == 6  # ON or PWM
                is_error = state in fault_states
                self.update_value(ch_id, status_str, active=is_active, error=is_error)

        if 'profet_currents' in telemetry_data:
            currents = telemetry_data['profet_currents']
            for i, current_ma in enumerate(currents):
                ch_id = f'o_{i+1}.current'
                if current_ma >= 1000:
                    self.update_value(ch_id, f"{current_ma/1000:.2f}A")
                else:
                    self.update_value(ch_id, f"{current_ma}mA")

        # Update analog input channels
        if 'adc_values' in telemetry_data:
            adc_values = telemetry_data['adc_values']
            ref_voltage = telemetry_data.get('reference_voltage', 5.0)
            for i, adc_raw in enumerate(adc_values):
                ch_id = f'a_{i+1}.voltage'
                voltage = (adc_raw / 4095.0) * ref_voltage
                self.update_value(ch_id, f"{voltage:.2f}V")

        # Update CAN RX channels
        if 'can_rx_values' in telemetry_data:
            for ch_id, value in telemetry_data['can_rx_values'].items():
                self.update_value(ch_id, value)

        # Update keypad channels
        if 'keypad_states' in telemetry_data:
            for keypad_id, state in telemetry_data['keypad_states'].items():
                self.update_value(keypad_id, "ON" if state else "OFF", active=state)

    def _update_display(self):
        """Periodic display update (for change color decay)."""
        # Reset changed colors back to normal after a short delay
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, self.COL_NAME)
            if not name_item:
                continue

            ch_id = name_item.data(Qt.ItemDataRole.UserRole)
            if ch_id not in self._channels:
                continue

            ch = self._channels[ch_id]

            # Get current background color
            bg = name_item.background().color()
            if bg == self.COLOR_CHANGED:
                # Decay green back to normal
                if ch.get('error'):
                    self._set_row_color(row, self.COLOR_ERROR)
                elif ch.get('active'):
                    self._set_row_color(row, self.COLOR_ACTIVE)
                else:
                    self._set_row_color(row, self.COLOR_NORMAL)

    def _apply_filter(self):
        """Apply filter to show/hide rows."""
        filter_text = self.filter_edit.text().lower()

        visible_count = 0
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, self.COL_NAME)
            if not name_item:
                continue

            name = name_item.text().lower()
            visible = filter_text in name if filter_text else True
            self.table.setRowHidden(row, not visible)
            if visible:
                visible_count += 1

        self.count_label.setText(f"{visible_count} of {self.table.rowCount()} channels")

    def get_channel_count(self) -> int:
        """Get number of configured channels."""
        return len(self._channels)

    def populate_from_config(self, config_manager):
        """
        Populate channels from config manager.

        Args:
            config_manager: ConfigManager instance with channel configurations
        """
        channels = []

        # Add PMU system channels
        pmu_system_channels = [
            {'id': 'pmu1.status', 'name': 'c_pmu1_status', 'unit': ''},
            {'id': 'pmu1.userError', 'name': 'c_pmu1_userError', 'unit': ''},
            {'id': 'pmu1.batteryVoltage', 'name': 'c_pmu1_batteryVoltage', 'unit': 'V'},
            {'id': 'pmu1.boardTemperatureL', 'name': 'c_pmu1_boardTemperatureL', 'unit': '°C'},
            {'id': 'pmu1.boardTemperatureR', 'name': 'c_pmu1_boardTemperatureR', 'unit': '°C'},
            {'id': 'pmu1.5VOutput', 'name': 'c_pmu1_5VOutput', 'unit': 'V'},
            {'id': 'pmu1.3V3Output', 'name': 'c_pmu1_3V3Output', 'unit': 'V'},
            {'id': 'pmu1.totalCurrent', 'name': 'c_pmu1_totalCurrent', 'unit': 'A'},
        ]
        channels.extend(pmu_system_channels)

        # Add CAN RX channels
        try:
            can_inputs = config_manager.get_can_inputs()
            for ch in can_inputs:
                if ch.get('enabled', True):
                    channels.append({
                        'id': ch.get('id', ''),
                        'name': ch.get('id', ''),
                        'unit': ch.get('unit', ''),
                        'channel_type': 'can_rx'
                    })
        except Exception:
            pass

        # Add output channels
        try:
            outputs = config_manager.get_outputs()
            for out in outputs:
                ch_num = out.get('channel', 0) + 1
                name = out.get('name', f'output{ch_num}')
                # Add status and current for each output
                channels.append({
                    'id': f'o_{ch_num}.status',
                    'name': f'o_{name}.status',
                    'unit': '',
                    'channel_type': 'output'
                })
                channels.append({
                    'id': f'o_{ch_num}.current',
                    'name': f'o_{name}.current',
                    'unit': 'mA',
                    'channel_type': 'output'
                })
                channels.append({
                    'id': f'o_{ch_num}.active',
                    'name': f'o_{name}.active',
                    'unit': '',
                    'channel_type': 'output'
                })
        except Exception:
            pass

        # Add analog input channels
        try:
            inputs = config_manager.get_inputs()
            for inp in inputs:
                ch_num = inp.get('channel', 0) + 1
                name = inp.get('name', f'analog{ch_num}')
                channels.append({
                    'id': f'a_{ch_num}.voltage',
                    'name': f'a_{name}.voltage',
                    'unit': 'V',
                    'channel_type': 'analog'
                })
        except Exception:
            pass

        # Add keypad channels
        try:
            keypads = config_manager.get_keypads()
            for kp in keypads:
                kp_id = kp.get('id', 'keypad')
                for btn_idx in range(kp.get('button_count', 8)):
                    channels.append({
                        'id': f'kb_{kp_id}.{btn_idx}.active',
                        'name': f'kb_{kp_id}.{btn_idx}.active',
                        'unit': '',
                        'channel_type': 'keypad'
                    })
        except Exception:
            pass

        # Add virtual/logic channels
        try:
            logic_channels = config_manager.get_logic_channels()
            for lc in logic_channels:
                ch_id = lc.get('id', '')
                channels.append({
                    'id': ch_id,
                    'name': f'k_{ch_id}',
                    'unit': '',
                    'channel_type': 'logic'
                })
        except Exception:
            pass

        self.set_channels(channels)

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
    QHeaderView, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List, Any, Optional


class VariablesInspector(QWidget):
    """Variables inspector widget with real-time telemetry display."""

    # Colors for different states (dark theme)
    COLOR_BG = QColor(0, 0, 0)                 # Black background
    COLOR_TEXT = QColor(255, 255, 255)         # White text
    COLOR_NORMAL = QColor(0, 0, 0)             # Black - normal background
    COLOR_ACTIVE = QColor(50, 80, 50)          # Dark green - active/triggered
    COLOR_ERROR = QColor(80, 40, 40)           # Dark red - error/fault
    COLOR_DISABLED = QColor(60, 60, 60)        # Dark gray - disabled
    COLOR_CHANGED = QColor(40, 60, 40)         # Darker green - recently changed

    # Column indices
    COL_NAME = 0
    COL_VALUE = 1
    COL_UNIT = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._connected = False
        self._channels: Dict[str, Dict[str, Any]] = {}  # name -> {value, unit, type, active}
        self._channel_id_map: Dict[int, str] = {}  # channel_id -> stored_id for fast lookup
        self._row_index_map: Dict[str, int] = {}  # channel_id -> row index for O(1) lookup
        self._changed_rows: set = set()  # Track rows that need color reset
        self._pending_updates: bool = False  # Flag for batched viewport updates
        self._init_ui()

        # Update timer - only for color decay, runs less frequently
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(250)  # Update every 250ms (was 100ms)

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Toolbar
        toolbar = QHBoxLayout()

        self.status_label = QLabel("Offline")
        self.status_label.setStyleSheet("color: #b0b0b0;")
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
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_VALUE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_UNIT, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnWidth(self.COL_NAME, 180)
        self.table.setColumnWidth(self.COL_VALUE, 80)
        self.table.setColumnWidth(self.COL_UNIT, 40)

        self.table.setAlternatingRowColors(False)  # We use custom row colors
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Dark theme styling
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
            QScrollBar:vertical {
                background-color: #1a1a1a;
                width: 14px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                min-height: 30px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #1a1a1a;
                height: 14px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: #555555;
                min-width: 30px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

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
            # Set constant channel values (they don't come from telemetry)
            self._update_constant_channels()
        else:
            self.status_label.setText("Offline")
            self.status_label.setStyleSheet("color: #b0b0b0;")
            # Reset all values to "?"
            self._reset_values()

    def _update_constant_channels(self):
        """Update constant channels with their fixed values."""
        # These are system constants that never change
        # zero = 0, one = 1 (displayed as float for consistency)
        if 'zero' in self._channels:
            self.update_value('zero', 0.0)
        if 'one' in self._channels:
            self.update_value('one', 1.0)

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
        self._channel_id_map.clear()

        for ch in channels:
            ch_id = ch.get('id', '')
            if not ch_id:
                continue

            # Get runtime channel ID for telemetry matching
            runtime_id = ch.get('channel_id') or ch.get('runtime_channel_id')

            self._channels[ch_id] = {
                'name': ch.get('name', ch_id),
                'unit': ch.get('unit', ''),
                'type': ch.get('channel_type', 'unknown'),
                'channel_type': ch.get('channel_type', 'unknown'),
                'channel_id': ch.get('channel_id'),  # JSON channel ID
                'runtime_channel_id': ch.get('runtime_channel_id'),  # Runtime ID for telemetry
                'value': '?',
                'active': False,
                'error': False,
            }

            # Build reverse lookup map for fast telemetry matching
            if runtime_id is not None:
                self._channel_id_map[runtime_id] = ch_id

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

        # Disable updates during bulk population for performance
        self.table.setUpdatesEnabled(False)

        self.table.setRowCount(len(sorted_ids))

        # Build row index map for O(1) lookup
        self._row_index_map.clear()

        for row, ch_id in enumerate(sorted_ids):
            ch = self._channels[ch_id]

            # Build reverse lookup map
            self._row_index_map[ch_id] = row

            # Name (not editable)
            name_item = QTableWidgetItem(ch['name'])
            name_item.setData(Qt.ItemDataRole.UserRole, ch_id)  # Store ID in item
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, self.COL_NAME, name_item)

            # Value (read-only)
            value_item = QTableWidgetItem(str(ch['value']))
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, self.COL_VALUE, value_item)

            # Unit (not editable)
            unit_item = QTableWidgetItem(ch['unit'])
            unit_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            unit_item.setFlags(unit_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, self.COL_UNIT, unit_item)

            # Initial color
            self._set_row_color(row, self.COLOR_DISABLED if not self._connected else self.COLOR_NORMAL)

        # Re-enable updates and repaint once
        self.table.setUpdatesEnabled(True)

        self.count_label.setText(f"{len(sorted_ids)} channels")
        self._apply_filter()

    def _set_row_color(self, row: int, color: QColor):
        """Set background color for entire row."""
        for col in range(3):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(color))

    def _get_row_by_id(self, channel_id: str) -> int:
        """Find row index by channel ID using O(1) lookup."""
        return self._row_index_map.get(channel_id, -1)

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

        # Update table - use O(1) row lookup
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
            # Recently changed - track for color decay
            self._set_row_color(row, self.COLOR_CHANGED)
            self._changed_rows.add(row)
        else:
            self._set_row_color(row, self.COLOR_NORMAL)
            self._changed_rows.discard(row)

        # NOTE: Removed viewport().update() - batched updates handled by timer

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
        # Update PMU system channels (using pmu.* naming)
        if 'board_temp_l' in telemetry_data:
            self.update_value('pmu.boardTemperatureL', telemetry_data['board_temp_l'])
        if 'board_temp_r' in telemetry_data:
            self.update_value('pmu.boardTemperatureR', telemetry_data['board_temp_r'])
        if 'battery_voltage' in telemetry_data:
            self.update_value('pmu.batteryVoltage', telemetry_data['battery_voltage'])
        if 'voltage_5v' in telemetry_data:
            self.update_value('pmu.5VOutput', telemetry_data['voltage_5v'])
        if 'voltage_3v3' in telemetry_data:
            self.update_value('pmu.3V3Output', telemetry_data['voltage_3v3'])
        if 'pmu_status' in telemetry_data:
            self.update_value('pmu.status', telemetry_data['pmu_status'])
        if 'user_error' in telemetry_data:
            self.update_value('pmu.userError', telemetry_data['user_error'],
                            error=telemetry_data['user_error'] != 0)
        if 'total_current' in telemetry_data:
            self.update_value('pmu.totalCurrent', telemetry_data['total_current'])
        if 'uptime' in telemetry_data:
            self.update_value('pmu.uptime', telemetry_data['uptime'])

        # Update hardware output channels (pmu.o{i}.*) - 40 PROFET outputs
        if 'profet_states' in telemetry_data:
            states = telemetry_data['profet_states']
            state_names = ["OFF", "ON", "OC", "OT", "SC", "OL", "PWM", "DIS"]
            fault_states = [2, 3, 4, 5]  # OC, OT, SC, OL

            for i, state in enumerate(states):
                # Hardware output status (pmu.o{i}.status)
                ch_id = f'pmu.o{i+1}.status'
                status_str = state_names[state] if state < len(state_names) else "?"
                is_active = state == 1 or state == 6  # ON or PWM
                is_error = state in fault_states
                self.update_value(ch_id, status_str, active=is_active, error=is_error)

        if 'profet_currents' in telemetry_data:
            currents = telemetry_data['profet_currents']
            for i, current_ma in enumerate(currents):
                # Hardware output current (pmu.o{i}.current)
                ch_id = f'pmu.o{i+1}.current'
                if current_ma >= 1000:
                    self.update_value(ch_id, f"{current_ma/1000:.2f}A")
                else:
                    self.update_value(ch_id, f"{current_ma}mA")

        # Update output duty cycles
        if 'profet_duties' in telemetry_data:
            duties = telemetry_data['profet_duties']
            states = telemetry_data.get('profet_states', [0] * 40)

            for i, duty in enumerate(duties):
                state = states[i] if i < len(states) else 0

                # Duty cycle (pmu.o{i}.dc)
                ch_id = f'pmu.o{i+1}.dc'
                if state == 1:  # ON
                    self.update_value(ch_id, "100.00%")
                elif state == 6:  # PWM
                    self.update_value(ch_id, f"{duty/10:.2f}%")
                else:
                    self.update_value(ch_id, "0.00%")

        # Update hardware analog input channels (pmu.a{i}.*)
        if 'adc_values' in telemetry_data:
            adc_values = telemetry_data['adc_values']
            ref_voltage = telemetry_data.get('reference_voltage', 3.3)  # 3.3V ADC reference
            for i, adc_raw in enumerate(adc_values):
                # Voltage (pmu.a{i}.voltage)
                ch_id = f'pmu.a{i+1}.voltage'
                voltage = (adc_raw / 4095.0) * ref_voltage
                self.update_value(ch_id, f"{voltage:.2f}V")

                # Raw ADC value (pmu.a{i}.raw)
                ch_id = f'pmu.a{i+1}.raw'
                self.update_value(ch_id, adc_raw)

        # Update hardware digital input channels (pmu.d{i}.*)
        if 'digital_states' in telemetry_data:
            digital_states = telemetry_data['digital_states']
            for i, state in enumerate(digital_states):
                ch_id = f'pmu.d{i+1}.state'
                self.update_value(ch_id, "1" if state else "0", active=state)

        # Update CAN RX channels
        if 'can_rx_values' in telemetry_data:
            for ch_id, value in telemetry_data['can_rx_values'].items():
                self.update_value(ch_id, value)

        # Update keypad channels (legacy)
        if 'keypad_states' in telemetry_data:
            for keypad_id, state in telemetry_data['keypad_states'].items():
                self.update_value(keypad_id, "ON" if state else "OFF", active=state)

        # Update BlinkMarine keypad button states
        if 'blinkmarine_buttons' in telemetry_data:
            for btn_id, state in telemetry_data['blinkmarine_buttons'].items():
                self.update_value(btn_id, "ON" if state else "OFF", active=state)

        # Update virtual channels (logic, timer, switch, number, etc.)
        if 'virtual_channels' in telemetry_data:
            for ch_id, value in telemetry_data['virtual_channels'].items():
                # Fast O(1) lookup using channel_id map
                stored_id = self._channel_id_map.get(ch_id)
                if stored_id is None:
                    continue

                ch_data = self._channels.get(stored_id)
                if ch_data is None:
                    continue

                # Format based on channel type
                ch_type = ch_data.get('channel_type', '')
                if ch_type == 'logic':
                    # Boolean display
                    display_value = "ON" if value > 0 else "OFF"
                    self.update_value(stored_id, display_value, active=(value > 0))
                elif ch_type == 'timer':
                    # Timer main channel shows ON/OFF status (running state)
                    # Value is 1000 when running, 0 when stopped
                    running = value > 0
                    display_value = "ON" if running else "OFF"
                    self.update_value(stored_id, display_value, active=running)
                elif ch_type == 'timer_running':
                    # Timer running flag (1 = running, 0 = stopped)
                    running = value > 0
                    self.update_value(stored_id, "1" if running else "0", active=running)
                elif ch_type == 'timer_elapsed':
                    # Timer elapsed channel - shows time in ms, display as seconds
                    seconds = value / 1000.0
                    if seconds >= 3600:
                        h = int(seconds // 3600)
                        m = int((seconds % 3600) // 60)
                        s = seconds % 60
                        time_str = f"{h}h {m}m {s:.2f}s"
                    elif seconds >= 60:
                        m = int(seconds // 60)
                        s = seconds % 60
                        time_str = f"{m}m {s:.2f}s"
                    else:
                        time_str = f"{seconds:.2f}s"
                    self.update_value(stored_id, time_str)
                elif ch_type == 'switch':
                    # Enum display (show state index)
                    self.update_value(stored_id, f"State {value // 1000}")
                else:
                    # Numeric display (scaled by 1000)
                    self.update_value(stored_id, f"{value / 1000:.2f}")

        # Always update constant channels (they don't come from telemetry)
        self._update_constant_channels()

    def _update_display(self):
        """Periodic display update (for change color decay)."""
        # Only process rows that were recently changed - O(changed_rows) instead of O(all_rows)
        if not self._changed_rows:
            return

        rows_to_process = list(self._changed_rows)
        self._changed_rows.clear()

        for row in rows_to_process:
            name_item = self.table.item(row, self.COL_NAME)
            if not name_item:
                continue

            ch_id = name_item.data(Qt.ItemDataRole.UserRole)
            if ch_id not in self._channels:
                continue

            ch = self._channels[ch_id]

            # Decay green back to appropriate color
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

        # Add constant channels
        constant_channels = [
            {'id': 'zero', 'name': 'zero', 'unit': '', 'channel_id': 1012, 'channel_type': 'system'},
            {'id': 'one', 'name': 'one', 'unit': '', 'channel_id': 1013, 'channel_type': 'system'},
        ]
        channels.extend(constant_channels)

        # Add PMU system channels (pmu.* naming)
        pmu_system_channels = [
            {'id': 'pmu.status', 'name': 'PMU Status', 'unit': ''},
            {'id': 'pmu.userError', 'name': 'User Error', 'unit': ''},
            {'id': 'pmu.batteryVoltage', 'name': 'Battery Voltage', 'unit': 'V'},
            {'id': 'pmu.boardTemperatureL', 'name': 'Board Temp L', 'unit': '°C'},
            {'id': 'pmu.boardTemperatureR', 'name': 'Board Temp R', 'unit': '°C'},
            {'id': 'pmu.boardTemperatureMax', 'name': 'Board Temp Max', 'unit': '°C'},
            {'id': 'pmu.5VOutput', 'name': '5V Output', 'unit': 'V'},
            {'id': 'pmu.3V3Output', 'name': '3.3V Output', 'unit': 'V'},
            {'id': 'pmu.totalCurrent', 'name': 'Total Current', 'unit': 'A'},
            {'id': 'pmu.uptime', 'name': 'Uptime', 'unit': 's'},
            {'id': 'pmu.isTurningOff', 'name': 'Is Turning Off', 'unit': ''},
        ]
        channels.extend(pmu_system_channels)

        # Add PMU hardware analog input channels (pmu.a{i}.*)
        for i in range(1, 21):
            channels.append({
                'id': f'pmu.a{i}.voltage',
                'name': f'Analog {i} Voltage',
                'unit': 'V',
                'channel_type': 'system'
            })
            channels.append({
                'id': f'pmu.a{i}.raw',
                'name': f'Analog {i} Raw',
                'unit': '',
                'channel_type': 'system'
            })

        # Add PMU hardware digital input channels (pmu.d{i}.*)
        for i in range(1, 21):
            channels.append({
                'id': f'pmu.d{i}.state',
                'name': f'Digital {i} State',
                'unit': '',
                'channel_type': 'system'
            })

        # Add PMU hardware output channels (pmu.o{i}.*) - 40 PROFET outputs
        # Only add key sub-channels to reduce row count (status, current, dc)
        for i in range(1, 41):
            output_subchannels = [
                ('status', 'Status', ''),
                ('current', 'Current', 'mA'),
                ('dc', 'Duty Cycle', '%'),
            ]
            for sub_id, sub_name, unit in output_subchannels:
                channels.append({
                    'id': f'pmu.o{i}.{sub_id}',
                    'name': f'Output {i} {sub_name}',
                    'unit': unit,
                    'channel_type': 'output'
                })

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

        # Add user-created output channel sub-properties (reduced set for performance)
        try:
            outputs = config_manager.get_outputs()
            for out in outputs:
                out_id = out.get('id', out.get('name', ''))
                out_name = out.get('name', out_id)
                if not out_id:
                    continue
                # Only essential sub-properties to reduce row count
                output_subprops = [
                    ('status', 'Status', ''),
                    ('current', 'Current', 'mA'),
                    ('dc', 'Duty Cycle', '%'),
                    ('fault', 'Fault', ''),
                ]
                for sub_id, sub_name, unit in output_subprops:
                    channels.append({
                        'id': f'{out_id}.{sub_id}',
                        'name': f'{out_name} - {sub_name}',
                        'unit': unit,
                        'channel_type': 'output'
                    })
        except Exception:
            pass

        # Add user-created analog input channel sub-properties
        try:
            inputs = config_manager.get_inputs()
            for inp in inputs:
                inp_id = inp.get('id', inp.get('name', ''))
                inp_name = inp.get('name', inp_id)
                if not inp_id:
                    continue
                channels.append({
                    'id': f'{inp_id}.voltage',
                    'name': f'{inp_name} - Voltage',
                    'unit': 'V',
                    'channel_type': 'analog'
                })
                channels.append({
                    'id': f'{inp_id}.raw',
                    'name': f'{inp_name} - Raw',
                    'unit': '',
                    'channel_type': 'analog'
                })
        except Exception:
            pass

        # Add keypad channels (legacy)
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

        # Add BlinkMarine keypad button channels
        try:
            blinkmarine_keypads = config_manager.get_blinkmarine_keypads()
            for kp in blinkmarine_keypads:
                kp_name = kp.get('name', kp.get('id', 'keypad'))
                keypad_type = kp.get('keypad_type', '2x6')
                # Determine button count based on keypad type
                button_count = 12 if keypad_type == '2x6' else 16
                buttons = kp.get('buttons', [])

                for btn_idx in range(button_count):
                    btn_name = f"Button {btn_idx + 1}"
                    # Try to get custom button name from config
                    if btn_idx < len(buttons):
                        btn_config = buttons[btn_idx]
                        if btn_config.get('name'):
                            btn_name = btn_config.get('name')

                    # Add button state channel
                    channels.append({
                        'id': f'bm_{kp_name}.btn{btn_idx + 1}',
                        'name': f'{kp_name} {btn_name}',
                        'unit': '',
                        'channel_type': 'keypad_button'
                    })
        except Exception:
            pass

        # Virtual channel ID counter - must match firmware assignment order
        # Firmware assigns IDs starting at 200 (PMU_CHANNEL_ID_VIRTUAL_START)
        # Channels are assigned IDs in the order they appear in the JSON channels array
        virtual_channel_id = 200

        # Get all channels from config in order and assign virtual channel IDs
        # IMPORTANT: This list must match the channel types that firmware actually registers
        # with AllocateVirtualChannelID() in pmu_config_json.c
        # Currently registered: logic, number, switch, filter, timer
        # NOT registered yet: can_rx (has TODO in firmware)
        VIRTUAL_CHANNEL_TYPES = {'logic', 'number', 'switch', 'filter', 'timer'}

        try:
            all_channels = config_manager.get_all_channels()
            for ch in all_channels:
                ch_type = ch.get('channel_type', '')
                ch_id = ch.get('id', '')

                if ch_type in VIRTUAL_CHANNEL_TYPES:
                    # Map channel type to display prefix
                    prefixes = {'logic': 'k_', 'number': 'n_', 'switch': 's_', 'can_rx': 'crx_', 'timer': 't_', 'filter': 'f_'}
                    prefix = prefixes.get(ch_type, '')

                    # Main channel
                    channels.append({
                        'id': ch_id,
                        'name': f'{prefix}{ch_id}',
                        'unit': ch.get('unit', ''),
                        'channel_type': ch_type,
                        'channel_id': virtual_channel_id
                    })
                    virtual_channel_id += 1

                    # Timer has additional sub-properties
                    if ch_type == 'timer':
                        ch_name = ch.get('name', ch_id)
                        # .elapsed - elapsed time
                        channels.append({
                            'id': f'{ch_id}.elapsed',
                            'name': f'{ch_name} - Elapsed',
                            'unit': 'ms',
                            'channel_type': 'timer_elapsed',
                            'channel_id': virtual_channel_id
                        })
                        virtual_channel_id += 1
                        # .running - is timer running
                        channels.append({
                            'id': f'{ch_id}.running',
                            'name': f'{ch_name} - Running',
                            'unit': '',
                            'channel_type': 'timer_running',
                            'channel_id': virtual_channel_id
                        })
                        virtual_channel_id += 1
        except Exception:
            pass

        self.set_channels(channels)

        # If already connected, initialize constant channels
        if self._connected:
            self._update_constant_channels()

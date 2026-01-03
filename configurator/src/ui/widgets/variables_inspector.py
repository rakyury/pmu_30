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
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VariablesInspector(QWidget):
    """Variables inspector widget with real-time telemetry display."""

    # Signal emitted when user double-clicks a channel to edit it
    # (channel_type, channel_id) - main_window will look up full config
    channel_edit_requested = pyqtSignal(str, str)

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

        # Double-click to edit channel
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        layout.addWidget(self.table)

        # Status bar
        self.count_label = QLabel("0 channels")
        layout.addWidget(self.count_label)

    def set_connected(self, connected: bool):
        """Set connection state."""
        self._connected = connected
        if not connected:
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
        self._channel_id_map.clear()

        logger.info(f"[DEBUG] set_channels called with {len(channels)} channels")

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
        Update virtual channels from telemetry packet.

        Only updates virtual channels (logic, number, timer, filter, switch, table_2d, table_3d, pid).
        Hardware/system channels are updated in PMU Monitor widget.

        Args:
            telemetry_data: Telemetry data dict with channel values
        """
        # Update virtual channels only (logic, timer, switch, number, etc.)
        if 'virtual_channels' not in telemetry_data:
            return

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
            elif ch_type in ('number', 'filter', 'table_2d', 'table_3d', 'pid'):
                # Numeric display (scaled by 1000)
                self.update_value(stored_id, f"{value / 1000:.2f}")

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

    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle double-click on table cell - emit signal to edit the channel."""
        if row < 0 or row >= self.table.rowCount():
            return

        # Get channel ID from the row
        name_item = self.table.item(row, self.COL_NAME)
        if not name_item:
            return

        # Find the channel by row in our index
        ch_id = None
        for stored_id, stored_row in self._row_index_map.items():
            if stored_row == row:
                ch_id = stored_id
                break

        if not ch_id or ch_id not in self._channels:
            logger.debug(f"Double-click: channel not found for row {row}")
            return

        ch_data = self._channels[ch_id]
        ch_type = ch_data.get('channel_type', ch_data.get('type', ''))

        # Only emit for editable channel types
        EDITABLE_TYPES = {
            'logic', 'number', 'timer', 'filter', 'switch', 'table_2d', 'table_3d',
            'analog_input', 'digital_input', 'power_output', 'hbridge',
            'can_rx', 'can_tx', 'pid'
        }

        if ch_type in EDITABLE_TYPES:
            logger.info(f"Double-click edit: {ch_type} - {ch_id}")
            self.channel_edit_requested.emit(ch_type, ch_id)
        else:
            logger.debug(f"Double-click: channel type '{ch_type}' not editable")

    def get_channel_count(self) -> int:
        """Get number of configured channels."""
        return len(self._channels)

    def populate_from_config(self, config_manager):
        """
        Populate channels from config manager.

        ONLY shows virtual channels (logic, number, timer, filter, switch, table_2d, table_3d, pid).
        Hardware/system channels are displayed in PMU Monitor widget.

        Uses actual channel_id from config (matches firmware binary config).

        Args:
            config_manager: ConfigManager instance with channel configurations
        """
        channels = []

        # Virtual channel types that should appear in Variables Inspector
        VIRTUAL_CHANNEL_TYPES = {
            'logic', 'number', 'switch', 'filter', 'timer',
            'table_2d', 'table_3d', 'pid'
        }

        logger.info(f"[DEBUG] populate_from_config called")

        try:
            all_channels = config_manager.get_all_channels()
            logger.info(f"[DEBUG] config_manager returned {len(all_channels)} channels")
            for ch in all_channels:
                ch_type = ch.get('channel_type', '')
                ch_id = ch.get('id', '')
                # Use actual channel_id from config (matches firmware telemetry)
                runtime_id = ch.get('channel_id')

                logger.info(f"[DEBUG]   Config channel: type={ch_type}, id={ch_id}, channel_id={runtime_id}")

                if runtime_id is None:
                    continue  # Skip channels without proper ID assignment

                # Use channel_name for display, fallback to id
                ch_display_name = ch.get('channel_name', ch.get('name', ch_id))

                if ch_type in VIRTUAL_CHANNEL_TYPES:
                    channels.append({
                        'id': ch_id,
                        'name': ch_display_name,
                        'unit': ch.get('unit', ''),
                        'channel_type': ch_type,
                        'channel_id': runtime_id  # Use actual ID from config
                    })
                    logger.info(f"[DEBUG]     -> Added to list: {ch_id} with runtime_id={runtime_id}")
        except Exception as e:
            logger.error(f"[DEBUG] populate_from_config error: {e}")

        self.set_channels(channels)

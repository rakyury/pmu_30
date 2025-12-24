"""
CAN Monitor Widget
Real-time CAN bus monitoring with decoded signal values
Similar to ECUMaster CAN Live mode

Features:
- Real-time message display with timestamps
- Decoded signal values based on configuration
- Message filtering by ID/name
- Pause/resume functionality
- Raw data view with hex/decimal toggle
- Send CAN message capability
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QCheckBox, QLineEdit, QComboBox, QSpinBox, QSplitter,
    QHeaderView, QToolBar, QFrame, QTabWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont
from typing import Dict, Any, List, Optional
from collections import deque
from datetime import datetime
import struct


class CANMonitor(QWidget):
    """Real-time CAN bus monitor widget."""

    # Signals
    send_message = pyqtSignal(int, bytes, bool)  # (arbitration_id, data, is_extended)

    # Colors
    COLOR_RX = QColor('#22c55e')       # Green for received
    COLOR_TX = QColor('#3b82f6')       # Blue for transmitted
    COLOR_ERROR = QColor('#ef4444')    # Red for errors
    COLOR_HIGHLIGHT = QColor('#f59e0b')  # Orange for highlighted

    def __init__(self, parent=None):
        super().__init__(parent)
        self.can_messages_config = []  # CAN message definitions
        self.can_inputs_config = []    # CAN input/signal definitions
        self._connected = False
        self._paused = False

        # Message history
        self.message_history = deque(maxlen=1000)

        # Live values for decoded signals
        self.signal_values = {}  # {signal_id: value}

        # Filter settings
        self._filter_id = None
        self._show_only_configured = False

        self._init_ui()
        self._setup_update_timer()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Message stream
        stream_widget = self._create_stream_widget()
        splitter.addWidget(stream_widget)

        # Right side - Tabs for Decoded Values and Send
        right_tabs = QTabWidget()

        # Decoded values tab
        decoded_widget = self._create_decoded_widget()
        right_tabs.addTab(decoded_widget, "Decoded Values")

        # Send message tab
        send_widget = self._create_send_widget()
        right_tabs.addTab(send_widget, "Send Message")

        splitter.addWidget(right_tabs)
        splitter.setSizes([500, 300])

        layout.addWidget(splitter)

        # Status bar
        status_layout = QHBoxLayout()
        self.rx_count_label = QLabel("RX: 0")
        self.tx_count_label = QLabel("TX: 0")
        self.error_count_label = QLabel("Errors: 0")
        self.bus_load_label = QLabel("Load: 0%")
        status_layout.addWidget(self.rx_count_label)
        status_layout.addWidget(self.tx_count_label)
        status_layout.addWidget(self.error_count_label)
        status_layout.addStretch()
        status_layout.addWidget(self.bus_load_label)

        self.connection_label = QLabel("Offline")
        self.connection_label.setStyleSheet("color: #888;")
        status_layout.addWidget(self.connection_label)

        layout.addLayout(status_layout)

        # Counters
        self._rx_count = 0
        self._tx_count = 0
        self._error_count = 0

    def _create_toolbar(self) -> QToolBar:
        """Create toolbar with controls."""
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # Pause/Resume button
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._on_pause_toggle)
        toolbar.addWidget(self.pause_btn)

        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_messages)
        toolbar.addWidget(self.clear_btn)

        toolbar.addSeparator()

        # Filter controls
        toolbar.addWidget(QLabel(" Filter: "))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("ID (hex) or name...")
        self.filter_edit.setMaximumWidth(150)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_edit)

        self.configured_only_check = QCheckBox("Configured only")
        self.configured_only_check.toggled.connect(self._on_filter_changed)
        toolbar.addWidget(self.configured_only_check)

        toolbar.addSeparator()

        # Display format
        toolbar.addWidget(QLabel(" Format: "))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Hex", "Decimal", "ASCII"])
        self.format_combo.currentIndexChanged.connect(self._refresh_display)
        toolbar.addWidget(self.format_combo)

        return toolbar

    def _create_stream_widget(self) -> QWidget:
        """Create message stream panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("CAN Message Stream")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        # Message table
        self.stream_table = QTableWidget()
        self.stream_table.setColumnCount(6)
        self.stream_table.setHorizontalHeaderLabels([
            "Time", "Dir", "ID", "Name", "DLC", "Data"
        ])

        header = self.stream_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.stream_table.setColumnWidth(0, 80)  # Time
        self.stream_table.setColumnWidth(1, 30)  # Dir
        self.stream_table.setColumnWidth(2, 80)  # ID
        self.stream_table.setColumnWidth(4, 35)  # DLC

        self.stream_table.verticalHeader().setVisible(False)
        self.stream_table.setAlternatingRowColors(True)
        self.stream_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.stream_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.stream_table)

        return widget

    def _create_decoded_widget(self) -> QWidget:
        """Create decoded values panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("Live Signal Values")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        # Decoded values table
        self.decoded_table = QTableWidget()
        self.decoded_table.setColumnCount(4)
        self.decoded_table.setHorizontalHeaderLabels([
            "Signal", "Value", "Unit", "Age"
        ])

        header = self.decoded_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)

        self.decoded_table.setColumnWidth(1, 80)   # Value
        self.decoded_table.setColumnWidth(2, 50)   # Unit
        self.decoded_table.setColumnWidth(3, 50)   # Age

        self.decoded_table.verticalHeader().setVisible(False)
        self.decoded_table.setAlternatingRowColors(True)
        self.decoded_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.decoded_table)

        return widget

    def _create_send_widget(self) -> QWidget:
        """Create send message panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("Send CAN Message")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        form = QFormLayout()

        # Arbitration ID
        id_layout = QHBoxLayout()
        self.send_id_edit = QLineEdit()
        self.send_id_edit.setPlaceholderText("0x123")
        self.send_id_edit.setMaximumWidth(100)
        id_layout.addWidget(self.send_id_edit)

        self.send_extended_check = QCheckBox("Extended (29-bit)")
        id_layout.addWidget(self.send_extended_check)
        id_layout.addStretch()

        form.addRow("ID:", id_layout)

        # Data bytes
        self.send_data_edit = QLineEdit()
        self.send_data_edit.setPlaceholderText("00 11 22 33 44 55 66 77")
        form.addRow("Data:", self.send_data_edit)

        # DLC info
        self.send_dlc_label = QLabel("DLC: 0")
        form.addRow("", self.send_dlc_label)

        layout.addLayout(form)

        # Update DLC on data change
        self.send_data_edit.textChanged.connect(self._update_send_dlc)

        # Send buttons
        btn_layout = QHBoxLayout()

        self.send_once_btn = QPushButton("Send Once")
        self.send_once_btn.clicked.connect(self._on_send_once)
        btn_layout.addWidget(self.send_once_btn)

        self.send_periodic_btn = QPushButton("Start Periodic")
        self.send_periodic_btn.setCheckable(True)
        self.send_periodic_btn.toggled.connect(self._on_send_periodic)
        btn_layout.addWidget(self.send_periodic_btn)

        self.periodic_interval_spin = QSpinBox()
        self.periodic_interval_spin.setRange(10, 10000)
        self.periodic_interval_spin.setValue(100)
        self.periodic_interval_spin.setSuffix(" ms")
        btn_layout.addWidget(self.periodic_interval_spin)

        layout.addLayout(btn_layout)

        # Quick send buttons for configured messages
        layout.addWidget(QLabel("Quick Send:"))

        self.quick_send_layout = QVBoxLayout()
        layout.addLayout(self.quick_send_layout)

        layout.addStretch()

        # Periodic send timer
        self.periodic_timer = QTimer(self)
        self.periodic_timer.timeout.connect(self._on_send_once)

        return widget

    def _setup_update_timer(self):
        """Setup timer for display updates."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(100)  # 10 Hz

    def set_configuration(self, messages: List[Dict], inputs: List[Dict]):
        """Set CAN configuration for decoding."""
        self.can_messages_config = messages or []
        self.can_inputs_config = inputs or []
        self._populate_decoded_table()
        self._update_quick_send_buttons()

    def _populate_decoded_table(self):
        """Populate decoded values table with configured signals."""
        self.decoded_table.setRowCount(0)

        for inp in self.can_inputs_config:
            row = self.decoded_table.rowCount()
            self.decoded_table.insertRow(row)

            # Signal name
            name = inp.get("id", inp.get("name", "Unknown"))
            name_item = QTableWidgetItem(name)
            self.decoded_table.setItem(row, 0, name_item)

            # Value
            value_item = QTableWidgetItem("---")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.decoded_table.setItem(row, 1, value_item)

            # Unit
            unit = inp.get("unit", "")
            unit_item = QTableWidgetItem(unit)
            unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.decoded_table.setItem(row, 2, unit_item)

            # Age
            age_item = QTableWidgetItem("---")
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.decoded_table.setItem(row, 3, age_item)

    def _update_quick_send_buttons(self):
        """Update quick send buttons based on configured TX messages."""
        # Clear existing buttons
        while self.quick_send_layout.count():
            child = self.quick_send_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add buttons for TX messages
        for msg in self.can_messages_config:
            if msg.get("direction", "rx") == "tx":
                btn = QPushButton(msg.get("name", f"0x{msg.get('base_id', 0):X}"))
                btn.setProperty("msg_config", msg)
                btn.clicked.connect(self._on_quick_send)
                self.quick_send_layout.addWidget(btn)

    def _on_pause_toggle(self, paused: bool):
        """Handle pause toggle."""
        self._paused = paused
        self.pause_btn.setText("Resume" if paused else "Pause")

    def _clear_messages(self):
        """Clear message history."""
        self.message_history.clear()
        self.stream_table.setRowCount(0)
        self._rx_count = 0
        self._tx_count = 0
        self._error_count = 0
        self._update_counters()

    def _on_filter_changed(self):
        """Handle filter change."""
        filter_text = self.filter_edit.text().strip()

        if filter_text:
            # Try to parse as hex ID
            try:
                if filter_text.startswith("0x"):
                    self._filter_id = int(filter_text, 16)
                else:
                    self._filter_id = int(filter_text, 16)
            except ValueError:
                # Use as name filter
                self._filter_id = filter_text
        else:
            self._filter_id = None

        self._show_only_configured = self.configured_only_check.isChecked()
        self._refresh_display()

    def _refresh_display(self):
        """Refresh message display with current filters."""
        self.stream_table.setRowCount(0)

        for msg in self.message_history:
            if self._should_show_message(msg):
                self._add_message_to_table(msg)

    def _should_show_message(self, msg: Dict) -> bool:
        """Check if message should be shown based on filters."""
        if self._show_only_configured:
            msg_id = msg.get("id")
            configured_ids = {m.get("base_id") for m in self.can_messages_config}
            if msg_id not in configured_ids:
                return False

        if self._filter_id is not None:
            if isinstance(self._filter_id, int):
                if msg.get("id") != self._filter_id:
                    return False
            else:
                # Name filter
                name = msg.get("name", "").lower()
                if self._filter_id.lower() not in name:
                    return False

        return True

    def _format_data(self, data: bytes) -> str:
        """Format data bytes according to selected format."""
        format_type = self.format_combo.currentText()

        if format_type == "Hex":
            return " ".join(f"{b:02X}" for b in data)
        elif format_type == "Decimal":
            return " ".join(f"{b:3d}" for b in data)
        else:  # ASCII
            result = []
            for b in data:
                if 32 <= b < 127:
                    result.append(chr(b))
                else:
                    result.append(".")
            return "".join(result)

    def _add_message_to_table(self, msg: Dict):
        """Add message to stream table."""
        row = self.stream_table.rowCount()
        self.stream_table.insertRow(row)

        # Time
        time_item = QTableWidgetItem(msg.get("time", ""))
        self.stream_table.setItem(row, 0, time_item)

        # Direction
        direction = msg.get("direction", "RX")
        dir_item = QTableWidgetItem(direction)
        dir_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        color = self.COLOR_TX if direction == "TX" else self.COLOR_RX
        dir_item.setForeground(QBrush(color))
        self.stream_table.setItem(row, 1, dir_item)

        # ID
        arb_id = msg.get("id", 0)
        is_extended = msg.get("extended", False)
        id_str = f"0x{arb_id:08X}" if is_extended else f"0x{arb_id:03X}"
        id_item = QTableWidgetItem(id_str)
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stream_table.setItem(row, 2, id_item)

        # Name (from config)
        name = msg.get("name", "")
        if not name:
            for cfg in self.can_messages_config:
                if cfg.get("base_id") == arb_id:
                    name = cfg.get("name", "")
                    break
        name_item = QTableWidgetItem(name)
        self.stream_table.setItem(row, 3, name_item)

        # DLC
        data = msg.get("data", b"")
        dlc_item = QTableWidgetItem(str(len(data)))
        dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stream_table.setItem(row, 4, dlc_item)

        # Data
        data_str = self._format_data(data)
        data_item = QTableWidgetItem(data_str)
        data_item.setFont(QFont("Consolas", 9))
        self.stream_table.setItem(row, 5, data_item)

        # Auto scroll to bottom
        self.stream_table.scrollToBottom()

    def receive_message(self, arb_id: int, data: bytes, is_extended: bool = False, is_error: bool = False):
        """Process received CAN message."""
        if self._paused:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        msg = {
            "time": timestamp,
            "direction": "RX",
            "id": arb_id,
            "extended": is_extended,
            "data": data,
            "name": "",
            "error": is_error
        }

        # Find message name from config
        for cfg in self.can_messages_config:
            if cfg.get("base_id") == arb_id:
                msg["name"] = cfg.get("name", "")
                break

        self.message_history.append(msg)

        if is_error:
            self._error_count += 1
        else:
            self._rx_count += 1

        self._update_counters()

        if self._should_show_message(msg):
            self._add_message_to_table(msg)

        # Decode signals
        self._decode_signals(arb_id, data)

    def _decode_signals(self, arb_id: int, data: bytes):
        """Decode signals from received message."""
        for inp in self.can_inputs_config:
            # Find message reference
            msg_ref = inp.get("message_ref", "")
            matching_msg = None
            for msg in self.can_messages_config:
                if msg.get("id") == msg_ref and msg.get("base_id") == arb_id:
                    matching_msg = msg
                    break

            if not matching_msg:
                continue

            # Decode value based on configuration
            try:
                start_byte = inp.get("start_byte", 0)
                data_format = inp.get("data_format", "16bit")
                data_type = inp.get("data_type", "unsigned")
                byte_order = inp.get("byte_order", "little_endian")

                # Extract bytes
                if data_format == "8bit":
                    if start_byte < len(data):
                        raw_value = data[start_byte]
                        if data_type == "signed" and raw_value > 127:
                            raw_value -= 256
                elif data_format == "16bit":
                    if start_byte + 1 < len(data):
                        fmt = "<H" if byte_order == "little_endian" else ">H"
                        if data_type == "signed":
                            fmt = "<h" if byte_order == "little_endian" else ">h"
                        raw_value = struct.unpack(fmt, data[start_byte:start_byte+2])[0]
                    else:
                        continue
                elif data_format == "32bit":
                    if start_byte + 3 < len(data):
                        fmt = "<I" if byte_order == "little_endian" else ">I"
                        if data_type == "signed":
                            fmt = "<i" if byte_order == "little_endian" else ">i"
                        raw_value = struct.unpack(fmt, data[start_byte:start_byte+4])[0]
                    else:
                        continue
                else:
                    continue

                # Apply scaling
                multiplier = inp.get("multiplier", 1.0)
                divider = inp.get("divider", 1.0)
                offset = inp.get("offset", 0.0)

                value = (raw_value * multiplier / divider) + offset

                # Store value
                signal_id = inp.get("id", "")
                self.signal_values[signal_id] = {
                    "value": value,
                    "timestamp": datetime.now()
                }

            except (struct.error, IndexError):
                pass

    def _update_display(self):
        """Update decoded values display."""
        if not self._connected:
            return

        now = datetime.now()

        for row in range(self.decoded_table.rowCount()):
            name_item = self.decoded_table.item(row, 0)
            if not name_item:
                continue

            signal_id = name_item.text()
            signal_data = self.signal_values.get(signal_id)

            value_item = self.decoded_table.item(row, 1)
            age_item = self.decoded_table.item(row, 3)

            if signal_data:
                value = signal_data["value"]
                timestamp = signal_data["timestamp"]
                age_ms = (now - timestamp).total_seconds() * 1000

                value_item.setText(f"{value:.2f}")
                age_item.setText(f"{int(age_ms)}")

                # Color based on age
                if age_ms < 500:
                    value_item.setForeground(QBrush(self.COLOR_RX))
                elif age_ms < 2000:
                    value_item.setForeground(QBrush(Qt.GlobalColor.black))
                else:
                    value_item.setForeground(QBrush(Qt.GlobalColor.gray))
            else:
                value_item.setText("---")
                age_item.setText("---")

    def _update_counters(self):
        """Update counter labels."""
        self.rx_count_label.setText(f"RX: {self._rx_count}")
        self.tx_count_label.setText(f"TX: {self._tx_count}")
        self.error_count_label.setText(f"Errors: {self._error_count}")

    def _update_send_dlc(self):
        """Update DLC label based on data input."""
        data_text = self.send_data_edit.text().strip()
        if not data_text:
            self.send_dlc_label.setText("DLC: 0")
            return

        try:
            bytes_list = data_text.replace(",", " ").split()
            dlc = len(bytes_list)
            self.send_dlc_label.setText(f"DLC: {dlc}")
        except:
            self.send_dlc_label.setText("DLC: ?")

    def _parse_send_data(self) -> Optional[tuple]:
        """Parse send data fields."""
        # Parse ID
        id_text = self.send_id_edit.text().strip()
        if not id_text:
            return None

        try:
            if id_text.startswith("0x"):
                arb_id = int(id_text, 16)
            else:
                arb_id = int(id_text, 16)
        except ValueError:
            return None

        # Parse data
        data_text = self.send_data_edit.text().strip()
        if not data_text:
            data = b""
        else:
            try:
                bytes_list = data_text.replace(",", " ").split()
                data = bytes([int(b, 16) for b in bytes_list])
            except ValueError:
                return None

        is_extended = self.send_extended_check.isChecked()

        return arb_id, data, is_extended

    def _on_send_once(self):
        """Send message once."""
        if not self._connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
            return

        parsed = self._parse_send_data()
        if not parsed:
            QMessageBox.warning(self, "Invalid Data", "Please enter valid ID and data.")
            return

        arb_id, data, is_extended = parsed

        # Emit signal to send
        self.send_message.emit(arb_id, data, is_extended)

        # Log to stream
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = {
            "time": timestamp,
            "direction": "TX",
            "id": arb_id,
            "extended": is_extended,
            "data": data,
            "name": ""
        }
        self.message_history.append(msg)
        self._tx_count += 1
        self._update_counters()

        if self._should_show_message(msg):
            self._add_message_to_table(msg)

    def _on_send_periodic(self, checked: bool):
        """Toggle periodic sending."""
        if checked:
            # Validate data before starting periodic send
            if not self._connected:
                QMessageBox.warning(self, "Not Connected", "Please connect to device first.")
                self.send_periodic_btn.setChecked(False)
                return

            parsed = self._parse_send_data()
            if not parsed:
                QMessageBox.warning(self, "Invalid Data", "Please enter valid ID and data.")
                self.send_periodic_btn.setChecked(False)
                return

            interval = self.periodic_interval_spin.value()
            self.periodic_timer.start(interval)
            self.send_periodic_btn.setText("Stop Periodic")
        else:
            self.periodic_timer.stop()
            self.send_periodic_btn.setText("Start Periodic")

    def _on_quick_send(self):
        """Handle quick send button click."""
        sender = self.sender()
        if not sender:
            return

        msg_config = sender.property("msg_config")
        if not msg_config:
            return

        arb_id = msg_config.get("base_id", 0)
        default_data = msg_config.get("default_data", [0] * 8)
        is_extended = msg_config.get("is_extended", False)

        data = bytes(default_data[:8])
        self.send_message.emit(arb_id, data, is_extended)

    def set_connected(self, connected: bool):
        """Update connection state."""
        self._connected = connected
        if connected:
            self.connection_label.setText("Online")
            self.connection_label.setStyleSheet("color: #22c55e; font-weight: bold;")
        else:
            self.connection_label.setText("Offline")
            self.connection_label.setStyleSheet("color: #888;")
            # Clear values
            self.signal_values.clear()
            for row in range(self.decoded_table.rowCount()):
                self.decoded_table.item(row, 1).setText("---")
                self.decoded_table.item(row, 3).setText("---")

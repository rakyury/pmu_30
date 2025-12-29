"""
Monitor Widgets - CAN, LIN and Wireless status monitors

This module contains widgets for monitoring communication buses and wireless status.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QLineEdit, QComboBox, QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush
from typing import Optional
from collections import deque
from datetime import datetime


class CANMonitorWidget(QWidget):
    """CAN bus monitor widget for emulator."""

    COLOR_RX = QColor('#22c55e')       # Green for received
    COLOR_TX = QColor('#3b82f6')       # Blue for transmitted

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = True  # Start paused
        self.message_history: deque = deque(maxlen=500)
        self._filter_id: Optional[int] = None
        self._init_ui()

    def _init_ui(self):
        # Set size policy to expand
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()

        self.pause_btn = QPushButton("Resume")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setChecked(True)  # Start checked (paused)
        self.pause_btn.clicked.connect(self._toggle_pause)
        toolbar.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_messages)
        toolbar.addWidget(self.clear_btn)

        toolbar.addWidget(QLabel("Filter ID:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("e.g. 0x100")
        self.filter_edit.setMaximumWidth(100)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_edit)

        self.msg_count_label = QLabel("Messages: 0")
        toolbar.addWidget(self.msg_count_label)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Splitter for message stream and send panel
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Message table
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.msg_table = QTableWidget()
        self.msg_table.setColumnCount(6)
        self.msg_table.setHorizontalHeaderLabels(["Time", "Dir", "Bus", "ID", "DLC", "Data"])
        self.msg_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.msg_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.msg_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.msg_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.msg_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.msg_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.msg_table.setAlternatingRowColors(False)
        self.msg_table.setFont(QFont("Consolas", 9))
        self.msg_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table_layout.addWidget(self.msg_table, 1)  # Stretch factor 1

        splitter.addWidget(table_widget)

        # Send CAN message panel
        send_widget = QGroupBox("Send CAN Message")
        send_layout = QGridLayout(send_widget)

        send_layout.addWidget(QLabel("Bus:"), 0, 0)
        self.bus_combo = QComboBox()
        self.bus_combo.addItems(["CAN1", "CAN2", "CAN3", "CAN4"])
        send_layout.addWidget(self.bus_combo, 0, 1)

        send_layout.addWidget(QLabel("ID:"), 1, 0)
        self.send_id_edit = QLineEdit("0x100")
        self.send_id_edit.setMaximumWidth(100)
        send_layout.addWidget(self.send_id_edit, 1, 1)

        send_layout.addWidget(QLabel("DLC:"), 2, 0)
        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 8)
        self.dlc_spin.setValue(8)
        send_layout.addWidget(self.dlc_spin, 2, 1)

        send_layout.addWidget(QLabel("Data:"), 3, 0)
        self.data_edit = QLineEdit("00 00 00 00 00 00 00 00")
        self.data_edit.setFont(QFont("Consolas", 9))
        send_layout.addWidget(self.data_edit, 3, 1)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send_message)
        send_layout.addWidget(self.send_btn, 4, 0, 1, 2)

        # Quick send buttons
        quick_group = QGroupBox("Quick Send")
        quick_layout = QVBoxLayout(quick_group)

        self.quick1_btn = QPushButton("Engine RPM 3000")
        self.quick1_btn.clicked.connect(lambda: self._quick_send(0x100, b'\x00\x00\x0B\xB8\x00\x00\x00\x00'))
        quick_layout.addWidget(self.quick1_btn)

        self.quick2_btn = QPushButton("Vehicle Speed 100km/h")
        self.quick2_btn.clicked.connect(lambda: self._quick_send(0x101, b'\x64\x00\x00\x00\x00\x00\x00\x00'))
        quick_layout.addWidget(self.quick2_btn)

        self.quick3_btn = QPushButton("Ignition ON")
        self.quick3_btn.clicked.connect(lambda: self._quick_send(0x102, b'\x01\x00\x00\x00\x00\x00\x00\x00'))
        quick_layout.addWidget(self.quick3_btn)

        send_layout.addWidget(quick_group, 5, 0, 1, 2)
        send_layout.setRowStretch(6, 1)

        splitter.addWidget(send_widget)
        splitter.setSizes([600, 250])
        splitter.setStretchFactor(0, 2)  # Table side gets more space
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)  # Stretch factor 1 for splitter

    def _toggle_pause(self, checked: bool):
        self._paused = checked
        self.pause_btn.setText("Resume" if checked else "Pause")

    def _clear_messages(self):
        self.message_history.clear()
        self.msg_table.setRowCount(0)
        self.msg_count_label.setText("Messages: 0")

    def _on_filter_changed(self, text: str):
        try:
            if text.strip():
                self._filter_id = int(text, 0)  # Parse hex or decimal
            else:
                self._filter_id = None
        except ValueError:
            self._filter_id = None

    def add_message(self, direction: str, bus: int, arb_id: int, data: bytes, timestamp: Optional[datetime] = None):
        """Add a CAN message to the display."""
        if self._paused:
            return

        if self._filter_id is not None and arb_id != self._filter_id:
            return

        if timestamp is None:
            timestamp = datetime.now()

        # Add to history
        msg = {
            'time': timestamp,
            'dir': direction,
            'bus': bus,
            'id': arb_id,
            'data': data
        }
        self.message_history.append(msg)

        # Disable updates while modifying table
        self.msg_table.setUpdatesEnabled(False)

        # Add to table
        row = self.msg_table.rowCount()
        self.msg_table.insertRow(row)

        # Time
        time_item = QTableWidgetItem(timestamp.strftime("%H:%M:%S.%f")[:-3])
        self.msg_table.setItem(row, 0, time_item)

        # Direction
        dir_item = QTableWidgetItem(direction)
        dir_item.setForeground(QBrush(self.COLOR_RX if direction == "RX" else self.COLOR_TX))
        self.msg_table.setItem(row, 1, dir_item)

        # Bus
        self.msg_table.setItem(row, 2, QTableWidgetItem(f"CAN{bus + 1}"))

        # ID
        id_item = QTableWidgetItem(f"0x{arb_id:03X}")
        id_item.setFont(QFont("Consolas", 9))
        self.msg_table.setItem(row, 3, id_item)

        # DLC
        self.msg_table.setItem(row, 4, QTableWidgetItem(str(len(data))))

        # Data
        data_str = " ".join(f"{b:02X}" for b in data)
        data_item = QTableWidgetItem(data_str)
        data_item.setFont(QFont("Consolas", 9))
        self.msg_table.setItem(row, 5, data_item)

        # Limit rows
        if self.msg_table.rowCount() > 500:
            self.msg_table.removeRow(0)

        # Re-enable updates
        self.msg_table.setUpdatesEnabled(True)

        # Auto-scroll (only if visible)
        if self.msg_table.isVisible():
            self.msg_table.scrollToBottom()

        self.msg_count_label.setText(f"Messages: {len(self.message_history)}")

    def _send_message(self):
        """Send CAN message from form."""
        try:
            arb_id = int(self.send_id_edit.text(), 0)
            dlc = self.dlc_spin.value()
            data_str = self.data_edit.text().replace(" ", "")
            data = bytes.fromhex(data_str)[:dlc]
            bus = self.bus_combo.currentIndex()

            # Add to display as TX
            self.add_message("TX", bus, arb_id, data)

            # TODO: Actually send via protocol

        except Exception as e:
            pass

    def _quick_send(self, arb_id: int, data: bytes):
        """Quick send preset message."""
        bus = self.bus_combo.currentIndex()
        self.add_message("TX", bus, arb_id, data)
        # TODO: Actually send via protocol


class LINMonitorWidget(QWidget):
    """LIN bus monitor widget for emulator."""

    COLOR_MASTER = QColor('#3b82f6')    # Blue for master frames
    COLOR_SLAVE = QColor('#22c55e')     # Green for slave responses
    COLOR_ERROR = QColor('#ef4444')     # Red for errors

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = True  # Start paused
        self.frame_history: deque = deque(maxlen=500)
        self._filter_id: Optional[int] = None
        self._init_ui()

    def _init_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()

        self.pause_btn = QPushButton("Resume")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setChecked(True)  # Start checked (paused)
        self.pause_btn.clicked.connect(self._toggle_pause)
        toolbar.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_frames)
        toolbar.addWidget(self.clear_btn)

        toolbar.addWidget(QLabel("Filter ID:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("e.g. 0x10")
        self.filter_edit.setMaximumWidth(80)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_edit)

        self.frame_count_label = QLabel("Frames: 0")
        toolbar.addWidget(self.frame_count_label)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Splitter for frame stream and send panel
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Frame table
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.frame_table = QTableWidget()
        self.frame_table.setColumnCount(7)
        self.frame_table.setHorizontalHeaderLabels(["Time", "Type", "Bus", "ID", "Len", "Data", "Checksum"])
        self.frame_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.frame_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.frame_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.frame_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.frame_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.frame_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.frame_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.frame_table.setAlternatingRowColors(False)
        self.frame_table.setFont(QFont("Consolas", 9))
        self.frame_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table_layout.addWidget(self.frame_table, 1)

        splitter.addWidget(table_widget)

        # Send LIN frame panel
        send_widget = QGroupBox("Send LIN Frame")
        send_layout = QGridLayout(send_widget)

        send_layout.addWidget(QLabel("Bus:"), 0, 0)
        self.bus_combo = QComboBox()
        self.bus_combo.addItems(["LIN1", "LIN2"])
        send_layout.addWidget(self.bus_combo, 0, 1)

        send_layout.addWidget(QLabel("ID:"), 1, 0)
        self.send_id_spin = QSpinBox()
        self.send_id_spin.setRange(0, 63)
        self.send_id_spin.setValue(0)
        self.send_id_spin.setPrefix("0x")
        self.send_id_spin.setDisplayIntegerBase(16)
        send_layout.addWidget(self.send_id_spin, 1, 1)

        send_layout.addWidget(QLabel("Length:"), 2, 0)
        self.len_spin = QSpinBox()
        self.len_spin.setRange(1, 8)
        self.len_spin.setValue(8)
        send_layout.addWidget(self.len_spin, 2, 1)

        send_layout.addWidget(QLabel("Data:"), 3, 0)
        self.data_edit = QLineEdit("00 00 00 00 00 00 00 00")
        self.data_edit.setFont(QFont("Consolas", 9))
        send_layout.addWidget(self.data_edit, 3, 1)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send_frame)
        send_layout.addWidget(self.send_btn, 4, 0, 1, 2)

        # Quick send buttons
        quick_group = QGroupBox("Quick Send")
        quick_layout = QVBoxLayout(quick_group)

        self.quick1_btn = QPushButton("Wiper Status Request")
        self.quick1_btn.clicked.connect(lambda: self._quick_send(0x20, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'))
        quick_layout.addWidget(self.quick1_btn)

        self.quick2_btn = QPushButton("Window Control")
        self.quick2_btn.clicked.connect(lambda: self._quick_send(0x21, b'\x01\x00\x00\x00\x00\x00\x00\x00'))
        quick_layout.addWidget(self.quick2_btn)

        self.quick3_btn = QPushButton("Mirror Adjust")
        self.quick3_btn.clicked.connect(lambda: self._quick_send(0x22, b'\x02\x80\x80\x00\x00\x00\x00\x00'))
        quick_layout.addWidget(self.quick3_btn)

        send_layout.addWidget(quick_group, 5, 0, 1, 2)
        send_layout.setRowStretch(6, 1)

        splitter.addWidget(send_widget)
        splitter.setSizes([600, 250])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

    def _toggle_pause(self, checked: bool):
        self._paused = checked
        self.pause_btn.setText("Resume" if checked else "Pause")

    def _clear_frames(self):
        self.frame_history.clear()
        self.frame_table.setRowCount(0)
        self.frame_count_label.setText("Frames: 0")

    def _on_filter_changed(self, text: str):
        try:
            if text.strip():
                self._filter_id = int(text, 0)
            else:
                self._filter_id = None
        except ValueError:
            self._filter_id = None

    def add_frame(self, frame_type: str, bus: int, frame_id: int, data: bytes, checksum: int = 0, timestamp: Optional[datetime] = None):
        """Add a LIN frame to the display."""
        if self._paused:
            return

        if self._filter_id is not None and frame_id != self._filter_id:
            return

        if timestamp is None:
            timestamp = datetime.now()

        # Add to history
        frame = {
            'time': timestamp,
            'type': frame_type,
            'bus': bus,
            'id': frame_id,
            'data': data,
            'checksum': checksum
        }
        self.frame_history.append(frame)

        # Disable updates while modifying table
        self.frame_table.setUpdatesEnabled(False)

        # Add to table
        row = self.frame_table.rowCount()
        self.frame_table.insertRow(row)

        # Time
        time_item = QTableWidgetItem(timestamp.strftime("%H:%M:%S.%f")[:-3])
        self.frame_table.setItem(row, 0, time_item)

        # Type
        type_item = QTableWidgetItem(frame_type)
        if frame_type == "Master":
            type_item.setForeground(QBrush(self.COLOR_MASTER))
        elif frame_type == "Slave":
            type_item.setForeground(QBrush(self.COLOR_SLAVE))
        elif frame_type == "Error":
            type_item.setForeground(QBrush(self.COLOR_ERROR))
        self.frame_table.setItem(row, 1, type_item)

        # Bus
        self.frame_table.setItem(row, 2, QTableWidgetItem(f"LIN{bus + 1}"))

        # ID
        id_item = QTableWidgetItem(f"0x{frame_id:02X}")
        id_item.setFont(QFont("Consolas", 9))
        self.frame_table.setItem(row, 3, id_item)

        # Length
        self.frame_table.setItem(row, 4, QTableWidgetItem(str(len(data))))

        # Data
        data_str = " ".join(f"{b:02X}" for b in data)
        data_item = QTableWidgetItem(data_str)
        data_item.setFont(QFont("Consolas", 9))
        self.frame_table.setItem(row, 5, data_item)

        # Checksum
        cs_item = QTableWidgetItem(f"0x{checksum:02X}")
        cs_item.setFont(QFont("Consolas", 9))
        self.frame_table.setItem(row, 6, cs_item)

        # Limit rows
        if self.frame_table.rowCount() > 500:
            self.frame_table.removeRow(0)

        # Re-enable updates
        self.frame_table.setUpdatesEnabled(True)

        # Auto-scroll (only if visible)
        if self.frame_table.isVisible():
            self.frame_table.scrollToBottom()

        self.frame_count_label.setText(f"Frames: {len(self.frame_history)}")

    def _send_frame(self):
        """Send LIN frame from form."""
        try:
            frame_id = self.send_id_spin.value()
            length = self.len_spin.value()
            data_str = self.data_edit.text().replace(" ", "")
            data = bytes.fromhex(data_str)[:length]
            bus = self.bus_combo.currentIndex()

            # Calculate checksum (classic LIN checksum)
            checksum = sum(data) & 0xFF
            checksum = (~checksum) & 0xFF

            # Add to display as Master
            self.add_frame("Master", bus, frame_id, data, checksum)

            # TODO: Actually send via protocol

        except Exception as e:
            pass

    def _quick_send(self, frame_id: int, data: bytes):
        """Quick send preset frame."""
        bus = self.bus_combo.currentIndex()
        checksum = sum(data) & 0xFF
        checksum = (~checksum) & 0xFF
        self.add_frame("Master", bus, frame_id, data, checksum)
        # TODO: Actually send via protocol


class WirelessStatusWidget(QWidget):
    """Widget for WiFi and Bluetooth status display."""

    # Signals for wireless control
    wifi_toggle = pyqtSignal(bool)  # enable
    wifi_mode_toggle = pyqtSignal()  # toggle AP/STA
    bt_toggle = pyqtSignal(bool)  # enable
    bt_mode_toggle = pyqtSignal()  # toggle BLE/Classic
    bt_advertise = pyqtSignal(bool)  # start/stop advertising

    def __init__(self, parent=None):
        super().__init__(parent)
        self._wifi_enabled = False
        self._bt_enabled = False
        self._bt_advertising = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(16)

        # WiFi Panel
        wifi_group = QGroupBox("WiFi")
        wifi_layout = QGridLayout(wifi_group)
        wifi_layout.setSpacing(4)

        wifi_layout.addWidget(QLabel("State:"), 0, 0)
        self.wifi_state = QLabel("OFF")
        self.wifi_state.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.wifi_state.setStyleSheet("color: #f00;")
        wifi_layout.addWidget(self.wifi_state, 0, 1)

        wifi_layout.addWidget(QLabel("Mode:"), 1, 0)
        self.wifi_mode = QLabel("-")
        wifi_layout.addWidget(self.wifi_mode, 1, 1)

        wifi_layout.addWidget(QLabel("IP:"), 2, 0)
        self.wifi_ip = QLabel("0.0.0.0")
        self.wifi_ip.setFont(QFont("Consolas", 9))
        wifi_layout.addWidget(self.wifi_ip, 2, 1)

        wifi_layout.addWidget(QLabel("RSSI:"), 3, 0)
        self.wifi_rssi = QLabel("-")
        wifi_layout.addWidget(self.wifi_rssi, 3, 1)

        wifi_layout.addWidget(QLabel("Clients:"), 4, 0)
        self.wifi_clients = QLabel("0")
        wifi_layout.addWidget(self.wifi_clients, 4, 1)

        # WiFi Controls
        wifi_btn_layout = QHBoxLayout()
        self.wifi_toggle_btn = QPushButton("Enable")
        self.wifi_toggle_btn.clicked.connect(self._toggle_wifi)
        wifi_btn_layout.addWidget(self.wifi_toggle_btn)

        self.wifi_mode_btn = QPushButton("AP Mode")
        self.wifi_mode_btn.clicked.connect(self._toggle_wifi_mode)
        wifi_btn_layout.addWidget(self.wifi_mode_btn)

        wifi_layout.addLayout(wifi_btn_layout, 5, 0, 1, 2)
        layout.addWidget(wifi_group)

        # Bluetooth Panel
        bt_group = QGroupBox("Bluetooth")
        bt_layout = QGridLayout(bt_group)
        bt_layout.setSpacing(4)

        bt_layout.addWidget(QLabel("State:"), 0, 0)
        self.bt_state = QLabel("OFF")
        self.bt_state.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.bt_state.setStyleSheet("color: #f00;")
        bt_layout.addWidget(self.bt_state, 0, 1)

        bt_layout.addWidget(QLabel("Mode:"), 1, 0)
        self.bt_mode = QLabel("-")
        bt_layout.addWidget(self.bt_mode, 1, 1)

        bt_layout.addWidget(QLabel("MAC:"), 2, 0)
        self.bt_mac = QLabel("00:00:00:00:00:00")
        self.bt_mac.setFont(QFont("Consolas", 9))
        bt_layout.addWidget(self.bt_mac, 2, 1)

        bt_layout.addWidget(QLabel("Connections:"), 3, 0)
        self.bt_connections = QLabel("0")
        bt_layout.addWidget(self.bt_connections, 3, 1)

        # Bluetooth Controls
        bt_btn_layout = QHBoxLayout()
        self.bt_toggle_btn = QPushButton("Enable")
        self.bt_toggle_btn.clicked.connect(self._toggle_bluetooth)
        bt_btn_layout.addWidget(self.bt_toggle_btn)

        self.bt_mode_btn = QPushButton("BLE Mode")
        self.bt_mode_btn.clicked.connect(self._toggle_ble_mode)
        bt_btn_layout.addWidget(self.bt_mode_btn)

        self.bt_adv_btn = QPushButton("Advertise")
        self.bt_adv_btn.clicked.connect(self._toggle_advertise)
        bt_btn_layout.addWidget(self.bt_adv_btn)

        bt_layout.addLayout(bt_btn_layout, 4, 0, 1, 2)
        layout.addWidget(bt_group)

        layout.addStretch()

    def update_wifi_status(self, state: str, mode: str, ip: str, rssi: int, clients: int):
        """Update WiFi status display."""
        self.wifi_state.setText(state)
        self.wifi_state.setStyleSheet(f"color: {'#0f0' if state == 'ON' else '#f00'};")
        self.wifi_mode.setText(mode)
        self.wifi_ip.setText(ip)
        self.wifi_rssi.setText(f"{rssi} dBm" if rssi != 0 else "-")
        self.wifi_clients.setText(str(clients))
        self.wifi_toggle_btn.setText("Disable" if state == "ON" else "Enable")

    def update_bt_status(self, state: str, mode: str, mac: str, connections: int):
        """Update Bluetooth status display."""
        self.bt_state.setText(state)
        self.bt_state.setStyleSheet(f"color: {'#0f0' if state == 'ON' else '#f00'};")
        self.bt_mode.setText(mode)
        self.bt_mac.setText(mac)
        self.bt_connections.setText(str(connections))
        self.bt_toggle_btn.setText("Disable" if state == "ON" else "Enable")

    def _toggle_wifi(self):
        self._wifi_enabled = not self._wifi_enabled
        self.wifi_toggle.emit(self._wifi_enabled)
        # Update UI immediately for responsiveness
        self.wifi_state.setText("ON" if self._wifi_enabled else "OFF")
        self.wifi_state.setStyleSheet(f"color: {'#0f0' if self._wifi_enabled else '#f00'};")
        self.wifi_toggle_btn.setText("Disable" if self._wifi_enabled else "Enable")

    def _toggle_wifi_mode(self):
        self.wifi_mode_toggle.emit()
        # Toggle AP/STA mode display
        current = self.wifi_mode.text()
        new_mode = "STA" if current == "AP" else "AP"
        self.wifi_mode.setText(new_mode)
        self.wifi_mode_btn.setText("STA Mode" if new_mode == "AP" else "AP Mode")

    def _toggle_bluetooth(self):
        self._bt_enabled = not self._bt_enabled
        self.bt_toggle.emit(self._bt_enabled)
        # Update UI immediately
        self.bt_state.setText("ON" if self._bt_enabled else "OFF")
        self.bt_state.setStyleSheet(f"color: {'#0f0' if self._bt_enabled else '#f00'};")
        self.bt_toggle_btn.setText("Disable" if self._bt_enabled else "Enable")

    def _toggle_ble_mode(self):
        self.bt_mode_toggle.emit()
        # Toggle BLE/Classic mode display
        current = self.bt_mode.text()
        new_mode = "Classic" if current == "BLE" else "BLE"
        self.bt_mode.setText(new_mode)
        self.bt_mode_btn.setText("Classic Mode" if new_mode == "BLE" else "BLE Mode")

    def _toggle_advertise(self):
        self._bt_advertising = not self._bt_advertising
        self.bt_advertise.emit(self._bt_advertising)
        self.bt_adv_btn.setText("Stop Adv" if self._bt_advertising else "Advertise")
        self.bt_adv_btn.setStyleSheet("background-color: #050;" if self._bt_advertising else "")

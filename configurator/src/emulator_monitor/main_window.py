"""
PMU-30 Emulator Monitor - Main Window

Desktop application for monitoring and controlling the PMU-30 emulator.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QStatusBar, QPushButton, QGroupBox, QGridLayout,
    QProgressBar, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QLineEdit, QFrame, QScrollArea, QToolBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QBrush
from typing import Dict, Any, Optional, List
from collections import deque
from datetime import datetime
import struct
import random

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication.protocol import MessageType, ProtocolFrame, encode_frame, decode_frame, FrameBuilder


class OutputChannelWidget(QFrame):
    """Widget for displaying a single PROFET output channel."""

    clicked = pyqtSignal(int)

    STATE_COLORS = {
        0: "#333",    # OFF
        1: "#0a0",    # ON
        2: "#f00",    # OC (Overcurrent)
        3: "#f80",    # OT (Overtemp)
        4: "#f0f",    # SC (Short Circuit)
        5: "#ff0",    # OL (Open Load)
    }

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Channel label
        self.label = QLabel(f"CH{self.channel + 1}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.label)

        # Current display
        self.current_label = QLabel("0.0A")
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_label.setFont(QFont("Segoe UI", 8))
        layout.addWidget(self.current_label)

        self.setMinimumSize(60, 50)
        self.update_state(0, 0.0, 0)

    def update_state(self, state: int, current: float, fault: int):
        """Update channel state display."""
        color = self.STATE_COLORS.get(state, "#333")
        if fault > 0:
            # Has fault - show fault color
            if fault & 1:
                color = self.STATE_COLORS[2]  # OC
            elif fault & 2:
                color = self.STATE_COLORS[3]  # OT
            elif fault & 4:
                color = self.STATE_COLORS[4]  # SC
            elif fault & 8:
                color = self.STATE_COLORS[5]  # OL

        self.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
        self.current_label.setText(f"{current:.2f}A")

    def mousePressEvent(self, event):
        self.clicked.emit(self.channel)
        super().mousePressEvent(event)


class HBridgeChannelWidget(QFrame):
    """Compact widget for displaying H-Bridge motor status (like PROFET panels)."""

    clicked = pyqtSignal(int)

    MODE_NAMES = ["COAST", "FWD", "REV", "BRAKE", "PARK", "PID"]
    MODE_COLORS = {
        0: "#333",    # COAST - dark
        1: "#0a0",    # FWD - green
        2: "#00a",    # REV - blue
        3: "#a00",    # BRAKE - red
        4: "#a0a",    # PARK - magenta
        5: "#0aa",    # PID - cyan
    }

    def __init__(self, bridge: int, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Bridge label
        self.label = QLabel(f"HB{self.bridge + 1}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(self.label)

        # Mode label
        self.mode_label = QLabel("COAST")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.mode_label)

        # PWM bar
        self.pwm_bar = QProgressBar()
        self.pwm_bar.setRange(0, 100)
        self.pwm_bar.setTextVisible(True)
        self.pwm_bar.setFormat("PWM: %v%")
        self.pwm_bar.setMaximumHeight(18)
        layout.addWidget(self.pwm_bar)

        # Current display
        self.current_label = QLabel("0.00A")
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.current_label)

        # Position bar
        self.position_bar = QProgressBar()
        self.position_bar.setRange(0, 1000)
        self.position_bar.setTextVisible(True)
        self.position_bar.setFormat("Pos: %v")
        self.position_bar.setMaximumHeight(18)
        layout.addWidget(self.position_bar)

        self.setMinimumSize(120, 130)
        self.update_state(0, 0, 0.0, 0, 0)

    def update_state(self, mode: int, pwm: int, current: float, position: int, fault: int):
        """Update H-Bridge display."""
        mode_name = self.MODE_NAMES[mode] if mode < len(self.MODE_NAMES) else "?"
        self.mode_label.setText(mode_name)
        self.pwm_bar.setValue(pwm // 10)  # PWM is 0-1000
        self.current_label.setText(f"{current:.2f}A")
        self.position_bar.setValue(position)

        # Set background color based on mode
        color = self.MODE_COLORS.get(mode, "#333")
        if fault > 0:
            color = "#f00"  # Red for fault

        self.setStyleSheet(f"QFrame {{ background-color: {color}; border-radius: 6px; }}")

    def mousePressEvent(self, event):
        self.clicked.emit(self.bridge)
        super().mousePressEvent(event)


class HBridgeWidget(QGroupBox):
    """Widget for displaying H-Bridge motor status (legacy, kept for compatibility)."""

    MODE_NAMES = ["COAST", "FWD", "REV", "BRAKE", "PARK", "PID"]

    def __init__(self, bridge: int, parent=None):
        super().__init__(f"H-Bridge {bridge + 1}", parent)
        self.bridge = bridge
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(4)

        # Mode
        layout.addWidget(QLabel("Mode:"), 0, 0)
        self.mode_label = QLabel("COAST")
        self.mode_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.mode_label, 0, 1)

        # PWM
        layout.addWidget(QLabel("PWM:"), 1, 0)
        self.pwm_bar = QProgressBar()
        self.pwm_bar.setRange(0, 100)
        self.pwm_bar.setTextVisible(True)
        self.pwm_bar.setFormat("%v%")
        layout.addWidget(self.pwm_bar, 1, 1)

        # Current
        layout.addWidget(QLabel("Current:"), 2, 0)
        self.current_label = QLabel("0.00A")
        layout.addWidget(self.current_label, 2, 1)

        # Position
        layout.addWidget(QLabel("Position:"), 3, 0)
        self.position_bar = QProgressBar()
        self.position_bar.setRange(0, 1000)
        self.position_bar.setTextVisible(True)
        self.position_bar.setFormat("%v/1000")
        layout.addWidget(self.position_bar, 3, 1)

    def update_state(self, mode: int, pwm: int, current: float, position: int, fault: int):
        """Update H-Bridge display."""
        mode_name = self.MODE_NAMES[mode] if mode < len(self.MODE_NAMES) else "?"
        self.mode_label.setText(mode_name)
        self.pwm_bar.setValue(pwm // 10)  # PWM is 0-1000
        self.current_label.setText(f"{current:.2f}A")
        self.position_bar.setValue(position)

        if fault > 0:
            self.setStyleSheet("QGroupBox { border: 2px solid red; }")
        else:
            self.setStyleSheet("")


class AnalogInputWidget(QFrame):
    """Widget for displaying analog input."""

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.setFrameStyle(QFrame.Shape.Box)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)

        self.label = QLabel(f"AIN{self.channel + 1}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 8))
        layout.addWidget(self.label)

        self.value_label = QLabel("0.00V")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.value_label)

        self.setMinimumSize(55, 40)

    def update_value(self, voltage: float):
        """Update analog input display."""
        self.value_label.setText(f"{voltage:.2f}V")
        # Color based on voltage
        if voltage > 4.0:
            color = "#f00"
        elif voltage > 2.5:
            color = "#0a0"
        elif voltage > 1.0:
            color = "#ff0"
        else:
            color = "#666"
        self.value_label.setStyleSheet(f"color: {color}")


class DigitalInputWidget(QFrame):
    """Widget for displaying digital input."""

    clicked = pyqtSignal(int)

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.setFrameStyle(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.label = QLabel(f"D{self.channel + 1}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.label)

        self.setMinimumSize(40, 35)
        self.update_state(False)

    def update_state(self, state: bool):
        """Update digital input display."""
        if state:
            self.setStyleSheet("background-color: #0a0; border-radius: 4px;")
            self.label.setText(f"D{self.channel + 1}\nHI")
        else:
            self.setStyleSheet("background-color: #333; border-radius: 4px;")
            self.label.setText(f"D{self.channel + 1}\nLO")

    def mousePressEvent(self, event):
        self.clicked.emit(self.channel)
        super().mousePressEvent(event)


class CANMonitorWidget(QWidget):
    """CAN bus monitor widget for emulator."""

    COLOR_RX = QColor('#22c55e')       # Green for received
    COLOR_TX = QColor('#3b82f6')       # Blue for transmitted

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False
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

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self._toggle_pause)
        toolbar.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("🗑 Clear")
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
        self.msg_table.setAlternatingRowColors(True)
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
        self.pause_btn.setText("▶ Resume" if checked else "⏸ Pause")

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

        # Auto-scroll
        self.msg_table.scrollToBottom()

        # Limit rows
        if self.msg_table.rowCount() > 500:
            self.msg_table.removeRow(0)

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


class WirelessStatusWidget(QWidget):
    """Widget for WiFi and Bluetooth status display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(16)

        # WiFi Panel
        wifi_group = QGroupBox("📶 WiFi")
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
        bt_group = QGroupBox("📱 Bluetooth")
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
        # TODO: Send WiFi toggle command
        pass

    def _toggle_wifi_mode(self):
        # TODO: Send WiFi mode toggle command
        pass

    def _toggle_bluetooth(self):
        # TODO: Send Bluetooth toggle command
        pass

    def _toggle_ble_mode(self):
        # TODO: Send BLE mode toggle command
        pass

    def _toggle_advertise(self):
        # TODO: Send advertise toggle command
        pass


class RealTimeGraphWidget(QWidget):
    """Real-time graph widget using pyqtgraph."""

    COLORS = [
        '#22c55e',  # Green
        '#3b82f6',  # Blue
        '#f59e0b',  # Orange
        '#ef4444',  # Red
        '#8b5cf6',  # Purple
        '#06b6d4',  # Cyan
        '#f97316',  # Dark orange
        '#ec4899',  # Pink
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._data_history: Dict[str, deque] = {}
        self._time_data: deque = deque(maxlen=500)
        self._start_time = datetime.now()

    def _setup_ui(self):
        # Set size policy to expand
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Try to import pyqtgraph
        try:
            import pyqtgraph as pg

            # Configure pyqtgraph
            pg.setConfigOptions(antialias=True, background='#1a1a1a', foreground='#ffffff')

            # Control bar
            control_layout = QHBoxLayout()

            self.pause_btn = QPushButton("⏸ Pause")
            self.pause_btn.setCheckable(True)
            self.pause_btn.clicked.connect(self._toggle_pause)
            control_layout.addWidget(self.pause_btn)

            self.clear_btn = QPushButton("🗑 Clear")
            self.clear_btn.clicked.connect(self._clear_data)
            control_layout.addWidget(self.clear_btn)

            control_layout.addWidget(QLabel("Time Window:"))
            self.time_window_spin = QSpinBox()
            self.time_window_spin.setRange(5, 120)
            self.time_window_spin.setValue(30)
            self.time_window_spin.setSuffix(" sec")
            control_layout.addWidget(self.time_window_spin)

            control_layout.addStretch()
            layout.addLayout(control_layout)

            # Create plot widget with multiple subplots
            self.graphics_layout = pg.GraphicsLayoutWidget()
            self.graphics_layout.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self.graphics_layout, 1)  # Stretch factor 1

            # Create subplots
            # Analog inputs plot
            self.analog_plot = self.graphics_layout.addPlot(row=0, col=0, title="Analog Inputs")
            self.analog_plot.setLabel('left', 'Voltage', units='V')
            self.analog_plot.setLabel('bottom', 'Time', units='s')
            self.analog_plot.showGrid(x=True, y=True, alpha=0.3)
            self.analog_plot.setYRange(0, 5)
            self.analog_curves = {}

            # Current draw plot
            self.current_plot = self.graphics_layout.addPlot(row=0, col=1, title="Output Currents")
            self.current_plot.setLabel('left', 'Current', units='A')
            self.current_plot.setLabel('bottom', 'Time', units='s')
            self.current_plot.showGrid(x=True, y=True, alpha=0.3)
            self.current_plot.setYRange(0, 20)
            self.current_curves = {}

            # H-Bridge positions plot
            self.hbridge_plot = self.graphics_layout.addPlot(row=1, col=0, title="H-Bridge Positions")
            self.hbridge_plot.setLabel('left', 'Position')
            self.hbridge_plot.setLabel('bottom', 'Time', units='s')
            self.hbridge_plot.showGrid(x=True, y=True, alpha=0.3)
            self.hbridge_plot.setYRange(0, 1000)
            self.hbridge_curves = {}

            # System plot (voltage, temp)
            self.system_plot = self.graphics_layout.addPlot(row=1, col=1, title="System Status")
            self.system_plot.setLabel('left', 'Value')
            self.system_plot.setLabel('bottom', 'Time', units='s')
            self.system_plot.showGrid(x=True, y=True, alpha=0.3)
            self.system_curves = {}

            # Add legend
            self.analog_plot.addLegend(offset=(10, 10))
            self.current_plot.addLegend(offset=(10, 10))
            self.hbridge_plot.addLegend(offset=(10, 10))
            self.system_plot.addLegend(offset=(10, 10))

            self._paused = False
            self._pg = pg

        except ImportError:
            error_label = QLabel("pyqtgraph not installed.\nInstall with: pip install pyqtgraph")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px;")
            layout.addWidget(error_label)
            self._pg = None

    def _toggle_pause(self, checked: bool):
        self._paused = checked
        self.pause_btn.setText("▶ Resume" if checked else "⏸ Pause")

    def _clear_data(self):
        self._data_history.clear()
        self._time_data.clear()
        self._start_time = datetime.now()

        # Clear all curves
        for curves_dict in [self.analog_curves, self.current_curves,
                           self.hbridge_curves, self.system_curves]:
            for curve in curves_dict.values():
                curve.setData([], [])

    def add_data_point(self, category: str, name: str, value: float):
        """Add a data point to the graph."""
        if self._pg is None or self._paused:
            return

        # Calculate time offset
        now = datetime.now()
        time_offset = (now - self._start_time).total_seconds()

        # Store data
        key = f"{category}:{name}"
        if key not in self._data_history:
            self._data_history[key] = deque(maxlen=500)
        self._data_history[key].append((time_offset, value))

        # Get or create curve
        curve = self._get_or_create_curve(category, name)
        if curve:
            times = [p[0] for p in self._data_history[key]]
            values = [p[1] for p in self._data_history[key]]
            curve.setData(times, values)

            # Update x-axis range
            window = self.time_window_spin.value()
            min_time = max(0, time_offset - window)
            self._update_x_ranges(min_time, time_offset)

    def _get_or_create_curve(self, category: str, name: str):
        """Get existing curve or create new one."""
        if self._pg is None:
            return None

        curves_dict = {
            'analog': self.analog_curves,
            'current': self.current_curves,
            'hbridge': self.hbridge_curves,
            'system': self.system_curves,
        }.get(category)

        if curves_dict is None:
            return None

        if name not in curves_dict:
            plot = {
                'analog': self.analog_plot,
                'current': self.current_plot,
                'hbridge': self.hbridge_plot,
                'system': self.system_plot,
            }.get(category)

            color_idx = len(curves_dict) % len(self.COLORS)
            pen = self._pg.mkPen(color=self.COLORS[color_idx], width=2)
            curves_dict[name] = plot.plot([], [], pen=pen, name=name)

        return curves_dict[name]

    def _update_x_ranges(self, min_time: float, max_time: float):
        """Update x-axis range for all plots."""
        for plot in [self.analog_plot, self.current_plot,
                    self.hbridge_plot, self.system_plot]:
            plot.setXRange(min_time, max_time, padding=0)


class EmulatorMonitorWindow(QMainWindow):
    """Main window for the emulator monitor."""

    telemetry_received = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PMU-30 Emulator Monitor")
        self.setMinimumSize(1200, 800)

        # Connection state
        self.socket = None
        self.connected = False
        self.rx_buffer = b""

        # Telemetry data
        self.telemetry_data: Dict[str, Any] = {}

        self._setup_ui()
        self._setup_timers()

        # Connect to emulator on startup
        QTimer.singleShot(100, self._connect_to_emulator)

    def _setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # Connection bar
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("Emulator:"))
        self.host_edit = QLineEdit("localhost")
        self.host_edit.setMaximumWidth(120)
        conn_layout.addWidget(self.host_edit)
        conn_layout.addWidget(QLabel(":"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(9876)
        self.port_spin.setMaximumWidth(80)
        conn_layout.addWidget(self.port_spin)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connection)
        conn_layout.addWidget(self.connect_btn)

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        conn_layout.addWidget(self.status_label)
        conn_layout.addStretch()

        # System info
        self.voltage_label = QLabel("12.0V")
        self.voltage_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        conn_layout.addWidget(QLabel("Battery:"))
        conn_layout.addWidget(self.voltage_label)

        self.temp_label = QLabel("25°C")
        self.temp_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        conn_layout.addWidget(QLabel("Temp:"))
        conn_layout.addWidget(self.temp_label)

        layout.addLayout(conn_layout)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs
        self._create_outputs_tab()
        self._create_hbridge_tab()
        self._create_inputs_tab()
        self._create_wireless_tab()
        self._create_can_monitor_tab()
        self._create_graphs_tab()
        self._create_control_tab()

        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_outputs_tab(self):
        """Create PROFET outputs tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # PROFET grid (10x3)
        grid_group = QGroupBox("PROFET Outputs (30 channels)")
        grid_layout = QGridLayout(grid_group)
        grid_layout.setSpacing(4)

        self.output_widgets = []
        for i in range(30):
            row = i // 10
            col = i % 10
            w = OutputChannelWidget(i)
            w.clicked.connect(self._on_output_clicked)
            grid_layout.addWidget(w, row, col)
            self.output_widgets.append(w)

        layout.addWidget(grid_group)
        layout.addStretch()

        self.tabs.addTab(widget, "Outputs")

    def _create_hbridge_tab(self):
        """Create H-Bridge tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # H-Bridge grid (2x2 layout)
        grid_group = QGroupBox("H-Bridge Motors (4 channels)")
        grid_layout = QGridLayout(grid_group)
        grid_layout.setSpacing(8)

        self.hbridge_widgets = []
        for i in range(4):
            row = i // 2
            col = i % 2
            w = HBridgeChannelWidget(i)
            w.clicked.connect(self._on_hbridge_clicked)
            grid_layout.addWidget(w, row, col)
            self.hbridge_widgets.append(w)

        layout.addWidget(grid_group)
        layout.addStretch()

        self.tabs.addTab(widget, "H-Bridge")

    def _create_inputs_tab(self):
        """Create inputs tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Analog inputs
        analog_group = QGroupBox("Analog Inputs")
        analog_layout = QGridLayout(analog_group)

        self.analog_widgets = []
        for i in range(16):
            row = i // 8
            col = i % 8
            w = AnalogInputWidget(i)
            analog_layout.addWidget(w, row, col)
            self.analog_widgets.append(w)

        layout.addWidget(analog_group)

        # Digital inputs
        digital_group = QGroupBox("Digital Inputs (click to toggle)")
        digital_layout = QGridLayout(digital_group)

        self.digital_widgets = []
        for i in range(20):
            row = i // 10
            col = i % 10
            w = DigitalInputWidget(i)
            w.clicked.connect(self._on_digital_clicked)
            digital_layout.addWidget(w, row, col)
            self.digital_widgets.append(w)

        layout.addWidget(digital_group)
        layout.addStretch()

        self.tabs.addTab(widget, "Inputs")

    def _create_wireless_tab(self):
        """Create WiFi/Bluetooth status tab."""
        self.wireless_widget = WirelessStatusWidget()
        self.tabs.addTab(self.wireless_widget, "Wireless")

    def _create_can_monitor_tab(self):
        """Create CAN monitor tab."""
        self.can_monitor = CANMonitorWidget()
        self.tabs.addTab(self.can_monitor, "CAN Monitor")

    def _create_graphs_tab(self):
        """Create real-time graphs tab."""
        self.graphs_widget = RealTimeGraphWidget()
        self.tabs.addTab(self.graphs_widget, "Graphs")

    def _create_control_tab(self):
        """Create control/injection tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Fault injection
        fault_group = QGroupBox("Fault Injection")
        fault_layout = QGridLayout(fault_group)

        fault_layout.addWidget(QLabel("Channel:"), 0, 0)
        self.fault_channel_spin = QSpinBox()
        self.fault_channel_spin.setRange(1, 30)
        fault_layout.addWidget(self.fault_channel_spin, 0, 1)

        self.inject_oc_btn = QPushButton("Inject OC")
        self.inject_oc_btn.clicked.connect(lambda: self._inject_fault(1))
        fault_layout.addWidget(self.inject_oc_btn, 0, 2)

        self.inject_ot_btn = QPushButton("Inject OT")
        self.inject_ot_btn.clicked.connect(lambda: self._inject_fault(2))
        fault_layout.addWidget(self.inject_ot_btn, 0, 3)

        self.inject_sc_btn = QPushButton("Inject SC")
        self.inject_sc_btn.clicked.connect(lambda: self._inject_fault(4))
        fault_layout.addWidget(self.inject_sc_btn, 0, 4)

        self.inject_ol_btn = QPushButton("Inject OL")
        self.inject_ol_btn.clicked.connect(lambda: self._inject_fault(8))
        fault_layout.addWidget(self.inject_ol_btn, 0, 5)

        self.clear_fault_btn = QPushButton("Clear Fault")
        self.clear_fault_btn.clicked.connect(self._clear_fault)
        fault_layout.addWidget(self.clear_fault_btn, 0, 6)

        layout.addWidget(fault_group)

        # System control
        sys_group = QGroupBox("System Control")
        sys_layout = QGridLayout(sys_group)

        sys_layout.addWidget(QLabel("Battery Voltage (mV):"), 0, 0)
        self.voltage_spin = QSpinBox()
        self.voltage_spin.setRange(6000, 18000)
        self.voltage_spin.setValue(12000)
        self.voltage_spin.setSingleStep(100)
        sys_layout.addWidget(self.voltage_spin, 0, 1)

        self.set_voltage_btn = QPushButton("Set")
        self.set_voltage_btn.clicked.connect(self._set_voltage)
        sys_layout.addWidget(self.set_voltage_btn, 0, 2)

        sys_layout.addWidget(QLabel("Temperature (°C):"), 1, 0)
        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(-40, 150)
        self.temp_spin.setValue(25)
        sys_layout.addWidget(self.temp_spin, 1, 1)

        self.set_temp_btn = QPushButton("Set")
        self.set_temp_btn.clicked.connect(self._set_temperature)
        sys_layout.addWidget(self.set_temp_btn, 1, 2)

        self.restart_btn = QPushButton("Restart Emulator")
        self.restart_btn.setStyleSheet("background-color: #c50;")
        self.restart_btn.clicked.connect(self._restart_emulator)
        sys_layout.addWidget(self.restart_btn, 2, 0, 1, 3)

        layout.addWidget(sys_group)
        layout.addStretch()

        self.tabs.addTab(widget, "Control")

    def _setup_timers(self):
        """Setup update timers."""
        # Telemetry request timer
        self.telem_timer = QTimer(self)
        self.telem_timer.timeout.connect(self._request_telemetry)

        # Socket read timer
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self._read_socket)

        # Demo CAN traffic timer (simulates CAN bus activity)
        self._demo_can_counter = 0
        self.demo_can_timer = QTimer(self)
        self.demo_can_timer.timeout.connect(self._generate_demo_can)

    def _connect_to_emulator(self):
        """Connect to the emulator."""
        import socket

        host = self.host_edit.text()
        port = self.port_spin.value()

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2.0)
            self.socket.connect((host, port))
            self.socket.setblocking(False)

            self.connected = True
            self.status_label.setText(f"Connected to {host}:{port}")
            self.status_label.setStyleSheet("color: green;")
            self.connect_btn.setText("Disconnect")

            # Subscribe to telemetry
            frame = FrameBuilder.subscribe_telemetry(50)
            self._send_frame(frame)

            # Start timers
            self.telem_timer.start(100)  # 10 Hz request
            self.read_timer.start(20)    # 50 Hz read
            self.demo_can_timer.start(50)  # 20 Hz demo CAN traffic

            self.statusBar().showMessage(f"Connected to emulator at {host}:{port}")

        except Exception as e:
            self.statusBar().showMessage(f"Connection failed: {e}")
            self.socket = None

    def _disconnect(self):
        """Disconnect from emulator."""
        if self.socket:
            try:
                # Unsubscribe from telemetry
                frame = FrameBuilder.unsubscribe_telemetry()
                self._send_frame(frame)
            except:
                pass

            try:
                self.socket.close()
            except:
                pass

        self.socket = None
        self.connected = False
        self.telem_timer.stop()
        self.read_timer.stop()
        self.demo_can_timer.stop()

        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        self.connect_btn.setText("Connect")

    def _toggle_connection(self):
        """Toggle connection state."""
        if self.connected:
            self._disconnect()
        else:
            self._connect_to_emulator()

    def _send_frame(self, frame: ProtocolFrame):
        """Send a protocol frame."""
        if self.socket and self.connected:
            try:
                data = encode_frame(frame)
                self.socket.sendall(data)
            except Exception as e:
                self.statusBar().showMessage(f"Send error: {e}")
                self._disconnect()

    def _read_socket(self):
        """Read data from socket."""
        if not self.socket or not self.connected:
            return

        try:
            data = self.socket.recv(4096)
            if data:
                self.rx_buffer += data
                self._process_buffer()
        except BlockingIOError:
            pass  # No data available
        except Exception as e:
            self.statusBar().showMessage(f"Read error: {e}")
            self._disconnect()

    def _process_buffer(self):
        """Process received data buffer."""
        while len(self.rx_buffer) >= 6:  # Minimum frame size
            try:
                frame, consumed = decode_frame(self.rx_buffer)
                if frame:
                    self.rx_buffer = self.rx_buffer[consumed:]
                    self._handle_frame(frame)
                elif consumed > 0:
                    self.rx_buffer = self.rx_buffer[consumed:]
                else:
                    break  # Need more data
            except Exception as e:
                # Skip bad byte and try again
                self.rx_buffer = self.rx_buffer[1:]

    def _handle_frame(self, frame: ProtocolFrame):
        """Handle received protocol frame."""
        if frame.msg_type == MessageType.TELEMETRY_DATA:
            self._handle_telemetry(frame.payload)
        elif frame.msg_type == MessageType.PONG:
            pass  # Ping response
        elif frame.msg_type == MessageType.ERROR:
            self.statusBar().showMessage(f"Error from emulator")

    def _handle_telemetry(self, payload: bytes):
        """Handle telemetry data."""
        if len(payload) < 100:
            return

        try:
            offset = 0

            # Parse voltage and temperature
            voltage_mv, temp = struct.unpack_from("<Hh", payload, offset)
            offset += 4

            voltage_v = voltage_mv / 1000.0
            self.voltage_label.setText(f"{voltage_v:.1f}V")
            self.temp_label.setText(f"{temp}°C")

            # Update system graphs
            if hasattr(self, 'graphs_widget'):
                self.graphs_widget.add_data_point('system', 'Voltage', voltage_v)
                self.graphs_widget.add_data_point('system', 'Temp', temp)

            # Parse PROFET outputs (30 channels, 6 bytes each)
            for i in range(30):
                if offset + 6 > len(payload):
                    break
                state, current, fault, pwm = struct.unpack_from("<BHBh", payload, offset)
                offset += 6
                current_a = current / 1000.0
                self.output_widgets[i].update_state(state, current_a, fault)

                # Update current graph for first 4 channels
                if i < 4 and hasattr(self, 'graphs_widget'):
                    self.graphs_widget.add_data_point('current', f'CH{i+1}', current_a)

            # Parse H-Bridge (4 bridges)
            for i in range(4):
                if offset + 8 > len(payload):
                    break
                mode, state, pwm, current, position, fault = struct.unpack_from("<BBHhHB", payload, offset)
                offset += 9
                current_a = current / 1000.0
                if i < len(self.hbridge_widgets):
                    self.hbridge_widgets[i].update_state(mode, pwm, current_a, position, fault)

                # Update H-Bridge position graph
                if hasattr(self, 'graphs_widget'):
                    self.graphs_widget.add_data_point('hbridge', f'HB{i+1}', position)

            # Parse analog inputs
            for i in range(16):
                if offset + 2 > len(payload):
                    break
                raw_value, = struct.unpack_from("<H", payload, offset)
                offset += 2
                voltage = raw_value * 3.3 / 4095
                if i < len(self.analog_widgets):
                    self.analog_widgets[i].update_value(voltage)

                # Update analog graph for first 4 channels
                if i < 4 and hasattr(self, 'graphs_widget'):
                    self.graphs_widget.add_data_point('analog', f'AIN{i+1}', voltage)

            # Parse digital inputs
            if offset + 4 <= len(payload):
                di_states, = struct.unpack_from("<I", payload, offset)
                offset += 4
                for i in range(20):
                    if i < len(self.digital_widgets):
                        self.digital_widgets[i].update_state(bool(di_states & (1 << i)))

        except Exception as e:
            pass  # Ignore parsing errors

    def _request_telemetry(self):
        """Request telemetry update."""
        if self.connected:
            frame = FrameBuilder.ping()
            self._send_frame(frame)

    def _generate_demo_can(self):
        """Generate demo CAN traffic for testing."""
        import random

        self._demo_can_counter += 1

        # Simulate various CAN messages
        demo_messages = [
            # Engine RPM (varies)
            (0x100, struct.pack("<HHxxxx", 3000 + random.randint(-200, 200), 0)),
            # Vehicle speed
            (0x101, struct.pack("<HHxxxx", 60 + random.randint(-5, 5), 0)),
            # Coolant temp
            (0x102, struct.pack("<BBxxxxxx", 85, 0)),
            # Oil pressure
            (0x103, struct.pack("<HHxxxx", 350, 0)),
            # Throttle position
            (0x104, struct.pack("<BBxxxxxx", random.randint(10, 90), 0)),
            # Fuel level
            (0x110, struct.pack("<BBxxxxxx", 75, 0)),
            # Battery voltage
            (0x111, struct.pack("<HHxxxx", 13800 + random.randint(-100, 100), 0)),
            # Gear position
            (0x120, struct.pack("<BBxxxxxx", random.randint(1, 6), 0)),
        ]

        # Pick a random message to send
        idx = self._demo_can_counter % len(demo_messages)
        arb_id, data = demo_messages[idx]

        # Add to CAN monitor as received message
        if hasattr(self, 'can_monitor'):
            bus = random.randint(0, 1)  # Random bus 0 or 1
            self.can_monitor.add_message("RX", bus, arb_id, data)

    def _on_output_clicked(self, channel: int):
        """Handle output channel click."""
        self.fault_channel_spin.setValue(channel + 1)
        self.tabs.setCurrentIndex(6)  # Switch to control tab

    def _on_hbridge_clicked(self, bridge: int):
        """Handle H-Bridge click."""
        self.statusBar().showMessage(f"H-Bridge {bridge + 1} selected")
        self.tabs.setCurrentIndex(6)  # Switch to control tab

    def _on_digital_clicked(self, channel: int):
        """Handle digital input click - toggle state."""
        # TODO: Send command to toggle digital input
        self.statusBar().showMessage(f"Toggle DI{channel + 1}")

    def _inject_fault(self, fault_type: int):
        """Inject fault into channel."""
        channel = self.fault_channel_spin.value() - 1
        # TODO: Send fault injection command
        self.statusBar().showMessage(f"Inject fault 0x{fault_type:02X} into CH{channel + 1}")

    def _clear_fault(self):
        """Clear fault from channel."""
        channel = self.fault_channel_spin.value() - 1
        # TODO: Send clear fault command
        self.statusBar().showMessage(f"Clear fault from CH{channel + 1}")

    def _set_voltage(self):
        """Set battery voltage."""
        voltage = self.voltage_spin.value()
        # TODO: Send voltage command
        self.statusBar().showMessage(f"Set voltage to {voltage}mV")

    def _set_temperature(self):
        """Set temperature."""
        temp = self.temp_spin.value()
        # TODO: Send temperature command
        self.statusBar().showMessage(f"Set temperature to {temp}°C")

    def _restart_emulator(self):
        """Restart emulator."""
        # TODO: Send restart command
        self.statusBar().showMessage("Restarting emulator...")

    def closeEvent(self, event):
        """Handle window close."""
        self._disconnect()
        event.accept()

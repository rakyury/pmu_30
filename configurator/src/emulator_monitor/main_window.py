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
    QLineEdit, QFrame, QScrollArea, QToolBar, QSizePolicy, QDialog,
    QSlider, QFileDialog, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QBrush
from typing import Dict, Any, Optional, List
from collections import deque
from datetime import datetime
import struct
import random
import json

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication.protocol import MessageType, ProtocolFrame, encode_frame, decode_frame, FrameBuilder
from communication.telemetry import parse_telemetry, TELEMETRY_PACKET_SIZE


class OutputChannelWidget(QFrame):
    """Widget for displaying a single PROFET output channel."""

    clicked = pyqtSignal(int)

    STATE_COLORS = {
        0: "#333",    # OFF
        1: "#0a0",    # ON
        2: "#f00",    # OC (Overcurrent)
        3: "#f80",    # OT (Overtemp)
        4: "#f0f",    # SC (Short Circuit)
        5: "#ffa500",    # OL (Open Load) - orange for readability
    }

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._last_color = None
        self._last_current = None
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

        # Only update if changed
        if color != self._last_color:
            self.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            self._last_color = color

        current_text = f"{current:.2f}A"
        if current_text != self._last_current:
            self.current_label.setText(current_text)
            self._last_current = current_text

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
        self._last_color = None
        self._last_mode = None
        self._last_pwm = None
        self._last_current = None
        self._last_position = None
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
        # Only update changed values
        mode_name = self.MODE_NAMES[mode] if mode < len(self.MODE_NAMES) else "?"
        if mode_name != self._last_mode:
            self.mode_label.setText(mode_name)
            self._last_mode = mode_name

        pwm_val = pwm // 10
        if pwm_val != self._last_pwm:
            self.pwm_bar.setValue(pwm_val)
            self._last_pwm = pwm_val

        current_text = f"{current:.2f}A"
        if current_text != self._last_current:
            self.current_label.setText(current_text)
            self._last_current = current_text

        if position != self._last_position:
            self.position_bar.setValue(position)
            self._last_position = position

        # Set background color based on mode
        color = self.MODE_COLORS.get(mode, "#333")
        if fault > 0:
            color = "#f00"  # Red for fault

        if color != self._last_color:
            self.setStyleSheet(f"QFrame {{ background-color: {color}; border-radius: 6px; }}")
            self._last_color = color

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

    clicked = pyqtSignal(int)

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._last_voltage_text = None
        self._last_active = None
        self.setFrameStyle(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
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
        voltage_text = f"{voltage:.2f}V"
        if voltage_text != self._last_voltage_text:
            self.value_label.setText(voltage_text)
            self._last_voltage_text = voltage_text

        # Background color based on voltage (like digital inputs)
        is_active = voltage > 0.5
        if is_active != self._last_active:
            if is_active:
                self.setStyleSheet("background-color: #0a0; border-radius: 4px;")
                self.value_label.setStyleSheet("color: white;")
            else:
                self.setStyleSheet("background-color: #333; border-radius: 4px;")
                self.value_label.setStyleSheet("color: #888;")
            self._last_active = is_active

    def mousePressEvent(self, event):
        self.clicked.emit(self.channel)
        super().mousePressEvent(event)


class DigitalInputWidget(QFrame):
    """Widget for displaying digital input."""

    clicked = pyqtSignal(int)

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._last_state = None
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
        if state == self._last_state:
            return
        self._last_state = state

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

        self.pause_btn = QPushButton("▶ Resume")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setChecked(True)  # Start checked (paused)
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

        self.pause_btn = QPushButton("▶ Resume")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setChecked(True)  # Start checked (paused)
        self.pause_btn.clicked.connect(self._toggle_pause)
        toolbar.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("🗑 Clear")
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
        self.pause_btn.setText("▶ Resume" if checked else "⏸ Pause")

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


class AnalogInputDialog(QDialog):
    """Dialog for configuring analog input simulation."""

    set_voltage = pyqtSignal(int, float)  # channel, voltage

    def __init__(self, channel: int, current_voltage: float = 0.0, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.setWindowTitle(f"Analog Input AIN{channel + 1}")
        self.setMinimumWidth(300)
        self._setup_ui(current_voltage)

    def _setup_ui(self, current_voltage: float):
        layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(f"Configure simulated voltage for AIN{self.channel + 1}")
        layout.addWidget(info_label)

        # Voltage slider
        voltage_group = QGroupBox("Voltage")
        voltage_layout = QGridLayout(voltage_group)

        voltage_layout.addWidget(QLabel("Value:"), 0, 0)
        self.voltage_slider = QSlider(Qt.Orientation.Horizontal)
        self.voltage_slider.setRange(0, 500)  # 0.00V to 5.00V
        self.voltage_slider.setValue(int(current_voltage * 100))
        self.voltage_slider.valueChanged.connect(self._on_voltage_changed)
        voltage_layout.addWidget(self.voltage_slider, 0, 1)

        self.voltage_label = QLabel(f"{current_voltage:.2f}V")
        self.voltage_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.voltage_label.setMinimumWidth(60)
        voltage_layout.addWidget(self.voltage_label, 0, 2)

        # Quick presets
        presets_layout = QHBoxLayout()
        for v in [0.0, 1.0, 2.5, 3.3, 5.0]:
            btn = QPushButton(f"{v}V")
            btn.clicked.connect(lambda checked, val=v: self._set_preset(val))
            presets_layout.addWidget(btn)
        voltage_layout.addLayout(presets_layout, 1, 0, 1, 3)

        layout.addWidget(voltage_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(self.apply_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _on_voltage_changed(self, value: int):
        voltage = value / 100.0
        self.voltage_label.setText(f"{voltage:.2f}V")

    def _set_preset(self, voltage: float):
        self.voltage_slider.setValue(int(voltage * 100))

    def _apply(self):
        voltage = self.voltage_slider.value() / 100.0
        self.set_voltage.emit(self.channel, voltage)


class DigitalInputDialog(QDialog):
    """Dialog for configuring digital input simulation."""

    set_state = pyqtSignal(int, bool)  # channel, state

    def __init__(self, channel: int, current_state: bool = False, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.current_state = current_state
        self.setWindowTitle(f"Digital Input DI{channel + 1}")
        self.setMinimumWidth(250)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(f"Configure simulated state for DI{self.channel + 1}")
        layout.addWidget(info_label)

        # State group
        state_group = QGroupBox("State")
        state_layout = QHBoxLayout(state_group)

        self.low_btn = QPushButton("LOW")
        self.low_btn.setCheckable(True)
        self.low_btn.setChecked(not self.current_state)
        self.low_btn.clicked.connect(lambda: self._set_state(False))
        self.low_btn.setStyleSheet("QPushButton:checked { background-color: #333; }")
        state_layout.addWidget(self.low_btn)

        self.high_btn = QPushButton("HIGH")
        self.high_btn.setCheckable(True)
        self.high_btn.setChecked(self.current_state)
        self.high_btn.clicked.connect(lambda: self._set_state(True))
        self.high_btn.setStyleSheet("QPushButton:checked { background-color: #0a0; }")
        state_layout.addWidget(self.high_btn)

        layout.addWidget(state_group)

        # Pulse buttons
        pulse_group = QGroupBox("Pulse")
        pulse_layout = QHBoxLayout(pulse_group)

        for duration in [100, 500, 1000]:
            btn = QPushButton(f"{duration}ms")
            btn.clicked.connect(lambda checked, d=duration: self._pulse(d))
            pulse_layout.addWidget(btn)

        layout.addWidget(pulse_group)

        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

    def _set_state(self, state: bool):
        self.low_btn.setChecked(not state)
        self.high_btn.setChecked(state)
        self.current_state = state
        self.set_state.emit(self.channel, state)

    def _pulse(self, duration_ms: int):
        # Send HIGH, then schedule LOW
        self.set_state.emit(self.channel, True)
        self._set_state(True)
        QTimer.singleShot(duration_ms, lambda: self._set_state(False))


class ControlDialog(QDialog):
    """Control dialog for fault injection and system settings."""

    # Signals for commands
    inject_fault = pyqtSignal(int, int)  # channel, fault_type
    clear_fault = pyqtSignal(int)  # channel
    set_voltage = pyqtSignal(int)  # voltage_mv
    set_temperature = pyqtSignal(int)  # temp_c
    set_channel_state = pyqtSignal(int, bool, int)  # channel, on, pwm
    set_hbridge = pyqtSignal(int, int, int)  # bridge, mode, pwm
    restart_emulator = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Emulator Control")
        self.setMinimumSize(500, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ===== Channel Control =====
        channel_group = QGroupBox("Channel Control")
        channel_layout = QGridLayout(channel_group)

        channel_layout.addWidget(QLabel("Channel:"), 0, 0)
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(1, 30)
        channel_layout.addWidget(self.channel_spin, 0, 1)

        self.channel_on_btn = QPushButton("Turn ON")
        self.channel_on_btn.clicked.connect(self._turn_channel_on)
        channel_layout.addWidget(self.channel_on_btn, 0, 2)

        self.channel_off_btn = QPushButton("Turn OFF")
        self.channel_off_btn.clicked.connect(self._turn_channel_off)
        channel_layout.addWidget(self.channel_off_btn, 0, 3)

        channel_layout.addWidget(QLabel("PWM %:"), 1, 0)
        self.pwm_slider = QSlider(Qt.Orientation.Horizontal)
        self.pwm_slider.setRange(0, 100)
        self.pwm_slider.setValue(100)
        channel_layout.addWidget(self.pwm_slider, 1, 1, 1, 2)

        self.pwm_label = QLabel("100%")
        self.pwm_slider.valueChanged.connect(lambda v: self.pwm_label.setText(f"{v}%"))
        channel_layout.addWidget(self.pwm_label, 1, 3)

        layout.addWidget(channel_group)

        # ===== Fault Injection =====
        fault_group = QGroupBox("Fault Injection")
        fault_layout = QGridLayout(fault_group)

        fault_layout.addWidget(QLabel("Channel:"), 0, 0)
        self.fault_channel_spin = QSpinBox()
        self.fault_channel_spin.setRange(1, 30)
        fault_layout.addWidget(self.fault_channel_spin, 0, 1)

        fault_btns = QHBoxLayout()
        self.inject_oc_btn = QPushButton("OC")
        self.inject_oc_btn.setToolTip("Overcurrent")
        self.inject_oc_btn.clicked.connect(lambda: self._inject_fault(1))
        fault_btns.addWidget(self.inject_oc_btn)

        self.inject_ot_btn = QPushButton("OT")
        self.inject_ot_btn.setToolTip("Overtemperature")
        self.inject_ot_btn.clicked.connect(lambda: self._inject_fault(2))
        fault_btns.addWidget(self.inject_ot_btn)

        self.inject_sc_btn = QPushButton("SC")
        self.inject_sc_btn.setToolTip("Short Circuit")
        self.inject_sc_btn.clicked.connect(lambda: self._inject_fault(4))
        fault_btns.addWidget(self.inject_sc_btn)

        self.inject_ol_btn = QPushButton("OL")
        self.inject_ol_btn.setToolTip("Open Load")
        self.inject_ol_btn.clicked.connect(lambda: self._inject_fault(8))
        fault_btns.addWidget(self.inject_ol_btn)

        self.clear_fault_btn = QPushButton("Clear")
        self.clear_fault_btn.setStyleSheet("background-color: #050;")
        self.clear_fault_btn.clicked.connect(self._clear_fault)
        fault_btns.addWidget(self.clear_fault_btn)

        fault_layout.addLayout(fault_btns, 0, 2, 1, 4)
        layout.addWidget(fault_group)

        # ===== H-Bridge Control =====
        hbridge_group = QGroupBox("H-Bridge Control")
        hbridge_layout = QGridLayout(hbridge_group)

        hbridge_layout.addWidget(QLabel("Bridge:"), 0, 0)
        self.bridge_combo = QComboBox()
        self.bridge_combo.addItems(["HB1", "HB2", "HB3", "HB4"])
        hbridge_layout.addWidget(self.bridge_combo, 0, 1)

        hbridge_layout.addWidget(QLabel("Mode:"), 0, 2)
        self.hb_mode_combo = QComboBox()
        self.hb_mode_combo.addItems(["COAST", "FORWARD", "REVERSE", "BRAKE", "PARK", "PID"])
        hbridge_layout.addWidget(self.hb_mode_combo, 0, 3)

        hbridge_layout.addWidget(QLabel("PWM %:"), 1, 0)
        self.hb_pwm_slider = QSlider(Qt.Orientation.Horizontal)
        self.hb_pwm_slider.setRange(0, 100)
        self.hb_pwm_slider.setValue(50)
        hbridge_layout.addWidget(self.hb_pwm_slider, 1, 1, 1, 2)

        self.hb_pwm_label = QLabel("50%")
        self.hb_pwm_slider.valueChanged.connect(lambda v: self.hb_pwm_label.setText(f"{v}%"))
        hbridge_layout.addWidget(self.hb_pwm_label, 1, 3)

        self.hb_apply_btn = QPushButton("Apply")
        self.hb_apply_btn.clicked.connect(self._apply_hbridge)
        hbridge_layout.addWidget(self.hb_apply_btn, 2, 0, 1, 4)

        layout.addWidget(hbridge_group)

        # ===== System Control =====
        sys_group = QGroupBox("System Control")
        sys_layout = QGridLayout(sys_group)

        sys_layout.addWidget(QLabel("Battery Voltage:"), 0, 0)
        self.voltage_spin = QSpinBox()
        self.voltage_spin.setRange(6000, 18000)
        self.voltage_spin.setValue(12000)
        self.voltage_spin.setSingleStep(100)
        self.voltage_spin.setSuffix(" mV")
        sys_layout.addWidget(self.voltage_spin, 0, 1)

        self.set_voltage_btn = QPushButton("Set")
        self.set_voltage_btn.clicked.connect(self._set_voltage)
        sys_layout.addWidget(self.set_voltage_btn, 0, 2)

        sys_layout.addWidget(QLabel("Temperature:"), 1, 0)
        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(-40, 150)
        self.temp_spin.setValue(25)
        self.temp_spin.setSuffix(" °C")
        sys_layout.addWidget(self.temp_spin, 1, 1)

        self.set_temp_btn = QPushButton("Set")
        self.set_temp_btn.clicked.connect(self._set_temperature)
        sys_layout.addWidget(self.set_temp_btn, 1, 2)

        layout.addWidget(sys_group)

        # ===== Restart =====
        self.restart_btn = QPushButton("🔄 Restart Emulator")
        self.restart_btn.setStyleSheet("background-color: #c50; font-weight: bold; padding: 8px;")
        self.restart_btn.clicked.connect(self._restart)
        layout.addWidget(self.restart_btn)

        layout.addStretch()

    def _turn_channel_on(self):
        ch = self.channel_spin.value() - 1
        pwm = self.pwm_slider.value() * 10  # 0-1000
        self.set_channel_state.emit(ch, True, pwm)

    def _turn_channel_off(self):
        ch = self.channel_spin.value() - 1
        self.set_channel_state.emit(ch, False, 0)

    def _inject_fault(self, fault_type: int):
        ch = self.fault_channel_spin.value() - 1
        self.inject_fault.emit(ch, fault_type)

    def _clear_fault(self):
        ch = self.fault_channel_spin.value() - 1
        self.clear_fault.emit(ch)

    def _apply_hbridge(self):
        bridge = self.bridge_combo.currentIndex()
        mode = self.hb_mode_combo.currentIndex()
        pwm = self.hb_pwm_slider.value() * 10  # 0-1000
        self.set_hbridge.emit(bridge, mode, pwm)

    def _set_voltage(self):
        self.set_voltage.emit(self.voltage_spin.value())

    def _set_temperature(self):
        self.set_temperature.emit(self.temp_spin.value())

    def _restart(self):
        self.restart_emulator.emit()


class ScenarioEditorWidget(QWidget):
    """Scenario editor for creating and running test sequences."""

    # Signal emitted when a scenario action should be executed
    execute_action = pyqtSignal(dict)  # action dict

    ACTION_TYPES = [
        "Set Output",
        "Set H-Bridge",
        "Set Digital Input",
        "Set Voltage",
        "Set Temperature",
        "Inject Fault",
        "Clear Fault",
        "Wait",
        "Send CAN",
        "Send LIN",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scenario_steps: List[dict] = []
        self._running = False
        self._paused = False
        self._current_step = 0
        self._step_timer = QTimer(self)
        self._step_timer.timeout.connect(self._execute_next_step)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Left side - Step list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._new_scenario)
        toolbar.addWidget(self.new_btn)

        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self._load_scenario)
        toolbar.addWidget(self.load_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_scenario)
        toolbar.addWidget(self.save_btn)

        toolbar.addStretch()
        left_layout.addLayout(toolbar)

        # Steps list
        self.steps_list = QListWidget()
        self.steps_list.setFont(QFont("Consolas", 10))
        self.steps_list.itemSelectionChanged.connect(self._on_step_selected)
        self.steps_list.itemDoubleClicked.connect(self._edit_step)
        left_layout.addWidget(self.steps_list)

        # Step management buttons
        step_btns = QHBoxLayout()

        self.add_btn = QPushButton("+ Add")
        self.add_btn.clicked.connect(self._add_step)
        step_btns.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_step)
        self.edit_btn.setEnabled(False)
        step_btns.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_step)
        self.delete_btn.setEnabled(False)
        step_btns.addWidget(self.delete_btn)

        self.move_up_btn = QPushButton("↑")
        self.move_up_btn.setMaximumWidth(30)
        self.move_up_btn.clicked.connect(self._move_step_up)
        self.move_up_btn.setEnabled(False)
        step_btns.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("↓")
        self.move_down_btn.setMaximumWidth(30)
        self.move_down_btn.clicked.connect(self._move_step_down)
        self.move_down_btn.setEnabled(False)
        step_btns.addWidget(self.move_down_btn)

        left_layout.addLayout(step_btns)

        # Playback controls
        playback_group = QGroupBox("Playback")
        playback_layout = QHBoxLayout(playback_group)

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self._toggle_playback)
        playback_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self._stop_playback)
        self.stop_btn.setEnabled(False)
        playback_layout.addWidget(self.stop_btn)

        self.loop_check = QCheckBox("Loop")
        playback_layout.addWidget(self.loop_check)

        left_layout.addWidget(playback_group)

        # Progress
        self.progress_label = QLabel("Step: 0 / 0")
        left_layout.addWidget(self.progress_label)

        layout.addWidget(left_panel, 2)

        # Right side - Step editor
        right_panel = QGroupBox("Step Editor")
        right_layout = QVBoxLayout(right_panel)

        # Action type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Action:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(self.ACTION_TYPES)
        self.action_combo.currentIndexChanged.connect(self._on_action_type_changed)
        type_layout.addWidget(self.action_combo)
        right_layout.addLayout(type_layout)

        # Parameters area (dynamic based on action type)
        self.params_group = QGroupBox("Parameters")
        self.params_layout = QGridLayout(self.params_group)
        right_layout.addWidget(self.params_group)

        # Delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay after (ms):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 60000)
        self.delay_spin.setValue(100)
        self.delay_spin.setSingleStep(100)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        right_layout.addLayout(delay_layout)

        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional description")
        desc_layout.addWidget(self.desc_edit)
        right_layout.addLayout(desc_layout)

        # Apply button
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.clicked.connect(self._apply_step_changes)
        self.apply_btn.setEnabled(False)
        right_layout.addWidget(self.apply_btn)

        # Test button
        self.test_btn = QPushButton("Test This Step")
        self.test_btn.clicked.connect(self._test_current_step)
        right_layout.addWidget(self.test_btn)

        right_layout.addStretch()
        layout.addWidget(right_panel, 1)

        # Initialize parameters UI
        self._setup_params_for_action(0)

    def _clear_params_layout(self):
        """Clear all widgets from params layout."""
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _setup_params_for_action(self, action_idx: int):
        """Setup parameter inputs for the selected action type."""
        self._clear_params_layout()

        action = self.ACTION_TYPES[action_idx]

        if action == "Set Output":
            self.params_layout.addWidget(QLabel("Channel:"), 0, 0)
            self.param_channel = QSpinBox()
            self.param_channel.setRange(1, 30)
            self.params_layout.addWidget(self.param_channel, 0, 1)

            self.params_layout.addWidget(QLabel("State:"), 1, 0)
            self.param_state = QComboBox()
            self.param_state.addItems(["OFF", "ON"])
            self.params_layout.addWidget(self.param_state, 1, 1)

            self.params_layout.addWidget(QLabel("PWM %:"), 2, 0)
            self.param_pwm = QSpinBox()
            self.param_pwm.setRange(0, 100)
            self.param_pwm.setValue(100)
            self.params_layout.addWidget(self.param_pwm, 2, 1)

        elif action == "Set H-Bridge":
            self.params_layout.addWidget(QLabel("Bridge:"), 0, 0)
            self.param_bridge = QComboBox()
            self.param_bridge.addItems(["HB1", "HB2", "HB3", "HB4"])
            self.params_layout.addWidget(self.param_bridge, 0, 1)

            self.params_layout.addWidget(QLabel("Mode:"), 1, 0)
            self.param_mode = QComboBox()
            self.param_mode.addItems(["COAST", "FORWARD", "REVERSE", "BRAKE", "PARK", "PID"])
            self.params_layout.addWidget(self.param_mode, 1, 1)

            self.params_layout.addWidget(QLabel("PWM %:"), 2, 0)
            self.param_pwm = QSpinBox()
            self.param_pwm.setRange(0, 100)
            self.param_pwm.setValue(50)
            self.params_layout.addWidget(self.param_pwm, 2, 1)

        elif action == "Set Digital Input":
            self.params_layout.addWidget(QLabel("Channel:"), 0, 0)
            self.param_channel = QSpinBox()
            self.param_channel.setRange(1, 20)
            self.params_layout.addWidget(self.param_channel, 0, 1)

            self.params_layout.addWidget(QLabel("State:"), 1, 0)
            self.param_state = QComboBox()
            self.param_state.addItems(["LOW", "HIGH"])
            self.params_layout.addWidget(self.param_state, 1, 1)

        elif action == "Set Voltage":
            self.params_layout.addWidget(QLabel("Voltage (mV):"), 0, 0)
            self.param_voltage = QSpinBox()
            self.param_voltage.setRange(6000, 18000)
            self.param_voltage.setValue(12000)
            self.param_voltage.setSingleStep(100)
            self.params_layout.addWidget(self.param_voltage, 0, 1)

        elif action == "Set Temperature":
            self.params_layout.addWidget(QLabel("Temperature (°C):"), 0, 0)
            self.param_temp = QSpinBox()
            self.param_temp.setRange(-40, 150)
            self.param_temp.setValue(25)
            self.params_layout.addWidget(self.param_temp, 0, 1)

        elif action == "Inject Fault":
            self.params_layout.addWidget(QLabel("Channel:"), 0, 0)
            self.param_channel = QSpinBox()
            self.param_channel.setRange(1, 30)
            self.params_layout.addWidget(self.param_channel, 0, 1)

            self.params_layout.addWidget(QLabel("Fault:"), 1, 0)
            self.param_fault = QComboBox()
            self.param_fault.addItems(["Overcurrent (OC)", "Overtemp (OT)", "Short Circuit (SC)", "Open Load (OL)"])
            self.params_layout.addWidget(self.param_fault, 1, 1)

        elif action == "Clear Fault":
            self.params_layout.addWidget(QLabel("Channel:"), 0, 0)
            self.param_channel = QSpinBox()
            self.param_channel.setRange(1, 30)
            self.params_layout.addWidget(self.param_channel, 0, 1)

        elif action == "Wait":
            self.params_layout.addWidget(QLabel("Duration (ms):"), 0, 0)
            self.param_duration = QSpinBox()
            self.param_duration.setRange(10, 60000)
            self.param_duration.setValue(1000)
            self.param_duration.setSingleStep(100)
            self.params_layout.addWidget(self.param_duration, 0, 1)

        elif action == "Send CAN":
            self.params_layout.addWidget(QLabel("Bus:"), 0, 0)
            self.param_bus = QComboBox()
            self.param_bus.addItems(["CAN1", "CAN2", "CAN3", "CAN4"])
            self.params_layout.addWidget(self.param_bus, 0, 1)

            self.params_layout.addWidget(QLabel("ID (hex):"), 1, 0)
            self.param_can_id = QLineEdit("0x100")
            self.params_layout.addWidget(self.param_can_id, 1, 1)

            self.params_layout.addWidget(QLabel("Data (hex):"), 2, 0)
            self.param_can_data = QLineEdit("00 00 00 00 00 00 00 00")
            self.param_can_data.setFont(QFont("Consolas", 9))
            self.params_layout.addWidget(self.param_can_data, 2, 1)

        elif action == "Send LIN":
            self.params_layout.addWidget(QLabel("Bus:"), 0, 0)
            self.param_bus = QComboBox()
            self.param_bus.addItems(["LIN1", "LIN2"])
            self.params_layout.addWidget(self.param_bus, 0, 1)

            self.params_layout.addWidget(QLabel("ID (0-63):"), 1, 0)
            self.param_lin_id = QSpinBox()
            self.param_lin_id.setRange(0, 63)
            self.params_layout.addWidget(self.param_lin_id, 1, 1)

            self.params_layout.addWidget(QLabel("Data (hex):"), 2, 0)
            self.param_lin_data = QLineEdit("00 00 00 00 00 00 00 00")
            self.param_lin_data.setFont(QFont("Consolas", 9))
            self.params_layout.addWidget(self.param_lin_data, 2, 1)

    def _on_action_type_changed(self, index: int):
        """Handle action type combo change."""
        self._setup_params_for_action(index)

    def _on_step_selected(self):
        """Handle step selection in list."""
        selected = self.steps_list.selectedItems()
        has_selection = len(selected) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection and self.steps_list.currentRow() > 0)
        self.move_down_btn.setEnabled(has_selection and self.steps_list.currentRow() < len(self.scenario_steps) - 1)
        self.apply_btn.setEnabled(has_selection)

        if has_selection:
            self._load_step_to_editor(self.steps_list.currentRow())

    def _load_step_to_editor(self, index: int):
        """Load step data into the editor."""
        if index < 0 or index >= len(self.scenario_steps):
            return

        step = self.scenario_steps[index]
        action_type = step.get("action", "Set Output")
        action_idx = self.ACTION_TYPES.index(action_type) if action_type in self.ACTION_TYPES else 0

        self.action_combo.setCurrentIndex(action_idx)
        self._setup_params_for_action(action_idx)

        # Load parameters
        params = step.get("params", {})

        if action_type == "Set Output":
            self.param_channel.setValue(params.get("channel", 1))
            self.param_state.setCurrentIndex(1 if params.get("on", False) else 0)
            self.param_pwm.setValue(params.get("pwm", 100))

        elif action_type == "Set H-Bridge":
            self.param_bridge.setCurrentIndex(params.get("bridge", 0))
            self.param_mode.setCurrentIndex(params.get("mode", 0))
            self.param_pwm.setValue(params.get("pwm", 50))

        elif action_type == "Set Digital Input":
            self.param_channel.setValue(params.get("channel", 1))
            self.param_state.setCurrentIndex(1 if params.get("high", False) else 0)

        elif action_type == "Set Voltage":
            self.param_voltage.setValue(params.get("voltage_mv", 12000))

        elif action_type == "Set Temperature":
            self.param_temp.setValue(params.get("temp_c", 25))

        elif action_type == "Inject Fault":
            self.param_channel.setValue(params.get("channel", 1))
            fault_map = {1: 0, 2: 1, 4: 2, 8: 3}
            self.param_fault.setCurrentIndex(fault_map.get(params.get("fault_type", 1), 0))

        elif action_type == "Clear Fault":
            self.param_channel.setValue(params.get("channel", 1))

        elif action_type == "Wait":
            self.param_duration.setValue(params.get("duration_ms", 1000))

        elif action_type == "Send CAN":
            self.param_bus.setCurrentIndex(params.get("bus", 0))
            self.param_can_id.setText(f"0x{params.get('id', 0x100):03X}")
            data = params.get("data", [0]*8)
            self.param_can_data.setText(" ".join(f"{b:02X}" for b in data))

        elif action_type == "Send LIN":
            self.param_bus.setCurrentIndex(params.get("bus", 0))
            self.param_lin_id.setValue(params.get("id", 0))
            data = params.get("data", [0]*8)
            self.param_lin_data.setText(" ".join(f"{b:02X}" for b in data))

        self.delay_spin.setValue(step.get("delay_ms", 100))
        self.desc_edit.setText(step.get("description", ""))

    def _get_step_from_editor(self) -> dict:
        """Get step data from the editor."""
        action_type = self.ACTION_TYPES[self.action_combo.currentIndex()]
        params = {}

        if action_type == "Set Output":
            params = {
                "channel": self.param_channel.value(),
                "on": self.param_state.currentIndex() == 1,
                "pwm": self.param_pwm.value(),
            }
        elif action_type == "Set H-Bridge":
            params = {
                "bridge": self.param_bridge.currentIndex(),
                "mode": self.param_mode.currentIndex(),
                "pwm": self.param_pwm.value(),
            }
        elif action_type == "Set Digital Input":
            params = {
                "channel": self.param_channel.value(),
                "high": self.param_state.currentIndex() == 1,
            }
        elif action_type == "Set Voltage":
            params = {"voltage_mv": self.param_voltage.value()}
        elif action_type == "Set Temperature":
            params = {"temp_c": self.param_temp.value()}
        elif action_type == "Inject Fault":
            fault_values = [1, 2, 4, 8]
            params = {
                "channel": self.param_channel.value(),
                "fault_type": fault_values[self.param_fault.currentIndex()],
            }
        elif action_type == "Clear Fault":
            params = {"channel": self.param_channel.value()}
        elif action_type == "Wait":
            params = {"duration_ms": self.param_duration.value()}
        elif action_type == "Send CAN":
            try:
                can_id = int(self.param_can_id.text(), 0)
                data = bytes.fromhex(self.param_can_data.text().replace(" ", ""))
            except:
                can_id = 0x100
                data = bytes(8)
            params = {
                "bus": self.param_bus.currentIndex(),
                "id": can_id,
                "data": list(data[:8]),
            }
        elif action_type == "Send LIN":
            try:
                data = bytes.fromhex(self.param_lin_data.text().replace(" ", ""))
            except:
                data = bytes(8)
            params = {
                "bus": self.param_bus.currentIndex(),
                "id": self.param_lin_id.value(),
                "data": list(data[:8]),
            }

        return {
            "action": action_type,
            "params": params,
            "delay_ms": self.delay_spin.value(),
            "description": self.desc_edit.text(),
        }

    def _format_step_display(self, step: dict) -> str:
        """Format step for list display."""
        action = step.get("action", "Unknown")
        params = step.get("params", {})
        delay = step.get("delay_ms", 0)
        desc = step.get("description", "")

        if action == "Set Output":
            ch = params.get("channel", 1)
            state = "ON" if params.get("on", False) else "OFF"
            pwm = params.get("pwm", 100)
            text = f"CH{ch} {state} {pwm}%"
        elif action == "Set H-Bridge":
            modes = ["COAST", "FWD", "REV", "BRAKE", "PARK", "PID"]
            br = params.get("bridge", 0) + 1
            mode = modes[params.get("mode", 0)]
            pwm = params.get("pwm", 50)
            text = f"HB{br} {mode} {pwm}%"
        elif action == "Set Digital Input":
            ch = params.get("channel", 1)
            state = "HIGH" if params.get("high", False) else "LOW"
            text = f"DI{ch} {state}"
        elif action == "Set Voltage":
            v = params.get("voltage_mv", 12000)
            text = f"{v/1000:.1f}V"
        elif action == "Set Temperature":
            t = params.get("temp_c", 25)
            text = f"{t}°C"
        elif action == "Inject Fault":
            ch = params.get("channel", 1)
            faults = {1: "OC", 2: "OT", 4: "SC", 8: "OL"}
            ft = faults.get(params.get("fault_type", 1), "?")
            text = f"CH{ch} {ft}"
        elif action == "Clear Fault":
            ch = params.get("channel", 1)
            text = f"CH{ch}"
        elif action == "Wait":
            dur = params.get("duration_ms", 1000)
            text = f"{dur}ms"
        elif action == "Send CAN":
            can_id = params.get("id", 0x100)
            text = f"0x{can_id:03X}"
        elif action == "Send LIN":
            lin_id = params.get("id", 0)
            text = f"0x{lin_id:02X}"
        else:
            text = ""

        line = f"{action}: {text}"
        if delay > 0:
            line += f" (+{delay}ms)"
        if desc:
            line += f" [{desc}]"
        return line

    def _refresh_steps_list(self):
        """Refresh the steps list display."""
        self.steps_list.clear()
        for i, step in enumerate(self.scenario_steps):
            text = f"{i+1}. {self._format_step_display(step)}"
            self.steps_list.addItem(text)
        self._update_progress_label()

    def _update_progress_label(self):
        """Update the progress label."""
        total = len(self.scenario_steps)
        if self._running:
            self.progress_label.setText(f"Step: {self._current_step + 1} / {total}")
        else:
            self.progress_label.setText(f"Steps: {total}")

    def _add_step(self):
        """Add a new step."""
        step = self._get_step_from_editor()
        self.scenario_steps.append(step)
        self._refresh_steps_list()
        self.steps_list.setCurrentRow(len(self.scenario_steps) - 1)

    def _edit_step(self):
        """Edit the selected step (loads into editor)."""
        current = self.steps_list.currentRow()
        if current >= 0:
            self._load_step_to_editor(current)

    def _apply_step_changes(self):
        """Apply changes from editor to selected step."""
        current = self.steps_list.currentRow()
        if current >= 0:
            self.scenario_steps[current] = self._get_step_from_editor()
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(current)

    def _delete_step(self):
        """Delete the selected step."""
        current = self.steps_list.currentRow()
        if current >= 0:
            del self.scenario_steps[current]
            self._refresh_steps_list()

    def _move_step_up(self):
        """Move selected step up."""
        current = self.steps_list.currentRow()
        if current > 0:
            self.scenario_steps[current], self.scenario_steps[current-1] = \
                self.scenario_steps[current-1], self.scenario_steps[current]
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(current - 1)

    def _move_step_down(self):
        """Move selected step down."""
        current = self.steps_list.currentRow()
        if current < len(self.scenario_steps) - 1:
            self.scenario_steps[current], self.scenario_steps[current+1] = \
                self.scenario_steps[current+1], self.scenario_steps[current]
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(current + 1)

    def _new_scenario(self):
        """Create a new empty scenario."""
        if self.scenario_steps:
            reply = QMessageBox.question(
                self, "New Scenario",
                "Clear current scenario?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.scenario_steps = []
        self._refresh_steps_list()

    def _load_scenario(self):
        """Load scenario from file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Scenario",
            "", "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.scenario_steps = data.get("steps", [])
                self._refresh_steps_list()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load scenario:\n{e}")

    def _save_scenario(self):
        """Save scenario to file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario",
            "scenario.json", "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                data = {
                    "version": 1,
                    "steps": self.scenario_steps,
                }
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save scenario:\n{e}")

    def _toggle_playback(self):
        """Toggle scenario playback."""
        if self._running:
            if self._paused:
                self._paused = False
                self.play_btn.setText("⏸ Pause")
                self._execute_next_step()
            else:
                self._paused = True
                self.play_btn.setText("▶ Resume")
                self._step_timer.stop()
        else:
            if not self.scenario_steps:
                return
            self._running = True
            self._paused = False
            self._current_step = 0
            self.play_btn.setText("⏸ Pause")
            self.stop_btn.setEnabled(True)
            self._execute_next_step()

    def _stop_playback(self):
        """Stop scenario playback."""
        self._running = False
        self._paused = False
        self._step_timer.stop()
        self.play_btn.setText("▶ Play")
        self.stop_btn.setEnabled(False)
        self._update_progress_label()

    def _execute_next_step(self):
        """Execute the next step in the scenario."""
        if not self._running or self._paused:
            return

        if self._current_step >= len(self.scenario_steps):
            if self.loop_check.isChecked():
                self._current_step = 0
            else:
                self._stop_playback()
                return

        # Highlight current step
        self.steps_list.setCurrentRow(self._current_step)
        self._update_progress_label()

        # Get and execute step
        step = self.scenario_steps[self._current_step]
        self.execute_action.emit(step)

        # Get delay and schedule next step
        delay = step.get("delay_ms", 100)
        if step.get("action") == "Wait":
            delay = step.get("params", {}).get("duration_ms", 1000)

        self._current_step += 1
        self._step_timer.start(delay)

    def _test_current_step(self):
        """Test the step currently in the editor."""
        step = self._get_step_from_editor()
        self.execute_action.emit(step)


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

            # Enable checkbox - graphs disabled by default
            self.enable_checkbox = QCheckBox("Enable Graphs")
            self.enable_checkbox.setChecked(False)
            self.enable_checkbox.stateChanged.connect(self._toggle_enable)
            control_layout.addWidget(self.enable_checkbox)

            self.pause_btn = QPushButton("⏸ Pause")
            self.pause_btn.setCheckable(True)
            self.pause_btn.setEnabled(False)  # Disabled until graphs are enabled
            self.pause_btn.clicked.connect(self._toggle_pause)
            control_layout.addWidget(self.pause_btn)

            self.clear_btn = QPushButton("🗑 Clear")
            self.clear_btn.setEnabled(False)  # Disabled until graphs are enabled
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

            self._paused = True  # Disabled by default
            self._enabled = False  # Graphs disabled by default
            self._pg = pg

        except ImportError:
            error_label = QLabel("pyqtgraph not installed.\nInstall with: pip install pyqtgraph")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px;")
            layout.addWidget(error_label)
            self._pg = None
            self._enabled = False

    def _toggle_enable(self, state: int):
        """Toggle graph enable state."""
        self._enabled = state == 2  # Qt.CheckState.Checked is 2
        self.pause_btn.setEnabled(self._enabled)
        self.clear_btn.setEnabled(self._enabled)
        if self._enabled:
            self._paused = False
            self.pause_btn.setChecked(False)
            self.pause_btn.setText("⏸ Pause")
        else:
            self._paused = True

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
        if self._pg is None or self._paused or not self._enabled:
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
        self._user_disconnected = False  # Track if user clicked disconnect
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

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

        # Control button
        self.control_btn = QPushButton("🎛️ Control")
        self.control_btn.clicked.connect(self._open_control_dialog)
        conn_layout.addWidget(self.control_btn)

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
        self._create_lin_monitor_tab()
        self._create_scenario_tab()
        self._create_graphs_tab()

        # Control dialog (lazy created)
        self.control_dialog = None

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
            w.clicked.connect(self._on_analog_clicked)
            w.update_value(0.0)  # Initialize with 0V style
            analog_layout.addWidget(w, row, col)
            self.analog_widgets.append(w)

        layout.addWidget(analog_group)

        # Digital inputs
        digital_group = QGroupBox("Digital Inputs (click to configure)")
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

    def _create_lin_monitor_tab(self):
        """Create LIN monitor tab."""
        self.lin_monitor = LINMonitorWidget()
        self.tabs.addTab(self.lin_monitor, "LIN Monitor")

    def _create_scenario_tab(self):
        """Create scenario editor tab."""
        self.scenario_widget = ScenarioEditorWidget()
        self.scenario_widget.execute_action.connect(self._on_scenario_action)
        self.tabs.addTab(self.scenario_widget, "Scenarios")

    def _create_graphs_tab(self):
        """Create real-time graphs tab."""
        self.graphs_widget = RealTimeGraphWidget()
        self.tabs.addTab(self.graphs_widget, "Graphs")

    def _open_control_dialog(self):
        """Open the control dialog."""
        if self.control_dialog is None:
            self.control_dialog = ControlDialog(self)
            # Connect signals to handlers
            self.control_dialog.inject_fault.connect(self._on_inject_fault)
            self.control_dialog.clear_fault.connect(self._on_clear_fault)
            self.control_dialog.set_voltage.connect(self._on_set_voltage)
            self.control_dialog.set_temperature.connect(self._on_set_temperature)
            self.control_dialog.set_channel_state.connect(self._on_set_channel)
            self.control_dialog.set_hbridge.connect(self._on_set_hbridge)
            self.control_dialog.restart_emulator.connect(self._on_restart_emulator)

        self.control_dialog.show()
        self.control_dialog.raise_()

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

        # Demo LIN traffic timer (simulates LIN bus activity)
        self._demo_lin_counter = 0
        self.demo_lin_timer = QTimer(self)
        self.demo_lin_timer.timeout.connect(self._generate_demo_lin)

        # Auto-reconnect timer
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self._try_reconnect)

    def _try_reconnect(self):
        """Attempt to reconnect to the emulator."""
        if self.connected or self._user_disconnected:
            self.reconnect_timer.stop()
            return

        self._reconnect_attempts += 1
        if self._reconnect_attempts > self._max_reconnect_attempts:
            self.reconnect_timer.stop()
            self.status_label.setText("Reconnect failed")
            self.statusBar().showMessage("Auto-reconnect failed after max attempts")
            return

        self.status_label.setText(f"Reconnecting... ({self._reconnect_attempts}/{self._max_reconnect_attempts})")
        self.status_label.setStyleSheet("color: orange;")

        # Try to connect
        import socket
        host = self.host_edit.text()
        port = self.port_spin.value()

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2.0)
            self.socket.connect((host, port))
            self.socket.setblocking(False)

            self.connected = True
            self._reconnect_attempts = 0
            self.reconnect_timer.stop()

            self.status_label.setText(f"Connected to {host}:{port}")
            self.status_label.setStyleSheet("color: green;")
            self.connect_btn.setText("Disconnect")

            # Start timers (only telemetry and socket read, not demo traffic)
            self.telem_timer.start(200)  # 5 Hz telemetry
            self.read_timer.start(100)   # 10 Hz socket read

            # Subscribe to telemetry at 5Hz (200ms)
            frame = FrameBuilder.subscribe_telemetry(200)
            self._send_frame(frame)

            self.statusBar().showMessage("Reconnected successfully")

        except Exception as e:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            self.socket = None

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

            # Subscribe to telemetry at 5Hz (200ms)
            frame = FrameBuilder.subscribe_telemetry(200)
            self._send_frame(frame)

            # Start timers
            self.telem_timer.start(200)  # 5 Hz telemetry request
            self.read_timer.start(100)   # 10 Hz socket read

            self.statusBar().showMessage(f"Connected to emulator at {host}:{port}")

        except Exception as e:
            self.statusBar().showMessage(f"Connection failed: {e}")
            self.socket = None

    def _disconnect(self, user_initiated: bool = False):
        """Disconnect from emulator."""
        was_connected = self.connected

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
        self.demo_lin_timer.stop()

        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        self.connect_btn.setText("Connect")

        # Start auto-reconnect if connection was lost unexpectedly
        if was_connected and not user_initiated:
            self._user_disconnected = False
            self._reconnect_attempts = 0
            self.reconnect_timer.start(2000)  # Try every 2 seconds
            self.status_label.setText("Connection lost - reconnecting...")
            self.status_label.setStyleSheet("color: orange;")
        elif user_initiated:
            self._user_disconnected = True
            self.reconnect_timer.stop()

    def _toggle_connection(self):
        """Toggle connection state."""
        if self.connected:
            self._disconnect(user_initiated=True)
        else:
            self._user_disconnected = False
            self._reconnect_attempts = 0
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
        """Handle telemetry data using standard 174-byte format."""
        if len(payload) < TELEMETRY_PACKET_SIZE:
            return

        try:
            # Use standard telemetry parser
            telemetry = parse_telemetry(payload)

            # Update voltage and temperature display
            voltage_v = telemetry.input_voltage_mv / 1000.0
            self.voltage_label.setText(f"{voltage_v:.1f}V")
            self.temp_label.setText(f"{telemetry.temperature_c}°C")

            # Update system graphs
            if hasattr(self, 'graphs_widget'):
                self.graphs_widget.add_data_point('system', 'Voltage', voltage_v)
                self.graphs_widget.add_data_point('system', 'Temp', telemetry.temperature_c)

            # Update PROFET outputs (30 channels)
            for i in range(30):
                state = telemetry.profet_states[i].value if hasattr(telemetry.profet_states[i], 'value') else telemetry.profet_states[i]
                duty = telemetry.profet_duties[i]
                # Calculate approximate current from duty (placeholder)
                current_a = duty / 1000.0 * 0.1  # Rough estimate
                fault = 0  # Fault info not in standard telemetry
                self.output_widgets[i].update_state(state, current_a, fault)

                # Update current graph for first 4 channels
                if i < 4 and hasattr(self, 'graphs_widget'):
                    self.graphs_widget.add_data_point('current', f'CH{i+1}', current_a)

            # Update H-Bridge (4 bridges)
            for i in range(4):
                state = telemetry.hbridge_states[i]
                mode = state & 0x07  # Lower 3 bits
                position = telemetry.hbridge_positions[i]
                pwm = 0  # PWM not in standard telemetry
                current_a = 0  # Current not in standard telemetry
                fault = 0
                if i < len(self.hbridge_widgets):
                    self.hbridge_widgets[i].update_state(mode, pwm, current_a, position, fault)

                # Update H-Bridge position graph
                if hasattr(self, 'graphs_widget'):
                    self.graphs_widget.add_data_point('hbridge', f'HB{i+1}', position)

            # Update analog inputs (20 channels, but only show first 16 in widgets)
            for i in range(min(16, len(self.analog_widgets))):
                raw_value = telemetry.adc_values[i] if i < len(telemetry.adc_values) else 0
                voltage = raw_value * 3.3 / 4095
                self.analog_widgets[i].update_value(voltage)

                # Update analog graph for first 4 channels
                if i < 4 and hasattr(self, 'graphs_widget'):
                    self.graphs_widget.add_data_point('analog', f'AIN{i+1}', voltage)

            # Update digital inputs (20 channels)
            for i in range(min(20, len(self.digital_widgets))):
                state = telemetry.digital_inputs[i] if i < len(telemetry.digital_inputs) else 0
                self.digital_widgets[i].update_state(bool(state))

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

    def _generate_demo_lin(self):
        """Generate demo LIN traffic for testing."""
        import random

        self._demo_lin_counter += 1

        # Simulate various LIN frames
        demo_frames = [
            # Wiper status (Master request, then Slave response)
            ("Master", 0x20, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'),
            ("Slave", 0x20, b'\x01\x02\x00\x00\x00\x00\x00\x00'),
            # Window position
            ("Master", 0x21, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'),
            ("Slave", 0x21, struct.pack("<HHxxxx", random.randint(0, 100), 0)),
            # Mirror position
            ("Master", 0x22, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'),
            ("Slave", 0x22, struct.pack("<BBBBBBBB", 0x80, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)),
            # Seat memory
            ("Master", 0x30, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'),
            ("Slave", 0x30, struct.pack("<BBBBBBBB", 0x01, 0x50, 0x80, 0x60, 0x00, 0x00, 0x00, 0x00)),
        ]

        # Pick frames to send (Master followed by Slave)
        idx = (self._demo_lin_counter * 2) % len(demo_frames)
        frame_type, frame_id, data = demo_frames[idx]

        # Calculate checksum
        checksum = sum(data) & 0xFF
        checksum = (~checksum) & 0xFF

        # Add to LIN monitor
        if hasattr(self, 'lin_monitor'):
            bus = 0  # LIN1
            self.lin_monitor.add_frame(frame_type, bus, frame_id, data, checksum)

    def _on_output_clicked(self, channel: int):
        """Handle output channel click - open control dialog."""
        self._open_control_dialog()
        if self.control_dialog:
            self.control_dialog.channel_spin.setValue(channel + 1)
            self.control_dialog.fault_channel_spin.setValue(channel + 1)

    def _on_hbridge_clicked(self, bridge: int):
        """Handle H-Bridge click - open control dialog."""
        self._open_control_dialog()
        if self.control_dialog:
            self.control_dialog.bridge_combo.setCurrentIndex(bridge)

    def _on_analog_clicked(self, channel: int):
        """Handle analog input click - open config dialog."""
        current_voltage = 0.0
        # Get current voltage from widget text
        try:
            text = self.analog_widgets[channel].value_label.text()
            current_voltage = float(text.replace("V", ""))
        except:
            pass

        dialog = AnalogInputDialog(channel, current_voltage, self)
        dialog.set_voltage.connect(self._on_set_analog_voltage)
        dialog.show()

    def _on_set_analog_voltage(self, channel: int, voltage: float):
        """Handle analog voltage change from dialog."""
        # Convert voltage to millivolts and send to emulator
        voltage_mv = int(voltage * 1000)
        frame = FrameBuilder.emu_set_analog_input(channel, voltage_mv)
        self._send_frame(frame)
        self.statusBar().showMessage(f"AIN{channel + 1} = {voltage:.2f}V")

    def _on_digital_clicked(self, channel: int):
        """Handle digital input click - open config dialog."""
        current_state = self.digital_widgets[channel].label.text().endswith("HI")

        dialog = DigitalInputDialog(channel, current_state, self)
        dialog.set_state.connect(self._on_set_digital_state)
        dialog.show()

    def _on_set_digital_state(self, channel: int, state: bool):
        """Handle digital input state change from dialog."""
        frame = FrameBuilder.emu_set_digital_input(channel, state)
        self._send_frame(frame)
        self.statusBar().showMessage(f"DI{channel + 1} -> {'HIGH' if state else 'LOW'}")

    # ===== Control Dialog Signal Handlers =====

    def _on_inject_fault(self, channel: int, fault_type: int):
        """Handle inject fault from dialog."""
        frame = FrameBuilder.emu_inject_fault(channel, fault_type)
        self._send_frame(frame)
        fault_names = {1: "OC", 2: "OT", 4: "SC", 8: "OL"}
        fault_name = fault_names.get(fault_type, f"0x{fault_type:02X}")
        self.statusBar().showMessage(f"Injected {fault_name} fault into CH{channel + 1}")

    def _on_clear_fault(self, channel: int):
        """Handle clear fault from dialog."""
        frame = FrameBuilder.emu_clear_fault(channel)
        self._send_frame(frame)
        self.statusBar().showMessage(f"Cleared fault from CH{channel + 1}")

    def _on_set_voltage(self, voltage_mv: int):
        """Handle set voltage from dialog."""
        frame = FrameBuilder.emu_set_voltage(voltage_mv)
        self._send_frame(frame)
        self.statusBar().showMessage(f"Set voltage to {voltage_mv}mV ({voltage_mv/1000:.1f}V)")

    def _on_set_temperature(self, temp_c: int):
        """Handle set temperature from dialog."""
        frame = FrameBuilder.emu_set_temperature(temp_c)
        self._send_frame(frame)
        self.statusBar().showMessage(f"Set temperature to {temp_c}°C")

    def _on_set_channel(self, channel: int, on: bool, pwm: int):
        """Handle set channel state from dialog."""
        frame = FrameBuilder.emu_set_output(channel, on, pwm)
        self._send_frame(frame)
        state = "ON" if on else "OFF"
        self.statusBar().showMessage(f"CH{channel + 1} {state} PWM={pwm//10}%")

    def _on_set_hbridge(self, bridge: int, mode: int, pwm: int):
        """Handle set H-Bridge from dialog."""
        frame = FrameBuilder.set_hbridge(bridge, mode, pwm)
        self._send_frame(frame)
        modes = ["COAST", "FWD", "REV", "BRAKE", "PARK", "PID"]
        mode_name = modes[mode] if mode < len(modes) else "?"
        self.statusBar().showMessage(f"HB{bridge + 1} {mode_name} PWM={pwm//10}%")

    def _on_restart_emulator(self):
        """Handle restart emulator from dialog."""
        frame = FrameBuilder.restart_device()
        self._send_frame(frame)
        self.statusBar().showMessage("Restarting emulator...")

    def _on_scenario_action(self, step: dict):
        """Handle scenario action execution."""
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "Set Output":
            ch = params.get("channel", 1) - 1
            on = params.get("on", False)
            pwm = params.get("pwm", 100) * 10  # 0-1000
            frame = FrameBuilder.emu_set_output(ch, on, pwm)
            self._send_frame(frame)
            self.statusBar().showMessage(f"Scenario: CH{ch+1} {'ON' if on else 'OFF'} {pwm//10}%")

        elif action == "Set H-Bridge":
            bridge = params.get("bridge", 0)
            mode = params.get("mode", 0)
            pwm = params.get("pwm", 50) * 10  # 0-1000
            frame = FrameBuilder.set_hbridge(bridge, mode, pwm)
            self._send_frame(frame)
            modes = ["COAST", "FWD", "REV", "BRAKE", "PARK", "PID"]
            self.statusBar().showMessage(f"Scenario: HB{bridge+1} {modes[mode]} {pwm//10}%")

        elif action == "Set Digital Input":
            ch = params.get("channel", 1) - 1
            high = params.get("high", False)
            frame = FrameBuilder.emu_set_digital_input(ch, high)
            self._send_frame(frame)
            self.statusBar().showMessage(f"Scenario: DI{ch+1} {'HIGH' if high else 'LOW'}")

        elif action == "Set Voltage":
            voltage_mv = params.get("voltage_mv", 12000)
            frame = FrameBuilder.emu_set_voltage(voltage_mv)
            self._send_frame(frame)
            self.statusBar().showMessage(f"Scenario: Voltage {voltage_mv/1000:.1f}V")

        elif action == "Set Temperature":
            temp_c = params.get("temp_c", 25)
            frame = FrameBuilder.emu_set_temperature(temp_c)
            self._send_frame(frame)
            self.statusBar().showMessage(f"Scenario: Temperature {temp_c}°C")

        elif action == "Inject Fault":
            ch = params.get("channel", 1) - 1
            fault_type = params.get("fault_type", 1)
            frame = FrameBuilder.emu_inject_fault(ch, fault_type)
            self._send_frame(frame)
            faults = {1: "OC", 2: "OT", 4: "SC", 8: "OL"}
            self.statusBar().showMessage(f"Scenario: Inject {faults.get(fault_type, '?')} on CH{ch+1}")

        elif action == "Clear Fault":
            ch = params.get("channel", 1) - 1
            frame = FrameBuilder.emu_clear_fault(ch)
            self._send_frame(frame)
            self.statusBar().showMessage(f"Scenario: Clear fault on CH{ch+1}")

        elif action == "Wait":
            duration = params.get("duration_ms", 1000)
            self.statusBar().showMessage(f"Scenario: Wait {duration}ms")

        elif action == "Send CAN":
            bus = params.get("bus", 0)
            can_id = params.get("id", 0x100)
            data = bytes(params.get("data", [0]*8))
            # Add to CAN monitor as TX
            if hasattr(self, 'can_monitor'):
                self.can_monitor.add_message("TX", bus, can_id, data)
            self.statusBar().showMessage(f"Scenario: CAN TX 0x{can_id:03X}")

        elif action == "Send LIN":
            bus = params.get("bus", 0)
            lin_id = params.get("id", 0)
            data = bytes(params.get("data", [0]*8))
            checksum = sum(data) & 0xFF
            checksum = (~checksum) & 0xFF
            # Add to LIN monitor as Master
            if hasattr(self, 'lin_monitor'):
                self.lin_monitor.add_frame("Master", bus, lin_id, data, checksum)
            self.statusBar().showMessage(f"Scenario: LIN TX 0x{lin_id:02X}")

    def closeEvent(self, event):
        """Handle window close."""
        self._disconnect()
        event.accept()

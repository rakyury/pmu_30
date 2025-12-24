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
    QLineEdit, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette
from typing import Dict, Any, Optional
import asyncio
import struct

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


class HBridgeWidget(QGroupBox):
    """Widget for displaying H-Bridge motor status."""

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
        layout = QHBoxLayout(widget)

        self.hbridge_widgets = []
        for i in range(4):
            w = HBridgeWidget(i)
            layout.addWidget(w)
            self.hbridge_widgets.append(w)

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
            voltage, temp = struct.unpack_from("<Hh", payload, offset)
            offset += 4

            self.voltage_label.setText(f"{voltage/1000:.1f}V")
            self.temp_label.setText(f"{temp}°C")

            # Parse PROFET outputs (30 channels, 6 bytes each)
            for i in range(30):
                if offset + 6 > len(payload):
                    break
                state, current, fault, pwm = struct.unpack_from("<BHBh", payload, offset)
                offset += 6
                self.output_widgets[i].update_state(state, current/1000.0, fault)

            # Parse H-Bridge (4 bridges)
            for i in range(4):
                if offset + 8 > len(payload):
                    break
                mode, state, pwm, current, position, fault = struct.unpack_from("<BBHhHB", payload, offset)
                offset += 9
                if i < len(self.hbridge_widgets):
                    self.hbridge_widgets[i].update_state(mode, pwm, current/1000.0, position, fault)

            # Parse analog inputs
            for i in range(16):
                if offset + 2 > len(payload):
                    break
                raw_value, = struct.unpack_from("<H", payload, offset)
                offset += 2
                voltage = raw_value * 3.3 / 4095
                if i < len(self.analog_widgets):
                    self.analog_widgets[i].update_value(voltage)

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

    def _on_output_clicked(self, channel: int):
        """Handle output channel click."""
        self.fault_channel_spin.setValue(channel + 1)
        self.tabs.setCurrentIndex(3)  # Switch to control tab

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

"""
PMU-30 Emulator Monitor - Main Window

Desktop application for monitoring and controlling the PMU-30 emulator.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QGroupBox, QGridLayout,
    QSpinBox, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any
import struct

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication.protocol import MessageType, ProtocolFrame, encode_frame, decode_frame, FrameBuilder
from communication.telemetry import parse_telemetry, TELEMETRY_PACKET_SIZE

# Import all widgets from widgets package
from .widgets import (
    OutputChannelWidget,
    HBridgeChannelWidget,
    AnalogInputWidget,
    DigitalInputWidget,
    AnalogInputDialog,
    DigitalInputDialog,
    ControlDialog,
    CANMonitorWidget,
    LINMonitorWidget,
    WirelessStatusWidget,
    RealTimeGraphWidget,
    ScenarioEditorWidget,
)


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
            import random
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

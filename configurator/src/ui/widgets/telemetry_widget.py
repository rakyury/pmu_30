"""
PMU-30 Telemetry Widget
Real-time telemetry display with live connection to device
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QProgressBar, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from typing import Optional, Dict, List
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class TelemetryData:
    """Telemetry data snapshot."""
    connected: bool = False
    voltage_v: float = 0.0
    current_a: float = 0.0
    power_w: float = 0.0
    temperature_c: int = 0
    uptime_ms: int = 0
    channel_states: List[int] = None
    channel_currents: List[int] = None
    analog_values: List[int] = None
    fault_flags: int = 0

    def __post_init__(self):
        if self.channel_states is None:
            self.channel_states = [0] * 30
        if self.channel_currents is None:
            self.channel_currents = [0] * 30
        if self.analog_values is None:
            self.analog_values = [0] * 20


class StatusIndicator(QFrame):
    """LED-style status indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setFrameShape(QFrame.Shape.Box)
        self._color = QColor(128, 128, 128)  # Gray = unknown
        self._set_color(self._color)

    def _set_color(self, color: QColor):
        self._color = color
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color.name()};
                border: 1px solid #666;
                border-radius: 8px;
            }}
        """)

    def set_ok(self):
        """Set indicator to OK (green)."""
        self._set_color(QColor(0, 200, 0))

    def set_warning(self):
        """Set indicator to warning (yellow)."""
        self._set_color(QColor(255, 200, 0))

    def set_error(self):
        """Set indicator to error (red)."""
        self._set_color(QColor(255, 0, 0))

    def set_unknown(self):
        """Set indicator to unknown (gray)."""
        self._set_color(QColor(128, 128, 128))

    def set_off(self):
        """Set indicator to off (dark gray)."""
        self._set_color(QColor(64, 64, 64))


class TelemetryWidget(QWidget):
    """
    Real-time telemetry display widget.

    Shows:
    - Connection status
    - System voltage, current, power
    - Temperature
    - Channel status overview
    - Fault indicators
    """

    # Signals
    connection_requested = pyqtSignal(str)  # port
    disconnection_requested = pyqtSignal()
    telemetry_rate_changed = pyqtSignal(int)  # Hz

    def __init__(self, parent=None):
        super().__init__(parent)
        self._telemetry = TelemetryData()
        self._connected = False
        self._streaming = False
        self._init_ui()

        # Update timer for UI refresh
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.start(100)  # 10 Hz UI update

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Connection bar
        conn_layout = QHBoxLayout()

        self.status_led = StatusIndicator()
        conn_layout.addWidget(self.status_led)

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("font-weight: bold;")
        conn_layout.addWidget(self.status_label)

        conn_layout.addStretch()

        conn_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self.port_combo.setEditable(True)
        conn_layout.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        conn_layout.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connection)
        conn_layout.addWidget(self.connect_btn)

        layout.addLayout(conn_layout)

        # Main telemetry grid
        grid = QGridLayout()
        grid.setSpacing(10)

        # === System Status Group ===
        system_group = QGroupBox("System Status")
        system_layout = QGridLayout()

        # Voltage
        system_layout.addWidget(QLabel("Input Voltage:"), 0, 0)
        self.voltage_label = QLabel("-- V")
        self.voltage_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        system_layout.addWidget(self.voltage_label, 0, 1)

        self.voltage_bar = QProgressBar()
        self.voltage_bar.setRange(0, 160)  # 0-16V scaled
        self.voltage_bar.setTextVisible(False)
        self.voltage_bar.setFixedHeight(8)
        system_layout.addWidget(self.voltage_bar, 0, 2)

        # Current
        system_layout.addWidget(QLabel("Total Current:"), 1, 0)
        self.current_label = QLabel("-- A")
        self.current_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        system_layout.addWidget(self.current_label, 1, 1)

        self.current_bar = QProgressBar()
        self.current_bar.setRange(0, 1000)  # 0-100A scaled
        self.current_bar.setTextVisible(False)
        self.current_bar.setFixedHeight(8)
        system_layout.addWidget(self.current_bar, 1, 2)

        # Power
        system_layout.addWidget(QLabel("Power:"), 2, 0)
        self.power_label = QLabel("-- W")
        self.power_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        system_layout.addWidget(self.power_label, 2, 1)

        self.power_bar = QProgressBar()
        self.power_bar.setRange(0, 1500)  # 0-1500W
        self.power_bar.setTextVisible(False)
        self.power_bar.setFixedHeight(8)
        system_layout.addWidget(self.power_bar, 2, 2)

        # Temperature
        system_layout.addWidget(QLabel("Temperature:"), 3, 0)
        self.temp_label = QLabel("-- C")
        self.temp_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        system_layout.addWidget(self.temp_label, 3, 1)

        self.temp_bar = QProgressBar()
        self.temp_bar.setRange(0, 120)  # 0-120C
        self.temp_bar.setTextVisible(False)
        self.temp_bar.setFixedHeight(8)
        system_layout.addWidget(self.temp_bar, 3, 2)

        system_group.setLayout(system_layout)
        grid.addWidget(system_group, 0, 0)

        # === Channel Overview Group ===
        channels_group = QGroupBox("Channel Overview (30 PROFET)")
        channels_layout = QVBoxLayout()

        # Channel grid - 6 rows x 5 columns
        self.channel_leds = []
        channel_grid = QGridLayout()
        channel_grid.setSpacing(4)

        for i in range(30):
            row = i // 6
            col = i % 6

            channel_frame = QVBoxLayout()
            led = StatusIndicator()
            led.set_off()
            self.channel_leds.append(led)

            label = QLabel(f"{i+1}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 9px;")

            channel_frame.addWidget(led, alignment=Qt.AlignmentFlag.AlignCenter)
            channel_frame.addWidget(label)

            container = QWidget()
            container.setLayout(channel_frame)
            channel_grid.addWidget(container, row, col)

        channels_layout.addLayout(channel_grid)

        # Summary
        summary_layout = QHBoxLayout()
        self.active_count_label = QLabel("Active: 0")
        self.fault_count_label = QLabel("Faults: 0")
        self.fault_count_label.setStyleSheet("color: red;")
        summary_layout.addWidget(self.active_count_label)
        summary_layout.addStretch()
        summary_layout.addWidget(self.fault_count_label)
        channels_layout.addLayout(summary_layout)

        channels_group.setLayout(channels_layout)
        grid.addWidget(channels_group, 0, 1)

        # === Faults Group ===
        faults_group = QGroupBox("System Faults")
        faults_layout = QVBoxLayout()

        self.fault_indicators = {}
        fault_names = [
            ("overvoltage", "Overvoltage"),
            ("undervoltage", "Undervoltage"),
            ("overtemp", "Overtemperature"),
            ("can1_error", "CAN1 Error"),
            ("can2_error", "CAN2 Error"),
            ("config_error", "Config Error"),
        ]

        for key, name in fault_names:
            fault_row = QHBoxLayout()
            led = StatusIndicator()
            led.set_off()
            self.fault_indicators[key] = led
            fault_row.addWidget(led)
            fault_row.addWidget(QLabel(name))
            fault_row.addStretch()
            faults_layout.addLayout(fault_row)

        faults_layout.addStretch()
        faults_group.setLayout(faults_layout)
        grid.addWidget(faults_group, 1, 0)

        # === Streaming Control ===
        stream_group = QGroupBox("Telemetry Stream")
        stream_layout = QVBoxLayout()

        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Rate:"))
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(1, 100)
        self.rate_spin.setValue(50)
        self.rate_spin.setSuffix(" Hz")
        rate_layout.addWidget(self.rate_spin)
        rate_layout.addStretch()
        stream_layout.addLayout(rate_layout)

        self.stream_btn = QPushButton("Start Stream")
        self.stream_btn.setEnabled(False)
        self.stream_btn.clicked.connect(self._toggle_stream)
        stream_layout.addWidget(self.stream_btn)

        # Stats
        self.packets_label = QLabel("Packets: 0")
        self.latency_label = QLabel("Latency: -- ms")
        stream_layout.addWidget(self.packets_label)
        stream_layout.addWidget(self.latency_label)

        stream_layout.addStretch()
        stream_group.setLayout(stream_layout)
        grid.addWidget(stream_group, 1, 1)

        layout.addLayout(grid)

    def _refresh_ports(self):
        """Refresh available serial ports."""
        try:
            from ..communication.serial_transport import SerialTransport
            ports = SerialTransport.list_ports()

            self.port_combo.clear()
            for port in ports:
                display = f"{port.port} - {port.description}"
                if port.is_pmu30:
                    display = f"* {display}"
                self.port_combo.addItem(display, port.port)
        except Exception as e:
            logger.error(f"Failed to list ports: {e}")

    def _toggle_connection(self):
        """Toggle connection state."""
        if self._connected:
            self.disconnection_requested.emit()
        else:
            port = self.port_combo.currentData()
            if port:
                self.connection_requested.emit(port)

    def _toggle_stream(self):
        """Toggle telemetry streaming."""
        if self._streaming:
            self._streaming = False
            self.stream_btn.setText("Start Stream")
        else:
            self._streaming = True
            self.stream_btn.setText("Stop Stream")
            self.telemetry_rate_changed.emit(self.rate_spin.value())

    def set_connected(self, connected: bool, device_name: str = ""):
        """Update connection state."""
        self._connected = connected

        if connected:
            self.status_led.set_ok()
            self.status_label.setText(f"Connected: {device_name}" if device_name else "Connected")
            self.connect_btn.setText("Disconnect")
            self.stream_btn.setEnabled(True)
        else:
            self.status_led.set_unknown()
            self.status_label.setText("Disconnected")
            self.connect_btn.setText("Connect")
            self.stream_btn.setEnabled(False)
            self._streaming = False
            self.stream_btn.setText("Start Stream")

    def update_telemetry(self, data: TelemetryData):
        """Update telemetry data."""
        self._telemetry = data

    def _update_display(self):
        """Update display from current telemetry data."""
        data = self._telemetry

        if not self._connected:
            return

        # System values
        self.voltage_label.setText(f"{data.voltage_v:.1f} V")
        self.voltage_bar.setValue(int(data.voltage_v * 10))

        # Color voltage bar based on value
        if data.voltage_v < 10.0:
            self.voltage_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif data.voltage_v > 15.0:
            self.voltage_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            self.voltage_bar.setStyleSheet("QProgressBar::chunk { background-color: #0078d4; }")

        self.current_label.setText(f"{data.current_a:.1f} A")
        self.current_bar.setValue(int(data.current_a * 10))

        self.power_label.setText(f"{data.power_w:.0f} W")
        self.power_bar.setValue(int(data.power_w))

        self.temp_label.setText(f"{data.temperature_c} C")
        self.temp_bar.setValue(data.temperature_c)

        # Color temp bar
        if data.temperature_c > 80:
            self.temp_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
        elif data.temperature_c > 60:
            self.temp_label.setStyleSheet("font-size: 18px; font-weight: bold; color: orange;")
        else:
            self.temp_label.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")

        # Channel LEDs
        active_count = 0
        fault_count = 0

        for i, led in enumerate(self.channel_leds):
            if i < len(data.channel_states):
                state = data.channel_states[i]
                if state == 0:  # OFF
                    led.set_off()
                elif state == 1:  # ON
                    led.set_ok()
                    active_count += 1
                elif state == 6:  # PWM
                    led.set_ok()
                    active_count += 1
                elif state >= 2 and state <= 5:  # Fault
                    led.set_error()
                    fault_count += 1
                else:
                    led.set_unknown()

        self.active_count_label.setText(f"Active: {active_count}")
        self.fault_count_label.setText(f"Faults: {fault_count}")

        # Fault indicators
        flags = data.fault_flags
        self.fault_indicators["overvoltage"].set_error() if flags & 0x01 else self.fault_indicators["overvoltage"].set_off()
        self.fault_indicators["undervoltage"].set_error() if flags & 0x02 else self.fault_indicators["undervoltage"].set_off()
        self.fault_indicators["overtemp"].set_error() if flags & 0x04 else self.fault_indicators["overtemp"].set_off()
        self.fault_indicators["can1_error"].set_error() if flags & 0x08 else self.fault_indicators["can1_error"].set_off()
        self.fault_indicators["can2_error"].set_error() if flags & 0x10 else self.fault_indicators["can2_error"].set_off()
        self.fault_indicators["config_error"].set_error() if flags & 0x40 else self.fault_indicators["config_error"].set_off()

    def update_stats(self, packets: int, latency_ms: float):
        """Update streaming statistics."""
        self.packets_label.setText(f"Packets: {packets}")
        self.latency_label.setText(f"Latency: {latency_ms:.1f} ms")

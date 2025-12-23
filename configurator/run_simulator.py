#!/usr/bin/env python3
"""
PMU-30 Device Simulator Demo

Runs the device simulator with a simple GUI to control simulated values.
Can be used standalone or alongside the configurator.

Usage:
    python run_simulator.py
"""

import sys
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QSlider, QPushButton, QSpinBox, QDoubleSpinBox,
    QTextEdit, QGridLayout, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

# Add src to path
sys.path.insert(0, 'src')

from communication.device_simulator import DeviceSimulator, SimulatorState
from communication.telemetry import ChannelState, FaultFlags
from communication.protocol import FrameBuilder, encode_frame, decode_frame, MessageType


class SimulatorControlPanel(QMainWindow):
    """GUI for controlling the device simulator."""

    def __init__(self):
        super().__init__()
        self.simulator = DeviceSimulator()
        self.setWindowTitle("PMU-30 Device Simulator")
        self.resize(800, 600)

        self._init_ui()
        self._start_timer()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Simulator Ready")
        self.status_label.setStyleSheet("font-weight: bold; color: green;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        self.start_btn = QPushButton("Start Simulator")
        self.start_btn.clicked.connect(self._toggle_simulator)
        status_layout.addWidget(self.start_btn)
        layout.addLayout(status_layout)

        # Main grid
        grid = QGridLayout()

        # === System Values ===
        system_group = QGroupBox("System Values")
        system_layout = QGridLayout()

        # Voltage
        system_layout.addWidget(QLabel("Input Voltage:"), 0, 0)
        self.voltage_slider = QSlider(Qt.Orientation.Horizontal)
        self.voltage_slider.setRange(80, 180)  # 8.0V - 18.0V
        self.voltage_slider.setValue(135)
        self.voltage_slider.valueChanged.connect(self._on_voltage_changed)
        system_layout.addWidget(self.voltage_slider, 0, 1)
        self.voltage_label = QLabel("13.5 V")
        system_layout.addWidget(self.voltage_label, 0, 2)

        # Temperature
        system_layout.addWidget(QLabel("Temperature:"), 1, 0)
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(-20, 100)
        self.temp_slider.setValue(35)
        self.temp_slider.valueChanged.connect(self._on_temp_changed)
        system_layout.addWidget(self.temp_slider, 1, 1)
        self.temp_label = QLabel("35 C")
        system_layout.addWidget(self.temp_label, 1, 2)

        system_group.setLayout(system_layout)
        grid.addWidget(system_group, 0, 0)

        # === Fault Injection ===
        fault_group = QGroupBox("Fault Injection")
        fault_layout = QVBoxLayout()

        self.fault_checks = {}
        faults = [
            ("Overvoltage", FaultFlags.OVERVOLTAGE),
            ("Undervoltage", FaultFlags.UNDERVOLTAGE),
            ("Overtemperature", FaultFlags.OVERTEMPERATURE),
            ("CAN1 Error", FaultFlags.CAN1_ERROR),
            ("CAN2 Error", FaultFlags.CAN2_ERROR),
            ("Config Error", FaultFlags.CONFIG_ERROR),
        ]

        for name, flag in faults:
            cb = QCheckBox(name)
            cb.toggled.connect(lambda checked, f=flag: self._on_fault_toggled(f, checked))
            fault_layout.addWidget(cb)
            self.fault_checks[flag] = cb

        fault_group.setLayout(fault_layout)
        grid.addWidget(fault_group, 0, 1)

        # === Channel Control ===
        channel_group = QGroupBox("Channel Control")
        channel_layout = QGridLayout()

        channel_layout.addWidget(QLabel("Channel:"), 0, 0)
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(0, 29)
        channel_layout.addWidget(self.channel_spin, 0, 1)

        channel_layout.addWidget(QLabel("State:"), 1, 0)
        self.state_combo = QComboBox()
        self.state_combo.addItems(["OFF", "ON", "PWM", "FAULT_OC", "FAULT_OT", "FAULT_SC"])
        channel_layout.addWidget(self.state_combo, 1, 1)

        channel_layout.addWidget(QLabel("Current (mA):"), 2, 0)
        self.current_spin = QSpinBox()
        self.current_spin.setRange(0, 40000)
        self.current_spin.setValue(0)
        channel_layout.addWidget(self.current_spin, 2, 1)

        apply_btn = QPushButton("Apply to Channel")
        apply_btn.clicked.connect(self._apply_channel)
        channel_layout.addWidget(apply_btn, 3, 0, 1, 2)

        channel_group.setLayout(channel_layout)
        grid.addWidget(channel_group, 1, 0)

        # === Telemetry Status ===
        telemetry_group = QGroupBox("Telemetry Status")
        telemetry_layout = QVBoxLayout()

        self.telemetry_label = QLabel("Rate: 0 Hz\nPackets: 0")
        self.telemetry_label.setFont(QFont("Courier", 10))
        telemetry_layout.addWidget(self.telemetry_label)

        telemetry_group.setLayout(telemetry_layout)
        grid.addWidget(telemetry_group, 1, 1)

        layout.addLayout(grid)

        # === Log ===
        log_group = QGroupBox("Protocol Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Courier", 9))
        log_layout.addWidget(self.log_text)

        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_btn)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

    def _start_timer(self):
        """Start update timer."""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_display)
        self.timer.start(100)

    def _toggle_simulator(self):
        """Toggle simulator on/off."""
        if self.simulator.is_running:
            asyncio.get_event_loop().run_until_complete(self.simulator.stop())
            self.start_btn.setText("Start Simulator")
            self.status_label.setText("Simulator Stopped")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
        else:
            asyncio.get_event_loop().run_until_complete(self.simulator.start())
            self.start_btn.setText("Stop Simulator")
            self.status_label.setText("Simulator Running")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")

    def _on_voltage_changed(self, value):
        voltage = value / 10.0
        self.voltage_label.setText(f"{voltage:.1f} V")
        self.simulator.set_voltage(voltage)

    def _on_temp_changed(self, value):
        self.temp_label.setText(f"{value} C")
        self.simulator.set_temperature(value)

    def _on_fault_toggled(self, fault: FaultFlags, checked: bool):
        if checked:
            self.simulator.set_fault(fault)
            self._log(f"Set fault: {fault.name}")
        else:
            self.simulator.clear_fault(fault)
            self._log(f"Clear fault: {fault.name}")

    def _apply_channel(self):
        ch = self.channel_spin.value()
        state_idx = self.state_combo.currentIndex()
        current = self.current_spin.value()

        states = [
            ChannelState.OFF,
            ChannelState.ON,
            ChannelState.PWM_ACTIVE,
            ChannelState.FAULT_OVERCURRENT,
            ChannelState.FAULT_OVERHEAT,
            ChannelState.FAULT_SHORT,
        ]

        self.simulator.set_channel_state(ch, states[state_idx])
        self.simulator.state.channels[ch].current_ma = current
        self._log(f"Channel {ch}: {states[state_idx].name}, {current}mA")

    def _update_display(self):
        """Update display with current state."""
        state = self.simulator.state
        rate = state.telemetry_rate_hz
        enabled = "Yes" if state.telemetry_enabled else "No"

        self.telemetry_label.setText(
            f"Rate: {rate} Hz\n"
            f"Streaming: {enabled}\n"
            f"Uptime: {state.uptime_ms // 1000}s\n"
            f"Voltage: {state.input_voltage_mv / 1000:.1f}V\n"
            f"Temp: {state.temperature_c}C"
        )

    def _log(self, message: str):
        """Add message to log."""
        self.log_text.append(message)

    def test_protocol(self):
        """Test protocol commands (for debugging)."""
        import asyncio

        async def run_test():
            await self.simulator.start()

            # Test PING
            ping = encode_frame(FrameBuilder.ping())
            response = await self.simulator.process_frame(ping)
            frame, _ = decode_frame(response)
            self._log(f"PING -> {frame.msg_type.name}")

            # Test GET_INFO
            get_info = encode_frame(FrameBuilder.get_info())
            response = await self.simulator.process_frame(get_info)
            frame, _ = decode_frame(response)
            self._log(f"GET_INFO -> {frame.msg_type.name}")

        asyncio.get_event_loop().run_until_complete(run_test())


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = SimulatorControlPanel()
    window.show()

    # Start simulator automatically
    asyncio.get_event_loop().run_until_complete(window.simulator.start())
    window.start_btn.setText("Stop Simulator")
    window.status_label.setText("Simulator Running")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

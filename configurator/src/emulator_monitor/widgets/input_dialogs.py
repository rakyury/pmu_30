"""
Input Dialogs - Dialogs for configuring emulator inputs and controls

This module contains dialogs for analog/digital input simulation and control.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QSlider, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


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
        self.restart_btn = QPushButton("Restart Emulator")
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

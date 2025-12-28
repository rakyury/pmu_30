"""
Input Emulator Widget
Allows setting digital/analog input states and injecting CAN messages for testing
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QSpinBox, QDoubleSpinBox, QLabel, QLineEdit, QComboBox,
    QCheckBox, QSizePolicy, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from typing import Optional, Callable
import struct


class InputEmulatorWidget(QWidget):
    """Widget for emulating input states during testing."""

    # Signal emitted when a digital input is set
    digital_input_changed = pyqtSignal(int, bool)  # (pin, state)
    # Signal emitted when an analog input is set
    analog_input_changed = pyqtSignal(int, float)  # (pin, voltage)
    # Signal emitted when a CAN message is injected
    can_message_injected = pyqtSignal(int, int, bytes)  # (bus_id, can_id, data)

    # Colors
    COLOR_ON = QColor(50, 120, 50)   # Green
    COLOR_OFF = QColor(60, 60, 60)   # Gray

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._send_callback: Optional[Callable] = None
        self._init_ui()

    def set_send_callback(self, callback: Callable):
        """Set the callback for sending commands to the emulator.

        Args:
            callback: Async function that takes (command_type, *args)
        """
        self._send_callback = callback

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Title
        title = QLabel("Input Emulator")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #10b981;")
        layout.addWidget(title)

        # Tab widget for different input types
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs
        self._create_digital_tab()
        self._create_analog_tab()
        self._create_can_tab()

    def _create_digital_tab(self):
        """Create digital inputs emulation tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Table for digital inputs
        self.digital_table = QTableWidget()
        self.digital_table.setColumnCount(3)
        self.digital_table.setHorizontalHeaderLabels(["Pin", "State", "Toggle"])

        header = self.digital_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)

        self.digital_table.setColumnWidth(0, 40)
        self.digital_table.setColumnWidth(2, 60)
        self.digital_table.verticalHeader().setVisible(False)

        # Populate with 20 digital inputs
        self.digital_table.setRowCount(20)
        self._digital_states = [False] * 20

        for i in range(20):
            # Pin number
            pin_item = QTableWidgetItem(f"D{i+1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pin_item.setFlags(pin_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.digital_table.setItem(i, 0, pin_item)

            # State
            state_item = QTableWidgetItem("OFF")
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            state_item.setFlags(state_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            state_item.setBackground(QBrush(self.COLOR_OFF))
            self.digital_table.setItem(i, 1, state_item)

            # Toggle button
            btn = QPushButton("Toggle")
            btn.setProperty("pin", i)
            btn.clicked.connect(self._on_digital_toggle)
            self.digital_table.setCellWidget(i, 2, btn)

        # Apply dark theme
        self.digital_table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                gridline-color: #333333;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #333333;
            }
        """)

        layout.addWidget(self.digital_table)

        # Bulk controls
        bulk_layout = QHBoxLayout()

        all_on_btn = QPushButton("All ON")
        all_on_btn.clicked.connect(lambda: self._set_all_digital(True))
        bulk_layout.addWidget(all_on_btn)

        all_off_btn = QPushButton("All OFF")
        all_off_btn.clicked.connect(lambda: self._set_all_digital(False))
        bulk_layout.addWidget(all_off_btn)

        bulk_layout.addStretch()
        layout.addLayout(bulk_layout)

        self.tabs.addTab(tab, "Digital Inputs")

    def _create_analog_tab(self):
        """Create analog inputs emulation tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Table for analog inputs
        self.analog_table = QTableWidget()
        self.analog_table.setColumnCount(4)
        self.analog_table.setHorizontalHeaderLabels(["Pin", "Voltage", "Set", "Send"])

        header = self.analog_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)

        self.analog_table.setColumnWidth(0, 40)
        self.analog_table.setColumnWidth(2, 80)
        self.analog_table.setColumnWidth(3, 50)
        self.analog_table.verticalHeader().setVisible(False)

        # Populate with 20 analog inputs
        self.analog_table.setRowCount(20)
        self._analog_spinboxes = []

        for i in range(20):
            # Pin number
            pin_item = QTableWidgetItem(f"A{i+1}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pin_item.setFlags(pin_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.analog_table.setItem(i, 0, pin_item)

            # Current voltage display
            voltage_item = QTableWidgetItem("0.00 V")
            voltage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            voltage_item.setFlags(voltage_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.analog_table.setItem(i, 1, voltage_item)

            # Voltage spinbox
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 5.0)
            spin.setSingleStep(0.1)
            spin.setDecimals(2)
            spin.setSuffix(" V")
            spin.setProperty("pin", i)
            self._analog_spinboxes.append(spin)
            self.analog_table.setCellWidget(i, 2, spin)

            # Send button
            btn = QPushButton("Set")
            btn.setProperty("pin", i)
            btn.clicked.connect(self._on_analog_send)
            self.analog_table.setCellWidget(i, 3, btn)

        # Apply dark theme
        self.analog_table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                gridline-color: #333333;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #333333;
            }
        """)

        layout.addWidget(self.analog_table)
        self.tabs.addTab(tab, "Analog Inputs")

    def _create_can_tab(self):
        """Create CAN message injection tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # CAN message form
        form_group = QGroupBox("Inject CAN Message")
        form_layout = QFormLayout()

        # Bus selection
        self.can_bus_combo = QComboBox()
        self.can_bus_combo.addItems(["CAN 1", "CAN 2"])
        form_layout.addRow("Bus:", self.can_bus_combo)

        # CAN ID
        self.can_id_spin = QSpinBox()
        self.can_id_spin.setRange(0, 0x1FFFFFFF)  # 29-bit max
        self.can_id_spin.setDisplayIntegerBase(16)
        self.can_id_spin.setPrefix("0x")
        self.can_id_spin.setValue(0x100)
        form_layout.addRow("CAN ID:", self.can_id_spin)

        # Extended ID checkbox
        self.can_extended_check = QCheckBox("Extended ID (29-bit)")
        form_layout.addRow("", self.can_extended_check)

        # Data bytes (8 hex inputs)
        data_layout = QHBoxLayout()
        self._can_data_edits = []
        for i in range(8):
            edit = QLineEdit("00")
            edit.setMaxLength(2)
            edit.setFixedWidth(35)
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setPlaceholderText("00")
            self._can_data_edits.append(edit)
            data_layout.addWidget(edit)
        data_layout.addStretch()
        form_layout.addRow("Data (hex):", data_layout)

        # DLC
        self.can_dlc_spin = QSpinBox()
        self.can_dlc_spin.setRange(0, 8)
        self.can_dlc_spin.setValue(8)
        form_layout.addRow("DLC:", self.can_dlc_spin)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Send button
        send_btn = QPushButton("Inject CAN Message")
        send_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 8px;")
        send_btn.clicked.connect(self._on_can_inject)
        layout.addWidget(send_btn)

        # Quick presets
        presets_group = QGroupBox("Quick Presets")
        presets_layout = QVBoxLayout()

        preset1_btn = QPushButton("ECU Status (0x100): [01 00 00 00 00 00 00 00]")
        preset1_btn.clicked.connect(lambda: self._apply_can_preset(0x100, [0x01, 0, 0, 0, 0, 0, 0, 0]))
        presets_layout.addWidget(preset1_btn)

        preset2_btn = QPushButton("Sensor Data (0x200): [FF 7F 00 00 00 00 00 00]")
        preset2_btn.clicked.connect(lambda: self._apply_can_preset(0x200, [0xFF, 0x7F, 0, 0, 0, 0, 0, 0]))
        presets_layout.addWidget(preset2_btn)

        presets_group.setLayout(presets_layout)
        layout.addWidget(presets_group)

        layout.addStretch()
        self.tabs.addTab(tab, "CAN Injection")

    def _on_digital_toggle(self):
        """Handle digital input toggle."""
        btn = self.sender()
        pin = btn.property("pin")

        # Toggle state
        self._digital_states[pin] = not self._digital_states[pin]
        new_state = self._digital_states[pin]

        # Update display
        state_item = self.digital_table.item(pin, 1)
        state_item.setText("ON" if new_state else "OFF")
        state_item.setBackground(QBrush(self.COLOR_ON if new_state else self.COLOR_OFF))

        # Emit signal
        self.digital_input_changed.emit(pin, new_state)

    def _set_all_digital(self, state: bool):
        """Set all digital inputs to a state."""
        for i in range(20):
            self._digital_states[i] = state
            state_item = self.digital_table.item(i, 1)
            state_item.setText("ON" if state else "OFF")
            state_item.setBackground(QBrush(self.COLOR_ON if state else self.COLOR_OFF))
            self.digital_input_changed.emit(i, state)

    def _on_analog_send(self):
        """Handle analog input send."""
        btn = self.sender()
        pin = btn.property("pin")
        voltage = self._analog_spinboxes[pin].value()

        # Update display
        voltage_item = self.analog_table.item(pin, 1)
        voltage_item.setText(f"{voltage:.2f} V")

        # Emit signal
        self.analog_input_changed.emit(pin, voltage)

    def _on_can_inject(self):
        """Handle CAN message injection."""
        bus_id = self.can_bus_combo.currentIndex()
        can_id = self.can_id_spin.value()
        dlc = self.can_dlc_spin.value()

        # Parse data bytes
        data = []
        for i in range(dlc):
            try:
                byte_val = int(self._can_data_edits[i].text(), 16)
                data.append(byte_val & 0xFF)
            except ValueError:
                data.append(0)

        data_bytes = bytes(data)

        # Emit signal
        self.can_message_injected.emit(bus_id, can_id, data_bytes)

        # Show confirmation
        hex_str = ' '.join(f'{b:02X}' for b in data_bytes)
        QMessageBox.information(
            self, "CAN Injected",
            f"Sent CAN message:\nBus: CAN {bus_id + 1}\nID: 0x{can_id:X}\nData: {hex_str}"
        )

    def _apply_can_preset(self, can_id: int, data: list):
        """Apply a CAN message preset."""
        self.can_id_spin.setValue(can_id)
        for i, byte_val in enumerate(data):
            if i < 8:
                self._can_data_edits[i].setText(f"{byte_val:02X}")
        self.can_dlc_spin.setValue(len(data))

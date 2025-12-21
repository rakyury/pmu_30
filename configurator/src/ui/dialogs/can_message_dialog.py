"""
CAN Message Configuration Dialog
Configures a single CAN message with signals
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List


class CANMessageDialog(QDialog):
    """Dialog for configuring a single CAN message."""

    SIGNAL_TYPES = ["uint8", "uint16", "uint32", "int8", "int16", "int32", "float", "bool"]
    BYTE_ORDERS = ["Little Endian", "Big Endian"]
    MAPPING_TYPES = ["Physical Input", "Physical Output", "Virtual Channel", "None"]

    def __init__(self, parent=None, message_config: Optional[Dict[str, Any]] = None,
                 can_id_list=None):
        super().__init__(parent)
        self.message_config = message_config
        self.can_id_list = can_id_list or []
        self.signals = []

        self.setWindowTitle("CAN Message Configuration")
        self.setModal(True)
        self.resize(700, 600)

        self._init_ui()

        if message_config:
            self._load_config(message_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings group
        basic_group = QGroupBox("Message Settings")
        basic_layout = QFormLayout()

        self.can_id_spin = QSpinBox()
        self.can_id_spin.setRange(0, 0x7FF)  # Standard CAN ID
        self.can_id_spin.setDisplayIntegerBase(16)
        self.can_id_spin.setPrefix("0x")
        self.can_id_spin.setToolTip("CAN Message ID (0x000-0x7FF)")
        basic_layout.addRow("CAN ID:", self.can_id_spin)

        self.extended_check = QCheckBox("Extended ID (29-bit)")
        self.extended_check.toggled.connect(self._on_extended_toggled)
        basic_layout.addRow("", self.extended_check)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Engine Data, Speed Info")
        basic_layout.addRow("Name: *", self.name_edit)

        self.period_spin = QSpinBox()
        self.period_spin.setRange(0, 10000)
        self.period_spin.setValue(100)
        self.period_spin.setSuffix(" ms")
        self.period_spin.setToolTip("Transmission period (0 = event-driven)")
        basic_layout.addRow("Period:", self.period_spin)

        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 8)
        self.dlc_spin.setValue(8)
        self.dlc_spin.setToolTip("Data Length Code (0-8 bytes)")
        basic_layout.addRow("DLC:", self.dlc_spin)

        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Transmit", "Receive"])
        basic_layout.addRow("Direction:", self.direction_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Signals group
        signals_group = QGroupBox("Signals")
        signals_layout = QVBoxLayout()

        # Signals table
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(6)
        self.signals_table.setHorizontalHeaderLabels([
            "Name", "Start Bit", "Length", "Type", "Byte Order", "Mapping"
        ])
        self.signals_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.signals_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        signals_layout.addWidget(self.signals_table)

        # Signal buttons
        signal_btn_layout = QHBoxLayout()

        self.add_signal_btn = QPushButton("Add Signal")
        self.add_signal_btn.clicked.connect(self._add_signal)
        signal_btn_layout.addWidget(self.add_signal_btn)

        self.remove_signal_btn = QPushButton("Remove Signal")
        self.remove_signal_btn.clicked.connect(self._remove_signal)
        signal_btn_layout.addWidget(self.remove_signal_btn)

        signal_btn_layout.addStretch()

        signals_layout.addLayout(signal_btn_layout)
        signals_group.setLayout(signals_layout)
        layout.addWidget(signals_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _on_extended_toggled(self, extended: bool):
        """Handle extended ID checkbox toggle."""
        if extended:
            self.can_id_spin.setRange(0, 0x1FFFFFFF)  # Extended CAN ID
        else:
            self.can_id_spin.setRange(0, 0x7FF)  # Standard CAN ID

    def _add_signal(self):
        """Add a new signal to the table."""
        row = self.signals_table.rowCount()
        self.signals_table.insertRow(row)

        # Name
        name_item = QTableWidgetItem(f"Signal_{row}")
        self.signals_table.setItem(row, 0, name_item)

        # Start Bit
        start_bit = QSpinBox()
        start_bit.setRange(0, 63)
        start_bit.setValue(row * 8)
        self.signals_table.setCellWidget(row, 1, start_bit)

        # Length
        length = QSpinBox()
        length.setRange(1, 64)
        length.setValue(8)
        self.signals_table.setCellWidget(row, 2, length)

        # Type
        sig_type = QComboBox()
        sig_type.addItems(self.SIGNAL_TYPES)
        self.signals_table.setCellWidget(row, 3, sig_type)

        # Byte Order
        byte_order = QComboBox()
        byte_order.addItems(self.BYTE_ORDERS)
        self.signals_table.setCellWidget(row, 4, byte_order)

        # Mapping
        mapping = QComboBox()
        mapping.addItems(self.MAPPING_TYPES)
        self.signals_table.setCellWidget(row, 5, mapping)

    def _remove_signal(self):
        """Remove selected signal from the table."""
        current_row = self.signals_table.currentRow()
        if current_row >= 0:
            self.signals_table.removeRow(current_row)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.can_id_spin.setValue(config.get("can_id", 0))
        self.extended_check.setChecked(config.get("extended", False))
        self.name_edit.setText(config.get("name", ""))
        self.period_spin.setValue(config.get("period_ms", 100))
        self.dlc_spin.setValue(config.get("dlc", 8))

        direction = config.get("direction", "Transmit")
        index = self.direction_combo.findText(direction)
        if index >= 0:
            self.direction_combo.setCurrentIndex(index)

        # Load signals
        signals = config.get("signals", [])
        for signal in signals:
            row = self.signals_table.rowCount()
            self.signals_table.insertRow(row)

            # Name
            name_item = QTableWidgetItem(signal.get("name", ""))
            self.signals_table.setItem(row, 0, name_item)

            # Start Bit
            start_bit = QSpinBox()
            start_bit.setRange(0, 63)
            start_bit.setValue(signal.get("start_bit", 0))
            self.signals_table.setCellWidget(row, 1, start_bit)

            # Length
            length = QSpinBox()
            length.setRange(1, 64)
            length.setValue(signal.get("length", 8))
            self.signals_table.setCellWidget(row, 2, length)

            # Type
            sig_type = QComboBox()
            sig_type.addItems(self.SIGNAL_TYPES)
            type_idx = sig_type.findText(signal.get("type", "uint8"))
            if type_idx >= 0:
                sig_type.setCurrentIndex(type_idx)
            self.signals_table.setCellWidget(row, 3, sig_type)

            # Byte Order
            byte_order = QComboBox()
            byte_order.addItems(self.BYTE_ORDERS)
            order_idx = byte_order.findText(signal.get("byte_order", "Little Endian"))
            if order_idx >= 0:
                byte_order.setCurrentIndex(order_idx)
            self.signals_table.setCellWidget(row, 4, byte_order)

            # Mapping
            mapping = QComboBox()
            mapping.addItems(self.MAPPING_TYPES)
            map_idx = mapping.findText(signal.get("mapping_type", "None"))
            if map_idx >= 0:
                mapping.setCurrentIndex(map_idx)
            self.signals_table.setCellWidget(row, 5, mapping)

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        # Parse signals from table
        signals = []
        for row in range(self.signals_table.rowCount()):
            name_item = self.signals_table.item(row, 0)
            start_bit_widget = self.signals_table.cellWidget(row, 1)
            length_widget = self.signals_table.cellWidget(row, 2)
            type_widget = self.signals_table.cellWidget(row, 3)
            byte_order_widget = self.signals_table.cellWidget(row, 4)
            mapping_widget = self.signals_table.cellWidget(row, 5)

            if name_item and start_bit_widget and length_widget:
                signals.append({
                    "name": name_item.text(),
                    "start_bit": start_bit_widget.value(),
                    "length": length_widget.value(),
                    "type": type_widget.currentText(),
                    "byte_order": byte_order_widget.currentText(),
                    "mapping_type": mapping_widget.currentText()
                })

        config = {
            "can_id": self.can_id_spin.value(),
            "extended": self.extended_check.isChecked(),
            "name": self.name_edit.text(),
            "period_ms": self.period_spin.value(),
            "dlc": self.dlc_spin.value(),
            "direction": self.direction_combo.currentText(),
            "signals": signals
        }

        return config

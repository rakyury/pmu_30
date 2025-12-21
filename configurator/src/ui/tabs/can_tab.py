"""
CAN Bus Configuration Tab
Manages CAN bus configuration and messages for PMU-30
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel, QGroupBox, QComboBox,
    QFileDialog, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..dialogs.can_message_dialog import CANMessageDialog
from typing import Dict, Any, List
import json


class CANTab(QWidget):
    """CAN Bus configuration tab."""

    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.can_messages = []
        self.can_config = {
            "bus_speed": 500000,
            "bus_enabled": True
        }
        self._init_ui()

    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)

        # Info label
        info_group = QGroupBox("CAN Bus Configuration")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "Configure CAN messages for communication with other ECUs.\n"
            "Supports standard (11-bit) and extended (29-bit) CAN IDs.\n"
            "Import DBC files for automatic message configuration."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Bus settings
        bus_settings_group = QGroupBox("Bus Settings")
        bus_layout = QFormLayout()

        self.bus_speed_combo = QComboBox()
        self.bus_speed_combo.addItems([
            "125 kbps", "250 kbps", "500 kbps", "1000 kbps"
        ])
        self.bus_speed_combo.setCurrentIndex(2)  # 500 kbps default
        self.bus_speed_combo.currentTextChanged.connect(self._on_bus_settings_changed)
        bus_layout.addRow("Bus Speed:", self.bus_speed_combo)

        bus_settings_group.setLayout(bus_layout)
        layout.addWidget(bus_settings_group)

        # Messages table
        messages_label = QLabel("CAN Messages")
        messages_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(messages_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "CAN ID", "Name", "Direction", "Period (ms)", "DLC", "Signals"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self.edit_message)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_msg_btn = QPushButton("Add Message")
        self.add_msg_btn.clicked.connect(self.add_message)
        button_layout.addWidget(self.add_msg_btn)

        self.edit_msg_btn = QPushButton("Edit")
        self.edit_msg_btn.clicked.connect(self.edit_message)
        button_layout.addWidget(self.edit_msg_btn)

        self.copy_msg_btn = QPushButton("Copy")
        self.copy_msg_btn.clicked.connect(self.copy_message)
        button_layout.addWidget(self.copy_msg_btn)

        self.delete_msg_btn = QPushButton("Delete")
        self.delete_msg_btn.clicked.connect(self.delete_message)
        button_layout.addWidget(self.delete_msg_btn)

        button_layout.addStretch()

        self.import_dbc_btn = QPushButton("Import DBC...")
        self.import_dbc_btn.clicked.connect(self.import_dbc)
        button_layout.addWidget(self.import_dbc_btn)

        self.export_dbc_btn = QPushButton("Export DBC...")
        self.export_dbc_btn.clicked.connect(self.export_dbc)
        button_layout.addWidget(self.export_dbc_btn)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_all_btn)

        layout.addLayout(button_layout)

        # Stats label
        self.stats_label = QLabel("Messages: 0 (TX: 0, RX: 0)")
        layout.addWidget(self.stats_label)

        self._update_table()

    def _on_bus_settings_changed(self):
        """Handle bus settings change."""
        speed_text = self.bus_speed_combo.currentText()
        speed_map = {
            "125 kbps": 125000,
            "250 kbps": 250000,
            "500 kbps": 500000,
            "1000 kbps": 1000000
        }
        self.can_config["bus_speed"] = speed_map.get(speed_text, 500000)
        self.configuration_changed.emit()

    def _update_table(self):
        """Update table with current CAN messages."""
        self.table.setRowCount(0)

        for idx, msg in enumerate(self.can_messages):
            row = self.table.rowCount()
            self.table.insertRow(row)

            # CAN ID
            can_id = msg.get("can_id", 0)
            extended = msg.get("extended", False)
            id_str = f"0x{can_id:03X}" if not extended else f"0x{can_id:08X}"
            can_id_item = QTableWidgetItem(id_str)
            can_id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, can_id_item)

            # Name
            name = QTableWidgetItem(msg.get("name", "Unnamed"))
            self.table.setItem(row, 1, name)

            # Direction
            direction = QTableWidgetItem(msg.get("direction", "Transmit"))
            direction.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, direction)

            # Period
            period = QTableWidgetItem(str(msg.get("period_ms", 0)))
            period.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, period)

            # DLC
            dlc = QTableWidgetItem(str(msg.get("dlc", 8)))
            dlc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, dlc)

            # Signals count
            signals = msg.get("signals", [])
            signals_item = QTableWidgetItem(f"{len(signals)} signals")
            signals_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, signals_item)

        self._update_stats()

    def _update_stats(self):
        """Update statistics label."""
        total = len(self.can_messages)
        tx = sum(1 for msg in self.can_messages if msg.get("direction") == "Transmit")
        rx = sum(1 for msg in self.can_messages if msg.get("direction") == "Receive")

        self.stats_label.setText(f"Messages: {total} (TX: {tx}, RX: {rx})")

    def _get_used_can_ids(self, exclude_index: int = -1) -> List[int]:
        """Get list of used CAN IDs."""
        used = []
        for idx, msg in enumerate(self.can_messages):
            if idx != exclude_index:
                can_id = msg.get("can_id")
                if can_id is not None:
                    used.append(can_id)
        return used

    def add_message(self):
        """Add new CAN message."""
        used_ids = self._get_used_can_ids()

        dialog = CANMessageDialog(
            self,
            message_config=None,
            can_id_list=used_ids
        )

        if dialog.exec():
            config = dialog.get_config()
            self.can_messages.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def edit_message(self):
        """Edit selected CAN message."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.can_messages):
            QMessageBox.warning(self, "No Selection", "Please select a message to edit.")
            return

        used_ids = self._get_used_can_ids(exclude_index=row)

        dialog = CANMessageDialog(
            self,
            message_config=self.can_messages[row],
            can_id_list=used_ids
        )

        if dialog.exec():
            config = dialog.get_config()
            self.can_messages[row] = config
            self._update_table()
            self.configuration_changed.emit()

    def copy_message(self):
        """Copy selected CAN message."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.can_messages):
            QMessageBox.warning(self, "No Selection", "Please select a message to copy.")
            return

        # Copy config
        import copy
        new_config = copy.deepcopy(self.can_messages[row])
        new_config["name"] = new_config.get("name", "") + " (Copy)"

        # Find next available CAN ID
        used_ids = self._get_used_can_ids()
        new_id = new_config.get("can_id", 0) + 1
        while new_id in used_ids and new_id < 0x7FF:
            new_id += 1

        new_config["can_id"] = new_id

        dialog = CANMessageDialog(
            self,
            message_config=new_config,
            can_id_list=used_ids
        )

        if dialog.exec():
            config = dialog.get_config()
            self.can_messages.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def delete_message(self):
        """Delete selected CAN message."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.can_messages):
            QMessageBox.warning(self, "No Selection", "Please select a message to delete.")
            return

        msg_name = self.can_messages[row].get("name", "Unnamed")

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete CAN message '{msg_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.can_messages[row]
            self._update_table()
            self.configuration_changed.emit()

    def clear_all(self):
        """Clear all CAN messages."""
        if not self.can_messages:
            return

        reply = QMessageBox.question(
            self, "Confirm Clear All",
            f"Delete all {len(self.can_messages)} CAN messages?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.can_messages.clear()
            self._update_table()
            self.configuration_changed.emit()

    def import_dbc(self):
        """Import CAN messages from DBC file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import DBC File",
            "",
            "DBC Files (*.dbc);;All Files (*)"
        )

        if filename:
            try:
                # TODO: Implement actual DBC parsing using cantools or similar
                QMessageBox.information(
                    self, "Import DBC",
                    f"DBC import from {filename} will be implemented.\n\n"
                    "This feature requires the 'cantools' library for parsing DBC files."
                )
                # Example placeholder for future implementation:
                # import cantools
                # db = cantools.database.load_file(filename)
                # for message in db.messages:
                #     self.can_messages.append({
                #         "can_id": message.frame_id,
                #         "name": message.name,
                #         "dlc": message.length,
                #         "signals": [...]
                #     })
                # self._update_table()
                # self.configuration_changed.emit()
            except Exception as e:
                QMessageBox.critical(
                    self, "Import Error",
                    f"Failed to import DBC file:\n{str(e)}"
                )

    def export_dbc(self):
        """Export CAN messages to DBC file."""
        if not self.can_messages:
            QMessageBox.warning(
                self, "No Messages",
                "No CAN messages to export."
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export DBC File",
            "",
            "DBC Files (*.dbc);;All Files (*)"
        )

        if filename:
            try:
                # TODO: Implement actual DBC generation using cantools or similar
                QMessageBox.information(
                    self, "Export DBC",
                    f"DBC export to {filename} will be implemented.\n\n"
                    "This feature requires the 'cantools' library for generating DBC files."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Error",
                    f"Failed to export DBC file:\n{str(e)}"
                )

    def load_configuration(self, config: dict):
        """Load CAN configuration."""
        can_config = config.get("can_buses", [])
        if can_config:
            # Load first bus (for now, single bus support)
            bus = can_config[0] if isinstance(can_config, list) else can_config
            self.can_config = bus.get("config", self.can_config)
            self.can_messages = bus.get("messages", [])

            # Update UI
            speed = self.can_config.get("bus_speed", 500000)
            speed_map = {
                125000: "125 kbps",
                250000: "250 kbps",
                500000: "500 kbps",
                1000000: "1000 kbps"
            }
            speed_text = speed_map.get(speed, "500 kbps")
            index = self.bus_speed_combo.findText(speed_text)
            if index >= 0:
                self.bus_speed_combo.setCurrentIndex(index)

        self._update_table()

    def get_configuration(self) -> dict:
        """Get current CAN configuration."""
        return {
            "can_buses": [{
                "name": "CAN1",
                "config": self.can_config,
                "messages": self.can_messages
            }]
        }

    def reset_to_defaults(self):
        """Reset to default configuration."""
        self.can_messages.clear()
        self.can_config = {
            "bus_speed": 500000,
            "bus_enabled": True
        }
        self.bus_speed_combo.setCurrentIndex(2)  # 500 kbps
        self._update_table()

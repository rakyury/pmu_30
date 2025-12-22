"""
CAN Messages Manager Dialog
Manages CAN Message Objects (Level 1 of two-level architecture)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any, List, Optional

from .can_message_dialog import CANMessageDialog


class CANMessagesManagerDialog(QDialog):
    """Dialog for managing CAN Message Objects."""

    messages_changed = pyqtSignal()

    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.can_messages = []

        # Load existing messages
        if config_manager:
            self.can_messages = list(config_manager.get_config().get("can_messages", []))

        self.setWindowTitle("CAN Messages Manager")
        self.setModal(True)
        self.resize(700, 500)

        self._init_ui()
        self._update_table()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "CAN Messages define the frame properties (ID, bus, timeout).\n"
            "CAN Inputs (signals) reference these messages to extract data."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Bus", "Base ID", "Type", "Timeout"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self._edit_message)
        layout.addWidget(self.table)

        # Buttons row
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Message")
        self.add_btn.clicked.connect(self._add_message)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_message)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_message)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self._duplicate_message)
        btn_layout.addWidget(self.duplicate_btn)

        layout.addLayout(btn_layout)

        # Stats
        self.stats_label = QLabel("Messages: 0")
        layout.addWidget(self.stats_label)

        # Dialog buttons
        dialog_btn_layout = QHBoxLayout()
        dialog_btn_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        self.ok_btn.setDefault(True)
        dialog_btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        dialog_btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(dialog_btn_layout)

    def _update_table(self):
        """Update table with current messages."""
        self.table.setRowCount(0)

        for msg in self.can_messages:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(msg.get("id", "")))

            # Name
            self.table.setItem(row, 1, QTableWidgetItem(msg.get("name", "")))

            # Bus
            bus_item = QTableWidgetItem(f"CAN {msg.get('can_bus', 1)}")
            bus_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, bus_item)

            # Base ID (hex)
            base_id = msg.get("base_id", 0)
            is_extended = msg.get("is_extended", False)
            id_str = f"0x{base_id:08X}" if is_extended else f"0x{base_id:03X}"
            id_item = QTableWidgetItem(id_str)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, id_item)

            # Type
            msg_type = msg.get("message_type", "normal")
            type_display = {
                "normal": "Normal",
                "compound": "Compound",
                "pmu1_rx": "PMU1",
                "pmu2_rx": "PMU2",
                "pmu3_rx": "PMU3"
            }.get(msg_type, msg_type)
            type_item = QTableWidgetItem(type_display)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, type_item)

            # Timeout
            timeout_item = QTableWidgetItem(f"{msg.get('timeout_ms', 500)} ms")
            timeout_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, timeout_item)

        self.stats_label.setText(f"Messages: {len(self.can_messages)}")

    def _get_existing_ids(self) -> List[str]:
        """Get list of existing message IDs."""
        return [msg.get("id", "") for msg in self.can_messages]

    def _add_message(self):
        """Add new CAN message."""
        existing_ids = self._get_existing_ids()

        dialog = CANMessageDialog(self, None, existing_ids)
        if dialog.exec():
            config = dialog.get_config()
            self.can_messages.append(config)
            self._update_table()

    def _edit_message(self):
        """Edit selected message."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.can_messages):
            QMessageBox.warning(self, "No Selection", "Please select a message to edit.")
            return

        existing_ids = self._get_existing_ids()

        dialog = CANMessageDialog(self, self.can_messages[row], existing_ids)
        if dialog.exec():
            self.can_messages[row] = dialog.get_config()
            self._update_table()

    def _delete_message(self):
        """Delete selected message."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.can_messages):
            QMessageBox.warning(self, "No Selection", "Please select a message to delete.")
            return

        msg_id = self.can_messages[row].get("id", "Unnamed")

        # Check if any CAN inputs reference this message
        if self.config_manager:
            channels = self.config_manager.get_config().get("channels", [])
            referencing = [
                ch.get("id", "?") for ch in channels
                if ch.get("channel_type") == "can_rx" and ch.get("message_ref") == msg_id
            ]

            if referencing:
                reply = QMessageBox.warning(
                    self, "Message In Use",
                    f"CAN message '{msg_id}' is referenced by {len(referencing)} CAN Input(s):\n"
                    f"{', '.join(referencing[:5])}{'...' if len(referencing) > 5 else ''}\n\n"
                    f"Delete anyway? (References will be broken)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        else:
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete CAN message '{msg_id}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        del self.can_messages[row]
        self._update_table()

    def _duplicate_message(self):
        """Duplicate selected message."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.can_messages):
            QMessageBox.warning(self, "No Selection", "Please select a message to duplicate.")
            return

        import copy
        new_msg = copy.deepcopy(self.can_messages[row])

        # Generate unique ID
        base_id = new_msg.get("id", "msg")
        existing_ids = self._get_existing_ids()
        counter = 1
        new_id = f"{base_id}_copy"
        while new_id in existing_ids:
            counter += 1
            new_id = f"{base_id}_copy{counter}"

        new_msg["id"] = new_id
        new_msg["name"] = new_msg.get("name", "") + " (Copy)"

        self.can_messages.append(new_msg)
        self._update_table()

    def _on_accept(self):
        """Save changes and close."""
        if self.config_manager:
            self.config_manager.get_config()["can_messages"] = self.can_messages
            self.config_manager.modified = True

        self.messages_changed.emit()
        self.accept()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get current messages list."""
        return self.can_messages

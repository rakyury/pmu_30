"""
CAN Bus Configuration Tab
Two-level architecture: CAN Messages (Level 1) + CAN Inputs (Level 2)

Based on Ecumaster PMU Client design pattern.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel, QGroupBox, QComboBox,
    QFileDialog, QFormLayout, QSplitter, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..dialogs.can_message_dialog import CANMessageDialog
from ..dialogs.can_input_dialog import CANInputDialog
from typing import Dict, Any, List, Optional
import copy


class CANTab(QWidget):
    """CAN Bus configuration tab with two-level architecture."""

    configuration_changed = pyqtSignal()

    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.can_messages = []  # Level 1: CAN Message Objects
        self.can_inputs = []    # Level 2: CAN Input channels (from channels array)
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
            "Configure CAN communication using a two-level architecture:\n"
            "1. CAN Messages - define frame properties (ID, bus, timeout)\n"
            "2. CAN Inputs - extract signals from messages (format, scaling)"
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

        # Splitter for two tables
        splitter = QSplitter(Qt.Orientation.Vertical)

        # === CAN Messages Section (Level 1) ===
        messages_widget = QWidget()
        messages_layout = QVBoxLayout(messages_widget)
        messages_layout.setContentsMargins(0, 0, 0, 0)

        messages_header = QLabel("CAN Messages")
        messages_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        messages_layout.addWidget(messages_header)

        self.messages_table = QTableWidget()
        self.messages_table.setColumnCount(6)
        self.messages_table.setHorizontalHeaderLabels([
            "ID", "Name", "Bus", "Base ID", "Type", "Timeout"
        ])
        self.messages_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.messages_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.messages_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.messages_table.itemDoubleClicked.connect(self._edit_message)
        self.messages_table.itemSelectionChanged.connect(self._on_message_selection_changed)
        messages_layout.addWidget(self.messages_table)

        # Message buttons
        msg_btn_layout = QHBoxLayout()

        self.add_msg_btn = QPushButton("Add Message")
        self.add_msg_btn.clicked.connect(self._add_message)
        msg_btn_layout.addWidget(self.add_msg_btn)

        self.edit_msg_btn = QPushButton("Edit")
        self.edit_msg_btn.clicked.connect(self._edit_message)
        msg_btn_layout.addWidget(self.edit_msg_btn)

        self.delete_msg_btn = QPushButton("Delete")
        self.delete_msg_btn.clicked.connect(self._delete_message)
        msg_btn_layout.addWidget(self.delete_msg_btn)

        msg_btn_layout.addStretch()

        self.import_dbc_btn = QPushButton("Import DBC...")
        self.import_dbc_btn.clicked.connect(self._import_dbc)
        msg_btn_layout.addWidget(self.import_dbc_btn)

        messages_layout.addLayout(msg_btn_layout)

        self.msg_stats_label = QLabel("Messages: 0")
        messages_layout.addWidget(self.msg_stats_label)

        splitter.addWidget(messages_widget)

        # === CAN Inputs Section (Level 2) ===
        inputs_widget = QWidget()
        inputs_layout = QVBoxLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 0, 0, 0)

        inputs_header = QLabel("CAN Inputs (Signals)")
        inputs_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        inputs_layout.addWidget(inputs_header)

        self.inputs_table = QTableWidget()
        self.inputs_table.setColumnCount(4)
        self.inputs_table.setHorizontalHeaderLabels([
            "Channel ID", "Message", "Format", "Scale"
        ])
        self.inputs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.inputs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.inputs_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.inputs_table.itemDoubleClicked.connect(self._edit_input)
        inputs_layout.addWidget(self.inputs_table)

        # Input buttons
        input_btn_layout = QHBoxLayout()

        self.add_input_btn = QPushButton("Add Input")
        self.add_input_btn.clicked.connect(self._add_input)
        input_btn_layout.addWidget(self.add_input_btn)

        self.edit_input_btn = QPushButton("Edit")
        self.edit_input_btn.clicked.connect(self._edit_input)
        input_btn_layout.addWidget(self.edit_input_btn)

        self.delete_input_btn = QPushButton("Delete")
        self.delete_input_btn.clicked.connect(self._delete_input)
        input_btn_layout.addWidget(self.delete_input_btn)

        input_btn_layout.addStretch()

        self.filter_check = QCheckBox("Filter by selected message")
        self.filter_check.stateChanged.connect(self._update_inputs_table)
        input_btn_layout.addWidget(self.filter_check)

        inputs_layout.addLayout(input_btn_layout)

        self.input_stats_label = QLabel("Inputs: 0")
        inputs_layout.addWidget(self.input_stats_label)

        splitter.addWidget(inputs_widget)

        # Set initial splitter sizes
        splitter.setSizes([300, 300])

        layout.addWidget(splitter)

        self._update_messages_table()
        self._update_inputs_table()

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

    def _on_message_selection_changed(self):
        """Handle message selection change."""
        if self.filter_check.isChecked():
            self._update_inputs_table()

    # ========== Messages Table (Level 1) ==========

    def _update_messages_table(self):
        """Update messages table with current CAN messages."""
        self.messages_table.setRowCount(0)

        for idx, msg in enumerate(self.can_messages):
            row = self.messages_table.rowCount()
            self.messages_table.insertRow(row)

            # ID
            msg_id = QTableWidgetItem(msg.get("id", ""))
            self.messages_table.setItem(row, 0, msg_id)

            # Name
            name = QTableWidgetItem(msg.get("name", ""))
            self.messages_table.setItem(row, 1, name)

            # Bus
            can_bus = QTableWidgetItem(f"CAN {msg.get('can_bus', 1)}")
            can_bus.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.messages_table.setItem(row, 2, can_bus)

            # Base ID (hex)
            base_id = msg.get("base_id", 0)
            is_extended = msg.get("is_extended", False)
            id_str = f"0x{base_id:08X}" if is_extended else f"0x{base_id:03X}"
            base_id_item = QTableWidgetItem(id_str)
            base_id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.messages_table.setItem(row, 3, base_id_item)

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
            self.messages_table.setItem(row, 4, type_item)

            # Timeout
            timeout = QTableWidgetItem(f"{msg.get('timeout_ms', 500)} ms")
            timeout.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.messages_table.setItem(row, 5, timeout)

        self.msg_stats_label.setText(f"Messages: {len(self.can_messages)}")

    def _get_message_ids(self) -> List[str]:
        """Get list of message IDs."""
        return [msg.get("id", "") for msg in self.can_messages]

    def _add_message(self):
        """Add new CAN message."""
        existing_ids = self._get_message_ids()

        dialog = CANMessageDialog(
            self,
            message_config=None,
            existing_ids=existing_ids
        )

        if dialog.exec():
            config = dialog.get_config()
            self.can_messages.append(config)
            self._update_messages_table()
            self.configuration_changed.emit()

    def _edit_message(self):
        """Edit selected CAN message."""
        row = self.messages_table.currentRow()
        if row < 0 or row >= len(self.can_messages):
            QMessageBox.warning(self, "No Selection", "Please select a message to edit.")
            return

        existing_ids = self._get_message_ids()

        dialog = CANMessageDialog(
            self,
            message_config=self.can_messages[row],
            existing_ids=existing_ids
        )

        if dialog.exec():
            old_id = self.can_messages[row].get("id", "")
            config = dialog.get_config()
            new_id = config.get("id", "")

            # Update message references in inputs if ID changed
            if old_id != new_id:
                for inp in self.can_inputs:
                    if inp.get("message_ref") == old_id:
                        inp["message_ref"] = new_id

            self.can_messages[row] = config
            self._update_messages_table()
            self._update_inputs_table()
            self.configuration_changed.emit()

    def _delete_message(self):
        """Delete selected CAN message."""
        row = self.messages_table.currentRow()
        if row < 0 or row >= len(self.can_messages):
            QMessageBox.warning(self, "No Selection", "Please select a message to delete.")
            return

        msg_id = self.can_messages[row].get("id", "Unnamed")

        # Check if any inputs reference this message
        referencing_inputs = [
            inp.get("id", "?") for inp in self.can_inputs
            if inp.get("message_ref") == msg_id
        ]

        if referencing_inputs:
            reply = QMessageBox.warning(
                self, "Message In Use",
                f"CAN message '{msg_id}' is referenced by {len(referencing_inputs)} input(s):\n"
                f"{', '.join(referencing_inputs[:5])}{'...' if len(referencing_inputs) > 5 else ''}\n\n"
                f"Delete message and remove references?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # Remove references
            for inp in self.can_inputs:
                if inp.get("message_ref") == msg_id:
                    inp["message_ref"] = ""
        else:
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete CAN message '{msg_id}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        del self.can_messages[row]
        self._update_messages_table()
        self._update_inputs_table()
        self.configuration_changed.emit()

    # ========== Inputs Table (Level 2) ==========

    def _update_inputs_table(self):
        """Update inputs table with current CAN inputs."""
        self.inputs_table.setRowCount(0)

        # Get selected message ID for filtering
        filter_message_id = None
        if self.filter_check.isChecked():
            row = self.messages_table.currentRow()
            if row >= 0 and row < len(self.can_messages):
                filter_message_id = self.can_messages[row].get("id")

        shown_count = 0
        for idx, inp in enumerate(self.can_inputs):
            # Apply filter
            if filter_message_id and inp.get("message_ref") != filter_message_id:
                continue

            row = self.inputs_table.rowCount()
            self.inputs_table.insertRow(row)
            shown_count += 1

            # Store original index for editing
            self.inputs_table.setItem(row, 0, QTableWidgetItem(inp.get("id", "")))

            # Message reference
            message_ref = QTableWidgetItem(inp.get("message_ref", ""))
            self.inputs_table.setItem(row, 1, message_ref)

            # Format (e.g., "U16 LE")
            data_type = inp.get("data_type", "unsigned")
            if hasattr(data_type, 'value'):
                data_type = data_type.value
            data_format = inp.get("data_format", "16bit")
            if hasattr(data_format, 'value'):
                data_format = data_format.value
            byte_order = inp.get("byte_order", "little_endian")

            type_short = {"unsigned": "U", "signed": "S", "float": "F"}.get(data_type, "?")
            format_short = {"8bit": "8", "16bit": "16", "32bit": "32", "custom": "C"}.get(data_format, "?")
            order_short = "LE" if byte_order == "little_endian" else "BE"

            format_str = f"{type_short}{format_short} {order_short}"
            format_item = QTableWidgetItem(format_str)
            format_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.inputs_table.setItem(row, 2, format_item)

            # Scale
            multiplier = inp.get("multiplier", 1.0)
            divider = inp.get("divider", 1.0)
            offset = inp.get("offset", 0.0)
            scale_parts = []
            if multiplier != 1.0:
                scale_parts.append(f"x{multiplier}")
            if divider != 1.0:
                scale_parts.append(f"/{divider}")
            if offset != 0.0:
                scale_parts.append(f"+{offset}" if offset > 0 else f"{offset}")
            scale_str = " ".join(scale_parts) if scale_parts else "1:1"
            scale_item = QTableWidgetItem(scale_str)
            scale_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.inputs_table.setItem(row, 3, scale_item)

        if filter_message_id:
            self.input_stats_label.setText(f"Inputs: {shown_count} (filtered from {len(self.can_inputs)})")
        else:
            self.input_stats_label.setText(f"Inputs: {len(self.can_inputs)}")

    def _get_input_ids(self) -> List[str]:
        """Get list of CAN input channel IDs."""
        return [inp.get("id", "") for inp in self.can_inputs]

    def _find_input_index(self, channel_id: str) -> int:
        """Find index of input by channel ID."""
        for i, inp in enumerate(self.can_inputs):
            if inp.get("id") == channel_id:
                return i
        return -1

    def _add_input(self):
        """Add new CAN input."""
        message_ids = self._get_message_ids()
        if not message_ids:
            QMessageBox.warning(
                self, "No Messages",
                "Please create at least one CAN message before adding inputs."
            )
            return

        existing_ids = self._get_input_ids()
        if self.config_manager:
            # Also include other channel IDs
            all_channel_ids = [ch.get("id", "") for ch in self.config_manager.get_all_channels()]
            existing_ids = list(set(existing_ids + all_channel_ids))

        dialog = CANInputDialog(
            self,
            input_config=None,
            message_ids=message_ids,
            existing_channel_ids=existing_ids
        )

        if dialog.exec():
            config = dialog.get_config()
            self.can_inputs.append(config)
            self._update_inputs_table()
            self.configuration_changed.emit()

    def _edit_input(self):
        """Edit selected CAN input."""
        row = self.inputs_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an input to edit.")
            return

        # Get channel ID from table
        id_item = self.inputs_table.item(row, 0)
        if not id_item:
            return

        channel_id = id_item.text()
        original_index = self._find_input_index(channel_id)
        if original_index < 0:
            return

        message_ids = self._get_message_ids()
        existing_ids = self._get_input_ids()
        if self.config_manager:
            all_channel_ids = [ch.get("id", "") for ch in self.config_manager.get_all_channels()]
            existing_ids = list(set(existing_ids + all_channel_ids))

        dialog = CANInputDialog(
            self,
            input_config=self.can_inputs[original_index],
            message_ids=message_ids,
            existing_channel_ids=existing_ids
        )

        if dialog.exec():
            config = dialog.get_config()
            self.can_inputs[original_index] = config
            self._update_inputs_table()
            self.configuration_changed.emit()

    def _delete_input(self):
        """Delete selected CAN input."""
        row = self.inputs_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an input to delete.")
            return

        # Get channel ID from table
        id_item = self.inputs_table.item(row, 0)
        if not id_item:
            return

        channel_id = id_item.text()
        original_index = self._find_input_index(channel_id)
        if original_index < 0:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete CAN input '{channel_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.can_inputs[original_index]
            self._update_inputs_table()
            self.configuration_changed.emit()

    # ========== DBC Import ==========

    def _import_dbc(self):
        """Import CAN messages from DBC file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import DBC File",
            "",
            "DBC Files (*.dbc);;All Files (*)"
        )

        if filename:
            try:
                # TODO: Implement actual DBC parsing using cantools
                QMessageBox.information(
                    self, "Import DBC",
                    f"DBC import from {filename} will be implemented.\n\n"
                    "This feature requires the 'cantools' library for parsing DBC files.\n\n"
                    "Install with: pip install cantools"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Import Error",
                    f"Failed to import DBC file:\n{str(e)}"
                )

    # ========== Configuration Load/Save ==========

    def load_configuration(self, config: dict):
        """Load CAN configuration from config dict."""
        # Load CAN messages (Level 1) from can_messages array
        self.can_messages = config.get("can_messages", [])

        # Load CAN inputs (Level 2) from channels array
        channels = config.get("channels", [])
        self.can_inputs = [
            ch for ch in channels
            if ch.get("channel_type") == "can_rx"
        ]

        # Load bus settings
        can_buses = config.get("can_buses", [])
        if can_buses and isinstance(can_buses, list) and len(can_buses) > 0:
            bus = can_buses[0]
            self.can_config = {
                "bus_speed": bus.get("bitrate", 500000),
                "bus_enabled": bus.get("enabled", True)
            }

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

        self._update_messages_table()
        self._update_inputs_table()

    def get_configuration(self) -> dict:
        """Get current CAN configuration for saving."""
        return {
            "can_messages": self.can_messages,
            "can_inputs": self.can_inputs,  # Will be merged into channels array
            "can_buses": [{
                "bus": 1,
                "enabled": self.can_config.get("bus_enabled", True),
                "bitrate": self.can_config.get("bus_speed", 500000),
                "fd_enabled": False
            }]
        }

    def get_can_messages(self) -> List[Dict[str, Any]]:
        """Get CAN messages for config_manager."""
        return self.can_messages

    def get_can_inputs(self) -> List[Dict[str, Any]]:
        """Get CAN inputs for config_manager (to merge into channels)."""
        return self.can_inputs

    def reset_to_defaults(self):
        """Reset to default configuration."""
        self.can_messages.clear()
        self.can_inputs.clear()
        self.can_config = {
            "bus_speed": 500000,
            "bus_enabled": True
        }
        self.bus_speed_combo.setCurrentIndex(2)  # 500 kbps
        self._update_messages_table()
        self._update_inputs_table()

"""
Logic Engine Tab
Manages logic functions and virtual channels for PMU-30
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..dialogs.logic_function_dialog import LogicFunctionDialog
from typing import Dict, Any, List


class LogicTab(QWidget):
    """Logic Engine configuration tab."""

    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logic_functions = []
        self._init_ui()

    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)

        # Info label
        info_group = QGroupBox("Logic Engine")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "Configure logic functions using physical inputs/outputs and 256 virtual channels.\n"
            "Supports: AND, OR, NOT, XOR, Timers, Counters, Comparisons, Math operations."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Virtual channels info
        virt_info = QLabel("Virtual Channels: 256 available (0-255)")
        virt_info.setStyleSheet("color: #0078d4; font-weight: bold;")
        layout.addWidget(virt_info)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Virtual Ch", "Name", "Operation", "Inputs"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self.edit_function)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Function")
        self.add_btn.clicked.connect(self.add_function)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_function)
        button_layout.addWidget(self.edit_btn)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self.copy_function)
        button_layout.addWidget(self.copy_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_function)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)

        # Stats label
        self.stats_label = QLabel("Functions: 0 / Virtual Channels Used: 0")
        layout.addWidget(self.stats_label)

        self._update_table()

    def _update_table(self):
        """Update table with current logic functions."""
        self.table.setRowCount(0)

        for idx, func in enumerate(self.logic_functions):
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Virtual channel
            virt_ch = QTableWidgetItem(str(func.get("virtual_channel", 0)))
            virt_ch.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, virt_ch)

            # Name
            name = QTableWidgetItem(func.get("name", "Unnamed"))
            self.table.setItem(row, 1, name)

            # Operation
            operation = QTableWidgetItem(func.get("operation", "AND"))
            self.table.setItem(row, 2, operation)

            # Inputs summary
            inputs = func.get("inputs", [])
            inputs_str = f"{len(inputs)} inputs"
            inputs_item = QTableWidgetItem(inputs_str)
            self.table.setItem(row, 3, inputs_item)

        self._update_stats()

    def _update_stats(self):
        """Update statistics label."""
        func_count = len(self.logic_functions)

        # Count unique virtual channels
        used_channels = set()
        for func in self.logic_functions:
            vch = func.get("virtual_channel")
            if vch is not None:
                used_channels.add(vch)

        self.stats_label.setText(
            f"Functions: {func_count} / Virtual Channels Used: {len(used_channels)}/256"
        )

    def _get_used_virtual_channels(self, exclude_index: int = -1) -> List[int]:
        """Get list of used virtual channel numbers."""
        used = []
        for idx, func in enumerate(self.logic_functions):
            if idx != exclude_index:
                vch = func.get("virtual_channel")
                if vch is not None:
                    used.append(vch)
        return used

    def add_function(self):
        """Add new logic function."""
        used_channels = self._get_used_virtual_channels()

        # Find next available virtual channel
        next_channel = 0
        for ch in range(256):
            if ch not in used_channels:
                next_channel = ch
                break

        dialog = LogicFunctionDialog(
            self,
            function_config={"virtual_channel": next_channel},
            used_channels=used_channels
        )

        if dialog.exec():
            config = dialog.get_config()
            self.logic_functions.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def edit_function(self):
        """Edit selected logic function."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.logic_functions):
            QMessageBox.warning(self, "No Selection", "Please select a function to edit.")
            return

        used_channels = self._get_used_virtual_channels(exclude_index=row)

        dialog = LogicFunctionDialog(
            self,
            function_config=self.logic_functions[row],
            used_channels=used_channels
        )

        if dialog.exec():
            config = dialog.get_config()
            self.logic_functions[row] = config
            self._update_table()
            self.configuration_changed.emit()

    def copy_function(self):
        """Copy selected logic function."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.logic_functions):
            QMessageBox.warning(self, "No Selection", "Please select a function to copy.")
            return

        used_channels = self._get_used_virtual_channels()

        # Find next available virtual channel
        next_channel = 0
        for ch in range(256):
            if ch not in used_channels:
                next_channel = ch
                break

        if next_channel >= 256:
            QMessageBox.warning(
                self, "No Channels Available",
                "All 256 virtual channels are in use. Cannot copy function."
            )
            return

        # Copy config and update channel
        import copy
        new_config = copy.deepcopy(self.logic_functions[row])
        new_config["virtual_channel"] = next_channel
        new_config["name"] = new_config.get("name", "") + " (Copy)"

        dialog = LogicFunctionDialog(
            self,
            function_config=new_config,
            used_channels=used_channels
        )

        if dialog.exec():
            config = dialog.get_config()
            self.logic_functions.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def delete_function(self):
        """Delete selected logic function."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.logic_functions):
            QMessageBox.warning(self, "No Selection", "Please select a function to delete.")
            return

        func_name = self.logic_functions[row].get("name", "Unnamed")

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete logic function '{func_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.logic_functions[row]
            self._update_table()
            self.configuration_changed.emit()

    def clear_all(self):
        """Clear all logic functions."""
        if not self.logic_functions:
            return

        reply = QMessageBox.question(
            self, "Confirm Clear All",
            f"Delete all {len(self.logic_functions)} logic functions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.logic_functions.clear()
            self._update_table()
            self.configuration_changed.emit()

    def load_configuration(self, config: dict):
        """Load logic functions from configuration."""
        self.logic_functions = config.get("logic_functions", [])
        self._update_table()

    def get_configuration(self) -> dict:
        """Get current logic functions configuration."""
        return {
            "logic_functions": self.logic_functions
        }

    def reset_to_defaults(self):
        """Reset to default configuration."""
        self.logic_functions.clear()
        self._update_table()

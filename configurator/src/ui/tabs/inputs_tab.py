"""
Inputs Tab - CRUD interface for 20 universal input channels
"""

from .base_tab import BaseTab
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt
from ..dialogs.input_config_dialog import InputConfigDialog
from typing import Dict, Any, List


class InputsTab(BaseTab):
    """Tab for configuring 20 universal input channels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("<b>20 Universal Input Channels</b>")
        header.setStyleSheet("font-size: 14px; padding: 5px;")
        layout.addWidget(header)

        # Info label
        info = QLabel(
            "Configure analog/digital inputs: switches, rotary switches, analog sensors, frequency inputs"
        )
        info.setStyleSheet("color: #888; padding: 2px;")
        layout.addWidget(info)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Channel", "Name", "Type", "Parameters", "Pull-up", "Filter"
        ])

        # Configure table appearance
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.doubleClicked.connect(self._on_edit)

        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Input")
        self.add_btn.clicked.connect(self._on_add)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._on_edit)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._on_delete)
        button_layout.addWidget(self.delete_btn)

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self._on_duplicate)
        button_layout.addWidget(self.duplicate_btn)

        button_layout.addStretch()

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self._on_clear_all)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)

        # Update button states
        self._update_buttons()

    def _update_table(self):
        """Update table with current inputs."""
        self.table.setRowCount(len(self.inputs))

        for row, input_cfg in enumerate(self.inputs):
            # Channel
            channel_item = QTableWidgetItem(str(input_cfg.get("channel", 0)))
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, channel_item)

            # Name
            name_item = QTableWidgetItem(input_cfg.get("name", ""))
            self.table.setItem(row, 1, name_item)

            # Type
            type_item = QTableWidgetItem(input_cfg.get("type", ""))
            self.table.setItem(row, 2, type_item)

            # Parameters (formatted summary)
            params = input_cfg.get("parameters", {})
            params_text = self._format_parameters(input_cfg.get("type", ""), params)
            params_item = QTableWidgetItem(params_text)
            self.table.setItem(row, 3, params_item)

            # Pull-up
            pullup_text = "Yes" if input_cfg.get("pull_up", False) else "No"
            pullup_item = QTableWidgetItem(pullup_text)
            pullup_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, pullup_item)

            # Filter
            filter_item = QTableWidgetItem(str(input_cfg.get("filter_samples", 5)))
            filter_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, filter_item)

        self._update_buttons()

    def _format_parameters(self, input_type: str, params: Dict[str, Any]) -> str:
        """Format parameters for display."""
        if input_type in ["Switch Active Low", "Switch Active High"]:
            return f"Threshold: {params.get('threshold', 2.5)}V, Debounce: {params.get('debounce_ms', 50)}ms"

        elif input_type == "Rotary Switch":
            return f"{params.get('positions', 4)} positions, Debounce: {params.get('debounce_ms', 50)}ms"

        elif input_type == "Linear Analog":
            return f"Range: {params.get('min_voltage', 0.0)}V - {params.get('max_voltage', 5.0)}V"

        elif input_type == "Calibrated Analog":
            mult = params.get('multiplier', 1.0)
            offset = params.get('offset', 0.0)
            unit = params.get('unit', '')
            return f"y = {mult}x + {offset} {unit}"

        elif input_type == "Frequency Input":
            return f"Range: {params.get('min_freq', 0.0)} - {params.get('max_freq', 1000.0)}Hz"

        return ""

    def _update_buttons(self):
        """Update button enabled states."""
        has_selection = len(self.table.selectedItems()) > 0
        has_inputs = len(self.inputs) > 0
        can_add = len(self.inputs) < 20

        self.add_btn.setEnabled(can_add)
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.duplicate_btn.setEnabled(has_selection and can_add)
        self.clear_btn.setEnabled(has_inputs)

        # Update add button text
        if can_add:
            self.add_btn.setText(f"Add Input ({len(self.inputs)}/20)")
        else:
            self.add_btn.setText("Maximum Reached (20/20)")

    def _get_used_channels(self, exclude_index: int = -1) -> List[int]:
        """Get list of used channel numbers, optionally excluding an index."""
        used = []
        for i, input_cfg in enumerate(self.inputs):
            if i != exclude_index:
                used.append(input_cfg.get("channel", 0))
        return used

    def _on_add(self):
        """Add new input."""
        if len(self.inputs) >= 20:
            QMessageBox.warning(self, "Maximum Inputs", "Maximum 20 inputs allowed.")
            return

        # Find first unused channel
        used_channels = self._get_used_channels()
        next_channel = 0
        for ch in range(20):
            if ch not in used_channels:
                next_channel = ch
                break

        dialog = InputConfigDialog(
            self,
            input_config={"channel": next_channel},
            used_channels=used_channels
        )

        if dialog.exec():
            config = dialog.get_config()

            # Validate channel not in use
            if config["channel"] in used_channels:
                QMessageBox.warning(
                    self, "Channel In Use",
                    f"Channel {config['channel']} is already configured."
                )
                return

            self.inputs.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def _on_edit(self):
        """Edit selected input."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.inputs):
            return

        used_channels = self._get_used_channels(exclude_index=row)

        dialog = InputConfigDialog(
            self,
            input_config=self.inputs[row],
            used_channels=used_channels
        )

        if dialog.exec():
            config = dialog.get_config()

            # Validate channel not in use by another input
            if config["channel"] in used_channels:
                QMessageBox.warning(
                    self, "Channel In Use",
                    f"Channel {config['channel']} is already configured by another input."
                )
                return

            self.inputs[row] = config
            self._update_table()
            self.configuration_changed.emit()

    def _on_delete(self):
        """Delete selected input."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.inputs):
            return

        input_cfg = self.inputs[row]
        reply = QMessageBox.question(
            self, "Delete Input",
            f"Delete input '{input_cfg.get('name', 'Unnamed')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.inputs[row]
            self._update_table()
            self.configuration_changed.emit()

    def _on_duplicate(self):
        """Duplicate selected input."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.inputs):
            return

        if len(self.inputs) >= 20:
            QMessageBox.warning(self, "Maximum Inputs", "Maximum 20 inputs allowed.")
            return

        # Create copy with next available channel
        used_channels = self._get_used_channels()
        next_channel = 0
        for ch in range(20):
            if ch not in used_channels:
                next_channel = ch
                break

        # Deep copy config
        import copy
        new_config = copy.deepcopy(self.inputs[row])
        new_config["channel"] = next_channel
        new_config["name"] = new_config.get("name", "") + " (Copy)"

        dialog = InputConfigDialog(
            self,
            input_config=new_config,
            used_channels=used_channels
        )

        if dialog.exec():
            config = dialog.get_config()

            # Validate channel
            if config["channel"] in used_channels:
                QMessageBox.warning(
                    self, "Channel In Use",
                    f"Channel {config['channel']} is already configured."
                )
                return

            self.inputs.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def _on_clear_all(self):
        """Clear all inputs."""
        if not self.inputs:
            return

        reply = QMessageBox.question(
            self, "Clear All Inputs",
            f"Delete all {len(self.inputs)} input configurations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.inputs.clear()
            self._update_table()
            self.configuration_changed.emit()

    def load_configuration(self, config: dict):
        """Load configuration from dict."""
        self.inputs = config.get("inputs", [])
        self._update_table()

    def get_configuration(self) -> dict:
        """Get configuration as dict."""
        return {"inputs": self.inputs}

    def reset_to_defaults(self):
        """Reset to default configuration."""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "Clear all input configurations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.inputs.clear()
            self._update_table()
            self.configuration_changed.emit()

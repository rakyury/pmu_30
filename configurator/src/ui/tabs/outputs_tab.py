"""
Outputs Tab - CRUD interface for 30 PROFET 2 output channels
"""

from .base_tab import BaseTab
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt
from ..dialogs.output_config_dialog import OutputConfigDialog
from typing import Dict, Any, List


class OutputsTab(BaseTab):
    """Tab for configuring 30 PROFET 2 output channels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.outputs: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("<b>30 PROFET 2 High-Side Switch Outputs</b>")
        header.setStyleSheet("font-size: 14px; padding: 5px;")
        layout.addWidget(header)

        # Info label
        info = QLabel(
            "Configure intelligent high-side switches with current sensing, "
            "overcurrent protection, and PWM capability"
        )
        info.setStyleSheet("color: #888; padding: 2px;")
        layout.addWidget(info)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Ch", "Name", "Enabled", "Current Limit", "PWM", "Diagnostics", "Status"
        ])

        # Configure table appearance
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.doubleClicked.connect(self._on_edit)

        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Output")
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
        """Update table with current outputs."""
        self.table.setRowCount(len(self.outputs))

        for row, output_cfg in enumerate(self.outputs):
            # Channel
            channel_item = QTableWidgetItem(str(output_cfg.get("channel", 0)))
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, channel_item)

            # Name
            name_item = QTableWidgetItem(output_cfg.get("name", ""))
            self.table.setItem(row, 1, name_item)

            # Enabled
            enabled_text = "Yes" if output_cfg.get("enabled", True) else "No"
            enabled_item = QTableWidgetItem(enabled_text)
            enabled_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, enabled_item)

            # Current Limit
            protection = output_cfg.get("protection", {})
            current_limit = protection.get("current_limit", 10.0)
            current_item = QTableWidgetItem(f"{current_limit:.1f} A")
            current_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, current_item)

            # PWM
            pwm = output_cfg.get("pwm", {})
            if pwm.get("enabled", False):
                pwm_text = f"{pwm.get('frequency', 1000)} Hz"
            else:
                pwm_text = "Off"
            pwm_item = QTableWidgetItem(pwm_text)
            pwm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, pwm_item)

            # Diagnostics
            advanced = output_cfg.get("advanced", {})
            diag_text = "On" if advanced.get("diagnostics", True) else "Off"
            diag_item = QTableWidgetItem(diag_text)
            diag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, diag_item)

            # Status (summary)
            status = self._get_status_summary(output_cfg)
            status_item = QTableWidgetItem(status)
            self.table.setItem(row, 6, status_item)

        self._update_buttons()

    def _get_status_summary(self, output_cfg: Dict[str, Any]) -> str:
        """Get status summary for output."""
        if not output_cfg.get("enabled", True):
            return "Disabled"

        protection = output_cfg.get("protection", {})
        pwm = output_cfg.get("pwm", {})

        parts = []
        parts.append(f"≤{protection.get('current_limit', 10.0):.1f}A")

        if pwm.get("enabled", False):
            parts.append(f"PWM {pwm.get('default_duty', 50):.0f}%")

        return ", ".join(parts)

    def _update_buttons(self):
        """Update button enabled states."""
        has_selection = len(self.table.selectedItems()) > 0
        has_outputs = len(self.outputs) > 0
        can_add = len(self.outputs) < 30

        self.add_btn.setEnabled(can_add)
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.duplicate_btn.setEnabled(has_selection and can_add)
        self.clear_btn.setEnabled(has_outputs)

        # Update add button text
        if can_add:
            self.add_btn.setText(f"Add Output ({len(self.outputs)}/30)")
        else:
            self.add_btn.setText("Maximum Reached (30/30)")

    def _get_used_channels(self, exclude_index: int = -1) -> List[int]:
        """Get list of used channel numbers, optionally excluding an index."""
        used = []
        for i, output_cfg in enumerate(self.outputs):
            if i != exclude_index:
                used.append(output_cfg.get("channel", 0))
        return used

    def _on_add(self):
        """Add new output."""
        if len(self.outputs) >= 30:
            QMessageBox.warning(self, "Maximum Outputs", "Maximum 30 outputs allowed.")
            return

        # Find first unused channel
        used_channels = self._get_used_channels()
        next_channel = 0
        for ch in range(30):
            if ch not in used_channels:
                next_channel = ch
                break

        dialog = OutputConfigDialog(
            self,
            output_config={"channel": next_channel},
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

            self.outputs.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def _on_edit(self):
        """Edit selected output."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.outputs):
            return

        used_channels = self._get_used_channels(exclude_index=row)

        dialog = OutputConfigDialog(
            self,
            output_config=self.outputs[row],
            used_channels=used_channels
        )

        if dialog.exec():
            config = dialog.get_config()

            # Validate channel not in use by another output
            if config["channel"] in used_channels:
                QMessageBox.warning(
                    self, "Channel In Use",
                    f"Channel {config['channel']} is already configured by another output."
                )
                return

            self.outputs[row] = config
            self._update_table()
            self.configuration_changed.emit()

    def _on_delete(self):
        """Delete selected output."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.outputs):
            return

        output_cfg = self.outputs[row]
        reply = QMessageBox.question(
            self, "Delete Output",
            f"Delete output '{output_cfg.get('name', 'Unnamed')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.outputs[row]
            self._update_table()
            self.configuration_changed.emit()

    def _on_duplicate(self):
        """Duplicate selected output."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.outputs):
            return

        if len(self.outputs) >= 30:
            QMessageBox.warning(self, "Maximum Outputs", "Maximum 30 outputs allowed.")
            return

        # Create copy with next available channel
        used_channels = self._get_used_channels()
        next_channel = 0
        for ch in range(30):
            if ch not in used_channels:
                next_channel = ch
                break

        # Deep copy config
        import copy
        new_config = copy.deepcopy(self.outputs[row])
        new_config["channel"] = next_channel
        new_config["name"] = new_config.get("name", "") + " (Copy)"

        dialog = OutputConfigDialog(
            self,
            output_config=new_config,
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

            self.outputs.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def _on_clear_all(self):
        """Clear all outputs."""
        if not self.outputs:
            return

        reply = QMessageBox.question(
            self, "Clear All Outputs",
            f"Delete all {len(self.outputs)} output configurations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.outputs.clear()
            self._update_table()
            self.configuration_changed.emit()

    def load_configuration(self, config: dict):
        """Load configuration from dict."""
        self.outputs = config.get("outputs", [])
        self._update_table()

    def get_configuration(self) -> dict:
        """Get configuration as dict."""
        return {"outputs": self.outputs}

    def reset_to_defaults(self):
        """Reset to default configuration."""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "Clear all output configurations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.outputs.clear()
            self._update_table()
            self.configuration_changed.emit()

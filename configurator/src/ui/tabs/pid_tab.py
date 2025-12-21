"""
PID Controllers Tab
Manages PID controllers for PMU-30
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..dialogs.pid_controller_dialog import PIDControllerDialog
from typing import Dict, Any, List


class PIDTab(QWidget):
    """PID Controllers configuration tab."""

    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pid_controllers = []
        self._init_ui()

    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)

        # Info label
        info_group = QGroupBox("PID Controllers")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "Configure PID (Proportional-Integral-Derivative) controllers for closed-loop control.\n"
            "Use cases: Temperature control, Speed regulation, Position control, etc.\n"
            "Each controller reads from an input and writes to an output."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Input", "Output", "Kp", "Ki", "Kd", "Setpoint"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self.edit_controller)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add PID Controller")
        self.add_btn.clicked.connect(self.add_controller)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_controller)
        button_layout.addWidget(self.edit_btn)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self.copy_controller)
        button_layout.addWidget(self.copy_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_controller)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)

        # Stats label
        self.stats_label = QLabel("Controllers: 0 (Enabled: 0)")
        layout.addWidget(self.stats_label)

        self._update_table()

    def _update_table(self):
        """Update table with current PID controllers."""
        self.table.setRowCount(0)

        for idx, ctrl in enumerate(self.pid_controllers):
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Name
            name = QTableWidgetItem(ctrl.get("name", "Unnamed"))
            if not ctrl.get("enabled", True):
                name.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 0, name)

            # Input
            input_src = ctrl.get("input_source", {})
            input_str = f"{input_src.get('type', 'N/A').split('(')[0].strip()}: {input_src.get('channel', 0)}"
            input_item = QTableWidgetItem(input_str)
            self.table.setItem(row, 1, input_item)

            # Output
            output_tgt = ctrl.get("output_target", {})
            output_str = f"{output_tgt.get('type', 'N/A').split('(')[0].strip()}: {output_tgt.get('channel', 0)}"
            output_item = QTableWidgetItem(output_str)
            self.table.setItem(row, 2, output_item)

            # PID parameters
            params = ctrl.get("parameters", {})
            kp_item = QTableWidgetItem(f"{params.get('kp', 0.0):.3f}")
            kp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, kp_item)

            ki_item = QTableWidgetItem(f"{params.get('ki', 0.0):.3f}")
            ki_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, ki_item)

            kd_item = QTableWidgetItem(f"{params.get('kd', 0.0):.3f}")
            kd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, kd_item)

            # Setpoint
            setpoint_item = QTableWidgetItem(f"{ctrl.get('setpoint', 0.0):.2f}")
            setpoint_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, setpoint_item)

        self._update_stats()

    def _update_stats(self):
        """Update statistics label."""
        total = len(self.pid_controllers)
        enabled = sum(1 for ctrl in self.pid_controllers if ctrl.get("enabled", True))

        self.stats_label.setText(f"Controllers: {total} (Enabled: {enabled})")

    def add_controller(self):
        """Add new PID controller."""
        dialog = PIDControllerDialog(self, pid_config=None)

        if dialog.exec():
            config = dialog.get_config()
            self.pid_controllers.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def edit_controller(self):
        """Edit selected PID controller."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.pid_controllers):
            QMessageBox.warning(self, "No Selection", "Please select a controller to edit.")
            return

        dialog = PIDControllerDialog(
            self,
            pid_config=self.pid_controllers[row]
        )

        if dialog.exec():
            config = dialog.get_config()
            self.pid_controllers[row] = config
            self._update_table()
            self.configuration_changed.emit()

    def copy_controller(self):
        """Copy selected PID controller."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.pid_controllers):
            QMessageBox.warning(self, "No Selection", "Please select a controller to copy.")
            return

        # Copy config
        import copy
        new_config = copy.deepcopy(self.pid_controllers[row])
        new_config["name"] = new_config.get("name", "") + " (Copy)"

        dialog = PIDControllerDialog(
            self,
            pid_config=new_config
        )

        if dialog.exec():
            config = dialog.get_config()
            self.pid_controllers.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def delete_controller(self):
        """Delete selected PID controller."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.pid_controllers):
            QMessageBox.warning(self, "No Selection", "Please select a controller to delete.")
            return

        ctrl_name = self.pid_controllers[row].get("name", "Unnamed")

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete PID controller '{ctrl_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.pid_controllers[row]
            self._update_table()
            self.configuration_changed.emit()

    def clear_all(self):
        """Clear all PID controllers."""
        if not self.pid_controllers:
            return

        reply = QMessageBox.question(
            self, "Confirm Clear All",
            f"Delete all {len(self.pid_controllers)} PID controllers?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.pid_controllers.clear()
            self._update_table()
            self.configuration_changed.emit()

    def load_configuration(self, config: dict):
        """Load PID controllers from configuration."""
        self.pid_controllers = config.get("pid_controllers", [])
        self._update_table()

    def get_configuration(self) -> dict:
        """Get current PID controllers configuration."""
        return {
            "pid_controllers": self.pid_controllers
        }

    def reset_to_defaults(self):
        """Reset to default configuration."""
        self.pid_controllers.clear()
        self._update_table()

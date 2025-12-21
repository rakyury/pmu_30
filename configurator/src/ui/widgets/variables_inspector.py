"""
Variables Inspector Widget
Shows all system variables, CAN data, and PMU status
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from typing import Dict, List


class VariablesInspector(QWidget):
    """Variables inspector widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._create_default_structure()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_values)
        self.update_timer.start(500)  # Update every 500ms

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Value", "Unit"])
        self.tree.setColumnWidth(0, 180)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 60)
        self.tree.setAlternatingRowColors(True)

        layout.addWidget(self.tree)

    def _create_default_structure(self):
        """Create default tree structure."""
        # CAN Variables section
        self.can_section = QTreeWidgetItem(self.tree, ["CAN Variables", "", ""])
        self.can_section.setExpanded(False)

        # Add some example CAN variables
        can_vars = [
            ("in.BrakeSwitch", "?", ""),
            ("in.ClutchSwitch", "?", ""),
            ("in.Wipers", "?", ""),
            ("a_Fuel_level", "?", ""),
            ("c_ecu_rpm", "?", "rpm"),
            ("c_ecu_map", "?", "kPa"),
            ("c_ecu_boost", "?", "bar"),
            ("c_ecu_tps", "?", "%"),
            ("c_ecu_clt", "?", "°C"),
            ("c_ecu_iat", "?", "°C"),
            ("c_ecu_batt", "?", "V"),
            ("c_ecu_gear", "?", ""),
            ("c_ecu_lambda1", "?", "lambda"),
            ("c_ecu_faultCodeCount", "?", ""),
            ("c_ecu_fuelP", "?", "bar"),
            ("c_ecu_oilT", "?", "°C"),
            ("c_ecu_oilP", "?", "bar"),
        ]

        for name, value, unit in can_vars:
            item = QTreeWidgetItem(self.can_section, [name, value, unit])

        # PMU section
        self.pmu_section = QTreeWidgetItem(self.tree, ["PMU", "", ""])
        self.pmu_section.setExpanded(True)

        # PMU System Status subsection
        self.pmu_system = QTreeWidgetItem(self.pmu_section, ["System Status", "", ""])
        self.pmu_system.setExpanded(True)

        pmu_system_vars = [
            ("Board temperature 1", "?", "°C"),
            ("Board temperature 2", "?", "°C"),
            ("Battery voltage", "?", "V"),
            ("5V output", "?", "V"),
            ("Board 3V3", "?", "V"),
            ("Flash temperature", "?", "°C"),
            ("Total current", "?", "A"),
        ]

        for name, value, unit in pmu_system_vars:
            item = QTreeWidgetItem(self.pmu_system, [name, value, unit])

        # PMU Status Flags subsection
        self.pmu_flags = QTreeWidgetItem(self.pmu_section, ["Status Flags", "", ""])
        self.pmu_flags.setExpanded(True)

        pmu_flag_vars = [
            ("Reset detector", "?", ""),
            ("Status", "?", ""),
            ("User error", "?", ""),
            ("Is turning off", "?", ""),
            ("HW OUT active mask", "?", ""),
        ]

        for name, value, unit in pmu_flag_vars:
            item = QTreeWidgetItem(self.pmu_flags, [name, value, unit])

        # PMU Outputs subsection
        self.pmu_outputs = QTreeWidgetItem(self.pmu_section, ["Outputs Status", "", ""])
        self.pmu_outputs.setExpanded(False)

        # Create 30 output indicators (.o1 through .o30)
        for i in range(1, 31):
            output_name = f".o{i}"
            item = QTreeWidgetItem(self.pmu_outputs, [output_name, "?", ""])

    def _update_values(self):
        """Update real-time values (when connected to device)."""
        # TODO: Update from device when connected
        pass

    def update_variable(self, name: str, value: str, unit: str = ""):
        """Update specific variable value."""
        # Search for variable in tree
        for i in range(self.tree.topLevelItemCount()):
            section = self.tree.topLevelItem(i)
            for j in range(section.childCount()):
                item = section.child(j)
                if item.text(0) == name:
                    item.setText(1, value)
                    if unit:
                        item.setText(2, unit)
                    return

    def add_can_variable(self, name: str, value: str = "?", unit: str = ""):
        """Add new CAN variable."""
        item = QTreeWidgetItem(self.can_section, [name, value, unit])

    def clear_can_variables(self):
        """Clear all CAN variables."""
        while self.can_section.childCount() > 0:
            self.can_section.removeChild(self.can_section.child(0))

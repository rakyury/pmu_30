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

    # Category mapping for 64 function types
    FUNCTION_CATEGORIES = {
        # Mathematical (10 types)
        "add": "Mathematical", "subtract": "Mathematical", "multiply": "Mathematical",
        "divide": "Mathematical", "min": "Mathematical", "max": "Mathematical",
        "average": "Mathematical", "abs": "Mathematical", "scale": "Mathematical", "clamp": "Mathematical",
        # Comparison (7 types)
        "greater": "Comparison", "less": "Comparison", "equal": "Comparison",
        "not_equal": "Comparison", "greater_equal": "Comparison", "less_equal": "Comparison",
        "in_range": "Comparison",
        # Logic (6 types)
        "and": "Logic", "or": "Logic", "not": "Logic", "xor": "Logic", "nand": "Logic", "nor": "Logic",
        # Tables (2 types)
        "table_1d": "Tables", "table_2d": "Tables",
        # Filters (5 types)
        "moving_avg": "Filters", "low_pass": "Filters", "min_window": "Filters",
        "max_window": "Filters", "median": "Filters",
        # Control (4 types)
        "pid": "Control", "hysteresis": "Control", "rate_limit": "Control", "debounce": "Control",
        # Special (12 types - timers, latches, etc.)
        "mux": "Special", "demux": "Special", "conditional": "Special",
        "flash": "Special", "pulse": "Special", "toggle": "Special",
        "set_latch": "Special", "reset_latch": "Special", "sr_latch": "Special",
        "counter": "Special", "timer_on": "Special", "timer_off": "Special",
    }

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
            "Configure logic functions with 64 operation types in 7 categories:\n"
            "Mathematical (add, subtract, multiply, scale, clamp), Comparison (>, <, ==, in_range), "
            "Logic (AND, OR, NOT, XOR), \n"
            "Tables (1D/2D lookup), Filters (moving_avg, low_pass, median), "
            "Control (PID, hysteresis, rate_limit), Special (mux, conditional)."
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Output Ch", "Name", "Type", "Category", "Inputs", "Parameters"])
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

    def _get_function_type(self, func: dict) -> str:
        """Get function type from config (supports both old and new formats)."""
        # New format: "type" field
        if "type" in func:
            return func["type"]
        # Old format: "operation" field
        if "operation" in func:
            op = func["operation"].lower()
            # Map old operations to new types
            if "(" in op:
                op = op.split("(")[0].strip()
            return op
        return "unknown"

    def _get_output_channel(self, func: dict) -> str:
        """Get output channel from config (supports both old and new formats)."""
        # New format: "output" field (can be channel ID or name)
        if "output" in func:
            return str(func["output"])
        # Old format: "virtual_channel" field
        if "virtual_channel" in func:
            return f"V{func['virtual_channel']}"
        return "?"

    def _format_parameters(self, func: dict) -> str:
        """Format function parameters for display."""
        func_type = self._get_function_type(func)
        params = func.get("parameters", {})

        if not params:
            return "-"

        # Format based on function type
        if func_type == "pid":
            return f"Kp={params.get('kp', 0):.2f}, Ki={params.get('ki', 0):.2f}, Kd={params.get('kd', 0):.2f}"
        elif func_type == "hysteresis":
            return f"ON={params.get('threshold_on', 0)}, OFF={params.get('threshold_off', 0)}"
        elif func_type == "scale":
            return f"×{params.get('multiplier', 1):.2f}, +{params.get('offset', 0):.2f}"
        elif func_type == "clamp":
            return f"Min={params.get('min', 0)}, Max={params.get('max', 100)}"
        elif func_type in ["moving_avg", "min_window", "max_window", "median"]:
            return f"Window={params.get('window_size', 5)}"
        elif func_type == "low_pass":
            return f"TC={params.get('time_constant', 0.1):.3f}s"
        elif func_type == "rate_limit":
            return f"Max={params.get('max_rate', 100)}/s"
        elif func_type == "debounce":
            return f"{params.get('debounce_ms', 50)}ms"
        elif func_type == "in_range":
            return f"[{params.get('min', 0)}, {params.get('max', 100)}]"
        elif func_type in ["flash", "pulse"]:
            return f"Period={params.get('period_ms', 1000)}ms, Duty={params.get('duty_cycle', 50)}%"
        elif func_type in ["timer_on", "timer_off"]:
            return f"Delay={params.get('delay_ms', 1000)}ms"
        elif func_type == "counter":
            return f"Max={params.get('max_count', 100)}"
        elif func_type == "mux":
            return f"{len(params.get('inputs', []))} inputs"
        else:
            # Generic parameter display (show first 2 params)
            param_strs = [f"{k}={v}" for k, v in list(params.items())[:2]]
            return ", ".join(param_strs) if param_strs else "-"

    def _update_table(self):
        """Update table with current logic functions."""
        self.table.setRowCount(0)

        for idx, func in enumerate(self.logic_functions):
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Output channel
            output_ch = QTableWidgetItem(self._get_output_channel(func))
            output_ch.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, output_ch)

            # Name
            name = QTableWidgetItem(func.get("name", "Unnamed"))
            self.table.setItem(row, 1, name)

            # Type
            func_type = self._get_function_type(func)
            type_item = QTableWidgetItem(func_type)
            self.table.setItem(row, 2, type_item)

            # Category
            category = self.FUNCTION_CATEGORIES.get(func_type.lower(), "Other")
            category_item = QTableWidgetItem(category)
            self.table.setItem(row, 3, category_item)

            # Inputs summary
            inputs = func.get("inputs", [])
            if isinstance(inputs, list):
                inputs_str = ", ".join(str(inp) for inp in inputs[:3])
                if len(inputs) > 3:
                    inputs_str += f" +{len(inputs)-3}"
            else:
                inputs_str = str(inputs)
            inputs_item = QTableWidgetItem(inputs_str)
            self.table.setItem(row, 4, inputs_item)

            # Parameters
            params_str = self._format_parameters(func)
            params_item = QTableWidgetItem(params_str)
            self.table.setItem(row, 5, params_item)

        self._update_stats()

    def _update_stats(self):
        """Update statistics label."""
        func_count = len(self.logic_functions)

        # Count unique virtual channels (supports both formats)
        used_channels = set()
        for func in self.logic_functions:
            # Old format: virtual_channel field
            vch = func.get("virtual_channel")
            if vch is not None:
                used_channels.add(f"V{vch}")
            # New format: output field (if it starts with V or is a number)
            output = func.get("output")
            if output is not None:
                output_str = str(output)
                if output_str.startswith("V") or output_str.isdigit():
                    used_channels.add(output_str)

        # Count by category
        category_counts = {}
        for func in self.logic_functions:
            func_type = self._get_function_type(func)
            category = self.FUNCTION_CATEGORIES.get(func_type.lower(), "Other")
            category_counts[category] = category_counts.get(category, 0) + 1

        category_str = ", ".join([f"{cat}: {count}" for cat, count in sorted(category_counts.items())])

        self.stats_label.setText(
            f"Functions: {func_count} | Channels Used: {len(used_channels)} | By Category: {category_str}"
        )

    def _get_used_virtual_channels(self, exclude_index: int = -1) -> List[int]:
        """Get list of used virtual channel numbers (for backward compatibility)."""
        used = []
        for idx, func in enumerate(self.logic_functions):
            if idx != exclude_index:
                # Old format: virtual_channel field
                vch = func.get("virtual_channel")
                if vch is not None and isinstance(vch, int):
                    used.append(vch)
                # New format: output field (if it's a virtual channel)
                output = func.get("output")
                if output is not None:
                    output_str = str(output)
                    # Check if it's a virtual channel (V0-V255 or 0-255)
                    if output_str.startswith("V") and output_str[1:].isdigit():
                        used.append(int(output_str[1:]))
                    elif output_str.isdigit():
                        ch_num = int(output_str)
                        if ch_num < 256:  # Assume it's a virtual channel
                            used.append(ch_num)
        return used

    def add_function(self):
        """Add new logic function."""
        used_channels = self._get_used_virtual_channels()

        # Find next available virtual channel for default suggestion
        next_channel = 0
        for ch in range(256):
            if ch not in used_channels:
                next_channel = ch
                break

        # Create default config with suggested virtual channel
        default_config = {
            "type": "add",
            "name": "New Function",
            "enabled": True,
            "output": f"V{next_channel}",
            "inputs": [],
            "parameters": {}
        }

        dialog = LogicFunctionDialog(
            self,
            function_config=default_config,
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

        # Update for new format (output) or old format (virtual_channel)
        if "output" in new_config:
            new_config["output"] = f"V{next_channel}"
        else:
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

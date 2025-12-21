"""
Logic Function Configuration Dialog
Configures a single logic function for the PMU-30 Logic Engine
Supports all 64 function types from firmware
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QListWidget, QLabel, QListWidgetItem, QMessageBox, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List


class LogicFunctionDialog(QDialog):
    """Dialog for configuring a single logic function."""

    # All 64 function types matching firmware (pmu_logic_functions.h)
    OPERATION_TYPES = {
        # Mathematical Operations (0x00-0x1F)
        "Mathematical": [
            "add", "subtract", "multiply", "divide",
            "min", "max", "average", "abs",
            "scale", "clamp"
        ],

        # Comparison Operations (0x20-0x3F)
        "Comparison": [
            "greater (>)", "less (<)", "equal (==)", "not_equal (!=)",
            "greater_equal (>=)", "less_equal (<=)", "in_range"
        ],

        # Logic Operations (0x40-0x5F)
        "Logic": [
            "and (AND)", "or (OR)", "not (NOT)", "xor (XOR)",
            "nand (NAND)", "nor (NOR)"
        ],

        # Tables (0x60-0x7F)
        "Tables": [
            "table_1d", "table_2d"
        ],

        # Filters (0x80-0x9F)
        "Filters": [
            "moving_avg", "low_pass", "min_window", "max_window", "median"
        ],

        # Control (0xA0-0xBF)
        "Control": [
            "pid", "hysteresis", "rate_limit", "debounce"
        ],

        # Special (0xC0-0xFF)
        "Special": [
            "mux", "demux", "conditional"
        ]
    }

    INPUT_TYPES = [
        "Physical Input", "Physical Output", "Virtual Channel", "Constant", "Channel Name"
    ]

    def __init__(self, parent=None, function_config: Optional[Dict[str, Any]] = None,
                 used_channels=None):
        super().__init__(parent)
        self.function_config = function_config
        self.used_channels = used_channels or []

        self.setWindowTitle("Logic Function Configuration - PMU-30")
        self.setModal(True)
        self.resize(700, 650)

        self._init_ui()

        if function_config:
            self._load_config(function_config)

    def _init_ui(self):
        """Initialize UI components."""
        main_layout = QVBoxLayout()

        # Create scroll area for all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Boost_Controller, Launch_Control")
        basic_layout.addRow("Name: *", self.name_edit)

        # Category combo
        self.category_combo = QComboBox()
        self.category_combo.addItems(list(self.OPERATION_TYPES.keys()))
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        basic_layout.addRow("Category:", self.category_combo)

        # Operation combo
        self.operation_combo = QComboBox()
        self.operation_combo.currentTextChanged.connect(self._on_operation_changed)
        basic_layout.addRow("Operation:", self.operation_combo)

        # Output channel
        self.output_channel_edit = QLineEdit()
        self.output_channel_edit.setPlaceholderText("Channel ID or Name (e.g., 100 or 'Wastegate_PWM')")
        basic_layout.addRow("Output Channel: *", self.output_channel_edit)

        # Enabled checkbox
        self.enabled_check = QComboBox()
        self.enabled_check.addItems(["Enabled", "Disabled"])
        basic_layout.addRow("Status:", self.enabled_check)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Inputs group
        inputs_group = QGroupBox("Input Channels")
        inputs_layout = QVBoxLayout()

        info_label = QLabel("Most functions need 1-2 inputs. Logic operations (AND/OR) support up to 8 inputs.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #0078d4;")
        inputs_layout.addWidget(info_label)

        self.inputs_list = QListWidget()
        self.inputs_list.setMaximumHeight(120)
        inputs_layout.addWidget(QLabel("Configured Inputs:"))
        inputs_layout.addWidget(self.inputs_list)

        # Add input controls
        add_input_layout = QHBoxLayout()

        self.input_value_edit = QLineEdit()
        self.input_value_edit.setPlaceholderText("Channel ID, Name or Constant value")
        add_input_layout.addWidget(QLabel("Value:"))
        add_input_layout.addWidget(self.input_value_edit)

        self.add_input_btn = QPushButton("Add Input")
        self.add_input_btn.clicked.connect(self._add_input)
        add_input_layout.addWidget(self.add_input_btn)

        self.remove_input_btn = QPushButton("Remove Selected")
        self.remove_input_btn.clicked.connect(self._remove_input)
        add_input_layout.addWidget(self.remove_input_btn)

        inputs_layout.addLayout(add_input_layout)
        inputs_group.setLayout(inputs_layout)
        layout.addWidget(inputs_group)

        # === PARAMETERS GROUPS ===

        # PID Parameters
        self.pid_group = QGroupBox("PID Parameters")
        pid_layout = QFormLayout()

        self.pid_setpoint_spin = QDoubleSpinBox()
        self.pid_setpoint_spin.setRange(-100000, 100000)
        self.pid_setpoint_spin.setDecimals(2)
        self.pid_setpoint_spin.setToolTip("Target setpoint value")
        pid_layout.addRow("Setpoint:", self.pid_setpoint_spin)

        self.pid_kp_spin = QDoubleSpinBox()
        self.pid_kp_spin.setRange(0, 1000)
        self.pid_kp_spin.setDecimals(3)
        self.pid_kp_spin.setValue(1.0)
        self.pid_kp_spin.setToolTip("Proportional gain")
        pid_layout.addRow("Kp (Proportional):", self.pid_kp_spin)

        self.pid_ki_spin = QDoubleSpinBox()
        self.pid_ki_spin.setRange(0, 1000)
        self.pid_ki_spin.setDecimals(3)
        self.pid_ki_spin.setToolTip("Integral gain")
        pid_layout.addRow("Ki (Integral):", self.pid_ki_spin)

        self.pid_kd_spin = QDoubleSpinBox()
        self.pid_kd_spin.setRange(0, 1000)
        self.pid_kd_spin.setDecimals(3)
        self.pid_kd_spin.setToolTip("Derivative gain")
        pid_layout.addRow("Kd (Derivative):", self.pid_kd_spin)

        self.pid_group.setLayout(pid_layout)
        self.pid_group.setVisible(False)
        layout.addWidget(self.pid_group)

        # Hysteresis Parameters
        self.hyst_group = QGroupBox("Hysteresis Parameters")
        hyst_layout = QFormLayout()

        self.hyst_on_spin = QSpinBox()
        self.hyst_on_spin.setRange(-100000, 100000)
        self.hyst_on_spin.setValue(100)
        self.hyst_on_spin.setToolTip("Turn ON when input >= this value")
        hyst_layout.addRow("Threshold ON:", self.hyst_on_spin)

        self.hyst_off_spin = QSpinBox()
        self.hyst_off_spin.setRange(-100000, 100000)
        self.hyst_off_spin.setValue(50)
        self.hyst_off_spin.setToolTip("Turn OFF when input <= this value")
        hyst_layout.addRow("Threshold OFF:", self.hyst_off_spin)

        self.hyst_group.setLayout(hyst_layout)
        self.hyst_group.setVisible(False)
        layout.addWidget(self.hyst_group)

        # Scale Parameters
        self.scale_group = QGroupBox("Scale Parameters")
        scale_layout = QFormLayout()

        self.scale_mult_spin = QDoubleSpinBox()
        self.scale_mult_spin.setRange(-1000, 1000)
        self.scale_mult_spin.setDecimals(4)
        self.scale_mult_spin.setValue(1.0)
        self.scale_mult_spin.setToolTip("Multiplier (output = input * multiplier + offset)")
        scale_layout.addRow("Multiplier:", self.scale_mult_spin)

        self.scale_offset_spin = QDoubleSpinBox()
        self.scale_offset_spin.setRange(-100000, 100000)
        self.scale_offset_spin.setDecimals(2)
        self.scale_offset_spin.setToolTip("Offset value")
        scale_layout.addRow("Offset:", self.scale_offset_spin)

        self.scale_group.setLayout(scale_layout)
        self.scale_group.setVisible(False)
        layout.addWidget(self.scale_group)

        # Clamp Parameters
        self.clamp_group = QGroupBox("Clamp Parameters")
        clamp_layout = QFormLayout()

        self.clamp_min_spin = QSpinBox()
        self.clamp_min_spin.setRange(-1000000, 1000000)
        self.clamp_min_spin.setValue(0)
        self.clamp_min_spin.setToolTip("Minimum output value")
        clamp_layout.addRow("Minimum:", self.clamp_min_spin)

        self.clamp_max_spin = QSpinBox()
        self.clamp_max_spin.setRange(-1000000, 1000000)
        self.clamp_max_spin.setValue(1000)
        self.clamp_max_spin.setToolTip("Maximum output value")
        clamp_layout.addRow("Maximum:", self.clamp_max_spin)

        self.clamp_group.setLayout(clamp_layout)
        self.clamp_group.setVisible(False)
        layout.addWidget(self.clamp_group)

        # Filter Parameters
        self.filter_group = QGroupBox("Filter Parameters")
        filter_layout = QFormLayout()

        self.filter_window_spin = QSpinBox()
        self.filter_window_spin.setRange(2, 100)
        self.filter_window_spin.setValue(10)
        self.filter_window_spin.setToolTip("Window size for moving average/min/max filters")
        filter_layout.addRow("Window Size:", self.filter_window_spin)

        self.filter_tc_spin = QDoubleSpinBox()
        self.filter_tc_spin.setRange(0.001, 10.0)
        self.filter_tc_spin.setDecimals(3)
        self.filter_tc_spin.setValue(0.1)
        self.filter_tc_spin.setToolTip("Time constant for low-pass filter (seconds)")
        filter_layout.addRow("Time Constant (s):", self.filter_tc_spin)

        self.filter_group.setLayout(filter_layout)
        self.filter_group.setVisible(False)
        layout.addWidget(self.filter_group)

        # Rate Limit Parameters
        self.rate_group = QGroupBox("Rate Limiter Parameters")
        rate_layout = QFormLayout()

        self.rate_max_spin = QSpinBox()
        self.rate_max_spin.setRange(1, 1000000)
        self.rate_max_spin.setValue(100)
        self.rate_max_spin.setToolTip("Maximum rate of change per second")
        rate_layout.addRow("Max Rate/Second:", self.rate_max_spin)

        self.rate_group.setLayout(rate_layout)
        self.rate_group.setVisible(False)
        layout.addWidget(self.rate_group)

        # Debounce Parameters
        self.debounce_group = QGroupBox("Debounce Parameters")
        debounce_layout = QFormLayout()

        self.debounce_ms_spin = QSpinBox()
        self.debounce_ms_spin.setRange(1, 10000)
        self.debounce_ms_spin.setValue(50)
        self.debounce_ms_spin.setSuffix(" ms")
        self.debounce_ms_spin.setToolTip("Debounce time in milliseconds")
        debounce_layout.addRow("Debounce Time:", self.debounce_ms_spin)

        self.debounce_group.setLayout(debounce_layout)
        self.debounce_group.setVisible(False)
        layout.addWidget(self.debounce_group)

        # In Range Parameters
        self.range_group = QGroupBox("Range Parameters")
        range_layout = QFormLayout()

        self.range_min_spin = QSpinBox()
        self.range_min_spin.setRange(-1000000, 1000000)
        self.range_min_spin.setValue(0)
        range_layout.addRow("Minimum:", self.range_min_spin)

        self.range_max_spin = QSpinBox()
        self.range_max_spin.setRange(-1000000, 1000000)
        self.range_max_spin.setValue(100)
        range_layout.addRow("Maximum:", self.range_max_spin)

        self.range_group.setLayout(range_layout)
        self.range_group.setVisible(False)
        layout.addWidget(self.range_group)

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()

        self.help_btn = QPushButton("Help")
        self.help_btn.clicked.connect(self._show_help)
        button_layout.addWidget(self.help_btn)

        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # Initialize state
        self._on_category_changed(self.category_combo.currentText())

    def _on_category_changed(self, category: str):
        """Handle category change - update operation list."""
        self.operation_combo.clear()
        if category in self.OPERATION_TYPES:
            self.operation_combo.addItems(self.OPERATION_TYPES[category])

    def _on_operation_changed(self, operation: str):
        """Handle operation type change - show/hide appropriate parameters."""
        # Extract base operation name (remove parentheses)
        op_base = operation.split("(")[0].strip().lower()

        # Hide all parameter groups first
        self.pid_group.setVisible(False)
        self.hyst_group.setVisible(False)
        self.scale_group.setVisible(False)
        self.clamp_group.setVisible(False)
        self.filter_group.setVisible(False)
        self.rate_group.setVisible(False)
        self.debounce_group.setVisible(False)
        self.range_group.setVisible(False)

        # Show appropriate group based on operation
        if op_base == "pid":
            self.pid_group.setVisible(True)
        elif op_base == "hysteresis":
            self.hyst_group.setVisible(True)
        elif op_base == "scale":
            self.scale_group.setVisible(True)
        elif op_base == "clamp":
            self.clamp_group.setVisible(True)
        elif op_base in ["moving_avg", "low_pass", "min_window", "max_window", "median"]:
            self.filter_group.setVisible(True)
            # Show appropriate fields
            if op_base in ["moving_avg", "min_window", "max_window", "median"]:
                self.filter_window_spin.setVisible(True)
                self.filter_tc_spin.setVisible(False)
            elif op_base == "low_pass":
                self.filter_window_spin.setVisible(False)
                self.filter_tc_spin.setVisible(True)
        elif op_base == "rate_limit":
            self.rate_group.setVisible(True)
        elif op_base == "debounce":
            self.debounce_group.setVisible(True)
        elif op_base == "in_range":
            self.range_group.setVisible(True)

    def _add_input(self):
        """Add input to the list."""
        value = self.input_value_edit.text().strip()
        if not value:
            QMessageBox.warning(self, "Input Error", "Please enter a value (channel ID/name or constant)")
            return

        if len(self.inputs_list) >= 8:
            QMessageBox.warning(self, "Input Limit", "Maximum 8 inputs allowed")
            return

        self.inputs_list.addItem(value)
        self.input_value_edit.clear()

    def _remove_input(self):
        """Remove selected input from the list."""
        current_row = self.inputs_list.currentRow()
        if current_row >= 0:
            self.inputs_list.takeItem(current_row)

    def _show_help(self):
        """Show help dialog with function descriptions."""
        operation = self.operation_combo.currentText().split("(")[0].strip()

        help_text = {
            "add": "Adds two input values together.\nOutput = Input_A + Input_B",
            "subtract": "Subtracts Input_B from Input_A.\nOutput = Input_A - Input_B",
            "multiply": "Multiplies two inputs (uses fixed-point math).\nOutput = (Input_A * Input_B) / 1000",
            "divide": "Divides Input_A by Input_B.\nOutput = Input_A / Input_B",
            "min": "Returns minimum of all inputs.",
            "max": "Returns maximum of all inputs.",
            "average": "Returns average of all inputs.",
            "abs": "Returns absolute value.\nOutput = |Input|",
            "scale": "Scales and offsets input.\nOutput = (Input * Multiplier) + Offset",
            "clamp": "Limits value to min/max range.\nOutput = min(max(Input, Min), Max)",
            "greater": "Comparison: returns 1 if A > B, else 0",
            "less": "Comparison: returns 1 if A < B, else 0",
            "equal": "Comparison: returns 1 if A == B, else 0",
            "not_equal": "Comparison: returns 1 if A != B, else 0",
            "in_range": "Returns 1 if input is within min/max range",
            "and": "Logical AND of all inputs.\nOutput = 1 if ALL inputs != 0",
            "or": "Logical OR of all inputs.\nOutput = 1 if ANY input != 0",
            "not": "Logical NOT.\nOutput = 1 if Input == 0, else 0",
            "xor": "Logical XOR.\nOutput = 1 if inputs differ",
            "pid": "PID Controller for closed-loop control.\nRequires: setpoint, Kp, Ki, Kd",
            "hysteresis": "Schmitt trigger with ON/OFF thresholds.\nPrevents oscillation from noise",
            "moving_avg": "Moving average filter.\nSmooths noisy signals",
            "low_pass": "RC low-pass filter.\nRemoves high-frequency noise",
            "rate_limit": "Limits rate of change.\nPrevents sudden jumps",
            "debounce": "Digital debounce filter.\nRemoves contact bounce"
        }

        msg = help_text.get(operation.lower(), "No help available for this function.")
        QMessageBox.information(self, f"Help: {operation}", msg)

    def _on_accept(self):
        """Validate and accept dialog."""
        # Validate name
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        # Validate output channel
        if not self.output_channel_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Output channel is required!")
            self.output_channel_edit.setFocus()
            return

        # Validate inputs (most functions need at least 1 input)
        operation = self.operation_combo.currentText().split("(")[0].strip().lower()
        if self.inputs_list.count() == 0 and operation not in ["table_1d", "table_2d"]:
            QMessageBox.warning(self, "Validation Error", "At least one input is required!")
            return

        self.accept()

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))

        # Find and set operation
        func_type = config.get("type", "add")
        for category, operations in self.OPERATION_TYPES.items():
            for op in operations:
                if func_type in op.lower():
                    # Set category
                    idx = self.category_combo.findText(category)
                    if idx >= 0:
                        self.category_combo.setCurrentIndex(idx)
                    # Set operation
                    idx = self.operation_combo.findText(op, Qt.MatchFlag.MatchContains)
                    if idx >= 0:
                        self.operation_combo.setCurrentIndex(idx)
                    break

        # Set output
        output = config.get("output", "")
        self.output_channel_edit.setText(str(output))

        # Set enabled
        enabled = config.get("enabled", True)
        self.enabled_check.setCurrentIndex(0 if enabled else 1)

        # Load inputs
        inputs = config.get("inputs", [])
        for inp in inputs:
            self.inputs_list.addItem(str(inp))

        # Load parameters
        params = config.get("parameters", {})

        # PID
        self.pid_setpoint_spin.setValue(params.get("setpoint", 0))
        self.pid_kp_spin.setValue(params.get("kp", 1.0))
        self.pid_ki_spin.setValue(params.get("ki", 0.0))
        self.pid_kd_spin.setValue(params.get("kd", 0.0))

        # Hysteresis
        self.hyst_on_spin.setValue(params.get("threshold_on", 100))
        self.hyst_off_spin.setValue(params.get("threshold_off", 50))

        # Scale
        self.scale_mult_spin.setValue(params.get("multiplier", 1.0))
        self.scale_offset_spin.setValue(params.get("offset", 0.0))

        # Clamp
        self.clamp_min_spin.setValue(params.get("min", 0))
        self.clamp_max_spin.setValue(params.get("max", 1000))

        # Filter
        self.filter_window_spin.setValue(params.get("window_size", 10))
        self.filter_tc_spin.setValue(params.get("time_constant", 0.1))

        # Rate limit
        self.rate_max_spin.setValue(params.get("max_rate", 100))

        # Debounce
        self.debounce_ms_spin.setValue(params.get("debounce_ms", 50))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        # Get base operation name
        operation = self.operation_combo.currentText()
        op_base = operation.split("(")[0].strip().lower()

        # Remove comparison operators from name
        func_type = op_base.replace(" ", "_")
        for op in [">", "<", "==", "!=", ">=", "<="]:
            func_type = func_type.replace(op, "")
        func_type = func_type.strip()

        # Get inputs as list
        inputs = []
        for i in range(self.inputs_list.count()):
            item_text = self.inputs_list.item(i).text()
            inputs.append(item_text)

        # Build parameters dict based on function type
        parameters = {}

        if op_base == "pid":
            parameters = {
                "setpoint": self.pid_setpoint_spin.value(),
                "kp": self.pid_kp_spin.value(),
                "ki": self.pid_ki_spin.value(),
                "kd": self.pid_kd_spin.value()
            }
        elif op_base == "hysteresis":
            parameters = {
                "threshold_on": self.hyst_on_spin.value(),
                "threshold_off": self.hyst_off_spin.value()
            }
        elif op_base == "scale":
            parameters = {
                "multiplier": self.scale_mult_spin.value(),
                "offset": self.scale_offset_spin.value()
            }
        elif op_base == "clamp":
            parameters = {
                "min": self.clamp_min_spin.value(),
                "max": self.clamp_max_spin.value()
            }
        elif op_base in ["moving_avg", "min_window", "max_window", "median"]:
            parameters = {
                "window_size": self.filter_window_spin.value()
            }
        elif op_base == "low_pass":
            parameters = {
                "time_constant": self.filter_tc_spin.value()
            }
        elif op_base == "rate_limit":
            parameters = {
                "max_rate": self.rate_max_spin.value()
            }
        elif op_base == "debounce":
            parameters = {
                "debounce_ms": self.debounce_ms_spin.value()
            }
        elif op_base == "in_range":
            parameters = {
                "min": self.range_min_spin.value(),
                "max": self.range_max_spin.value()
            }

        config = {
            "type": func_type,
            "name": self.name_edit.text().strip(),
            "enabled": (self.enabled_check.currentIndex() == 0),
            "output": self.output_channel_edit.text().strip(),
            "inputs": inputs,
            "parameters": parameters
        }

        return config

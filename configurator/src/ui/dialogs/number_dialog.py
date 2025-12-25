"""
Number (Math Channel) Configuration Dialog
Math operations with operation-specific UI
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QLabel, QStackedWidget, QWidget, QGridLayout
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, MathOperation, ChannelMultiplier


class NumberDialog(BaseChannelDialog):
    """Dialog for configuring math/number channels with operation-specific UI."""

    # Operation display names
    OPERATION_NAMES = {
        MathOperation.CONSTANT: "Constant",
        MathOperation.CHANNEL: "Channel or constant",
        MathOperation.ADD: "Addition",
        MathOperation.SUBTRACT: "Subtraction",
        MathOperation.MULTIPLY: "Multiply",
        MathOperation.DIVIDE: "Divide",
        MathOperation.MODULO: "Modulo",
        MathOperation.MIN: "Min",
        MathOperation.MAX: "Max",
        MathOperation.CLAMP: "Clamp",
        MathOperation.LOOKUP2: "Lookup2",
        MathOperation.LOOKUP3: "Lookup3",
        MathOperation.LOOKUP4: "Lookup4",
        MathOperation.LOOKUP5: "Lookup5",
    }

    # Multiplier options
    MULTIPLIER_OPTIONS = [
        ("*1", ChannelMultiplier.MUL_1.value),
        ("*10", ChannelMultiplier.MUL_10.value),
        ("*100", ChannelMultiplier.MUL_100.value),
        ("*1000", ChannelMultiplier.MUL_1000.value),
        ("raw", ChannelMultiplier.RAW.value),
    ]

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent, config, available_channels, ChannelType.NUMBER, existing_channels)

        self._create_operation_group()
        self._create_params_group()

        # Connect operation change
        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        # Initialize view
        self._on_operation_changed()

    def _create_operation_group(self):
        """Create operation selection group"""
        op_group = QGroupBox("Operation Type")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Operation and Decimal places in same row
        layout.addWidget(QLabel("Operation:"), 0, 0)
        self.operation_combo = QComboBox()
        for op in MathOperation:
            self.operation_combo.addItem(self.OPERATION_NAMES[op], op.value)
        layout.addWidget(self.operation_combo, 0, 1)

        layout.addWidget(QLabel("Decimal places:"), 0, 2)
        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(0, 6)
        self.decimal_spin.setValue(2)
        layout.addWidget(self.decimal_spin, 0, 3)

        # Operation description
        self.op_description = QLabel("")
        self.op_description.setStyleSheet("color: #b0b0b0; font-style: italic;")
        self.op_description.setWordWrap(True)
        layout.addWidget(self.op_description, 1, 0, 1, 4)

        op_group.setLayout(layout)
        self.content_layout.addWidget(op_group)

    def _create_params_group(self):
        """Create operation parameters group with stacked widget"""
        self.params_group = QGroupBox("Parameters")
        params_layout = QFormLayout()

        self.stacked_widget = QStackedWidget()
        params_layout.addRow(self.stacked_widget)

        self.params_group.setLayout(params_layout)
        self.content_layout.addWidget(self.params_group)

        # Create pages for each operation type
        self._create_constant_page()      # 0 - CONSTANT
        self._create_channel_page()       # 1 - CHANNEL
        self._create_binary_page("add")   # 2 - ADD
        self._create_binary_page("subtract")  # 3 - SUBTRACT
        self._create_binary_page("multiply")  # 4 - MULTIPLY
        self._create_binary_page("divide")    # 5 - DIVIDE
        self._create_binary_page("modulo")    # 6 - MODULO
        self._create_binary_page("min")       # 7 - MIN
        self._create_binary_page("max")       # 8 - MAX
        self._create_clamp_page()         # 9 - CLAMP
        self._create_lookup_page(2)       # 10 - LOOKUP2
        self._create_lookup_page(3)       # 11 - LOOKUP3
        self._create_lookup_page(4)       # 12 - LOOKUP4
        self._create_lookup_page(5)       # 13 - LOOKUP5

    def _create_multiplier_combo(self) -> QComboBox:
        """Create channel multiplier combobox"""
        combo = QComboBox()
        for label, value in self.MULTIPLIER_OPTIONS:
            combo.addItem(label, value)
        combo.setMaximumWidth(80)
        return combo

    def _create_channel_with_multiplier(self, placeholder: str) -> tuple:
        """Create channel selector with multiplier dropdown"""
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(0, 1)

        widget, edit = self._create_channel_selector(placeholder)
        layout.addWidget(widget, 0, 0)

        multiplier = self._create_multiplier_combo()
        layout.addWidget(multiplier, 0, 1)

        return container, edit, multiplier

    def _create_constant_page(self):
        """Create constant value page"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setColumnStretch(1, 1)

        layout.addWidget(QLabel("Value:"), 0, 0)
        self.constant_value_spin = QDoubleSpinBox()
        self.constant_value_spin.setRange(-1000000, 1000000)
        self.constant_value_spin.setDecimals(4)
        layout.addWidget(self.constant_value_spin, 0, 1)

        self.stacked_widget.addWidget(page)

    def _create_channel_page(self):
        """Create channel or constant page"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setColumnStretch(1, 1)

        # Channel with multiplier
        layout.addWidget(QLabel("Channel:"), 0, 0)
        self.channel_container, self.channel_edit, self.channel_multiplier = \
            self._create_channel_with_multiplier("Select channel...")
        layout.addWidget(self.channel_container, 0, 1)

        self.stacked_widget.addWidget(page)

    def _create_binary_page(self, op_name: str):
        """Create page for binary operations"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setColumnStretch(1, 1)

        # Input 1 with multiplier
        layout.addWidget(QLabel("Input 1: *"), 0, 0)
        container1, edit1, mult1 = self._create_channel_with_multiplier("Select first value...")
        setattr(self, f"{op_name}_input1_container", container1)
        setattr(self, f"{op_name}_input1_edit", edit1)
        setattr(self, f"{op_name}_input1_mult", mult1)
        layout.addWidget(container1, 0, 1)

        # Input 2 with multiplier
        layout.addWidget(QLabel("Input 2: *"), 1, 0)
        container2, edit2, mult2 = self._create_channel_with_multiplier("Select second value...")
        setattr(self, f"{op_name}_input2_container", container2)
        setattr(self, f"{op_name}_input2_edit", edit2)
        setattr(self, f"{op_name}_input2_mult", mult2)
        layout.addWidget(container2, 1, 1)

        self.stacked_widget.addWidget(page)

    def _create_clamp_page(self):
        """Create clamp page"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Input with multiplier
        layout.addWidget(QLabel("Input: *"), 0, 0)
        self.clamp_container, self.clamp_edit, self.clamp_mult = \
            self._create_channel_with_multiplier("Select input channel...")
        layout.addWidget(self.clamp_container, 0, 1, 1, 3)

        # Min and Max in same row
        layout.addWidget(QLabel("Minimum:"), 1, 0)
        self.clamp_min_spin = QDoubleSpinBox()
        self.clamp_min_spin.setRange(-1000000, 1000000)
        self.clamp_min_spin.setDecimals(2)
        self.clamp_min_spin.setValue(0.0)
        layout.addWidget(self.clamp_min_spin, 1, 1)

        layout.addWidget(QLabel("Maximum:"), 1, 2)
        self.clamp_max_spin = QDoubleSpinBox()
        self.clamp_max_spin.setRange(-1000000, 1000000)
        self.clamp_max_spin.setDecimals(2)
        self.clamp_max_spin.setValue(100.0)
        layout.addWidget(self.clamp_max_spin, 1, 3)

        self.stacked_widget.addWidget(page)

    def _create_lookup_page(self, count: int):
        """Create lookup page with N values"""
        page = QWidget()
        layout = QGridLayout(page)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Channel with multiplier
        layout.addWidget(QLabel("Channel: *"), 0, 0)
        container, edit, mult = self._create_channel_with_multiplier("Select input channel...")
        setattr(self, f"lookup{count}_container", container)
        setattr(self, f"lookup{count}_edit", edit)
        setattr(self, f"lookup{count}_mult", mult)
        layout.addWidget(container, 0, 1, 1, 3)

        # Value spinboxes
        row = 1
        for i in range(count):
            col = (i % 2) * 2
            if i % 2 == 0 and i > 0:
                row += 1

            layout.addWidget(QLabel(f"Value [{i}]:"), row, col)
            spin = QDoubleSpinBox()
            spin.setRange(-1000000, 1000000)
            spin.setDecimals(2)
            spin.setValue(0.0)
            setattr(self, f"lookup{count}_value{i}", spin)
            layout.addWidget(spin, row, col + 1)

        if count % 2 == 1:
            row += 1

        self.stacked_widget.addWidget(page)

    def _on_operation_changed(self):
        """Handle operation type change"""
        index = self.operation_combo.currentIndex()
        operation = self.operation_combo.currentData()

        # Switch to corresponding page
        self.stacked_widget.setCurrentIndex(index)

        # Update description
        descriptions = {
            "constant": "Returns a fixed constant value",
            "channel": "Returns channel value with optional multiplier",
            "add": "Output = Input1 + Input2",
            "subtract": "Output = Input1 - Input2",
            "multiply": "Output = Input1 × Input2",
            "divide": "Output = Input1 ÷ Input2",
            "modulo": "Output = Input1 mod Input2",
            "min": "Output = min(Input1, Input2)",
            "max": "Output = max(Input1, Input2)",
            "clamp": "Output = value limited to min/max range",
            "lookup2": "2-point lookup table",
            "lookup3": "3-point lookup table",
            "lookup4": "4-point lookup table",
            "lookup5": "5-point lookup table",
        }
        self.op_description.setText(descriptions.get(operation, ""))

    def _get_multiplier_value(self, combo: QComboBox) -> str:
        """Get multiplier combo current value"""
        return combo.currentData() or ChannelMultiplier.MUL_1.value

    def _set_multiplier_value(self, combo: QComboBox, value: str):
        """Set multiplier combo by value"""
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        operation = config.get("operation", "constant")
        for i in range(self.operation_combo.count()):
            if self.operation_combo.itemData(i) == operation:
                self.operation_combo.setCurrentIndex(i)
                break

        self.decimal_spin.setValue(config.get("decimal_places", 2))

        inputs = config.get("inputs", [])
        multipliers = config.get("input_multipliers", [])

        if operation == "constant":
            self.constant_value_spin.setValue(config.get("constant_value", 0.0))

        elif operation == "channel":
            if inputs:
                self.channel_edit.setText(inputs[0])
            if multipliers:
                self._set_multiplier_value(self.channel_multiplier, multipliers[0])

        elif operation in ["add", "subtract", "multiply", "divide", "modulo", "min", "max"]:
            edit1 = getattr(self, f"{operation}_input1_edit")
            edit2 = getattr(self, f"{operation}_input2_edit")
            mult1 = getattr(self, f"{operation}_input1_mult")
            mult2 = getattr(self, f"{operation}_input2_mult")
            if len(inputs) >= 1:
                edit1.setText(inputs[0])
            if len(inputs) >= 2:
                edit2.setText(inputs[1])
            if len(multipliers) >= 1:
                self._set_multiplier_value(mult1, multipliers[0])
            if len(multipliers) >= 2:
                self._set_multiplier_value(mult2, multipliers[1])

        elif operation == "clamp":
            if inputs:
                self.clamp_edit.setText(inputs[0])
            if multipliers:
                self._set_multiplier_value(self.clamp_mult, multipliers[0])
            self.clamp_min_spin.setValue(config.get("clamp_min", 0.0))
            self.clamp_max_spin.setValue(config.get("clamp_max", 100.0))

        elif operation.startswith("lookup"):
            count = int(operation[-1])
            edit = getattr(self, f"lookup{count}_edit")
            mult = getattr(self, f"lookup{count}_mult")
            if inputs:
                edit.setText(inputs[0])
            if multipliers:
                self._set_multiplier_value(mult, multipliers[0])
            lookup_values = config.get("lookup_values", [])
            for i in range(count):
                spin = getattr(self, f"lookup{count}_value{i}")
                if i < len(lookup_values):
                    spin.setValue(lookup_values[i])

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []
        operation = self.operation_combo.currentData()

        if operation == "channel":
            if not self.channel_edit.text().strip():
                errors.append("Channel is required")

        elif operation in ["add", "subtract", "multiply", "divide", "modulo", "min", "max"]:
            edit1 = getattr(self, f"{operation}_input1_edit")
            edit2 = getattr(self, f"{operation}_input2_edit")
            if not edit1.text().strip():
                errors.append("Input 1 is required")
            if not edit2.text().strip():
                errors.append("Input 2 is required")

        elif operation == "clamp":
            if not self.clamp_edit.text().strip():
                errors.append("Input is required")
            if self.clamp_min_spin.value() >= self.clamp_max_spin.value():
                errors.append("Minimum must be less than maximum")

        elif operation.startswith("lookup"):
            count = int(operation[-1])
            edit = getattr(self, f"lookup{count}_edit")
            if not edit.text().strip():
                errors.append("Channel is required")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()
        operation = self.operation_combo.currentData()

        config["operation"] = operation
        config["inputs"] = []
        config["input_multipliers"] = []
        config["constant_value"] = 0.0
        config["clamp_min"] = 0.0
        config["clamp_max"] = 100.0
        config["lookup_values"] = []
        config["decimal_places"] = self.decimal_spin.value()

        if operation == "constant":
            config["constant_value"] = self.constant_value_spin.value()

        elif operation == "channel":
            config["inputs"] = [self.channel_edit.text().strip()]
            config["input_multipliers"] = [self._get_multiplier_value(self.channel_multiplier)]

        elif operation in ["add", "subtract", "multiply", "divide", "modulo", "min", "max"]:
            edit1 = getattr(self, f"{operation}_input1_edit")
            edit2 = getattr(self, f"{operation}_input2_edit")
            mult1 = getattr(self, f"{operation}_input1_mult")
            mult2 = getattr(self, f"{operation}_input2_mult")
            config["inputs"] = [edit1.text().strip(), edit2.text().strip()]
            config["input_multipliers"] = [
                self._get_multiplier_value(mult1),
                self._get_multiplier_value(mult2)
            ]

        elif operation == "clamp":
            config["inputs"] = [self.clamp_edit.text().strip()]
            config["input_multipliers"] = [self._get_multiplier_value(self.clamp_mult)]
            config["clamp_min"] = self.clamp_min_spin.value()
            config["clamp_max"] = self.clamp_max_spin.value()

        elif operation.startswith("lookup"):
            count = int(operation[-1])
            edit = getattr(self, f"lookup{count}_edit")
            mult = getattr(self, f"lookup{count}_mult")
            config["inputs"] = [edit.text().strip()]
            config["input_multipliers"] = [self._get_multiplier_value(mult)]
            config["lookup_values"] = []
            for i in range(count):
                spin = getattr(self, f"lookup{count}_value{i}")
                config["lookup_values"].append(spin.value())

        return config

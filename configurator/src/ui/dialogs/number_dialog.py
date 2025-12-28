"""
Number (Math Channel) Configuration Dialog
Math operations with operation-specific UI
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QSpinBox,
    QLabel, QStackedWidget, QWidget, QGridLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, MathOperation, ChannelMultiplier
from models.quantities import (
    get_quantity_names, get_units_for_quantity, get_default_unit, DisplayConfig
)
from ui.widgets.constant_spinbox import ConstantSpinBox


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

        # Initialize decimal places on all spinboxes
        self._on_decimal_places_changed(self.decimal_spin.value())

        # Connect operation change
        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        # Initialize view
        self._on_operation_changed()

        # Finalize UI sizing
        self._finalize_ui()

    def _create_operation_group(self):
        """Create operation selection group"""
        op_group = QGroupBox("Operation Type")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Operation selection
        layout.addWidget(QLabel("Operation:"), 0, 0)
        self.operation_combo = QComboBox()
        for op in MathOperation:
            self.operation_combo.addItem(self.OPERATION_NAMES[op], op.value)
        layout.addWidget(self.operation_combo, 0, 1, 1, 3)

        # Quantity/Unit row
        layout.addWidget(QLabel("Quantity/Unit:"), 1, 0)

        qu_container = QWidget()
        qu_layout = QHBoxLayout(qu_container)
        qu_layout.setContentsMargins(0, 0, 0, 0)
        qu_layout.setSpacing(4)

        self.quantity_combo = QComboBox()
        self.quantity_combo.setMinimumWidth(120)
        for name in get_quantity_names():
            self.quantity_combo.addItem(name)
        self.quantity_combo.currentTextChanged.connect(self._on_quantity_changed)
        qu_layout.addWidget(self.quantity_combo)

        self.unit_combo = QComboBox()
        self.unit_combo.setMinimumWidth(70)
        qu_layout.addWidget(self.unit_combo)

        qu_layout.addStretch()
        layout.addWidget(qu_container, 1, 1, 1, 3)

        # Decimal places row
        layout.addWidget(QLabel("Decimal places:"), 2, 0)
        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(0, 4)
        self.decimal_spin.setValue(2)  # Default 2 decimals
        self.decimal_spin.setToolTip("Number of decimal places for display (0-4)")
        self.decimal_spin.valueChanged.connect(self._on_decimal_places_changed)
        layout.addWidget(self.decimal_spin, 2, 1)

        # Operation description
        self.op_description = QLabel("")
        self.op_description.setStyleSheet("color: #b0b0b0; font-style: italic;")
        self.op_description.setWordWrap(True)
        layout.addWidget(self.op_description, 3, 0, 1, 4)

        op_group.setLayout(layout)
        self.content_layout.addWidget(op_group)

        # Initialize units
        self._update_units()

    def _on_quantity_changed(self, quantity: str):
        """Handle quantity selection change."""
        self._update_units()

    def _update_units(self):
        """Update unit combo based on selected quantity."""
        quantity = self.quantity_combo.currentText()
        units = get_units_for_quantity(quantity)
        default_unit = get_default_unit(quantity)

        self.unit_combo.clear()
        for unit in units:
            self.unit_combo.addItem(unit.symbol)

        index = self.unit_combo.findText(default_unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

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
        self.constant_value_spin = ConstantSpinBox()
        self.constant_value_spin.setRange(-10000.00, 10000.00)  # Display range
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
        self.clamp_min_spin = ConstantSpinBox()
        self.clamp_min_spin.setRange(-10000.00, 10000.00)
        self.clamp_min_spin.setValue(0.0)
        layout.addWidget(self.clamp_min_spin, 1, 1)

        layout.addWidget(QLabel("Maximum:"), 1, 2)
        self.clamp_max_spin = ConstantSpinBox()
        self.clamp_max_spin.setRange(-10000.00, 10000.00)
        self.clamp_max_spin.setValue(100.0)
        layout.addWidget(self.clamp_max_spin, 1, 3)

        self.stacked_widget.addWidget(page)

    def _create_lookup_page(self, count: int):
        """Create lookup page with selector + N channel inputs.

        Lookup operation: Selector value (0 to N-1) determines which of the
        N input channels to use as output. For example:
        - Lookup4: selector=2 outputs the value from Channel [2]
        """
        page = QWidget()
        layout = QGridLayout(page)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Selector channel with multiplier (determines which input to use)
        layout.addWidget(QLabel("Selector: *"), 0, 0)
        container, edit, mult = self._create_channel_with_multiplier("Select selector channel...")
        setattr(self, f"lookup{count}_selector_container", container)
        setattr(self, f"lookup{count}_selector_edit", edit)
        setattr(self, f"lookup{count}_selector_mult", mult)
        layout.addWidget(container, 0, 1, 1, 3)

        # N input channel selectors (channels to select from)
        row = 1
        for i in range(count):
            col = (i % 2) * 2
            if i % 2 == 0 and i > 0:
                row += 1

            layout.addWidget(QLabel(f"Channel [{i}]:"), row, col)
            ch_container, ch_edit, ch_mult = self._create_channel_with_multiplier(f"Select channel {i}...")
            setattr(self, f"lookup{count}_ch{i}_container", ch_container)
            setattr(self, f"lookup{count}_ch{i}_edit", ch_edit)
            setattr(self, f"lookup{count}_ch{i}_mult", ch_mult)
            layout.addWidget(ch_container, row, col + 1)

        if count % 2 == 1:
            row += 1

        self.stacked_widget.addWidget(page)

    def _on_decimal_places_changed(self, value: int):
        """
        Handle decimal places setting change.

        Note: ConstantSpinBox always uses 2 decimal places for input.
        The decimal_places setting is stored in config for display purposes
        (e.g., in monitors or when formatting output values).
        """
        # ConstantSpinBox uses fixed 2 decimal places - no dynamic update needed
        # decimal_places value is saved in config for display formatting elsewhere
        pass

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
            "lookup2": "Selector 0-1 selects from 2 channels",
            "lookup3": "Selector 0-2 selects from 3 channels",
            "lookup4": "Selector 0-3 selects from 4 channels",
            "lookup5": "Selector 0-4 selects from 5 channels",
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

        # Load quantity/unit settings
        quantity = config.get("quantity", "User")
        unit = config.get("unit", "user")
        decimal_places = config.get("decimal_places", 2)  # Default 2 decimals

        index = self.quantity_combo.findText(quantity)
        if index >= 0:
            self.quantity_combo.setCurrentIndex(index)
        self._update_units()

        index = self.unit_combo.findText(unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

        self.decimal_spin.setValue(decimal_places)

        inputs = config.get("inputs", [])
        multipliers = config.get("input_multipliers", [])

        if operation == "constant":
            self.constant_value_spin.setValue(config.get("constant_value", 0.0))

        elif operation == "channel":
            if inputs:
                self._set_channel_edit_value(self.channel_edit, inputs[0])
            if multipliers:
                self._set_multiplier_value(self.channel_multiplier, multipliers[0])

        elif operation in ["add", "subtract", "multiply", "divide", "modulo", "min", "max"]:
            edit1 = getattr(self, f"{operation}_input1_edit")
            edit2 = getattr(self, f"{operation}_input2_edit")
            mult1 = getattr(self, f"{operation}_input1_mult")
            mult2 = getattr(self, f"{operation}_input2_mult")
            if len(inputs) >= 1:
                self._set_channel_edit_value(edit1, inputs[0])
            if len(inputs) >= 2:
                self._set_channel_edit_value(edit2, inputs[1])
            if len(multipliers) >= 1:
                self._set_multiplier_value(mult1, multipliers[0])
            if len(multipliers) >= 2:
                self._set_multiplier_value(mult2, multipliers[1])

        elif operation == "clamp":
            if inputs:
                self._set_channel_edit_value(self.clamp_edit, inputs[0])
            if multipliers:
                self._set_multiplier_value(self.clamp_mult, multipliers[0])
            self.clamp_min_spin.setValue(config.get("clamp_min", 0.0))
            self.clamp_max_spin.setValue(config.get("clamp_max", 100.0))

        elif operation.startswith("lookup"):
            count = int(operation[-1])
            # Load selector channel
            selector_edit = getattr(self, f"lookup{count}_selector_edit")
            selector_mult = getattr(self, f"lookup{count}_selector_mult")
            selector_channel = config.get("selector_channel")
            selector_multiplier = config.get("selector_multiplier", "mul_1")
            if selector_channel:
                self._set_channel_edit_value(selector_edit, selector_channel)
            self._set_multiplier_value(selector_mult, selector_multiplier)

            # Load lookup input channels
            lookup_channels = config.get("lookup_channels", inputs or [])
            lookup_multipliers = config.get("lookup_multipliers", multipliers or [])
            for i in range(count):
                ch_edit = getattr(self, f"lookup{count}_ch{i}_edit")
                ch_mult = getattr(self, f"lookup{count}_ch{i}_mult")
                if i < len(lookup_channels) and lookup_channels[i]:
                    self._set_channel_edit_value(ch_edit, lookup_channels[i])
                if i < len(lookup_multipliers):
                    self._set_multiplier_value(ch_mult, lookup_multipliers[i])

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
            selector_edit = getattr(self, f"lookup{count}_selector_edit")
            if not selector_edit.text().strip():
                errors.append("Selector channel is required")
            # At least one input channel should be selected
            has_any_channel = False
            for i in range(count):
                ch_edit = getattr(self, f"lookup{count}_ch{i}_edit")
                if ch_edit.text().strip():
                    has_any_channel = True
                    break
            if not has_any_channel:
                errors.append("At least one input channel is required")

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

        # Quantity/Unit display settings
        config["quantity"] = self.quantity_combo.currentText()
        config["unit"] = self.unit_combo.currentText()
        config["decimal_places"] = self.decimal_spin.value()

        if operation == "constant":
            config["constant_value"] = self.constant_value_spin.value()

        elif operation == "channel":
            channel_id = self._get_channel_id_from_edit(self.channel_edit)
            config["inputs"] = [channel_id if channel_id else ""]
            config["input_multipliers"] = [self._get_multiplier_value(self.channel_multiplier)]

        elif operation in ["add", "subtract", "multiply", "divide", "modulo", "min", "max"]:
            edit1 = getattr(self, f"{operation}_input1_edit")
            edit2 = getattr(self, f"{operation}_input2_edit")
            mult1 = getattr(self, f"{operation}_input1_mult")
            mult2 = getattr(self, f"{operation}_input2_mult")
            ch_id1 = self._get_channel_id_from_edit(edit1)
            ch_id2 = self._get_channel_id_from_edit(edit2)
            config["inputs"] = [ch_id1 if ch_id1 else "", ch_id2 if ch_id2 else ""]
            config["input_multipliers"] = [
                self._get_multiplier_value(mult1),
                self._get_multiplier_value(mult2)
            ]

        elif operation == "clamp":
            channel_id = self._get_channel_id_from_edit(self.clamp_edit)
            config["inputs"] = [channel_id if channel_id else ""]
            config["input_multipliers"] = [self._get_multiplier_value(self.clamp_mult)]
            config["clamp_min"] = self.clamp_min_spin.value()
            config["clamp_max"] = self.clamp_max_spin.value()

        elif operation.startswith("lookup"):
            count = int(operation[-1])
            # Save selector channel
            selector_edit = getattr(self, f"lookup{count}_selector_edit")
            selector_mult = getattr(self, f"lookup{count}_selector_mult")
            selector_id = self._get_channel_id_from_edit(selector_edit)
            config["selector_channel"] = selector_id if selector_id else ""
            config["selector_multiplier"] = self._get_multiplier_value(selector_mult)

            # Save lookup input channels
            lookup_channels = []
            lookup_multipliers = []
            for i in range(count):
                ch_edit = getattr(self, f"lookup{count}_ch{i}_edit")
                ch_mult = getattr(self, f"lookup{count}_ch{i}_mult")
                ch_id = self._get_channel_id_from_edit(ch_edit)
                lookup_channels.append(ch_id if ch_id else "")
                lookup_multipliers.append(self._get_multiplier_value(ch_mult))

            config["lookup_channels"] = lookup_channels
            config["lookup_multipliers"] = lookup_multipliers
            # Keep backwards compatibility
            config["inputs"] = [config["selector_channel"]]
            config["input_multipliers"] = [config["selector_multiplier"]]

        return config

    def _finalize_ui(self):
        """Override to customize dialog size - compact form."""
        self.adjustSize()
        current_size = self.sizeHint()

        # Apply size adjustments:
        # - Width: 1.3x (slightly wider than content)
        # - Height: 0.7x (30% reduction)
        new_width = int(current_size.width() * 1.3)
        new_height = int(current_size.height() * 0.7)

        self.resize(new_width, new_height)
        self.setMinimumSize(new_width, new_height)

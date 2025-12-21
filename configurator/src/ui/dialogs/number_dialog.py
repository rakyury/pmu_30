"""
Number (Math Channel) Configuration Dialog
Math channels with operation-specific UI for each function type
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QDoubleSpinBox, QDialogButtonBox, QGroupBox, QComboBox,
    QPushButton, QLabel, QWidget, QStackedWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional
from .channel_selector_dialog import ChannelSelectorDialog


class NumberDialog(QDialog):
    """Dialog for configuring math channels with operation-specific UI."""

    # Mathematical operations
    MATH_OPERATIONS = [
        "constant",
        "add",
        "subtract",
        "multiply",
        "divide",
        "min",
        "max",
        "average",
        "abs",
        "scale",
        "clamp",
        "conditional"  # if-then-else
    ]

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None, available_channels: Optional[Dict] = None):
        super().__init__(parent)
        self.config = config or {}
        self.available_channels = available_channels or {}
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Number (Math Channel) Configuration")
        self.setMinimumWidth(550)

        layout = QVBoxLayout(self)

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., n_total_current, n_boost_pressure")
        basic_layout.addRow("Name: *", self.name_edit)

        # Operation type
        self.operation_combo = QComboBox()
        self.operation_combo.addItems(self.MATH_OPERATIONS)
        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)
        basic_layout.addRow("Operation:", self.operation_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Stacked widget for operation-specific parameters
        self.params_group = QGroupBox("Operation Parameters")
        params_layout = QVBoxLayout()

        self.stacked_widget = QStackedWidget()
        params_layout.addWidget(self.stacked_widget)

        self.params_group.setLayout(params_layout)
        layout.addWidget(self.params_group)

        # Create pages for all operations
        self._create_operation_pages()

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initialize state
        self._on_operation_changed(0)

    def _create_channel_selector(self, placeholder: str = "Select channel..."):
        """Helper to create a channel selector layout."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setReadOnly(True)
        layout.addWidget(edit, stretch=1)

        btn = QPushButton("Browse...")
        btn.clicked.connect(lambda: self._browse_channel(edit))
        layout.addWidget(btn)

        return container, edit

    def _create_operation_pages(self):
        """Create all operation-specific pages."""

        # Page 0: Constant
        page_constant = QWidget()
        layout_constant = QFormLayout(page_constant)

        self.constant_value_spin = QDoubleSpinBox()
        self.constant_value_spin.setRange(-1000000, 1000000)
        self.constant_value_spin.setDecimals(4)
        self.constant_value_spin.setSingleStep(0.1)
        layout_constant.addRow("Value:", self.constant_value_spin)

        self.constant_unit_edit = QLineEdit()
        self.constant_unit_edit.setPlaceholderText("e.g., °C, bar, rpm...")
        layout_constant.addRow("Unit:", self.constant_unit_edit)

        self.stacked_widget.addWidget(page_constant)

        # Page 1-4: Binary operations (add, subtract, multiply, divide)
        for op_name in ["add", "subtract", "multiply", "divide"]:
            page = QWidget()
            layout_form = QFormLayout(page)

            widget1, edit1 = self._create_channel_selector()
            setattr(self, f"{op_name}_value1_widget", widget1)
            setattr(self, f"{op_name}_value1_edit", edit1)
            layout_form.addRow("Value 1:", widget1)

            widget2, edit2 = self._create_channel_selector()
            setattr(self, f"{op_name}_value2_widget", widget2)
            setattr(self, f"{op_name}_value2_edit", edit2)
            layout_form.addRow("Value 2:", widget2)

            self.stacked_widget.addWidget(page)

        # Page 5-7: Multi-value operations (min, max, average)
        for op_name in ["min", "max", "average"]:
            page = QWidget()
            layout_form = QFormLayout(page)

            widget1, edit1 = self._create_channel_selector()
            setattr(self, f"{op_name}_value1_widget", widget1)
            setattr(self, f"{op_name}_value1_edit", edit1)
            layout_form.addRow("Value 1:", widget1)

            widget2, edit2 = self._create_channel_selector()
            setattr(self, f"{op_name}_value2_widget", widget2)
            setattr(self, f"{op_name}_value2_edit", edit2)
            layout_form.addRow("Value 2:", widget2)

            widget3, edit3 = self._create_channel_selector("Select channel (optional)...")
            setattr(self, f"{op_name}_value3_widget", widget3)
            setattr(self, f"{op_name}_value3_edit", edit3)
            layout_form.addRow("Value 3 (optional):", widget3)

            self.stacked_widget.addWidget(page)

        # Page 8: Abs
        page_abs = QWidget()
        layout_abs = QFormLayout(page_abs)

        self.abs_channel_widget, self.abs_channel_edit = self._create_channel_selector()
        layout_abs.addRow("Channel:", self.abs_channel_widget)

        self.stacked_widget.addWidget(page_abs)

        # Page 9: Scale
        page_scale = QWidget()
        layout_scale = QFormLayout(page_scale)

        self.scale_channel_widget, self.scale_channel_edit = self._create_channel_selector()
        layout_scale.addRow("Channel:", self.scale_channel_widget)

        self.scale_multiplier_spin = QDoubleSpinBox()
        self.scale_multiplier_spin.setRange(-1000, 1000)
        self.scale_multiplier_spin.setDecimals(4)
        self.scale_multiplier_spin.setValue(1.0)
        self.scale_multiplier_spin.setToolTip("Output = Input × Multiplier + Offset")
        layout_scale.addRow("Multiplier:", self.scale_multiplier_spin)

        self.scale_offset_spin = QDoubleSpinBox()
        self.scale_offset_spin.setRange(-1000000, 1000000)
        self.scale_offset_spin.setDecimals(2)
        self.scale_offset_spin.setValue(0.0)
        layout_scale.addRow("Offset:", self.scale_offset_spin)

        self.stacked_widget.addWidget(page_scale)

        # Page 10: Clamp
        page_clamp = QWidget()
        layout_clamp = QFormLayout(page_clamp)

        self.clamp_channel_widget, self.clamp_channel_edit = self._create_channel_selector()
        layout_clamp.addRow("Channel:", self.clamp_channel_widget)

        self.clamp_min_spin = QDoubleSpinBox()
        self.clamp_min_spin.setRange(-1000000, 1000000)
        self.clamp_min_spin.setDecimals(2)
        self.clamp_min_spin.setValue(0.0)
        self.clamp_min_spin.setToolTip("Minimum output value")
        layout_clamp.addRow("Minimum:", self.clamp_min_spin)

        self.clamp_max_spin = QDoubleSpinBox()
        self.clamp_max_spin.setRange(-1000000, 1000000)
        self.clamp_max_spin.setDecimals(2)
        self.clamp_max_spin.setValue(100.0)
        self.clamp_max_spin.setToolTip("Maximum output value")
        layout_clamp.addRow("Maximum:", self.clamp_max_spin)

        self.stacked_widget.addWidget(page_clamp)

        # Page 11: Conditional
        page_cond = QWidget()
        layout_cond = QFormLayout(page_cond)

        self.cond_condition_widget, self.cond_condition_edit = self._create_channel_selector("Select condition channel...")
        layout_cond.addRow("Condition channel:", self.cond_condition_widget)

        self.cond_true_widget, self.cond_true_edit = self._create_channel_selector("Select channel for true...")
        layout_cond.addRow("Result if true:", self.cond_true_widget)

        self.cond_false_widget, self.cond_false_edit = self._create_channel_selector("Select channel for false...")
        layout_cond.addRow("Result if false:", self.cond_false_widget)

        self.stacked_widget.addWidget(page_cond)

    def _on_operation_changed(self, index: int):
        """Handle operation type change - switch to appropriate page."""
        # Map operation index to page index
        self.stacked_widget.setCurrentIndex(index)

    def _browse_channel(self, target_edit: QLineEdit):
        """Browse and select channel for target field."""
        current = target_edit.text()
        channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if channel:
            target_edit.setText(channel)

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        operation = self.operation_combo.currentText()

        # Validate operation-specific fields
        if operation in ["add", "subtract", "multiply", "divide"]:
            edit1 = getattr(self, f"{operation}_value1_edit")
            edit2 = getattr(self, f"{operation}_value2_edit")
            if not edit1.text().strip():
                QMessageBox.warning(self, "Validation Error", "Value 1 is required!")
                return
            if not edit2.text().strip():
                QMessageBox.warning(self, "Validation Error", "Value 2 is required!")
                return

        elif operation in ["min", "max", "average"]:
            edit1 = getattr(self, f"{operation}_value1_edit")
            edit2 = getattr(self, f"{operation}_value2_edit")
            if not edit1.text().strip():
                QMessageBox.warning(self, "Validation Error", "Value 1 is required!")
                return
            if not edit2.text().strip():
                QMessageBox.warning(self, "Validation Error", "Value 2 is required!")
                return

        elif operation == "abs":
            if not self.abs_channel_edit.text().strip():
                QMessageBox.warning(self, "Validation Error", "Channel is required!")
                return

        elif operation == "scale":
            if not self.scale_channel_edit.text().strip():
                QMessageBox.warning(self, "Validation Error", "Channel is required!")
                return

        elif operation == "clamp":
            if not self.clamp_channel_edit.text().strip():
                QMessageBox.warning(self, "Validation Error", "Channel is required!")
                return
            if self.clamp_min_spin.value() >= self.clamp_max_spin.value():
                QMessageBox.warning(self, "Validation Error", "Minimum value must be less than maximum value!")
                return

        elif operation == "conditional":
            if not self.cond_condition_edit.text().strip():
                QMessageBox.warning(self, "Validation Error", "Condition channel is required!")
                return
            if not self.cond_true_edit.text().strip():
                QMessageBox.warning(self, "Validation Error", "Result if true is required!")
                return
            if not self.cond_false_edit.text().strip():
                QMessageBox.warning(self, "Validation Error", "Result if false is required!")
                return

        self.accept()

    def _load_config(self):
        """Load configuration into UI."""
        if not self.config:
            return

        self.name_edit.setText(self.config.get("name", ""))

        # Load operation type
        operation = self.config.get("operation", "constant")
        idx = self.operation_combo.findText(operation)
        if idx >= 0:
            self.operation_combo.setCurrentIndex(idx)

        # Load operation-specific data
        if operation == "constant":
            self.constant_value_spin.setValue(self.config.get("value", 0.0))
            self.constant_unit_edit.setText(self.config.get("unit", ""))

        else:
            inputs = self.config.get("inputs", [])
            params = self.config.get("parameters", {})

            if operation in ["add", "subtract", "multiply", "divide"]:
                edit1 = getattr(self, f"{operation}_value1_edit")
                edit2 = getattr(self, f"{operation}_value2_edit")
                if len(inputs) >= 1:
                    edit1.setText(inputs[0])
                if len(inputs) >= 2:
                    edit2.setText(inputs[1])

            elif operation in ["min", "max", "average"]:
                edit1 = getattr(self, f"{operation}_value1_edit")
                edit2 = getattr(self, f"{operation}_value2_edit")
                edit3 = getattr(self, f"{operation}_value3_edit")
                if len(inputs) >= 1:
                    edit1.setText(inputs[0])
                if len(inputs) >= 2:
                    edit2.setText(inputs[1])
                if len(inputs) >= 3:
                    edit3.setText(inputs[2])

            elif operation == "abs":
                if len(inputs) >= 1:
                    self.abs_channel_edit.setText(inputs[0])

            elif operation == "scale":
                if len(inputs) >= 1:
                    self.scale_channel_edit.setText(inputs[0])
                self.scale_multiplier_spin.setValue(params.get("multiplier", 1.0))
                self.scale_offset_spin.setValue(params.get("offset", 0.0))

            elif operation == "clamp":
                if len(inputs) >= 1:
                    self.clamp_channel_edit.setText(inputs[0])
                self.clamp_min_spin.setValue(params.get("min", 0.0))
                self.clamp_max_spin.setValue(params.get("max", 100.0))

            elif operation == "conditional":
                if len(inputs) >= 1:
                    self.cond_condition_edit.setText(inputs[0])
                if len(inputs) >= 2:
                    self.cond_true_edit.setText(inputs[1])
                if len(inputs) >= 3:
                    self.cond_false_edit.setText(inputs[2])

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from UI."""
        operation = self.operation_combo.currentText()

        config = {
            "name": self.name_edit.text(),
            "operation": operation,
            "value": 0.0,
            "unit": "",
            "inputs": [],
            "parameters": {}
        }

        if operation == "constant":
            config["value"] = self.constant_value_spin.value()
            config["unit"] = self.constant_unit_edit.text()

        elif operation in ["add", "subtract", "multiply", "divide"]:
            edit1 = getattr(self, f"{operation}_value1_edit")
            edit2 = getattr(self, f"{operation}_value2_edit")
            config["inputs"] = [edit1.text(), edit2.text()]

        elif operation in ["min", "max", "average"]:
            edit1 = getattr(self, f"{operation}_value1_edit")
            edit2 = getattr(self, f"{operation}_value2_edit")
            edit3 = getattr(self, f"{operation}_value3_edit")
            inputs = [edit1.text(), edit2.text()]
            if edit3.text().strip():
                inputs.append(edit3.text())
            config["inputs"] = inputs

        elif operation == "abs":
            config["inputs"] = [self.abs_channel_edit.text()]

        elif operation == "scale":
            config["inputs"] = [self.scale_channel_edit.text()]
            config["parameters"] = {
                "multiplier": self.scale_multiplier_spin.value(),
                "offset": self.scale_offset_spin.value()
            }

        elif operation == "clamp":
            config["inputs"] = [self.clamp_channel_edit.text()]
            config["parameters"] = {
                "min": self.clamp_min_spin.value(),
                "max": self.clamp_max_spin.value()
            }

        elif operation == "conditional":
            config["inputs"] = [
                self.cond_condition_edit.text(),
                self.cond_true_edit.text(),
                self.cond_false_edit.text()
            ]

        return config

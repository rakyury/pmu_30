"""
Logic Function Configuration Dialog
Configures a single logic function for the PMU-30 Logic Engine
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QListWidget,
    QLabel, QListWidgetItem
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List


class LogicFunctionDialog(QDialog):
    """Dialog for configuring a single logic function."""

    OPERATION_TYPES = [
        "AND", "OR", "NOT", "XOR", "NAND", "NOR",
        "Timer ON Delay", "Timer OFF Delay", "Counter",
        "Compare >", "Compare <", "Compare ==",
        "Math Add", "Math Subtract", "Math Multiply", "Math Divide"
    ]

    INPUT_TYPES = [
        "Physical Input", "Physical Output", "Virtual Channel", "Constant"
    ]

    def __init__(self, parent=None, function_config: Optional[Dict[str, Any]] = None,
                 used_channels=None):
        super().__init__(parent)
        self.function_config = function_config
        self.used_channels = used_channels or []

        self.setWindowTitle("Logic Function Configuration")
        self.setModal(True)
        self.resize(600, 500)

        self._init_ui()

        if function_config:
            self._load_config(function_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Brake Light Logic, Engine Start")
        basic_layout.addRow("Name: *", self.name_edit)

        self.operation_combo = QComboBox()
        self.operation_combo.addItems(self.OPERATION_TYPES)
        self.operation_combo.currentTextChanged.connect(self._on_operation_changed)
        basic_layout.addRow("Operation:", self.operation_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Inputs group
        inputs_group = QGroupBox("Inputs")
        inputs_layout = QVBoxLayout()

        # Input list
        self.inputs_list = QListWidget()
        self.inputs_list.setMaximumHeight(150)
        inputs_layout.addWidget(QLabel("Configured Inputs:"))
        inputs_layout.addWidget(self.inputs_list)

        # Add input controls
        add_input_layout = QHBoxLayout()

        self.input_type_combo = QComboBox()
        self.input_type_combo.addItems(self.INPUT_TYPES)
        self.input_type_combo.currentTextChanged.connect(self._on_input_type_changed)
        add_input_layout.addWidget(QLabel("Type:"))
        add_input_layout.addWidget(self.input_type_combo)

        self.input_channel_spin = QSpinBox()
        self.input_channel_spin.setRange(0, 255)
        add_input_layout.addWidget(QLabel("Channel:"))
        add_input_layout.addWidget(self.input_channel_spin)

        self.add_input_btn = QPushButton("Add Input")
        self.add_input_btn.clicked.connect(self._add_input)
        add_input_layout.addWidget(self.add_input_btn)

        self.remove_input_btn = QPushButton("Remove Selected")
        self.remove_input_btn.clicked.connect(self._remove_input)
        add_input_layout.addWidget(self.remove_input_btn)

        inputs_layout.addLayout(add_input_layout)
        inputs_group.setLayout(inputs_layout)
        layout.addWidget(inputs_group)

        # Timer/Counter parameters (shown conditionally)
        self.params_group = QGroupBox("Parameters")
        params_layout = QFormLayout()

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 60000)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setToolTip("Delay time in milliseconds")
        params_layout.addRow("Delay Time:", self.delay_spin)

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 10000)
        self.threshold_spin.setToolTip("Counter threshold or comparison value")
        params_layout.addRow("Threshold:", self.threshold_spin)

        self.params_group.setLayout(params_layout)
        layout.addWidget(self.params_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize state
        self._on_operation_changed(self.operation_combo.currentText())

    def _on_accept(self):
        """Validate and accept dialog."""
        # Validate name (required field)
        if not self.name_edit.text().strip():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _on_operation_changed(self, operation: str):
        """Handle operation type change."""
        # Show/hide parameters based on operation
        show_params = any(op in operation for op in ["Timer", "Counter", "Compare"])
        self.params_group.setVisible(show_params)

        if "Timer" in operation:
            self.delay_spin.setVisible(True)
            self.threshold_spin.setVisible(False)
        elif "Counter" in operation:
            self.delay_spin.setVisible(False)
            self.threshold_spin.setVisible(True)
        elif "Compare" in operation:
            self.delay_spin.setVisible(False)
            self.threshold_spin.setVisible(True)
        else:
            self.delay_spin.setVisible(False)
            self.threshold_spin.setVisible(False)

    def _on_input_type_changed(self, input_type: str):
        """Handle input type change."""
        if input_type == "Physical Input":
            self.input_channel_spin.setRange(0, 19)
            self.input_channel_spin.setToolTip("Physical input channel (0-19)")
        elif input_type == "Physical Output":
            self.input_channel_spin.setRange(0, 29)
            self.input_channel_spin.setToolTip("Physical output channel (0-29)")
        elif input_type == "Virtual Channel":
            self.input_channel_spin.setRange(0, 255)
            self.input_channel_spin.setToolTip("Virtual channel (0-255)")
        else:  # Constant
            self.input_channel_spin.setRange(0, 1)
            self.input_channel_spin.setToolTip("Constant value (0 or 1)")

    def _add_input(self):
        """Add input to the list."""
        input_type = self.input_type_combo.currentText()
        channel = self.input_channel_spin.value()

        input_str = f"{input_type}: {channel}"
        self.inputs_list.addItem(input_str)

    def _remove_input(self):
        """Remove selected input from the list."""
        current_row = self.inputs_list.currentRow()
        if current_row >= 0:
            self.inputs_list.takeItem(current_row)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))

        operation = config.get("operation", "AND")
        index = self.operation_combo.findText(operation)
        if index >= 0:
            self.operation_combo.setCurrentIndex(index)

        # Load inputs
        inputs = config.get("inputs", [])
        for inp in inputs:
            input_type = inp.get("type", "Virtual Channel")
            channel = inp.get("channel", 0)
            input_str = f"{input_type}: {channel}"
            self.inputs_list.addItem(input_str)

        # Load parameters
        params = config.get("parameters", {})
        self.delay_spin.setValue(params.get("delay_ms", 0))
        self.threshold_spin.setValue(params.get("threshold", 0))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        # Parse inputs from list
        inputs = []
        for i in range(self.inputs_list.count()):
            item_text = self.inputs_list.item(i).text()
            # Parse "Type: Channel"
            parts = item_text.split(": ")
            if len(parts) == 2:
                inputs.append({
                    "type": parts[0],
                    "channel": int(parts[1])
                })

        config = {
            "name": self.name_edit.text().strip(),
            "operation": self.operation_combo.currentText(),
            "inputs": inputs,
            "parameters": {
                "delay_ms": self.delay_spin.value(),
                "threshold": self.threshold_spin.value()
            }
        }

        return config

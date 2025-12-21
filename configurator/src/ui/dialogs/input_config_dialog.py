"""
Input Channel Configuration Dialog
Configures one of 20 universal analog/digital inputs
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class InputConfigDialog(QDialog):
    """Dialog for configuring a single input channel."""

    INPUT_TYPES = [
        "Switch Active Low",
        "Switch Active High",
        "Rotary Switch",
        "Linear Analog",
        "Calibrated Analog",
        "Frequency Input"
    ]

    def __init__(self, parent=None, input_config: Optional[Dict[str, Any]] = None, used_channels=None):
        super().__init__(parent)
        self.input_config = input_config
        self.used_channels = used_channels or []

        self.setWindowTitle("Input Channel Configuration")
        self.setModal(True)
        self.resize(500, 600)

        self._init_ui()

        if input_config:
            self._load_config(input_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        # Channel selection - dropdown with available channels only
        self.channel_combo = QComboBox()
        self.channel_combo.setToolTip("Physical input channel (0-19)")
        self._populate_available_channels()
        basic_layout.addRow("Channel:", self.channel_combo)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Brake Pressure")
        basic_layout.addRow("Name: *", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(self.INPUT_TYPES)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        basic_layout.addRow("Type:", self.type_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Type-specific settings group
        self.type_group = QGroupBox("Type-Specific Settings")
        self.type_layout = QFormLayout()
        self.type_group.setLayout(self.type_layout)
        layout.addWidget(self.type_group)

        # Hardware settings group
        hw_group = QGroupBox("Hardware Settings")
        hw_layout = QFormLayout()

        self.pullup_check = QCheckBox("Enable Pull-up")
        hw_layout.addRow("", self.pullup_check)

        self.pulldown_check = QCheckBox("Enable Pull-down")
        hw_layout.addRow("", self.pulldown_check)

        self.filter_spin = QSpinBox()
        self.filter_spin.setRange(1, 100)
        self.filter_spin.setValue(5)
        self.filter_spin.setToolTip("Number of samples to average (1-100)")
        hw_layout.addRow("Filter Samples:", self.filter_spin)

        hw_group.setLayout(hw_layout)
        layout.addWidget(hw_group)

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

        # Initialize type-specific fields
        self._on_type_changed(0)

    def _clear_type_layout(self):
        """Clear all widgets from type-specific layout."""
        while self.type_layout.rowCount() > 0:
            self.type_layout.removeRow(0)

    def _on_type_changed(self, index):
        """Handle input type change."""
        self._clear_type_layout()

        input_type = self.INPUT_TYPES[index]

        if input_type in ["Switch Active Low", "Switch Active High"]:
            self.debounce_spin = QSpinBox()
            self.debounce_spin.setRange(0, 1000)
            self.debounce_spin.setValue(50)
            self.debounce_spin.setSuffix(" ms")
            self.debounce_spin.setToolTip("Debounce time in milliseconds")
            self.type_layout.addRow("Debounce:", self.debounce_spin)

            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(0.0, 5.0)
            self.threshold_spin.setValue(2.5)
            self.threshold_spin.setSuffix(" V")
            self.threshold_spin.setDecimals(2)
            self.threshold_spin.setSingleStep(0.1)
            self.type_layout.addRow("Threshold:", self.threshold_spin)

        elif input_type == "Rotary Switch":
            self.positions_spin = QSpinBox()
            self.positions_spin.setRange(2, 12)
            self.positions_spin.setValue(4)
            self.positions_spin.setToolTip("Number of switch positions")
            self.type_layout.addRow("Positions:", self.positions_spin)

            self.debounce_spin = QSpinBox()
            self.debounce_spin.setRange(0, 1000)
            self.debounce_spin.setValue(50)
            self.debounce_spin.setSuffix(" ms")
            self.type_layout.addRow("Debounce:", self.debounce_spin)

        elif input_type == "Linear Analog":
            self.min_voltage_spin = QDoubleSpinBox()
            self.min_voltage_spin.setRange(0.0, 5.0)
            self.min_voltage_spin.setValue(0.0)
            self.min_voltage_spin.setSuffix(" V")
            self.min_voltage_spin.setDecimals(2)
            self.min_voltage_spin.setSingleStep(0.1)
            self.type_layout.addRow("Min Voltage:", self.min_voltage_spin)

            self.max_voltage_spin = QDoubleSpinBox()
            self.max_voltage_spin.setRange(0.0, 5.0)
            self.max_voltage_spin.setValue(5.0)
            self.max_voltage_spin.setSuffix(" V")
            self.max_voltage_spin.setDecimals(2)
            self.max_voltage_spin.setSingleStep(0.1)
            self.type_layout.addRow("Max Voltage:", self.max_voltage_spin)

        elif input_type == "Calibrated Analog":
            self.multiplier_spin = QDoubleSpinBox()
            self.multiplier_spin.setRange(-1000.0, 1000.0)
            self.multiplier_spin.setValue(1.0)
            self.multiplier_spin.setDecimals(4)
            self.multiplier_spin.setSingleStep(0.1)
            self.multiplier_spin.setToolTip("Calibration multiplier (output = (voltage * multiplier) + offset)")
            self.type_layout.addRow("Multiplier:", self.multiplier_spin)

            self.offset_spin = QDoubleSpinBox()
            self.offset_spin.setRange(-1000.0, 1000.0)
            self.offset_spin.setValue(0.0)
            self.offset_spin.setDecimals(4)
            self.offset_spin.setSingleStep(0.1)
            self.offset_spin.setToolTip("Calibration offset")
            self.type_layout.addRow("Offset:", self.offset_spin)

            self.unit_edit = QLineEdit()
            self.unit_edit.setPlaceholderText("e.g., bar, °C, %")
            self.unit_edit.setToolTip("Engineering unit")
            self.type_layout.addRow("Unit:", self.unit_edit)

        elif input_type == "Frequency Input":
            self.min_freq_spin = QDoubleSpinBox()
            self.min_freq_spin.setRange(0.0, 10000.0)
            self.min_freq_spin.setValue(0.0)
            self.min_freq_spin.setSuffix(" Hz")
            self.min_freq_spin.setDecimals(1)
            self.type_layout.addRow("Min Frequency:", self.min_freq_spin)

            self.max_freq_spin = QDoubleSpinBox()
            self.max_freq_spin.setRange(0.0, 10000.0)
            self.max_freq_spin.setValue(1000.0)
            self.max_freq_spin.setSuffix(" Hz")
            self.max_freq_spin.setDecimals(1)
            self.type_layout.addRow("Max Frequency:", self.max_freq_spin)

            self.timeout_spin = QSpinBox()
            self.timeout_spin.setRange(10, 10000)
            self.timeout_spin.setValue(1000)
            self.timeout_spin.setSuffix(" ms")
            self.timeout_spin.setToolTip("Timeout for signal loss detection")
            self.type_layout.addRow("Timeout:", self.timeout_spin)

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _populate_available_channels(self):
        """Populate channel dropdown with available channels."""
        self.channel_combo.clear()

        # Get current channel if editing
        current_channel = None
        if self.input_config:
            current_channel = self.input_config.get("channel")

        # Add available channels (0-19)
        for ch in range(20):
            if ch not in self.used_channels or ch == current_channel:
                self.channel_combo.addItem(f"Channel {ch}", ch)

        # If no channels available, add a placeholder
        if self.channel_combo.count() == 0:
            self.channel_combo.addItem("No channels available", -1)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        # Find and select the channel in combo box
        channel = config.get("channel", 0)
        index = self.channel_combo.findData(channel)
        if index >= 0:
            self.channel_combo.setCurrentIndex(index)
        self.name_edit.setText(config.get("name", ""))

        input_type = config.get("type", "Switch Active Low")
        if input_type in self.INPUT_TYPES:
            self.type_combo.setCurrentText(input_type)

        params = config.get("parameters", {})

        # Load hardware settings
        self.pullup_check.setChecked(config.get("pull_up", False))
        self.pulldown_check.setChecked(config.get("pull_down", False))
        self.filter_spin.setValue(config.get("filter_samples", 5))

        # Load type-specific parameters
        if hasattr(self, 'debounce_spin'):
            self.debounce_spin.setValue(params.get("debounce_ms", 50))
        if hasattr(self, 'threshold_spin'):
            self.threshold_spin.setValue(params.get("threshold", 2.5))
        if hasattr(self, 'positions_spin'):
            self.positions_spin.setValue(params.get("positions", 4))
        if hasattr(self, 'min_voltage_spin'):
            self.min_voltage_spin.setValue(params.get("min_voltage", 0.0))
        if hasattr(self, 'max_voltage_spin'):
            self.max_voltage_spin.setValue(params.get("max_voltage", 5.0))
        if hasattr(self, 'multiplier_spin'):
            self.multiplier_spin.setValue(params.get("multiplier", 1.0))
        if hasattr(self, 'offset_spin'):
            self.offset_spin.setValue(params.get("offset", 0.0))
        if hasattr(self, 'unit_edit'):
            self.unit_edit.setText(params.get("unit", ""))
        if hasattr(self, 'min_freq_spin'):
            self.min_freq_spin.setValue(params.get("min_freq", 0.0))
        if hasattr(self, 'max_freq_spin'):
            self.max_freq_spin.setValue(params.get("max_freq", 1000.0))
        if hasattr(self, 'timeout_spin'):
            self.timeout_spin.setValue(params.get("timeout_ms", 1000))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        config = {
            "channel": self.channel_combo.currentData(),
            "name": self.name_edit.text(),
            "type": self.type_combo.currentText(),
            "pull_up": self.pullup_check.isChecked(),
            "pull_down": self.pulldown_check.isChecked(),
            "filter_samples": self.filter_spin.value(),
            "parameters": {}
        }

        input_type = self.type_combo.currentText()
        params = config["parameters"]

        if input_type in ["Switch Active Low", "Switch Active High"]:
            params["debounce_ms"] = self.debounce_spin.value()
            params["threshold"] = self.threshold_spin.value()

        elif input_type == "Rotary Switch":
            params["positions"] = self.positions_spin.value()
            params["debounce_ms"] = self.debounce_spin.value()

        elif input_type == "Linear Analog":
            params["min_voltage"] = self.min_voltage_spin.value()
            params["max_voltage"] = self.max_voltage_spin.value()

        elif input_type == "Calibrated Analog":
            params["multiplier"] = self.multiplier_spin.value()
            params["offset"] = self.offset_spin.value()
            params["unit"] = self.unit_edit.text()

        elif input_type == "Frequency Input":
            params["min_freq"] = self.min_freq_spin.value()
            params["max_freq"] = self.max_freq_spin.value()
            params["timeout_ms"] = self.timeout_spin.value()

        return config

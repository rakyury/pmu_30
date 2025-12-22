"""
Input Channel Configuration Dialog
Configures one of 20 universal analog/digital inputs
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class InputConfigDialog(QDialog):
    """Dialog for configuring a single input channel."""

    INPUT_TYPES = [
        "switch - active high",
        "switch - active low",
        "rotary switch",
        "linear analog sensor",
        "calibrated analog sensor",
        "frequency input"
    ]

    PULLUP_OPTIONS = [
        "None",
        "10K pullup",
        "10K pulldown",
        "100K pullup",
        "100K pulldown"
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

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Brake Pressure, Throttle Position")
        basic_layout.addRow("Name: *", self.name_edit)

        # Pin selection - dropdown with available pins only
        self.pin_combo = QComboBox()
        self.pin_combo.setToolTip("Physical input pin (A1-A20)")
        self._populate_available_pins()
        basic_layout.addRow("Pin:", self.pin_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItems(self.INPUT_TYPES)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        basic_layout.addRow("Type:", self.type_combo)

        # Pullup/Pulldown as single dropdown
        self.pullup_combo = QComboBox()
        self.pullup_combo.addItems(self.PULLUP_OPTIONS)
        basic_layout.addRow("Pullup/Pulldown:", self.pullup_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Type-specific settings group
        self.type_group = QGroupBox("Type-Specific Settings")
        self.type_layout = QFormLayout()
        self.type_group.setLayout(self.type_layout)
        layout.addWidget(self.type_group)

        # Filter settings
        filter_group = QGroupBox("Filter Settings")
        filter_layout = QFormLayout()

        self.filter_spin = QSpinBox()
        self.filter_spin.setRange(1, 100)
        self.filter_spin.setValue(5)
        self.filter_spin.setToolTip("Number of samples to average (1-100)")
        filter_layout.addRow("Filter Samples:", self.filter_spin)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

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

        if input_type in ["switch - active high", "switch - active low"]:
            # Voltage thresholds with time parameters
            # "1 if voltage >"
            threshold_high_layout = QHBoxLayout()
            self.threshold_high_spin = QDoubleSpinBox()
            self.threshold_high_spin.setRange(0.0, 30.0)
            self.threshold_high_spin.setValue(2.5)
            self.threshold_high_spin.setSuffix(" V")
            self.threshold_high_spin.setDecimals(2)
            self.threshold_high_spin.setSingleStep(0.1)
            threshold_high_layout.addWidget(self.threshold_high_spin)
            threshold_high_layout.addWidget(QLabel("for"))
            self.threshold_high_time_spin = QSpinBox()
            self.threshold_high_time_spin.setRange(0, 10000)
            self.threshold_high_time_spin.setValue(50)
            self.threshold_high_time_spin.setSuffix(" ms")
            threshold_high_layout.addWidget(self.threshold_high_time_spin)
            threshold_high_layout.addStretch()
            self.type_layout.addRow("1 if voltage >:", threshold_high_layout)

            # "0 if voltage <"
            threshold_low_layout = QHBoxLayout()
            self.threshold_low_spin = QDoubleSpinBox()
            self.threshold_low_spin.setRange(0.0, 30.0)
            self.threshold_low_spin.setValue(1.5)
            self.threshold_low_spin.setSuffix(" V")
            self.threshold_low_spin.setDecimals(2)
            self.threshold_low_spin.setSingleStep(0.1)
            threshold_low_layout.addWidget(self.threshold_low_spin)
            threshold_low_layout.addWidget(QLabel("for"))
            self.threshold_low_time_spin = QSpinBox()
            self.threshold_low_time_spin.setRange(0, 10000)
            self.threshold_low_time_spin.setValue(50)
            self.threshold_low_time_spin.setSuffix(" ms")
            threshold_low_layout.addWidget(self.threshold_low_time_spin)
            threshold_low_layout.addStretch()
            self.type_layout.addRow("0 if voltage <:", threshold_low_layout)

        elif input_type == "rotary switch":
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

        elif input_type == "linear analog sensor":
            self.min_voltage_spin = QDoubleSpinBox()
            self.min_voltage_spin.setRange(0.0, 30.0)
            self.min_voltage_spin.setValue(0.0)
            self.min_voltage_spin.setSuffix(" V")
            self.min_voltage_spin.setDecimals(2)
            self.min_voltage_spin.setSingleStep(0.1)
            self.type_layout.addRow("Min Voltage:", self.min_voltage_spin)

            self.max_voltage_spin = QDoubleSpinBox()
            self.max_voltage_spin.setRange(0.0, 30.0)
            self.max_voltage_spin.setValue(5.0)
            self.max_voltage_spin.setSuffix(" V")
            self.max_voltage_spin.setDecimals(2)
            self.max_voltage_spin.setSingleStep(0.1)
            self.type_layout.addRow("Max Voltage:", self.max_voltage_spin)

        elif input_type == "calibrated analog sensor":
            # Calibration table
            calib_label = QLabel("Calibration Table:")
            calib_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            self.type_layout.addRow(calib_label)

            # Table toolbar
            table_toolbar = QHBoxLayout()
            self.calib_add_btn = QPushButton("Add Row")
            self.calib_add_btn.clicked.connect(self._add_calibration_row)
            table_toolbar.addWidget(self.calib_add_btn)

            self.calib_remove_btn = QPushButton("Remove Row")
            self.calib_remove_btn.clicked.connect(self._remove_calibration_row)
            table_toolbar.addWidget(self.calib_remove_btn)

            table_toolbar.addStretch()

            self.calib_sort_btn = QPushButton("Sort by Voltage")
            self.calib_sort_btn.clicked.connect(self._sort_calibration_table)
            table_toolbar.addWidget(self.calib_sort_btn)

            self.type_layout.addRow(table_toolbar)

            # Calibration table widget
            self.calibration_table = QTableWidget()
            self.calibration_table.setColumnCount(2)
            self.calibration_table.setHorizontalHeaderLabels(["Voltage (V)", "Value"])
            self.calibration_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.calibration_table.setMinimumHeight(150)
            self.calibration_table.setMaximumHeight(200)

            # Add default calibration points
            for _ in range(3):
                self._add_calibration_row()

            self.type_layout.addRow(self.calibration_table)

        elif input_type == "frequency input":
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

    def _add_calibration_row(self):
        """Add row to calibration table."""
        if not hasattr(self, 'calibration_table'):
            return

        row = self.calibration_table.rowCount()
        self.calibration_table.insertRow(row)

        # Create editable cells with default values
        voltage_item = QTableWidgetItem("0.0")
        value_item = QTableWidgetItem("0.0")

        self.calibration_table.setItem(row, 0, voltage_item)
        self.calibration_table.setItem(row, 1, value_item)

    def _remove_calibration_row(self):
        """Remove selected row from calibration table."""
        if not hasattr(self, 'calibration_table'):
            return

        current_row = self.calibration_table.currentRow()
        if current_row >= 0:
            self.calibration_table.removeRow(current_row)

    def _sort_calibration_table(self):
        """Sort calibration table by voltage values."""
        if not hasattr(self, 'calibration_table'):
            return

        # Collect all rows
        rows = []
        for i in range(self.calibration_table.rowCount()):
            voltage_item = self.calibration_table.item(i, 0)
            value_item = self.calibration_table.item(i, 1)
            if voltage_item and value_item:
                try:
                    voltage = float(voltage_item.text())
                    value = float(value_item.text())
                    rows.append((voltage, value))
                except ValueError:
                    continue

        # Sort by voltage
        rows.sort(key=lambda r: r[0])

        # Clear table and refill
        self.calibration_table.setRowCount(0)
        for voltage, value in rows:
            row = self.calibration_table.rowCount()
            self.calibration_table.insertRow(row)
            self.calibration_table.setItem(row, 0, QTableWidgetItem(str(voltage)))
            self.calibration_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _populate_available_pins(self):
        """Populate pin dropdown with available pins."""
        self.pin_combo.clear()

        # Get current channel if editing
        current_channel = None
        if self.input_config:
            current_channel = self.input_config.get("channel")

        # Add available pins (A1-A20)
        for ch in range(20):
            if ch not in self.used_channels or ch == current_channel:
                self.pin_combo.addItem(f"A{ch + 1}", ch)

        # If no pins available, add a placeholder
        if self.pin_combo.count() == 0:
            self.pin_combo.addItem("No pins available", -1)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))

        # Find and select the pin in combo box
        channel = config.get("channel", 0)
        index = self.pin_combo.findData(channel)
        if index >= 0:
            self.pin_combo.setCurrentIndex(index)

        input_type = config.get("type", "switch - active low")
        if input_type in self.INPUT_TYPES:
            self.type_combo.setCurrentText(input_type)

        # Load pullup/pulldown setting
        pullup_option = config.get("pullup_option", "None")
        idx = self.pullup_combo.findText(pullup_option)
        if idx >= 0:
            self.pullup_combo.setCurrentIndex(idx)

        self.filter_spin.setValue(config.get("filter_samples", 5))

        params = config.get("parameters", {})

        # Load type-specific parameters
        if hasattr(self, 'threshold_high_spin'):
            self.threshold_high_spin.setValue(params.get("threshold_high", 2.5))
            self.threshold_high_time_spin.setValue(params.get("threshold_high_time_ms", 50))
        if hasattr(self, 'threshold_low_spin'):
            self.threshold_low_spin.setValue(params.get("threshold_low", 1.5))
            self.threshold_low_time_spin.setValue(params.get("threshold_low_time_ms", 50))
        if hasattr(self, 'debounce_spin'):
            self.debounce_spin.setValue(params.get("debounce_ms", 50))
        if hasattr(self, 'positions_spin'):
            self.positions_spin.setValue(params.get("positions", 4))
        if hasattr(self, 'min_voltage_spin'):
            self.min_voltage_spin.setValue(params.get("min_voltage", 0.0))
        if hasattr(self, 'max_voltage_spin'):
            self.max_voltage_spin.setValue(params.get("max_voltage", 5.0))
        if hasattr(self, 'calibration_table'):
            # Load calibration table data
            calibration_data = params.get("calibration_table", [])
            if calibration_data:
                self.calibration_table.setRowCount(0)
                for voltage, value in calibration_data:
                    row = self.calibration_table.rowCount()
                    self.calibration_table.insertRow(row)
                    self.calibration_table.setItem(row, 0, QTableWidgetItem(str(voltage)))
                    self.calibration_table.setItem(row, 1, QTableWidgetItem(str(value)))
        if hasattr(self, 'min_freq_spin'):
            self.min_freq_spin.setValue(params.get("min_freq", 0.0))
        if hasattr(self, 'max_freq_spin'):
            self.max_freq_spin.setValue(params.get("max_freq", 1000.0))
        if hasattr(self, 'timeout_spin'):
            self.timeout_spin.setValue(params.get("timeout_ms", 1000))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        config = {
            "channel": self.pin_combo.currentData(),
            "name": self.name_edit.text(),
            "type": self.type_combo.currentText(),
            "pullup_option": self.pullup_combo.currentText(),
            "filter_samples": self.filter_spin.value(),
            "parameters": {}
        }

        input_type = self.type_combo.currentText()
        params = config["parameters"]

        if input_type in ["switch - active high", "switch - active low"]:
            params["threshold_high"] = self.threshold_high_spin.value()
            params["threshold_high_time_ms"] = self.threshold_high_time_spin.value()
            params["threshold_low"] = self.threshold_low_spin.value()
            params["threshold_low_time_ms"] = self.threshold_low_time_spin.value()

        elif input_type == "rotary switch":
            params["positions"] = self.positions_spin.value()
            params["debounce_ms"] = self.debounce_spin.value()

        elif input_type == "linear analog sensor":
            params["min_voltage"] = self.min_voltage_spin.value()
            params["max_voltage"] = self.max_voltage_spin.value()

        elif input_type == "calibrated analog sensor":
            # Collect calibration table data
            calibration_data = []
            if hasattr(self, 'calibration_table'):
                for i in range(self.calibration_table.rowCount()):
                    voltage_item = self.calibration_table.item(i, 0)
                    value_item = self.calibration_table.item(i, 1)
                    if voltage_item and value_item:
                        try:
                            voltage = float(voltage_item.text())
                            value = float(value_item.text())
                            calibration_data.append((voltage, value))
                        except ValueError:
                            continue
            params["calibration_table"] = calibration_data

        elif input_type == "frequency input":
            params["min_freq"] = self.min_freq_spin.value()
            params["max_freq"] = self.max_freq_spin.value()
            params["timeout_ms"] = self.timeout_spin.value()

        return config

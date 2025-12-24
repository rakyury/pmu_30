"""
Analog Input Configuration Dialog
Supports: switch (active low/high), rotary switch, linear, calibrated
"""

from PyQt6.QtWidgets import (
    QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QLabel, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QVBoxLayout
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, AnalogInputSubtype


class AnalogInputDialog(BaseChannelDialog):
    """Dialog for configuring analog input channels"""

    # Subtype display names
    SUBTYPE_NAMES = {
        AnalogInputSubtype.SWITCH_ACTIVE_LOW: "switch - active low",
        AnalogInputSubtype.SWITCH_ACTIVE_HIGH: "switch - active high",
        AnalogInputSubtype.ROTARY_SWITCH: "rotary switch",
        AnalogInputSubtype.LINEAR: "linear analog sensor",
        AnalogInputSubtype.CALIBRATED: "calibrated analog sensor",
    }

    # Pullup/Pulldown options
    PULLUP_OPTIONS = [
        ("default: 1M pulldown", "1m_down"),
        ("None", "none"),
        ("10K pullup", "10k_up"),
        ("10K pulldown", "10k_down"),
        ("100K pullup", "100k_up"),
        ("100K pulldown", "100k_down"),
    ]

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 used_pins: Optional[List[int]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        self.used_pins = used_pins or []
        # Get current channel if editing (to allow keeping same pin)
        self.current_channel = config.get('channel') if config else None
        super().__init__(parent, config, available_channels, ChannelType.ANALOG_INPUT, existing_channels)

        self._create_settings_group()
        self._create_switch_group()
        self._create_rotary_group()
        self._create_linear_group()
        self._create_calibration_group()

        # Connect type change handler
        self.subtype_combo.currentIndexChanged.connect(self._on_subtype_changed)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        # Update visibility based on current subtype
        self._on_subtype_changed()

    def _create_settings_group(self):
        """Create main settings group"""
        settings_group = QGroupBox("Input Settings")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Pin and Type in same row
        layout.addWidget(QLabel("Pin:"), row, 0)
        self.pin_combo = QComboBox()
        for i in range(20):
            # Only show pins that are not in use (or the current pin if editing)
            if i not in self.used_pins or i == self.current_channel:
                self.pin_combo.addItem(f"A{i + 1}", i)
        layout.addWidget(self.pin_combo, row, 1)

        layout.addWidget(QLabel("Type:"), row, 2)
        self.subtype_combo = QComboBox()
        for subtype in AnalogInputSubtype:
            self.subtype_combo.addItem(self.SUBTYPE_NAMES[subtype], subtype.value)
        layout.addWidget(self.subtype_combo, row, 3)
        row += 1

        # Pullup/Pulldown and Decimal places in same row
        layout.addWidget(QLabel("Pullup/Pulldown:"), row, 0)
        self.pullup_combo = QComboBox()
        for name, value in self.PULLUP_OPTIONS:
            self.pullup_combo.addItem(name, value)
        layout.addWidget(self.pullup_combo, row, 1)

        self.decimal_label = QLabel("Decimal places:")
        layout.addWidget(self.decimal_label, row, 2)
        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(0, 6)
        self.decimal_spin.setValue(0)
        layout.addWidget(self.decimal_spin, row, 3)

        settings_group.setLayout(layout)
        self.content_layout.addWidget(settings_group)

    def _create_switch_group(self):
        """Create switch mode settings group (active low/high)"""
        self.switch_group = QGroupBox("Switch Thresholds")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # 1 if voltage > threshold for time
        layout.addWidget(QLabel("1 if voltage >:"), row, 0)
        self.threshold_high_spin = QDoubleSpinBox()
        self.threshold_high_spin.setRange(0.0, 30.0)
        self.threshold_high_spin.setDecimals(2)
        self.threshold_high_spin.setValue(2.5)
        self.threshold_high_spin.setSuffix(" V")
        layout.addWidget(self.threshold_high_spin, row, 1)

        layout.addWidget(QLabel("for:"), row, 2)
        self.threshold_high_time_spin = QSpinBox()
        self.threshold_high_time_spin.setRange(0, 10000)
        self.threshold_high_time_spin.setValue(50)
        self.threshold_high_time_spin.setSuffix(" ms")
        layout.addWidget(self.threshold_high_time_spin, row, 3)
        row += 1

        # 0 if voltage < threshold for time
        layout.addWidget(QLabel("0 if voltage <:"), row, 0)
        self.threshold_low_spin = QDoubleSpinBox()
        self.threshold_low_spin.setRange(0.0, 30.0)
        self.threshold_low_spin.setDecimals(2)
        self.threshold_low_spin.setValue(1.5)
        self.threshold_low_spin.setSuffix(" V")
        layout.addWidget(self.threshold_low_spin, row, 1)

        layout.addWidget(QLabel("for:"), row, 2)
        self.threshold_low_time_spin = QSpinBox()
        self.threshold_low_time_spin.setRange(0, 10000)
        self.threshold_low_time_spin.setValue(50)
        self.threshold_low_time_spin.setSuffix(" ms")
        layout.addWidget(self.threshold_low_time_spin, row, 3)

        self.switch_group.setLayout(layout)
        self.content_layout.addWidget(self.switch_group)

    def _create_rotary_group(self):
        """Create rotary switch settings group"""
        self.rotary_group = QGroupBox("Rotary Switch Settings")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        layout.addWidget(QLabel("Positions:"), 0, 0)
        self.positions_spin = QSpinBox()
        self.positions_spin.setRange(2, 12)
        self.positions_spin.setValue(4)
        layout.addWidget(self.positions_spin, 0, 1)

        layout.addWidget(QLabel("Debounce:"), 0, 2)
        self.debounce_spin = QSpinBox()
        self.debounce_spin.setRange(0, 1000)
        self.debounce_spin.setValue(50)
        self.debounce_spin.setSuffix(" ms")
        layout.addWidget(self.debounce_spin, 0, 3)

        self.rotary_group.setLayout(layout)
        self.content_layout.addWidget(self.rotary_group)

    def _create_linear_group(self):
        """Create linear mode settings group"""
        self.linear_group = QGroupBox("Value Mapping")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Min value row
        layout.addWidget(QLabel("Min value:"), row, 0)
        self.min_value_spin = QDoubleSpinBox()
        self.min_value_spin.setRange(-1000000, 1000000)
        self.min_value_spin.setDecimals(2)
        self.min_value_spin.setValue(0.0)
        layout.addWidget(self.min_value_spin, row, 1)

        layout.addWidget(QLabel("for voltage [V]:"), row, 2)
        self.min_voltage_spin = QDoubleSpinBox()
        self.min_voltage_spin.setRange(0.0, 30.0)
        self.min_voltage_spin.setDecimals(2)
        self.min_voltage_spin.setValue(0.0)
        layout.addWidget(self.min_voltage_spin, row, 3)
        row += 1

        # Max value row
        layout.addWidget(QLabel("Max value:"), row, 0)
        self.max_value_spin = QDoubleSpinBox()
        self.max_value_spin.setRange(-1000000, 1000000)
        self.max_value_spin.setDecimals(2)
        self.max_value_spin.setValue(100.0)
        layout.addWidget(self.max_value_spin, row, 1)

        layout.addWidget(QLabel("for voltage [V]:"), row, 2)
        self.max_voltage_spin = QDoubleSpinBox()
        self.max_voltage_spin.setRange(0.0, 30.0)
        self.max_voltage_spin.setDecimals(2)
        self.max_voltage_spin.setValue(5.0)
        layout.addWidget(self.max_voltage_spin, row, 3)

        self.linear_group.setLayout(layout)
        self.content_layout.addWidget(self.linear_group)

    def _create_calibration_group(self):
        """Create calibration table group"""
        self.calib_group = QGroupBox("Calibration Table")
        layout = QVBoxLayout()

        # Table toolbar
        toolbar = QHBoxLayout()

        self.add_row_btn = QPushButton("Add Row")
        self.add_row_btn.clicked.connect(self._add_calibration_row)
        toolbar.addWidget(self.add_row_btn)

        self.remove_row_btn = QPushButton("Remove Row")
        self.remove_row_btn.clicked.connect(self._remove_calibration_row)
        toolbar.addWidget(self.remove_row_btn)

        toolbar.addStretch()

        self.sort_btn = QPushButton("Sort by Voltage")
        self.sort_btn.clicked.connect(self._sort_calibration_table)
        toolbar.addWidget(self.sort_btn)

        layout.addLayout(toolbar)

        # Calibration table
        self.calib_table = QTableWidget()
        self.calib_table.setColumnCount(2)
        self.calib_table.setHorizontalHeaderLabels(["Voltage [V]", "Value"])
        self.calib_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.calib_table.setMinimumHeight(150)
        layout.addWidget(self.calib_table)

        # Add default rows
        for _ in range(3):
            self._add_calibration_row()

        self.calib_group.setLayout(layout)
        self.content_layout.addWidget(self.calib_group)

    def _on_subtype_changed(self):
        """Handle subtype selection change"""
        subtype_value = self.subtype_combo.currentData()

        is_switch = subtype_value in [
            AnalogInputSubtype.SWITCH_ACTIVE_LOW.value,
            AnalogInputSubtype.SWITCH_ACTIVE_HIGH.value
        ]
        is_rotary = subtype_value == AnalogInputSubtype.ROTARY_SWITCH.value
        is_linear = subtype_value == AnalogInputSubtype.LINEAR.value
        is_calibrated = subtype_value == AnalogInputSubtype.CALIBRATED.value

        # Show/hide groups based on type
        self.switch_group.setVisible(is_switch)
        self.rotary_group.setVisible(is_rotary)
        self.linear_group.setVisible(is_linear)
        self.calib_group.setVisible(is_calibrated)

        # Decimal places only for linear/calibrated
        self.decimal_label.setVisible(is_linear or is_calibrated)
        self.decimal_spin.setVisible(is_linear or is_calibrated)

    def _add_calibration_row(self):
        """Add row to calibration table"""
        row = self.calib_table.rowCount()
        self.calib_table.insertRow(row)

        voltage_item = QTableWidgetItem("0.0")
        voltage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        value_item = QTableWidgetItem("0.0")
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.calib_table.setItem(row, 0, voltage_item)
        self.calib_table.setItem(row, 1, value_item)

    def _remove_calibration_row(self):
        """Remove selected row from calibration table"""
        current_row = self.calib_table.currentRow()
        if current_row >= 0:
            self.calib_table.removeRow(current_row)

    def _sort_calibration_table(self):
        """Sort calibration table by voltage values"""
        rows = []
        for i in range(self.calib_table.rowCount()):
            voltage_item = self.calib_table.item(i, 0)
            value_item = self.calib_table.item(i, 1)
            if voltage_item and value_item:
                try:
                    voltage = float(voltage_item.text())
                    value = float(value_item.text())
                    rows.append((voltage, value))
                except ValueError:
                    continue

        rows.sort(key=lambda r: r[0])

        self.calib_table.setRowCount(0)
        for voltage, value in rows:
            row = self.calib_table.rowCount()
            self.calib_table.insertRow(row)

            voltage_item = QTableWidgetItem(str(voltage))
            voltage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            value_item = QTableWidgetItem(str(value))
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.calib_table.setItem(row, 0, voltage_item)
            self.calib_table.setItem(row, 1, value_item)

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        # Subtype
        subtype = config.get("subtype", "linear")
        for i in range(self.subtype_combo.count()):
            if self.subtype_combo.itemData(i) == subtype:
                self.subtype_combo.setCurrentIndex(i)
                break

        # Pin
        pin = config.get("input_pin", 0)
        if 0 <= pin < self.pin_combo.count():
            self.pin_combo.setCurrentIndex(pin)

        # Pullup option
        pullup = config.get("pullup_option", "1m_down")
        for i in range(self.pullup_combo.count()):
            if self.pullup_combo.itemData(i) == pullup:
                self.pullup_combo.setCurrentIndex(i)
                break

        # Decimal places
        self.decimal_spin.setValue(config.get("decimal_places", 0))

        # Switch thresholds
        self.threshold_high_spin.setValue(config.get("threshold_high", 2.5))
        self.threshold_high_time_spin.setValue(config.get("threshold_high_time_ms", 50))
        self.threshold_low_spin.setValue(config.get("threshold_low", 1.5))
        self.threshold_low_time_spin.setValue(config.get("threshold_low_time_ms", 50))

        # Rotary switch
        self.positions_spin.setValue(config.get("positions", 4))
        self.debounce_spin.setValue(config.get("debounce_ms", 50))

        # Linear mode values
        self.min_value_spin.setValue(config.get("min_value", 0.0))
        self.min_voltage_spin.setValue(config.get("min_voltage", 0.0))
        self.max_value_spin.setValue(config.get("max_value", 100.0))
        self.max_voltage_spin.setValue(config.get("max_voltage", 5.0))

        # Calibration points
        calibration_points = config.get("calibration_points", [])
        if calibration_points:
            self.calib_table.setRowCount(0)
            for point in calibration_points:
                row = self.calib_table.rowCount()
                self.calib_table.insertRow(row)

                voltage_item = QTableWidgetItem(str(point.get("voltage", 0.0)))
                voltage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                value_item = QTableWidgetItem(str(point.get("value", 0.0)))
                value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.calib_table.setItem(row, 0, voltage_item)
                self.calib_table.setItem(row, 1, value_item)

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []

        subtype_value = self.subtype_combo.currentData()

        if subtype_value == AnalogInputSubtype.CALIBRATED.value:
            if self.calib_table.rowCount() < 2:
                errors.append("Calibration table must have at least 2 points")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()

        subtype_value = self.subtype_combo.currentData()

        # Collect calibration points
        calibration_points = []
        for i in range(self.calib_table.rowCount()):
            voltage_item = self.calib_table.item(i, 0)
            value_item = self.calib_table.item(i, 1)
            if voltage_item and value_item:
                try:
                    voltage = float(voltage_item.text())
                    value = float(value_item.text())
                    calibration_points.append({"voltage": voltage, "value": value})
                except ValueError:
                    continue

        config.update({
            "subtype": subtype_value,
            "input_pin": self.pin_combo.currentData(),
            "pullup_option": self.pullup_combo.currentData(),
            "decimal_places": self.decimal_spin.value(),
            "threshold_high": self.threshold_high_spin.value(),
            "threshold_high_time_ms": self.threshold_high_time_spin.value(),
            "threshold_low": self.threshold_low_spin.value(),
            "threshold_low_time_ms": self.threshold_low_time_spin.value(),
            "positions": self.positions_spin.value(),
            "debounce_ms": self.debounce_spin.value(),
            "min_voltage": self.min_voltage_spin.value(),
            "max_voltage": self.max_voltage_spin.value(),
            "min_value": self.min_value_spin.value(),
            "max_value": self.max_value_spin.value(),
            "calibration_points": calibration_points
        })

        return config

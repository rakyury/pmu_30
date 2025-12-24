"""
Digital Input Configuration Dialog
Supports multiple subtypes: Switch, Frequency, RPM, Flex Fuel, Beacon, PULS oil sensor
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel, QGridLayout
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, DigitalInputSubtype, EdgeType


class DigitalInputDialog(BaseChannelDialog):
    """Dialog for configuring digital input channels"""

    # Subtype display names
    SUBTYPE_NAMES = {
        DigitalInputSubtype.SWITCH_ACTIVE_LOW: "Switch - active low",
        DigitalInputSubtype.SWITCH_ACTIVE_HIGH: "Switch - active high",
        DigitalInputSubtype.FREQUENCY: "Frequency",
        DigitalInputSubtype.RPM: "RPM",
        DigitalInputSubtype.FLEX_FUEL: "Flex Fuel",
        DigitalInputSubtype.BEACON: "Beacon",
        DigitalInputSubtype.PULS_OIL_SENSOR: "PULS oil sensor",
    }

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 used_pins: Optional[List[int]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        self.used_pins = used_pins or []
        # Get current pin if editing (to allow keeping same pin)
        self.current_pin = config.get('input_pin') if config else None
        super().__init__(parent, config, available_channels, ChannelType.DIGITAL_INPUT, existing_channels)

        self._create_type_group()
        self._create_hardware_group()
        self._create_frequency_group()
        self._create_rpm_group()

        # Connect subtype change handler
        self.subtype_combo.currentIndexChanged.connect(self._on_subtype_changed)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        # Update visibility based on current subtype
        self._on_subtype_changed()

    def _create_type_group(self):
        """Create type selection group with two-column layout"""
        type_group = QGroupBox("Input Type")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Subtype and Input pin in same row
        layout.addWidget(QLabel("Type:"), 0, 0)
        self.subtype_combo = QComboBox()
        for subtype in DigitalInputSubtype:
            self.subtype_combo.addItem(self.SUBTYPE_NAMES[subtype], subtype.value)
        layout.addWidget(self.subtype_combo, 0, 1)

        layout.addWidget(QLabel("Input Pin:"), 0, 2)
        self.input_pin_combo = QComboBox()
        for i in range(8):
            # Only show pins that are not in use (or the current pin if editing)
            if i not in self.used_pins or i == self.current_pin:
                self.input_pin_combo.addItem(f"D{i + 1}", i)
        layout.addWidget(self.input_pin_combo, 0, 3)

        type_group.setLayout(layout)
        self.content_layout.addWidget(type_group)

    def _create_hardware_group(self):
        """Create hardware settings group with two-column layout"""
        self.hw_group = QGroupBox("Hardware Settings")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Pullup checkbox (full row)
        self.pullup_check = QCheckBox("Enable internal pull-up resistor")
        layout.addWidget(self.pullup_check, row, 0, 1, 4)
        row += 1

        # Threshold and Debounce in same row
        layout.addWidget(QLabel("Threshold:"), row, 0)
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 30.0)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(2.51)
        self.threshold_spin.setSuffix(" V")
        self.threshold_spin.setToolTip("Voltage threshold for digital state detection")
        layout.addWidget(self.threshold_spin, row, 1)

        self.debounce_label = QLabel("Debounce:")
        layout.addWidget(self.debounce_label, row, 2)
        self.debounce_spin = QSpinBox()
        self.debounce_spin.setRange(0, 10000)
        self.debounce_spin.setValue(50)
        self.debounce_spin.setSuffix(" ms")
        self.debounce_spin.setToolTip("Debounce time to filter contact bounce")
        layout.addWidget(self.debounce_spin, row, 3)

        self.hw_group.setLayout(layout)
        self.content_layout.addWidget(self.hw_group)

    def _create_frequency_group(self):
        """Create frequency-specific settings group with two-column layout"""
        self.freq_group = QGroupBox("Frequency Settings")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Trigger edge and Timeout in same row
        layout.addWidget(QLabel("Trigger Edge:"), row, 0)
        self.trigger_edge_combo = self._create_edge_combo(include_both=True)
        layout.addWidget(self.trigger_edge_combo, row, 1)

        layout.addWidget(QLabel("Timeout:"), row, 2)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 60000)
        self.timeout_spin.setValue(1000)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setToolTip("Timeout before output goes to zero")
        layout.addWidget(self.timeout_spin, row, 3)
        row += 1

        # Multiplier and Divider in same row
        layout.addWidget(QLabel("Multiplier:"), row, 0)
        self.multiplier_spin = QDoubleSpinBox()
        self.multiplier_spin.setRange(0.001, 1000.0)
        self.multiplier_spin.setDecimals(3)
        self.multiplier_spin.setValue(1.0)
        self.multiplier_spin.setToolTip("Output = Input * Multiplier / Divider")
        layout.addWidget(self.multiplier_spin, row, 1)

        layout.addWidget(QLabel("Divider:"), row, 2)
        self.divider_spin = QDoubleSpinBox()
        self.divider_spin.setRange(0.001, 1000.0)
        self.divider_spin.setDecimals(3)
        self.divider_spin.setValue(1.0)
        self.divider_spin.setToolTip("Output = Input * Multiplier / Divider")
        layout.addWidget(self.divider_spin, row, 3)

        self.freq_group.setLayout(layout)
        self.content_layout.addWidget(self.freq_group)

    def _create_rpm_group(self):
        """Create RPM-specific settings group"""
        self.rpm_group = QGroupBox("RPM Settings")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Number of teeth
        layout.addWidget(QLabel("Number of Teeth:"), 0, 0)
        self.teeth_spin = QSpinBox()
        self.teeth_spin.setRange(1, 200)
        self.teeth_spin.setValue(58)
        self.teeth_spin.setToolTip("Number of teeth on the trigger wheel")
        layout.addWidget(self.teeth_spin, 0, 1)

        # Info label
        info_label = QLabel("RPM = (Frequency * 60 * Multiplier) / (Teeth * Divider)")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label, 1, 0, 1, 4)

        self.rpm_group.setLayout(layout)
        self.content_layout.addWidget(self.rpm_group)

    def _on_subtype_changed(self):
        """Handle subtype selection change - show/hide relevant groups"""
        subtype_value = self.subtype_combo.currentData()

        is_switch = subtype_value in [
            DigitalInputSubtype.SWITCH_ACTIVE_LOW.value,
            DigitalInputSubtype.SWITCH_ACTIVE_HIGH.value
        ]
        is_frequency = subtype_value == DigitalInputSubtype.FREQUENCY.value
        is_rpm = subtype_value == DigitalInputSubtype.RPM.value
        is_flex_fuel = subtype_value == DigitalInputSubtype.FLEX_FUEL.value
        is_beacon = subtype_value == DigitalInputSubtype.BEACON.value
        is_puls = subtype_value == DigitalInputSubtype.PULS_OIL_SENSOR.value

        # Debounce only for switch types
        self.debounce_spin.setVisible(is_switch)
        self.debounce_label.setVisible(is_switch)

        # Frequency group for frequency/RPM types
        self.freq_group.setVisible(is_frequency or is_rpm)

        # RPM group only for RPM type
        self.rpm_group.setVisible(is_rpm)

        # Flex Fuel, Beacon, PULS - only basic settings
        # (threshold is enough for these types)

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        # Subtype
        subtype = config.get("subtype", "switch_active_low")
        for i in range(self.subtype_combo.count()):
            if self.subtype_combo.itemData(i) == subtype:
                self.subtype_combo.setCurrentIndex(i)
                break

        # Input pin - find by data value, not index
        pin = config.get("input_pin", 0)
        index = self.input_pin_combo.findData(pin)
        if index >= 0:
            self.input_pin_combo.setCurrentIndex(index)

        # Hardware settings
        self.pullup_check.setChecked(config.get("enable_pullup", False))
        self.threshold_spin.setValue(config.get("threshold_voltage", 2.51))
        self.debounce_spin.setValue(config.get("debounce_ms", 50))

        # Frequency settings
        self._set_edge_combo_value(
            self.trigger_edge_combo,
            config.get("trigger_edge", "rising")
        )
        self.multiplier_spin.setValue(config.get("multiplier", 1.0))
        self.divider_spin.setValue(config.get("divider", 1.0))
        self.timeout_spin.setValue(config.get("timeout_ms", 1000))

        # RPM settings
        self.teeth_spin.setValue(config.get("number_of_teeth", 58))

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []

        subtype_value = self.subtype_combo.currentData()

        if subtype_value == DigitalInputSubtype.RPM.value:
            if self.teeth_spin.value() < 1:
                errors.append("Number of teeth must be at least 1")

        if self.divider_spin.value() == 0:
            errors.append("Divider cannot be zero")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()

        subtype_value = self.subtype_combo.currentData()

        config.update({
            "subtype": subtype_value,
            "input_pin": self.input_pin_combo.currentData(),
            "enable_pullup": self.pullup_check.isChecked(),
            "threshold_voltage": self.threshold_spin.value(),
            "debounce_ms": self.debounce_spin.value(),
            "trigger_edge": self._get_edge_combo_value(self.trigger_edge_combo),
            "multiplier": self.multiplier_spin.value(),
            "divider": self.divider_spin.value(),
            "timeout_ms": self.timeout_spin.value(),
            "number_of_teeth": self.teeth_spin.value()
        })

        return config

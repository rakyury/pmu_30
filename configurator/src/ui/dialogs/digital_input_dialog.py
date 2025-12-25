"""
Digital Input Configuration Dialog
Supports multiple subtypes: Switch, Frequency, RPM, Flex Fuel, Beacon, PULS oil sensor
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel, QGridLayout, QWidget, QVBoxLayout, QHBoxLayout,
    QProgressBar, QFrame
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, DigitalInputSubtype, EdgeType, ButtonMode


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

    # Button mode display names (ECUMaster compatible)
    BUTTON_MODE_NAMES = {
        ButtonMode.DIRECT: "Direct (passthrough)",
        ButtonMode.MOMENTARY: "Momentary (output while pressed)",
        ButtonMode.TOGGLE: "Toggle (press to toggle)",
        ButtonMode.LATCHING: "Latching (stays on until reset)",
        ButtonMode.LONG_PRESS: "Long Press (separate short/long actions)",
        ButtonMode.DOUBLE_CLICK: "Double Click (detect double taps)",
        ButtonMode.PRESS_AND_HOLD: "Press and Hold (progressive action)",
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

        # Increase dialog size to fit all content without scrollbar
        self.setMinimumHeight(480)
        self.resize(600, 500)

        self._create_type_group()
        self._create_hardware_group()
        self._create_button_function_group()
        self._create_frequency_group()
        self._create_rpm_group()

        # Connect subtype change handler
        self.subtype_combo.currentIndexChanged.connect(self._on_subtype_changed)
        self.button_mode_combo.currentIndexChanged.connect(self._on_button_mode_changed)

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
            # Skip KEYPAD_BUTTON - it's a virtual button from CAN keypad, not editable here
            if subtype in self.SUBTYPE_NAMES:
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

    def _create_button_function_group(self):
        """Create button function settings group (ECUMaster compatible)"""
        self.button_group = QGroupBox("Button Function")
        layout = QVBoxLayout()

        # Mode selector row
        mode_layout = QGridLayout()
        mode_layout.setColumnStretch(1, 1)
        mode_layout.setColumnStretch(3, 1)

        mode_layout.addWidget(QLabel("Button Mode:"), 0, 0)
        self.button_mode_combo = QComboBox()
        for mode in ButtonMode:
            self.button_mode_combo.addItem(self.BUTTON_MODE_NAMES[mode], mode.value)
        self.button_mode_combo.setToolTip(
            "Select how the button input behaves:\n"
            "• Direct: Raw input passthrough\n"
            "• Momentary: Output only while pressed\n"
            "• Toggle: Press to toggle on/off\n"
            "• Latching: Stays on until reset channel activates\n"
            "• Long Press: Different action for short/long presses\n"
            "• Double Click: Detect single vs double taps\n"
            "• Press and Hold: Progressive action with timer"
        )
        mode_layout.addWidget(self.button_mode_combo, 0, 1)

        # Invert checkbox
        self.invert_check = QCheckBox("Invert input")
        self.invert_check.setToolTip("Invert the logical state of the input")
        mode_layout.addWidget(self.invert_check, 0, 2, 1, 2)

        layout.addLayout(mode_layout)

        # Container for mode-specific settings
        self.button_settings_container = QWidget()
        settings_layout = QVBoxLayout(self.button_settings_container)
        settings_layout.setContentsMargins(0, 8, 0, 0)

        # --- Long Press Settings ---
        self.long_press_widget = QWidget()
        lp_layout = QGridLayout(self.long_press_widget)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.setColumnStretch(1, 1)
        lp_layout.setColumnStretch(3, 1)

        lp_layout.addWidget(QLabel("Long Press Time:"), 0, 0)
        self.long_press_spin = QSpinBox()
        self.long_press_spin.setRange(100, 5000)
        self.long_press_spin.setValue(500)
        self.long_press_spin.setSuffix(" ms")
        self.long_press_spin.setToolTip("Time to hold for long press detection")
        lp_layout.addWidget(self.long_press_spin, 0, 1)

        lp_layout.addWidget(QLabel("Long Press Output:"), 0, 2)
        self.long_press_output_widget, self.long_press_output_edit = self._create_channel_selector("long_press_output")
        lp_layout.addWidget(self.long_press_output_widget, 0, 3)

        # Progress bar visualization for long press
        lp_progress_layout = QHBoxLayout()
        lp_progress_layout.addWidget(QLabel("Short"))
        self.long_press_progress = QProgressBar()
        self.long_press_progress.setRange(0, 100)
        self.long_press_progress.setValue(50)
        self.long_press_progress.setFormat("")
        self.long_press_progress.setFixedHeight(12)
        self.long_press_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background: #333;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:0.5 #8b5cf6, stop:1 #ec4899);
                border-radius: 2px;
            }
        """)
        lp_progress_layout.addWidget(self.long_press_progress, 1)
        lp_progress_layout.addWidget(QLabel("Long"))
        lp_layout.addLayout(lp_progress_layout, 1, 0, 1, 4)

        settings_layout.addWidget(self.long_press_widget)

        # --- Double Click Settings ---
        self.double_click_widget = QWidget()
        dc_layout = QGridLayout(self.double_click_widget)
        dc_layout.setContentsMargins(0, 0, 0, 0)
        dc_layout.setColumnStretch(1, 1)
        dc_layout.setColumnStretch(3, 1)

        dc_layout.addWidget(QLabel("Click Window:"), 0, 0)
        self.double_click_spin = QSpinBox()
        self.double_click_spin.setRange(50, 1000)
        self.double_click_spin.setValue(300)
        self.double_click_spin.setSuffix(" ms")
        self.double_click_spin.setToolTip("Time window to detect double click")
        dc_layout.addWidget(self.double_click_spin, 0, 1)

        dc_layout.addWidget(QLabel("Double Click Output:"), 0, 2)
        self.double_click_output_widget, self.double_click_output_edit = self._create_channel_selector("double_click_output")
        dc_layout.addWidget(self.double_click_output_widget, 0, 3)

        settings_layout.addWidget(self.double_click_widget)

        # --- Press and Hold Settings ---
        self.press_hold_widget = QWidget()
        ph_layout = QGridLayout(self.press_hold_widget)
        ph_layout.setContentsMargins(0, 0, 0, 0)
        ph_layout.setColumnStretch(1, 1)
        ph_layout.setColumnStretch(3, 1)

        ph_layout.addWidget(QLabel("Hold Start Time:"), 0, 0)
        self.hold_start_spin = QSpinBox()
        self.hold_start_spin.setRange(100, 10000)
        self.hold_start_spin.setValue(500)
        self.hold_start_spin.setSuffix(" ms")
        self.hold_start_spin.setToolTip("Time to start progressive action")
        self.hold_start_spin.valueChanged.connect(self._update_hold_progress)
        ph_layout.addWidget(self.hold_start_spin, 0, 1)

        ph_layout.addWidget(QLabel("Hold Full Time:"), 0, 2)
        self.hold_full_spin = QSpinBox()
        self.hold_full_spin.setRange(500, 30000)
        self.hold_full_spin.setValue(2000)
        self.hold_full_spin.setSuffix(" ms")
        self.hold_full_spin.setToolTip("Time to reach full action")
        self.hold_full_spin.valueChanged.connect(self._update_hold_progress)
        ph_layout.addWidget(self.hold_full_spin, 0, 3)

        # Progress bar visualization for press and hold
        ph_progress_layout = QHBoxLayout()
        ph_progress_layout.addWidget(QLabel("0%"))
        self.hold_progress = QProgressBar()
        self.hold_progress.setRange(0, 100)
        self.hold_progress.setFormat("")
        self.hold_progress.setFixedHeight(16)
        self.hold_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                background: #333;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #22c55e, stop:0.5 #eab308, stop:1 #ef4444);
                border-radius: 3px;
            }
        """)
        ph_progress_layout.addWidget(self.hold_progress, 1)
        ph_progress_layout.addWidget(QLabel("100%"))
        ph_layout.addLayout(ph_progress_layout, 1, 0, 1, 4)

        # Hold time markers
        marker_layout = QHBoxLayout()
        self.hold_start_marker = QLabel("▲ Start")
        self.hold_start_marker.setStyleSheet("color: #22c55e; font-size: 10px;")
        self.hold_full_marker = QLabel("▲ Full")
        self.hold_full_marker.setStyleSheet("color: #ef4444; font-size: 10px;")
        marker_layout.addWidget(self.hold_start_marker)
        marker_layout.addStretch()
        marker_layout.addWidget(self.hold_full_marker)
        ph_layout.addLayout(marker_layout, 2, 0, 1, 4)

        settings_layout.addWidget(self.press_hold_widget)

        # --- Latching/Toggle Settings ---
        self.reset_widget = QWidget()
        reset_layout = QGridLayout(self.reset_widget)
        reset_layout.setContentsMargins(0, 0, 0, 0)
        reset_layout.setColumnStretch(1, 2)

        reset_layout.addWidget(QLabel("Reset Channel:"), 0, 0)
        self.reset_channel_widget, self.reset_channel_edit = self._create_channel_selector("reset_channel")
        self.reset_channel_widget.setToolTip(
            "Channel that resets the latch/toggle state when activated"
        )
        reset_layout.addWidget(self.reset_channel_widget, 0, 1)

        settings_layout.addWidget(self.reset_widget)

        layout.addWidget(self.button_settings_container)
        self.button_group.setLayout(layout)
        self.content_layout.addWidget(self.button_group)

        # Initialize progress bar
        self._update_hold_progress()

    def _update_hold_progress(self):
        """Update the hold progress bar visualization"""
        start = self.hold_start_spin.value()
        full = self.hold_full_spin.value()
        if full > 0:
            progress = int((start / full) * 100)
            self.hold_progress.setValue(progress)

    def _on_button_mode_changed(self):
        """Handle button mode change - show/hide relevant settings"""
        mode_value = self.button_mode_combo.currentData()

        # Hide all mode-specific widgets first
        self.long_press_widget.setVisible(False)
        self.double_click_widget.setVisible(False)
        self.press_hold_widget.setVisible(False)
        self.reset_widget.setVisible(False)

        # Show relevant widget based on mode
        if mode_value == ButtonMode.LONG_PRESS.value:
            self.long_press_widget.setVisible(True)
        elif mode_value == ButtonMode.DOUBLE_CLICK.value:
            self.double_click_widget.setVisible(True)
        elif mode_value == ButtonMode.PRESS_AND_HOLD.value:
            self.press_hold_widget.setVisible(True)
        elif mode_value in [ButtonMode.LATCHING.value, ButtonMode.TOGGLE.value]:
            self.reset_widget.setVisible(True)

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
        info_label.setStyleSheet("color: #b0b0b0; font-style: italic;")
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

        # Button function group only for switch types
        self.button_group.setVisible(is_switch)
        if is_switch:
            self._on_button_mode_changed()

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

        # Button function settings
        self.invert_check.setChecked(config.get("invert", False))
        button_mode = config.get("button_mode", "direct")
        for i in range(self.button_mode_combo.count()):
            if self.button_mode_combo.itemData(i) == button_mode:
                self.button_mode_combo.setCurrentIndex(i)
                break

        # Long press settings
        self.long_press_spin.setValue(config.get("long_press_ms", 500))
        if hasattr(self, 'long_press_output_edit'):
            self._set_channel_edit_value(self.long_press_output_edit, config.get("long_press_output"))

        # Double click settings
        self.double_click_spin.setValue(config.get("double_click_ms", 300))
        if hasattr(self, 'double_click_output_edit'):
            self._set_channel_edit_value(self.double_click_output_edit, config.get("double_click_output"))

        # Press and hold settings
        self.hold_start_spin.setValue(config.get("hold_start_ms", 500))
        self.hold_full_spin.setValue(config.get("hold_full_ms", 2000))

        # Reset channel for latching/toggle
        if hasattr(self, 'reset_channel_edit'):
            self._set_channel_edit_value(self.reset_channel_edit, config.get("reset_channel"))

        self._on_button_mode_changed()
        self._update_hold_progress()

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
            "invert": self.invert_check.isChecked(),
            "trigger_edge": self._get_edge_combo_value(self.trigger_edge_combo),
            "multiplier": self.multiplier_spin.value(),
            "divider": self.divider_spin.value(),
            "timeout_ms": self.timeout_spin.value(),
            "number_of_teeth": self.teeth_spin.value()
        })

        # Button function settings (only for switch subtypes)
        if subtype_value in [DigitalInputSubtype.SWITCH_ACTIVE_LOW.value,
                             DigitalInputSubtype.SWITCH_ACTIVE_HIGH.value]:
            button_mode = self.button_mode_combo.currentData()
            config["button_mode"] = button_mode

            if button_mode == ButtonMode.LONG_PRESS.value:
                config["long_press_ms"] = self.long_press_spin.value()
                if hasattr(self, 'long_press_output_edit'):
                    config["long_press_output"] = self.long_press_output_edit.text().strip()

            elif button_mode == ButtonMode.DOUBLE_CLICK.value:
                config["double_click_ms"] = self.double_click_spin.value()
                if hasattr(self, 'double_click_output_edit'):
                    config["double_click_output"] = self.double_click_output_edit.text().strip()

            elif button_mode == ButtonMode.PRESS_AND_HOLD.value:
                config["hold_start_ms"] = self.hold_start_spin.value()
                config["hold_full_ms"] = self.hold_full_spin.value()

            elif button_mode in [ButtonMode.LATCHING.value, ButtonMode.TOGGLE.value]:
                if hasattr(self, 'reset_channel_edit'):
                    config["reset_channel"] = self.reset_channel_edit.text().strip()

        return config

"""
Output Channel Configuration Dialog
Configures one of 30 high-side switch outputs
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List
from .channel_selector_dialog import ChannelSelectorDialog
from .base_channel_dialog import get_next_channel_id


class OutputConfigDialog(QDialog):
    """Dialog for configuring a single high-side output channel."""

    def __init__(self, parent=None, output_config: Optional[Dict[str, Any]] = None,
                 used_channels=None, available_channels=None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.output_config = output_config
        self.used_channels = used_channels or []
        self.available_channels = available_channels or {}  # Dict of (channel_id, name) tuples
        self.existing_channels = existing_channels or []

        # Store selected channel IDs (numeric)
        self._source_channel_id = None  # For control function
        self._duty_channel_id = None    # For PWM duty source

        # Determine if editing existing or creating new
        self.is_edit_mode = bool(output_config and output_config.get("channel_id") is not None)

        # Store or generate channel_id
        if self.is_edit_mode:
            self._channel_id = output_config.get("channel_id", 0)
        else:
            self._channel_id = get_next_channel_id(existing_channels)

        self.setWindowTitle("Edit Output" if self.is_edit_mode else "New Output")
        self.setModal(True)
        self.resize(600, 480)

        self._init_ui()

        if output_config:
            self._load_config(output_config)
        else:
            # Auto-generate name for new outputs
            self._auto_generate_name()

    def _auto_generate_name(self):
        """Auto-generate name for new output."""
        self.name_edit.setText(f"Output {self._channel_id}")

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        # Channel ID (read-only, auto-generated)
        self.channel_id_label = QLabel(str(self._channel_id))
        self.channel_id_label.setStyleSheet("font-weight: bold; color: #666;")
        basic_layout.addRow("Channel ID:", self.channel_id_label)

        # Name (editable)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Fuel Pump, Starter, Headlights")
        basic_layout.addRow("Name: *", self.name_edit)

        # Pin selection - up to 3 pins for increased current capacity
        pin_selection_layout = QVBoxLayout()
        pin_selection_layout.addWidget(QLabel("Pins (select 1-3 for higher current):"))

        pins_layout = QHBoxLayout()
        self.pin1_combo = QComboBox()
        self.pin1_combo.setToolTip("Primary output pin (O1-O30)")
        self._populate_available_pins(self.pin1_combo)
        self.pin1_combo.currentIndexChanged.connect(self._on_pin_selection_changed)
        pins_layout.addWidget(QLabel("Pin 1:"))
        pins_layout.addWidget(self.pin1_combo)

        self.pin2_combo = QComboBox()
        self.pin2_combo.setToolTip("Optional second pin for higher current")
        self._populate_available_pins(self.pin2_combo, include_none=True)
        self.pin2_combo.currentIndexChanged.connect(self._on_pin_selection_changed)
        pins_layout.addWidget(QLabel("Pin 2:"))
        pins_layout.addWidget(self.pin2_combo)

        self.pin3_combo = QComboBox()
        self.pin3_combo.setToolTip("Optional third pin for maximum current")
        self._populate_available_pins(self.pin3_combo, include_none=True)
        self.pin3_combo.currentIndexChanged.connect(self._on_pin_selection_changed)
        pins_layout.addWidget(QLabel("Pin 3:"))
        pins_layout.addWidget(self.pin3_combo)

        pin_selection_layout.addLayout(pins_layout)
        basic_layout.addRow("", pin_selection_layout)

        # On/Off enable checkbox
        self.enabled_check = QCheckBox("On/Off")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("", self.enabled_check)

        # Function control (always visible)
        control_function_layout = QHBoxLayout()
        self.control_function_edit = QLineEdit()
        self.control_function_edit.setPlaceholderText("Select function/channel...")
        self.control_function_edit.setReadOnly(True)
        self.control_function_edit.textChanged.connect(self._on_control_function_changed)
        control_function_layout.addWidget(self.control_function_edit, stretch=1)

        self.control_function_btn = QPushButton("Browse...")
        self.control_function_btn.clicked.connect(self._browse_control_function)
        control_function_layout.addWidget(self.control_function_btn)

        basic_layout.addRow("Control Function:", control_function_layout)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Current protection group - organized in 2 columns
        protection_group = QGroupBox("Current Protection")
        protection_layout = QGridLayout()

        # Row 0: Current Limit | Inrush Current
        protection_layout.addWidget(QLabel("Current Limit:"), 0, 0)
        self.current_limit_spin = QDoubleSpinBox()
        self.current_limit_spin.setRange(0.1, 50.0)
        self.current_limit_spin.setValue(10.0)
        self.current_limit_spin.setSuffix(" A")
        self.current_limit_spin.setDecimals(1)
        self.current_limit_spin.setSingleStep(0.5)
        self.current_limit_spin.setToolTip("Overcurrent shutdown threshold (0.1-50A)")
        protection_layout.addWidget(self.current_limit_spin, 0, 1)

        protection_layout.addWidget(QLabel("Inrush Current:"), 0, 2)
        self.inrush_current_spin = QDoubleSpinBox()
        self.inrush_current_spin.setRange(0.1, 100.0)
        self.inrush_current_spin.setValue(20.0)
        self.inrush_current_spin.setSuffix(" A")
        self.inrush_current_spin.setDecimals(1)
        self.inrush_current_spin.setSingleStep(1.0)
        self.inrush_current_spin.setToolTip("Peak current allowed during startup")
        protection_layout.addWidget(self.inrush_current_spin, 0, 3)

        # Row 1: Inrush Time | Retry Count
        protection_layout.addWidget(QLabel("Inrush Time:"), 1, 0)
        self.inrush_time_spin = QSpinBox()
        self.inrush_time_spin.setRange(10, 5000)
        self.inrush_time_spin.setValue(500)
        self.inrush_time_spin.setSuffix(" ms")
        self.inrush_time_spin.setToolTip("Time to allow inrush current")
        protection_layout.addWidget(self.inrush_time_spin, 1, 1)

        protection_layout.addWidget(QLabel("Retry Count:"), 1, 2)
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(3)
        self.retry_count_spin.setToolTip("Auto-retry attempts after fault (0 = disabled)")
        protection_layout.addWidget(self.retry_count_spin, 1, 3)

        # Row 2: Retry forever | Retry Delay
        self.retry_forever_check = QCheckBox("Retry forever")
        self.retry_forever_check.toggled.connect(self._on_retry_forever_toggled)
        protection_layout.addWidget(self.retry_forever_check, 2, 0, 1, 2)

        protection_layout.addWidget(QLabel("Retry Delay:"), 2, 2)
        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(100, 10000)
        self.retry_delay_spin.setValue(1000)
        self.retry_delay_spin.setSuffix(" ms")
        self.retry_delay_spin.setToolTip("Delay between retry attempts")
        protection_layout.addWidget(self.retry_delay_spin, 2, 3)

        protection_group.setLayout(protection_layout)
        layout.addWidget(protection_group)

        # PWM settings group - organized in 2 columns
        pwm_group = QGroupBox("PWM Settings")
        pwm_layout = QGridLayout()

        # Row 0: Enable PWM checkbox (full width)
        self.pwm_enabled_check = QCheckBox("Enable PWM Control")
        self.pwm_enabled_check.toggled.connect(self._on_pwm_toggled)
        pwm_layout.addWidget(self.pwm_enabled_check, 0, 0, 1, 4)

        # Row 1: PWM Frequency | Duty Value
        pwm_layout.addWidget(QLabel("PWM Frequency:"), 1, 0)
        self.pwm_freq_spin = QSpinBox()
        self.pwm_freq_spin.setRange(100, 20000)
        self.pwm_freq_spin.setValue(1000)
        self.pwm_freq_spin.setSuffix(" Hz")
        self.pwm_freq_spin.setToolTip("PWM frequency (100-20000 Hz)")
        pwm_layout.addWidget(self.pwm_freq_spin, 1, 1)

        pwm_layout.addWidget(QLabel("Duty Value:"), 1, 2)
        self.pwm_duty_spin = QDoubleSpinBox()
        self.pwm_duty_spin.setRange(0.0, 100.0)
        self.pwm_duty_spin.setValue(50.0)
        self.pwm_duty_spin.setSuffix(" %")
        self.pwm_duty_spin.setDecimals(1)
        self.pwm_duty_spin.setSingleStep(5.0)
        self.pwm_duty_spin.setToolTip("Fixed PWM duty cycle (0-100%)")
        pwm_layout.addWidget(self.pwm_duty_spin, 1, 3)

        # Row 2: Duty Function (full width)
        pwm_layout.addWidget(QLabel("Duty Function:"), 2, 0)
        duty_function_layout = QHBoxLayout()
        self.duty_function_edit = QLineEdit()
        self.duty_function_edit.setPlaceholderText("Select channel/function for duty...")
        self.duty_function_edit.setReadOnly(True)
        duty_function_layout.addWidget(self.duty_function_edit, stretch=1)

        self.duty_function_btn = QPushButton("Browse...")
        self.duty_function_btn.clicked.connect(self._browse_duty_function)
        duty_function_layout.addWidget(self.duty_function_btn)
        pwm_layout.addLayout(duty_function_layout, 2, 1, 1, 3)

        # Row 3: Enable Soft Start | Soft Start Duration
        self.soft_start_check = QCheckBox("Enable Soft Start")
        self.soft_start_check.toggled.connect(self._on_soft_start_toggled)
        pwm_layout.addWidget(self.soft_start_check, 3, 0, 1, 2)

        pwm_layout.addWidget(QLabel("Soft Start Duration:"), 3, 2)
        self.soft_start_duration_spin = QSpinBox()
        self.soft_start_duration_spin.setRange(10, 10000)
        self.soft_start_duration_spin.setValue(1000)
        self.soft_start_duration_spin.setSuffix(" ms")
        self.soft_start_duration_spin.setToolTip("Soft start ramp duration")
        pwm_layout.addWidget(self.soft_start_duration_spin, 3, 3)

        pwm_group.setLayout(pwm_layout)
        layout.addWidget(pwm_group)

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

        # Initialize controls state
        self._on_pwm_toggled(False)
        self._on_soft_start_toggled(False)
        self._on_retry_forever_toggled(False)

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        # Validate that at least one pin is selected
        pin1 = self.pin1_combo.currentData()
        if pin1 is None or pin1 < 0:
            QMessageBox.warning(self, "Validation Error", "At least Pin 1 must be selected!")
            self.pin1_combo.setFocus()
            return

        # Validate no duplicate pins
        pins = []
        if pin1 is not None and pin1 >= 0:
            pins.append(pin1)

        pin2 = self.pin2_combo.currentData()
        if pin2 is not None and pin2 >= 0:
            if pin2 in pins:
                QMessageBox.warning(self, "Validation Error", "Pin 2 cannot be the same as Pin 1!")
                self.pin2_combo.setFocus()
                return
            pins.append(pin2)

        pin3 = self.pin3_combo.currentData()
        if pin3 is not None and pin3 >= 0:
            if pin3 in pins:
                QMessageBox.warning(self, "Validation Error", "Pin 3 cannot be the same as Pin 1 or Pin 2!")
                self.pin3_combo.setFocus()
                return
            pins.append(pin3)

        # Validate that none of the selected pins are already used by other outputs
        current_pins = []
        if self.output_config:
            current_pins = self.output_config.get("pins", [])

        for pin in pins:
            if pin in self.used_channels and pin not in current_pins:
                QMessageBox.warning(
                    self, "Validation Error",
                    f"Pin O{pin + 1} is already used by another output!"
                )
                return

        self.accept()

    def _populate_available_pins(self, combo: QComboBox, include_none: bool = False, exclude_pins: list = None):
        """Populate pin dropdown with available pins.

        Args:
            combo: The combobox to populate
            include_none: Whether to include "None" option
            exclude_pins: Additional pins to exclude (from other combos in the form)
        """
        # Save current selection
        current_selection = combo.currentData()

        combo.clear()

        # Add "None" option for optional pins
        if include_none:
            combo.addItem("None", -1)

        # Get currently used pins if editing (allow these pins for this output)
        current_pins = []
        if self.output_config:
            current_pins = self.output_config.get("pins", [])

        # Combine used channels with pins to exclude from form
        exclude_set = set(self.used_channels)
        if exclude_pins:
            exclude_set.update(exclude_pins)

        # Add available pins (O1-O30)
        for pin in range(30):
            if pin not in exclude_set or pin in current_pins:
                combo.addItem(f"O{pin + 1}", pin)

        # If no pins available and not optional, add a placeholder
        if combo.count() == 0 and not include_none:
            combo.addItem("No pins available", -1)

        # Restore selection if possible
        if current_selection is not None:
            index = combo.findData(current_selection)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _on_pin_selection_changed(self):
        """Handle pin selection change - update other combos to exclude selected pins."""
        # Get currently selected pins from each combo
        pin1 = self.pin1_combo.currentData()
        pin2 = self.pin2_combo.currentData()
        pin3 = self.pin3_combo.currentData()

        # Build exclusion lists for each combo (exclude pins selected in OTHER combos)
        exclude_for_pin1 = []
        exclude_for_pin2 = []
        exclude_for_pin3 = []

        if pin1 is not None and pin1 >= 0:
            exclude_for_pin2.append(pin1)
            exclude_for_pin3.append(pin1)

        if pin2 is not None and pin2 >= 0:
            exclude_for_pin1.append(pin2)
            exclude_for_pin3.append(pin2)

        if pin3 is not None and pin3 >= 0:
            exclude_for_pin1.append(pin3)
            exclude_for_pin2.append(pin3)

        # Block signals to prevent recursion
        self.pin1_combo.blockSignals(True)
        self.pin2_combo.blockSignals(True)
        self.pin3_combo.blockSignals(True)

        # Repopulate combos with updated exclusions
        self._populate_available_pins(self.pin1_combo, include_none=False, exclude_pins=exclude_for_pin1)
        self._populate_available_pins(self.pin2_combo, include_none=True, exclude_pins=exclude_for_pin2)
        self._populate_available_pins(self.pin3_combo, include_none=True, exclude_pins=exclude_for_pin3)

        # Unblock signals
        self.pin1_combo.blockSignals(False)
        self.pin2_combo.blockSignals(False)
        self.pin3_combo.blockSignals(False)

    def _on_control_function_changed(self, text: str):
        """Handle control function change - disable checkbox if function is set."""
        has_function = bool(text.strip())
        self.enabled_check.setEnabled(not has_function)
        if has_function:
            self.enabled_check.setChecked(False)

    def _on_retry_forever_toggled(self, enabled: bool):
        """Handle retry forever enable/disable."""
        self.retry_count_spin.setEnabled(not enabled)

    def _on_soft_start_toggled(self, enabled: bool):
        """Handle soft start enable/disable."""
        self.soft_start_duration_spin.setEnabled(enabled)

    def _on_pwm_toggled(self, enabled: bool):
        """Handle PWM enable/disable."""
        self.pwm_freq_spin.setEnabled(enabled)
        self.pwm_duty_spin.setEnabled(enabled)
        self.duty_function_edit.setEnabled(enabled)
        self.duty_function_btn.setEnabled(enabled)
        self.soft_start_check.setEnabled(enabled)
        self.soft_start_duration_spin.setEnabled(enabled and self.soft_start_check.isChecked())

    def _get_channel_name_by_id(self, channel_id) -> str:
        """Find channel name by its numeric channel_id."""
        if channel_id is None:
            return ""
        for category, channels in self.available_channels.items():
            for ch in channels:
                if isinstance(ch, tuple) and len(ch) == 2:
                    ch_id, name = ch
                    if ch_id == channel_id:
                        return name
        # Fallback - return str of channel_id
        return str(channel_id) if channel_id else ""

    def _browse_control_function(self):
        """Browse and select control function channel."""
        channel_id = ChannelSelectorDialog.select_channel(
            self, self._source_channel_id, self.available_channels
        )
        if channel_id is not None:
            self._source_channel_id = channel_id
            name = self._get_channel_name_by_id(channel_id)
            self.control_function_edit.setText(name)

    def _browse_duty_function(self):
        """Browse and select duty function channel."""
        channel_id = ChannelSelectorDialog.select_channel(
            self, self._duty_channel_id, self.available_channels
        )
        if channel_id is not None:
            self._duty_channel_id = channel_id
            name = self._get_channel_name_by_id(channel_id)
            self.duty_function_edit.setText(name)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog.

        Supports both nested format (pwm.duty_value) and flat format (duty_fixed).
        """
        self.name_edit.setText(config.get("name", config.get("id", "")))

        # Load pins (up to 3)
        pins = config.get("pins", [])
        if len(pins) > 0:
            index = self.pin1_combo.findData(pins[0])
            if index >= 0:
                self.pin1_combo.setCurrentIndex(index)
        if len(pins) > 1:
            index = self.pin2_combo.findData(pins[1])
            if index >= 0:
                self.pin2_combo.setCurrentIndex(index)
        if len(pins) > 2:
            index = self.pin3_combo.findData(pins[2])
            if index >= 0:
                self.pin3_combo.setCurrentIndex(index)

        # Control settings - source_channel can be numeric (new) or string (legacy)
        # Block signal to prevent _on_control_function_changed from resetting enabled
        self.control_function_edit.blockSignals(True)
        source_channel = config.get("source_channel", config.get("control_function"))
        if source_channel is not None:
            if isinstance(source_channel, int):
                # Numeric channel_id - store and find name for display
                self._source_channel_id = source_channel
                display_name = self._get_channel_name_by_id(source_channel)
                self.control_function_edit.setText(display_name if display_name else str(source_channel))
            else:
                # Legacy string format - display as-is
                self.control_function_edit.setText(str(source_channel))
                self._source_channel_id = None  # Can't determine numeric ID from string
        else:
            self.control_function_edit.setText("")
            self._source_channel_id = None
        self.control_function_edit.blockSignals(False)
        # Set enabled state AFTER control function is set
        enabled = config.get("enabled", True)
        self.enabled_check.setChecked(enabled)
        # If control function is set, disable the checkbox but keep its loaded value
        if source_channel is not None:
            self.enabled_check.setEnabled(False)

        # Protection settings - check both nested and flat formats
        protection = config.get("protection", {})
        self.current_limit_spin.setValue(
            protection.get("current_limit", config.get("current_limit_a", 10.0)))
        self.inrush_current_spin.setValue(
            protection.get("inrush_current", config.get("inrush_current_a", 20.0)))
        self.inrush_time_spin.setValue(
            protection.get("inrush_time_ms", config.get("inrush_time_ms", 500)))
        self.retry_count_spin.setValue(
            protection.get("retry_count", config.get("retry_count", 3)))
        self.retry_forever_check.setChecked(
            protection.get("retry_forever", config.get("retry_forever", False)))
        self.retry_delay_spin.setValue(
            protection.get("retry_delay_ms", config.get("retry_delay_ms", 1000)))

        # PWM settings - check both nested and flat formats
        pwm = config.get("pwm", {})
        self.pwm_enabled_check.setChecked(
            pwm.get("enabled", config.get("pwm_enabled", False)))
        self.pwm_freq_spin.setValue(
            pwm.get("frequency", config.get("pwm_frequency_hz", 1000)))

        # Duty settings - support both formats:
        # - nested: pwm.duty_value, pwm.duty_function
        # - flat: duty_fixed, duty_channel
        duty_value = pwm.get("duty_value", config.get("duty_fixed", 50.0))
        duty_channel = pwm.get("duty_function", config.get("duty_channel"))
        self.pwm_duty_spin.setValue(duty_value)
        if duty_channel is not None:
            if isinstance(duty_channel, int):
                self._duty_channel_id = duty_channel
                display_name = self._get_channel_name_by_id(duty_channel)
                self.duty_function_edit.setText(display_name if display_name else str(duty_channel))
            else:
                self.duty_function_edit.setText(str(duty_channel) if duty_channel else "")
                self._duty_channel_id = None
        else:
            self.duty_function_edit.setText("")
            self._duty_channel_id = None

        # Soft start - check both formats
        self.soft_start_check.setChecked(
            pwm.get("soft_start_enabled", config.get("soft_start_ms", 0) > 0))
        self.soft_start_duration_spin.setValue(
            pwm.get("soft_start_duration_ms", config.get("soft_start_ms", 1000)))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog.

        Outputs both nested and flat formats for compatibility.
        """
        # Collect selected pins (1-3)
        pins = []
        pin1 = self.pin1_combo.currentData()
        if pin1 is not None and pin1 >= 0:
            pins.append(pin1)

        pin2 = self.pin2_combo.currentData()
        if pin2 is not None and pin2 >= 0:
            pins.append(pin2)

        pin3 = self.pin3_combo.currentData()
        if pin3 is not None and pin3 >= 0:
            pins.append(pin3)

        name = self.name_edit.text().strip()
        duty_value = self.pwm_duty_spin.value()
        pwm_enabled = self.pwm_enabled_check.isChecked()
        pwm_freq = self.pwm_freq_spin.value()
        soft_start_enabled = self.soft_start_check.isChecked()
        soft_start_ms = self.soft_start_duration_spin.value() if soft_start_enabled else 0

        config = {
            "channel_id": self._channel_id,
            "channel_type": "power_output",
            "pins": pins,
            "name": name,
            "id": name,  # String name for display
            "enabled": self.enabled_check.isChecked(),
            "source_channel": self._source_channel_id,  # Numeric channel_id for firmware
            # Flat format fields for model compatibility
            "pwm_enabled": pwm_enabled,
            "pwm_frequency_hz": pwm_freq,
            "duty_fixed": duty_value,
            "duty_channel": self._duty_channel_id,  # Numeric channel_id for firmware
            "soft_start_ms": soft_start_ms,
            "current_limit_a": self.current_limit_spin.value(),
            "inrush_current_a": self.inrush_current_spin.value(),
            "inrush_time_ms": self.inrush_time_spin.value(),
            "retry_count": self.retry_count_spin.value(),
            "retry_forever": self.retry_forever_check.isChecked(),
            "retry_delay_ms": self.retry_delay_spin.value(),
            # Nested format for backward compatibility
            "protection": {
                "current_limit": self.current_limit_spin.value(),
                "inrush_current": self.inrush_current_spin.value(),
                "inrush_time_ms": self.inrush_time_spin.value(),
                "retry_count": self.retry_count_spin.value(),
                "retry_forever": self.retry_forever_check.isChecked(),
                "retry_delay_ms": self.retry_delay_spin.value()
            },
            "pwm": {
                "enabled": pwm_enabled,
                "frequency": pwm_freq,
                "duty_value": duty_value,
                "duty_function": self._duty_channel_id,  # Numeric channel_id
                "soft_start_enabled": soft_start_enabled,
                "soft_start_duration_ms": self.soft_start_duration_spin.value()
            }
        }

        return config

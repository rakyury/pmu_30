"""
Output Channel Configuration Dialog
Configures one of 30 high-side switch outputs

Inherits from BaseChannelDialog for common channel handling (name, channel_id).
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QLabel, QMessageBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from .channel_selector_dialog import ChannelSelectorDialog
from models.channel import ChannelType
from models.channel_display_service import ChannelDisplayService
from ui.widgets.constant_spinbox import CurrentSpinBox, PercentageSpinBox


class OutputConfigDialog(BaseChannelDialog):
    """Dialog for configuring a single high-side output channel.

    Inherits from BaseChannelDialog which provides:
    - Channel ID generation and display
    - Name field with auto-generation
    - Common validation
    - Button layout
    """

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None,
                 available_channels=None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None,
                 **kwargs):
        """Initialize OutputConfigDialog.

        Args:
            parent: Parent widget
            config: Output configuration (for editing) or None (for creating)
            available_channels: Dict of available channels for source selection
            existing_channels: List of existing channel configs
            **kwargs: Additional arguments:
                - used_pins: List of already used output pins
                - output_config: Alias for config (backwards compatibility)
                - used_channels: Alias for used_pins (backwards compatibility)
        """
        # Handle backwards compatibility aliases
        if config is None:
            config = kwargs.get('output_config')

        # Handle used_pins/used_channels naming inconsistency
        self.used_pins = kwargs.get('used_pins') or kwargs.get('used_channels') or []

        # Store selected channel IDs (can be numeric int or string ID)
        self._source_channel_id = None  # For control function (int or str)
        self._duty_channel_id = None    # For PWM duty source (int or str)

        # Initialize base class (handles channel_id, name, etc.)
        super().__init__(parent, config, available_channels, ChannelType.POWER_OUTPUT, existing_channels)

        # Create tabbed sections
        self.tab_widget = QTabWidget()
        self.content_layout.addWidget(self.tab_widget)

        # Output Settings tab (first)
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        self._create_output_settings_group(output_layout)
        output_layout.addStretch()
        self.tab_widget.addTab(output_tab, "Output")

        # Protection tab
        protection_tab = QWidget()
        protection_layout = QVBoxLayout(protection_tab)
        self._create_protection_group(protection_layout)
        protection_layout.addStretch()
        self.tab_widget.addTab(protection_tab, "Protection")

        # PWM tab
        pwm_tab = QWidget()
        pwm_layout = QVBoxLayout(pwm_tab)
        self._create_pwm_group(pwm_layout)
        pwm_layout.addStretch()
        self.tab_widget.addTab(pwm_tab, "PWM")

        # Initialize controls state BEFORE loading config
        self._on_pwm_toggled(False)
        self._on_soft_start_toggled(False)
        self._on_retry_forever_toggled(False)

        # Load config if editing (this will override the initial state)
        if config:
            self._load_specific_config(config)

        # Finalize UI sizing
        self._finalize_ui()

    def _create_output_settings_group(self, parent_layout):
        """Create output-specific settings group (pins, control function)."""
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()

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
        output_layout.addRow("", pin_selection_layout)

        # Function control (output is controlled ONLY by control function)
        control_function_layout = QHBoxLayout()
        self.control_function_edit = QLineEdit()
        self.control_function_edit.setPlaceholderText("Select function/channel...")
        self.control_function_edit.setReadOnly(True)
        control_function_layout.addWidget(self.control_function_edit, stretch=1)

        self.control_function_btn = QPushButton("Browse...")
        self.control_function_btn.clicked.connect(self._browse_control_function)
        control_function_layout.addWidget(self.control_function_btn)

        self.control_function_clear_btn = QPushButton("✕")
        self.control_function_clear_btn.setFixedWidth(30)
        self.control_function_clear_btn.setToolTip("Clear control function")
        self.control_function_clear_btn.clicked.connect(self._clear_control_function)
        control_function_layout.addWidget(self.control_function_clear_btn)

        output_layout.addRow("Control Function:", control_function_layout)

        output_group.setLayout(output_layout)
        parent_layout.addWidget(output_group)

    def _create_protection_group(self, parent_layout):
        """Create current protection settings group."""
        protection_group = QGroupBox("Current Protection")
        protection_layout = QGridLayout()

        # Row 0: Current Limit | Inrush Current
        protection_layout.addWidget(QLabel("Current Limit:"), 0, 0)
        self.current_limit_spin = CurrentSpinBox()
        self.current_limit_spin.setRange(0.1, 50.0)
        self.current_limit_spin.setValue(10.0)
        self.current_limit_spin.setSingleStep(0.5)
        self.current_limit_spin.setToolTip("Overcurrent shutdown threshold (0.1-50A)")
        protection_layout.addWidget(self.current_limit_spin, 0, 1)

        protection_layout.addWidget(QLabel("Inrush Current:"), 0, 2)
        self.inrush_current_spin = CurrentSpinBox()
        self.inrush_current_spin.setRange(0.1, 100.0)
        self.inrush_current_spin.setValue(20.0)
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

        # Row 3: Load Shedding Priority
        protection_layout.addWidget(QLabel("Shed Priority:"), 3, 0)
        self.shed_priority_spin = QSpinBox()
        self.shed_priority_spin.setRange(0, 10)
        self.shed_priority_spin.setValue(5)
        self.shed_priority_spin.setToolTip(
            "Load shedding priority (0=critical/never shed, 1-10=shed order, higher=shed first)")
        protection_layout.addWidget(self.shed_priority_spin, 3, 1)

        # Add explanatory label for shed priority
        shed_priority_label = QLabel("0=Critical, 10=Shed first")
        shed_priority_label.setStyleSheet("color: #888; font-size: 11px;")
        protection_layout.addWidget(shed_priority_label, 3, 2, 1, 2)

        protection_group.setLayout(protection_layout)
        parent_layout.addWidget(protection_group)

    def _create_pwm_group(self, parent_layout):
        """Create PWM settings group."""
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
        self.pwm_duty_spin = PercentageSpinBox()
        self.pwm_duty_spin.setValue(50.0)
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

        self.duty_function_clear_btn = QPushButton("✕")
        self.duty_function_clear_btn.setFixedWidth(30)
        self.duty_function_clear_btn.setToolTip("Clear duty function")
        self.duty_function_clear_btn.clicked.connect(self._clear_duty_function)
        duty_function_layout.addWidget(self.duty_function_clear_btn)

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
        parent_layout.addWidget(pwm_group)

    def _validate_specific(self) -> List[str]:
        """Validate output-specific fields."""
        errors = []

        # Validate that at least one pin is selected
        pin1 = self.pin1_combo.currentData()
        if pin1 is None or pin1 < 0:
            errors.append("At least Pin 1 must be selected")
            return errors

        # Validate no duplicate pins
        pins = []
        if pin1 is not None and pin1 >= 0:
            pins.append(pin1)

        pin2 = self.pin2_combo.currentData()
        if pin2 is not None and pin2 >= 0:
            if pin2 in pins:
                errors.append("Pin 2 cannot be the same as Pin 1")
            else:
                pins.append(pin2)

        pin3 = self.pin3_combo.currentData()
        if pin3 is not None and pin3 >= 0:
            if pin3 in pins:
                errors.append("Pin 3 cannot be the same as Pin 1 or Pin 2")
            else:
                pins.append(pin3)

        # Validate that none of the selected pins are already used by other outputs
        current_pins = []
        if self.config:
            current_pins = self.config.get("pins", [])

        for pin in pins:
            if pin in self.used_pins and pin not in current_pins:
                errors.append(f"Pin O{pin + 1} is already used by another output")

        return errors

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
        # Support both "pins" and "output_pins" field names
        current_pins = []
        if self.config:
            current_pins = self.config.get("output_pins") or self.config.get("pins") or []

        # Combine used channels with pins to exclude from form
        exclude_set = set(self.used_pins)
        if exclude_pins:
            exclude_set.update(exclude_pins)

        # Add available pins (O1-O30) with power rating
        # All PMU-30 outputs are rated for 40A
        for pin in range(30):
            if pin not in exclude_set or pin in current_pins:
                combo.addItem(f"O{pin + 1} (40A)", pin)

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
        self.duty_function_clear_btn.setEnabled(enabled)
        self.soft_start_check.setEnabled(enabled)
        self.soft_start_duration_spin.setEnabled(enabled and self.soft_start_check.isChecked())

    def _browse_control_function(self):
        """Browse and select control function channel."""
        accepted, channel_id = ChannelSelectorDialog.select_channel(
            self, self._source_channel_id, self.available_channels
        )
        if accepted:
            # User confirmed - update even if cleared (None)
            self._source_channel_id = channel_id
            if channel_id is not None:
                name = self._get_channel_display_name(channel_id)
                self.control_function_edit.setText(name)
            else:
                self.control_function_edit.setText("")

    def _clear_control_function(self):
        """Clear control function selection."""
        self._source_channel_id = None
        self.control_function_edit.setText("")

    def _browse_duty_function(self):
        """Browse and select duty function channel."""
        accepted, channel_id = ChannelSelectorDialog.select_channel(
            self, self._duty_channel_id, self.available_channels
        )
        if accepted:
            # User confirmed - update even if cleared (None)
            self._duty_channel_id = channel_id
            if channel_id is not None:
                name = self._get_channel_display_name(channel_id)
                self.duty_function_edit.setText(name)
            else:
                self.duty_function_edit.setText("")

    def _clear_duty_function(self):
        """Clear duty function selection."""
        self._duty_channel_id = None
        self.duty_function_edit.setText("")

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load output-specific configuration.

        Supports both nested format (pwm.duty_value) and flat format (duty_fixed).
        """
        # Load pins (up to 3) - support both "output_pins" and "pins" field names
        pins = config.get("output_pins") or config.get("pins") or []
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

        # Control settings - source_channel can be numeric (int) or string (channel ID)
        source_channel = config.get("source_channel", config.get("control_function"))
        if source_channel is not None:
            self._source_channel_id = source_channel  # Store as-is (int or str)
            if isinstance(source_channel, int):
                # Numeric channel ID - look up display name
                display_name = self._get_channel_display_name(source_channel)
                self.control_function_edit.setText(display_name if display_name else str(source_channel))
            else:
                # String channel ID - display as-is
                self.control_function_edit.setText(str(source_channel))
        else:
            self.control_function_edit.setText("")
            self._source_channel_id = None

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
        self.shed_priority_spin.setValue(
            protection.get("shed_priority", config.get("shed_priority", 5)))

        # PWM settings - check both nested and flat formats
        pwm = config.get("pwm", {})
        self.pwm_enabled_check.setChecked(
            pwm.get("enabled", config.get("pwm_enabled", False)))
        self.pwm_freq_spin.setValue(
            pwm.get("frequency", config.get("pwm_frequency_hz", 1000)))

        # Duty settings - support both formats
        duty_value = pwm.get("duty_value", config.get("duty_fixed", 50.0))
        duty_channel = pwm.get("duty_function", config.get("duty_channel"))
        self.pwm_duty_spin.setValue(duty_value)
        if duty_channel is not None:
            self._duty_channel_id = duty_channel  # Store as-is (int or str)
            if isinstance(duty_channel, int):
                display_name = self._get_channel_display_name(duty_channel)
                self.duty_function_edit.setText(display_name if display_name else str(duty_channel))
            else:
                # String channel ID - display as-is
                self.duty_function_edit.setText(str(duty_channel))
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
        # Get base config (channel_id, name, channel_type)
        config = self.get_base_config()

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

        # Add output-specific fields
        config.update({
            "output_pins": pins,  # Primary field name (used by defaults and firmware)
            "pins": pins,  # Also include for backwards compatibility
            "id": name,  # String name for display
            "source_channel": self._source_channel_id,  # Channel ID (int or str) for firmware
            # Flat format fields for model compatibility
            "pwm_enabled": pwm_enabled,
            "pwm_frequency_hz": pwm_freq,
            "duty_fixed": duty_value,
            "duty_channel": self._duty_channel_id,  # Channel ID (int or str) for firmware
            "soft_start_ms": soft_start_ms,
            "current_limit_a": self.current_limit_spin.value(),
            "inrush_current_a": self.inrush_current_spin.value(),
            "inrush_time_ms": self.inrush_time_spin.value(),
            "retry_count": self.retry_count_spin.value(),
            "retry_forever": self.retry_forever_check.isChecked(),
            "retry_delay_ms": self.retry_delay_spin.value(),
            "shed_priority": self.shed_priority_spin.value(),
            # Nested format for backward compatibility
            "protection": {
                "current_limit": self.current_limit_spin.value(),
                "inrush_current": self.inrush_current_spin.value(),
                "inrush_time_ms": self.inrush_time_spin.value(),
                "retry_count": self.retry_count_spin.value(),
                "retry_forever": self.retry_forever_check.isChecked(),
                "retry_delay_ms": self.retry_delay_spin.value(),
                "shed_priority": self.shed_priority_spin.value()
            },
            "pwm": {
                "enabled": pwm_enabled,
                "frequency": pwm_freq,
                "duty_value": duty_value,
                "duty_function": self._duty_channel_id,  # Channel ID (int or str)
                "soft_start_enabled": soft_start_enabled,
                "soft_start_duration_ms": self.soft_start_duration_spin.value()
            }
        })

        return config

    def _finalize_ui(self):
        """Override to customize dialog size - compact form."""
        # First adjust to content
        self.adjustSize()

        # Get base size
        current_size = self.sizeHint()

        # Apply size adjustments:
        # - Width: 0.86x (compact)
        # - Height: 0.7x (30% reduction)
        new_width = int(current_size.width() * 0.86)
        new_height = int(current_size.height() * 0.7)

        self.resize(new_width, new_height)
        self.setMinimumSize(new_width, new_height)

"""
Timer Configuration Dialog
Allows creation of timers with various modes
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDialogButtonBox, QGroupBox, QCheckBox, QLabel
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List


class TimerDialog(QDialog):
    """Dialog for configuring timers."""

    TIMER_MODES = [
        "On Delay",
        "Off Delay",
        "Pulse",
        "Retentive"
    ]

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None, available_channels: Optional[List[str]] = None):
        super().__init__(parent)
        self.config = config or {}
        self.available_channels = available_channels or []
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Timer Configuration")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter timer name...")
        basic_layout.addRow("Name: *", self.name_edit)

        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        basic_layout.addRow("Enabled:", self.enabled_check)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.TIMER_MODES)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        basic_layout.addRow("Mode:", self.mode_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Trigger group
        trigger_group = QGroupBox("Trigger")
        trigger_layout = QFormLayout()

        self.trigger_channel_combo = QComboBox()
        self.trigger_channel_combo.setEditable(True)
        self.trigger_channel_combo.addItems(self.available_channels)
        self.trigger_channel_combo.setPlaceholderText("Select trigger channel...")
        trigger_layout.addRow("Trigger Channel:", self.trigger_channel_combo)

        self.trigger_invert_check = QCheckBox("Invert trigger (active low)")
        trigger_layout.addRow("", self.trigger_invert_check)

        trigger_group.setLayout(trigger_layout)
        layout.addWidget(trigger_group)

        # Timing group
        timing_group = QGroupBox("Timing")
        timing_layout = QFormLayout()

        delay_layout = QHBoxLayout()
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 3600000)  # 0 to 1 hour in ms
        self.delay_spin.setValue(1000)
        self.delay_spin.setSuffix(" ms")
        delay_layout.addWidget(self.delay_spin)
        timing_layout.addRow("Delay:", delay_layout)

        # Pulse duration (only for Pulse mode)
        pulse_layout = QHBoxLayout()
        self.pulse_spin = QSpinBox()
        self.pulse_spin.setRange(1, 3600000)
        self.pulse_spin.setValue(100)
        self.pulse_spin.setSuffix(" ms")
        self.pulse_label = QLabel("Pulse Duration:")
        pulse_layout.addWidget(self.pulse_spin)
        timing_layout.addRow(self.pulse_label, pulse_layout)

        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)

        # Behavior
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout()

        self.reset_on_trigger_check = QCheckBox("Reset on trigger loss")
        behavior_layout.addWidget(self.reset_on_trigger_check)

        self.one_shot_check = QCheckBox("One-shot mode (requires reset)")
        behavior_layout.addWidget(self.one_shot_check)

        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)

        # Mode description
        self.mode_desc_label = QLabel()
        self.mode_desc_label.setWordWrap(True)
        self.mode_desc_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(self.mode_desc_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Update mode description
        self._on_mode_changed(self.mode_combo.currentText())

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _on_mode_changed(self, mode: str):
        """Handle mode change."""
        # Show/hide pulse duration based on mode
        is_pulse = mode == "Pulse"
        self.pulse_label.setVisible(is_pulse)
        self.pulse_spin.setVisible(is_pulse)

        # Update description
        descriptions = {
            "On Delay": "Output turns ON after delay when trigger becomes active.",
            "Off Delay": "Output turns OFF after delay when trigger becomes inactive.",
            "Pulse": "Output generates a pulse of fixed duration when triggered.",
            "Retentive": "Timer accumulates time while trigger is active, retains value when inactive."
        }
        self.mode_desc_label.setText(descriptions.get(mode, ""))

    def _load_config(self):
        """Load configuration into UI."""
        if not self.config:
            return

        self.name_edit.setText(self.config.get("name", ""))
        self.enabled_check.setChecked(self.config.get("enabled", True))

        mode = self.config.get("mode", "On Delay")
        idx = self.mode_combo.findText(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

        trigger = self.config.get("trigger", {})
        channel = trigger.get("channel", "")
        if channel:
            self.trigger_channel_combo.setCurrentText(channel)
        self.trigger_invert_check.setChecked(trigger.get("invert", False))

        timing = self.config.get("timing", {})
        self.delay_spin.setValue(timing.get("delay_ms", 1000))
        self.pulse_spin.setValue(timing.get("pulse_duration_ms", 100))

        behavior = self.config.get("behavior", {})
        self.reset_on_trigger_check.setChecked(behavior.get("reset_on_trigger_loss", False))
        self.one_shot_check.setChecked(behavior.get("one_shot", False))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from UI."""
        return {
            "name": self.name_edit.text(),
            "enabled": self.enabled_check.isChecked(),
            "mode": self.mode_combo.currentText(),
            "trigger": {
                "channel": self.trigger_channel_combo.currentText(),
                "invert": self.trigger_invert_check.isChecked()
            },
            "timing": {
                "delay_ms": self.delay_spin.value(),
                "pulse_duration_ms": self.pulse_spin.value()
            },
            "behavior": {
                "reset_on_trigger_loss": self.reset_on_trigger_check.isChecked(),
                "one_shot": self.one_shot_check.isChecked()
            }
        }

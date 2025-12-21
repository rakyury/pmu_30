"""
Switch Configuration Dialog
Allows creation of conditional switches
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDoubleSpinBox, QDialogButtonBox, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List


class SwitchDialog(QDialog):
    """Dialog for configuring conditional switches."""

    COMPARISON_TYPES = [
        "Greater than (>)",
        "Less than (<)",
        "Equal to (=)",
        "Not equal to (!=)",
        "Greater or equal (>=)",
        "Less or equal (<=)"
    ]

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None, available_channels: Optional[List[str]] = None):
        super().__init__(parent)
        self.config = config or {}
        self.available_channels = available_channels or []
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Switch Configuration")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter switch name...")
        basic_layout.addRow("Name:", self.name_edit)

        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        basic_layout.addRow("Enabled:", self.enabled_check)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Condition group
        condition_group = QGroupBox("Condition")
        condition_layout = QFormLayout()

        self.channel_combo = QComboBox()
        self.channel_combo.setEditable(True)
        self.channel_combo.addItems(self.available_channels)
        self.channel_combo.setPlaceholderText("Select or enter channel...")
        condition_layout.addRow("Input Channel:", self.channel_combo)

        self.comparison_combo = QComboBox()
        self.comparison_combo.addItems(self.COMPARISON_TYPES)
        condition_layout.addRow("Comparison:", self.comparison_combo)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(-1000000, 1000000)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setSingleStep(1.0)
        condition_layout.addRow("Threshold:", self.threshold_spin)

        condition_group.setLayout(condition_layout)
        layout.addWidget(condition_group)

        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout()

        self.invert_check = QCheckBox("Invert output (normally closed)")
        behavior_layout.addWidget(self.invert_check)

        self.hysteresis_check = QCheckBox("Enable hysteresis")
        self.hysteresis_check.stateChanged.connect(self._on_hysteresis_changed)
        behavior_layout.addWidget(self.hysteresis_check)

        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Hysteresis:"))
        self.hysteresis_spin = QDoubleSpinBox()
        self.hysteresis_spin.setRange(0, 1000)
        self.hysteresis_spin.setDecimals(2)
        self.hysteresis_spin.setValue(1.0)
        self.hysteresis_spin.setEnabled(False)
        h_layout.addWidget(self.hysteresis_spin)
        behavior_layout.addLayout(h_layout)

        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_hysteresis_changed(self, state):
        """Handle hysteresis enable/disable."""
        self.hysteresis_spin.setEnabled(state == Qt.CheckState.Checked.value)

    def _load_config(self):
        """Load configuration into UI."""
        if not self.config:
            return

        self.name_edit.setText(self.config.get("name", ""))
        self.enabled_check.setChecked(self.config.get("enabled", True))

        condition = self.config.get("condition", {})
        channel = condition.get("channel", "")
        if channel:
            self.channel_combo.setCurrentText(channel)

        comparison = condition.get("comparison", "Greater than (>)")
        idx = self.comparison_combo.findText(comparison)
        if idx >= 0:
            self.comparison_combo.setCurrentIndex(idx)

        self.threshold_spin.setValue(condition.get("threshold", 0.0))

        behavior = self.config.get("behavior", {})
        self.invert_check.setChecked(behavior.get("invert", False))

        use_hysteresis = behavior.get("use_hysteresis", False)
        self.hysteresis_check.setChecked(use_hysteresis)
        self.hysteresis_spin.setValue(behavior.get("hysteresis", 1.0))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from UI."""
        return {
            "name": self.name_edit.text(),
            "enabled": self.enabled_check.isChecked(),
            "condition": {
                "channel": self.channel_combo.currentText(),
                "comparison": self.comparison_combo.currentText(),
                "threshold": self.threshold_spin.value()
            },
            "behavior": {
                "invert": self.invert_check.isChecked(),
                "use_hysteresis": self.hysteresis_check.isChecked(),
                "hysteresis": self.hysteresis_spin.value()
            }
        }


# Need to import QLabel
from PyQt6.QtWidgets import QLabel

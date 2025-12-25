"""
Timer Configuration Dialog
Supports start/stop channels, edge detection, counting modes and time limits
"""

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QSpinBox, QGridLayout,
    QLabel, QWidget
)
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, EdgeType, TimerMode


class TimerDialog(BaseChannelDialog):
    """Dialog for configuring timer channels"""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent, config, available_channels, ChannelType.TIMER, existing_channels)

        # Increase height to avoid scrollbar
        self.setMinimumHeight(520)
        self.resize(600, 540)

        self._create_trigger_group()
        self._create_settings_group()

        # Load config if editing
        if config:
            self._load_specific_config(config)

    def _create_trigger_group(self):
        """Create start/stop trigger settings group with two-column layout"""
        trigger_group = QGroupBox("Triggers")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Start channel selector (full width)
        layout.addWidget(QLabel("Start Channel: *"), row, 0)
        self.start_channel_widget, self.start_channel_edit = self._create_channel_selector(
            "Select channel that starts the timer..."
        )
        layout.addWidget(self.start_channel_widget, row, 1, 1, 3)
        row += 1

        # Start edge and Stop edge in same row
        layout.addWidget(QLabel("Start Edge:"), row, 0)
        self.start_edge_combo = self._create_edge_combo(include_both=False, include_level=True)
        layout.addWidget(self.start_edge_combo, row, 1)

        layout.addWidget(QLabel("Stop Edge:"), row, 2)
        self.stop_edge_combo = self._create_edge_combo(include_both=False, include_level=True)
        self.stop_edge_combo.setCurrentIndex(1)  # Default to Falling
        layout.addWidget(self.stop_edge_combo, row, 3)
        row += 1

        # Stop channel selector (full width)
        layout.addWidget(QLabel("Stop Channel:"), row, 0)
        self.stop_channel_widget, self.stop_channel_edit = self._create_channel_selector(
            "Select channel that stops the timer (optional)..."
        )
        layout.addWidget(self.stop_channel_widget, row, 1, 1, 3)
        row += 1

        # Info
        info = QLabel(
            "Timer starts when start edge is detected on start channel.\n"
            "If stop channel is not set, timer stops when reaching the limit."
        )
        info.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addWidget(info, row, 0, 1, 4)

        trigger_group.setLayout(layout)
        self.content_layout.addWidget(trigger_group)

    def _create_settings_group(self):
        """Create mode and limit settings group with two-column layout"""
        settings_group = QGroupBox("Settings")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Mode selection
        layout.addWidget(QLabel("Mode:"), row, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Count up", TimerMode.COUNT_UP.value)
        self.mode_combo.addItem("Count down", TimerMode.COUNT_DOWN.value)
        self.mode_combo.setToolTip(
            "Count Up: starts at 0 and counts up to limit\n"
            "Count Down: starts at limit and counts down to 0"
        )
        layout.addWidget(self.mode_combo, row, 1)
        row += 1

        # Time limit - all three spinboxes in one row
        layout.addWidget(QLabel("Time Limit:"), row, 0)

        # Container for h:m:s spinboxes
        limit_container = QWidget()
        limit_layout = QGridLayout(limit_container)
        limit_layout.setContentsMargins(0, 0, 0, 0)

        # Hours
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 999)
        self.hours_spin.setValue(0)
        self.hours_spin.setSuffix(" h")
        limit_layout.addWidget(self.hours_spin, 0, 0)

        # Minutes
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(1)
        self.minutes_spin.setSuffix(" min")
        limit_layout.addWidget(self.minutes_spin, 0, 1)

        # Seconds
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setValue(0)
        self.seconds_spin.setSuffix(" s")
        limit_layout.addWidget(self.seconds_spin, 0, 2)

        layout.addWidget(limit_container, row, 1, 1, 3)
        row += 1

        # Total seconds display
        self.total_label = QLabel("Total: 60 seconds")
        self.total_label.setStyleSheet("color: #0078d4;")
        layout.addWidget(self.total_label, row, 1, 1, 3)
        row += 1

        # Connect spinboxes to update total
        self.hours_spin.valueChanged.connect(self._update_total)
        self.minutes_spin.valueChanged.connect(self._update_total)
        self.seconds_spin.valueChanged.connect(self._update_total)

        # Info
        info = QLabel(
            "Count Up: Timer value goes 0 -> Limit\n"
            "Count Down: Timer value goes Limit -> 0"
        )
        info.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addWidget(info, row, 0, 1, 4)

        settings_group.setLayout(layout)
        self.content_layout.addWidget(settings_group)

    def _update_total(self):
        """Update total seconds display"""
        total = (
            self.hours_spin.value() * 3600 +
            self.minutes_spin.value() * 60 +
            self.seconds_spin.value()
        )

        if total >= 3600:
            hours = total // 3600
            minutes = (total % 3600) // 60
            seconds = total % 60
            self.total_label.setText(f"Total: {hours}h {minutes}m {seconds}s ({total} seconds)")
        elif total >= 60:
            minutes = total // 60
            seconds = total % 60
            self.total_label.setText(f"Total: {minutes}m {seconds}s ({total} seconds)")
        else:
            self.total_label.setText(f"Total: {total} seconds")

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        # Start channel - use helper to show channel name
        self._set_channel_edit_value(
            self.start_channel_edit,
            config.get("start_channel")
        )
        self._set_edge_combo_value(
            self.start_edge_combo,
            config.get("start_edge", "rising")
        )

        # Stop channel - use helper to show channel name
        self._set_channel_edit_value(
            self.stop_channel_edit,
            config.get("stop_channel")
        )
        self._set_edge_combo_value(
            self.stop_edge_combo,
            config.get("stop_edge", "falling")
        )

        # Mode
        mode = config.get("mode", "count_up")
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == mode:
                self.mode_combo.setCurrentIndex(i)
                break

        # Limit
        self.hours_spin.setValue(config.get("limit_hours", 0))
        self.minutes_spin.setValue(config.get("limit_minutes", 1))
        self.seconds_spin.setValue(config.get("limit_seconds", 0))

        self._update_total()

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []

        # Start channel is always required (use "one" function for auto-start)
        if not self.start_channel_edit.text().strip():
            errors.append("Start channel is required (use 'one' function for auto-start)")

        total_time = (
            self.hours_spin.value() * 3600 +
            self.minutes_spin.value() * 60 +
            self.seconds_spin.value()
        )
        if total_time == 0:
            errors.append("Time limit must be greater than 0")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()

        # Get channel IDs using helper method
        start_channel_id = self._get_channel_id_from_edit(self.start_channel_edit)
        stop_channel_id = self._get_channel_id_from_edit(self.stop_channel_edit)

        config.update({
            "start_channel": start_channel_id if start_channel_id else "",
            "start_edge": self._get_edge_combo_value(self.start_edge_combo),
            "stop_channel": stop_channel_id if stop_channel_id else "",
            "stop_edge": self._get_edge_combo_value(self.stop_edge_combo),
            "mode": self.mode_combo.currentData(),
            "limit_hours": self.hours_spin.value(),
            "limit_minutes": self.minutes_spin.value(),
            "limit_seconds": self.seconds_spin.value()
        })

        return config

"""
Filter Configuration Dialog
Signal filtering with different filter types
"""

from PyQt6.QtWidgets import (
    QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QLabel, QGridLayout
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, FilterType


class FilterDialog(BaseChannelDialog):
    """Dialog for configuring filter channels."""

    # Filter type display names
    FILTER_TYPE_NAMES = {
        FilterType.MOVING_AVG: "Moving Average",
        FilterType.LOW_PASS: "Low Pass",
        FilterType.MIN_WINDOW: "Minimum (Window)",
        FilterType.MAX_WINDOW: "Maximum (Window)",
        FilterType.MEDIAN: "Median",
    }

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None):
        super().__init__(parent, config, available_channels, ChannelType.FILTER)

        self._create_filter_group()

        # Connect filter type change
        self.filter_type_combo.currentIndexChanged.connect(self._on_filter_type_changed)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        # Initialize visibility
        self._on_filter_type_changed()

    def _create_filter_group(self):
        """Create filter settings group"""
        filter_group = QGroupBox("Filter Settings")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Input channel (full width)
        layout.addWidget(QLabel("Input Channel: *"), row, 0)
        self.input_widget, self.input_edit = self._create_channel_selector(
            "Select input channel to filter..."
        )
        layout.addWidget(self.input_widget, row, 1, 1, 3)
        row += 1

        # Filter type
        layout.addWidget(QLabel("Filter Type:"), row, 0)
        self.filter_type_combo = QComboBox()
        for ft in FilterType:
            self.filter_type_combo.addItem(self.FILTER_TYPE_NAMES[ft], ft.value)
        layout.addWidget(self.filter_type_combo, row, 1)
        row += 1

        # Window size (for moving avg, min/max window, median)
        self.window_label = QLabel("Window Size:")
        layout.addWidget(self.window_label, row, 0)
        self.window_spin = QSpinBox()
        self.window_spin.setRange(2, 100)
        self.window_spin.setValue(10)
        self.window_spin.setToolTip("Number of samples in the filter window")
        layout.addWidget(self.window_spin, row, 1)

        # Time constant (for low pass)
        self.time_const_label = QLabel("Time Constant:")
        layout.addWidget(self.time_const_label, row, 2)
        self.time_const_spin = QDoubleSpinBox()
        self.time_const_spin.setRange(0.001, 100.0)
        self.time_const_spin.setDecimals(3)
        self.time_const_spin.setValue(0.1)
        self.time_const_spin.setSuffix(" s")
        self.time_const_spin.setToolTip("Filter time constant in seconds")
        layout.addWidget(self.time_const_spin, row, 3)
        row += 1

        # Info labels
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label, row, 0, 1, 4)

        filter_group.setLayout(layout)
        self.content_layout.addWidget(filter_group)

    def _on_filter_type_changed(self):
        """Handle filter type change - show/hide relevant parameters"""
        filter_type = self.filter_type_combo.currentData()

        # Window-based filters
        is_window_filter = filter_type in [
            FilterType.MOVING_AVG.value,
            FilterType.MIN_WINDOW.value,
            FilterType.MAX_WINDOW.value,
            FilterType.MEDIAN.value
        ]

        # Low pass filter
        is_low_pass = filter_type == FilterType.LOW_PASS.value

        self.window_label.setVisible(is_window_filter)
        self.window_spin.setVisible(is_window_filter)
        self.time_const_label.setVisible(is_low_pass)
        self.time_const_spin.setVisible(is_low_pass)

        # Update info text
        info_texts = {
            FilterType.MOVING_AVG.value: "Calculates the average of the last N samples",
            FilterType.LOW_PASS.value: "First-order low-pass filter with configurable time constant",
            FilterType.MIN_WINDOW.value: "Returns the minimum value from the last N samples",
            FilterType.MAX_WINDOW.value: "Returns the maximum value from the last N samples",
            FilterType.MEDIAN.value: "Returns the median value from the last N samples (noise rejection)",
        }
        self.info_label.setText(info_texts.get(filter_type, ""))

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        # Input channel
        self.input_edit.setText(config.get("input_channel", ""))

        # Filter type
        filter_type = config.get("filter_type", "moving_avg")
        for i in range(self.filter_type_combo.count()):
            if self.filter_type_combo.itemData(i) == filter_type:
                self.filter_type_combo.setCurrentIndex(i)
                break

        # Parameters
        self.window_spin.setValue(config.get("window_size", 10))
        self.time_const_spin.setValue(config.get("time_constant", 0.1))

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []

        if not self.input_edit.text().strip():
            errors.append("Input channel is required")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()

        config.update({
            "input_channel": self.input_edit.text().strip(),
            "filter_type": self.filter_type_combo.currentData(),
            "window_size": self.window_spin.value(),
            "time_constant": self.time_const_spin.value()
        })

        return config

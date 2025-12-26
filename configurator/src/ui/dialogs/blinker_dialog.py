"""
Blinker (Turn Signal) Module Configuration Dialog
Configures turn signal and hazard light control module
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QLabel, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List
from .channel_selector_dialog import ChannelSelectorDialog
from .base_channel_dialog import get_next_channel_id
from models.channel_display_service import ChannelDisplayService


class BlinkerDialog(QDialog):
    """Dialog for configuring a Blinker (Turn Signal) control module."""

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None,
                 available_channels=None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None,
                 **kwargs):
        """Initialize BlinkerDialog.

        Args:
            parent: Parent widget
            config: Blinker configuration (for editing) or None (for creating)
            available_channels: Dict of available channels for source selection
            existing_channels: List of existing channel configs
            **kwargs: Additional arguments:
                - blinker_config: Alias for config (backwards compatibility)
        """
        super().__init__(parent)
        # Handle backwards compatibility aliases
        if config is None:
            config = kwargs.get('blinker_config')
        self.config = config
        self.available_channels = available_channels or {}
        self.existing_channels = existing_channels or []

        # Determine if editing existing or creating new
        self.is_edit_mode = bool(config and config.get("channel_id") is not None)

        # Store or generate channel_id
        if self.is_edit_mode:
            self._channel_id = config.get("channel_id", 0)
        else:
            self._channel_id = get_next_channel_id(existing_channels)

        self.setWindowTitle("Edit Blinker Module" if self.is_edit_mode else "New Blinker Module")
        self.setModal(True)
        self.resize(550, 550)

        self._init_ui()

        if config:
            self._load_config(config)
        else:
            self._auto_generate_name()

    def _auto_generate_name(self):
        """Auto-generate name for new Blinker."""
        self.name_edit.setText(f"Blinker {self._channel_id}")

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Create tab widget
        tabs = QTabWidget()

        # Basic tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.addWidget(self._create_basic_group())
        basic_layout.addWidget(self._create_io_group())
        basic_layout.addStretch()
        tabs.addTab(basic_tab, "Basic")

        # Timing tab
        timing_tab = QWidget()
        timing_layout = QVBoxLayout(timing_tab)
        timing_layout.addWidget(self._create_timing_group())
        timing_layout.addWidget(self._create_lane_change_group())
        timing_layout.addWidget(self._create_options_group())
        timing_layout.addStretch()
        tabs.addTab(timing_tab, "Timing")

        layout.addWidget(tabs)

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

    def _create_basic_group(self) -> QGroupBox:
        """Create basic settings group."""
        group = QGroupBox("Basic Settings")
        layout = QFormLayout()

        # Channel ID (read-only)
        self.channel_id_label = QLabel(str(self._channel_id))
        self.channel_id_label.setStyleSheet("font-weight: bold; color: #b0b0b0;")
        layout.addRow("Channel ID:", self.channel_id_label)

        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Turn Signals, Indicators")
        layout.addRow("Name: *", self.name_edit)

        # Enabled
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        layout.addRow("", self.enabled_check)

        group.setLayout(layout)
        return group

    def _create_io_group(self) -> QGroupBox:
        """Create inputs/outputs group."""
        group = QGroupBox("Inputs / Outputs")
        layout = QGridLayout()

        # Left input
        layout.addWidget(QLabel("Left Input:"), 0, 0)
        left_in_layout = QHBoxLayout()
        self.left_channel_edit = QLineEdit()
        self.left_channel_edit.setPlaceholderText("Select input channel...")
        self.left_channel_edit.setReadOnly(True)
        left_in_layout.addWidget(self.left_channel_edit, stretch=1)
        self.left_channel_btn = QPushButton("...")
        self.left_channel_btn.setMaximumWidth(30)
        self.left_channel_btn.clicked.connect(self._browse_left_channel)
        left_in_layout.addWidget(self.left_channel_btn)
        layout.addLayout(left_in_layout, 0, 1)

        # Left output
        layout.addWidget(QLabel("Left Output:"), 0, 2)
        left_out_layout = QHBoxLayout()
        self.left_output_edit = QLineEdit()
        self.left_output_edit.setPlaceholderText("Select output channel...")
        self.left_output_edit.setReadOnly(True)
        left_out_layout.addWidget(self.left_output_edit, stretch=1)
        self.left_output_btn = QPushButton("...")
        self.left_output_btn.setMaximumWidth(30)
        self.left_output_btn.clicked.connect(self._browse_left_output)
        left_out_layout.addWidget(self.left_output_btn)
        layout.addLayout(left_out_layout, 0, 3)

        # Right input
        layout.addWidget(QLabel("Right Input:"), 1, 0)
        right_in_layout = QHBoxLayout()
        self.right_channel_edit = QLineEdit()
        self.right_channel_edit.setPlaceholderText("Select input channel...")
        self.right_channel_edit.setReadOnly(True)
        right_in_layout.addWidget(self.right_channel_edit, stretch=1)
        self.right_channel_btn = QPushButton("...")
        self.right_channel_btn.setMaximumWidth(30)
        self.right_channel_btn.clicked.connect(self._browse_right_channel)
        right_in_layout.addWidget(self.right_channel_btn)
        layout.addLayout(right_in_layout, 1, 1)

        # Right output
        layout.addWidget(QLabel("Right Output:"), 1, 2)
        right_out_layout = QHBoxLayout()
        self.right_output_edit = QLineEdit()
        self.right_output_edit.setPlaceholderText("Select output channel...")
        self.right_output_edit.setReadOnly(True)
        right_out_layout.addWidget(self.right_output_edit, stretch=1)
        self.right_output_btn = QPushButton("...")
        self.right_output_btn.setMaximumWidth(30)
        self.right_output_btn.clicked.connect(self._browse_right_output)
        right_out_layout.addWidget(self.right_output_btn)
        layout.addLayout(right_out_layout, 1, 3)

        # Hazard input
        layout.addWidget(QLabel("Hazard Input:"), 2, 0)
        hazard_layout = QHBoxLayout()
        self.hazard_channel_edit = QLineEdit()
        self.hazard_channel_edit.setPlaceholderText("Select hazard button...")
        self.hazard_channel_edit.setReadOnly(True)
        hazard_layout.addWidget(self.hazard_channel_edit, stretch=1)
        self.hazard_channel_btn = QPushButton("...")
        self.hazard_channel_btn.setMaximumWidth(30)
        self.hazard_channel_btn.clicked.connect(self._browse_hazard_channel)
        hazard_layout.addWidget(self.hazard_channel_btn)
        layout.addLayout(hazard_layout, 2, 1, 1, 3)

        # Trailer outputs (optional)
        layout.addWidget(QLabel("Left Trailer:"), 3, 0)
        left_trailer_layout = QHBoxLayout()
        self.left_trailer_edit = QLineEdit()
        self.left_trailer_edit.setPlaceholderText("Optional...")
        self.left_trailer_edit.setReadOnly(True)
        left_trailer_layout.addWidget(self.left_trailer_edit, stretch=1)
        self.left_trailer_btn = QPushButton("...")
        self.left_trailer_btn.setMaximumWidth(30)
        self.left_trailer_btn.clicked.connect(self._browse_left_trailer)
        left_trailer_layout.addWidget(self.left_trailer_btn)
        layout.addLayout(left_trailer_layout, 3, 1)

        layout.addWidget(QLabel("Right Trailer:"), 3, 2)
        right_trailer_layout = QHBoxLayout()
        self.right_trailer_edit = QLineEdit()
        self.right_trailer_edit.setPlaceholderText("Optional...")
        self.right_trailer_edit.setReadOnly(True)
        right_trailer_layout.addWidget(self.right_trailer_edit, stretch=1)
        self.right_trailer_btn = QPushButton("...")
        self.right_trailer_btn.setMaximumWidth(30)
        self.right_trailer_btn.clicked.connect(self._browse_right_trailer)
        right_trailer_layout.addWidget(self.right_trailer_btn)
        layout.addLayout(right_trailer_layout, 3, 3)

        group.setLayout(layout)
        return group

    def _create_timing_group(self) -> QGroupBox:
        """Create flash timing group."""
        group = QGroupBox("Flash Timing")
        layout = QGridLayout()

        # Flash ON time
        layout.addWidget(QLabel("Flash ON:"), 0, 0)
        self.flash_on_spin = QSpinBox()
        self.flash_on_spin.setRange(100, 2000)
        self.flash_on_spin.setValue(500)
        self.flash_on_spin.setSuffix(" ms")
        layout.addWidget(self.flash_on_spin, 0, 1)

        # Flash OFF time
        layout.addWidget(QLabel("Flash OFF:"), 0, 2)
        self.flash_off_spin = QSpinBox()
        self.flash_off_spin.setRange(100, 2000)
        self.flash_off_spin.setValue(500)
        self.flash_off_spin.setSuffix(" ms")
        layout.addWidget(self.flash_off_spin, 0, 3)

        # Flash rate (Hz)
        layout.addWidget(QLabel("Flash Rate:"), 1, 0)
        self.flash_rate_spin = QDoubleSpinBox()
        self.flash_rate_spin.setRange(0.5, 5.0)
        self.flash_rate_spin.setValue(1.0)
        self.flash_rate_spin.setSuffix(" Hz")
        self.flash_rate_spin.setDecimals(1)
        layout.addWidget(self.flash_rate_spin, 1, 1)

        # Fast flash rate (bulb out)
        layout.addWidget(QLabel("Fast Flash:"), 1, 2)
        self.fast_flash_spin = QDoubleSpinBox()
        self.fast_flash_spin.setRange(1.0, 10.0)
        self.fast_flash_spin.setValue(2.0)
        self.fast_flash_spin.setSuffix(" Hz")
        self.fast_flash_spin.setDecimals(1)
        self.fast_flash_spin.setToolTip("Fast flash rate for bulb-out detection")
        layout.addWidget(self.fast_flash_spin, 1, 3)

        group.setLayout(layout)
        return group

    def _create_lane_change_group(self) -> QGroupBox:
        """Create lane change tap settings."""
        group = QGroupBox("Lane Change Tap")
        layout = QGridLayout()

        # Enable lane change
        self.lane_change_check = QCheckBox("Enable lane change tap")
        self.lane_change_check.setChecked(True)
        self.lane_change_check.toggled.connect(self._on_lane_change_toggled)
        layout.addWidget(self.lane_change_check, 0, 0, 1, 4)

        # Number of flashes
        layout.addWidget(QLabel("Flash Count:"), 1, 0)
        self.lane_change_flashes_spin = QSpinBox()
        self.lane_change_flashes_spin.setRange(1, 10)
        self.lane_change_flashes_spin.setValue(3)
        layout.addWidget(self.lane_change_flashes_spin, 1, 1)

        # Tap timeout
        layout.addWidget(QLabel("Tap Timeout:"), 1, 2)
        self.lane_change_timeout_spin = QSpinBox()
        self.lane_change_timeout_spin.setRange(100, 2000)
        self.lane_change_timeout_spin.setValue(400)
        self.lane_change_timeout_spin.setSuffix(" ms")
        self.lane_change_timeout_spin.setToolTip("Max time for tap detection")
        layout.addWidget(self.lane_change_timeout_spin, 1, 3)

        group.setLayout(layout)
        return group

    def _create_options_group(self) -> QGroupBox:
        """Create options group."""
        group = QGroupBox("Options")
        layout = QVBoxLayout()

        # Hazard priority
        self.hazard_priority_check = QCheckBox("Hazard overrides turn signals")
        self.hazard_priority_check.setChecked(True)
        layout.addWidget(self.hazard_priority_check)

        # Fast flash on bulb out
        self.fast_flash_bulb_check = QCheckBox("Fast flash on bulb out")
        self.fast_flash_bulb_check.setChecked(True)
        layout.addWidget(self.fast_flash_bulb_check)

        # Output mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Output Mode:"))
        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItem("Toggle (Latching)", "toggle")
        self.output_mode_combo.addItem("Momentary", "momentary")
        mode_layout.addWidget(self.output_mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        group.setLayout(layout)
        return group

    def _on_lane_change_toggled(self, enabled):
        """Handle lane change enable toggle."""
        self.lane_change_flashes_spin.setEnabled(enabled)
        self.lane_change_timeout_spin.setEnabled(enabled)

    # Channel helper method
    def _get_channel_display_name(self, channel_id) -> str:
        """Get display name for a channel using central lookup."""
        return ChannelDisplayService.get_display_name(channel_id, self.available_channels)

    # Channel browser methods
    def _browse_left_channel(self):
        current = self.left_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.left_channel_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_right_channel(self):
        current = self.right_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.right_channel_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_hazard_channel(self):
        current = self.hazard_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.hazard_channel_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_left_output(self):
        current = self.left_output_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.left_output_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_right_output(self):
        current = self.right_output_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.right_output_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_left_trailer(self):
        current = self.left_trailer_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.left_trailer_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_right_trailer(self):
        current = self.right_trailer_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.right_trailer_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))
        self.enabled_check.setChecked(config.get("enabled", True))

        # I/O channels - convert channel IDs to display names
        self.left_channel_edit.setText(self._get_channel_display_name(config.get("left_channel", "")))
        self.right_channel_edit.setText(self._get_channel_display_name(config.get("right_channel", "")))
        self.hazard_channel_edit.setText(self._get_channel_display_name(config.get("hazard_channel", "")))
        self.left_output_edit.setText(self._get_channel_display_name(config.get("left_output", "")))
        self.right_output_edit.setText(self._get_channel_display_name(config.get("right_output", "")))
        self.left_trailer_edit.setText(self._get_channel_display_name(config.get("left_trailer_output", "")))
        self.right_trailer_edit.setText(self._get_channel_display_name(config.get("right_trailer_output", "")))


        # Timing
        self.flash_on_spin.setValue(config.get("flash_on_ms", 500))
        self.flash_off_spin.setValue(config.get("flash_off_ms", 500))
        self.flash_rate_spin.setValue(config.get("flash_rate_hz", 1.0))
        self.fast_flash_spin.setValue(config.get("fast_flash_rate_hz", 2.0))

        # Lane change
        self.lane_change_check.setChecked(config.get("lane_change_enabled", True))
        self.lane_change_flashes_spin.setValue(config.get("lane_change_flashes", 3))
        self.lane_change_timeout_spin.setValue(config.get("lane_change_timeout_ms", 400))

        # Options
        self.hazard_priority_check.setChecked(config.get("hazard_priority", True))
        self.fast_flash_bulb_check.setChecked(config.get("fast_flash_on_bulb_out", True))
        mode = config.get("output_mode", "toggle")
        index = self.output_mode_combo.findData(mode)
        if index >= 0:
            self.output_mode_combo.setCurrentIndex(index)

        # Update control states
        self._on_lane_change_toggled(self.lane_change_check.isChecked())

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        return {
            "channel_id": self._channel_id,
            "channel_type": "blinker",
            "name": self.name_edit.text().strip(),
            "enabled": self.enabled_check.isChecked(),

            # I/O channels
            "left_channel": self.left_channel_edit.text(),
            "right_channel": self.right_channel_edit.text(),
            "hazard_channel": self.hazard_channel_edit.text(),
            "left_output": self.left_output_edit.text(),
            "right_output": self.right_output_edit.text(),
            "left_trailer_output": self.left_trailer_edit.text(),
            "right_trailer_output": self.right_trailer_edit.text(),

            # Timing
            "flash_on_ms": self.flash_on_spin.value(),
            "flash_off_ms": self.flash_off_spin.value(),
            "flash_rate_hz": self.flash_rate_spin.value(),
            "fast_flash_rate_hz": self.fast_flash_spin.value(),

            # Lane change
            "lane_change_enabled": self.lane_change_check.isChecked(),
            "lane_change_flashes": self.lane_change_flashes_spin.value(),
            "lane_change_timeout_ms": self.lane_change_timeout_spin.value(),

            # Options
            "hazard_priority": self.hazard_priority_check.isChecked(),
            "fast_flash_on_bulb_out": self.fast_flash_bulb_check.isChecked(),
            "output_mode": self.output_mode_combo.currentData(),
        }

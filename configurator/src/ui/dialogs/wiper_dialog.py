"""
Wiper Module Configuration Dialog
Configures windshield wiper control module
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QSpinBox, QLabel,
    QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List
from .channel_selector_dialog import ChannelSelectorDialog
from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType
from models.channel_display_service import ChannelDisplayService


class WiperDialog(BaseChannelDialog):
    """Dialog for configuring a Wiper control module."""

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None,
                 available_channels=None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None,
                 **kwargs):
        """Initialize WiperDialog.

        Args:
            parent: Parent widget
            config: Wiper configuration (for editing) or None (for creating)
            available_channels: Dict of available channels for source selection
            existing_channels: List of existing channel configs
            **kwargs: Additional arguments:
                - used_numbers: List of already used wiper numbers
                - wiper_config: Alias for config (backwards compatibility)
                - used_bridges: Alias for used_numbers (backwards compatibility)
        """
        # Handle backwards compatibility aliases
        if config is None:
            config = kwargs.get('wiper_config')

        # Store used_numbers before super().__init__
        self.used_numbers = kwargs.get('used_numbers') or kwargs.get('used_bridges') or []
        self._config_for_bridge = config

        # Initialize base class (creates Basic Settings with name, channel_id, enabled)
        super().__init__(parent, config, available_channels, ChannelType.WIPER, existing_channels)

        self.resize(550, 500)

        # Create Wiper specific UI
        self._create_wiper_ui()

        if config:
            self._load_specific_config(config)

    def _create_wiper_ui(self):
        """Create Wiper specific UI components."""
        # Create tabs for organized settings
        tabs = QTabWidget()

        # Basic tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.addWidget(self._create_bridge_group())
        basic_layout.addWidget(self._create_inputs_group())
        basic_layout.addStretch()
        tabs.addTab(basic_tab, "Basic")

        # Speed & Timing tab
        speed_tab = QWidget()
        speed_layout = QVBoxLayout(speed_tab)
        speed_layout.addWidget(self._create_speed_group())
        speed_layout.addWidget(self._create_intermittent_group())
        speed_layout.addWidget(self._create_wash_group())
        speed_layout.addStretch()
        tabs.addTab(speed_tab, "Speed & Timing")

        # Add tabs to base class content_layout
        self.content_layout.addWidget(tabs)

    def _create_bridge_group(self) -> QGroupBox:
        """Create H-Bridge selection group."""
        group = QGroupBox("H-Bridge Settings")
        layout = QFormLayout()

        # H-Bridge Number
        bridge_layout = QHBoxLayout()
        self.bridge_combo = QComboBox()
        self._populate_bridge_combo()
        bridge_layout.addWidget(self.bridge_combo)
        bridge_layout.addStretch()
        layout.addRow("H-Bridge:", bridge_layout)

        group.setLayout(layout)
        return group

    def _create_inputs_group(self) -> QGroupBox:
        """Create control inputs group."""
        group = QGroupBox("Control Inputs")
        layout = QGridLayout()

        # Control channel (wiper switch)
        layout.addWidget(QLabel("Wiper Switch:"), 0, 0)
        ctrl_layout = QHBoxLayout()
        self.control_channel_edit = QLineEdit()
        self.control_channel_edit.setPlaceholderText("Select switch channel...")
        self.control_channel_edit.setReadOnly(True)
        ctrl_layout.addWidget(self.control_channel_edit, stretch=1)
        self.control_channel_btn = QPushButton("...")
        self.control_channel_btn.setMaximumWidth(30)
        self.control_channel_btn.clicked.connect(self._browse_control_channel)
        ctrl_layout.addWidget(self.control_channel_btn)
        layout.addLayout(ctrl_layout, 0, 1)

        # Wash channel
        layout.addWidget(QLabel("Wash Button:"), 1, 0)
        wash_layout = QHBoxLayout()
        self.wash_channel_edit = QLineEdit()
        self.wash_channel_edit.setPlaceholderText("Optional...")
        self.wash_channel_edit.setReadOnly(True)
        wash_layout.addWidget(self.wash_channel_edit, stretch=1)
        self.wash_channel_btn = QPushButton("...")
        self.wash_channel_btn.setMaximumWidth(30)
        self.wash_channel_btn.clicked.connect(self._browse_wash_channel)
        wash_layout.addWidget(self.wash_channel_btn)
        layout.addLayout(wash_layout, 1, 1)

        # Park sensor
        layout.addWidget(QLabel("Park Sensor:"), 2, 0)
        park_layout = QHBoxLayout()
        self.park_channel_edit = QLineEdit()
        self.park_channel_edit.setPlaceholderText("Optional...")
        self.park_channel_edit.setReadOnly(True)
        park_layout.addWidget(self.park_channel_edit, stretch=1)
        self.park_channel_btn = QPushButton("...")
        self.park_channel_btn.setMaximumWidth(30)
        self.park_channel_btn.clicked.connect(self._browse_park_channel)
        park_layout.addWidget(self.park_channel_btn)
        layout.addLayout(park_layout, 2, 1)

        # Rain sensor
        layout.addWidget(QLabel("Rain Sensor:"), 3, 0)
        rain_layout = QHBoxLayout()
        self.rain_sensor_edit = QLineEdit()
        self.rain_sensor_edit.setPlaceholderText("Optional...")
        self.rain_sensor_edit.setReadOnly(True)
        rain_layout.addWidget(self.rain_sensor_edit, stretch=1)
        self.rain_sensor_btn = QPushButton("...")
        self.rain_sensor_btn.setMaximumWidth(30)
        self.rain_sensor_btn.clicked.connect(self._browse_rain_sensor)
        rain_layout.addWidget(self.rain_sensor_btn)
        layout.addLayout(rain_layout, 3, 1)

        group.setLayout(layout)
        return group

    def _create_speed_group(self) -> QGroupBox:
        """Create speed settings group."""
        group = QGroupBox("Speed Settings")
        layout = QFormLayout()

        # Slow PWM
        self.slow_pwm_spin = QSpinBox()
        self.slow_pwm_spin.setRange(0, 255)
        self.slow_pwm_spin.setValue(180)
        self.slow_pwm_spin.setToolTip("PWM value for slow speed (0-255)")
        layout.addRow("Slow Speed PWM:", self.slow_pwm_spin)

        # Fast PWM
        self.fast_pwm_spin = QSpinBox()
        self.fast_pwm_spin.setRange(0, 255)
        self.fast_pwm_spin.setValue(255)
        self.fast_pwm_spin.setToolTip("PWM value for fast speed (0-255)")
        layout.addRow("Fast Speed PWM:", self.fast_pwm_spin)

        # Park position
        self.park_position_spin = QSpinBox()
        self.park_position_spin.setRange(0, 100)
        self.park_position_spin.setValue(50)
        self.park_position_spin.setSuffix(" %")
        self.park_position_spin.setToolTip("Park position sensor threshold")
        layout.addRow("Park Position:", self.park_position_spin)

        # Park timeout
        self.park_timeout_spin = QSpinBox()
        self.park_timeout_spin.setRange(1000, 30000)
        self.park_timeout_spin.setValue(5000)
        self.park_timeout_spin.setSuffix(" ms")
        self.park_timeout_spin.setToolTip("Maximum time to reach park position")
        layout.addRow("Park Timeout:", self.park_timeout_spin)

        # Auto wipe on start
        self.auto_wipe_check = QCheckBox("Single wipe on ignition")
        layout.addRow("", self.auto_wipe_check)

        group.setLayout(layout)
        return group

    def _create_intermittent_group(self) -> QGroupBox:
        """Create intermittent mode settings."""
        group = QGroupBox("Intermittent Mode")
        layout = QGridLayout()

        # Min delay
        layout.addWidget(QLabel("Min Delay:"), 0, 0)
        self.int_min_spin = QSpinBox()
        self.int_min_spin.setRange(500, 30000)
        self.int_min_spin.setValue(1000)
        self.int_min_spin.setSuffix(" ms")
        layout.addWidget(self.int_min_spin, 0, 1)

        # Max delay
        layout.addWidget(QLabel("Max Delay:"), 0, 2)
        self.int_max_spin = QSpinBox()
        self.int_max_spin.setRange(1000, 60000)
        self.int_max_spin.setValue(10000)
        self.int_max_spin.setSuffix(" ms")
        layout.addWidget(self.int_max_spin, 0, 3)

        # Variable delay channel
        layout.addWidget(QLabel("Delay Control:"), 1, 0)
        delay_layout = QHBoxLayout()
        self.delay_channel_edit = QLineEdit()
        self.delay_channel_edit.setPlaceholderText("Optional - analog for variable delay...")
        self.delay_channel_edit.setReadOnly(True)
        delay_layout.addWidget(self.delay_channel_edit, stretch=1)
        self.delay_channel_btn = QPushButton("...")
        self.delay_channel_btn.setMaximumWidth(30)
        self.delay_channel_btn.clicked.connect(self._browse_delay_channel)
        delay_layout.addWidget(self.delay_channel_btn)
        layout.addLayout(delay_layout, 1, 1, 1, 3)

        group.setLayout(layout)
        return group

    def _create_wash_group(self) -> QGroupBox:
        """Create wash and wipe coordination settings."""
        group = QGroupBox("Wash & Wipe")
        layout = QFormLayout()

        # Wipes after wash
        self.wash_wipe_count_spin = QSpinBox()
        self.wash_wipe_count_spin.setRange(0, 10)
        self.wash_wipe_count_spin.setValue(3)
        self.wash_wipe_count_spin.setToolTip("Number of wipes after wash button released")
        layout.addRow("Wipes After Wash:", self.wash_wipe_count_spin)

        # Delay after wash
        self.wash_delay_spin = QSpinBox()
        self.wash_delay_spin.setRange(0, 5000)
        self.wash_delay_spin.setValue(500)
        self.wash_delay_spin.setSuffix(" ms")
        self.wash_delay_spin.setToolTip("Delay after wash before wiping")
        layout.addRow("Delay After Wash:", self.wash_delay_spin)

        group.setLayout(layout)
        return group

    def _populate_bridge_combo(self):
        """Populate H-Bridge dropdown with available bridges."""
        self.bridge_combo.clear()

        # Get current bridge if editing
        current_bridge = None
        if self._config_for_bridge:
            current_bridge = self._config_for_bridge.get("hbridge_number")

        # Add available bridges (HB1-HB4)
        for bridge in range(4):
            if bridge not in self.used_numbers or bridge == current_bridge:
                self.bridge_combo.addItem(f"HB{bridge + 1}", bridge)

        if self.bridge_combo.count() == 0:
            self.bridge_combo.addItem("No bridges available", -1)

    # Channel helper method
    def _get_channel_display_name(self, channel_id) -> str:
        """Get display name for a channel using central lookup."""
        return ChannelDisplayService.get_display_name(channel_id, self.available_channels)

    def _browse_control_channel(self):
        current = self.control_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.control_channel_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_wash_channel(self):
        current = self.wash_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.wash_channel_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_park_channel(self):
        current = self.park_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.park_channel_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_rain_sensor(self):
        current = self.rain_sensor_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.rain_sensor_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _browse_delay_channel(self):
        current = self.delay_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.delay_channel_edit.setText(self._get_channel_display_name(channel) if channel else "")

    def _validate_specific(self) -> list:
        """Validate Wiper specific fields."""
        errors = []

        # Validate bridge selection
        bridge = self.bridge_combo.currentData()
        if bridge is None or bridge < 0:
            errors.append("Please select an H-Bridge")

        return errors

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load Wiper specific configuration."""
        # Bridge number
        bridge = config.get("hbridge_number", 0)
        index = self.bridge_combo.findData(bridge)
        if index >= 0:
            self.bridge_combo.setCurrentIndex(index)

        # Input channels - convert channel IDs to display names
        self.control_channel_edit.setText(self._get_channel_display_name(config.get("control_channel", "")))
        self.wash_channel_edit.setText(self._get_channel_display_name(config.get("wash_channel", "")))
        self.park_channel_edit.setText(self._get_channel_display_name(config.get("park_channel", "")))
        self.rain_sensor_edit.setText(self._get_channel_display_name(config.get("rain_sensor_channel", "")))

        # Speed settings
        self.slow_pwm_spin.setValue(config.get("slow_pwm", 180))
        self.fast_pwm_spin.setValue(config.get("fast_pwm", 255))
        self.park_position_spin.setValue(config.get("park_position", 50))
        self.park_timeout_spin.setValue(config.get("park_timeout_ms", 5000))
        self.auto_wipe_check.setChecked(config.get("auto_wipe_on_start", False))

        # Intermittent
        self.int_min_spin.setValue(config.get("intermittent_min_ms", 1000))
        self.int_max_spin.setValue(config.get("intermittent_max_ms", 10000))
        self.delay_channel_edit.setText(self._get_channel_display_name(config.get("intermittent_delay_channel", "")))

        # Wash
        self.wash_wipe_count_spin.setValue(config.get("wash_wipe_count", 3))
        self.wash_delay_spin.setValue(config.get("wash_wipe_delay_ms", 500))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        # Get base config (channel_id, name, enabled, channel_type)
        config = self.get_base_config()

        # Add Wiper specific fields
        config.update({
            "hbridge_number": self.bridge_combo.currentData(),
            "output_speed": "",  # Reserved for future use

            # Input channels
            "control_channel": self.control_channel_edit.text(),
            "wash_channel": self.wash_channel_edit.text(),
            "park_channel": self.park_channel_edit.text(),
            "rain_sensor_channel": self.rain_sensor_edit.text(),

            # Speed settings
            "slow_pwm": self.slow_pwm_spin.value(),
            "fast_pwm": self.fast_pwm_spin.value(),
            "park_position": self.park_position_spin.value(),
            "park_timeout_ms": self.park_timeout_spin.value(),
            "auto_wipe_on_start": self.auto_wipe_check.isChecked(),

            # Intermittent
            "intermittent_min_ms": self.int_min_spin.value(),
            "intermittent_max_ms": self.int_max_spin.value(),
            "intermittent_delay_channel": self.delay_channel_edit.text(),

            # Wash
            "wash_wipe_count": self.wash_wipe_count_spin.value(),
            "wash_wipe_delay_ms": self.wash_delay_spin.value(),
        })

        return config

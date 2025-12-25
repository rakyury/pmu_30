"""
Wiper Module Configuration Dialog
Configures windshield wiper control module
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QSpinBox, QLabel,
    QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List
from .channel_selector_dialog import ChannelSelectorDialog
from .base_channel_dialog import get_next_channel_id


class WiperDialog(QDialog):
    """Dialog for configuring a Wiper control module."""

    def __init__(self, parent=None, wiper_config: Optional[Dict[str, Any]] = None,
                 used_bridges=None, available_channels=None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.wiper_config = wiper_config
        self.used_bridges = used_bridges or []
        self.available_channels = available_channels or {}
        self.existing_channels = existing_channels or []

        # Determine if editing existing or creating new
        self.is_edit_mode = bool(wiper_config and wiper_config.get("channel_id") is not None)

        # Store or generate channel_id
        if self.is_edit_mode:
            self._channel_id = wiper_config.get("channel_id", 0)
        else:
            self._channel_id = get_next_channel_id(existing_channels)

        self.setWindowTitle("Edit Wiper Module" if self.is_edit_mode else "New Wiper Module")
        self.setModal(True)
        self.resize(550, 500)

        self._init_ui()

        if wiper_config:
            self._load_config(wiper_config)
        else:
            self._auto_generate_name()

    def _auto_generate_name(self):
        """Auto-generate name for new Wiper."""
        self.name_edit.setText(f"Wiper {self._channel_id}")

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Create tab widget
        tabs = QTabWidget()

        # Basic tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.addWidget(self._create_basic_group())
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
        self.name_edit.setPlaceholderText("e.g., Front Wipers, Rear Wiper")
        layout.addRow("Name: *", self.name_edit)

        # H-Bridge Number
        bridge_layout = QHBoxLayout()
        self.bridge_combo = QComboBox()
        self._populate_bridge_combo()
        bridge_layout.addWidget(self.bridge_combo)
        bridge_layout.addStretch()
        layout.addRow("H-Bridge:", bridge_layout)

        # Enabled
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        layout.addRow("", self.enabled_check)

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
        if self.wiper_config:
            current_bridge = self.wiper_config.get("hbridge_number")

        # Add available bridges (HB1-HB4)
        for bridge in range(4):
            if bridge not in self.used_bridges or bridge == current_bridge:
                self.bridge_combo.addItem(f"HB{bridge + 1}", bridge)

        if self.bridge_combo.count() == 0:
            self.bridge_combo.addItem("No bridges available", -1)

    def _browse_control_channel(self):
        current = self.control_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.control_channel_edit.setText(channel if channel else "")

    def _browse_wash_channel(self):
        current = self.wash_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.wash_channel_edit.setText(channel if channel else "")

    def _browse_park_channel(self):
        current = self.park_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.park_channel_edit.setText(channel if channel else "")

    def _browse_rain_sensor(self):
        current = self.rain_sensor_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.rain_sensor_edit.setText(channel if channel else "")

    def _browse_delay_channel(self):
        current = self.delay_channel_edit.text()
        accepted, channel = ChannelSelectorDialog.select_channel(self, current, self.available_channels)
        if accepted:
            self.delay_channel_edit.setText(channel if channel else "")

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        # Validate bridge selection
        bridge = self.bridge_combo.currentData()
        if bridge is None or bridge < 0:
            QMessageBox.warning(self, "Validation Error", "Please select an H-Bridge!")
            self.bridge_combo.setFocus()
            return

        self.accept()

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))
        self.enabled_check.setChecked(config.get("enabled", True))

        # Bridge number
        bridge = config.get("hbridge_number", 0)
        index = self.bridge_combo.findData(bridge)
        if index >= 0:
            self.bridge_combo.setCurrentIndex(index)

        # Input channels
        self.control_channel_edit.setText(config.get("control_channel", ""))
        self.wash_channel_edit.setText(config.get("wash_channel", ""))
        self.park_channel_edit.setText(config.get("park_channel", ""))
        self.rain_sensor_edit.setText(config.get("rain_sensor_channel", ""))

        # Speed settings
        self.slow_pwm_spin.setValue(config.get("slow_pwm", 180))
        self.fast_pwm_spin.setValue(config.get("fast_pwm", 255))
        self.park_position_spin.setValue(config.get("park_position", 50))
        self.park_timeout_spin.setValue(config.get("park_timeout_ms", 5000))
        self.auto_wipe_check.setChecked(config.get("auto_wipe_on_start", False))

        # Intermittent
        self.int_min_spin.setValue(config.get("intermittent_min_ms", 1000))
        self.int_max_spin.setValue(config.get("intermittent_max_ms", 10000))
        self.delay_channel_edit.setText(config.get("intermittent_delay_channel", ""))

        # Wash
        self.wash_wipe_count_spin.setValue(config.get("wash_wipe_count", 3))
        self.wash_delay_spin.setValue(config.get("wash_wipe_delay_ms", 500))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        return {
            "channel_id": self._channel_id,
            "channel_type": "wiper",
            "name": self.name_edit.text().strip(),
            "enabled": self.enabled_check.isChecked(),
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
        }

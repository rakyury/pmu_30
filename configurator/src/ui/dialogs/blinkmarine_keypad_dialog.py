"""
BlinkMarine CAN Keypad Configuration Dialog (CANopen Protocol)

Supports PKP-2600-SI (2x6) and PKP-2800-SI (2x8) CAN keypads from BlinkMarine.

CANopen Communication:
- TPDO1 (0x180 + NodeID): Button states from keypad
- RPDO1 (0x200 + NodeID): LED control to keypad
- Heartbeat (0x700 + NodeID): Node monitoring
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QComboBox, QSpinBox, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QTabWidget, QWidget, QGridLayout, QMessageBox, QSlider
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Dict, Any, Optional, List


class BlinkMarineKeypadDialog(QDialog):
    """Dialog for configuring BlinkMarine CAN keypads (CANopen)."""

    # Keypad types
    KEYPAD_PKP2600SI = 0  # 12 buttons (2x6)
    KEYPAD_PKP2800SI = 1  # 16 buttons (2x8)

    KEYPAD_LAYOUTS = {
        KEYPAD_PKP2600SI: (2, 6),
        KEYPAD_PKP2800SI: (2, 8),
    }

    # LED colors
    LED_COLORS = [
        ("Off", 0),
        ("Red", 1),
        ("Green", 2),
        ("Blue", 3),
        ("Yellow", 4),
        ("Cyan", 5),
        ("Magenta", 6),
        ("White", 7),
    ]

    # LED control modes
    LED_CTRL_MODES = [
        ("Off (LED always off)", 0),
        ("Follow Button", 1),
        ("Channel Controlled", 2),
        ("Toggle on Press", 3),
    ]

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.config = config or {}
        self.available_channels = available_channels or {}
        self.existing_channels = existing_channels or []
        self.button_configs = {}

        self._init_ui()

        if config:
            self._load_config(config)

    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("BlinkMarine CAN Keypad (CANopen)")
        self.setModal(True)
        self.setMinimumSize(700, 600)
        self.resize(800, 700)

        layout = QVBoxLayout(self)

        # Create tabs
        self.tabs = QTabWidget()

        general_tab = self._create_general_tab()
        self.tabs.addTab(general_tab, "General")

        buttons_tab = self._create_buttons_tab()
        self.tabs.addTab(buttons_tab, "Buttons")

        led_tab = self._create_led_tab()
        self.tabs.addTab(led_tab, "LED Control")

        layout.addWidget(self.tabs)

        # Dialog buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Keypad Identity
        identity_group = QGroupBox("Keypad Identity")
        identity_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., SteeringKeypad, DashKeypad")
        identity_layout.addRow("Name: *", self.name_edit)

        self.keypad_type_combo = QComboBox()
        self.keypad_type_combo.addItems([
            "PKP-2600-SI (12 buttons, 2x6)",
            "PKP-2800-SI (16 buttons, 2x8)"
        ])
        self.keypad_type_combo.currentIndexChanged.connect(self._on_type_changed)
        identity_layout.addRow("Model:", self.keypad_type_combo)

        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        identity_layout.addRow("", self.enabled_check)

        identity_group.setLayout(identity_layout)
        layout.addWidget(identity_group)

        # CANopen Configuration
        can_group = QGroupBox("CANopen Configuration")
        can_layout = QFormLayout()

        self.can_bus_combo = QComboBox()
        self.can_bus_combo.addItems(["CAN 1", "CAN 2", "CAN 3", "CAN 4"])
        can_layout.addRow("CAN Bus:", self.can_bus_combo)

        # Node ID (1-127)
        node_layout = QHBoxLayout()
        self.node_id_spin = QSpinBox()
        self.node_id_spin.setRange(1, 127)
        self.node_id_spin.setValue(1)
        node_layout.addWidget(self.node_id_spin)
        node_layout.addWidget(QLabel("(CANopen Node ID, 1-127)"))
        node_layout.addStretch()
        can_layout.addRow("Node ID:", node_layout)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 30000)
        self.timeout_spin.setValue(1000)
        self.timeout_spin.setSuffix(" ms")
        can_layout.addRow("Timeout:", self.timeout_spin)

        can_group.setLayout(can_layout)
        layout.addWidget(can_group)

        # LED Brightness
        brightness_group = QGroupBox("LED Settings")
        brightness_layout = QFormLayout()

        bright_layout = QHBoxLayout()
        self.led_brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.led_brightness_slider.setRange(0, 100)
        self.led_brightness_slider.setValue(100)
        self.led_brightness_slider.valueChanged.connect(self._on_brightness_changed)
        bright_layout.addWidget(self.led_brightness_slider)
        self.brightness_label = QLabel("100%")
        self.brightness_label.setMinimumWidth(50)
        bright_layout.addWidget(self.brightness_label)
        brightness_layout.addRow("Brightness:", bright_layout)

        brightness_group.setLayout(brightness_layout)
        layout.addWidget(brightness_group)

        # CANopen Info
        info_label = QLabel(
            "CANopen Protocol:\n"
            "  TPDO1 (0x180 + NodeID): Button states\n"
            "  RPDO1 (0x200 + NodeID): LED control\n"
            "  Heartbeat (0x700 + NodeID): Online detection"
        )
        info_label.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()
        return tab

    def _on_brightness_changed(self, value):
        """Update brightness label."""
        self.brightness_label.setText(f"{value}%")

    def _create_buttons_tab(self) -> QWidget:
        """Create button configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Visual keypad
        keypad_group = QGroupBox("Keypad Layout")
        keypad_layout = QVBoxLayout()

        self.keypad_grid = QGridLayout()
        self.keypad_grid.setSpacing(5)
        self.button_widgets = []

        keypad_layout.addLayout(self.keypad_grid)
        keypad_group.setLayout(keypad_layout)
        layout.addWidget(keypad_group)

        # Button configuration table
        config_group = QGroupBox("Button Configuration")
        config_layout = QVBoxLayout()

        self.buttons_table = QTableWidget()
        self.buttons_table.setColumnCount(3)
        self.buttons_table.setHorizontalHeaderLabels(["Key", "Enabled", "Name"])

        header = self.buttons_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.buttons_table.setColumnWidth(0, 50)
        self.buttons_table.setColumnWidth(1, 70)
        self.buttons_table.verticalHeader().setVisible(False)
        self.buttons_table.setMinimumHeight(300)

        config_layout.addWidget(self.buttons_table)

        # Quick actions
        quick_layout = QHBoxLayout()
        enable_all_btn = QPushButton("Enable All")
        enable_all_btn.clicked.connect(self._enable_all_buttons)
        quick_layout.addWidget(enable_all_btn)

        disable_all_btn = QPushButton("Disable All")
        disable_all_btn.clicked.connect(self._disable_all_buttons)
        quick_layout.addWidget(disable_all_btn)
        quick_layout.addStretch()

        config_layout.addLayout(quick_layout)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        self._update_button_grid()
        return tab

    def _create_led_tab(self) -> QWidget:
        """Create LED control tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        led_group = QGroupBox("LED Configuration")
        led_layout = QVBoxLayout()

        self.led_table = QTableWidget()
        self.led_table.setColumnCount(5)
        self.led_table.setHorizontalHeaderLabels([
            "Key", "Control Mode", "On Color", "Off Color", "LED Channel"
        ])

        header = self.led_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.led_table.setColumnWidth(0, 50)
        self.led_table.setColumnWidth(2, 100)
        self.led_table.setColumnWidth(3, 100)
        self.led_table.verticalHeader().setVisible(False)
        self.led_table.setMinimumHeight(300)

        led_layout.addWidget(self.led_table)

        # Quick actions
        quick_layout = QHBoxLayout()
        follow_btn = QPushButton("Set All: Follow Button")
        follow_btn.clicked.connect(lambda: self._set_all_led_mode(1))
        quick_layout.addWidget(follow_btn)

        off_btn = QPushButton("Set All: Off")
        off_btn.clicked.connect(lambda: self._set_all_led_mode(0))
        quick_layout.addWidget(off_btn)
        quick_layout.addStretch()

        led_layout.addLayout(quick_layout)
        led_group.setLayout(led_layout)
        layout.addWidget(led_group)

        # Info
        info_label = QLabel(
            "LED Control Modes:\n"
            "  Off: LED always off\n"
            "  Follow Button: LED mirrors button state\n"
            "  Channel Controlled: LED controlled by channel value\n"
            "  Toggle on Press: LED toggles on button press"
        )
        info_label.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()
        return tab

    def _on_type_changed(self):
        """Handle keypad type change."""
        self._update_button_grid()
        self._update_buttons_table()
        self._update_led_table()

    def _get_keypad_type(self) -> int:
        return self.keypad_type_combo.currentIndex()

    def _get_button_count(self) -> int:
        keypad_type = self._get_keypad_type()
        rows, cols = self.KEYPAD_LAYOUTS.get(keypad_type, (2, 6))
        return rows * cols

    def _update_button_grid(self):
        """Update visual keypad grid."""
        for widget in self.button_widgets:
            widget.deleteLater()
        self.button_widgets.clear()

        keypad_type = self._get_keypad_type()
        rows, cols = self.KEYPAD_LAYOUTS.get(keypad_type, (2, 6))

        for row in range(rows):
            for col in range(cols):
                btn_index = row * cols + col
                btn = QPushButton(f"{btn_index + 1}")
                btn.setFixedSize(50, 40)
                btn.setFont(QFont("", 10, QFont.Weight.Bold))
                btn.setProperty("button_index", btn_index)
                btn.clicked.connect(self._on_button_clicked)
                self.keypad_grid.addWidget(btn, row, col)
                self.button_widgets.append(btn)

        self._update_buttons_table()
        self._update_led_table()

    def _update_buttons_table(self):
        """Update buttons configuration table."""
        self.buttons_table.blockSignals(True)
        button_count = self._get_button_count()
        self.buttons_table.setRowCount(button_count)

        for i in range(button_count):
            key_item = QTableWidgetItem(f"{i + 1}")
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.buttons_table.setItem(i, 0, key_item)

            config = self.button_configs.get(i, {})

            enabled_check = QCheckBox()
            enabled_check.setChecked(config.get("enabled", True))
            enabled_check.setProperty("button_index", i)
            self.buttons_table.setCellWidget(i, 1, enabled_check)

            name_item = QTableWidgetItem(config.get("name", f"Button {i + 1}"))
            self.buttons_table.setItem(i, 2, name_item)

        self.buttons_table.blockSignals(False)

    def _update_led_table(self):
        """Update LED configuration table."""
        if not hasattr(self, 'led_table'):
            return

        button_count = self._get_button_count()
        self.led_table.setRowCount(button_count)

        for i in range(button_count):
            config = self.button_configs.get(i, {})

            key_item = QTableWidgetItem(f"{i + 1}")
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.led_table.setItem(i, 0, key_item)

            mode_combo = QComboBox()
            for name, _ in self.LED_CTRL_MODES:
                mode_combo.addItem(name)
            mode_combo.setCurrentIndex(config.get("led_ctrl_mode", 1))
            mode_combo.setProperty("button_index", i)
            self.led_table.setCellWidget(i, 1, mode_combo)

            on_color_combo = QComboBox()
            for name, _ in self.LED_COLORS:
                on_color_combo.addItem(name)
            on_color_combo.setCurrentIndex(config.get("led_on_color", 2))
            self.led_table.setCellWidget(i, 2, on_color_combo)

            off_color_combo = QComboBox()
            for name, _ in self.LED_COLORS:
                off_color_combo.addItem(name)
            off_color_combo.setCurrentIndex(config.get("led_off_color", 0))
            self.led_table.setCellWidget(i, 3, off_color_combo)

            led_channel_combo = self._create_led_channel_combo()
            led_channel_name = config.get("led_channel_name", "")
            if led_channel_name:
                idx = led_channel_combo.findText(led_channel_name)
                if idx >= 0:
                    led_channel_combo.setCurrentIndex(idx)
            self.led_table.setCellWidget(i, 4, led_channel_combo)

    def _create_led_channel_combo(self) -> QComboBox:
        """Create channel selector combo box."""
        combo = QComboBox()
        combo.addItem("", "")

        for category, channels in self.available_channels.items():
            if isinstance(channels, list):
                for ch in channels:
                    if isinstance(ch, dict):
                        name = ch.get("channel_name", ch.get("name", ""))
                        if name:
                            combo.addItem(name)
                    elif isinstance(ch, str):
                        combo.addItem(ch)
        return combo

    def _on_button_clicked(self):
        """Handle keypad button click."""
        sender = self.sender()
        if sender:
            btn_index = sender.property("button_index")
            self.buttons_table.selectRow(btn_index)
            self.tabs.setCurrentIndex(1)

    def _enable_all_buttons(self):
        for i in range(self.buttons_table.rowCount()):
            widget = self.buttons_table.cellWidget(i, 1)
            if isinstance(widget, QCheckBox):
                widget.setChecked(True)

    def _disable_all_buttons(self):
        for i in range(self.buttons_table.rowCount()):
            widget = self.buttons_table.cellWidget(i, 1)
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)

    def _set_all_led_mode(self, mode: int):
        for i in range(self.led_table.rowCount()):
            widget = self.led_table.cellWidget(i, 1)
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(mode)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))
        self.keypad_type_combo.setCurrentIndex(config.get("type", 0))
        self.enabled_check.setChecked(config.get("enabled", True))
        self.can_bus_combo.setCurrentIndex(config.get("can_bus", 1) - 1)
        self.node_id_spin.setValue(config.get("node_id", 1))
        self.timeout_spin.setValue(config.get("timeout_ms", 1000))
        self.led_brightness_slider.setValue(config.get("led_brightness", 100))

        buttons = config.get("buttons", [])
        if isinstance(buttons, list):
            for i, btn_config in enumerate(buttons):
                if isinstance(btn_config, dict):
                    self.button_configs[i] = btn_config
        elif isinstance(buttons, dict):
            self.button_configs = {
                int(k) if isinstance(k, str) else k: v
                for k, v in buttons.items()
            }

        self._update_button_grid()

    def _on_accept(self):
        """Validate and accept."""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return
        self.accept()

    def _collect_button_configs(self) -> List[Dict[str, Any]]:
        """Collect button configurations."""
        button_count = self._get_button_count()
        buttons = []

        for i in range(button_count):
            enabled_widget = self.buttons_table.cellWidget(i, 1)
            enabled = enabled_widget.isChecked() if isinstance(enabled_widget, QCheckBox) else True

            name_item = self.buttons_table.item(i, 2)
            name = name_item.text() if name_item else f"Button {i + 1}"

            mode_widget = self.led_table.cellWidget(i, 1)
            led_ctrl_mode = mode_widget.currentIndex() if isinstance(mode_widget, QComboBox) else 1

            on_color_widget = self.led_table.cellWidget(i, 2)
            led_on_color = on_color_widget.currentIndex() if isinstance(on_color_widget, QComboBox) else 2

            off_color_widget = self.led_table.cellWidget(i, 3)
            led_off_color = off_color_widget.currentIndex() if isinstance(off_color_widget, QComboBox) else 0

            led_channel_widget = self.led_table.cellWidget(i, 4)
            led_channel_name = led_channel_widget.currentText() if isinstance(led_channel_widget, QComboBox) else ""

            buttons.append({
                "enabled": enabled,
                "name": name,
                "led_on_color": led_on_color,
                "led_off_color": led_off_color,
                "led_ctrl_mode": led_ctrl_mode,
                "led_channel_name": led_channel_name,
            })

        return buttons

    def get_config(self) -> Dict[str, Any]:
        """Get keypad configuration."""
        return {
            "channel_type": "blinkmarine_keypad",
            "name": self.name_edit.text().strip(),
            "type": self._get_keypad_type(),
            "enabled": self.enabled_check.isChecked(),
            "can_bus": self.can_bus_combo.currentIndex() + 1,
            "node_id": self.node_id_spin.value(),
            "timeout_ms": self.timeout_spin.value(),
            "led_brightness": self.led_brightness_slider.value(),
            "buttons": self._collect_button_configs(),
        }

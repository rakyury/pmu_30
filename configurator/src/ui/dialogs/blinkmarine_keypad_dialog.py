"""
BlinkMarine CAN Keypad Configuration Dialog
Supports PKP-2600-SI (2x6) and PKP-2800-SI (2x8) CAN keypads from BlinkMarine

Protocol: PKP2600SI J1939 User Manual Rev 1.5
- Uses J1939 29-bit extended CAN IDs
- Keypad sends button press/release events via CAN
- PMU can control LED backlights via CAN TX
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QComboBox, QSpinBox, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QTabWidget, QWidget, QGridLayout, QFrame, QMessageBox,
    QSlider
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from typing import Dict, Any, Optional, List


class BlinkMarineKeypadDialog(QDialog):
    """Dialog for configuring BlinkMarine CAN keypads (PKP2600SI/PKP2800SI J1939)."""

    # Keypad types (matching firmware enum PMU_BlinkMarine_Type_t)
    KEYPAD_PKP2600SI = 0  # 12 buttons (2x6)
    KEYPAD_PKP2800SI = 1  # 16 buttons (2x8)

    # Button layout (rows x cols)
    KEYPAD_LAYOUTS = {
        KEYPAD_PKP2600SI: (2, 6),
        KEYPAD_PKP2800SI: (2, 8),
    }

    # LED colors (matching firmware enum PMU_BM_LedColor_t)
    LED_COLORS = [
        ("Off", 0x00),
        ("Red", 0x01),
        ("Green", 0x02),
        ("Blue", 0x03),
        ("Yellow", 0x04),
        ("Cyan", 0x05),
        ("Magenta", 0x06),
        ("White", 0x07),
        ("Amber", 0x08),
        ("Yellow-Green", 0x09),
    ]

    # LED states (matching firmware enum PMU_BM_LedState_t)
    LED_STATES = [
        ("Off", 0x00),
        ("On", 0x01),
        ("Blink", 0x02),
        ("Alt Blink", 0x03),
    ]

    # LED control modes (matching firmware enum PMU_BM_LedCtrlMode_t)
    LED_CTRL_MODES = [
        ("Off (LED always off)", 0),
        ("Follow Button", 1),
        ("Channel Controlled", 2),
        ("Toggle on Press", 3),
    ]

    # Default J1939 addresses
    DEFAULT_SOURCE_ADDR = 0x21
    DEFAULT_KEYPAD_ID = 0x21
    DEFAULT_DEST_ADDR = 0xFF  # Broadcast

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.config = config or {}
        self.available_channels = available_channels or {}
        self.existing_channels = existing_channels or []
        self.button_configs = {}  # {button_index: config_dict}

        self._init_ui()

        if config:
            self._load_config(config)

    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("BlinkMarine CAN Keypad (J1939)")
        self.setModal(True)
        self.setMinimumSize(800, 700)
        self.resize(900, 800)

        layout = QVBoxLayout(self)

        # Create tabs
        self.tabs = QTabWidget()

        # General tab
        general_tab = self._create_general_tab()
        self.tabs.addTab(general_tab, "General")

        # Buttons tab
        buttons_tab = self._create_buttons_tab()
        self.tabs.addTab(buttons_tab, "Buttons")

        # LED Control tab
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
        self.name_edit.setToolTip("Unique name for this keypad")
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

        # J1939 CAN Configuration
        can_group = QGroupBox("J1939 CAN Configuration")
        can_layout = QFormLayout()

        self.can_bus_combo = QComboBox()
        self.can_bus_combo.addItems(["CAN 1", "CAN 2", "CAN 3", "CAN 4"])
        can_layout.addRow("CAN Bus:", self.can_bus_combo)

        # Source Address (keypad's address)
        src_layout = QHBoxLayout()
        self.source_addr_spin = QSpinBox()
        self.source_addr_spin.setRange(0, 255)
        self.source_addr_spin.setValue(self.DEFAULT_SOURCE_ADDR)
        self.source_addr_spin.setPrefix("0x")
        self.source_addr_spin.setDisplayIntegerBase(16)
        src_layout.addWidget(self.source_addr_spin)
        src_layout.addWidget(QLabel("(Keypad's J1939 source address, default 0x21)"))
        src_layout.addStretch()
        can_layout.addRow("Source Address:", src_layout)

        # Keypad Identifier
        kpid_layout = QHBoxLayout()
        self.keypad_id_spin = QSpinBox()
        self.keypad_id_spin.setRange(0, 255)
        self.keypad_id_spin.setValue(self.DEFAULT_KEYPAD_ID)
        self.keypad_id_spin.setPrefix("0x")
        self.keypad_id_spin.setDisplayIntegerBase(16)
        kpid_layout.addWidget(self.keypad_id_spin)
        kpid_layout.addWidget(QLabel("(Keypad identifier in messages, default 0x21)"))
        kpid_layout.addStretch()
        can_layout.addRow("Keypad ID:", kpid_layout)

        # Destination Address (our address)
        dest_layout = QHBoxLayout()
        self.dest_addr_spin = QSpinBox()
        self.dest_addr_spin.setRange(0, 255)
        self.dest_addr_spin.setValue(self.DEFAULT_DEST_ADDR)
        self.dest_addr_spin.setPrefix("0x")
        self.dest_addr_spin.setDisplayIntegerBase(16)
        dest_layout.addWidget(self.dest_addr_spin)
        dest_layout.addWidget(QLabel("(Our address for receiving, 0xFF=broadcast)"))
        dest_layout.addStretch()
        can_layout.addRow("Dest Address:", dest_layout)

        self.extended_check = QCheckBox("Use Extended IDs (29-bit J1939)")
        self.extended_check.setChecked(True)
        self.extended_check.setToolTip("J1939 protocol uses 29-bit extended CAN IDs")
        can_layout.addRow("", self.extended_check)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 30000)
        self.timeout_spin.setValue(1000)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setToolTip("Timeout before keypad is considered offline")
        can_layout.addRow("Timeout:", self.timeout_spin)

        can_group.setLayout(can_layout)
        layout.addWidget(can_group)

        # Backlight configuration
        backlight_group = QGroupBox("Backlight Settings")
        backlight_layout = QFormLayout()

        # LED brightness (0-63)
        led_bright_layout = QHBoxLayout()
        self.led_brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.led_brightness_slider.setRange(0, 63)
        self.led_brightness_slider.setValue(63)
        self.led_brightness_slider.valueChanged.connect(self._on_led_brightness_changed)
        led_bright_layout.addWidget(self.led_brightness_slider)
        self.led_brightness_label = QLabel("100%")
        self.led_brightness_label.setMinimumWidth(50)
        led_bright_layout.addWidget(self.led_brightness_label)
        backlight_layout.addRow("LED Brightness:", led_bright_layout)

        # Backlight brightness (0-63)
        bl_bright_layout = QHBoxLayout()
        self.backlight_brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.backlight_brightness_slider.setRange(0, 63)
        self.backlight_brightness_slider.setValue(32)
        self.backlight_brightness_slider.valueChanged.connect(self._on_backlight_brightness_changed)
        bl_bright_layout.addWidget(self.backlight_brightness_slider)
        self.backlight_brightness_label = QLabel("50%")
        self.backlight_brightness_label.setMinimumWidth(50)
        bl_bright_layout.addWidget(self.backlight_brightness_label)
        backlight_layout.addRow("Backlight Brightness:", bl_bright_layout)

        # Backlight color
        self.backlight_color_combo = QComboBox()
        for name, _ in self.LED_COLORS:
            self.backlight_color_combo.addItem(name)
        self.backlight_color_combo.setCurrentIndex(7)  # White
        backlight_layout.addRow("Backlight Color:", self.backlight_color_combo)

        backlight_group.setLayout(backlight_layout)
        layout.addWidget(backlight_group)

        # Info
        info_label = QLabel(
            "BlinkMarine PKP series keypads use J1939 protocol over CAN.\n"
            "Protocol reference: PKP2600SI J1939 User Manual Rev 1.5\n"
            "CAN ID format: 18EF[DA][SA] (Priority 6, PGN 0xEF00 Proprietary A)"
        )
        info_label.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()

        return tab

    def _on_led_brightness_changed(self, value):
        """Update LED brightness label."""
        percent = int((value / 63) * 100)
        self.led_brightness_label.setText(f"{percent}%")

    def _on_backlight_brightness_changed(self, value):
        """Update backlight brightness label."""
        percent = int((value / 63) * 100)
        self.backlight_brightness_label.setText(f"{percent}%")

    def _create_buttons_tab(self) -> QWidget:
        """Create button configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Visual keypad representation
        keypad_group = QGroupBox("Keypad Layout")
        keypad_layout = QVBoxLayout()

        self.keypad_grid = QGridLayout()
        self.keypad_grid.setSpacing(5)
        self.button_widgets = []

        # Will be populated by _update_button_grid()
        keypad_layout.addLayout(self.keypad_grid)

        keypad_group.setLayout(keypad_layout)
        layout.addWidget(keypad_group)

        # Button configuration table
        config_group = QGroupBox("Button Configuration")
        config_layout = QVBoxLayout()

        self.buttons_table = QTableWidget()
        self.buttons_table.setColumnCount(4)
        self.buttons_table.setHorizontalHeaderLabels([
            "Key", "Enabled", "Name", "Virtual Channel"
        ])

        header = self.buttons_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.buttons_table.setColumnWidth(0, 50)
        self.buttons_table.setColumnWidth(1, 70)
        self.buttons_table.verticalHeader().setVisible(False)
        self.buttons_table.setMinimumHeight(350)
        self.buttons_table.cellChanged.connect(self._on_button_cell_changed)

        config_layout.addWidget(self.buttons_table)

        # Quick action buttons
        quick_layout = QHBoxLayout()

        self.enable_all_btn = QPushButton("Enable All")
        self.enable_all_btn.clicked.connect(self._enable_all_buttons)
        quick_layout.addWidget(self.enable_all_btn)

        self.disable_all_btn = QPushButton("Disable All")
        self.disable_all_btn.clicked.connect(self._disable_all_buttons)
        quick_layout.addWidget(self.disable_all_btn)

        self.assign_sequential_btn = QPushButton("Auto-Name Channels")
        self.assign_sequential_btn.setToolTip("Generate virtual channel names based on keypad name")
        self.assign_sequential_btn.clicked.connect(self._assign_sequential)
        quick_layout.addWidget(self.assign_sequential_btn)

        quick_layout.addStretch()

        config_layout.addLayout(quick_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Info
        info_label = QLabel(
            "Virtual channels are auto-created as Switch type channels.\n"
            "Button presses set the channel value to 1, releases set it to 0."
        )
        info_label.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addWidget(info_label)

        # Initialize grid
        self._update_button_grid()

        return tab

    def _create_led_tab(self) -> QWidget:
        """Create LED control configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # LED Configuration Table
        led_config_group = QGroupBox("LED Configuration per Button")
        led_layout = QVBoxLayout()

        self.led_table = QTableWidget()
        self.led_table.setColumnCount(6)
        self.led_table.setHorizontalHeaderLabels([
            "Key", "Control Mode", "On Color", "Off Color", "Alt Color", "LED Channel"
        ])

        header = self.led_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.led_table.setColumnWidth(0, 50)
        self.led_table.setColumnWidth(2, 100)
        self.led_table.setColumnWidth(3, 100)
        self.led_table.setColumnWidth(4, 100)

        self.led_table.verticalHeader().setVisible(False)
        self.led_table.setMinimumHeight(350)

        led_layout.addWidget(self.led_table)

        led_config_group.setLayout(led_layout)
        layout.addWidget(led_config_group)

        # Quick actions
        quick_layout = QHBoxLayout()

        set_follow_btn = QPushButton("Set All: Follow Button")
        set_follow_btn.clicked.connect(lambda: self._set_all_led_mode(1))
        quick_layout.addWidget(set_follow_btn)

        set_off_btn = QPushButton("Set All: Off")
        set_off_btn.clicked.connect(lambda: self._set_all_led_mode(0))
        quick_layout.addWidget(set_off_btn)

        quick_layout.addStretch()

        layout.addLayout(quick_layout)

        # Info
        info_label = QLabel(
            "LED Control Modes:\n"
            "  Off: LED is always off\n"
            "  Follow Button: LED mirrors button state (on when pressed)\n"
            "  Channel Controlled: LED state is controlled by a channel value\n"
            "  Toggle on Press: LED toggles each time button is pressed\n\n"
            "Alt Color is used for Alt Blink mode (alternates between On and Alt colors)"
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
        """Get current keypad type."""
        return self.keypad_type_combo.currentIndex()

    def _get_button_count(self) -> int:
        """Get number of buttons for current type."""
        keypad_type = self._get_keypad_type()
        rows, cols = self.KEYPAD_LAYOUTS.get(keypad_type, (2, 6))
        return rows * cols

    def _update_button_grid(self):
        """Update visual keypad grid."""
        # Clear existing buttons
        for widget in self.button_widgets:
            widget.deleteLater()
        self.button_widgets.clear()

        # Get layout
        keypad_type = self._get_keypad_type()
        rows, cols = self.KEYPAD_LAYOUTS.get(keypad_type, (2, 6))

        # Create button widgets
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
            # Key number (1-based like in protocol)
            key_item = QTableWidgetItem(f"{i + 1}")
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.buttons_table.setItem(i, 0, key_item)

            # Get existing config
            config = self.button_configs.get(i, {})

            # Enabled checkbox
            enabled_check = QCheckBox()
            enabled_check.setChecked(config.get("enabled", True))
            enabled_check.setProperty("button_index", i)
            enabled_check.stateChanged.connect(self._on_button_enabled_changed)
            self.buttons_table.setCellWidget(i, 1, enabled_check)

            # Name
            name_item = QTableWidgetItem(config.get("name", f"Button {i + 1}"))
            self.buttons_table.setItem(i, 2, name_item)

            # Virtual channel name
            channel_item = QTableWidgetItem(config.get("virtual_channel", ""))
            self.buttons_table.setItem(i, 3, channel_item)

        self.buttons_table.blockSignals(False)

    def _update_led_table(self):
        """Update LED configuration table."""
        # Guard: led_table may not exist yet during initialization
        if not hasattr(self, 'led_table'):
            return

        button_count = self._get_button_count()
        self.led_table.setRowCount(button_count)

        for i in range(button_count):
            config = self.button_configs.get(i, {})

            # Key number
            key_item = QTableWidgetItem(f"{i + 1}")
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.led_table.setItem(i, 0, key_item)

            # Control mode
            mode_combo = QComboBox()
            for name, _ in self.LED_CTRL_MODES:
                mode_combo.addItem(name)
            mode_combo.setCurrentIndex(config.get("led_ctrl_mode", 1))  # Default: Follow Button
            mode_combo.setProperty("button_index", i)
            mode_combo.currentIndexChanged.connect(self._on_led_mode_changed)
            self.led_table.setCellWidget(i, 1, mode_combo)

            # On color
            on_color_combo = QComboBox()
            for name, _ in self.LED_COLORS:
                on_color_combo.addItem(name)
            on_color_combo.setCurrentIndex(config.get("led_on_color", 2))  # Default: Green
            on_color_combo.setProperty("button_index", i)
            self.led_table.setCellWidget(i, 2, on_color_combo)

            # Off color
            off_color_combo = QComboBox()
            for name, _ in self.LED_COLORS:
                off_color_combo.addItem(name)
            off_color_combo.setCurrentIndex(config.get("led_off_color", 0))  # Default: Off
            off_color_combo.setProperty("button_index", i)
            self.led_table.setCellWidget(i, 3, off_color_combo)

            # Alt color (for alt blink)
            alt_color_combo = QComboBox()
            for name, _ in self.LED_COLORS:
                alt_color_combo.addItem(name)
            alt_color_combo.setCurrentIndex(config.get("led_secondary", 1))  # Default: Red
            alt_color_combo.setProperty("button_index", i)
            self.led_table.setCellWidget(i, 4, alt_color_combo)

            # LED channel (for channel-controlled mode)
            led_channel_item = QTableWidgetItem(config.get("led_channel_name", ""))
            self.led_table.setItem(i, 5, led_channel_item)

    def _on_button_clicked(self):
        """Handle keypad button click (for selection)."""
        sender = self.sender()
        if sender:
            btn_index = sender.property("button_index")
            self.buttons_table.selectRow(btn_index)
            self.tabs.setCurrentIndex(1)  # Switch to Buttons tab

    def _on_button_cell_changed(self, row, col):
        """Handle button config cell change."""
        if row not in self.button_configs:
            self.button_configs[row] = {}

        if col == 2:  # Name
            item = self.buttons_table.item(row, col)
            if item:
                self.button_configs[row]["name"] = item.text()
        elif col == 3:  # Virtual channel
            item = self.buttons_table.item(row, col)
            if item:
                self.button_configs[row]["virtual_channel"] = item.text()

    def _on_button_enabled_changed(self, state):
        """Handle button enabled checkbox change."""
        sender = self.sender()
        if sender:
            btn_index = sender.property("button_index")
            if btn_index not in self.button_configs:
                self.button_configs[btn_index] = {}
            self.button_configs[btn_index]["enabled"] = (state == Qt.CheckState.Checked.value)

    def _on_led_mode_changed(self, index):
        """Handle LED mode combo change."""
        sender = self.sender()
        if sender:
            btn_index = sender.property("button_index")
            if btn_index not in self.button_configs:
                self.button_configs[btn_index] = {}
            self.button_configs[btn_index]["led_ctrl_mode"] = index

    def _enable_all_buttons(self):
        """Enable all buttons."""
        for i in range(self.buttons_table.rowCount()):
            widget = self.buttons_table.cellWidget(i, 1)
            if isinstance(widget, QCheckBox):
                widget.setChecked(True)

    def _disable_all_buttons(self):
        """Disable all buttons."""
        for i in range(self.buttons_table.rowCount()):
            widget = self.buttons_table.cellWidget(i, 1)
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)

    def _assign_sequential(self):
        """Assign sequential channel names to buttons."""
        keypad_name = self.name_edit.text().strip() or "Keypad"
        # Use name as base for button channel names
        clean_name = keypad_name.replace(" ", "_")

        button_count = self._get_button_count()
        self.buttons_table.blockSignals(True)

        for i in range(button_count):
            if i not in self.button_configs:
                self.button_configs[i] = {}

            self.button_configs[i]["name"] = f"Button {i + 1}"
            self.button_configs[i]["virtual_channel"] = f"{clean_name}_Btn{i + 1}"
            self.button_configs[i]["enabled"] = True

            # Update table
            name_item = self.buttons_table.item(i, 2)
            if name_item:
                name_item.setText(f"Button {i + 1}")
            channel_item = self.buttons_table.item(i, 3)
            if channel_item:
                channel_item.setText(f"{clean_name}_Btn{i + 1}")
            enabled_widget = self.buttons_table.cellWidget(i, 1)
            if isinstance(enabled_widget, QCheckBox):
                enabled_widget.setChecked(True)

        self.buttons_table.blockSignals(False)

    def _set_all_led_mode(self, mode: int):
        """Set all LED control modes."""
        for i in range(self.led_table.rowCount()):
            widget = self.led_table.cellWidget(i, 1)
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(mode)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        # Name
        name = config.get("name", "")
        self.name_edit.setText(name)

        # Keypad type
        keypad_type = config.get("type", self.KEYPAD_PKP2600SI)
        self.keypad_type_combo.setCurrentIndex(keypad_type)

        # Enabled
        self.enabled_check.setChecked(config.get("enabled", True))

        # CAN config
        self.can_bus_combo.setCurrentIndex(config.get("can_bus", 1) - 1)
        self.source_addr_spin.setValue(config.get("source_address", self.DEFAULT_SOURCE_ADDR))
        self.keypad_id_spin.setValue(config.get("keypad_identifier", self.DEFAULT_KEYPAD_ID))
        self.dest_addr_spin.setValue(config.get("destination_address", self.DEFAULT_DEST_ADDR))
        self.extended_check.setChecked(config.get("use_extended_id", True))
        self.timeout_spin.setValue(config.get("timeout_ms", 1000))

        # Brightness
        self.led_brightness_slider.setValue(config.get("led_brightness", 63))
        self.backlight_brightness_slider.setValue(config.get("backlight_brightness", 32))
        self.backlight_color_combo.setCurrentIndex(config.get("backlight_color", 7))

        # Button configs
        buttons = config.get("buttons", [])
        if isinstance(buttons, list):
            for i, btn_config in enumerate(buttons):
                if isinstance(btn_config, dict):
                    self.button_configs[i] = btn_config
        elif isinstance(buttons, dict):
            # Legacy format with dict
            self.button_configs = {
                int(k) if isinstance(k, str) else k: v
                for k, v in buttons.items()
            }

        self._update_button_grid()

    def _on_accept(self):
        """Validate and accept."""
        errors = []

        if not self.name_edit.text().strip():
            errors.append("Name is required")

        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return

        self.accept()

    def _collect_button_configs(self) -> List[Dict[str, Any]]:
        """Collect button configurations from tables."""
        button_count = self._get_button_count()
        buttons = []

        for i in range(button_count):
            # Get from buttons table
            enabled_widget = self.buttons_table.cellWidget(i, 1)
            enabled = enabled_widget.isChecked() if isinstance(enabled_widget, QCheckBox) else True

            name_item = self.buttons_table.item(i, 2)
            name = name_item.text() if name_item else f"Button {i + 1}"

            channel_item = self.buttons_table.item(i, 3)
            virtual_channel = channel_item.text() if channel_item else ""

            # Get from LED table
            mode_widget = self.led_table.cellWidget(i, 1)
            led_ctrl_mode = mode_widget.currentIndex() if isinstance(mode_widget, QComboBox) else 1

            on_color_widget = self.led_table.cellWidget(i, 2)
            led_on_color = on_color_widget.currentIndex() if isinstance(on_color_widget, QComboBox) else 2

            off_color_widget = self.led_table.cellWidget(i, 3)
            led_off_color = off_color_widget.currentIndex() if isinstance(off_color_widget, QComboBox) else 0

            alt_color_widget = self.led_table.cellWidget(i, 4)
            led_secondary = alt_color_widget.currentIndex() if isinstance(alt_color_widget, QComboBox) else 1

            led_channel_item = self.led_table.item(i, 5)
            led_channel_name = led_channel_item.text() if led_channel_item else ""

            buttons.append({
                "enabled": enabled,
                "name": name,
                "virtual_channel": virtual_channel,
                "led_on_color": led_on_color,
                "led_off_color": led_off_color,
                "led_secondary": led_secondary,
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
            "source_address": self.source_addr_spin.value(),
            "keypad_identifier": self.keypad_id_spin.value(),
            "destination_address": self.dest_addr_spin.value(),
            "use_extended_id": self.extended_check.isChecked(),
            "timeout_ms": self.timeout_spin.value(),
            "led_brightness": self.led_brightness_slider.value(),
            "backlight_brightness": self.backlight_brightness_slider.value(),
            "backlight_color": self.backlight_color_combo.currentIndex(),
            "buttons": self._collect_button_configs(),
        }

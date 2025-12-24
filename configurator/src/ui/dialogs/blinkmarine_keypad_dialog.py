"""
BlinkMarine CAN Keypad Configuration Dialog
Supports 2x6 and 2x8 CAN keypads from BlinkMarine

Protocol:
- Keypad sends button press/release events via CAN
- PMU can control LED backlights via CAN TX
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QComboBox, QSpinBox, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QTabWidget, QWidget, QGridLayout, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from typing import Dict, Any, Optional, List


class BlinkMarineKeypadDialog(QDialog):
    """Dialog for configuring BlinkMarine CAN keypads."""

    # Keypad types
    KEYPAD_2X6 = "2x6"
    KEYPAD_2X8 = "2x8"

    # Button layout (rows x cols)
    KEYPAD_LAYOUTS = {
        KEYPAD_2X6: (2, 6),
        KEYPAD_2X8: (2, 8),
    }

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.config = config or {}
        self.existing_channels = existing_channels or []
        self.button_configs = {}  # {button_index: config_dict}

        self._init_ui()

        if config:
            self._load_config(config)

    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("BlinkMarine CAN Keypad")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

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
        self.name_edit.setPlaceholderText("e.g., Steering Wheel Keypad")
        identity_layout.addRow("Name: *", self.name_edit)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("e.g., keypad_1")
        identity_layout.addRow("ID:", self.id_edit)

        self.keypad_type_combo = QComboBox()
        self.keypad_type_combo.addItems(["2x6 (12 buttons)", "2x8 (16 buttons)"])
        self.keypad_type_combo.currentIndexChanged.connect(self._on_type_changed)
        identity_layout.addRow("Type:", self.keypad_type_combo)

        identity_group.setLayout(identity_layout)
        layout.addWidget(identity_group)

        # CAN Configuration
        can_group = QGroupBox("CAN Configuration")
        can_layout = QFormLayout()

        self.can_bus_combo = QComboBox()
        self.can_bus_combo.addItems(["CAN 1", "CAN 2"])
        can_layout.addRow("CAN Bus:", self.can_bus_combo)

        # RX ID (buttons from keypad)
        rx_layout = QHBoxLayout()
        self.rx_id_edit = QLineEdit()
        self.rx_id_edit.setPlaceholderText("0x100")
        self.rx_id_edit.setMaximumWidth(100)
        rx_layout.addWidget(self.rx_id_edit)
        rx_layout.addWidget(QLabel("Keypad button events"))
        rx_layout.addStretch()
        can_layout.addRow("RX Base ID:", rx_layout)

        # TX ID (LED control to keypad)
        tx_layout = QHBoxLayout()
        self.tx_id_edit = QLineEdit()
        self.tx_id_edit.setPlaceholderText("0x101")
        self.tx_id_edit.setMaximumWidth(100)
        tx_layout.addWidget(self.tx_id_edit)
        tx_layout.addWidget(QLabel("LED control commands"))
        tx_layout.addStretch()
        can_layout.addRow("TX Base ID:", tx_layout)

        self.extended_check = QCheckBox("Extended IDs (29-bit)")
        can_layout.addRow("", self.extended_check)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 30000)
        self.timeout_spin.setValue(500)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setToolTip("Timeout before keypad is considered offline")
        can_layout.addRow("Timeout:", self.timeout_spin)

        can_group.setLayout(can_layout)
        layout.addWidget(can_group)

        # Info
        info_label = QLabel(
            "BlinkMarine keypads communicate via CAN bus.\n"
            "RX ID: Keypad sends button press/release events\n"
            "TX ID: PMU sends LED brightness/color commands"
        )
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()

        return tab

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
        config_group = QGroupBox("Button Actions")
        config_layout = QVBoxLayout()

        self.buttons_table = QTableWidget()
        self.buttons_table.setColumnCount(5)
        self.buttons_table.setHorizontalHeaderLabels([
            "Button", "Name", "Channel", "Press Action", "Release Action"
        ])

        header = self.buttons_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.buttons_table.setColumnWidth(0, 60)
        self.buttons_table.verticalHeader().setVisible(False)
        self.buttons_table.itemDoubleClicked.connect(self._on_button_edit)

        config_layout.addWidget(self.buttons_table)

        # Quick action buttons
        quick_layout = QHBoxLayout()

        self.assign_sequential_btn = QPushButton("Assign Sequential Channels")
        self.assign_sequential_btn.setToolTip("Create digital input channels for each button")
        self.assign_sequential_btn.clicked.connect(self._assign_sequential)
        quick_layout.addWidget(self.assign_sequential_btn)

        self.clear_assignments_btn = QPushButton("Clear All")
        self.clear_assignments_btn.clicked.connect(self._clear_assignments)
        quick_layout.addWidget(self.clear_assignments_btn)

        quick_layout.addStretch()

        config_layout.addLayout(quick_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Initialize grid
        self._update_button_grid()

        return tab

    def _create_led_tab(self) -> QWidget:
        """Create LED control configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # LED Mode
        mode_group = QGroupBox("LED Control Mode")
        mode_layout = QFormLayout()

        self.led_mode_combo = QComboBox()
        self.led_mode_combo.addItems([
            "Off (No LED control)",
            "Mirror Input State",
            "Channel Controlled",
            "Custom Logic"
        ])
        self.led_mode_combo.currentIndexChanged.connect(self._on_led_mode_changed)
        mode_layout.addRow("Mode:", self.led_mode_combo)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # LED Configuration Table
        led_config_group = QGroupBox("LED Configuration")
        led_layout = QVBoxLayout()

        self.led_table = QTableWidget()
        self.led_table.setColumnCount(5)
        self.led_table.setHorizontalHeaderLabels([
            "Button", "LED Channel", "On Color", "Off Color", "Brightness"
        ])

        header = self.led_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.led_table.verticalHeader().setVisible(False)

        led_layout.addWidget(self.led_table)

        led_config_group.setLayout(led_layout)
        layout.addWidget(led_config_group)

        # Color picker info
        info_label = QLabel(
            "LED colors are 8-bit RGB values.\n"
            "Some BlinkMarine models support full RGB, others only brightness."
        )
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()

        return tab

    def _on_type_changed(self):
        """Handle keypad type change."""
        self._update_button_grid()
        self._update_buttons_table()
        self._update_led_table()

    def _get_keypad_type(self) -> str:
        """Get current keypad type."""
        if self.keypad_type_combo.currentIndex() == 0:
            return self.KEYPAD_2X6
        return self.KEYPAD_2X8

    def _get_button_count(self) -> int:
        """Get number of buttons for current type."""
        keypad_type = self._get_keypad_type()
        rows, cols = self.KEYPAD_LAYOUTS[keypad_type]
        return rows * cols

    def _update_button_grid(self):
        """Update visual keypad grid."""
        # Clear existing buttons
        for widget in self.button_widgets:
            widget.deleteLater()
        self.button_widgets.clear()

        # Get layout
        keypad_type = self._get_keypad_type()
        rows, cols = self.KEYPAD_LAYOUTS[keypad_type]

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

    def _update_buttons_table(self):
        """Update buttons configuration table."""
        button_count = self._get_button_count()
        self.buttons_table.setRowCount(button_count)

        for i in range(button_count):
            # Button number
            btn_item = QTableWidgetItem(f"B{i + 1}")
            btn_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_item.setFlags(btn_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.buttons_table.setItem(i, 0, btn_item)

            # Get existing config
            config = self.button_configs.get(i, {})

            # Name
            name_item = QTableWidgetItem(config.get("name", ""))
            self.buttons_table.setItem(i, 1, name_item)

            # Channel
            channel_item = QTableWidgetItem(config.get("channel", ""))
            self.buttons_table.setItem(i, 2, channel_item)

            # Press action
            press_item = QTableWidgetItem(config.get("press_action", "Set High"))
            self.buttons_table.setItem(i, 3, press_item)

            # Release action
            release_item = QTableWidgetItem(config.get("release_action", "Set Low"))
            self.buttons_table.setItem(i, 4, release_item)

    def _update_led_table(self):
        """Update LED configuration table."""
        button_count = self._get_button_count()
        self.led_table.setRowCount(button_count)

        for i in range(button_count):
            # Button number
            btn_item = QTableWidgetItem(f"B{i + 1}")
            btn_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_item.setFlags(btn_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.led_table.setItem(i, 0, btn_item)

            # LED channel
            led_channel_item = QTableWidgetItem("")
            self.led_table.setItem(i, 1, led_channel_item)

            # On color
            on_color_item = QTableWidgetItem("#00FF00")
            self.led_table.setItem(i, 2, on_color_item)

            # Off color
            off_color_item = QTableWidgetItem("#000000")
            self.led_table.setItem(i, 3, off_color_item)

            # Brightness
            brightness_item = QTableWidgetItem("100%")
            self.led_table.setItem(i, 4, brightness_item)

    def _on_button_clicked(self):
        """Handle keypad button click (for selection)."""
        sender = self.sender()
        if sender:
            btn_index = sender.property("button_index")
            self.buttons_table.selectRow(btn_index)

    def _on_button_edit(self, item):
        """Handle button config edit."""
        row = item.row()
        col = item.column()

        # Update button_configs
        if row not in self.button_configs:
            self.button_configs[row] = {}

        if col == 1:  # Name
            self.button_configs[row]["name"] = item.text()
        elif col == 2:  # Channel
            self.button_configs[row]["channel"] = item.text()
        elif col == 3:  # Press action
            self.button_configs[row]["press_action"] = item.text()
        elif col == 4:  # Release action
            self.button_configs[row]["release_action"] = item.text()

    def _assign_sequential(self):
        """Assign sequential channel names to buttons."""
        keypad_name = self.name_edit.text().strip() or "keypad"
        keypad_id = self.id_edit.text().strip() or keypad_name.lower().replace(" ", "_")

        button_count = self._get_button_count()
        for i in range(button_count):
            self.button_configs[i] = {
                "name": f"Button {i + 1}",
                "channel": f"{keypad_id}_btn{i + 1}",
                "press_action": "Set High",
                "release_action": "Set Low"
            }

        self._update_buttons_table()

    def _clear_assignments(self):
        """Clear all button assignments."""
        self.button_configs.clear()
        self._update_buttons_table()

    def _on_led_mode_changed(self):
        """Handle LED mode change."""
        mode = self.led_mode_combo.currentIndex()
        self.led_table.setEnabled(mode > 0)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))
        self.id_edit.setText(config.get("id", ""))

        # Keypad type
        keypad_type = config.get("keypad_type", self.KEYPAD_2X6)
        if keypad_type == self.KEYPAD_2X8:
            self.keypad_type_combo.setCurrentIndex(1)
        else:
            self.keypad_type_combo.setCurrentIndex(0)

        # CAN config
        self.can_bus_combo.setCurrentIndex(config.get("can_bus", 1) - 1)
        self.rx_id_edit.setText(f"0x{config.get('rx_base_id', 0x100):03X}")
        self.tx_id_edit.setText(f"0x{config.get('tx_base_id', 0x101):03X}")
        self.extended_check.setChecked(config.get("extended_id", False))
        self.timeout_spin.setValue(config.get("timeout_ms", 500))

        # Button configs
        self.button_configs = config.get("buttons", {})
        # Convert string keys to int if needed
        self.button_configs = {
            int(k) if isinstance(k, str) else k: v
            for k, v in self.button_configs.items()
        }

        # LED mode
        self.led_mode_combo.setCurrentIndex(config.get("led_mode", 0))

        self._update_button_grid()

    def _on_accept(self):
        """Validate and accept."""
        errors = []

        if not self.name_edit.text().strip():
            errors.append("Name is required")

        # Validate CAN IDs
        try:
            rx_text = self.rx_id_edit.text().strip()
            if rx_text:
                int(rx_text.replace("0x", "").replace("0X", ""), 16)
        except ValueError:
            errors.append("Invalid RX ID format")

        try:
            tx_text = self.tx_id_edit.text().strip()
            if tx_text:
                int(tx_text.replace("0x", "").replace("0X", ""), 16)
        except ValueError:
            errors.append("Invalid TX ID format")

        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return

        self.accept()

    def get_config(self) -> Dict[str, Any]:
        """Get keypad configuration."""
        # Parse CAN IDs
        rx_text = self.rx_id_edit.text().strip()
        rx_id = int(rx_text.replace("0x", "").replace("0X", ""), 16) if rx_text else 0x100

        tx_text = self.tx_id_edit.text().strip()
        tx_id = int(tx_text.replace("0x", "").replace("0X", ""), 16) if tx_text else 0x101

        # Read button configs from table
        for row in range(self.buttons_table.rowCount()):
            name_item = self.buttons_table.item(row, 1)
            channel_item = self.buttons_table.item(row, 2)
            press_item = self.buttons_table.item(row, 3)
            release_item = self.buttons_table.item(row, 4)

            self.button_configs[row] = {
                "name": name_item.text() if name_item else "",
                "channel": channel_item.text() if channel_item else "",
                "press_action": press_item.text() if press_item else "Set High",
                "release_action": release_item.text() if release_item else "Set Low"
            }

        return {
            "channel_type": "blinkmarine_keypad",
            "name": self.name_edit.text().strip(),
            "id": self.id_edit.text().strip() or self.name_edit.text().strip().lower().replace(" ", "_"),
            "keypad_type": self._get_keypad_type(),
            "can_bus": self.can_bus_combo.currentIndex() + 1,
            "rx_base_id": rx_id,
            "tx_base_id": tx_id,
            "extended_id": self.extended_check.isChecked(),
            "timeout_ms": self.timeout_spin.value(),
            "buttons": self.button_configs,
            "led_mode": self.led_mode_combo.currentIndex(),
        }

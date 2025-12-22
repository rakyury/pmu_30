"""
CAN Input (Signal) Configuration Dialog
Configures a CAN Input channel (Level 2) - signal extraction from CAN Message

References a CAN Message Object and defines how to extract a signal value.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QLabel, QCheckBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List


class CANInputDialog(QDialog):
    """Dialog for configuring a CAN Input channel (Level 2)."""

    DATA_TYPES = [
        ("Unsigned", "unsigned"),
        ("Signed", "signed"),
        ("Float", "float"),
    ]

    DATA_FORMATS = [
        ("8-bit", "8bit"),
        ("16-bit", "16bit"),
        ("32-bit", "32bit"),
        ("Custom", "custom"),
    ]

    BYTE_ORDERS = [
        ("Little Endian (Intel)", "little_endian"),
        ("Big Endian (Motorola)", "big_endian"),
    ]

    TIMEOUT_BEHAVIORS = [
        ("Use Default Value", "use_default"),
        ("Hold Last Value", "hold_last"),
        ("Set to Zero", "set_zero"),
    ]

    def __init__(self, parent=None, input_config: Optional[Dict[str, Any]] = None,
                 message_ids: Optional[List[str]] = None,
                 existing_channel_ids: Optional[List[str]] = None):
        """
        Initialize CAN Input Dialog.

        Args:
            parent: Parent widget
            input_config: Existing input configuration (for editing)
            message_ids: List of available CAN message IDs
            existing_channel_ids: List of existing channel IDs (for validation)
        """
        super().__init__(parent)
        self.input_config = input_config
        self.message_ids = message_ids or []
        self.existing_channel_ids = existing_channel_ids or []
        self.editing_id = input_config.get("id", "") if input_config else ""

        self.setWindowTitle("CAN Input" if not input_config else f"Edit CAN Input: {self.editing_id}")
        self.setModal(True)
        self.resize(550, 650)

        self._init_ui()

        if input_config:
            self._load_config(input_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Identification group
        id_group = QGroupBox("Identification")
        id_layout = QFormLayout()

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("e.g., crx_engine_rpm")
        self.id_edit.setToolTip("Unique channel ID (must start with crx_)")
        id_layout.addRow("Channel ID: *", self.id_edit)

        id_group.setLayout(id_layout)
        layout.addWidget(id_group)

        # Message Reference group
        msg_group = QGroupBox("Message Reference")
        msg_layout = QFormLayout()

        self.message_combo = QComboBox()
        if not self.message_ids:
            self.message_combo.addItem("(No messages available)", "")
            self.message_combo.setEnabled(False)
        else:
            self.message_combo.addItem("-- Select Message --", "")
            for msg_id in self.message_ids:
                self.message_combo.addItem(msg_id, msg_id)
        self.message_combo.setToolTip("Select the CAN message this input reads from")
        msg_layout.addRow("Message: *", self.message_combo)

        self.frame_offset_spin = QSpinBox()
        self.frame_offset_spin.setRange(0, 7)
        self.frame_offset_spin.setValue(0)
        self.frame_offset_spin.setPrefix("+")
        self.frame_offset_spin.setToolTip("Frame offset for compound/multiplexed messages (0 for normal)")
        msg_layout.addRow("Frame Offset:", self.frame_offset_spin)

        msg_group.setLayout(msg_layout)
        layout.addWidget(msg_group)

        # Data Extraction group
        data_group = QGroupBox("Data Extraction")
        data_layout = QFormLayout()

        # Data Type
        self.data_type_combo = QComboBox()
        for display_name, _ in self.DATA_TYPES:
            self.data_type_combo.addItem(display_name)
        self.data_type_combo.setToolTip("Value interpretation (unsigned, signed, or float)")
        data_layout.addRow("Data Type:", self.data_type_combo)

        # Data Format
        self.data_format_combo = QComboBox()
        for display_name, _ in self.DATA_FORMATS:
            self.data_format_combo.addItem(display_name)
        self.data_format_combo.currentIndexChanged.connect(self._on_format_changed)
        self.data_format_combo.setToolTip("Predefined format or custom bit field")
        data_layout.addRow("Data Format:", self.data_format_combo)

        # Byte Order
        self.byte_order_combo = QComboBox()
        for display_name, _ in self.BYTE_ORDERS:
            self.byte_order_combo.addItem(display_name)
        self.byte_order_combo.setToolTip("Byte order for multi-byte values")
        data_layout.addRow("Byte Order:", self.byte_order_combo)

        # Byte Offset
        self.byte_offset_spin = QSpinBox()
        self.byte_offset_spin.setRange(0, 7)
        self.byte_offset_spin.setValue(0)
        self.byte_offset_spin.setToolTip("Starting byte position in message (0-7)")
        data_layout.addRow("Byte Offset:", self.byte_offset_spin)

        # Custom bit field section
        self.custom_frame = QFrame()
        custom_layout = QFormLayout()
        custom_layout.setContentsMargins(0, 10, 0, 0)

        self.start_bit_spin = QSpinBox()
        self.start_bit_spin.setRange(0, 63)
        self.start_bit_spin.setValue(0)
        self.start_bit_spin.setToolTip("Start bit position (0-63)")
        custom_layout.addRow("Start Bit:", self.start_bit_spin)

        self.bit_length_spin = QSpinBox()
        self.bit_length_spin.setRange(1, 64)
        self.bit_length_spin.setValue(16)
        self.bit_length_spin.setToolTip("Bit length (1-64)")
        custom_layout.addRow("Bit Length:", self.bit_length_spin)

        self.custom_frame.setLayout(custom_layout)
        self.custom_frame.setVisible(False)  # Hidden by default
        data_layout.addRow("", self.custom_frame)

        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # Scaling group
        scale_group = QGroupBox("Scaling")
        scale_layout = QFormLayout()

        self.multiplier_spin = QDoubleSpinBox()
        self.multiplier_spin.setRange(-1000000, 1000000)
        self.multiplier_spin.setDecimals(6)
        self.multiplier_spin.setValue(1.0)
        self.multiplier_spin.setToolTip("Multiplier (value * multiplier)")
        scale_layout.addRow("Multiplier:", self.multiplier_spin)

        self.divider_spin = QDoubleSpinBox()
        self.divider_spin.setRange(0.000001, 1000000)
        self.divider_spin.setDecimals(6)
        self.divider_spin.setValue(1.0)
        self.divider_spin.setToolTip("Divider (value / divider)")
        scale_layout.addRow("Divider:", self.divider_spin)

        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(-1000000, 1000000)
        self.offset_spin.setDecimals(4)
        self.offset_spin.setValue(0.0)
        self.offset_spin.setToolTip("Offset added after multiplier/divider")
        scale_layout.addRow("Offset:", self.offset_spin)

        self.decimals_spin = QSpinBox()
        self.decimals_spin.setRange(0, 6)
        self.decimals_spin.setValue(0)
        self.decimals_spin.setToolTip("Decimal places for display")
        scale_layout.addRow("Decimal Places:", self.decimals_spin)

        scale_group.setLayout(scale_layout)
        layout.addWidget(scale_group)

        # Units group
        units_group = QGroupBox("Units & Display")
        units_layout = QFormLayout()

        self.quantity_edit = QLineEdit()
        self.quantity_edit.setPlaceholderText("e.g., Engine Speed, Temperature")
        self.quantity_edit.setToolTip("Physical quantity description")
        units_layout.addRow("Quantity:", self.quantity_edit)

        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("e.g., rpm, degC, bar")
        self.unit_edit.setToolTip("Unit of measurement")
        units_layout.addRow("Unit:", self.unit_edit)

        units_group.setLayout(units_layout)
        layout.addWidget(units_group)

        # Timeout Behavior group
        timeout_group = QGroupBox("Timeout Behavior")
        timeout_layout = QFormLayout()

        self.default_value_spin = QDoubleSpinBox()
        self.default_value_spin.setRange(-1000000, 1000000)
        self.default_value_spin.setDecimals(4)
        self.default_value_spin.setValue(0.0)
        self.default_value_spin.setToolTip("Value to use when message times out")
        timeout_layout.addRow("Default Value:", self.default_value_spin)

        self.timeout_behavior_combo = QComboBox()
        for display_name, _ in self.TIMEOUT_BEHAVIORS:
            self.timeout_behavior_combo.addItem(display_name)
        self.timeout_behavior_combo.setToolTip("What to do when CAN message times out")
        timeout_layout.addRow("On Timeout:", self.timeout_behavior_combo)

        timeout_group.setLayout(timeout_layout)
        layout.addWidget(timeout_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _on_format_changed(self, index: int):
        """Handle data format change."""
        format_value = self.DATA_FORMATS[index][1]
        self.custom_frame.setVisible(format_value == "custom")

    def _on_accept(self):
        """Validate and accept dialog."""
        # Validate ID
        channel_id = self.id_edit.text().strip()
        if not channel_id:
            QMessageBox.warning(self, "Validation Error", "Channel ID is required!")
            self.id_edit.setFocus()
            return

        # Check ID format
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', channel_id):
            QMessageBox.warning(
                self, "Validation Error",
                "Channel ID must start with a letter and contain only letters, numbers, and underscores!"
            )
            self.id_edit.setFocus()
            return

        # Check for duplicate ID
        if channel_id != self.editing_id and channel_id in self.existing_channel_ids:
            QMessageBox.warning(
                self, "Validation Error",
                f"Channel ID '{channel_id}' already exists!"
            )
            self.id_edit.setFocus()
            return

        # Validate message reference
        message_ref = self.message_combo.currentData()
        if not message_ref:
            QMessageBox.warning(
                self, "Validation Error",
                "Please select a CAN message!"
            )
            self.message_combo.setFocus()
            return

        # Validate divider
        if self.divider_spin.value() == 0:
            QMessageBox.warning(
                self, "Validation Error",
                "Divider cannot be zero!"
            )
            self.divider_spin.setFocus()
            return

        self.accept()

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.id_edit.setText(config.get("id", ""))

        # Message reference
        message_ref = config.get("message_ref", "")
        idx = self.message_combo.findData(message_ref)
        if idx >= 0:
            self.message_combo.setCurrentIndex(idx)

        # Frame offset
        self.frame_offset_spin.setValue(config.get("frame_offset", 0))

        # Data type
        data_type = config.get("data_type", "unsigned")
        if isinstance(data_type, str):
            for i, (_, value) in enumerate(self.DATA_TYPES):
                if value == data_type:
                    self.data_type_combo.setCurrentIndex(i)
                    break

        # Data format
        data_format = config.get("data_format", "16bit")
        if isinstance(data_format, str):
            for i, (_, value) in enumerate(self.DATA_FORMATS):
                if value == data_format:
                    self.data_format_combo.setCurrentIndex(i)
                    break

        # Byte order
        byte_order = config.get("byte_order", "little_endian")
        for i, (_, value) in enumerate(self.BYTE_ORDERS):
            if value == byte_order:
                self.byte_order_combo.setCurrentIndex(i)
                break

        # Byte offset
        self.byte_offset_spin.setValue(config.get("byte_offset", 0))

        # Custom bitfield
        self.start_bit_spin.setValue(config.get("start_bit", 0))
        self.bit_length_spin.setValue(config.get("bit_length", 16))

        # Scaling
        self.multiplier_spin.setValue(config.get("multiplier", 1.0))
        self.divider_spin.setValue(config.get("divider", 1.0))
        self.offset_spin.setValue(config.get("offset", 0.0))
        self.decimals_spin.setValue(config.get("decimal_places", 0))

        # Units
        self.quantity_edit.setText(config.get("quantity", ""))
        self.unit_edit.setText(config.get("unit", ""))

        # Timeout behavior
        self.default_value_spin.setValue(config.get("default_value", 0.0))
        timeout_behavior = config.get("timeout_behavior", "use_default")
        if isinstance(timeout_behavior, str):
            for i, (_, value) in enumerate(self.TIMEOUT_BEHAVIORS):
                if value == timeout_behavior:
                    self.timeout_behavior_combo.setCurrentIndex(i)
                    break

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        data_type_index = self.data_type_combo.currentIndex()
        data_type = self.DATA_TYPES[data_type_index][1]

        data_format_index = self.data_format_combo.currentIndex()
        data_format = self.DATA_FORMATS[data_format_index][1]

        byte_order_index = self.byte_order_combo.currentIndex()
        byte_order = self.BYTE_ORDERS[byte_order_index][1]

        timeout_behavior_index = self.timeout_behavior_combo.currentIndex()
        timeout_behavior = self.TIMEOUT_BEHAVIORS[timeout_behavior_index][1]

        config = {
            "id": self.id_edit.text().strip(),
            "channel_type": "can_rx",
            "message_ref": self.message_combo.currentData() or "",
            "frame_offset": self.frame_offset_spin.value(),
            "data_type": data_type,
            "data_format": data_format,
            "byte_order": byte_order,
            "byte_offset": self.byte_offset_spin.value(),
            "start_bit": self.start_bit_spin.value(),
            "bit_length": self.bit_length_spin.value(),
            "multiplier": self.multiplier_spin.value(),
            "divider": self.divider_spin.value(),
            "offset": self.offset_spin.value(),
            "decimal_places": self.decimals_spin.value(),
            "quantity": self.quantity_edit.text().strip(),
            "unit": self.unit_edit.text().strip(),
            "default_value": self.default_value_spin.value(),
            "timeout_behavior": timeout_behavior,
        }

        return config

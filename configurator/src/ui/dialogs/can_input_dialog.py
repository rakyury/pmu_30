"""
CAN Input (Signal) Configuration Dialog
Configures a CAN Input channel (Level 2) - signal extraction from CAN Message

References a CAN Message Object and defines how to extract a signal value.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox,
    QLabel, QCheckBox, QMessageBox, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List

import logging

from models.channel_display_service import ChannelIdGenerator
from models.quantities import get_quantity_names, get_units_for_quantity, get_default_unit
from ui.widgets.constant_spinbox import ConstantSpinBox

logger = logging.getLogger(__name__)


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

    # CAN Input Signal Templates (Link ECU Generic Dashboard)
    TEMPLATES = {
        "Link: Engine RPM": {
            "id": "crx_ecu_rpm", "frame_offset": 0, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 2, "multiplier": 1.0, "divider": 1.0,
            "offset": 0.0, "decimal_places": 0, "default_value": 0.0, "timeout_behavior": "use_default"
        },
        "Link: MAP (kPa)": {
            "id": "crx_ecu_map", "frame_offset": 0, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 4, "multiplier": 1.0, "divider": 10.0,
            "offset": 0.0, "decimal_places": 1, "default_value": 101.0, "timeout_behavior": "use_default"
        },
        "Link: TPS (%)": {
            "id": "crx_ecu_tps", "frame_offset": 1, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 4, "multiplier": 1.0, "divider": 10.0,
            "offset": 0.0, "decimal_places": 1, "default_value": 0.0, "timeout_behavior": "use_default"
        },
        "Link: Baro (kPa)": {
            "id": "crx_ecu_baro", "frame_offset": 1, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 2, "multiplier": 1.0, "divider": 10.0,
            "offset": 0.0, "decimal_places": 1, "default_value": 101.0, "timeout_behavior": "use_default"
        },
        "Link: Injector Duty (%)": {
            "id": "crx_ecu_injdc", "frame_offset": 1, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 6, "multiplier": 1.0, "divider": 10.0,
            "offset": 0.0, "decimal_places": 1, "default_value": 0.0, "timeout_behavior": "use_default"
        },
        "Link: Coolant Temp (°C)": {
            "id": "crx_ecu_clt", "frame_offset": 2, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 6, "multiplier": 1.0, "divider": 10.0,
            "offset": -50.0, "decimal_places": 1, "default_value": 20.0, "timeout_behavior": "use_default"
        },
        "Link: Intake Air Temp (°C)": {
            "id": "crx_ecu_iat", "frame_offset": 3, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 2, "multiplier": 1.0, "divider": 10.0,
            "offset": -50.0, "decimal_places": 1, "default_value": 20.0, "timeout_behavior": "use_default"
        },
        "Link: Battery Voltage": {
            "id": "crx_ecu_batt", "frame_offset": 3, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 4, "multiplier": 1.0, "divider": 100.0,
            "offset": 0.0, "decimal_places": 2, "default_value": 12.0, "timeout_behavior": "use_default"
        },
        "Link: Gear": {
            "id": "crx_ecu_gear", "frame_offset": 4, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 2, "multiplier": 1.0, "divider": 1.0,
            "offset": 0.0, "decimal_places": 0, "default_value": 0.0, "timeout_behavior": "use_default"
        },
        "Link: Ignition Angle (°)": {
            "id": "crx_ecu_ign", "frame_offset": 4, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 6, "multiplier": 1.0, "divider": 10.0,
            "offset": -100.0, "decimal_places": 1, "default_value": 0.0, "timeout_behavior": "use_default"
        },
        "Link: Lambda 1": {
            "id": "crx_ecu_lambda1", "frame_offset": 6, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 4, "multiplier": 1.0, "divider": 1000.0,
            "offset": 0.0, "decimal_places": 3, "default_value": 1.0, "timeout_behavior": "use_default"
        },
        "Link: Lambda 2": {
            "id": "crx_ecu_lambda2", "frame_offset": 6, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 6, "multiplier": 1.0, "divider": 1000.0,
            "offset": 0.0, "decimal_places": 3, "default_value": 1.0, "timeout_behavior": "use_default"
        },
        "Link: Fuel Pressure (bar)": {
            "id": "crx_ecu_fuelp", "frame_offset": 7, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 6, "multiplier": 1.0, "divider": 10.0,
            "offset": 0.0, "decimal_places": 2, "default_value": 3.0, "timeout_behavior": "use_default"
        },
        "Link: Oil Temp (°C)": {
            "id": "crx_ecu_oilt", "frame_offset": 0, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 2, "multiplier": 1.0, "divider": 10.0,
            "offset": -50.0, "decimal_places": 1, "default_value": 20.0, "timeout_behavior": "use_default",
            "_note": "Frame offset 0 from m_linkecu_B (base + 8)"
        },
        "Link: Oil Pressure (bar)": {
            "id": "crx_ecu_oilp", "frame_offset": 0, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 4, "multiplier": 1.0, "divider": 100.0,
            "offset": 0.0, "decimal_places": 2, "default_value": 0.0, "timeout_behavior": "use_default",
            "_note": "Frame offset 0 from m_linkecu_B (base + 8)"
        },
        "Link: Vehicle Speed (km/h)": {
            "id": "crx_ecu_speed", "frame_offset": 1, "data_type": "unsigned", "data_format": "16bit",
            "byte_order": "little_endian", "byte_offset": 6, "multiplier": 1.0, "divider": 10.0,
            "offset": 0.0, "decimal_places": 1, "default_value": 0.0, "timeout_behavior": "use_default",
            "_note": "Frame offset 1 from m_linkecu_B (base + 9)"
        },
    }

    def __init__(self, parent=None, input_config: Optional[Dict[str, Any]] = None,
                 message_ids: Optional[List[str]] = None,
                 existing_channel_ids: Optional[List[str]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize CAN Input Dialog.

        Args:
            parent: Parent widget
            input_config: Existing input configuration (for editing)
            message_ids: List of available CAN message IDs
            existing_channel_ids: List of existing channel IDs (for name validation)
            existing_channels: List of all existing channel configs (for channel_id generation)
        """
        super().__init__(parent)
        self.input_config = input_config
        self.message_ids = message_ids or []
        self.existing_channel_ids = existing_channel_ids or []
        self.existing_channels = existing_channels or []
        # For backwards compatibility, try 'name' first, fall back to 'id'
        self.editing_name = (input_config.get("name", "") or input_config.get("id", "")) if input_config else ""

        # Generate or load channel_id (must be positive integer, 0 means not assigned)
        existing_ch_id = input_config.get("channel_id") if input_config else None
        if isinstance(existing_ch_id, int) and existing_ch_id > 0:
            self._channel_id = existing_ch_id
        else:
            self._channel_id = ChannelIdGenerator.get_next_channel_id(self.existing_channels)

        self.setWindowTitle("CAN Input" if not input_config else f"Edit CAN Input: {self.editing_name}")
        self.setModal(True)
        self.resize(182, 333)  # Very compact (10% narrower)

        self._init_ui()

        if input_config:
            self._load_config(input_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Template selection (only for new inputs)
        if not self.input_config:
            template_group = QGroupBox("Quick Start from Template")
            template_layout = QHBoxLayout()

            template_layout.addWidget(QLabel("Template:"))

            self.template_combo = QComboBox()
            self.template_combo.addItem("-- Select Template --")
            for name in self.TEMPLATES.keys():
                self.template_combo.addItem(name)
            self.template_combo.currentTextChanged.connect(self._on_template_selected)
            template_layout.addWidget(self.template_combo, 1)

            template_group.setLayout(template_layout)
            layout.addWidget(template_group)

        # Identification group
        id_group = QGroupBox("Identification")
        id_layout = QFormLayout()

        # Channel ID (read-only, shown when editing)
        if self.input_config:
            self.channel_id_label = QLabel(str(self._channel_id))
            self.channel_id_label.setStyleSheet("font-weight: bold; color: #b0b0b0;")
            id_layout.addRow("Channel ID:", self.channel_id_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., EngineRPM, CoolantTemp")
        self.name_edit.setToolTip("Unique channel name")
        id_layout.addRow("Name: *", self.name_edit)

        id_group.setLayout(id_layout)
        layout.addWidget(id_group)

        # Message Reference group
        msg_group = QGroupBox("Message Reference")
        msg_layout = QFormLayout()

        self.message_combo = QComboBox()

        # When editing, ensure the current message_ref is in the list even if not in message_ids
        effective_message_ids = list(self.message_ids)
        if self.input_config:
            current_ref = self.input_config.get("message_ref", "")
            if current_ref and current_ref not in effective_message_ids:
                effective_message_ids.insert(0, current_ref)
                logger.warning(f"Message ref '{current_ref}' not in available messages, adding to list")

        if not effective_message_ids:
            self.message_combo.addItem("(No messages available)", "")
            self.message_combo.setEnabled(False)
        else:
            self.message_combo.addItem("-- Select Message --", "")
            for msg_id in effective_message_ids:
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

        # Scaling group - integer values
        scale_group = QGroupBox("Scaling")
        scale_layout = QFormLayout()

        self.multiplier_spin = QSpinBox()
        self.multiplier_spin.setRange(-1000000, 1000000)
        self.multiplier_spin.setValue(1)
        self.multiplier_spin.setToolTip("Multiplier (value * multiplier)")
        scale_layout.addRow("Multiplier:", self.multiplier_spin)

        self.divider_spin = QSpinBox()
        self.divider_spin.setRange(1, 1000000)
        self.divider_spin.setValue(1)
        self.divider_spin.setToolTip("Divider (value / divider)")
        scale_layout.addRow("Divider:", self.divider_spin)

        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(-1000000, 1000000)
        self.offset_spin.setValue(0)
        self.offset_spin.setToolTip("Offset added after multiplier/divider")
        scale_layout.addRow("Offset:", self.offset_spin)

        self.decimals_spin = QSpinBox()
        self.decimals_spin.setRange(0, 6)
        self.decimals_spin.setValue(0)
        self.decimals_spin.setToolTip("Decimal places for display")
        scale_layout.addRow("Decimal Places:", self.decimals_spin)

        # Quantity/Unit selection
        qu_container = QWidget()
        qu_layout = QHBoxLayout(qu_container)
        qu_layout.setContentsMargins(0, 0, 0, 0)
        qu_layout.setSpacing(4)

        self.quantity_combo = QComboBox()
        self.quantity_combo.setMinimumWidth(120)
        for name in get_quantity_names():
            self.quantity_combo.addItem(name)
        self.quantity_combo.currentTextChanged.connect(self._on_quantity_changed)
        qu_layout.addWidget(self.quantity_combo)

        self.unit_combo = QComboBox()
        self.unit_combo.setMinimumWidth(70)
        qu_layout.addWidget(self.unit_combo)

        scale_layout.addRow("Quantity/Unit:", qu_container)

        # Initialize units for default quantity
        self._on_quantity_changed(self.quantity_combo.currentText())

        scale_group.setLayout(scale_layout)
        layout.addWidget(scale_group)

        # Timeout Behavior group
        timeout_group = QGroupBox("Timeout Behavior")
        timeout_layout = QFormLayout()

        self.default_value_spin = ConstantSpinBox()
        self.default_value_spin.setRange(-10000.00, 10000.00)
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

    def _on_template_selected(self, template_name: str):
        """Handle template selection."""
        if template_name == "-- Select Template --":
            return

        if template_name in self.TEMPLATES:
            template = self.TEMPLATES[template_name].copy()

            # Remove internal notes
            template.pop("_note", None)

            # Check if name already exists and modify if needed
            base_name = template.get("name", "") or template.get("id", "CANInput")
            final_name = base_name
            counter = 1
            while final_name in self.existing_channel_ids:
                final_name = f"{base_name}_{counter}"
                counter += 1
            template["name"] = final_name

            # Load the template configuration
            self._load_config(template)

    def _on_accept(self):
        """Validate and accept dialog."""
        # Validate name
        channel_name = self.name_edit.text().strip()
        if not channel_name:
            QMessageBox.warning(self, "Validation Error", "Channel name is required!")
            self.name_edit.setFocus()
            return

        # Check name format - allow most characters except problematic ones
        forbidden_chars = '"\'\\;{}[]'
        if not channel_name[0].isalpha() and channel_name[0] != '_':
            QMessageBox.warning(
                self, "Validation Error",
                "Name must start with a letter or underscore!"
            )
            self.name_edit.setFocus()
            return
        if any(c in channel_name for c in forbidden_chars):
            QMessageBox.warning(
                self, "Validation Error",
                "Name cannot contain: \" ' \\ ; { } [ ]"
            )
            self.name_edit.setFocus()
            return

        # Check for duplicate name
        if channel_name != self.editing_name and channel_name in self.existing_channel_ids:
            QMessageBox.warning(
                self, "Validation Error",
                f"Channel name '{channel_name}' already exists!"
            )
            self.name_edit.setFocus()
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

    def _on_quantity_changed(self, quantity: str):
        """Update available units when quantity changes."""
        units = get_units_for_quantity(quantity)
        default_unit = get_default_unit(quantity)

        self.unit_combo.clear()
        for unit in units:
            self.unit_combo.addItem(unit.symbol)

        index = self.unit_combo.findText(default_unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        logger.debug(f"CANInputDialog._load_config: config={config}")
        logger.debug(f"CANInputDialog._load_config: message_ids={self.message_ids}")

        # For backwards compatibility, try 'name' first, fall back to 'id'
        name = config.get("name", "") or config.get("id", "")
        self.name_edit.setText(name)

        # Message reference
        message_ref = config.get("message_ref", "")
        logger.debug(f"CANInputDialog._load_config: message_ref='{message_ref}'")

        # List all combo items for debugging
        combo_items = [(self.message_combo.itemText(i), self.message_combo.itemData(i))
                       for i in range(self.message_combo.count())]
        logger.debug(f"CANInputDialog._load_config: combo items={combo_items}")

        idx = self.message_combo.findData(message_ref)
        logger.debug(f"CANInputDialog._load_config: findData('{message_ref}') = {idx}")

        if idx >= 0:
            self.message_combo.setCurrentIndex(idx)
        else:
            logger.warning(f"Message ref '{message_ref}' not found in combo. Available: {[item[1] for item in combo_items]}")

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

        # Scaling (integer values)
        self.multiplier_spin.setValue(int(config.get("multiplier", 1)))
        self.divider_spin.setValue(max(1, int(config.get("divider", 1))))
        self.offset_spin.setValue(int(config.get("offset", 0)))
        self.decimals_spin.setValue(config.get("decimal_places", 0))

        # Quantity/Unit
        quantity = config.get("quantity", "User")
        index = self.quantity_combo.findText(quantity)
        if index >= 0:
            self.quantity_combo.setCurrentIndex(index)
        unit = config.get("unit", "user")
        index = self.unit_combo.findText(unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

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
            "channel_id": self._channel_id,
            "name": self.name_edit.text().strip(),
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
            "quantity": self.quantity_combo.currentText(),
            "unit": self.unit_combo.currentText(),
            "default_value": self.default_value_spin.value(),
            "timeout_behavior": timeout_behavior,
        }

        return config

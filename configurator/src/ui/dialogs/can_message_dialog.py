"""
CAN Message Object Configuration Dialog
Configures a CAN Message Object (Level 1) - frame properties only

Signals are configured separately in CAN Input Dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QLabel,
    QCheckBox, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional, List


class CANMessageDialog(QDialog):
    """Dialog for configuring a CAN Message Object (Level 1)."""

    MESSAGE_TYPES = [
        ("Normal", "normal"),
        ("Compound (Multiplexed)", "compound"),
        ("PMU1 RX Format", "pmu1_rx"),
        ("PMU2 RX Format", "pmu2_rx"),
        ("PMU3 RX Format", "pmu3_rx"),
    ]

    # CAN Message Templates
    TEMPLATES = {
        "Link ECU Generic Dashboard": {
            "id": "msg_link_dash",
            "name": "Link ECU Generic Dashboard",
            "can_bus": 1,
            "base_id": 0x3E8,
            "is_extended": False,
            "message_type": "compound",
            "frame_count": 8,
            "dlc": 8,
            "timeout_ms": 200,
            "enabled": True,
            "description": "Link ECU Generic Dashboard stream (frames 0-7). Compound message with frame index in byte 0."
        },
        "Link ECU Generic Dashboard 2": {
            "id": "msg_link_dash2",
            "name": "Link ECU Generic Dashboard 2",
            "can_bus": 1,
            "base_id": 0x3E8,
            "is_extended": False,
            "message_type": "compound",
            "frame_count": 8,
            "dlc": 8,
            "timeout_ms": 200,
            "enabled": True,
            "description": "Link ECU Generic Dashboard 2 stream (frames 8-15). Extended data including oil temp/press, wheel speeds, knock levels."
        },
        "ECUMaster PMU Status": {
            "id": "msg_pmu_status",
            "name": "ECUMaster PMU Status",
            "can_bus": 1,
            "base_id": 0x600,
            "is_extended": False,
            "message_type": "compound",
            "frame_count": 8,
            "dlc": 8,
            "timeout_ms": 100,
            "enabled": True,
            "description": "ECUMaster PMU Standard CAN Stream - status, outputs, currents, voltages."
        },
        "AEM CD-7 Dash": {
            "id": "msg_aem_cd7",
            "name": "AEM CD-7 Dashboard",
            "can_bus": 1,
            "base_id": 0x1F0,
            "is_extended": False,
            "message_type": "normal",
            "frame_count": 1,
            "dlc": 8,
            "timeout_ms": 100,
            "enabled": True,
            "description": "AEM CD-7 Dashboard input message."
        },
        "MoTeC M1 Series": {
            "id": "msg_motec_m1",
            "name": "MoTeC M1 Telemetry",
            "can_bus": 1,
            "base_id": 0x640,
            "is_extended": False,
            "message_type": "compound",
            "frame_count": 8,
            "dlc": 8,
            "timeout_ms": 50,
            "enabled": True,
            "description": "MoTeC M1 Series ECU telemetry stream."
        },
    }

    def __init__(self, parent=None, message_config: Optional[Dict[str, Any]] = None,
                 existing_ids: Optional[List[str]] = None):
        """
        Initialize CAN Message Dialog.

        Args:
            parent: Parent widget
            message_config: Existing message configuration (for editing)
            existing_ids: List of existing message IDs (for validation)
        """
        super().__init__(parent)
        self.message_config = message_config
        self.existing_ids = existing_ids or []
        # For backwards compatibility, try 'name' first, fall back to 'id'
        self.editing_name = (message_config.get("name", "") or message_config.get("id", "")) if message_config else ""

        self.setWindowTitle("CAN Message Object" if not message_config else f"Edit CAN Message: {self.editing_name}")
        self.setModal(True)
        self.resize(500, 450)

        self._init_ui()

        if message_config:
            self._load_config(message_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Template selection (only for new messages)
        if not self.message_config:
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

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., ECU_Base, LinkDash")
        self.name_edit.setToolTip("Unique name for this message")
        id_layout.addRow("Name: *", self.name_edit)

        id_group.setLayout(id_layout)
        layout.addWidget(id_group)

        # CAN Settings group
        can_group = QGroupBox("CAN Settings")
        can_layout = QFormLayout()

        # CAN Bus
        self.can_bus_combo = QComboBox()
        self.can_bus_combo.addItems(["CAN 1", "CAN 2", "CAN 3", "CAN 4"])
        self.can_bus_combo.setToolTip("Select CAN bus (1-4)")
        can_layout.addRow("CAN Bus:", self.can_bus_combo)

        # Base ID with hex display
        id_row_layout = QHBoxLayout()
        self.base_id_spin = QSpinBox()
        self.base_id_spin.setRange(0, 0x7FF)
        self.base_id_spin.setDisplayIntegerBase(16)
        self.base_id_spin.setPrefix("0x")
        self.base_id_spin.setToolTip("CAN Message ID (hex)")
        id_row_layout.addWidget(self.base_id_spin)

        self.extended_check = QCheckBox("Extended (29-bit)")
        self.extended_check.toggled.connect(self._on_extended_toggled)
        id_row_layout.addWidget(self.extended_check)

        can_layout.addRow("Base ID:", id_row_layout)

        # Message Type
        self.type_combo = QComboBox()
        for display_name, _ in self.MESSAGE_TYPES:
            self.type_combo.addItem(display_name)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.type_combo.setToolTip("Message type (Normal for single-frame, Compound for multiplexed)")
        can_layout.addRow("Type:", self.type_combo)

        # Frame Count (for compound)
        self.frame_count_spin = QSpinBox()
        self.frame_count_spin.setRange(1, 8)
        self.frame_count_spin.setValue(1)
        self.frame_count_spin.setToolTip("Number of frames for compound/multiplexed messages")
        self.frame_count_spin.setEnabled(False)
        can_layout.addRow("Frame Count:", self.frame_count_spin)

        # DLC
        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 64)
        self.dlc_spin.setValue(8)
        self.dlc_spin.setToolTip("Data Length Code (bytes per frame)")
        can_layout.addRow("DLC:", self.dlc_spin)

        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 65535)
        self.timeout_spin.setValue(500)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setToolTip("Reception timeout (0 = no timeout)")
        can_layout.addRow("Timeout:", self.timeout_spin)

        # Enabled
        self.enabled_check = QCheckBox("Message enabled")
        self.enabled_check.setChecked(True)
        can_layout.addRow("", self.enabled_check)

        can_group.setLayout(can_layout)
        layout.addWidget(can_group)

        # Description group
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout()

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Optional description...")
        desc_layout.addWidget(self.description_edit)

        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)

        # Info label
        info_label = QLabel(
            "<i>Note: Signals are configured separately using CAN Inputs.</i>"
        )
        info_label.setStyleSheet("color: #b0b0b0;")
        layout.addWidget(info_label)

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

    def _on_extended_toggled(self, extended: bool):
        """Handle extended ID checkbox toggle."""
        if extended:
            self.base_id_spin.setRange(0, 0x1FFFFFFF)  # Extended CAN ID (29-bit)
        else:
            self.base_id_spin.setRange(0, 0x7FF)  # Standard CAN ID (11-bit)
            # Clamp current value if needed
            if self.base_id_spin.value() > 0x7FF:
                self.base_id_spin.setValue(0x7FF)

    def _on_type_changed(self, index: int):
        """Handle message type change."""
        # Enable frame count only for compound type
        msg_type = self.MESSAGE_TYPES[index][1]
        self.frame_count_spin.setEnabled(msg_type == "compound")
        if msg_type != "compound":
            self.frame_count_spin.setValue(1)

    def _on_template_selected(self, template_name: str):
        """Handle template selection."""
        if template_name == "-- Select Template --":
            return

        if template_name in self.TEMPLATES:
            template = self.TEMPLATES[template_name].copy()

            # Check if name already exists and modify if needed
            base_name = template.get("name", "") or template.get("id", "msg_template")
            final_name = base_name
            counter = 1
            while final_name in self.existing_ids:
                final_name = f"{base_name}_{counter}"
                counter += 1
            template["name"] = final_name

            # Load the template configuration
            self._load_config(template)

    def _on_accept(self):
        """Validate and accept dialog."""
        # Validate name
        msg_name = self.name_edit.text().strip()
        if not msg_name:
            QMessageBox.warning(self, "Validation Error", "Message name is required!")
            self.name_edit.setFocus()
            return

        # Check name format - allow most characters except problematic ones
        forbidden_chars = '"\'\\;{}[]'
        if not msg_name[0].isalpha() and msg_name[0] != '_':
            QMessageBox.warning(
                self, "Validation Error",
                "Name must start with a letter or underscore!"
            )
            self.name_edit.setFocus()
            return
        if any(c in msg_name for c in forbidden_chars):
            QMessageBox.warning(
                self, "Validation Error",
                "Name cannot contain: \" ' \\ ; { } [ ]"
            )
            self.name_edit.setFocus()
            return

        # Check for duplicate name (only if creating new or name changed)
        if msg_name != self.editing_name and msg_name in self.existing_ids:
            QMessageBox.warning(
                self, "Validation Error",
                f"Message name '{msg_name}' already exists!"
            )
            self.name_edit.setFocus()
            return

        self.accept()

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        # Name is the primary identifier - try 'name' first, fall back to 'id' for backwards compatibility
        name = config.get("name", "") or config.get("id", "")
        self.name_edit.setText(name)

        # CAN Bus (1-4 -> index 0-3)
        can_bus = config.get("can_bus", 1)
        self.can_bus_combo.setCurrentIndex(can_bus - 1)

        # Base ID and extended
        is_extended = config.get("is_extended", False)
        self.extended_check.setChecked(is_extended)
        self.base_id_spin.setValue(config.get("base_id", 0))

        # Message Type
        msg_type = config.get("message_type", "normal")
        for i, (_, value) in enumerate(self.MESSAGE_TYPES):
            if value == msg_type:
                self.type_combo.setCurrentIndex(i)
                break

        # Frame Count
        self.frame_count_spin.setValue(config.get("frame_count", 1))

        # DLC
        self.dlc_spin.setValue(config.get("dlc", 8))

        # Timeout
        self.timeout_spin.setValue(config.get("timeout_ms", 500))

        # Enabled
        self.enabled_check.setChecked(config.get("enabled", True))

        # Description
        self.description_edit.setPlainText(config.get("description", ""))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        msg_type_index = self.type_combo.currentIndex()
        msg_type = self.MESSAGE_TYPES[msg_type_index][1]

        name = self.name_edit.text().strip()
        config = {
            "name": name,  # Primary identifier - unique, user-editable
            "can_bus": self.can_bus_combo.currentIndex() + 1,  # 0-3 -> 1-4
            "base_id": self.base_id_spin.value(),
            "is_extended": self.extended_check.isChecked(),
            "message_type": msg_type,
            "frame_count": self.frame_count_spin.value(),
            "dlc": self.dlc_spin.value(),
            "timeout_ms": self.timeout_spin.value(),
            "enabled": self.enabled_check.isChecked(),
            "description": self.description_edit.toPlainText().strip()
        }

        return config

"""
CAN Output (TX) Configuration Dialog

Combines message properties with signal mapping in one dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QLabel,
    QCheckBox, QMessageBox, QGroupBox, QFrame, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any, Optional, List
import re


class ChannelSlotWidget(QFrame):
    """Widget for a single channel slot in CAN TX message."""

    channel_browse_requested = pyqtSignal(int)  # slot index

    DATA_TYPES = [
        ("8bit unsigned", "8bit_unsigned"),
        ("8bit signed", "8bit_signed"),
        ("16bit big endian", "16bit_be"),
        ("16bit little endian", "16bit_le"),
        ("32bit big endian", "32bit_be"),
        ("32bit little endian", "32bit_le"),
    ]

    MULTIPLIERS = [
        ("*1", 1.0),
        ("*0.1", 0.1),
        ("*0.01", 0.01),
        ("*10", 10.0),
        ("*100", 100.0),
    ]

    def __init__(self, slot_index: int, parent=None):
        super().__init__(parent)
        self.slot_index = slot_index
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # Label
        label = QLabel(f"Channel #{self.slot_index}:")
        label.setFixedWidth(80)
        layout.addWidget(label)

        # Data type dropdown
        self.type_combo = QComboBox()
        self.type_combo.setFixedWidth(130)
        for display_name, _ in self.DATA_TYPES:
            self.type_combo.addItem(display_name)
        layout.addWidget(self.type_combo)

        # Channel source field
        self.channel_edit = QLineEdit()
        self.channel_edit.setPlaceholderText("Channel...")
        layout.addWidget(self.channel_edit, 1)

        # Browse button
        self.browse_btn = QPushButton("...")
        self.browse_btn.setFixedWidth(30)
        self.browse_btn.clicked.connect(lambda: self.channel_browse_requested.emit(self.slot_index))
        layout.addWidget(self.browse_btn)

        # Multiplier dropdown
        self.mult_combo = QComboBox()
        self.mult_combo.setFixedWidth(70)
        for display_name, _ in self.MULTIPLIERS:
            self.mult_combo.addItem(display_name)
        layout.addWidget(self.mult_combo)

    def set_enabled(self, enabled: bool):
        """Enable or disable this slot."""
        self.type_combo.setEnabled(enabled)
        self.channel_edit.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.mult_combo.setEnabled(enabled)

    def get_config(self) -> Dict[str, Any]:
        """Get configuration for this slot."""
        type_index = self.type_combo.currentIndex()
        mult_index = self.mult_combo.currentIndex()

        return {
            "data_type": self.DATA_TYPES[type_index][1],
            "channel": self.channel_edit.text().strip(),
            "multiplier": self.MULTIPLIERS[mult_index][1],
        }

    def set_config(self, config: Dict[str, Any]):
        """Set configuration for this slot."""
        # Data type
        data_type = config.get("data_type", "8bit_unsigned")
        for i, (_, value) in enumerate(self.DATA_TYPES):
            if value == data_type:
                self.type_combo.setCurrentIndex(i)
                break

        # Channel
        self.channel_edit.setText(config.get("channel", ""))

        # Multiplier
        mult = config.get("multiplier", 1.0)
        for i, (_, value) in enumerate(self.MULTIPLIERS):
            if abs(value - mult) < 0.001:
                self.mult_combo.setCurrentIndex(i)
                break

    def set_channel(self, channel_id: str):
        """Set the channel ID."""
        self.channel_edit.setText(channel_id)


class CANOutputDialog(QDialog):
    """Dialog for configuring CAN TX output."""

    TRANSMIT_MODES = [
        ("Cycle", "cycle"),
        ("Triggered", "triggered"),
    ]

    TRIGGER_EDGES = [
        ("Rising", "rising"),
        ("Falling", "falling"),
        ("Both", "both"),
    ]

    def __init__(self, parent=None, output_config: Optional[Dict[str, Any]] = None,
                 existing_ids: Optional[List[str]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None):
        """
        Initialize CAN Output Dialog.

        Args:
            parent: Parent widget
            output_config: Existing configuration (for editing)
            existing_ids: List of existing output IDs (for validation)
            available_channels: Dict of channel categories to channel IDs
        """
        super().__init__(parent)
        self.output_config = output_config
        self.existing_ids = existing_ids or []
        self.available_channels = available_channels or {}
        # For backwards compatibility, try 'name' first, fall back to 'id'
        self.editing_name = (output_config.get("name", "") or output_config.get("id", "")) if output_config else ""

        self.setWindowTitle("CAN Output" if not output_config else f"Edit CAN Output: {self.editing_name}")
        self.setModal(True)
        self.resize(650, 550)

        self.channel_slots: List[ChannelSlotWidget] = []

        self._init_ui()

        if output_config:
            self._load_config(output_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header row with Name
        header_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., tx_engine_data")
        header_layout.addRow("Name:", self.name_edit)
        layout.addLayout(header_layout)

        # Message settings row
        msg_layout = QHBoxLayout()

        # CAN Bus
        msg_layout.addWidget(QLabel("CANbus:"))
        self.can_bus_combo = QComboBox()
        self.can_bus_combo.addItems(["CAN1", "CAN2"])
        self.can_bus_combo.setFixedWidth(80)
        msg_layout.addWidget(self.can_bus_combo)

        msg_layout.addSpacing(10)

        # ID (hex)
        msg_layout.addWidget(QLabel("ID (hex):"))
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("0x100")
        self.id_edit.setFixedWidth(100)
        msg_layout.addWidget(self.id_edit)

        msg_layout.addSpacing(10)

        # Standard/Extended
        self.frame_type_combo = QComboBox()
        self.frame_type_combo.addItems(["Standard", "Extended"])
        self.frame_type_combo.setFixedWidth(90)
        msg_layout.addWidget(self.frame_type_combo)

        msg_layout.addSpacing(10)

        # DLC
        msg_layout.addWidget(QLabel("DLC:"))
        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 8)
        self.dlc_spin.setValue(8)
        self.dlc_spin.setFixedWidth(50)
        self.dlc_spin.valueChanged.connect(self._on_dlc_changed)
        msg_layout.addWidget(self.dlc_spin)

        msg_layout.addStretch()

        layout.addLayout(msg_layout)

        # Transmit mode row
        tx_layout = QHBoxLayout()

        tx_layout.addWidget(QLabel("Transmit mode:"))
        self.tx_mode_combo = QComboBox()
        for display_name, _ in self.TRANSMIT_MODES:
            self.tx_mode_combo.addItem(display_name)
        self.tx_mode_combo.setFixedWidth(100)
        self.tx_mode_combo.currentIndexChanged.connect(self._on_tx_mode_changed)
        tx_layout.addWidget(self.tx_mode_combo)

        tx_layout.addSpacing(20)

        # Cycle mode widgets
        self.freq_label = QLabel("Frequency [Hz]:")
        tx_layout.addWidget(self.freq_label)
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(1, 1000)
        self.freq_spin.setValue(10)
        self.freq_spin.setFixedWidth(70)
        tx_layout.addWidget(self.freq_spin)

        # Triggered mode widgets (hidden by default)
        self.edge_label = QLabel("Edge:")
        self.edge_label.setVisible(False)
        tx_layout.addWidget(self.edge_label)
        self.edge_combo = QComboBox()
        for display_name, _ in self.TRIGGER_EDGES:
            self.edge_combo.addItem(display_name)
        self.edge_combo.setFixedWidth(80)
        self.edge_combo.setVisible(False)
        tx_layout.addWidget(self.edge_combo)

        self.trigger_channel_label = QLabel("Channel:")
        self.trigger_channel_label.setVisible(False)
        tx_layout.addWidget(self.trigger_channel_label)
        self.trigger_channel_edit = QLineEdit()
        self.trigger_channel_edit.setFixedWidth(150)
        self.trigger_channel_edit.setVisible(False)
        tx_layout.addWidget(self.trigger_channel_edit)

        self.trigger_browse_btn = QPushButton("...")
        self.trigger_browse_btn.setFixedWidth(30)
        self.trigger_browse_btn.setVisible(False)
        self.trigger_browse_btn.clicked.connect(self._browse_trigger_channel)
        tx_layout.addWidget(self.trigger_browse_btn)

        tx_layout.addStretch()

        layout.addLayout(tx_layout)

        layout.addSpacing(10)

        # Channel slots (8 slots for 8 bytes)
        slots_frame = QFrame()
        slots_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        slots_layout = QVBoxLayout(slots_frame)
        slots_layout.setSpacing(4)

        for i in range(8):
            slot = ChannelSlotWidget(i, self)
            slot.channel_browse_requested.connect(self._on_channel_browse_requested)
            self.channel_slots.append(slot)
            slots_layout.addWidget(slot)

        layout.addWidget(slots_frame)

        layout.addSpacing(10)

        # Buttons row
        button_layout = QHBoxLayout()

        self.save_canx_btn = QPushButton("Save .CANX File")
        self.save_canx_btn.clicked.connect(self._save_canx)
        button_layout.addWidget(self.save_canx_btn)

        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        # Initialize slot states based on DLC
        self._on_dlc_changed(self.dlc_spin.value())

    def _on_dlc_changed(self, dlc: int):
        """Update channel slot availability based on DLC."""
        # Calculate how many bytes each slot uses
        # For simplicity, we'll enable/disable based on byte position
        # This is approximate - actual behavior depends on data types
        for i, slot in enumerate(self.channel_slots):
            # Enable if slot index is less than DLC
            slot.set_enabled(i < dlc)

    def _on_tx_mode_changed(self, index: int):
        """Handle transmit mode change."""
        is_cycle = self.TRANSMIT_MODES[index][1] == "cycle"

        # Show/hide cycle widgets
        self.freq_label.setVisible(is_cycle)
        self.freq_spin.setVisible(is_cycle)

        # Show/hide triggered widgets
        self.edge_label.setVisible(not is_cycle)
        self.edge_combo.setVisible(not is_cycle)
        self.trigger_channel_label.setVisible(not is_cycle)
        self.trigger_channel_edit.setVisible(not is_cycle)
        self.trigger_browse_btn.setVisible(not is_cycle)

    def _on_channel_browse_requested(self, slot_index: int):
        """Handle channel browse request for a slot."""
        channel_id = self._show_channel_selector()
        if channel_id:
            self.channel_slots[slot_index].set_channel(channel_id)

    def _browse_trigger_channel(self):
        """Browse for trigger channel."""
        channel_id = self._show_channel_selector()
        if channel_id:
            self.trigger_channel_edit.setText(channel_id)

    def _show_channel_selector(self) -> Optional[str]:
        """Show channel selector dialog and return selected channel ID."""
        from .channel_selector_dialog import ChannelSelectorDialog

        dialog = ChannelSelectorDialog(
            self,
            current_channel="",
            channels_data=self.available_channels,
            show_tree=True
        )

        if dialog.exec():
            return dialog.get_selected_channel()
        return None

    def _save_canx(self):
        """Save configuration as .CANX file."""
        from PyQt6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save CANX File",
            f"{self.name_edit.text() or 'can_output'}.canx",
            "CANX Files (*.canx);;All Files (*)"
        )

        if filename:
            try:
                import json
                config = self.get_config()
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                QMessageBox.information(self, "Saved", f"Configuration saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")

    def _on_accept(self):
        """Validate and accept dialog."""
        # Validate name
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        # Check name format
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            QMessageBox.warning(
                self, "Validation Error",
                "Name must start with a letter and contain only letters, numbers, and underscores!"
            )
            self.name_edit.setFocus()
            return

        # Check for duplicate ID
        if name != self.editing_name and name in self.existing_ids:
            QMessageBox.warning(
                self, "Validation Error",
                f"Name '{name}' already exists!"
            )
            self.name_edit.setFocus()
            return

        # Validate CAN ID
        id_text = self.id_edit.text().strip()
        try:
            if id_text.startswith("0x") or id_text.startswith("0X"):
                can_id = int(id_text, 16)
            else:
                can_id = int(id_text)

            is_extended = self.frame_type_combo.currentIndex() == 1
            max_id = 0x1FFFFFFF if is_extended else 0x7FF

            if can_id < 0 or can_id > max_id:
                raise ValueError("ID out of range")
        except ValueError:
            QMessageBox.warning(
                self, "Validation Error",
                "Invalid CAN ID! Enter a valid hex number (e.g., 0x100)"
            )
            self.id_edit.setFocus()
            return

        self.accept()

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        # Name is the primary identifier - try 'name' first, fall back to 'id' for backwards compatibility
        name = config.get("name", "") or config.get("id", "")
        self.name_edit.setText(name)

        # CAN Bus (1/2 -> index 0/1)
        can_bus = config.get("can_bus", 1)
        self.can_bus_combo.setCurrentIndex(can_bus - 1)

        # CAN ID
        can_id = config.get("message_id", 0)
        is_extended = config.get("is_extended", False)
        self.id_edit.setText(f"0x{can_id:X}")
        self.frame_type_combo.setCurrentIndex(1 if is_extended else 0)

        # DLC
        self.dlc_spin.setValue(config.get("dlc", 8))

        # Transmit mode
        tx_mode = config.get("transmit_mode", "cycle")
        for i, (_, value) in enumerate(self.TRANSMIT_MODES):
            if value == tx_mode:
                self.tx_mode_combo.setCurrentIndex(i)
                break

        # Frequency
        self.freq_spin.setValue(config.get("frequency_hz", 10))

        # Trigger settings
        trigger_edge = config.get("trigger_edge", "rising")
        for i, (_, value) in enumerate(self.TRIGGER_EDGES):
            if value == trigger_edge:
                self.edge_combo.setCurrentIndex(i)
                break
        self.trigger_channel_edit.setText(config.get("trigger_channel", ""))

        # Channel slots
        signals = config.get("signals", [])
        for i, slot in enumerate(self.channel_slots):
            if i < len(signals):
                slot.set_config(signals[i])

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        # Parse CAN ID
        id_text = self.id_edit.text().strip()
        try:
            if id_text.startswith("0x") or id_text.startswith("0X"):
                can_id = int(id_text, 16)
            else:
                can_id = int(id_text)
        except ValueError:
            can_id = 0

        tx_mode_index = self.tx_mode_combo.currentIndex()
        tx_mode = self.TRANSMIT_MODES[tx_mode_index][1]

        edge_index = self.edge_combo.currentIndex()
        trigger_edge = self.TRIGGER_EDGES[edge_index][1]

        # Collect signals from enabled slots
        dlc = self.dlc_spin.value()
        signals = []
        for i, slot in enumerate(self.channel_slots):
            if i < dlc:
                signals.append(slot.get_config())

        name = self.name_edit.text().strip()
        config = {
            "name": name,  # Primary identifier - unique, user-editable
            "channel_type": "can_tx",
            "can_bus": self.can_bus_combo.currentIndex() + 1,
            "message_id": can_id,
            "is_extended": self.frame_type_combo.currentIndex() == 1,
            "dlc": dlc,
            "transmit_mode": tx_mode,
            "frequency_hz": self.freq_spin.value(),
            "trigger_edge": trigger_edge,
            "trigger_channel": self.trigger_channel_edit.text().strip(),
            "signals": signals,
        }

        return config

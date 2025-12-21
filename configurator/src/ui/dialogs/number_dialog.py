"""
Number (Constant) Configuration Dialog
Allows creation of numeric constants/variables
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QDoubleSpinBox, QTextEdit, QDialogButtonBox, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


class NumberDialog(QDialog):
    """Dialog for configuring numeric constants."""

    def __init__(self, parent=None, config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.config = config or {}
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Number Configuration")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # Basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter number name...")
        basic_layout.addRow("Name:", self.name_edit)

        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1000000, 1000000)
        self.value_spin.setDecimals(4)
        self.value_spin.setSingleStep(0.1)
        basic_layout.addRow("Value:", self.value_spin)

        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("e.g., °C, bar, rpm...")
        basic_layout.addRow("Unit:", self.unit_edit)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Description
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout()

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Optional description...")
        desc_layout.addWidget(self.description_edit)

        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_config(self):
        """Load configuration into UI."""
        if not self.config:
            return

        self.name_edit.setText(self.config.get("name", ""))
        self.value_spin.setValue(self.config.get("value", 0.0))
        self.unit_edit.setText(self.config.get("unit", ""))
        self.description_edit.setPlainText(self.config.get("description", ""))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from UI."""
        return {
            "name": self.name_edit.text(),
            "value": self.value_spin.value(),
            "unit": self.unit_edit.text(),
            "description": self.description_edit.toPlainText()
        }

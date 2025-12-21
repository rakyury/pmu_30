"""
LUA Script Configuration Dialog
Configures a single LUA script for the PMU-30
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QLabel,
    QPlainTextEdit, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Dict, Any, Optional


class LuaScriptDialog(QDialog):
    """Dialog for configuring a single LUA script."""

    TRIGGER_TYPES = [
        "Periodic (Timer)",
        "On Input Change",
        "On Virtual Channel Change",
        "On CAN Message",
        "Manual Trigger Only"
    ]

    def __init__(self, parent=None, script_config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.script_config = script_config

        self.setWindowTitle("LUA Script Configuration")
        self.setModal(True)
        self.resize(750, 600)

        self._init_ui()

        if script_config:
            self._load_config(script_config)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Custom Control Logic, Data Processing")
        basic_layout.addRow("Name:", self.name_edit)

        self.enabled_check = QCheckBox("Script Enabled")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("", self.enabled_check)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Brief description of what this script does")
        basic_layout.addRow("Description:", self.description_edit)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Trigger configuration
        trigger_group = QGroupBox("Trigger Configuration")
        trigger_layout = QFormLayout()

        self.trigger_type_combo = QComboBox()
        self.trigger_type_combo.addItems(self.TRIGGER_TYPES)
        self.trigger_type_combo.currentTextChanged.connect(self._on_trigger_type_changed)
        trigger_layout.addRow("Trigger Type:", self.trigger_type_combo)

        # Periodic settings
        self.period_spin = QSpinBox()
        self.period_spin.setRange(1, 60000)
        self.period_spin.setValue(100)
        self.period_spin.setSuffix(" ms")
        self.period_spin.setToolTip("Script execution period")
        trigger_layout.addRow("Period:", self.period_spin)

        # Input/Channel settings
        self.trigger_channel_spin = QSpinBox()
        self.trigger_channel_spin.setRange(0, 255)
        self.trigger_channel_spin.setToolTip("Input or virtual channel to monitor")
        trigger_layout.addRow("Monitor Channel:", self.trigger_channel_spin)

        trigger_group.setLayout(trigger_layout)
        layout.addWidget(trigger_group)

        # Script editor
        editor_group = QGroupBox("LUA 5.4 Script")
        editor_layout = QVBoxLayout()

        # Info label
        info_label = QLabel(
            "Available APIs:\n"
            "• pmu.getInput(ch) - Read physical input 0-19\n"
            "• pmu.setOutput(ch, value) - Set physical output 0-29\n"
            "• pmu.getVirtual(ch) - Read virtual channel 0-255\n"
            "• pmu.setVirtual(ch, value) - Write virtual channel 0-255\n"
            "• pmu.canSend(id, data) - Send CAN message\n"
            "• pmu.log(level, message) - Write to system log"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #888888; font-size: 11px; }")
        editor_layout.addWidget(info_label)

        # Script text editor
        self.script_editor = QPlainTextEdit()
        self.script_editor.setPlaceholderText(
            "-- LUA 5.4 Script\n"
            "-- Example:\n"
            "local input_val = pmu.getInput(0)\n"
            "if input_val > 50 then\n"
            "    pmu.setOutput(0, 100)\n"
            "    pmu.setVirtual(0, input_val * 2)\n"
            "else\n"
            "    pmu.setOutput(0, 0)\n"
            "end"
        )

        # Set monospace font for code editing
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.script_editor.setFont(font)
        self.script_editor.setTabStopDistance(40)  # 4 spaces
        self.script_editor.setMinimumHeight(200)

        editor_layout.addWidget(self.script_editor)

        editor_group.setLayout(editor_layout)
        layout.addWidget(editor_group)

        # Script settings
        settings_group = QGroupBox("Script Settings")
        settings_layout = QFormLayout()

        self.max_execution_time_spin = QSpinBox()
        self.max_execution_time_spin.setRange(1, 1000)
        self.max_execution_time_spin.setValue(50)
        self.max_execution_time_spin.setSuffix(" ms")
        self.max_execution_time_spin.setToolTip("Maximum execution time before script is terminated")
        settings_layout.addRow("Max Execution Time:", self.max_execution_time_spin)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Normal", "High"])
        self.priority_combo.setCurrentIndex(1)
        self.priority_combo.setToolTip("Execution priority relative to other scripts")
        settings_layout.addRow("Priority:", self.priority_combo)

        self.error_action_combo = QComboBox()
        self.error_action_combo.addItems(["Disable Script", "Log and Continue", "Ignore Errors"])
        self.error_action_combo.setCurrentIndex(0)
        self.error_action_combo.setToolTip("Action to take when script encounters an error")
        settings_layout.addRow("On Error:", self.error_action_combo)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.validate_btn = QPushButton("Validate Syntax")
        self.validate_btn.clicked.connect(self._validate_syntax)
        button_layout.addWidget(self.validate_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize trigger fields visibility
        self._on_trigger_type_changed(self.trigger_type_combo.currentText())

    def _on_trigger_type_changed(self, trigger_type: str):
        """Update UI based on trigger type selection."""
        is_periodic = "Periodic" in trigger_type
        is_input = "Input Change" in trigger_type
        is_virtual = "Virtual Channel" in trigger_type

        # Show/hide period field
        self.period_spin.setEnabled(is_periodic)

        # Show/hide channel field
        self.trigger_channel_spin.setEnabled(is_input or is_virtual)

    def _validate_syntax(self):
        """Validate LUA script syntax."""
        from PyQt6.QtWidgets import QMessageBox

        script = self.script_editor.toPlainText().strip()

        if not script:
            QMessageBox.warning(self, "Empty Script", "Please enter a script to validate.")
            return

        # TODO: Implement actual LUA syntax validation using lupa or similar
        QMessageBox.information(
            self, "Syntax Validation",
            "LUA syntax validation will be implemented.\n\n"
            "This feature requires the 'lupa' library for LUA integration.\n\n"
            "The script will be validated when uploaded to the device."
        )

    def _load_config(self, config: Dict[str, Any]):
        """Load configuration into dialog."""
        self.name_edit.setText(config.get("name", ""))
        self.enabled_check.setChecked(config.get("enabled", True))
        self.description_edit.setText(config.get("description", ""))

        # Trigger configuration
        trigger = config.get("trigger", {})
        trigger_type = trigger.get("type", "Periodic (Timer)")
        index = self.trigger_type_combo.findText(trigger_type)
        if index >= 0:
            self.trigger_type_combo.setCurrentIndex(index)

        self.period_spin.setValue(trigger.get("period_ms", 100))
        self.trigger_channel_spin.setValue(trigger.get("channel", 0))

        # Script content
        self.script_editor.setPlainText(config.get("script", ""))

        # Settings
        settings = config.get("settings", {})
        self.max_execution_time_spin.setValue(settings.get("max_execution_ms", 50))

        priority = settings.get("priority", "Normal")
        priority_index = self.priority_combo.findText(priority)
        if priority_index >= 0:
            self.priority_combo.setCurrentIndex(priority_index)

        error_action = settings.get("error_action", "Disable Script")
        error_index = self.error_action_combo.findText(error_action)
        if error_index >= 0:
            self.error_action_combo.setCurrentIndex(error_index)

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        config = {
            "name": self.name_edit.text(),
            "enabled": self.enabled_check.isChecked(),
            "description": self.description_edit.text(),
            "trigger": {
                "type": self.trigger_type_combo.currentText(),
                "period_ms": self.period_spin.value(),
                "channel": self.trigger_channel_spin.value()
            },
            "script": self.script_editor.toPlainText(),
            "settings": {
                "max_execution_ms": self.max_execution_time_spin.value(),
                "priority": self.priority_combo.currentText(),
                "error_action": self.error_action_combo.currentText()
            }
        }

        return config

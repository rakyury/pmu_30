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
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from typing import Dict, Any, Optional
import re


class LuaSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Lua language."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Define highlighting rules
        self.highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))  # Blue
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "and", "break", "do", "else", "elseif", "end", "false", "for",
            "function", "if", "in", "local", "nil", "not", "or", "repeat",
            "return", "then", "true", "until", "while", "goto"
        ]
        for word in keywords:
            pattern = f"\\b{word}\\b"
            self.highlighting_rules.append((re.compile(pattern), keyword_format))

        # String literals (single and double quotes)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))  # Orange
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))  # Light green
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*\b'), number_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))  # Green
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r'--[^\n]*'), comment_format))

        # Built-in functions
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#DCDCAA"))  # Yellow
        builtins = ["pmu\.getInput", "pmu\.setOutput", "pmu\.getVirtual",
                   "pmu\.setVirtual", "pmu\.canSend", "pmu\.log"]
        for builtin in builtins:
            self.highlighting_rules.append((re.compile(builtin), builtin_format))

    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        for pattern, format_style in self.highlighting_rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format_style)


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
        self.resize(650, 500)

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
        basic_layout.addRow("Name: *", self.name_edit)

        self.enabled_check = QCheckBox("Script Enabled")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("", self.enabled_check)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Brief description of what this script does")
        basic_layout.addRow("Description:", self.description_edit)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Trigger configuration - simplified
        trigger_layout = QHBoxLayout()
        trigger_layout.addWidget(QLabel("Trigger:"))

        self.trigger_type_combo = QComboBox()
        self.trigger_type_combo.addItems(self.TRIGGER_TYPES)
        trigger_layout.addWidget(self.trigger_type_combo, 1)

        trigger_layout.addWidget(QLabel("Period:"))
        self.period_spin = QSpinBox()
        self.period_spin.setRange(1, 60000)
        self.period_spin.setValue(100)
        self.period_spin.setSuffix(" ms")
        trigger_layout.addWidget(self.period_spin)

        layout.addLayout(trigger_layout)

        # Script editor
        editor_group = QGroupBox("LUA 5.4 Script")
        editor_layout = QVBoxLayout()

        # Script text editor
        self.script_editor = QPlainTextEdit()
        self.script_editor.setPlaceholderText(
            "-- LUA 5.4 Script Example:\n"
            "local input_val = pmu.getInput(0)\n"
            "if input_val > 50 then\n"
            "    pmu.setOutput(0, 100)\n"
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
        self.script_editor.setMinimumHeight(250)

        # Apply syntax highlighting
        self.highlighter = LuaSyntaxHighlighter(self.script_editor.document())

        editor_layout.addWidget(self.script_editor)

        editor_group.setLayout(editor_layout)
        layout.addWidget(editor_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.validate_btn = QPushButton("Validate Syntax")
        self.validate_btn.clicked.connect(self._validate_syntax)
        button_layout.addWidget(self.validate_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _on_accept(self):
        """Validate and accept dialog."""
        from PyQt6.QtWidgets import QMessageBox

        # Validate name (required field)
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            self.name_edit.setFocus()
            return

        self.accept()

    def _validate_syntax(self):
        """Validate LUA script syntax."""
        from PyQt6.QtWidgets import QMessageBox

        script = self.script_editor.toPlainText().strip()

        if not script:
            QMessageBox.warning(self, "Empty Script", "Please enter a script to validate.")
            return

        # Basic syntax validation
        errors = []

        # Check for balanced keywords
        lines = script.split('\n')
        block_stack = []

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments
            if line_stripped.startswith('--'):
                continue

            # Check for block openings
            if re.search(r'\b(function|if|for|while|repeat)\b', line_stripped):
                block_stack.append((line_num, line_stripped))

            # Check for block closings
            if 'end' in line_stripped:
                if not block_stack:
                    errors.append(f"Line {line_num}: 'end' without matching block opening")
                else:
                    block_stack.pop()

            if 'until' in line_stripped:
                if not block_stack:
                    errors.append(f"Line {line_num}: 'until' without matching 'repeat'")
                else:
                    block_stack.pop()

        # Check for unclosed blocks
        if block_stack:
            for line_num, line in block_stack:
                errors.append(f"Line {line_num}: Unclosed block - '{line[:30]}...'")

        # Check for common syntax errors
        for line_num, line in enumerate(lines, 1):
            # Check for Python-style comparisons
            if '==' in line and not line.strip().startswith('--'):
                pass  # == is valid in Lua
            if re.search(r'\b(elif|elif:|else:)\b', line):
                errors.append(f"Line {line_num}: Use 'elseif' instead of 'elif'")
            if re.search(r'\b(True|False|None)\b', line):
                errors.append(f"Line {line_num}: Use 'true', 'false', 'nil' (lowercase)")

        # Display results
        if errors:
            error_text = "\n".join(errors[:10])  # Show first 10 errors
            if len(errors) > 10:
                error_text += f"\n\n... and {len(errors) - 10} more errors"
            QMessageBox.warning(
                self, "Syntax Errors Found",
                f"Found {len(errors)} potential syntax error(s):\n\n{error_text}"
            )
        else:
            QMessageBox.information(
                self, "Syntax Check Passed",
                "No obvious syntax errors detected.\n\n"
                "Note: This is a basic check. Full validation occurs on device."
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

        # Script content
        self.script_editor.setPlainText(config.get("script", ""))

    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog."""
        config = {
            "name": self.name_edit.text(),
            "enabled": self.enabled_check.isChecked(),
            "description": self.description_edit.text(),
            "trigger": {
                "type": self.trigger_type_combo.currentText(),
                "period_ms": self.period_spin.value()
            },
            "script": self.script_editor.toPlainText()
        }

        return config

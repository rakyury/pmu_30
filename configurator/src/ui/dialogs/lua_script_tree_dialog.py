"""
Lua Script Tree Dialog

Dialog for configuring Lua scripts in the project tree with:
- Enhanced code editor with line numbers and syntax highlighting
- Console output for debugging
- Run/Stop/Validate buttons for device testing
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QLabel,
    QSpinBox, QTextEdit, QSplitter, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCharFormat
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType, LuaTriggerType, LuaPriority


class LuaScriptTreeDialog(BaseChannelDialog):
    """Dialog for configuring Lua scripts in the project tree."""

    # Signal emitted when user wants to run script on device
    run_requested = pyqtSignal(str, str)  # script_name, script_code
    stop_requested = pyqtSignal(str)  # script_name

    TRIGGER_TYPES = [
        ("Manual", LuaTriggerType.MANUAL),
        ("Periodic", LuaTriggerType.PERIODIC),
        ("On Input Change", LuaTriggerType.ON_INPUT_CHANGE),
        ("On Virtual Change", LuaTriggerType.ON_VIRTUAL_CHANGE),
        ("On Startup", LuaTriggerType.ON_STARTUP),
    ]

    PRIORITIES = [
        ("Low", LuaPriority.LOW),
        ("Normal", LuaPriority.NORMAL),
        ("High", LuaPriority.HIGH),
    ]

    # Script templates
    SCRIPT_TEMPLATES = {
        "Empty": "",
        "Basic Input/Output": '''-- Basic Input/Output Example
-- Read input and control output based on threshold

local input_val = pmu.getInput(0)
local threshold = 50

if input_val > threshold then
    pmu.setOutput(0, 100)
    pmu.log("Output ON: " .. tostring(input_val))
else
    pmu.setOutput(0, 0)
    pmu.log("Output OFF: " .. tostring(input_val))
end
''',
        "PWM Control": '''-- PWM Control Example
-- Adjust PWM duty based on analog input

local analog_val = pmu.getAnalog(0)  -- 0-100%
local min_duty = 10
local max_duty = 90

-- Map analog value to PWM range
local duty = min_duty + (analog_val / 100) * (max_duty - min_duty)

pmu.setOutputPWM(0, 1, duty)
pmu.log("PWM Duty: " .. string.format("%.1f%%", duty))
''',
        "Toggle Output": '''-- Toggle Output on Input Change
-- Toggles output state when input goes high

local input_state = pmu.getInput(0)
local current_output = pmu.getVirtual(0)  -- Store state in virtual channel

if input_state > 0 then
    -- Toggle
    if current_output > 0 then
        pmu.setOutput(0, 0)
        pmu.setVirtual(0, 0)
    else
        pmu.setOutput(0, 100)
        pmu.setVirtual(0, 1)
    end
end
''',
        "Delay Timer": '''-- Delay Timer Example
-- Turn on output after input is active for specified time

local input_active = pmu.getInput(0) > 0
local delay_ms = 1000  -- 1 second delay
local timer = pmu.getVirtual(0)  -- Store timer value

if input_active then
    timer = timer + 100  -- Assuming 100ms periodic trigger
    if timer >= delay_ms then
        pmu.setOutput(0, 100)
        pmu.log("Delay complete - Output ON")
    end
else
    timer = 0
    pmu.setOutput(0, 0)
end

pmu.setVirtual(0, timer)
''',
        "Multi-Input Logic": '''-- Multi-Input Logic Example
-- Output is ON only when ALL inputs are active

local input1 = pmu.getInput(0) > 0
local input2 = pmu.getInput(1) > 0
local input3 = pmu.getInput(2) > 0

if input1 and input2 and input3 then
    pmu.setOutput(0, 100)
    pmu.log("All inputs active - Output ON")
else
    pmu.setOutput(0, 0)
end
''',
        "CAN Message Send": '''-- CAN Message Send Example
-- Send CAN message when input changes

local input_val = pmu.getInput(0)
local last_val = pmu.getVirtual(0)

-- Only send when value changes
if input_val ~= last_val then
    local can_id = 0x100
    local data = {input_val, 0, 0, 0, 0, 0, 0, 0}

    pmu.canSend(1, can_id, data)
    pmu.setVirtual(0, input_val)
    pmu.log("CAN sent: ID=0x" .. string.format("%X", can_id))
end
''',
        "Temperature Monitor": '''-- Temperature Monitor Example
-- Monitor temperature and control cooling fan

local temp = pmu.getTemperature()  -- Device temperature
local fan_on_temp = 60   -- Turn fan ON above this
local fan_off_temp = 50  -- Turn fan OFF below this

local fan_state = pmu.getVirtual(0)

if temp > fan_on_temp then
    pmu.setOutput(0, 100)  -- Fan ON
    pmu.setVirtual(0, 1)
    pmu.log("Fan ON - Temp: " .. tostring(temp) .. "C")
elseif temp < fan_off_temp and fan_state > 0 then
    pmu.setOutput(0, 0)    -- Fan OFF
    pmu.setVirtual(0, 0)
    pmu.log("Fan OFF - Temp: " .. tostring(temp) .. "C")
end
''',
        "Pulse Generator": '''-- Pulse Generator Example
-- Generate pulse output at specified frequency

local pulse_period_ms = 500  -- 1 Hz = 500ms on, 500ms off
local timer = pmu.getVirtual(0)
local state = pmu.getVirtual(1)

timer = timer + 100  -- Assuming 100ms periodic trigger

if timer >= pulse_period_ms then
    timer = 0
    -- Toggle state
    if state > 0 then
        pmu.setOutput(0, 0)
        pmu.setVirtual(1, 0)
    else
        pmu.setOutput(0, 100)
        pmu.setVirtual(1, 1)
    end
end

pmu.setVirtual(0, timer)
''',
    }

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        # Set channel type before calling super().__init__
        super().__init__(
            parent=parent,
            config=config,
            available_channels=available_channels,
            channel_type=ChannelType.LUA_SCRIPT,
            existing_channels=existing_channels
        )

        self.is_running = False
        self._init_lua_ui()

        if config:
            self._load_lua_config(config)

        # Finalize UI sizing
        self._finalize_ui()

    def _init_lua_ui(self):
        """Initialize Lua-specific UI components."""
        self.setMinimumWidth(800)
        self.setMinimumHeight(700)
        self.resize(900, 750)

        # Add name and description to basic settings group
        self._add_basic_fields()

        # Trigger settings
        self._create_trigger_group()

        # Create main splitter for editor and console
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # Script editor group
        self._create_editor_group()

        # Console output group
        self._create_console_group()

        self.content_layout.addWidget(self.splitter, stretch=1)

        # Update buttons layout
        self._update_buttons()

    def _add_basic_fields(self):
        """Add name, description, and enabled fields to basic group."""
        # Find the basic group
        basic_group = self.scroll_widget.findChildren(QGroupBox)[0]
        basic_layout = basic_group.layout()

        # Name field
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Human-readable name for the script")
        basic_layout.addRow("Name:", self.name_edit)

        # Enabled checkbox
        self.enabled_check = QCheckBox("Script Enabled")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("", self.enabled_check)

        # Description field
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Brief description of what this script does")
        basic_layout.addRow("Description:", self.description_edit)

    def _create_trigger_group(self):
        """Create trigger configuration group."""
        trigger_group = QGroupBox("Trigger Settings")
        trigger_layout = QFormLayout()

        # Trigger type
        self.trigger_combo = QComboBox()
        for label, _ in self.TRIGGER_TYPES:
            self.trigger_combo.addItem(label)
        self.trigger_combo.currentIndexChanged.connect(self._on_trigger_changed)
        trigger_layout.addRow("Trigger Type:", self.trigger_combo)

        # Period (for periodic trigger)
        self.period_spin = QSpinBox()
        self.period_spin.setRange(10, 60000)
        self.period_spin.setValue(100)
        self.period_spin.setSuffix(" ms")
        trigger_layout.addRow("Period:", self.period_spin)

        # Trigger channel (for input/virtual change)
        self.trigger_channel_container, self.trigger_channel_edit = self._create_channel_selector(
            "Select trigger channel..."
        )
        trigger_layout.addRow("Trigger Channel:", self.trigger_channel_container)

        # Max execution time
        self.max_exec_spin = QSpinBox()
        self.max_exec_spin.setRange(1, 1000)
        self.max_exec_spin.setValue(50)
        self.max_exec_spin.setSuffix(" ms")
        trigger_layout.addRow("Max Execution:", self.max_exec_spin)

        # Priority
        self.priority_combo = QComboBox()
        for label, _ in self.PRIORITIES:
            self.priority_combo.addItem(label)
        self.priority_combo.setCurrentIndex(1)  # Normal
        trigger_layout.addRow("Priority:", self.priority_combo)

        trigger_group.setLayout(trigger_layout)
        self.content_layout.addWidget(trigger_group)

        # Initial visibility update
        self._on_trigger_changed(0)

    def _on_trigger_changed(self, index):
        """Update UI based on selected trigger type."""
        trigger_type = self.TRIGGER_TYPES[index][1]

        # Show/hide period based on trigger type
        is_periodic = trigger_type == LuaTriggerType.PERIODIC
        self.period_spin.setEnabled(is_periodic)

        # Show/hide trigger channel based on trigger type
        needs_channel = trigger_type in [
            LuaTriggerType.ON_INPUT_CHANGE,
            LuaTriggerType.ON_VIRTUAL_CHANGE
        ]
        self.trigger_channel_container.setEnabled(needs_channel)

    def _create_editor_group(self):
        """Create script editor group with enhanced editor."""
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # Header with template selector and position indicator
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Lua 5.4 Script"))

        # Template selector
        header_layout.addWidget(QLabel("  Template:"))
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(150)
        for template_name in self.SCRIPT_TEMPLATES.keys():
            self.template_combo.addItem(template_name)
        self.template_combo.currentTextChanged.connect(self._on_template_selected)
        header_layout.addWidget(self.template_combo)

        header_layout.addStretch()

        self.position_label = QLabel("Ln 1, Col 1")
        self.position_label.setStyleSheet("color: #b0b0b0;")
        header_layout.addWidget(self.position_label)

        editor_layout.addLayout(header_layout)

        # Import and create the enhanced editor
        try:
            from ui.widgets.lua_editor import LuaCodeEditor
            self.script_editor = LuaCodeEditor()
        except ImportError:
            # Fallback to basic editor if enhanced one is not available
            from PyQt6.QtWidgets import QPlainTextEdit
            self.script_editor = QPlainTextEdit()
            font = QFont("Consolas", 10)
            self.script_editor.setFont(font)

        self.script_editor.setPlaceholderText(
            "-- Lua 5.4 Script Example:\n"
            "local val = pmu.getInput(0)\n"
            "if val > 50 then\n"
            "    pmu.setOutput(0, 100)\n"
            "else\n"
            "    pmu.setOutput(0, 0)\n"
            "end\n"
            "pmu.log('Value: ' .. tostring(val))"
        )

        # Connect cursor position signal if available
        if hasattr(self.script_editor, 'cursorPositionChanged'):
            self.script_editor.cursorPositionChanged.connect(self._update_position)

        editor_layout.addWidget(self.script_editor)

        self.splitter.addWidget(editor_widget)

    def _create_console_group(self):
        """Create console output group."""
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)
        console_layout.setContentsMargins(0, 0, 0, 0)

        # Header with clear button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Console Output"))
        header_layout.addStretch()

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #b0b0b0; font-weight: bold;")
        header_layout.addWidget(self.status_label)

        self.clear_console_btn = QPushButton("Clear")
        self.clear_console_btn.setMaximumWidth(60)
        self.clear_console_btn.clicked.connect(self._clear_console)
        header_layout.addWidget(self.clear_console_btn)

        console_layout.addLayout(header_layout)

        # Console output text
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Consolas", 9))
        self.console_output.setMaximumHeight(150)

        # Dark console style
        self.console_output.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: 1px solid #3C3C3C;
            }
        """)

        console_layout.addWidget(self.console_output)

        self.splitter.addWidget(console_widget)

        # Set initial splitter sizes (70% editor, 30% console)
        self.splitter.setSizes([500, 150])

    def _update_buttons(self):
        """Update buttons layout with run/validate controls."""
        # Find the existing button layout
        button_layout = self.main_layout.itemAt(self.main_layout.count() - 1).layout()

        # Insert action buttons at the beginning
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setToolTip("Check script syntax")
        self.validate_btn.clicked.connect(self._validate_script)
        button_layout.insertWidget(0, self.validate_btn)

        self.run_btn = QPushButton("Run on Device")
        self.run_btn.setToolTip("Load and run script on connected device")
        self.run_btn.clicked.connect(self._run_on_device)
        button_layout.insertWidget(1, self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setToolTip("Stop script execution")
        self.stop_btn.clicked.connect(self._stop_execution)
        self.stop_btn.setEnabled(False)
        button_layout.insertWidget(2, self.stop_btn)

        # Add spacer after action buttons
        button_layout.insertStretch(3)

    def _update_position(self):
        """Update cursor position indicator."""
        if hasattr(self.script_editor, 'get_cursor_position'):
            line, col = self.script_editor.get_cursor_position()
        else:
            cursor = self.script_editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1

        self.position_label.setText(f"Ln {line}, Col {col}")

    def _on_template_selected(self, template_name: str):
        """Handle template selection."""
        if template_name not in self.SCRIPT_TEMPLATES:
            return

        template_code = self.SCRIPT_TEMPLATES[template_name]

        # If empty template or editor is empty, just set
        current_text = self.script_editor.toPlainText().strip()
        if not template_code or not current_text:
            self.script_editor.setPlainText(template_code)
            return

        # Ask before replacing existing code
        result = QMessageBox.question(
            self, "Replace Script",
            "Replace current script with template?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            self.script_editor.setPlainText(template_code)
            self._log_console(f"Loaded template: {template_name}", "info")

    def _clear_console(self):
        """Clear console output."""
        self.console_output.clear()

    def _log_console(self, message: str, level: str = "info"):
        """Add message to console output."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color based on level
        colors = {
            "info": "#CCCCCC",
            "success": "#6A9955",
            "warning": "#DCDCAA",
            "error": "#F44747",
        }
        color = colors.get(level, "#CCCCCC")

        html = f'<span style="color: #b0b0b0;">[{timestamp}]</span> <span style="color: {color};">{message}</span><br>'
        self.console_output.insertHtml(html)

        # Scroll to bottom
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _validate_script(self):
        """Validate Lua script syntax."""
        script = self.script_editor.toPlainText().strip()

        if not script:
            QMessageBox.warning(self, "Empty Script", "Please enter a script to validate.")
            return

        errors = self._check_syntax(script)

        if errors:
            self._log_console("Syntax validation failed:", "error")
            for error in errors[:10]:
                self._log_console(f"  {error}", "error")
            if len(errors) > 10:
                self._log_console(f"  ... and {len(errors) - 10} more errors", "error")

            self.status_label.setText("Errors Found")
            self.status_label.setStyleSheet("color: #F44747; font-weight: bold;")
        else:
            self._log_console("Syntax validation passed", "success")
            self.status_label.setText("Valid")
            self.status_label.setStyleSheet("color: #6A9955; font-weight: bold;")

    def _check_syntax(self, script: str) -> List[str]:
        """Check Lua syntax and return list of errors."""
        import re
        errors = []
        lines = script.split('\n')
        block_stack = []

        # Lua keywords and valid constructs
        lua_keywords = {
            'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
            'function', 'goto', 'if', 'in', 'local', 'nil', 'not', 'or',
            'repeat', 'return', 'then', 'true', 'until', 'while'
        }

        # Pattern for valid Lua identifier
        identifier_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'

        # Pattern for valid Lua line (simplified)
        valid_line_patterns = [
            rf'^{identifier_pattern}\s*=',  # assignment: var = ...
            rf'^local\s+{identifier_pattern}',  # local declaration
            rf'^{identifier_pattern}\s*\(',  # function call: func(...)
            rf'^{identifier_pattern}\.{identifier_pattern}',  # method/field: obj.method
            rf'^{identifier_pattern}:{identifier_pattern}',  # method call: obj:method
            rf'^\w+\s*\[',  # indexing: arr[...]
            r'^(if|for|while|repeat|function|return|do|end|else|elseif|until|break|goto)\b',  # keywords
            r'^--',  # comment
            r'^\s*$',  # empty line
        ]

        valid_code_lines = 0
        total_code_lines = 0

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith('--'):
                continue

            total_code_lines += 1

            # Remove string literals for analysis
            line_no_strings = re.sub(r'"[^"]*"', '""', line_stripped)
            line_no_strings = re.sub(r"'[^']*'", "''", line_no_strings)

            # Check if line matches any valid Lua pattern
            is_valid = False
            for pattern in valid_line_patterns:
                if re.search(pattern, line_no_strings, re.IGNORECASE):
                    is_valid = True
                    valid_code_lines += 1
                    break

            # Also accept lines that contain keywords or typical Lua operators
            if not is_valid:
                words = re.findall(r'\b\w+\b', line_no_strings)
                for word in words:
                    if word.lower() in lua_keywords or word in ['pmu', 'string', 'math', 'table', 'tostring', 'tonumber', 'print', 'pairs', 'ipairs']:
                        is_valid = True
                        valid_code_lines += 1
                        break

            # Check for non-ASCII characters outside strings (likely invalid)
            line_outside_strings = line_no_strings
            if re.search(r'[^\x00-\x7F]', line_outside_strings):
                # Contains non-ASCII - check if it's in a string in original line
                if not re.search(r'["\'][^"\']*[^\x00-\x7F][^"\']*["\']', line_stripped):
                    errors.append(f"Line {line_num}: Invalid characters (non-ASCII outside strings)")

            # Check for block openings
            for kw in ['function', 'if', 'for', 'while', 'repeat']:
                if re.search(rf'\b{kw}\b', line_stripped):
                    # Don't count one-line if statements
                    if kw == 'if' and 'then' in line_stripped and 'end' in line_stripped:
                        continue
                    block_stack.append((line_num, kw))

            # Check for block closings
            if re.search(r'\bend\b', line_stripped):
                if not block_stack:
                    errors.append(f"Line {line_num}: 'end' without matching block opening")
                else:
                    block_stack.pop()

            if re.search(r'\buntil\b', line_stripped):
                if not block_stack or block_stack[-1][1] != 'repeat':
                    errors.append(f"Line {line_num}: 'until' without matching 'repeat'")
                elif block_stack:
                    block_stack.pop()

            # Check for common Python-isms
            if re.search(r'\b(elif|elif:)\b', line_stripped):
                errors.append(f"Line {line_num}: Use 'elseif' instead of 'elif'")
            if re.search(r'\belse\s*:', line_stripped):
                errors.append(f"Line {line_num}: Remove colon after 'else'")
            if re.search(r'\b(True|False|None)\b', line_stripped):
                errors.append(f"Line {line_num}: Use 'true', 'false', 'nil' (lowercase)")
            if re.search(r'def\s+\w+', line_stripped):
                errors.append(f"Line {line_num}: Use 'function' instead of 'def'")

        # Check for unclosed blocks
        for line_num, keyword in block_stack:
            errors.append(f"Line {line_num}: Unclosed '{keyword}' block")

        # If no valid Lua constructs found in non-trivial code
        if total_code_lines > 0 and valid_code_lines == 0:
            errors.insert(0, "No valid Lua syntax detected - script appears to be invalid")

        # If very few lines are valid (less than 30%), likely invalid
        if total_code_lines > 3 and valid_code_lines < total_code_lines * 0.3:
            errors.insert(0, f"Only {valid_code_lines}/{total_code_lines} lines appear to be valid Lua")

        return errors

    def _run_on_device(self):
        """Run script on connected device."""
        script = self.script_editor.toPlainText().strip()

        if not script:
            QMessageBox.warning(self, "Empty Script", "Please enter a script to run.")
            return

        # Validate first
        errors = self._check_syntax(script)
        if errors:
            result = QMessageBox.warning(
                self, "Syntax Errors",
                "Script has syntax errors. Run anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result == QMessageBox.StandardButton.No:
                return

        script_name = self.name_edit.text().strip() or "unnamed"

        self._log_console(f"Loading script '{script_name}'...", "info")
        self.status_label.setText("Running...")
        self.status_label.setStyleSheet("color: #569CD6; font-weight: bold;")

        self.is_running = True
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Emit signal for external handling
        self.run_requested.emit(script_name, script)

        # Simulate execution for now (actual implementation would come from LuaExecutor)
        self._log_console("Script loaded successfully", "success")
        self._log_console("Executing...", "info")

    def _stop_execution(self):
        """Stop script execution."""
        script_name = self.name_edit.text().strip() or "unnamed"

        self._log_console("Stopping script...", "warning")
        self.stop_requested.emit(script_name)

        self.is_running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet("color: #DCDCAA; font-weight: bold;")
        self._log_console("Script stopped", "warning")

    def append_console_output(self, message: str, level: str = "info"):
        """Public method to append output from device."""
        self._log_console(message, level)

    def set_execution_complete(self, success: bool, message: str = ""):
        """Called when script execution completes."""
        self.is_running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if success:
            self.status_label.setText("Completed")
            self.status_label.setStyleSheet("color: #6A9955; font-weight: bold;")
            self._log_console(message or "Execution completed", "success")
        else:
            self.status_label.setText("Error")
            self.status_label.setStyleSheet("color: #F44747; font-weight: bold;")
            self._log_console(message or "Execution failed", "error")

    def _load_lua_config(self, config: Dict[str, Any]):
        """Load Lua-specific configuration."""
        self.name_edit.setText(config.get("name", ""))
        self.enabled_check.setChecked(config.get("enabled", True))
        self.description_edit.setText(config.get("description", ""))

        # Trigger settings
        trigger_type = config.get("trigger_type", "manual")
        for i, (_, tt) in enumerate(self.TRIGGER_TYPES):
            if tt.value == trigger_type:
                self.trigger_combo.setCurrentIndex(i)
                break

        self.period_spin.setValue(config.get("trigger_period_ms", 100))
        self.trigger_channel_edit.setText(config.get("trigger_channel", ""))
        self.max_exec_spin.setValue(config.get("max_execution_ms", 50))

        # Priority
        priority = config.get("priority", "normal")
        for i, (_, p) in enumerate(self.PRIORITIES):
            if p.value == priority:
                self.priority_combo.setCurrentIndex(i)
                break

        # Script content
        self.script_editor.setPlainText(config.get("script", ""))

    def _validate_specific(self) -> List[str]:
        """Validate Lua-specific fields."""
        errors = []

        # Script cannot be empty
        if not self.script_editor.toPlainText().strip():
            errors.append("Script cannot be empty")

        # Trigger channel required for certain trigger types
        trigger_type = self.TRIGGER_TYPES[self.trigger_combo.currentIndex()][1]
        if trigger_type in [LuaTriggerType.ON_INPUT_CHANGE, LuaTriggerType.ON_VIRTUAL_CHANGE]:
            if not self.trigger_channel_edit.text().strip():
                errors.append("Trigger channel is required for this trigger type")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration from dialog."""
        config = self.get_base_config()

        config.update({
            "name": self.name_edit.text().strip(),
            "description": self.description_edit.text().strip(),
            "enabled": self.enabled_check.isChecked(),
            "script": self.script_editor.toPlainText(),
            "trigger_type": self.TRIGGER_TYPES[self.trigger_combo.currentIndex()][1].value,
            "trigger_period_ms": self.period_spin.value(),
            "trigger_channel": self.trigger_channel_edit.text().strip(),
            "max_execution_ms": self.max_exec_spin.value(),
            "priority": self.PRIORITIES[self.priority_combo.currentIndex()][1].value,
        })

        return config

"""
Lua Code Editor Widget with Line Numbers and Syntax Highlighting

Enhanced code editor for Lua scripts with:
- Line number panel
- Syntax highlighting
- Current line highlighting
- Autocomplete for PMU API
- Bracket matching
- Tab → 4 spaces
- Auto-indent
"""

from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QTextEdit, QCompleter,
    QApplication
)
from PyQt6.QtCore import Qt, QRect, QSize, QStringListModel
from PyQt6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QFontMetrics,
    QSyntaxHighlighter, QTextDocument, QTextCharFormat,
    QTextCursor, QPalette, QKeyEvent
)
import re


# PMU API functions for autocomplete
PMU_API_FUNCTIONS = [
    # Channel access (universal channel system)
    "channel.get(channel_id)",
    "channel.set(channel_id, value)",
    "channel.find(name)",
    "channel.info(channel_id)",
    "channel.list()",
    # Shorthand functions
    "getChannel(channel_id)",
    "setChannel(channel_id, value)",
    "getInput(channel)",
    "setOutput(channel, value)",
    # CAN functions
    "sendCAN(bus, id, data)",
    # System functions
    "system.voltage()",
    "system.current()",
    "system.temperature()",
    "system.uptime()",
    "getVoltage()",
    "getTemperature()",
    # Utility functions
    "log(message)",
    "print(message)",
    "millis()",
    "delay(ms)",
    "sleep(ms)",
    # Logic functions
    "logic.add(output, input_a, input_b)",
    "logic.subtract(output, input_a, input_b)",
    "logic.multiply(output, input_a, input_b)",
    "logic.divide(output, input_a, input_b)",
    "logic.compare(output, input_a, input_b, op)",
    "logic.pid(output, input, setpoint, kp, ki, kd)",
    "logic.hysteresis(output, input, on_threshold, off_threshold)",
    "logic.enable(func_id, enabled)",
]

# Lua keywords
LUA_KEYWORDS = [
    "and", "break", "do", "else", "elseif", "end", "false",
    "for", "function", "goto", "if", "in", "local", "nil", "not",
    "or", "repeat", "return", "then", "true", "until", "while"
]

# Lua built-in functions
LUA_BUILTINS = [
    "print", "type", "tostring", "tonumber", "pairs", "ipairs",
    "next", "select", "unpack", "table", "string", "math",
    "assert", "error", "pcall", "xpcall", "setmetatable", "getmetatable",
    "rawget", "rawset", "rawequal", "rawlen",
]

# Common math functions
MATH_FUNCTIONS = [
    "math.abs", "math.floor", "math.ceil", "math.max", "math.min",
    "math.sin", "math.cos", "math.tan", "math.sqrt", "math.pow",
    "math.random", "math.randomseed", "math.log", "math.exp",
]

# Common string functions
STRING_FUNCTIONS = [
    "string.len", "string.sub", "string.upper", "string.lower",
    "string.find", "string.match", "string.gsub", "string.format",
]

# Common table functions
TABLE_FUNCTIONS = [
    "table.insert", "table.remove", "table.sort", "table.concat",
]


class LuaSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Lua code"""

    def __init__(self, parent: QTextDocument = None):
        super().__init__(parent)
        self._init_formats()
        self._init_rules()

    def _init_formats(self):
        """Initialize text formats for different syntax elements"""
        # Keywords (blue)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#569CD6"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        # Strings (orange)
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#CE9178"))

        # Comments (green)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955"))
        self.comment_format.setFontItalic(True)

        # Numbers (light green)
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#B5CEA8"))

        # Functions (yellow)
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#DCDCAA"))

        # PMU API (cyan)
        self.pmu_format = QTextCharFormat()
        self.pmu_format.setForeground(QColor("#4EC9B0"))
        self.pmu_format.setFontWeight(QFont.Weight.Bold)

        # Built-ins (purple)
        self.builtin_format = QTextCharFormat()
        self.builtin_format.setForeground(QColor("#C586C0"))

        # Operators (white)
        self.operator_format = QTextCharFormat()
        self.operator_format.setForeground(QColor("#D4D4D4"))

    def _init_rules(self):
        """Initialize highlighting rules"""
        self.rules = []

        # Keywords
        keyword_pattern = r'\b(' + '|'.join(LUA_KEYWORDS) + r')\b'
        self.rules.append((re.compile(keyword_pattern), self.keyword_format))

        # Built-in functions
        builtin_pattern = r'\b(' + '|'.join(LUA_BUILTINS) + r')\b'
        self.rules.append((re.compile(builtin_pattern), self.builtin_format))

        # PMU API (channel, system, logic tables)
        pmu_pattern = r'\b(channel|system|logic)\.\w+'
        self.rules.append((re.compile(pmu_pattern), self.pmu_format))

        # Global PMU functions
        pmu_funcs = r'\b(getChannel|setChannel|getInput|setOutput|sendCAN|getVoltage|getTemperature|log|millis|delay|sleep)\b'
        self.rules.append((re.compile(pmu_funcs), self.pmu_format))

        # Numbers (integers and floats)
        number_pattern = r'\b\d+\.?\d*\b'
        self.rules.append((re.compile(number_pattern), self.number_format))

        # Function definitions
        func_pattern = r'\bfunction\s+(\w+)'
        self.rules.append((re.compile(func_pattern), self.function_format))

        # Function calls
        call_pattern = r'\b(\w+)\s*\('
        self.rules.append((re.compile(call_pattern), self.function_format))

        # Operators
        operator_pattern = r'[+\-*/%^#=<>~]|\.\.|\.\.\.'
        self.rules.append((re.compile(operator_pattern), self.operator_format))

    def highlightBlock(self, text: str):
        """Apply syntax highlighting to a block of text"""
        # Apply basic rules
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - match.start()
                self.setFormat(start, length, fmt)

        # Handle strings (single and double quoted)
        self._highlight_strings(text)

        # Handle comments
        self._highlight_comments(text)

    def _highlight_strings(self, text: str):
        """Highlight string literals"""
        in_string = False
        string_char = None
        start = 0

        i = 0
        while i < len(text):
            c = text[i]

            if not in_string:
                if c in '"\'':
                    in_string = True
                    string_char = c
                    start = i
                elif c == '[' and i + 1 < len(text) and text[i + 1] == '[':
                    # Long string [[...]]
                    end = text.find(']]', i + 2)
                    if end != -1:
                        self.setFormat(i, end + 2 - i, self.string_format)
                        i = end + 1
                    else:
                        self.setFormat(i, len(text) - i, self.string_format)
                        break
            else:
                if c == string_char and (i == 0 or text[i - 1] != '\\'):
                    self.setFormat(start, i - start + 1, self.string_format)
                    in_string = False
            i += 1

        # Unclosed string at end of line
        if in_string:
            self.setFormat(start, len(text) - start, self.string_format)

    def _highlight_comments(self, text: str):
        """Highlight comments"""
        # Single line comment
        comment_start = text.find('--')
        if comment_start != -1:
            # Check if it's a long comment --[[
            if comment_start + 2 < len(text) and text[comment_start + 2:comment_start + 4] == '[[':
                # Long comment (multi-line) - just highlight to end of line for now
                self.setFormat(comment_start, len(text) - comment_start, self.comment_format)
            else:
                self.setFormat(comment_start, len(text) - comment_start, self.comment_format)


class LineNumberArea(QWidget):
    """Widget for displaying line numbers"""

    def __init__(self, editor: 'LuaCodeEditor'):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class LuaCodeEditor(QPlainTextEdit):
    """Enhanced Lua code editor with line numbers and syntax highlighting"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Setup
        self._setup_font()
        self._setup_colors()
        self._setup_line_number_area()
        self._setup_highlighter()
        self._setup_completer()
        self._setup_behavior()

        # Connect signals
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        # Initial setup
        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def _setup_font(self):
        """Setup monospace font"""
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        # Tab width
        fm = QFontMetrics(font)
        self.setTabStopDistance(4 * fm.horizontalAdvance(' '))

    def _setup_colors(self):
        """Setup editor colors (dark theme)"""
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#1E1E1E"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#D4D4D4"))
        self.setPalette(palette)

        # Current line color
        self.current_line_color = QColor("#2D2D2D")

        # Line number colors
        self.line_number_bg = QColor("#1E1E1E")
        self.line_number_fg = QColor("#858585")

    def _setup_line_number_area(self):
        """Setup line number area widget"""
        self.line_number_area = LineNumberArea(self)

    def _setup_highlighter(self):
        """Setup syntax highlighter"""
        self.highlighter = LuaSyntaxHighlighter(self.document())

    def _setup_completer(self):
        """Setup autocomplete"""
        # Combine all completions
        completions = (
            PMU_API_FUNCTIONS +
            LUA_KEYWORDS +
            LUA_BUILTINS +
            MATH_FUNCTIONS +
            STRING_FUNCTIONS +
            TABLE_FUNCTIONS
        )

        self.completer = QCompleter(completions, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self._insert_completion)

    def _setup_behavior(self):
        """Setup editor behavior"""
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def line_number_area_width(self) -> int:
        """Calculate width needed for line number area"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1

        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def _update_line_number_area_width(self, _):
        """Update viewport margins when line count changes"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        """Scroll line number area with editor"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(),
                                         self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Handle resize to update line number area"""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                                 self.line_number_area_width(), cr.height()))

    def _highlight_current_line(self):
        """Highlight the current line"""
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self.current_line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        """Paint line numbers"""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), self.line_number_bg)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setPen(self.line_number_fg)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(0, top, self.line_number_area.width() - 5,
                               self.fontMetrics().height(),
                               Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key presses for special behavior"""
        # Handle completer
        if self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return,
                               Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                return

        # Tab → 4 spaces
        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
            return

        # Auto-indent on Enter
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()

            # Get current indentation
            indent = ""
            for c in text:
                if c in ' \t':
                    indent += c
                else:
                    break

            # Increase indent after keywords that start blocks
            stripped = text.strip()
            if stripped.endswith(':') or any(stripped.startswith(kw) for kw in
                                             ['function', 'if', 'for', 'while', 'repeat', 'else', 'elseif', 'do']):
                if not stripped.endswith('end'):
                    indent += "    "

            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return

        # Handle bracket matching hint
        if event.text() in '({[':
            super().keyPressEvent(event)
            matching = {'(': ')', '{': '}', '[': ']'}
            # Optionally auto-close brackets
            return

        super().keyPressEvent(event)

        # Show completer on typing
        if event.text() and (event.text().isalnum() or event.text() in '._'):
            self._show_completer()

    def _show_completer(self):
        """Show autocomplete popup"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        prefix = cursor.selectedText()

        # Include previous character for pmu. detection
        cursor2 = self.textCursor()
        cursor2.movePosition(QTextCursor.MoveOperation.StartOfWord)
        cursor2.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
        cursor2.movePosition(QTextCursor.MoveOperation.EndOfWord,
                           QTextCursor.MoveMode.KeepAnchor)
        extended_prefix = cursor2.selectedText()

        if extended_prefix.startswith('pmu.'):
            prefix = extended_prefix

        if len(prefix) < 2:
            self.completer.popup().hide()
            return

        if prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(prefix)
            self.completer.popup().setCurrentIndex(
                self.completer.completionModel().index(0, 0))

        rect = self.cursorRect()
        rect.setWidth(self.completer.popup().sizeHintForColumn(0)
                     + self.completer.popup().verticalScrollBar().sizeHint().width())
        self.completer.complete(rect)

    def _insert_completion(self, completion: str):
        """Insert the selected completion"""
        cursor = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        cursor.movePosition(QTextCursor.MoveOperation.Left)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfWord)
        cursor.insertText(completion[-extra:] if extra > 0 else '')
        self.setTextCursor(cursor)

    def get_cursor_position(self) -> tuple[int, int]:
        """Get current cursor position (line, column)"""
        cursor = self.textCursor()
        return cursor.blockNumber() + 1, cursor.columnNumber() + 1

    def goto_line(self, line: int):
        """Move cursor to specified line"""
        block = self.document().findBlockByLineNumber(line - 1)
        if block.isValid():
            cursor = QTextCursor(block)
            self.setTextCursor(cursor)
            self.centerCursor()

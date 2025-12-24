"""
Log Viewer Widget - Real-time firmware log monitoring.

Features:
- Real-time log streaming from device
- Log level filtering (DEBUG, INFO, WARN, ERROR)
- Source filtering (by module)
- Search/filter text
- Log file loading
- Export to file
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict
from collections import deque

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QPushButton,
    QComboBox, QLineEdit, QLabel, QTextEdit, QCheckBox,
    QFileDialog, QMessageBox, QSplitter, QListWidget, QListWidgetItem,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QFont, QAction, QTextCursor

logger = logging.getLogger(__name__)


# Log level colors
LOG_COLORS = {
    'DEBUG': '#888888',   # Gray
    'INFO': '#4CAF50',    # Green
    'WARN': '#FF9800',    # Orange
    'WARNING': '#FF9800', # Orange
    'ERROR': '#F44336',   # Red
}

LOG_LEVELS = ['DEBUG', 'INFO', 'WARN', 'ERROR']


class LogEntry:
    """Represents a single log entry."""

    def __init__(self, level: str, source: str, message: str, timestamp: datetime = None):
        self.level = level.upper()
        self.source = source
        self.message = message
        self.timestamp = timestamp or datetime.now()

    def __str__(self):
        ts = self.timestamp.strftime('%H:%M:%S.%f')[:-3]
        return f"[{ts}] [{self.level:5}] [{self.source:12}] {self.message}"


class LogViewerWidget(QWidget):
    """Widget for viewing firmware logs."""

    log_received = pyqtSignal(str, str, str)  # level, source, message

    def __init__(self, parent=None):
        super().__init__(parent)

        self.logs: deque = deque(maxlen=10000)  # Max 10000 entries
        self.sources: set = set()
        self.is_paused = False
        self.min_level = 'DEBUG'
        self.filter_text = ''
        self.filter_sources: set = set()  # Empty = all

        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # Level filter
        toolbar.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(LOG_LEVELS)
        self.level_combo.setCurrentText('INFO')
        self.level_combo.currentTextChanged.connect(self._on_level_changed)
        toolbar.addWidget(self.level_combo)

        toolbar.addSeparator()

        # Text filter
        toolbar.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search logs...")
        self.filter_edit.setMaximumWidth(200)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_edit)

        toolbar.addSeparator()

        # Pause button
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._on_pause_toggled)
        toolbar.addWidget(self.pause_btn)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._on_clear)
        toolbar.addWidget(clear_btn)

        toolbar.addSeparator()

        # Load/Save
        load_btn = QPushButton("Load...")
        load_btn.clicked.connect(self._on_load)
        toolbar.addWidget(load_btn)

        save_btn = QPushButton("Save...")
        save_btn.clicked.connect(self._on_save)
        toolbar.addWidget(save_btn)

        # Auto-scroll checkbox
        self.autoscroll_cb = QCheckBox("Auto-scroll")
        self.autoscroll_cb.setChecked(True)
        toolbar.addWidget(self.autoscroll_cb)

        layout.addWidget(toolbar)

        # Main area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Source list (left)
        source_panel = QWidget()
        source_layout = QVBoxLayout(source_panel)
        source_layout.setContentsMargins(0, 0, 0, 0)

        source_label = QLabel("Sources")
        source_label.setStyleSheet("font-weight: bold;")
        source_layout.addWidget(source_label)

        self.source_list = QListWidget()
        self.source_list.setMaximumWidth(150)
        self.source_list.itemChanged.connect(self._on_source_filter_changed)
        source_layout.addWidget(self.source_list)

        splitter.addWidget(source_panel)

        # Log text area (right)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Dark theme styling
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
            }
        """)

        splitter.addWidget(self.log_text)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([120, 500])

        layout.addWidget(splitter)

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("0 entries")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.rate_label = QLabel("0 msg/s")
        status_layout.addWidget(self.rate_label)
        layout.addLayout(status_layout)

        # Rate tracking
        self._msg_count = 0
        self._rate_timer = QTimer(self)
        self._rate_timer.timeout.connect(self._update_rate)
        self._rate_timer.start(1000)

    def _setup_connections(self):
        """Setup internal connections."""
        self.log_received.connect(self._on_log_received)

    def add_log(self, level: str, source: str, message: str):
        """Add a log entry (thread-safe via signal)."""
        self.log_received.emit(level, source, message)

    def _on_log_received(self, level: str, source: str, message: str):
        """Handle log entry (in UI thread)."""
        entry = LogEntry(level, source, message)
        self.logs.append(entry)
        self._msg_count += 1

        # Track sources
        if source and source not in self.sources:
            self.sources.add(source)
            self._add_source_item(source)

        # Update display if not paused
        if not self.is_paused:
            if self._should_show(entry):
                self._append_entry(entry)

        self._update_status()

    def _should_show(self, entry: LogEntry) -> bool:
        """Check if entry should be displayed based on filters."""
        # Level filter
        level_idx = LOG_LEVELS.index(entry.level) if entry.level in LOG_LEVELS else 0
        min_idx = LOG_LEVELS.index(self.min_level) if self.min_level in LOG_LEVELS else 0
        if level_idx < min_idx:
            return False

        # Source filter
        if self.filter_sources and entry.source not in self.filter_sources:
            return False

        # Text filter
        if self.filter_text:
            search = self.filter_text.lower()
            if search not in entry.message.lower() and search not in entry.source.lower():
                return False

        return True

    def _append_entry(self, entry: LogEntry):
        """Append entry to text display."""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Format with color
        fmt = QTextCharFormat()
        color = LOG_COLORS.get(entry.level, '#FFFFFF')
        fmt.setForeground(QColor(color))

        cursor.insertText(str(entry) + '\n', fmt)

        # Auto-scroll
        if self.autoscroll_cb.isChecked():
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()

    def _add_source_item(self, source: str):
        """Add source to filter list."""
        item = QListWidgetItem(source)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        self.source_list.addItem(item)

    def _rebuild_display(self):
        """Rebuild entire display from logs."""
        self.log_text.clear()
        for entry in self.logs:
            if self._should_show(entry):
                self._append_entry(entry)

    def _on_level_changed(self, level: str):
        self.min_level = level
        self._rebuild_display()

    def _on_filter_changed(self, text: str):
        self.filter_text = text
        self._rebuild_display()

    def _on_source_filter_changed(self, item: QListWidgetItem):
        self.filter_sources.clear()
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                self.filter_sources.add(item.text())
        self._rebuild_display()

    def _on_pause_toggled(self, paused: bool):
        self.is_paused = paused
        self.pause_btn.setText("Resume" if paused else "Pause")
        if not paused:
            self._rebuild_display()

    def _on_clear(self):
        self.logs.clear()
        self.log_text.clear()
        self._update_status()

    def _on_load(self):
        """Load logs from file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Log File", "",
            "Log Files (*.log *.txt);;All Files (*)"
        )
        if filename:
            try:
                self._load_log_file(filename)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load log file: {e}")

    def _load_log_file(self, filename: str):
        """Load and parse log file."""
        self.logs.clear()
        self.log_text.clear()

        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Try to parse structured log format
                # [HH:MM:SS.mmm] [LEVEL] [SOURCE] message
                try:
                    if line.startswith('['):
                        parts = line.split('] [')
                        if len(parts) >= 3:
                            ts_str = parts[0][1:]
                            level = parts[1]
                            rest = parts[2].split('] ', 1)
                            source = rest[0]
                            message = rest[1] if len(rest) > 1 else ''

                            entry = LogEntry(level, source, message)
                            self.logs.append(entry)

                            if source and source not in self.sources:
                                self.sources.add(source)
                                self._add_source_item(source)
                            continue
                except Exception:
                    pass

                # Plain text line
                entry = LogEntry('INFO', 'FILE', line)
                self.logs.append(entry)

        self._rebuild_display()
        self._update_status()

    def _on_save(self):
        """Save logs to file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", f"pmu_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for entry in self.logs:
                        f.write(str(entry) + '\n')
                QMessageBox.information(self, "Saved", f"Saved {len(self.logs)} log entries")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _update_status(self):
        """Update status bar."""
        visible = sum(1 for e in self.logs if self._should_show(e))
        self.status_label.setText(f"{visible}/{len(self.logs)} entries")

    def _update_rate(self):
        """Update message rate display."""
        self.rate_label.setText(f"{self._msg_count} msg/s")
        self._msg_count = 0

"""
Data Logger Widget - Professional ECU-style data logging and analysis.

Features:
- Real-time streaming telemetry at 50-500 Hz
- Multi-channel graph display with zoom/pan/scroll
- Channel selector with categories
- Time cursor and selection tools
- Recording to file
- CSV export
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import deque
import csv
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QPushButton, QComboBox, QSpinBox, QLabel, QCheckBox,
    QTreeWidget, QTreeWidgetItem, QSlider, QToolBar, QFileDialog,
    QMessageBox, QStatusBar, QMenu, QFrame, QScrollArea, QDoubleSpinBox,
    QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QAction, QColor, QPen

# Use pyqtgraph for fast plotting
try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False
    pg = None

logger = logging.getLogger(__name__)


# Channel category colors
CATEGORY_COLORS = {
    'System': '#4CAF50',      # Green
    'Outputs': '#2196F3',     # Blue
    'Inputs': '#FF9800',      # Orange
    'H-Bridge': '#9C27B0',    # Purple
    'CAN': '#00BCD4',         # Cyan
    'Logic': '#E91E63',       # Pink
    'PID': '#795548',         # Brown
    'User': '#607D8B',        # Gray
}

# Default channel definitions
DEFAULT_CHANNELS = [
    {'id': 0x0001, 'name': 'Battery Voltage', 'unit': 'V', 'category': 'System', 'min': 0, 'max': 30},
    {'id': 0x0002, 'name': 'Board Temp L', 'unit': 'C', 'category': 'System', 'min': -40, 'max': 125},
    {'id': 0x0003, 'name': 'Board Temp R', 'unit': 'C', 'category': 'System', 'min': -40, 'max': 125},
    {'id': 0x0004, 'name': '5V Output', 'unit': 'V', 'category': 'System', 'min': 0, 'max': 6},
    {'id': 0x0005, 'name': '3.3V Output', 'unit': 'V', 'category': 'System', 'min': 0, 'max': 4},
    {'id': 0x0006, 'name': 'Total Current', 'unit': 'A', 'category': 'System', 'min': 0, 'max': 200},
]


class DataChannel:
    """Represents a data channel for logging."""

    def __init__(self, channel_id: int, name: str, unit: str = '',
                 category: str = 'User', min_val: float = 0, max_val: float = 100,
                 color: Optional[str] = None):
        self.id = channel_id
        self.name = name
        self.unit = unit
        self.category = category
        self.min_val = min_val
        self.max_val = max_val
        self.enabled = False
        self.visible = True
        self.color = color or CATEGORY_COLORS.get(category, '#FFFFFF')

        # Data storage
        self.timestamps: List[float] = []
        self.values: List[float] = []

        # Statistics
        self.current_value = 0.0
        self.min_recorded = float('inf')
        self.max_recorded = float('-inf')
        self.avg_value = 0.0

    def add_sample(self, timestamp: float, value: float):
        """Add a data sample."""
        self.timestamps.append(timestamp)
        self.values.append(value)
        self.current_value = value

        # Update statistics
        if value < self.min_recorded:
            self.min_recorded = value
        if value > self.max_recorded:
            self.max_recorded = value

        # Running average
        n = len(self.values)
        self.avg_value = ((self.avg_value * (n - 1)) + value) / n

    def clear(self):
        """Clear all data."""
        self.timestamps.clear()
        self.values.clear()
        self.current_value = 0.0
        self.min_recorded = float('inf')
        self.max_recorded = float('-inf')
        self.avg_value = 0.0


class DataLoggerWidget(QWidget):
    """Professional data logger widget with graphs and analysis tools."""

    # Signals
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    channel_toggled = pyqtSignal(int, bool)  # channel_id, enabled

    def __init__(self, parent=None):
        super().__init__(parent)

        self.channels: Dict[int, DataChannel] = {}
        self.is_recording = False
        self.is_live = False
        self.start_time = 0.0
        self.sample_rate = 100  # Hz
        self.time_window = 10.0  # Seconds visible
        self.cursor_time = 0.0

        # Graph references
        self.plot_items: Dict[int, Any] = {}

        self._init_ui()
        self._init_channels()
        self._setup_timer()

    def _init_ui(self):
        """Initialize user interface."""
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        self._create_toolbar()
        layout.addWidget(self.toolbar)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        # Left panel - Channel selector
        left_panel = self._create_channel_panel()
        splitter.addWidget(left_panel)

        # Right panel - Graphs
        right_panel = self._create_graph_panel()
        splitter.addWidget(right_panel)

        # Set splitter proportions
        splitter.setSizes([250, 750])
        splitter.setStretchFactor(0, 0)  # Channel panel fixed
        splitter.setStretchFactor(1, 1)  # Graph panel expands

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setMaximumHeight(24)
        layout.addWidget(self.status_bar)

        self._update_status()

    def _create_toolbar(self):
        """Create main toolbar."""
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)

        # Recording controls
        self.record_btn = QPushButton("Record")
        self.record_btn.setCheckable(True)
        self.record_btn.toggled.connect(self._on_record_toggled)
        self.toolbar.addWidget(self.record_btn)

        self.live_btn = QPushButton("Live")
        self.live_btn.setCheckable(True)
        self.live_btn.toggled.connect(self._on_live_toggled)
        self.toolbar.addWidget(self.live_btn)

        self.toolbar.addSeparator()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._on_clear)
        self.toolbar.addWidget(clear_btn)

        self.toolbar.addSeparator()

        # Sample rate
        self.toolbar.addWidget(QLabel("Rate:"))
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(10, 500)
        self.rate_spin.setValue(100)
        self.rate_spin.setSuffix(" Hz")
        self.rate_spin.valueChanged.connect(self._on_rate_changed)
        self.toolbar.addWidget(self.rate_spin)

        self.toolbar.addSeparator()

        # Time window
        self.toolbar.addWidget(QLabel("Window:"))
        self.window_spin = QSpinBox()
        self.window_spin.setRange(1, 300)
        self.window_spin.setValue(10)
        self.window_spin.setSuffix(" s")
        self.window_spin.valueChanged.connect(self._on_window_changed)
        self.toolbar.addWidget(self.window_spin)

        self.toolbar.addSeparator()

        # Zoom controls
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedWidth(30)
        zoom_in_btn.clicked.connect(self._zoom_in)
        self.toolbar.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedWidth(30)
        zoom_out_btn.clicked.connect(self._zoom_out)
        self.toolbar.addWidget(zoom_out_btn)

        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self._zoom_fit)
        self.toolbar.addWidget(fit_btn)

        self.toolbar.addSeparator()

        # Export
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._on_export)
        self.toolbar.addWidget(export_btn)

        # Load log
        load_btn = QPushButton("Load Log")
        load_btn.clicked.connect(self._on_load_log)
        self.toolbar.addWidget(load_btn)

        self.toolbar.addSeparator()

        # Trigger recording
        self.trigger_btn = QPushButton("Trigger")
        self.trigger_btn.setCheckable(True)
        self.trigger_btn.setToolTip("Enable trigger-based recording")
        self.trigger_btn.toggled.connect(self._on_trigger_toggled)
        self.toolbar.addWidget(self.trigger_btn)

        # Trigger settings (shown when trigger enabled)
        self.trigger_channel_combo = QComboBox()
        self.trigger_channel_combo.setMinimumWidth(120)
        self.trigger_channel_combo.setToolTip("Trigger channel")
        self.trigger_channel_combo.setVisible(False)
        self.toolbar.addWidget(self.trigger_channel_combo)

        self.trigger_condition_combo = QComboBox()
        self.trigger_condition_combo.addItems(['>', '<', '>=', '<=', '==', '!=', 'Rising', 'Falling'])
        self.trigger_condition_combo.setToolTip("Trigger condition")
        self.trigger_condition_combo.setVisible(False)
        self.toolbar.addWidget(self.trigger_condition_combo)

        self.trigger_value_spin = QDoubleSpinBox()
        self.trigger_value_spin.setRange(-99999, 99999)
        self.trigger_value_spin.setValue(0)
        self.trigger_value_spin.setToolTip("Trigger value")
        self.trigger_value_spin.setVisible(False)
        self.toolbar.addWidget(self.trigger_value_spin)

        # Pre-trigger buffer
        self.toolbar.addWidget(QLabel("Pre:"))
        self.pretrigger_spin = QSpinBox()
        self.pretrigger_spin.setRange(0, 60)
        self.pretrigger_spin.setValue(2)
        self.pretrigger_spin.setSuffix(" s")
        self.pretrigger_spin.setToolTip("Pre-trigger buffer (seconds)")
        self.pretrigger_spin.setVisible(False)
        self.toolbar.addWidget(self.pretrigger_spin)

        # Trigger state tracking
        self.trigger_enabled = False
        self.trigger_armed = False
        self.trigger_last_value = None

    def _create_channel_panel(self) -> QWidget:
        """Create channel selector panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)

        # Channel tree
        self.channel_tree = QTreeWidget()
        self.channel_tree.setHeaderLabels(['Channel', 'Value', 'Unit'])
        self.channel_tree.setColumnWidth(0, 150)
        self.channel_tree.setColumnWidth(1, 60)
        self.channel_tree.setColumnWidth(2, 40)
        self.channel_tree.itemChanged.connect(self._on_channel_item_changed)
        self.channel_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.channel_tree.customContextMenuRequested.connect(self._on_channel_context_menu)
        layout.addWidget(self.channel_tree)

        # Quick actions
        btn_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_channels)
        btn_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self._clear_all_channels)
        btn_layout.addWidget(clear_all_btn)

        layout.addLayout(btn_layout)

        return panel

    def _create_graph_panel(self) -> QWidget:
        """Create graph display panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_PYQTGRAPH:
            # Configure pyqtgraph
            pg.setConfigOptions(antialias=True, background='k', foreground='w')

            # Create plot widget
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setLabel('bottom', 'Time', units='s')
            self.plot_widget.setLabel('left', 'Value')

            # Enable mouse interaction
            self.plot_widget.setMouseEnabled(x=True, y=True)
            self.plot_widget.enableAutoRange(axis='y')

            # Add cursor line
            self.cursor_line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('r', width=1))
            self.plot_widget.addItem(self.cursor_line)

            # Add legend
            self.legend = self.plot_widget.addLegend()

            layout.addWidget(self.plot_widget)
        else:
            # Fallback label
            label = QLabel("pyqtgraph not installed. Install with: pip install pyqtgraph")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: red; padding: 20px;")
            layout.addWidget(label)
            self.plot_widget = None

        # Time slider
        slider_layout = QHBoxLayout()

        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 1000)
        self.time_slider.setValue(1000)  # Start at end
        self.time_slider.valueChanged.connect(self._on_time_slider_changed)
        slider_layout.addWidget(self.time_slider)

        self.time_label = QLabel("0.000 s")
        self.time_label.setMinimumWidth(80)
        slider_layout.addWidget(self.time_label)

        layout.addLayout(slider_layout)

        return panel

    def _init_channels(self):
        """Initialize default channels."""
        # Add default channels
        for ch_def in DEFAULT_CHANNELS:
            self.add_channel(
                ch_def['id'], ch_def['name'], ch_def['unit'],
                ch_def.get('category', 'User'),
                ch_def.get('min', 0), ch_def.get('max', 100)
            )

        # Add output channels (30)
        for i in range(30):
            self.add_channel(
                0x0100 + i * 2, f'OUT{i+1} State', '', 'Outputs', 0, 1
            )
            self.add_channel(
                0x0100 + i * 2 + 1, f'OUT{i+1} Current', 'A', 'Outputs', 0, 30
            )

        # Add analog inputs (20)
        for i in range(20):
            self.add_channel(
                0x0200 + i, f'AIN{i+1}', 'V', 'Inputs', 0, 5
            )

        # Add H-Bridge channels (4)
        for i in range(4):
            self.add_channel(0x0300 + i * 4, f'HB{i+1} Position', '%', 'H-Bridge', 0, 100)
            self.add_channel(0x0300 + i * 4 + 1, f'HB{i+1} Current', 'A', 'H-Bridge', -30, 30)
            self.add_channel(0x0300 + i * 4 + 2, f'HB{i+1} PWM', '%', 'H-Bridge', 0, 100)

        self._update_channel_tree()

    def populate_from_config(self, config_manager):
        """
        Populate virtual channels from configuration.

        Virtual channels (Logic, Number, Switch, CAN RX) get IDs starting at 200
        in the same order as they appear in the config (same as firmware assignment).
        """
        try:
            all_channels = config_manager.get_all_channels()

            # Track virtual channel ID - starts at 200, same as firmware
            virtual_channel_id = 200

            # Virtual channel types and their display info
            VIRTUAL_TYPES = {
                'logic': {'category': 'Logic', 'prefix': 'Logic', 'unit': '', 'min': 0, 'max': 1},
                'number': {'category': 'Logic', 'prefix': 'Number', 'unit': '', 'min': -999999, 'max': 999999},
                'switch': {'category': 'Logic', 'prefix': 'Switch', 'unit': '', 'min': 0, 'max': 100},
                'can_rx': {'category': 'CAN', 'prefix': 'CAN RX', 'unit': '', 'min': -999999, 'max': 999999},
                'timer': {'category': 'Logic', 'prefix': 'Timer', 'unit': 'ms', 'min': 0, 'max': 999999},
                'filter': {'category': 'Logic', 'prefix': 'Filter', 'unit': '', 'min': -999999, 'max': 999999},
            }

            # Process channels in same order as config to match firmware IDs
            for ch in all_channels:
                ch_type = ch.get('channel_type', '')
                if ch_type in VIRTUAL_TYPES:
                    info = VIRTUAL_TYPES[ch_type]
                    ch_id = ch.get('id', 0)
                    ch_name = ch.get('name', f'{info["prefix"]}_{ch_id}')

                    # Use virtual_channel_id which matches telemetry
                    self.add_channel(
                        virtual_channel_id,
                        ch_name,
                        info['unit'],
                        info['category'],
                        info['min'],
                        info['max']
                    )
                    virtual_channel_id += 1

            self._update_channel_tree()
            logger.info(f"Loaded {virtual_channel_id - 200} virtual channels to Data Logger")

        except Exception as e:
            logger.error(f"Error populating Data Logger from config: {e}")

    def _setup_timer(self):
        """Setup update timer."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_update)
        self.update_timer.start(50)  # 20 Hz UI update

    def add_channel(self, channel_id: int, name: str, unit: str = '',
                    category: str = 'User', min_val: float = 0, max_val: float = 100):
        """Add a data channel."""
        if channel_id in self.channels:
            return

        channel = DataChannel(channel_id, name, unit, category, min_val, max_val)
        self.channels[channel_id] = channel

    def remove_channel(self, channel_id: int):
        """Remove a data channel."""
        if channel_id in self.channels:
            del self.channels[channel_id]
            if channel_id in self.plot_items:
                if self.plot_widget:
                    self.plot_widget.removeItem(self.plot_items[channel_id])
                del self.plot_items[channel_id]

    def _update_channel_tree(self):
        """Update channel tree widget."""
        self.channel_tree.blockSignals(True)
        self.channel_tree.clear()

        # Group by category
        categories: Dict[str, List[DataChannel]] = {}
        for channel in self.channels.values():
            if channel.category not in categories:
                categories[channel.category] = []
            categories[channel.category].append(channel)

        # Create tree items
        for cat_name, channels in sorted(categories.items()):
            cat_item = QTreeWidgetItem([cat_name])
            cat_item.setFlags(cat_item.flags() | Qt.ItemFlag.ItemIsAutoTristate)

            color = CATEGORY_COLORS.get(cat_name, '#FFFFFF')
            cat_item.setForeground(0, QColor(color))

            for channel in sorted(channels, key=lambda c: c.name):
                ch_item = QTreeWidgetItem([
                    channel.name,
                    f'{channel.current_value:.2f}',
                    channel.unit
                ])
                ch_item.setData(0, Qt.ItemDataRole.UserRole, channel.id)
                ch_item.setFlags(ch_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                ch_item.setCheckState(0, Qt.CheckState.Checked if channel.enabled else Qt.CheckState.Unchecked)
                ch_item.setForeground(0, QColor(channel.color))
                cat_item.addChild(ch_item)

            self.channel_tree.addTopLevelItem(cat_item)
            cat_item.setExpanded(False)  # Collapsed by default

        self.channel_tree.blockSignals(False)

    def _on_channel_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle channel checkbox change."""
        if column == 0 and item.parent():  # Is a channel item
            channel_id = item.data(0, Qt.ItemDataRole.UserRole)
            checked = item.checkState(0) == Qt.CheckState.Checked

            if channel_id in self.channels:
                self.channels[channel_id].enabled = checked
                self._update_plot_visibility(channel_id)
                self.channel_toggled.emit(channel_id, checked)

    def _on_channel_context_menu(self, pos):
        """Show channel context menu."""
        item = self.channel_tree.itemAt(pos)
        if not item or not item.parent():
            return

        channel_id = item.data(0, Qt.ItemDataRole.UserRole)
        channel = self.channels.get(channel_id)
        if not channel:
            return

        menu = QMenu(self)

        # Toggle visibility
        if channel.enabled:
            action = menu.addAction("Hide from graph")
            action.triggered.connect(lambda: self._toggle_channel_visibility(channel_id))

        # Change color
        color_menu = menu.addMenu("Color")
        colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FFFFFF']
        for color in colors:
            action = color_menu.addAction("")
            action.setData(color)
            action.triggered.connect(lambda checked, c=color: self._set_channel_color(channel_id, c))

        menu.exec(self.channel_tree.mapToGlobal(pos))

    def _toggle_channel_visibility(self, channel_id: int):
        """Toggle channel visibility."""
        if channel_id in self.channels:
            self.channels[channel_id].visible = not self.channels[channel_id].visible
            self._update_plot_visibility(channel_id)

    def _set_channel_color(self, channel_id: int, color: str):
        """Set channel color."""
        if channel_id in self.channels:
            self.channels[channel_id].color = color
            if channel_id in self.plot_items and self.plot_widget:
                self.plot_items[channel_id].setPen(pg.mkPen(color, width=1))

    def _update_plot_visibility(self, channel_id: int):
        """Update plot item visibility."""
        if not self.plot_widget or not HAS_PYQTGRAPH:
            return

        channel = self.channels.get(channel_id)
        if not channel:
            return

        if channel.enabled and channel.visible:
            if channel_id not in self.plot_items:
                # Create plot item
                pen = pg.mkPen(channel.color, width=1)
                self.plot_items[channel_id] = self.plot_widget.plot(
                    [], [], pen=pen, name=channel.name
                )
        else:
            if channel_id in self.plot_items:
                self.plot_widget.removeItem(self.plot_items[channel_id])
                del self.plot_items[channel_id]

    def _select_all_channels(self):
        """Select all channels."""
        for channel in self.channels.values():
            channel.enabled = True
        self._update_channel_tree()
        for ch_id in self.channels:
            self._update_plot_visibility(ch_id)

    def _clear_all_channels(self):
        """Clear all channel selections."""
        for channel in self.channels.values():
            channel.enabled = False
        self._update_channel_tree()
        for ch_id in self.channels:
            self._update_plot_visibility(ch_id)

    def _add_math_channel(self):
        """Add a calculated math channel."""
        from PyQt6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Math Channel")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        # Channel name
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g., Total Power")
        layout.addRow("Name:", name_edit)

        # Source channel A
        ch_a_combo = QComboBox()
        for ch_id, ch in sorted(self.channels.items(), key=lambda x: x[1].name):
            ch_a_combo.addItem(ch.name, ch_id)
        layout.addRow("Channel A:", ch_a_combo)

        # Operation
        op_combo = QComboBox()
        op_combo.addItems(['+', '-', '*', '/', 'max', 'min', 'avg', 'abs(A)', 'sqrt(A)', 'A^2'])
        layout.addRow("Operation:", op_combo)

        # Source channel B (optional for some ops)
        ch_b_combo = QComboBox()
        ch_b_combo.addItem("(constant)", None)
        for ch_id, ch in sorted(self.channels.items(), key=lambda x: x[1].name):
            ch_b_combo.addItem(ch.name, ch_id)
        layout.addRow("Channel B:", ch_b_combo)

        # Constant value
        const_spin = QDoubleSpinBox()
        const_spin.setRange(-99999, 99999)
        const_spin.setValue(1.0)
        layout.addRow("Constant:", const_spin)

        # Unit
        unit_edit = QLineEdit()
        unit_edit.setPlaceholderText("e.g., W, V, A")
        layout.addRow("Unit:", unit_edit)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text() or "Math Channel"
            ch_a_id = ch_a_combo.currentData()
            op = op_combo.currentText()
            ch_b_id = ch_b_combo.currentData()
            const_val = const_spin.value()
            unit = unit_edit.text()

            # Create math channel with unique ID
            math_id = 0x1000 + len([c for c in self.channels if c >= 0x1000])

            # Store math channel config
            math_config = {
                'ch_a': ch_a_id,
                'op': op,
                'ch_b': ch_b_id,
                'const': const_val
            }

            self.add_channel(math_id, name, unit, 'User', -99999, 99999)
            self.channels[math_id].math_config = math_config
            self._update_channel_tree()

            logger.info(f"Added math channel: {name} = {op}")

    def _compute_math_channels(self, timestamp: float):
        """Compute values for math channels."""
        for ch_id, channel in self.channels.items():
            if not hasattr(channel, 'math_config'):
                continue

            cfg = channel.math_config
            ch_a = self.channels.get(cfg['ch_a'])
            ch_b = self.channels.get(cfg['ch_b']) if cfg['ch_b'] else None

            if not ch_a or not ch_a.values:
                continue

            val_a = ch_a.current_value
            val_b = ch_b.current_value if ch_b and ch_b.values else cfg['const']

            result = 0
            op = cfg['op']

            try:
                if op == '+':
                    result = val_a + val_b
                elif op == '-':
                    result = val_a - val_b
                elif op == '*':
                    result = val_a * val_b
                elif op == '/':
                    result = val_a / val_b if val_b != 0 else 0
                elif op == 'max':
                    result = max(val_a, val_b)
                elif op == 'min':
                    result = min(val_a, val_b)
                elif op == 'avg':
                    result = (val_a + val_b) / 2
                elif op == 'abs(A)':
                    result = abs(val_a)
                elif op == 'sqrt(A)':
                    result = val_a ** 0.5 if val_a >= 0 else 0
                elif op == 'A^2':
                    result = val_a * val_a

                channel.add_sample(timestamp, result)
            except Exception:
                pass

    def add_sample(self, channel_id: int, timestamp: float, value: float):
        """Add a sample to a channel."""
        if channel_id in self.channels:
            self.channels[channel_id].add_sample(timestamp, value)

            # Check trigger
            if self._check_trigger(channel_id, value):
                self._on_trigger_fired()

    def add_samples(self, timestamp: float, data: Dict[int, float]):
        """Add samples for multiple channels."""
        for channel_id, value in data.items():
            self.add_sample(channel_id, timestamp, value)

    def _on_trigger_fired(self):
        """Handle trigger condition met."""
        if not self.trigger_armed:
            return

        self.trigger_armed = False  # One-shot
        self.trigger_btn.setText("Triggered!")
        self.trigger_btn.setStyleSheet("background-color: #44FF44;")

        # Start recording if not already
        if not self.is_recording:
            self.record_btn.setChecked(True)

    def update_from_telemetry(self, telemetry_data: dict):
        """Update data logger from telemetry data.

        Maps telemetry fields to channel IDs:
        - 0x0001: Battery Voltage (V)
        - 0x0002: Board Temp Left (C)
        - 0x0003: Board Temp Right (C)
        - 0x0004: 5V Output (V)
        - 0x0005: 3.3V Output (V)
        - 0x0100 + i*2: OUTi State (0/1)
        - 0x0100 + i*2 + 1: OUTi Current (A)
        - 0x0200 + i: AINi (V)
        """
        if not self.is_live:
            return

        import time
        if self.start_time == 0:
            self.start_time = time.time()

        timestamp = time.time() - self.start_time

        samples = {}

        # System channels
        if 'voltage_v' in telemetry_data:
            samples[0x0001] = telemetry_data['voltage_v']
        if 'temperature_c' in telemetry_data:
            samples[0x0002] = telemetry_data['temperature_c']
        if 'board_temp_2' in telemetry_data and telemetry_data['board_temp_2']:
            samples[0x0003] = telemetry_data['board_temp_2']
        if 'output_5v_mv' in telemetry_data and telemetry_data['output_5v_mv']:
            samples[0x0004] = telemetry_data['output_5v_mv'] / 1000.0
        if 'output_3v3_mv' in telemetry_data and telemetry_data['output_3v3_mv']:
            samples[0x0005] = telemetry_data['output_3v3_mv'] / 1000.0
        if 'current_a' in telemetry_data:
            samples[0x0006] = telemetry_data['current_a']

        # Output channels
        if 'channel_states' in telemetry_data:
            states = telemetry_data['channel_states']
            for i, state in enumerate(states[:30]):
                samples[0x0100 + i * 2] = float(state) if state else 0.0

        if 'channel_currents' in telemetry_data:
            currents = telemetry_data['channel_currents']
            for i, current in enumerate(currents[:30]):
                samples[0x0100 + i * 2 + 1] = float(current) if current else 0.0

        # Analog inputs
        if 'analog_values' in telemetry_data:
            adc_values = telemetry_data['analog_values']
            for i, val in enumerate(adc_values[:20]):
                # Convert ADC to voltage (12-bit ADC, 3.3V reference)
                voltage = (float(val) / 4095.0) * 3.3 if val else 0.0
                samples[0x0200 + i] = voltage

        # Virtual channels (Logic, Number, Switch, CAN RX, etc.)
        if 'virtual_channels' in telemetry_data:
            for ch_id, value in telemetry_data['virtual_channels'].items():
                samples[ch_id] = float(value)

        # Add all samples
        if samples:
            self.add_samples(timestamp, samples)
            # Compute math channels
            self._compute_math_channels(timestamp)

    def _on_update(self):
        """Periodic UI update."""
        if not self.plot_widget or not HAS_PYQTGRAPH:
            return

        # Update plots
        for channel_id, plot_item in self.plot_items.items():
            channel = self.channels.get(channel_id)
            if channel and channel.timestamps:
                plot_item.setData(channel.timestamps, channel.values)

        # Update channel values in tree
        self._update_channel_values()

        # Update status
        self._update_status()

    def _update_channel_values(self):
        """Update displayed channel values."""
        for i in range(self.channel_tree.topLevelItemCount()):
            cat_item = self.channel_tree.topLevelItem(i)
            for j in range(cat_item.childCount()):
                ch_item = cat_item.child(j)
                channel_id = ch_item.data(0, Qt.ItemDataRole.UserRole)
                channel = self.channels.get(channel_id)
                if channel:
                    ch_item.setText(1, f'{channel.current_value:.2f}')

    def _update_status(self):
        """Update status bar."""
        total_samples = sum(len(ch.timestamps) for ch in self.channels.values())
        enabled_count = sum(1 for ch in self.channels.values() if ch.enabled)

        status = f"Channels: {enabled_count}/{len(self.channels)} | "
        status += f"Samples: {total_samples} | "
        status += f"Rate: {self.sample_rate} Hz | "
        status += f"Recording: {'Yes' if self.is_recording else 'No'} | "
        status += f"Live: {'Yes' if self.is_live else 'No'}"

        self.status_bar.showMessage(status)

    def _on_record_toggled(self, checked: bool):
        """Handle record button toggle."""
        self.is_recording = checked
        if checked:
            self.start_time = 0.0  # Will be set on first sample
            self.record_btn.setText("Stop")
            self.record_btn.setStyleSheet("background-color: #FF4444;")
            self.recording_started.emit()
        else:
            self.record_btn.setText("Record")
            self.record_btn.setStyleSheet("")
            self.recording_stopped.emit()

    def _on_live_toggled(self, checked: bool):
        """Handle live button toggle."""
        self.is_live = checked
        if checked:
            self.live_btn.setText("Stop Live")
            self.live_btn.setStyleSheet("background-color: #44FF44;")
        else:
            self.live_btn.setText("Live")
            self.live_btn.setStyleSheet("")

    def _on_trigger_toggled(self, checked: bool):
        """Handle trigger button toggle."""
        self.trigger_enabled = checked
        self.trigger_armed = checked

        # Show/hide trigger settings
        self.trigger_channel_combo.setVisible(checked)
        self.trigger_condition_combo.setVisible(checked)
        self.trigger_value_spin.setVisible(checked)
        self.pretrigger_spin.setVisible(checked)

        if checked:
            self.trigger_btn.setText("Armed")
            self.trigger_btn.setStyleSheet("background-color: #FFAA00;")
            # Populate trigger channel combo
            self._update_trigger_channels()
        else:
            self.trigger_btn.setText("Trigger")
            self.trigger_btn.setStyleSheet("")
            self.trigger_last_value = None

    def _update_trigger_channels(self):
        """Update trigger channel combo with available channels."""
        self.trigger_channel_combo.clear()
        for ch_id, channel in sorted(self.channels.items(), key=lambda x: x[1].name):
            self.trigger_channel_combo.addItem(channel.name, ch_id)

    def _check_trigger(self, channel_id: int, value: float) -> bool:
        """Check if trigger condition is met."""
        if not self.trigger_enabled or not self.trigger_armed:
            return False

        # Check if this is the trigger channel
        trigger_ch_id = self.trigger_channel_combo.currentData()
        if trigger_ch_id != channel_id:
            return False

        condition = self.trigger_condition_combo.currentText()
        threshold = self.trigger_value_spin.value()

        triggered = False

        if condition == '>':
            triggered = value > threshold
        elif condition == '<':
            triggered = value < threshold
        elif condition == '>=':
            triggered = value >= threshold
        elif condition == '<=':
            triggered = value <= threshold
        elif condition == '==':
            triggered = abs(value - threshold) < 0.001
        elif condition == '!=':
            triggered = abs(value - threshold) >= 0.001
        elif condition == 'Rising':
            if self.trigger_last_value is not None:
                triggered = self.trigger_last_value < threshold and value >= threshold
        elif condition == 'Falling':
            if self.trigger_last_value is not None:
                triggered = self.trigger_last_value >= threshold and value < threshold

        self.trigger_last_value = value
        return triggered

    def _on_clear(self):
        """Clear all data."""
        for channel in self.channels.values():
            channel.clear()
        self._update_status()

    def _on_rate_changed(self, value: int):
        """Handle sample rate change."""
        self.sample_rate = value

    def _on_window_changed(self, value: int):
        """Handle time window change."""
        self.time_window = value
        if self.plot_widget:
            # Update x-axis range
            pass  # Auto-range handles this

    def _zoom_in(self):
        """Zoom in on graphs."""
        if self.plot_widget:
            vb = self.plot_widget.getViewBox()
            vb.scaleBy((0.5, 0.5))

    def _zoom_out(self):
        """Zoom out on graphs."""
        if self.plot_widget:
            vb = self.plot_widget.getViewBox()
            vb.scaleBy((2.0, 2.0))

    def _zoom_fit(self):
        """Fit all data in view."""
        if self.plot_widget:
            self.plot_widget.enableAutoRange()

    def _on_time_slider_changed(self, value: int):
        """Handle time slider change."""
        if not self.channels:
            return

        # Find max timestamp across all channels
        max_time = 0
        for channel in self.channels.values():
            if channel.timestamps:
                max_time = max(max_time, channel.timestamps[-1])

        if max_time > 0:
            self.cursor_time = (value / 1000.0) * max_time
            self.time_label.setText(f"{self.cursor_time:.3f} s")

            if self.plot_widget and HAS_PYQTGRAPH:
                self.cursor_line.setPos(self.cursor_time)

    def _on_export(self):
        """Export data to CSV."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not filename:
            return

        if not filename.endswith('.csv'):
            filename += '.csv'

        try:
            self.export_to_csv(filename)
            QMessageBox.information(self, "Export Complete",
                                   f"Data exported to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def export_to_csv(self, filename: str):
        """Export all enabled channel data to CSV."""
        enabled_channels = [ch for ch in self.channels.values() if ch.enabled]

        if not enabled_channels:
            raise ValueError("No channels enabled for export")

        # Find all unique timestamps
        all_timestamps = set()
        for channel in enabled_channels:
            all_timestamps.update(channel.timestamps)
        all_timestamps = sorted(all_timestamps)

        if not all_timestamps:
            raise ValueError("No data to export")

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            header = ['Time (s)']
            for ch in enabled_channels:
                header.append(f'{ch.name} ({ch.unit})' if ch.unit else ch.name)
            writer.writerow(header)

            # Data rows
            for ts in all_timestamps:
                row = [f'{ts:.4f}']
                for ch in enabled_channels:
                    # Find closest value for this timestamp
                    if ts in ch.timestamps:
                        idx = ch.timestamps.index(ts)
                        row.append(f'{ch.values[idx]:.4f}')
                    else:
                        row.append('')
                writer.writerow(row)

        logger.info(f"Exported {len(all_timestamps)} samples to {filename}")

    def _on_load_log(self):
        """Load log file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Log File", "",
            "Log Files (*.plog *.csv);;All Files (*)"
        )

        if not filename:
            return

        try:
            if filename.endswith('.csv'):
                self.load_from_csv(filename)
            else:
                self.load_from_plog(filename)
            QMessageBox.information(self, "Load Complete",
                                   f"Loaded log from {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))

    def load_from_csv(self, filename: str):
        """Load data from CSV file."""
        self._on_clear()

        with open(filename, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)

            # Parse channel names from header
            for i, col_name in enumerate(header[1:], start=1):
                # Extract channel name and unit
                name = col_name
                unit = ''
                if '(' in col_name and ')' in col_name:
                    name = col_name[:col_name.rfind('(')].strip()
                    unit = col_name[col_name.rfind('(')+1:col_name.rfind(')')]

                ch_id = 0x1000 + i
                self.add_channel(ch_id, name, unit, 'User')
                self.channels[ch_id].enabled = True

            # Read data
            channel_ids = list(self.channels.keys())[-len(header)+1:]

            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    timestamp = float(row[0])
                    for i, value_str in enumerate(row[1:]):
                        if value_str and i < len(channel_ids):
                            self.add_sample(channel_ids[i], timestamp, float(value_str))
                except ValueError:
                    continue

        self._update_channel_tree()
        for ch_id in channel_ids:
            self._update_plot_visibility(ch_id)

    def load_from_plog(self, filename: str):
        """Load data from binary PLOG file."""
        # TODO: Implement binary log file loading
        raise NotImplementedError("PLOG file loading not yet implemented")

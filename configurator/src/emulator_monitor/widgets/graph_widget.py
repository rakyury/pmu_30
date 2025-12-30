"""
Graph Widget - Real-time graphing widget using pyqtgraph

This module contains the RealTimeGraphWidget for visualizing telemetry data.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from typing import Dict
from collections import deque
from datetime import datetime


class RealTimeGraphWidget(QWidget):
    """Real-time graph widget using pyqtgraph."""

    COLORS = [
        '#22c55e',  # Green
        '#3b82f6',  # Blue
        '#f59e0b',  # Orange
        '#ef4444',  # Red
        '#8b5cf6',  # Purple
        '#06b6d4',  # Cyan
        '#f97316',  # Dark orange
        '#ec4899',  # Pink
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._data_history: Dict[str, deque] = {}
        self._time_data: deque = deque(maxlen=500)
        self._start_time = datetime.now()

    def _setup_ui(self):
        # Set size policy to expand
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Try to import pyqtgraph
        try:
            import pyqtgraph as pg

            # Configure pyqtgraph
            pg.setConfigOptions(antialias=True, background='#1a1a1a', foreground='#ffffff')

            # Control bar
            control_layout = QHBoxLayout()

            # Enable checkbox - graphs disabled by default
            self.enable_checkbox = QCheckBox("Enable Graphs")
            self.enable_checkbox.setChecked(False)
            self.enable_checkbox.stateChanged.connect(self._toggle_enable)
            control_layout.addWidget(self.enable_checkbox)

            self.pause_btn = QPushButton("Pause")
            self.pause_btn.setCheckable(True)
            self.pause_btn.setEnabled(False)  # Disabled until graphs are enabled
            self.pause_btn.clicked.connect(self._toggle_pause)
            control_layout.addWidget(self.pause_btn)

            self.clear_btn = QPushButton("Clear")
            self.clear_btn.setEnabled(False)  # Disabled until graphs are enabled
            self.clear_btn.clicked.connect(self._clear_data)
            control_layout.addWidget(self.clear_btn)

            control_layout.addWidget(QLabel("Time Window:"))
            self.time_window_spin = QSpinBox()
            self.time_window_spin.setRange(5, 120)
            self.time_window_spin.setValue(30)
            self.time_window_spin.setSuffix(" sec")
            control_layout.addWidget(self.time_window_spin)

            control_layout.addStretch()
            layout.addLayout(control_layout)

            # Create plot widget with multiple subplots
            self.graphics_layout = pg.GraphicsLayoutWidget()
            self.graphics_layout.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self.graphics_layout, 1)  # Stretch factor 1

            # Create subplots
            # Analog inputs plot
            self.analog_plot = self.graphics_layout.addPlot(row=0, col=0, title="Analog Inputs")
            self.analog_plot.setLabel('left', 'Voltage', units='V')
            self.analog_plot.setLabel('bottom', 'Time', units='s')
            self.analog_plot.showGrid(x=True, y=True, alpha=0.3)
            self.analog_plot.setYRange(0, 5)
            self.analog_curves = {}

            # Current draw plot
            self.current_plot = self.graphics_layout.addPlot(row=0, col=1, title="Output Currents")
            self.current_plot.setLabel('left', 'Current', units='A')
            self.current_plot.setLabel('bottom', 'Time', units='s')
            self.current_plot.showGrid(x=True, y=True, alpha=0.3)
            self.current_plot.setYRange(0, 20)
            self.current_curves = {}

            # H-Bridge positions plot
            self.hbridge_plot = self.graphics_layout.addPlot(row=1, col=0, title="H-Bridge Positions")
            self.hbridge_plot.setLabel('left', 'Position')
            self.hbridge_plot.setLabel('bottom', 'Time', units='s')
            self.hbridge_plot.showGrid(x=True, y=True, alpha=0.3)
            self.hbridge_plot.setYRange(0, 1000)
            self.hbridge_curves = {}

            # System plot (voltage, temp)
            self.system_plot = self.graphics_layout.addPlot(row=1, col=1, title="System Status")
            self.system_plot.setLabel('left', 'Value')
            self.system_plot.setLabel('bottom', 'Time', units='s')
            self.system_plot.showGrid(x=True, y=True, alpha=0.3)
            self.system_curves = {}

            # Add legend
            self.analog_plot.addLegend(offset=(10, 10))
            self.current_plot.addLegend(offset=(10, 10))
            self.hbridge_plot.addLegend(offset=(10, 10))
            self.system_plot.addLegend(offset=(10, 10))

            self._paused = True  # Disabled by default
            self._enabled = False  # Graphs disabled by default
            self._pg = pg

        except ImportError:
            error_label = QLabel("pyqtgraph not installed.\nInstall with: pip install pyqtgraph")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px;")
            layout.addWidget(error_label)
            self._pg = None
            self._enabled = False

    def _toggle_enable(self, state: int):
        """Toggle graph enable state."""
        self._enabled = state == 2  # Qt.CheckState.Checked is 2
        self.pause_btn.setEnabled(self._enabled)
        self.clear_btn.setEnabled(self._enabled)
        if self._enabled:
            self._paused = False
            self.pause_btn.setChecked(False)
            self.pause_btn.setText("Pause")
        else:
            self._paused = True

    def _toggle_pause(self, checked: bool):
        self._paused = checked
        self.pause_btn.setText("Resume" if checked else "Pause")

    def _clear_data(self):
        self._data_history.clear()
        self._time_data.clear()
        self._start_time = datetime.now()

        # Clear all curves
        for curves_dict in [self.analog_curves, self.current_curves,
                           self.hbridge_curves, self.system_curves]:
            for curve in curves_dict.values():
                curve.setData([], [])

    def add_data_point(self, category: str, name: str, value: float):
        """Add a data point to the graph."""
        if self._pg is None or self._paused or not self._enabled:
            return

        # Calculate time offset
        now = datetime.now()
        time_offset = (now - self._start_time).total_seconds()

        # Store data
        key = f"{category}:{name}"
        if key not in self._data_history:
            self._data_history[key] = deque(maxlen=500)
        self._data_history[key].append((time_offset, value))

        # Get or create curve
        curve = self._get_or_create_curve(category, name)
        if curve:
            times = [p[0] for p in self._data_history[key]]
            values = [p[1] for p in self._data_history[key]]
            curve.setData(times, values)

            # Update x-axis range
            window = self.time_window_spin.value()
            min_time = max(0, time_offset - window)
            self._update_x_ranges(min_time, time_offset)

    def _get_or_create_curve(self, category: str, name: str):
        """Get existing curve or create new one."""
        if self._pg is None:
            return None

        curves_dict = {
            'analog': self.analog_curves,
            'current': self.current_curves,
            'hbridge': self.hbridge_curves,
            'system': self.system_curves,
        }.get(category)

        if curves_dict is None:
            return None

        if name not in curves_dict:
            plot = {
                'analog': self.analog_plot,
                'current': self.current_plot,
                'hbridge': self.hbridge_plot,
                'system': self.system_plot,
            }.get(category)

            color_idx = len(curves_dict) % len(self.COLORS)
            pen = self._pg.mkPen(color=self.COLORS[color_idx], width=2)
            curves_dict[name] = plot.plot([], [], pen=pen, name=name)

        return curves_dict[name]

    def _update_x_ranges(self, min_time: float, max_time: float):
        """Update x-axis range for all plots."""
        for plot in [self.analog_plot, self.current_plot,
                    self.hbridge_plot, self.system_plot]:
            plot.setXRange(min_time, max_time, padding=0)

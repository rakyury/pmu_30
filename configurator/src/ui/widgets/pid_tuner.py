"""
PID Tuner Widget
Real-time PID controller tuning with live graph visualization
Similar to ECUMaster EMU PRO PID tuner

Features:
- Real-time plot of setpoint, process variable, and output
- Live Kp, Ki, Kd adjustment with sliders and spinboxes
- Step response testing
- Controller reset capability
- Recording and export
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSlider, QComboBox, QPushButton, QLabel,
    QCheckBox, QSpinBox, QSplitter, QFrame, QToolBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from typing import Dict, Any, List, Optional
from collections import deque
import time

try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False


class PIDTuner(QWidget):
    """Real-time PID tuner widget with graphing."""

    # Signals
    parameters_changed = pyqtSignal(str, dict)  # (controller_id, {kp, ki, kd, setpoint})
    controller_reset = pyqtSignal(str)  # controller_id
    controller_enabled_changed = pyqtSignal(str, bool)  # (controller_id, enabled)

    # Colors for plot lines
    COLOR_SETPOINT = '#22c55e'      # Green
    COLOR_PROCESS = '#3b82f6'       # Blue
    COLOR_OUTPUT = '#f59e0b'        # Orange/Amber
    COLOR_ERROR = '#ef4444'         # Red
    COLOR_GRID = '#374151'          # Gray

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controllers = []
        self.current_controller_id = None
        self._connected = False

        # Data buffers for plotting (circular buffers)
        self.history_length = 600  # 60 seconds at 10Hz
        self.time_data = deque(maxlen=self.history_length)
        self.setpoint_data = deque(maxlen=self.history_length)
        self.process_data = deque(maxlen=self.history_length)
        self.output_data = deque(maxlen=self.history_length)
        self.error_data = deque(maxlen=self.history_length)
        self._start_time = time.time()

        # Recording state
        self._recording = False
        self._recorded_data = []

        # Step test state
        self._step_test_active = False
        self._step_original_setpoint = 0.0
        self._step_target_setpoint = 0.0

        # Live update flag
        self._live_update = True

        self._init_ui()
        self._setup_update_timer()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Graph
        graph_widget = self._create_graph_widget()
        splitter.addWidget(graph_widget)

        # Right side - Controls
        controls_widget = self._create_controls_widget()
        splitter.addWidget(controls_widget)

        splitter.setSizes([600, 300])
        layout.addWidget(splitter)

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Select a PID controller to tune")
        self.status_label.setStyleSheet("color: #888;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        self.connection_label = QLabel("Offline")
        self.connection_label.setStyleSheet("color: #888;")
        status_layout.addWidget(self.connection_label)

        layout.addLayout(status_layout)

    def _create_toolbar(self) -> QToolBar:
        """Create toolbar with actions."""
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # Controller selector
        self.controller_combo = QComboBox()
        self.controller_combo.setMinimumWidth(150)
        self.controller_combo.currentIndexChanged.connect(self._on_controller_changed)
        toolbar.addWidget(QLabel(" Controller: "))
        toolbar.addWidget(self.controller_combo)

        toolbar.addSeparator()

        # Live update toggle
        self.live_check = QCheckBox("Live Update")
        self.live_check.setChecked(True)
        self.live_check.toggled.connect(self._on_live_toggle)
        toolbar.addWidget(self.live_check)

        toolbar.addSeparator()

        # Step test
        self.step_btn = QPushButton("Step Test")
        self.step_btn.setToolTip("Apply step change to setpoint for response analysis")
        self.step_btn.clicked.connect(self._on_step_test)
        toolbar.addWidget(self.step_btn)

        # Reset controller
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setToolTip("Reset controller (clear integral term)")
        self.reset_btn.clicked.connect(self._on_reset_controller)
        toolbar.addWidget(self.reset_btn)

        toolbar.addSeparator()

        # Recording
        self.record_btn = QPushButton("Record")
        self.record_btn.setCheckable(True)
        self.record_btn.toggled.connect(self._on_record_toggle)
        toolbar.addWidget(self.record_btn)

        # Clear graph
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_graph)
        toolbar.addWidget(self.clear_btn)

        return toolbar

    def _create_graph_widget(self) -> QWidget:
        """Create the graph widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_PYQTGRAPH:
            # Configure pyqtgraph for dark theme
            pg.setConfigOptions(antialias=True, background='#1f2937', foreground='#e5e7eb')

            # Create plot widget
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setLabel('bottom', 'Time', units='s')
            self.plot_widget.setLabel('left', 'Value')
            self.plot_widget.addLegend(offset=(10, 10))

            # Create plot curves
            self.setpoint_curve = self.plot_widget.plot(
                pen=pg.mkPen(color=self.COLOR_SETPOINT, width=2),
                name='Setpoint'
            )
            self.process_curve = self.plot_widget.plot(
                pen=pg.mkPen(color=self.COLOR_PROCESS, width=2),
                name='Process'
            )
            self.output_curve = self.plot_widget.plot(
                pen=pg.mkPen(color=self.COLOR_OUTPUT, width=2, style=Qt.PenStyle.DashLine),
                name='Output'
            )

            layout.addWidget(self.plot_widget)
        else:
            # Fallback if pyqtgraph not available
            fallback_label = QLabel(
                "pyqtgraph not available.\n"
                "Install with: pip install pyqtgraph"
            )
            fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback_label.setStyleSheet("color: #888; font-size: 14px;")
            layout.addWidget(fallback_label)
            self.plot_widget = None

        return widget

    def _create_controls_widget(self) -> QWidget:
        """Create the controls panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        # PID Parameters group
        params_group = QGroupBox("PID Parameters")
        params_layout = QVBoxLayout()

        # Kp control
        kp_layout = self._create_parameter_control("Kp", 0.0, 100.0, 1.0, 0.1)
        self.kp_slider, self.kp_spin = kp_layout
        params_layout.addLayout(self._wrap_parameter("Kp (Proportional)", self.kp_slider, self.kp_spin))

        # Ki control
        ki_layout = self._create_parameter_control("Ki", 0.0, 100.0, 0.0, 0.01)
        self.ki_slider, self.ki_spin = ki_layout
        params_layout.addLayout(self._wrap_parameter("Ki (Integral)", self.ki_slider, self.ki_spin))

        # Kd control
        kd_layout = self._create_parameter_control("Kd", 0.0, 100.0, 0.0, 0.01)
        self.kd_slider, self.kd_spin = kd_layout
        params_layout.addLayout(self._wrap_parameter("Kd (Derivative)", self.kd_slider, self.kd_spin))

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Setpoint group
        setpoint_group = QGroupBox("Setpoint")
        setpoint_layout = QFormLayout()

        self.setpoint_spin = QDoubleSpinBox()
        self.setpoint_spin.setRange(-100000.0, 100000.0)
        self.setpoint_spin.setDecimals(2)
        self.setpoint_spin.setValue(0.0)
        self.setpoint_spin.valueChanged.connect(self._on_parameter_changed)
        setpoint_layout.addRow("Target:", self.setpoint_spin)

        # Step test settings
        self.step_size_spin = QDoubleSpinBox()
        self.step_size_spin.setRange(0.1, 1000.0)
        self.step_size_spin.setDecimals(1)
        self.step_size_spin.setValue(10.0)
        self.step_size_spin.setToolTip("Step size for step response test")
        setpoint_layout.addRow("Step Size:", self.step_size_spin)

        setpoint_group.setLayout(setpoint_layout)
        layout.addWidget(setpoint_group)

        # Real-time values group
        values_group = QGroupBox("Real-time Values")
        values_layout = QFormLayout()

        self.current_setpoint_label = QLabel("---")
        self.current_setpoint_label.setStyleSheet(f"color: {self.COLOR_SETPOINT}; font-weight: bold;")
        values_layout.addRow("Setpoint:", self.current_setpoint_label)

        self.current_process_label = QLabel("---")
        self.current_process_label.setStyleSheet(f"color: {self.COLOR_PROCESS}; font-weight: bold;")
        values_layout.addRow("Process:", self.current_process_label)

        self.current_output_label = QLabel("---")
        self.current_output_label.setStyleSheet(f"color: {self.COLOR_OUTPUT}; font-weight: bold;")
        values_layout.addRow("Output:", self.current_output_label)

        self.current_error_label = QLabel("---")
        self.current_error_label.setStyleSheet(f"color: {self.COLOR_ERROR}; font-weight: bold;")
        values_layout.addRow("Error:", self.current_error_label)

        values_group.setLayout(values_layout)
        layout.addWidget(values_group)

        # Graph settings group
        graph_group = QGroupBox("Graph Settings")
        graph_layout = QFormLayout()

        self.history_spin = QSpinBox()
        self.history_spin.setRange(10, 300)
        self.history_spin.setValue(60)
        self.history_spin.setSuffix(" sec")
        self.history_spin.valueChanged.connect(self._on_history_changed)
        graph_layout.addRow("History:", self.history_spin)

        self.show_error_check = QCheckBox("Show Error")
        self.show_error_check.setChecked(False)
        self.show_error_check.toggled.connect(self._toggle_error_curve)
        graph_layout.addRow("", self.show_error_check)

        graph_group.setLayout(graph_layout)
        layout.addWidget(graph_group)

        layout.addStretch()

        return widget

    def _create_parameter_control(self, name: str, min_val: float, max_val: float,
                                   default: float, step: float) -> tuple:
        """Create a slider + spinbox combo for parameter control."""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(min_val * 100), int(max_val * 100))
        slider.setValue(int(default * 100))

        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setDecimals(4)
        spin.setSingleStep(step)

        # Connect slider and spinbox
        slider.valueChanged.connect(lambda v: spin.setValue(v / 100.0))
        spin.valueChanged.connect(lambda v: slider.setValue(int(v * 100)))
        spin.valueChanged.connect(self._on_parameter_changed)

        return slider, spin

    def _wrap_parameter(self, label: str, slider: QSlider, spin: QDoubleSpinBox) -> QVBoxLayout:
        """Wrap parameter controls in a layout."""
        layout = QVBoxLayout()
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.addWidget(QLabel(label))
        header.addStretch()
        header.addWidget(spin)
        layout.addLayout(header)

        layout.addWidget(slider)
        return layout

    def _setup_update_timer(self):
        """Setup timer for graph updates."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_graph)
        self.update_timer.start(100)  # 10 Hz update rate

    def set_controllers(self, controllers: List[Dict[str, Any]]):
        """Set available PID controllers."""
        self.controllers = controllers
        self.controller_combo.clear()

        if not controllers:
            self.controller_combo.addItem("No controllers configured")
            self._set_controls_enabled(False)
            return

        for ctrl in controllers:
            name = ctrl.get("name", ctrl.get("id", "Unnamed"))
            ctrl_id = ctrl.get("id", ctrl.get("channel_id", ""))
            self.controller_combo.addItem(name, ctrl_id)

        self._set_controls_enabled(True)

        # Load first controller
        if controllers:
            self._load_controller(controllers[0])

    def _load_controller(self, controller: Dict[str, Any]):
        """Load controller parameters into controls."""
        self.current_controller_id = controller.get("id", controller.get("channel_id", ""))

        # Block signals during loading
        self.kp_spin.blockSignals(True)
        self.ki_spin.blockSignals(True)
        self.kd_spin.blockSignals(True)
        self.setpoint_spin.blockSignals(True)

        self.kp_spin.setValue(controller.get("kp", 1.0))
        self.ki_spin.setValue(controller.get("ki", 0.0))
        self.kd_spin.setValue(controller.get("kd", 0.0))
        self.setpoint_spin.setValue(controller.get("setpoint_value", controller.get("setpoint", 0.0)))

        self.kp_spin.blockSignals(False)
        self.ki_spin.blockSignals(False)
        self.kd_spin.blockSignals(False)
        self.setpoint_spin.blockSignals(False)

        # Clear graph for new controller
        self._clear_graph()

        self.status_label.setText(f"Tuning: {controller.get('name', 'Unknown')}")

    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable controls."""
        self.kp_spin.setEnabled(enabled)
        self.kp_slider.setEnabled(enabled)
        self.ki_spin.setEnabled(enabled)
        self.ki_slider.setEnabled(enabled)
        self.kd_spin.setEnabled(enabled)
        self.kd_slider.setEnabled(enabled)
        self.setpoint_spin.setEnabled(enabled)
        self.step_btn.setEnabled(enabled)
        self.reset_btn.setEnabled(enabled)

    def _on_controller_changed(self, index: int):
        """Handle controller selection change."""
        if index < 0 or index >= len(self.controllers):
            return

        self._load_controller(self.controllers[index])

    def _on_parameter_changed(self):
        """Handle parameter change - emit signal to update device."""
        if not self._live_update or not self.current_controller_id:
            return

        params = {
            'kp': self.kp_spin.value(),
            'ki': self.ki_spin.value(),
            'kd': self.kd_spin.value(),
            'setpoint': self.setpoint_spin.value()
        }

        self.parameters_changed.emit(self.current_controller_id, params)

    def _on_live_toggle(self, checked: bool):
        """Toggle live parameter updates."""
        self._live_update = checked
        if checked:
            self._on_parameter_changed()  # Send current values

    def _on_step_test(self):
        """Start or stop step response test."""
        if self._step_test_active:
            # Stop test - restore original setpoint
            self.setpoint_spin.setValue(self._step_original_setpoint)
            self._step_test_active = False
            self.step_btn.setText("Step Test")
            self.status_label.setText(f"Step test ended")
        else:
            # Start test - apply step change
            self._step_original_setpoint = self.setpoint_spin.value()
            self._step_target_setpoint = self._step_original_setpoint + self.step_size_spin.value()
            self.setpoint_spin.setValue(self._step_target_setpoint)
            self._step_test_active = True
            self.step_btn.setText("End Step")
            self.status_label.setText(f"Step test: {self._step_original_setpoint:.1f} → {self._step_target_setpoint:.1f}")

    def _on_reset_controller(self):
        """Reset the current controller."""
        if self.current_controller_id:
            self.controller_reset.emit(self.current_controller_id)
            self.status_label.setText(f"Controller reset sent")

    def _on_record_toggle(self, recording: bool):
        """Toggle data recording."""
        self._recording = recording
        if recording:
            self._recorded_data = []
            self.record_btn.setText("Stop")
            self.status_label.setText("Recording...")
        else:
            self.record_btn.setText("Record")
            self.status_label.setText(f"Recorded {len(self._recorded_data)} samples")
            # TODO: Could offer to export data here

    def _on_history_changed(self, seconds: int):
        """Handle history length change."""
        self.history_length = seconds * 10  # 10 Hz
        # Recreate buffers with new size
        self.time_data = deque(list(self.time_data)[-self.history_length:], maxlen=self.history_length)
        self.setpoint_data = deque(list(self.setpoint_data)[-self.history_length:], maxlen=self.history_length)
        self.process_data = deque(list(self.process_data)[-self.history_length:], maxlen=self.history_length)
        self.output_data = deque(list(self.output_data)[-self.history_length:], maxlen=self.history_length)
        self.error_data = deque(list(self.error_data)[-self.history_length:], maxlen=self.history_length)

    def _toggle_error_curve(self, show: bool):
        """Toggle error curve visibility."""
        if HAS_PYQTGRAPH and self.plot_widget:
            if show:
                if not hasattr(self, 'error_curve') or self.error_curve is None:
                    self.error_curve = self.plot_widget.plot(
                        pen=pg.mkPen(color=self.COLOR_ERROR, width=2, style=Qt.PenStyle.DotLine),
                        name='Error'
                    )
            else:
                if hasattr(self, 'error_curve') and self.error_curve:
                    self.plot_widget.removeItem(self.error_curve)
                    self.error_curve = None

    def _clear_graph(self):
        """Clear all graph data."""
        self.time_data.clear()
        self.setpoint_data.clear()
        self.process_data.clear()
        self.output_data.clear()
        self.error_data.clear()
        self._start_time = time.time()

        if HAS_PYQTGRAPH and self.plot_widget:
            self.setpoint_curve.setData([], [])
            self.process_curve.setData([], [])
            self.output_curve.setData([], [])
            if hasattr(self, 'error_curve') and self.error_curve:
                self.error_curve.setData([], [])

    def update_telemetry(self, controller_id: str, setpoint: float, process: float, output: float):
        """Update with new telemetry data from device."""
        if controller_id != self.current_controller_id:
            return

        # Calculate time relative to start
        current_time = time.time() - self._start_time

        # Add data points
        self.time_data.append(current_time)
        self.setpoint_data.append(setpoint)
        self.process_data.append(process)
        self.output_data.append(output)
        self.error_data.append(setpoint - process)

        # Update value labels
        self.current_setpoint_label.setText(f"{setpoint:.2f}")
        self.current_process_label.setText(f"{process:.2f}")
        self.current_output_label.setText(f"{output:.2f}")
        self.current_error_label.setText(f"{setpoint - process:.2f}")

        # Record if recording
        if self._recording:
            self._recorded_data.append({
                'time': current_time,
                'setpoint': setpoint,
                'process': process,
                'output': output,
                'error': setpoint - process
            })

    def _update_graph(self):
        """Update the graph with current data."""
        if not HAS_PYQTGRAPH or not self.plot_widget:
            return

        if len(self.time_data) < 2:
            return

        time_list = list(self.time_data)
        self.setpoint_curve.setData(time_list, list(self.setpoint_data))
        self.process_curve.setData(time_list, list(self.process_data))
        self.output_curve.setData(time_list, list(self.output_data))

        if hasattr(self, 'error_curve') and self.error_curve and self.show_error_check.isChecked():
            self.error_curve.setData(time_list, list(self.error_data))

    def set_connected(self, connected: bool):
        """Update connection state."""
        self._connected = connected
        if connected:
            self.connection_label.setText("Online")
            self.connection_label.setStyleSheet("color: #22c55e; font-weight: bold;")
        else:
            self.connection_label.setText("Offline")
            self.connection_label.setStyleSheet("color: #888;")
            # Clear real-time values
            self.current_setpoint_label.setText("---")
            self.current_process_label.setText("---")
            self.current_output_label.setText("---")
            self.current_error_label.setText("---")

    def get_recorded_data(self) -> List[Dict]:
        """Get recorded data for export."""
        return self._recorded_data.copy()

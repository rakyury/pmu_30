"""
H-Bridge Motor Monitor Widget
Real-time monitoring of H-Bridge motor controller channels
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QLabel, QProgressBar,
    QSlider, QSpinBox, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, List, Any


class HBridgeMonitor(QWidget):
    """H-Bridge motor channels monitor widget with real-time telemetry display."""

    # Signal emitted when user double-clicks a channel to edit it
    channel_edit_requested = pyqtSignal(str, dict)  # (channel_type, channel_config)

    # Signals for H-Bridge control commands
    hbridge_command = pyqtSignal(int, str, int)  # (bridge_number, command, pwm_value)
    # Commands: "coast", "forward", "reverse", "brake", "stop"

    # Colors for different states (dark theme - matching Variables Inspector)
    COLOR_NORMAL = QColor(0, 0, 0)            # Pure black (matching Variables Inspector)
    COLOR_FORWARD = QColor(50, 80, 50)        # Dark green
    COLOR_REVERSE = QColor(40, 40, 100)       # Dark blue
    COLOR_BRAKE = QColor(80, 80, 0)           # Dark yellow
    COLOR_FAULT = QColor(80, 40, 40)          # Dark red
    COLOR_DISABLED = QColor(60, 60, 60)       # Dark gray
    COLOR_STALLED = QColor(100, 60, 0)        # Dark orange

    # Column indices
    COL_BRIDGE = 0
    COL_NAME = 1
    COL_MODE = 2
    COL_DIR = 3
    COL_PWM = 4
    COL_CURRENT = 5
    COL_SPEED = 6
    COL_POSITION = 7
    COL_TEMP = 8
    COL_STATUS = 9

    # Mode names matching firmware
    MODE_NAMES = {
        0: "Coast",
        1: "Forward",
        2: "Reverse",
        3: "Brake",
        4: "Wiper",
        5: "PID",
    }

    # State names
    STATE_NAMES = {
        0: "IDLE",
        1: "RUN",
        2: "STALL",
        3: "FAULT",
        4: "OC",
        5: "OT",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hbridges_data = []
        self._connected = False
        self._telemetry = {}  # Store latest telemetry per bridge
        self._init_ui()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_values)
        self.update_timer.start(100)  # Update every 100ms

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Toolbar
        toolbar = QHBoxLayout()

        toolbar.addStretch()

        # All Stop button
        self.all_stop_btn = QPushButton("All Stop")
        self.all_stop_btn.setMaximumWidth(70)
        self.all_stop_btn.setStyleSheet("background-color: #ff6666;")
        self.all_stop_btn.clicked.connect(self._all_stop)
        toolbar.addWidget(self.all_stop_btn)

        layout.addLayout(toolbar)

        # Table with H-Bridge columns
        # Bridge | Name | Mode | Dir | PWM | Current | Speed | Position | Temp | Status
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Bridge", "Name", "Mode", "Dir", "PWM", "Current", "Speed", "Position", "Temp", "Status"
        ])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_BRIDGE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_MODE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_DIR, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_PWM, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_CURRENT, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_SPEED, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_POSITION, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_TEMP, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(self.COL_BRIDGE, 50)
        self.table.setColumnWidth(self.COL_MODE, 55)
        self.table.setColumnWidth(self.COL_DIR, 40)
        self.table.setColumnWidth(self.COL_PWM, 45)
        self.table.setColumnWidth(self.COL_CURRENT, 60)
        self.table.setColumnWidth(self.COL_SPEED, 55)
        self.table.setColumnWidth(self.COL_POSITION, 60)
        self.table.setColumnWidth(self.COL_TEMP, 50)
        self.table.setColumnWidth(self.COL_STATUS, 55)

        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # Dark theme styling (matching Variables Inspector - pure black)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #000000;
                color: #ffffff;
                gridline-color: #333333;
            }
            QTableWidget::item {
                background-color: #000000;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #333333;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.table)

        # Control panel
        control_group = QGroupBox("Motor Control")
        control_layout = QHBoxLayout()

        # Direction buttons
        self.fwd_btn = QPushButton("FWD")
        self.fwd_btn.setMinimumWidth(50)
        self.fwd_btn.setStyleSheet("background-color: #90EE90;")
        self.fwd_btn.clicked.connect(lambda: self._send_command("forward"))
        control_layout.addWidget(self.fwd_btn)

        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setMinimumWidth(50)
        self.stop_btn.setStyleSheet("background-color: #FFD700;")
        self.stop_btn.clicked.connect(lambda: self._send_command("coast"))
        control_layout.addWidget(self.stop_btn)

        self.rev_btn = QPushButton("REV")
        self.rev_btn.setMinimumWidth(50)
        self.rev_btn.setStyleSheet("background-color: #87CEEB;")
        self.rev_btn.clicked.connect(lambda: self._send_command("reverse"))
        control_layout.addWidget(self.rev_btn)

        self.brake_btn = QPushButton("BRAKE")
        self.brake_btn.setMinimumWidth(50)
        self.brake_btn.setStyleSheet("background-color: #FFA07A;")
        self.brake_btn.clicked.connect(lambda: self._send_command("brake"))
        control_layout.addWidget(self.brake_btn)

        control_layout.addWidget(QLabel("PWM:"))

        # PWM slider
        self.pwm_slider = QSlider(Qt.Orientation.Horizontal)
        self.pwm_slider.setRange(0, 255)
        self.pwm_slider.setValue(255)
        self.pwm_slider.setMinimumWidth(100)
        self.pwm_slider.valueChanged.connect(self._on_pwm_changed)
        control_layout.addWidget(self.pwm_slider)

        # PWM value spinbox
        self.pwm_spin = QSpinBox()
        self.pwm_spin.setRange(0, 255)
        self.pwm_spin.setValue(255)
        self.pwm_spin.setMinimumWidth(50)
        self.pwm_spin.valueChanged.connect(self._on_pwm_spin_changed)
        control_layout.addWidget(self.pwm_spin)

        self.pwm_percent_label = QLabel("100%")
        self.pwm_percent_label.setMinimumWidth(40)
        control_layout.addWidget(self.pwm_percent_label)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Initially disable controls
        self._set_controls_enabled(False)

    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable control buttons."""
        self.fwd_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
        self.rev_btn.setEnabled(enabled)
        self.brake_btn.setEnabled(enabled)
        self.pwm_slider.setEnabled(enabled)
        self.pwm_spin.setEnabled(enabled)

    def _on_selection_changed(self):
        """Handle table row selection change."""
        items = self.table.selectedItems()
        has_selection = len(items) > 0 and self._connected
        self._set_controls_enabled(has_selection)

    def _on_pwm_changed(self, value: int):
        """Handle PWM slider change."""
        self.pwm_spin.blockSignals(True)
        self.pwm_spin.setValue(value)
        self.pwm_spin.blockSignals(False)
        percent = (value / 255.0) * 100
        self.pwm_percent_label.setText(f"{percent:.2f}%")

    def _on_pwm_spin_changed(self, value: int):
        """Handle PWM spinbox change."""
        self.pwm_slider.blockSignals(True)
        self.pwm_slider.setValue(value)
        self.pwm_slider.blockSignals(False)
        percent = (value / 255.0) * 100
        self.pwm_percent_label.setText(f"{percent:.2f}%")

    def _get_selected_bridge(self) -> int:
        """Get selected bridge number or -1 if none selected."""
        row = self.table.currentRow()
        if row >= 0 and row < len(self.hbridges_data):
            return self.hbridges_data[row].get('bridge_number', row)
        return -1

    def _send_command(self, command: str):
        """Send command for selected H-Bridge."""
        bridge = self._get_selected_bridge()
        if bridge >= 0:
            pwm = self.pwm_slider.value()
            self.hbridge_command.emit(bridge, command, pwm)

    def set_hbridges(self, hbridges: List[Dict[str, Any]]):
        """Set H-Bridge configurations to monitor."""
        self.hbridges_data = hbridges
        self._populate_table()

    def set_connected(self, connected: bool):
        """Set connection state."""
        self._connected = connected
        if connected:
            pass  # Connection status shown in status bar
        else:
            pass  # Connection status shown in status bar
            self._reset_values()

    def _reset_values(self):
        """Reset all telemetry values to '?'."""
        for row in range(self.table.rowCount()):
            for col in [self.COL_MODE, self.COL_DIR, self.COL_PWM, self.COL_CURRENT,
                       self.COL_SPEED, self.COL_POSITION, self.COL_TEMP, self.COL_STATUS]:
                item = self.table.item(row, col)
                if item:
                    item.setText("?")
                    item.setBackground(QBrush(self.COLOR_DISABLED))

    def _all_stop(self):
        """Emergency stop all H-Bridges."""
        # Emit signal or call controller to stop all motors
        pass

    def _populate_table(self):
        """Populate table with H-Bridge configurations."""
        self.table.setRowCount(len(self.hbridges_data))

        for row, hbridge in enumerate(self.hbridges_data):
            # Bridge number
            bridge_num = hbridge.get('bridge_number', row)
            bridge_item = QTableWidgetItem(f"HB{bridge_num + 1}")
            bridge_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_BRIDGE, bridge_item)

            # Name
            name = hbridge.get('name', f"Motor {row + 1}")
            name_item = QTableWidgetItem(name)
            self.table.setItem(row, self.COL_NAME, name_item)

            # Mode
            mode = hbridge.get('mode', 'coast')
            if hasattr(mode, 'value'):
                mode = mode.value
            mode_item = QTableWidgetItem(mode.capitalize())
            mode_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_MODE, mode_item)

            # Direction
            direction = hbridge.get('direction', 'forward')
            if hasattr(direction, 'value'):
                direction = direction.value
            dir_item = QTableWidgetItem("FWD" if direction == 'forward' else "REV")
            dir_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_DIR, dir_item)

            # PWM
            pwm_item = QTableWidgetItem("?")
            pwm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_PWM, pwm_item)

            # Current
            curr_item = QTableWidgetItem("?")
            curr_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_CURRENT, curr_item)

            # Speed (RPM or rad/s)
            speed_item = QTableWidgetItem("?")
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_SPEED, speed_item)

            # Position
            pos_item = QTableWidgetItem("?")
            pos_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_POSITION, pos_item)

            # Temperature
            temp_item = QTableWidgetItem("?")
            temp_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, self.COL_TEMP, temp_item)

            # Status
            status_item = QTableWidgetItem("?")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, self.COL_STATUS, status_item)

            # Set initial row color
            enabled = hbridge.get('enabled', True)
            if enabled:
                self._set_row_color(row, self.COLOR_NORMAL)
            else:
                self._set_row_color(row, self.COLOR_DISABLED)

    def _set_row_color(self, row: int, color: QColor):
        """Set background color for entire row."""
        bg_brush = QBrush(color)
        fg_brush = QBrush(QColor(255, 255, 255))  # White text
        for col in range(10):
            item = self.table.item(row, col)
            if item:
                item.setBackground(bg_brush)
                item.setForeground(fg_brush)

    def _update_values(self):
        """Update real-time values (called by timer)."""
        # Values are updated via update_from_telemetry() called from main window
        pass

    def update_from_telemetry(self, hbridge_states: List[Dict[str, Any]]):
        """
        Update all H-Bridges from telemetry data.

        Args:
            hbridge_states: List of H-Bridge telemetry dictionaries with keys:
                - mode: Current operating mode (0-5)
                - state: Current state (0=IDLE, 1=RUN, 2=STALL, 3=FAULT)
                - pwm: PWM duty (0-255)
                - direction: Direction (0=coast, 1=forward, 2=reverse)
                - current: Motor current in mA
                - omega: Angular velocity (rad/s)
                - theta: Angular position (rad)
                - temp: Motor temperature (C)
                - stalled: Stall flag
                - endstop: End-stop flag (0=free, 1=min, 2=max)
        """
        for row in range(min(self.table.rowCount(), len(hbridge_states))):
            telemetry = hbridge_states[row]

            # Mode
            mode_val = telemetry.get('mode', 0)
            mode_str = self.MODE_NAMES.get(mode_val, f"M{mode_val}")
            mode_item = self.table.item(row, self.COL_MODE)
            if mode_item:
                mode_item.setText(mode_str)

            # Direction
            direction = telemetry.get('direction', 0)
            dir_str = {0: "-", 1: "FWD", 2: "REV", 3: "BRK"}.get(direction, "?")
            dir_item = self.table.item(row, self.COL_DIR)
            if dir_item:
                dir_item.setText(dir_str)

            # PWM
            pwm = telemetry.get('pwm', 0)
            pwm_percent = (pwm / 255.0) * 100
            pwm_item = self.table.item(row, self.COL_PWM)
            if pwm_item:
                pwm_item.setText(f"{pwm_percent:.2f}%")

            # Current
            current = telemetry.get('current', 0)
            curr_item = self.table.item(row, self.COL_CURRENT)
            if curr_item:
                if current >= 1000:
                    curr_item.setText(f"{current/1000:.2f}A")
                else:
                    curr_item.setText(f"{current:.2f}mA")

            # Speed (omega in rad/s -> RPM)
            omega = telemetry.get('omega', 0)
            rpm = abs(omega) * 9.549  # rad/s to RPM (30/pi)
            speed_item = self.table.item(row, self.COL_SPEED)
            if speed_item:
                if rpm > 0.1:
                    speed_item.setText(f"{rpm:.2f}")
                else:
                    speed_item.setText("0.00")

            # Position (theta in radians -> degrees or raw)
            theta = telemetry.get('theta', 0)
            degrees = (theta * 180.0 / 3.14159)  # rad to degrees
            pos_item = self.table.item(row, self.COL_POSITION)
            if pos_item:
                pos_item.setText(f"{degrees:.2f}")

            # Temperature
            temp = telemetry.get('temp', 25)
            temp_item = self.table.item(row, self.COL_TEMP)
            if temp_item:
                temp_item.setText(f"{temp:.2f}C")

            # Status
            state = telemetry.get('state', 0)
            stalled = telemetry.get('stalled', 0)
            endstop = telemetry.get('endstop', 0)
            fault = telemetry.get('fault', 0)

            status_str = "OK"
            if fault:
                status_str = "FAULT"
            elif stalled:
                status_str = "STALL"
            elif endstop == 1:
                status_str = "END-"
            elif endstop == 2:
                status_str = "END+"
            elif state == 1:
                status_str = "RUN"
            elif state == 0:
                status_str = "IDLE"

            status_item = self.table.item(row, self.COL_STATUS)
            if status_item:
                status_item.setText(status_str)

            # Set row color based on state
            if fault:
                self._set_row_color(row, self.COLOR_FAULT)
            elif stalled:
                self._set_row_color(row, self.COLOR_STALLED)
            elif direction == 1:  # Forward
                self._set_row_color(row, self.COLOR_FORWARD)
            elif direction == 2:  # Reverse
                self._set_row_color(row, self.COLOR_REVERSE)
            elif direction == 3 or mode_val == 3:  # Brake
                self._set_row_color(row, self.COLOR_BRAKE)
            else:
                self._set_row_color(row, self.COLOR_NORMAL)

    def get_channel_count(self) -> int:
        """Get number of configured H-Bridge channels."""
        return len(self.hbridges_data)

    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle double-click on table cell - emit signal to edit the channel."""
        if row < 0 or row >= len(self.hbridges_data):
            return
        hbridge_data = self.hbridges_data[row]
        self.channel_edit_requested.emit('hbridge', hbridge_data)

"""
Output Widgets - PROFET and H-Bridge output channel widgets

This module contains widgets for displaying output channel states.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QGroupBox, QGridLayout, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class OutputChannelWidget(QFrame):
    """Widget for displaying a single PROFET output channel."""

    clicked = pyqtSignal(int)

    STATE_COLORS = {
        0: "#333",    # OFF
        1: "#0a0",    # ON
        2: "#f00",    # OC (Overcurrent)
        3: "#f80",    # OT (Overtemp)
        4: "#f0f",    # SC (Short Circuit)
        5: "#ffa500",    # OL (Open Load) - orange for readability
    }

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._last_color = None
        self._last_current = None
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Channel label
        self.label = QLabel(f"CH{self.channel + 1}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.label)

        # Current display
        self.current_label = QLabel("0.0A")
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_label.setFont(QFont("Segoe UI", 8))
        layout.addWidget(self.current_label)

        self.setMinimumSize(60, 50)
        self.update_state(0, 0.0, 0)

    def update_state(self, state: int, current: float, fault: int):
        """Update channel state display."""
        color = self.STATE_COLORS.get(state, "#333")
        if fault > 0:
            # Has fault - show fault color
            if fault & 1:
                color = self.STATE_COLORS[2]  # OC
            elif fault & 2:
                color = self.STATE_COLORS[3]  # OT
            elif fault & 4:
                color = self.STATE_COLORS[4]  # SC
            elif fault & 8:
                color = self.STATE_COLORS[5]  # OL

        # Only update if changed
        if color != self._last_color:
            self.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            self._last_color = color

        current_text = f"{current:.2f}A"
        if current_text != self._last_current:
            self.current_label.setText(current_text)
            self._last_current = current_text

    def mousePressEvent(self, event):
        self.clicked.emit(self.channel)
        super().mousePressEvent(event)


class HBridgeChannelWidget(QFrame):
    """Compact widget for displaying H-Bridge motor status (like PROFET panels)."""

    clicked = pyqtSignal(int)

    MODE_NAMES = ["COAST", "FWD", "REV", "BRAKE", "PARK", "PID"]
    MODE_COLORS = {
        0: "#333",    # COAST - dark
        1: "#0a0",    # FWD - green
        2: "#00a",    # REV - blue
        3: "#a00",    # BRAKE - red
        4: "#a0a",    # PARK - magenta
        5: "#0aa",    # PID - cyan
    }

    def __init__(self, bridge: int, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self._last_color = None
        self._last_mode = None
        self._last_pwm = None
        self._last_current = None
        self._last_position = None
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Bridge label
        self.label = QLabel(f"HB{self.bridge + 1}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(self.label)

        # Mode label
        self.mode_label = QLabel("COAST")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.mode_label)

        # PWM bar
        self.pwm_bar = QProgressBar()
        self.pwm_bar.setRange(0, 100)
        self.pwm_bar.setTextVisible(True)
        self.pwm_bar.setFormat("PWM: %v%")
        self.pwm_bar.setMaximumHeight(18)
        layout.addWidget(self.pwm_bar)

        # Current display
        self.current_label = QLabel("0.00A")
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.current_label)

        # Position bar
        self.position_bar = QProgressBar()
        self.position_bar.setRange(0, 1000)
        self.position_bar.setTextVisible(True)
        self.position_bar.setFormat("Pos: %v")
        self.position_bar.setMaximumHeight(18)
        layout.addWidget(self.position_bar)

        self.setMinimumSize(120, 130)
        self.update_state(0, 0, 0.0, 0, 0)

    def update_state(self, mode: int, pwm: int, current: float, position: int, fault: int):
        """Update H-Bridge display."""
        # Only update changed values
        mode_name = self.MODE_NAMES[mode] if mode < len(self.MODE_NAMES) else "?"
        if mode_name != self._last_mode:
            self.mode_label.setText(mode_name)
            self._last_mode = mode_name

        pwm_val = pwm // 10
        if pwm_val != self._last_pwm:
            self.pwm_bar.setValue(pwm_val)
            self._last_pwm = pwm_val

        current_text = f"{current:.2f}A"
        if current_text != self._last_current:
            self.current_label.setText(current_text)
            self._last_current = current_text

        if position != self._last_position:
            self.position_bar.setValue(position)
            self._last_position = position

        # Set background color based on mode
        color = self.MODE_COLORS.get(mode, "#333")
        if fault > 0:
            color = "#f00"  # Red for fault

        if color != self._last_color:
            self.setStyleSheet(f"QFrame {{ background-color: {color}; border-radius: 6px; }}")
            self._last_color = color

    def mousePressEvent(self, event):
        self.clicked.emit(self.bridge)
        super().mousePressEvent(event)


class HBridgeWidget(QGroupBox):
    """Widget for displaying H-Bridge motor status (legacy, kept for compatibility)."""

    MODE_NAMES = ["COAST", "FWD", "REV", "BRAKE", "PARK", "PID"]

    def __init__(self, bridge: int, parent=None):
        super().__init__(f"H-Bridge {bridge + 1}", parent)
        self.bridge = bridge
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(4)

        # Mode
        layout.addWidget(QLabel("Mode:"), 0, 0)
        self.mode_label = QLabel("COAST")
        self.mode_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.mode_label, 0, 1)

        # PWM
        layout.addWidget(QLabel("PWM:"), 1, 0)
        self.pwm_bar = QProgressBar()
        self.pwm_bar.setRange(0, 100)
        self.pwm_bar.setTextVisible(True)
        self.pwm_bar.setFormat("%v%")
        layout.addWidget(self.pwm_bar, 1, 1)

        # Current
        layout.addWidget(QLabel("Current:"), 2, 0)
        self.current_label = QLabel("0.00A")
        layout.addWidget(self.current_label, 2, 1)

        # Position
        layout.addWidget(QLabel("Position:"), 3, 0)
        self.position_bar = QProgressBar()
        self.position_bar.setRange(0, 1000)
        self.position_bar.setTextVisible(True)
        self.position_bar.setFormat("%v/1000")
        layout.addWidget(self.position_bar, 3, 1)

    def update_state(self, mode: int, pwm: int, current: float, position: int, fault: int):
        """Update H-Bridge display."""
        mode_name = self.MODE_NAMES[mode] if mode < len(self.MODE_NAMES) else "?"
        self.mode_label.setText(mode_name)
        self.pwm_bar.setValue(pwm // 10)  # PWM is 0-1000
        self.current_label.setText(f"{current:.2f}A")
        self.position_bar.setValue(position)

        if fault > 0:
            self.setStyleSheet("QGroupBox { border: 2px solid red; }")
        else:
            self.setStyleSheet("")

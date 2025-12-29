"""
Input Widgets - Analog and digital input display widgets

This module contains widgets for displaying input channel states.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class AnalogInputWidget(QFrame):
    """Widget for displaying analog input."""

    clicked = pyqtSignal(int)

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._last_voltage_text = None
        self._last_active = None
        self.setFrameStyle(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)

        self.label = QLabel(f"AIN{self.channel + 1}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 8))
        layout.addWidget(self.label)

        self.value_label = QLabel("0.00V")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.value_label)

        self.setMinimumSize(55, 40)

    def update_value(self, voltage: float):
        """Update analog input display."""
        voltage_text = f"{voltage:.2f}V"
        if voltage_text != self._last_voltage_text:
            self.value_label.setText(voltage_text)
            self._last_voltage_text = voltage_text

        # Background color based on voltage (like digital inputs)
        is_active = voltage > 0.5
        if is_active != self._last_active:
            if is_active:
                self.setStyleSheet("background-color: #0a0; border-radius: 4px;")
                self.value_label.setStyleSheet("color: white;")
            else:
                self.setStyleSheet("background-color: #333; border-radius: 4px;")
                self.value_label.setStyleSheet("color: #888;")
            self._last_active = is_active

    def mousePressEvent(self, event):
        self.clicked.emit(self.channel)
        super().mousePressEvent(event)


class DigitalInputWidget(QFrame):
    """Widget for displaying digital input."""

    clicked = pyqtSignal(int)

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._last_state = None
        self.setFrameStyle(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.label = QLabel(f"D{self.channel + 1}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.label)

        self.setMinimumSize(40, 35)
        self.update_state(False)

    def update_state(self, state: bool):
        """Update digital input display."""
        if state == self._last_state:
            return
        self._last_state = state

        if state:
            self.setStyleSheet("background-color: #0a0; border-radius: 4px;")
            self.label.setText(f"D{self.channel + 1}\nHI")
        else:
            self.setStyleSheet("background-color: #333; border-radius: 4px;")
            self.label.setText(f"D{self.channel + 1}\nLO")

    def mousePressEvent(self, event):
        self.clicked.emit(self.channel)
        super().mousePressEvent(event)

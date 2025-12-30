"""
Connection Status Widget

Enhanced connection status display for the status bar.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush


class StatusIndicator(QWidget):
    """Circular status indicator that shows connection state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#6b7280")  # Gray - disconnected
        self._pulsing = False
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._update_pulse)
        self._pulse_opacity = 1.0
        self._pulse_direction = -1

        self.setFixedSize(12, 12)

    def set_connected(self):
        """Set indicator to connected state (green)."""
        self._stop_pulse()
        self._color = QColor("#22c55e")  # Green
        self.update()

    def set_disconnected(self):
        """Set indicator to disconnected state (gray)."""
        self._stop_pulse()
        self._color = QColor("#6b7280")  # Gray
        self.update()

    def set_reconnecting(self):
        """Set indicator to reconnecting state (orange, pulsing)."""
        self._color = QColor("#f59e0b")  # Orange
        self._start_pulse()

    def set_error(self):
        """Set indicator to error state (red)."""
        self._stop_pulse()
        self._color = QColor("#ef4444")  # Red
        self.update()

    def _start_pulse(self):
        """Start pulsing animation."""
        if not self._pulsing:
            self._pulsing = True
            self._pulse_opacity = 1.0
            self._pulse_direction = -1
            self._pulse_timer.start(50)

    def _stop_pulse(self):
        """Stop pulsing animation."""
        self._pulsing = False
        self._pulse_timer.stop()
        self._pulse_opacity = 1.0
        self.update()

    def _update_pulse(self):
        """Update pulse animation."""
        self._pulse_opacity += self._pulse_direction * 0.05
        if self._pulse_opacity <= 0.3:
            self._pulse_direction = 1
        elif self._pulse_opacity >= 1.0:
            self._pulse_direction = -1
        self.update()

    def paintEvent(self, event):
        """Paint the circular indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Create color with current opacity
        color = QColor(self._color)
        if self._pulsing:
            color.setAlphaF(self._pulse_opacity)

        # Draw filled circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(1, 1, 10, 10)

        # Draw border
        border_color = QColor(self._color)
        border_color = border_color.darker(120)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(1, 1, 10, 10)


class ConnectionStatusWidget(QWidget):
    """Enhanced connection status widget for status bar."""

    def __init__(self, device_controller=None, parent=None):
        super().__init__(parent)
        self.device_controller = device_controller
        self._setup_ui()

        if device_controller:
            self._connect_signals()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        # Status indicator
        self.indicator = StatusIndicator()
        layout.addWidget(self.indicator)

        # Status text
        self.status_label = QLabel("OFFLINE")
        self.status_label.setStyleSheet("color: #6b7280; font-weight: bold;")
        layout.addWidget(self.status_label)

        # Device info (hidden when disconnected)
        self.device_label = QLabel()
        self.device_label.setStyleSheet("color: #9ca3af;")
        self.device_label.hide()
        layout.addWidget(self.device_label)

        # Reconnect info (hidden normally)
        self.reconnect_label = QLabel()
        self.reconnect_label.setStyleSheet("color: #f59e0b;")
        self.reconnect_label.hide()
        layout.addWidget(self.reconnect_label)

    def _connect_signals(self):
        """Connect to device controller signals."""
        if self.device_controller:
            self.device_controller.connected.connect(self._on_connected)
            self.device_controller.disconnected.connect(self._on_disconnected)
            self.device_controller.reconnecting.connect(self._on_reconnecting)
            self.device_controller.reconnect_failed.connect(self._on_reconnect_failed)
            self.device_controller.error.connect(self._on_error)

    def _on_connected(self):
        """Handle connection established."""
        self.indicator.set_connected()
        self.status_label.setText("ONLINE")
        self.status_label.setStyleSheet("color: #22c55e; font-weight: bold;")

        # Show device info if available
        if self.device_controller and hasattr(self.device_controller, 'get_device_info'):
            try:
                device_info = self.device_controller.get_device_info()
                if device_info:
                    version = device_info.get("version", "")
                    if version:
                        self.device_label.setText(f"v{version}")
                        self.device_label.show()
                    else:
                        self.device_label.hide()
                else:
                    self.device_label.hide()
            except Exception:
                self.device_label.hide()
        else:
            self.device_label.hide()

        self.reconnect_label.hide()

    def _on_disconnected(self):
        """Handle disconnection."""
        self.indicator.set_disconnected()
        self.status_label.setText("OFFLINE")
        self.status_label.setStyleSheet("color: #6b7280; font-weight: bold;")
        self.device_label.hide()
        self.reconnect_label.hide()

    def _on_reconnecting(self, attempt: int, max_attempts: int):
        """Handle reconnection attempt."""
        self.indicator.set_reconnecting()
        self.status_label.setText("RECONNECTING")
        self.status_label.setStyleSheet("color: #f59e0b; font-weight: bold;")
        self.device_label.hide()

        max_str = str(max_attempts) if max_attempts > 0 else "..."
        self.reconnect_label.setText(f"({attempt}/{max_str})")
        self.reconnect_label.show()

    def _on_reconnect_failed(self):
        """Handle reconnection failure."""
        self.indicator.set_error()
        self.status_label.setText("OFFLINE")
        self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.device_label.hide()
        self.reconnect_label.setText("(failed)")
        self.reconnect_label.setStyleSheet("color: #ef4444;")
        self.reconnect_label.show()

        # Hide failure message after 5 seconds
        QTimer.singleShot(5000, self._clear_failure)

    def _clear_failure(self):
        """Clear failure indication."""
        if self.status_label.text() == "OFFLINE":
            self.reconnect_label.hide()
            self.indicator.set_disconnected()

    def _on_error(self, error_msg: str):
        """Handle device error."""
        # Don't change status for errors, just show briefly
        pass

    def set_connected(self, connected: bool):
        """Manually set connection state."""
        if connected:
            self._on_connected()
        else:
            self._on_disconnected()

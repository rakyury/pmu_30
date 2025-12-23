"""
PMU-30 Connection Bar
Compact connection control widget for bottom panel
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
import logging

logger = logging.getLogger(__name__)


class StatusLED(QFrame):
    """Small LED indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._set_color(QColor(128, 128, 128))

    def _set_color(self, color: QColor):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color.name()};
                border: 1px solid #555;
                border-radius: 6px;
            }}
        """)

    def set_connected(self):
        self._set_color(QColor(0, 200, 0))

    def set_disconnected(self):
        self._set_color(QColor(128, 128, 128))

    def set_error(self):
        self._set_color(QColor(255, 0, 0))

    def set_connecting(self):
        self._set_color(QColor(255, 200, 0))


class ConnectionBar(QWidget):
    """Compact connection control bar."""

    # Signals
    connection_requested = pyqtSignal(str)  # port
    disconnection_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)

        # Status LED
        self.led = StatusLED()
        layout.addWidget(self.led)

        # Status label
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("font-weight: bold;")
        self.status_label.setMinimumWidth(150)
        layout.addWidget(self.status_label)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #ccc;")
        layout.addWidget(sep1)

        # Port selection
        layout.addWidget(QLabel("Port:"))

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(180)
        self.port_combo.setEditable(True)
        layout.addWidget(self.port_combo)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedWidth(70)
        self.refresh_btn.clicked.connect(self._refresh_ports)
        layout.addWidget(self.refresh_btn)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedWidth(80)
        self.connect_btn.clicked.connect(self._toggle_connection)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        layout.addWidget(self.connect_btn)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #ccc;")
        layout.addWidget(sep2)

        # Telemetry stats
        self.stats_label = QLabel("Packets: 0 | Latency: -- ms")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

        layout.addStretch()

        # Device info (right side)
        self.device_label = QLabel("")
        self.device_label.setStyleSheet("color: #888;")
        layout.addWidget(self.device_label)

        # Initial refresh
        self._refresh_ports()

    def _refresh_ports(self):
        """Refresh available ports."""
        try:
            from communication.serial_transport import SerialTransport
            ports = SerialTransport.list_ports()

            self.port_combo.clear()
            self.port_combo.addItem("SIMULATOR - Virtual PMU-30", "SIMULATOR")

            for port in ports:
                display = f"{port.port} - {port.description}"
                if port.is_pmu30:
                    display = f"* {display}"
                self.port_combo.addItem(display, port.port)

        except Exception as e:
            logger.error(f"Failed to list ports: {e}")
            self.port_combo.clear()
            self.port_combo.addItem("SIMULATOR - Virtual PMU-30", "SIMULATOR")

    def _toggle_connection(self):
        """Toggle connection."""
        if self._connected:
            self.disconnection_requested.emit()
        else:
            port = self.port_combo.currentData()
            if port:
                self.led.set_connecting()
                self.status_label.setText("Connecting...")
                self.connection_requested.emit(port)

    def set_connected(self, connected: bool, device_name: str = ""):
        """Update connection state."""
        self._connected = connected

        if connected:
            self.led.set_connected()
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d83b01;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #b83301;
                }
            """)
            self.device_label.setText(device_name)
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
        else:
            self.led.set_disconnected()
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("font-weight: bold; color: #666;")
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
            """)
            self.device_label.setText("")
            self.port_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)

    def set_error(self, message: str):
        """Show error state."""
        self.led.set_error()
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")

    def update_stats(self, packets: int, latency_ms: float):
        """Update telemetry statistics."""
        self.stats_label.setText(f"Packets: {packets} | Latency: {latency_ms:.1f} ms")

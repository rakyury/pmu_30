"""
LED Indicator Widget

Mimics the hardware LED indications from PMU-30 firmware.
Shows system status, connection state, and output summary.
"""

import logging
from enum import IntEnum
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen

logger = logging.getLogger(__name__)


class LEDColor(IntEnum):
    """LED colors matching firmware."""
    OFF = 0
    GREEN = 1
    RED = 2
    ORANGE = 3


class LEDPattern(IntEnum):
    """LED patterns matching firmware."""
    OFF = 0
    SOLID = 1
    BLINK_SLOW = 2  # 500ms period
    BLINK_FAST = 3  # 200ms period
    PULSE = 4       # Fade in/out
    FLASH = 5       # Quick double flash


class SystemStatus(IntEnum):
    """System status matching firmware."""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    WARNING = 3
    FAULT = 4
    CRITICAL = 5


# Color palette
LED_COLORS = {
    LEDColor.OFF: QColor(60, 60, 60),
    LEDColor.GREEN: QColor(0, 200, 0),
    LEDColor.RED: QColor(220, 0, 0),
    LEDColor.ORANGE: QColor(255, 165, 0),
}

LED_COLORS_DIM = {
    LEDColor.OFF: QColor(40, 40, 40),
    LEDColor.GREEN: QColor(0, 80, 0),
    LEDColor.RED: QColor(80, 0, 0),
    LEDColor.ORANGE: QColor(100, 65, 0),
}


class LEDWidget(QWidget):
    """Single LED indicator widget."""

    def __init__(self, size: int = 12, parent=None):
        super().__init__(parent)
        self._size = size
        self._color = LEDColor.OFF
        self._pattern = LEDPattern.OFF
        self._phase = 0
        self._brightness = 1.0
        self._tooltip_base = ""

        self.setFixedSize(size + 4, size + 4)
        self.setToolTip("LED Off")

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_phase)
        self._timer.start(50)  # 20Hz update

    def set_state(self, color: LEDColor, pattern: LEDPattern, tooltip: str = ""):
        """Set LED color and pattern."""
        self._color = color
        self._pattern = pattern
        self._tooltip_base = tooltip
        self._phase = 0
        self._update_tooltip()
        self.update()

    def set_color(self, color: LEDColor):
        """Set LED color, keep pattern."""
        self._color = color
        self.update()

    def set_pattern(self, pattern: LEDPattern):
        """Set LED pattern, keep color."""
        self._pattern = pattern
        self._phase = 0
        self.update()

    def _update_phase(self):
        """Update animation phase."""
        self._phase += 1

        if self._pattern == LEDPattern.OFF or self._pattern == LEDPattern.SOLID:
            self._brightness = 1.0 if self._pattern == LEDPattern.SOLID else 0.0
        elif self._pattern == LEDPattern.BLINK_SLOW:
            # 500ms period (10 frames at 50ms)
            self._brightness = 1.0 if (self._phase // 10) % 2 == 0 else 0.2
        elif self._pattern == LEDPattern.BLINK_FAST:
            # 200ms period (4 frames at 50ms)
            self._brightness = 1.0 if (self._phase // 4) % 2 == 0 else 0.2
        elif self._pattern == LEDPattern.PULSE:
            # Smooth pulse using sine-like pattern
            import math
            self._brightness = 0.3 + 0.7 * abs(math.sin(self._phase * 0.1))
        elif self._pattern == LEDPattern.FLASH:
            # Double flash pattern
            cycle = self._phase % 30
            if cycle < 3 or (cycle >= 6 and cycle < 9):
                self._brightness = 1.0
            else:
                self._brightness = 0.2

        self.update()

    def _update_tooltip(self):
        """Update tooltip text."""
        pattern_names = {
            LEDPattern.OFF: "Off",
            LEDPattern.SOLID: "On",
            LEDPattern.BLINK_SLOW: "Blinking (slow)",
            LEDPattern.BLINK_FAST: "Blinking (fast)",
            LEDPattern.PULSE: "Pulsing",
            LEDPattern.FLASH: "Flashing",
        }
        color_names = {
            LEDColor.OFF: "Off",
            LEDColor.GREEN: "Green",
            LEDColor.RED: "Red",
            LEDColor.ORANGE: "Orange",
        }

        if self._tooltip_base:
            tooltip = f"{self._tooltip_base}\n{color_names.get(self._color, 'Unknown')} - {pattern_names.get(self._pattern, 'Unknown')}"
        else:
            tooltip = f"{color_names.get(self._color, 'Unknown')} - {pattern_names.get(self._pattern, 'Unknown')}"

        self.setToolTip(tooltip)

    def paintEvent(self, event):
        """Paint the LED."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get base color
        if self._color == LEDColor.OFF or self._pattern == LEDPattern.OFF:
            color = LED_COLORS_DIM[LEDColor.OFF]
        else:
            bright = LED_COLORS.get(self._color, LED_COLORS[LEDColor.OFF])
            dim = LED_COLORS_DIM.get(self._color, LED_COLORS_DIM[LEDColor.OFF])

            # Interpolate based on brightness
            r = int(dim.red() + (bright.red() - dim.red()) * self._brightness)
            g = int(dim.green() + (bright.green() - dim.green()) * self._brightness)
            b = int(dim.blue() + (bright.blue() - dim.blue()) * self._brightness)
            color = QColor(r, g, b)

        # Draw LED
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = self._size // 2

        # Outer ring (darker)
        painter.setPen(QPen(QColor(30, 30, 30), 1))
        painter.setBrush(QBrush(color.darker(130)))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

        # Inner glow
        glow_radius = radius - 2
        if glow_radius > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(center_x - glow_radius, center_y - glow_radius,
                              glow_radius * 2, glow_radius * 2)

            # Highlight
            highlight_radius = glow_radius // 2
            if highlight_radius > 0 and self._brightness > 0.5:
                highlight = color.lighter(150)
                highlight.setAlpha(int(100 * self._brightness))
                painter.setBrush(QBrush(highlight))
                painter.drawEllipse(center_x - highlight_radius - 1,
                                  center_y - highlight_radius - 1,
                                  highlight_radius * 2, highlight_radius * 2)


class LEDIndicatorBar(QFrame):
    """
    Status bar LED indicator panel.

    Shows:
    - System status LED (connection, faults)
    - CAN bus status LEDs
    - Output summary LEDs
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setStyleSheet("""
            LEDIndicatorBar {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 2px;
            }
            QLabel {
                color: #888;
                font-size: 10px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)

        # System status LED
        self._status_led = LEDWidget(12)
        self._status_led.set_state(LEDColor.OFF, LEDPattern.OFF, "System Status")
        layout.addWidget(QLabel("SYS"))
        layout.addWidget(self._status_led)

        layout.addWidget(self._create_separator())

        # CAN bus status LEDs
        self._can1_led = LEDWidget(10)
        self._can1_led.set_state(LEDColor.OFF, LEDPattern.OFF, "CAN Bus 1")
        layout.addWidget(QLabel("CAN1"))
        layout.addWidget(self._can1_led)

        self._can2_led = LEDWidget(10)
        self._can2_led.set_state(LEDColor.OFF, LEDPattern.OFF, "CAN Bus 2")
        layout.addWidget(QLabel("CAN2"))
        layout.addWidget(self._can2_led)

        layout.addWidget(self._create_separator())

        # Output status summary
        self._out_active_led = LEDWidget(10)
        self._out_active_led.set_state(LEDColor.OFF, LEDPattern.OFF, "Active Outputs")
        layout.addWidget(QLabel("OUT"))
        layout.addWidget(self._out_active_led)

        self._out_fault_led = LEDWidget(10)
        self._out_fault_led.set_state(LEDColor.OFF, LEDPattern.OFF, "Output Faults")
        layout.addWidget(QLabel("FLT"))
        layout.addWidget(self._out_fault_led)

        layout.addWidget(self._create_separator())

        # Telemetry activity LED
        self._telemetry_led = LEDWidget(10)
        self._telemetry_led.set_state(LEDColor.OFF, LEDPattern.OFF, "Telemetry")
        layout.addWidget(QLabel("TEL"))
        layout.addWidget(self._telemetry_led)

        # Activity counters
        self._active_outputs = 0
        self._fault_count = 0
        self._telemetry_blink_timer = QTimer(self)
        self._telemetry_blink_timer.timeout.connect(self._telemetry_blink_off)

    def _create_separator(self) -> QFrame:
        """Create a vertical separator."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("QFrame { color: #444; }")
        return sep

    def set_connection_status(self, connected: bool, connecting: bool = False):
        """Update connection status LED."""
        if connected:
            self._status_led.set_state(LEDColor.GREEN, LEDPattern.SOLID, "Connected")
        elif connecting:
            self._status_led.set_state(LEDColor.ORANGE, LEDPattern.BLINK_SLOW, "Connecting...")
        else:
            self._status_led.set_state(LEDColor.OFF, LEDPattern.OFF, "Disconnected")

    def set_system_status(self, status: SystemStatus):
        """Update system status LED based on protection state."""
        if status == SystemStatus.CONNECTED:
            self._status_led.set_state(LEDColor.GREEN, LEDPattern.PULSE, "Running")
        elif status == SystemStatus.WARNING:
            self._status_led.set_state(LEDColor.ORANGE, LEDPattern.BLINK_SLOW, "Warning")
        elif status == SystemStatus.FAULT:
            self._status_led.set_state(LEDColor.RED, LEDPattern.BLINK_FAST, "Fault")
        elif status == SystemStatus.CRITICAL:
            self._status_led.set_state(LEDColor.RED, LEDPattern.SOLID, "Critical!")
        elif status == SystemStatus.CONNECTING:
            self._status_led.set_state(LEDColor.ORANGE, LEDPattern.BLINK_SLOW, "Connecting...")
        else:
            self._status_led.set_state(LEDColor.OFF, LEDPattern.OFF, "Disconnected")

    def set_can_status(self, bus: int, online: bool, active: bool = False):
        """Update CAN bus status LED."""
        led = self._can1_led if bus == 1 else self._can2_led
        tooltip = f"CAN Bus {bus}"

        if not online:
            led.set_state(LEDColor.OFF, LEDPattern.OFF, f"{tooltip} - Offline")
        elif active:
            led.set_state(LEDColor.GREEN, LEDPattern.BLINK_FAST, f"{tooltip} - Active")
        else:
            led.set_state(LEDColor.GREEN, LEDPattern.SOLID, f"{tooltip} - Online")

    def set_output_status(self, active_count: int, fault_count: int = 0):
        """Update output status LEDs."""
        self._active_outputs = active_count
        self._fault_count = fault_count

        # Active outputs LED
        if active_count > 0:
            self._out_active_led.set_state(
                LEDColor.GREEN, LEDPattern.SOLID,
                f"Active Outputs: {active_count}"
            )
        else:
            self._out_active_led.set_state(LEDColor.OFF, LEDPattern.OFF, "No Active Outputs")

        # Fault LED
        if fault_count > 0:
            self._out_fault_led.set_state(
                LEDColor.RED, LEDPattern.BLINK_FAST,
                f"Output Faults: {fault_count}"
            )
        else:
            self._out_fault_led.set_state(LEDColor.OFF, LEDPattern.OFF, "No Faults")

    def telemetry_received(self):
        """Flash telemetry LED on data received."""
        self._telemetry_led.set_state(LEDColor.GREEN, LEDPattern.SOLID, "Telemetry Active")
        self._telemetry_blink_timer.start(100)  # Turn off after 100ms

    def _telemetry_blink_off(self):
        """Turn off telemetry LED after blink."""
        self._telemetry_blink_timer.stop()
        self._telemetry_led.set_state(LEDColor.GREEN, LEDPattern.OFF, "Telemetry Active")

    def set_telemetry_active(self, active: bool):
        """Set telemetry LED state."""
        if active:
            self._telemetry_led.set_state(LEDColor.GREEN, LEDPattern.PULSE, "Telemetry Active")
        else:
            self._telemetry_led.set_state(LEDColor.OFF, LEDPattern.OFF, "Telemetry Inactive")


class OutputChannelLEDBar(QFrame):
    """
    40-channel output LED indicator bar.

    Mimics the firmware's channel LED visualization with compact LEDs
    showing each output's state (OFF, ON, PWM, FAULT).
    """

    NUM_CHANNELS = 40  # 30 PROFET + 4 H-Bridge + 6 spare
    LEDS_PER_ROW = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setStyleSheet("""
            OutputChannelLEDBar {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 2px;
            }
            QLabel {
                color: #666;
                font-size: 8px;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 2, 4, 2)
        main_layout.setSpacing(2)

        # Label
        label = QLabel("OUT")
        label.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        main_layout.addWidget(label)

        # Two rows of LEDs
        led_container = QWidget()
        led_layout = QVBoxLayout(led_container)
        led_layout.setContentsMargins(0, 0, 0, 0)
        led_layout.setSpacing(1)

        self._channel_leds = []

        # Create two rows
        for row in range(2):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(1)

            for col in range(self.LEDS_PER_ROW):
                ch = row * self.LEDS_PER_ROW + col
                led = LEDWidget(6)  # Small LEDs
                led.set_state(LEDColor.OFF, LEDPattern.OFF, f"Output {ch}")
                row_layout.addWidget(led)
                self._channel_leds.append(led)

            led_layout.addWidget(row_widget)

        main_layout.addWidget(led_container)

        # State tracking
        self._output_states = [0] * self.NUM_CHANNELS
        self._fault_flags = [0] * self.NUM_CHANNELS

    def update_channel(self, channel: int, state: int, fault: bool = False):
        """
        Update a single channel LED.

        Args:
            channel: Channel index (0-39)
            state: 0=OFF, 1=ON, 2=PWM
            fault: True if channel has a fault
        """
        if channel >= self.NUM_CHANNELS:
            return

        led = self._channel_leds[channel]

        if fault:
            led.set_state(LEDColor.RED, LEDPattern.BLINK_FAST, f"Output {channel}: FAULT")
        elif state == 0:  # OFF
            led.set_state(LEDColor.OFF, LEDPattern.OFF, f"Output {channel}: OFF")
        elif state == 1:  # ON
            led.set_state(LEDColor.GREEN, LEDPattern.SOLID, f"Output {channel}: ON")
        elif state == 2:  # PWM
            led.set_state(LEDColor.GREEN, LEDPattern.BLINK_SLOW, f"Output {channel}: PWM")
        else:
            led.set_state(LEDColor.OFF, LEDPattern.OFF, f"Output {channel}")

    def update_all_channels(self, states: list, faults: list = None):
        """
        Update all channel LEDs from state and fault lists.

        Args:
            states: List of states (0=OFF, 1=ON, 2=PWM)
            faults: Optional list of fault flags per channel
        """
        if faults is None:
            faults = [0] * len(states)

        for i, (state, fault) in enumerate(zip(states, faults)):
            if i >= self.NUM_CHANNELS:
                break
            self.update_channel(i, state, bool(fault))

    def set_all_off(self):
        """Turn off all channel LEDs."""
        for i in range(self.NUM_CHANNELS):
            self._channel_leds[i].set_state(LEDColor.OFF, LEDPattern.OFF, f"Output {i}: OFF")

    def set_all_disconnected(self):
        """Set all channels to disconnected state (dim)."""
        for i in range(self.NUM_CHANNELS):
            self._channel_leds[i].set_state(LEDColor.OFF, LEDPattern.OFF, f"Output {i}")

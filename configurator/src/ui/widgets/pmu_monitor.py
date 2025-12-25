"""
PMU-30 Real-time Monitor Widget
ECUMaster-style tree view for device state monitoring
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QLabel, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MonitorValue:
    """Single monitored value."""
    name: str
    value: Any = "?"
    unit: str = ""
    category: str = ""
    is_fault: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class PMUMonitorWidget(QWidget):
    """
    Real-time PMU state monitor in tree view format.

    Shows all device parameters organized in categories:
    - System (voltage, temperature, current)
    - Outputs (o1-o30 states and currents)
    - Inputs (i1-i20 states)
    - H-Bridges (hb1-hb4)
    - CAN Bus status
    - Faults
    - Device info
    """

    # Colors for different states (dark theme)
    COLOR_NORMAL = QColor(200, 200, 200)      # Light gray for normal text
    COLOR_WARNING = QColor(255, 200, 100)     # Orange for warnings
    COLOR_ERROR = QColor(255, 100, 100)       # Red for errors
    COLOR_ACTIVE = QColor(100, 255, 100)      # Green for active
    COLOR_DISABLED = QColor(128, 128, 128)    # Gray for disabled

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._values: Dict[str, MonitorValue] = {}
        self._items: Dict[str, QTreeWidgetItem] = {}

        self._init_ui()
        self._init_values()

        # Update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._refresh_display)
        self._update_timer.start(100)  # 10Hz refresh

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header
        header_layout = QHBoxLayout()

        self.status_label = QLabel("Offline", self)
        self.status_label.setStyleSheet("color: #b0b0b0;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Tree widget
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["Name", "Value", "Unit"])
        self.tree.setAlternatingRowColors(False)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(15)

        # Column widths
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 60)
        self.tree.setColumnWidth(2, 40)

        # Style (dark theme)
        self.tree.setStyleSheet("""
            QTreeWidget {
                font-size: 11px;
                border: 1px solid #333;
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QTreeWidget::item {
                padding: 2px;
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QTreeWidget::branch {
                background-color: #1a1a1a;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #333;
            }
        """)

        layout.addWidget(self.tree)

    def _init_values(self):
        """Initialize all monitored values."""
        # === System Category ===
        system_cat = self._add_category("System")

        self._add_value("board_temp_1", "Board temperature 1", "°C", system_cat)
        self._add_value("battery_voltage", "Battery voltage", "V", system_cat)
        self._add_value("board_temp_2", "Board temperature 2", "°C", system_cat)
        self._add_value("5v_output", "5V output", "V", system_cat)
        self._add_value("3v3_output", "Board 3V3", "V", system_cat)
        self._add_value("flash_temp", "Flash temperature", "°C", system_cat)
        self._add_value("total_current", "Total current", "A", system_cat)
        self._add_value("reset_detector", "Reset detector", "", system_cat)
        self._add_value("status", "Status", "", system_cat)
        self._add_value("user_error", "User error", "", system_cat)
        self._add_value("is_turning_off", "Is turning off", "", system_cat)

        # === HW OUT Active Mask ===
        out_active_cat = self._add_category("HW OUT active mask")
        for i in range(1, 31):
            self._add_value(f"out_active_{i}", f".o{i}", "", out_active_cat)

        # === HW LS OUT Active ===
        ls_active_cat = self._add_category("HW LS OUT active")
        for i in range(1, 7):
            self._add_value(f"ls_active_{i}", f".l{i}", "", ls_active_cat)

        # === HW LS OUT Shutdown ===
        ls_shutdown_cat = self._add_category("HW LS OUT shutdown")
        for i in range(1, 7):
            self._add_value(f"ls_shutdown_{i}", f".l{i}", "", ls_shutdown_cat)

        # === Output Currents ===
        out_current_cat = self._add_category("Output currents")
        for i in range(1, 31):
            self._add_value(f"out_current_{i}", f"o{i} current", "mA", out_current_cat)

        # === Output States ===
        out_state_cat = self._add_category("Output states")
        for i in range(1, 31):
            self._add_value(f"out_state_{i}", f"o{i} state", "", out_state_cat)

        # === Analog Inputs ===
        ain_cat = self._add_category("Analog inputs")
        for i in range(1, 21):
            self._add_value(f"ain_{i}", f"AIN{i}", "V", ain_cat)

        # === Digital Inputs ===
        din_cat = self._add_category("Digital inputs")
        for i in range(1, 21):
            self._add_value(f"din_{i}", f"DIN{i}", "", din_cat)

        # === H-Bridges ===
        hb_cat = self._add_category("H-Bridges")
        for i in range(1, 5):
            hb_sub = self._add_category(f"HB{i}", hb_cat)
            self._add_value(f"hb{i}_state", "State", "", hb_sub)
            self._add_value(f"hb{i}_current", "Current", "A", hb_sub)
            self._add_value(f"hb{i}_duty", "Duty", "%", hb_sub)

        # === CAN Bus ===
        can_cat = self._add_category("CAN Bus")
        for i in range(1, 5):
            can_sub = self._add_category(f"CAN{i}", can_cat)
            self._add_value(f"can{i}_status", "Status", "", can_sub)
            self._add_value(f"can{i}_rx_count", "RX count", "", can_sub)
            self._add_value(f"can{i}_tx_count", "TX count", "", can_sub)
            self._add_value(f"can{i}_errors", "Errors", "", can_sub)

        # === Faults ===
        fault_cat = self._add_category("Faults")
        self._add_value("fault_overvoltage", "Overvoltage", "", fault_cat)
        self._add_value("fault_undervoltage", "Undervoltage", "", fault_cat)
        self._add_value("fault_overtemp", "Overtemperature", "", fault_cat)
        self._add_value("fault_can1", "CAN1 error", "", fault_cat)
        self._add_value("fault_can2", "CAN2 error", "", fault_cat)
        self._add_value("fault_config", "Config error", "", fault_cat)
        self._add_value("fault_watchdog", "Watchdog reset", "", fault_cat)

        # === Device Info ===
        info_cat = self._add_category("Device info")
        self._add_value("serial_a", "Serial number part A", "", info_cat)
        self._add_value("serial_b", "Serial number part B", "", info_cat)
        self._add_value("serial_c", "Serial number part C", "", info_cat)
        self._add_value("firmware_version", "Firmware version", "", info_cat)
        self._add_value("hardware_rev", "Hardware revision", "", info_cat)
        self._add_value("uptime", "Uptime", "s", info_cat)

        # Expand important categories
        system_cat.setExpanded(True)

    def _add_category(self, name: str, parent=None) -> QTreeWidgetItem:
        """Add a category to the tree."""
        if parent is None:
            item = QTreeWidgetItem(self.tree)
        else:
            item = QTreeWidgetItem(parent)

        item.setText(0, name)
        item.setFirstColumnSpanned(False)

        # Bold font for categories
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

        return item

    def _add_value(self, key: str, name: str, unit: str, parent: QTreeWidgetItem) -> QTreeWidgetItem:
        """Add a value item to the tree."""
        item = QTreeWidgetItem(parent)
        item.setText(0, name)
        item.setText(1, "?")
        item.setText(2, unit)
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setTextAlignment(2, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Store reference
        self._items[key] = item
        self._values[key] = MonitorValue(name=name, unit=unit)

        return item

    def set_value(self, key: str, value: Any, is_fault: bool = False):
        """Set a monitored value."""
        if key not in self._values:
            return

        self._values[key].value = value
        self._values[key].is_fault = is_fault

    def set_connected(self, connected: bool):
        """Set connection state."""
        self._connected = connected

        if connected:
            self.status_label.setText("Online")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("Offline")
            self.status_label.setStyleSheet("color: #b0b0b0;")
            # Reset all values to "?"
            for key in self._values:
                self._values[key].value = "?"
                self._values[key].is_fault = False

    def _refresh_display(self):
        """Refresh the tree display with current values."""
        for key, item in self._items.items():
            if key not in self._values:
                continue

            mv = self._values[key]

            # Format value
            if isinstance(mv.value, float):
                text = f"{mv.value:.2f}"
            elif isinstance(mv.value, int):
                text = str(mv.value)
            elif mv.value is None:
                text = "?"
            else:
                text = str(mv.value)

            item.setText(1, text)

            # Set background color based on state
            if mv.is_fault:
                bg = self.COLOR_ERROR
            elif mv.value == "?" or not self._connected:
                bg = self.COLOR_DISABLED
            elif isinstance(mv.value, bool) and mv.value:
                bg = self.COLOR_ACTIVE
            elif isinstance(mv.value, (int, float)):
                # Check limits
                if mv.min_value is not None and mv.value < mv.min_value:
                    bg = self.COLOR_WARNING
                elif mv.max_value is not None and mv.value > mv.max_value:
                    bg = self.COLOR_WARNING
                else:
                    bg = self.COLOR_NORMAL
            else:
                bg = self.COLOR_NORMAL

            for col in range(3):
                item.setBackground(col, QBrush(bg))

    def update_from_telemetry(self, data: dict):
        """Update values from telemetry packet."""
        # System values
        self.set_value("battery_voltage", data.get("voltage_v", "?"))
        self.set_value("board_temp_1", data.get("temperature_c", "?"))
        self.set_value("total_current", data.get("current_a", "?"))
        self.set_value("uptime", data.get("uptime_ms", 0) // 1000 if data.get("uptime_ms") else "?")

        # Extended system values from expanded telemetry
        self.set_value("board_temp_2", data.get("board_temp_2", "?"))
        output_5v = data.get("output_5v_mv", 0)
        self.set_value("5v_output", output_5v / 1000.0 if isinstance(output_5v, (int, float)) and output_5v else "?")
        output_3v3 = data.get("output_3v3_mv", 0)
        self.set_value("3v3_output", output_3v3 / 1000.0 if isinstance(output_3v3, (int, float)) and output_3v3 else "?")
        self.set_value("flash_temp", data.get("flash_temp", "?"))

        # System status bits
        system_status = data.get("system_status", 0)
        self.set_value("status", hex(system_status) if isinstance(system_status, int) else "?")
        self.set_value("reset_detector", "Yes" if system_status & 0x01 else "No")
        self.set_value("user_error", "Yes" if system_status & 0x02 else "No")
        self.set_value("is_turning_off", "Yes" if system_status & 0x04 else "No")

        # Output states
        channel_states = data.get("channel_states", [])
        for i, state in enumerate(channel_states[:30]):
            state_names = ["OFF", "ON", "OC", "OT", "SC", "OL", "PWM", "DIS"]
            state_str = state_names[state] if state < len(state_names) else "?"
            self.set_value(f"out_state_{i+1}", state_str)
            self.set_value(f"out_active_{i+1}", 1 if state in [1, 6] else 0)

        # Output currents
        channel_currents = data.get("channel_currents", [])
        for i, current in enumerate(channel_currents[:30]):
            self.set_value(f"out_current_{i+1}", current)

        # Analog inputs
        analog_values = data.get("analog_values", [])
        for i, val in enumerate(analog_values[:20]):
            # Convert ADC to voltage (12-bit, 3.3V ref)
            voltage = (val / 4095.0) * 3.3 if isinstance(val, (int, float)) else "?"
            self.set_value(f"ain_{i+1}", voltage)

        # Fault flags - display as OK/FAULT
        fault_flags = data.get("fault_flags", 0)
        self.set_value("fault_overvoltage", "FAULT" if fault_flags & 0x01 else "OK", bool(fault_flags & 0x01))
        self.set_value("fault_undervoltage", "FAULT" if fault_flags & 0x02 else "OK", bool(fault_flags & 0x02))
        self.set_value("fault_overtemp", "FAULT" if fault_flags & 0x04 else "OK", bool(fault_flags & 0x04))
        self.set_value("fault_can1", "FAULT" if fault_flags & 0x08 else "OK", bool(fault_flags & 0x08))
        self.set_value("fault_can2", "FAULT" if fault_flags & 0x10 else "OK", bool(fault_flags & 0x10))
        self.set_value("fault_config", "FAULT" if fault_flags & 0x40 else "OK", bool(fault_flags & 0x40))
        self.set_value("fault_watchdog", "FAULT" if fault_flags & 0x80 else "OK", bool(fault_flags & 0x80))

    def update_device_info(self, info: dict):
        """Update device info values."""
        serial = info.get("serial_number", "")
        if len(serial) >= 12:
            self.set_value("serial_a", serial[:4])
            self.set_value("serial_b", serial[4:8])
            self.set_value("serial_c", serial[8:12])

        self.set_value("firmware_version", info.get("firmware_version", "?"))
        self.set_value("hardware_rev", info.get("hardware_revision", "?"))

    def expand_all(self):
        """Expand all tree items."""
        self.tree.expandAll()

    def collapse_all(self):
        """Collapse all tree items."""
        self.tree.collapseAll()

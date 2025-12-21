"""
H-Bridge Configuration Tab
Manages 4 dual H-Bridge channels for DC motor control
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..dialogs.hbridge_dialog import HBridgeDialog
from typing import Dict, Any, List


class HBridgeTab(QWidget):
    """H-Bridge configuration tab."""

    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Initialize 4 H-Bridge channels with default configuration
        self.hbridge_channels = [self._create_default_channel(i) for i in range(4)]
        self._init_ui()

    def _create_default_channel(self, channel: int) -> Dict[str, Any]:
        """Create default configuration for an H-Bridge channel."""
        return {
            "name": f"H-Bridge {channel}",
            "enabled": False,
            "mode": "Bidirectional",
            "control": {
                "mode": "PWM (0-100%)",
                "forward": {
                    "type": "Physical Input (0-19)",
                    "channel": channel * 3
                },
                "reverse": {
                    "type": "Physical Input (0-19)",
                    "channel": channel * 3 + 1
                },
                "speed": {
                    "type": "Physical Input (0-19)",
                    "channel": channel * 3 + 2
                }
            },
            "pwm": {
                "frequency": "5 kHz",
                "min_duty": 10,
                "max_duty": 100
            },
            "protection": {
                "current_limit_a": 10.0,
                "thermal_protection": True,
                "overcurrent_action": "Disable Output"
            },
            "advanced": {
                "soft_start_ms": 100,
                "soft_stop_ms": 100,
                "active_braking": False,
                "invert_direction": False
            }
        }

    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)

        # Info group
        info_group = QGroupBox("H-Bridge Motor Control")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "4 dual H-Bridge channels for DC motor control.\n"
            "Each channel can drive bidirectional motors with PWM speed control.\n"
            "Supports current limiting, thermal protection, and soft start/stop."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Channel", "Name", "Mode", "PWM Freq", "Current Limit", "Status"
        ])
        self.table.setRowCount(4)  # Fixed 4 H-Bridge channels
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self.edit_channel)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.configure_btn = QPushButton("Configure")
        self.configure_btn.clicked.connect(self.edit_channel)
        button_layout.addWidget(self.configure_btn)

        self.copy_btn = QPushButton("Copy to...")
        self.copy_btn.clicked.connect(self.copy_channel)
        button_layout.addWidget(self.copy_btn)

        button_layout.addStretch()

        self.reset_channel_btn = QPushButton("Reset Channel")
        self.reset_channel_btn.clicked.connect(self.reset_channel)
        button_layout.addWidget(self.reset_channel_btn)

        self.reset_all_btn = QPushButton("Reset All")
        self.reset_all_btn.clicked.connect(self.reset_all)
        button_layout.addWidget(self.reset_all_btn)

        layout.addLayout(button_layout)

        # Stats label
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)

        self._update_table()

    def _update_table(self):
        """Update table with current H-Bridge configurations."""
        for channel in range(4):
            config = self.hbridge_channels[channel]

            # Channel number
            channel_item = QTableWidgetItem(str(channel))
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            channel_item.setFlags(channel_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if not config.get("enabled", False):
                channel_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(channel, 0, channel_item)

            # Name
            name = QTableWidgetItem(config.get("name", f"H-Bridge {channel}"))
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if not config.get("enabled", False):
                name.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(channel, 1, name)

            # Mode
            mode = QTableWidgetItem(config.get("mode", "Bidirectional"))
            mode.setFlags(mode.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(channel, 2, mode)

            # PWM Frequency
            pwm_freq = config.get("pwm", {}).get("frequency", "5 kHz")
            freq_item = QTableWidgetItem(pwm_freq)
            freq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            freq_item.setFlags(freq_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(channel, 3, freq_item)

            # Current Limit
            current_limit = config.get("protection", {}).get("current_limit_a", 10.0)
            current_item = QTableWidgetItem(f"{current_limit:.1f} A")
            current_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            current_item.setFlags(current_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(channel, 4, current_item)

            # Status
            status_text = "Enabled" if config.get("enabled", False) else "Disabled"
            status = QTableWidgetItem(status_text)
            status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status.setFlags(status.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if config.get("enabled", False):
                status.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(channel, 5, status)

        self._update_stats()

    def _update_stats(self):
        """Update statistics label."""
        enabled_count = sum(1 for ch in self.hbridge_channels if ch.get("enabled", False))
        total_current = sum(ch.get("protection", {}).get("current_limit_a", 0)
                          for ch in self.hbridge_channels if ch.get("enabled", False))

        self.stats_label.setText(
            f"H-Bridge Channels: {enabled_count}/4 Enabled | "
            f"Total Current Limit: {total_current:.1f} A"
        )

    def edit_channel(self):
        """Edit selected H-Bridge channel."""
        row = self.table.currentRow()
        if row < 0 or row >= 4:
            QMessageBox.warning(self, "No Selection", "Please select an H-Bridge channel to configure.")
            return

        dialog = HBridgeDialog(
            self,
            channel=row,
            config=self.hbridge_channels[row]
        )

        if dialog.exec():
            config = dialog.get_config()
            self.hbridge_channels[row] = config
            self._update_table()
            self.configuration_changed.emit()

    def copy_channel(self):
        """Copy configuration from one channel to another."""
        from PyQt6.QtWidgets import QInputDialog

        row = self.table.currentRow()
        if row < 0 or row >= 4:
            QMessageBox.warning(self, "No Selection", "Please select an H-Bridge channel to copy from.")
            return

        items = [f"H-Bridge {i}" for i in range(4) if i != row]
        item, ok = QInputDialog.getItem(
            self, "Copy Configuration",
            f"Copy configuration from H-Bridge {row} to:",
            items, 0, False
        )

        if ok and item:
            # Extract destination channel number
            dest_channel = int(item.split()[-1])

            # Copy configuration
            import copy
            self.hbridge_channels[dest_channel] = copy.deepcopy(self.hbridge_channels[row])
            self.hbridge_channels[dest_channel]["name"] = f"H-Bridge {dest_channel}"

            self._update_table()
            self.configuration_changed.emit()

            QMessageBox.information(
                self, "Configuration Copied",
                f"Configuration copied from H-Bridge {row} to H-Bridge {dest_channel}"
            )

    def reset_channel(self):
        """Reset selected channel to defaults."""
        row = self.table.currentRow()
        if row < 0 or row >= 4:
            QMessageBox.warning(self, "No Selection", "Please select an H-Bridge channel to reset.")
            return

        reply = QMessageBox.question(
            self, "Confirm Reset",
            f"Reset H-Bridge {row} to default configuration?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.hbridge_channels[row] = self._create_default_channel(row)
            self._update_table()
            self.configuration_changed.emit()

    def reset_all(self):
        """Reset all channels to defaults."""
        reply = QMessageBox.question(
            self, "Confirm Reset All",
            "Reset all H-Bridge channels to default configuration?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.hbridge_channels = [self._create_default_channel(i) for i in range(4)]
            self._update_table()
            self.configuration_changed.emit()

    def load_configuration(self, config: dict):
        """Load H-Bridge configuration."""
        hbridge_config = config.get("hbridge", [])

        # Load configuration for each channel
        for i in range(4):
            if i < len(hbridge_config):
                self.hbridge_channels[i] = hbridge_config[i]
            else:
                self.hbridge_channels[i] = self._create_default_channel(i)

        self._update_table()

    def get_configuration(self) -> dict:
        """Get current H-Bridge configuration."""
        return {
            "hbridge": self.hbridge_channels
        }

    def reset_to_defaults(self):
        """Reset to default configuration."""
        self.hbridge_channels = [self._create_default_channel(i) for i in range(4)]
        self._update_table()

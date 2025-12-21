"""
Channel Selector Dialog
Universal dialog for selecting any channel/signal in the system
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtCore import Qt
from typing import List, Dict, Any, Optional


class ChannelSelectorDialog(QDialog):
    """Dialog for selecting a channel from all available sources."""

    def __init__(self, parent=None, current_channel: str = "", channels_data: Optional[Dict[str, List[str]]] = None):
        super().__init__(parent)
        self.selected_channel = current_channel
        self.channels_data = channels_data or {}

        self.setWindowTitle("Select Channel")
        self.setModal(True)
        self.resize(600, 500)

        self._init_ui()
        self._populate_channels()

        # Select current channel if provided
        if current_channel:
            self._select_channel(current_channel)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header with count
        self.header_label = QLabel()
        self.header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.header_label)

        # Search/filter box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search channels...")
        self.search_edit.textChanged.connect(self._on_search)
        layout.addWidget(self.search_edit)

        # Channel list
        self.channel_list = QListWidget()
        self.channel_list.setAlternatingRowColors(True)
        self.channel_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.channel_list)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _populate_channels(self):
        """Populate channel list with all available channels."""
        self.all_channels = []

        # Physical Inputs
        if "inputs_physical" in self.channels_data:
            for ch in self.channels_data["inputs_physical"]:
                self.all_channels.append(("Input (Physical)", ch))

        # Virtual Inputs
        if "inputs_virtual" in self.channels_data:
            for ch in self.channels_data["inputs_virtual"]:
                self.all_channels.append(("Input (Virtual)", ch))

        # Physical Outputs
        if "outputs_physical" in self.channels_data:
            for ch in self.channels_data["outputs_physical"]:
                self.all_channels.append(("Output (Physical)", ch))

        # Virtual Outputs
        if "outputs_virtual" in self.channels_data:
            for ch in self.channels_data["outputs_virtual"]:
                self.all_channels.append(("Output (Virtual)", ch))

        # Functions
        if "functions" in self.channels_data:
            for ch in self.channels_data["functions"]:
                self.all_channels.append(("Function", ch))

        # Tables
        if "tables" in self.channels_data:
            for ch in self.channels_data["tables"]:
                self.all_channels.append(("Table", ch))

        # Numbers/Constants
        if "numbers" in self.channels_data:
            for ch in self.channels_data["numbers"]:
                self.all_channels.append(("Number", ch))

        # Switches
        if "switches" in self.channels_data:
            for ch in self.channels_data["switches"]:
                self.all_channels.append(("Switch", ch))

        # Timers
        if "timers" in self.channels_data:
            for ch in self.channels_data["timers"]:
                self.all_channels.append(("Timer", ch))

        # Enums
        if "enums" in self.channels_data:
            for ch in self.channels_data["enums"]:
                self.all_channels.append(("Enum", ch))

        # CAN Signals
        if "can_signals" in self.channels_data:
            for ch in self.channels_data["can_signals"]:
                self.all_channels.append(("CAN", ch))

        # PID Controllers
        if "pid_controllers" in self.channels_data:
            for ch in self.channels_data["pid_controllers"]:
                self.all_channels.append(("PID", ch))

        # H-Bridge
        if "hbridge" in self.channels_data:
            for ch in self.channels_data["hbridge"]:
                self.all_channels.append(("H-Bridge", ch))

        self._update_list()

    def _update_list(self, filter_text: str = ""):
        """Update channel list with optional filter."""
        self.channel_list.clear()

        filter_lower = filter_text.lower()
        visible_count = 0

        for category, channel in self.all_channels:
            # Apply filter
            if filter_text and filter_lower not in channel.lower():
                continue

            item = QListWidgetItem(channel)
            item.setData(Qt.ItemDataRole.UserRole, channel)
            item.setToolTip(f"{category}: {channel}")

            # Add category prefix for clarity
            item.setText(channel)

            self.channel_list.addItem(item)
            visible_count += 1

        # Update header
        total_count = len(self.all_channels)
        if filter_text:
            self.header_label.setText(f"Select Channel [{visible_count} of {total_count}]")
        else:
            self.header_label.setText(f"Select Channel [{total_count} of {total_count}]")

    def _on_search(self, text: str):
        """Handle search text change."""
        self._update_list(text)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle item double-click."""
        self.accept()

    def _select_channel(self, channel: str):
        """Select a channel in the list."""
        for i in range(self.channel_list.count()):
            item = self.channel_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == channel:
                self.channel_list.setCurrentItem(item)
                self.channel_list.scrollToItem(item)
                break

    def get_selected_channel(self) -> str:
        """Get selected channel name."""
        current = self.channel_list.currentItem()
        if current:
            return current.data(Qt.ItemDataRole.UserRole)
        return ""

    @staticmethod
    def select_channel(parent=None, current_channel: str = "", channels_data: Optional[Dict[str, List[str]]] = None) -> Optional[str]:
        """Static method to show dialog and return selected channel."""
        dialog = ChannelSelectorDialog(parent, current_channel, channels_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected_channel()
        return None

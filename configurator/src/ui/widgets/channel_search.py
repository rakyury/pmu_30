"""
Channel Search Widget

Provides quick search functionality for finding channels in the configuration.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget,
    QTreeWidgetItem, QLabel, QComboBox, QPushButton, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeyEvent

from models.channel import ChannelType


class ChannelSearchDialog(QDialog):
    """Dialog for searching channels in the configuration."""

    # Signal emitted when a channel is selected (channel_type, channel_data)
    channel_selected = pyqtSignal(object, dict)

    def __init__(self, parent=None, project_tree=None):
        super().__init__(parent)
        self.project_tree = project_tree
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)

        self._setup_ui()
        self._load_all_channels()

    def _setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Search Channels")
        self.setMinimumSize(500, 400)
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # Search input row
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search channels...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input)

        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", None)
        self.category_combo.addItem("Inputs", "inputs")
        self.category_combo.addItem("Outputs", "outputs")
        self.category_combo.addItem("Virtual", "virtual")
        self.category_combo.addItem("CAN", "can")
        self.category_combo.currentIndexChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.category_combo)

        layout.addLayout(search_layout)

        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Name", "Type", "Details"])
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setRootIsDecorated(False)
        self.results_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.results_tree.itemSelectionChanged.connect(self._on_selection_changed)

        # Configure header
        header = self.results_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.results_tree)

        # Status and buttons
        bottom_layout = QHBoxLayout()

        self.status_label = QLabel("")
        bottom_layout.addWidget(self.status_label)

        bottom_layout.addStretch()

        self.go_button = QPushButton("Go to Channel")
        self.go_button.setEnabled(False)
        self.go_button.clicked.connect(self._on_go_clicked)
        bottom_layout.addWidget(self.go_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_button)

        layout.addLayout(bottom_layout)

        # Focus on search input
        self.search_input.setFocus()

    def _load_all_channels(self):
        """Load all channels from project tree."""
        self._all_channels = []

        if not self.project_tree:
            return

        channels = self.project_tree.get_all_channels()
        for channel in channels:
            channel_type_str = channel.get("channel_type", "")
            try:
                channel_type = ChannelType(channel_type_str)
            except ValueError:
                channel_type = None

            self._all_channels.append({
                "name": channel.get("name", channel.get("id", "unnamed")),
                "channel_type": channel_type,
                "channel_type_str": channel_type_str,
                "data": channel,
                "category": self._get_category(channel_type_str)
            })

        self._update_results(self._all_channels)

    def _get_category(self, channel_type_str: str) -> str:
        """Get category for a channel type."""
        input_types = {"digital_input", "analog_input"}
        output_types = {"output", "hbridge"}
        can_types = {"can_rx", "can_tx", "can_message"}
        virtual_types = {"logic", "timer", "number", "enum", "filter", "table2d", "table3d", "pid", "handler", "switch"}

        if channel_type_str in input_types:
            return "inputs"
        elif channel_type_str in output_types:
            return "outputs"
        elif channel_type_str in can_types:
            return "can"
        elif channel_type_str in virtual_types:
            return "virtual"
        return "other"

    def _on_search_text_changed(self, text: str):
        """Handle search text change with debouncing."""
        self._search_timer.stop()
        self._search_timer.start(150)  # 150ms debounce

    def _on_filter_changed(self):
        """Handle filter change."""
        self._perform_search()

    def _perform_search(self):
        """Perform the search."""
        search_text = self.search_input.text().lower().strip()
        category_filter = self.category_combo.currentData()

        results = []
        for channel in self._all_channels:
            # Category filter
            if category_filter and channel["category"] != category_filter:
                continue

            # Text search
            if search_text:
                name = channel["name"].lower()
                type_str = channel["channel_type_str"].lower()

                # Search in name and type
                if search_text not in name and search_text not in type_str:
                    # Also search in details
                    data = channel["data"]
                    details = str(data).lower()
                    if search_text not in details:
                        continue

            results.append(channel)

        self._update_results(results)

    def _update_results(self, results: List[Dict]):
        """Update the results tree."""
        self.results_tree.clear()

        for channel in results:
            item = QTreeWidgetItem()
            item.setText(0, channel["name"])
            item.setText(1, channel["channel_type_str"])
            item.setText(2, self._get_channel_details(channel["data"]))
            item.setData(0, Qt.ItemDataRole.UserRole, channel)
            self.results_tree.addTopLevelItem(item)

        count = len(results)
        total = len(self._all_channels)
        if count == total:
            self.status_label.setText(f"{count} channels")
        else:
            self.status_label.setText(f"{count} of {total} channels")

    def _get_channel_details(self, data: Dict) -> str:
        """Get display details for a channel."""
        channel_type = data.get("channel_type", "")

        if channel_type == "digital_input":
            pin = data.get("input_pin", "?")
            return f"Pin {pin}"
        elif channel_type == "analog_input":
            pin = data.get("input_pin", "?")
            return f"Pin {pin}"
        elif channel_type == "output":
            output_num = data.get("output_num", "?")
            return f"Output {output_num}"
        elif channel_type == "logic":
            operation = data.get("operation", "?")
            return f"Op: {operation}"
        elif channel_type == "timer":
            timer_type = data.get("type", "?")
            return f"Type: {timer_type}"
        elif channel_type == "can_rx":
            msg_name = data.get("can_message", "?")
            return f"Msg: {msg_name}"
        elif channel_type == "can_tx":
            msg_name = data.get("can_message", "?")
            return f"Msg: {msg_name}"
        elif channel_type == "pid":
            return "PID Controller"
        elif channel_type == "handler":
            return "Handler"

        return ""

    def _on_selection_changed(self):
        """Handle selection change."""
        items = self.results_tree.selectedItems()
        self.go_button.setEnabled(len(items) > 0)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double-click."""
        self._navigate_to_selected()

    def _on_go_clicked(self):
        """Handle Go button click."""
        self._navigate_to_selected()

    def _navigate_to_selected(self):
        """Navigate to the selected channel."""
        items = self.results_tree.selectedItems()
        if not items:
            return

        item = items[0]
        channel_info = item.data(0, Qt.ItemDataRole.UserRole)
        if channel_info:
            channel_type = channel_info["channel_type"]
            channel_data = channel_info["data"]
            self.channel_selected.emit(channel_type, channel_data)
            self.close()

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self.results_tree.selectedItems():
                self._navigate_to_selected()
            elif self.results_tree.topLevelItemCount() == 1:
                # If only one result, select and navigate
                self.results_tree.setCurrentItem(self.results_tree.topLevelItem(0))
                self._navigate_to_selected()
        elif event.key() == Qt.Key.Key_Down and self.search_input.hasFocus():
            # Move focus to results
            if self.results_tree.topLevelItemCount() > 0:
                self.results_tree.setFocus()
                self.results_tree.setCurrentItem(self.results_tree.topLevelItem(0))
        else:
            super().keyPressEvent(event)

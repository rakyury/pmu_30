"""
Channel Selector Dialog
Universal dialog for selecting any GPIO channel in the system
Supports all GPIO types with categorization
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QLabel,
    QTreeWidget, QTreeWidgetItem, QSplitter, QWidget,
    QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from typing import List, Dict, Any, Optional

from models.channel import ChannelType, CHANNEL_PREFIX_MAP


class ChannelSelectorDialog(QDialog):
    """Dialog for selecting a channel from all available sources."""

    # Category definitions with display names and channel types
    CATEGORIES = {
        "Inputs": {
            "icon_color": "#10b981",  # Green
            "types": [
                (ChannelType.DIGITAL_INPUT, "Digital Inputs"),
                (ChannelType.ANALOG_INPUT, "Analog Inputs"),
                (ChannelType.CAN_RX, "CAN RX"),
            ]
        },
        "Outputs": {
            "icon_color": "#ef4444",  # Red
            "types": [
                (ChannelType.POWER_OUTPUT, "Power Outputs"),
                (ChannelType.CAN_TX, "CAN TX"),
            ]
        },
        "Functions": {
            "icon_color": "#3b82f6",  # Blue
            "types": [
                (ChannelType.LOGIC, "Logic Functions"),
                (ChannelType.NUMBER, "Math Channels"),
                (ChannelType.FILTER, "Filters"),
            ]
        },
        "Tables": {
            "icon_color": "#8b5cf6",  # Purple
            "types": [
                (ChannelType.TABLE_2D, "2D Tables"),
                (ChannelType.TABLE_3D, "3D Tables"),
            ]
        },
        "State": {
            "icon_color": "#f59e0b",  # Orange
            "types": [
                (ChannelType.SWITCH, "Switches"),
                (ChannelType.TIMER, "Timers"),
            ]
        },
        "Data": {
            "icon_color": "#06b6d4",  # Cyan
            "types": [
                (ChannelType.ENUM, "Enumerations"),
            ]
        }
    }

    # Channel type to category key mapping
    CHANNEL_TYPE_CATEGORY_KEY = {
        ChannelType.DIGITAL_INPUT: "digital_inputs",
        ChannelType.ANALOG_INPUT: "analog_inputs",
        ChannelType.POWER_OUTPUT: "power_outputs",
        ChannelType.CAN_RX: "can_rx",
        ChannelType.CAN_TX: "can_tx",
        ChannelType.LOGIC: "logic",
        ChannelType.NUMBER: "numbers",
        ChannelType.TABLE_2D: "tables_2d",
        ChannelType.TABLE_3D: "tables_3d",
        GPIOType.SWITCH: "switches",
        GPIOType.TIMER: "timers",
        GPIOType.FILTER: "filters",
        GPIOType.ENUM: "enums",
    }

    def __init__(self, parent=None, current_channel: str = "",
                 channels_data: Optional[Dict[str, List[str]]] = None,
                 show_tree: bool = True):
        """
        Initialize channel selector dialog.

        Args:
            parent: Parent widget
            current_channel: Currently selected channel (to highlight)
            channels_data: Dictionary with channel lists by type
            show_tree: If True, show tree view with categories; otherwise flat list
        """
        super().__init__(parent)
        self.selected_channel = current_channel
        self.channels_data = channels_data or {}
        self.show_tree = show_tree
        self.all_channels: List[tuple] = []  # (gpio_type, channel_id, display_name)

        self.setWindowTitle("Select Channel")
        self.setModal(True)
        self.resize(700, 550)

        self._init_ui()
        self._populate_channels()

        # Select current channel if provided
        if current_channel:
            self._select_channel(current_channel)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header with count and filter
        header_layout = QHBoxLayout()

        self.header_label = QLabel()
        self.header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        # Category filter
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        for cat_name in self.CATEGORIES.keys():
            self.category_filter.addItem(cat_name, cat_name)
        self.category_filter.currentIndexChanged.connect(self._on_filter_changed)
        header_layout.addWidget(QLabel("Filter:"))
        header_layout.addWidget(self.category_filter)

        layout.addLayout(header_layout)

        # Search/filter box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search channels by name or ID...")
        self.search_edit.textChanged.connect(self._on_search)
        self.search_edit.setClearButtonEnabled(True)
        layout.addWidget(self.search_edit)

        # Main content
        if self.show_tree:
            # Tree view with categories
            self.tree = QTreeWidget()
            self.tree.setHeaderLabels(["Channel", "Type"])
            self.tree.setColumnWidth(0, 350)
            self.tree.setAlternatingRowColors(True)
            self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
            self.tree.itemSelectionChanged.connect(self._on_selection_changed)
            layout.addWidget(self.tree)
            self.channel_list = None
        else:
            # Flat list
            self.channel_list = QListWidget()
            self.channel_list.setAlternatingRowColors(True)
            self.channel_list.itemDoubleClicked.connect(self._on_item_double_clicked)
            layout.addWidget(self.channel_list)
            self.tree = None

        # Preview panel
        self.preview_label = QLabel("Select a channel to see details")
        self.preview_label.setStyleSheet(
            "color: #666; font-style: italic; padding: 8px; "
            "background-color: #f5f5f5; border-radius: 4px;"
        )
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)

        # Buttons
        button_layout = QHBoxLayout()

        # Clear selection button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_selection)
        button_layout.addWidget(self.clear_btn)

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

        # Map old keys to new GPIO types for backwards compatibility
        key_mapping = {
            # Old format
            "inputs_physical": GPIOType.ANALOG_INPUT,
            "inputs_virtual": GPIOType.ANALOG_INPUT,
            "outputs_physical": GPIOType.POWER_OUTPUT,
            "outputs_virtual": GPIOType.POWER_OUTPUT,
            "functions": GPIOType.LOGIC,
            "tables": GPIOType.TABLE_2D,
            "numbers": GPIOType.NUMBER,
            "switches": GPIOType.SWITCH,
            "timers": GPIOType.TIMER,
            "enums": GPIOType.ENUM,
            "can_signals": GPIOType.CAN_RX,
            "pid_controllers": GPIOType.NUMBER,  # Map PID to number
            "hbridge": GPIOType.POWER_OUTPUT,  # Map H-Bridge to output
            # New GPIO format keys
            "digital_inputs": GPIOType.DIGITAL_INPUT,
            "analog_inputs": GPIOType.ANALOG_INPUT,
            "power_outputs": GPIOType.POWER_OUTPUT,
            "can_rx": GPIOType.CAN_RX,
            "can_tx": GPIOType.CAN_TX,
            "logic": GPIOType.LOGIC,
            "tables_2d": GPIOType.TABLE_2D,
            "tables_3d": GPIOType.TABLE_3D,
            "filters": GPIOType.FILTER,
        }

        # Process channels from data
        for key, channels in self.channels_data.items():
            gpio_type = key_mapping.get(key)
            if gpio_type and channels:
                prefix = GPIO_TYPE_PREFIXES.get(gpio_type, "")
                for ch in channels:
                    # Ensure channel has prefix
                    if prefix and not ch.startswith(prefix):
                        channel_id = f"{prefix}{ch}"
                    else:
                        channel_id = ch
                    self.all_channels.append((gpio_type, channel_id, ch))

        self._update_display()

    def _update_display(self, filter_text: str = "", category_filter: str = None):
        """Update display with optional filter."""
        filter_lower = filter_text.lower()
        visible_count = 0

        if self.show_tree and self.tree:
            self.tree.clear()
            category_items = {}

            for gpio_type, channel_id, display_name in self.all_channels:
                # Apply text filter
                if filter_text:
                    if filter_lower not in channel_id.lower() and filter_lower not in display_name.lower():
                        continue

                # Find category for this GPIO type
                cat_name = None
                type_name = None
                for cat, info in self.CATEGORIES.items():
                    for gtype, tname in info["types"]:
                        if gtype == gpio_type:
                            cat_name = cat
                            type_name = tname
                            break
                    if cat_name:
                        break

                # Apply category filter
                if category_filter and cat_name != category_filter:
                    continue

                if not cat_name:
                    cat_name = "Other"
                    type_name = gpio_type.value if gpio_type else "Unknown"

                # Create category item if needed
                if cat_name not in category_items:
                    cat_item = QTreeWidgetItem(self.tree, [cat_name, ""])
                    cat_item.setExpanded(True)
                    cat_color = self.CATEGORIES.get(cat_name, {}).get("icon_color", "#666")
                    cat_item.setForeground(0, QColor(cat_color))
                    cat_item.setData(0, Qt.ItemDataRole.UserRole, None)  # No channel data for categories
                    category_items[cat_name] = cat_item

                # Add channel item
                item = QTreeWidgetItem(category_items[cat_name])
                item.setText(0, channel_id)
                item.setText(1, type_name)
                item.setData(0, Qt.ItemDataRole.UserRole, channel_id)
                item.setToolTip(0, f"{type_name}: {channel_id}")
                visible_count += 1

        elif self.channel_list:
            self.channel_list.clear()

            for gpio_type, channel_id, display_name in self.all_channels:
                # Apply text filter
                if filter_text:
                    if filter_lower not in channel_id.lower() and filter_lower not in display_name.lower():
                        continue

                # Find type name
                type_name = gpio_type.value if gpio_type else "Unknown"
                for cat, info in self.CATEGORIES.items():
                    for gtype, tname in info["types"]:
                        if gtype == gpio_type:
                            type_name = tname
                            break

                # Apply category filter
                if category_filter:
                    cat_match = False
                    for gtype, _ in self.CATEGORIES.get(category_filter, {}).get("types", []):
                        if gtype == gpio_type:
                            cat_match = True
                            break
                    if not cat_match:
                        continue

                item = QListWidgetItem(channel_id)
                item.setData(Qt.ItemDataRole.UserRole, channel_id)
                item.setToolTip(f"{type_name}: {channel_id}")
                self.channel_list.addItem(item)
                visible_count += 1

        # Update header
        total_count = len(self.all_channels)
        if filter_text or category_filter:
            self.header_label.setText(f"Channels [{visible_count} of {total_count}]")
        else:
            self.header_label.setText(f"Channels [{total_count}]")

    def _on_search(self, text: str):
        """Handle search text change."""
        category = self.category_filter.currentData()
        self._update_display(text, category)

    def _on_filter_changed(self):
        """Handle category filter change."""
        category = self.category_filter.currentData()
        self._update_display(self.search_edit.text(), category)

    def _on_item_double_clicked(self, item, column=0):
        """Handle item double-click."""
        if self.tree:
            channel = item.data(0, Qt.ItemDataRole.UserRole)
            if channel:  # Not a category
                self.accept()
        else:
            self.accept()

    def _on_selection_changed(self):
        """Handle selection change - update preview."""
        if self.tree:
            items = self.tree.selectedItems()
            if items:
                item = items[0]
                channel = item.data(0, Qt.ItemDataRole.UserRole)
                if channel:
                    type_name = item.text(1) or "Channel"
                    self.preview_label.setText(f"<b>{type_name}</b><br>{channel}")
                    self.preview_label.setStyleSheet(
                        "color: #333; padding: 8px; "
                        "background-color: #e8f4f8; border-radius: 4px; border: 1px solid #0078d4;"
                    )
                    return

        self.preview_label.setText("Select a channel to see details")
        self.preview_label.setStyleSheet(
            "color: #666; font-style: italic; padding: 8px; "
            "background-color: #f5f5f5; border-radius: 4px;"
        )

    def _select_channel(self, channel: str):
        """Select a channel in the list."""
        if self.tree:
            # Iterate through all items
            iterator = self.tree.itemIterator() if hasattr(self.tree, 'itemIterator') else None
            # Manual iteration
            for i in range(self.tree.topLevelItemCount()):
                cat_item = self.tree.topLevelItem(i)
                for j in range(cat_item.childCount()):
                    child = cat_item.child(j)
                    if child.data(0, Qt.ItemDataRole.UserRole) == channel:
                        self.tree.setCurrentItem(child)
                        self.tree.scrollToItem(child)
                        return
        elif self.channel_list:
            for i in range(self.channel_list.count()):
                item = self.channel_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == channel:
                    self.channel_list.setCurrentItem(item)
                    self.channel_list.scrollToItem(item)
                    return

    def _clear_selection(self):
        """Clear current selection."""
        self.selected_channel = ""
        if self.tree:
            self.tree.clearSelection()
        elif self.channel_list:
            self.channel_list.clearSelection()
        self._on_selection_changed()

    def get_selected_channel(self) -> str:
        """Get selected channel name."""
        if self.tree:
            items = self.tree.selectedItems()
            if items:
                channel = items[0].data(0, Qt.ItemDataRole.UserRole)
                if channel:
                    return channel
        elif self.channel_list:
            current = self.channel_list.currentItem()
            if current:
                return current.data(Qt.ItemDataRole.UserRole)
        return ""

    @staticmethod
    def select_channel(parent=None, current_channel: str = "",
                       channels_data: Optional[Dict[str, List[str]]] = None,
                       show_tree: bool = True) -> Optional[str]:
        """Static method to show dialog and return selected channel."""
        dialog = ChannelSelectorDialog(parent, current_channel, channels_data, show_tree)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected_channel()
        return None

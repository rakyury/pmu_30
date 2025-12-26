"""
Channel Selector Dialog
Universal dialog for selecting any channel in the system
Supports all channel types with categorization
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

from models.channel import ChannelType


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
        "System": {
            "icon_color": "#64748b",  # Slate gray
            "types": [
                (ChannelType.SYSTEM, "System Channels"),
                (ChannelType.OUTPUT_STATUS, "Output States"),
            ]
        }
    }

    # Predefined system channels with numeric IDs (from firmware pmu_channel.h)
    # Format: (channel_id: int, string_name: str, display_name: str)
    SYSTEM_CHANNELS = [
        # Constant values (always return 0 or 1)
        (1012, "zero", "Zero (constant 0)"),
        (1013, "one", "One (constant 1)"),

        # PMU System channels (1000-1011)
        (1000, "pmu.batteryVoltage", "Battery Voltage (mV)"),
        (1001, "pmu.totalCurrent", "Total Current (mA)"),
        (1002, "pmu.mcuTemperature", "MCU Temperature (°C)"),
        (1003, "pmu.boardTemperatureL", "Board Temperature L (°C)"),
        (1004, "pmu.boardTemperatureR", "Board Temperature R (°C)"),
        (1005, "pmu.boardTemperatureMax", "Board Temperature Max (°C)"),
        (1006, "pmu.uptime", "Uptime (s)"),
        (1007, "pmu.status", "System Status"),
        (1008, "pmu.userError", "User Error"),
        (1009, "pmu.5VOutput", "5V Output (mV)"),
        (1010, "pmu.3V3Output", "3.3V Output (mV)"),
        (1011, "pmu.isTurningOff", "Is Turning Off"),

        # RTC channels (1020-1027)
        (1020, "pmu.rtc.time", "RTC Time"),
        (1021, "pmu.rtc.date", "RTC Date"),
        (1022, "pmu.rtc.hour", "RTC Hour"),
        (1023, "pmu.rtc.minute", "RTC Minute"),
        (1024, "pmu.rtc.second", "RTC Second"),
        (1025, "pmu.rtc.day", "RTC Day"),
        (1026, "pmu.rtc.month", "RTC Month"),
        (1027, "pmu.rtc.year", "RTC Year"),

        # Serial number channels (1030-1031)
        (1030, "pmu.serialNumber.high", "Serial Number (high)"),
        (1031, "pmu.serialNumber.low", "Serial Number (low)"),
    ]

    # PMU Hardware analog input sub-properties
    ANALOG_INPUT_SUBCHANNELS = [
        ("voltage", "Voltage"),     # Raw voltage (mV)
        ("raw", "Raw ADC"),         # Raw ADC value
    ]

    # PMU Hardware digital input sub-properties
    DIGITAL_INPUT_SUBCHANNELS = [
        ("state", "State"),         # Digital state (0/1)
    ]

    # Output sub-properties (ECUMaster compatible)
    # These are available for each power output channel
    OUTPUT_SUBCHANNELS = [
        ("active", "Active"),           # Is output currently on
        ("current", "Current"),         # Current draw (mA)
        ("dc", "Duty Cycle"),           # PWM duty cycle (%)
        ("fault", "Fault"),             # Fault detected
        ("load", "Load"),               # Load detection
        ("numRetries", "Retry Count"),  # Number of retries after fault
        ("peakCurrent", "Peak Current"), # Peak current (mA)
        ("status", "Status"),           # Output status code
        ("timeAboveMax", "Time Above Max"), # Time above max threshold (ms)
        ("trip", "Trip"),               # Trip/overcurrent flag
        ("voltage", "Voltage"),         # Output voltage (mV)
    ]

    # Timer sub-properties
    TIMER_SUBCHANNELS = [
        ("elapsed", "Elapsed Time"),    # Elapsed time (ms)
        ("running", "Is Running"),      # Timer is currently running
    ]

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
        ChannelType.SWITCH: "switches",
        ChannelType.TIMER: "timers",
        ChannelType.FILTER: "filters",
        ChannelType.SYSTEM: "system",
        ChannelType.OUTPUT_STATUS: "output_status",
    }

    def __init__(self, parent=None, current_channel: str = "",
                 channels_data: Optional[Dict[str, List[str]]] = None,
                 show_tree: bool = True,
                 exclude_channel: Any = None):
        """
        Initialize channel selector dialog.

        Args:
            parent: Parent widget
            current_channel: Currently selected channel (to highlight)
            channels_data: Dictionary with channel lists by type
            show_tree: If True, show tree view with categories; otherwise flat list
            exclude_channel: Channel ID to exclude from selection (prevents self-reference)
        """
        super().__init__(parent)
        self.selected_channel = current_channel
        self.channels_data = channels_data or {}
        self.show_tree = show_tree
        self.exclude_channel = exclude_channel
        self.all_channels: List[tuple] = []  # (channel_type, channel_id, display_name)

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

        # View toggle button
        self.view_toggle_btn = QPushButton("Flat View" if self.show_tree else "Tree View")
        self.view_toggle_btn.setFixedWidth(80)
        self.view_toggle_btn.clicked.connect(self._toggle_view)
        header_layout.addWidget(self.view_toggle_btn)

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

        # Main content - create both but show one
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Channel", "Type"])
        self.tree.setColumnWidth(0, 350)
        self.tree.setAlternatingRowColors(False)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)

        self.channel_list = QListWidget()
        self.channel_list.setAlternatingRowColors(False)
        self.channel_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.channel_list.itemSelectionChanged.connect(self._on_selection_changed)

        # Add both to layout, hide one
        layout.addWidget(self.tree)
        layout.addWidget(self.channel_list)

        if self.show_tree:
            self.channel_list.hide()
        else:
            self.tree.hide()

        # Preview panel
        self.preview_label = QLabel("Select a channel to see details")
        self.preview_label.setStyleSheet(
            "color: #b0b0b0; font-style: italic; padding: 8px; "
            "background-color: #2d2d2d; border-radius: 4px;"
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
        """Populate channel list with all available channels.

        Supports two formats:
        - New format: lists of (channel_id: int, name: str) tuples
        - Old format: lists of strings (for backwards compatibility)
        """
        self.all_channels = []

        # Map keys to channel types
        key_mapping = {
            # New channel format keys
            "digital_inputs": ChannelType.DIGITAL_INPUT,
            "analog_inputs": ChannelType.ANALOG_INPUT,
            "power_outputs": ChannelType.POWER_OUTPUT,
            "can_rx": ChannelType.CAN_RX,
            "can_tx": ChannelType.CAN_TX,
            "logic": ChannelType.LOGIC,
            "numbers": ChannelType.NUMBER,
            "tables_2d": ChannelType.TABLE_2D,
            "tables_3d": ChannelType.TABLE_3D,
            "filters": ChannelType.FILTER,
            "switches": ChannelType.SWITCH,
            "timers": ChannelType.TIMER,
            "lua_scripts": ChannelType.LUA_SCRIPT,
            "pid_controllers": ChannelType.PID,
        }

        # Process channels from data
        # New format: (string_id, display_name, units, decimal_places)
        # Tuple format: (channel_type, channel_id, display_name, units, decimal_places)
        for key, channels in self.channels_data.items():
            channel_type = key_mapping.get(key)
            if channel_type and channels:
                for ch in channels:
                    if isinstance(ch, tuple) and len(ch) >= 4:
                        # New format: (string_id, display_name, units, decimal_places)
                        channel_id, display_name, units, decimal_places = ch[0], ch[1], ch[2], ch[3]
                        self.all_channels.append((channel_type, channel_id, display_name, units, decimal_places))
                    elif isinstance(ch, tuple) and len(ch) == 2:
                        # Old format: (string_id, display_name) - backwards compat
                        channel_id, display_name = ch
                        self.all_channels.append((channel_type, channel_id, display_name, "", None))
                    elif isinstance(ch, str):
                        # Old format: string name (backwards compat, use string as ID)
                        self.all_channels.append((channel_type, ch, ch, "", None))

        # Add predefined system channels (now with numeric IDs)
        for ch_num_id, ch_str_id, ch_name in self.SYSTEM_CHANNELS:
            # System channels: display name is the string ID (pmu.xxx), numeric ID is ch_num_id
            self.all_channels.append((ChannelType.SYSTEM, ch_num_id, ch_str_id, "", None))

        # Add hardware analog input channels (a1 through a20)
        # Analog voltage base: 1220 + (input_index - 1)
        for i in range(1, 21):
            ch_num_id = 1220 + (i - 1)  # 1220-1239
            ch_name = f"pmu.a{i}.voltage"  # String ID format as display name
            self.all_channels.append((ChannelType.SYSTEM, ch_num_id, ch_name, "", None))

        # Add hardware digital input channels (d1 through d20)
        # Digital input base: 0-19 (physical inputs)
        for i in range(1, 21):
            ch_num_id = i - 1  # 0-19
            ch_name = f"pmu.d{i}.state"  # String ID format as display name
            self.all_channels.append((ChannelType.SYSTEM, ch_num_id, ch_name, "", None))

        # Add hardware output sub-channels (o1 through o30)
        # Output status: 1100 + output_index, current: 1130 + output_index, etc.
        for i in range(1, 31):
            idx = i - 1
            # Status sub-channel
            self.all_channels.append((ChannelType.OUTPUT_STATUS, 1100 + idx, f"pmu.o{i}.status", "", None))
            # Current sub-channel
            self.all_channels.append((ChannelType.OUTPUT_STATUS, 1130 + idx, f"pmu.o{i}.current", "", None))
            # Voltage sub-channel
            self.all_channels.append((ChannelType.OUTPUT_STATUS, 1160 + idx, f"pmu.o{i}.voltage", "", None))
            # Active sub-channel
            self.all_channels.append((ChannelType.OUTPUT_STATUS, 1190 + idx, f"pmu.o{i}.active", "", None))
            # Duty cycle sub-channel
            self.all_channels.append((ChannelType.OUTPUT_STATUS, 1250 + idx, f"pmu.o{i}.dutyCycle", "", None))

        # Add sub-channels for user-created power outputs
        user_outputs = self.channels_data.get("power_outputs", [])
        for idx, output in enumerate(user_outputs):
            if isinstance(output, tuple) and len(output) >= 2:
                output_id, output_name = output[0], output[1]
            else:
                output_id = output_name = str(output)
            # User outputs use their channel_id (first element) if it's numeric
            base_id = output_id if isinstance(output_id, int) else (200 + idx)
            for sub_id, sub_name in self.OUTPUT_SUBCHANNELS:
                ch_name = f"{output_name} - {sub_name}"
                # Generate sub-channel numeric ID based on base + offset
                self.all_channels.append((ChannelType.OUTPUT_STATUS, base_id, ch_name, "", None))

        # Add sub-channels for user-created timers
        user_timers = self.channels_data.get("timers", [])
        for idx, timer in enumerate(user_timers):
            if isinstance(timer, tuple) and len(timer) >= 2:
                timer_id, timer_name = timer[0], timer[1]
            else:
                timer_id = timer_name = str(timer)
            base_id = timer_id if isinstance(timer_id, int) else (300 + idx)
            for sub_id, sub_name in self.TIMER_SUBCHANNELS:
                ch_name = f"{timer_name} - {sub_name}"
                self.all_channels.append((ChannelType.SYSTEM, base_id, ch_name, "", None))

        self._update_display()

    def _update_display(self, filter_text: str = "", category_filter: str = None):
        """Update display with optional filter.

        Shows display_name to user but stores channel_id (numeric or string) in UserRole.
        Tree view shows: Category -> Type -> Channels (two-level grouping)
        """
        filter_lower = filter_text.lower()
        visible_count = 0

        def format_channel_text(display_name: str, channel_id, units: str, decimal_places) -> str:
            """Format channel display text with name, ID, units and decimal places."""
            # Ensure we always have a display text
            if not display_name:
                if channel_id is not None:
                    display_name = f"#{channel_id}" if isinstance(channel_id, int) else str(channel_id)
                else:
                    display_name = "unnamed"

            # Show ID in brackets - numeric with #, string as-is
            if channel_id is not None:
                if isinstance(channel_id, int):
                    text = f"{display_name}  [#{channel_id}]"
                else:
                    text = f"{display_name}  [{channel_id}]"
            else:
                text = display_name

            # Add units and decimal places if available
            extra_info = []
            if units:
                extra_info.append(units)
            if decimal_places is not None:
                extra_info.append(f".{decimal_places}")
            if extra_info:
                text += f"  ({', '.join(extra_info)})"

            return text

        if self.show_tree and self.tree is not None:
            self.tree.clear()
            category_items = {}  # cat_name -> QTreeWidgetItem
            type_items = {}  # (cat_name, type_name) -> QTreeWidgetItem

            for ch_data in self.all_channels:
                # Unpack tuple: (channel_type, channel_id, display_name, units, decimal_places)
                gpio_type = ch_data[0]
                channel_id = ch_data[1]  # Numeric int ID
                display_name = ch_data[2]
                units = ch_data[3] if len(ch_data) > 3 else ""
                decimal_places = ch_data[4] if len(ch_data) > 4 else None

                # Skip excluded channel (prevents self-reference)
                if self.exclude_channel is not None and channel_id == self.exclude_channel:
                    continue

                # Convert to string for filtering
                channel_id_str = str(channel_id) if channel_id is not None else ""
                display_name_str = str(display_name) if display_name else ""

                # Apply text filter
                if filter_text:
                    if filter_lower not in channel_id_str.lower() and filter_lower not in display_name_str.lower():
                        continue

                # Find category for this channel type
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

                # Create type sub-item if needed (two-level grouping)
                type_key = (cat_name, type_name)
                if type_key not in type_items:
                    type_item = QTreeWidgetItem(category_items[cat_name], [type_name, ""])
                    type_item.setExpanded(True)
                    type_item.setData(0, Qt.ItemDataRole.UserRole, None)  # No channel data for types
                    type_item.setForeground(0, QColor("#888888"))
                    type_items[type_key] = type_item

                # Add channel item under type
                item = QTreeWidgetItem(type_items[type_key])
                item.setText(0, format_channel_text(display_name_str, channel_id, units, decimal_places))
                item.setText(1, "")  # Type already shown in parent
                item.setData(0, Qt.ItemDataRole.UserRole, channel_id)  # Store ID
                id_display = f"#{channel_id}" if isinstance(channel_id, int) else str(channel_id)
                tooltip = f"{type_name}: {display_name_str}\nChannel ID: {id_display}"
                if units:
                    tooltip += f"\nUnits: {units}"
                if decimal_places is not None:
                    tooltip += f"\nDecimals: {decimal_places}"
                item.setToolTip(0, tooltip)
                visible_count += 1

            # Update type counts and collapse large groups
            for type_key, type_item in type_items.items():
                child_count = type_item.childCount()
                type_item.setText(1, f"({child_count})")
                if child_count > 15:
                    type_item.setExpanded(False)

        elif self.channel_list is not None:
            self.channel_list.clear()

            for ch_data in self.all_channels:
                # Unpack tuple: (channel_type, channel_id, display_name, units, decimal_places)
                gpio_type = ch_data[0]
                channel_id = ch_data[1]  # Numeric int ID
                display_name = ch_data[2]
                units = ch_data[3] if len(ch_data) > 3 else ""
                decimal_places = ch_data[4] if len(ch_data) > 4 else None
                # Skip excluded channel (prevents self-reference)
                if self.exclude_channel is not None and channel_id == self.exclude_channel:
                    continue

                # Convert to string for filtering
                channel_id_str = str(channel_id) if channel_id is not None else ""
                display_name_str = str(display_name) if display_name else ""

                # Apply text filter
                if filter_text:
                    if filter_lower not in channel_id_str.lower() and filter_lower not in display_name_str.lower():
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

                # Create list item with formatted text
                item = QListWidgetItem(format_channel_text(display_name_str, channel_id, units, decimal_places))
                item.setData(Qt.ItemDataRole.UserRole, channel_id)  # Store ID
                id_display = f"#{channel_id}" if isinstance(channel_id, int) else str(channel_id)
                tooltip = f"{type_name}: {display_name_str}\nChannel ID: {id_display}"
                if units:
                    tooltip += f"\nUnits: {units}"
                if decimal_places is not None:
                    tooltip += f"\nDecimals: {decimal_places}"
                item.setToolTip(tooltip)
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

    def _toggle_view(self):
        """Toggle between tree and flat list view."""
        self.show_tree = not self.show_tree

        if self.show_tree:
            self.channel_list.hide()
            self.tree.show()
            self.view_toggle_btn.setText("Flat View")
        else:
            self.tree.hide()
            self.channel_list.show()
            self.view_toggle_btn.setText("Tree View")

        # Remember selected channel
        selected = self.get_selected_channel()

        # Refresh display
        self._update_display(self.search_edit.text(), self.category_filter.currentData())

        # Restore selection
        if selected:
            self._select_channel(selected)

    def _on_item_double_clicked(self, item, column=0):
        """Handle item double-click."""
        # Get channel data - works for both tree and list items
        channel = item.data(0, Qt.ItemDataRole.UserRole) if self.show_tree else item.data(Qt.ItemDataRole.UserRole)
        if channel:  # Valid channel selected (not a category header)
            self.accept()

    def _on_selection_changed(self):
        """Handle selection change - update preview."""
        channel_id = None
        display_text = None

        if self.tree:
            items = self.tree.selectedItems()
            if items:
                item = items[0]
                channel_id = item.data(0, Qt.ItemDataRole.UserRole)
                if channel_id is not None:
                    # Find original display name from all_channels
                    for ch_data in self.all_channels:
                        if ch_data[1] == channel_id:
                            display_text = ch_data[2]
                            break
        elif self.channel_list:
            current = self.channel_list.currentItem()
            if current:
                channel_id = current.data(Qt.ItemDataRole.UserRole)
                for ch_data in self.all_channels:
                    if ch_data[1] == channel_id:
                        display_text = ch_data[2]
                        break

        if channel_id is not None:
            id_display = f"#{channel_id}" if isinstance(channel_id, int) else str(channel_id)
            self.preview_label.setText(
                f"<b>Name:</b> {display_text or 'unnamed'}<br>"
                f"<b>Channel ID:</b> <code>{id_display}</code>"
            )
            self.preview_label.setStyleSheet(
                "color: #fff; padding: 8px; "
                "background-color: #1a3a4d; border-radius: 4px; border: 1px solid #0078d4;"
            )
        else:
            self.preview_label.setText("Select a channel to see details")
            self.preview_label.setStyleSheet(
                "color: #b0b0b0; font-style: italic; padding: 8px; "
                "background-color: #2d2d2d; border-radius: 4px;"
            )

    def _select_channel(self, channel_id):
        """Select a channel in the list by its channel_id (int or str)."""
        if self.tree:
            # Manual iteration through three-level hierarchy: Category -> Type -> Channel
            for i in range(self.tree.topLevelItemCount()):
                cat_item = self.tree.topLevelItem(i)
                for j in range(cat_item.childCount()):
                    type_item = cat_item.child(j)
                    for k in range(type_item.childCount()):
                        channel_item = type_item.child(k)
                        if channel_item.data(0, Qt.ItemDataRole.UserRole) == channel_id:
                            # Expand parents
                            cat_item.setExpanded(True)
                            type_item.setExpanded(True)
                            self.tree.setCurrentItem(channel_item)
                            self.tree.scrollToItem(channel_item)
                            return
        elif self.channel_list:
            for i in range(self.channel_list.count()):
                item = self.channel_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == channel_id:
                    self.channel_list.setCurrentItem(item)
                    self.channel_list.scrollToItem(item)
                    return

    def _clear_selection(self):
        """Clear current selection."""
        self.selected_channel = None
        if self.tree:
            self.tree.clearSelection()
        elif self.channel_list:
            self.channel_list.clearSelection()
        self._on_selection_changed()

    def get_selected_channel(self) -> Any:
        """Get selected channel_id (string 'id' field for firmware references)."""
        if self.tree:
            items = self.tree.selectedItems()
            if items:
                channel_id = items[0].data(0, Qt.ItemDataRole.UserRole)
                if channel_id is not None:
                    return channel_id
        elif self.channel_list:
            current = self.channel_list.currentItem()
            if current:
                return current.data(Qt.ItemDataRole.UserRole)
        return None

    @staticmethod
    def get_system_channel_name(channel_id: int) -> Optional[str]:
        """Get string_name for a system channel by its numeric ID.

        This is the central lookup for resolving numeric system channel IDs
        to their human-readable string names (e.g., 1007 -> "pmu.status").

        Args:
            channel_id: Numeric channel ID

        Returns:
            String name (e.g., "pmu.status") or None if not a system channel
        """
        if channel_id is None:
            return None

        # Check predefined system channels
        for ch_id, str_name, display_name in ChannelSelectorDialog.SYSTEM_CHANNELS:
            if ch_id == channel_id:
                return str_name

        # Hardware analog input channels (1220-1239)
        if 1220 <= channel_id <= 1239:
            idx = channel_id - 1220 + 1
            return f"pmu.a{idx}.voltage"

        # Hardware digital input channels (0-19)
        if 0 <= channel_id <= 19:
            return f"pmu.d{channel_id + 1}.state"

        # Output status sub-channels (1100-1129)
        if 1100 <= channel_id <= 1129:
            idx = channel_id - 1100 + 1
            return f"pmu.o{idx}.status"

        # Output current sub-channels (1130-1159)
        if 1130 <= channel_id <= 1159:
            idx = channel_id - 1130 + 1
            return f"pmu.o{idx}.current"

        # Output voltage sub-channels (1160-1189)
        if 1160 <= channel_id <= 1189:
            idx = channel_id - 1160 + 1
            return f"pmu.o{idx}.voltage"

        # Output active sub-channels (1190-1219)
        if 1190 <= channel_id <= 1219:
            idx = channel_id - 1190 + 1
            return f"pmu.o{idx}.active"

        # Output duty cycle sub-channels (1250-1279)
        if 1250 <= channel_id <= 1279:
            idx = channel_id - 1250 + 1
            return f"pmu.o{idx}.dutyCycle"

        return None

    @staticmethod
    def get_channel_display_name(channel_id, available_channels: Optional[Dict[str, List]] = None) -> str:
        """Get display name for any channel (user or system).

        This is the universal lookup for resolving channel_id to display name.
        Use this in any dialog that needs to display a channel name.

        Args:
            channel_id: Channel ID (numeric int or string)
            available_channels: Dict of available channels for user channel lookup

        Returns:
            Display name string (e.g., "FuelLevel", "pmu.status") or "#{id}" fallback
        """
        if channel_id is None or channel_id == "":
            return ""

        # Normalize to int if possible
        numeric_id = None
        if isinstance(channel_id, int):
            numeric_id = channel_id
        elif isinstance(channel_id, str):
            clean_id = channel_id.lstrip('#').strip()
            if clean_id.isdigit():
                numeric_id = int(clean_id)

        # 1. Search user channels in available_channels
        if available_channels:
            for category, channels in available_channels.items():
                for ch in channels:
                    if isinstance(ch, tuple) and len(ch) >= 2:
                        ch_id = ch[0]
                        ch_name = ch[1]
                        if ch_id == channel_id or (numeric_id is not None and ch_id == numeric_id):
                            return str(ch_name)

        # 2. Check system channels
        if numeric_id is not None:
            system_name = ChannelSelectorDialog.get_system_channel_name(numeric_id)
            if system_name:
                return system_name

        # 3. Fallback
        if numeric_id is not None:
            return f"#{numeric_id}"
        return str(channel_id) if channel_id else ""

    @staticmethod
    def select_channel(parent=None, current_channel=None,
                       channels_data: Optional[Dict[str, List]] = None,
                       show_tree: bool = True,
                       exclude_channel: Any = None) -> tuple:
        """Static method to show dialog and return selected channel_id.

        Args:
            parent: Parent widget
            current_channel: Currently selected channel_id (string)
            channels_data: Dict mapping category to list of (string_id, name) tuples
            show_tree: Show tree view or flat list
            exclude_channel: Channel ID to exclude from selection (prevents self-reference)

        Returns:
            Tuple of (accepted: bool, channel_id_or_none)
            - (True, string_id) - User selected a channel (string 'id' for firmware)
            - (True, None) - User cleared selection (pressed Clear + OK)
            - (False, None) - User cancelled dialog
        """
        dialog = ChannelSelectorDialog(parent, current_channel, channels_data, show_tree, exclude_channel)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return (True, dialog.get_selected_channel())
        return (False, None)

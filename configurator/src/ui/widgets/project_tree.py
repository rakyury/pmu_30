"""
Project Tree Widget
Hierarchical tree view of all channels (unified architecture)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMenu, QMessageBox, QHeaderView, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPixmap, QPainter, QBrush
from typing import Dict, Any, Optional, List
import logging

from models.channel import ChannelType, CHANNEL_PREFIX_MAP
from ui.widgets.channel_formatter import (
    format_channel_details, format_channel_source, format_channel_tooltip
)

logger = logging.getLogger(__name__)


class ProjectTree(QWidget):
    """Project tree with unified channel architecture."""

    # Signals
    item_selected = pyqtSignal(str, object)  # (channel_type, item_data)
    item_added = pyqtSignal(str)  # channel_type
    item_edited = pyqtSignal(str, object)  # (channel_type, item_data)
    item_deleted = pyqtSignal(str, object)  # (channel_type, item_data)
    configuration_changed = pyqtSignal()
    show_dependents_requested = pyqtSignal(str, str)  # (channel_type, channel_name)

    # Status colors for icons
    STATUS_COLORS = {
        "enabled": "#22c55e",      # Green - active/enabled
        "disabled": "#6b7280",     # Gray - disabled
        "error": "#ef4444",        # Red - error state
        "warning": "#f59e0b",      # Orange - warning
        "input": "#3b82f6",        # Blue - input
        "output": "#8b5cf6",       # Purple - output
        "logic": "#06b6d4",        # Cyan - logic/function
        "timer": "#ec4899",        # Pink - timer
        "table": "#14b8a6",        # Teal - table
        "can": "#f97316",          # Orange - CAN
        "script": "#84cc16",       # Lime - script
        "peripheral": "#a855f7",   # Violet - peripheral
        "handler": "#f43f5e",      # Rose - event handler
    }

    # Folder structure with channel types
    FOLDER_STRUCTURE = {
        "Inputs": {
            "subfolders": {
                "Digital Inputs": {"channel_type": ChannelType.DIGITAL_INPUT},
                "Analog Inputs": {"channel_type": ChannelType.ANALOG_INPUT},
                "CAN Inputs": {"channel_type": ChannelType.CAN_RX},
            }
        },
        "Outputs": {
            "subfolders": {
                "Power Outputs": {"channel_type": ChannelType.POWER_OUTPUT},
                "H-Bridge Motors": {"channel_type": ChannelType.HBRIDGE},
                "CAN Outputs": {"channel_type": ChannelType.CAN_TX},
            }
        },
        "Functions": {
            "subfolders": {
                "Logic": {"channel_type": ChannelType.LOGIC},
                "Math": {"channel_type": ChannelType.NUMBER},
                "Filters": {"channel_type": ChannelType.FILTER},
                "PID Controllers": {"channel_type": ChannelType.PID},
            }
        },
        "Tables": {
            "subfolders": {
                "2D Tables": {"channel_type": ChannelType.TABLE_2D},
                "3D Tables": {"channel_type": ChannelType.TABLE_3D},
            }
        },
        "State": {
            "subfolders": {
                "Switches": {"channel_type": ChannelType.SWITCH},
                "Timers": {"channel_type": ChannelType.TIMER},
            }
        },
        "Scripts": {
            "subfolders": {
                "Lua Scripts": {"channel_type": ChannelType.LUA_SCRIPT},
            }
        },
        "Handlers": {
            "subfolders": {
                "Event Handlers": {"channel_type": ChannelType.HANDLER},
            }
        },
        "Peripherals": {
            "subfolders": {
                "CAN Keypads": {"channel_type": ChannelType.BLINKMARINE_KEYPAD},
            }
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._init_ui()
        self._create_folder_structure()

        # Store folder references by channel type
        self.channel_type_folders: Dict[ChannelType, QTreeWidgetItem] = {}
        self._map_folders_to_channel_types()

        # Cache for status icons
        self._icon_cache: Dict[str, QIcon] = {}

        # Initial button states
        self._update_button_states()

    def _create_status_icon(self, color: str, shape: str = "circle") -> QIcon:
        """Create a colored status icon.

        Args:
            color: Hex color string
            shape: 'circle', 'square', or 'triangle'
        """
        cache_key = f"{color}_{shape}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        size = 12
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)

        if shape == "circle":
            painter.drawEllipse(1, 1, size - 2, size - 2)
        elif shape == "square":
            painter.drawRect(2, 2, size - 4, size - 4)
        elif shape == "triangle":
            from PyQt6.QtGui import QPolygon
            from PyQt6.QtCore import QPoint
            points = [QPoint(size // 2, 1), QPoint(size - 1, size - 1), QPoint(1, size - 1)]
            painter.drawPolygon(QPolygon(points))

        painter.end()

        icon = QIcon(pixmap)
        self._icon_cache[cache_key] = icon
        return icon

    def _get_channel_status_color(self, channel_type: ChannelType, data: Dict[str, Any]) -> str:
        """Get status color for channel based on type and state."""

        # Map channel type to color category
        type_color_map = {
            ChannelType.DIGITAL_INPUT: "input",
            ChannelType.ANALOG_INPUT: "input",
            ChannelType.CAN_RX: "can",
            ChannelType.POWER_OUTPUT: "output",
            ChannelType.HBRIDGE: "output",
            ChannelType.CAN_TX: "can",
            ChannelType.LOGIC: "logic",
            ChannelType.NUMBER: "logic",
            ChannelType.FILTER: "logic",
            ChannelType.PID: "logic",
            ChannelType.TABLE_2D: "table",
            ChannelType.TABLE_3D: "table",
            ChannelType.SWITCH: "logic",
            ChannelType.TIMER: "timer",
            ChannelType.LUA_SCRIPT: "script",
            ChannelType.BLINKMARINE_KEYPAD: "peripheral",
            ChannelType.HANDLER: "handler",
        }

        color_key = type_color_map.get(channel_type, "enabled")
        return self.STATUS_COLORS.get(color_key, self.STATUS_COLORS["enabled"])

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Tree widget with 3 columns: Name, Details, Source
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Name", "Details", "Source"])
        self.tree.setColumnWidth(0, 180)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 150)
        self.tree.header().setStretchLastSection(True)
        self.tree.setIconSize(QSize(14, 14))
        self.tree.setIndentation(16)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

        # Dark theme styling (matching monitors - pure black background, consistent selection)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #000000;
                color: #ffffff;
                gridline-color: #333333;
            }
            QTreeWidget::item {
                background-color: #000000;
                color: #ffffff;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QTreeWidget::branch {
                background-color: #000000;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #333333;
            }
        """)

        layout.addWidget(self.tree)

        # Buttons panel
        button_layout = QVBoxLayout()
        button_layout.setSpacing(2)

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_item)
        button_layout.addWidget(self.add_btn)

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self._duplicate_item)
        button_layout.addWidget(self.duplicate_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_item)
        button_layout.addWidget(self.delete_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_item)
        button_layout.addWidget(self.edit_btn)

        button_layout.addStretch()

        # Main horizontal layout
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.tree, stretch=1)
        h_layout.addLayout(button_layout)

        layout.addLayout(h_layout)

    def _create_folder_structure(self):
        """Create hierarchical folder structure."""
        self.folder_items: Dict[str, QTreeWidgetItem] = {}

        # Bold font for root folders
        bold_font = QFont()
        bold_font.setBold(True)

        # Italic font for subfolders
        italic_font = QFont()
        italic_font.setItalic(True)

        for folder_name, folder_info in self.FOLDER_STRUCTURE.items():
            # Create main folder with 3 columns
            main_folder = QTreeWidgetItem(self.tree, [folder_name, "", ""])
            main_folder.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "folder",
                "folder_name": folder_name
            })
            main_folder.setFont(0, bold_font)
            main_folder.setExpanded(True)

            self.folder_items[folder_name] = main_folder

            # Create subfolders
            for subfolder_name, subfolder_info in folder_info.get("subfolders", {}).items():
                subfolder = QTreeWidgetItem(main_folder, [subfolder_name, "", ""])
                subfolder.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "folder",
                    "folder_name": subfolder_name,
                    "channel_type": subfolder_info.get("channel_type")
                })
                subfolder.setFont(0, italic_font)
                subfolder.setExpanded(False)

                # Store reference
                key = f"{folder_name}/{subfolder_name}"
                self.folder_items[key] = subfolder

    def _map_folders_to_channel_types(self):
        """Map folders to channel types for quick access."""
        for folder_name, folder_info in self.FOLDER_STRUCTURE.items():
            for subfolder_name, subfolder_info in folder_info.get("subfolders", {}).items():
                channel_type = subfolder_info.get("channel_type")
                if channel_type:
                    key = f"{folder_name}/{subfolder_name}"
                    self.channel_type_folders[channel_type] = self.folder_items.get(key)

    def _get_folder_for_type(self, channel_type: ChannelType) -> Optional[QTreeWidgetItem]:
        """Get folder item for channel type."""
        return self.channel_type_folders.get(channel_type)

    def _on_selection_changed(self):
        """Handle selection change."""
        self._update_button_states()

        items = self.tree.selectedItems()
        if items:
            item = items[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                item_type = data.get("type", "")
                if item_type == "channel":
                    channel_type = data.get("channel_type")
                    if channel_type:
                        self.item_selected.emit(channel_type.value, data)

    def _update_button_states(self):
        """Update button enabled states based on selection."""
        items = self.tree.selectedItems()

        # Default: all buttons disabled
        can_add = False
        can_edit = False
        can_delete = False
        can_duplicate = False

        if items:
            item = items[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                item_type = data.get("type", "")

                if item_type == "folder":
                    # Folder with channel_type selected - can add
                    channel_type = data.get("channel_type")
                    if channel_type:
                        can_add = True

                elif item_type == "channel":
                    # Channel selected - can edit, delete, duplicate
                    can_edit = True
                    can_delete = True
                    can_duplicate = True
                    # Can also add to parent folder
                    parent = item.parent()
                    if parent:
                        parent_data = parent.data(0, Qt.ItemDataRole.UserRole)
                        if parent_data and parent_data.get("channel_type"):
                            can_add = True

        self.add_btn.setEnabled(can_add)
        self.edit_btn.setEnabled(can_edit)
        self.delete_btn.setEnabled(can_delete)
        self.duplicate_btn.setEnabled(can_duplicate)

    def _on_item_double_clicked(self, item, column):
        """Handle double click - edit item directly (not via selection)."""
        if item is None:
            logger.debug("Double-click: item is None")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            logger.debug("Double-click: no data on item")
            return

        if data.get("type") == "channel":
            channel_type = data.get("channel_type")
            if channel_type:
                logger.info(f"Double-click edit: {channel_type.value} - {data.get('data', {}).get('id', 'unnamed')}")
                # Emit signal directly with item data (bypass selectedItems)
                self.item_edited.emit(channel_type.value, data)
            else:
                logger.warning("Double-click: channel has no type")
        else:
            logger.debug(f"Double-click on non-channel: {data.get('type')}")

    def _show_context_menu(self, position):
        """Show context menu."""
        item = self.tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if data.get("type") == "folder":
            channel_type = data.get("channel_type")
            if channel_type:
                add_action = menu.addAction(f"Add {channel_type.value}")
                add_action.triggered.connect(self._add_item)
        else:
            edit_action = menu.addAction("Edit")
            edit_action.triggered.connect(self._edit_item)

            duplicate_action = menu.addAction("Duplicate")
            duplicate_action.triggered.connect(self._duplicate_item)

            # Show what depends on this channel (for logic functions and similar)
            ch_type = data.get("channel_type")
            if ch_type and ch_type.value in ("logic", "number", "timer", "filter", "switch", "table_2d", "table_3d", "pid", "enum"):
                menu.addSeparator()
                dependents_action = menu.addAction("Show Dependents")
                dependents_action.triggered.connect(lambda checked=False, d=data: self._show_dependents(d))

            menu.addSeparator()

            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(self._delete_item)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _add_item(self):
        """Add new item."""
        items = self.tree.selectedItems()
        if not items:
            return

        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        # Get channel type from folder or parent
        channel_type = None
        if data.get("type") == "folder":
            channel_type = data.get("channel_type")
        else:
            parent_item = item.parent()
            if parent_item:
                parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
                channel_type = parent_data.get("channel_type")

        if channel_type:
            self.item_added.emit(channel_type.value)

    def _duplicate_item(self):
        """Duplicate selected item."""
        items = self.tree.selectedItems()
        if not items:
            return

        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get("type") == "channel":
            parent = item.parent()
            if parent:
                import copy
                from ui.dialogs.base_channel_dialog import get_next_channel_id
                new_data = copy.deepcopy(data)

                # Generate new channel_id and update name
                channel_data = new_data.get("data", {})
                channel_type = new_data.get("channel_type")
                all_channels = self.get_all_channels()
                channel_data["channel_id"] = get_next_channel_id(all_channels)
                old_name = channel_data.get("channel_name", "") or channel_data.get("name", "") or channel_data.get("id", "")
                channel_data["channel_name"] = f"{old_name} (Copy)"
                channel_data["name"] = f"{old_name} (Copy)"
                # Remove old 'id' field if present (use channel_id instead)
                channel_data.pop("id", None)

                # Display just the name (channel_id shown in dialog)
                display_text = channel_data['name']

                # Add new item with all 3 columns
                new_item = QTreeWidgetItem(parent)
                new_item.setText(0, display_text)
                new_item.setText(1, format_channel_details(channel_type, channel_data))
                new_item.setText(2, format_channel_source(channel_type, channel_data))

                # Add status icon
                status_color = self._get_channel_status_color(channel_type, channel_data)
                new_item.setIcon(0, self._create_status_icon(status_color))

                # Add tooltip
                tooltip = format_channel_tooltip(channel_type, channel_data)
                new_item.setToolTip(0, tooltip)
                new_item.setToolTip(1, tooltip)
                new_item.setToolTip(2, tooltip)

                new_item.setData(0, Qt.ItemDataRole.UserRole, new_data)

                self.configuration_changed.emit()

    def _delete_item(self):
        """Delete selected item."""
        items = self.tree.selectedItems()
        if not items:
            return

        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get("type") == "channel":
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete '{item.text(0)}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                    channel_type = data.get("channel_type")
                    if channel_type:
                        self.item_deleted.emit(channel_type.value, data)
                    self.configuration_changed.emit()

    def _edit_item(self):
        """Edit selected item (from Edit button)."""
        items = self.tree.selectedItems()
        if not items:
            logger.debug("Edit button: no items selected")
            return

        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get("type") == "channel":
            channel_type = data.get("channel_type")
            if channel_type:
                logger.info(f"Edit button: {channel_type.value} - {data.get('data', {}).get('id', 'unnamed')}")
                self.item_edited.emit(channel_type.value, data)
            else:
                logger.warning("Edit button: channel has no type")
        else:
            logger.debug(f"Edit button: item is not a channel")

    def _show_dependents(self, data: Dict[str, Any]):
        """Show channels that depend on this channel."""
        if not data:
            return

        channel_data = data.get("data", {})
        channel_type = data.get("channel_type")

        # Get channel name for signal
        channel_name = channel_data.get("channel_name", "") or channel_data.get("name", "") or channel_data.get("id", "")

        if channel_type and channel_name:
            self.show_dependents_requested.emit(channel_type.value, channel_name)

    # ========== Add channel methods ==========

    def clear_all(self):
        """Clear all channels from the tree (keep folder structure)."""
        for channel_type, folder in self.channel_type_folders.items():
            # Remove all children (channels) but keep the folder
            while folder.childCount() > 0:
                folder.removeChild(folder.child(0))

    def add_channel(self, channel_type: ChannelType, channel_data: Dict[str, Any], emit_signal: bool = True) -> Optional[QTreeWidgetItem]:
        """Add a channel to the appropriate folder.

        Args:
            channel_type: Type of channel to add
            channel_data: Channel configuration data
            emit_signal: Whether to emit configuration_changed signal (default True)
        """
        folder = self._get_folder_for_type(channel_type)
        if not folder:
            return None

        item = QTreeWidgetItem(folder)
        # Use 'channel_name' field for display, fallback to 'name' then 'id' for backwards compatibility
        channel_name = channel_data.get("channel_name", "") or channel_data.get("name", "") or channel_data.get("id", "") or "unnamed"
        channel_id = channel_data.get("channel_id", "")

        # Display just the name (channel_id shown in dialog when editing)
        item.setText(0, channel_name)
        item.setText(1, format_channel_details(channel_type, channel_data))
        item.setText(2, format_channel_source(channel_type, channel_data))

        # Add status icon
        status_color = self._get_channel_status_color(channel_type, channel_data)
        item.setIcon(0, self._create_status_icon(status_color))

        # Add tooltip with full details
        tooltip = format_channel_tooltip(channel_type, channel_data)
        item.setToolTip(0, tooltip)
        item.setToolTip(1, tooltip)
        item.setToolTip(2, tooltip)

        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "channel",
            "channel_type": channel_type,
            "data": channel_data
        })

        folder.setExpanded(True)

        # Emit configuration changed signal (unless suppressed for bulk loading)
        if emit_signal:
            self.configuration_changed.emit()

        return item

    # ========== Legacy add methods (for compatibility) ==========

    def add_output(self, output_data: Dict[str, Any]):
        """Add output to tree (legacy)."""
        self.add_channel(ChannelType.POWER_OUTPUT, output_data)

    def add_input(self, input_data: Dict[str, Any]):
        """Add input to tree (legacy)."""
        input_type = input_data.get("type", "analog")
        if input_type == "digital":
            self.add_channel(ChannelType.DIGITAL_INPUT, input_data)
        else:
            self.add_channel(ChannelType.ANALOG_INPUT, input_data)

    def add_logic_function(self, logic_data: Dict[str, Any]):
        """Add logic function to tree (legacy)."""
        self.add_channel(ChannelType.LOGIC, logic_data)

    def add_number(self, number_data: Dict[str, Any]):
        """Add number to tree (legacy)."""
        self.add_channel(ChannelType.NUMBER, number_data)

    def add_switch(self, switch_data: Dict[str, Any]):
        """Add switch to tree (legacy)."""
        self.add_channel(ChannelType.SWITCH, switch_data)

    def add_table(self, table_data: Dict[str, Any]):
        """Add table to tree (legacy)."""
        self.add_channel(ChannelType.TABLE_2D, table_data)

    def add_timer(self, timer_data: Dict[str, Any]):
        """Add timer to tree (legacy)."""
        self.add_channel(ChannelType.TIMER, timer_data)

    def add_can_message(self, can_data: Dict[str, Any]):
        """Add CAN message to tree (legacy)."""
        direction = can_data.get("direction", "rx")
        if direction == "tx":
            self.add_channel(ChannelType.CAN_TX, can_data)
        else:
            self.add_channel(ChannelType.CAN_RX, can_data)

    def add_hbridge(self, hbridge_data: Dict[str, Any]):
        """Add H-Bridge motor to tree."""
        self.add_channel(ChannelType.HBRIDGE, hbridge_data)

    def add_pid_controller(self, pid_data: Dict[str, Any]):
        """Add PID controller to tree."""
        self.add_channel(ChannelType.PID, pid_data)

    def add_lua_script(self, lua_data: Dict[str, Any]):
        """Add LUA script to tree."""
        self.add_channel(ChannelType.LUA_SCRIPT, lua_data)

    def add_blinkmarine_keypad(self, keypad_data: Dict[str, Any]):
        """Add BlinkMarine CAN keypad to tree."""
        self.add_channel(ChannelType.BLINKMARINE_KEYPAD, keypad_data)

    # ========== Update and get methods ==========

    def update_current_item(self, new_data: Dict[str, Any]) -> bool:
        """Update currently selected item with new data."""
        items = self.tree.selectedItems()
        if not items:
            return False

        item = items[0]
        old_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not old_data or old_data.get("type") != "channel":
            return False

        channel_type = old_data.get("channel_type")
        if not channel_type:
            return False

        # Update display - use 'channel_name' field, fallback to 'name' then 'id' for backwards compatibility
        channel_name = new_data.get("channel_name", "") or new_data.get("name", "") or new_data.get("id", "") or "unnamed"
        channel_id = new_data.get("channel_id", "")

        # Display just the name (channel_id shown in dialog when editing)
        item.setText(0, channel_name)
        item.setText(1, format_channel_details(channel_type, new_data))
        item.setText(2, format_channel_source(channel_type, new_data))

        # Update status icon
        status_color = self._get_channel_status_color(channel_type, new_data)
        item.setIcon(0, self._create_status_icon(status_color))

        # Update tooltip
        tooltip = format_channel_tooltip(channel_type, new_data)
        item.setToolTip(0, tooltip)
        item.setToolTip(1, tooltip)
        item.setToolTip(2, tooltip)

        # Update stored data
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "channel",
            "channel_type": channel_type,
            "data": new_data
        })

        self.configuration_changed.emit()
        return True

    def get_channels_by_type(self, channel_type: ChannelType) -> List[Dict[str, Any]]:
        """Get all channels of specified type with channel_type field included."""
        channels = []
        folder = self._get_folder_for_type(channel_type)
        if folder:
            for i in range(folder.childCount()):
                child = folder.child(i)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("type") == "channel":
                    channel_data = data.get("data", {}).copy()
                    # Ensure channel_type is included in the channel data
                    channel_data["channel_type"] = channel_type.value
                    channels.append(channel_data)
        return channels

    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Get all channels from all folders."""
        channels = []
        for channel_type in ChannelType:
            channels.extend(self.get_channels_by_type(channel_type))
        return channels

    def find_channel_item(self, channel_id_or_name: str) -> Optional[QTreeWidgetItem]:
        """Find tree item by channel ID or name."""
        for folder in self.folder_items.values():
            for i in range(folder.childCount()):
                item = folder.child(i)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, dict):
                    channel_data = data.get("data", data)
                    # Check id, name, and channel_name for compatibility
                    item_id = channel_data.get("id", "")
                    item_name = channel_data.get("name", "") or channel_data.get("channel_name", "")
                    if item_id == channel_id_or_name or item_name == channel_id_or_name:
                        return item
        return None

    def find_channel_item_by_name(self, name: str) -> Optional[QTreeWidgetItem]:
        """Find tree item by channel name."""
        for folder in self.folder_items.values():
            for i in range(folder.childCount()):
                item = folder.child(i)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, dict):
                    channel_data = data.get("data", data)
                    # Check both name and channel_name for compatibility
                    item_name = channel_data.get("name", "") or channel_data.get("channel_name", "")
                    if item_name == name:
                        return item
        return None

    def update_channel_by_id(self, channel_id: str, new_data: Dict[str, Any]) -> bool:
        """Update a channel by its ID."""
        item = self.find_channel_item(channel_id)
        if not item:
            return False

        old_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not old_data or old_data.get("type") != "channel":
            return False

        channel_type = old_data.get("channel_type")
        if not channel_type:
            return False

        # Update display
        channel_name = new_data.get("channel_name", "") or new_data.get("name", "") or new_data.get("id", "") or "unnamed"
        ch_id = new_data.get("channel_id", "")

        if ch_id:
            display_text = f"{channel_name} [#{ch_id}]"
        else:
            display_text = channel_name

        item.setText(0, display_text)
        item.setText(1, format_channel_details(channel_type, new_data))
        item.setText(2, format_channel_source(channel_type, new_data))

        # Update status icon
        status_color = self._get_channel_status_color(channel_type, new_data)
        item.setIcon(0, self._create_status_icon(status_color))

        # Update tooltip
        tooltip = format_channel_tooltip(channel_type, new_data)
        item.setToolTip(0, tooltip)
        item.setToolTip(1, tooltip)
        item.setToolTip(2, tooltip)

        # Update stored data
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "channel",
            "channel_type": channel_type,
            "data": new_data
        })

        self.configuration_changed.emit()
        return True

    def remove_channel_by_id(self, channel_id: str, emit_signal: bool = True) -> bool:
        """Remove a channel by its ID.

        Args:
            channel_id: ID of the channel to remove
            emit_signal: Whether to emit configuration_changed signal (default True)
        """
        item = self.find_channel_item(channel_id)
        if not item:
            return False

        parent = item.parent()
        if parent:
            parent.removeChild(item)
            if emit_signal:
                self.configuration_changed.emit()
            return True
        return False

    def update_channel_by_name(self, channel_name: str, new_data: Dict[str, Any], emit_signal: bool = True) -> bool:
        """Update a channel by its name.

        Args:
            channel_name: Name of the channel to update
            new_data: New channel configuration data
            emit_signal: Whether to emit configuration_changed signal (default True)
        """
        item = self.find_channel_item_by_name(channel_name)
        if not item:
            return False

        old_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not old_data or old_data.get("type") != "channel":
            return False

        channel_type = old_data.get("channel_type")
        if not channel_type:
            return False

        # Update display
        display_name = new_data.get("channel_name", "") or new_data.get("name", "") or new_data.get("id", "") or "unnamed"
        ch_id = new_data.get("channel_id", "")

        if ch_id:
            display_text = f"{display_name} [#{ch_id}]"
        else:
            display_text = display_name

        item.setText(0, display_text)
        item.setText(1, format_channel_details(channel_type, new_data))
        item.setText(2, format_channel_source(channel_type, new_data))

        # Update status icon
        status_color = self._get_channel_status_color(channel_type, new_data)
        item.setIcon(0, self._create_status_icon(status_color))

        # Update tooltip
        tooltip = format_channel_tooltip(channel_type, new_data)
        item.setToolTip(0, tooltip)
        item.setToolTip(1, tooltip)
        item.setToolTip(2, tooltip)

        # Update stored data
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "channel",
            "channel_type": channel_type,
            "data": new_data
        })

        if emit_signal:
            self.configuration_changed.emit()
        return True

    def remove_channel_by_name(self, channel_name: str, emit_signal: bool = True) -> bool:
        """Remove a channel by its name.

        Args:
            channel_name: Name of the channel to remove
            emit_signal: Whether to emit configuration_changed signal (default True)
        """
        item = self.find_channel_item_by_name(channel_name)
        if not item:
            return False

        parent = item.parent()
        if parent:
            parent.removeChild(item)
            if emit_signal:
                self.configuration_changed.emit()
            return True
        return False

    # ========== Legacy get methods ==========

    def get_all_outputs(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.POWER_OUTPUT)

    def get_all_inputs(self) -> List[Dict[str, Any]]:
        return (self.get_channels_by_type(ChannelType.DIGITAL_INPUT) +
                self.get_channels_by_type(ChannelType.ANALOG_INPUT))

    def get_all_logic_functions(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.LOGIC)

    def get_all_numbers(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.NUMBER)

    def get_all_switches(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.SWITCH)

    def get_all_tables(self) -> List[Dict[str, Any]]:
        return (self.get_channels_by_type(ChannelType.TABLE_2D) +
                self.get_channels_by_type(ChannelType.TABLE_3D))

    def get_all_timers(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.TIMER)

    def get_all_hbridges(self) -> List[Dict[str, Any]]:
        """Get all H-Bridge motor channels."""
        return self.get_channels_by_type(ChannelType.HBRIDGE)

    def get_all_pid_controllers(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.PID)

    def get_all_lua_scripts(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.LUA_SCRIPT)

    def get_all_blinkmarine_keypads(self) -> List[Dict[str, Any]]:
        """Get all BlinkMarine CAN keypads."""
        return self.get_channels_by_type(ChannelType.BLINKMARINE_KEYPAD)

    def get_all_used_output_pins(self, exclude_channel_id: str = None) -> List[int]:
        """Get all output pins currently in use by power outputs.

        Args:
            exclude_channel_id: Optional channel name to exclude (for editing existing channel)

        Returns:
            List of used output pin numbers (0-29)
        """
        used_pins = []
        for output in self.get_all_outputs():
            # Skip the channel being edited (check 'channel_name' first for consistency)
            channel_name = output.get('channel_name', '') or output.get('name', '') or output.get('id', '')
            if exclude_channel_id and channel_name == exclude_channel_id:
                continue
            # Collect all pins from this output (can have 1-3 pins)
            pins = output.get('pins', [])
            if isinstance(pins, list):
                used_pins.extend(pins)
            elif isinstance(pins, int):
                used_pins.append(pins)
            # Also check legacy 'channel' field
            channel = output.get('channel')
            if channel is not None and channel not in used_pins:
                used_pins.append(channel)
        return used_pins

    def get_all_used_analog_input_pins(self, exclude_channel_id: str = None) -> List[int]:
        """Get all analog input pins currently in use.

        Args:
            exclude_channel_id: Optional channel name to exclude (for editing existing channel)

        Returns:
            List of used analog input pin numbers (0-19)
        """
        used_pins = []
        for inp in self.get_channels_by_type(ChannelType.ANALOG_INPUT):
            # Check 'channel_name' first for consistency
            channel_name = inp.get('channel_name', '') or inp.get('name', '') or inp.get('id', '')
            if exclude_channel_id and channel_name == exclude_channel_id:
                continue
            # Pin is stored in 'input_pin' field
            pin = inp.get('input_pin')
            if pin is not None:
                used_pins.append(pin)
        return used_pins

    def get_all_used_digital_input_pins(self, exclude_channel_id: str = None) -> List[int]:
        """Get all digital input pins currently in use.

        Args:
            exclude_channel_id: Optional channel name to exclude (for editing existing channel)

        Returns:
            List of used digital input pin numbers
        """
        used_pins = []
        for inp in self.get_channels_by_type(ChannelType.DIGITAL_INPUT):
            # Check 'channel_name' first for consistency
            channel_name = inp.get('channel_name', '') or inp.get('name', '') or inp.get('id', '')
            if exclude_channel_id and channel_name == exclude_channel_id:
                continue
            # Pin is stored in 'input_pin' field
            pin = inp.get('input_pin')
            if pin is not None:
                used_pins.append(pin)
        return used_pins

    def get_all_used_hbridge_numbers(self, exclude_channel_id: str = None) -> List[int]:
        """Get all H-Bridge numbers currently in use.

        Args:
            exclude_channel_id: Optional channel name to exclude (for editing existing channel)

        Returns:
            List of used H-Bridge numbers (0-3)
        """
        used_bridges = []
        for hb in self.get_channels_by_type(ChannelType.HBRIDGE):
            # Check 'channel_name' first for consistency
            channel_name = hb.get('channel_name', '') or hb.get('name', '') or hb.get('id', '')
            if exclude_channel_id and channel_name == exclude_channel_id:
                continue
            bridge = hb.get('bridge_number')
            if bridge is not None:
                used_bridges.append(bridge)
        return used_bridges

    def clear_all(self):
        """Clear all channels from tree (keep folder structure)."""
        for channel_type in ChannelType:
            folder = self._get_folder_for_type(channel_type)
            if folder:
                while folder.childCount() > 0:
                    folder.removeChild(folder.child(0))

    def load_channels(self, channels: List[Dict[str, Any]]):
        """Load channels from configuration."""
        self.clear_all()

        for channel in channels:
            channel_type_str = channel.get("channel_type", "")
            try:
                channel_type = ChannelType(channel_type_str)
                self.add_channel(channel_type, channel, emit_signal=False)
            except ValueError:
                continue

        # Auto-collapse folders with many children
        self._auto_collapse_large_folders()
        # Note: Don't emit configuration_changed here - loading is not a modification

    def _auto_collapse_large_folders(self, threshold: int = 10):
        """Collapse subfolders that have more than threshold children.

        Only collapses subfolders with channel items - does not auto-expand.
        Top-level category folders are always expanded.
        """
        # Process all top-level items (main category folders)
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            if not top_item:
                continue

            # Always expand top-level categories
            top_item.setExpanded(True)

            # Process subfolders (channel type folders)
            for j in range(top_item.childCount()):
                subfolder = top_item.child(j)
                if not subfolder:
                    continue

                child_count = subfolder.childCount()

                # Collapse folders with many children
                if child_count > threshold:
                    subfolder.setExpanded(False)
                elif child_count > 0:
                    # Expand folders that have content but not too many
                    subfolder.setExpanded(True)
                # Empty folders stay collapsed (default state)

"""
Project Tree Widget
Hierarchical tree view of all channels (unified architecture)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont
from typing import Dict, Any, Optional, List

from models.channel import ChannelType, CHANNEL_PREFIX_MAP


class ProjectTree(QWidget):
    """Project tree with unified channel architecture."""

    # Signals
    item_selected = pyqtSignal(str, object)  # (channel_type, item_data)
    item_added = pyqtSignal(str)  # channel_type
    item_edited = pyqtSignal(str, object)  # (channel_type, item_data)
    item_deleted = pyqtSignal(str, object)  # (channel_type, item_data)
    configuration_changed = pyqtSignal()

    # Folder structure with channel types
    FOLDER_STRUCTURE = {
        "Inputs": {
            "subfolders": {
                "Digital Inputs": {"channel_type": ChannelType.DIGITAL_INPUT},
                "Analog Inputs": {"channel_type": ChannelType.ANALOG_INPUT},
                "CAN RX": {"channel_type": ChannelType.CAN_RX},
            }
        },
        "Outputs": {
            "subfolders": {
                "Power Outputs": {"channel_type": ChannelType.POWER_OUTPUT},
                "CAN TX": {"channel_type": ChannelType.CAN_TX},
            }
        },
        "Functions": {
            "subfolders": {
                "Logic": {"channel_type": ChannelType.LOGIC},
                "Math": {"channel_type": ChannelType.NUMBER},
                "Filters": {"channel_type": ChannelType.FILTER},
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
        "Data": {
            "subfolders": {
                "Enumerations": {"channel_type": ChannelType.ENUM},
            }
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._create_folder_structure()

        # Store folder references by channel type
        self.channel_type_folders: Dict[ChannelType, QTreeWidgetItem] = {}
        self._map_folders_to_channel_types()

        # Initial button states
        self._update_button_states()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Name")
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Name", "Details"])
        self.tree.setColumnWidth(0, 200)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
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

        for folder_name, folder_info in self.FOLDER_STRUCTURE.items():
            # Create main folder
            main_folder = QTreeWidgetItem(self.tree, [folder_name, ""])
            main_folder.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "folder",
                "folder_name": folder_name
            })
            main_folder.setFont(0, bold_font)
            main_folder.setExpanded(True)

            self.folder_items[folder_name] = main_folder

            # Create subfolders
            for subfolder_name, subfolder_info in folder_info.get("subfolders", {}).items():
                subfolder = QTreeWidgetItem(main_folder, [subfolder_name, ""])
                subfolder.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "folder",
                    "folder_name": subfolder_name,
                    "channel_type": subfolder_info.get("channel_type")
                })
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
        """Handle double click - edit item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "channel":
            self._edit_item()

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
                new_data = copy.deepcopy(data)

                # Update ID
                channel_data = new_data.get("data", {})
                old_id = channel_data.get("id", "")
                channel_data["id"] = f"{old_id}_copy"
                channel_data["name"] = channel_data.get("name", "") + " (Copy)"

                # Add new item
                new_item = QTreeWidgetItem(parent)
                new_item.setText(0, channel_data.get("id", "Copy"))
                new_item.setText(1, item.text(1))
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
        """Edit selected item."""
        items = self.tree.selectedItems()
        if not items:
            return

        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get("type") == "channel":
            channel_type = data.get("channel_type")
            if channel_type:
                self.item_edited.emit(channel_type.value, data)

    # ========== Add channel methods ==========

    def add_channel(self, channel_type: ChannelType, channel_data: Dict[str, Any]) -> Optional[QTreeWidgetItem]:
        """Add a channel to the appropriate folder."""
        folder = self._get_folder_for_type(channel_type)
        if not folder:
            return None

        item = QTreeWidgetItem(folder)
        prefix = CHANNEL_PREFIX_MAP.get(channel_type, "")
        channel_id = channel_data.get("id", "unnamed")

        # Add prefix if not present
        if prefix and not channel_id.startswith(prefix):
            display_id = f"{prefix}{channel_id}"
        else:
            display_id = channel_id

        item.setText(0, display_id)
        item.setText(1, self._get_channel_details(channel_type, channel_data))

        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "channel",
            "channel_type": channel_type,
            "data": channel_data
        })

        folder.setExpanded(True)
        return item

    def _get_channel_details(self, channel_type: ChannelType, data: Dict[str, Any]) -> str:
        """Get display details string for channel."""
        if channel_type == ChannelType.DIGITAL_INPUT:
            subtype = data.get("subtype", "switch")
            return subtype.replace("_", " ").title()

        elif channel_type == ChannelType.ANALOG_INPUT:
            return f"A{data.get('input_pin', 0)}"

        elif channel_type == ChannelType.POWER_OUTPUT:
            return f"Ch{data.get('channel', 0)}"

        elif channel_type == ChannelType.LOGIC:
            op = data.get("operation", "and").upper()
            delay_on = data.get("delay_on_ms", 0)
            delay_off = data.get("delay_off_ms", 0)
            if delay_on or delay_off:
                return f"{op} (+{delay_on}/-{delay_off}ms)"
            return op

        elif channel_type == ChannelType.NUMBER:
            op = data.get("operation", "constant")
            if op == "constant":
                val = data.get("constant_value", 0)
                unit = data.get("unit", "")
                return f"{val} {unit}".strip()
            return op

        elif channel_type == ChannelType.TIMER:
            mode = data.get("mode", "count_up")
            h = data.get("limit_hours", 0)
            m = data.get("limit_minutes", 0)
            s = data.get("limit_seconds", 0)
            return f"{mode} ({h}:{m:02d}:{s:02d})"

        elif channel_type == ChannelType.SWITCH:
            states = data.get("states", [])
            return f"{len(states)} states"

        elif channel_type == ChannelType.TABLE_2D or channel_type == ChannelType.TABLE_3D:
            points = data.get("table_data", [])
            return f"{len(points)} points"

        elif channel_type == ChannelType.ENUM:
            items = data.get("items", [])
            return f"{len(items)} items"

        elif channel_type == ChannelType.CAN_RX or channel_type == ChannelType.CAN_TX:
            msg_id = data.get("message_id", 0)
            return f"ID: 0x{msg_id:X}"

        elif channel_type == ChannelType.FILTER:
            filter_type = data.get("filter_type", "moving_avg")
            return filter_type.replace("_", " ").title()

        return ""

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

    def add_enum(self, enum_data: Dict[str, Any]):
        """Add enum to tree."""
        self.add_channel(ChannelType.ENUM, enum_data)

    def add_can_message(self, can_data: Dict[str, Any]):
        """Add CAN message to tree (legacy)."""
        direction = can_data.get("direction", "rx")
        if direction == "tx":
            self.add_channel(ChannelType.CAN_TX, can_data)
        else:
            self.add_channel(ChannelType.CAN_RX, can_data)

    def add_hbridge(self, hbridge_data: Dict[str, Any]):
        """Add H-Bridge to tree (legacy - maps to power output)."""
        self.add_channel(ChannelType.POWER_OUTPUT, hbridge_data)

    def add_pid_controller(self, pid_data: Dict[str, Any]):
        """Add PID controller to tree (legacy - maps to number)."""
        self.add_channel(ChannelType.NUMBER, pid_data)

    def add_lua_script(self, lua_data: Dict[str, Any]):
        """Add LUA script to tree (legacy - not in new architecture)."""
        pass  # LUA scripts are not part of channel architecture

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

        # Update display
        prefix = CHANNEL_PREFIX_MAP.get(channel_type, "")
        channel_id = new_data.get("id", "unnamed")

        if prefix and not channel_id.startswith(prefix):
            display_id = f"{prefix}{channel_id}"
        else:
            display_id = channel_id

        item.setText(0, display_id)
        item.setText(1, self._get_channel_details(channel_type, new_data))

        # Update stored data
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "channel",
            "channel_type": channel_type,
            "data": new_data
        })

        self.configuration_changed.emit()
        return True

    def get_channels_by_type(self, channel_type: ChannelType) -> List[Dict[str, Any]]:
        """Get all channels of specified type."""
        channels = []
        folder = self._get_folder_for_type(channel_type)
        if folder:
            for i in range(folder.childCount()):
                child = folder.child(i)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("type") == "channel":
                    channels.append(data.get("data", {}))
        return channels

    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Get all channels from all folders."""
        channels = []
        for channel_type in ChannelType:
            channels.extend(self.get_channels_by_type(channel_type))
        return channels

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
        return []  # Mapped to power outputs

    def get_all_pid_controllers(self) -> List[Dict[str, Any]]:
        return []  # Mapped to numbers

    def get_all_lua_scripts(self) -> List[Dict[str, Any]]:
        return []  # Not in channel architecture

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
                self.add_channel(channel_type, channel)
            except ValueError:
                continue

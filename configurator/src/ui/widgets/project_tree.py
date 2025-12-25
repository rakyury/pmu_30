"""
Project Tree Widget
Hierarchical tree view of all channels (unified architecture)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMenu, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPixmap, QPainter, QBrush
from typing import Dict, Any, Optional, List
import logging

from models.channel import ChannelType, CHANNEL_PREFIX_MAP

logger = logging.getLogger(__name__)


class ProjectTree(QWidget):
    """Project tree with unified channel architecture."""

    # Signals
    item_selected = pyqtSignal(str, object)  # (channel_type, item_data)
    item_added = pyqtSignal(str)  # channel_type
    item_edited = pyqtSignal(str, object)  # (channel_type, item_data)
    item_deleted = pyqtSignal(str, object)  # (channel_type, item_data)
    configuration_changed = pyqtSignal()

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
        "Data": {
            "subfolders": {
                "Enumerations": {"channel_type": ChannelType.ENUM},
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
        # Check enabled state first
        enabled = data.get("enabled", True)
        if not enabled:
            return self.STATUS_COLORS["disabled"]

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
            ChannelType.ENUM: "table",
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
                old_name = channel_data.get("name", channel_data.get("id", ""))
                channel_data["name"] = f"{old_name} (Copy)"
                # Remove old 'id' field if present (use channel_id instead)
                channel_data.pop("id", None)

                # Display format: "Name [#ID]"
                display_text = f"{channel_data['name']} [#{channel_data['channel_id']}]"

                # Add new item with all 3 columns
                new_item = QTreeWidgetItem(parent)
                new_item.setText(0, display_text)
                new_item.setText(1, self._get_channel_details(channel_type, channel_data))
                new_item.setText(2, self._get_channel_source(channel_type, channel_data))

                # Add status icon
                status_color = self._get_channel_status_color(channel_type, channel_data)
                new_item.setIcon(0, self._create_status_icon(status_color))

                # Add tooltip
                tooltip = self._get_channel_tooltip(channel_type, channel_data)
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
        # Use 'name' field for display (new system), fallback to 'id' for backwards compatibility
        channel_name = channel_data.get("name", channel_data.get("id", "unnamed"))
        channel_id = channel_data.get("channel_id", "")

        # Display format: "Name [#ID]" if channel_id exists
        if channel_id:
            display_text = f"{channel_name} [#{channel_id}]"
        else:
            display_text = channel_name

        item.setText(0, display_text)
        item.setText(1, self._get_channel_details(channel_type, channel_data))
        item.setText(2, self._get_channel_source(channel_type, channel_data))

        # Add status icon
        status_color = self._get_channel_status_color(channel_type, channel_data)
        item.setIcon(0, self._create_status_icon(status_color))

        # Add tooltip with full details
        tooltip = self._get_channel_tooltip(channel_type, channel_data)
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

    def _get_channel_details(self, channel_type: ChannelType, data: Dict[str, Any]) -> str:
        """Get display details string for channel."""
        if channel_type == ChannelType.DIGITAL_INPUT:
            subtype = data.get("subtype", "switch_active_low")

            # Special handling for keypad buttons (ECUMaster style)
            if subtype == "keypad_button":
                keypad_id = data.get("keypad_id", "")
                btn_idx = data.get("button_index", 0)
                btn_mode = data.get("button_mode", "momentary")
                mode_display = {
                    "momentary": "Momentary",
                    "toggle": "Toggle",
                    "latching": "Latching",
                    "direct": "Direct"
                }.get(btn_mode, btn_mode.title())
                return f"Keypad Button {btn_idx + 1} ({mode_display})"

            pin = data.get("input_pin", 0)
            # Format subtype nicely
            subtype_display = {
                "switch_active_low": "Switch Active Low",
                "switch_active_high": "Switch Active High",
                "frequency": "Frequency",
                "rpm": "RPM",
                "flex_fuel": "Flex Fuel",
                "beacon": "Beacon",
                "puls_oil_sensor": "PULS Oil"
            }.get(subtype, subtype.replace("_", " ").title())
            return f"D{pin + 1} {subtype_display}"

        elif channel_type == ChannelType.ANALOG_INPUT:
            pin = data.get("input_pin", 0)
            subtype = data.get("subtype", "linear")
            pullup = data.get("pullup_option", "1m_down")

            # Format subtype
            subtype_display = {
                "switch_active_low": "Switch Low",
                "switch_active_high": "Switch High",
                "rotary_switch": "Rotary",
                "linear": "Linear",
                "calibrated": "Calibrated"
            }.get(subtype, subtype)

            # Format pullup/pulldown
            pullup_display = ""
            if pullup and pullup != "none" and pullup != "1m_down":
                pullup_map = {
                    "10k_up": "10K↑",
                    "10k_down": "10K↓",
                    "100k_up": "100K↑",
                    "100k_down": "100K↓"
                }
                pullup_display = f" {pullup_map.get(pullup, '')}"

            return f"A{pin + 1} {subtype_display}{pullup_display}"

        elif channel_type == ChannelType.POWER_OUTPUT:
            parts = []

            # Pins
            pins = data.get('pins', [data.get('channel', 0)])
            if isinstance(pins, list) and pins:
                pins_str = ", ".join([f"O{p + 1}" for p in pins])
            else:
                pins_str = f"O{data.get('channel', 0) + 1}"
            parts.append(pins_str)

            # Current limit
            current_limit = data.get('current_limit_a', 0) or data.get('current_limit', 0)
            if current_limit:
                parts.append(f"{current_limit}A")

            # Retry count
            retry_count = data.get('retry_count', 0)
            if retry_count:
                parts.append(f"x{retry_count}")

            # Control source
            source_channel = data.get('source_channel')
            if source_channel:
                if isinstance(source_channel, int):
                    parts.append(f"Ch#{source_channel}")
                else:
                    parts.append(str(source_channel))
            elif data.get('enabled', False):
                parts.append("ON")

            # PWM indicator
            pwm_enabled = data.get('pwm_enabled', False) or data.get('pwm', {}).get('enabled', False)
            if pwm_enabled:
                freq = data.get('pwm_frequency_hz', 0) or data.get('pwm', {}).get('frequency', 0)
                duty = data.get('pwm', {}).get('duty_value', 100)
                parts.append(f"PWM {freq}Hz {duty}%")

            return " ".join(parts)

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
            auto_start = " [AUTO]" if data.get("auto_start", False) else ""
            return f"{mode} ({h}:{m:02d}:{s:02d}){auto_start}"

        elif channel_type == ChannelType.SWITCH:
            states = data.get("states", [])
            return f"{len(states)} states"

        elif channel_type == ChannelType.TABLE_2D or channel_type == ChannelType.TABLE_3D:
            points = data.get("table_data", [])
            return f"{len(points)} points"

        elif channel_type == ChannelType.ENUM:
            items = data.get("items", [])
            return f"{len(items)} items"

        elif channel_type == ChannelType.CAN_RX:
            # CAN Input - show message reference and format
            msg_ref = data.get("message_ref", "")
            data_format = data.get("data_format", "16bit")
            if hasattr(data_format, 'value'):
                data_format = data_format.value
            byte_order = data.get("byte_order", "little_endian")
            order_short = "LE" if byte_order == "little_endian" else "BE"
            format_short = {"8bit": "8", "16bit": "16", "32bit": "32", "custom": "C"}.get(data_format, "?")
            return f"{msg_ref} [{format_short}{order_short}]"

        elif channel_type == ChannelType.CAN_TX:
            msg_id = data.get("message_id", 0)
            can_bus = data.get("can_bus", 1)
            tx_mode = data.get("transmit_mode", "cycle")
            if tx_mode == "cycle":
                freq = data.get("frequency_hz", 10)
                return f"CAN{can_bus} 0x{msg_id:X} @ {freq}Hz"
            else:
                return f"CAN{can_bus} 0x{msg_id:X} (Triggered)"

        elif channel_type == ChannelType.FILTER:
            filter_type = data.get("filter_type", "moving_avg")
            return filter_type.replace("_", " ").title()

        elif channel_type == ChannelType.LUA_SCRIPT:
            trigger = data.get("trigger_type", "manual")
            enabled = data.get("enabled", True)
            status = "[ON]" if enabled else "[OFF]"
            return f"{trigger} {status}"

        elif channel_type == ChannelType.PID:
            kp = data.get("kp", 1.0)
            ki = data.get("ki", 0.0)
            kd = data.get("kd", 0.0)
            enabled = data.get("enabled", True)
            status = "[ON]" if enabled else "[OFF]"
            return f"P:{kp:.2f} I:{ki:.2f} D:{kd:.2f} {status}"

        elif channel_type == ChannelType.HBRIDGE:
            bridge = data.get("bridge_number", 0)
            mode = data.get("mode", "coast")
            if hasattr(mode, 'value'):
                mode = mode.value
            preset = data.get("motor_preset", "custom")
            if hasattr(preset, 'value'):
                preset = preset.value
            enabled = data.get("enabled", True)
            status = "[ON]" if enabled else "[OFF]"
            return f"HB{bridge + 1} {mode} ({preset}) {status}"

        elif channel_type == ChannelType.BLINKMARINE_KEYPAD:
            keypad_type = data.get("keypad_type", "2x6")
            rx_id = data.get("rx_base_id", 0x100)
            can_bus = data.get("can_bus", 1)
            button_count = 12 if keypad_type == "2x6" else 16
            return f"{keypad_type} ({button_count} btns) CAN{can_bus} RX:0x{rx_id:03X}"

        elif channel_type == ChannelType.HANDLER:
            event = data.get("event", "channel_on")
            action = data.get("action", "write_channel")
            enabled = data.get("enabled", True)
            status = "[ON]" if enabled else "[OFF]"
            # Format event display
            event_display = {
                "channel_on": "ON",
                "channel_off": "OFF",
                "channel_fault": "FAULT",
                "channel_cleared": "CLEARED",
                "threshold_high": "THR↑",
                "threshold_low": "THR↓",
                "system_undervolt": "UNDERVOLT",
                "system_overvolt": "OVERVOLT",
                "system_overtemp": "OVERTEMP",
            }.get(event, event)
            # Format action display
            action_display = {
                "write_channel": "→CH",
                "send_can": "→CAN",
                "send_lin": "→LIN",
                "run_lua": "→LUA",
                "set_output": "→OUT",
            }.get(action, action)
            return f"{event_display} {action_display} {status}"

        return ""

    def _get_channel_source(self, channel_type: ChannelType, data: Dict[str, Any]) -> str:
        """Get source/control channel info for display in Source column."""
        # Power output - show source channel
        if channel_type == ChannelType.POWER_OUTPUT:
            source = data.get('source_channel')
            if source:
                if isinstance(source, int):
                    return f"Channel #{source}"
                return str(source)
            if data.get('enabled', False):
                return "Always ON"
            return "Manual"

        # H-Bridge - show direction/speed source
        elif channel_type == ChannelType.HBRIDGE:
            dir_src = data.get('direction_source')
            speed_src = data.get('speed_source')
            parts = []
            if dir_src:
                parts.append(f"Dir: #{dir_src}" if isinstance(dir_src, int) else f"Dir: {dir_src}")
            if speed_src:
                parts.append(f"Spd: #{speed_src}" if isinstance(speed_src, int) else f"Spd: {speed_src}")
            return ", ".join(parts) if parts else "Manual"

        # Logic - show input sources
        elif channel_type == ChannelType.LOGIC:
            inputs = data.get('input_channels', [])
            if inputs:
                if len(inputs) <= 2:
                    src_list = [f"#{i}" if isinstance(i, int) else str(i) for i in inputs]
                    return ", ".join(src_list)
                return f"{len(inputs)} inputs"
            return ""

        # Math/Number - show input source
        elif channel_type == ChannelType.NUMBER:
            op = data.get('operation', 'constant')
            if op == 'constant':
                return ""
            inputs = data.get('input_channels', [])
            if inputs:
                if len(inputs) <= 2:
                    src_list = [f"#{i}" if isinstance(i, int) else str(i) for i in inputs]
                    return ", ".join(src_list)
                return f"{len(inputs)} inputs"
            return ""

        # Filter - show input source
        elif channel_type == ChannelType.FILTER:
            input_ch = data.get('input_channel')
            if input_ch:
                return f"#{input_ch}" if isinstance(input_ch, int) else str(input_ch)
            return ""

        # PID - show setpoint and input sources
        elif channel_type == ChannelType.PID:
            setpoint = data.get('setpoint_source')
            input_ch = data.get('input_source')
            parts = []
            if setpoint:
                parts.append(f"SP: #{setpoint}" if isinstance(setpoint, int) else f"SP: {setpoint}")
            if input_ch:
                parts.append(f"PV: #{input_ch}" if isinstance(input_ch, int) else f"PV: {input_ch}")
            return ", ".join(parts) if parts else ""

        # Timer - show trigger source or auto-start
        elif channel_type == ChannelType.TIMER:
            if data.get('auto_start', False):
                return "Auto-start on boot"
            start_ch = data.get('start_channel')
            if start_ch:
                return f"Start: #{start_ch}" if isinstance(start_ch, int) else f"Start: {start_ch}"
            return ""

        # Switch - show control source
        elif channel_type == ChannelType.SWITCH:
            ctrl = data.get('control_channel')
            if ctrl:
                return f"#{ctrl}" if isinstance(ctrl, int) else str(ctrl)
            return ""

        # Table - show axis sources
        elif channel_type == ChannelType.TABLE_2D:
            x_src = data.get('x_source')
            if x_src:
                return f"X: #{x_src}" if isinstance(x_src, int) else f"X: {x_src}"
            return ""

        elif channel_type == ChannelType.TABLE_3D:
            x_src = data.get('x_source')
            y_src = data.get('y_source')
            parts = []
            if x_src:
                parts.append(f"X: #{x_src}" if isinstance(x_src, int) else f"X: {x_src}")
            if y_src:
                parts.append(f"Y: #{y_src}" if isinstance(y_src, int) else f"Y: {y_src}")
            return ", ".join(parts) if parts else ""

        # CAN TX - show data sources
        elif channel_type == ChannelType.CAN_TX:
            signals = data.get('signals', [])
            if signals:
                sources = []
                for sig in signals[:2]:
                    src = sig.get('source_channel')
                    if src:
                        sources.append(f"#{src}" if isinstance(src, int) else str(src))
                if len(signals) > 2:
                    return f"{', '.join(sources)}, +{len(signals) - 2}"
                return ", ".join(sources)
            return ""

        # CAN RX - show message reference
        elif channel_type == ChannelType.CAN_RX:
            msg_ref = data.get('message_ref', '')
            if msg_ref:
                return msg_ref
            return ""

        # Lua Script - show trigger source
        elif channel_type == ChannelType.LUA_SCRIPT:
            trigger_ch = data.get('trigger_channel')
            if trigger_ch:
                return f"#{trigger_ch}" if isinstance(trigger_ch, int) else str(trigger_ch)
            return data.get('trigger_type', 'manual').capitalize()

        # Handler - show source and condition
        elif channel_type == ChannelType.HANDLER:
            source = data.get('source_channel', '')
            condition = data.get('condition_channel', '')
            parts = []
            if source:
                parts.append(f"Src: {source}")
            if condition:
                parts.append(f"If: {condition}")
            return ", ".join(parts) if parts else ""

        return ""

    def _get_channel_tooltip(self, channel_type: ChannelType, data: Dict[str, Any]) -> str:
        """Get detailed tooltip for channel."""
        lines = []
        channel_name = data.get("name", data.get("id", "unnamed"))
        channel_id = data.get("channel_id", "")

        lines.append(f"<b>{channel_name}</b>")
        if channel_id:
            lines.append(f"Channel ID: #{channel_id}")
        lines.append(f"Type: {channel_type.value.replace('_', ' ').title()}")
        lines.append("")

        # Type-specific details
        if channel_type == ChannelType.DIGITAL_INPUT:
            lines.append(f"<b>Pin:</b> D{data.get('input_pin', 0) + 1}")
            lines.append(f"<b>Subtype:</b> {data.get('subtype', 'switch_active_low')}")
            if data.get('invert', False):
                lines.append("<b>Inverted:</b> Yes")

        elif channel_type == ChannelType.ANALOG_INPUT:
            lines.append(f"<b>Pin:</b> A{data.get('input_pin', 0) + 1}")
            lines.append(f"<b>Subtype:</b> {data.get('subtype', 'linear')}")
            pullup = data.get('pullup_option', 'none')
            if pullup and pullup != 'none':
                lines.append(f"<b>Pull:</b> {pullup}")
            min_v = data.get('min_voltage', 0)
            max_v = data.get('max_voltage', 5.0)
            min_val = data.get('min_value', 0)
            max_val = data.get('max_value', 100)
            lines.append(f"<b>Range:</b> {min_v}V-{max_v}V -> {min_val}-{max_val}")

        elif channel_type == ChannelType.POWER_OUTPUT:
            pins = data.get('pins', [data.get('channel', 0)])
            if isinstance(pins, list):
                pins_str = ", ".join([f"O{p + 1}" for p in pins])
            else:
                pins_str = f"O{pins + 1}"
            lines.append(f"<b>Pins:</b> {pins_str}")
            lines.append(f"<b>Current Limit:</b> {data.get('current_limit_a', 0)}A")
            lines.append(f"<b>Retry:</b> {data.get('retry_count', 0)} times")
            lines.append(f"<b>Retry Delay:</b> {data.get('retry_delay_ms', 0)}ms")
            lines.append(f"<b>Inrush Time:</b> {data.get('inrush_time_ms', 0)}ms")
            if data.get('pwm_enabled') or data.get('pwm', {}).get('enabled'):
                freq = data.get('pwm_frequency_hz', 0) or data.get('pwm', {}).get('frequency', 0)
                lines.append(f"<b>PWM:</b> {freq}Hz")

        elif channel_type == ChannelType.LOGIC:
            lines.append(f"<b>Operation:</b> {data.get('operation', 'and').upper()}")
            lines.append(f"<b>Delay ON:</b> {data.get('delay_on_ms', 0)}ms")
            lines.append(f"<b>Delay OFF:</b> {data.get('delay_off_ms', 0)}ms")
            inputs = data.get('input_channels', [])
            if inputs:
                lines.append(f"<b>Inputs:</b> {len(inputs)} channels")

        elif channel_type == ChannelType.NUMBER:
            op = data.get('operation', 'constant')
            lines.append(f"<b>Operation:</b> {op}")
            if op == 'constant':
                lines.append(f"<b>Value:</b> {data.get('constant_value', 0)} {data.get('unit', '')}")
            lines.append(f"<b>Min:</b> {data.get('min_value', 0)}")
            lines.append(f"<b>Max:</b> {data.get('max_value', 100)}")

        elif channel_type == ChannelType.TIMER:
            lines.append(f"<b>Mode:</b> {data.get('mode', 'count_up')}")
            h = data.get('limit_hours', 0)
            m = data.get('limit_minutes', 0)
            s = data.get('limit_seconds', 0)
            lines.append(f"<b>Limit:</b> {h}:{m:02d}:{s:02d}")
            if data.get('auto_start', False):
                lines.append("<b>Auto-start:</b> Yes (starts on boot)")
            else:
                start_ch = data.get('start_channel', '')
                if start_ch:
                    lines.append(f"<b>Start Channel:</b> {start_ch}")
            stop_ch = data.get('stop_channel', '')
            if stop_ch:
                lines.append(f"<b>Stop Channel:</b> {stop_ch}")

        elif channel_type == ChannelType.PID:
            lines.append(f"<b>Kp:</b> {data.get('kp', 1.0)}")
            lines.append(f"<b>Ki:</b> {data.get('ki', 0.0)}")
            lines.append(f"<b>Kd:</b> {data.get('kd', 0.0)}")
            lines.append(f"<b>Output Min:</b> {data.get('output_min', 0)}")
            lines.append(f"<b>Output Max:</b> {data.get('output_max', 1000)}")
            lines.append(f"<b>Sample Time:</b> {data.get('sample_time_ms', 100)}ms")

        elif channel_type == ChannelType.HBRIDGE:
            lines.append(f"<b>Bridge:</b> HB{data.get('bridge_number', 0) + 1}")
            mode = data.get('mode', 'coast')
            if hasattr(mode, 'value'):
                mode = mode.value
            lines.append(f"<b>Mode:</b> {mode}")
            preset = data.get('motor_preset', 'custom')
            if hasattr(preset, 'value'):
                preset = preset.value
            lines.append(f"<b>Preset:</b> {preset}")

        elif channel_type == ChannelType.CAN_RX:
            lines.append(f"<b>Message:</b> {data.get('message_ref', '')}")
            data_format = data.get('data_format', '16bit')
            if hasattr(data_format, 'value'):
                data_format = data_format.value
            lines.append(f"<b>Format:</b> {data_format}")
            lines.append(f"<b>Byte Order:</b> {data.get('byte_order', 'little_endian')}")
            lines.append(f"<b>Start Bit:</b> {data.get('start_bit', 0)}")

        elif channel_type == ChannelType.CAN_TX:
            lines.append(f"<b>Message ID:</b> 0x{data.get('message_id', 0):X}")
            lines.append(f"<b>CAN Bus:</b> {data.get('can_bus', 1)}")
            lines.append(f"<b>Mode:</b> {data.get('transmit_mode', 'cycle')}")
            if data.get('transmit_mode') == 'cycle':
                lines.append(f"<b>Frequency:</b> {data.get('frequency_hz', 10)}Hz")

        elif channel_type == ChannelType.LUA_SCRIPT:
            lines.append(f"<b>Trigger:</b> {data.get('trigger_type', 'manual')}")
            lines.append(f"<b>Enabled:</b> {'Yes' if data.get('enabled', True) else 'No'}")
            code = data.get('code', '')
            if code:
                lines.append(f"<b>Code Lines:</b> {len(code.splitlines())}")

        elif channel_type == ChannelType.BLINKMARINE_KEYPAD:
            lines.append(f"<b>Type:</b> {data.get('keypad_type', '2x6')}")
            lines.append(f"<b>CAN Bus:</b> {data.get('can_bus', 1)}")
            lines.append(f"<b>RX Base ID:</b> 0x{data.get('rx_base_id', 0x100):03X}")
            lines.append(f"<b>TX Base ID:</b> 0x{data.get('tx_base_id', 0x200):03X}")
            buttons = data.get('buttons', [])
            configured = sum(1 for b in buttons if b.get('channel_id'))
            lines.append(f"<b>Configured Buttons:</b> {configured}/{len(buttons)}")

        elif channel_type == ChannelType.HANDLER:
            event = data.get('event', 'channel_on')
            action = data.get('action', 'write_channel')
            lines.append(f"<b>Event:</b> {event.replace('_', ' ').title()}")
            source = data.get('source_channel', '')
            if source:
                lines.append(f"<b>Source Channel:</b> {source}")
            condition = data.get('condition_channel', '')
            if condition:
                lines.append(f"<b>Condition:</b> {condition}")
            lines.append(f"<b>Action:</b> {action.replace('_', ' ').title()}")
            target = data.get('target_channel', '')
            if target:
                lines.append(f"<b>Target:</b> {target}")
            if action == 'run_lua':
                lua_func = data.get('lua_function', '')
                if lua_func:
                    lines.append(f"<b>Lua Function:</b> {lua_func}")
            lines.append(f"<b>Enabled:</b> {'Yes' if data.get('enabled', True) else 'No'}")

        return "<br>".join(lines)

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

        # Update display - use 'name' field (new system), fallback to 'id' for backwards compatibility
        channel_name = new_data.get("name", new_data.get("id", "unnamed"))
        channel_id = new_data.get("channel_id", "")

        # Display format: "Name [#ID]" if channel_id exists
        if channel_id:
            display_text = f"{channel_name} [#{channel_id}]"
        else:
            display_text = channel_name

        item.setText(0, display_text)
        item.setText(1, self._get_channel_details(channel_type, new_data))
        item.setText(2, self._get_channel_source(channel_type, new_data))

        # Update status icon
        status_color = self._get_channel_status_color(channel_type, new_data)
        item.setIcon(0, self._create_status_icon(status_color))

        # Update tooltip
        tooltip = self._get_channel_tooltip(channel_type, new_data)
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

    def find_channel_item(self, channel_id: str) -> Optional[QTreeWidgetItem]:
        """Find tree item by channel ID."""
        for folder in self.folders.values():
            for i in range(folder.childCount()):
                item = folder.child(i)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, dict):
                    channel_data = data.get("data", data)
                    item_id = channel_data.get("id", "")
                    if item_id == channel_id:
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
        channel_name = new_data.get("name", new_data.get("id", "unnamed"))
        ch_id = new_data.get("channel_id", "")

        if ch_id:
            display_text = f"{channel_name} [#{ch_id}]"
        else:
            display_text = channel_name

        item.setText(0, display_text)
        item.setText(1, self._get_channel_details(channel_type, new_data))
        item.setText(2, self._get_channel_source(channel_type, new_data))

        # Update status icon
        status_color = self._get_channel_status_color(channel_type, new_data)
        item.setIcon(0, self._create_status_icon(status_color))

        # Update tooltip
        tooltip = self._get_channel_tooltip(channel_type, new_data)
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

    def remove_channel_by_id(self, channel_id: str) -> bool:
        """Remove a channel by its ID."""
        item = self.find_channel_item(channel_id)
        if not item:
            return False

        parent = item.parent()
        if parent:
            parent.removeChild(item)
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
            # Skip the channel being edited (check 'name' first, then 'id' for backwards compatibility)
            channel_name = output.get('name', output.get('id', ''))
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
            # Check 'name' first, then 'id' for backwards compatibility
            channel_name = inp.get('name', inp.get('id', ''))
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
            # Check 'name' first, then 'id' for backwards compatibility
            channel_name = inp.get('name', inp.get('id', ''))
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
            # Check 'name' first, then 'id' for backwards compatibility
            channel_name = hb.get('name', hb.get('id', ''))
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
        self.configuration_changed.emit()

    def _auto_collapse_large_folders(self, threshold: int = 10):
        """Collapse folders that have more than threshold children."""
        def process_item(item: QTreeWidgetItem):
            child_count = item.childCount()
            if child_count > threshold:
                item.setExpanded(False)
            else:
                item.setExpanded(True)
            # Process child folders recursively
            for i in range(child_count):
                child = item.child(i)
                if child.childCount() > 0:
                    process_item(child)

        # Process all top-level items (main category folders)
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            if top_item:
                # Always expand top-level categories
                top_item.setExpanded(True)
                # Process subfolders
                for j in range(top_item.childCount()):
                    subfolder = top_item.child(j)
                    if subfolder:
                        process_item(subfolder)

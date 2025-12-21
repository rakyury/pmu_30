"""
Project Tree Widget
Hierarchical tree view of all configuration items (like ECUMaster PMU Client)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMenu, QMessageBox, QStyle, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from typing import Dict, Any, Optional, List


class ProjectTree(QWidget):
    """Project tree with all configuration items."""

    # Signals
    item_selected = pyqtSignal(str, object)  # (item_type, item_data)
    item_added = pyqtSignal(str)  # item_type
    item_edited = pyqtSignal(str, object)  # (item_type, item_data)
    item_deleted = pyqtSignal(str, object)  # (item_type, item_data)
    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._create_default_structure()

    def _get_icon(self, category: str) -> QIcon:
        """Get icon for category."""
        app = QApplication.instance()
        if not app:
            return QIcon()

        style = app.style()
        icon_map = {
            "outputs": QStyle.StandardPixmap.SP_MediaPlay,
            "inputs": QStyle.StandardPixmap.SP_ArrowRight,
            "logic": QStyle.StandardPixmap.SP_FileIcon,
            "switches": QStyle.StandardPixmap.SP_DialogYesButton,
            "can": QStyle.StandardPixmap.SP_DriveNetIcon,
            "timers": QStyle.StandardPixmap.SP_BrowserReload,
            "tables": QStyle.StandardPixmap.SP_FileDialogListView,
            "numbers": QStyle.StandardPixmap.SP_DialogOkButton,
            "hbridge": QStyle.StandardPixmap.SP_ComputerIcon,
            "pid": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "lua": QStyle.StandardPixmap.SP_FileDialogContentsView,
        }

        pixmap_type = icon_map.get(category, QStyle.StandardPixmap.SP_DirIcon)
        return style.standardIcon(pixmap_type)

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Name")
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Name", "Formula/Value"])
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

    def _create_default_structure(self):
        """Create default tree structure."""
        # OUT folder
        self.out_folder = QTreeWidgetItem(self.tree, ["OUT", ""])
        self.out_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "outputs"})
        self.out_folder.setIcon(0, self._get_icon("outputs"))
        self.out_folder.setExpanded(True)

        # IN folder
        self.in_folder = QTreeWidgetItem(self.tree, ["IN", ""])
        self.in_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "inputs"})
        self.in_folder.setIcon(0, self._get_icon("inputs"))
        self.in_folder.setExpanded(True)

        # Functions folder
        self.functions_folder = QTreeWidgetItem(self.tree, ["Functions", ""])
        self.functions_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "logic"})
        self.functions_folder.setIcon(0, self._get_icon("logic"))
        self.functions_folder.setExpanded(True)

        # Switches folder
        self.switches_folder = QTreeWidgetItem(self.tree, ["Switches", ""])
        self.switches_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "switches"})
        self.switches_folder.setIcon(0, self._get_icon("switches"))

        # CAN folder
        self.can_folder = QTreeWidgetItem(self.tree, ["CAN", ""])
        self.can_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "can"})
        self.can_folder.setIcon(0, self._get_icon("can"))

        # Timers folder
        self.timers_folder = QTreeWidgetItem(self.tree, ["Timers", ""])
        self.timers_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "timers"})
        self.timers_folder.setIcon(0, self._get_icon("timers"))

        # Tables folder
        self.tables_folder = QTreeWidgetItem(self.tree, ["Tables", ""])
        self.tables_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "tables"})
        self.tables_folder.setIcon(0, self._get_icon("tables"))

        # Numbers folder
        self.numbers_folder = QTreeWidgetItem(self.tree, ["Numbers", ""])
        self.numbers_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "numbers"})
        self.numbers_folder.setIcon(0, self._get_icon("numbers"))

        # H-Bridge folder
        self.hbridge_folder = QTreeWidgetItem(self.tree, ["H-Bridge", ""])
        self.hbridge_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "hbridge"})
        self.hbridge_folder.setIcon(0, self._get_icon("hbridge"))

        # PID folder
        self.pid_folder = QTreeWidgetItem(self.tree, ["PID Controllers", ""])
        self.pid_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "pid"})
        self.pid_folder.setIcon(0, self._get_icon("pid"))

        # LUA folder
        self.lua_folder = QTreeWidgetItem(self.tree, ["Lua Scripts", ""])
        self.lua_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "category": "lua"})
        self.lua_folder.setIcon(0, self._get_icon("lua"))

    def _on_selection_changed(self):
        """Handle selection change."""
        items = self.tree.selectedItems()
        if items:
            item = items[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                item_type = data.get("type", "")
                self.item_selected.emit(item_type, data)

    def _on_item_double_clicked(self, item, column):
        """Handle double click - edit item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") != "folder":
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
            add_action = menu.addAction("Add Item")
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

        # Get category from folder or parent
        if data.get("type") == "folder":
            category = data.get("category", "")
            parent_item = item
        else:
            parent_item = item.parent()
            if parent_item:
                parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
                category = parent_data.get("category", "")
            else:
                return

        # Emit signal to open appropriate dialog
        self.item_added.emit(category)

    def _duplicate_item(self):
        """Duplicate selected item."""
        items = self.tree.selectedItems()
        if not items:
            return

        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get("type") != "folder":
            # Create duplicate
            parent = item.parent()
            if parent:
                new_item = QTreeWidgetItem(parent)
                new_item.setText(0, item.text(0) + " (Copy)")
                new_item.setText(1, item.text(1))

                # Deep copy data
                import copy
                new_data = copy.deepcopy(data)
                new_item.setData(0, Qt.ItemDataRole.UserRole, new_data)

                self.configuration_changed.emit()

    def _delete_item(self):
        """Delete selected item."""
        items = self.tree.selectedItems()
        if not items:
            return

        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get("type") != "folder":
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete '{item.text(0)}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                    self.item_deleted.emit(data.get("category", ""), data)
                    self.configuration_changed.emit()

    def _edit_item(self):
        """Edit selected item."""
        items = self.tree.selectedItems()
        if not items:
            return

        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get("type") != "folder":
            category = data.get("category", "")
            self.item_edited.emit(category, data)

    def add_output(self, output_data: Dict[str, Any]):
        """Add output to tree."""
        item = QTreeWidgetItem(self.out_folder)
        item.setText(0, f"o_{output_data.get('name', 'Unnamed')}")
        item.setText(1, f"Ch{output_data.get('channel', 0)}")
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "output",
            "category": "outputs",
            "data": output_data
        })

    def add_input(self, input_data: Dict[str, Any]):
        """Add input to tree."""
        item = QTreeWidgetItem(self.in_folder)
        item.setText(0, f"in.{input_data.get('name', 'Unnamed')}")
        item.setText(1, input_data.get('type', ''))
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "input",
            "category": "inputs",
            "data": input_data
        })

    def add_logic_function(self, logic_data: Dict[str, Any]):
        """Add logic function to tree."""
        item = QTreeWidgetItem(self.functions_folder)
        item.setText(0, logic_data.get('name', 'Unnamed'))

        # Build formula string
        operation = logic_data.get('operation', 'AND')
        item.setText(1, f"{operation}")

        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "logic",
            "category": "logic",
            "data": logic_data
        })

    def add_hbridge(self, hbridge_data: Dict[str, Any]):
        """Add H-Bridge to tree."""
        item = QTreeWidgetItem(self.hbridge_folder)
        item.setText(0, hbridge_data.get('name', 'Unnamed'))
        item.setText(1, hbridge_data.get('mode', 'Bidirectional'))
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "hbridge",
            "category": "hbridge",
            "data": hbridge_data
        })

    def add_pid_controller(self, pid_data: Dict[str, Any]):
        """Add PID controller to tree."""
        item = QTreeWidgetItem(self.pid_folder)
        item.setText(0, pid_data.get('name', 'Unnamed'))
        params = pid_data.get('parameters', {})
        item.setText(1, f"Kp={params.get('kp', 0)}, Ki={params.get('ki', 0)}, Kd={params.get('kd', 0)}")
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pid",
            "category": "pid",
            "data": pid_data
        })

    def add_lua_script(self, lua_data: Dict[str, Any]):
        """Add LUA script to tree."""
        item = QTreeWidgetItem(self.lua_folder)
        item.setText(0, lua_data.get('name', 'Unnamed'))
        trigger = lua_data.get('trigger', {})
        item.setText(1, trigger.get('type', 'Manual'))
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "lua",
            "category": "lua",
            "data": lua_data
        })

    def add_number(self, number_data: Dict[str, Any]):
        """Add number constant to tree."""
        item = QTreeWidgetItem(self.numbers_folder)
        item.setText(0, number_data.get('name', 'Unnamed'))
        value = number_data.get('value', 0.0)
        unit = number_data.get('unit', '')
        item.setText(1, f"{value} {unit}".strip())
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "number",
            "category": "numbers",
            "data": number_data
        })

    def add_switch(self, switch_data: Dict[str, Any]):
        """Add switch to tree."""
        item = QTreeWidgetItem(self.switches_folder)
        item.setText(0, switch_data.get('name', 'Unnamed'))
        condition = switch_data.get('condition', {})
        comparison = condition.get('comparison', '>')
        threshold = condition.get('threshold', 0)
        item.setText(1, f"{comparison} {threshold}")
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "switch",
            "category": "switches",
            "data": switch_data
        })

    def add_table(self, table_data: Dict[str, Any]):
        """Add lookup table to tree."""
        item = QTreeWidgetItem(self.tables_folder)
        item.setText(0, table_data.get('name', 'Unnamed'))
        table_points = table_data.get('table_data', [])
        item.setText(1, f"{len(table_points)} points")
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "table",
            "category": "tables",
            "data": table_data
        })

    def add_timer(self, timer_data: Dict[str, Any]):
        """Add timer to tree."""
        item = QTreeWidgetItem(self.timers_folder)
        item.setText(0, timer_data.get('name', 'Unnamed'))
        mode = timer_data.get('mode', 'On Delay')
        timing = timer_data.get('timing', {})
        delay = timing.get('delay_ms', 0)
        item.setText(1, f"{mode} ({delay}ms)")
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "timer",
            "category": "timers",
            "data": timer_data
        })

    def add_can_message(self, can_data: Dict[str, Any]):
        """Add CAN message to tree."""
        item = QTreeWidgetItem(self.can_folder)
        item.setText(0, can_data.get('name', 'Unnamed'))
        msg_id = can_data.get('id', 0)
        item.setText(1, f"ID: 0x{msg_id:X}")
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "can",
            "category": "can",
            "data": can_data
        })

    def update_current_item(self, new_data: Dict[str, Any]):
        """Update currently selected item with new data."""
        items = self.tree.selectedItems()
        if not items:
            return False

        item = items[0]
        old_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not old_data or old_data.get("type") == "folder":
            return False

        category = old_data.get("category", "")

        # Update the item based on category
        if category == "outputs":
            item.setText(0, f"o_{new_data.get('name', 'Unnamed')}")
            item.setText(1, f"Ch{new_data.get('channel', 0)}")
        elif category == "inputs":
            item.setText(0, f"in.{new_data.get('name', 'Unnamed')}")
            item.setText(1, new_data.get('type', ''))
        elif category == "logic":
            item.setText(0, new_data.get('name', 'Unnamed'))
            operation = new_data.get('operation', 'AND')
            item.setText(1, f"{operation}")
        elif category == "hbridge":
            item.setText(0, new_data.get('name', 'Unnamed'))
            item.setText(1, new_data.get('mode', 'Bidirectional'))
        elif category == "pid":
            item.setText(0, new_data.get('name', 'Unnamed'))
            params = new_data.get('parameters', {})
            item.setText(1, f"Kp={params.get('kp', 0)}, Ki={params.get('ki', 0)}, Kd={params.get('kd', 0)}")
        elif category == "lua":
            item.setText(0, new_data.get('name', 'Unnamed'))
            trigger = new_data.get('trigger', {})
            item.setText(1, trigger.get('type', 'Manual'))

        # Update stored data
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": old_data.get("type"),
            "category": category,
            "data": new_data
        })

        self.configuration_changed.emit()
        return True

    def get_all_outputs(self) -> List[Dict[str, Any]]:
        """Get all output configurations."""
        outputs = []
        for i in range(self.out_folder.childCount()):
            child = self.out_folder.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "output":
                outputs.append(data.get("data", {}))
        return outputs

    def get_all_inputs(self) -> List[Dict[str, Any]]:
        """Get all input configurations."""
        inputs = []
        for i in range(self.in_folder.childCount()):
            child = self.in_folder.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "input":
                inputs.append(data.get("data", {}))
        return inputs

    def get_all_logic_functions(self) -> List[Dict[str, Any]]:
        """Get all logic function configurations."""
        functions = []
        for i in range(self.functions_folder.childCount()):
            child = self.functions_folder.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "logic":
                functions.append(data.get("data", {}))
        return functions

    def get_all_hbridges(self) -> List[Dict[str, Any]]:
        """Get all H-Bridge configurations."""
        hbridges = []
        for i in range(self.hbridge_folder.childCount()):
            child = self.hbridge_folder.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "hbridge":
                hbridges.append(data.get("data", {}))
        return hbridges

    def get_all_pid_controllers(self) -> List[Dict[str, Any]]:
        """Get all PID controller configurations."""
        controllers = []
        for i in range(self.pid_folder.childCount()):
            child = self.pid_folder.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "pid":
                controllers.append(data.get("data", {}))
        return controllers

    def get_all_lua_scripts(self) -> List[Dict[str, Any]]:
        """Get all LUA script configurations."""
        scripts = []
        for i in range(self.lua_folder.childCount()):
            child = self.lua_folder.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "lua":
                scripts.append(data.get("data", {}))
        return scripts

    def clear_all(self):
        """Clear all items from tree (keep folder structure)."""
        for folder in [self.out_folder, self.in_folder, self.functions_folder,
                      self.switches_folder, self.can_folder, self.timers_folder,
                      self.tables_folder, self.numbers_folder, self.hbridge_folder,
                      self.pid_folder, self.lua_folder]:
            while folder.childCount() > 0:
                folder.removeChild(folder.child(0))
